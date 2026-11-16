from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest
from django.db import connection
from django.http import QueryDict
from django.template.loader import render_to_string
from django.test import RequestFactory
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from tests.test_reconciliation_workbench import make_case

from apps.hub.models import ClientCompany, FinancialAccount, MovementReconciliation
from apps.hub.reconciliation_report import (
    build_source_report,
    render_conference_csv,
    report_period_params,
    report_presentation_context,
)
from apps.hub.reconciliation_service import ReconciliationError
from apps.hub.reconciliation_workbench import (
    conference_return_url,
    portfolio_return_url,
    source_review_context,
)
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def case(organization, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return make_case(organization)


@pytest.mark.parametrize(
    "query",
    [
        "start=2026-09-12&start=2026-09-12",
        "end=2026-09-12&end=2026-09-13",
        "start=",
        "end=",
        "start=20260912",
        "start=2026-W37-6",
        "start=2026-02-30",
        "start=2026-09-13&end=2026-09-12",
    ],
)
def test_period_rejects_ambiguous_or_invalid_dates_before_reading(case, query):
    request = RequestFactory().get("/?" + query)
    with (
        CaptureQueriesContext(connection) as captured,
        pytest.raises(ReconciliationError, match="Confira o período solicitado"),
    ):
        source_review_context(case["source"], request)
    assert not captured.captured_queries


def test_period_accepts_only_canonical_dates_and_keeps_omissions():
    assert report_period_params(QueryDict("start=2026-09-12")) == {
        "start": date(2026, 9, 12),
        "end": None,
    }
    assert report_period_params(QueryDict("")) == {"start": None, "end": None}


def test_report_carries_both_histories_documents_sources_and_exact_amounts(case):
    source = case["source"]
    movement = source.movements.get(source_key="ofx:test-0")
    record = case["ledger"].ledger_records.get(external_key="entry-0")
    MovementReconciliation.objects.create(
        organization=source.organization,
        movement=movement,
        entry=record.entry,
        amount_cents=2500,
        state="confirmed",
        confirmed_by=case["user"],
        confirmed_at=timezone.now(),
    )
    with CaptureQueriesContext(connection) as captured:
        report = build_source_report(source)
        context = report_presentation_context(source, report)
        html = render_to_string("hub/reconciliation_print_report.html", context)
    writes = [
        query["sql"]
        for query in captured
        if query["sql"].lstrip().split()[0].upper() in {"INSERT", "UPDATE", "DELETE"}
    ]
    assert writes == []
    bank = next(
        row for row in context["report_sections"][0]["rows"] if row["reference"] == str(movement.pk)
    )
    assert bank["history"] == "Recebimento sintético 0"
    assert bank["state_label"] == "Parcial"
    assert bank["amount_label"] == "R$ 100,00"
    assert bank["allocated_label"] == "R$ 25,00"
    assert bank["remaining_label"] == "R$ 75,00"
    ledger = next(
        row for row in context["report_sections"][1]["rows"] if row["reference"] == str(record.pk)
    )
    assert ledger["history"] == "Razão independente sintético 0"
    assert ledger["document"] == "DOC-0"
    assert ledger["source_position"] == "Linhas 2, 3"
    assert ledger["state_label"] == "Parcial"
    for text in (
        case["company"].name,
        case["account"].name,
        "001:123",
        "12/09/2026",
        "extrato-teste.ofx",
        "razao-teste.csv",
        source.content_hash,
        "DOC-0",
        "Não informado",
        "Cobertura e aceite pendentes",
    ):
        assert text in html
    assert len(context["report_sources"]) == 2
    assert len(report["bank_rows"]) == len(report["ledger_rows"]) == 3
    assert context["report_sections"][0]["pending_count"] == 3
    assert context["report_generated_label"]


def test_zero_amount_stays_pending_and_unknown_balance_is_not_zero(case):
    case["source"].movements.filter(source_key="ofx:test-0").update(amount_cents=0)
    report = build_source_report(case["source"])
    context = report_presentation_context(case["source"], report)
    zero = next(row for row in context["report_sections"][0]["rows"] if row["amount_cents"] == 0)
    assert zero["state"] == "pending" and zero["state_label"] == "A conferir"
    assert all(balance["value"] == "Não informado" for balance in context["report_balances"])
    supplied = report_presentation_context(
        case["source"], build_source_report(case["source"], opening_ledger_cents=0)
    )
    assert supplied["report_balances"][2]["value"] == "R$ 0,00"


def test_report_html_escapes_imported_text_and_csv_contract_is_unchanged(case):
    source = case["source"]
    source.original_filename = '<script>alert("source")</script>.ofx'
    source.save(update_fields=["original_filename"])
    source.movements.update(original_description='<img src=x onerror="alert(1)">')
    record = case["ledger"].ledger_records.first()
    record.source_reference = {"document": '<script>alert("document")</script>'}
    record.save(update_fields=["source_reference"])
    report = build_source_report(source)
    html = render_to_string(
        "hub/reconciliation_print_report.html", report_presentation_context(source, report)
    )
    assert "<img src=x" not in html and '<script>alert("' not in html
    assert "&lt;img src=x" in html and "&lt;script&gt;" in html
    original_fields = {
        "reference",
        "date",
        "direction",
        "amount_cents",
        "allocated_cents",
        "remaining_cents",
    }
    old_shape = {
        **report,
        **{
            key: [
                {field: value for field, value in row.items() if field in original_fields}
                for row in report[key]
            ]
            for key in ("bank_rows", "ledger_rows")
        },
    }
    assert render_conference_csv(report) == render_conference_csv(old_shape)


def test_period_filters_both_sides_and_empty_ledger_does_not_claim_comparison(case):
    movement = case["source"].movements.get(source_key="ofx:test-1")
    movement.occurred_on = date(2026, 9, 13)
    movement.save(update_fields=["occurred_on"])
    record = case["ledger"].ledger_records.get(external_key="entry-1")
    for entry in (record.entry, record.accounting_entry):
        entry.occurred_on = date(2026, 9, 13)
        entry.save(update_fields=["occurred_on"])
    report = build_source_report(case["source"], start=date(2026, 9, 13), end=date(2026, 9, 13))
    assert report["bank_count"] == report["ledger_count"] == 1
    assert report["bank_rows"][0]["reference"] == str(movement.pk)
    assert report["ledger_rows"][0]["reference"] == str(record.pk)
    empty = build_source_report(case["source"], start=date(2026, 10, 1), end=date(2026, 10, 31))
    context = report_presentation_context(case["source"], empty)
    assert context["report_ledger_net_label"] == "Sem registros"
    assert context["report_difference_label"] == "Não comparável"


@pytest.mark.parametrize(
    "corrupt", ["ledger_company", "ledger_source", "ledger_account", "ledger_org"]
)
def test_report_rejects_misrelated_ledger_without_exposing_foreign_data(case, corrupt):
    source = case["source"]
    record = case["ledger"].ledger_records.first()
    other_org = Organization.objects.create(name="Foreign office", slug="foreign-report")
    other_company = ClientCompany.objects.create(
        organization=source.organization, name="Foreign company", dominio_code="FOREIGN"
    )
    other_account = FinancialAccount.objects.create(
        organization=source.organization, company=other_company, name="Foreign account"
    )
    if corrupt == "ledger_company":
        record.entry.company = other_company
        record.entry.save(update_fields=["company"])
    elif corrupt == "ledger_source":
        case["ledger"].company = other_company
        case["ledger"].save(update_fields=["company"])
    elif corrupt == "ledger_account":
        case["ledger"].financial_account = other_account
        case["ledger"].save(update_fields=["financial_account"])
    else:
        record.accounting_entry.organization = other_org
        record.accounting_entry.save(update_fields=["organization"])
    with pytest.raises(ReconciliationError, match="fora do escopo") as error:
        build_source_report(source)
    assert "Foreign" not in str(error.value)


@pytest.mark.parametrize("corrupt", ["organization", "company", "account"])
def test_report_rejects_cross_scope_allocations(case, corrupt):
    source = case["source"]
    movement = source.movements.first()
    record = case["ledger"].ledger_records.first()
    allocation = MovementReconciliation.objects.create(
        organization=source.organization,
        movement=movement,
        entry=record.entry,
        amount_cents=100,
        state="confirmed",
        confirmed_by=case["user"],
        confirmed_at=timezone.now(),
    )
    if corrupt == "organization":
        allocation.organization = Organization.objects.create(name="Other", slug="other-allocation")
        allocation.save(update_fields=["organization"])
    elif corrupt == "company":
        record.entry.company = ClientCompany.objects.create(
            organization=source.organization, name="Other", dominio_code="OTHER"
        )
        record.entry.save(update_fields=["company"])
    else:
        record.financial_account = FinancialAccount.objects.create(
            organization=source.organization, company=case["company"], name="Other account"
        )
        record.save(update_fields=["financial_account"])
    with pytest.raises(ReconciliationError, match="fora"):
        build_source_report(source)


def test_workbench_preserves_period_filters_and_safe_portfolio_return(case):
    portfolio = (
        reverse("hub:reconciliation-portfolio")
        + "?"
        + urlencode(
            {
                "company": str(case["company"].pk),
                "month": "2026-09",
                "q": "sintética",
            }
        )
    )
    request = RequestFactory().get(
        "/",
        {
            "start": "2026-09-12",
            "end": "2026-09-12",
            "state": "all",
            "q": "Recebimento",
            "page": "1",
            "portfolio_return": portfolio,
        },
    )
    context = source_review_context(case["source"], request)
    download = parse_qs(context["conference_report_querystring"])
    assert download == {
        "start": ["2026-09-12"],
        "end": ["2026-09-12"],
        "portfolio_return": [portfolio],
    }
    detail_query = parse_qs(urlsplit(context["conference_rows"][0]["detail_url"]).query)
    return_url = detail_query["return_to"][0]
    filters = parse_qs(urlsplit(return_url).query)
    assert filters == {**download, "state": ["all"], "q": ["Recebimento"], "page": ["1"]}
    detail_request = RequestFactory().get("/", {"return_to": return_url})
    assert conference_return_url(detail_request, case["source"].pk) == return_url


@pytest.mark.parametrize(
    "candidate",
    [
        "https://outside.invalid/",
        "//outside.invalid/",
        "/wrong/",
        "\\outside.invalid/",
        "{path}?q=%0Aevil",
        "{path}?q=%5Cevil",
        "{path}#fragment",
    ],
)
def test_portfolio_return_rejects_external_or_ambiguous_targets(candidate):
    candidate = candidate.format(path=reverse("hub:reconciliation-portfolio"))
    assert not portfolio_return_url(RequestFactory().get("/", {"portfolio_return": candidate}))


def test_return_links_reject_duplicates_and_invalid_period(case):
    portfolio = reverse("hub:reconciliation-portfolio")
    assert not portfolio_return_url(
        RequestFactory().get("/", {"portfolio_return": [portfolio] * 2})
    )
    source_url = reverse("hub:reconciliation-source-review", args=[case["source"].pk])
    for target in (
        source_url + "?start=invalid",
        source_url + "?start=2026-09-12&start=2026-09-12",
    ):
        assert not conference_return_url(
            RequestFactory().get("/", {"return_to": target}), case["source"].pk
        )


def test_presentation_rejects_a_report_from_another_source(case):
    report = build_source_report(case["source"])
    report["company_id"] = "different-company"
    with pytest.raises(ReconciliationError, match="fora da empresa"):
        report_presentation_context(case["source"], report)


def test_native_source_positions_and_large_negative_values_remain_readable(case):
    record = case["ledger"].ledger_records.first()
    record.source_reference = {"row_codes": ["SYN-1", "SYN-2"], "document": "SYN-DOC"}
    record.save(update_fields=["source_reference"])
    report = build_source_report(case["source"])
    report["bank_net_cents"] = -12345678901
    context = report_presentation_context(case["source"], report)
    assert context["report_bank_net_label"] == "-R$ 123.456.789,01"
    row = next(
        row for row in context["report_sections"][1]["rows"] if row["reference"] == str(record.pk)
    )
    assert row["source_position"] == "Registros SYN-1, SYN-2"
