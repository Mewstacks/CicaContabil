"""D-420: a tela acha o plano de contas da empresa pela descoberta D-373 (dados sintéticos)."""

from __future__ import annotations

import pytest

from apps.hub.models import ClientCompany
from apps.hub.multisource.suggested_accounts import chart_for_company
from test_account_discovery import discovered, discovered_profile, sources  # noqa: F401

pytestmark = pytest.mark.django_db


def test_chart_for_company_reads_the_discovered_chart(discovered):  # noqa: F811
    record = discovered.company_coverage.select_related("company").get(source_company_code=212)
    chart = chart_for_company(record.company)
    assert chart is not None and len(chart) > 0
    assert any(account.code == 8 for account in chart.accounts)


def test_company_without_discovery_has_no_chart(organization):
    company = ClientCompany.objects.create(organization=organization, name="Sem plano")
    assert chart_for_company(company) is None
