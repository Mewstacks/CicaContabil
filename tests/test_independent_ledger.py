from __future__ import annotations

import csv
import io
from datetime import date

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.hub.ledger_import import LEDGER_COLUMNS, import_ledger_source
from apps.hub.models import (
    AccountingEntry,
    ClientCompany,
    FinancialAccount,
    IndependentLedgerRecord,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    MovementReconciliation,
    NormalizedMovement,
    ReconciliationMatch,
    ReconciliationRun,
)
from apps.hub.reconciliation import (
    confirm_reconciliation_match,
    import_ofx,
    rebuild_reconciliation_matches,
)
from apps.hub.reconciliation_report import build_source_report, render_conference_csv
from apps.hub.reconciliation_service import (
    ReconciliationError,
    _entry_capacity,
    approve_journal_entry,
    confirm_reconciliation,
    create_export,
    create_journal_entry_from_movement,
    create_source_file,
    process_run,
    undo_reconciliation,
    validate_journal_entry,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def account(organization, tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        company = ClientCompany.objects.create(organization=organization, name="Empresa sintética")
        account = FinancialAccount.objects.create(
            organization=organization,
            company=company,
            name="Banco de teste",
            account_reference="001:123",
            ledger_code="1.1",
        )
        for code in ["1.1", "2.1", "3.1"]:
            LedgerAccount.objects.create(
                organization=organization, company=company, code=code, name=code
            )
        yield account


def ledger_bytes(count=1, *, compound=False):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(LEDGER_COLUMNS)
    for i in range(count):
        common = [f"journal-{i}", "bank", "2026-09-12", f"Fonte independente {i}"]
        writer.writerow([*common, "1.1", "debit", 10000 + i, "inflow", f"DOC-{i}"])
        writer.writerow(
            [
                common[0],
                "other",
                *common[2:],
                "2.1",
                "credit",
                12000 + i if compound else 10000 + i,
                "",
                f"DOC-{i}",
            ]
        )
        if compound:
            writer.writerow([common[0], "fee", *common[2:], "3.1", "debit", 2000, "", f"DOC-{i}"])
    return output.getvalue().encode()


def source_for(account, content=None):
    source, run, _ = create_source_file(
        organization=account.organization,
        company=account.company,
        filename="razao.csv",
        content=content or ledger_bytes(),
        origin="accounting",
        financial_account=account,
    )
    return source, run


def bank_for(account, count=1, *, legacy=True):
    rows = "".join(
        f"<STMTTRN><DTPOSTED>20260912<TRNAMT>{(10000 + i) / 100:.2f}"
        f"<FITID>fit-{i}<MEMO>Crédito de teste {i}</STMTTRN>"
        for i in range(count)
    )
    content = (
        f"OFXHEADER:100\n<OFX><BANKID>001<ACCTID>123<BANKTRANLIST>{rows}</BANKTRANLIST></OFX>"
    ).encode()
    kwargs = dict(
        organization=account.organization,
        company=account.company,
        filename="extrato.ofx",
        content=content,
        financial_account=account,
    )
    source, run, _ = create_source_file(**kwargs, origin="bank_statement")
    if legacy:
        import_ofx(**kwargs)
    assert process_run(str(run.pk))["created"] == count
    return source, content


def test_complete_ledger_import_creates_two_linked_views_and_preserves_provenance(account):
    source, run = source_for(account, ledger_bytes(compound=True))
    result = process_run(str(run.pk))
    run.refresh_from_db()
    assert result["created"] == 1, run.errors
    assert run.stage == "ledger_review"
    record = source.ledger_records.get()
    assert record.entry.lines.count() == 3
    assert record.entry.movement_id is None
    assert record.entry.state == "draft"
    assert not source.movements.exists()
    assert record.source_reference["content_hash"] == source.content_hash
    assert record.source_reference["rows"] == [2, 3, 4]
    assert _entry_capacity(record.entry) == 10000  # Bank effect, not 12000 total debits.
    assert source.operational_activity.work_status == "pending"
    assert import_ledger_source(source) == {"created": 0, "ignored": 1, "processed": 1}
    with pytest.raises(ReconciliationError, match="fonte de comparação"):
        approve_journal_entry(entry=record.entry)


@pytest.mark.parametrize(
    "broken",
    [
        lambda b: b.replace(b"10000;;DOC", b"9999;;DOC"),
        lambda b: b.replace(b"inflow", b"D"),
        lambda b: b.replace(b";2.1;", b";9.9;"),
        lambda b: b.replace(b";10000;", b";NaN;"),
        lambda b: b.replace(b";10000;", b";0;"),
        lambda b: b.replace(b";2026-09-12;", b";12/09/2026;"),
        lambda b: b.replace(b"journal-0;other", b"journal-0;bank"),
        lambda b: b.replace(b"cash_direction", b"direction"),
    ],
)
def test_malformed_ledger_is_atomic_and_never_becomes_bank_movements(account, broken):
    _source, run = source_for(account, broken(ledger_bytes()))
    assert process_run(str(run.pk))["state"] == "failed"
    assert not IndependentLedgerRecord.objects.exists()
    assert not JournalEntry.objects.exists()
    assert not AccountingEntry.objects.exists()
    assert not NormalizedMovement.objects.exists()


def test_invalid_second_journal_rolls_back_whole_source(account):
    data = ledger_bytes(2).replace(b";10001;;DOC-1", b";9999;;DOC-1")
    source, _ = source_for(account, data)
    with pytest.raises(ReconciliationError, match="desequilibrado"):
        import_ledger_source(source)
    assert not JournalEntry.objects.exists()


def test_reordered_source_is_idempotent_and_changed_key_cannot_replace_decisions(account):
    source, _ = source_for(account)
    import_ledger_source(source)
    original = IndependentLedgerRecord.objects.get()
    lines = ledger_bytes().splitlines()
    reordered, _ = source_for(account, b"\n".join([lines[0], lines[2], lines[1]]) + b"\n")
    assert import_ledger_source(reordered)["ignored"] == 1
    changed, _ = source_for(account, ledger_bytes().replace(b"10000", b"10001"))
    with pytest.raises(ReconciliationError, match="conteúdo diferente"):
        import_ledger_source(changed)
    original.refresh_from_db()
    assert IndependentLedgerRecord.objects.count() == JournalEntry.objects.count() == 1
    assert original.accounting_entry.amount_cents == 10000


@pytest.mark.parametrize("path", ["legacy", "advanced"])
def test_confirmation_is_shared_by_both_views_and_undo_keeps_decision_history(account, path):
    ledger, _ = source_for(account)
    import_ledger_source(ledger)
    bank, _ = bank_for(account)
    record, movement = ledger.ledger_records.get(), bank.movements.get()
    match = ReconciliationMatch.objects.get()
    if path == "legacy":
        confirm_reconciliation_match(match=match, accounting_entry=record.accounting_entry)
        confirm_reconciliation_match(match=match, accounting_entry=record.accounting_entry)
    else:
        confirm_reconciliation(
            movement=movement,
            entry=record.entry,
            amount_cents=10000,
            evidence={"review": "synthetic-source"},
        )
    match.refresh_from_db()
    assert match.status == "matched"
    reconciliation = MovementReconciliation.objects.get()
    assert reconciliation.amount_cents == 10000
    assert reconciliation.decisions.count() == 1
    rebuild_reconciliation_matches(organization=account.organization, company=account.company)
    match.refresh_from_db()
    assert match.is_manual
    undo_reconciliation(reconciliation=reconciliation)
    match.refresh_from_db()
    assert match.status == "ambiguous" and match.accounting_entry_id is None
    assert reconciliation.decisions.count() == 2
    confirm_reconciliation_match(match=match, accounting_entry=record.accounting_entry)
    assert reconciliation.decisions.count() == 3


def test_late_legacy_upload_projects_existing_allocation(account):
    ledger, _ = source_for(account)
    import_ledger_source(ledger)
    bank, content = bank_for(account, legacy=False)
    record = ledger.ledger_records.get()
    confirm_reconciliation(
        movement=bank.movements.get(),
        entry=record.entry,
        amount_cents=10000,
        evidence={"review": "synthetic"},
    )
    assert not ReconciliationMatch.objects.exists()
    import_ofx(
        organization=account.organization,
        company=account.company,
        filename="same.ofx",
        content=content,
    )
    assert ReconciliationMatch.objects.get().status == "matched"
    assert MovementReconciliation.objects.count() == 1


def test_legacy_confirmation_waits_for_processed_ofx(account):
    ledger, _ = source_for(account)
    import_ledger_source(ledger)
    bank, _ = bank_for(account)
    bank.movements.all().delete()
    record = ledger.ledger_records.get()
    with pytest.raises(ValueError, match="Processe o mesmo OFX"):
        confirm_reconciliation_match(
            match=ReconciliationMatch.objects.get(), accounting_entry=record.accounting_entry
        )
    assert not MovementReconciliation.objects.exists()


@pytest.mark.parametrize(
    "field,value",
    [("direction", "outflow"), ("amount_cents", -10000), ("occurred_on", date(2026, 9, 13))],
)
def test_independent_source_rejects_incompatible_bank_facts(account, field, value):
    ledger, _ = source_for(account)
    import_ledger_source(ledger)
    bank, _ = bank_for(account)
    movement = bank.movements.get()
    setattr(movement, field, value)
    movement.save()
    with pytest.raises(ReconciliationError, match="conta, data, direção"):
        confirm_reconciliation(
            movement=movement,
            entry=ledger.ledger_records.get().entry,
            amount_cents=10000,
            evidence={"review": "test"},
        )
    assert not MovementReconciliation.objects.exists()


def test_source_report_shows_missing_items_in_both_directions_and_unknown_balances(account):
    ledger, _ = source_for(account, ledger_bytes(2))
    import_ledger_source(ledger)
    bank, _ = bank_for(account, 3)
    record = ledger.ledger_records.get(external_key="journal-0")
    confirm_reconciliation_match(
        match=ReconciliationMatch.objects.get(transaction__external_id="fit-0"),
        accounting_entry=record.accounting_entry,
    )
    report = build_source_report(bank)
    assert report["bank_count"] == 3 and report["ledger_count"] == 2
    assert report["bank_unmatched_count"] == 2 and report["ledger_unmatched_count"] == 1
    assert report["period_difference_cents"] == 10002
    assert report["opening_ledger_cents"] is report["closing_bank_cents"] is None
    assert not report["homologated"] and not report["coverage_confirmed"]
    assert "não informado" in render_conference_csv(report).decode("utf-8-sig")
    with pytest.raises(ReconciliationError, match="início do período"):
        build_source_report(bank, start=date(2026, 10, 1), end=date(2026, 9, 1))


def test_200_independent_synthetic_journals_share_allocations_and_survive_retry(account):
    ledger, run = source_for(account, ledger_bytes(200))
    assert process_run(str(run.pk))["created"] == 200
    bank, _ = bank_for(account, 200)
    records = {r.external_key: r for r in ledger.ledger_records.select_related("accounting_entry")}
    for match in ReconciliationMatch.objects.select_related("transaction"):
        index = match.transaction.external_id.removeprefix("fit-")
        confirm_reconciliation_match(
            match=match, accounting_entry=records[f"journal-{index}"].accounting_entry
        )
    assert MovementReconciliation.objects.filter(state="confirmed").count() == 200
    assert ReconciliationMatch.objects.filter(status="matched").count() == 200
    retry = ReconciliationRun.objects.create(organization=account.organization, source_file=ledger)
    assert process_run(str(retry.pk))["ignored"] == 200
    report = build_source_report(bank)
    assert report["bank_unmatched_count"] == report["ledger_unmatched_count"] == 0
    assert report["period_difference_cents"] == 0
    assert not report[
        "coverage_confirmed"
    ]  # Synthetic volume never grants the customer acceptance.


def test_report_download_is_private_and_company_scoped(account, user):
    from django.test import Client

    from apps.hub.models import CompanyAccessGrant, ProductModule
    from apps.organizations.models import Membership

    ProductModule.objects.create(
        organization=account.organization, code="reconciliation", enabled=True
    )
    member = Membership.objects.create(organization=account.organization, user=user, role="owner")
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(account.organization_id)
    session.save()
    bank, _ = bank_for(account)
    url = reverse("hub:reconciliation-source-report", args=[bank.pk])
    response = client.get(url)
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store, private"
    assert response["X-Content-Type-Options"] == "nosniff"
    assert "conferencia-banco-razao.csv" in response["Content-Disposition"]
    assert "Nenhum Razão independente" in response.content.decode("utf-8-sig")
    member.role = "operator"
    member.save()
    assert client.get(url).status_code == 404
    CompanyAccessGrant.objects.create(
        organization=account.organization,
        membership=member,
        company=account.company,
        modules=["reconciliation"],
    )
    assert client.get(url).status_code == 200
    client.logout()
    assert client.get(url).status_code == 302


@pytest.mark.django_db(transaction=True)
def test_postgres_legacy_and_advanced_views_share_source_capacity(account):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connection, connections

    if connection.vendor != "postgresql":
        pytest.skip("Concorrência entre filas exige PostgreSQL com conexões independentes.")
    ledger, _ = source_for(account)
    import_ledger_source(ledger)
    bank, content = bank_for(account)
    other, run, _ = create_source_file(
        organization=account.organization,
        company=account.company,
        filename="other.ofx",
        content=content.replace(b"fit-0", b"fit-99"),
        origin="bank_statement",
        financial_account=account,
    )
    assert process_run(str(run.pk))["created"] == 1
    record_id = ledger.ledger_records.get().pk
    match_id = ReconciliationMatch.objects.get(
        transaction__statement__content_hash=bank.content_hash
    ).pk
    movement_id = other.movements.get().pk
    barrier = Barrier(2)

    def confirm(path):
        connections.close_all()
        try:
            record = IndependentLedgerRecord.objects.get(pk=record_id)
            barrier.wait(timeout=10)
            try:
                if path == "legacy":
                    confirm_reconciliation_match(
                        match=ReconciliationMatch.objects.get(pk=match_id),
                        accounting_entry=record.accounting_entry,
                    )
                else:
                    confirm_reconciliation(
                        movement=NormalizedMovement.objects.get(pk=movement_id),
                        entry=record.entry,
                        amount_cents=10000,
                        evidence={"review": "independent"},
                    )
                return "confirmed"
            except ValueError:
                return "refused"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(confirm, ["legacy", "advanced"])) == ["confirmed", "refused"]
    assert MovementReconciliation.objects.filter(state="confirmed").count() == 1


@pytest.mark.django_db(transaction=True)
def test_postgres_simultaneous_ledger_retries_create_one_complete_journal(account):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connection, connections

    from apps.hub.models import ReconciliationSourceFile

    if connection.vendor != "postgresql":
        pytest.skip("Retentativa concorrente do Razão exige PostgreSQL.")
    source, _ = source_for(account)
    barrier = Barrier(2)

    def receive(_):
        connections.close_all()
        try:
            local = ReconciliationSourceFile.objects.get(pk=source.pk)
            barrier.wait(timeout=10)
            return import_ledger_source(local)["created"]
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(receive, [1, 2])) == [0, 1]
    assert IndependentLedgerRecord.objects.count() == JournalEntry.objects.count() == 1
    assert JournalLine.objects.count() == 2


