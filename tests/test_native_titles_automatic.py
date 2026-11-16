"""Company-wide fiscal capture retains raw facts without a bank or manual counts."""

from copy import deepcopy
from datetime import date
from hashlib import sha256
from pathlib import Path
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    JournalEntry,
    ProductModule,
    ReconciliationSourceFile,
    ReconciliationTitleAllocation,
    ReconciliationTitleSnapshot,
)
from apps.intelligence.models import CompanyTitleCollection, NativeTitleCollection
from apps.intelligence.native_title_comparison import NativeTitleComparisonError, _load
from apps.intelligence.native_title_contract import (
    AUTOMATIC_VERSION,
    FAMILIES,
    MAX_ROWS,
    VERSION,
    canonical_hash,
    contract_hash,
    manifest,
    review_summary,
    validate_scope,
    validate_snapshot,
)
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantContract
from test_native_ledger import post
from test_native_titles import complete, encode, sample
from test_native_titles import fiscal as fiscal_fixture

fiscal_source = fiscal_fixture

pytestmark = pytest.mark.django_db
CAPABILITY = {"version": "1.0.9", "company_scope": True, "automatic_counts": True}


def automatic_sample(capture_id=None, company=37, start="2019-12-01"):
    scope, snapshot = sample(capture_id)
    del scope["comparison_bank_account_code"]
    del scope["expected_counts"]
    year, month = date.fromisoformat(start).year, date.fromisoformat(start).month
    end = date(year + (month == 12), month % 12 + 1, 1).isoformat()
    scope.update(company_code=company, period_start=start, period_end_exclusive=end)
    snapshot.update(version=AUTOMATIC_VERSION, scope_revision=canonical_hash(scope))
    for family in snapshot["families"]:
        spec = manifest()["families"][family["name"]]
        for kind in ("installments", "payments", "accounting_links"):
            for row in family[kind]:
                for field, value in list(row.items()):
                    if value == "2026-09-12":
                        row[field] = start[:8] + "12"
                if kind == "accounting_links":
                    row["fili_lan"] = company
                else:
                    row["codi_emp"] = company
                if kind == "installments":
                    row[spec["due_field"]] = (
                        end[:8] + "02" if family["name"] == "saidas" else start[:8] + "20"
                    )
    return validate_scope(scope), snapshot


@pytest.fixture
def company_capture(fiscal_source):
    agent, _, user, legacy, _, _ = fiscal_source
    legacy.delete()
    company = ClientCompany.objects.create(
        organization=agent.organization, name="Empresa sem conta", dominio_code="37"
    )
    scope, data = automatic_sample()
    job = CompanyTitleCollection.objects.create(
        id=scope["capture_id"],
        organization=agent.organization,
        company=company,
        agent=agent,
        requested_by=user,
        evidence_reference="Solicitação sintética pela tela",
        request_key=uuid4(),
        batch_key=uuid4(),
        scope=scope,
        scope_revision=canonical_hash(scope),
        contract_hash=contract_hash(),
    )
    return agent, company, user, job, data


def test_company_without_account_captures_historical_sources_and_preserves_money(company_capture):
    agent, company, _, job, data = company_capture
    assert not FinancialAccount.objects.filter(company=company).exists()
    pending = post(agent, "agent-v2-titles-next", CAPABILITY)
    assert pending.status_code == 200, pending.content
    assert pending.json()["job"]["version"] == AUTOMATIC_VERSION
    assert pending.json()["job"]["scope"] == job.scope
    job.refresh_from_db()
    assert job.claimed_at is not None
    response = complete(agent, job, data)
    assert response.status_code == 200, response.content
    job.refresh_from_db()
    source = job.source_file
    assert source.company == company and source.financial_account is None
    assert source.origin == "obligation" and source.kind == "json"
    with source.content.open("rb") as stream:
        content = stream.read()
    assert content == encode(data)
    assert b'"-2.00"' in content and b'"0.00"' in content and b"0001/A  " in content
    assert complete(agent, job, data).json() == response.json()
    assert job.result["requires_semantic_review"] is True
    assert job.result["bank_linkage"] == "unproven"
    assert ReconciliationSourceFile.objects.count() == 1
    assert not NativeTitleCollection.objects.exists()
    for model in [JournalEntry, ReconciliationTitleSnapshot, ReconciliationTitleAllocation]:
        assert not model.objects.exists()


