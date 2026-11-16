from __future__ import annotations

import hashlib
import io
import json
from copy import deepcopy

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import IntegrityError, connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from tests.test_portfolio_readiness import encode, profiles

from apps.audit.models import AuditEvent
from apps.hub.account_candidates import (
    SOURCE_FIELDS,
    AccountCandidateImportError,
    import_account_candidates,
    preview_account_candidates,
)
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    LedgerAccount,
    ReconciliationAccountCandidate,
    ReconciliationSourceFile,
)
from apps.intelligence.models import NativeLedgerCollection, NativeTitleCollection
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def sources(organization):
    portfolio, accounts = profiles()
    for row in portfolio["snapshot"]["companies"]:
        ClientCompany.objects.create(
            organization=organization,
            dominio_code=str(row["company_code"]),
            name=f"Synthetic company {row['company_code']}",
            dominio_status="A",
        )
    # More than one company/account; source ordering cannot change the worksheet numbering.
    accounts["snapshot"]["configured_accounts"].append(
        {
            "company_code": 212,
            "chart_company_code": 212,
            "account_code": 8,
            "account_type_raw": "A",
            "account_status_raw": "A",
            "catalogue_matches": 1,
        }
    )
    return portfolio, accounts


def run_import(organization, sources, **kwargs):
    return import_account_candidates(
        organization=organization,
        portfolio_raw=encode(sources[0]),
        accounts_raw=encode(sources[1]),
        request_reference="D-365 synthetic technical execution",
        **kwargs,
    )


def test_preview_and_default_import_write_nothing_including_audit(organization, sources):
    before = AuditEvent.objects.count()
    with CaptureQueriesContext(connection) as queries:
        preview = preview_account_candidates(
            organization=organization,
            portfolio_raw=encode(sources[0]),
            accounts_raw=encode(sources[1]),
        )
        default = run_import(organization, sources)
    assert preview == default
    assert preview["company_count"] == preview["candidate_count"] == preview["to_create"] == 3
    assert preview["companies_with_candidates"] == 2
    assert not preview["created"] and not preview["existing"] and not preview["applied"]
    assert not ReconciliationAccountCandidate.objects.exists()
    assert AuditEvent.objects.count() == before
    assert not [
        q for q in queries if q["sql"].lstrip().split()[0].upper() in {"INSERT", "UPDATE", "DELETE"}
    ]
    json.dumps(preview)  # The private preview is serializable without special encoders.


def test_apply_keeps_provenance_raw_flags_and_human_fields_unknown(organization, sources):
    report = run_import(organization, sources, apply=True)
    assert report["created"] == 3 and report["applied"]
    candidates = list(ReconciliationAccountCandidate.objects.all())
    assert [item.case_reference for item in candidates] == ["C01", "C02", "C03"]
    assert [item.source_key for item in candidates] == ["212:212:8", "213:99:8", "213:99:9"]
    for item in candidates:
        assert item.company.dominio_code == str(item.source_company_code)
        assert item.source_file_sha256 == hashlib.sha256(encode(sources[1])).hexdigest()
        assert item.portfolio_file_sha256 == hashlib.sha256(encode(sources[0])).hexdigest()
        assert item.source_observed_at.isoformat() == "2026-11-13T18:00:00+00:00"
        assert item.evidence["candidate"]["account_type_raw"] == "A"
        assert item.evidence["candidate"]["account_status_raw"] == "A"
        assert all(value is None for value in item.evidence["candidate"]["review"].values())
        assert item.state == "pending" and item.financial_account_id is None
        assert item.reviewed_by_id is item.reviewed_at is None
        assert item.review_data == {} and item.review_evidence == ""
        assert not item.evidence["candidate"]["ready_for_financial_capture"]
    assert not FinancialAccount.objects.exists() and not LedgerAccount.objects.exists()
    assert not ReconciliationSourceFile.objects.exists()
    assert (
        not NativeLedgerCollection.objects.exists() and not NativeTitleCollection.objects.exists()
    )
    event = AuditEvent.objects.get(action="hub.reconciliation.account_candidates.imported")
    assert event.actor_id is None
    assert event.metadata["request_reference"] == "D-365 synthetic technical execution"
    assert event.metadata["manifest_sha256"] == report["manifest_sha256"]
    assert not event.metadata["human_review_performed"]
    assert not event.metadata["financial_collection_enabled"]
    assert "account_reference" not in json.dumps(event.metadata)
    assert "Synthetic company" not in json.dumps(event.metadata)


