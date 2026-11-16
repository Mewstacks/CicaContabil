"""Retained synthetic suggestions are reviewed without any new provider call."""

from copy import deepcopy
from unittest.mock import Mock, patch

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    LedgerAccount,
    ProductModule,
    ReconciliationRule,
)
from apps.intelligence.models import DeparaAiBatch, EgressAudit
from apps.intelligence.native_title_contract import canonical_hash
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantContract

pytestmark = pytest.mark.django_db


def make_batch(organization, user, *, name="Empresa fictícia"):
    company = ClientCompany.objects.create(organization=organization, name=name)
    account = FinancialAccount.objects.create(
        organization=organization, company=company, name="Banco fictício",
        account_reference="SYNTHETIC-1", ledger_code="1000",
    )
    accounts = []
    for code in ("1000", "2000", "3000"):
        ledger = LedgerAccount.objects.create(
            organization=organization, company=company, code=code,
            name=f"Conta fictícia {code}",
        )
        accounts.append({"code": code, "name": ledger.name})
    context = {
        "generation_profile": "depara-compact-v2",
        "items": [{"reference": "synthetic", "description": "Tarifa fictícia",
                   "direction": "outflow"}],
        "accounts": accounts, "bank_code": account.ledger_code,
        "account_reference": account.account_reference, "company_id": str(company.pk),
    }
    batch = DeparaAiBatch.objects.create(
        organization=organization, financial_account=account, requested_by=user,
        fingerprint=canonical_hash(context), context=context, state="succeeded",
        suggestions=[{"reference": "item_1", "debit": "2000", "credit": "1000"}],
    )
    return account, batch


@pytest.fixture
def case(organization, user, membership, client):
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"],
    )
    account, batch = make_batch(organization, user)
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.pk)
    session.save()
    return {"account": account, "batch": batch, "client": client,
            "membership": membership, "organization": organization, "user": user}


def url(case):
    return reverse("hub:reconciliation-depara-batch", args=[case["batch"].pk])


def data(case):
    response = case["client"].get(url(case))
    assert response.status_code == 200
    return {
        "action": "review",
        "expected_token": response.context["depara_form"]["expected_token"].value(),
        "confirmed": "on", "choice-0-selected": "on", "choice-0-debit": "2000",
        "choice-0-credit": "1000", "choice-0-history": "Tarifa conferida em exemplo fictício",
    }


def test_get_and_explicit_review_never_generate_or_activate(case):
    original = (AuditEvent.objects.count(), EgressAudit.objects.count())
    with patch("apps.intelligence.depara_ai.generate_claude_fallback_completion") as provider:
        listing = case["client"].get(reverse("hub:reconciliation-depara"))
        payload = data(case)
        assert listing.status_code == 200
        assert (AuditEvent.objects.count(), EgressAudit.objects.count()) == original
        response = case["client"].post(url(case), payload)
        assert response.status_code == 200
        rule = ReconciliationRule.objects.get()
        assert rule.state == "draft" and rule.actions["require_review"]
        assert rule.actions["debit_account_code"] == "2000"
        assert "no-store" in response["Cache-Control"]
        assert response["X-Content-Type-Options"] == "nosniff"
        assert str(case["account"].company_id) in response.context["depara_rules_url"]
        assert case["client"].post(url(case), payload).status_code == 200
        assert ReconciliationRule.objects.count() == 1
        assert not EgressAudit.objects.exists()
        provider.assert_not_called()


@pytest.mark.parametrize("missing", ["confirmed", "choice-0-history", "choice-0-selected"])
def test_human_review_fields_are_required(case, missing):
    payload = data(case)
    payload.pop(missing)
    assert case["client"].post(url(case), payload).status_code == 400
    assert not ReconciliationRule.objects.exists()


