"""HTTP enrollment keeps retained facts separate from explicit human bank review."""

from __future__ import annotations

from datetime import timedelta
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    LedgerAccount,
    ProductModule,
    ReconciliationAccountCandidate,
)
from apps.intelligence.models import NativeLedgerCollection
from apps.organizations.models import Membership, Organization
from apps.platform.models import SupportSession, TenantContract

pytestmark = pytest.mark.django_db


def make_candidate(organization, company, *, code=8, case="C01", chart=1):
    observed = timezone.now()
    source_code = int(company.dominio_code)
    key = f"{source_code}:{chart}:{code}"
    return ReconciliationAccountCandidate.objects.create(
        organization=organization,
        company=company,
        source_company_code=source_code,
        chart_company_code=chart,
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
                "chart_company_code": chart,
                "account_code": code,
                "candidate_key": key,
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


def login(organization, role):
    user = User.objects.create_user(
        f"{role}@candidate-navigation.test",
        "synthetic-only-password",
        full_name="Revisora fictícia",
    )
    membership = Membership.objects.create(organization=organization, user=user, role=role)
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.pk)
    session.save()
    return client, membership


@pytest.fixture
def case(organization):
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"]
    )
    first = ClientCompany.objects.create(
        organization=organization, name="Alfa fictícia", dominio_code="101"
    )
    second = ClientCompany.objects.create(
        organization=organization, name="Beta fictícia", dominio_code="102"
    )
    candidates = [
        make_candidate(organization, first),
        make_candidate(organization, second, case="C02"),
    ]
    client, membership = login(organization, "owner")
    return {
        "organization": organization,
        "companies": [first, second],
        "candidates": candidates,
        "client": client,
        "membership": membership,
    }


def detail(candidate):
    return reverse("hub:reconciliation-account-candidate", args=[candidate.pk])


def link_data(candidate):
    return {
        "action": "link",
        "expected_source_hash": candidate.source_file_sha256,
        "expected_state": "pending",
        "name": "Banco comprovado sintético",
        "bank_code": "001",
        "account_reference": "001:0123:000456-7",
        "bank_inflow_side": "debit",
        "evidence_reference": "Extrato e plano fictícios revisados",
        "bank_association_confirmed": "on",
        "chart_owner_confirmed": "on",
        "account_active_and_postable": "on",
    }


def counts():
    return {
        model.__name__: model.objects.count()
        for model in (
            ReconciliationAccountCandidate,
            FinancialAccount,
            LedgerAccount,
            AuditEvent,
            NativeLedgerCollection,
        )
    }


@pytest.mark.parametrize("role", ["owner", "operator", "auditor"])
def test_list_and_detail_use_company_and_module_intersection(case, role):
    client, membership = (
        login(case["organization"], role)
        if role != "owner"
        else (case["client"], case["membership"])
    )
    for company, modules in zip(case["companies"], (["reconciliation"], ["payroll"]), strict=True):
        CompanyAccessGrant.objects.create(
            organization=case["organization"],
            membership=membership,
            company=company,
            modules=modules,
        )
    page = client.get(reverse("hub:reconciliation-account-candidates"))
    assert page.status_code == 200 and page["Cache-Control"] == "no-store, private"
    assert len(page.context["candidate_rows"]) == (2 if role == "owner" else 1)
    assert client.get(detail(case["candidates"][0])).status_code == 200
    assert client.get(detail(case["candidates"][1])).status_code == (
        200 if role == "owner" else 404
    )


def test_revoked_access_cannot_read_or_write_candidate(case):
    client, membership = login(case["organization"], "operator")
    grant = CompanyAccessGrant.objects.create(
        organization=case["organization"],
        membership=membership,
        company=case["companies"][0],
        modules=["reconciliation"],
    )
    candidate = case["candidates"][0]
    assert client.get(detail(candidate)).status_code == 200
    grant.is_active = False
    grant.save(update_fields=["is_active"])
    before = counts()
    assert client.get(detail(candidate)).status_code == 404
    assert client.post(detail(candidate), link_data(candidate)).status_code == 404
    assert counts() == before


def test_other_tenant_candidate_never_appears(case):
    other = Organization.objects.create(name="Outro escritório fictício", slug="candidate-other")
    company = ClientCompany.objects.create(organization=other, name="Outra", dominio_code="201")
    candidate = make_candidate(other, company)
    assert case["client"].get(detail(candidate)).status_code == 404
    page = case["client"].get(
        reverse("hub:reconciliation-account-candidates"), {"company": company.pk}
    )
    assert page.context["candidate_errors"] and not page.context["candidate_rows"]


