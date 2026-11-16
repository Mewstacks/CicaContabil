"""Manual corrections preserve provenance and serialize identities already in use."""

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied
from django.db import close_old_connections, connection
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import (
    AccountingEntry,
    BankStatementImport,
    ClientCompany,
    CompanyAccessGrant,
    DataSource,
    FinancialAccount,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    OfxTransactionIdentity,
    ProductModule,
    ReconciliationAccountCandidate,
    ReconciliationSourceFile,
)
from apps.hub.setup_review import (
    SetupReviewConflict,
    SetupReviewError,
    account_integrity_errors,
    account_revision,
    account_usage_reasons,
    review_financial_account,
)
from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
from apps.organizations.models import Membership
from apps.platform.models import TenantContract

pytestmark = pytest.mark.django_db


@pytest.fixture
def prepared(organization):
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"],
    )
    actor = User.objects.create_user("manual-review@synthetic.test", "synthetic-password")
    member = Membership.objects.create(organization=organization, user=actor, role="owner")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa fictícia", dominio_code="9001",
    )
    ledger = LedgerAccount.objects.create(
        organization=organization, company=company, code="1001", name="Banco fictício",
    )
    account = FinancialAccount.objects.create(
        organization=organization, company=company, name="Conta fictícia",
        bank_code="001", account_reference="001:123:456", ledger_code=ledger.code,
    )
    return account, actor, member, ledger


def data(account, **changes):
    return {"name": "Nome conferido", "bank_code": account.bank_code,
            "account_reference": account.account_reference, "ledger_code": account.ledger_code,
            "active": account.active, "reason": "Cadastro conferido com documento fictício",
            "expected_revision": account_revision(account), **changes}


def review(prepared, changes=None):
    account, actor, _, _ = prepared
    return review_financial_account(
        account=account, actor=actor,
        authorized_companies=ClientCompany.objects.filter(organization=account.organization),
        cleaned_data=changes or data(account),
    )


def client_for(prepared):
    account, actor, _, _ = prepared
    client = Client()
    client.force_login(actor)
    session = client.session
    session["hub_organization_id"] = str(account.organization_id)
    session.save()
    return client


def endpoint(account):
    return reverse("hub:reconciliation-financial-account-edit", args=[account.pk])


def test_complete_existing_manual_account_and_record_before_after(prepared):
    account, actor, _, _ = prepared
    FinancialAccount.objects.filter(pk=account.pk).update(ledger_code="")
    account.refresh_from_db()
    result = review(prepared, data(account, ledger_code="1001"))
    assert result.pk == account.pk and result.ledger_code == "1001"
    event = AuditEvent.objects.get(action="hub.reconciliation.financial_account.corrected")
    assert event.actor == actor and event.metadata["history_count"] == 1
    assert event.metadata["changed_fields"] == ["name", "ledger_code"]
    assert result.review_history[0]["before"]["ledger_code"] == ""
    assert result.review_history[0]["after"]["ledger_code"] == "1001"
    assert result.review_history[0]["reason"] and "reason" not in event.metadata
    assert FinancialAccount.objects.count() == 1