@pytest.mark.parametrize("tamper", ["token", "suggestions", "account", "ledger", "extra_ledger"])
def test_concurrent_context_change_rejects_old_browser_review(case, tamper):
    payload = data(case)
    if tamper == "token":
        payload["expected_token"] += "invalid"
    elif tamper == "suggestions":
        DeparaAiBatch.objects.filter(pk=case["batch"].pk).update(
            suggestions=[{"reference": "item_1", "debit": "3000", "credit": "1000"}],
        )
    elif tamper == "account":
        FinancialAccount.objects.filter(pk=case["account"].pk).update(name="Nome corrigido")
    elif tamper == "ledger":
        LedgerAccount.objects.filter(company=case["account"].company, code="3000").update(
            name="Nome corrigido",
        )
    else:
        LedgerAccount.objects.create(
            organization=case["organization"], company=case["account"].company,
            code="4000", name="Nova conta fictícia",
        )
    response = case["client"].post(url(case), payload)
    assert response.status_code in {400, 409}
    assert not ReconciliationRule.objects.exists()


def test_auditor_can_neither_open_private_suggestions_nor_post(case):
    payload = data(case)
    case["membership"].role = "auditor"
    case["membership"].save()
    CompanyAccessGrant.objects.create(
        organization=case["organization"], company=case["account"].company,
        membership=case["membership"], modules=["reconciliation"],
    )
    response = case["client"].get(url(case))
    assert response.status_code == 403
    assert "Tarifa fictícia" not in response.content.decode()
    assert case["client"].post(url(case), payload).status_code == 403
    assert not ReconciliationRule.objects.exists()


def test_operator_scope_uses_same_company_module_grant(case):
    other_account, other_batch = make_batch(case["organization"], case["user"], name="Restrita")
    case["membership"].role = "operator"
    case["membership"].save()
    CompanyAccessGrant.objects.create(
        organization=case["organization"], company=case["account"].company,
        membership=case["membership"], modules=["reconciliation"],
    )
    CompanyAccessGrant.objects.create(
        organization=case["organization"], company=other_account.company,
        membership=case["membership"], modules=["payroll"],
    )
    assert case["client"].get(url(case)).status_code == 200
    response = case["client"].get(
        reverse("hub:reconciliation-depara-batch", args=[other_batch.pk]),
    )
    assert response.status_code == 404
    listing = case["client"].get(reverse("hub:reconciliation-depara"))
    assert "Restrita" not in listing.content.decode()


def test_explicit_company_filter_never_lists_other_authorized_company(case):
    _, other_batch = make_batch(case["organization"], case["user"], name="Outra autorizada")
    response = case["client"].get(reverse("hub:reconciliation-depara"), {
        "company": str(case["account"].company_id),
    })
    assert response.status_code == 200
    assert [row["batch"].pk for row in response.context["depara_rows"]] == [case["batch"].pk]
    assert str(other_batch.pk) not in response.content.decode()
    assert "company=" in response.context["depara_querystring"]


def test_other_office_token_and_batch_are_not_usable(case):
    payload = data(case)
    outsider = User.objects.create_user("other@depara.test", "synthetic-test-password")
    organization = Organization.objects.create(name="Outro escritório fictício", slug="other-dp")
    Membership.objects.create(organization=organization, user=outsider, role="owner")
    other_client = Client()
    other_client.force_login(outsider)
    session = other_client.session
    session["hub_organization_id"] = str(organization.pk)
    session.save()
    assert other_client.post(url(case), payload).status_code == 404
    assert not ReconciliationRule.objects.exists()


def test_same_office_other_actor_cannot_reuse_review_token(case):
    payload = data(case)
    reviewer = User.objects.create_user("reviewer@depara.test", "synthetic-test-password")
    Membership.objects.create(organization=case["organization"], user=reviewer, role="admin")
    case["client"].force_login(reviewer)
    session = case["client"].session
    session["hub_organization_id"] = str(case["organization"].pk)
    session.save()
    assert case["client"].post(url(case), payload).status_code == 409
    assert not ReconciliationRule.objects.exists()


def test_failed_audit_rolls_back_all_drafts(case):
    payload = data(case)
    with (
        patch("apps.intelligence.depara_ai.record_event", side_effect=RuntimeError("synthetic")),
        pytest.raises(RuntimeError, match="synthetic"),
    ):
        case["client"].post(url(case), payload)
    assert not ReconciliationRule.objects.exists()


