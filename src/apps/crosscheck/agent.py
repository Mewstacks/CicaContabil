"""UF x Domínio pelo agente Windows: pedido, recebimento e leitura das linhas (D-300, Q-47).

O agente consulta só o dataset `fiscal_counterparts` do catálogo embutido nele; a nuvem manda o
código, a versão, o hash e os parâmetros. O dataset nasce `validated: false` e atrás de
`CONTRAPROVA_AGENT_ENABLED`: ligado só depois do ensaio na base real (D-86, etapa 12). Até lá o
caminho por arquivo (CSV/XLSX) cobre a função.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.hub.models import ClientCompany, Connector
from apps.profitability.catalog import load_catalog
from apps.profitability.models import CompanyErpProfile, SistemaOrigem

from .engine.dominio_file import DominioRow
from .engine.tools import UF_DOMINIO
from .models import CrosscheckAgentJob, CrosscheckDominioRow, CrosscheckRun
from .services import CrosscheckError, _audit

DATASET_CODE = "fiscal_counterparts"
SOURCE_SYSTEM = SistemaOrigem.DOMINIO
#: Sem sinal de vida do agente por este tempo, o pedido deixa de esperar ou volta à fila.
JOB_STALE_AFTER = timedelta(minutes=15)
#: O que o agente pode dizer ao desistir (`/failure`); qualquer outro texto vira `agent_error`.
FAILURE_CODES = frozenset(
    {"dataset_mismatch", "dataset_not_validated", "row_limit", "odbc_error", "agent_error"}
)
FAILURE_MESSAGES = {
    "dataset_mismatch": "A consulta do agente não confere com o contrato desta versão.",
    "dataset_not_validated": "A consulta ao Domínio ainda não foi homologada.",
    "row_limit": "A consulta passou do limite de linhas; use o arquivo.",
    "odbc_error": "O agente não conseguiu consultar o Domínio.",
    "agent_error": "O agente falhou ao entregar o resultado.",
    "contagem_diverge": "O agente entregou menos linhas do que informou.",
    "expirado": "O agente não respondeu a tempo.",
}
_DIGITS = re.compile(r"\d+")


def agent_enabled() -> bool:
    return bool(getattr(settings, "CONTRAPROVA_AGENT_ENABLED", False))


# ---------------------------------------------------------------------------------------
# Quem é a empresa no Domínio


def _normalized_code(raw: str) -> int | None:
    text = (raw or "").strip()
    if not text or not _DIGITS.fullmatch(text):
        return None
    return int(text)


def resolve_dominio_codi_emp(company: ClientCompany) -> int:
    """O `codi_emp` da empresa no Domínio, ou recusa. Nunca deduzido do CNPJ.

    Vem do perfil ERP do Domínio quando existe (a restrição de unicidade garante um só por
    sistema), senão do `dominio_code` da carteira sem zeros à esquerda. Recusa quando perfil e
    código divergem ou quando outra empresa do escritório normaliza para o mesmo número:
    consultar a empresa errada devolveria a UF de outro cliente.
    """

    profile_code = (
        CompanyErpProfile.objects.filter(
            organization_id=company.organization_id,
            empresa=company,
            sistema_origem=SOURCE_SYSTEM,
            deleted_at__isnull=True,
            codi_emp__isnull=False,
        )
        .values_list("codi_emp", flat=True)
        .first()
    )
    from_portfolio = _normalized_code(company.dominio_code)
    code: int
    if profile_code is not None:
        code = int(profile_code)
        if from_portfolio is not None and from_portfolio != code:
            raise CrosscheckError(
                "O código do Domínio no perfil da empresa diverge do cadastro.", code="codi_emp"
            )
    elif from_portfolio is not None:
        code = from_portfolio
    else:
        raise CrosscheckError("A empresa não tem código do Domínio.", code="codi_emp")
    for other_id, raw in (
        ClientCompany.objects.filter(organization_id=company.organization_id)
        .exclude(pk=company.pk)
        .exclude(dominio_code="")
        .values_list("pk", "dominio_code")
    ):
        if other_id != company.pk and _normalized_code(raw) == code:
            raise CrosscheckError(
                "Outra empresa do escritório tem o mesmo código no Domínio.", code="codi_emp"
            )
    return code


# ---------------------------------------------------------------------------------------
# Pedido


def _window(competence: date) -> tuple[date, date]:
    """Competência mais ou menos um mês: nota escriturada fora do mês da emissão ainda entra."""

    start = (competence.replace(day=1) - timedelta(days=1)).replace(day=1)
    after = (competence.replace(day=28) + timedelta(days=4)).replace(day=1)
    end = ((after.replace(day=28) + timedelta(days=4)).replace(day=1)) - timedelta(days=1)
    return start, end


def _parameters(
    codi_emp: int, start: date, end: date, names: tuple[Any, ...]
) -> list[dict[str, Any]]:
    values: dict[str, Any] = {
        "codi_emp_sai": codi_emp,
        "start_sai": start.isoformat(),
        "end_sai": end.isoformat(),
        "codi_emp_ent": codi_emp,
        "start_ent": start.isoformat(),
        "end_ent": end.isoformat(),
    }
    return [
        {"name": item.name, "value": values[item.name], "odbc_type": item.odbc_type}
        for item in names
    ]


def request_agent_job(run: CrosscheckRun, *, actor: Any, request: Any = None) -> CrosscheckAgentJob:
    if not agent_enabled():
        raise CrosscheckError("A consulta pelo agente não está habilitada.", code="agent_off")
    if run.tool != UF_DOMINIO or run.options.get("dominio_source") != "agente":
        raise CrosscheckError("Esta conferência não usa o agente do Domínio.")
    if not Connector.objects.filter(
        organization_id=run.organization_id, kind=Connector.Kind.DOMINIO_AGENT, enabled=True
    ).exists():
        raise CrosscheckError("O escritório não tem o agente do Domínio habilitado.")
    codi_emp = resolve_dominio_codi_emp(run.company)
    definition = load_catalog().get(SOURCE_SYSTEM, DATASET_CODE)
    start, end = _window(run.competence)
    with transaction.atomic():
        locked = CrosscheckRun.objects.select_for_update().get(pk=run.pk)
        if locked.state != CrosscheckRun.State.DRAFT:
            raise CrosscheckError("A conferência já foi enviada.")
        if locked.agent_jobs.filter(state__in=CrosscheckAgentJob.ACTIVE_STATES).exists():
            raise CrosscheckError("Já há uma consulta em andamento.", code="active")
        CrosscheckDominioRow.objects.filter(run=locked).delete()
        job = CrosscheckAgentJob.objects.create(
            organization_id=run.organization_id,
            run=locked,
            dataset_code=definition.code,
            schema_version=definition.schema_version,
            query_sha256=definition.query_sha256,
            parameters=_parameters(codi_emp, start, end, definition.parameters),
            codi_emp=codi_emp,
            window_start=start,
            window_end=end,
            row_limit=definition.max_rows_per_run,
            requested_by=actor if getattr(actor, "is_authenticated", False) else None,
        )
    _audit("agent.requested", run, actor, request, job_id=str(job.id))
    return job


def switch_to_file(run: CrosscheckRun, *, actor: Any, request: Any = None) -> None:
    """Saída do agente: volta o papel do Domínio para o arquivo e descarta a consulta."""

    with transaction.atomic():
        locked = CrosscheckRun.objects.select_for_update().get(pk=run.pk)
        if locked.state != CrosscheckRun.State.DRAFT:
            raise CrosscheckError("A conferência já foi enviada.")
        locked.agent_jobs.filter(state__in=CrosscheckAgentJob.ACTIVE_STATES).update(
            state=CrosscheckAgentJob.State.EXPIRED,
            error_code="abandonado",
            completed_at=timezone.now(),
        )
        CrosscheckDominioRow.objects.filter(run=locked).delete()
        locked.options = {**locked.options, "dominio_source": "arquivo"}
        locked.save(update_fields=["options", "updated_at"])
    _audit("agent.abandoned", run, actor, request)


# ---------------------------------------------------------------------------------------
# Leitura pela conferência e pela tela


def latest_job(run: CrosscheckRun) -> CrosscheckAgentJob | None:
    return run.agent_jobs.order_by("-created_at").first()


def rows_ready(run: CrosscheckRun) -> bool:
    job = latest_job(run)
    return job is not None and job.state == CrosscheckAgentJob.State.SUCCEEDED


def iter_rows(run: CrosscheckRun) -> Iterator[DominioRow]:
    """Linhas recebidas do agente, em páginas por id: nunca o conjunto inteiro na memória."""

    last = 0
    while True:
        page = list(run.dominio_rows.filter(id__gt=last).order_by("id")[:5000])
        if not page:
            return
        for row in page:
            yield DominioRow(key=row.chave, direcao=row.direcao, uf=row.uf)
        last = page[-1].id


def status_payload(job: CrosscheckAgentJob | None) -> dict[str, Any]:
    if job is None:
        return {"state": "none", "label": "", "rows": 0}
    return {
        "state": job.state,
        "label": job.get_state_display(),
        "rows": job.rows_received,
        "error": FAILURE_MESSAGES.get(job.error_code, "") if job.error_code else "",
    }


# ---------------------------------------------------------------------------------------
# Expiração (chamada pelo recuperador do Beat)


def expire_stale_jobs(now: Any = None) -> int:
    """Pedido que ninguém pegou, ou que o agente largou, deixa de esperar para sempre."""

    now = now or timezone.now()
    stale = now - JOB_STALE_AFTER
    abandoned = now - 4 * JOB_STALE_AFTER
    queued = CrosscheckAgentJob.objects.filter(
        state=CrosscheckAgentJob.State.QUEUED, created_at__lt=stale
    ).update(state=CrosscheckAgentJob.State.EXPIRED, error_code="expirado", completed_at=now)
    silent = CrosscheckAgentJob.objects.filter(
        state__in=(CrosscheckAgentJob.State.CLAIMED, CrosscheckAgentJob.State.RECEIVING),
        last_activity_at__lt=abandoned,
    ).update(state=CrosscheckAgentJob.State.EXPIRED, error_code="expirado", completed_at=now)
    return int(queued) + int(silent)
