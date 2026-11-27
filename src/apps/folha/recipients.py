"""Quem recebe o e-mail da folha: decisão fail-closed a partir dos contatos do Domínio.

A folha traz o salário de todos; adivinhar o destinatário é pior do que perguntar. A fonte é o
cadastro de contatos da empresa (``GEEMPRE_CONTATO``), lido na máquina do agente. O campo de
observação é texto livre e sujo, e é ele que diz qual e-mail é o da folha. Portado do
``contatos.py`` do HubFedrizzi (regras, não código).
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

FOLHA_MARKS = ("FOLHA", "FIOLHA", "FOLNA", "PAGTO", "PAGAMENTO")
REFUSED_MARKS = ("SEMCONTATO", "HONORARIO", "PARTICULAR")
CHANNEL_MARKS = ("WHATS", "WPP", "WATS", "WHTAS")

UNIQUE = "unico"
MARKED = "marcado"
AMBIGUOUS = "ambiguo"
NO_EMAIL = "sem_email"

_EMAIL = re.compile(r"^[A-Za-z0-9._%+'-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
_SPLIT = re.compile(r"[\s/;,]+")


class RecipientError(ValueError):
    """Escolha de destinatário recusada."""


@dataclass(frozen=True)
class Contact:
    emails: tuple[str, ...]
    note: str = ""


@dataclass
class Decision:
    situation: str
    candidates: list[str] = field(default_factory=list)
    recipients: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def blocks_sending(self) -> bool:
        return self.situation in {AMBIGUOUS, NO_EMAIL} and not self.recipients


def normalize_note(note: str) -> str:
    text = unicodedata.normalize("NFKD", note or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).upper()
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


def _has(note: str, marks: tuple[str, ...]) -> bool:
    spaced = f" {note} "
    compact = note.replace(" ", "")
    return any(f" {m} " in spaced or m in compact for m in marks)


def extract_emails(raw: str) -> list[str]:
    """Endereços plausíveis do campo, sem repetir e na ordem. Endereço truncado é descartado."""

    seen: dict[str, None] = {}
    for part in _SPLIT.split(raw or ""):
        part = part.strip().strip("<>()[]\"'").rstrip(".")
        if part and _EMAIL.match(part):
            seen.setdefault(part.lower(), None)
    return list(seen)


def is_refused(note: str) -> bool:
    normalized = normalize_note(note)
    if _has(normalized, REFUSED_MARKS):
        return True
    # Recado de canal ("MANDAR NO WPP") só recusa se NÃO disser também que é da folha.
    return _has(normalized, CHANNEL_MARKS) and not _has(normalized, FOLHA_MARKS)


def is_payroll(note: str) -> bool:
    return _has(normalize_note(note), FOLHA_MARKS)


def decide(contacts: list[Contact]) -> Decision:
    usable = [c for c in contacts if c.emails and not is_refused(c.note)]
    candidates: list[str] = []
    for contact in usable:
        for email in contact.emails:
            if email not in candidates:
                candidates.append(email)
    if not usable:
        has_email = any(c.emails for c in contacts)
        reason = (
            "Todos os contatos com e-mail estão marcados para não receber."
            if has_email
            else "Nenhum contato com e-mail válido."
        )
        return Decision(NO_EMAIL, reason=reason)
    if len(usable) == 1:
        return Decision(UNIQUE, candidates, list(usable[0].emails))
    marked = [c for c in usable if is_payroll(c.note)]
    if len(marked) == 1:
        return Decision(MARKED, candidates, list(marked[0].emails))
    reason = (
        "Mais de um contato marcado como folha."
        if marked
        else "Vários contatos e nenhum marcado como folha."
    )
    return Decision(AMBIGUOUS, candidates, reason=reason)


def resolve(decision: Decision, *, chosen: list[str], manual: str = "") -> list[str]:
    """Aplica a escolha humana. Só vale entre os candidatos lidos agora, ou e-mail manual quando
    o cadastro não tem nenhum utilizável (``sem_email``) — nunca para ignorar contato válido."""

    if decision.situation in {UNIQUE, MARKED} and not chosen and not manual:
        return list(decision.recipients)
    if manual:
        if decision.situation != NO_EMAIL:
            raise RecipientError(
                "E-mail manual só vale quando o cadastro não tem contato utilizável."
            )
        found = extract_emails(manual)
        if len(found) != 1 or found[0] != manual.strip().lower():
            raise RecipientError("Informe um único e-mail válido.")
        return found
    if not chosen:
        raise RecipientError("Escolha o destinatário.")
    allowed = set(decision.candidates)
    picked = [e.strip().lower() for e in chosen]
    if any(e not in allowed for e in picked):
        raise RecipientError("Destinatário fora dos contatos atuais do cadastro.")
    return list(dict.fromkeys(picked))
