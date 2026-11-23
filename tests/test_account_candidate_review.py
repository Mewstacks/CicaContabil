"""Human enrollment is complete, scoped, atomic and replay safe."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Barrier

import pytest
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connection
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.account_candidate_forms import AccountCandidateDismissForm, AccountCandidateLinkForm
from apps.hub.account_candidate_review import (
    CandidateReviewError,
    dismiss_candidate,
    finalize_candidate,
)
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    LedgerAccount,
    ProductModule,
    ReconciliationAccountCandidate,
    ReconciliationRule,
)
from apps.intelligence.models import NativeLedgerCollection, NativeTitleCollection
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantContract

pytestmark = pytest.mark.django_db


def make_candidate(organization, company, *, code=8, case="C01"):
    observed = timezone.now()
    source_code = int(company.dominio_code)
    key = f"{source_code}:21:{code}"
    return ReconciliationAccountCandidate.objects.create(
        organization=organization,
        company=company,
        source_company_code=source_code,
        chart_company_code=21,
        account_code=code,
        case_reference=case,
        source_key=key,
        source_file_sha256="a" * 64,
        portfolio_file_sha256="b" * 64,
        source_observed_at=observed,
        evidence={
            "version": "reconciliation-account-candidates-v1",
            "candidate": {
                "company_code": source_code,
                "chart_company_code": 21,
                "account_code": code,
                "candidate_key": key,
                "review": None,
                "account_level_counts": None,
                "collection_scope": None,
            },
            "sources": {
                "configured_accounts": {
                    "input_file_sha256": "a" * 64,
                    "observed_at_utc": observed.isoformat(),
                },
                "portfolio": {"input_file_sha256": "b" * 64},
            },
        },
    )


def link_data(candidate):
    return {
        "expected_source_hash": candidate.source_file_sha256,
        "expected_state": "pending",
        "name": "Conta bancária sintética",
        "bank_code": "001",
        "account_reference": "0001:000123-4",
        "bank_inflow_side": "debit",
        "evidence_reference": "Extrato e plano sintéticos conferidos pela revisora",
        "bank_association_confirmed": True,
        "chart_owner_confirmed": True,
        "account_active_and_postable": True,
    }


@pytest.fixture
def prepared(organization, user, membership):
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"]
    )
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa sintética", dominio_code="21"
    )
    candidate = make_candidate(organization, company)
    return {
        "candidate": candidate,
        "actor": user,
        "authorized_companies": ClientCompany.objects.filter(organization=organization),
        "cleaned_data": link_data(candidate),
    }


def snapshot():
    return {
        model.__name__: list(model.objects.order_by("pk").values())
        for model in (ReconciliationAccountCandidate, FinancialAccount, LedgerAccount, AuditEvent)
    }


def test_form_has_no_assumed_direction_or_confirmations(prepared):
    form = AccountCandidateLinkForm(candidate=prepared["candidate"])
    assert form["bank_inflow_side"].value() is None
    for field in (
        "bank_association_confirmed",
        "chart_owner_confirmed",
        "account_active_and_postable",
    ):
        assert form[field].value() is None
    assert not {"account_code", "chart_company_code", "source_company_code"} & form.fields.keys()
    assert form["expected_source_hash"].value() == "a" * 64
    assert AccountCandidateLinkForm(
        prepared["cleaned_data"], candidate=prepared["candidate"]
    ).is_valid()


@pytest.mark.parametrize(
    "field",
    [
        "name",
        "bank_code",
        "account_reference",
        "bank_inflow_side",
        "evidence_reference",
        "bank_association_confirmed",
        "chart_owner_confirmed",
        "account_active_and_postable",
        "expected_source_hash",
        "expected_state",
    ],
)
def test_incomplete_review_cannot_write(prepared, field):
    prepared["cleaned_data"].pop(field)
    before = snapshot()
    with pytest.raises(CandidateReviewError):
        finalize_candidate(**prepared)
    assert snapshot() == before


def test_creates_only_accounts_and_private_human_review(prepared):
    source = deepcopy(prepared["candidate"].evidence)
    result = finalize_candidate(**prepared)
    account = FinancialAccount.objects.get()
    ledger = LedgerAccount.objects.get()
    assert result.state == "linked" and result.financial_account == account
    assert result.reviewed_by == prepared["actor"] and result.reviewed_at
    assert account.account_reference == "0001:000123-4" and account.ledger_code == "8"
    assert account.active and ledger.active and ledger.accepts_entries and ledger.nature == ""
    assert result.review_data["bank_inflow_side"] == "debit"
    assert result.review_evidence == prepared["cleaned_data"]["evidence_reference"]
    assert result.evidence == source
    assert not NativeLedgerCollection.objects.exists()
    assert not NativeTitleCollection.objects.exists()
    assert not ReconciliationRule.objects.exists()
    metadata = str(
        AuditEvent.objects.get(action="hub.reconciliation.account_candidate.linked").metadata
    )
    assert account.account_reference not in metadata and result.review_evidence not in metadata


def make_ledger(prepared, **changes):
    candidate = prepared["candidate"]
    data = {
        "organization": candidate.organization,
        "company": candidate.company,
        "code": str(candidate.account_code),
        "name": prepared["cleaned_data"]["name"],
        "active": True,
        "accepts_entries": True,
        "nature": "asset",
    }
    data.update(changes)
    return LedgerAccount.objects.create(**data)


def make_account(prepared, **changes):
    candidate = prepared["candidate"]
    data = {
        "organization": candidate.organization,
        "company": candidate.company,
        "ledger_code": str(candidate.account_code),
        "active": True,
        **{
            key: prepared["cleaned_data"][key] for key in ("name", "bank_code", "account_reference")
        },
    }
    data.update(changes)
    return FinancialAccount.objects.create(**data)


def test_reuses_exact_existing_accounts_without_overwriting(prepared):
    ledger = make_ledger(prepared)
    account = make_account(prepared)
    before = (list(LedgerAccount.objects.values()), list(FinancialAccount.objects.values()))
    assert finalize_candidate(**prepared).financial_account == account
    assert (list(LedgerAccount.objects.values()), list(FinancialAccount.objects.values())) == before
    ledger.refresh_from_db()
    assert ledger.nature == "asset"


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "Outro plano"},
        {"active": False},
        {"accepts_entries": False},
        {"organization": "other"},
    ],
)
def test_ledger_conflicts_fail_without_changes(prepared, changes):
    changes = dict(changes)
    if changes.get("organization") == "other":
        changes["organization"] = Organization.objects.create(name="Outra", slug="other-ledger")
    make_ledger(prepared, **changes)
    before = snapshot()
    with pytest.raises(CandidateReviewError):
        finalize_candidate(**prepared)
    assert snapshot() == before


@pytest.mark.parametrize(
    "changes",
    [
        {"name": "Outra conta"},
        {"bank_code": "002"},
        {"ledger_code": "9"},
        {"account_reference": "Outra referência"},
        {"active": False},
    ],
)
def test_financial_conflicts_fail_without_creating_ledger(prepared, changes):
    make_account(prepared, **changes)
    before = snapshot()
    with pytest.raises(CandidateReviewError):
        finalize_candidate(**prepared)
    assert snapshot() == before


def test_exact_replay_keeps_first_actor_and_changed_replay_fails(prepared):
    original = finalize_candidate(**prepared)
    second = User.objects.create_user(email="reviewer2@example.test", password="synthetic-only")
    Membership.objects.create(organization=original.organization, user=second, role="owner")
    prepared["actor"] = second
    before = snapshot()
    repeated = finalize_candidate(**prepared)
    assert repeated.reviewed_by_id == original.reviewed_by_id
    assert snapshot() == before
    prepared["cleaned_data"]["bank_inflow_side"] = "credit"
    with pytest.raises(CandidateReviewError):
        finalize_candidate(**prepared)
    assert snapshot() == before


@pytest.mark.parametrize(
    "change",
    ["hidden_hash", "hidden_state", "company_code", "account_code", "evidence", "portfolio_hash"],
)
def test_stale_or_inconsistent_origin_cannot_write(prepared, change):
    candidate = prepared["candidate"]
    if change == "hidden_hash":
        prepared["cleaned_data"]["expected_source_hash"] = "c" * 64
    elif change == "hidden_state":
        prepared["cleaned_data"]["expected_state"] = "linked"
    elif change == "company_code":
        ClientCompany.objects.filter(pk=candidate.company_id).update(dominio_code="22")
    elif change == "account_code":
        ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).update(account_code=9)
    elif change == "evidence":
        ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).update(evidence={})
    else:
        ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).update(
            portfolio_file_sha256="c" * 64
        )
    before = snapshot()
    with pytest.raises(CandidateReviewError):
        finalize_candidate(**prepared)
    assert snapshot() == before


@pytest.mark.parametrize("role", ["auditor", "member", "billing"])
def test_non_configurator_cannot_review(prepared, membership, role):
    membership.role = role
    membership.save(update_fields=["role"])
    before = snapshot()
    with pytest.raises(PermissionDenied):
        finalize_candidate(**prepared)
    assert snapshot() == before


@pytest.mark.parametrize("revoked", ["membership", "user", "company", "scope", "organization"])
def test_revoked_access_rechecked_at_write(prepared, membership, revoked):
    if revoked == "membership":
        Membership.objects.filter(pk=membership.pk).update(is_active=False)
    elif revoked == "user":
        User.objects.filter(pk=prepared["actor"].pk).update(is_active=False)
    elif revoked == "company":
        ClientCompany.objects.filter(pk=prepared["candidate"].company_id).update(active=False)
    elif revoked == "scope":
        prepared["authorized_companies"] = ClientCompany.objects.none()
    else:
        Organization.objects.filter(pk=membership.organization_id).update(is_active=False)
    before = snapshot()
    with pytest.raises(PermissionDenied):
        finalize_candidate(**prepared)
    assert snapshot() == before


def test_company_and_module_must_be_on_same_grant(prepared, membership):
    membership.role = "operator"
    membership.save(update_fields=["role"])
    candidate = prepared["candidate"]
    other = ClientCompany.objects.create(
        organization=candidate.organization, name="Outra empresa", dominio_code="22"
    )
    grant = CompanyAccessGrant.objects.create(
        organization=candidate.organization,
        membership=membership,
        company=candidate.company,
        modules=["nfse"],
    )
    CompanyAccessGrant.objects.create(
        organization=candidate.organization,
        membership=membership,
        company=other,
        modules=["reconciliation"],
    )
    before = snapshot()
    with pytest.raises(PermissionDenied):
        finalize_candidate(**prepared)
    assert snapshot() == before
    grant.modules = ["reconciliation"]
    grant.save(update_fields=["modules"])
    assert finalize_candidate(**prepared).state == "linked"


def test_suspended_contract_produces_actionable_error(prepared):
    TenantContract.objects.filter(organization=prepared["candidate"].organization).update(
        status="suspended"
    )
    before = snapshot()
    with pytest.raises(CandidateReviewError, match="contrato"):
        finalize_candidate(**prepared)
    assert snapshot() == before


def test_audit_failure_rolls_back_candidate_and_accounts(prepared, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr("apps.hub.account_candidate_review.record_event", fail)
    before = snapshot()
    with pytest.raises(RuntimeError):
        finalize_candidate(**prepared)
    assert snapshot() == before


def test_dismiss_needs_reason_and_replays_without_overwriting(prepared):
    candidate = prepared["candidate"]
    data = {"expected_source_hash": candidate.source_file_sha256, "expected_state": "pending"}
    assert not AccountCandidateDismissForm(data, candidate=candidate).is_valid()
    prepared["cleaned_data"] = data
    before = snapshot()
    with pytest.raises(CandidateReviewError):
        dismiss_candidate(**prepared)
    assert snapshot() == before
    data["reason"] = "Não corresponde à conta bancária desta empresa, conforme revisão sintética"
    result = dismiss_candidate(**prepared)
    assert result.state == "dismissed" and result.review_evidence == data["reason"]
    assert not FinancialAccount.objects.exists() and not LedgerAccount.objects.exists()
    before = snapshot()
    assert dismiss_candidate(**prepared).pk == result.pk
    assert snapshot() == before
    prepared["cleaned_data"] = link_data(candidate)
    with pytest.raises(CandidateReviewError):
        finalize_candidate(**prepared)
    assert snapshot() == before


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("same_candidate", [True, False])
def test_concurrent_reviews_are_serialized_by_company(prepared, same_candidate):
    if connection.vendor != "postgresql":
        pytest.skip("Row locking requires PostgreSQL")
    first = prepared["candidate"]
    second = (
        first
        if same_candidate
        else make_candidate(first.organization, first.company, code=9, case="C02")
    )
    barrier = Barrier(2)
    actor_id = prepared["actor"].pk

    def review(candidate_id):
        close_old_connections()
        try:
            candidate = ReconciliationAccountCandidate.objects.get(pk=candidate_id)
            barrier.wait(timeout=10)
            try:
                result = finalize_candidate(
                    candidate=candidate,
                    actor=User.objects.get(pk=actor_id),
                    authorized_companies=ClientCompany.objects.filter(
                        organization_id=candidate.organization_id
                    ),
                    cleaned_data=link_data(candidate),
                )
                return "linked", result.financial_account_id
            except CandidateReviewError:
                return "conflict", None
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(review, [first.pk, second.pk]))
    assert FinancialAccount.objects.count() == LedgerAccount.objects.count() == 1
    assert (
        AuditEvent.objects.filter(action="hub.reconciliation.account_candidate.linked").count() == 1
    )
    if same_candidate:
        assert results[0] == results[1] and results[0][0] == "linked"
    else:
        assert sorted(item[0] for item in results) == ["conflict", "linked"]
        assert ReconciliationAccountCandidate.objects.filter(state="pending").count() == 1
