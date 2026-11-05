"""One allocation for both views of a proven independent journal (D-305)."""

from __future__ import annotations

from typing import Any

from apps.hub.models import (
    BankTransaction,
    IndependentLedgerRecord,
    JournalEntry,
    MovementReconciliation,
    NormalizedMovement,
    ReconciliationMatch,
    ReconciliationSourceFile,
)


def independent_record(entry: JournalEntry) -> IndependentLedgerRecord | None:
    try:
        return entry.independent_source
    except IndependentLedgerRecord.DoesNotExist:
        return None


def movement_has_ledger_match(movement: NormalizedMovement) -> bool:
    """Read both histories without creating a legacy projection during validation."""
    if movement.reconciliations.filter(state="confirmed").exists():
        return True
    fitid = movement.source_reference.get("fitid")
    return bool(
        movement.source_file.kind == "ofx"
        and fitid
        and ReconciliationMatch.objects.filter(
            organization_id=movement.organization_id,
            transaction__statement__company_id=movement.company_id,
            transaction__statement__content_hash=movement.source_file.content_hash,
            transaction__external_id=fitid,
            status="matched",
        ).exists()
    )


def compatible_record(movement: NormalizedMovement, record: IndependentLedgerRecord) -> bool:
    source = record.accounting_entry
    account = movement.financial_account
    reference = (
        account.account_reference
        if account is not None
        else movement.source_reference.get("account", "")
    )
    return bool(
        movement.source_file.origin == ReconciliationSourceFile.Origin.BANK_STATEMENT
        and record.organization_id == movement.organization_id
        and source.organization_id == movement.organization_id
        and source.data_source.organization_id == movement.organization_id
        and source.company_id == movement.company_id
        and record.source_file.company_id == movement.company_id
        and record.source_file.origin == ReconciliationSourceFile.Origin.ACCOUNTING
        and record.source_file_id != movement.source_file_id
        and record.entry.movement_id is None
        and reference
        and source.account_reference == reference
        and record.financial_account.account_reference == reference
        and record.financial_account.company_id == movement.company_id
        and record.bank_line.entry_id == record.entry_id
        and record.bank_line.account_code == record.financial_account.ledger_code
        and record.bank_line.amount_cents == source.amount_cents
        and source.direction == movement.direction
        and (movement.amount_cents > 0) == (source.direction == "inflow")
        and source.occurred_on == movement.occurred_on == record.entry.occurred_on
    )


def movement_for_legacy(match: ReconciliationMatch) -> NormalizedMovement | None:
    item = match.transaction
    return NormalizedMovement.objects.filter(
        organization_id=match.organization_id,
        company_id=item.statement.company_id,
        source_file__kind="ofx",
        source_file__origin="bank_statement",
        source_file__content_hash=item.statement.content_hash,
        source_key=f"ofx:{item.external_id}",
    ).first()


def legacy_for_movement(movement: NormalizedMovement) -> ReconciliationMatch | None:
    if movement.source_file.kind != "ofx":
        return None
    fitid = movement.source_reference.get("fitid")
    if not fitid:
        return None
    bank = BankTransaction.objects.filter(
        organization_id=movement.organization_id,
        statement__company_id=movement.company_id,
        statement__content_hash=movement.source_file.content_hash,
        external_id=fitid,
    ).first()
    if bank is None:
        return None
    match, _ = ReconciliationMatch.objects.get_or_create(
        organization_id=movement.organization_id,
        transaction=bank,
    )
    return match


def project_confirmed_allocation(movement: NormalizedMovement) -> None:
    """Caller owns the company lock. Partial/compound allocations stay in the new view."""
    match = legacy_for_movement(movement)
    if match is None:
        return
    allocations = list(movement.reconciliations.filter(state="confirmed").select_related("entry"))
    complete = len(allocations) == 1 and allocations[0].amount_cents == abs(movement.amount_cents)
    record = independent_record(allocations[0].entry) if complete else None
    if match.status == "matched" and (
        record is None or match.accounting_entry_id != record.accounting_entry_id
    ):
        # Never overwrite a human decision from the older, unbridged history.
        from apps.hub.reconciliation_service import ReconciliationError

        raise ReconciliationError("A fila OFX já possui outra confirmação; revise o histórico.")
    if record is None:
        return
    allocation = allocations[0]
    _update_match(
        match,
        accounting_entry=record.accounting_entry,
        status="matched",
        is_manual=True,
        resolved_by=allocation.confirmed_by,
        resolved_at=allocation.confirmed_at,
    )


def clear_legacy_projection(reconciliation: MovementReconciliation) -> None:
    record = independent_record(reconciliation.entry)
    if record is None:
        return
    match = legacy_for_movement(reconciliation.movement)
    if match and match.accounting_entry_id == record.accounting_entry_id:
        _update_match(
            match,
            accounting_entry=None,
            status="ambiguous",
            is_manual=False,
            resolved_by=None,
            resolved_at=None,
        )


def _update_match(match: ReconciliationMatch, **values: Any) -> None:
    for key, value in values.items():
        setattr(match, key, value)
    match.dominio_entry = None
    match.save(update_fields=[*values, "dominio_entry", "updated_at"])
