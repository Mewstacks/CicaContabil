"""Active-job recovery is bounded by its lease, never by faster idle polling."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier, current_thread
from unittest.mock import patch
from uuid import uuid4

import pytest
from celery.exceptions import Retry, SoftTimeLimitExceeded
from django.conf import settings
from django.db import close_old_connections, connection
from django.db.models.query import QuerySet
from django.utils import timezone

from apps.hub import reconciliation_recovery as recovery
from apps.hub import reconciliation_service as service
from apps.hub.models import ClientCompany, ReconciliationRun
from apps.hub.tasks import (
    process_reconciliation_run,
    recover_reconciliation_run,
    recover_reconciliation_runs,
    resume_reconciliation_after_worker_start,
)

OFX = (
    b"OFXHEADER:100\n<OFX><BANKID>001<ACCTID>synthetic<BANKTRANLIST>"
    b"<STMTTRN><DTPOSTED>20260912<TRNAMT>-10.00<FITID>first<NAME>First synthetic"
    b"</STMTTRN><STMTTRN><DTPOSTED>20260913<TRNAMT>20.00<FITID>second"
    b"<NAME>Second synthetic</STMTTRN></BANKTRANLIST></OFX>"
)


@pytest.fixture
def case(organization, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    company = ClientCompany.objects.create(organization=organization, name="Synthetic")
    source, run, _ = service.create_source_file(
        organization=organization,
        company=company,
        filename="recovery.ofx",
        origin="bank_statement",
        content=OFX,
    )
    return source, run


def leased(run, *, seconds=-1, token=True):
    run.state = ReconciliationRun.State.PROCESSING
    run.lease_token = uuid4() if token else None
    run.lease_until = timezone.now() + timedelta(seconds=seconds)
    run.started_at = run.lease_until - timedelta(seconds=recovery.LEASE_SECONDS)
    run.save()
    return run.lease_token


def test_active_lease_and_task_limit_preserve_the_idle_schedule():
    assert process_reconciliation_run.time_limit == 300
    assert process_reconciliation_run.soft_time_limit == 270
    assert recovery.LEASE_SECONDS == 360
    assert settings.BACKGROUND_RECOVERY_INTERVAL_MINUTES == 15
    assert settings.CELERY_BEAT_SCHEDULE["recover-reconciliation-runs"]["schedule"].minute == {
        0, 15, 30, 45,
    }
    assert "hub.recover_reconciliation_run" not in {
        item["task"] for item in settings.CELERY_BEAT_SCHEDULE.values()
    }


@pytest.mark.django_db
def test_watchdog_is_armed_before_parsing_and_survives_abrupt_interruption(case):
    source, run = case
    now = timezone.now()
    observed = []

    def crash(token, deadline):
        run.refresh_from_db()
        assert run.lease_token == token and run.state == "processing"
        assert not source.movements.exists()
        observed.append(deadline)
        raise KeyboardInterrupt

    with patch.object(service.timezone, "now", return_value=now), pytest.raises(KeyboardInterrupt):
        service.process_run(str(run.pk), on_acquired=crash)
    assert observed == [now + timedelta(seconds=360)]
    run.refresh_from_db()
    assert run.state == "processing" and run.lease_token is not None


@pytest.mark.django_db
def test_watchdog_publish_failure_returns_own_attempt_to_waiting_without_financial_writes(case):
    source, run = case
    with pytest.raises(recovery.RecoveryDeliveryError):
        service.process_run(
            str(run.pk), on_acquired=lambda *_: (_ for _ in ()).throw(
                recovery.RecoveryDeliveryError("synthetic delivery failure")
            ),
        )
    run.refresh_from_db()
    assert (run.state, run.lease_token, run.lease_until) == ("waiting", None, None)
    assert not source.movements.exists()


@pytest.mark.django_db
def test_failed_watchdog_publish_cannot_release_a_newer_attempt(case):
    _, run = case
    replacement = uuid4()

    def changed_then_failed(*_):
        ReconciliationRun.objects.filter(pk=run.pk).update(lease_token=replacement)
        raise recovery.RecoveryDeliveryError("synthetic delivery failure")

    with pytest.raises(recovery.RecoveryDeliveryError):
        service.process_run(str(run.pk), on_acquired=changed_then_failed)
    run.refresh_from_db()
    assert run.state == "processing" and run.lease_token == replacement


@pytest.mark.django_db
@pytest.mark.parametrize("token", [True, False])
def test_expired_attempt_is_recovered_once_including_legacy_null_token(
    case, token, django_capture_on_commit_callbacks,
):
    _, run = case
    original = leased(run, token=token)
    run.checkpoint = {"kept": "synthetic"}
    run.save(update_fields=["checkpoint"])
    with patch("apps.hub.tasks.process_reconciliation_run.delay") as dispatch:
        with django_capture_on_commit_callbacks(execute=True):
            assert recover_reconciliation_runs() == 1
            assert recover_reconciliation_runs() == 0
        dispatch.assert_called_once_with(str(run.pk))
    run.refresh_from_db()
    assert (run.state, run.lease_token, run.lease_until) == ("waiting", None, None)
    assert run.stage == "recovered" and run.checkpoint == {"kept": "synthetic"}
    if original is not None:
        # A failed publish after the CAS committed can retry delivery from WAITING.
        with patch("apps.hub.tasks.process_reconciliation_run.delay") as dispatch:
            assert recovery.recover_run(str(run.pk), str(original)) == "dispatched"
            dispatch.assert_called_once_with(str(run.pk))


@pytest.mark.django_db
def test_valid_lease_is_rearmed_without_execution_or_state_change(case):
    _, run = case
    now = timezone.now()
    token = leased(run, seconds=360)
    with (
        patch.object(recovery.timezone, "now", return_value=now),
        patch.object(recover_reconciliation_run, "apply_async") as arm,
        patch.object(process_reconciliation_run, "delay") as dispatch,
    ):
        assert recovery.recover_run(str(run.pk), str(token)) == "armed"
    arm.assert_called_once()
    assert arm.call_args.kwargs["args"] == [str(run.pk), str(token)]
    assert 361 <= arm.call_args.kwargs["countdown"] <= 362
    dispatch.assert_not_called()
    run.refresh_from_db()
    assert run.state == "processing" and run.lease_token == token


@pytest.mark.django_db
def test_stale_watchdog_does_not_touch_a_newer_attempt(case):
    _, run = case
    token = leased(run, seconds=-1)
    with patch.object(process_reconciliation_run, "delay") as dispatch:
        assert recovery.recover_run(str(run.pk), str(uuid4())) == "stale"
    run.refresh_from_db()
    assert run.lease_token == token and run.state == "processing"
    dispatch.assert_not_called()


@pytest.mark.django_db
@pytest.mark.parametrize("state", ["review", "completed", "completed_alerts", "failed", "canceled"])
def test_watchdog_never_reopens_terminal_or_human_review_state(case, state):
    _, run = case
    token = leased(run)
    ReconciliationRun.objects.filter(pk=run.pk).update(state=state)
    with patch.object(process_reconciliation_run, "delay") as dispatch:
        assert recovery.recover_run(str(run.pk), str(token)) == "terminal"
    run.refresh_from_db()
    assert run.state == state
    dispatch.assert_not_called()


@pytest.mark.django_db
def test_sweep_cas_cannot_overwrite_a_completion_after_its_read(case, monkeypatch):
    _, run = case
    token = leased(run)
    update = QuerySet.update

    def finish_before_recovery(query, **kwargs):
        if query.model is ReconciliationRun and kwargs.get("stage") == "recovered":
            update(
                ReconciliationRun.objects.filter(pk=run.pk), state="review", lease_token=None,
                lease_until=None,
            )
        return update(query, **kwargs)

    monkeypatch.setattr(QuerySet, "update", finish_before_recovery)
    with patch.object(process_reconciliation_run, "delay") as dispatch:
        assert recovery.recover_run(str(run.pk), str(token)) == "changed"
    run.refresh_from_db()
    assert run.state == "review"
    dispatch.assert_not_called()


@pytest.mark.django_db
def test_previous_attempt_cannot_finish_or_write_after_ownership_changes(case):
    source, run = case
    original_parser = service._records_from_ofx
    previous_token = None

    def replace_ownership(source):
        nonlocal previous_token
        run.refresh_from_db()
        previous_token = run.lease_token
        ReconciliationRun.objects.filter(pk=run.pk).update(lease_token=uuid4())
        return original_parser(source)

    with patch.object(service, "_records_from_ofx", side_effect=replace_ownership):
        assert service.process_run(str(run.pk))["state"] == "not_ready"
    assert not source.movements.exists()
    service._finish_run(run, previous_token, "completed", "completed")
    run.refresh_from_db()
    assert run.state == "processing" and run.lease_token != previous_token


@pytest.mark.django_db
@pytest.mark.parametrize("interruption", [KeyboardInterrupt, SoftTimeLimitExceeded])
def test_partial_crash_replay_preserves_human_edit_and_does_not_duplicate(
    case, user, django_capture_on_commit_callbacks, interruption,
):
    source, run = case
    apply = service.apply_rules
    calls = 0

    def crash_second(movement):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise interruption
        return apply(movement)

    with (
        patch.object(service, "apply_rules", side_effect=crash_second),
        pytest.raises(interruption),
    ):
        service.process_run(str(run.pk))
    first = source.movements.get()
    first.edited_by = user
    first.review_state = "ignored"
    first.description = "Human review preserved"
    first.save()
    run.refresh_from_db()
    assert run.state == "processing" and run.lease_token is not None
    lease = run.lease_until
    with (
        patch.object(recovery.timezone, "now", return_value=lease + timedelta(seconds=1)),
        patch.object(process_reconciliation_run, "delay"),
        django_capture_on_commit_callbacks(execute=True),
    ):
        assert recovery.recover_run(str(run.pk), str(run.lease_token)) == "recovered"
    result = service.process_run(str(run.pk))
    assert result["created"] == 1 and source.movements.count() == 2
    first.refresh_from_db()
    assert first.edited_by_id == user.pk and first.review_state == "ignored"
    assert first.description == "Human review preserved"
    assert service.process_run(str(run.pk))["state"] == "not_ready"
    assert source.movements.count() == 2


@pytest.mark.django_db
def test_startup_rebuilds_only_waiting_and_active_work(case):
    source, run = case
    token = leased(run, seconds=300)
    waiting = ReconciliationRun.objects.create(organization=run.organization, source_file=source)
    ReconciliationRun.objects.create(
        organization=run.organization, source_file=source, state="review"
    )
    with (
        patch.object(process_reconciliation_run, "delay") as dispatch,
        patch.object(recover_reconciliation_run, "apply_async") as arm,
    ):
        assert recovery.resume_active_runs() == {"armed": 1, "dispatched": 1}
    dispatch.assert_called_once_with(str(waiting.pk))
    assert arm.call_args.kwargs["args"] == [str(run.pk), str(token)]


@pytest.mark.django_db
def test_idle_startup_creates_no_recurring_work():
    with patch.object(recover_reconciliation_run, "apply_async") as arm:
        assert recovery.resume_active_runs() == {}
    arm.assert_not_called()


def test_worker_ready_only_enqueues_bootstrap():
    with patch("apps.hub.tasks.resume_active_reconciliation_runs.delay") as dispatch:
        resume_reconciliation_after_worker_start()
    dispatch.assert_called_once_with()


def test_task_retries_soft_timeout_instead_of_declaring_processing_failed():
    with (
        patch("apps.hub.tasks.process_run", side_effect=SoftTimeLimitExceeded),
        patch.object(process_reconciliation_run, "retry", side_effect=Retry()) as retry,
        pytest.raises(Retry),
    ):
        process_reconciliation_run(str(uuid4()))
    assert retry.call_args.kwargs["countdown"] == 30
    assert retry.call_args.kwargs["max_retries"] == 12


@pytest.mark.django_db
def test_redelivery_rearms_active_lease_without_parallel_processing(case):
    _, run = case
    token = leased(run, seconds=300)
    with patch.object(recover_reconciliation_run, "apply_async") as arm:
        assert process_reconciliation_run(str(run.pk))["state"] == "not_ready"
    assert arm.call_args.kwargs["args"] == [str(run.pk), str(token)]


@pytest.mark.django_db
def test_delivery_error_has_no_broker_details_and_keeps_durable_work(case):
    _, run = case
    with (
        patch.object(process_reconciliation_run, "delay", side_effect=RuntimeError("private-url")),
        pytest.raises(
            recovery.RecoveryDeliveryError, match=r"^Reconciliation delivery unavailable$"
        ),
    ):
        recovery.recover_run(str(run.pk))
    run.refresh_from_db()
    assert run.state == "waiting"


@pytest.mark.django_db(transaction=True)
def test_postgresql_simultaneous_recovery_dispatches_only_one_attempt(case, monkeypatch):
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL conditional-update locking")
    _, run = case
    token = leased(run)
    barrier = Barrier(2)
    first = QuerySet.first

    def read_together(query):
        result = first(query)
        if query.model is ReconciliationRun and current_thread().name.startswith("recovery-race"):
            barrier.wait(timeout=10)
        return result

    monkeypatch.setattr(QuerySet, "first", read_together)

    def worker():
        close_old_connections()
        try:
            return recovery.recover_run(str(run.pk), str(token))
        finally:
            close_old_connections()

    with (
        patch.object(process_reconciliation_run, "delay") as dispatch,
        ThreadPoolExecutor(max_workers=2, thread_name_prefix="recovery-race") as pool,
    ):
        results = list(pool.map(lambda _: worker(), range(2)))
    assert sorted(results) == ["changed", "recovered"]
    dispatch.assert_called_once_with(str(run.pk))
