"""D-397 item 8: what really happened to each bank movement, in the client's words (direct use).

Offices outside direct use keep the existing review-oriented screens; nothing here writes.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any

from apps.hub.models import (
    JournalEntry,
    MovementReconciliation,
    NormalizedMovement,
    ReconciliationRule,
)

OUTCOMES: dict[str, tuple[str, str]] = {
    "confirmed": ("Conferido com o Razão", "is-active"),
    "exported": ("Enviado ao Domínio", "is-active"),
    "posted": ("Lançado pela CICA", "is-active"),
    "similar": ("Parecido com o Razão · não lançado", "is-muted"),
    "no_rule": ("Sem regra · não lançado", "is-muted"),
    "no_razao": ("Aguardando o Razão do mês", "is-muted"),
    "statement_only": ("Extrato sem Razão", "is-muted"),
    "ignored": ("Ignorado", "is-muted"),
}
HELP = {
    "confirmed": "Já está no Razão do Domínio.",
    "exported": "Lançado pela CICA e incluído num arquivo para o Domínio.",
    "posted": "Lançado pela CICA; vai no próximo arquivo para o Domínio.",
    "similar": "Há um registro parecido no Razão (mesmo valor, data próxima); não foi lançado.",
    "no_rule": "Nenhuma regra reconhece este histórico ainda; nada foi lançado.",
    "no_razao": "O Razão deste mês ainda não chegou; a CICA lança depois que ele chegar.",
    "statement_only": "Conta sem conta contábil no Domínio: só consulta do extrato.",
    "ignored": "Marcado para não lançar.",
}


def movement_outcomes(movements: Iterable[NormalizedMovement]) -> dict[str, dict[str, str]]:
    from apps.hub.direct_use import _ledger_months
    from apps.hub.double_booking import is_similar, ledger_index

    movements = [m for m in movements if m is not None]
    if not movements:
        return {}
    ids = [m.pk for m in movements]
    confirmed = set(
        MovementReconciliation.objects.filter(
            movement_id__in=ids, state=MovementReconciliation.State.CONFIRMED
        ).values_list("movement_id", flat=True)
    )
    entry_state: dict[Any, str] = {}
    rank: dict[str, int] = {JournalEntry.State.EXPORTED: 3, JournalEntry.State.APPROVED: 2}
    for movement_id, state in (
        JournalEntry.objects.filter(movement_id__in=ids)
        .exclude(state=JournalEntry.State.INVALID)
        .exclude(purpose="source_ledger")
        .values_list("movement_id", "state")
    ):
        if rank.get(state, 0) > rank.get(entry_state.get(movement_id, ""), 0):
            entry_state[movement_id] = state
    accounts: dict[Any, tuple[set[tuple[int, int]], Any]] = {}
    result: dict[str, dict[str, str]] = {}
    for movement in movements:
        account = movement.financial_account
        if movement.review_state == NormalizedMovement.ReviewState.IGNORED:
            key = "ignored"
        elif movement.pk in confirmed:
            key = "confirmed"
        elif entry_state.get(movement.pk) == JournalEntry.State.EXPORTED:
            key = "exported"
        elif entry_state.get(movement.pk) == JournalEntry.State.APPROVED:
            key = "posted"
        elif account is None or not account.ledger_code:
            key = "statement_only"
        else:
            if account.pk not in accounts:
                accounts[account.pk] = (_ledger_months(account), ledger_index(account))
            months, index = accounts[account.pk]
            occurred = movement.occurred_on
            if occurred is None or (occurred.year, occurred.month) not in months:
                key = "no_razao"
            elif is_similar(index, movement):
                key = "similar"
            else:
                key = "no_rule"
        label, css = OUTCOMES[key]
        result[str(movement.pk)] = {"key": key, "label": label, "css": css, "help": HELP[key]}
    return result


def outcome_counts(outcomes: dict[str, dict[str, str]]) -> list[dict[str, Any]]:
    counts = Counter(item["key"] for item in outcomes.values())
    return [
        {"key": key, "label": OUTCOMES[key][0], "count": counts[key], "help": HELP[key]}
        for key in OUTCOMES
        if counts[key]
    ]


def rule_label(rule: ReconciliationRule | None) -> str:
    """Pattern instead of the technical rule name ("DE-PARA Razão 0d00…")."""
    from apps.hub.depara_ai_auto import RULE_PREFIX as AI_PREFIX
    from apps.hub.depara_ledger import LEVEL_LABELS, RULE_PREFIX, suggestion_evidence

    if rule is None:
        return ""
    if not rule.name.startswith((RULE_PREFIX, AI_PREFIX)):
        return rule.name
    evidence = suggestion_evidence(rule) or {}
    if rule.name.startswith(AI_PREFIX):
        from apps.audit.models import AuditEvent
        from apps.hub.depara_ai_auto import SUGGESTED_ACTION

        event = (
            AuditEvent.objects.filter(action=SUGGESTED_ACTION, target_id=str(rule.pk))
            .order_by("-occurred_at")
            .first()
        )
        label = (event.metadata or {}).get("label", "") if event else ""
        return f"Regra da IA: “{label}”" if label else "Regra da IA"
    label = evidence.get("label", "")
    level = LEVEL_LABELS.get(evidence.get("level", ""), "Padrão")
    return f"Regra pelo Razão: {level.lower()} “{label}”" if label else "Regra pelo Razão"
