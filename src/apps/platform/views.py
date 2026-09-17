from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ControlPlaneBinding, ProductModule, RemoteSupportGrant
from apps.hub.module_catalog import OFFERED_MODULE_CHOICES, OFFERED_MODULE_CODES
from apps.intelligence.models import AssistantSettings, ClaudeFallbackApproval, EgressAudit
from apps.organizations.models import Membership, Organization
from apps.platform.forms import (
    AssistantRetentionForm,
    ClaudeFallbackForm,
    InvitationForm,
    TenantContractForm,
    TenantServiceRateForm,
    TokenOfferForm,
)
from apps.platform.models import (
    DominioSupportTicket,
    Invitation,
    Invoice,
    PlatformAccess,
    PlatformConfiguration,
    SupportSession,
    TenantContract,
    TenantLifecycle,
    TokenPriceBook,
    UsageEvent,
)
from apps.platform.notifications import TransactionalEmailError, send_invitation_email
from apps.platform.payments import ManualBillingError, set_manual_invoice_status
from apps.platform.policies import platform_required
from apps.platform.services import (
    LifecycleTransitionError,
    allowed_lifecycle_targets,
    has_platform_role,
    platform_role,
    support_access_mode,
    transition_lifecycle,
)


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
    # Somebody who already belongs to the office is not visiting it. Impersonating an
    # office you are a member of hides your own role, drops your office switcher and
    # labels you a visitor in your own workspace -- and it narrows you to the session's
    # company list even though your membership grants more.
    if Membership.objects.filter(
        organization=session.organization, user=session.support_user, is_active=True
    ).exists():
        return None
    return session


@platform_required(
    PlatformAccess.Role.DEVELOPER, PlatformAccess.Role.SUPPORT, PlatformAccess.Role.COMMERCIAL
)
def dashboard(request: HttpRequest) -> HttpResponse:
    ctx = context(request)
    role = ctx["platform_role"]
    can_review_dominio_tickets = role in {
        PlatformAccess.Role.DEVELOPER,
        PlatformAccess.Role.ADMIN,
    }
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
            "tenants": Organization.objects.filter(is_active=True)
            .select_related("lifecycle")
            .order_by("-created_at", "-id")[:8],
            "dominio_tickets": (
                DominioSupportTicket.objects.filter(status=DominioSupportTicket.Status.OPEN)
                .select_related("organization")
                .order_by("created_at")[:8]
                if can_review_dominio_tickets
                else []
            ),
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


def _save_modules(request: HttpRequest, user: User, organization: Organization) -> None:
    if ControlPlaneBinding.objects.filter(organization=organization).exists():
        messages.error(
            request,
            "Os sistemas desta instalação são definidos pelo controle central da Mewstack.",
        )
        return
    selected = set(request.POST.getlist("modules"))
    allowed = set(OFFERED_MODULE_CODES)
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


def _issue_invitation(
    request: HttpRequest, user: User, organization: Organization, form: InvitationForm
) -> None:
    with transaction.atomic():
        raw_token, digest = Invitation.issue_token()
        Invitation.objects.filter(
            organization=organization,
            email=form.cleaned_data["email"],
            status=Invitation.Status.PENDING,
        ).update(status=Invitation.Status.REVOKED)
        invitation = Invitation.objects.create(
            organization=organization,
            email=form.cleaned_data["email"],
            full_name=form.cleaned_data["full_name"],
            role=form.cleaned_data["role"],
            token_digest=digest,
            expires_at=timezone.now() + timedelta(days=7),
            created_by=user,
        )
        send_invitation_email(
            invitation=invitation,
            activation_url=request.build_absolute_uri(f"/ativar/{raw_token}/"),
        )
    record_event(
        action="platform.invitation.issued",
        actor=user,
        organization=organization,
        target=invitation,
        request=request,
        metadata={"delivery": "email"},
    )
    messages.success(request, f"Convite enviado para {invitation.email}.")


