"""Exported accounting facts cannot become new postings (D-311)."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier

import pytest
from django.db import close_old_connections, connection
from django.test import override_settings

from apps.hub.models import (
    AccountingExport,
    ClientCompany,
    JournalEntry,
    JournalLine,
    LedgerAccount,
)
from apps.hub.reconciliation_service import (
    ReconciliationError,
    approve_journal_entry,
    create_export,
)

pytestmark = pytest.mark.django_db
START, END = date(2026, 9, 1), date(2026, 9, 30)


@pytest.fixture
def posting(organization, tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path, RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED=True):
        company = ClientCompany.objects.create(organization=organization, name="Synthetic")
        entry = JournalEntry.objects.create(
            organization=organization,
            company=company,
            occurred_on=START,
            history="Synthetic posting",
            purpose="record",
            state="approved",
        )
        for code, side in [("1", "debit"), ("2", "credit")]:
            LedgerAccount.objects.create(
                organization=organization, company=company, code=code, name=code
            )
            JournalLine.objects.create(
                organization=organization,
                entry=entry,
                account_code=code,
                side=side,
                amount_cents=12345,
            )
        yield entry


def export(entry, **kwargs):
    return create_export(
        organization=entry.organization,
        company=entry.company,
        start=kwargs.pop("start", START),
        end=kwargs.pop("end", END),
        **kwargs,
    )


def test_approval_cannot_reopen_exported_entry_or_invalidate_snapshot(posting):
    original = export(posting)
    posting.history = ""
    posting.save(update_fields=["history"])
    with pytest.raises(ReconciliationError, match="já exportado"):
        approve_journal_entry(entry=posting)
    posting.refresh_from_db()
    assert posting.state == "exported"
    assert AccountingExport.objects.get(pk=original.pk).content_hash == original.content_hash


def test_history_blocks_new_export_even_after_entry_state_regresses(posting):
    export(posting)
    JournalEntry.objects.filter(pk=posting.pk).update(state="approved")
    with pytest.raises(ReconciliationError, match="já exportados"):
        export(posting)
    with pytest.raises(ReconciliationError, match="já exportado"):
        approve_journal_entry(entry=posting)
    assert AccountingExport.objects.count() == 1


def test_reexport_uses_original_bytes_version_and_order_after_live_changes(posting):
    original = export(posting)
    with original.content.open("rb") as stream:
        expected = stream.read()
    JournalEntry.objects.filter(pk=posting.pk).update(history="Changed after export")
    posting.lines.update(amount_cents=99999)
    repeated = export(posting, reexport_of=original, reexport_reason="Explicit reviewed resend")
    with repeated.content.open("rb") as stream:
        assert stream.read() == expected
    assert repeated.content_hash == original.content_hash
    assert repeated.adapter_version == original.adapter_version
    assert repeated.entry_ids == original.entry_ids
    assert repeated.reexport_of_id == original.pk
    assert repeated.state == "ready" and repeated.confirmed_at is None


@pytest.mark.parametrize("change", ["period", "target", "state", "missing", "tampered"])
def test_reexport_refuses_invalid_original_without_new_records(posting, change):
    original = export(posting)
    kwargs = {}
    if change == "period":
        kwargs["end"] = date(2026, 10, 1)
    elif change in {"target", "state"}:
        AccountingExport.objects.filter(pk=original.pk).update(
            **{change: "siescon" if change == "target" else "failed"}
        )
    elif change == "missing":
        original.content.storage.delete(original.content.name)
    else:
        with original.content.open("wb") as stream:
            stream.write(b"corrupt")
    with pytest.raises(ReconciliationError):
        export(posting, reexport_of=original, reexport_reason="Explicit resend", **kwargs)
    assert AccountingExport.objects.count() == 1


def test_export_validates_period_in_service(posting):
    with pytest.raises(ReconciliationError, match="início do período"):
        export(posting, start=END, end=START)
    assert not AccountingExport.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_postgresql_simultaneous_approval_and_export_cannot_reopen_posting(posting):
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    barrier = Barrier(2)

    def run(action):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            with override_settings(RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED=True):
                try:
                    return (
                        export(posting)
                        if action == "export"
                        else approve_journal_entry(entry=posting)
                    )
                except ReconciliationError:
                    return None
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(run, ["approve", "export"]))
    posting.refresh_from_db()
    assert any(isinstance(result, AccountingExport) for result in results)
    assert posting.state == "exported"
    assert AccountingExport.objects.count() == 1
    with pytest.raises(ReconciliationError):
        export(posting)
