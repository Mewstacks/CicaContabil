"""Recover active reconciliation work without increasing idle database polling.

The database lease is the durable authority; broker watchdogs can be rebuilt on
worker startup. The timing bound assumes a working worker, broker, database and
available queue capacity. This is neither backup nor a production RPO claim.
"""

from __future__ import annotations

import logging
import math
import uuid
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from apps.hub.models import ReconciliationRun

logger = logging.getLogger(__name__)

TASK_HARD_LIMIT_SECONDS = 300
TASK_SOFT_LIMIT_SECONDS = 270
LEASE_SECONDS = TASK_HARD_LIMIT_SECONDS + 60


class RecoveryDeliveryError(RuntimeError):
    """A retryable delivery failure with no broker URL or input data in its text."""


def dispatch_run(run_id: str) -> None:
    from apps.hub.tasks import process_reconciliation_run

    try:
        process_reconciliation_run.delay(run_id)
    except Exception as exc:
        logger.warning(
            "Reconciliation delivery unavailable",
            extra={"run_id": run_id, "failure_type": type(exc).__name__},
        )
        raise RecoveryDeliveryError("Reconciliation delivery unavailable") from None


def schedule_recovery(run_id: str, token: uuid.UUID, deadline: datetime) -> None:
    from apps.hub.tasks import recover_reconciliation_run

    delay = max(1, math.ceil((deadline - timezone.now()).total_seconds()) + 1)
    try:
        recover_reconciliation_run.apply_async(args=[run_id, str(token)], countdown=delay)
    except Exception as exc:
        logger.warning(
            "Reconciliation watchdog unavailable",
            extra={"run_id": run_id, "failure_type": type(exc).__name__},
        )
        raise RecoveryDeliveryError("Reconciliation watchdog unavailable") from None


def recover_run(run_id: str, expected_token: str | None = None) -> str:
    """Rearm a valid lease or CAS an expired one; never reset a completed run."""
    try:
        parsed_id = uuid.UUID(str(run_id))
        token = uuid.UUID(expected_token) if expected_token is not None else None
    except (ValueError, TypeError, AttributeError):
        return "invalid_id"
    current = ReconciliationRun.objects.filter(pk=parsed_id).values(
        "state", "lease_token", "lease_until"
    ).first()
    if current is None:
        return "missing"
    if current["state"] == ReconciliationRun.State.WAITING:
        if current["lease_until"] is not None and current["lease_until"] >= timezone.now():
            if current["lease_token"] is None:
                return "invalid_lease"
            schedule_recovery(str(parsed_id), current["lease_token"], current["lease_until"])
            return "armed"
        # Also repairs a publish failure after the CAS committed. Duplicate broker
        # deliveries are harmless: acquisition is a conditional database update.
        dispatch_run(str(parsed_id))
        return "dispatched"
    if current["state"] != ReconciliationRun.State.PROCESSING:
        return "terminal"
    if token is not None and current["lease_token"] != token:
        return "stale"
    deadline = current["lease_until"]
    if deadline is None:
        # Do not invent ownership/expiry for a malformed historical record.
        return "invalid_lease"
    now = timezone.now()
    if deadline >= now:
        if current["lease_token"] is None:
            return "invalid_lease"
        schedule_recovery(str(parsed_id), current["lease_token"], deadline)
        return "armed"
    with transaction.atomic():
        recovered = ReconciliationRun.objects.filter(
            pk=parsed_id,
            state=ReconciliationRun.State.PROCESSING,
            lease_token=current["lease_token"],
            lease_until=deadline,
            lease_until__lt=now,
        ).update(
            state=ReconciliationRun.State.WAITING,
            stage="recovered",
            lease_token=None,
            lease_until=None,
        )
        if recovered:
            transaction.on_commit(lambda: dispatch_run(str(parsed_id)))
    return "recovered" if recovered else "changed"


def resume_active_runs() -> dict[str, int]:
    """One startup pass; no recurring task is created when the queue is empty."""
    counts: dict[str, int] = {}
    run_ids = ReconciliationRun.objects.filter(
        state__in=[ReconciliationRun.State.WAITING, ReconciliationRun.State.PROCESSING]
    ).order_by("pk").values_list("pk", flat=True)
    for run_id in run_ids.iterator(chunk_size=100):
        result = recover_run(str(run_id))
        counts[result] = counts.get(result, 0) + 1
    return counts