def test_old_agent_cannot_receive_company_jobs_and_capability_records_real_request(company_capture):
    agent, _, _, job, _ = company_capture
    response = post(agent, "agent-v2-titles-next", {"version": "1.0.9"})
    assert response.status_code == 200 and response.json()["job"] is None
    job.refresh_from_db()
    assert job.claimed_at is None
    agent.refresh_from_db()
    assert agent.title_capabilities["automatic_counts"] is False
    assert agent.title_capabilities_observed_at is not None
    assert post(agent, "agent-v2-titles-next", CAPABILITY).json()["job"]["id"] == str(job.pk)
    agent.refresh_from_db()
    assert agent.title_capabilities == CAPABILITY


@pytest.mark.parametrize("value", [1, "true", False, None])
def test_capability_requires_real_booleans(company_capture, value):
    agent, _, _, job, _ = company_capture
    response = post(agent, "agent-v2-titles-next", {**CAPABILITY, "automatic_counts": value})
    assert response.status_code == 400
    job.refresh_from_db()
    agent.refresh_from_db()
    assert job.claimed_at is None and agent.title_capabilities == {}


@pytest.mark.parametrize("change", ["company", "role", "inactive", "agent_scope", "hash"])
def test_delivery_and_receipt_recheck_current_authority(company_capture, change):
    agent, company, user, job, data = company_capture
    assert post(agent, "agent-v2-titles-next", CAPABILITY).status_code == 200
    if change == "company":
        company.dominio_code = "38"
        company.save(update_fields=["dominio_code"])
    elif change == "role":
        Membership.objects.filter(user=user, organization=agent.organization).update(role="viewer")
    elif change == "inactive":
        company.active = False
        company.save(update_fields=["active"])
    elif change == "agent_scope":
        agent.sync_scope["revision"] = "0" * 64
        agent.save(update_fields=["sync_scope"])
    else:
        job.scope_revision = "0" * 64
        job.save(update_fields=["scope_revision"])
    assert post(agent, "agent-v2-titles-next", CAPABILITY).status_code in (401, 409)
    assert complete(agent, job, data).status_code in (401, 409)
    assert not ReconciliationSourceFile.objects.exists()


def test_invalid_oldest_job_does_not_starve_authorized_company(company_capture):
    agent, company, user, job, _ = company_capture
    job.scope_revision = "0" * 64
    job.save(update_fields=["scope_revision"])
    scope, _ = automatic_sample(start="2019-11-01")
    valid = CompanyTitleCollection.objects.create(
        id=scope["capture_id"],
        organization=agent.organization,
        company=company,
        agent=agent,
        requested_by=user,
        evidence_reference="Outro mês",
        request_key=uuid4(),
        batch_key=uuid4(),
        scope=scope,
        scope_revision=canonical_hash(scope),
        contract_hash=contract_hash(),
    )
    response = post(agent, "agent-v2-titles-next", CAPABILITY)
    assert response.status_code == 200, response.content
    assert response.json()["job"]["id"] == str(valid.pk)
    assert response.json()["review_required"] is True


def test_transient_failure_advances_other_company_jobs_and_preserves_identity(company_capture):
    agent, company, user, job, _ = company_capture
    scope, _ = automatic_sample(start="2019-11-01")
    other = CompanyTitleCollection.objects.create(
        id=scope["capture_id"],
        organization=agent.organization,
        company=company,
        agent=agent,
        requested_by=user,
        evidence_reference="Outro mês",
        request_key=uuid4(),
        batch_key=uuid4(),
        scope=scope,
        scope_revision=canonical_hash(scope),
        contract_hash=contract_hash(),
    )
    assert post(agent, "agent-v2-titles-next", CAPABILITY).json()["job"]["id"] == str(job.pk)
    response = post(
        agent,
        "agent-v2-titles-failure",
        {
            "scope_revision": job.scope_revision,
            "contract_hash": job.contract_hash,
            "code": "source_changed",
        },
        job=job,
    )
    assert response.status_code == 200 and response.json()["state"] == "queued"
    assert post(agent, "agent-v2-titles-next", CAPABILITY).json()["job"]["id"] == str(other.pk)


