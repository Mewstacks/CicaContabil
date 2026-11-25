"""Fila de trabalhos do escritorio (Fase 2, peca 3, D-332).

O gateway nunca fala com o banco do Dominio. Ele enfileira um trabalho (`ferramenta` e
`argumentos`, o contrato do `dominio-mcp relay-job`) e o agente do computador do escritorio,
que so faz conexao de saida, puxa so a fila do proprio escritorio, executa e devolve o envelope.

Limites, todos com teste: so as onze ferramentas do arquivo `dominio_tools.json`; argumentos
<= 16 KB e 8 niveis; ate 5 trabalhos abertos por escritorio; trabalho parado na fila por mais de
60 s ou em execucao por mais de 120 s expira; so o agente que pegou o trabalho entrega o
resultado, uma vez, com o `id` e o contrato conferidos.
"""

from __future__ import annotations

import asyncio
import functools
import json
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.intelligence.models import EdgeAgent
from apps.mcpgateway.models import McpJob, McpSetting
from apps.organizations.models import Organization

RELAY_CONTRACT = 1
MAX_ARGUMENT_BYTES = 16 * 1024
MAX_ARGUMENT_DEPTH = 8
MAX_OPEN_JOBS = 5
MAX_ENVELOPE_BYTES = 20 * 1024
QUEUE_TTL = timedelta(seconds=60)
RUN_TTL = timedelta(seconds=120)
AGENT_ONLINE_WINDOW = timedelta(seconds=120)
CALL_TIMEOUT_SECONDS = 25
POLL_INTERVAL = 0.3
_TOOLS_FILE = Path(__file__).with_name("dominio_tools.json")


class JobError(Exception):
    """Falha esperada: a mensagem vai para a pessoa, em portugues, sem detalhe interno."""


@functools.cache
def _tool_definitions() -> tuple[dict[str, Any], ...]:
    return tuple(json.loads(_TOOLS_FILE.read_text(encoding="utf-8")))


def dominio_tools() -> list[dict[str, Any]]:
    return [dict(tool) for tool in _tool_definitions()]


def dominio_tool_names() -> frozenset[str]:
    return frozenset(str(tool["name"]) for tool in _tool_definitions())


def is_enabled(organization: Organization) -> bool:
    return McpSetting.objects.filter(organization=organization, enabled=True).exists()


def active_agents(organization: Organization) -> Any:
    return EdgeAgent.objects.filter(organization=organization, status=EdgeAgent.Status.ACTIVE)


def agent_online(organization: Organization) -> bool:
    since = timezone.now() - AGENT_ONLINE_WINDOW
    return bool(active_agents(organization).filter(last_seen_at__gte=since).exists())


def tools_visible(organization: Organization) -> bool:
    """O conector mostra as ferramentas do Dominio so com a chave ligada e um agente pareado."""
    return is_enabled(organization) and active_agents(organization).exists()


def _depth(value: Any, level: int = 0) -> int:
    if level > MAX_ARGUMENT_DEPTH:
        return level
    if isinstance(value, dict):
        return max((_depth(v, level + 1) for v in value.values()), default=level + 1)
    if isinstance(value, list):
        return max((_depth(v, level + 1) for v in value), default=level + 1)
    return level


def sweep(organization: Organization) -> None:
    """Expira o que ficou parado; roda a cada pedido e a cada puxada do agente."""
    now = timezone.now()
    McpJob.objects.filter(
        organization=organization, status=McpJob.Status.PENDING, created_at__lt=now - QUEUE_TTL
    ).update(status=McpJob.Status.EXPIRED, error_code="fila_expirada", finished_at=now)
    McpJob.objects.filter(
        organization=organization, status=McpJob.Status.CLAIMED, claimed_at__lt=now - RUN_TTL
    ).update(status=McpJob.Status.EXPIRED, error_code="execucao_expirada", finished_at=now)


def enqueue(
    *, organization: Organization, user: Any, tool: str, arguments: dict[str, Any], request: Any
) -> McpJob:
    if tool not in dominio_tool_names():
        raise JobError("Ferramenta não disponível neste conector.")
    encoded = json.dumps(arguments, ensure_ascii=False, separators=(",", ":"), default=str)
    if len(encoded.encode("utf-8")) > MAX_ARGUMENT_BYTES or _depth(arguments) > MAX_ARGUMENT_DEPTH:
        raise JobError("Argumentos grandes demais.")
    if not agent_online(organization):
        raise JobError(
            "O computador do escritório não está conectado. Confira o serviço no servidor."
        )
    with transaction.atomic():
        # serializa por escritorio: sem isso duas chamadas juntas furam o teto de trabalhos
        Organization.objects.select_for_update().filter(pk=organization.pk).first()
        sweep(organization)
        open_jobs = McpJob.objects.filter(
            organization=organization, status__in=[McpJob.Status.PENDING, McpJob.Status.CLAIMED]
        ).count()
        if open_jobs >= MAX_OPEN_JOBS:
            raise JobError("Há consultas demais em andamento neste escritório. Tente em instantes.")
        job = McpJob.objects.create(
            organization=organization,
            requested_by=user,
            tool=tool,
            arguments=arguments,
        )
    record_event(
        action="mcpgateway.job_requested",
        actor=user,
        organization=organization,
        target=job,
        request=request,
        metadata={"tool": tool},
    )
    return job


