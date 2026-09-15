"""The triage item state machine.

This module has no Django model dependency on purpose: it is pure data (the allowed
edges) plus one pure function (``ensure_transition_allowed``). Nothing here reads a
mailbox, calls the AI adapter, or touches the filesystem — the rule from
``docs/plano-triagem-documental.md`` front 2 is that the domain layer contains no I/O.

Flow (see the plan doc for the full rationale of each state):

    recebido -> em_quarentena
    em_quarentena -> rejeitado | aguardando_extracao
    aguardando_extracao -> em_extracao
    em_extracao -> aguardando_revisao | pronto_para_arquivar | falha
    aguardando_revisao -> pronto_para_arquivar | rejeitado
    pronto_para_arquivar -> arquivando
    arquivando -> arquivado | falha_de_arquivamento
    falha_de_arquivamento -> arquivando            (retry)
    falha -> aguardando_extracao                   (retry)
"""

from __future__ import annotations

from django.db import models


class TriageStatus(models.TextChoices):
    RECEIVED = "recebido", "Recebido"
    QUARANTINED = "em_quarentena", "Em quarentena"
    REJECTED = "rejeitado", "Rejeitado"
    AWAITING_EXTRACTION = "aguardando_extracao", "Aguardando extração"
    EXTRACTING = "em_extracao", "Em extração"
    AWAITING_REVIEW = "aguardando_revisao", "Aguardando revisão"
    READY_TO_ARCHIVE = "pronto_para_arquivar", "Pronto para arquivar"
    FAILED = "falha", "Falha"
    ARCHIVING = "arquivando", "Arquivando"
    ARCHIVED = "arquivado", "Arquivado"
    ARCHIVE_FAILED = "falha_de_arquivamento", "Falha ao arquivar"


TERMINAL_STATUSES = frozenset({TriageStatus.REJECTED, TriageStatus.ARCHIVED})


class InvalidTransition(ValueError):
    """A TriageItem was asked to move through an edge the state machine forbids."""


_ALLOWED_TRANSITIONS: dict[TriageStatus, frozenset[TriageStatus]] = {
    TriageStatus.RECEIVED: frozenset({TriageStatus.QUARANTINED}),
    TriageStatus.QUARANTINED: frozenset({TriageStatus.REJECTED, TriageStatus.AWAITING_EXTRACTION}),
    TriageStatus.AWAITING_EXTRACTION: frozenset({TriageStatus.EXTRACTING}),
    TriageStatus.EXTRACTING: frozenset(
        {TriageStatus.AWAITING_REVIEW, TriageStatus.READY_TO_ARCHIVE, TriageStatus.FAILED}
    ),
    TriageStatus.AWAITING_REVIEW: frozenset({TriageStatus.READY_TO_ARCHIVE, TriageStatus.REJECTED}),
    TriageStatus.READY_TO_ARCHIVE: frozenset({TriageStatus.ARCHIVING}),
    TriageStatus.ARCHIVING: frozenset({TriageStatus.ARCHIVED, TriageStatus.ARCHIVE_FAILED}),
    TriageStatus.ARCHIVE_FAILED: frozenset({TriageStatus.ARCHIVING}),
    TriageStatus.FAILED: frozenset({TriageStatus.AWAITING_EXTRACTION}),
    TriageStatus.REJECTED: frozenset(),
    TriageStatus.ARCHIVED: frozenset(),
}


def ensure_transition_allowed(current: str, target: str) -> None:
    """Raise ``InvalidTransition`` unless ``current -> target`` is a real edge."""

    try:
        current_status = TriageStatus(current)
    except ValueError as exc:
        raise InvalidTransition(f"Estado atual desconhecido: {current!r}.") from exc
    try:
        target_status = TriageStatus(target)
    except ValueError as exc:
        raise InvalidTransition(f"Estado de destino desconhecido: {target!r}.") from exc
    allowed = _ALLOWED_TRANSITIONS.get(current_status, frozenset())
    if target_status not in allowed:
        raise InvalidTransition(
            f"Transição inválida: {current_status.label} -> {target_status.label}."
        )