def test_auditor_and_support_have_no_review_forms_or_post_permission(case):
    auditor, membership = login(case["organization"], "auditor")
    CompanyAccessGrant.objects.create(
        organization=case["organization"],
        membership=membership,
        company=case["companies"][0],
        modules=["reconciliation"],
    )
    support_user = User.objects.create_user("support@candidate-navigation.test", "synthetic-only")
    support = SupportSession.objects.create(
        organization=case["organization"],
        support_user=support_user,
        company_ids=[str(case["companies"][0].pk)],
        justification="QA sintético somente leitura",
        expires_at=timezone.now() + timedelta(minutes=20),
    )
    support_client = Client()
    support_client.force_login(support_user)
    session = support_client.session
    session["hub_support_session_id"] = str(support.pk)
    session.save()
    before = counts()
    for client in (auditor, support_client):
        page = client.get(detail(case["candidates"][0]))
        assert page.status_code == 200 and not page.context["can_review_candidate"]
        assert b'id="candidate-link-form"' not in page.content
        assert b'id="candidate-dismiss-form"' not in page.content
        assert client.get(detail(case["candidates"][1])).status_code == 404
        assert (
            client.post(detail(case["candidates"][0]), link_data(case["candidates"][0])).status_code
            == 403
        )
    assert counts() == before


@pytest.mark.parametrize(
    "query",
    [
        "status=unknown",
        "status=",
        "status=all&status=pending",
        "company=invalid",
        "company=",
        "company=bad&company=bad",
        "q=a&q=b",
        "page=bad",
        "page=0",
        "page=999",
        "page=1&page=2",
    ],
)
def test_invalid_list_filters_never_expand_query(case, query):
    before = counts()
    page = case["client"].get(reverse("hub:reconciliation-account-candidates") + "?" + query)
    assert page.status_code == 200 and page.context["candidate_errors"]
    assert (
        not page.context["candidate_rows"] and page.context["candidate_page"].paginator.count == 0
    )
    assert counts() == before


def test_pagination_and_detail_return_preserve_company_filters(case):
    for index in range(2, 28):
        make_candidate(
            case["organization"], case["companies"][0], code=index + 100, case=f"C{index + 1:02d}"
        )
    params = {
        "company": str(case["companies"][0].pk),
        "status": "pending",
        "q": "Alfa",
        "page": "2",
    }
    page = case["client"].get(reverse("hub:reconciliation-account-candidates"), params)
    assert page.context["candidate_page"].paginator.count == 27
    assert len(page.context["candidate_rows"]) == 2
    row = page.context["candidate_rows"][0]
    response = case["client"].get(row["url"])
    back = parse_qs(urlparse(response.context["candidate_list_url"]).query)
    assert back == {key: [value] for key, value in params.items()}
    assert response.context["candidate"].company == case["companies"][0]


def test_oversized_numeric_search_returns_error_without_integer_conversion(case):
    page = case["client"].get(reverse("hub:reconciliation-account-candidates"), {"q": "9" * 5000})
    assert page.status_code == 200 and page.context["candidate_errors"]
    assert not page.context["candidate_rows"]


def test_inconsistent_financial_account_is_not_exposed(case):
    other = Organization.objects.create(name="Outra organização", slug="candidate-corruption")
    other_company = ClientCompany.objects.create(organization=other, name="Empresa externa")
    account = FinancialAccount.objects.create(
        organization=other,
        company=other_company,
        name="Referência privada de outra organização",
        account_reference="foreign",
    )
    candidate = case["candidates"][0]
    ReconciliationAccountCandidate.objects.filter(pk=candidate.pk).update(
        financial_account=account, state="linked"
    )
    assert case["client"].get(detail(candidate)).status_code == 404
    page = case["client"].get(reverse("hub:reconciliation-account-candidates"), {"status": "all"})
    assert account.name not in page.content.decode()
    assert all(row["candidate"].pk != candidate.pk for row in page.context["candidate_rows"])


def test_detail_refuses_conflicting_company_context(case):
    before = counts()
    url = detail(case["candidates"][0]) + "?company=" + str(case["companies"][1].pk)
    assert case["client"].get(url).status_code == 400
    assert case["client"].post(url, link_data(case["candidates"][0])).status_code == 400
    assert counts() == before


def test_get_never_preapproves_bank_direction_or_checks(case):
    before = counts()
    page = case["client"].get(detail(case["candidates"][0]))
    form = page.context["review_form"]
    for name in (
        "name",
        "bank_code",
        "account_reference",
        "bank_inflow_side",
        "evidence_reference",
        "bank_association_confirmed",
        "chart_owner_confirmed",
        "account_active_and_postable",
    ):
        assert not form[name].value()
    assert counts() == before
    assert b'<details class="account-provenance">' in page.content
    assert b'id="candidate-link-form"' in page.content


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
    ],
)
def test_partial_review_does_not_create_an_account(case, field):
    candidate = case["candidates"][0]
    data = link_data(candidate)
    data.pop(field)
    before = counts()
    response = case["client"].post(detail(candidate), data)
    assert response.status_code == 400 and response.context["review_form"].errors
    assert counts() == before
    candidate.refresh_from_db()
    assert candidate.state == "pending" and not candidate.reviewed_by_id


