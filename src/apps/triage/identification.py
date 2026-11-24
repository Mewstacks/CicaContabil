"""Which company is this document for? A scoreboard of signals, never a guess.

Each signal gives points to one company of the office. A company is accepted with at least
``ACCEPT_SCORE`` points and a lead of ``ACCEPT_MARGIN`` over the runner-up. Two *hard*
proofs (CNPJ, Domínio code, field rule, known bank account) for different companies are a
conflict: nobody decides, a person does. A wrong company is worse than no company.

Signals (points): CNPJ in name, subject, text or body 100 (hard; letters accepted since
jul/2026); Domínio code prefix in the file name 100 (hard); field rule taught by the office
100 (hard); bank account learned from 2 proofs 100 (hard); sender learned from 3 e-mails
and 3 files 100; the company's name in the text 40. Learned links and rules only ever come
from the same office. Structure only taken from HubFedrizzi ``identificacao.py``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import PurePosixPath
from uuid import UUID

from apps.common.cnpj import normalize_cnpj
from apps.hub.models import ClientCompany
from apps.triage import learning
from apps.triage.catalog import words
from apps.triage.models import LearnedLink, TriageItem

ACCEPT_SCORE = 100
ACCEPT_MARGIN = 50
HARD_POINTS = 100
NAME_POINTS = 40
_CNPJ = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z0-9]{2})\.?([A-Za-z0-9]{3})\.?([A-Za-z0-9]{3})/?"
    r"([A-Za-z0-9]{4})-?(\d{2})(?![A-Za-z0-9])"
)
_LEGAL_WORDS = frozenset({"ltda", "me", "epp", "eireli", "sa", "s", "a", "de", "da", "do", "e"})


@dataclass(frozen=True)
class Signal:
    kind: str
    company_id: UUID
    points: int
    text: str
    hard: bool


@dataclass
class Identification:
    company: ClientCompany | None = None
    status: str = "none"  # accepted | conflict | ambiguous | weak | none
    score: int = 0
    margin: int = 0
    signals: list[Signal] = field(default_factory=list)
    candidates: list[tuple[ClientCompany, int]] = field(default_factory=list)

    def as_scores(self) -> dict[str, object]:
        return {"score": self.score, "margin": self.margin, "status": self.status}


def _name_phrase(name: str) -> str:
    tokens = [token for token in words(name).split() if token not in _LEGAL_WORDS]
    phrase = " ".join(tokens)
    return phrase if len(phrase) >= 8 else ""


def identify_company(item: TriageItem, sources: dict[str, str]) -> Identification:
    companies = list(ClientCompany.objects.filter(organization=item.organization, active=True))
    by_id = {company.pk: company for company in companies}
    # one signal per (company, kind): the first, strongest evidence found
    found: dict[UUID, dict[str, Signal]] = {}

    def add(company: ClientCompany, kind: str, points: int, text: str, *, hard: bool) -> None:
        found.setdefault(company.pk, {}).setdefault(
            kind, Signal(kind, company.pk, points, text, hard)
        )

    by_cnpj: dict[str, ClientCompany] = {}
    for company in companies:
        try:
            by_cnpj[normalize_cnpj(company.cnpj_masked)] = company
        except Exception:  # noqa: S112 - blank or malformed registration: found by code only
            continue
    for source, text in sources.items():
        for match in _CNPJ.finditer(text):
            try:
                cnpj = normalize_cnpj("".join(match.groups()))
            except Exception:  # noqa: S112 - not a valid CNPJ
                continue
            if cnpj in by_cnpj:
                add(by_cnpj[cnpj], "cnpj", HARD_POINTS, f"CNPJ no {source}", hard=True)

    stem = PurePosixPath(item.original_name.replace("\\", "/")).stem
    prefix = re.match(r"\s*([A-Za-z0-9]+)[_\s-]", stem)
    if prefix:
        for company in companies:
            if (
                company.dominio_code
                and company.dominio_code.casefold() == prefix.group(1).casefold()
            ):
                add(company, "code", HARD_POINTS, "Código Domínio no nome", hard=True)

    for company in companies:
        phrase = _name_phrase(company.name)
        if not phrase:
            continue
        for source, text in sources.items():
            if f" {phrase} " in f" {words(text)} ":
                add(company, "name", NAME_POINTS, f"Nome da empresa no {source}", hard=False)
                break

    for key in learning.item_sender_keys(item):
        for company in learning.active_link_companies(
            item.organization, LearnedLink.Kind.SENDER, key
        ):
            add(company, "sender", HARD_POINTS, "Remetente conhecido", hard=False)
    account = (
        learning.ofx_account_key(sources.get("conteúdo", ""))
        if item.original_name.casefold().endswith(".ofx")
        else ""
    )
    for company in learning.active_link_companies(
        item.organization, LearnedLink.Kind.ACCOUNT, account
    ):
        add(company, "account", HARD_POINTS, "Conta bancária conhecida", hard=True)
    # Each source on its own: a rule anchors on lines, and sources must not be glued together.
    for text in (sources.get("conteúdo", ""), sources.get("corpo", "")):
        for rule in learning.matching_rules(item.organization, text):
            if rule.company_id in by_id:
                label = rule.anchor or rule.value
                add(
                    by_id[rule.company_id],
                    "rule",
                    HARD_POINTS,
                    f"Regra de campo: {label}",
                    hard=True,
                )

    totals = {pk: sum(sig.points for sig in sigs.values()) for pk, sigs in found.items()}
    ranking = sorted(totals.items(), key=lambda pair: pair[1], reverse=True)
    result = Identification(
        candidates=[(by_id[pk], points) for pk, points in ranking if pk in by_id]
    )
    if not ranking:
        return result

    def ordered(pk: UUID) -> list[Signal]:
        return sorted(found[pk].values(), key=lambda sig: (not sig.hard, -sig.points, sig.kind))

    hard_companies = [pk for pk, sigs in found.items() if any(sig.hard for sig in sigs.values())]
    top_pk, top = ranking[0]
    second = ranking[1][1] if len(ranking) > 1 else 0
    result.score, result.margin = top, top - second
    if len(hard_companies) > 1:
        result.status = "conflict"
        result.signals = [sig for pk in hard_companies for sig in ordered(pk) if sig.hard]
        return result
    result.signals = ordered(top_pk)
    if top >= ACCEPT_SCORE and top - second >= ACCEPT_MARGIN:
        result.status, result.company = "accepted", by_id[top_pk]
    elif top >= ACCEPT_SCORE:
        result.status = "ambiguous"
    else:
        result.status = "weak"
    return result
