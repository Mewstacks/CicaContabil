"""Regressions for the independent-source and shared OFX intake boundaries (D-303)."""

from __future__ import annotations

import hashlib
from datetime import date

import pytest
from django.test import override_settings

from apps.audit.models import AuditEvent
from apps.hub.models import (
    AccountingEntry,
    BankStatementImport,
    BankTransaction,
    ClientCompany,
    DataSource,
    DominioBankEntry,
    FinancialAccount,
    NormalizedMovement,
    OfxTransactionIdentity,
    ReconciliationMatch,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation import (
    OfxParseError,
    confirm_reconciliation_match,
    import_ofx,
    parse_ofx,
)
from apps.hub.reconciliation_service import ReconciliationError, create_source_file, process_run
from apps.organizations.models import Organization

OFX = (
    b"OFXHEADER:100\n<OFX><STMTRS><BANKACCTFROM><BANKID>001<ACCTID>123</BANKACCTFROM>"
    b"<BANKTRANLIST><STMTTRN><DTPOSTED>20260912<TRNAMT>-12.34<FITID>fit-1"
    b"<NAME>Fornecedor</STMTTRN></BANKTRANLIST></STMTRS></OFX>"
)


@pytest.fixture
def company(organization: Organization) -> ClientCompany:
    return ClientCompany.objects.create(organization=organization, name="Empresa fictícia")


@pytest.mark.parametrize(
    "amount", [b"NaN", b"Infinity", b"1e999", b"0", b"0.001", b"92233720368547759"]
)
def test_ofx_rejects_non_finite_zero_or_overflow_amounts(amount: bytes) -> None:
    with pytest.raises(OfxParseError, match="valor válido"):
        parse_ofx(OFX.replace(b"-12.34", amount))


@pytest.mark.parametrize("fitid", [b"", b"x" * 161])
def test_ofx_requires_a_bounded_bank_transaction_identity(fitid: bytes) -> None:
    with pytest.raises(OfxParseError, match="FITID"):
        parse_ofx(OFX.replace(b"fit-1", fitid))


def test_ofx_rejects_duplicate_fitid_inside_one_file() -> None:
    transaction = OFX.split(b"<BANKTRANLIST>")[1].split(b"</BANKTRANLIST>")[0]
    with pytest.raises(OfxParseError, match="FITID"):
        parse_ofx(OFX.replace(b"</BANKTRANLIST>", transaction + b"</BANKTRANLIST>"))


def test_ofx_preserves_branch_and_rejects_multi_account_files() -> None:
    assert (
        parse_ofx(OFX.replace(b"<ACCTID>", b"<BRANCHID>002<ACCTID>")).account_reference
        == "001:002:123"
    )
    with pytest.raises(OfxParseError, match="único banco"):
        parse_ofx(OFX.replace(b"</STMTRS>", b"<ACCTID>999</STMTRS>"))


@pytest.mark.django_db
@pytest.mark.parametrize("first_path", ["source", "legacy"])
def test_shared_identity_blocks_overlap_in_either_queue_before_worker_runs(
    company: ClientCompany,
    tmp_path,
    first_path: str,
) -> None:
    args = {"organization": company.organization, "company": company, "filename": "extrato.ofx"}
    with override_settings(MEDIA_ROOT=tmp_path):
        if first_path == "source":
            create_source_file(**args, content=OFX, origin="bank_statement")
        else:
            import_ofx(**args, content=OFX)
        # The same source hash can feed both views, including a retry.
        source, run, _created = create_source_file(**args, content=OFX, origin="bank_statement")
        statement, _ = import_ofx(**args, content=OFX)
        assert statement.transactions.count() == 1
        assert OfxTransactionIdentity.objects.count() == 1
        assert process_run(str(run.pk))["created"] == 1
        for path in ["source", "legacy"]:
            with pytest.raises((OfxParseError, ReconciliationError), match="sobreposição"):
                if path == "source":
                    create_source_file(**args, content=OFX + b"\n", origin="bank_statement")
                else:
                    import_ofx(**args, content=OFX + b"\n")
        assert ReconciliationSourceFile.objects.count() == 1
        assert NormalizedMovement.objects.count() == 1
        assert BankStatementImport.objects.count() == 1
        assert BankTransaction.objects.count() == 1
        assert OfxTransactionIdentity.objects.count() == 1
        assert source.runs.count() == 1


@pytest.mark.django_db
def test_partially_overlapping_file_is_rejected_as_a_whole(company: ClientCompany) -> None:
    args = {"organization": company.organization, "company": company, "filename": "extrato.ofx"}
    import_ofx(**args, content=OFX)
    transaction = OFX.split(b"<BANKTRANLIST>")[1].split(b"</BANKTRANLIST>")[0]
    overlap = OFX.replace(
        b"</BANKTRANLIST>", transaction.replace(b"fit-1", b"fit-2") + b"</BANKTRANLIST>"
    )
    with pytest.raises(OfxParseError, match="nenhuma linha"):
        import_ofx(**args, content=overlap)
    assert BankStatementImport.objects.count() == BankTransaction.objects.count() == 1
    assert not OfxTransactionIdentity.objects.filter(external_id="fit-2").exists()


@pytest.mark.django_db
def test_same_fitid_is_independent_between_accounts_companies_and_tenants(
    company: ClientCompany,
) -> None:
    organization = company.organization
    other = ClientCompany.objects.create(organization=organization, name="Outra")
    outsider = Organization.objects.create(name="Outro escritório", slug="outro-escritorio")
    outside_company = ClientCompany.objects.create(organization=outsider, name="Outra")
    for selected in [company, other, outside_company]:
        for account in [b"123", b"999"]:
            import_ofx(
                organization=selected.organization,
                company=selected,
                filename="extrato.ofx",
                content=OFX.replace(b"<ACCTID>123", b"<ACCTID>" + account),
            )
    assert BankTransaction.objects.count() == OfxTransactionIdentity.objects.count() == 6


@pytest.mark.django_db
@pytest.mark.parametrize("path", ["source", "legacy"])
def test_wrong_selected_account_never_feeds_either_queue(
    company: ClientCompany, tmp_path, path: str
) -> None:
    account = FinancialAccount.objects.create(
        organization=company.organization,
        company=company,
        name="Outra",
        account_reference="001:999",
    )
    args = {
        "organization": company.organization,
        "company": company,
        "filename": "extrato.ofx",
        "content": OFX,
        "financial_account": account,
    }
    with (
        override_settings(MEDIA_ROOT=tmp_path),
        pytest.raises(
            (OfxParseError, ReconciliationError),
            match="conta financeira selecionada",
        ),
    ):
        if path == "source":
            create_source_file(**args, origin="bank_statement")
        else:
            import_ofx(**args)
    assert not BankTransaction.objects.exists()
    assert not ReconciliationSourceFile.objects.exists()
    assert not OfxTransactionIdentity.objects.exists()
    assert not list(tmp_path.rglob("*.ofx"))


@pytest.fixture
def match_and_entry(company: ClientCompany):
    statement, _ = import_ofx(
        organization=company.organization,
        company=company,
        filename="extrato.ofx",
        content=OFX,
    )
    source = DataSource.objects.create(
        organization=company.organization,
        kind="other_manual",
        label="Razão independente",
    )
    entry = AccountingEntry.objects.create(
        organization=company.organization,
        company=company,
        data_source=source,
        external_key="ledger-1",
        occurred_on=date(2026, 9, 12),
        amount_cents=1234,
        direction="outflow",
        account_reference="001:123",
    )
    return ReconciliationMatch.objects.get(transaction__statement=statement), entry


@pytest.mark.django_db
@pytest.mark.parametrize("direction", ["", "C", "D", "inflow", "1"])
def test_unknown_or_opposite_direction_cannot_be_confirmed(match_and_entry, direction: str) -> None:
    match, entry = match_and_entry
    entry.direction = direction
    entry.save()
    with pytest.raises(ValueError, match="natureza"):
        confirm_reconciliation_match(match=match, accounting_entry=entry)
    match.refresh_from_db()
    assert match.status != "matched"


@pytest.mark.django_db
@pytest.mark.parametrize("account_reference", ["", "001:999", "002:123"])
def test_missing_or_wrong_account_cannot_be_confirmed(
    match_and_entry, account_reference: str
) -> None:
    match, entry = match_and_entry
    entry.account_reference = account_reference
    entry.save()
    with pytest.raises(ValueError, match="conta da fonte"):
        confirm_reconciliation_match(match=match, accounting_entry=entry)


@pytest.mark.django_db
@pytest.mark.parametrize("kind", ["dominio_local_agent", "dominio_web_backup"])
def test_bank_mirror_never_becomes_ledger_proof(match_and_entry, kind: str) -> None:
    match, entry = match_and_entry
    entry.data_source.kind = kind
    entry.data_source.save()
    with pytest.raises(ValueError, match="não comprova"):
        confirm_reconciliation_match(match=match, accounting_entry=entry)
    mirror = DominioBankEntry.objects.create(
        organization=entry.organization,
        company=entry.company,
        source_id="001|2|3",
        occurred_on=entry.occurred_on,
        amount_cents=entry.amount_cents,
    )
    with pytest.raises(ValueError, match="não comprova"):
        confirm_reconciliation_match(match=match, dominio_entry=mirror)


@pytest.mark.django_db
def test_confirmation_is_idempotent_and_cannot_consume_candidate_twice(match_and_entry) -> None:
    match, entry = match_and_entry
    confirm_reconciliation_match(match=match, accounting_entry=entry)
    count = AuditEvent.objects.filter(action="hub.reconciliation.match_confirmed").count()
    confirm_reconciliation_match(match=match, accounting_entry=entry)
    assert AuditEvent.objects.filter(action="hub.reconciliation.match_confirmed").count() == count
    statement, _ = import_ofx(
        organization=entry.organization,
        company=entry.company,
        filename="outro.ofx",
        content=OFX.replace(b"fit-1", b"fit-2"),
    )
    another = ReconciliationMatch.objects.get(transaction__statement=statement)
    with pytest.raises(ValueError, match="já foi utilizado"):
        confirm_reconciliation_match(match=another, accounting_entry=entry)
    assert ReconciliationMatch.objects.filter(status="matched").count() == 1


@pytest.mark.django_db
def test_stale_candidate_is_reloaded_before_confirmation(match_and_entry) -> None:
    match, entry = match_and_entry
    AccountingEntry.objects.filter(pk=entry.pk).update(amount_cents=999)
    with pytest.raises(ValueError, match="não corresponde"):
        confirm_reconciliation_match(match=match, accounting_entry=entry)


@pytest.mark.django_db
def test_pre_migration_overlap_is_detected_without_rewriting_history(
    company: ClientCompany,
) -> None:
    statement, _ = import_ofx(
        organization=company.organization,
        company=company,
        filename="antigo.ofx",
        content=OFX,
    )
    OfxTransactionIdentity.objects.all().delete()  # historical rows predate this identity registry
    with pytest.raises(OfxParseError, match="sobreposição"):
        import_ofx(
            organization=company.organization,
            company=company,
            filename="novo.ofx",
            content=OFX + b"\n",
        )
    assert statement.content_hash == hashlib.sha256(OFX).hexdigest()
    assert statement.transactions.count() == 1


@pytest.mark.django_db(transaction=True)
def test_postgres_simultaneous_confirmations_cannot_reuse_candidate(company: ClientCompany) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connection, connections

    if connection.vendor != "postgresql":
        pytest.skip("Travas de alocação exigem PostgreSQL com conexões independentes.")
    pairs = []
    for fitid in [b"fit-1", b"fit-2"]:
        statement, _ = import_ofx(
            organization=company.organization,
            company=company,
            filename="extrato.ofx",
            content=OFX.replace(b"fit-1", fitid),
        )
        pairs.append(ReconciliationMatch.objects.get(transaction__statement=statement).pk)
    source = DataSource.objects.create(
        organization=company.organization,
        kind="other_manual",
        label="Razão independente",
    )
    entry = AccountingEntry.objects.create(
        organization=company.organization,
        company=company,
        data_source=source,
        external_key="ledger-1",
        occurred_on=date(2026, 9, 12),
        amount_cents=1234,
        direction="outflow",
        account_reference="001:123",
    )
    barrier = Barrier(2)

    def confirm(match_id):
        connections.close_all()
        try:
            match = ReconciliationMatch.objects.get(pk=match_id)
            selected = AccountingEntry.objects.get(pk=entry.pk)
            barrier.wait(timeout=10)
            try:
                confirm_reconciliation_match(match=match, accounting_entry=selected)
                return "confirmed"
            except ValueError:
                return "refused"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(confirm, pairs)) == ["confirmed", "refused"]
    assert ReconciliationMatch.objects.filter(status="matched").count() == 1