@pytest.mark.parametrize(
    "kind", ["source", "accounting", "statement", "identity", "journal", "job", "scope"],
)
def test_used_identity_cannot_change_but_name_can(prepared, kind):
    account, _, _, _ = prepared
    scope = {"organization": account.organization, "company": account.company}
    if kind == "source":
        ReconciliationSourceFile.objects.create(
            **scope, financial_account=account, origin="bank_statement", kind="csv",
            original_filename="synthetic.csv", content_hash="a" * 64, size_bytes=0,
        )
    elif kind == "accounting":
        source = DataSource.objects.create(
            organization=account.organization, kind="other_manual", label="Synthetic",
        )
        AccountingEntry.objects.create(
            **scope, data_source=source, external_key="synthetic-1", occurred_on=date(2026, 9, 1),
            amount_cents=100, direction="inflow", account_reference=account.account_reference,
        )
    elif kind == "statement":
        BankStatementImport.objects.create(
            **scope, original_filename="synthetic.ofx", content_hash="b" * 64,
            account_reference=account.account_reference,
        )
    elif kind == "identity":
        OfxTransactionIdentity.objects.create(
            **scope, account_reference=account.account_reference,
            external_id="synthetic-1", content_hash="c" * 64,
        )
    elif kind == "journal":
        entry = JournalEntry.objects.create(
            **scope, occurred_on=date(2026, 9, 1), history="Sintético", purpose="synthetic",
        )
        JournalLine.objects.create(
            organization=account.organization, entry=entry,
            account_code=account.ledger_code, side="debit", amount_cents=100,
        )
    else:
        agent = EdgeAgent.objects.create(
            organization=account.organization, label="Sintético", fingerprint="synthetic",
            shared_secret="synthetic-only", sync_scope={"financial_account_id": str(account.pk)}
            if kind == "scope" else {},
        )
        if kind == "job":
            NativeLedgerCollection.objects.create(
                organization=account.organization, agent=agent, financial_account=account,
                scope={}, scope_revision="d" * 64, contract_hash="e" * 64,
            )
    assert account_usage_reasons(account)
    with pytest.raises(SetupReviewError, match="preservados"):
        review(prepared, data(account, account_reference="001:999:999"))
    account.refresh_from_db()
    assert account.account_reference == "001:123:456"
    assert review(prepared).name == "Nome conferido"


def test_legacy_name_change_does_not_require_new_ledger_account(prepared):
    account, _, _, ledger = prepared
    ledger.delete()
    assert account_integrity_errors(account) == {
        "ledger_code": "Escolha uma conta contábil ativa que aceite lançamentos desta empresa."
    }
    assert review(prepared).name == "Nome conferido"
    account.refresh_from_db()
    assert LedgerAccount.objects.count() == 0
    with pytest.raises(SetupReviewError, match="contábil"):
        review(prepared, data(account, bank_code="002"))


@pytest.mark.parametrize("missing", ["bank_code", "account_reference", "ledger_code"])
def test_new_identity_cannot_be_incomplete(prepared, missing):
    account = prepared[0]
    with pytest.raises(SetupReviewError):
        review(prepared, data(account, **{missing: ""}))
    account.refresh_from_db()
    assert getattr(account, missing)
    assert not AuditEvent.objects.exists()


@pytest.mark.parametrize("field", ["active", "accepts_entries"])
def test_new_activation_requires_active_analytical_ledger(prepared, field):
    account, _, _, ledger = prepared
    FinancialAccount.objects.filter(pk=account.pk).update(active=False)
    setattr(ledger, field, False)
    ledger.save(update_fields=[field])
    account.refresh_from_db()
    with pytest.raises(SetupReviewError, match="contábil"):
        review(prepared, data(account, active=True))
    account.refresh_from_db()
    assert not account.active


def test_stale_revision_and_duplicate_reference_preserve_data(prepared):
    account = prepared[0]
    old_data = data(account)
    review(prepared)
    with pytest.raises(SetupReviewConflict):
        review(prepared, old_data)
    account.refresh_from_db()
    FinancialAccount.objects.create(
        organization=account.organization, company=account.company,
        name="Outra conta", account_reference="001:999:999",
    )
    with pytest.raises(SetupReviewError, match="Já existe"):
        review(prepared, data(account, account_reference="001:999:999"))
    assert AuditEvent.objects.count() == 1
    account.refresh_from_db()
    assert account.account_reference == "001:123:456"


