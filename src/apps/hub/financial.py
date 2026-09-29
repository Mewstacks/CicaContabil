"""Persisted, explainable DRE and cash inputs without ERP-specific assumptions."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.cash_projection import CashMovement, CashProjection, CashView, project_cash
from apps.hub.dre import DreMapping, DreResult, calculate_dre
from apps.hub.models import (
    AccountingBalanceLine,
    AccountingBalanceSnapshot,
    CashScenario,
    DreMappingSet,
)


@dataclass(frozen=True)
class AccountingBalanceInput:
    account_code: str
    balance_cents: int
    account_name: str = ""


@transaction.atomic
def record_accounting_balance_snapshot(
    *,
    snapshot: AccountingBalanceSnapshot,
    lines: Iterable[AccountingBalanceInput],
    actor: User,
    request: object,
) -> tuple[AccountingBalanceSnapshot, bool]:
    """Store one source observation idempotently without placing balances in audit logs."""

    inputs = tuple(lines)
    codes = [item.account_code.strip() for item in inputs]
    if not snapshot.organization_id or not snapshot.company_id:
        raise ValueError("A fotografia contábil exige escritório e empresa.")
    if not codes or any(not code for code in codes):
        raise ValueError("A fotografia contábil exige ao menos uma conta identificada.")
    if len(codes) != len(set(codes)):
        raise ValueError("Uma fotografia contábil não pode repetir a mesma conta.")
    existing = AccountingBalanceSnapshot.objects.filter(
        organization=snapshot.organization,
        company=snapshot.company,
        competence=snapshot.competence,
        source_kind=snapshot.source_kind,
        source_reference=snapshot.source_reference,
    ).first()
    if existing is not None:
        return existing, False
    snapshot.created_by = actor
    snapshot.full_clean()
    snapshot.save()
    AccountingBalanceLine.objects.bulk_create(
        [
            AccountingBalanceLine(
                snapshot=snapshot,
                account_code=code,
                account_name=item.account_name.strip(),
                balance_cents=item.balance_cents,
            )
            for item, code in zip(inputs, codes, strict=True)
        ]
    )
    record_event(
        action="hub.accounting_balance_snapshot.recorded",
        actor=actor,
        organization=snapshot.organization,
        target=snapshot,
        request=request,
        metadata={
            "company_id": str(snapshot.company_id),
            "competence": snapshot.competence.isoformat(),
            "source_kind": snapshot.source_kind,
            "line_count": len(inputs),
        },
    )
    return snapshot, True


def calculate_snapshot_dre(
    *, snapshot: AccountingBalanceSnapshot, mapping_set: DreMappingSet
) -> DreResult:
    """Calculate only with a mapping belonging to the snapshot's office."""

    if snapshot.organization_id != mapping_set.organization_id:
        raise ValueError("O mapeamento DRE precisa pertencer ao mesmo escritório.")
    balances = {
        line.account_code: line.balance_cents
        for line in snapshot.lines.all().only("account_code", "balance_cents")
    }
    mappings = [
        DreMapping(account_code=item.account_code, group=item.group, sign=item.sign)
        for item in mapping_set.mappings.all().only("account_code", "group", "sign")
    ]
    return calculate_dre(balances_cents=balances, mappings=mappings)


def project_cash_scenario(*, scenario: CashScenario) -> CashProjection:
    """Translate persistent scenario facts to the deterministic calculator."""

    movements = [
        CashMovement(
            occurred_on=item.occurred_on,
            description=item.description,
            gross_receipt_cents=item.gross_receipt_cents,
            payment_cents=item.payment_cents,
            retention_cents=item.retention_cents,
            provision_cents=item.provision_cents,
            retention_already_provisioned=item.retention_already_provisioned,
        )
        for item in scenario.movements.all()
    ]
    return project_cash(
        view=CashView(scenario.view),
        opening_balance_cents=scenario.opening_balance_cents,
        movements=movements,
    )
