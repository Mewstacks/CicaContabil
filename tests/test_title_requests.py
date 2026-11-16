"""Synthetic company requests: exact batches, current access, history and replay."""

from datetime import date
from time import monotonic
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.audit.models import AuditEvent
from apps.hub.models import ClientCompany, CompanyAccessGrant
from apps.hub.title_requests import (
    TitleRequestConflict,
    TitleRequestError,
    preview_title_requests,
    request_title_batch,
    retry_title_request,
    title_job_context,
    validate_title_job,
)
from apps.intelligence.models import CompanyTitleCollection
from test_native_titles import fiscal as fiscal_fixture

fiscal = fiscal_fixture
pytestmark = pytest.mark.django_db


def selection(fiscal, **changes):
    _, account, actor, *_ = fiscal
    result = dict(
        companies=[account.company],
        actor=actor,
        start_month=date(2026, 1, 1),
        end_month=date(2026, 3, 1),
        request_key=uuid4(),
    )
    result.update(changes)
    return result


def request(fiscal, **changes):
    params = selection(fiscal, **changes)
    preview = preview_title_requests(**params)
    jobs, created = request_title_batch(**params, expected_revision=preview["revision"])
    return params, jobs, created


def test_company_without_account_historical_months_preview_and_replay(fiscal):
    _, account, _, *_ = fiscal
    other = ClientCompany.objects.create(
        organization=account.organization, name="Sem conta", dominio_code="213"
    )
    params = selection(
        fiscal,
        companies=[account.company, other],
        start_month=date(1, 1, 1),
        end_month=date(1, 2, 1),
    )
    preview = preview_title_requests(**params)
    assert preview["count"] == 4 and not CompanyTitleCollection.objects.exists()
    jobs, created = request_title_batch(**params, expected_revision=preview["revision"])
    assert created and len(jobs) == 4
    assert {job.scope["period_start"] for job in jobs} == {"0001-01-01", "0001-02-01"}
    assert all(
        set(job.scope) == {"capture_id", "company_code", "period_start", "period_end_exclusive"}
        for job in jobs
    )
    repeated, created = request_title_batch(**params, expected_revision=preview["revision"])
    assert not created and {job.pk for job in repeated} == {job.pk for job in jobs}
    assert (
        AuditEvent.objects.filter(action="hub.reconciliation.title_collection_requested").count()
        == 1
    )
    assert all(validate_title_job(job) for job in jobs)


def test_batch_rejects_stale_identity_and_changed_nonce_selection(fiscal):
    params = selection(fiscal)
    preview = preview_title_requests(**params)
    company = params["companies"][0]
    company.dominio_code = "214"
    company.save()
    with pytest.raises(TitleRequestConflict):
        request_title_batch(**params, expected_revision=preview["revision"])
    assert not CompanyTitleCollection.objects.exists()
    current = preview_title_requests(**params)
    request_title_batch(**params, expected_revision=current["revision"])
    params["end_month"] = date(2026, 4, 1)
    changed = preview_title_requests(**params)
    with pytest.raises(TitleRequestConflict):
        request_title_batch(**params, expected_revision=changed["revision"])


def test_revoked_grant_blocks_batch_and_history_before_counts(fiscal, membership):
    _, account, actor, *_ = fiscal
    membership.role = "operator"
    membership.save()
    grant = CompanyAccessGrant.objects.create(
        organization=account.organization,
        membership=membership,
        company=account.company,
        modules=["reconciliation"],
        is_active=True,
    )
    params, jobs, _ = request(fiscal)
    grant.is_active = False
    grant.save()
    with pytest.raises(PermissionDenied):
        title_job_context(job=jobs[0], actor=actor)
    with pytest.raises(PermissionDenied):
        preview_title_requests(**params)
    assert not validate_title_job(jobs[0])


def test_bounds_and_auditor_are_closed(fiscal, membership):
    for changes in [
        dict(start_month=date(2026, 2, 2)),
        dict(end_month=date(2025, 1, 1)),
        dict(start_month=date(1, 1, 1), end_month=date(9998, 12, 1)),
    ]:
        with pytest.raises(TitleRequestError):
            preview_title_requests(**selection(fiscal, **changes))
    params, jobs, _ = request(fiscal)
    membership.role = "auditor"
    membership.save()
    with pytest.raises(PermissionDenied):
        preview_title_requests(**params)
    CompanyAccessGrant.objects.create(
        organization=membership.organization,
        membership=membership,
        company=params["companies"][0],
        modules=["reconciliation"],
        is_active=True,
    )
    assert title_job_context(job=jobs[0], actor=params["actor"])["can_retry"] is False


def test_stale_request_can_be_retried_without_editing_original(fiscal):
    params, jobs, _ = request(fiscal)
    old = jobs[0]
    old_scope = dict(old.scope)
    company = params["companies"][0]
    company.dominio_code = "214"
    company.save()
    context = title_job_context(job=old, actor=params["actor"])
    assert context["status"] == "review" and context["can_retry"]
    key = uuid4()
    fresh, created = retry_title_request(job=old, actor=params["actor"], request_key=key)
    assert created and fresh.scope["company_code"] == 214 and fresh.batch_key == key
    old.refresh_from_db()
    assert old.scope == old_scope and old.state == "queued"


def test_full_portfolio_batch_is_bounded_and_uses_bulk_queries(fiscal):
    _, account, _, *_ = fiscal
    companies = ClientCompany.objects.bulk_create(
        [
            ClientCompany(
                organization=account.organization, name=f"Sintética {i}", dominio_code=str(1000 + i)
            )
            for i in range(145)
        ]
    )
    companies.insert(0, account.company)
    params = selection(
        fiscal, companies=companies, start_month=date(2025, 1, 1), end_month=date(2025, 12, 1)
    )
    started = monotonic()
    with CaptureQueriesContext(connection) as queries:
        preview = preview_title_requests(**params)
        jobs, created = request_title_batch(**params, expected_revision=preview["revision"])
    assert created and len(jobs) == 1752 and CompanyTitleCollection.objects.count() == 1752
    assert len(queries) < 150, len(queries)
    print(f"D369 batch 146x12: {monotonic() - started:.3f}s, {len(queries)} queries")


@pytest.mark.django_db(transaction=True)
def test_postgresql_replayed_batch_is_atomic(fiscal):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connections

    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    params = selection(fiscal)
    revision = preview_title_requests(**params)["revision"]
    barrier = Barrier(2)

    def run(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            jobs, created = request_title_batch(**params, expected_revision=revision)
            return created, {job.pk for job in jobs}
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(run, range(2)))
    assert sorted(item[0] for item in result) == [False, True]
    assert result[0][1] == result[1][1]
    assert CompanyTitleCollection.objects.count() == 3
