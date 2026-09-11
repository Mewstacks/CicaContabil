from __future__ import annotations

from datetime import timedelta

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ControlPlaneBinding, ProductModule, RemoteSupportGrant
from apps.organizations.models import Organization
from apps.platform.forms import InvitationForm
from apps.platform.models import (
    Invitation,
    PlatformAccess,
    SupportSession,
    TenantLifecycle,
)
from apps.platform.policies import platform_required
from apps.platform.services import has_platform_role, platform_role, support_access_mode


def _platform_user(request: HttpRequest) -> User:
    if not request.user.is_authenticated:
        raise PermissionDenied
    return request.user


def context(request: HttpRequest) -> dict[str, object]:
    return {
        "platform_role": platform_role(request.user),
        "support_session": current_support(request),
    }


def current_support(request: HttpRequest) -> SupportSession | None:
    session_id = request.session.get("hub_support_session_id")
    if not session_id:
        return None
    session = SupportSession.objects.filter(
        id=session_id,
        support_user=_platform_user(request),
    ).first()
    if not session or not session.usable():
        request.session.pop("hub_support_session_id", None)
        return None
    return session


@platform_required(
    PlatformAccess.Role.DEVELOPER, PlatformAccess.Role.SUPPORT, PlatformAccess.Role.COMMERCIAL
)
def dashboard(request: HttpRequest) -> HttpResponse:
    ctx = context(request)
    ctx.update(
        {
            "page_title": "Console da plataforma",
            "tenant_count": Organization.objects.filter(is_active=True).count(),
            "activation_count": TenantLifecycle.objects.filter(
                state=TenantLifecycle.State.ACTIVATION_PENDING
            ).count(),
            "suspended_count": TenantLifecycle.objects.filter(
                state=TenantLifecycle.State.SUSPENDED
            ).count(),
            "tenants": Organization.objects.filter(is_active=True).select_related("lifecycle")[:8],
        }
    )
    return render(request, "platform/dashboard.html", ctx)


@platform_required(
    PlatformAccess.Role.COMMERCIAL,
    PlatformAccess.Role.SUPPORT,
    PlatformAccess.Role.DEVELOPER,
)
@require_http_methods(["GET", "POST"])
def tenants(request: HttpRequest) -> HttpResponse:
    user = _platform_user(request)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        slug = request.POST.get("slug", "").strip()
        if not name or not slug:
            messages.error(request, "Informe o nome e o identificador do escritório.")
        elif Organization.objects.filter(slug=slug).exists():
            messages.error(request, "Esse identificador já está em uso.")
        else:
            with transaction.atomic():
                organization = Organization.objects.create(name=name, slug=slug)
                TenantLifecycle.objects.create(
                    organization=organization,
                    state=TenantLifecycle.State.ACTIVATION_PENDING,
                    changed_by=user,
                )
                record_event(
                    action="platform.tenant.provisioned",
                    actor=user,
                    organization=organization,
                    request=request,
                )
            messages.success(
                request, "Escritório provisionado. Crie o contrato e a ativação interna."
            )
            return redirect("platform:tenant-detail", organization_id=organization.id)
    ctx = context(request)
    ctx.update(
        {"page_title": "Escritórios", "tenants": Organization.objects.select_related("lifecycle")}
    )
    return render(request, "platform/tenants.html", ctx)


