"""Celery entry points of the NFS-e procuração lane (D-304).

Kept out of `tasks.py` so the legacy module is not edited; registered through
`CELERY_IMPORTS`. Every task returns at once while `NFSE_PROCURACAO_SYNC_ENABLED` is off or
the ADN environment is not production, and never touches a row of the legacy lane.
"""

from __future__ import annotations

import logging
from typing import Any

from celery import shared_task
from django.conf import settings
from django.core.cache import cache

from apps.hub import company_roster, procuracao_alerts
from apps.hub.models import NfseSync
from apps.hub.nfse_procuracao import (
    due_certificate_ids,
    next_due_sync_id,
    recover_stale_procuracao_syncs,
    run_procuracao_sync,
    seed_procuracao_syncs,
)

logger = logging.getLogger(__name__)

PAUSE_CACHE_KEY = "hub:nfse-procuracao:pause"
CHAIN_DELAY_SECONDS = 1


def lane_enabled() -> bool:
    return bool(
        settings.NFSE_PROCURACAO_SYNC_ENABLED and settings.NFSE_ADN_ENVIRONMENT == "production"
    )


def lane_paused() -> bool:
    return bool(cache.get(PAUSE_CACHE_KEY))


def _enqueue(sync_id: Any) -> bool:
    queued = NfseSync.objects.filter(
        pk=sync_id, status__in=[NfseSync.Status.IDLE, NfseSync.Status.RETRY]
    ).update(status=NfseSync.Status.QUEUED)
    if not queued:
        return False
    try:
        poll_procuracao_sync.delay(str(sync_id))
    except Exception:
        logger.exception("Could not enqueue procuração sync %s", sync_id)
        NfseSync.objects.filter(pk=sync_id, status=NfseSync.Status.QUEUED).update(
            status=NfseSync.Status.RETRY, last_error_code="queue_delivery"
        )
        return False
    return True


@shared_task(name="hub.seed_procuracao_syncs")  # type: ignore[untyped-decorator]
def seed_procuracao_syncs_task(organization_id: str | None = None) -> dict[str, int]:
    return seed_procuracao_syncs(organization_id=organization_id)


@shared_task(name="hub.dispatch_procuracao_syncs")  # type: ignore[untyped-decorator]
def dispatch_procuracao_syncs() -> int:
    """Start one company per office certificate that has work due; recovery on every tick."""

    if not lane_enabled() or lane_paused():
        return 0
    recover_stale_procuracao_syncs()
    seed_procuracao_syncs()
    started = 0
    for certificate_id in due_certificate_ids():
        sync_id = next_due_sync_id(certificate_id)
        if sync_id is not None and _enqueue(sync_id):
            started += 1
    return started


@shared_task(name="hub.poll_procuracao_sync")  # type: ignore[untyped-decorator]
def poll_procuracao_sync(sync_id: str) -> dict[str, Any]:
    if not lane_enabled():
        return {"state": "disabled"}
    result = run_procuracao_sync(sync_id)
    if result.get("pause_seconds"):
        cache.set(PAUSE_CACHE_KEY, True, int(result["pause_seconds"]))
    certificate_id = result.get("certificate_id")
    if certificate_id is not None and not result.get("quarantined") and not lane_paused():
        chain_procuracao_certificate.apply_async(
            args=[str(certificate_id)], countdown=CHAIN_DELAY_SECONDS
        )
    return result


@shared_task(name="hub.chain_procuracao_certificate")  # type: ignore[untyped-decorator]
def chain_procuracao_certificate(certificate_id: str) -> int:
    """After a company, take the next due one of the same certificate (floor of 1 s)."""

    if not lane_enabled() or lane_paused():
        return 0
    sync_id = next_due_sync_id(certificate_id)
    return int(sync_id is not None and _enqueue(sync_id))


@shared_task(name="hub.purge_roster_artifacts")  # type: ignore[untyped-decorator]
def purge_roster_artifacts() -> dict[str, int]:
    """Retention of roster uploads (E4); runs whatever the state of the collection lane."""

    return company_roster.purge_roster_artifacts()


@shared_task(name="hub.notify_office_certificates")  # type: ignore[untyped-decorator]
def notify_office_certificates() -> int:
    """Daily: the e-CNPJ of a procuração office is about to expire (30, 15, 7, 3, 1 days) or has
    already expired and collection stopped."""

    return (
        procuracao_alerts.notify_office_certificate_expiring()
        + procuracao_alerts.notify_office_certificate_expired()
    )


@shared_task(name="hub.notify_lost_procuracoes")  # type: ignore[untyped-decorator]
def notify_lost_procuracoes() -> int:
    """Daily: companies that had a procuração and no longer do."""

    return procuracao_alerts.notify_lost_procuracoes()


@shared_task(name="hub.check_procuracao_lane")  # type: ignore[untyped-decorator]
def check_procuracao_lane() -> dict[str, Any]:
    """Hourly while the lane is on: logs a warning when collection is falling behind."""

    return procuracao_alerts.lane_health()
