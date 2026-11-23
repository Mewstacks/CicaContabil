"""What an office taught the engine: sender and bank-account links, sender rules, field rules.

Everything is keyed by the office: nothing learned in one office can change a decision in
another (every query filters ``organization``; ``clean()`` refuses a foreign company).
Learning only happens from hard proofs and from a person's decision, and a person's
correction of an archived document blocks the wrong link for good.

Pattern (structure only): HubFedrizzi ``services.py`` learning loops, ``regras.py``.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from email.utils import parseaddr

from django.db import transaction

from apps.hub.models import ClientCompany
from apps.organizations.models import Membership, Organization
from apps.triage.catalog import words
from apps.triage.models import (
    DocumentType,
    ExtractionRule,
    LearnedLink,
    LinkProof,
    SenderRule,
    TriageItem,
)

SENDER_MIN_EMAILS = 3
SENDER_MIN_FILES = 3
ACCOUNT_MIN_PROOFS = 2
SENDER_RULE_CONFIRMATIONS = 3
RULE_MAX_ERRORS = 3
_CONFIRMED_CAP = 30
_OFX_BANK = re.compile(r"<BANKID>\s*([0-9A-Za-z]+)", re.IGNORECASE)
_OFX_ACCOUNT = re.compile(r"<ACCTID>\s*([0-9A-Za-z.\-]+)", re.IGNORECASE)


def sender_key(value: str) -> str:
    """The bare, lower-cased address of a ``From`` value ("" when there is none)."""

    address = parseaddr(value or "")[1].strip().casefold()
    return address if "@" in address else ""


def _internal_forward(item: TriageItem, outer: str) -> bool:
    """Is the outer sender known staff of this office (the mailbox itself or a member)?

    Only then is the author named in the body worth anything: any outside sender can write
    ``De: someone@victim`` in a message, and a domain match proves nothing (the From header is
    spoofable and DKIM/DMARC results are not available here). Staff means the mailbox address
    or the e-mail of a person with a membership in this office.
    """

    mailbox = item.mailbox if item.mailbox_id else None
    if mailbox is None or "@" not in outer:
        return False
    if outer == mailbox.address.strip().casefold():
        return True
    return Membership.objects.filter(
        organization_id=item.organization_id, user__email__iexact=outer
    ).exists()


def item_sender_keys(item: TriageItem) -> list[str]:
    """The authenticated-looking sender, plus the original author of an internal forward."""

    outer = sender_key(item.sender)
    keys = [outer] if outer else []
    original = sender_key(item.original_sender)
    if original and original not in keys and _internal_forward(item, outer):
        keys.insert(0, original)
    return keys


def ofx_account_key(text: str) -> str:
    bank, account = _OFX_BANK.search(text or ""), _OFX_ACCOUNT.search(text or "")
    if not bank or not account:
        return ""
    return f"{bank.group(1).lstrip('0') or '0'}:{account.group(1)}"[:254]


def link_is_active(link: LearnedLink) -> bool:
    if link.blocked:
        return False
    proofs = link.proofs.all()
    files = proofs.values("content_hash").distinct().count()
    if link.kind == LearnedLink.Kind.SENDER:
        emails = proofs.values("message_id").distinct().count()
        return emails >= SENDER_MIN_EMAILS and files >= SENDER_MIN_FILES
    return files >= ACCOUNT_MIN_PROOFS


def active_link_companies(organization: Organization, kind: str, key: str) -> list[ClientCompany]:
    """Companies this office taught the engine for ``key`` (active links only)."""

    if not key:
        return []
    found: list[ClientCompany] = []
    for link in LearnedLink.objects.filter(
        organization=organization, kind=kind, key=key, blocked=False
    ).select_related("company"):
        if link.company.active and link_is_active(link):
            found.append(link.company)
    return found


def record_hard_proof(item: TriageItem, company: ClientCompany) -> bool:
    """Count this e-mail and file as a proof of sender/account → company.

    Idempotent per (message, file). Returns True when a link just became active, so the
    caller can reclassify what was waiting.
    """

    if company.organization_id != item.organization_id or not item.content_hash:
        return False
    message_id = item.message_id or f"item:{item.pk}"
    became_active = False
    keys = [(LearnedLink.Kind.SENDER, key) for key in item_sender_keys(item)]
    for kind, key in keys:
        with transaction.atomic():
            link, _ = LearnedLink.objects.get_or_create(
                organization_id=item.organization_id, kind=kind, key=key, company=company
            )
            if link.blocked:
                continue
            was_active = link_is_active(link)
            LinkProof.objects.get_or_create(
                organization_id=item.organization_id,
                link=link,
                message_id=message_id,
                content_hash=item.content_hash,
            )
            became_active = became_active or (not was_active and link_is_active(link))
    return became_active


def record_account_proof(item: TriageItem, company: ClientCompany, text: str) -> bool:
    """Same as ``record_hard_proof`` for the account key of a structured OFX document."""

    key = ofx_account_key(text)
    if not key or company.organization_id != item.organization_id:
        return False
    message_id = item.message_id or f"item:{item.pk}"
    link, _ = LearnedLink.objects.get_or_create(
        organization_id=item.organization_id,
        kind=LearnedLink.Kind.ACCOUNT,
        key=key,
        company=company,
    )
    if link.blocked:
        return False
    was_active = link_is_active(link)
    LinkProof.objects.get_or_create(
        organization_id=item.organization_id,
        link=link,
        message_id=message_id,
        content_hash=item.content_hash,
    )
    return not was_active and link_is_active(link)


def learn_from_approval(item: TriageItem) -> bool:
    """A person approved ``item``: its company is the truth the sender/account links learn.

    Auto-approved items never teach (no self-reinforcement) and nothing is learned before a
    person decided, so a crafted e-mail cannot poison the links by itself. Returns True when a
    link just became active (pending items then deserve a fresh look).
    """

    company = item.company
    if (
        item.auto_decision == "auto"
        or company is None
        or company.organization_id != item.organization_id
    ):
        return False
    activated = record_hard_proof(item, company)
    account = str((item.scores or {}).get("account", ""))
    if account:
        bank, _, number = account.partition(":")
        activated = (
            record_account_proof(item, company, f"<BANKID>{bank}</BANKID><ACCTID>{number}</ACCTID>")
            or activated
        )
    return activated


# ---- sender rule: a person's confirmation, three activate -----------------------------------


def confirm_sender_rule(item: TriageItem) -> SenderRule | None:
    """A reviewer approved ``item`` with this type: count it once for its sender."""

    if item.document_type_id is None:
        return None
    key = (item_sender_keys(item) or [""])[0]
    if not key:
        return None
    rule, _ = SenderRule.objects.get_or_create(
        organization_id=item.organization_id, sender=key, document_type_id=item.document_type_id
    )
    if rule.blocked:
        return rule
    confirmed = list(rule.confirmed_items or [])
    if str(item.pk) not in confirmed:
        confirmed.append(str(item.pk))
        rule.confirmed_items = confirmed[-_CONFIRMED_CAP:]
        rule.save(update_fields=["confirmed_items", "updated_at"])
    return rule


def sender_rule_types(item: TriageItem) -> list[DocumentType]:
    """Types this office's active sender rules point to for the item's sender."""

    found: list[DocumentType] = []
    for key in item_sender_keys(item):
        for rule in SenderRule.objects.filter(
            organization_id=item.organization_id, sender=key, blocked=False
        ).select_related("document_type"):
            if len(rule.confirmed_items or []) >= SENDER_RULE_CONFIRMATIONS and (
                rule.document_type.active
            ):
                found.append(rule.document_type)
    return found


# ---- field rules: the operator selects the text that names the company ---------------------


def derive_rule(text: str, selected: str) -> tuple[str, str]:
    """(mode, anchor) for a selection inside ``text``; raises ``ValueError`` when unusable."""

    selected = " ".join(selected.split())
    if len(selected) < 4 or selected.isdigit() or len(selected) > 200:
        raise ValueError("Selecione um trecho com nome ou identificação da empresa.")
    lines = [line.strip() for line in text.splitlines()]
    for index, line in enumerate(lines):
        normalized = " ".join(line.split())
        position = normalized.find(selected)
        if position < 0:
            continue
        before = normalized[:position].rstrip()
        if before.endswith(":") and 1 < len(before) <= 121:
            return "dois_pontos", before[:-1].strip()[:120]
        if normalized == selected:
            previous = next((lines[j] for j in range(index - 1, -1, -1) if lines[j]), "")
            if previous and len(previous) <= 120:
                return "linha_seguinte", " ".join(previous.split())[:120]
        return "contem", ""
    raise ValueError("O trecho não está no texto lido do documento.")


def create_field_rule(
    *, item: TriageItem, company: ClientCompany, selected: str, text: str
) -> ExtractionRule:
    if company.organization_id != item.organization_id:
        raise ValueError("A empresa não pertence a este escritório.")
    mode, anchor = derive_rule(text, selected)
    return ExtractionRule.objects.create(
        organization_id=item.organization_id,
        mode=mode,
        anchor=anchor,
        value=" ".join(selected.split())[:200],
        company=company,
        source_item=item,
    )


def _captured(rule: ExtractionRule, text: str) -> list[str]:
    anchor = words(rule.anchor)
    if rule.mode == ExtractionRule.Mode.COLON:
        found: list[str] = []
        for line in text.splitlines():
            head, sep, tail = line.partition(":")
            if sep and words(head) == anchor and tail.strip():
                found.append(tail.strip())
        return found
    if rule.mode == ExtractionRule.Mode.NEXT_LINE:
        lines = [line.strip() for line in text.splitlines()]
        found = []
        for index, line in enumerate(lines[:-1]):
            if line and words(line) == anchor:
                following = next((candidate for candidate in lines[index + 1 :] if candidate), "")
                if following:
                    found.append(following)
        return found
    return [text] if f" {words(rule.value)} " in f" {words(text)} " else []


def matching_rules(organization: Organization, text: str) -> Iterable[ExtractionRule]:
    """Active field rules of this office that fire on ``text`` (value equals the capture)."""

    for rule in ExtractionRule.objects.filter(
        organization=organization, active=True
    ).select_related("company"):
        if not rule.company.active:
            continue
        wanted = words(rule.value)
        if rule.mode == ExtractionRule.Mode.CONTAINS:
            if _captured(rule, text):
                yield rule
        elif any(words(value) == wanted for value in _captured(rule, text)):
            yield rule


# ---- correction of an archived document undoes a wrong link ---------------------------------


def undo_wrong_company(item: TriageItem, wrong: ClientCompany | None) -> None:
    """A person says ``item`` was filed under the wrong company: block what taught that."""

    if wrong is None or wrong.organization_id != item.organization_id:
        return
    for kind, key in [(LearnedLink.Kind.SENDER, k) for k in item_sender_keys(item)] + [
        (LearnedLink.Kind.ACCOUNT, str((item.scores or {}).get("account", "")))
    ]:
        if key:
            LearnedLink.objects.filter(
                organization_id=item.organization_id, kind=kind, key=key, company=wrong
            ).update(blocked=True)
    for rule in ExtractionRule.objects.filter(
        organization_id=item.organization_id, company=wrong, source_item=item
    ):
        rule.errors = RULE_MAX_ERRORS
        rule.active = False
        rule.save(update_fields=["errors", "active", "updated_at"])
