"""Tarefas assíncronas da ingestão de rentabilidade.

O processamento sai da requisição de propósito: um contrato de horas pode trazer
centenas de milhares de linhas, e aplicar isso enquanto o agente espera põe o
processo web para segurar uma transação longa.
"""

from __future__ import annotations

from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.profitability.models import IngestRun


@shared_task(name="profitability.process_ingest_run")  # type: ignore[untyped-decorator]
def process_ingest_run(run_id: str) -> str:
    """Aplica uma execução e devolve o estado em que ela terminou.

    A falha é gravada na própria execução antes de subir: sem isso, um contrato
    errado deixa a execução presa em "processando" para sempre, e a tela não sabe
    dizer o que aconteceu.
    """

    from apps.profitability.ingest import process_run

    try:
        process_run(run_id)
    except ValueError as exc:
        IngestRun.objects.filter(pk=run_id).update(
            status=IngestRun.Status.FAILED,
            error_code=str(exc)[:80],
            completed_at=timezone.now(),
            updated_at=timezone.now(),
        )
        raise
    return IngestRun.Status.SUCCEEDED


@shared_task(name="profitability.reap_stale_runs")  # type: ignore[untyped-decorator]
def reap_stale_runs() -> int:
    """Fecha execuções que o agente abriu e abandonou.

    Um agente que perde a rede no meio do envio deixa a execução recebendo para
    sempre, e a chave de idempotência dele volta a bater na retomada — o que faria
    a próxima tentativa reaproveitar uma execução meio enviada, com contagem de
    linhas de duas leituras diferentes.
    """

    if not settings.PROFITABILITY_SYNC_ENABLED:
        return 0
    limite = timezone.now() - timedelta(hours=6)
    return IngestRun.objects.filter(
        status=IngestRun.Status.RECEIVING, updated_at__lt=limite
    ).update(
        status=IngestRun.Status.FAILED,
        error_code="abandonada_pelo_agente",
        completed_at=timezone.now(),
        updated_at=timezone.now(),
    )
