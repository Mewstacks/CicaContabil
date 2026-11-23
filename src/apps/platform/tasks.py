"""Scheduled platform billing work."""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.utils import timezone

from apps.platform import collection, dunning
from apps.platform.billing import close_competence
from apps.platform.models import OperationalRun, TenantContract, TenantLifecycle
from apps.platform.operations import track_scheduled_operation


@shared_task(name="platform.close_previous_competence")  # type: ignore[untyped-decorator]
@track_scheduled_operation(OperationalRun.Task.CLOSE_COMPETENCE)
def close_previous_competence() -> dict[str, object]:
    """Close the prior BRT competence; repeated beat delivery is safe."""

    current_month_start = timezone.localdate().replace(day=1)
    previous_day = current_month_start - timedelta(days=1)
    previous_month = previous_day.replace(day=1)
    deferred: list[str] = []
    invoices = close_competence(period_start=previous_month, deferred_organization_ids=deferred)
    return {
        "competencia": f"{previous_month:%m/%Y}",
        "faturas_concluidas": len(invoices),
        "escritorios_adiados": len(deferred),
    }


@shared_task(name="platform.advance_tenant_lifecycles")  # type: ignore[untyped-decorator]
@track_scheduled_operation(OperationalRun.Task.ADVANCE_LIFECYCLES)
def advance_tenant_lifecycles() -> int:
    """End a trial without making a commercial decision on behalf of Mewstack."""

    today = timezone.localdate()
    changed = 0
    contracts = TenantContract.objects.select_related("organization").filter(
        status=TenantContract.Status.TRIAL
    )
    for contract in contracts.iterator():
        lifecycle, _ = TenantLifecycle.objects.get_or_create(organization=contract.organization)
        if contract.status == TenantContract.Status.TRIAL and contract.trial_ends_on:
            if today > contract.trial_ends_on:
                contract.status = TenantContract.Status.GRACE
                contract.grace_ends_on = contract.trial_ends_on + timedelta(days=7)
                lifecycle.state = TenantLifecycle.State.GRACE
                lifecycle.reason = (
                    "Teste encerrado; novas operações aguardam definição comercial pela Mewstack."
                )
            else:
                continue
        else:
            continue
        contract.save(update_fields=["status", "grace_ends_on", "updated_at"])
        lifecycle.save(update_fields=["state", "reason", "updated_at"])
        changed += 1
    return changed


@shared_task(name="platform.enforce_payment_policy")  # type: ignore[untyped-decorator]
def enforce_payment_policy() -> dict[str, int]:
    """D-79 every day: the 7-day carência ends on a date, with or without a provider event."""

    if not collection.enabled():
        return {"skipped": 1}
    return dunning.enforce_all()


@shared_task(name="platform.reconcile_payments")  # type: ignore[untyped-decorator]
def reconcile_payments() -> dict[str, int]:
    """Find Asaas charges whose creation response was lost (no idempotency header exists)."""

    if not collection.enabled():
        return {"skipped": 1}
    return collection.reconcile_unconfirmed()
