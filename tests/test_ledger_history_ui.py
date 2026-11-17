"""A growing portfolio keeps every month, source and retry reachable without broadening access."""

from datetime import date
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.hub.ledger_requests import ledger_request_context, request_ledger
from apps.hub.models import CompanyAccessGrant, ReconciliationSourceFile
from apps.intelligence.models import NativeLedgerCollection
from test_ledger_request_ui import case as case_fixture
from test_ledger_request_ui import command, endpoint, mapping, options
from test_ledger_request_ui import context as context_fixture

case = case_fixture
context = context_fixture
pytestmark = pytest.mark.django_db


def requests(case, month, count):
    revision = ledger_request_context(account=case["account"], actor=case["actor"])[
        "mapping_revision"
    ]
    return [
        request_ledger(
            account=case["account"], actor=case["actor"], month=month,
            request_key=uuid4(), expected_mapping_revision=revision,
        )[0]
        for _ in range(count)
    ]


def sources(case, count):
    return ReconciliationSourceFile.objects.bulk_create([
        ReconciliationSourceFile(
            organization=case["account"].organization, company=case["account"].company,
            financial_account=case["account"], origin="bank_statement", kind="csv",
            original_filename=f"extrato-sintetico-{index:03}.csv",
            content_hash=f"{index + 1:064x}", size_bytes=20,
        )
        for index in range(count)
    ])


def test_old_month_remains_visible_after_twenty_newer_requests_in_another_month(case):
    mapping(case)
    oldest = requests(case, date(2026, 9, 1), 1)[0]
    requests(case, date(2026, 10, 1), 20)
    before = (NativeLedgerCollection.objects.count(), AuditEvent.objects.count())
    response = case["client"].get(endpoint(), options(case))
    assert response.status_code == 200
    assert [row["job"].pk for row in response.context["ledger_jobs"]] == [oldest.pk]
    assert response.context["ledger_jobs_page"].paginator.count == 1
    assert "Nenhuma solicitação nesta competência" not in response.content.decode()
    assert (NativeLedgerCollection.objects.count(), AuditEvent.objects.count()) == before


def test_every_request_and_source_is_reachable_with_independent_pages_and_retained_context(case):
    mapping(case)
    jobs = requests(case, date(2026, 9, 1), 43)
    requests(case, date(2026, 10, 1), 21)
    files = sources(case, 23)
    ids = []
    for number, size in ((1, 20), (2, 20), (3, 3)):
        response = case["client"].get(
            endpoint(), options(case, page=number, sources_page=2, bank_source=str(files[0].pk))
        )
        assert response.status_code == 200
        rows = response.context["ledger_jobs"]
        assert len(rows) == size
        assert response.context["ledger_jobs_page"].paginator.count == 43
        assert response.context["ledger_sources_page"].paginator.count == 23
        assert len(response.context["ledger_bank_sources"]) == 3
        ids.extend(row["job"].pk for row in rows)
        for direction in ("previous", "next"):
            target = response.context[f"ledger_jobs_{direction}_url"]
            if target:
                query = parse_qs(urlsplit(target).query)
                assert query["bank_source"] == [str(files[0].pk)]
                assert query["company"] == [str(case["account"].company_id)]
                assert query["account"] == [str(case["account"].pk)]
                assert query["month"] == ["2026-09"] and query["sources_page"] == ["2"]
        if number == 2:
            previous_source = response.context["ledger_sources_previous_url"]
            assert parse_qs(urlsplit(previous_source).query)["page"] == ["2"]
    assert len(ids) == len(set(ids)) == 43
    assert set(ids) == {job.pk for job in jobs}
    first = case["client"].get(endpoint(), options(case))
    source_ids = [row["source"].pk for row in first.context["ledger_bank_sources"]]
    source_ids.extend(row["source"].pk for row in response.context["ledger_bank_sources"])
    assert len(source_ids) == len(set(source_ids)) == 23
    assert set(source_ids) == {item.pk for item in files}


@pytest.mark.parametrize("field", ["page", "sources_page"])
@pytest.mark.parametrize(
    "value", ["", "0", "-1", "x", "1.5", "\u0661", "100000000", "999", ["1", "2"]]
)
def test_invalid_history_pages_never_expand_query_or_write(case, field, value):
    mapping(case)
    requests(case, date(2026, 9, 1), 1)
    before = (NativeLedgerCollection.objects.count(), AuditEvent.objects.count())
    response = case["client"].get(endpoint(), options(case, **{field: value}))
    assert response.status_code == 400
    assert not response.context.get("ledger_jobs")
    assert not response.context.get("ledger_bank_sources")
    assert "Nenhuma solicitação nesta competência" not in response.content.decode()
    response = case["client"].post(endpoint(), command(case, **{field: value}))
    assert response.status_code == 400
    assert (NativeLedgerCollection.objects.count(), AuditEvent.objects.count()) == before


