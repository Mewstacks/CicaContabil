"""Full catalogue navigation, scoped evidence and minimal real-user confirmation."""

from __future__ import annotations

from copy import deepcopy
from urllib.parse import parse_qs, urlparse

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.hub.account_discovery import latest_consistent_discovery, prepared_account_facts
from apps.hub.models import (
    CompanyAccessGrant,
    FinancialAccount,
    ProductModule,
    ReconciliationAccountCandidate,
    ReconciliationAccountDiscovery,
    ReconciliationLedgerMapping,
)
from apps.platform.models import TenantContract
from test_account_candidate_navigation import login
from test_account_discovery import discovered as discovered_fixture
from test_account_discovery import discovered_profile as discovered_profile_fixture
from test_account_discovery import (
    run_discovery,
    scoped,
)
from test_account_discovery import sources as sources_fixture
from test_account_source_details import protected

sources = sources_fixture
discovered_profile = discovered_profile_fixture
discovered = discovered_fixture
pytestmark = pytest.mark.django_db


@pytest.fixture
def web(organization, discovered):
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"]
    )
    client, membership = login(organization, "owner")
    coverage, chart = scoped(discovered)
    return dict(client=client, membership=membership, coverage=coverage, chart=chart)


def overview():
    return reverse("hub:reconciliation-account-discovery")


def company_url(coverage):
    return reverse("hub:reconciliation-discovered-company", args=[coverage.company_id])


def detail_url(coverage, chart, month="2026-09"):
    return (
        reverse("hub:reconciliation-discovered-account", args=[coverage.company_id, chart.pk])
        + "?month="
        + month
    )


def confirmed(coverage, chart, month="2026-09"):
    prepared = prepared_account_facts(coverage, chart, month=month)
    values = dict(
        bank_code="748",
        account_reference="0001 / 000123-4",
        bank_inflow_side="debit",
        branch_code=212,
        chart_owner_confirmed=True,
        branch_scope_confirmed=True,
        bank_association_confirmed=True,
        account_active_and_postable=True,
    )
    return {
        "expected_revision": prepared["revision"],
        **{key: values[key] for key in prepared["pending_fields"]},
    }


def test_full_catalogue_includes_company_without_candidate_and_account_outside_configuration(
    web, discovered
):
    client = web["client"]
    before = protected()
    response = client.get(overview(), {"month": "2026-09"})
    assert response.status_code == 200
    assert response.context["discovery_scoped_count"] == 3
    assert "Synthetic company 214" in response.content.decode()
    coverage, account = scoped(discovered, 213, 213, 77)
    response = client.get(company_url(coverage), {"month": "2026-09", "q": "Outro nome"})
    assert response.status_code == 200
    assert response.context["discovery_page"].paginator.count == 1
    assert "Outro nome literal " in response.content.decode()
    response = client.get(detail_url(coverage, account))
    assert response.status_code == 200
    assert "chart_owner_confirmed" in response.context["discovery_form"].fields
    assert protected() == before


def test_known_fields_are_readonly_and_only_unproven_fields_are_requested(web):
    response = web["client"].get(detail_url(web["coverage"], web["chart"]))
    assert response.status_code == 200
    fields = response.context["discovery_form"].fields
    assert {
        "name",
        "account_code",
        "chart_company_code",
        "branch_code",
        "chart_owner_confirmed",
    }.isdisjoint(fields)
    assert {
        "bank_code",
        "account_reference",
        "bank_inflow_side",
        "bank_association_confirmed",
        "account_active_and_postable",
    } <= fields.keys()
    assert not fields["evidence_reference"].required
    assert "checked" not in response.content.decode().split('id="discovery-link-form"')[1]
    assert response["Cache-Control"] == "no-store, private"
    assert response["X-Content-Type-Options"] == "nosniff"


def test_confirm_once_then_ready_link_replay_preserves_existing_candidates(web):
    coverage, chart = web["coverage"], web["chart"]
    before_candidates = list(ReconciliationAccountCandidate.objects.order_by("pk").values())
    data = confirmed(coverage, chart)
    response = web["client"].post(detail_url(coverage, chart), data)
    assert response.status_code == 302
    assert FinancialAccount.objects.count() == ReconciliationLedgerMapping.objects.count() == 1
    response = web["client"].get(response.url)
    assert response.status_code == 200
    assert response.context["discovery_prepared"]["collection_ready"]
    assert "Buscar Razão desta competência" in response.content.decode()
    assert 'id="discovery-link-form"' not in response.content.decode()
    query = parse_qs(urlparse(response.context["discovery_ledger_url"]).query)
    assert query["month"] == ["2026-09"]
    assert query["company"] == [str(coverage.company_id)]
    repeated = web["client"].post(detail_url(coverage, chart), data)
    assert repeated.status_code in (302, 409)
    assert FinancialAccount.objects.count() == 1
    assert list(ReconciliationAccountCandidate.objects.order_by("pk").values()) == before_candidates


