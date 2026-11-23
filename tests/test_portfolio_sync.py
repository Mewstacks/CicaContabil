"""Portfolio scans exercise real intake, persistence, retries and office boundaries."""

from __future__ import annotations

import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from uuid import uuid4

import pytest
from django.db import close_old_connections, connection
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import ClientCompany, DominioBankEntry
from apps.intelligence.agent_scope import build_portfolio_scope, validate_sync_scope
from apps.intelligence.agents import issue_enrollment, redeem_enrollment
from apps.intelligence.models import AgentCompanyScan, EdgeAgent
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db
ROUTE = "agent-v2-dominio-portfolio-companies"


@pytest.fixture
def portfolio(organization):
    scope = build_portfolio_scope(
        organization=organization,
        start=date(2026, 9, 1),
        end=date(2026, 9, 30),
        company_status_map={"A": True, "I": False},  # Synthetic mapping, not ERP evidence.
    )
    code = issue_enrollment(organization=organization, sync_scope=scope)
    return redeem_enrollment(
        code=code.code,
        label="Portfolio",
        fingerprint="test",
        allow_scoped=True,
        allow_portfolio=True,
    )


def post(credentials, payload, route=ROUTE, protocol="scoped-v2"):
    body = json.dumps(payload).encode()
    timestamp = str(int(timezone.now().timestamp()))
    signature = hmac.new(
        credentials.shared_secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return Client().post(
        reverse(route),
        data=body,
        content_type="application/json",
        secure=True,
        headers={
            "X-Hub-Agent-ID": credentials.agent_id,
            "X-Hub-Agent-Timestamp": timestamp,
            "X-Hub-Agent-Signature": signature,
            "X-Hub-Agent-Protocol": protocol,
        },
    )


def open_scan(credentials, count):
    response = post(
        credentials,
        {
            "action": "open",
            "scope_revision": credentials.sync_scope["revision"],
            "expected_count": count,
        },
    )
    assert response.status_code == 200, response.content
    return response.json()


def row(code=1, status="A"):
    return {"codigo": str(code), "nome": f"Empresa {code}", "cnpj_masked": "", "status": status}


def page(credentials, run, rows, *, complete=True, **overrides):
    return {
        "action": "page",
        "scope_revision": credentials.sync_scope["revision"],
        "run_id": run["run_id"],
        "after": run["after"],
        "rows": rows,
        "complete": complete,
        "source_count": run["expected_count"],
        **overrides,
    }


def test_501_companies_resume_after_lost_ack_and_preserve_inactive_history(portfolio, organization):
    historic = ClientCompany.objects.create(
        organization=organization, dominio_code="900", name="Histórica"
    )
    run = open_scan(portfolio, 501)
    payload = page(
        portfolio, run, [row(i, "I" if i == 5 else "A") for i in range(1, 501)], complete=False
    )
    first = post(portfolio, payload)
    assert first.status_code == 200
    assert first.json()["created"] == 500
    replay = post(portfolio, payload)
    assert replay.status_code == 200 and replay.json()["replayed"]
    resumed = open_scan(portfolio, 501)
    assert resumed["run_id"] == run["run_id"] and resumed["after"] == "500"
    final = post(portfolio, page(portfolio, resumed, [row(501)]))
    assert final.status_code == 200 and final.json()["complete"]
    scan = AgentCompanyScan.objects.get(pk=run["run_id"])
    assert scan.received_count == 501 and scan.page_count == 2 and scan.completed_at
    inactive = ClientCompany.objects.get(dominio_code="5")
    assert not inactive.active and inactive.dominio_status == "I"
    historic.refresh_from_db()
    assert historic.active  # Missing from a scan never means deleted/inactive.
    assert ClientCompany.objects.count() == 502
    assert not DominioBankEntry.objects.exists()


def test_new_scan_updates_source_status_without_duplicating_companies(portfolio):
    run = open_scan(portfolio, 1)
    assert post(portfolio, page(portfolio, run, [row(1, "I")])).status_code == 200
    company = ClientCompany.objects.get()
    assert not company.active
    new = open_scan(portfolio, 1)
    assert new["run_id"] != run["run_id"]
    response = post(portfolio, page(portfolio, new, [{**row(), "nome": "Nome atualizado"}]))
    assert response.status_code == 200 and response.json()["updated"] == 1
    company.refresh_from_db()
    assert company.active and company.name == "Nome atualizado" and company.dominio_status == "A"
    assert ClientCompany.objects.count() == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"status": "UNKNOWN"},
        {"codigo": "01"},
        {"codigo": "0"},
        {"nome": ""},
        {"nome": "a" * 181},
        {"cnpj_masked": "123"},
        {"email": "unexpected@example.com"},
        {"status": True},
        {"organization_id": str(uuid4())},
    ],
)
def test_bad_row_rolls_back_whole_page_and_checkpoint(portfolio, bad):
    run = open_scan(portfolio, 2)
    response = post(portfolio, page(portfolio, run, [row(), {**row(2), **bad}]))
    assert response.status_code == 400
    assert not ClientCompany.objects.exists()
    scan = AgentCompanyScan.objects.get()
    assert scan.cursor == "0" and scan.received_count == 0 and not scan.completed_at