@pytest.mark.django_db(transaction=True)
def test_postgres_simultaneous_overlapping_uploads_are_atomic(company: ClientCompany) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connection, connections

    if connection.vendor != "postgresql":
        pytest.skip("Travas de identidade exigem PostgreSQL com conexões independentes.")
    barrier = Barrier(2)

    def upload(content):
        connections.close_all()
        try:
            selected_company = ClientCompany.objects.get(pk=company.pk)
            barrier.wait(timeout=10)
            try:
                import_ofx(
                    organization=selected_company.organization,
                    company=selected_company,
                    filename="extrato.ofx",
                    content=content,
                )
                return "imported"
            except OfxParseError:
                return "refused"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(upload, [OFX, OFX + b"\n"])) == ["imported", "refused"]
    assert BankStatementImport.objects.count() == BankTransaction.objects.count() == 1
    assert OfxTransactionIdentity.objects.count() == 1


@pytest.mark.django_db
def test_historical_audit_reports_unsafe_decision_without_mutating_it(match_and_entry) -> None:
    import json
    from io import StringIO

    from django.core.management import call_command

    match, entry = match_and_entry
    entry.direction = "D"
    entry.account_reference = ""
    entry.save()
    match.accounting_entry = entry
    match.status = "matched"
    match.save()
    events_before = AuditEvent.objects.count()
    result = StringIO()
    call_command("audit_ofx_integrity", organization=str(entry.organization_id), stdout=result)
    report = json.loads(result.getvalue())
    assert report["issues"]["unknown_or_incompatible_direction"] == 1
    assert report["issues"]["missing_or_incompatible_account"] == 1
    assert report["homologated"] is False and report["read_only"] is True
    match.refresh_from_db()
    assert match.status == "matched" and match.accounting_entry_id == entry.pk
    assert AuditEvent.objects.count() == events_before


