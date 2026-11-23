"""D-384: an OFX suggests the chart account of its bank; linking stays human."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from apps.hub.account_discovery_suggest import suggest_accounts, suggested_inflow_side
from apps.hub.account_discovery_views import SESSION_PREFILL
from apps.hub.models import CompanyAccessGrant, FinancialAccount
from test_account_candidate_navigation import login
from test_account_discovery import discovered as discovered_fixture
from test_account_discovery import discovery_profile, run_import
from test_account_discovery import sources as sources_fixture
from test_account_discovery_navigation import company_url, confirmed, detail_url
from test_account_discovery_navigation import web as web_fixture
from test_discovery_ofx_prefill import state, synthetic_ofx, upload

sources = sources_fixture
discovered = discovered_fixture
web = web_fixture
pytestmark = pytest.mark.django_db

BANK_ROWS = [
    (900, "DEPÓSITOS BANCÁRIOS", "1101002", "S"),
    (901, "BANCO SICREDI", "1101002004", "A"),
    (902, "BANCO ITAÚ", "1101002002", "A"),
    (903, "COTA CAPITAL SICREDI", "1101005001", "A"),
]


@pytest.fixture
def discovered_profile(organization, sources):
    run_import(organization, sources, apply=True)
    data = discovery_profile(sources)
    for code, name, classification, kind in BANK_ROWS:
        data["snapshot"]["chart_accounts"].append(
            dict(
                chart_company_code=212,
                account_code=code,
                account_name_raw=name,
                classification_raw=classification,
                account_type_raw=kind,
                account_status_raw="A",
                inactive_on_raw=None,
            )
        )
    return data


def account(plan, code, name, classification, kind="A", status="A"):
    return SimpleNamespace(
        chart_company_code=plan,
        account_code=code,
        row=dict(
            account_name_raw=name,
            classification_raw=classification,
            account_type_raw=kind,
            account_status_raw=status,
        ),
    )


def codes(items):
    return [item.account.account_code for item in items]


def test_ranks_bank_name_inside_bank_group_first():
    chart = [
        account(1, 1, "CAIXA GERAL", "1101001001"),
        account(1, 2, "DEPÓSITOS BANCÁRIOS", "1101002", "S"),
        account(1, 3, "BANCO ITAÚ", "1101002001"),
        account(1, 4, "SICREDI", "1101002002"),
        account(1, 5, "COTA CAPITAL SICREDI", "1101005001"),
        account(1, 6, "SICREDI APLICAÇÃO", "1101002003"),
        account(1, 7, "BANCO SICREDI ANTIGO", "1101002004", status="I"),
        account(1, 8, "FORNECEDOR SICREDI", "2101001001"),
    ]
    result = suggest_accounts(chart, bank_id="0748", account_id="00012345-6")
    assert codes(result) == [4, 3]
    assert "O nome corresponde ao banco do extrato" in result[0].reasons
    assert result[1].reasons == ("Está no grupo de bancos do plano",)


def test_account_number_in_name_breaks_ties_and_caixa_is_not_cef():
    chart = [
        account(1, 2, "BANCOS CONTA MOVIMENTO", "1101002", "S"),
        account(1, 3, "BANCO ITAÚ - CONTA 19434-2", "1101002001"),
        account(1, 4, "BANCO ITAÚ", "1101002002"),
        account(1, 5, "CAIXA", "1101001001"),
    ]
    assert codes(suggest_accounts(chart, bank_id="341", account_id="0019434-2")) == [3, 4]
    assert codes(suggest_accounts(chart, bank_id="104", account_id="1")) == [3, 4]


def test_unknown_bank_still_lists_bank_group_and_limit_applies():
    chart = [account(1, 2, "DEPÓSITOS BANCÁRIOS", "1101002", "S")] + [
        account(1, 10 + i, f"BANCO {i}", f"110100200{i}") for i in range(8)
    ]
    assert len(suggest_accounts(chart, bank_id="999", account_id="1")) == 5
    assert suggest_accounts([], bank_id="748", account_id="1") == []


def test_inflow_side_suggested_only_for_asset_accounts():
    assert suggested_inflow_side({"classification_raw": "1.1.01.002"}) == "debit"
    assert suggested_inflow_side({"classification_raw": "2101"}) == ""
    assert suggested_inflow_side({}) == ""


def suggest(client, coverage, content=None, name="extrato.ofx"):
    return client.post(
        company_url(coverage) + "?month=2026-09",
        {"action": "suggest", "statement": upload(content or synthetic_ofx(), name)},
    )


def test_company_page_suggests_and_prefills_without_writing(web, discovered):
    coverage = web["coverage"]
    before = state()
    response = suggest(web["client"], coverage)
    assert response.status_code == 200
    assert state() == before
    suggestions = response.context["discovery_suggestions"]
    assert [item["account"].account_code for item in suggestions][:2] == [901, 902]
    assert suggestions[0]["best"]
    html = response.content.decode()
    assert "Mais provável" in html and "Usar esta conta" in html
    assert response["Cache-Control"] == "no-store, private"
    chart = discovered.chart_accounts.get(chart_company_code=212, account_code=901)
    page = web["client"].get(suggestions[0]["url"])
    assert page.status_code == 200
    form = page.context["discovery_form"]
    assert not form.is_bound
    assert form["bank_code"].value() == "748"
    assert form["account_reference"].value() == "748:0101:00012345-6"
    assert form["bank_inflow_side"].value() == "debit"
    assert not form["bank_association_confirmed"].value()
    assert "Dados lidos do extrato. Confira antes de confirmar." in page.content.decode()
    assert state() == before
    data = confirmed(coverage, chart)
    data.update(bank_code="748", account_reference="748:0101:00012345-6")
    assert web["client"].post(detail_url(coverage, chart), data).status_code == 302
    assert FinancialAccount.objects.get().account_reference == "748:0101:00012345-6"
    assert SESSION_PREFILL not in web["client"].session


def test_recalled_identity_is_scoped_to_company_and_expires(web, discovered, monkeypatch):
    coverage = web["coverage"]
    assert suggest(web["client"], coverage).status_code == 200
    other = discovered.company_coverage.exclude(pk=coverage.pk).first()
    session = web["client"].session
    session[SESSION_PREFILL]["company_id"] = str(other.company_id)
    session.save()
    chart = discovered.chart_accounts.get(chart_company_code=212, account_code=901)
    assert web["client"].get(detail_url(coverage, chart)).context["discovery_prefill"] is None
    assert suggest(web["client"], coverage).status_code == 200
    session = web["client"].session
    session[SESSION_PREFILL]["stored_at"] = "2000-01-01T00:00:00+00:00"
    session.save()
    assert web["client"].get(detail_url(coverage, chart)).context["discovery_prefill"] is None


@pytest.mark.parametrize(
    ("content", "name"),
    [(b"not an ofx", "extrato.ofx"), (synthetic_ofx(), "extrato.csv")],
)
def test_invalid_file_suggests_nothing(web, content, name):
    before = state()
    response = suggest(web["client"], web["coverage"], content, name)
    assert response.status_code == 400
    assert response.context["discovery_suggestions"] == []
    assert response.context["discovery_suggest_error"]
    assert SESSION_PREFILL not in web["client"].session
    assert state() == before


def test_read_only_profile_cannot_suggest(organization, web):
    client, member = login(organization, "auditor")
    CompanyAccessGrant.objects.create(
        organization=organization,
        membership=member,
        company=web["coverage"].company,
        modules=["reconciliation"],
    )
    page = client.get(company_url(web["coverage"]) + "?month=2026-09")
    assert page.status_code == 200
    assert 'id="discovery-suggest-form"' not in page.content.decode()
    assert suggest(client, web["coverage"]).status_code == 403