def test_legacy_cli_cannot_enqueue_company_envelope_in_legacy_table(fiscal_source):
    _, _, _, _, _, options = fiscal_source

    scope, _ = automatic_sample()
    Path(options["scope"]).write_bytes(encode(scope))
    with pytest.raises(CommandError):
        call_command("queue_contad_native_titles", **options, allow_financial_capture=True)
    assert NativeTitleCollection.objects.count() == 1
    assert not CompanyTitleCollection.objects.exists()


def test_ambiguous_capture_id_between_tables_is_never_delivered_or_completed(fiscal_source):
    agent, account, user, legacy, _, _ = fiscal_source
    scope, data = automatic_sample(capture_id=legacy.pk, company=212)
    job = CompanyTitleCollection.objects.create(
        id=legacy.pk,
        organization=agent.organization,
        company=account.company,
        agent=agent,
        requested_by=user,
        evidence_reference="Identidade sintética ambígua",
        request_key=uuid4(),
        batch_key=uuid4(),
        scope=scope,
        scope_revision=canonical_hash(scope),
        contract_hash=contract_hash(),
    )
    assert post(agent, "agent-v2-titles-next", CAPABILITY).status_code == 409
    assert complete(agent, job, data).status_code == 404
    assert not ReconciliationSourceFile.objects.exists()


def test_loader_rejects_cross_organization_company_even_for_member_of_both(company_capture):
    agent, company, user, job, data = company_capture
    assert complete(agent, job, data).status_code == 200
    other = Organization.objects.create(name="Outro escritório", slug="other-capture-office")
    Membership.objects.create(organization=other, user=user, role="owner")
    ProductModule.objects.create(organization=other, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=other, status="active", selected_modules=["reconciliation"]
    )
    company.organization = other
    company.save(update_fields=["organization"])
    with pytest.raises((NativeTitleComparisonError, PermissionDenied)):
        _load(job.pk, agent.organization_id, user)


def test_loader_rejects_ambiguous_capture_even_if_only_one_table_is_captured(company_capture):
    agent, _, user, job, data = company_capture
    assert complete(agent, job, data).status_code == 200
    scope, _ = sample(job.pk)
    NativeTitleCollection.objects.create(
        id=job.pk,
        organization=agent.organization,
        agent=agent,
        financial_account=FinancialAccount.objects.get(organization=agent.organization),
        requested_by=user,
        evidence_reference="Identidade ambígua sintética",
        scope=scope,
        scope_revision=canonical_hash(scope),
        contract_hash=contract_hash(),
        state="queued",
    )
    with pytest.raises(NativeTitleComparisonError):
        _load(job.pk, agent.organization_id, user)


def test_company_table_cannot_disguise_legacy_bank_scope_as_company_source(company_capture):
    agent, _, user, job, data = company_capture
    assert complete(agent, job, data).status_code == 200
    job.refresh_from_db()
    scope, legacy_data = sample(job.pk)
    content = encode(legacy_data)
    source = job.source_file
    source.content.save(source.original_filename, ContentFile(content), save=False)
    source.content_hash, source.size_bytes = sha256(content).hexdigest(), len(content)
    source.company = FinancialAccount.objects.get(organization=agent.organization).company
    source.save()
    job.company = source.company
    job.scope, job.scope_revision = scope, canonical_hash(scope)
    job.content_hash, job.result = source.content_hash, review_summary(legacy_data)
    job.save(update_fields=["company", "scope", "scope_revision", "content_hash", "result"])
    with pytest.raises(NativeTitleComparisonError):
        _load(job.pk, agent.organization_id, user)