def linked_candidate(prepared):
    account, actor, _, _ = prepared
    return ReconciliationAccountCandidate.objects.create(
        organization=account.organization, company=account.company,
        financial_account=account, source_company_code=9001, chart_company_code=1,
        account_code=1001, case_reference="C01", source_key="9001:1:1001",
        source_file_sha256="a" * 64, portfolio_file_sha256="b" * 64,
        source_observed_at=account.created_at, state="linked",
        reviewed_by=actor, reviewed_at=account.created_at,
        review_data={"decision": "linked", "bank_inflow_side": "debit"},
        review_evidence="Evidência bancária fictícia preservada",
    )


def test_linked_candidate_routes_identity_to_its_own_review(prepared):
    account = prepared[0]
    candidate = linked_candidate(prepared)
    assert not account_usage_reasons(account)
    with pytest.raises(SetupReviewConflict, match="vínculo"):
        review(prepared)
    client = client_for(prepared)
    page = client.get(endpoint(account))
    assert page.context["setup_can_edit"]
    for field in ("name", "bank_code", "account_reference", "ledger_code"):
        assert page.context["setup_form"].fields[field].widget.attrs["readonly"]
    assert not page.context["setup_form"].fields["active"].widget.attrs.get("readonly")
    assert str(candidate.pk) in page.context["setup_candidate_url"]
    assert client.post(endpoint(account), data(account)).status_code == 409


def test_linked_used_account_can_deactivate_and_reactivate_preserving_bank_review(prepared):
    account, actor, _, _ = prepared
    candidate = linked_candidate(prepared)
    before_candidate = ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).values().get()
    ReconciliationSourceFile.objects.create(
        organization=account.organization, company=account.company, financial_account=account,
        origin="bank_statement", kind="csv", original_filename="used-synthetic.csv",
        content_hash="a" * 64, size_bytes=0,
    )
    client = client_for(prepared)
    old_name = account.name
    submission = data(account, name=old_name, active=False)
    assert client.post(endpoint(account), submission).status_code == 302
    account.refresh_from_db()
    assert not account.active and len(account.review_history) == 1
    assert account.review_history[0]["before"]["active"] is True
    assert account.review_history[0]["after"]["active"] is False
    assert account.review_history[0]["actor_id"] == str(actor.pk)
    assert client.post(endpoint(account), submission).status_code == 409
    activated = client.post(endpoint(account), data(account, name=old_name, active=True))
    assert activated.status_code == 302
    account.refresh_from_db()
    assert account.active and len(account.review_history) == 2
    assert (
        ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).values().get()
        == before_candidate
    )
    audits = AuditEvent.objects.filter(action="hub.reconciliation.financial_account.corrected")
    assert audits.count() == 2
    assert all(event.metadata["changed_fields"] == ["active"] for event in audits)


@pytest.mark.parametrize("field", ["name", "bank_code", "account_reference", "ledger_code"])
def test_linked_account_cannot_bypass_bank_review_when_changing_active(prepared, field):
    account = prepared[0]
    candidate = linked_candidate(prepared)
    before_candidate = ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).values().get()
    changes = data(account, name=account.name, active=False)
    changes[field] = "999"
    with pytest.raises(SetupReviewConflict, match="somente"):
        review(prepared, changes)
    account.refresh_from_db()
    assert account.active and account.review_history == []
    assert (
        ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).values().get()
        == before_candidate
    )
    assert not AuditEvent.objects.exists()


def test_linked_active_change_requires_reason_and_audit_is_atomic(prepared):
    account = prepared[0]
    linked_candidate(prepared)
    with pytest.raises(SetupReviewError):
        review(prepared, data(account, name=account.name, active=False, reason=""))
    with (
        patch("apps.hub.setup_review.record_event", side_effect=RuntimeError("synthetic failure")),
        pytest.raises(RuntimeError),
    ):
        review(prepared, data(account, name=account.name, active=False))
    account.refresh_from_db()
    assert account.active and account.review_history == []
    assert not AuditEvent.objects.exists()