def test_altered_ledger_file_is_refused_before_any_journal_is_written(account):
    from pathlib import Path

    source, _ = source_for(account)
    Path(source.content.path).write_bytes(ledger_bytes().replace(b"10000", b"10001"))
    with pytest.raises(ReconciliationError, match="hash do arquivo"):
        import_ledger_source(source)
    assert not JournalEntry.objects.exists()


def test_report_refuses_incomplete_processing_and_modified_source(account):
    from pathlib import Path

    bank, _ = bank_for(account)
    run = bank.runs.get()
    run.state = "failed"
    run.save()
    with pytest.raises(ReconciliationError, match="Corrija ou retome"):
        build_source_report(bank)
    run.state = "review"
    run.save()
    Path(bank.content.path).write_bytes(b"modified")
    with pytest.raises(ReconciliationError, match="hash do extrato"):
        build_source_report(bank)


def test_read_only_audit_detects_broken_projection_without_repair(account):
    import json

    from django.core.management import call_command

    ledger, _ = source_for(account)
    import_ledger_source(ledger)
    bank_for(account)
    match = ReconciliationMatch.objects.get()
    match.accounting_entry = ledger.ledger_records.get().accounting_entry
    match.status = "matched"
    match.save()
    output = io.StringIO()
    call_command("audit_ofx_integrity", organization=str(account.organization_id), stdout=output)
    report = json.loads(output.getvalue())
    assert report["issues"]["missing_shared_ledger_allocation"] == 1
    assert report["read_only"] and not report["homologated"]
    assert not MovementReconciliation.objects.exists()


