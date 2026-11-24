"""Rotas do agente Windows para o Contraprova (fila "pull", `/api/agent/v2/contraprova/`).

A autenticação é a do resto do agente (identificador, mTLS quando exigido e assinatura do
corpo), importada de `apps.intelligence.agent_v2`. Com `CONTRAPROVA_AGENT_ENABLED` desligado
todas as rotas respondem 404, que o agente entende como "sem trabalho".

Protocolo (também em `docs/planejamento/etapas/15-contraprova.md`):

* `jobs/next`            pede um trabalho; o reivindicado volta à fila se o agente calar 15 min.
* `jobs/<id>/batches`    página de linhas (`sequence` em ordem); repetir uma já aceita é inofensivo.
* `jobs/<id>/complete`   fecha com a contagem; a nuvem confere contra o que recebeu.
* `jobs/<id>/failure`    desiste com um código fixo e um texto curto, sem dado de linha.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from django.db import models, transaction
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.audit.services import record_event
from apps.hub.models import Connector
from apps.intelligence.agent_v2 import agent_error, agent_payload, authenticated_agent
from apps.intelligence.models import EdgeAgent

from .agent import FAILURE_CODES, JOB_STALE_AFTER, agent_enabled
from .engine.dominio_file import UFS
from .engine.keys import is_well_formed
from .models import CrosscheckAgentJob, CrosscheckDominioRow, CrosscheckRun

PAGE_SIZE = 500
MAX_ROWS_PER_BATCH = 2_000
MAX_BATCHES_PER_JOB = 1_000


def _off() -> JsonResponse:
    return agent_error("Recurso desligado.", 404)


def _authenticate(request: HttpRequest) -> EdgeAgent | JsonResponse:
    if not agent_enabled():
        return _off()
    agent = authenticated_agent(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    return agent


def _connector_enabled(agent: EdgeAgent) -> bool:
    return Connector.objects.filter(
        organization=agent.organization, kind=Connector.Kind.DOMINIO_AGENT, enabled=True
    ).exists()


def _job_payload(job: CrosscheckAgentJob) -> dict[str, Any]:
    return {
        "id": str(job.id),
        "dataset_code": job.dataset_code,
        "schema_version": job.schema_version,
        "query_sha256": job.query_sha256,
        "parameters": job.parameters,
        "max_rows": job.row_limit,
        "page_size": PAGE_SIZE,
    }


def _reset_partial(job: CrosscheckAgentJob) -> None:
    """Trabalho retomado recomeça do zero: o agente refaz a consulta inteira."""

    CrosscheckDominioRow.objects.filter(job=job).delete()
    job.next_sequence = 0
    job.rows_received = 0


@csrf_exempt
@require_POST
def next_job(request: HttpRequest) -> JsonResponse:
    """Entrega um trabalho do escritório do agente, reivindicando sem duplicar."""

    agent = _authenticate(request)
    if isinstance(agent, JsonResponse):
        return agent
    payload = agent_payload(request)
    if payload is None:
        return agent_error("Pedido inválido.", 400)
    if str(payload.get("source_system") or "dominio") != "dominio":
        return agent_error("Sistema de origem desconhecido.", 400)
    if not _connector_enabled(agent):
        return JsonResponse({"job": None})
    now = timezone.now()
    stale_before = now - JOB_STALE_AFTER
    with transaction.atomic():
        own = (
            CrosscheckAgentJob.objects.select_for_update()
            .select_related("run")
            .filter(
                organization=agent.organization,
                state__in=(CrosscheckAgentJob.State.CLAIMED, CrosscheckAgentJob.State.RECEIVING),
                claimed_by=str(agent.id),
            )
            .order_by("claimed_at")
            .first()
        )
        job = own or (
            CrosscheckAgentJob.objects.select_for_update(skip_locked=True)
            .select_related("run")
            .filter(organization=agent.organization)
            .filter(
                models.Q(state=CrosscheckAgentJob.State.QUEUED)
                | models.Q(
                    state__in=(
                        CrosscheckAgentJob.State.CLAIMED,
                        CrosscheckAgentJob.State.RECEIVING,
                    ),
                    last_activity_at__lt=stale_before,
                )
            )
            .order_by("created_at")
            .first()
        )
        if job is None:
            return JsonResponse({"job": None})
        if job.run.state != CrosscheckRun.State.DRAFT:
            job.state = CrosscheckAgentJob.State.EXPIRED
            job.error_code = "abandonado"
            job.completed_at = now
            job.save(update_fields=["state", "error_code", "completed_at", "updated_at"])
            return JsonResponse({"job": None})
        if job.state != CrosscheckAgentJob.State.QUEUED and own is None:
            _reset_partial(job)
        elif job.state == CrosscheckAgentJob.State.RECEIVING and own is not None:
            # O mesmo agente voltou a pedir: ele perdeu o contexto, então recomeça.
            _reset_partial(job)
        job.state = CrosscheckAgentJob.State.CLAIMED
        job.claimed_by = str(agent.id)
        job.claimed_at = job.claimed_at or now
        job.last_activity_at = now
        job.save(
            update_fields=[
                "state",
                "claimed_by",
                "claimed_at",
                "last_activity_at",
                "next_sequence",
                "rows_received",
                "updated_at",
            ]
        )
    response = JsonResponse({"job": _job_payload(job)})
    response["Cache-Control"] = "no-store"
    return response


def _own_job(agent: EdgeAgent, job_id: UUID) -> CrosscheckAgentJob | None:
    job = (
        CrosscheckAgentJob.objects.select_for_update()
        .select_related("run")
        .filter(id=job_id, organization=agent.organization)
        .first()
    )
    if job is None or job.claimed_by != str(agent.id):
        return None
    return job


def _fail(job: CrosscheckAgentJob, code: str) -> None:
    job.state = CrosscheckAgentJob.State.FAILED
    job.error_code = code[:40]
    job.completed_at = timezone.now()
    job.save(update_fields=["state", "error_code", "completed_at", "updated_at"])
    CrosscheckDominioRow.objects.filter(job=job).delete()


def _clean_rows(raw: Any) -> list[CrosscheckDominioRow] | None:
    if not isinstance(raw, list) or len(raw) > MAX_ROWS_PER_BATCH:
        return None
    rows: list[CrosscheckDominioRow] = []
    for item in raw:
        if not isinstance(item, dict):
            return None
        key = str(item.get("chave_nfe") or "").strip().upper()
        direction = str(item.get("direcao") or "").strip().upper()
        uf = str(item.get("uf") or "").strip().upper()
        if not is_well_formed(key) or direction not in {"S", "E"} or (uf and uf not in UFS):
            return None
        rows.append(CrosscheckDominioRow(chave=key, direcao=direction, uf=uf))
    return rows


@csrf_exempt
@require_POST
def append_batch(request: HttpRequest, job_id: UUID) -> JsonResponse:
    agent = _authenticate(request)
    if isinstance(agent, JsonResponse):
        return agent
    payload = agent_payload(request, 4_000_000)
    if payload is None:
        return agent_error("Página inválida.", 400)
    try:
        sequence = int(payload.get("sequence", -1))
    except (TypeError, ValueError):
        sequence = -1
    rows = _clean_rows(payload.get("rows"))
    if sequence < 0 or rows is None:
        return agent_error("Página inválida.", 400)
    now = timezone.now()
    with transaction.atomic():
        job = _own_job(agent, job_id)
        if job is None:
            return agent_error("Trabalho não encontrado para este agente.", 404)
        if job.state not in {
            CrosscheckAgentJob.State.CLAIMED,
            CrosscheckAgentJob.State.RECEIVING,
        }:
            return agent_error("O trabalho não está recebendo páginas.", 409)
        if sequence < job.next_sequence:
            return JsonResponse({"status": "duplicate"})
        if sequence > job.next_sequence or sequence >= MAX_BATCHES_PER_JOB:
            return agent_error("Página fora de ordem.", 409)
        if job.rows_received + len(rows) > job.row_limit:
            _fail(job, "row_limit")
            return agent_error("A consulta passou do limite de linhas.", 413)
        for row in rows:
            row.run_id = job.run_id
            row.job_id = job.id
        CrosscheckDominioRow.objects.bulk_create(rows, batch_size=500, ignore_conflicts=True)
        job.state = CrosscheckAgentJob.State.RECEIVING
        job.next_sequence = sequence + 1
        job.rows_received += len(rows)
        job.last_activity_at = now
        job.save(
            update_fields=[
                "state",
                "next_sequence",
                "rows_received",
                "last_activity_at",
                "updated_at",
            ]
        )
    return JsonResponse({"status": "accepted"})


@csrf_exempt
@require_POST
def complete_job(request: HttpRequest, job_id: UUID) -> JsonResponse:
    agent = _authenticate(request)
    if isinstance(agent, JsonResponse):
        return agent
    payload = agent_payload(request, 16_384)
    if payload is None:
        return agent_error("Fechamento inválido.", 400)
    try:
        row_count = int(payload.get("row_count", -1))
        pages = int(payload.get("pages", -1))
    except (TypeError, ValueError):
        return agent_error("Fechamento inválido.", 400)
    with transaction.atomic():
        job = _own_job(agent, job_id)
        if job is None:
            return agent_error("Trabalho não encontrado para este agente.", 404)
        if job.state == CrosscheckAgentJob.State.SUCCEEDED:
            return JsonResponse({"status": "duplicate"})
        if job.state not in {
            CrosscheckAgentJob.State.CLAIMED,
            CrosscheckAgentJob.State.RECEIVING,
        }:
            return agent_error("O trabalho não está aberto.", 409)
        stored = CrosscheckDominioRow.objects.filter(job=job).count()
        # `ignore_conflicts` descarta chave repetida: a conta fecha com o que o agente leu.
        if row_count != job.rows_received or pages != job.next_sequence or stored > row_count:
            _fail(job, "contagem_diverge")
            return agent_error("A contagem não confere com o que foi recebido.", 409)
        job.state = CrosscheckAgentJob.State.SUCCEEDED
        job.completed_at = timezone.now()
        job.last_activity_at = job.completed_at
        job.save(update_fields=["state", "completed_at", "last_activity_at", "updated_at"])
    record_event(
        action="crosscheck.agent.received",
        organization=job.organization,
        target=job.run,
        metadata={"run_id": str(job.run_id), "job_id": str(job.id), "row_count": row_count},
    )
    return JsonResponse({"status": "completed"})


@csrf_exempt
@require_POST
def fail_job(request: HttpRequest, job_id: UUID) -> JsonResponse:
    agent = _authenticate(request)
    if isinstance(agent, JsonResponse):
        return agent
    payload = agent_payload(request, 16_384)
    if payload is None:
        return agent_error("Falha inválida.", 400)
    code = str(payload.get("error_code") or "")
    code = code if code in FAILURE_CODES else "agent_error"
    with transaction.atomic():
        job = _own_job(agent, job_id)
        if job is None:
            return agent_error("Trabalho não encontrado para este agente.", 404)
        if job.state in {CrosscheckAgentJob.State.SUCCEEDED, CrosscheckAgentJob.State.FAILED}:
            return JsonResponse({"status": "duplicate"})
        job.error_detail = str(payload.get("detail") or "")[:200]
        _fail(job, code)
        job.save(update_fields=["error_detail", "updated_at"])
    record_event(
        action="crosscheck.agent.failed",
        organization=job.organization,
        target=job.run,
        success=False,
        metadata={"run_id": str(job.run_id), "job_id": str(job.id), "reason": code},
    )
    return JsonResponse({"status": "recorded"})
