from __future__ import annotations

from datetime import date
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from django.db import connection
from django.http import QueryDict
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.hub.models import (
    AccountingEntry,
    ClientCompany,
    DataSource,
    FinancialAccount,
    IndependentLedgerRecord,
    JournalEntry,
    JournalLine,
    NormalizedMovement,
    ReconciliationRun,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_portfolio import portfolio_context
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def portfolio_route(monkeypatch):
    # The service contract is independent of the view and its URL integration.
    def resolve(name, *args, **kwargs):
        if name == "hub:reconciliation-portfolio":
            return "/app/conciliacao/carteira/"
        return reverse(name, *args, **kwargs)

    monkeypatch.setattr("apps.hub.reconciliation_portfolio.reverse", resolve)


def company(organization, name="Empresa sintética"):
    return ClientCompany.objects.create(
        organization=organization, name=name, dominio_code=uuid4().hex[:8],
    )


def account(company, reference=None):
    return FinancialAccount.objects.create(
        organization=company.organization, company=company, name="Banco sintético",
        account_reference=reference or uuid4().hex[:8], ledger_code="8",
    )


def source(company, account=None, origin="bank_statement"):
    return ReconciliationSourceFile.objects.create(
        organization=company.organization, company=company, financial_account=account,
        kind="csv", origin=origin, original_filename="fonte-sintetica.csv",
        content_hash=uuid4().hex * 2, size_bytes=10, content="never-open-this-test-file.csv",
    )


def bank(account, when=date(2026, 9, 15), *, state="completed", source_company=None):
    original = source(source_company or account.company, account)
    run = ReconciliationRun.objects.create(
        organization=account.organization, source_file=original, state=state, stage="done",
    )
    movement = NormalizedMovement.objects.create(
        organization=account.organization, company=original.company, financial_account=account,
        source_file=original, run=run, source_key=uuid4().hex, occurred_on=when,
        amount_cents=10000, direction="inflow",
    )
    return original, run, movement


def ledger(account, when=date(2026, 9, 15)):
    original = source(account.company, account, "accounting")
    data_source, _ = DataSource.objects.get_or_create(
        organization=account.organization, kind="other_manual", defaults={"label": "Teste"},
    )
    entry = JournalEntry.objects.create(
        organization=account.organization, company=account.company, occurred_on=when,
        history="Razão sintético", purpose="source_ledger",
    )
    line = JournalLine.objects.create(
        organization=account.organization, entry=entry, account_code=account.ledger_code,
        side="debit", amount_cents=10000,
    )
    accounting = AccountingEntry.objects.create(
        organization=account.organization, company=account.company, data_source=data_source,
        external_key=uuid4().hex, occurred_on=when, amount_cents=10000, direction="inflow",
        account_reference=account.account_reference,
    )
    return IndependentLedgerRecord.objects.create(
        organization=account.organization, source_file=original, financial_account=account,
        external_key=uuid4().hex, fingerprint="a" * 64, entry=entry, bank_line=line,
        accounting_entry=accounting,
    )


def context(organization, query="month=2026-09", *, companies=None, can_manage=False):
    return portfolio_context(
        office=organization,
        companies=companies if companies is not None else ClientCompany.objects.filter(
            organization=organization,
        ),
        params=QueryDict(query), can_manage=can_manage,
    )


def test_empty_company_is_visible_without_fabricating_account(organization):
    item = company(organization)
    result = context(organization, can_manage=True)
    row = result["rows"][0]
    assert row["company"] == item and row["accounts"] == []
    assert row["status"] == "missing_account"
    assert result["counts"]["missing_account"] == 1
    assert str(item.pk) in row["actions"][0]["url"]
    assert FinancialAccount.objects.count() == 0


def test_bank_and_ledger_must_share_account_and_month(organization):
    item = company(organization)
    first, second = account(item, "A"), account(item, "B")
    bank(first)
    ledger(second)
    ledger(first, date(2026, 10, 15))
    result = context(organization)
    statuses = {row["account"].pk: row["status"] for row in result["rows"][0]["accounts"]}
    assert statuses == {first.pk: "missing_ledger", second.pk: "missing_bank"}
    assert result["counts"]["available"] == 0
    ledger(first)
    assert context(organization)["counts"]["available"] == 1


def test_available_does_not_require_posting_chart_or_equal_counts(organization):
    item = account(company(organization))
    bank(item)
    ledger(item)
    ledger(item)
    row = context(organization)["rows"][0]["accounts"][0]
    assert row["status"] == "available"
    assert row["bank_count"] == 1 and row["ledger_count"] == 2
    assert "conferir" in row["status_label"]


@pytest.mark.parametrize("field,value", [
    ("active", False), ("account_reference", ""), ("ledger_code", ""),
])
def test_incomplete_account_never_becomes_available(organization, field, value):
    item = account(company(organization))
    bank(item)
    ledger(item)
    setattr(item, field, value)
    item.save(update_fields=[field])
    row = context(organization)["rows"][0]["accounts"][0]
    assert row["status"] == "review" and row["issues"]


@pytest.mark.parametrize("state", ["failed", "canceled", "waiting", "processing"])
def test_failed_or_running_import_is_not_available(organization, state):
    item = account(company(organization))
    bank(item, state=state)
    ledger(item)
    row = context(organization)["rows"][0]["accounts"][0]
    assert row["status"] == "review"
    assert row["sources"][0]["review_url"] == ""


def test_undated_and_empty_sources_need_review_without_inventing_month(organization):
    item = account(company(organization))
    bank(item, when=None)
    source(item.company, item)
    result = context(organization, "month=2026-10")
    row = result["rows"][0]["accounts"][0]
    assert row["status"] == "review" and row["bank_count"] == 0
    assert row["bank_source_count"] == 2
    assert context(organization, "month=2026-09")["counts"]["available"] == 0


def test_invalid_bank_relationship_is_not_counted(organization):
    item = account(company(organization))
    _, _, movement = bank(item)
    movement.financial_account = account(item.company)
    movement.save(update_fields=["financial_account"])
    ledger(item)
    rows = context(organization)["rows"][0]["accounts"]
    row = next(row for row in rows if row["account"] == item)
    assert row["bank_count"] == 0 and row["status"] == "review"


def test_invalid_relationship_outside_month_blocks_entire_source_conference(organization):
    item = account(company(organization))
    original, run, _ = bank(item)
    ledger(item)
    NormalizedMovement.objects.create(
        organization=organization, company=item.company,
        financial_account=account(item.company), source_file=original, run=run,
        source_key="wrong-account-in-next-month", occurred_on=date(2026, 10, 15),
        amount_cents=10000, direction="inflow",
    )
    result = context(organization, "month=2026-09", can_manage=True)
    row = next(row for row in result["rows"][0]["accounts"] if row["account"] == item)
    assert row["bank_count"] == 1 and row["ledger_count"] == 1
    assert row["status"] == "review" and row["sources"][0]["review_url"] == ""
    assert all(action["label"] != "Abrir conferência" for action in row["actions"])


@pytest.mark.parametrize("relation", ["date", "source", "bank_line", "reference", "derived"])
def test_inconsistent_ledger_relationship_is_not_counted(organization, relation):
    item = account(company(organization))
    _, _, movement = bank(item)
    record = ledger(item)
    if relation == "date":
        AccountingEntry.objects.filter(pk=record.accounting_entry_id).update(
            occurred_on=date(2026, 10, 15),
        )
    elif relation == "source":
        ReconciliationSourceFile.objects.filter(pk=record.source_file_id).update(
            origin="bank_statement",
        )
    elif relation == "bank_line":
        JournalLine.objects.filter(pk=record.bank_line_id).update(account_code="wrong")
    elif relation == "reference":
        AccountingEntry.objects.filter(pk=record.accounting_entry_id).update(
            account_reference="another-bank",
        )
    else:
        JournalEntry.objects.filter(pk=record.entry_id).update(movement=movement)
    row = context(organization)["rows"][0]["accounts"][0]
    assert row["ledger_count"] == 0 and row["status"] == "review"


def test_unassigned_bank_source_is_visible_as_review(organization):
    item = company(organization)
    source(item)
    row = context(organization)["rows"][0]
    assert row["unassigned_source_count"] == 1
    assert set(row["statuses"]) == {"missing_account", "review"}


def test_default_month_comes_only_from_authorized_bank_movements(organization):
    allowed, hidden = company(organization, "Permitida"), company(organization, "Oculta")
    bank(account(allowed), date(2026, 9, 30))
    bank(account(hidden), date(2027, 1, 15))
    result = context(organization, "", companies=ClientCompany.objects.filter(pk=allowed.pk))
    assert result["month"] == "2026-09" and result["counts"]["all"] == 1
    assert context(organization, "")["month"] == "2027-01"


def test_default_month_ignores_broken_bank_account_and_source_relations(organization):
    item = account(company(organization))
    bank(item, date(2026, 9, 15))
    _, _, future = bank(item, date(2026, 11, 15))
    future.financial_account = account(item.company)
    future.save(update_fields=["financial_account"])
    wrong_company = company(organization, "Outra empresa")
    bank(item, date(2026, 12, 15), source_company=wrong_company)
    _, _, zero = bank(item, date(2027, 1, 15))
    zero.amount_cents = 0
    zero.save(update_fields=["amount_cents"])
    assert context(organization, "")["month"] == "2026-09"


@pytest.mark.parametrize("query", [
    "month=", "month=2026-13", "month=2026-9", "month=2026-09&month=2026-10",
    "month=2026-09&company=bad", "month=2026-09&account=bad", "status=wrong",
    "page=0", "page=2&page=1", "page=two", "q=" + "x" * 101,
])
def test_invalid_filters_fail_closed(organization, query):
    company(organization)
    result = context(organization, query)
    assert result["errors"] and result["rows"] == []
    assert result["page"].paginator.count == 0


def test_foreign_company_or_account_and_mismatched_selection_fail_closed(organization):
    allowed = company(organization)
    another = company(organization)
    foreign_org = Organization.objects.create(name="Other", slug="other")
    foreign = account(company(foreign_org))
    for query in [
        f"company={foreign.company_id}", f"account={foreign.pk}",
        f"company={allowed.pk}&account={account(another).pk}",
    ]:
        result = context(organization, "month=2026-09&" + query)
        assert result["errors"] and result["rows"] == []
    result = context(
        organization, f"company={another.pk}",
        companies=ClientCompany.objects.filter(pk=allowed.pk),
    )
    assert result["errors"] and result["rows"] == []


def test_status_filter_applies_before_pagination(organization):
    for number in range(26):
        company(organization, f"Empresa {number:02}")
    ready = account(company(organization, "ZZ disponível"))
    bank(ready)
    ledger(ready)
    result = context(organization)
    assert len(result["rows"]) == 25 and result["page"].paginator.count == 27
    second = context(organization, "month=2026-09&page=2")
    assert len(second["rows"]) == 2
    filtered = context(organization, "month=2026-09&status=available")
    assert len(filtered["rows"]) == 1 and filtered["rows"][0]["company"] == ready.company
    assert filtered["counts"]["all"] == 27 and filtered["counts"]["missing_account"] == 26
    assert context(organization, "month=2026-09&page=3")["errors"]


def test_links_preserve_month_scope_and_offer_no_writes_to_readers(organization):
    item = account(company(organization))
    bank(item)
    row = context(organization, can_manage=False)["rows"][0]["accounts"][0]
    assert row["actions"] == []
    review = parse_qs(urlsplit(row["sources"][0]["review_url"]).query)
    assert review["start"] == ["2026-09-01"] and review["end"] == ["2026-09-30"]
    assert urlsplit(review["portfolio_return"][0]).path == "/app/conciliacao/carteira/"
    row = context(organization, can_manage=True)["rows"][0]["accounts"][0]
    upload = parse_qs(urlsplit(row["actions"][0]["url"]).query)
    assert upload["upload_account"] == [str(item.pk)]
    assert upload["upload_company"] == [str(item.company_id)]
    assert upload["upload_origin"] == ["accounting"]


def test_read_only_and_query_count_does_not_grow_per_company(organization):
    item = account(company(organization))
    bank(item)
    ledger(item)
    with CaptureQueriesContext(connection) as first:
        context(organization)
    for number in range(30):
        extra = account(company(organization, f"Outra {number:02}"))
        bank(extra)
        ledger(extra)
    with CaptureQueriesContext(connection) as expanded:
        result = context(organization)
    assert len(first) == len(expanded) <= 6
    assert result["counts"]["available"] == 31
    assert all(query["sql"].lstrip().upper().startswith("SELECT") for query in expanded)
    assert all("FOR UPDATE" not in query["sql"].upper() for query in expanded)