def _posting_case(account):
    ledger, _ = source_for(account)
    import_ledger_source(ledger)
    bank, _ = bank_for(account)
    movement = bank.movements.get()
    movement.debit_account_code = "1.1"
    movement.credit_account_code = "2.1"
    movement.save(update_fields=["debit_account_code", "credit_account_code"])
    return movement, ledger.ledger_records.get()


@pytest.mark.parametrize("amount", [5000, 10000])
def test_any_confirmed_allocation_blocks_new_posting_including_partial(account, amount):
    movement, record = _posting_case(account)
    allocation = confirm_reconciliation(
        movement=movement, entry=record.entry, amount_cents=amount, evidence={"reviewed": True}
    )
    with pytest.raises(ReconciliationError, match="já possui conciliação"):
        create_journal_entry_from_movement(movement=movement)
    undo_reconciliation(reconciliation=allocation)
    assert create_journal_entry_from_movement(movement=movement).state == "draft"


@pytest.mark.parametrize("state", ["draft", "approved"])
def test_ledger_confirmation_invalidates_derived_posting_without_reviving_on_undo(account, state):
    movement, record = _posting_case(account)
    derived = create_journal_entry_from_movement(movement=movement)
    if state == "approved":
        approve_journal_entry(entry=derived)
    match = ReconciliationMatch.objects.get()
    confirm_reconciliation_match(match=match, accounting_entry=record.accounting_entry)
    derived.refresh_from_db()
    assert derived.state == "invalid"
    assert any("já possui conciliação" in error for error in validate_journal_entry(derived))
    with pytest.raises(ReconciliationError, match="já possui conciliação"):
        approve_journal_entry(entry=derived)
    undo_reconciliation(reconciliation=MovementReconciliation.objects.get())
    derived.refresh_from_db()
    assert derived.state == "invalid"