@pytest.mark.django_db(transaction=True)
def test_postgres_rebuild_and_confirmation_preserve_human_decision(company: ClientCompany) -> None:
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connection, connections

    from apps.hub.reconciliation import rebuild_reconciliation_matches

    if connection.vendor != "postgresql":
        pytest.skip("Reconstrução concorrente exige PostgreSQL com conexões independentes.")
    statement, _ = import_ofx(
        organization=company.organization,
        company=company,
        filename="extrato.ofx",
        content=OFX,
    )
    match = ReconciliationMatch.objects.get(transaction__statement=statement)
    source = DataSource.objects.create(
        organization=company.organization,
        kind="other_manual",
        label="Razão independente",
    )
    entry = AccountingEntry.objects.create(
        organization=company.organization,
        company=company,
        data_source=source,
        external_key="ledger-1",
        occurred_on=date(2026, 9, 12),
        amount_cents=1234,
        direction="outflow",
        account_reference="001:123",
    )
    barrier = Barrier(2)

    def act(kind):
        connections.close_all()
        try:
            barrier.wait(timeout=10)
            if kind == "confirm":
                confirm_reconciliation_match(
                    match=ReconciliationMatch.objects.get(pk=match.pk),
                    accounting_entry=AccountingEntry.objects.get(pk=entry.pk),
                )
            else:
                rebuild_reconciliation_matches(organization=company.organization, company=company)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(act, ["confirm", "rebuild"]))
    match.refresh_from_db()
    assert match.status == "matched" and match.is_manual and match.accounting_entry_id == entry.pk