def test_linked_legacy_deactivation_allows_missing_plan_but_reactivation_requires_it(prepared):
    account, _, _, ledger = prepared
    candidate = linked_candidate(prepared)
    before_candidate = ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).values().get()
    ledger.delete()
    review(prepared, data(account, name=account.name, active=False))
    account.refresh_from_db()
    assert not account.active
    with pytest.raises(SetupReviewError, match="contábil"):
        review(prepared, data(account, name=account.name, active=True))
    account.refresh_from_db()
    assert not account.active and len(account.review_history) == 1
    assert (
        ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).values().get()
        == before_candidate
    )


@pytest.mark.parametrize("revocation", ["membership", "user", "module", "grant", "contract"])
def test_service_rechecks_permission_and_contract(prepared, revocation):
    account, actor, member, _ = prepared
    member.role = "operator"
    member.save(update_fields=["role"])
    grant = CompanyAccessGrant.objects.create(
        organization=account.organization, company=account.company,
        membership=member, modules=["reconciliation"],
    )
    if revocation == "membership":
        member.is_active = False
        member.save(update_fields=["is_active"])
    elif revocation == "user":
        actor.is_active = False
        actor.save(update_fields=["is_active"])
    elif revocation == "module":
        grant.modules = ["payroll"]
        grant.save(update_fields=["modules"])
    elif revocation == "grant":
        grant.is_active = False
        grant.save(update_fields=["is_active"])
    else:
        TenantContract.objects.filter(organization=account.organization).update(status="suspended")
    with pytest.raises((PermissionDenied, SetupReviewError)):
        review(prepared)
    assert not AuditEvent.objects.exists()


def test_audit_failure_rolls_back_correction(prepared):
    with (
        patch("apps.hub.setup_review.record_event", side_effect=RuntimeError("synthetic failure")),
        pytest.raises(RuntimeError),
    ):
        review(prepared)
    prepared[0].refresh_from_db()
    assert prepared[0].name == "Conta fictícia"


def test_http_read_only_auditor_and_duplicate_fields(prepared):
    account, _, member, _ = prepared
    client = client_for(prepared)
    audit_count = AuditEvent.objects.count()
    page = client.get(endpoint(account))
    assert page.status_code == 200 and page["Cache-Control"] == "no-store, private"
    assert AuditEvent.objects.count() == audit_count
    duplicate = data(account, reason=["Um motivo", "Outro motivo"])
    assert client.post(endpoint(account), duplicate).status_code == 400
    member.role = "auditor"
    member.save(update_fields=["role"])
    CompanyAccessGrant.objects.create(
        organization=account.organization, company=account.company,
        membership=member, modules=["reconciliation"],
    )
    page = client.get(endpoint(account))
    assert page.status_code == 200 and not page.context["setup_can_edit"]
    assert client.post(endpoint(account), data(account)).status_code == 403
    assert not AuditEvent.objects.filter(
        action="hub.reconciliation.financial_account.corrected",
    ).exists()


def test_http_success_and_stale_replay(prepared):
    account = prepared[0]
    client = client_for(prepared)
    original = data(account)
    response = client.post(endpoint(account), original)
    assert response.status_code == 302 and str(account.company_id) in response.url
    assert response.url.endswith("#contas-financeiras")
    assert client.post(endpoint(account), original).status_code == 409
    assert AuditEvent.objects.filter(
        action="hub.reconciliation.financial_account.corrected",
    ).count() == 1
    page = client.get(endpoint(account))
    assert page.context["setup_history"][0]["reason"] == original["reason"]
    assert page.context["setup_history"][0]["changes"][0]["before"] == "Conta fictícia"


def test_http_company_and_module_grant_intersection(prepared):
    account, _, member, _ = prepared
    member.role = "operator"
    member.save(update_fields=["role"])
    grant = CompanyAccessGrant.objects.create(
        organization=account.organization, company=account.company,
        membership=member, modules=["payroll"],
    )
    client = client_for(prepared)
    assert client.get(endpoint(account)).status_code == 404
    assert client.post(endpoint(account), data(account)).status_code == 404
    grant.modules = ["reconciliation"]
    grant.save(update_fields=["modules"])
    assert client.get(endpoint(account)).status_code == 200
    grant.is_active = False
    grant.save(update_fields=["is_active"])
    assert client.post(endpoint(account), data(account)).status_code == 404