@platform_required(
    PlatformAccess.Role.COMMERCIAL,
    PlatformAccess.Role.SUPPORT,
    PlatformAccess.Role.DEVELOPER,
)
@require_http_methods(["GET", "POST"])
def tenant_detail(request: HttpRequest, organization_id: str) -> HttpResponse:
    user = _platform_user(request)
    organization = get_object_or_404(Organization, id=organization_id)
    invite_form = InvitationForm(request.POST or None, prefix="invite")
    activation_link = None
    if request.method == "POST" and request.POST.get("action") == "modules":
        if ControlPlaneBinding.objects.filter(organization=organization).exists():
            messages.error(request, "Os sistemas desta instalação são definidos pelo CRMew.")
        else:
            selected = set(request.POST.getlist("modules"))
            allowed = set(ProductModule.Code.values)
            for code in allowed:
                ProductModule.objects.update_or_create(
                    organization=organization,
                    code=code,
                    defaults={
                        "enabled": code in selected,
                        "enabled_at": timezone.now() if code in selected else None,
                    },
                )
            record_event(
                action="platform.tenant.modules_updated",
                actor=user,
                organization=organization,
                request=request,
                metadata={"module_count": len(selected & allowed)},
            )
            messages.success(request, "Alterações salvas.")
        return redirect("platform:tenant-detail", organization_id=organization.id)
    if (
        request.method == "POST"
        and request.POST.get("action") == "invite"
        and invite_form.is_valid()
    ):
        raw_token, digest = Invitation.issue_token()
        Invitation.objects.filter(
            organization=organization,
            email=invite_form.cleaned_data["email"],
            status=Invitation.Status.PENDING,
        ).update(status=Invitation.Status.REVOKED)
        invitation = Invitation.objects.create(
            organization=organization,
            email=invite_form.cleaned_data["email"],
            full_name=invite_form.cleaned_data["full_name"],
            role=invite_form.cleaned_data["role"],
            token_digest=digest,
            expires_at=timezone.now() + timedelta(days=7),
            created_by=user,
        )
        activation_link = request.build_absolute_uri(f"/ativar/{raw_token}/")
        record_event(
            action="platform.invitation.issued",
            actor=user,
            organization=organization,
            target=invitation,
            request=request,
        )
        messages.success(request, "Ativação criada. Copie o link agora; ele não é exibido de novo.")
    ctx = context(request)
    ctx.update(
        {
            "page_title": "",
            "tenant": organization,
            "invite_form": invite_form,
            "activation_link": activation_link,
            "can_start_support": has_platform_role(
                request.user,
                PlatformAccess.Role.SUPPORT,
                PlatformAccess.Role.DEVELOPER,
            ),
            "modules": ProductModule.objects.filter(organization=organization).order_by("code"),
            "module_choices": ProductModule.Code.choices,
            "enabled_module_codes": set(
                ProductModule.objects.filter(organization=organization, enabled=True).values_list(
                    "code", flat=True
                )
            ),
            "managed_by_crmew": ControlPlaneBinding.objects.filter(
                organization=organization
            ).exists(),
        }
    )
    return render(request, "platform/tenant_detail.html", ctx)


@platform_required(PlatformAccess.Role.SUPPORT, PlatformAccess.Role.DEVELOPER)
@require_http_methods(["POST"])
def start_support(request: HttpRequest, organization_id: str) -> HttpResponse:
    user = _platform_user(request)
    organization = get_object_or_404(Organization, id=organization_id, is_active=True)
    justification = request.POST.get("justification", "").strip()
    if len(justification) < 12:
        messages.error(request, "Explique o motivo do acesso em pelo menos 12 caracteres.")
        return redirect("platform:tenant-detail", organization_id=organization.id)
    control_grant = None
    if ControlPlaneBinding.objects.filter(organization=organization).exists():
        control_grant = (
            RemoteSupportGrant.objects.filter(
                organization=organization,
                subject=user.email.casefold(),
                expires_at__gt=timezone.now(),
            )
            .order_by("expires_at")
            .first()
        )
        if control_grant is None:
            messages.error(
                request,
                "O CRMew nÃ£o autorizou uma sessÃ£o de suporte ativa para este escritÃ³rio.",
            )
            return redirect("platform:tenant-detail", organization_id=organization.id)
    active = SupportSession.objects.filter(
        support_user=user,
        status=SupportSession.Status.OPEN,
        expires_at__gt=timezone.now(),
    )
    active.update(status=SupportSession.Status.CLOSED, closed_at=timezone.now())
    expires_at = (
        control_grant.expires_at if control_grant else timezone.now() + timedelta(minutes=30)
    )
    support = SupportSession.objects.create(
        organization=organization,
        support_user=user,
        justification=control_grant.justification if control_grant else justification,
        company_ids=control_grant.company_ids if control_grant else [],
        control_grant_hash=control_grant.source_hash if control_grant else "",
        access_mode=support_access_mode(user),
        expires_at=expires_at,
    )
    request.session["hub_support_session_id"] = str(support.id)
    request.session["hub_organization_id"] = str(organization.id)
    request.session.pop("hub_company_id", None)
    record_event(
        action="platform.support.opened",
        actor=user,
        organization=organization,
        target=support,
        request=request,
        metadata={
            "duration_minutes": max(0, int((expires_at - timezone.now()).total_seconds() // 60)),
            "access_mode": support.access_mode,
        },
    )
    return redirect("hub:dashboard")


@platform_required(PlatformAccess.Role.SUPPORT)
@require_http_methods(["POST"])
def end_support(request: HttpRequest) -> HttpResponse:
    user = _platform_user(request)
    support = current_support(request)
    if support:
        support.status = SupportSession.Status.CLOSED
        support.closed_at = timezone.now()
        support.save(update_fields=["status", "closed_at", "updated_at"])
        record_event(
            action="platform.support.closed",
            actor=user,
            organization=support.organization,
            target=support,
            request=request,
        )
    request.session.pop("hub_support_session_id", None)
    return redirect("platform:dashboard")