@pytest.mark.parametrize("query,status", [
    ("page=0", 400), ("page=x", 400), ("page=1&page=2", 400), ("account=&account=", 404),
])
def test_invalid_list_filters_never_expand_query(case, query, status):
    response = case["client"].get(reverse("hub:reconciliation-depara") + "?" + query)
    assert response.status_code == status
    if status == 400:
        assert not response.context["depara_rows"]
    assert str(case["batch"].pk) not in response.content.decode()


def test_duplicate_post_field_is_rejected(case):
    payload = data(case)
    payload["choice-0-debit"] = ["2000", "3000"]
    assert case["client"].post(url(case), payload).status_code == 400
    assert not ReconciliationRule.objects.exists()


def test_missing_verified_chart_exposes_configuration_without_inferring_accounts(case, monkeypatch):
    # A retained native review packet may exist before its accounts are approved.
    packet = {
        "choices": deepcopy(case["batch"].suggestions),
        "context": case["batch"].context, "requires_chart_review": True,
    }
    reader = Mock(return_value=packet)
    monkeypatch.setattr("apps.hub.depara_review_views.depara_review_packet", reader)
    LedgerAccount.objects.filter(company=case["account"].company).delete()
    response = case["client"].get(url(case))
    assert response.status_code == 200 and not response.context["depara_chart_ready"]
    html = response.content.decode()
    assert "Conferir ou cadastrar contas" in html
    assert "disabled" in html
    assert not LedgerAccount.objects.exists() and not ReconciliationRule.objects.exists()


def test_legacy_chart_changed_is_actionable_and_does_not_reprepare(case):
    LedgerAccount.objects.filter(company=case["account"].company).update(active=False)
    response = case["client"].get(url(case))
    assert response.status_code == 400
    assert "Conferir ou cadastrar contas" in response.content.decode()
    assert DeparaAiBatch.objects.count() == 1 and not EgressAudit.objects.exists()


def test_review_requires_csrf(case):
    payload = data(case)
    client = Client(enforce_csrf_checks=True)
    client.cookies = case["client"].cookies
    assert client.post(url(case), payload).status_code == 403
    assert not ReconciliationRule.objects.exists()


def test_four_suggestions_keep_individual_selection_and_history(case):
    batch = case["batch"]
    context = deepcopy(batch.context)
    context["items"] = [
        {"reference": f"synthetic-{index}", "description": f"Tarifa fictícia {index}",
         "direction": "outflow"} for index in range(1, 5)
    ]
    batch.context, batch.fingerprint = context, canonical_hash(context)
    batch.suggestions = [
        {"reference": f"item_{index}", "debit": "2000", "credit": "1000"}
        for index in range(1, 5)
    ]
    batch.save()
    response = case["client"].get(url(case))
    assert len(response.context["depara_choices"]) == 4
    assert all(not row["form"]["selected"].value() for row in response.context["depara_choices"])
    payload = data(case)
    payload.update({
        "choice-3-selected": "on", "choice-3-debit": "3000", "choice-3-credit": "1000",
        "choice-3-history": "Quarta sugestão conferida",
    })
    response = case["client"].post(url(case), payload)
    assert response.status_code == 200
    assert ReconciliationRule.objects.filter(state="draft").count() == 2


def test_unknown_post_fields_fail_closed(case):
    payload = data(case)
    payload["generate"] = "on"
    assert case["client"].post(url(case), payload).status_code == 400
    assert not ReconciliationRule.objects.exists() and not EgressAudit.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_retained_reviews_preserve_one_draft_and_no_provider_call(case):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connection

    from apps.intelligence.depara_ai import review_depara_ai

    if connection.vendor != "postgresql":
        pytest.skip("Concurrent draft creation requires PostgreSQL row locks.")
    barrier = Barrier(2)
    choices = [{"reference": "item_1", "debit": "2000", "credit": "1000",
                "history": "Exemplo concorrente revisado"}]

    def review():
        close_old_connections()
        try:
            barrier.wait(timeout=15)
            return review_depara_ai(
                batch=case["batch"], actor=case["user"], choices=choices,
            )[0].status
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(lambda _: review(), range(2)))
    assert sorted(outcomes) == ["draft", "preserved"]
    assert ReconciliationRule.objects.filter(state="draft").count() == 1
    assert not EgressAudit.objects.exists()
