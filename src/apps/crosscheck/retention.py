"""Retenção do Contraprova (D-302).

Arquivos de entrada: 24 h depois de a conferência terminar (rascunho: 72 h sem movimento).
Achados e relatório: 90 dias. O cabeçalho da conferência e os recibos dos arquivos (papel,
tamanho, hash) ficam como trilha; só o conteúdo some.
"""

from __future__ import annotations

import logging
from datetime import datetime

from django.db.models import Q
from django.utils import timezone

from apps.audit.services import record_event

from . import limits
from .models import (
    CrosscheckDominioRow,
    CrosscheckFinding,
    CrosscheckInput,
    CrosscheckRun,
    crosscheck_storage,
)

logger = logging.getLogger(__name__)

BATCH = 50
MAX_BATCHES = 20


def _delete_object(name: str, *, keep_for: CrosscheckInput | None = None) -> None:
    """Apaga o objeto, a não ser que outra entrada ainda não purgada o referencie."""

    if not name:
        return
    shared = CrosscheckInput.objects.filter(content=name, purged_at__isnull=True)
    if keep_for is not None:
        shared = shared.exclude(pk=keep_for.pk)
    if not shared.exists():
        crosscheck_storage().delete(name)


def _purge_run_inputs(run: CrosscheckRun, now: datetime) -> int:
    purged = 0
    for item in run.inputs.filter(purged_at__isnull=True):
        name = item.content.name or ""
        try:
            _delete_object(name, keep_for=item)
        except Exception:
            logger.exception("crosscheck.purge_input_failed", extra={"run_id": str(run.id)})
            return purged
        CrosscheckInput.objects.filter(pk=item.pk).update(content="", purged_at=now)
        purged += 1
    # As linhas recebidas do agente são entrada como o arquivo: somem junto (D-302).
    CrosscheckDominioRow.objects.filter(run=run).delete()
    CrosscheckRun.objects.filter(pk=run.pk).update(inputs_purged_at=now)
    return purged


def purge_inputs(now: datetime | None = None) -> dict[str, int]:
    """Apaga os arquivos de conferências terminadas há mais de 24 h e de rascunhos parados."""

    now = now or timezone.now()
    counts = {"runs": 0, "files": 0, "drafts_expired": 0}
    for _ in range(MAX_BATCHES):
        due = list(
            CrosscheckRun.objects.filter(inputs_purged_at__isnull=True)
            .filter(
                Q(
                    state__in=(
                        CrosscheckRun.State.DONE,
                        CrosscheckRun.State.FAILED,
                        CrosscheckRun.State.CANCELED,
                    ),
                    finished_at__lte=now - limits.INPUT_RETENTION,
                )
                | Q(
                    state=CrosscheckRun.State.DRAFT,
                    updated_at__lte=now - limits.DRAFT_RETENTION,
                )
            )
            .select_related("organization")[:BATCH]
        )
        if not due:
            break
        for run in due:
            if run.state == CrosscheckRun.State.DRAFT:
                CrosscheckRun.objects.filter(pk=run.pk, state=CrosscheckRun.State.DRAFT).update(
                    state=CrosscheckRun.State.EXPIRED, finished_at=now
                )
                counts["drafts_expired"] += 1
            files = _purge_run_inputs(run, now)
            counts["runs"] += 1
            counts["files"] += files
            record_event(
                action="crosscheck.run.inputs_purged",
                organization=run.organization,
                target=run,
                metadata={"run_id": str(run.id), "tool": run.tool, "file_count": files},
            )
        if len(due) < BATCH:
            break
    return counts


def expire_results(now: datetime | None = None) -> dict[str, int]:
    """Apaga achados e relatório com mais de 90 dias; o cabeçalho continua."""

    now = now or timezone.now()
    counts = {"runs": 0}
    for _ in range(MAX_BATCHES):
        due = list(
            CrosscheckRun.objects.filter(
                state=CrosscheckRun.State.DONE, results_expire_at__lte=now
            ).select_related("organization")[:BATCH]
        )
        if not due:
            break
        for run in due:
            name = run.result_file.name
            try:
                if name:
                    crosscheck_storage().delete(name)
            except Exception:
                logger.exception("crosscheck.expire_result_failed", extra={"run_id": str(run.id)})
                continue
            CrosscheckFinding.objects.filter(run=run).delete()
            CrosscheckRun.objects.filter(pk=run.pk).update(
                state=CrosscheckRun.State.EXPIRED, result_file="", updated_at=now
            )
            counts["runs"] += 1
            record_event(
                action="crosscheck.run.results_expired",
                organization=run.organization,
                target=run,
                metadata={"run_id": str(run.id), "tool": run.tool},
            )
        if len(due) < BATCH:
            break
    return counts


def purge_expired(now: datetime | None = None) -> dict[str, int]:
    inputs = purge_inputs(now)
    results = expire_results(now)
    return {
        "runs_inputs": inputs["runs"],
        "files": inputs["files"],
        "drafts_expired": inputs["drafts_expired"],
        "runs_results": results["runs"],
    }