def test_historical_posting_is_revalidated_at_approval_and_export(account):
    movement, record = _posting_case(account)
    derived = create_journal_entry_from_movement(movement=movement)
    confirm_reconciliation(
        movement=movement, entry=record.entry, amount_cents=10000, evidence={"reviewed": True}
    )
    # Reproduce a pre-fix approval; audit/export must not trust its old state.
    JournalEntry.objects.filter(pk=derived.pk).update(state="approved")
    with (
        override_settings(RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED=True),
        pytest.raises(ReconciliationError, match="já possui conciliação"),
    ):
        create_export(
            organization=account.organization,
            company=account.company,
            start=date(2026, 9, 1),
            end=date(2026, 9, 30),
        )
    assert not account.company.accounting_exports.exists()


def test_exported_posting_requires_explicit_import_review_before_ledger_match(account):
    movement, record = _posting_case(account)
    derived = approve_journal_entry(entry=create_journal_entry_from_movement(movement=movement))
    with override_settings(RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED=True):
        export = create_export(
            organization=account.organization,
            company=account.company,
            start=date(2026, 9, 1),
            end=date(2026, 9, 30),
        )
    with pytest.raises(ReconciliationError, match="já foi exportado"):
        confirm_reconciliation(
            movement=movement, entry=record.entry, amount_cents=10000, evidence={"reviewed": True}
        )
    assert export.entry_ids == [str(derived.pk)]
    assert not MovementReconciliation.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("operation", ["generate", "approve", "export"])