def test_company_intake_rollback_removes_owned_file_and_requires_retained_original(
    company_capture,
    monkeypatch,
    settings,
):
    agent, _, _, job, data = company_capture

    def broken_audit(**kwargs):
        raise RuntimeError("synthetic audit failure")

    with monkeypatch.context() as patch:
        patch.setattr("apps.intelligence.native_titles.record_event", broken_audit)
        with pytest.raises(RuntimeError, match="synthetic audit failure"):
            complete(agent, job, data)
    job.refresh_from_db()
    assert job.state == "queued" and job.source_file is None
    assert not ReconciliationSourceFile.objects.exists()
    assert not [p for p in Path(settings.MEDIA_ROOT).rglob("*") if p.is_file()]
    assert complete(agent, job, data).status_code == 200
    job.refresh_from_db()
    source = job.source_file
    source.content.delete(save=False)
    assert complete(agent, job, data).status_code == 409
    assert ReconciliationSourceFile.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_company_receipts_keep_one_private_source_and_audit(company_capture):
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections, connection

    from apps.audit.models import AuditEvent

    if connection.vendor != "postgresql":
        pytest.skip("Requires independent PostgreSQL transactions and row locks")
    agent, _, _, job, data = company_capture

    def send():
        close_old_connections()
        try:
            response = complete(agent, job, data)
            return response.status_code, response.json()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        responses = list(pool.map(lambda _: send(), range(2)))
    assert responses[0] == responses[1] and responses[0][0] == 200
    assert ReconciliationSourceFile.objects.count() == 1
    assert (
        AuditEvent.objects.filter(
            action="intelligence.native_titles_captured", target_id=str(job.pk)
        ).count()
        == 1
    )
    assert not ReconciliationTitleSnapshot.objects.exists()


@pytest.mark.parametrize(
    "start,end",
    [
        ("0001-01-01", "0001-02-01"),
        ("2020-02-01", "2020-03-01"),
        ("9998-12-01", "9999-01-01"),
    ],
)
def test_supported_month_boundaries_accept_no_human_counts(start, end):
    scope, data = automatic_sample(start=start)
    assert scope["period_end_exclusive"] == end
    assert validate_snapshot(encode(data), scope) == data


@pytest.mark.parametrize(
    "field,value",
    [
        ("company_code", 0),
        ("company_code", True),
        ("company_code", 37.0),
        ("company_code", "37"),
        ("company_code", 2**31),
        ("period_start", "2019-12-02"),
        ("period_start", "2019-2-01"),
        ("period_start", "9999-12-01"),
        ("period_end_exclusive", "2020-02-01"),
        ("comparison_bank_account_code", 8),
        ("expected_counts", {}),
    ],
)
def test_invalid_automatic_scope_is_rejected(field, value):
    scope, _ = automatic_sample()
    scope[field] = value
    with pytest.raises(ValueError):
        validate_scope(scope)


@pytest.mark.parametrize(
    "field",
    [
        "due_installments",
        "selected_installments",
        "payments",
        "accounting_links",
        "missing_headers",
        "missing_installments",
    ],
)
def test_source_counts_must_match_observed_rows_without_expected_counts(field):
    scope, data = automatic_sample()
    data["families"][0]["control"][field] += 1
    with pytest.raises(ValueError):
        validate_snapshot(encode(data), scope)


@pytest.mark.parametrize(
    "change", ["duplicate", "wrong_company", "foreign_payment", "limit", "version"]
)
def test_v2_independently_checks_source_keys_limits_and_version(change):
    scope, data = automatic_sample()
    family = data["families"][0]
    if change == "duplicate":
        family["payments"].append(deepcopy(family["payments"][0]))
        family["control"]["payments"] += 1
    elif change == "wrong_company":
        family["installments"][0]["codi_emp"] = 38
    elif change == "foreign_payment":
        spec = manifest()["families"][FAMILIES[0]]
        family["payments"][0][spec["payment_date_field"]] = "2020-01-01"
    elif change == "limit":
        family["control"]["payments"] = MAX_ROWS + 1
    else:
        data["version"] = VERSION
    with pytest.raises(ValueError):
        validate_snapshot(encode(data), scope)