def creation_data(account, **changes):
    return {"action": "financial_account", "company": account.company_id,
            "name": "Nova conta fictícia", "bank_code": "001",
            "account_reference": "001:nova:999", "ledger_code": "1001", "active": "on",
            **changes}


@pytest.mark.parametrize("missing", ["bank_code", "account_reference", "ledger_code"])
def test_configuration_cannot_create_incomplete_active_account(prepared, missing):
    account = prepared[0]
    response = client_for(prepared).post(
        reverse("hub:reconciliation-configuration"), creation_data(account, **{missing: ""}),
    )
    assert response.status_code == 200
    assert missing in response.context["financial_account_form"].errors
    assert FinancialAccount.objects.count() == 1


def test_configuration_financial_toggle_requires_correction_reason(prepared):
    account = prepared[0]
    response = client_for(prepared).post(reverse("hub:reconciliation-configuration"), {
        "action": "toggle_setup", "company": account.company_id,
        "setup_kind": "financial_account", "setup_id": account.pk,
    })
    assert response.status_code == 302 and response.url == endpoint(account)
    account.refresh_from_db()
    assert account.active and account.review_history == []


def test_configuration_incomplete_active_account_is_not_ready(prepared):
    account = prepared[0]
    client = client_for(prepared)
    configuration = reverse("hub:reconciliation-configuration")
    ready = client.get(configuration, {"company": account.company_id})
    assert ready.context["reconciliation_setup_next_action"]["state"] == "ready"
    upload = client.get(ready.context["reconciliation_setup_next_action"]["href"])
    assert upload.context["upload_open"]
    assert str(upload.context["upload_form"]["company"].value()) == str(account.company_id)
    FinancialAccount.objects.create(
        organization=account.organization, company=account.company,
        name="Conta incompleta antiga", account_reference="incompleta",
    )
    incomplete = client.get(configuration, {"company": account.company_id})
    assert incomplete.context["reconciliation_setup_next_action"]["state"] == "blocked"
    assert incomplete.context["reconciliation_setup_status"]["financial_accounts"] == 1


def test_configuration_creation_rolls_back_when_audit_fails(prepared):
    client = client_for(prepared)
    with (
        patch("apps.hub.views.record_event", side_effect=RuntimeError("synthetic failure")),
        pytest.raises(RuntimeError),
    ):
        client.post(reverse("hub:reconciliation-configuration"), creation_data(prepared[0]))
    assert FinancialAccount.objects.count() == 1


def test_configuration_rechecks_integrity_after_company_lock(prepared):
    client = client_for(prepared)
    with patch("apps.hub.setup_review.account_integrity_errors", side_effect=[
        {}, {"ledger_code": "O plano foi alterado durante a revisão."}, {},
    ]):
        response = client.post(
            reverse("hub:reconciliation-configuration"), creation_data(prepared[0]),
        )
    assert response.status_code == 200
    assert "ledger_code" in response.context["financial_account_form"].errors
    assert FinancialAccount.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_corrections_preserve_one_revision(prepared):
    if connection.vendor != "postgresql":
        pytest.skip("Row-level locking requires PostgreSQL")
    account = prepared[0]
    original = data(account)
    barrier = Barrier(2)

    def attempt(name):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                review(prepared, {**original, "name": name})
            except SetupReviewConflict:
                return "conflict"
            return "saved"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(attempt, ["Primeiro nome", "Segundo nome"]))
    assert sorted(results) == ["conflict", "saved"]
    assert AuditEvent.objects.filter(
        action="hub.reconciliation.financial_account.corrected",
    ).count() == 1
