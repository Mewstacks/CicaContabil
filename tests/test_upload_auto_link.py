"""D-385: Domínio bank accounts appear in the import form and are linked from the OFX."""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.hub.models import FinancialAccount, ReconciliationLedgerMapping, ReconciliationSourceFile
from test_account_discovery import discovered as discovered_fixture
from test_account_discovery import sources as sources_fixture
from test_account_discovery_navigation import web as web_fixture
from test_discovery_ofx_prefill import synthetic_ofx, upload
from test_discovery_ofx_suggest import discovered_profile as profile_fixture

sources = sources_fixture
discovered_profile = profile_fixture
discovered = discovered_fixture
web = web_fixture
pytestmark = pytest.mark.django_db


def bank(discovered, code=901):
    return discovered.chart_accounts.get(chart_company_code=212, account_code=code)


def send(client, coverage, value, files, origin="accounting"):
    return client.post(
        reverse("hub:reconciliation-upload"),
        {
            "purpose": "general",
            "company": str(coverage.company_id),
            "financial_account": value,
            "origin": origin,
            "files": files,
        },
    )


def test_bank_accounts_of_the_chart_are_listed_for_the_company(web, discovered):
    html = web["client"].get(reverse("hub:reconciliation")).content.decode()
    assert f'value="dominio:{bank(discovered).pk}"' in html
    assert "BANCO SICREDI · conta 901 (vincula pelo OFX)" in html
    assert f'data-company-id="{web["coverage"].company_id}"' in html
    assert f'value="dominio:{bank(discovered, 903).pk}"' not in html  # cota capital


def test_choosing_the_account_with_an_ofx_links_and_imports(web, discovered):
    coverage = web["coverage"]
    response = send(
        web["client"], coverage, f"dominio:{bank(discovered).pk}", [upload(synthetic_ofx())]
    )
    assert response.status_code == 302
    account = FinancialAccount.objects.get()
    assert account.company_id == coverage.company_id
    assert account.account_reference == "748:0101:00012345-6"
    mapping = ReconciliationLedgerMapping.objects.get(financial_account=account)
    assert mapping.scope["bank_account_code"] == 901
    assert mapping.scope["bank_inflow_side"] == "debit"
    source = ReconciliationSourceFile.objects.get()
    assert source.financial_account_id == account.pk
    assert source.origin == ReconciliationSourceFile.Origin.BANK_STATEMENT
    html = web["client"].get(reverse("hub:reconciliation")).content.decode()
    assert f'value="dominio:{bank(discovered).pk}"' not in html
    again = send(web["client"], coverage, str(account.pk), [upload(synthetic_ofx(rows=3), "b.ofx")])
    assert again.status_code == 302
    assert FinancialAccount.objects.count() == 1


def test_without_ofx_nothing_is_linked(web, discovered):
    csv = upload(b"data,valor\n2026-09-01,10\n", "extrato.csv")
    response = send(web["client"], web["coverage"], f"dominio:{bank(discovered).pk}", [csv])
    assert response.status_code == 400
    assert "OFX" in response.content.decode()
    assert not FinancialAccount.objects.exists()
    assert not ReconciliationSourceFile.objects.exists()


def test_invalid_or_foreign_value_is_refused(web, discovered):
    for value in ("dominio:nao-uuid", "dominio:00000000-0000-0000-0000-000000000000"):
        response = send(web["client"], web["coverage"], value, [upload(synthetic_ofx())])
        assert response.status_code == 400
    assert not FinancialAccount.objects.exists()
