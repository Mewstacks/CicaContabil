"""Rotas do agente Windows para a fila RPA (`/api/agent/v2/rpa/`).

Autenticação é a do resto do agente (`authenticated_agent`: identificador, mTLS e assinatura).
Com ``RPA_AGENT_ENABLED`` desligado todas as rotas respondem 404, que o agente lê como "sem
trabalho". Todas as respostas são ``no-store``.

* ``next``                 pede um trabalho dos tipos que o agente declara saber executar.
* ``<id>/heartbeat``       renova a reserva e informa a fase (``phase``).
* ``<id>/artifacts``       entrega um arquivo (base64) com hash; repetir é inofensivo.
* ``<id>/complete``        fecha com o resultado.
* ``<id>/failure``         desiste com um código fixo e texto curto sem dado de linha.

Toda chamada depois de ``next`` carrega ``lease_token``; sem ele, ou com o de uma reserva antiga,
a resposta é 409 ``reserva_perdida``.
"""

from __future__ import annotations

import base64
import binascii
from typing import Any
from uuid import UUID

from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.intelligence.agent_v2 import agent_error, agent_payload, authenticated_agent
from apps.intelligence.models import EdgeAgent

from . import registry, services
from .models import RpaJob
from .registry import RpaError

MAX_BODY = 36_000_000


def _authenticate(request: HttpRequest) -> EdgeAgent | JsonResponse:
    if not services.agent_enabled():
        return agent_error("Recurso desligado.", 404)
    agent = authenticated_agent(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    return agent


def _no_store(response: JsonResponse) -> JsonResponse:
    response["Cache-Control"] = "no-store"
    return response


def _problem(exc: RpaError) -> JsonResponse:
    status = {"nao_encontrado": 404, "reserva_perdida": 409, "resultado_diferente": 409}.get(
        exc.code, 422
    )
    return _no_store(JsonResponse({"detail": exc.message, "code": exc.code}, status=status))


def _lease_token(payload: dict[str, Any]) -> str:
    return str(payload.get("lease_token") or "")


@csrf_exempt
@require_POST
def next_job(request: HttpRequest) -> JsonResponse:
    agent = _authenticate(request)
    if isinstance(agent, JsonResponse):
        return agent
    payload = agent_payload(request, 16_384)
    if payload is None:
        return agent_error("Pedido inválido.", 400)
    raw_kinds = payload.get("kinds")
    if not isinstance(raw_kinds, list) or not all(isinstance(k, str) for k in raw_kinds):
        return agent_error("Informe os tipos de trabalho que o agente executa.", 400)
    claimed = services.claim_next(
        organization=agent.organization, agent_id=str(agent.id), kinds=raw_kinds[:40]
    )
    if claimed is None:
        return _no_store(JsonResponse({"job": None}))
    job, token = claimed
    spec = registry.get(job.kind)
    return _no_store(
        JsonResponse(
            {
                "job": {
                    "id": str(job.id),
                    "kind": job.kind,
                    "payload": job.payload,
                    "attempt": job.attempts,
                    "lease_token": token,
                    "lease_seconds": spec.lease_seconds,
                    "exclusive_group": spec.exclusive_group,
                }
            }
        )
    )


def _call(request: HttpRequest, job_id: UUID, action: str) -> JsonResponse:
    agent = _authenticate(request)
    if isinstance(agent, JsonResponse):
        return agent
    payload = agent_payload(request, MAX_BODY if action == "artifact" else 1_000_000)
    if payload is None:
        return agent_error("Pedido inválido.", 400)
    common: dict[str, Any] = {
        "job_id": job_id,
        "organization": agent.organization,
        "agent_id": str(agent.id),
        "token": _lease_token(payload),
    }
    try:
        if action == "heartbeat":
            job = services.heartbeat(**common, phase=str(payload.get("phase") or "")[:40])
            return _no_store(JsonResponse({"status": "ok", "lease_expires_at": _iso(job)}))
        if action == "artifact":
            try:
                content = base64.b64decode(str(payload.get("content_base64") or ""), validate=True)
            except (binascii.Error, ValueError):
                return agent_error("Conteúdo do arquivo inválido.", 400)
            artifact = services.attach_artifact(
                **common,
                name=str(payload.get("name") or "arquivo"),
                content=content,
                claimed_sha256=str(payload.get("sha256") or ""),
                content_type=str(payload.get("content_type") or ""),
            )
            return _no_store(JsonResponse({"status": "stored", "sha256": artifact.sha256}))
        if action == "complete":
            result = payload.get("result")
            if not isinstance(result, dict):
                return agent_error("Resultado inválido.", 400)
            services.complete(**common, result=result)
            return _no_store(JsonResponse({"status": "completed"}))
        services.fail(
            **common,
            code=str(payload.get("code") or "agent_error"),
            detail=str(payload.get("detail") or ""),
        )
        return _no_store(JsonResponse({"status": "failed"}))
    except RpaError as exc:
        return _problem(exc)


def _iso(job: RpaJob) -> str | None:
    return job.lease_expires_at.isoformat() if job.lease_expires_at else None


@csrf_exempt
@require_POST
def heartbeat(request: HttpRequest, job_id: UUID) -> JsonResponse:
    return _call(request, job_id, "heartbeat")


@csrf_exempt
@require_POST
def artifact(request: HttpRequest, job_id: UUID) -> JsonResponse:
    return _call(request, job_id, "artifact")


@csrf_exempt
@require_POST
def complete(request: HttpRequest, job_id: UUID) -> JsonResponse:
    return _call(request, job_id, "complete")


@csrf_exempt
@require_POST
def failure(request: HttpRequest, job_id: UUID) -> JsonResponse:
    return _call(request, job_id, "failure")
