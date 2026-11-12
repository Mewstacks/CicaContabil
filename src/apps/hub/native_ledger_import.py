"""Atomic native source journals. No account classification, bank mirrors or approvals."""

from __future__ import annotations

import hashlib
from collections import defaultdict
from typing import Any

from django.db import transaction

from apps.audit.services import record_event
from apps.hub.dominio_journal_normalization import LedgerParty, NormalizedJournalCandidate
from apps.hub.models import (
    AccountingEntry,
    ClientCompany,
    DataSource,
    IndependentLedgerRecord,
    JournalEntry,
    JournalLine,
    ReconciliationSourceFile,
)
from apps.intelligence.native_ledger_contract import VERSION, canonical_hash


@transaction.atomic
def import_native_source(
    *,
    source: ReconciliationSourceFile,
    candidate: NormalizedJournalCandidate,
    snapshot: dict[str, Any],
    job_id: str,
) -> dict[str, int]:
    ClientCompany.objects.select_for_update().get(
        pk=source.company_id, organization_id=source.organization_id
    )
    account = source.financial_account
    if (
        account is None
        or account.organization_id != source.organization_id
        or account.company_id != source.company_id
        or not account.active
        or account.ledger_code != "8"
        or not account.account_reference
        or source.kind != "json"
        or source.origin != "accounting"
    ):
        raise ValueError("ledger_account_scope")
    grouped: dict[str, list[LedgerParty]] = defaultdict(list)
    for party in candidate.parties:
        grouped[party.entry_key].append(party)
    prepared = []
    for key, parties in grouped.items():
        bank = next(p for p in parties if p.cash_direction)
        raw_rows = [r for r in snapshot["records"] if key == f"dominio:212:lote:{r['lot_code']}"]
        # Include raw history codes/nulls/catalogue so provenance changes cannot silently replay.
        used = {int(p.account_code) for p in parties}
        fingerprint = canonical_hash(
            {
                "parties": [vars(p) for p in parties],
                "source_rows": raw_rows,
                "accounts": [a for a in snapshot["accounts"] if a["account_code"] in used],
            }
        )
        existing = IndependentLedgerRecord.objects.filter(
            organization=source.organization, financial_account=account, external_key=key
        ).first()
        if existing is not None and existing.fingerprint != fingerprint:
            raise ValueError("ledger_content_conflict")
        prepared.append((key, parties, bank, fingerprint, existing, raw_rows))
    data_source, _ = DataSource.objects.get_or_create(
        organization=source.organization,
        kind=DataSource.Kind.DOMINIO_LOCAL_AGENT,
        defaults={"label": "Domínio Local (agente)"},
    )
    created = 0
    for key, parties, bank, fingerprint, existing, raw_rows in prepared:
        if existing is not None:
            continue
        entry = JournalEntry.objects.create(
            organization=source.organization,
            company=source.company,
            occurred_on=bank.date,
            history=bank.history,
            purpose="source_ledger",
        )
        bank_line = None
        for party in parties:
            line = JournalLine.objects.create(
                organization=source.organization,
                entry=entry,
                account_code=party.account_code,
                side=party.side,
                amount_cents=party.amount_cents,
                history=party.history,
            )
            if party is bank:
                bank_line = line
        accounting = AccountingEntry.objects.create(
            organization=source.organization,
            data_source=data_source,
            company=source.company,
            external_key="ledger:" + hashlib.sha256(f"{account.pk}:{key}".encode()).hexdigest(),
            occurred_on=bank.date,
            description=bank.history,
            amount_cents=bank.amount_cents,
            direction=bank.cash_direction,
            account_reference=account.account_reference,
        )
        assert bank_line is not None
        IndependentLedgerRecord.objects.create(
            organization=source.organization,
            source_file=source,
            financial_account=account,
            external_key=key,
            fingerprint=fingerprint,
            entry=entry,
            accounting_entry=accounting,
            bank_line=bank_line,
            source_reference={
                "contract": VERSION,
                "job_id": job_id,
                "content_hash": source.content_hash,
                "scope_revision": snapshot["scope_revision"],
                "row_codes": [r["row_code"] for r in raw_rows],
                "party_keys": [p.line_key for p in parties],
                "document": bank.document,
            },
        )
        created += 1
    record_event(
        action="hub.reconciliation.native_ledger_imported",
        organization=source.organization,
        target=source,
        metadata={"created": created, "total": len(prepared), "job_id": job_id},
    )
    from apps.hub.reconciliation import rebuild_reconciliation_matches

    rebuild_reconciliation_matches(organization=source.organization, company=source.company)
    return {
        "created": created,
        "ignored": len(prepared) - created,
        "journals": len(prepared),
        "parties": len(candidate.parties),
        "source_rows": candidate.source_rows,
        "bank_effects": candidate.bank_effects,
    }
