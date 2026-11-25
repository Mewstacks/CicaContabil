"""Tela do escritorio para configurar o proprio conector MCP.

Dono ou administrador liga a chave, pareia o computador onde fica o Dominio (codigo de uso unico),
ve quem esta conectado e revoga. Nada aqui mostra segredo: o codigo de pareamento aparece uma vez,
guardado na sessao so ate a proxima carga.
"""

from __future__ import annotations

from typing import Any, cast

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.views import office_required, refuse, workspace_context
from apps.intelligence.agents import issue_enrollment, revoke_agent
from apps.intelligence.models import EdgeAgent
from apps.mcpgateway import conf, jobs
from apps.mcpgateway.authorize import revoke_tokens
from apps.mcpgateway.models import McpConsent, McpJob, McpSetting
from apps.organizations.models import Membership, Organization

SESSION_CODE = "mcp_enrollment_code"
RECENT_JOBS = 8
INSTALLER = "instalar-servico.ps1"


def _manager(context: dict[str, object]) -> Membership | None:
    membership = context["membership"]
    if (
        context["support_session"] is None
        and isinstance(membership, Membership)
        and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
    ):
        return membership
    return None


def _hub_origin(request: HttpRequest) -> str:
    return conf.origin() if conf.enabled() else request.build_absolute_uri("/").rstrip("/")


def _agent_rows(organization: Organization) -> list[dict[str, Any]]:
    since = timezone.now() - jobs.AGENT_ONLINE_WINDOW
    return [
        {
            "agent": agent,
            "online": agent.last_seen_at is not None and agent.last_seen_at >= since,
        }
        for agent in jobs.active_agents(organization).order_by("-enrolled_at")
    ]


@office_required
@require_http_methods(["GET", "POST"])
def connector(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    membership = _manager(context)
    if membership is None:
        return refuse(request, "Somente donos e administradores configuram o conector MCP.")
    if request.method == "POST":
        return _act(request, office, membership)
    setting = McpSetting.objects.filter(organization=office).first()
    rows = _agent_rows(office)
    code = request.session.pop(SESSION_CODE, "")
    context.update(
        {
            "page_title": "Conector MCP",
            "gateway_available": conf.enabled(),
            "mcp_enabled": bool(setting and setting.enabled),
            "agents": rows,
            "agent_online": any(row["online"] for row in rows),
            "enrollment_code": code,
            "install_command": (
                f".\\{INSTALLER} -Hub {_hub_origin(request)} -Codigo {code}" if code else ""
            ),
            "connector_url": conf.resource_url() if conf.enabled() else "",
            "consents": McpConsent.objects.filter(organization=office)
            .select_related("user", "application")
            .order_by("-created_at"),
            "recent_jobs": McpJob.objects.filter(organization=office).order_by("-created_at")[
                :RECENT_JOBS
            ],
        }
    )
    return render(request, "mcpgateway/connector.html", context)


def _act(request: HttpRequest, office: Organization, membership: Membership) -> HttpResponse:
    user = cast(User, request.user)
    action = request.POST.get("action", "")
    if action in {"ligar", "desligar"}:
        McpSetting.objects.update_or_create(
            organization=office,
            defaults={"enabled": action == "ligar", "updated_by": user},
        )
        record_event(
            action="mcpgateway.setting_changed",
            actor=user,
            organization=office,
            request=request,
            metadata={"enabled": action == "ligar"},
        )
        messages.success(
            request, "Conector ligado." if action == "ligar" else "Conector desligado."
        )
    elif action == "parear":
        credentials = issue_enrollment(organization=office, actor=user, request=request)
        request.session[SESSION_CODE] = credentials.code
        messages.success(request, "Código criado. Vale por 30 minutos.")
    elif action == "revogar-agente":
        agent_id = _uuid_or_none(request.POST.get("id"))
        agent = (
            EdgeAgent.objects.filter(
                organization=office, id=agent_id, status=EdgeAgent.Status.ACTIVE
            ).first()
            if agent_id
            else None
        )
        if agent is not None:
            revoke_agent(agent=agent, actor=user, request=request)
            messages.success(request, "Computador desconectado.")
    elif action == "revogar-cliente":
        consent_id = _int_or_none(request.POST.get("id"))
        consent = (
            McpConsent.objects.select_related("application", "user")
            .filter(organization=office, pk=consent_id)
            .first()
            if consent_id is not None
            else None
        )
        if consent is not None:
            revoke_tokens(user=consent.user, application=consent.application)
            record_event(
                action="mcpgateway.tokens_revoked",
                actor=user,
                organization=office,
                request=request,
                metadata={"reason": "office_admin"},
            )
            consent.delete()
            messages.success(request, "Acesso revogado.")
    return redirect("mcp-connector")


def _uuid_or_none(value: str | None) -> str | None:
    import uuid

    try:
        return str(uuid.UUID(str(value)))
    except ValueError:
        return None


def _int_or_none(value: str | None) -> int | None:
    try:
        return int(str(value))
    except ValueError:
        return None