def test_invalid_post_preserves_bank_input_and_shows_field_errors(web):
    data = confirmed(web["coverage"], web["chart"])
    data.update(
        bank_code="", account_reference="0000 / preservar", bank_association_confirmed=False
    )
    response = web["client"].post(detail_url(web["coverage"], web["chart"]), data)
    assert response.status_code == 400
    assert response.context["discovery_form"]["account_reference"].value() == "0000 / preservar"
    assert 'aria-invalid="true"' in response.content.decode()
    assert not FinancialAccount.objects.exists()


def test_new_month_reuses_confirmed_bank_identity_and_only_requests_missing_scope(web):
    coverage, chart = web["coverage"], web["chart"]
    assert (
        web["client"].post(detail_url(coverage, chart), confirmed(coverage, chart)).status_code
        == 302
    )
    response = web["client"].get(detail_url(coverage, chart, "2026-10"))
    assert response.status_code == 200
    fields = response.context["discovery_form"].fields
    assert {
        "bank_code",
        "account_reference",
        "bank_inflow_side",
        "bank_association_confirmed",
    }.isdisjoint(fields)
    assert "chart_owner_confirmed" in fields
    assert "branch_code" in fields
    assert "month=2026-10" in response.context["discovery_back_url"]


def test_dismissed_candidate_is_visible_without_form_and_cannot_be_bypassed(web):
    coverage, chart = web["coverage"], web["chart"]
    data = confirmed(coverage, chart)
    candidate = ReconciliationAccountCandidate.objects.get(company=coverage.company)
    candidate.state = "dismissed"
    candidate.review_evidence = "Synthetic prior decision"
    candidate.save()
    before = protected()
    response = web["client"].get(detail_url(coverage, chart))
    assert response.status_code == 200
    assert not response.context["discovery_can_confirm"]
    assert "Consultar conferência anterior" in response.content.decode()
    assert 'id="discovery-link-form"' not in response.content.decode()
    assert web["client"].post(detail_url(coverage, chart), data).status_code == 409
    assert protected() == before


def test_zero_branch_requires_technical_fix_and_does_not_request_invented_confirmation(
    organization, sources, discovered_profile, web
):
    data = deepcopy(discovered_profile)
    data["observed_at_utc"] = "2026-11-15T18:00:00.0000000Z"
    for row in data["snapshot"]["observed_chart_usage"]:
        if row["company_code"] == 212:
            row["branch_code"] = 0
    run_discovery(organization, sources, data, apply=True)
    coverage, chart = scoped(latest_consistent_discovery(organization))
    before = protected()
    response = web["client"].get(detail_url(coverage, chart))
    assert response.status_code == 200
    assert "ajuste técnico" in response.content.decode()
    assert not response.context["discovery_can_confirm"]
    assert 'id="discovery-link-form"' not in response.content.decode()
    assert (
        web["client"].post(detail_url(coverage, chart), confirmed(coverage, chart)).status_code
        == 409
    )
    assert protected() == before


@pytest.mark.parametrize(
    "query",
    [
        "month=2026-00",
        "month=invalid",
        "month=2026-09&month=2026-10",
        "page=0",
        "page=9999999",
        "q=" + "a" * 101,
        "chart=999999999999999",
    ],
)
def test_invalid_filters_do_not_broaden_query(web, query):
    response = web["client"].get(overview() + "?" + query)
    assert response.status_code == 400
    assert not response.context["discovery_rows"]


def test_unknown_chart_and_out_of_range_page_have_actionable_empty_state(web):
    for query in ({"chart": 9999, "month": "2026-09"}, {"page": 999, "month": "2026-09"}):
        response = web["client"].get(company_url(web["coverage"]), query)
        assert response.status_code == 400
        assert not response.context["discovery_rows"]
        assert "Rever filtros" in response.content.decode()