def test_existing_operational_accounts_remain_unlinked_and_unchanged(organization, sources):
    company = ClientCompany.objects.get(organization=organization, dominio_code="212")
    FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Preserved bank",
        account_reference="001:123",
        ledger_code="8",
    )
    LedgerAccount.objects.create(
        organization=organization, company=company, code="8", name="Preserved ledger"
    )
    before = list(FinancialAccount.objects.values()), list(LedgerAccount.objects.values())
    run_import(organization, sources, apply=True)
    assert before == (list(FinancialAccount.objects.values()), list(LedgerAccount.objects.values()))
    assert not ReconciliationAccountCandidate.objects.exclude(financial_account=None).exists()


@pytest.mark.parametrize("state", ["pending", "linked", "dismissed"])
def test_replay_preserves_candidate_human_review_and_audit(organization, sources, user, state):
    initial = run_import(organization, sources, apply=True)
    candidate = ReconciliationAccountCandidate.objects.first()
    if state != "pending":
        candidate.state = state
        candidate.reviewed_by = user
        candidate.reviewed_at = timezone.now()
        candidate.review_evidence = "Synthetic human evidence"
        candidate.review_data = {"bank_inflow_side": "credit", "source_reviewed": True}
        if state == "linked":
            candidate.financial_account = FinancialAccount.objects.create(
                organization=organization,
                company=candidate.company,
                name="Human linked bank",
                account_reference="001:456",
                ledger_code="8",
            )
        candidate.save()
    before = list(ReconciliationAccountCandidate.objects.order_by("pk").values())
    audit_before = list(AuditEvent.objects.values())
    replay = run_import(organization, sources, apply=True)
    assert replay["created"] == replay["to_create"] == 0 and replay["existing"] == 3
    assert replay["manifest_sha256"] == initial["manifest_sha256"]
    assert before == list(ReconciliationAccountCandidate.objects.order_by("pk").values())
    assert audit_before == list(AuditEvent.objects.values())


@pytest.mark.parametrize(
    "change", ["extra_company", "missing_company", "noncanonical_code", "empty_code"]
)
def test_office_company_set_must_match_original_profile_exactly(organization, sources, change):
    if change == "extra_company":
        ClientCompany.objects.create(organization=organization, name="Extra", dominio_code="999")
    elif change == "missing_company":
        ClientCompany.objects.filter(organization=organization, dominio_code="214").delete()
    else:
        ClientCompany.objects.filter(organization=organization, dominio_code="214").update(
            dominio_code="0214" if change == "noncanonical_code" else ""
        )
    with pytest.raises(AccountCandidateImportError, match="coincidir integralmente"):
        run_import(organization, sources, apply=True)
    assert not ReconciliationAccountCandidate.objects.exists() and not AuditEvent.objects.exists()


def test_equal_source_codes_are_isolated_between_offices(organization, sources):
    other = Organization.objects.create(name="Other synthetic office", slug="other-candidates")
    for code in (212, 213, 214):
        ClientCompany.objects.create(organization=other, name="Other", dominio_code=str(code))
    run_import(organization, sources, apply=True)
    report = run_import(other, sources, apply=True)
    assert report["created"] == 3 and ReconciliationAccountCandidate.objects.count() == 6
    assert (
        not ReconciliationAccountCandidate.objects.filter(organization=other)
        .exclude(company__organization=other)
        .exists()
    )


def test_same_account_code_in_distinct_source_plans_remains_two_candidates(organization, sources):
    row = deepcopy(sources[1]["snapshot"]["configured_accounts"][0])
    row["chart_company_code"] = 98
    sources[1]["snapshot"]["configured_accounts"].append(row)
    sources[1]["snapshot"]["configured_accounts"].reverse()
    report = run_import(organization, sources, apply=True)
    assert report["created"] == 4
    assert [(row["case_reference"], row["source_key"]) for row in report["candidates"]] == [
        ("C01", "212:212:8"),
        ("C02", "213:98:8"),
        ("C03", "213:99:8"),
        ("C04", "213:99:9"),
    ]
    assert not FinancialAccount.objects.exists() and not LedgerAccount.objects.exists()


