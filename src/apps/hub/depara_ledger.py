"""D-391: DE-PARA suggestions learned from the contra accounts the office booked in the Razão.

Truth comes only from confirmed bank-statement ↔ Razão reconciliations whose Domínio journal
has exactly one contra line. A suggestion needs repeated, unanimous evidence and must not match
any other historical movement of the account with a different contra account. Suggestions are
created as DRAFT rules; activation stays a human decision (depara_rule_activation).
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from django.db import transaction

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    MovementReconciliation,
    NormalizedMovement,
    ReconciliationRule,
)
from apps.hub.reconciliation_bridge import independent_record
from apps.hub.reconciliation_service import _matches_condition

logger = logging.getLogger(__name__)
SUGGESTED_ACTION = "hub.reconciliation.depara_ledger_suggested"
RULE_PREFIX = "DE-PARA Razão"
LEVELS = (
    # (name, minimum support)
    ("exato", 2),
    ("palavras", 2),
    ("inicio", 5),
)
LEVEL_LABELS = {
    "exato": "Histórico igual a",
    "palavras": "Histórico com as palavras",
    "inicio": "Histórico começa com",
}


@dataclass(frozen=True)
class LedgerExample:
    movement: NormalizedMovement
    debit: str
    credit: str
    history: str
    month: str

    @property
    def action(self) -> tuple[str, str]:
        return self.debit, self.credit


@dataclass
class Suggestion:
    level: str
    label: str
    direction: str
    conditions: list[dict[str, Any]]
    debit: str
    credit: str
    history: str
    examples: list[LedgerExample] = field(default_factory=list)

    @property
    def support(self) -> int:
        return len(self.examples)

    @property
    def months(self) -> list[str]:
        return sorted({example.month for example in self.examples})

    def fingerprint(self) -> str:
        payload = {"conditions": self.conditions, "debit": self.debit, "credit": self.credit}
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(encoded.encode()).hexdigest()


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(char for char in folded if not unicodedata.combining(char)).upper()
    return " ".join(re.sub(r"[^A-Z0-9 ]", " ", ascii_text).split())


def _raw_words(text: str) -> list[str]:
    return [word for word in re.split(r"[\W_]+", text or "") if word and not re.search(r"\d", word)]


def _words(text: str) -> list[str]:
    return [_plain(word) for word in _raw_words(text) if _plain(word)]


def ledger_examples(
    account: FinancialAccount,
) -> tuple[list[LedgerExample], list[NormalizedMovement]]:
    """Single-contra truth examples, plus every other reconciled movement (for false positives)."""
    by_movement: dict[Any, list[MovementReconciliation]] = defaultdict(list)
    for row in MovementReconciliation.objects.filter(
        organization_id=account.organization_id,
        state=MovementReconciliation.State.CONFIRMED,
        movement__financial_account=account,
        movement__company_id=account.company_id,
        movement__source_file__origin="bank_statement",
    ).select_related("movement", "movement__financial_account", "entry"):
        by_movement[row.movement_id].append(row)
    examples: list[LedgerExample] = []
    others: list[NormalizedMovement] = []
    for rows in by_movement.values():
        movement = rows[0].movement
        if len(rows) != 1 or rows[0].amount_cents != abs(movement.amount_cents):
            others.append(movement)
            continue
        entry = rows[0].entry
        record = independent_record(entry)
        lines = list(entry.lines.all()) if record is not None else []
        bank = [line for line in lines if line.pk == record.bank_line_id] if record else []
        contra = [line for line in lines if record is None or line.pk != record.bank_line_id]
        if len(bank) != 1 or len(contra) != 1 or not movement.occurred_on:
            others.append(movement)
            continue
        sides = {bank[0].side: bank[0].account_code, contra[0].side: contra[0].account_code}
        debit, credit = sides.get("debit", ""), sides.get("credit", "")
        if not debit or not credit or debit == credit:
            others.append(movement)
            continue
        examples.append(
            LedgerExample(
                movement=movement,
                debit=str(debit),
                credit=str(credit),
                history=(entry.history or "").strip(),
                month=movement.occurred_on.strftime("%Y-%m"),
            )
        )
    return examples, others


def _description_condition(
    level: str, group: list[LedgerExample]
) -> tuple[dict[str, Any], str] | None:
    descriptions = [example.movement.description or "" for example in group]
    if level == "exato":
        if len({text.casefold().strip() for text in descriptions}) != 1:
            return None
        value = descriptions[0].strip()
        return {"field": "description", "operator": "equals", "value": value}, value
    words = _raw_words(descriptions[0])
    if level == "inicio":
        words = words[:2]
    if not words or (level == "inicio" and len(words) < 2):
        return None
    if level == "inicio":
        pattern = r"^\W*" + r"\W+".join(re.escape(word) for word in words) + r"\b"
    else:
        pattern = r"\b" + r"\b.*\b".join(re.escape(word) for word in words) + r"\b"
    if len(pattern) > 160:
        return None
    label = " ".join(_plain(word) for word in words)
    return {"field": "description", "operator": "regex", "value": pattern}, label


def _group_key(level: str, example: LedgerExample) -> str:
    text = example.movement.description or ""
    if level == "exato":
        return text.casefold().strip()
    words = _words(text)
    return " ".join(words[:2] if level == "inicio" else words)


def _matches(conditions: list[dict[str, Any]], movement: NormalizedMovement) -> bool:
    return all(_matches_condition(condition, movement) for condition in conditions)


def _history(group: list[LedgerExample], label: str) -> str:
    histories = Counter(example.history for example in group if example.history)
    if histories:
        text, count = histories.most_common(1)[0]
        if count * 2 >= len(group):
            return text[:500]
    return label[:500]


def propose(account: FinancialAccount) -> dict[str, Any]:
    """Validated suggestions for one bank account; read only."""
    examples, others = ledger_examples(account)
    candidates: list[Suggestion] = []
    rejected: Counter[str] = Counter()
    for level, minimum in LEVELS:
        groups: dict[tuple[str, str], list[LedgerExample]] = defaultdict(list)
        for example in examples:
            key = _group_key(level, example)
            if key:
                groups[(key, example.movement.direction)].append(example)
        for (_key, direction), group in groups.items():
            if len(group) < minimum:
                continue
            actions = {example.action for example in group}
            if len(actions) != 1:
                rejected["divergente"] += 1
                continue
            built = _description_condition(level, group)
            if built is None:
                rejected["padrao_invalido"] += 1
                continue
            condition, label = built
            conditions = [
                condition,
                {"field": "direction", "operator": "equals", "value": direction},
                {
                    "field": "financial_account",
                    "operator": "equals",
                    "value": account.account_reference,
                },
            ]
            if not all(_matches(conditions, example.movement) for example in group):
                rejected["padrao_invalido"] += 1
                continue
            action = next(iter(actions))
            false_positive = any(
                _matches(conditions, example.movement) and example.action != action
                for example in examples
            ) or any(_matches(conditions, movement) for movement in others)
            if false_positive:
                rejected["casaria_outra_conta"] += 1
                continue
            covered = [example for example in examples if _matches(conditions, example.movement)]
            candidates.append(
                Suggestion(
                    level=level,
                    label=label,
                    direction=direction,
                    conditions=conditions,
                    debit=action[0],
                    credit=action[1],
                    history=_history(group, label),
                    examples=covered,
                )
            )
    # Keep the broadest validated rule; drop a narrower one fully covered with the same action.
    order = {name: index for index, (name, _minimum) in enumerate(LEVELS)}
    candidates.sort(key=lambda item: (-order[item.level], -item.support))
    kept: list[Suggestion] = []
    for candidate in candidates:
        ids = {example.movement.pk for example in candidate.examples}
        if any(
            (k.debit, k.credit) == (candidate.debit, candidate.credit)
            and ids <= {example.movement.pk for example in k.examples}
            for k in kept
        ):
            continue
        kept.append(candidate)
    covered_ids = {example.movement.pk for suggestion in kept for example in suggestion.examples}
    return {
        "examples": len(examples),
        "excluded_compound_or_partial": len(others),
        "suggestions": kept,
        "covered": len(covered_ids),
        "rejected": dict(rejected),
    }


def _rule_name(suggestion: Suggestion) -> str:
    return f"{RULE_PREFIX} {suggestion.fingerprint()[:24]}"


@transaction.atomic
def create_drafts(account: FinancialAccount) -> dict[str, Any]:
    """Create one DRAFT rule per new validated suggestion (technical actor, no activation)."""
    ClientCompany.objects.select_for_update().get(
        pk=account.company_id, organization_id=account.organization_id
    )
    result = propose(account)
    created, existing = [], 0
    for suggestion in result["suggestions"]:
        name = _rule_name(suggestion)
        if ReconciliationRule.objects.filter(
            organization_id=account.organization_id, company_id=account.company_id, name=name
        ).exists():
            existing += 1
            continue
        rule = ReconciliationRule.objects.create(
            organization_id=account.organization_id,
            company_id=account.company_id,
            name=name,
            priority=100,
            state=ReconciliationRule.State.DRAFT,
            all_conditions=suggestion.conditions,
            any_conditions=[],
            actions={
                "debit_account_code": suggestion.debit,
                "credit_account_code": suggestion.credit,
                "accounting_history": suggestion.history,
                "require_review": True,
            },
        )
        record_event(
            action=SUGGESTED_ACTION,
            actor=None,
            organization=account.organization,
            target=rule,
            metadata={
                "decision": "D-391",
                "financial_account_id": str(account.pk),
                "level": suggestion.level,
                "label": suggestion.label,
                "direction": suggestion.direction,
                "support": suggestion.support,
                "months": suggestion.months,
                "movement_ids": [str(e.movement.pk) for e in suggestion.examples][:200],
                "in_sample_false_positives": 0,
                "source": "razao_confirmado",
            },
        )
        created.append(rule)
    valid_names = {_rule_name(suggestion) for suggestion in result["suggestions"]}
    retired = 0
    for rule, _evidence in ledger_rules(account):
        if rule.state != ReconciliationRule.State.DRAFT or rule.name in valid_names:
            continue
        rule.state = ReconciliationRule.State.DISABLED
        rule.save(update_fields=["state", "updated_at"])
        record_event(
            action="hub.reconciliation.rule.state_changed",
            actor=None,
            organization=account.organization,
            target=rule,
            metadata={"state": "disabled", "reason": "sem_evidencia_atual", "decision": "D-392"},
        )
        retired += 1
    return {**result, "created": len(created), "existing": existing, "retired": retired}


def refresh_ledger_suggestions(account_id: Any) -> None:
    """D-392: after confirmations commit, refresh this account's suggestions; never raises."""

    def run() -> None:
        try:
            account = FinancialAccount.objects.select_related("company", "organization").get(
                pk=account_id, active=True
            )
            create_drafts(account)
        except Exception:
            logger.exception("DE-PARA pelo Razão não atualizado para a conta %s", account_id)

    if account_id:
        transaction.on_commit(run)


