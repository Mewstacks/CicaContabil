"""Pontos do agente do escritorio: puxar o proximo trabalho e devolver o resultado.

Mesma identidade e assinatura do agente de sincronizacao (`X-Hub-Agent-*`, HMAC-SHA256 sobre
`timestamp.corpo`, janela de 5 min, mTLS opcional). O agente so le a fila do proprio escritorio
e so entrega resultado de trabalho que ele mesmo pegou. Desligado com o gateway.
"""

from __future__ import annotations

import json
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.intelligence.agent_api import _valid_mtls_client
from apps.intelligence.agents import verify_agent_signature
from apps.intelligence.models import EdgeAgent
from apps.mcpgateway import conf, jobs

MAX_BODY = 32 * 1024


def _json(payload: dict[str, Any], status: int = 200) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response


def _agent(request: HttpRequest) -> EdgeAgent | None:
    agent_id = request.headers.get("X-Hub-Agent-ID", "")
    try:
        agent = EdgeAgent.objects.select_related("organization").filter(id=agent_id).first()
    except (ValueError, TypeError, ValidationError):
        return None
    if (
        agent is None
        or not _valid_mtls_client(request, agent)
        or not verify_agent_signature(
            agent=agent,
            timestamp=request.headers.get("X-Hub-Agent-Timestamp", ""),
            body=request.body,
            signature=request.headers.get("X-Hub-Agent-Signature", ""),
        )
    ):
        return None
    return agent


def _payload(request: HttpRequest) -> dict[str, Any] | None:
    if len(request.body) > MAX_BODY:
        return None
    try:
        payload = json.loads(request.body or b"{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _authorize_claim(request: HttpRequest) -> tuple[EdgeAgent, float] | JsonResponse:
    if not conf.enabled():
        return _json({"error": "indisponivel"}, 404)
    agent = _agent(request)
    if agent is None:
        return _json({"error": "Agente não autorizado."}, 401)
    payload = _payload(request)
    if payload is None:
        return _json({"error": "Corpo inválido."}, 400)
    cap = float(getattr(settings, "MCP_AGENT_LONG_POLL_SECONDS", 10))
    asked = payload.get("wait", 0)
    wait = min(max(float(asked), 0.0), cap) if isinstance(asked, int | float) else 0.0
    return agent, wait


@csrf_exempt
async def claim(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return _json({"error": "method_not_allowed"}, 405)
    checked = await sync_to_async(_authorize_claim)(request)
    if isinstance(checked, JsonResponse):
        return checked
    agent, wait = checked
    job = await jobs.claim(agent, wait_seconds=wait)
    return _json({"job": jobs.relay_payload(job) if job else None})


@csrf_exempt
@require_POST
def result(request: HttpRequest) -> JsonResponse:
    if not conf.enabled():
        return _json({"error": "indisponivel"}, 404)
    agent = _agent(request)
    if agent is None:
        return _json({"error": "Agente não autorizado."}, 401)
    payload = _payload(request)
    if payload is None:
        return _json({"error": "Corpo inválido."}, 400)
    try:
        jobs.finish(
            agent=agent, job_id=str(payload.get("id", "")), envelope=payload.get("envelope")
        )
    except (jobs.JobError, ValueError) as exc:
        return _json({"error": str(exc)}, 409)
    return _json({"ok": True})