def test_partial_existing_registration_replays_without_rewriting_retained_candidate(
    organization,
    sources,
):
    run_import(organization, sources, apply=True)
    retained = ReconciliationAccountCandidate.objects.first()
    ReconciliationAccountCandidate.objects.exclude(pk=retained.pk).delete()
    original = ReconciliationAccountCandidate.objects.filter(pk=retained.pk).values().get()
    report = run_import(organization, sources, apply=True)
    assert report["existing"] == 1 and report["created"] == 2
    assert original == ReconciliationAccountCandidate.objects.filter(pk=retained.pk).values().get()


@pytest.mark.parametrize(
    "change",
    ["account_bytes", "portfolio_bytes", "flag", "source_key", "case", "evidence", "omitted"],
)
def test_source_conflict_is_atomic_and_never_overwrites_existing_candidates(
    organization, sources, change
):
    run_import(organization, sources, apply=True)
    portfolio_raw, accounts_raw = map(encode, sources)
    candidate = ReconciliationAccountCandidate.objects.first()
    if change == "account_bytes":
        accounts_raw += b" "
    elif change == "portfolio_bytes":
        portfolio_raw += b" "
    elif change == "flag":
        sources[1]["snapshot"]["configured_accounts"][0]["account_status_raw"] = "I"
        accounts_raw = encode(sources[1])
    elif change == "omitted":
        sources[1]["snapshot"]["configured_accounts"].pop()
        accounts_raw = encode(sources[1])
    else:
        if change == "source_key":
            candidate.source_key = "999:999:999"
        elif change == "case":
            candidate.case_reference = "C99"
        else:
            candidate.evidence = {"changed": True}
        candidate.save()
    before = list(ReconciliationAccountCandidate.objects.order_by("pk").values())
    audit_before = AuditEvent.objects.count()
    with pytest.raises(AccountCandidateImportError):
        import_account_candidates(
            organization=organization,
            portfolio_raw=portfolio_raw,
            accounts_raw=accounts_raw,
            request_reference="D-365",
            apply=True,
        )
    assert before == list(ReconciliationAccountCandidate.objects.order_by("pk").values())
    assert AuditEvent.objects.count() == audit_before


@pytest.mark.parametrize(
    "change", ["duplicate", "outside", "claimed_approval", "foreign_field", "mismatch"]
)
def test_invalid_profile_refuses_whole_batch(organization, sources, change):
    portfolio, accounts = sources
    row = accounts["snapshot"]["configured_accounts"][0]
    if change == "duplicate":
        accounts["snapshot"]["configured_accounts"].append(deepcopy(row))
    elif change == "outside":
        row["company_code"] = 999
    elif change == "claimed_approval":
        accounts["bank_association_approved"] = True
    elif change == "foreign_field":
        row["account_reference"] = "must-not-be-accepted"
    else:
        portfolio["snapshot"]["companies"][0]["configuration_rows"] = 0
        portfolio["snapshot"]["companies"][0]["codi_pad_raw"] = None
    with pytest.raises(AccountCandidateImportError):
        run_import(organization, sources, apply=True)
    assert not ReconciliationAccountCandidate.objects.exists() and not AuditEvent.objects.exists()


