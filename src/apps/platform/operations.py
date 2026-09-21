"""Durable execution records for scheduled platform operations."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps

from django.db import transaction
from django.db.models import OuterRef, Subquery
from django.utils import timezone

from apps.platform.models import OperationalRun

OperationResult = int | dict[str, int] | dict[str, object]


SCHEDULED_OPERATION_DETAILS: tuple[tuple[str, str], ...] = (
    (OperationalRun.Task.ADVANCE_LIFECYCLES, "Diariamente às 00:01"),
    (OperationalRun.Task.CLOSE_COMPETENCE, "Diariamente às 00:05"),
    (OperationalRun.Task.REFRESH_KNOWLEDGE, "Diariamente às 02:10"),
    (OperationalRun.Task.REFRESH_SHARED_KNOWLEDGE, "Diariamente às 02:25"),
    (OperationalRun.Task.PURGE_INTELLIGENCE, "Diariamente às 02:40"),
    (OperationalRun.Task.RETRY_ATTACHMENTS, "A cada 5 minutos"),
    (OperationalRun.Task.REFRESH_REFORM, "Diariamente às 05:20"),
)


def run_scheduled_operation(
    *, task: str, callback: Callable[[], OperationResult]
) -> OperationResult:
    """Execute one task and preserve a compact result even if it raises.

    No customer content, credentials, or provider payload belongs in this log.
    """

    run = OperationalRun.objects.create(task=task)
    try:
        result = callback()
    except Exception as exc:
        with transaction.atomic():
            OperationalRun.objects.filter(id=run.id).update(
                state=OperationalRun.State.FAILED,
                finished_at=timezone.now(),
                error_code=exc.__class__.__name__[:80],
                error_message=(
                    "A rotina falhou. Consulte os registros técnicos com o ID da execução."
                ),
            )
        raise
    summary: dict[str, object]
    if isinstance(result, int):
        summary = {"processed": result}
    else:
        summary = {str(key): value for key, value in result.items()}
    partial = bool(summary.get("escritorios_adiados", 0))
    OperationalRun.objects.filter(id=run.id).update(
        state=(OperationalRun.State.PARTIAL if partial else OperationalRun.State.SUCCEEDED),
        finished_at=timezone.now(),
        summary=summary,
    )
    return result


def track_scheduled_operation(
    task: str,
) -> Callable[[Callable[[], OperationResult]], Callable[[], OperationResult]]:
    """Decorate a no-argument Celery task with an operational outcome record."""

    def decorate(callback: Callable[[], OperationResult]) -> Callable[[], OperationResult]:
        @wraps(callback)
        def wrapped() -> OperationResult:
            return run_scheduled_operation(task=task, callback=callback)

        return wrapped

    return decorate


def scheduled_operation_overview() -> list[dict[str, object]]:
    """Return one compact, operator-safe status row for every scheduled task."""

    # Keep the console bounded as the execution ledger grows.  Pulling every
    # historical run just to render seven rows would eventually make the
    # developer screen slower precisely when it is most needed.
    latest_run_id = (
        OperationalRun.objects.filter(task=OuterRef("task"))
        .order_by("-started_at")
        .values("id")[:1]
    )
    latest_by_task = {
        run.task: run
        for run in OperationalRun.objects.filter(id=Subquery(latest_run_id))
    }
    rows: list[dict[str, object]] = []
    for task, cadence in SCHEDULED_OPERATION_DETAILS:
        run = latest_by_task.get(task)
        summary = ""
        if run and run.summary:
            if task == OperationalRun.Task.CLOSE_COMPETENCE:
                completed = int(run.summary.get("faturas_concluidas", 0))
                deferred = int(run.summary.get("escritorios_adiados", 0))
                summary = (
                    f"Competência {run.summary.get('competencia', '—')} · "
                    f"{completed} fatura{'s' if completed != 1 else ''} concluída"
                    f"{'s' if completed != 1 else ''} · "
                    f"{deferred} escritório{'s' if deferred != 1 else ''} adiado"
                    f"{'s' if deferred != 1 else ''}"
                )
            else:
                summary = " · ".join(
                    f"{key}: {value}" for key, value in run.summary.items()
                )
        rows.append(
            {
                "task": task,
                "label": OperationalRun.Task(task).label,
                "cadence": cadence,
                "run": run,
                "summary": summary,
            }
        )
    return rows