@pytest.mark.parametrize("field", ["action", "bank_code", "bank_association_confirmed"])
def test_duplicate_post_controls_are_rejected(case, field):
    candidate = case["candidates"][0]
    data = link_data(candidate)
    data[field] = [data[field], data[field]]
    before = counts()
    assert case["client"].post(detail(candidate), data).status_code == 400
    assert counts() == before


def test_link_registers_current_actor_and_becomes_read_only(case):
    candidate = case["candidates"][0]
    data = link_data(candidate)
    data["reviewed_by"] = "invented-client-identity"
    response = case["client"].post(detail(candidate), data)
    assert response.status_code == 302
    candidate.refresh_from_db()
    assert candidate.state == "linked" and candidate.reviewed_by == case["membership"].user
    assert candidate.financial_account.account_reference == data["account_reference"]
    assert candidate.review_data["bank_inflow_side"] == "debit"
    assert not NativeLedgerCollection.objects.exists()
    page = case["client"].get(response.url)
    assert (
        not page.context["can_review_candidate"] and b'id="candidate-link-form"' not in page.content
    )
    assert "Consultar conta" in page.content.decode()
    assert str(candidate.company_id) in page.context["candidate_configuration_url"]
    before = counts()
    assert case["client"].post(detail(candidate), data).status_code == 409
    assert counts() == before


def test_dismiss_requires_reason_and_never_creates_financial_account(case):
    candidate = case["candidates"][0]
    data = {
        "action": "dismiss",
        "expected_source_hash": candidate.source_file_sha256,
        "expected_state": "pending",
    }
    assert case["client"].post(detail(candidate), data).status_code == 400
    data["reason"] = "A conta contábil representa caixa físico, confirmado no plano fictício."
    response = case["client"].post(detail(candidate), data)
    assert response.status_code == 302
    candidate.refresh_from_db()
    assert candidate.state == "dismissed" and candidate.review_evidence == data["reason"]
    assert not FinancialAccount.objects.exists() and not LedgerAccount.objects.exists()
    assert b'id="candidate-dismiss-form"' not in case["client"].get(response.url).content


def test_stale_source_and_suspended_contract_return_actionable_error(case):
    candidate = case["candidates"][0]
    data = link_data(candidate)
    data["expected_source_hash"] = "c" * 64
    before = counts()
    assert case["client"].post(detail(candidate), data).status_code == 400
    assert counts() == before
    TenantContract.objects.filter(organization=case["organization"]).update(status="suspended")
    response = case["client"].post(detail(candidate), link_data(candidate))
    assert response.status_code == 400 and response.context["review_form"].non_field_errors()
    assert counts() == before


def test_csrf_is_required_for_human_review(case):
    client = Client(enforce_csrf_checks=True)
    client.force_login(case["membership"].user)
    session = client.session
    session["hub_organization_id"] = str(case["organization"].pk)
    session.save()
    before = counts()
    assert (
        client.post(detail(case["candidates"][0]), link_data(case["candidates"][0])).status_code
        == 403
    )
    assert counts() == before


def test_detail_has_unique_form_control_ids_and_escaped_company(case):
    company = case["companies"][0]
    company.name = '<img src=x onerror="alert(1)">'
    company.save(update_fields=["name"])
    page = case["client"].get(detail(case["candidates"][0]))
    text = page.content.decode()
    assert '<img src=x onerror="alert(1)">' not in text
    assert "&lt;img" in text

    class ControlParser(HTMLParser):
        identifiers = []
        labels = []

        def handle_starttag(self, tag, attrs):
            attributes = dict(attrs)
            if tag in {"input", "textarea", "select"} and attributes.get("id", "").startswith(
                "candidate-"
            ):
                self.identifiers.append(attributes["id"])
            if tag == "label" and attributes.get("for", "").startswith("candidate-"):
                self.labels.append(attributes["for"])

    parser = ControlParser()
    parser.feed(text)
    assert len(parser.identifiers) == len(set(parser.identifiers))
    assert set(parser.labels) <= set(parser.identifiers)


def test_numeric_identifiers_are_not_formatted_as_localized_values(case, settings):
    settings.LANGUAGE_CODE = "pt-br"
    settings.USE_THOUSAND_SEPARATOR = True
    company = ClientCompany.objects.create(
        organization=case["organization"], name="Identificadores fictícios", dominio_code="1002"
    )
    candidate = make_candidate(case["organization"], company, code=1000, chart=1001, case="C03")
    page = case["client"].get(detail(candidate))
    text = page.content.decode()
    for code in ("1000", "1001", "1002"):
        assert f"<dd>{code}</dd>" in text
    assert "1.000" not in text and "1.001" not in text and "1.002" not in text
    listing = case["client"].get(
        reverse("hub:reconciliation-account-candidates"), {"company": company.pk}
    )
    text = listing.content.decode()
    assert 'data-label="Conta contábil">1000' in text
    assert 'data-label="Plano de contas">Empresa 1001' in text
    assert "1.000" not in text and "1.001" not in text