@pytest.mark.parametrize(
    "rows", [[row(2), row(1)], [row(), row()], [row(i) for i in range(1, 502)]]
)
def test_duplicate_out_of_order_or_oversized_page_never_writes(portfolio, rows):
    run = open_scan(portfolio, len(rows))
    assert post(portfolio, page(portfolio, run, rows)).status_code == 400
    assert not ClientCompany.objects.exists()


@pytest.mark.parametrize("change", [{"source_count": 3}, {"after": "9"}, {"complete": "true"}])
def test_false_coverage_or_cursor_refused(portfolio, change):
    run = open_scan(portfolio, 2)
    assert post(portfolio, page(portfolio, run, [row(10)], **change)).status_code == 409
    assert not ClientCompany.objects.exists()


def test_incomplete_final_page_not_committed(portfolio):
    run = open_scan(portfolio, 2)
    assert post(portfolio, page(portfolio, run, [row()])).status_code == 409
    assert not ClientCompany.objects.exists()


@pytest.mark.parametrize("error", ["source_count_changed", "coverage_mismatch"])
def test_coverage_failure_restarts_even_if_original_count_returns(portfolio, error):
    run = open_scan(portfolio, 2)
    first = post(portfolio, page(portfolio, run, [row()], complete=False))
    assert first.status_code == 200
    run_after = {**run, "after": "1"}
    bad = (
        page(portfolio, run_after, [row(2)], source_count=3)
        if error == "source_count_changed"
        else page(portfolio, run_after, [])
    )
    response = post(portfolio, bad)
    assert response.status_code == 409 and response.json()["scan_aborted"]
    assert response.json()["code"] == error
    scan = AgentCompanyScan.objects.get(pk=run["run_id"])
    assert scan.aborted_at == scan.last_error_at and scan.aborted_at is not None
    assert scan.last_error_code == error and scan.completed_at is None
    assert scan.received_count == 1 and scan.cursor == "1"
    assert ClientCompany.objects.count() == 1
    resumed = open_scan(portfolio, 2)
    assert resumed["run_id"] != run["run_id"] and resumed["after"] == "0"
    final = post(portfolio, page(portfolio, resumed, [row(), row(2)]))
    assert final.status_code == 200 and final.json()["complete"]
    assert final.json()["created"] == 1 and final.json()["updated"] == 1
    assert ClientCompany.objects.count() == 2


def test_stale_conflicting_page_never_aborts_the_current_progress(portfolio):
    run = open_scan(portfolio, 2)
    good = page(portfolio, run, [row()], complete=False)
    assert post(portfolio, good).status_code == 200
    stale = page(portfolio, run, [row(2)], source_count=99)
    assert post(portfolio, stale).status_code == 409
    scan = AgentCompanyScan.objects.get()
    assert scan.aborted_at is None and scan.last_error_at is None
    assert scan.last_error_code == "" and scan.cursor == "1"
    replay = post(portfolio, good)
    assert replay.status_code == 200 and replay.json()["replayed"]


def test_completed_scan_is_not_aborted_and_original_receipt_still_replays(portfolio):
    run = open_scan(portfolio, 1)
    good = page(portfolio, run, [row()])
    assert post(portfolio, good).status_code == 200
    invalid = page(portfolio, {**run, "after": "1"}, [row(2)], source_count=2)
    assert post(portfolio, invalid).status_code == 409
    scan = AgentCompanyScan.objects.get()
    assert scan.completed_at is not None and scan.aborted_at is None
    assert scan.last_error_code == "" and scan.last_error_at is None
    replay = post(portfolio, good)
    assert replay.status_code == 200 and replay.json()["replayed"]


def test_source_count_change_aborts_incomplete_scan_and_restarts_without_data_loss(portfolio):
    run = open_scan(portfolio, 2)
    assert post(portfolio, page(portfolio, run, [row()], complete=False)).status_code == 200
    new = open_scan(portfolio, 3)
    assert new["run_id"] != run["run_id"] and new["after"] == "0"
    assert AgentCompanyScan.objects.get(pk=run["run_id"]).aborted_at
    assert post(portfolio, page(portfolio, run, [row(2)])).status_code == 403
    assert ClientCompany.objects.count() == 1


def test_zero_companies_is_explicit_completion_and_preserves_existing_companies(
    portfolio, organization
):
    company = ClientCompany.objects.create(
        organization=organization, dominio_code="1", name="Existente"
    )
    run = open_scan(portfolio, 0)
    payload = page(portfolio, run, [])
    assert post(portfolio, payload).json()["complete"]
    assert post(portfolio, payload).json()["replayed"]
    company.refresh_from_db()
    assert company.active