def test_month_changes_branch_confirmation_and_preserves_context(web, discovered):
    coverage, chart = scoped(discovered, 213, 99, 8)
    september = web["client"].get(detail_url(coverage, chart, "2026-09"))
    october = web["client"].get(detail_url(coverage, chart, "2026-10"))
    assert "branch_scope_confirmed" in september.context["discovery_form"].fields
    assert "branch_code" not in october.context["discovery_form"].fields
    assert "mesmo lote" in september.content.decode()
    assert "month=2026-10" in october.context["discovery_back_url"]


@pytest.mark.parametrize("role", ["operator", "auditor"])
def test_company_and_module_permissions_apply_to_shared_catalogue(
    organization, web, discovered, role
):
    client, member = login(organization, role)
    CompanyAccessGrant.objects.create(
        organization=organization,
        membership=member,
        company=web["coverage"].company,
        modules=["reconciliation"],
    )
    response = client.get(overview(), {"month": "2026-09"})
    assert response.status_code == 200
    assert response.context["discovery_scoped_count"] == 1
    allowed = client.get(detail_url(web["coverage"], web["chart"]))
    assert allowed.status_code == 200
    assert allowed.context["discovery_can_confirm"] == (role == "operator")
    coverage, chart = scoped(discovered, 213, 99, 8)
    assert client.get(company_url(coverage)).status_code in (403, 404)
    assert client.get(detail_url(coverage, chart)).status_code in (403, 404)
    assert client.post(detail_url(coverage, chart), confirmed(coverage, chart)).status_code in (
        403,
        404,
    )
    if role == "auditor":
        assert (
            client.post(
                detail_url(web["coverage"], web["chart"]), confirmed(web["coverage"], web["chart"])
            ).status_code
            == 403
        )
    assert not FinancialAccount.objects.exists()


def test_login_and_csrf_are_required(web):
    url = detail_url(web["coverage"], web["chart"])
    assert Client().get(url).status_code == 302
    client = Client(enforce_csrf_checks=True)
    client.force_login(web["membership"].user)
    session = client.session
    session["hub_organization_id"] = str(web["coverage"].organization_id)
    session.save()
    assert client.post(url, confirmed(web["coverage"], web["chart"])).status_code == 403
    assert not FinancialAccount.objects.exists()


def test_disabled_module_does_not_expose_catalogue(organization, web):
    ProductModule.objects.filter(organization=organization).update(enabled=False)
    response = web["client"].get(overview())
    assert response.status_code in (200, 403)
    assert "Synthetic company" not in response.content.decode()
    assert web["client"].get(detail_url(web["coverage"], web["chart"])).status_code == 404


def test_tampered_revision_and_duplicate_fields_do_not_write(web):
    data = confirmed(web["coverage"], web["chart"])
    data["expected_revision"] = "f" * 64
    assert web["client"].post(detail_url(web["coverage"], web["chart"]), data).status_code == 409
    data = confirmed(web["coverage"], web["chart"])
    data["bank_code"] = ["001", "748"]
    assert web["client"].post(detail_url(web["coverage"], web["chart"]), data).status_code == 400
    assert not FinancialAccount.objects.exists()


def test_catalogue_paginates_with_bounded_queries_and_retains_search(
    organization, sources, discovered_profile, web
):
    data = deepcopy(discovered_profile)
    data["observed_at_utc"] = "2026-11-15T18:00:00.0000000Z"
    sample = data["snapshot"]["chart_accounts"][0]
    data["snapshot"]["chart_accounts"].extend(
        dict(
            sample,
            chart_company_code=212,
            account_code=1000 + n,
            account_name_raw=f"Conta teste {n:03d}",
            classification_raw=f"1.100.{n:03d}",
        )
        for n in range(60)
    )
    run_discovery(organization, sources, data, apply=True)
    batch = latest_consistent_discovery(organization)
    coverage, _ = scoped(batch)
    with CaptureQueriesContext(connection) as queries:
        response = web["client"].get(
            company_url(coverage), {"month": "2026-09", "q": "Conta teste", "page": 2}
        )
    assert response.status_code == 200
    assert len(response.context["discovery_rows"]) == 25
    assert response.context["discovery_page"].paginator.count == 60
    assert "q=Conta+teste" in response.context["discovery_querystring"]
    assert len(queries) < 40


def test_missing_discovery_has_safe_empty_state(organization):
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    client, _ = login(organization, "owner")
    response = client.get(overview(), {"month": "2026-09"})
    assert response.status_code == 200
    assert "Aguardando consulta" in response.content.decode()
    assert ReconciliationAccountDiscovery.objects.count() == 0
