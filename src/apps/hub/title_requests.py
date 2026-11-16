"""Explicit monthly company title requests, independent of bank account configuration."""

from __future__ import annotations

import hmac
import re
from datetime import date, timedelta
from typing import Any
from uuid import UUID, uuid4, uuid5

from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.controlplane import company_queryset_for_module
from apps.hub.models import ClientCompany, FinancialAccount, ProductModule
from apps.intelligence.agent_scope import ACTIVE_PORTFOLIO_VERSION, validate_portfolio_scope
from apps.intelligence.models import CompanyTitleCollection, EdgeAgent, NativeTitleCollection
from apps.intelligence.native_title_contract import canonical_hash, contract_hash, validate_scope
from apps.organizations.models import Membership
from apps.platform.operation_access import require_operation_access

MAX_TITLE_REQUESTS = 2000
MAX_BATCH_JOBS = MAX_TITLE_REQUESTS
EDIT_ROLES = {"owner", "admin", "manager", "operator"}
type TitleJob = NativeTitleCollection | CompanyTitleCollection


class TitleRequestError(ValueError):
    pass


class TitleRequestConflict(TitleRequestError):
    pass


def authorize_title_company(
    company: ClientCompany, actor: User, *, write: bool = True
) -> Membership:
    company = ClientCompany.objects.select_related("organization").get(pk=company.pk)
    member = (
        Membership.objects.select_related("organization")
        .filter(
            organization_id=company.organization_id,
            user=actor,
            user__is_active=True,
            is_active=True,
            role__in=EDIT_ROLES if write else {*EDIT_ROLES, "auditor"},
        )
        .first()
    )
    if (
        member is None
        or not company_queryset_for_module(member, ProductModule.Code.RECONCILIATION)
        .filter(pk=company.pk)
        .exists()
    ):
        raise PermissionDenied("Seu acesso atual não permite consultar títulos desta empresa.")
    require_operation_access(company.organization, ProductModule.Code.RECONCILIATION)
    return member


def title_job_company(job: TitleJob) -> ClientCompany:
    return job.company if isinstance(job, CompanyTitleCollection) else job.financial_account.company


def _code(company: ClientCompany) -> int:
    value = company.dominio_code
    if (
        not isinstance(value, str)
        or not re.fullmatch(r"[1-9][0-9]{0,9}", value)
        or int(value) > 2147483647
    ):
        raise TitleRequestError(f"Confira o código da empresa {company.name} no Domínio.")
    return int(value)


def _month(value: date) -> date:
    if type(value) is not date or value.day != 1 or not 1 <= value.year <= 9998:
        raise TitleRequestError("Escolha uma competência mensal válida, entre 0001-01 e 9998-12.")
    return value


def _next_month(value: date) -> date:
    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)


def _key(value: Any) -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise TitleRequestError("Reabra a página para preparar uma nova solicitação.") from None


def _selection(
    companies: Any, actor: User, start_month: date, end_month: date, request_key: Any
) -> dict[str, Any]:
    start, end, key = _month(start_month), _month(end_month), _key(request_key)
    month_count = (end.year - start.year) * 12 + end.month - start.month + 1
    identifiers = [getattr(company, "pk", company) for company in companies]
    if not identifiers or len(set(identifiers)) != len(identifiers):
        raise TitleRequestError("Selecione as empresas, sem repetições.")
    if month_count < 1 or month_count * len(identifiers) > MAX_TITLE_REQUESTS:
        raise TitleRequestError(
            f"Escolha um intervalo em ordem e no máximo {MAX_TITLE_REQUESTS} coletas por lote."
        )
    selected = list(
        ClientCompany.objects.select_related("organization")
        .filter(pk__in=identifiers)
        .order_by("pk")
    )
    if (
        len(selected) != len(identifiers)
        or len({company.organization_id for company in selected}) != 1
    ):
        raise PermissionDenied("Selecione empresas do mesmo escritório autorizado.")
    member = (
        Membership.objects.select_related("organization")
        .filter(
            organization_id=selected[0].organization_id,
            user=actor,
            user__is_active=True,
            is_active=True,
            role__in=EDIT_ROLES,
        )
        .first()
    )
    if member is None or company_queryset_for_module(
        member, ProductModule.Code.RECONCILIATION
    ).filter(pk__in=identifiers).count() != len(identifiers):
        raise PermissionDenied(
            "Seu acesso atual não permite solicitar títulos de todas as empresas selecionadas."
        )
    require_operation_access(member.organization, ProductModule.Code.RECONCILIATION)
    for company in selected:
        _code(company)
    months = []
    month = start
    for _ in range(month_count):
        months.append(month)
        month = _next_month(month)
    identity = {
        "organization": str(selected[0].organization_id),
        "actor": str(actor.pk),
        "companies": [
            {"id": str(company.pk), "dominio_code": _code(company)} for company in selected
        ],
        "months": [month.isoformat() for month in months],
        "request_key": str(key),
    }
    return {
        "companies": selected,
        "months": months,
        "revision": canonical_hash(identity),
        "request_key": key,
    }