def _save_contract(
    request: HttpRequest, user: User, organization: Organization, form: TenantContractForm
) -> None:
    contract = form.save(commit=False)
    contract.organization = organization
    contract.save()
    record_event(
        action="platform.contract.saved",
        actor=user,
        organization=organization,
        target=contract,
        request=request,
        metadata={"status": contract.status, "plan": contract.plan.code if contract.plan else ""},
    )
    messages.success(request, "Contrato salvo.")


def _move_lifecycle(request: HttpRequest, user: User, lifecycle: TenantLifecycle) -> None:
    previous = lifecycle.state
    target = request.POST.get("state", "")
    if (
        target
        in {
            TenantLifecycle.State.SUSPENDED,
            TenantLifecycle.State.ARCHIVED,
        }
        and request.POST.get("confirm_lifecycle") != "on"
    ):
        messages.error(
            request,
            "Confirme o bloqueio de acesso antes de suspender ou arquivar o escritório.",
        )
        return
    try:
        with transaction.atomic():
            contract: TenantContract | None = None
            if target == TenantLifecycle.State.ACTIVE:
                contract = (
                    TenantContract.objects.select_for_update()
                    .filter(organization=lifecycle.organization)
                    .order_by("-created_at", "-id")
                    .first()
                )
                if contract is None or contract.status in {
                    TenantContract.Status.DRAFT,
                    TenantContract.Status.ARCHIVED,
                }:
                    messages.error(
                        request,
                        "Defina um contrato vigente antes de liberar o acesso operacional.",
                    )
                    return
            if contract is not None and contract.status in {
                TenantContract.Status.GRACE,
                TenantContract.Status.SUSPENDED,
            }:
                if not has_platform_role(
                    user,
                    PlatformAccess.Role.COMMERCIAL,
                    PlatformAccess.Role.DEVELOPER,
                    PlatformAccess.Role.ADMIN,
                ):
                    messages.error(
                        request,
                        "A reativação comercial exige perfil Comercial, Desenvolvedor "
                        "ou Administrador.",
                    )
                    return
                contract.status = TenantContract.Status.ACTIVE
                contract.grace_ends_on = None
                contract.save(update_fields=["status", "grace_ends_on", "updated_at"])
            transition_lifecycle(
                lifecycle=lifecycle,
                target=target,
                reason=request.POST.get("reason", ""),
                actor=user,
            )
    except LifecycleTransitionError as exc:
        messages.error(request, str(exc))
        return
    record_event(
        action="platform.tenant.lifecycle_changed",
        actor=user,
        organization=lifecycle.organization,
        target=lifecycle,
        request=request,
        metadata={"from": previous, "to": lifecycle.state, "reason": lifecycle.reason},
    )
    messages.success(request, f"Escritório em {lifecycle.get_state_display().lower()}.")


# Every POST on this page names its action, and the roles sit next to the branch instead
# of in a chain of ifs, so adding one cannot quietly widen who may run it.
_TENANT_ACTION_ROLES: dict[str, tuple[str, ...]] = {
    "modules": (
        PlatformAccess.Role.SUPPORT,
        PlatformAccess.Role.DEVELOPER,
        PlatformAccess.Role.ADMIN,
    ),
    # An activation link is a bearer credential for the tenant it opens.
    "invite": (PlatformAccess.Role.SUPPORT, PlatformAccess.Role.DEVELOPER),
    # Money is commercial's call; support reads contracts but does not write them.
    "contract": (PlatformAccess.Role.COMMERCIAL, PlatformAccess.Role.ADMIN),
    "service-rate": (PlatformAccess.Role.COMMERCIAL, PlatformAccess.Role.ADMIN),
    "token-offer": (PlatformAccess.Role.COMMERCIAL, PlatformAccess.Role.ADMIN),
    "invoice-status": (PlatformAccess.Role.COMMERCIAL, PlatformAccess.Role.ADMIN),
    "ai-fallback": (PlatformAccess.Role.DEVELOPER, PlatformAccess.Role.ADMIN),
    "ai-retention": (PlatformAccess.Role.DEVELOPER, PlatformAccess.Role.ADMIN),
    "lifecycle": (
        PlatformAccess.Role.SUPPORT,
        PlatformAccess.Role.DEVELOPER,
        PlatformAccess.Role.COMMERCIAL,
        PlatformAccess.Role.ADMIN,
    ),
}


