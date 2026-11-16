"""Customer navigation must retain the period and the same company/module boundary."""

from __future__ import annotations

import csv
import io
from datetime import timedelta
from urllib.parse import parse_qs, urlparse
from uuid import uuid4

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.ledger_import import LEDGER_COLUMNS
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    LedgerAccount,
    MovementReconciliation,
    ProductModule,
    ReconciliationDecision,
    ReconciliationRun,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_service import create_source_file, process_run
from apps.intelligence.models import NativeLedgerCollection
from apps.organizations.models import Membership
from apps.platform.models import SupportSession

pytestmark = pytest.mark.django_db


def _login(organization, *, role="owner"):
    user = User.objects.create_user(
        f"{role}-{uuid4().hex}@client-navigation.test", "synthetic-only-password"
    )
    membership = Membership.objects.create(organization=organization, user=user, role=role)
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.pk)
    session.save()
    return client, membership


def _company(organization, name):
    company = ClientCompany.objects.create(organization=organization, name=name)
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name=f"Conta {name}",
        account_reference="001:123",
        ledger_code="1.1",
    )
    bank = (
        "OFXHEADER:100\n<OFX><BANKID>001<ACCTID>123<BANKTRANLIST>"
        "<STMTTRN><DTPOSTED>20260912<TRNAMT>100.00<FITID>sep"
        "<MEMO>Movimento sintético setembro</STMTTRN>"
        "<STMTTRN><DTPOSTED>20261012<TRNAMT>200.00<FITID>oct"
        "<MEMO>Movimento sintético outubro</STMTTRN></BANKTRANLIST></OFX>"
    ).encode()
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        financial_account=account,
        filename="extrato-sintetico.ofx",
        content=bank,
        origin="bank_statement",
    )
    assert process_run(str(run.pk))["created"] == 2
    for code in ("1.1", "2.1"):
        LedgerAccount.objects.create(
            organization=organization, company=company, code=code, name=code
        )
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(LEDGER_COLUMNS)
    for month, amount in ((9, 10000), (10, 20000)):
        writer.writerow(
            [
                f"entry-{month}",
                "bank",
                f"2026-{month:02d}-12",
                "Razão sintético",
                "1.1",
                "debit",
                amount,
                "inflow",
                f"DOC-{month}",
            ]
        )
        writer.writerow(
            [
                f"entry-{month}",
                "other",
                f"2026-{month:02d}-12",
                "Razão sintético",
                "2.1",
                "credit",
                amount,
                "",
                f"DOC-{month}",
            ]
        )
    ledger, run, _ = create_source_file(
        organization=organization,
        company=company,
        financial_account=account,
        filename="razao-sintetico.csv",
        content=output.getvalue().encode(),
        origin="accounting",
    )
    assert process_run(str(run.pk))["created"] == 2
    return dict(company=company, account=account, source=source, ledger=ledger)