def _agent_state(agent: EdgeAgent | None) -> dict[str, str]:
    if agent is None or not agent.is_official or agent.status != EdgeAgent.Status.ACTIVE:
        return dict(
            code="missing",
            label="Agente não configurado",
            detail="Ative o agente oficial do escritório para buscar os títulos e baixas.",
        )
    capabilities = agent.title_capabilities
    if not isinstance(capabilities, dict) or agent.title_capabilities_observed_at is None:
        return dict(
            code="unknown",
            label="Aguardando confirmação do agente",
            detail="Confira se o agente CICA está em execução no computador do Domínio.",
        )
    if (
        capabilities.get("company_scope") is not True
        or capabilities.get("automatic_counts") is not True
    ):
        return dict(
            code="outdated",
            label="Agente precisa de atualização",
            detail="Atualize o agente CICA no computador do Domínio. O pedido fica na fila.",
            installer_url=getattr(settings, "EDGE_AGENT_INSTALLER_URL", ""),
        )
    if agent.last_seen_at is None or agent.last_seen_at < timezone.now() - timedelta(minutes=5):
        return dict(
            code="offline",
            label="Agente sem conexão recente",
            detail="Confira se o computador do Domínio está ligado e conectado à internet.",
        )
    return dict(code="online", label="Agente conectado", detail="Aguardando a próxima verificação.")


def preview_title_requests(
    *, companies: Any, actor: User, start_month: date, end_month: date, request_key: Any
) -> dict[str, Any]:
    selection = _selection(companies, actor, start_month, end_month, request_key)
    agent = EdgeAgent.objects.filter(
        organization_id=selection["companies"][0].organization_id, is_official=True, status="active"
    ).first()
    rows = [
        {"company": company, "month": month}
        for company in selection["companies"]
        for month in selection["months"]
    ]
    return {**selection, "rows": rows, "count": len(rows), "agent_state": _agent_state(agent)}