def test_postgres_ledger_match_serializes_with_posting_generation_approval_and_export(
    account, operation
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connection, connections

    if connection.vendor != "postgresql":
        pytest.skip("Escrituração concorrente exige PostgreSQL.")
    movement, record = _posting_case(account)
    derived = None
    if operation in {"approve", "export"}:
        derived = create_journal_entry_from_movement(movement=movement)
        if operation == "export":
            approve_journal_entry(entry=derived)
    barrier = Barrier(2)

    def run(action):
        connections.close_all()
        try:
            barrier.wait(timeout=10)
            try:
                if action == "match":
                    confirm_reconciliation(
                        movement=movement,
                        entry=record.entry,
                        amount_cents=10000,
                        evidence={"reviewed": True},
                    )
                elif operation == "generate":
                    create_journal_entry_from_movement(movement=movement)
                elif operation == "approve":
                    approve_journal_entry(entry=derived)
                else:
                    create_export(
                        organization=account.organization,
                        company=account.company,
                        start=date(2026, 9, 1),
                        end=date(2026, 9, 30),
                    )
                return "done"
            except ReconciliationError:
                return "refused"
        finally:
            connections.close_all()

    with (
        override_settings(RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED=True),
        ThreadPoolExecutor(max_workers=2) as pool,
    ):
        results = list(pool.map(run, ["match", "posting"]))
    assert "done" in results
    matched = MovementReconciliation.objects.filter(state="confirmed").exists()
    active_posting = movement.journal_entries.filter(
        state__in=["draft", "approved", "exported"]
    ).exists()
    assert not (matched and active_posting)
    if operation == "export":
        assert sorted(results) == ["done", "refused"]


def test_reconciled_movement_guides_review_and_blocks_edit_and_bulk_actions(account, user):
    from django.test import Client

    from apps.hub.models import ProductModule
    from apps.organizations.models import Membership

    ProductModule.objects.create(
        organization=account.organization, code="reconciliation", enabled=True
    )
    Membership.objects.create(organization=account.organization, user=user, role="owner")
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(account.organization_id)
    session.save()
    movement, record = _posting_case(account)
    confirm_reconciliation(
        movement=movement, entry=record.entry, amount_cents=10000, evidence={"reviewed": True}
    )
    url = reverse("hub:reconciliation-movement", args=[movement.pk])
    detail = client.get(url)
    assert detail.status_code == 200
    assert "Conferir a conciliação existente" in detail.content.decode()
    assert 'id="movement-review-form"' not in detail.content.decode()
    assert b'value="generate_entry"' not in detail.content
    assert b'value="approve_entry"' not in detail.content
    assert b"Desfazer" in detail.content
    before = movement.revision
    assert client.post(url, {"action": "ignore_movement", "reason": "não pode"}).status_code == 302
    movement.refresh_from_db()
    assert movement.revision == before
    assert client.post(url, {"action": "generate_entry"}).status_code == 302
    assert not movement.journal_entries.exists()


def test_read_only_audit_reports_historical_duplicate_posting_without_changing_it(account):
    import json

    from django.core.management import call_command

    movement, record = _posting_case(account)
    derived = create_journal_entry_from_movement(movement=movement)
    confirm_reconciliation(
        movement=movement, entry=record.entry, amount_cents=10000, evidence={"reviewed": True}
    )
    JournalEntry.objects.filter(pk=derived.pk).update(state="approved")
    output = io.StringIO()
    call_command("audit_ofx_integrity", organization=str(account.organization_id), stdout=output)
    report = json.loads(output.getvalue())
    assert report["issues"]["derived_postings_on_reconciled_movements"] == 1
    assert report["read_only"] and not report["homologated"]
    derived.refresh_from_db()
    assert derived.state == "approved"