def relay_payload(job: McpJob) -> dict[str, Any]:
    """O corpo que o agente entrega ao `relay-job`: sem campo de SQL, contrato 1."""
    return {
        "contrato": RELAY_CONTRACT,
        "id": job.id.hex,
        "ferramenta": job.tool,
        "argumentos": job.arguments,
    }


def touch_agent(agent: EdgeAgent) -> None:
    agent.last_seen_at = timezone.now()
    agent.save(update_fields=["last_seen_at", "updated_at"])


def try_claim(agent: EdgeAgent) -> McpJob | None:
    """Uma tentativa, curta e atomica; quem espera e o chamador (sem travar o processo)."""
    sweep(agent.organization)
    with transaction.atomic():
        job = (
            McpJob.objects.select_for_update(skip_locked=True)
            .filter(organization=agent.organization, status=McpJob.Status.PENDING)
            .order_by("created_at")
            .first()
        )
        if job is not None:
            job.status = McpJob.Status.CLAIMED
            job.agent = agent
            job.claimed_at = timezone.now()
            job.save(update_fields=["status", "agent", "claimed_at"])
        return job


async def claim(agent: EdgeAgent, *, wait_seconds: float = 0) -> McpJob | None:
    """Long-poll sem travar: o Hub roda em ASGI e as views sincronas dividem UMA thread por
    processo, entao a espera e `asyncio.sleep` e cada acesso ao banco e uma unidade curta."""
    deadline = time.monotonic() + max(0.0, wait_seconds)
    await sync_to_async(touch_agent)(agent)
    while True:
        job = await sync_to_async(try_claim)(agent)
        if job is not None or time.monotonic() >= deadline:
            return job
        await asyncio.sleep(POLL_INTERVAL)


def finish(*, agent: EdgeAgent, job_id: str, envelope: Any) -> McpJob:
    if not isinstance(envelope, dict) or not isinstance(envelope.get("ok"), bool):
        raise JobError("Envelope inválido.")
    if len(json.dumps(envelope, default=str).encode("utf-8")) > MAX_ENVELOPE_BYTES:
        raise JobError("Envelope grande demais.")
    with transaction.atomic():
        job = (
            McpJob.objects.select_for_update()
            .filter(
                id=job_id,
                organization=agent.organization,
                agent=agent,
                status=McpJob.Status.CLAIMED,
            )
            .first()
        )
        if job is None:
            raise JobError("Trabalho desconhecido ou já encerrado.")
        if envelope.get("contrato") != RELAY_CONTRACT or envelope.get("id") != job.id.hex:
            raise JobError("Envelope de outro trabalho.")
        job.finished_at = timezone.now()
        if envelope["ok"]:
            body = envelope.get("resultado")
            if not isinstance(body, dict):
                raise JobError("Envelope sem resultado.")
            job.status, job.result = McpJob.Status.DONE, body
        else:
            error = envelope.get("erro")
            error = error if isinstance(error, dict) else {}
            job.status, job.result = McpJob.Status.FAILED, {"erro": error}
            job.error_code = str(error.get("codigo", "recusado"))[:64]
        job.save(update_fields=["status", "result", "error_code", "finished_at"])
    return job


def _refresh(job: McpJob) -> McpJob:
    job.refresh_from_db()
    return job


def _expire(job: McpJob) -> McpJob:
    McpJob.objects.filter(
        pk=job.pk, status__in=[McpJob.Status.PENDING, McpJob.Status.CLAIMED]
    ).update(status=McpJob.Status.EXPIRED, error_code="sem_resposta", finished_at=timezone.now())
    return _refresh(job)


async def await_result(job: McpJob, *, timeout: float = CALL_TIMEOUT_SECONDS) -> McpJob:
    deadline = time.monotonic() + timeout
    terminal = {McpJob.Status.DONE, McpJob.Status.FAILED, McpJob.Status.EXPIRED}
    while True:
        job = await sync_to_async(_refresh)(job)
        if job.status in terminal:
            return job
        if time.monotonic() >= deadline:
            return await sync_to_async(_expire)(job)
        await asyncio.sleep(POLL_INTERVAL)