@transaction.atomic
def request_title_batch(
    *,
    companies: Any,
    actor: User,
    start_month: date,
    end_month: date,
    request_key: Any,
    expected_revision: str,
    request: Any = None,
) -> tuple[list[CompanyTitleCollection], bool]:
    selection = _selection(companies, actor, start_month, end_month, request_key)
    organization = selection["companies"][0].organization
    agent = (
        EdgeAgent.objects.select_for_update()
        .filter(organization=organization, is_official=True, status="active")
        .first()
    )
    if (
        agent is None
        or not isinstance(agent.sync_scope, dict)
        or agent.sync_scope.get("version") != ACTIVE_PORTFOLIO_VERSION
    ):
        raise TitleRequestError(
            "Ative o agente oficial da carteira para buscar os títulos e baixas."
        )
    locked = list(
        ClientCompany.objects.select_for_update()
        .filter(pk__in=[company.pk for company in selection["companies"]])
        .order_by("pk")
    )
    selection = _selection(locked, actor, start_month, end_month, request_key)
    if not isinstance(expected_revision, str) or not hmac.compare_digest(
        selection["revision"], expected_revision
    ):
        raise TitleRequestConflict(
            "Os dados da empresa mudaram. Confira novamente a prévia do lote."
        )
    existing = list(
        CompanyTitleCollection.objects.filter(
            organization=organization, batch_key=selection["request_key"]
        ).order_by("company_id", "scope__period_start")
    )
    expected = {
        (company.pk, month.isoformat())
        for company in selection["companies"]
        for month in selection["months"]
    }
    if existing:
        if (
            len(existing) != len(expected)
            or {(job.company_id, job.scope.get("period_start")) for job in existing} != expected
            or any(
                job.requested_by_id != actor.pk
                or job.evidence_reference
                != "Solicitação mensal pela interface; lote " + expected_revision
                for job in existing
            )
        ):
            raise TitleRequestConflict(
                "Esta solicitação já foi usada com outra seleção. Reabra a página."
            )
        return existing, False
    result = []
    retained_contract_hash = contract_hash()
    for company in selection["companies"]:
        for month in selection["months"]:
            identifier = uuid4()
            scope = validate_scope(
                {
                    "capture_id": str(identifier),
                    "company_code": _code(company),
                    "period_start": month.isoformat(),
                    "period_end_exclusive": _next_month(month).isoformat(),
                }
            )
            job = CompanyTitleCollection(
                pk=identifier,
                organization=organization,
                company=company,
                agent=agent,
                requested_by=actor,
                request_key=uuid5(selection["request_key"], f"{company.pk}:{month.isoformat()}"),
                batch_key=selection["request_key"],
                scope=scope,
                scope_revision=canonical_hash(scope),
                contract_hash=retained_contract_hash,
                evidence_reference="Solicitação mensal pela interface; lote " + expected_revision,
            )
            result.append(job)
    CompanyTitleCollection.objects.bulk_create(result, batch_size=200)
    record_event(
        action="hub.reconciliation.title_collection_requested",
        actor=actor,
        organization=organization,
        target=result[0],
        request=request,
        metadata={
            "batch_key": str(selection["request_key"]),
            "revision": expected_revision,
            "jobs": len(result),
            "companies": len(selection["companies"]),
            "start_month": start_month.isoformat(),
            "end_month": end_month.isoformat(),
        },
    )
    return result, True


def validate_title_job(job: CompanyTitleCollection) -> bool:
    try:
        company = ClientCompany.objects.select_related("organization").get(pk=job.company_id)
        authorize_title_company(company, job.requested_by)
        scope = validate_scope(job.scope)
        agent = EdgeAgent.objects.get(pk=job.agent_id)
        validate_portfolio_scope(agent.sync_scope, agent.organization)
        return bool(
            job.organization_id == company.organization_id == agent.organization_id
            and agent.is_official
            and agent.status == "active"
            and isinstance(agent.sync_scope, dict)
            and agent.sync_scope.get("version") == ACTIVE_PORTFOLIO_VERSION
            and scope["company_code"] == _code(company)
            and str(job.pk) == scope["capture_id"]
            and set(scope) == {"capture_id", "company_code", "period_start", "period_end_exclusive"}
            and job.scope_revision == canonical_hash(scope)
            and job.contract_hash == contract_hash()
            and job.evidence_reference.strip()
        )
    except (
        ValueError,
        PermissionDenied,
        ClientCompany.DoesNotExist,
        EdgeAgent.DoesNotExist,
        AttributeError,
        TypeError,
        KeyError,
    ):
        return False


