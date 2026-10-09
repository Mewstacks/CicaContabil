"""Os pontos de entrada que o agente Windows usa para entregar o ERP.

Montados sobre o protocolo v2 que a CICA já tem, por D-284 e D-287: a
autenticação é a mesma do resto do agente — identificador, mTLS quando exigido e
assinatura do corpo — e vem importada de `apps.intelligence.agent_v2`, não
reescrita aqui.

O ciclo tem quatro passos. O agente pergunta o que rodar, abre uma execução,
envia as páginas e fecha. O que o catálogo devolve já vem filtrado pelo que este
escritório pode executar: contrato não validado não sai, e contrato que depende de
uma empresa-fonte armada só sai se ela estiver armada — nada vem armado por
padrão, porque errar para o lado permissivo leria o salário dos funcionários de
todo cliente.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.audit.services import record_event
from apps.hub.models import Connector
from apps.intelligence.agent_v2 import agent_error, agent_payload, authenticated_agent
from apps.intelligence.models import EdgeAgent
from apps.profitability.catalog import load_catalog
from apps.profitability.models import CompanyErpProfile, IngestBatch, IngestRun, SistemaOrigem

# Teto de linhas por página. O agente pagina; uma página gigante só transferiria o
# problema de memória do worker para o processo web.
MAX_ROWS_PER_BATCH = 2_000
MAX_BATCHES_PER_RUN = 1_000


def _connector(agent: EdgeAgent, source_system: str) -> Connector | None:
    """O conector habilitado para esta origem, ou nada.

    Não é criado sob demanda: um conector que nasce sozinho no primeiro ciclo é
    configuração aparecendo sem ninguém ter configurado nada.
    """

    if source_system == SistemaOrigem.DOMINIO:
        kind = Connector.Kind.DOMINIO_AGENT
    elif source_system == SistemaOrigem.SIESCON:
        kind = Connector.Kind.SIESCON
    else:
        return None
    return Connector.objects.filter(
        organization=agent.organization, kind=kind, enabled=True
    ).first()


def _papeis_armados(agent: EdgeAgent, source_system: str) -> set[str]:
    papeis: set[str] = set()
    for perfil in CompanyErpProfile.objects.filter(
        organization=agent.organization,
        sistema_origem=source_system,
        codi_emp__isnull=False,
        deleted_at__isnull=True,
    ).values_list("papel", flat=True):
        papeis |= set(perfil or [])
    return papeis


@csrf_exempt
@require_POST
def datasets(request: HttpRequest) -> JsonResponse:
    """Diz ao agente o que ele deve executar, e com qual consulta exata."""

    agent = authenticated_agent(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    if not settings.PROFITABILITY_SYNC_ENABLED:
        return JsonResponse({"datasets": [], "manifest_sha256": "", "enabled": False})
    payload = agent_payload(request)
    if payload is None:
        return agent_error("Pedido inválido.", 400)
    source_system = str(payload.get("source_system") or SistemaOrigem.DOMINIO)
    if source_system not in SistemaOrigem.values:
        return agent_error("Sistema de origem desconhecido.", 400)
    if _connector(agent, source_system) is None:
        return agent_error("O escritório não tem conector desta origem habilitado.", 409)

    catalog = load_catalog()
    armados = _papeis_armados(agent, source_system)
    saida: list[dict[str, Any]] = []
    for definition in catalog.definitions.values():
        if definition.source_system != source_system or not definition.validated:
            continue
        if definition.requires_source_role and definition.requires_source_role not in armados:
            continue
        saida.append(
            {
                "code": definition.code,
                "schema_version": definition.schema_version,
                "query_sha256": definition.query_sha256,
                "parameters": [
                    {"name": p.name, "odbc_type": p.odbc_type} for p in definition.parameters
                ],
                "allowed_run_kinds": list(definition.allowed_run_kinds),
                "max_rows_per_run": definition.max_rows_per_run,
            }
        )
    saida.sort(key=lambda item: item["code"])
    response = JsonResponse(
        {"datasets": saida, "manifest_sha256": catalog.manifest_sha256, "enabled": True}
    )
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_POST
def open_run(request: HttpRequest) -> JsonResponse:
    """Abre uma execução, recusando o que o contrato vigente não reconhece."""

    agent = authenticated_agent(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    if not settings.PROFITABILITY_SYNC_ENABLED:
        return agent_error("A sincronização de rentabilidade está desligada.", 409)
    payload = agent_payload(request)
    if payload is None:
        return agent_error("Pedido inválido.", 400)
    source_system = str(payload.get("source_system") or SistemaOrigem.DOMINIO)
    connector = _connector(agent, source_system)
    if connector is None:
        return agent_error("O escritório não tem conector desta origem habilitado.", 409)
    dataset_code = str(payload.get("dataset_code") or "")
    run_kind = str(payload.get("run_kind") or "")
    idempotency_key = str(payload.get("idempotency_key") or "")
    parameters = payload.get("parameters") or []
    if not idempotency_key or len(idempotency_key) > 160:
        return agent_error("Chave de idempotência inválida.", 400)
    if run_kind not in IngestRun.RunKind.values:
        return agent_error("Tipo de execução desconhecido.", 400)
    if not isinstance(parameters, list):
        return agent_error("Parâmetros inválidos.", 400)

    try:
        schema_version = int(payload.get("schema_version") or 0)
        definition = load_catalog().get_dispatchable(source_system, dataset_code, schema_version)
    except (TypeError, ValueError) as exc:
        return agent_error(str(exc), 400)
    if run_kind not in definition.allowed_run_kinds:
        return agent_error("Este contrato não aceita esse tipo de execução.", 400)

    # Repetir a mesma chave devolve a execução já aberta em vez de criar outra:
    # é o que faz uma reconexão do agente retomar em vez de duplicar.
    run, criado = IngestRun.objects.get_or_create(
        organization=agent.organization,
        connector=connector,
        idempotency_key=idempotency_key,
        defaults={
            "source_system": source_system,
            "dataset_code": dataset_code,
            "schema_version": definition.schema_version,
            "query_sha256": definition.query_sha256,
            "manifest_sha256": load_catalog().manifest_sha256,
            "run_kind": run_kind,
            "parameters": parameters,
            "status": IngestRun.Status.RECEIVING,
        },
    )
    if criado:
        record_event(
            action="profitability.ingest_run.opened",
            organization=agent.organization,
            target=run,
            request=request,
            metadata={"dataset": dataset_code, "kind": run_kind, "source": source_system},
        )
    response = JsonResponse(
        {"run_id": str(run.id), "status": run.status}, status=201 if criado else 200
    )
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_POST
def append_batch(request: HttpRequest, run_id: UUID) -> JsonResponse:
    """Recebe uma página de linhas e guarda cifrada até o processamento."""

    agent = authenticated_agent(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    payload = agent_payload(request)
    if payload is None:
        return agent_error("Página inválida.", 400)
    run = IngestRun.objects.filter(
        id=run_id, organization=agent.organization, status=IngestRun.Status.RECEIVING
    ).first()
    if run is None:
        return agent_error("Execução não encontrada para este agente.", 404)

    rows = payload.get("rows")
    sequence = payload.get("sequence")
    if (
        not isinstance(rows, list)
        or not all(isinstance(row, dict) for row in rows)
        or len(rows) > MAX_ROWS_PER_BATCH
        or not isinstance(sequence, int)
        or not 0 <= sequence < MAX_BATCHES_PER_RUN
    ):
        return agent_error("Página inválida.", 400)

    serialized = json.dumps(rows)
    checksum = hashlib.sha256(serialized.encode()).hexdigest()
    declarado = str(payload.get("checksum_sha256") or "")
    if declarado and declarado != checksum:
        # O agente disse uma coisa e enviou outra: a página não entra.
        return agent_error("A página não confere com a soma declarada.", 400)

    with transaction.atomic():
        _, criado = IngestBatch.objects.get_or_create(
            run=run,
            sequence=sequence,
            defaults={
                "organization": agent.organization,
                "row_count": len(rows),
                "checksum_sha256": checksum,
                "payload": serialized,
            },
        )
        if criado:
            IngestRun.objects.filter(pk=run.pk).update(
                row_count=run.row_count + len(rows), batch_count=run.batch_count + 1
            )
    return JsonResponse({"status": "received", "sequence": sequence, "duplicate": not criado})


@csrf_exempt
@require_POST
def complete_run(request: HttpRequest, run_id: UUID) -> JsonResponse:
    """Fecha o recebimento e enfileira o processamento."""

    from apps.profitability.tasks import process_ingest_run

    agent = authenticated_agent(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    run = IngestRun.objects.filter(
        id=run_id, organization=agent.organization, status=IngestRun.Status.RECEIVING
    ).first()
    if run is None:
        return agent_error("Execução não encontrada para este agente.", 404)

    payload = agent_payload(request) or {}
    declarado = payload.get("row_count")
    if isinstance(declarado, int) and declarado != run.row_count:
        return agent_error("Contagem declarada diverge das páginas recebidas.", 409)

    run.status = IngestRun.Status.PROCESSING
    run.save(update_fields=("status", "updated_at"))
    record_event(
        action="profitability.ingest_run.completed",
        organization=agent.organization,
        target=run,
        request=request,
        metadata={"dataset": run.dataset_code, "rows": run.row_count, "pages": run.batch_count},
    )
    process_ingest_run.delay(str(run.id))
    return JsonResponse({"status": run.status})


@csrf_exempt
@require_POST
def fail_run(request: HttpRequest, run_id: UUID) -> JsonResponse:
    """O agente desistiu: a execução fica registrada como falha, não some."""

    agent = authenticated_agent(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    run = IngestRun.objects.filter(
        id=run_id,
        organization=agent.organization,
        status__in=(IngestRun.Status.RECEIVING, IngestRun.Status.PROCESSING),
    ).first()
    if run is None:
        return agent_error("Execução não encontrada para este agente.", 404)

    payload = agent_payload(request) or {}
    run.status = IngestRun.Status.FAILED
    run.error_code = str(payload.get("code") or "agent_failure")[:80]
    run.completed_at = timezone.now()
    run.save(update_fields=("status", "error_code", "completed_at", "updated_at"))
    record_event(
        action="profitability.ingest_run.failed",
        organization=agent.organization,
        target=run,
        request=request,
        metadata={"dataset": run.dataset_code, "code": run.error_code},
    )
    return JsonResponse({"status": run.status})