def test_status_and_retry_preserve_history_pages_and_source_without_reading_other_jobs(case):
    mapping(case)
    jobs = requests(case, date(2026, 9, 1), 21)
    files = sources(case, 21)
    response = case["client"].get(
        endpoint(), options(case, page=2, sources_page=2, bank_source=str(files[0].pk))
    )
    row = response.context["ledger_jobs"][0]
    assert row["job"].pk == jobs[0].pk
    # A damaged different request must not prevent polling this authorized request.
    NativeLedgerCollection.objects.filter(pk=jobs[-1].pk).update(result=[])
    NativeLedgerCollection.objects.filter(pk=jobs[0].pk).update(state="review")
    status = case["client"].get(row["status_url"])
    assert status.status_code == 200 and status.json()["can_retry"]
    data = status.json()
    query = parse_qs(urlsplit(data["retry_url"]).query)
    assert query["page"] == ["2"] and query["sources_page"] == ["2"]
    assert query["bank_source"] == [str(files[0].pk)]
    payload = {
        "request_key": data["retry_key"], "expected_mapping_revision": data["mapping_revision"]
    }
    retried = case["client"].post(data["retry_url"], payload)
    assert retried.status_code == 302
    assert NativeLedgerCollection.objects.count() == 22
    returned = parse_qs(urlsplit(retried.url).query)
    assert returned["page"] == ["2"] and returned["sources_page"] == ["2"]
    assert returned["bank_source"] == [str(files[0].pk)] and returned["month"] == ["2026-09"]


def test_mapping_form_posts_and_preserves_selected_source_month_and_both_pages(case):
    mapping(case)
    requests(case, date(2026, 9, 1), 21)
    files = sources(case, 21)
    selected = options(case, page=2, sources_page=2, bank_source=str(files[0].pk))
    page = case["client"].get(endpoint(), selected)
    html = page.content.decode().split('name="action" value="mapping"', 1)[1].split("</form>", 1)[0]
    for key in ("company", "account", "month", "page", "sources_page", "bank_source"):
        assert f'name="{key}" value="{selected[key]}"' in html
    before = NativeLedgerCollection.objects.count()
    response = case["client"].post(endpoint(), {
        **selected,
        "action": "mapping",
        "mapping-expected_revision": page.context["ledger_mapping_revision"],
        "mapping-chart_company_code": "212",
        "mapping-branch_code": "212",
        "mapping-bank_inflow_side": "debit",
        "mapping-evidence_reference": "Revisão sintética preservando contexto",
        "mapping-confirmed": "on",
    })
    assert response.status_code == 302
    assert parse_qs(urlsplit(response.url).query) == {
        key: [str(value)] for key, value in selected.items()
    }
    returned = case["client"].get(response.url)
    assert returned.status_code == 200
    assert str(returned.context["ledger_form"]["bank_source"].value()) == str(files[0].pk)
    assert NativeLedgerCollection.objects.count() == before


@pytest.mark.parametrize("query", ["?page=0", "?page=2", "?sources_page=2", "?page=1&page=2"])
def test_invalid_retry_return_page_is_rejected_before_creating_job(case, query):
    mapping(case)
    job = requests(case, date(2026, 9, 1), 1)[0]
    NativeLedgerCollection.objects.filter(pk=job.pk).update(state="review")
    url = reverse("hub:reconciliation-ledger-retry", args=[job.pk])
    payload = command(case)
    response = case["client"].post(url + query, payload)
    assert response.status_code == 400
    assert NativeLedgerCollection.objects.count() == 1


def test_auditor_pages_without_retry_controls_and_revoked_access_refuses_history(case, membership):
    mapping(case)
    requests(case, date(2026, 9, 1), 21)
    NativeLedgerCollection.objects.update(state="review")
    membership.role = "auditor"
    membership.save(update_fields=["role"])
    grant = CompanyAccessGrant.objects.create(
        organization=case["account"].organization, company=case["account"].company,
        membership=membership, modules=["reconciliation"],
    )
    response = case["client"].get(endpoint(), options(case, page=2))
    assert response.status_code == 200 and len(response.context["ledger_jobs"]) == 1
    assert "Tentar novamente" not in response.content.decode()
    grant.delete()
    response = case["client"].get(endpoint(), options(case, page=2))
    assert response.status_code == 400
    assert not response.context.get("ledger_jobs")