def title_job_context(*, job: TitleJob, actor: User) -> dict[str, Any]:
    company = title_job_company(job)
    authorize_title_company(company, actor, write=False)
    if (
        job.organization_id != company.organization_id
        or job.agent.organization_id != company.organization_id
    ):
        raise PermissionDenied("Solicitação fora do escritório desta empresa.")
    scope = validate_scope(job.scope)
    if (
        job.scope_revision != canonical_hash(scope)
        or job.contract_hash != contract_hash()
        or not isinstance(job.result, dict)
    ):
        raise TitleRequestError("A solicitação precisa de revisão de integridade.")
    source = job.source_file
    source_available = bool(
        source
        and job.state == "captured"
        and source.organization_id == company.organization_id
        and source.company_id == company.pk
        and source.financial_account_id
        == (job.financial_account_id if isinstance(job, NativeTitleCollection) else None)
        and source.kind == "json"
        and source.origin == "obligation"
        and source.content_hash == job.content_hash
        and job.content_hash
    )
    status, label, detail = (
        job.state,
        "Na fila",
        "O agente buscará títulos e baixas quando estiver conectado.",
    )
    if (
        status == "queued"
        and isinstance(job, CompanyTitleCollection)
        and not validate_title_job(job)
    ):
        status, label, detail = (
            "review",
            "Solicitação precisa ser refeita",
            "O acesso, a empresa ou o agente mudou. Confira os dados e solicite novamente.",
        )
    elif status == "queued" and job.error_code:
        label, detail = (
            "Nova tentativa automática",
            "O agente tentará novamente. Confira a conexão ao Domínio.",
        )
    elif status == "queued" and getattr(job, "claimed_at", None):
        status, label, detail = (
            "delivered",
            "Solicitação entregue ao agente",
            "Aguardando o resultado da leitura do Domínio.",
        )
    elif status == "captured":
        label, detail = (
            "Fonte recebida",
            "Confira os dados recebidos. A interpretação e o vínculo à conta exigem revisão.",
        )
        if not source_available:
            status, label, detail = (
                "review",
                "Fonte precisa de revisão",
                "A fonte recebida não passou na verificação de integridade.",
            )
    elif status == "review":
        label, detail = (
            "Revisão necessária",
            "Confira os dados da empresa e a fonte do Domínio antes de solicitar novamente.",
        )
    counts = job.result.get("families", {})
    if not isinstance(counts, dict):
        counts = {}
    can_write = True
    try:
        authorize_title_company(company, actor)
    except PermissionDenied:
        can_write = False
    return {
        "job": job,
        "company": company,
        "month": date.fromisoformat(scope["period_start"]),
        "status": status,
        "label": label,
        "detail": detail,
        "can_retry": can_write and status == "review",
        "agent_state": _agent_state(job.agent),
        "counts": counts,
        "source_available": source_available,
    }


def retry_title_request(
    *, job: TitleJob, actor: User, request_key: Any, request: Any = None
) -> tuple[CompanyTitleCollection, bool]:
    company = title_job_company(job)
    authorize_title_company(company, actor)
    context = title_job_context(job=job, actor=actor)
    if not context["can_retry"]:
        raise TitleRequestError(
            "Esta coleta continua na fila ou já foi recebida; acompanhe o andamento."
        )
    month = date.fromisoformat(validate_scope(job.scope)["period_start"])
    preview = preview_title_requests(
        companies=[company],
        actor=actor,
        start_month=month,
        end_month=month,
        request_key=request_key,
    )
    jobs, created = request_title_batch(
        companies=[company],
        actor=actor,
        start_month=month,
        end_month=month,
        request_key=request_key,
        expected_revision=preview["revision"],
        request=request,
    )
    return jobs[0], created


def visible_title_jobs(
    companies: Any,
    *,
    limit: int = 100,
    month_start: date | None = None,
    month_end: date | None = None,
) -> list[TitleJob]:
    identifiers = [getattr(company, "pk", company) for company in companies]
    queries: list[Any] = [
        CompanyTitleCollection.objects.filter(company_id__in=identifiers).select_related(
            "company", "agent", "source_file"
        ),
        NativeTitleCollection.objects.filter(
            financial_account__company_id__in=identifiers
        ).select_related("financial_account__company", "agent", "source_file"),
    ]
    rows: list[TitleJob] = []
    for query in queries:
        if month_start:
            query = query.filter(scope__period_start__gte=month_start.isoformat())
        if month_end:
            query = query.filter(scope__period_start__lte=month_end.isoformat())
        rows.extend(query.order_by("-created_at", "-id")[:limit])
    return sorted(rows, key=lambda row: (row.created_at, str(row.pk)), reverse=True)[:limit]


def captures_for_account(account: FinancialAccount) -> list[TitleJob]:
    jobs: list[TitleJob] = list(
        CompanyTitleCollection.objects.filter(
            organization_id=account.organization_id, company_id=account.company_id, state="captured"
        ).order_by("-completed_at", "-created_at")[:100]
    )
    jobs.extend(
        NativeTitleCollection.objects.filter(
            organization_id=account.organization_id, financial_account=account, state="captured"
        ).order_by("-completed_at", "-created_at")[:100]
    )
    return sorted(
        jobs, key=lambda job: (job.completed_at or job.created_at, str(job.pk)), reverse=True
    )[:100]