@platform_required(
    PlatformAccess.Role.COMMERCIAL,
    PlatformAccess.Role.SUPPORT,
    PlatformAccess.Role.DEVELOPER,
)
@require_http_methods(["GET", "POST"])
def tenant_detail(request: HttpRequest, organization_id: str) -> HttpResponse:
    user = _platform_user(request)
    organization = get_object_or_404(Organization, id=organization_id)
    lifecycle, _ = TenantLifecycle.objects.get_or_create(organization=organization)
    contract = organization.contracts.select_related("plan").order_by("-created_at").first()
    action = request.POST.get("action", "") if request.method == "POST" else ""
    invite_form = InvitationForm(request.POST if action == "invite" else None, prefix="invite")
    contract_form = TenantContractForm(
        request.POST if action == "contract" else None, instance=contract
    )
    rate_form = TenantServiceRateForm(
        request.POST if action == "service-rate" else None, contract=contract
    )
    token_draft = (
        TokenPriceBook.objects.filter(contract=contract, status=TokenPriceBook.Status.DRAFT)
        .prefetch_related("module_rates__action_weights")
        .order_by("-version")
        .first()
        if contract
        else None
    )
    active_token_book = (
        TokenPriceBook.objects.filter(contract=contract, status=TokenPriceBook.Status.ACTIVE)
        .prefetch_related("module_rates__action_weights")
        .first()
        if contract
        else None
    )
    token_offer_form = TokenOfferForm(
        request.POST if action == "token-offer" else None,
        book=token_draft,
    )
    assistant_settings = AssistantSettings.objects.filter(organization=organization).first()
    fallback_approval = ClaudeFallbackApproval.objects.filter(organization=organization).first()
    fallback_form = ClaudeFallbackForm(
        request.POST if action == "ai-fallback" else None,
        settings=assistant_settings,
        approval=fallback_approval,
    )
    if action == "ai-fallback-credential":
        raise PermissionDenied("A chave Claude pertence ao .env da Mewstack.")
    retention_form = AssistantRetentionForm(
        request.POST if action == "ai-retention" else None,
        settings=assistant_settings,
    )

    if action:
        roles = _TENANT_ACTION_ROLES.get(action)
        if roles is None or not has_platform_role(request.user, *roles):
            raise PermissionDenied
        redirect_back = redirect("platform:tenant-detail", organization_id=organization.id)
        if action == "modules":
            _save_modules(request, user, organization)
            return redirect_back
        if action == "lifecycle":
            _move_lifecycle(request, user, lifecycle)
            return redirect_back
        if action == "invite" and invite_form.is_valid():
            try:
                _issue_invitation(request, user, organization, invite_form)
            except TransactionalEmailError:
                invite_form.add_error(
                    None,
                    "Não foi possível enviar o convite agora. Tente novamente em alguns minutos.",
                )
            else:
                return redirect_back
        if action == "contract" and contract_form.is_valid():
            _save_contract(request, user, organization, contract_form)
            return redirect_back
        if action == "service-rate" and rate_form.is_valid() and contract is not None:
            rate_form.save()
            messages.success(request, "Regra de consumo salva.")
            return redirect_back
        if action == "token-offer" and token_offer_form.is_valid() and contract is not None:
            book = token_offer_form.save(contract=contract)
            record_event(
                action="platform.tenant.token_offer_saved",
                actor=user,
                organization=organization,
                target=book,
                request=request,
                metadata={"version": book.version, "status": book.status},
            )
            messages.success(
                request,
                "Proposta de tokens salva. O dono ou administrador do escritório "
                "ainda precisa aceitar os termos.",
            )
            return redirect_back
        if action == "invoice-status":
            invoice = get_object_or_404(
                Invoice,
                pk=request.POST.get("invoice_id"),
                organization=organization,
            )
            try:
                invoice = set_manual_invoice_status(
                    invoice=invoice,
                    status=request.POST.get("status", ""),
                )
            except ManualBillingError as error:
                messages.error(request, str(error))
                return redirect_back
            record_event(
                action="platform.tenant.invoice_status_updated",
                actor=user,
                organization=organization,
                target=invoice,
                request=request,
                metadata={"status": invoice.status, "collection_mode": "external_manual"},
            )
            messages.success(request, "Registro de cobrança atualizado.")
            return redirect_back
        if action == "ai-fallback" and fallback_form.is_valid():
            if ControlPlaneBinding.objects.filter(organization=organization).exists():
                messages.error(
                    request,
                    "A política de fallback deste escritório é definida pelo controle central "
                    "da Mewstack.",
                )
                return redirect_back
            fallback_enabled = bool(fallback_form.cleaned_data["enabled"])
            with transaction.atomic():
                settings, _ = AssistantSettings.objects.select_for_update().get_or_create(
                    organization=organization
                )
                settings.claude_fallback_enabled = fallback_enabled
                settings.claude_full_data_allowed = (
                    bool(fallback_form.cleaned_data["allow_full_data"])
                    if fallback_enabled
                    else False
                )
                settings.claude_allowed_roles = (
                    list(fallback_form.cleaned_data["allowed_roles"]) if fallback_enabled else []
                )
                platform_configuration = PlatformConfiguration.objects.filter(key="default").first()
                settings.claude_model = (
                    platform_configuration.cloud_fallback_model
                    if fallback_enabled and platform_configuration
                    else ""
                )
                settings.claude_max_request_cents = (
                    fallback_form.cents(fallback_form.cleaned_data["max_request_brl"])
                    if fallback_enabled
                    else 0
                )
                settings.claude_api_key = ""
                settings.save()
                approval, _ = ClaudeFallbackApproval.objects.select_for_update().get_or_create(
                    organization=organization
                )
                approval.status = (
                    ClaudeFallbackApproval.Status.APPROVED
                    if fallback_enabled
                    else ClaudeFallbackApproval.Status.REVOKED
                )
                approval.daily_limit_cents = (
                    fallback_form.cents(fallback_form.cleaned_data["daily_limit_brl"])
                    if fallback_enabled
                    else 0
                )
                approval.monthly_limit_cents = (
                    fallback_form.cents(fallback_form.cleaned_data["monthly_limit_brl"])
                    if fallback_enabled
                    else 0
                )
                approval.valid_until = (
                    fallback_form.cleaned_data["valid_until"] if fallback_enabled else None
                )
                approval.approved_by = request.user if fallback_enabled else None
                approval.approved_at = timezone.now() if fallback_enabled else None
                approval.save()
            record_event(
                action="platform.tenant.ai_fallback_updated",
                actor=user,
                organization=organization,
                target=settings,
                request=request,
                metadata={
                    "enabled": fallback_enabled,
                    "model": settings.claude_model,
                    "max_request_cents": settings.claude_max_request_cents,
                    "daily_limit_cents": approval.daily_limit_cents,
                    "monthly_limit_cents": approval.monthly_limit_cents,
                },
            )
            messages.success(
                request,
                "Fallback externo habilitado com aprovação limitada."
                if fallback_enabled
                else "Fallback externo desabilitado.",
            )
            return redirect_back
        if action == "ai-retention" and retention_form.is_valid():
            with transaction.atomic():
                settings, _ = AssistantSettings.objects.select_for_update().get_or_create(
                    organization=organization
                )
                previous_days = settings.retention_days
                settings.retention_days = retention_form.cleaned_data["retention_days"]
                settings.save(update_fields=["retention_days", "updated_at"])
            record_event(
                action="platform.tenant.ai_retention_updated",
                actor=user,
                organization=organization,
                target=settings,
                request=request,
                metadata={
                    "previous_days": previous_days,
                    "retention_days": settings.retention_days,
                },
            )
            messages.success(request, "Retenção das conversas do Copiloto atualizada.")
            return redirect_back

    recent_invoices = list(
        Invoice.objects.filter(organization=organization).order_by("-period_start")[:12]
    )
    for invoice in recent_invoices:
        invoice.total_brl = Decimal(invoice.total_amount_cents) / 100  # type: ignore[attr-defined]
    can_inspect_egress = has_platform_role(
        request.user,
        PlatformAccess.Role.SUPPORT,
        PlatformAccess.Role.DEVELOPER,
        PlatformAccess.Role.ADMIN,
    )
    egress_attention = (
        list(
            EgressAudit.objects.filter(organization=organization, provider="anthropic")
            .filter(
                Q(call_state=EgressAudit.CallState.UNKNOWN)
                | Q(
                    call_state=EgressAudit.CallState.RESERVED,
                    created_at__lt=timezone.now() - timedelta(minutes=10),
                )
                | Q(
                    usage_event__status=UsageEvent.Status.RESERVED,
                    created_at__lt=timezone.now() - timedelta(minutes=10),
                )
            )
            .select_related("usage_event", "user_message__conversation")
            .order_by("-created_at", "-id")[:20]
        )
        if can_inspect_egress
        else []
    )
    ctx = context(request)
    ctx.update(
        {
            "page_title": "",
            "tenant": organization,
            "invite_form": invite_form,
            "contract_form": contract_form,
            "rate_form": rate_form,
            "token_offer_form": token_offer_form,
            "token_draft": token_draft,
            "active_token_book": active_token_book,
            "contract": contract,
            "recent_invoices": recent_invoices,
            "can_inspect_egress": can_inspect_egress,
            "egress_attention": egress_attention,
            "invoice_status_choices": Invoice.Status.choices,
            "lifecycle": lifecycle,
            "lifecycle_targets": [
                (state, TenantLifecycle.State(state).label)
                for state in allowed_lifecycle_targets(lifecycle)
            ],
            "can_edit_contract": has_platform_role(
                request.user, PlatformAccess.Role.COMMERCIAL, PlatformAccess.Role.ADMIN
            ),
            "can_move_lifecycle": has_platform_role(
                request.user,
                PlatformAccess.Role.SUPPORT,
                PlatformAccess.Role.DEVELOPER,
                PlatformAccess.Role.COMMERCIAL,
                PlatformAccess.Role.ADMIN,
            ),
            "can_start_support": has_platform_role(
                request.user,
                PlatformAccess.Role.SUPPORT,
                PlatformAccess.Role.DEVELOPER,
            ),
            "modules": ProductModule.objects.filter(organization=organization).order_by("code"),
            "module_choices": OFFERED_MODULE_CHOICES,
            "enabled_module_codes": set(
                ProductModule.objects.filter(organization=organization, enabled=True).values_list(
                    "code", flat=True
                )
            ),
            "managed_by_crmew": ControlPlaneBinding.objects.filter(
                organization=organization
            ).exists(),
            "fallback_form": fallback_form,
            "retention_form": retention_form,
            "fallback_settings": assistant_settings,
            "fallback_approval": fallback_approval,
            "can_edit_fallback": has_platform_role(
                request.user, PlatformAccess.Role.DEVELOPER, PlatformAccess.Role.ADMIN
            ),
            "can_manage_billing": has_platform_role(
                request.user, PlatformAccess.Role.COMMERCIAL, PlatformAccess.Role.ADMIN
            ),
        }
    )
    return render(request, "platform/tenant_detail.html", ctx)


@platform_required(PlatformAccess.Role.SUPPORT, PlatformAccess.Role.DEVELOPER)
@require_http_methods(["POST"])
def start_support(request: HttpRequest, organization_id: str) -> HttpResponse:
    user = _platform_user(request)
    organization = get_object_or_404(Organization, id=organization_id, is_active=True)
    if Membership.objects.filter(organization=organization, user=user, is_active=True).exists():
        messages.error(
            request,
            "Você já faz parte deste escritório. Abra-o pelo seletor, sem sessão de suporte.",
        )
        return redirect("platform:tenant-detail", organization_id=organization.id)
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
                "O controle central da Mewstack não autorizou uma sessão de suporte ativa "
                "para este escritório.",
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


@platform_required(PlatformAccess.Role.SUPPORT, PlatformAccess.Role.DEVELOPER)
@require_http_methods(["POST"])
def end_support(request: HttpRequest) -> HttpResponse:
    # start_support admits DEVELOPER too; without the same role here a developer could
    # open a tenant session and not close it until it expired on its own.
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
