"""D-393: offices in direct use see and use the data without human review steps.

Only offices listed by UUID in ``CICA_DIRECT_USE_ORGANIZATION_IDS`` (never demos or inactive
offices) get this behaviour:

* Razão-derived DE-PARA suggestions (D-391/D-392) are activated without mandatory review;
* bank movements classified by an active rule, with no Razão record that could be the same
  booking, become approved journal entries once that month's Razão has arrived;
* the Domínio export file can be generated without a homologation record.

Everything that prevents double booking stays: confirmed or similar Razão records are never
posted, an already booked Razão is never exported, and nothing is exported twice.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any

from django.conf import settings
from django.db import transaction

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    IndependentLedgerRecord,
    JournalEntry,
    NormalizedMovement,
    ReconciliationRule,
)
from apps.organizations.models import Organization

logger = logging.getLogger(__name__)
DECISION = "D-393"
STATE_ACTION = "hub.reconciliation.rule.state_changed"
POSTED_ACTION = "hub.reconciliation.direct_use_posted"


def direct_use_enabled(organization: Organization | None) -> bool:
    """An explicit office UUID is required; names, slugs and demos never opt in."""
    return bool(
        organization is not None
        and organization.is_active
        and not organization.is_demo
        and str(organization.pk) in getattr(settings, "CICA_DIRECT_USE_ORGANIZATION_IDS", [])
    )


def _activated_by_routine(rule: ReconciliationRule) -> bool:
    """True when the last state change of this rule was this routine, not a person."""
    event = (
        AuditEvent.objects.filter(action=STATE_ACTION, target_id=str(rule.pk))
        .order_by("-occurred_at")
        .first()
    )
    return bool(
        event is not None
        and event.actor_id is None
        and (event.metadata or {}).get("decision") == DECISION
    )


def routine_owns(rule: ReconciliationRule) -> bool:
    """Rules this routine may retire: drafts, or rules it activated itself."""
    if rule.state == ReconciliationRule.State.DRAFT:
        return True
    return rule.state == ReconciliationRule.State.ACTIVE and _activated_by_routine(rule)


@transaction.atomic
def activate_ledger_rules(account: FinancialAccount) -> dict[str, int]:
    """Activate every valid Razão-derived draft of this account, without mandatory review."""
    from apps.hub.depara_ledger import ledger_rules
    from apps.hub.depara_rule_activation import _actions, _conditions, _conflicts

    ClientCompany.objects.select_for_update().get(
        pk=account.company_id, organization_id=account.organization_id
    )
    activated = kept = 0
    for rule, _evidence in ledger_rules(account):
        if rule.state != ReconciliationRule.State.DRAFT:
            continue
        current = ReconciliationRule.objects.select_for_update().get(pk=rule.pk)
        actions = {**current.actions, "require_review": False}
        actions.pop("review", None)
        current.actions = actions
        try:
            _conditions(current)
            _actions(current)
            _conflicts(current)
        except ValueError as exc:
            kept += 1
            logger.info("Regra %s continua em rascunho: %s", current.pk, exc)
            continue
        current.state = ReconciliationRule.State.ACTIVE
        current.save(update_fields=["actions", "state", "updated_at"])
        record_event(
            action=STATE_ACTION,
            actor=None,
            organization=account.organization,
            target=current,
            metadata={"state": "active", "decision": DECISION, "automatic": True},
        )
        activated += 1
    return {"activated": activated, "kept_draft": kept}


def _ledger_months(account: FinancialAccount) -> set[tuple[int, int]]:
    """Months whose Razão already arrived for this bank account."""
    from apps.intelligence.models import NativeLedgerCollection

    months: set[tuple[int, int]] = set()
    for scope in NativeLedgerCollection.objects.filter(
        financial_account=account, state=NativeLedgerCollection.State.IMPORTED
    ).values_list("scope", flat=True):
        try:
            start = date.fromisoformat(str((scope or {}).get("period_start")))
        except (TypeError, ValueError):
            continue
        months.add((start.year, start.month))
    for occurred in IndependentLedgerRecord.objects.filter(
        organization_id=account.organization_id, financial_account=account
    ).values_list("accounting_entry__occurred_on", flat=True):
        if occurred:
            months.add((occurred.year, occurred.month))
    return months


def _ledger_keys(account: FinancialAccount) -> set[tuple[date, str, int]]:
    """Date/direction/amount of every Razão record of the account (used or not)."""
    keys = set()
    for occurred, direction, amount in IndependentLedgerRecord.objects.filter(
        organization_id=account.organization_id, financial_account=account
    ).values_list(
        "accounting_entry__occurred_on",
        "accounting_entry__direction",
        "accounting_entry__amount_cents",
    ):
        keys.add((occurred, direction, abs(int(amount or 0))))
    return keys


def post_unbooked(account: FinancialAccount) -> dict[str, int]:
    """Generate and approve entries for rule-classified movements absent from the Razão."""
    from apps.hub.reconciliation_bridge import movement_has_ledger_match
    from apps.hub.reconciliation_service import (
        ReconciliationError,
        apply_rules,
        approve_journal_entry,
        create_journal_entry_from_movement,
    )

    months = _ledger_months(account)
    if not months:
        return {"posted": 0, "skipped_similar": 0, "failed": 0}
    keys = _ledger_keys(account)
    posted = similar = failed = 0
    candidates = (
        NormalizedMovement.objects.filter(
            organization_id=account.organization_id,
            company_id=account.company_id,
            financial_account=account,
            source_file__origin="bank_statement",
            occurred_on__isnull=False,
        )
        .exclude(review_state=NormalizedMovement.ReviewState.IGNORED)
        .exclude(classification_source=NormalizedMovement.ClassificationSource.MANUAL)
        .exclude(reconciliations__state="confirmed")
        .exclude(amount_cents=0)
        .select_related("source_file", "financial_account")
        .order_by("occurred_on", "id")
    )
    for movement in candidates.iterator():
        occurred = movement.occurred_on
        if occurred is None or (occurred.year, occurred.month) not in months:
            continue
        if movement.journal_entries.exclude(state=JournalEntry.State.INVALID).exists():
            continue
        if (occurred, movement.direction, abs(movement.amount_cents)) in keys:
            similar += 1
            continue
        try:
            with transaction.atomic():
                if movement_has_ledger_match(movement):
                    continue
                movement = apply_rules(movement)
                if (
                    movement.classification_source
                    != NormalizedMovement.ClassificationSource.RULE
                    or movement.review_state != NormalizedMovement.ReviewState.READY
                    or not movement.debit_account_code
                    or not movement.credit_account_code
                ):
                    continue
                entry = create_journal_entry_from_movement(movement=movement)
                entry = approve_journal_entry(entry=entry)
                if entry.state != JournalEntry.State.APPROVED:
                    failed += 1
                    continue
                record_event(
                    action=POSTED_ACTION,
                    actor=None,
                    organization=account.organization,
                    target=entry,
                    metadata={
                        "decision": DECISION,
                        "movement_id": str(movement.pk),
                        "rule_id": str(movement.applied_rule_id or ""),
                    },
                )
                posted += 1
        except ReconciliationError:
            failed += 1
        except Exception:
            failed += 1
            logger.exception("Lançamento D-393 não gerado para o movimento %s", movement.pk)
    return {"posted": posted, "skipped_similar": similar, "failed": failed}


def run_for_account(account: FinancialAccount) -> dict[str, int]:
    """Activate this account's Razão rules and post what the Razão does not have."""
    if not direct_use_enabled(account.organization):
        return {}
    return {**activate_ledger_rules(account), **post_unbooked(account)}


def run_for_account_safely(account_id: Any) -> None:
    """Never raises: a failure is logged and the triggering operation stays committed."""
    try:
        account = FinancialAccount.objects.select_related("company", "organization").get(
            pk=account_id, active=True
        )
        run_for_account(account)
    except Exception:
        logger.exception("Uso direto D-393 não atualizado para a conta %s", account_id)


def run_for_organization(organization: Organization) -> list[dict[str, Any]]:
    results = []
    for account in FinancialAccount.objects.filter(
        organization=organization, active=True
    ).select_related("company", "organization"):
        try:
            results.append({"account": str(account.pk), **run_for_account(account)})
        except Exception as exc:  # one account never stops the others
            logger.exception("Uso direto D-393 falhou na conta %s", account.pk)
            results.append({"account": str(account.pk), "error": str(exc)[:200]})
    return results
