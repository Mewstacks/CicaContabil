"""Actual discovery import followed by scoped, minimal human confirmation."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from types import SimpleNamespace
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connection
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.account_discovery import prepared_account_facts
from apps.hub.account_discovery_review import DiscoveryReviewError, confirm_discovered_account
from apps.hub.ledger_requests import (
    LedgerRequestError,
    discovery_mapping_month_allowed,
    ledger_request_context,
    request_ledger,
    save_ledger_mapping,
    validate_job_mapping,
)
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    LedgerAccount,
    ProductModule,
    ReconciliationAccountCandidate,
    ReconciliationCompanyDiscovery,
    ReconciliationDiscoveredChartAccount,
    ReconciliationLedgerMapping,
)
from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantContract
from test_account_candidates import run_import
from test_account_candidates import sources as sources_fixture
from test_account_discovery import discovery_profile, run_discovery

sources = sources_fixture
pytestmark = pytest.mark.django_db


def prepare_review(organization, sources, user, *, profile=None, month="2026-09"):
    profile = profile or discovery_profile(sources)
    run_import(organization, sources, apply=True)
    run_discovery(organization, sources, profile, apply=True)
    coverage = ReconciliationCompanyDiscovery.objects.get(
        organization=organization,
        source_company_code=212,
    )
    chart = ReconciliationDiscoveredChartAccount.objects.get(
        organization=organization,
        chart_company_code=212,
        account_code=8,
    )
    prepared = prepared_account_facts(coverage, chart, month=month)
    values = dict(
        bank_code="001",
        account_reference="0001:000123-4",
        bank_inflow_side="debit",
        branch_code=212,
        bank_association_confirmed=True,
        account_active_and_postable=True,
        chart_owner_confirmed=True,
        branch_scope_confirmed=True,
    )
    return dict(
        company_discovery=coverage,
        chart_account=chart,
        month=month,
        actor=user,
        authorized_companies=ClientCompany.objects.filter(organization=organization),
        expected_revision=prepared["revision"],
        confirmed_data={key: values[key] for key in prepared["pending_fields"]},
    )


@pytest.fixture
def access(organization, user, membership):
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization,
        status="active",
        selected_modules=["reconciliation"],
    )
    return organization


@pytest.fixture
def review(access, sources, user):
    return prepare_review(access, sources, user)


def snapshot():
    return {
        model.__name__: list(model.objects.order_by("pk").values())
        for model in (
            FinancialAccount,
            LedgerAccount,
            ReconciliationLedgerMapping,
            ReconciliationAccountCandidate,
            NativeLedgerCollection,
            AuditEvent,
        )
    }


def confirmed(review):
    return confirm_discovered_account(**review)


@pytest.mark.parametrize(
    "name",
    [
        " Nome\tcom\ncontrole\r ",
        "\u200bFormato\u200d",
        "Privado\ue000",
        "Suplementar\U0001f600",
        "Controle\x01literal",
        "\U0001f600" * 75,
    ],
)
def test_source_name_unicode_remains_literal_through_models_hashes_and_replay(
    access,
    sources,
    user,
    name,
):
    profile = discovery_profile(sources)
    for table in ("configured_accounts", "chart_accounts"):
        for row in profile["snapshot"][table]:
            if row["chart_company_code"] == 212 and row["account_code"] == 8:
                row["account_name_raw"] = name
    options = prepare_review(access, sources, user, profile=profile)
    result = confirmed(options)
    account = result["financial_account"]
    account.refresh_from_db()
    assert account.name == name
    account.full_clean()
    ledger = LedgerAccount.objects.get(company=account.company, code="8")
    assert ledger.name == name
    ledger.full_clean()
    assert discovery_mapping_month_allowed(account, result["mapping"], "2026-09")
    assert confirmed(options)["replayed"]


def test_dismissed_candidate_is_not_reactivated_or_reported_as_branch_error(review):
    candidate = ReconciliationAccountCandidate.objects.get(
        company=review["company_discovery"].company, chart_company_code=212, account_code=8
    )
    candidate.state = "dismissed"
    candidate.review_evidence = "Synthetic prior decision"
    candidate.save()
    prepared = prepared_account_facts(
        review["company_discovery"], review["chart_account"], month="2026-09"
    )
    before = snapshot()
    with pytest.raises(DiscoveryReviewError, match="descartada"):
        confirmed({**review, "expected_revision": prepared["revision"]})
    assert snapshot() == before


def test_minimal_confirmation_preserves_source_and_candidates_and_audits_only_real_fields(review):
    before = list(ReconciliationAccountCandidate.objects.values())
    result = confirmed(review)
    account, mapping = result["financial_account"], result["mapping"]
    assert result["created"] and not result["replayed"]
    assert account.name == review["chart_account"].row["account_name_raw"]
    assert account.bank_code == "001" and account.account_reference == "0001:000123-4"
    assert account.ledger_code == "8" and LedgerAccount.objects.get().nature == ""
    assert list(ReconciliationAccountCandidate.objects.values()) == before
    assert mapping.reviewed_by_id == review["actor"].pk and mapping.reviewed_at
    proof = mapping.provenance
    assert proof["period_scope"]["allowed_months"] == ["2026-09"]
    assert proof["confirmed_fields"] == sorted(review["confirmed_data"])
    assert "name" in proof["source_fields"] and "bank_code" not in proof["source_fields"]
    assert not set(proof["source_fields"]) & set(proof["confirmed_fields"])
    event = AuditEvent.objects.get(action="hub.reconciliation.discovered_account_confirmed")
    assert event.actor_id == review["actor"].pk
    assert "000123" not in str(event.metadata) and account.name not in str(event.metadata)
    assert not NativeLedgerCollection.objects.exists()


@pytest.mark.parametrize(
    "field,value",
    [
        ("bank_association_confirmed", False),
        ("bank_association_confirmed", "true"),
        ("account_active_and_postable", False),
        ("bank_code", ""),
        ("bank_code", "1" * 21),
        ("account_reference", "bad\nreference"),
        ("account_reference", "x" * 161),
        ("bank_inflow_side", "either"),
        ("bank_inflow_side", []),
        ("name", "client override"),
        ("chart_company_code", 999),
        ("account_code", 999),
        ("evidence_reference", "x" * 1001),
    ],
)
def test_service_validates_missing_fields_and_rejects_source_overrides(review, field, value):
    review["confirmed_data"][field] = value
    before = snapshot()
    with pytest.raises(DiscoveryReviewError):
        confirmed(review)
    assert snapshot() == before


def test_replay_preserves_first_actor_and_refuses_changed_submission(review):
    first = confirmed(review)
    actor = User.objects.create_user("second@example.test", "synthetic-only")
    Membership.objects.create(
        organization=review["company_discovery"].organization,
        user=actor,
        role="owner",
    )
    review["actor"] = actor
    before = snapshot()
    replay = confirmed(review)
    assert (
        replay["replayed"] and replay["mapping"].reviewed_by_id == first["mapping"].reviewed_by_id
    )
    assert snapshot() == before
    review["confirmed_data"]["account_reference"] = "0001:changed"
    with pytest.raises(DiscoveryReviewError):
        confirmed(review)
    assert snapshot() == before


@pytest.mark.parametrize("change", ["revision", "company_code", "inactive", "tenant", "session"])
def test_changed_identity_or_scope_cannot_confirm(review, change):
    if change == "revision":
        review["expected_revision"] = "0" * 64
    elif change == "company_code":
        ClientCompany.objects.filter(pk=review["company_discovery"].company_id).update(
            dominio_code="909"
        )
    elif change == "inactive":
        ClientCompany.objects.filter(pk=review["company_discovery"].company_id).update(active=False)
    elif change == "tenant":
        review["authorized_companies"] = ClientCompany.objects.none()
    else:
        review["request"] = SimpleNamespace(user=SimpleNamespace(pk=uuid4()))
    before = snapshot()
    with pytest.raises((DiscoveryReviewError, PermissionDenied)):
        confirmed(review)
    assert snapshot() == before


@pytest.mark.parametrize("change", ["membership", "module", "contract", "company_grant"])
def test_live_access_rechecked_before_first_and_repeat_writes(review, membership, change):
    confirmed(review)
    if change == "membership":
        membership.is_active = False
        membership.save()
    elif change == "module":
        ProductModule.objects.filter(organization=membership.organization).update(enabled=False)
    elif change == "contract":
        TenantContract.objects.filter(organization=membership.organization).update(
            status="suspended"
        )
    else:
        membership.role = "operator"
        membership.save()
        CompanyAccessGrant.objects.create(
            organization=membership.organization,
            membership=membership,
            company=review["company_discovery"].company,
            modules=["nfse"],
        )
    before = snapshot()
    with pytest.raises((DiscoveryReviewError, PermissionDenied)):
        confirmed(review)
    assert snapshot() == before


@pytest.mark.parametrize("change", ["bank", "reference", "ledger", "inactive", "foreign"])
def test_existing_identity_conflict_never_creates_or_overwrites(review, change):
    coverage = review["company_discovery"]
    values = dict(
        organization=coverage.organization,
        company=coverage.company,
        name="Existing synthetic",
        bank_code="001",
        account_reference="0001:000123-4",
        ledger_code="8",
        active=True,
    )
    if change == "bank":
        values["bank_code"] = "002"
    elif change == "reference":
        values["account_reference"] = "different"
    elif change == "ledger":
        values["ledger_code"] = "9"
    elif change == "inactive":
        values["active"] = False
    else:
        values["organization"] = Organization.objects.create(name="Other", slug="other")
    FinancialAccount.objects.create(**values)
    # Refresh after the independent existing-account mutation; conflict itself must still fail.
    prepared = prepared_account_facts(coverage, review["chart_account"], month=review["month"])
    review["expected_revision"] = prepared["revision"]
    before = snapshot()
    with pytest.raises(DiscoveryReviewError):
        confirmed(review)
    assert snapshot() == before


def test_audit_failure_rolls_back_account_ledger_mapping_and_review(review, monkeypatch):
    def failed(**kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr("apps.hub.account_discovery_review.record_event", failed)
    before = snapshot()
    with pytest.raises(RuntimeError, match="synthetic audit"):
        confirmed(review)
    assert snapshot() == before


def add_agent(organization):
    return EdgeAgent.objects.create(
        organization=organization,
        label="Synthetic agent",
        fingerprint="synthetic",
        shared_secret="synthetic-only",
        is_official=True,
        status="active",
        last_seen_at=timezone.now(),
    )


def test_month_guard_blocks_request_and_admission_but_allows_confirmed_month(review):
    result = confirmed(review)
    account = result["financial_account"]
    add_agent(account.organization)
    context = ledger_request_context(account=account, actor=review["actor"])
    args = dict(
        account=account,
        actor=review["actor"],
        request_key=uuid4(),
        expected_mapping_revision=context["mapping_revision"],
    )
    job, created = request_ledger(**args, month=date(2026, 9, 1))
    assert created and validate_job_mapping(job)
    with pytest.raises(LedgerRequestError, match="competência"):
        request_ledger(**{**args, "request_key": uuid4()}, month=date(2026, 10, 1))
    changed = dict(job.scope, period_start="2026-10-01", period_end_exclusive="2026-11-01")
    NativeLedgerCollection.objects.filter(pk=job.pk).update(scope=changed)
    assert not validate_job_mapping(job)
    assert NativeLedgerCollection.objects.count() == 1


def test_generic_mapping_review_cannot_remove_discovery_month_scope(review):
    result = confirmed(review)
    account = result["financial_account"]
    current = ledger_request_context(account=account, actor=review["actor"])
    before = snapshot()
    with pytest.raises(LedgerRequestError, match="ficha da descoberta"):
        save_ledger_mapping(
            account=account,
            actor=review["actor"],
            expected_revision=current["mapping_revision"],
            chart_company_code=212,
            branch_code=212,
            bank_inflow_side="debit",
            evidence_reference="Synthetic generic review cannot broaden monthly scope",
            confirmed=True,
        )
    assert snapshot() == before
    result["mapping"].refresh_from_db()
    assert discovery_mapping_month_allowed(account, result["mapping"], "2026-09")
    assert not discovery_mapping_month_allowed(account, result["mapping"], "2026-10")


@pytest.mark.parametrize("field", ["company_discovery_id", "chart_account_id", "discovery_id"])
def test_malformed_discovery_identity_refuses_month_without_unhandled_validation(review, field):
    from apps.hub.ledger_requests import _stored_revision

    result = confirmed(review)
    account, mapping = result["financial_account"], result["mapping"]
    mapping.provenance["confirmations"][0]["source_identity"][field] = "invalid-uuid"
    mapping.revision = _stored_revision(mapping)
    mapping.save()
    assert not discovery_mapping_month_allowed(account, mapping, "2026-09", deep=True)


def test_extension_retains_confirmed_bank_fields_and_review_history(review):
    first = confirmed(review)
    account = first["financial_account"]
    previous = deepcopy(first["mapping"].provenance)
    prepared = prepared_account_facts(
        review["company_discovery"],
        review["chart_account"],
        month="2026-10",
    )
    assert not prepared["collection_ready"]
    assert not {
        "bank_code",
        "account_reference",
        "bank_inflow_side",
        "bank_association_confirmed",
        "account_active_and_postable",
    } & set(prepared["pending_fields"])
    values = dict(branch_code=212, branch_scope_confirmed=True, chart_owner_confirmed=True)
    extended = confirmed(
        {
            **review,
            "month": "2026-10",
            "expected_revision": prepared["revision"],
            "confirmed_data": {key: values[key] for key in prepared["pending_fields"]},
        }
    )
    mapping = extended["mapping"]
    assert not extended["created"] and mapping.financial_account_id == account.pk
    assert mapping.provenance["period_scope"]["allowed_months"] == ["2026-09", "2026-10"]
    assert mapping.review_history[0]["provenance"] == previous
    assert mapping.provenance["confirmations"][0] == previous["confirmations"][0]
    assert discovery_mapping_month_allowed(account, mapping, "2026-09")
    assert discovery_mapping_month_allowed(account, mapping, "2026-10")
    assert FinancialAccount.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_confirmation_creates_one_mapping_account_and_audit(access, sources, user):
    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL row locking required")
    review = prepare_review(access, sources, user)

    def worker():
        close_old_connections()
        try:
            result = confirmed(review)
            return result["financial_account"].pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        ids = list(executor.map(lambda _: worker(), range(2)))
    assert len(set(ids)) == 1
    assert FinancialAccount.objects.count() == LedgerAccount.objects.count() == 1
    assert ReconciliationLedgerMapping.objects.count() == 1
    assert (
        AuditEvent.objects.filter(action="hub.reconciliation.discovered_account_confirmed").count()
        == 1
    )


def test_other_chart_or_other_office_account_is_not_accepted(review, sources):
    foreign = Organization.objects.create(name="Another office", slug="another-office")
    altered = deepcopy(review)
    altered["chart_account"].organization_id = foreign.pk
    # Even an altered in-memory object never replaces the actual row, which is reloaded.
    result = confirmed(altered)
    assert (
        result["financial_account"].organization_id == review["company_discovery"].organization_id
    )
    before = snapshot()
    another = ReconciliationDiscoveredChartAccount.objects.get(
        chart_company_code=213, account_code=77
    )
    with pytest.raises(DiscoveryReviewError):
        confirmed({**review, "chart_account": another})
    assert snapshot() == before


def test_new_discovery_blocks_stale_form_but_does_not_invalidate_existing_human_review(
    review, sources
):
    result = confirmed(review)
    account, mapping = result["financial_account"], result["mapping"]
    profile = discovery_profile(sources)
    profile["observed_at_utc"] = "2026-11-15T18:00:00.0000000Z"
    run_discovery(account.organization, sources, profile, apply=True)
    before = snapshot()
    assert discovery_mapping_month_allowed(account, mapping, "2026-09")
    with pytest.raises(DiscoveryReviewError, match="fonte"):
        confirmed(review)
    assert snapshot() == before


def test_retained_technical_fact_corruption_blocks_period_even_with_valid_mapping_hash(review):
    result = confirmed(review)
    # Simulate out-of-band corruption, bypassing immutable managers only in this fixture.
    with connection.cursor() as cursor:
        cursor.execute(
            'UPDATE "hub_reconciliationdiscoveredchartaccount" SET row_sha256 = %s WHERE id = %s',
            [
                "0" * 64,
                review["chart_account"].pk.hex,
            ],
        )
    assert not discovery_mapping_month_allowed(
        result["financial_account"], result["mapping"], "2026-09"
    )


def test_multiple_branches_require_actual_choice_and_confirmation_without_automatic_truncation(
    access,
    sources,
    user,
):
    base = prepare_review(access, sources, user)
    coverage = ReconciliationCompanyDiscovery.objects.get(source_company_code=213)
    chart = ReconciliationDiscoveredChartAccount.objects.get(chart_company_code=99, account_code=8)
    prepared = prepared_account_facts(coverage, chart, month="2026-09")
    data = dict(
        bank_code="001",
        account_reference="0002:000123-4",
        bank_inflow_side="debit",
        bank_association_confirmed=True,
        account_active_and_postable=True,
        branch_scope_confirmed=True,
        branch_code=500,
    )
    options = {
        **base,
        "company_discovery": coverage,
        "chart_account": chart,
        "expected_revision": prepared["revision"],
        "confirmed_data": data,
    }
    assert prepared["branches"] == [213, 500]
    assert "branch_scope_confirmed" in prepared["pending_fields"]
    for changes in ({"branch_scope_confirmed": False}, {"branch_code": 999}):
        before = snapshot()
        with pytest.raises(DiscoveryReviewError):
            confirmed({**options, "confirmed_data": {**data, **changes}})
        assert snapshot() == before
    result = confirmed(options)
    assert result["mapping"].scope["branch_code"] == 500
    assert result["mapping"].provenance["confirmations"][0]["observed_branches"] == [213, 500]
    assert not NativeLedgerCollection.objects.exists()


def test_existing_same_identity_name_is_preserved_and_unused_account_can_be_reused(review):
    coverage = review["company_discovery"]
    account = FinancialAccount.objects.create(
        organization=coverage.organization,
        company=coverage.company,
        name="Human display name",
        bank_code="001",
        account_reference="0001:000123-4",
        ledger_code="8",
    )
    ledger = LedgerAccount.objects.create(
        organization=coverage.organization,
        company=coverage.company,
        name="Human ledger name",
        code="8",
        nature="asset",
    )
    prepared = prepared_account_facts(coverage, review["chart_account"], month="2026-09")
    before = list(FinancialAccount.objects.values()), list(LedgerAccount.objects.values())
    result = confirmed({**review, "expected_revision": prepared["revision"]})
    assert result["financial_account"].pk == account.pk and not result["created"]
    assert before == (list(FinancialAccount.objects.values()), list(LedgerAccount.objects.values()))
    ledger.refresh_from_db()
    assert ledger.nature == "asset"


def test_zero_observed_branch_remains_visible_but_cannot_create_an_unsupported_mapping(
    access, sources, user
):
    profile = discovery_profile(sources)
    for row in profile["snapshot"]["observed_chart_usage"]:
        if row["company_code"] == 212:
            row["branch_code"] = 0
    review = prepare_review(access, sources, user, profile=profile)
    prepared = prepared_account_facts(
        review["company_discovery"], review["chart_account"], month="2026-09"
    )
    assert prepared["branches"] == [0] and "branch_code" in prepared["pending_fields"]
    before = snapshot()
    with pytest.raises(DiscoveryReviewError, match="filial zero"):
        confirmed(review)
    assert snapshot() == before


def test_retained_raw_content_is_checked_deeply_on_confirmation_and_request(review):
    result = confirmed(review)
    account = result["financial_account"]
    add_agent(account.organization)
    with connection.cursor() as cursor:
        cursor.execute(
            'UPDATE "hub_reconciliationaccountdiscovery" SET source_data = %s WHERE id = %s',
            ['{"corrupted":true}', review["company_discovery"].discovery_id.hex],
        )
    with pytest.raises(DiscoveryReviewError):
        confirmed(review)
    context = ledger_request_context(account=account, actor=review["actor"])
    with pytest.raises(LedgerRequestError):
        request_ledger(
            account=account,
            actor=review["actor"],
            month=date(2026, 9, 1),
            request_key=uuid4(),
            expected_mapping_revision=context["mapping_revision"],
        )
    assert not NativeLedgerCollection.objects.exists()


def test_used_unreviewed_account_cannot_be_rebound_through_discovery(review):
    coverage = review["company_discovery"]
    account = FinancialAccount.objects.create(
        organization=coverage.organization,
        company=coverage.company,
        name="Existing used account",
        bank_code="001",
        account_reference="0001:000123-4",
        ledger_code="8",
    )
    NativeLedgerCollection.objects.create(
        organization=coverage.organization,
        financial_account=account,
        agent=add_agent(coverage.organization),
        scope={},
        scope_revision="a" * 64,
        contract_hash="b" * 64,
    )
    prepared = prepared_account_facts(coverage, review["chart_account"], month="2026-09")
    before = snapshot()
    with pytest.raises(DiscoveryReviewError, match="movimentos"):
        confirmed({**review, "expected_revision": prepared["revision"]})
    assert snapshot() == before


def test_legacy_imported_pilot_is_reused_without_creating_review_or_changing_any_source(
    review,
    settings,
    tmp_path,
):
    import hashlib
    import json

    from django.core.files.base import ContentFile

    from apps.hub.models import ReconciliationSourceFile
    from apps.intelligence.native_ledger_contract import canonical_hash, contract_hash
    from test_native_ledger import pilot_scope
    from test_native_ledger import snapshot as native_snapshot

    settings.MEDIA_ROOT = tmp_path
    coverage = review["company_discovery"]
    account = FinancialAccount.objects.create(
        organization=coverage.organization,
        company=coverage.company,
        name="Existing pilot",
        bank_code="001",
        account_reference="0001:000123-4",
        ledger_code="8",
    )
    scope = pilot_scope()
    content = json.dumps(native_snapshot(scope)).encode()
    digest = hashlib.sha256(content).hexdigest()
    source = ReconciliationSourceFile.objects.create(
        organization=coverage.organization,
        company=coverage.company,
        financial_account=account,
        origin="accounting",
        kind="json",
        content_hash=digest,
        size_bytes=len(content),
        content=ContentFile(content, name="synthetic-legacy.json"),
    )
    NativeLedgerCollection.objects.create(
        organization=coverage.organization,
        financial_account=account,
        agent=add_agent(coverage.organization),
        scope=scope,
        scope_revision=canonical_hash(scope),
        contract_hash=contract_hash(),
        state="imported",
        source_file=source,
        content_hash=digest,
    )
    prepared = prepared_account_facts(coverage, review["chart_account"], month="2026-09")
    assert prepared["collection_ready"] and prepared["pending_fields"] == []
    before = snapshot()
    result = confirmed({**review, "expected_revision": prepared["revision"], "confirmed_data": {}})
    assert result["financial_account"].pk == account.pk and result["mapping"] is None
    assert result["reused_existing"] and not result["created"]
    assert snapshot() == before
    assert not LedgerAccount.objects.exists() and not ReconciliationLedgerMapping.objects.exists()