def suggestion_evidence(rule: ReconciliationRule) -> dict[str, Any] | None:
    event = (
        AuditEvent.objects.filter(
            organization_id=rule.organization_id,
            action=SUGGESTED_ACTION,
            target_type="hub.reconciliationrule",
            target_id=str(rule.pk),
        )
        .order_by("-occurred_at")
        .first()
    )
    return event.metadata if event else None


def evaluate(account: FinancialAccount, *, month: str) -> dict[str, Any]:
    """Out-of-sample check: Razão-booked contra accounts of ``month`` vs current DE-PARA rules."""
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", month):
        raise ValueError("Informe a competência no formato AAAA-MM.")
    rules = list(
        ReconciliationRule.objects.filter(
            organization_id=account.organization_id,
            company_id=account.company_id,
            name__startswith=RULE_PREFIX,
            state__in=[ReconciliationRule.State.DRAFT, ReconciliationRule.State.ACTIVE],
        )
    )
    learned_from = {
        str(rule.pk): set((suggestion_evidence(rule) or {}).get("months", [])) for rule in rules
    }
    examples, _others = ledger_examples(account)
    correct = wrong = uncovered = conflicts = 0
    for example in (e for e in examples if e.month == month):
        hits = {
            (rule.actions.get("debit_account_code"), rule.actions.get("credit_account_code"))
            for rule in rules
            if month not in learned_from[str(rule.pk)]
            and _matches(rule.all_conditions, example.movement)
        }
        if not hits:
            uncovered += 1
        elif len(hits) > 1:
            conflicts += 1
        elif next(iter(hits)) == example.action:
            correct += 1
        else:
            wrong += 1
    predicted = correct + wrong
    return {
        "decision": "D-391",
        "month": month,
        "rules_evaluated": len(rules),
        "booked_movements": correct + wrong + uncovered + conflicts,
        "correct": correct,
        "wrong": wrong,
        "conflicts": conflicts,
        "uncovered": uncovered,
        "precision_percent": round(100 * correct / predicted, 4) if predicted else None,
        "note": "Regras aprendidas na própria competência avaliada são ignoradas.",
    }


