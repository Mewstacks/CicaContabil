"""Correct only unused human mappings, retaining provenance and every prior review."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from threading import Barrier
from types import SimpleNamespace

import pytest
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connection
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.account_candidate_forms import (
    AccountCandidateCorrectionForm,
    AccountCandidateReopenForm,
)
from apps.hub.account_candidate_review import (
    CandidateReviewConflict,
    CandidateReviewError,
    candidate_revision,
    dismiss_candidate,
    finalize_candidate,
    revise_candidate,
)
from apps.hub.models import (
    AccountingEntry,
    ClientCompany,
    CompanyAccessGrant,
    DataSource,
    FinancialAccount,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    ProductModule,
    ReconciliationAccountCandidate,
    ReconciliationSourceFile,
)
from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantContract
from test_account_candidate_review import link_data, make_candidate, snapshot
from test_account_candidate_review import prepared as prepared

pytestmark = pytest.mark.django_db


def correction_data(candidate, **changes):
    data = {
        **link_data(candidate),
        "expected_revision": candidate_revision(candidate),
        "reason": "Referência corrigida após nova conferência sintética",
        "evidence_reference": "Nova evidência sintética do banco e plano",
        "account_reference": "001:999:000456",
        "name": "Conta sintética corrigida",
    }
    data.update(changes)
    return data


@pytest.fixture
def linked(prepared):
    candidate = finalize_candidate(**prepared)
    prepared["candidate"] = candidate
    prepared["cleaned_data"] = correction_data(candidate)
    return prepared


def test_unused_correction_keeps_identity_source_and_full_review_history(linked):
    old = linked["candidate"]
    source = deepcopy(old.evidence)
    old_review = deepcopy(old.review_data)
    old_account = old.financial_account
    result = revise_candidate(**linked)
    assert result.pk == old.pk and result.financial_account_id == old_account.pk
    assert result.state == "linked" and result.evidence == source
    assert result.review_data["name"] == "Conta sintética corrigida"
    assert result.review_evidence == linked["cleaned_data"]["evidence_reference"]
    assert len(result.review_history) == 1
    history = result.review_history[0]
    assert (
        history["review_data"] == old_review and history["review_evidence"] == old.review_evidence
    )
    assert history["reviewed_by_id"] == str(old.reviewed_by_id)
    assert history["reviewed_at"] == old.reviewed_at.isoformat()
    assert history["financial_account"]["account_reference"] == old_account.account_reference
    assert history["reason"] == linked["cleaned_data"]["reason"]
    assert FinancialAccount.objects.count() == LedgerAccount.objects.count() == 1
    assert LedgerAccount.objects.get().name == "Conta sintética corrigida"
    assert (
        not ReconciliationSourceFile.objects.exists()
        and not NativeLedgerCollection.objects.exists()
    )
    assert (
        AuditEvent.objects.filter(action="hub.reconciliation.account_candidate.corrected").count()
        == 1
    )
    before = snapshot()
    with pytest.raises(CandidateReviewConflict):
        revise_candidate(**linked)
    assert snapshot() == before


def test_second_review_preserves_first_review_and_both_actors(linked):
    first_actor = linked["actor"]
    result = revise_candidate(**linked)
    second_actor = User.objects.create_user("second-correction@example.test", "synthetic")
    Membership.objects.create(organization=result.organization, user=second_actor, role="owner")
    previous_history = deepcopy(result.review_history)
    result = revise_candidate(
        candidate=result,
        actor=second_actor,
        authorized_companies=linked["authorized_companies"],
        cleaned_data=correction_data(result, bank_inflow_side="credit"),
    )
    assert result.reviewed_by == second_actor and len(result.review_history) == 2
    assert result.review_history[:1] == previous_history
    assert result.review_history[1]["reviewed_by_id"] == str(first_actor.pk)
    assert result.review_history[1]["changed_by_id"] == str(second_actor.pk)


def test_correction_requires_fresh_confirmations_reason_and_evidence(linked):
    form = AccountCandidateCorrectionForm(candidate=linked["candidate"])
    assert form["expected_revision"].value() == candidate_revision(linked["candidate"])
    for field in (
        "bank_association_confirmed",
        "chart_owner_confirmed",
        "account_active_and_postable",
        "evidence_reference",
        "reason",
    ):
        assert form[field].value() in (None, "")
    before = snapshot()
    for field in (
        "bank_association_confirmed",
        "chart_owner_confirmed",
        "account_active_and_postable",
        "evidence_reference",
        "reason",
    ):
        invalid = {**linked, "cleaned_data": {**linked["cleaned_data"], field: ""}}
        with pytest.raises(CandidateReviewError):
            revise_candidate(**invalid)
    assert snapshot() == before


@pytest.mark.parametrize("change", ["token", "account", "ledger", "evidence", "history"])
def test_stale_revision_fails_without_overwriting(linked, change):
    candidate = linked["candidate"]
    if change == "token":
        linked["cleaned_data"]["expected_revision"] = "0" * 64
    elif change == "account":
        FinancialAccount.objects.filter(pk=candidate.financial_account_id).update(
            name="Changed independently"
        )
    elif change == "ledger":
        LedgerAccount.objects.filter(company=candidate.company).update(name="Changed independently")
    elif change == "evidence":
        ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).update(
            review_evidence="Changed independently"
        )
    else:
        ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).update(
            review_history=[{"reason": "Prior independent correction"}]
        )
    before = snapshot()
    with pytest.raises(CandidateReviewConflict):
        revise_candidate(**linked)
    assert snapshot() == before


@pytest.mark.parametrize(
    "revoked",
    [
        "membership",
        "actor",
        "company",
        "organization",
        "scope",
        "module",
        "contract",
        "role",
        "session",
    ],
)
def test_correction_rechecks_current_access(linked, membership, revoked):
    if revoked == "membership":
        Membership.objects.filter(pk=membership.pk).update(is_active=False)
    elif revoked == "actor":
        User.objects.filter(pk=linked["actor"].pk).update(is_active=False)
    elif revoked == "company":
        ClientCompany.objects.filter(pk=linked["candidate"].company_id).update(active=False)
    elif revoked == "organization":
        Organization.objects.filter(pk=membership.organization_id).update(is_active=False)
    elif revoked == "scope":
        linked["authorized_companies"] = ClientCompany.objects.none()
    elif revoked == "module":
        ProductModule.objects.filter(organization=membership.organization).update(enabled=False)
    elif revoked == "contract":
        TenantContract.objects.filter(organization=membership.organization).update(
            status="suspended"
        )
    elif revoked == "role":
        Membership.objects.filter(pk=membership.pk).update(role="auditor")
    else:
        linked["request"] = SimpleNamespace(
            user=User.objects.create_user("other-session@example.test", "synthetic")
        )
    before = snapshot()
    with pytest.raises((PermissionDenied, CandidateReviewError)):
        revise_candidate(**linked)
    assert snapshot() == before


def test_company_and_module_cannot_be_combined_across_grants(linked, membership):
    candidate = linked["candidate"]
    membership.role = "operator"
    membership.save(update_fields=["role"])
    other = ClientCompany.objects.create(
        organization=candidate.organization, name="Other", dominio_code="22"
    )
    grant = CompanyAccessGrant.objects.create(
        organization=candidate.organization,
        company=candidate.company,
        membership=membership,
        modules=["nfse"],
    )
    CompanyAccessGrant.objects.create(
        organization=candidate.organization,
        company=other,
        membership=membership,
        modules=["reconciliation"],
    )
    before = snapshot()
    with pytest.raises(PermissionDenied):
        revise_candidate(**linked)
    assert snapshot() == before
    grant.modules = ["reconciliation"]
    grant.save(update_fields=["modules"])
    assert revise_candidate(**linked).state == "linked"


@pytest.mark.parametrize("other_tenant", [False, True])
def test_malformed_candidate_account_scope_cannot_mutate_foreign_account(linked, other_tenant):
    candidate = linked["candidate"]
    org = (
        Organization.objects.create(name="Other office", slug="other-correction")
        if other_tenant
        else candidate.organization
    )
    company = ClientCompany.objects.create(
        organization=org, name="Other company", dominio_code="22"
    )
    foreign = FinancialAccount.objects.create(
        organization=org,
        company=company,
        name="Foreign",
        bank_code="002",
        account_reference="002:foreign",
        ledger_code="8",
    )
    ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).update(financial_account=foreign)
    candidate.refresh_from_db()
    linked["cleaned_data"] = correction_data(candidate)
    before = snapshot()
    with pytest.raises(CandidateReviewError, match="nesta empresa"):
        revise_candidate(**linked)
    assert snapshot() == before


@pytest.mark.parametrize("kind", ["source", "journal", "accounting", "job", "agent_scope"])
def test_used_mapping_is_preserved_for_every_financial_consumer(linked, kind):
    candidate = linked["candidate"]
    account = candidate.financial_account
    scope = {"organization": candidate.organization, "company": candidate.company}
    if kind == "source":
        ReconciliationSourceFile.objects.create(
            **scope,
            financial_account=account,
            origin="bank_statement",
            kind="csv",
            original_filename="synthetic.csv",
            content_hash="a" * 64,
            size_bytes=0,
        )
    elif kind == "journal":
        entry = JournalEntry.objects.create(
            **scope, occurred_on=date(2026, 9, 1), history="Synthetic", purpose="source_ledger"
        )
        JournalLine.objects.create(
            organization=candidate.organization,
            entry=entry,
            account_code="8",
            side="debit",
            amount_cents=100,
        )
    elif kind == "accounting":
        source = DataSource.objects.create(
            organization=candidate.organization, kind="other_manual", label="Synthetic"
        )
        AccountingEntry.objects.create(
            **scope,
            data_source=source,
            external_key="synthetic",
            occurred_on=date(2026, 9, 1),
            amount_cents=100,
            direction="inflow",
            account_reference=account.account_reference,
        )
    else:
        agent = EdgeAgent.objects.create(
            organization=candidate.organization,
            label="Synthetic",
            fingerprint="synthetic",
            shared_secret="synthetic-only",
            sync_scope={"financial_account_id": str(account.pk)} if kind == "agent_scope" else {},
        )
        if kind == "job":
            NativeLedgerCollection.objects.create(
                organization=candidate.organization,
                agent=agent,
                financial_account=account,
                scope={},
                scope_revision="c" * 64,
                contract_hash="d" * 64,
            )
    before = snapshot()
    with pytest.raises(CandidateReviewError, match="usado precisa"):
        revise_candidate(**linked)
    assert snapshot() == before


def test_shared_candidate_account_and_conflicting_reference_fail_closed(linked):
    candidate = linked["candidate"]
    second = make_candidate(candidate.organization, candidate.company, code=9, case="C02")
    second.financial_account = candidate.financial_account
    second.save(update_fields=["financial_account"])
    before = snapshot()
    with pytest.raises(CandidateReviewError, match="compartilhada"):
        revise_candidate(**linked)
    assert snapshot() == before
    second.financial_account = None
    second.save(update_fields=["financial_account"])
    FinancialAccount.objects.create(
        organization=candidate.organization,
        company=candidate.company,
        name="Conflict",
        account_reference=linked["cleaned_data"]["account_reference"],
    )
    before = snapshot()
    with pytest.raises(CandidateReviewError, match="referência"):
        revise_candidate(**linked)
    assert snapshot() == before


def test_final_audit_failure_rolls_back_accounts_new_review_and_history(linked, monkeypatch):
    from apps.hub import account_candidate_review

    original = account_candidate_review.record_event

    def audit(**kwargs):
        if kwargs["action"] == "hub.reconciliation.account_candidate.corrected":
            raise RuntimeError("Synthetic audit failure")
        return original(**kwargs)

    monkeypatch.setattr(account_candidate_review, "record_event", audit)
    before = snapshot()
    with pytest.raises(RuntimeError):
        revise_candidate(**linked)
    assert snapshot() == before


def test_reopen_dismissal_preserves_reason_without_creating_or_activating_accounts(prepared):
    candidate = prepared["candidate"]
    original_reason = "Vínculo não comprovado na primeira conferência sintética"
    dismissed = dismiss_candidate(
        **{
            **prepared,
            "cleaned_data": {
                "expected_source_hash": candidate.source_file_sha256,
                "expected_state": "pending",
                "reason": original_reason,
            },
        }
    )
    bound = AccountCandidateReopenForm(candidate=dismissed)
    assert bound["expected_revision"].value() == candidate_revision(dismissed)
    data = {
        "expected_source_hash": dismissed.source_file_sha256,
        "expected_state": "pending",
        "expected_revision": candidate_revision(dismissed),
        "reason": "Nova fonte sintética disponível para conferir",
    }
    result = revise_candidate(
        **{**prepared, "candidate": dismissed, "cleaned_data": data}, reopen=True
    )
    assert result.state == "pending" and result.financial_account_id is None
    assert not result.review_data and not result.review_evidence and result.reviewed_by_id is None
    assert result.review_history[0]["review_evidence"] == original_reason
    assert not FinancialAccount.objects.exists() and not LedgerAccount.objects.exists()
    before = snapshot()
    with pytest.raises(CandidateReviewConflict):
        revise_candidate(**{**prepared, "candidate": dismissed, "cleaned_data": data}, reopen=True)
    assert snapshot() == before


def test_http_correction_keeps_history_and_stale_submit_returns_conflict(linked):
    client = Client()
    client.force_login(linked["actor"])
    session = client.session
    session["hub_organization_id"] = str(linked["candidate"].organization_id)
    session.save()
    url = reverse("hub:reconciliation-account-candidate", args=[linked["candidate"].pk])
    response = client.get(url)
    assert (
        response.status_code == 200 and b"candidate-correct-expected_revision" in response.content
    )
    data = {**linked["cleaned_data"], "action": "correct"}
    assert client.post(url, data).status_code == 302
    response = client.get(url)
    assert "Revisões anteriores (1)" in response.content.decode()
    before = snapshot()
    response = client.post(url, data)
    assert response.status_code == 409 and "A revisão mudou" in response.content.decode()
    assert snapshot() == before


@pytest.mark.django_db(transaction=True)
def test_two_concurrent_corrections_preserve_one_revision(linked):
    if connection.vendor != "postgresql":
        pytest.skip("Concurrent correction requires PostgreSQL row locking")
    barrier = Barrier(2)
    candidate_id = linked["candidate"].pk
    actor_id = linked["actor"].pk
    data = dict(linked["cleaned_data"])

    def correct(index):
        close_old_connections()
        try:
            candidate = ReconciliationAccountCandidate.objects.get(pk=candidate_id)
            barrier.wait(timeout=10)
            try:
                revise_candidate(
                    candidate=candidate,
                    actor=User.objects.get(pk=actor_id),
                    authorized_companies=ClientCompany.objects.filter(
                        organization_id=candidate.organization_id
                    ),
                    cleaned_data={**data, "reason": f"Synthetic correction {index}"},
                )
                return "corrected"
            except CandidateReviewConflict:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(correct, [1, 2])) == ["conflict", "corrected"]
    current = ReconciliationAccountCandidate.objects.get(pk=candidate_id)
    assert len(current.review_history) == 1
    assert (
        AuditEvent.objects.filter(action="hub.reconciliation.account_candidate.corrected").count()
        == 1
    )
