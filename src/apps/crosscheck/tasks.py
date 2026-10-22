"""Tarefas do Contraprova: executar, recuperar e apagar o que venceu (D-302)."""

from __future__ import annotations

from functools import partial

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from . import limits
from .models import CrosscheckRun


@shared_task(name="crosscheck.process_run")  # type: ignore[untyped-decorator]
def process_run_task(run_id: str) -> str:
    """Executa uma conferência; o arrendamento torna a reentrega inofensiva."""

    from .services import process_run

    return process_run(run_id)


@shared_task(name="crosscheck.recover_runs")  # type: ignore[untyped-decorator]
def recover_runs() -> int:
    """Devolve à fila a conferência cujo worker morreu e reenvia a que ficou sem ser pega."""

    from .agent import expire_stale_jobs

    now = timezone.now()
    expire_stale_jobs(now)
    with transaction.atomic():
        stuck = list(
            CrosscheckRun.objects.filter(
                state=CrosscheckRun.State.PROCESSING, lease_until__lt=now
            ).values_list("id", flat=True)
        )
        CrosscheckRun.objects.filter(id__in=stuck).update(
            state=CrosscheckRun.State.QUEUED,
            stage="recovered",
            lease_token=None,
            lease_until=None,
        )
        waiting = list(
            CrosscheckRun.objects.filter(
                state=CrosscheckRun.State.QUEUED,
                queued_at__lt=now - limits.QUEUE_RECOVERY_AFTER,
            )
            .exclude(id__in=stuck)
            .values_list("id", flat=True)[:100]
        )
        for run_id in [*stuck, *waiting]:
            transaction.on_commit(partial(process_run_task.delay, str(run_id)))
    return len(stuck) + len(waiting)


@shared_task(name="crosscheck.purge_expired")  # type: ignore[untyped-decorator]
def purge_expired_task() -> dict[str, int]:
    from .retention import purge_expired

    return purge_expired()