def ledger_rules(account: FinancialAccount) -> list[tuple[ReconciliationRule, dict[str, Any]]]:
    """Razão-derived rules of this bank account with their recorded evidence."""
    rows = []
    for rule in ReconciliationRule.objects.filter(
        organization_id=account.organization_id,
        company_id=account.company_id,
        name__startswith=RULE_PREFIX,
    ):
        evidence = suggestion_evidence(rule)
        if evidence and evidence.get("financial_account_id") == str(account.pk):
            rows.append((rule, evidence))
    rows.sort(key=lambda item: (-int(item[1].get("support", 0)), item[0].name))
    return rows


@transaction.atomic
def discard_suggestion(*, rule: ReconciliationRule, actor: Any, request: Any = None) -> None:
    """A draft the reviewer rejects becomes disabled; it can still be activated later."""
    from apps.hub.title_persistence import authorize_title_account

    ClientCompany.objects.select_for_update().get(
        pk=rule.company_id, organization_id=rule.organization_id
    )
    current = ReconciliationRule.objects.select_for_update().get(pk=rule.pk)
    evidence = suggestion_evidence(current) or {}
    account = FinancialAccount.objects.select_related("company").get(
        pk=str(evidence.get("financial_account_id") or ""),
        organization_id=current.organization_id,
    )
    authorize_title_account(account, actor)
    if current.state != ReconciliationRule.State.DRAFT:
        raise ValueError("A sugestão mudou. Reabra a lista antes de continuar.")
    current.state = ReconciliationRule.State.DISABLED
    current.save(update_fields=["state", "updated_at"])
    record_event(
        action="hub.reconciliation.rule.state_changed",
        actor=actor,
        organization=account.organization,
        target=current,
        request=request,
        metadata={"state": "disabled", "reason": "sugestao_descartada", "decision": "D-391"},
    )