def test_audit_failure_rolls_back_every_candidate(organization, sources, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("Synthetic audit failure")

    monkeypatch.setattr("apps.hub.account_candidates.record_event", fail)
    with pytest.raises(RuntimeError, match="Synthetic audit"):
        run_import(organization, sources, apply=True)
    assert not ReconciliationAccountCandidate.objects.exists() and not AuditEvent.objects.exists()


def test_model_checks_identity_and_database_prevents_duplicate_scope(organization, sources):
    run_import(organization, sources, apply=True)
    candidate = ReconciliationAccountCandidate.objects.first()
    values = {field: getattr(candidate, field) for field in SOURCE_FIELDS}
    with transaction.atomic(), pytest.raises(IntegrityError):
        ReconciliationAccountCandidate.objects.create(organization=organization, **values)
    candidate.source_key = "wrong"
    with pytest.raises(ValidationError, match="chave"):
        candidate.clean()
    candidate.source_key = values["source_key"]
    candidate.company = ClientCompany.objects.get(organization=organization, dominio_code="214")
    with pytest.raises(ValidationError, match="Empresa"):
        candidate.clean()


@pytest.mark.parametrize("request_reference", ["", " ", "x" * 241, "D-365\nprivate"])
def test_execution_reference_is_required_without_logging_user_content(
    organization, sources, request_reference
):
    with pytest.raises(AccountCandidateImportError, match="referência técnica"):
        import_account_candidates(
            organization=organization,
            portfolio_raw=encode(sources[0]),
            accounts_raw=encode(sources[1]),
            request_reference=request_reference,
            apply=True,
        )
    assert not ReconciliationAccountCandidate.objects.exists() and not AuditEvent.objects.exists()


def test_cli_defaults_to_preview_and_logs_only_counts_and_digest(organization, sources, tmp_path):
    portfolio, accounts = tmp_path / "portfolio.json", tmp_path / "accounts.json"
    portfolio.write_bytes(encode(sources[0]))
    accounts.write_bytes(encode(sources[1]))
    options = dict(
        organization=str(organization.pk),
        portfolio_file=str(portfolio),
        accounts_file=str(accounts),
        request_reference="D-365",
    )
    output = io.StringIO()
    call_command("import_reconciliation_accounts", **options, stdout=output)
    preview = json.loads(output.getvalue())
    assert preview["to_create"] == 3 and not preview["applied"]
    assert not ReconciliationAccountCandidate.objects.exists()
    for forbidden in ("candidates", "sources", "source_key", "account_code", "company_id"):
        assert forbidden not in preview
    output = io.StringIO()
    call_command("import_reconciliation_accounts", **options, apply=True, stdout=output)
    assert json.loads(output.getvalue())["created"] == 3


@pytest.mark.parametrize(
    "failure", ["missing_file", "unknown_office", "invalid_json", "source_conflict"]
)
def test_cli_errors_do_not_leak_files_or_make_partial_changes(
    organization, sources, tmp_path, failure
):
    portfolio, accounts = tmp_path / "portfolio.json", tmp_path / "private-account.json"
    portfolio.write_bytes(encode(sources[0]))
    accounts.write_bytes(encode(sources[1]))
    if failure == "missing_file":
        accounts.unlink()
    elif failure == "invalid_json":
        accounts.write_bytes(b'{"private_name":"DO-NOT-PRINT"}')
    elif failure == "source_conflict":
        run_import(organization, sources, apply=True)
        accounts.write_bytes(encode(sources[1]) + b" ")
    before = list(ReconciliationAccountCandidate.objects.values())
    output = io.StringIO()
    with pytest.raises(CommandError) as error:
        call_command(
            "import_reconciliation_accounts",
            organization="not-a-uuid" if failure == "unknown_office" else str(organization.pk),
            portfolio_file=str(portfolio),
            accounts_file=str(accounts),
            request_reference="D-365",
            apply=True,
            stdout=output,
        )
    assert "DO-NOT-PRINT" not in str(error.value) and str(tmp_path) not in str(error.value)
    assert output.getvalue() == ""
    assert before == list(ReconciliationAccountCandidate.objects.values())


@pytest.mark.django_db(transaction=True)
def test_concurrent_replay_creates_one_candidate_set_and_audit(organization, sources):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    if connection.vendor != "postgresql":
        pytest.skip("Candidate import serialization requires PostgreSQL row locks.")
    barrier = Barrier(2)

    def apply():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return run_import(organization, sources, apply=True)["created"]
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: apply(), range(2)))
    assert sorted(results) == [0, 3]
    assert ReconciliationAccountCandidate.objects.count() == 3
    assert (
        AuditEvent.objects.filter(action="hub.reconciliation.account_candidates.imported").count()
        == 1
    )