def test_office_codes_are_isolated_and_foreign_run_is_refused(portfolio, organization):
    other = Organization.objects.create(name="Outra", slug="outra")
    untouched = ClientCompany.objects.create(
        organization=other, dominio_code="1", name="Outra empresa"
    )
    run = open_scan(portfolio, 1)
    assert post(portfolio, page(portfolio, run, [row()])).status_code == 200
    untouched.refresh_from_db()
    assert untouched.name == "Outra empresa"
    assert ClientCompany.objects.filter(organization=organization).count() == 1
    assert post(portfolio, page(portfolio, run, [row()], run_id=str(uuid4()))).status_code == 403


def test_financial_routes_old_clients_stale_scope_and_revoked_agent_refused(portfolio):
    assert post(portfolio, {}, route="agent-v2-dominio-bank-entries").status_code == 401
    assert post(portfolio, {}, route="agent-v2-dominio-companies").status_code == 401
    assert post(portfolio, {}, protocol="scoped-v1").status_code == 401
    assert (
        post(
            portfolio, {"action": "open", "expected_count": 0, "scope_revision": "stale"}
        ).status_code
        == 403
    )
    EdgeAgent.objects.filter(pk=portfolio.agent_id).update(status=EdgeAgent.Status.REVOKED)
    assert post(portfolio, {}).status_code == 401
    assert not AgentCompanyScan.objects.exists()


@pytest.mark.parametrize(
    "change",
    [
        {"organization_id": str(uuid4())},
        {"datasets": ["companies", "bank_entries"]},
        {"company_status_map": {"A": "true"}},
        {"period_start": "invalid"},
        {"period_end": "9999-12-31"},
        {"revision": "0" * 64},
        {"sql": "SELECT secret"},
    ],
)
def test_manifest_rejects_unapproved_fields_sources_and_cross_office(
    portfolio, organization, change
):
    with pytest.raises(ValueError):
        validate_sync_scope({**portfolio.sync_scope, **change}, organization)


def test_failure_after_company_write_rolls_back_receipt_and_source(portfolio, monkeypatch):
    from apps.intelligence import portfolio as intake

    original = intake.sync_companies

    def fail_after_write(**kwargs):
        original(**kwargs)
        raise ValueError("Falha de transação simulada")

    monkeypatch.setattr(intake, "sync_companies", fail_after_write)
    run = open_scan(portfolio, 1)
    assert post(portfolio, page(portfolio, run, [row()])).status_code == 400
    assert not ClientCompany.objects.exists()
    scan = AgentCompanyScan.objects.get()
    assert scan.cursor == "0" and scan.page_count == 0 and scan.completed_at is None


def test_legacy_enrollment_does_not_consume_portfolio_code(portfolio, organization):
    from apps.intelligence.models import AgentEnrollment

    code = issue_enrollment(organization=organization, sync_scope=portfolio.sync_scope)
    with pytest.raises(ValueError, match="scoped-v2"):
        redeem_enrollment(code=code.code, label="Antigo", fingerprint="test", allow_scoped=True)
    assert AgentEnrollment.objects.filter(used_at__isnull=True).count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_open_and_replayed_page_have_one_commit(portfolio):
    if connection.vendor != "postgresql":
        pytest.skip("Row locking requires PostgreSQL")

    def opened(_):
        close_old_connections()
        try:
            return open_scan(portfolio, 1)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        runs = list(executor.map(opened, range(2)))
    assert runs[0]["run_id"] == runs[1]["run_id"]
    payload = page(portfolio, runs[0], [row()])

    def append(_):
        close_old_connections()
        try:
            response = post(portfolio, payload)
            assert response.status_code == 200, response.content
            return response.json()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(append, range(2)))
    assert sorted(result["replayed"] for result in responses) == [False, True]
    assert ClientCompany.objects.count() == 1
    scan = AgentCompanyScan.objects.get()
    assert scan.received_count == 1 and scan.page_count == 1


@pytest.mark.django_db(transaction=True)
def test_failed_final_page_cannot_abort_a_concurrent_completed_scan(portfolio):
    if connection.vendor != "postgresql":
        pytest.skip("Row locking requires PostgreSQL")
    run = open_scan(portfolio, 2)
    assert post(portfolio, page(portfolio, run, [row()], complete=False)).status_code == 200
    run["after"] = "1"
    payloads = [page(portfolio, run, [row(2)]), page(portfolio, run, [])]

    def append(payload):
        close_old_connections()
        try:
            return post(portfolio, payload).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        statuses = list(executor.map(append, payloads))
    assert statuses[1] == 409
    scan = AgentCompanyScan.objects.get(pk=run["run_id"])
    if statuses[0] == 200:
        assert scan.completed_at is not None and scan.aborted_at is None
        assert scan.last_error_code == "" and ClientCompany.objects.count() == 2
    else:
        assert statuses[0] == 403
        assert scan.completed_at is None and scan.aborted_at is not None
        assert ClientCompany.objects.count() == 1
        resumed = open_scan(portfolio, 2)
        assert resumed["after"] == "0"
        assert post(portfolio, page(portfolio, resumed, [row(), row(2)])).status_code == 200
        assert ClientCompany.objects.count() == 2