@pytest.fixture
def navigation(organization, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    first = _company(organization, "Alfa fictícia")
    second = _company(organization, "Beta fictícia")
    client, membership = _login(organization)
    return dict(
        organization=organization, client=client, membership=membership, first=first, second=second
    )


def _counts():
    return {
        model.__name__: model.objects.count()
        for model in (
            AuditEvent,
            NativeLedgerCollection,
            ReconciliationSourceFile,
            ReconciliationRun,
            FinancialAccount,
            MovementReconciliation,
            ReconciliationDecision,
        )
    }


@pytest.mark.parametrize("role", ["owner", "operator", "auditor"])
def test_portfolio_reads_only_company_and_module_intersection(navigation, role):
    case = navigation
    client, membership = _login(case["organization"], role=role)
    for key, modules in (("first", ["reconciliation"]), ("second", ["payroll"])):
        CompanyAccessGrant.objects.create(
            organization=case["organization"],
            membership=membership,
            company=case[key]["company"],
            modules=modules,
            capabilities=["bank_statements", "accounting_entries"],
        )
    response = client.get(reverse("hub:reconciliation-portfolio"), {"month": "2026-09"})
    assert response.status_code == 200
    companies = {row["company"].pk for row in response.context["portfolio"]["rows"]}
    expected = {case["first"]["company"].pk}
    if role == "owner":
        expected.add(case["second"]["company"].pk)
    assert companies == expected
    assert response["Cache-Control"] == "no-store, private"


@pytest.mark.parametrize("role", ["operator", "auditor"])
@pytest.mark.parametrize("route", ["reconciliation-source-review", "reconciliation-source-report"])
def test_source_routes_refuse_other_module_or_revoked_company(navigation, role, route):
    case = navigation
    client, membership = _login(case["organization"], role=role)
    allowed = CompanyAccessGrant.objects.create(
        organization=case["organization"],
        membership=membership,
        company=case["first"]["company"],
        modules=["reconciliation"],
    )
    CompanyAccessGrant.objects.create(
        organization=case["organization"],
        membership=membership,
        company=case["second"]["company"],
        modules=["payroll"],
    )
    params = {"format": "print"} if route.endswith("report") else {}
    assert (
        client.get(reverse(f"hub:{route}", args=[case["first"]["source"].pk]), params).status_code
        == 200
    )
    assert (
        client.get(reverse(f"hub:{route}", args=[case["second"]["source"].pk]), params).status_code
        == 404
    )
    allowed.is_active = False
    allowed.save(update_fields=["is_active"])
    assert (
        client.get(reverse(f"hub:{route}", args=[case["first"]["source"].pk]), params).status_code
        == 404
    )


def test_support_session_retains_explicit_company_scope(navigation):
    case = navigation
    user = User.objects.create_user("support@client-navigation.test", "synthetic-only-password")
    support = SupportSession.objects.create(
        organization=case["organization"],
        support_user=user,
        company_ids=[str(case["first"]["company"].pk)],
        justification="Ensaio sintético somente leitura",
        expires_at=timezone.now() + timedelta(minutes=20),
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_support_session_id"] = str(support.pk)
    session.save()
    response = client.get(reverse("hub:reconciliation-portfolio"), {"month": "2026-09"})
    assert response.status_code == 200
    assert [row["company"].pk for row in response.context["portfolio"]["rows"]] == [
        case["first"]["company"].pk
    ]
    assert not response.context["portfolio"]["can_manage"]
    for route in ("reconciliation-source-review", "reconciliation-source-report"):
        assert (
            client.get(reverse(f"hub:{route}", args=[case["first"]["source"].pk])).status_code
            == 200
        )
        assert (
            client.get(reverse(f"hub:{route}", args=[case["second"]["source"].pk])).status_code
            == 404
        )


def test_portfolio_paginates_companies_including_no_account(navigation):
    case = navigation
    ClientCompany.objects.bulk_create(
        [
            ClientCompany(organization=case["organization"], name=f"Sem conta fictícia {index:02d}")
            for index in range(25)
        ]
    )
    url = reverse("hub:reconciliation-portfolio")
    first = case["client"].get(url, {"month": "2026-09"})
    second = case["client"].get(url, {"month": "2026-09", "page": "2"})
    assert len(first.context["portfolio"]["rows"]) == 25
    assert len(second.context["portfolio"]["rows"]) == 2
    assert first.context["portfolio"]["page"].paginator.count == 27
    assert "month=2026-09" in second.context["portfolio"]["querystring"]
    missing = case["client"].get(url, {"month": "2026-09", "status": "missing_account"})
    assert missing.context["portfolio"]["page"].paginator.count == 25
    assert all(not row["accounts"] for row in missing.context["portfolio"]["rows"])


@pytest.mark.parametrize(
    "query",
    [
        "month=2026-13",
        "month=2026-9",
        "month=2026-09&month=2026-10",
        "page=0",
        "page=bad",
        "status=unknown",
        "company=bad",
        "account=bad",
        "status=all&status=missing_account",
    ],
)
def test_invalid_portfolio_filters_do_not_expand_scope(navigation, query):
    response = navigation["client"].get(reverse("hub:reconciliation-portfolio") + "?" + query)
    assert response.status_code == 200
    assert response.context["portfolio"]["errors"]
    assert not response.context["portfolio"]["rows"]
    assert response.context["portfolio"]["page"].paginator.count == 0


def test_portfolio_rejects_account_from_another_selected_company(navigation):
    response = navigation["client"].get(
        reverse("hub:reconciliation-portfolio"),
        {
            "month": "2026-09",
            "company": navigation["first"]["company"].pk,
            "account": navigation["second"]["account"].pk,
        },
    )
    assert response.context["portfolio"]["errors"] and not response.context["portfolio"]["rows"]


def test_month_context_survives_conference_detail_and_reports(navigation):
    case = navigation
    portfolio = case["client"].get(
        reverse("hub:reconciliation-portfolio"),
        {
            "month": "2026-10",
            "company": case["first"]["company"].pk,
        },
    )
    source_row = portfolio.context["portfolio"]["rows"][0]["accounts"][0]["sources"][0]
    page = case["client"].get(source_row["review_url"])
    assert len(page.context["conference_rows"]) == 1
    row = page.context["conference_rows"][0]
    assert row["movement"].occurred_on.month == 10
    detail = case["client"].get(row["detail_url"])
    params = parse_qs(urlparse(detail.context["conference_return_url"]).query)
    assert params["start"] == ["2026-10-01"] and params["end"] == ["2026-10-31"]
    assert "month=2026-10" in page.context["conference_portfolio_return_url"]
    query = parse_qs(page.context["conference_report_querystring"])
    assert query["start"] == ["2026-10-01"] and query["end"] == ["2026-10-31"]


@pytest.mark.parametrize("format_value", [None, "print"])
def test_reports_apply_period_and_preserve_default_csv(navigation, format_value):
    case = navigation
    params = {"start": "2026-10-01", "end": "2026-10-31"}
    if format_value:
        params["format"] = format_value
    response = case["client"].get(
        reverse("hub:reconciliation-source-report", args=[case["first"]["source"].pk]),
        params,
    )
    assert response.status_code == 200 and response["Cache-Control"] == "no-store, private"
    content = response.content.decode("utf-8-sig")
    if format_value:
        assert response["Content-Type"].startswith("text/html")
        assert "Movimento sintético outubro" in content
        assert "Movimento sintético setembro" not in content
        assert case["first"]["company"].name in content and case["first"]["account"].name in content
        assert "R$" in content
        assert "start=2026-10-01" in response.context["report_csv_url"]
        assert "end=2026-10-31" in response.context["report_conference_url"]
    else:
        assert response["Content-Type"].startswith("text/csv")
        assert "attachment" in response["Content-Disposition"]
        assert "bank;" in content and "ledger;" in content
        assert "2026-10-12" in content and "2026-09-12" not in content


@pytest.mark.parametrize(
    "query",
    [
        "start=2026-09-31",
        "start=20260901",
        "start=2026-10-31&end=2026-10-01",
        "start=2026-09-01&start=2026-10-01",
        "end=2026-10-01&end=2026-10-31",
    ],
)
def test_invalid_report_period_never_returns_unfiltered_report(navigation, query):
    url = reverse("hub:reconciliation-source-report", args=[navigation["first"]["source"].pk])
    response = navigation["client"].get(url + "?format=print&" + query)
    assert response.status_code in {302, 400}
    assert "Movimento sintético setembro" not in response.content.decode()
    assert "Movimento sintético outubro" not in response.content.decode()


@pytest.mark.parametrize("origin", ["bank_statement", "accounting"])
def test_upload_deep_link_prefills_authorized_context_without_writes(navigation, origin):
    case = navigation
    before = _counts()
    response = case["client"].get(
        reverse("hub:reconciliation"),
        {
            "upload_company": case["first"]["company"].pk,
            "upload_account": case["first"]["account"].pk,
            "upload_origin": origin,
            "open_upload": "1",
        },
    )
    assert response.status_code == 200
    form = response.context["upload_form"]
    assert str(form["company"].value()) == str(case["first"]["company"].pk)
    assert str(form["financial_account"].value()) == str(case["first"]["account"].pk)
    assert form["origin"].value() == origin
    assert response.context["upload_open"]
    assert _counts() == before


@pytest.mark.parametrize("invalid", ["company", "account", "mismatch", "origin", "duplicate"])
def test_invalid_upload_deep_link_does_not_select_another_company(navigation, invalid):
    case = navigation
    params = {
        "upload_company": str(case["first"]["company"].pk),
        "upload_account": str(case["first"]["account"].pk),
        "upload_origin": "bank_statement",
        "open_upload": "1",
    }
    if invalid in {"company", "account"}:
        params[f"upload_{invalid}"] = str(uuid4())
    elif invalid == "mismatch":
        params["upload_account"] = str(case["second"]["account"].pk)
    elif invalid == "origin":
        params["upload_origin"] = "document"
    else:
        params["upload_company"] = [params["upload_company"], str(case["second"]["company"].pk)]
    response = case["client"].get(reverse("hub:reconciliation"), params)
    assert response.status_code == 200 and not response.context.get("upload_open")
    assert not response.context["upload_form"]["company"].value()
    assert not response.context["upload_form"]["financial_account"].value()


@pytest.mark.parametrize("role", ["operator", "auditor"])
def test_upload_link_cannot_escape_company_module_or_read_only_scope(navigation, role):
    case = navigation
    client, membership = _login(case["organization"], role=role)
    for key, modules in (("first", ["reconciliation"]), ("second", ["payroll"])):
        CompanyAccessGrant.objects.create(
            organization=case["organization"],
            membership=membership,
            company=case[key]["company"],
            modules=modules,
        )
    before = _counts()
    selected = "first" if role == "auditor" else "second"
    response = client.get(
        reverse("hub:reconciliation"),
        {
            "upload_company": case[selected]["company"].pk,
            "upload_account": case[selected]["account"].pk,
            "upload_origin": "accounting",
            "open_upload": "1",
        },
    )
    assert response.status_code == 200 and not response.context.get("upload_open")
    assert not response.context["upload_form"]["company"].value()
    assert _counts() == before


def test_read_only_navigation_creates_no_jobs_accounts_audit_or_decisions(navigation):
    case = navigation
    before = _counts()
    urls = [
        reverse("hub:reconciliation-portfolio") + "?month=2026-09",
        reverse("hub:reconciliation-portfolio") + "?month=bad",
        reverse("hub:reconciliation-source-review", args=[case["first"]["source"].pk]),
        reverse("hub:reconciliation-source-report", args=[case["first"]["source"].pk]),
        reverse("hub:reconciliation-source-report", args=[case["first"]["source"].pk])
        + "?format=print",
    ]
    for url in urls:
        assert case["client"].get(url).status_code == 200
    assert _counts() == before
