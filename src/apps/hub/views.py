from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from typing import Concatenate, cast
from urllib.parse import quote, urlencode

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import IdentifierAuthenticationForm
from apps.accounts.models import User
from apps.audit.services import record_event
from apps.common.network import client_ip
from apps.common.ratelimit import rate_limited
from apps.common.redirects import safe_next
from apps.hub.controlplane import authorization_is_fresh, company_queryset_for_membership
from apps.hub.forms import (
    ActivationForm,
    CertificateUploadForm,
    CompanyForm,
    ConnectorConfigForm,
    DtePreparationForm,
)
from apps.hub.models import (
    Certificate,
    ClientCompany,
    Connector,
    ControlPlaneBinding,
    DteMessage,
    DteRun,
    DteRunItem,
    IntegrationArtifact,
    NfseDocument,
    OfficeProfile,
    ProductModule,
    ReviewCase,
    UsageAllowance,
)
from apps.hub.module_catalog import MODULES, ModuleDefinition, definition
from apps.hub.services import (
    DteRunTransitionError,
    approve_dte_run,
    cancel_dte_run,
    prepare_dte_run,
    store_certificate,
)
from apps.intelligence.agents import issue_enrollment
from apps.intelligence.models import EdgeAgent, IntelligenceConnector
from apps.organizations.models import Membership, Organization
from apps.platform.forms import LeadForm
from apps.platform.models import Invitation, PlatformAccess, TenantLifecycle
from apps.platform.services import has_platform_role
from apps.platform.views import current_support


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "hub/home.html")


@require_http_methods(["GET", "POST"])
def proposal(request: HttpRequest) -> HttpResponse:
    form = LeadForm(request.POST or None)
    if request.method == "POST" and rate_limited(
        f"lead:{client_ip(request)}",
        limit=settings.LEAD_RATE_LIMIT_PER_HOUR,
        window_seconds=3600,
    ):
        # Anonymous, unauthenticated, and it writes personal data to the database.
        messages.error(request, "Muitos pedidos deste endereço. Tente mais tarde.")
        return render(request, "hub/proposal.html", {"form": form}, status=429)
    if request.method == "POST" and form.is_valid():
        lead = form.save()
        record_event(action="hub.proposal.requested", target=lead, request=request)
        messages.success(
            request, "Pedido recebido. Acompanhe com nossa equipe pelo canal combinado."
        )
        return redirect("hub:proposal")
    return render(request, "hub/proposal.html", {"form": form})


@require_http_methods(["GET", "POST"])
def activate_invitation(request: HttpRequest, token: str) -> HttpResponse:
    invitation = get_object_or_404(
        Invitation, token_digest=hashlib.sha256(token.encode()).hexdigest()
    )
    if not invitation.usable():
        return render(request, "hub/activation_invalid.html", status=410)

    existing = User.objects.filter(email=invitation.email).first()
    if existing is not None:
        return _accept_as_existing_user(request, invitation, existing, token)

    form = ActivationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = User.objects.create_user(
                email=invitation.email,
                password=form.cleaned_data["password"],
            )
            user.full_name = invitation.full_name
            user.save(update_fields=["full_name"])
            _accept_invitation(request, invitation, user, account_existed=False)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session["hub_organization_id"] = str(invitation.organization_id)
        return redirect("hub:dashboard")
    return render(request, "hub/activate.html", {"form": form})


def _accept_as_existing_user(
    request: HttpRequest, invitation: Invitation, invited: User, token: str
) -> HttpResponse:
    """An invitation never sets the password of an account that already exists.

    Doing so would let anyone who can issue an invitation take over any account by
    typing its e-mail address. The invited person signs in first and then accepts.
    """

    if not request.user.is_authenticated or request.user.pk != invited.pk:
        login_url = f"{reverse('hub:login')}?next={quote(request.path)}"
        return render(
            request,
            "hub/activate_signin.html",
            {"invited_email": invitation.email, "login_url": login_url},
            status=403 if request.user.is_authenticated else 200,
        )
    if request.method == "POST":
        with transaction.atomic():
            _accept_invitation(request, invitation, invited, account_existed=True)
        request.session["hub_organization_id"] = str(invitation.organization_id)
        return redirect("hub:dashboard")
    return render(
        request,
        "hub/activate_accept.html",
        {"invitation": invitation, "token": token},
    )


def _accept_invitation(
    request: HttpRequest, invitation: Invitation, user: User, *, account_existed: bool
) -> None:
    Membership.objects.update_or_create(
        organization=invitation.organization,
        user=user,
        defaults={"role": invitation.role, "is_active": True},
    )
    invitation.status = Invitation.Status.ACCEPTED
    invitation.accepted_by = user
    invitation.save(update_fields=["status", "accepted_by", "updated_at"])
    TenantLifecycle.objects.filter(organization=invitation.organization).update(
        state=TenantLifecycle.State.ACTIVE, changed_by=user
    )
    record_event(
        action="hub.invitation.activated",
        actor=user,
        organization=invitation.organization,
        target=invitation,
        request=request,
        metadata={"account_existed": account_existed},
    )


@require_http_methods(["GET", "POST"])
def login_view(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        if has_platform_role(
            request.user,
            PlatformAccess.Role.DEVELOPER,
            PlatformAccess.Role.SUPPORT,
            PlatformAccess.Role.COMMERCIAL,
        ):
            return redirect("platform:dashboard")
        return redirect("hub:dashboard")
    form = IdentifierAuthenticationForm(request, data=request.POST or None)
    form.fields["password"].widget.attrs.update({"autocomplete": "current-password"})
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        membership = active_membership(request)
        if membership:
            request.session["hub_organization_id"] = str(membership.organization_id)
        target = request.POST.get("next")
        if target:
            return redirect(safe_next(request, target, fallback="hub:dashboard"))
        if has_platform_role(
            user,
            PlatformAccess.Role.DEVELOPER,
            PlatformAccess.Role.SUPPORT,
            PlatformAccess.Role.COMMERCIAL,
        ):
            return redirect("platform:dashboard")
        return redirect("hub:dashboard")
    return render(
        request,
        "hub/login.html",
        {"form": form, "next": safe_next(request, request.GET.get("next"), fallback="")},
    )


def active_membership(request: HttpRequest) -> Membership | None:
    if not request.user.is_authenticated:
        return None
    user = request.user
    memberships = Membership.objects.select_related("organization").filter(
        user=user, is_active=True, organization__is_active=True
    )
    selected = request.session.get("hub_organization_id")
    membership = memberships.filter(organization_id=selected).first() if selected else None
    if membership is None:
        membership = memberships.first()
        if membership:
            request.session["hub_organization_id"] = str(membership.organization_id)
    return membership


# Rows per page on the company registry.
COMPANIES_PER_PAGE = 25


def workspace_context(request: HttpRequest) -> dict[str, object]:
    user = cast(User, request.user)
    support_session = current_support(request) if request.user.is_authenticated else None
    # Support sessions define their own tenant scope.  Do not resolve a normal
    # membership first: its fallback can overwrite the support tenant stored in
    # the session and expose the operator's last workspace in the header.
    membership = active_membership(request) if support_session is None else None
    if support_session:
        office = support_session.organization
        companies_query = ClientCompany.objects.filter(
            organization=support_session.organization, active=True
        )
        companies = (
            companies_query.filter(id__in=support_session.company_ids)
            if support_session.company_ids
            else companies_query
        )
    elif membership:
        office = membership.organization
        companies = company_queryset_for_membership(membership)
    else:
        office = None
        companies = ClientCompany.objects.none()
    # An office can carry hundreds of companies. Resolving the active one by query keeps
    # every workspace page from loading the whole portfolio into memory just to render a
    # header, and keeps the switcher bounded.
    # There is no global "current company". A header switch that silently reinterprets
    # every screen is hidden modal state: the office works across its portfolio, and a
    # single company is a place you open (hub:company-detail), not a mode you enter.
    support_can_mutate = support_session is None or support_session.can_mutate
    module_rows = (
        ProductModule.objects.filter(organization=office, enabled=True).order_by("code")
        if office
        else ProductModule.objects.none()
    )
    enabled_modules = [MODULES[row.code] for row in module_rows if row.code in MODULES]
    # NFS-e is the original core workspace and remains visible for existing offices
    # that have not yet received a CRMew module snapshot.
    if (
        office
        and not ProductModule.objects.filter(
            organization=office, code=ProductModule.Code.NFSE
        ).exists()
    ):
        enabled_modules.insert(0, MODULES[ProductModule.Code.NFSE])
    return {
        "membership": membership,
        "support_session": support_session,
        "support_can_mutate": support_can_mutate,
        "office": office,
        "offices": Membership.objects.select_related("organization").filter(
            user=user, is_active=True, organization__is_active=True
        ),
        "companies": companies,
        "companies_count": companies.count(),
        "can_access_platform": has_platform_role(
            user,
            PlatformAccess.Role.DEVELOPER,
            PlatformAccess.Role.SUPPORT,
            PlatformAccess.Role.COMMERCIAL,
        ),
        "open_reviews_count": ReviewCase.objects.filter(
            organization=office, status=ReviewCase.Status.OPEN, document__company__in=companies
        ).count()
        if office
        else 0,
        "enabled_modules": enabled_modules,
    }


def refuse(request: HttpRequest, reason: str) -> HttpResponse:
    """Refuse with a page the person can leave, not a bare sentence.

    ``HttpResponseForbidden`` renders unstyled text with no navigation: whoever just
    clicked a menu item or submitted a form lands on a blank page whose only way out is
    the browser's back button. The status stays 403; only the body becomes a page that
    says what happened and where to go.
    """

    return render(request, "hub/forbidden.html", {"reason": reason}, status=403)


def office_required[**ViewParams](
    view: Callable[Concatenate[HttpRequest, ViewParams], HttpResponse],
) -> Callable[Concatenate[HttpRequest, ViewParams], HttpResponse]:
    @wraps(view)
    def wrapped(
        request: HttpRequest,
        *args: ViewParams.args,
        **kwargs: ViewParams.kwargs,
    ) -> HttpResponse:
        if not request.user.is_authenticated:
            return redirect(f"{reverse('hub:login')}?next={request.path}")
        support = current_support(request)
        membership = active_membership(request) if support is None else None
        office = (
            support.organization if support else membership.organization if membership else None
        )
        if office is None:
            # A platform operator has no membership of their own, so every workspace URL
            # lands here. Without their own way out the only control on the page signs
            # them out of the console they were actually working in.
            return render(
                request,
                "hub/no_office.html",
                {
                    "has_platform_console": has_platform_role(
                        request.user,
                        PlatformAccess.Role.DEVELOPER,
                        PlatformAccess.Role.SUPPORT,
                        PlatformAccess.Role.COMMERCIAL,
                    )
                },
                status=403,
            )
        if not authorization_is_fresh(office):
            return render(
                request,
                "hub/forbidden.html",
                {"reason": "A permissão precisa ser renovada pelo CRMew."},
                status=403,
            )
        return view(request, *args, **kwargs)

    return cast(Callable[Concatenate[HttpRequest, ViewParams], HttpResponse], wrapped)


@login_required
@require_http_methods(["POST"])
def switch_office(request: HttpRequest) -> HttpResponse:
    user = cast(User, request.user)
    membership = get_object_or_404(
        Membership,
        user=user,
        organization_id=request.POST.get("organization_id"),
        is_active=True,
        organization__is_active=True,
    )
    request.session["hub_organization_id"] = str(membership.organization_id)
    return redirect(safe_next(request, request.POST.get("next"), fallback="hub:dashboard"))


@office_required
def company_detail(request: HttpRequest, company_id: str) -> HttpResponse:
    """Everything the office holds about one client, on one page.

    This replaces the header's "current company" switch. A single company is a place
    you open from the registry and leave again, not a global mode that quietly
    reinterprets every other screen.
    """

    context = workspace_context(request)
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    company = get_object_or_404(companies, id=company_id)

    documents = (
        NfseDocument.objects.filter(organization=office, company=company)
        .select_related("review_case")
        .order_by("-captured_at")[:20]
    )
    context.update(
        {
            "page_title": company.name,
            "company": company,
            "documents": documents,
            "open_cases": ReviewCase.objects.filter(
                organization=office, status=ReviewCase.Status.OPEN, document__company=company
            ).select_related("document")[:20],
            "certificates": Certificate.objects.filter(
                organization=office, company=company, revoked_at__isnull=True
            ).order_by("-valid_until"),
            "dte_messages": DteMessage.objects.filter(
                organization=office, company=company
            ).order_by("-sent_at", "-first_seen_at")[:10],
            "document_count": NfseDocument.objects.filter(
                organization=office, company=company
            ).count(),
            "today": timezone.now(),
        }
    )
    return render(request, "hub/company_detail.html", context)


@office_required
def dashboard(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    open_cases = ReviewCase.objects.filter(
        organization=office,
        status=ReviewCase.Status.OPEN,
        document__company__in=scope,
    ).select_related("document", "document__company")[:8]
    context.update(
        {
            "page_title": "Visão geral",
            "open_cases": open_cases,
            "stats": {
                "companies": companies.count(),
                "documents": NfseDocument.objects.filter(
                    organization=office, company__in=scope
                ).count(),
                "pending": ReviewCase.objects.filter(
                    organization=office,
                    status=ReviewCase.Status.OPEN,
                    document__company__in=scope,
                ).count(),
                "certificates": Certificate.objects.filter(
                    organization=office, company__in=scope, revoked_at__isnull=True
                ).count(),
            },
            "module_states": context["enabled_modules"],
        }
    )
    return render(request, "hub/dashboard.html", context)


@office_required
def nfse_center(request: HttpRequest) -> HttpResponse:
    """Show only the fiscal documents belonging to the active company context."""

    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    scope = cast("QuerySet[ClientCompany]", context["companies"])

    documents = (
        NfseDocument.objects.filter(organization=office, company__in=scope)
        .select_related("review_case", "company")
        .prefetch_related("integration_artifacts")
        .order_by("-captured_at")
    )
    document_rows: list[dict[str, object]] = []
    for document in documents[:100]:
        artifact = next(iter(document.integration_artifacts.all()), None)
        review = getattr(document, "review_case", None)
        document_rows.append(
            {
                "document": document,
                "status": "Em revisão" if review else "Classificada" if artifact else "Recebida",
                "status_class": "attention" if review else "success" if artifact else "muted",
                "accumulator": artifact.accumulator_code if artifact else "—",
                "confidence": artifact.confidence
                if artifact
                else review.confidence
                if review
                else None,
            }
        )

    context.update(
        {
            "page_title": "Central NFS-e",
            "document_rows": document_rows,
            "nfse_stats": {
                "received": documents.count(),
                "pending": ReviewCase.objects.filter(
                    organization=office,
                    status=ReviewCase.Status.OPEN,
                    document__company__in=scope,
                ).count(),
                "classified": sum(1 for row in document_rows if row["status"] == "Classificada"),
            },
        }
    )
    return render(request, "hub/nfse_center.html", context)


def _module_page_context(
    request: HttpRequest, module: ModuleDefinition
) -> tuple[dict[str, object], HttpResponse | None]:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    enabled = ProductModule.objects.filter(
        organization=office, code=module.code, enabled=True
    ).exists()
    if not enabled and module.code != ProductModule.Code.NFSE:
        return context, render(
            request,
            "hub/module_unavailable.html",
            {**context, "page_title": module.label, "module": module},
            status=403,
        )
    if module.connector_kind == Connector.Kind.DOMINIO_AGENT:
        connector = None
        connected = IntelligenceConnector.objects.filter(
            organization=office,
            mode=IntelligenceConnector.Mode.EDGE_AGENT,
            status="healthy",
        ).exists()
    else:
        connector = (
            Connector.objects.defer("encrypted_configuration")
            .filter(organization=office, kind=module.connector_kind)
            .first()
            if module.connector_kind
            else None
        )
        connected = bool(
            connector and connector.enabled and connector.status in {"configured", "healthy"}
        )
    context.update(
        {
            "page_title": module.label,
            "module": module,
            "connector": connector,
            "connector_ready": connected,
        }
    )
    return context, None


def _operational_module(request: HttpRequest, code: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(code))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    company = None
    connector = context["connector"]
    if code == ProductModule.Code.GUIDES:
        kpis = [
            {
                "label": "Vencendo em 7 dias",
                "value": "0",
                "note": "Sem dados sincronizados",
                "tone": "attention",
            },
            {"label": "Em aberto", "value": "0", "note": "Nenhuma pendência", "tone": ""},
            {"label": "Transmitidas", "value": "0", "note": "Neste período", "tone": ""},
        ]
        panel_title, panel_note = "Próximos vencimentos", "Obrigações da empresa atual"
        empty_title = "Nenhum vencimento para mostrar"
        empty_text = (
            "Aguarde a primeira sincronização do Domínio para ver as obrigações desta empresa."
            if context["connector_ready"]
            else "Conecte o Domínio para trazer guias e DCTFWeb automaticamente."
        )
    elif code == ProductModule.Code.INTEGRA:
        artifact_filter = (
            {"organization": office, "document__company": company}
            if company
            else {"organization": office}
        )
        total = IntegrationArtifact.objects.filter(**artifact_filter).count()
        kpis = [
            {"label": "Solicitações hoje", "value": "0", "note": "Aguardando conexão", "tone": ""},
            {"label": "Em andamento", "value": "0", "note": "Sem fila pendente", "tone": ""},
            {
                "label": "Concluídas",
                "value": str(total),
                "note": "Registros integrados",
                "tone": "",
            },
        ]
        panel_title, panel_note = "Solicitações recentes", "Histórico do Integra Contador"
        empty_title, empty_text = (
            "Nenhuma solicitação ainda",
            "Quando uma operação for enviada, o protocolo e o retorno aparecerão aqui.",
        )
    elif code == ProductModule.Code.RECONCILIATION:
        kpis = [
            {
                "label": "Pendências",
                "value": "0",
                "note": "Nenhum extrato importado",
                "tone": "attention",
            },
            {"label": "Conciliados", "value": "0", "note": "Neste período", "tone": ""},
            {"label": "Divergências", "value": "0", "note": "Sem análise disponível", "tone": ""},
        ]
        panel_title, panel_note = "Última conciliação", "Extratos e lançamentos da empresa atual"
        empty_title, empty_text = (
            "Importe um OFX para começar",
            "A conciliação só começa depois que o arquivo bancário e o Domínio estiverem "
            "conectados.",
        )
    else:
        kpis = [
            {
                "label": "Alertas críticos",
                "value": "0",
                "note": "Nenhum alerta novo",
                "tone": "attention",
            },
            {"label": "Mudanças recentes", "value": "0", "note": "Fontes monitoradas", "tone": ""},
            {"label": "Empresas impactadas", "value": "0", "note": "Neste escritório", "tone": ""},
        ]
        panel_title, panel_note = (
            "Radar para esta empresa",
            "Mudanças com possível impacto operacional",
        )
        empty_title, empty_text = (
            "Nenhum alerta relevante",
            "O radar mostrará novidades depois que as fontes tributárias forem sincronizadas.",
        )
    context.update(
        {
            "kpis": kpis,
            "panel_title": panel_title,
            "panel_note": panel_note,
            "empty_title": empty_title,
            "empty_text": empty_text,
            "records": [],
            "setup_steps": [
                "Conexão do escritório",
                "Sincronização segura",
                "Dados prontos para uso",
            ],
            "connector": connector,
        }
    )
    return render(request, "hub/module_page.html", context)


@office_required
def guides(request: HttpRequest) -> HttpResponse:
    return _operational_module(request, ProductModule.Code.GUIDES)


@office_required
def integra(request: HttpRequest) -> HttpResponse:
    _context, blocked = _module_page_context(request, definition(ProductModule.Code.INTEGRA))
    if blocked:
        return blocked
    return redirect("hub:dte-center")


@office_required
@require_http_methods(["GET", "POST"])
def dte_center(request: HttpRequest) -> HttpResponse:
    """Prepare and monitor Caixa Postal runs without spreadsheet-based scopes."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.INTEGRA))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    allowed_companies = cast("QuerySet[ClientCompany]", context["companies"])
    allowed_company_ids = [company.id for company in allowed_companies]
    companies = ClientCompany.objects.filter(id__in=allowed_company_ids, active=True)
    connector = cast(Connector | None, context["connector"])
    form = DtePreparationForm(request.POST or None, companies=companies)

    if request.method == "POST":
        if not context["support_can_mutate"]:
            return refuse(request, "Esta sessão é somente leitura.")
        if not _can_prepare_dte(context):
            return refuse(request, "Seu perfil pode consultar, mas não preparar consultas DTE.")
        if form.is_valid():
            run = prepare_dte_run(
                organization=office,
                connector=connector,
                companies=list(form.cleaned_data["companies"]),
                actor=request.user,
                request=request,
            )
            messages.success(
                request,
                "Consulta DTE preparada para "
                f"{run.total_companies} empresa(s). Nenhuma consulta foi enviada ainda.",
            )
            return redirect("hub:dte-center")

    items = (
        DteRunItem.objects.filter(organization=office, company_id__in=allowed_company_ids)
        .select_related("company", "run", "run__requested_by")
        .order_by("-run__requested_at", "company__name")[:30]
    )
    recent_messages = (
        DteMessage.objects.filter(organization=office, company_id__in=allowed_company_ids)
        .select_related("company")
        .order_by("-sent_at", "-first_seen_at")[:8]
    )
    week_ago = timezone.now() - timedelta(days=7)
    context.update(
        {
            "page_title": "DTE \u2014 Caixa Postal",
            "dte_form": form,
            "dte_companies_count": companies.count(),
            "dte_items": items,
            "recent_dte_messages": recent_messages,
            "dte_stats": {
                "awaiting": DteRun.objects.filter(
                    organization=office, status=DteRun.Status.AWAITING_APPROVAL
                ).count(),
                "unread": DteMessage.objects.filter(
                    organization=office, company_id__in=allowed_company_ids, read_at__isnull=True
                ).count(),
                "new_this_week": DteMessage.objects.filter(
                    organization=office, company_id__in=allowed_company_ids, sent_at__gte=week_ago
                ).count(),
            },
            "pending_runs": (
                DteRun.objects.filter(organization=office, status=DteRun.Status.AWAITING_APPROVAL)
                .select_related("requested_by")
                .prefetch_related("items__company")
                .order_by("-requested_at")
            ),
            "can_prepare_dte": _can_prepare_dte(context),
        }
    )
    return render(request, "hub/dte_center.html", context)


def _can_prepare_dte(context: dict[str, object]) -> bool:
    if not context["support_can_mutate"]:
        return False
    if context["support_session"] is not None:
        return True
    membership = context["membership"]
    return isinstance(membership, Membership) and membership.role not in {
        Membership.Role.AUDITOR,
        Membership.Role.BILLING,
    }


@office_required
@require_http_methods(["POST"])
def decide_dte_run(request: HttpRequest, run_id: str) -> HttpResponse:
    """Authorize or withdraw a prepared run: the second step the screen promises."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.INTEGRA))
    if blocked:
        return blocked
    if not _can_prepare_dte(context):
        return refuse(request, "Seu perfil pode consultar, mas não autorizar consultas DTE.")
    office = cast(Organization, context["office"])
    run = get_object_or_404(
        DteRun, id=run_id, organization=office, status=DteRun.Status.AWAITING_APPROVAL
    )
    decision = request.POST.get("decision", "")
    try:
        if decision == "approve":
            confirmation = approve_dte_run(run=run, actor=request.user, request=request)
            messages.success(
                request,
                f"Consumo autorizado para {confirmation.estimated_units} empresa(s). "
                "A consulta entrou na fila de envio.",
            )
        elif decision == "cancel":
            cancel_dte_run(run=run, actor=request.user, request=request)
            messages.success(request, "Consulta retirada da fila.")
        else:
            messages.error(request, "Escolha autorizar ou retirar.")
    except DteRunTransitionError as error:
        messages.error(request, str(error))
    return redirect("hub:dte-center")


@office_required
def reconciliation(request: HttpRequest) -> HttpResponse:
    return _operational_module(request, ProductModule.Code.RECONCILIATION)


@office_required
def reform(request: HttpRequest) -> HttpResponse:
    return _operational_module(request, ProductModule.Code.REFORM)


@office_required
@require_http_methods(["GET", "POST"])
def companies(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    require_dominio_code = OfficeProfile.objects.filter(
        organization=office, require_dominio_code=True
    ).exists()
    form = CompanyForm(
        request.POST or None,
        organization=office,
        require_dominio_code=require_dominio_code,
    )
    if request.method == "POST" and not context["support_can_mutate"]:
        return refuse(request, "Esta sessão é somente leitura.")
    if (
        request.method == "POST"
        and ControlPlaneBinding.objects.filter(organization=office).exists()
    ):
        return refuse(request, "As empresas desta instalação são controladas pelo CRMew.")
    if request.method == "POST" and form.is_valid():
        company = form.save(commit=False)
        company.organization = office
        company.save()
        record_event(
            action="hub.company.created",
            actor=request.user,
            organization=office,
            target=company,
            request=request,
        )
        messages.success(request, "Empresa adicionada à operação.")
        return redirect("hub:companies")
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    query = request.GET.get("q", "").strip()
    situation = request.GET.get("situacao", "")
    link = request.GET.get("vinculo", "")

    rows = ClientCompany.objects.filter(organization=office)
    if not _sees_every_company(context):
        # The workspace scope already applied the CRMew company boundary; the registry
        # must not widen it just because it queries the office directly.
        rows = rows.filter(id__in=scope.values_list("id", flat=True))
    if query:
        rows = rows.filter(
            Q(name__icontains=query)
            | Q(cnpj_masked__icontains=query)
            | Q(dominio_code__icontains=query)
        )
    if situation == "pausada":
        rows = rows.filter(active=False)
    elif situation == "ativa":
        rows = rows.filter(active=True)
    if link == "sem":
        rows = rows.filter(dominio_code="")
    elif link == "com":
        rows = rows.exclude(dominio_code="")

    paginator = Paginator(rows.order_by("name"), COMPANIES_PER_PAGE)
    page = paginator.get_page(request.GET.get("pagina"))
    filters = {"q": query, "situacao": situation, "vinculo": link}
    context.update(
        {
            "page_title": "Empresas",
            "companies": page.object_list,
            "page_obj": page,
            "paginator": paginator,
            "total_companies": paginator.count,
            "filters": filters,
            "filters_applied": any(filters.values()),
            "query_without_page": urlencode(
                {key: value for key, value in filters.items() if value}
            ),
            "office_company_total": ClientCompany.objects.filter(organization=office).count(),
            "missing_dominio_code": ClientCompany.objects.filter(
                organization=office, dominio_code=""
            ).count(),
            "require_dominio_code": require_dominio_code,
            "form": form,
        }
    )
    return render(request, "hub/companies.html", context)


def _sees_every_company(context: dict[str, object]) -> bool:
    """True when no CRMew binding narrows the office to a per-user company list."""

    office = context["office"]
    return (
        isinstance(office, Organization)
        and not ControlPlaneBinding.objects.filter(organization=office).exists()
    )


@office_required
@require_http_methods(["GET", "POST"])
def certificates(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    if request.method == "POST" and not context["support_can_mutate"]:
        return refuse(request, "Esta sessão é somente leitura.")
    allowed_companies = cast("QuerySet[ClientCompany]", context["companies"])
    form = CertificateUploadForm(
        request.POST or None,
        request.FILES or None,
        organization=office,
        companies=ClientCompany.objects.filter(
            id__in=[company.id for company in allowed_companies]
        ),
    )
    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["pfx_file"]
        if upload.size > 2_000_000:
            form.add_error("pfx_file", "O arquivo deve ter no máximo 2 MB.")
        else:
            try:
                store_certificate(
                    company=form.cleaned_data["company"],
                    pfx_bytes=upload.read(),
                    password=form.cleaned_data["password"],
                    label=form.cleaned_data["label"],
                    actor=request.user,
                    request=request,
                )
            except ValueError as exc:
                form.add_error(None, str(exc))
            else:
                messages.success(
                    request,
                    "Certificado cifrado; o arquivo original não será exibido novamente.",
                )
                return redirect("hub:certificates")
    context.update(
        {
            "page_title": "Certificados",
            "certificates": Certificate.objects.filter(
                organization=office, company__in=allowed_companies
            ).select_related("company"),
            "form": form,
            "support_can_mutate": context["support_can_mutate"],
            "today": timezone.now(),
        }
    )
    return render(request, "hub/certificates.html", context)


@office_required
def reviews(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    context.update(
        {
            "page_title": "Revisão de NFS-e",
            "cases": ReviewCase.objects.filter(
                organization=office,
                document__company__in=scope,
            ).select_related("document", "document__company", "resolved_by"),
        }
    )
    return render(request, "hub/reviews.html", context)


@office_required
@require_http_methods(["POST"])
def resolve_review(request: HttpRequest, case_id: str) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    membership = context["membership"]
    if not context["support_can_mutate"]:
        return refuse(request, "Esta sessão é somente leitura.")
    if context["support_session"] is None and (
        not isinstance(membership, Membership)
        or membership.role
        in {
            Membership.Role.AUDITOR,
            Membership.Role.BILLING,
        }
    ):
        return refuse(request, "Seu perfil pode consultar, mas não classificar documentos.")
    review = get_object_or_404(
        ReviewCase,
        id=case_id,
        organization=office,
        status=ReviewCase.Status.OPEN,
        document__company__in=scope,
    )
    accumulator = request.POST.get("accumulator_code", "").strip()
    if not accumulator:
        messages.error(request, "Informe o acumulador usado para registrar a decisão.")
        return redirect("hub:reviews")
    review.status = ReviewCase.Status.RESOLVED
    review.resolved_accumulator = accumulator
    review.resolved_by = cast(User, request.user)
    review.resolved_at = timezone.now()
    review.save(
        update_fields=["status", "resolved_accumulator", "resolved_by", "resolved_at", "updated_at"]
    )
    record_event(
        action="hub.nfse.review_resolved",
        actor=request.user,
        organization=office,
        target=review,
        request=request,
        metadata={"has_accumulator": True},
    )
    messages.success(request, "Decisão registrada e preservada na auditoria.")
    return redirect("hub:reviews")


@office_required
@require_http_methods(["GET", "POST"])
def settings_view(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    membership = context["membership"]
    can_manage_dominio_agent = (
        context["support_session"] is None
        and isinstance(membership, Membership)
        and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
    )
    connector_form_invalid = False
    if request.method == "POST" and request.POST.get("action") == "dominio-policy":
        if not context["support_can_mutate"]:
            return refuse(request, "Esta sessão é somente leitura.")
        if not can_manage_dominio_agent:
            return refuse(
                request, "Somente owners e administradores mudam a política do escritório."
            )
        required = request.POST.get("require_dominio_code") == "on"
        OfficeProfile.objects.update_or_create(
            organization=office, defaults={"require_dominio_code": required}
        )
        record_event(
            action="hub.office.dominio_policy_changed",
            actor=request.user,
            organization=office,
            request=request,
            metadata={"require_dominio_code": required},
        )
        messages.success(
            request,
            "Código do Domínio passa a ser obrigatório."
            if required
            else "Código do Domínio volta a ser opcional.",
        )
        return redirect("hub:settings")
    if request.method == "POST":
        if not context["support_can_mutate"]:
            return refuse(request, "Esta sessão é somente leitura.")
        form = ConnectorConfigForm(request.POST)
        if form.is_valid():
            kind = form.cleaned_data["kind"]
            configuration = {
                "label": form.cleaned_data["label"],
                "endpoint": form.cleaned_data["endpoint"],
                "database_alias": form.cleaned_data["database_alias"],
            }
            if form.cleaned_data["secret"]:
                configuration["secret"] = form.cleaned_data["secret"]
            connector_updates = {
                "enabled": True,
                "status": "configured",
                "encrypted_configuration": json.dumps(configuration),
                "last_error_code": "",
            }
            updated = Connector.objects.filter(organization=office, kind=kind).update(
                **connector_updates
            )
            connector = (
                Connector.objects.defer("encrypted_configuration").get(
                    organization=office, kind=kind
                )
                if updated
                else Connector.objects.create(
                    organization=office,
                    kind=kind,
                    **connector_updates,
                )
            )
            record_event(
                action="hub.connector.configured",
                actor=request.user,
                organization=office,
                target=connector,
                request=request,
                metadata={"kind": kind, "has_secret": bool(form.cleaned_data["secret"])},
            )
            messages.success(request, "Conexão salva. O próximo ciclo fará o teste automático.")
            return redirect("hub:settings")
        connector_form_invalid = True
    else:
        form = ConnectorConfigForm()
    connectors = list(
        Connector.objects.defer("encrypted_configuration").filter(organization=office)
    )
    connector_by_kind = {item.kind: item for item in connectors}
    context.update(
        {
            "page_title": "Integrações",
            "modules": ProductModule.objects.filter(organization=office),
            "allowances": UsageAllowance.objects.filter(organization=office).order_by("metric"),
            "connectors": connectors,
            "connector_cards": [
                {
                    "kind": kind,
                    "label": label,
                    "connector": connector_by_kind.get(kind),
                }
                for kind, label in Connector.Kind.choices
                if kind != Connector.Kind.DOMINIO_AGENT
            ],
            "connector_form": form,
            "connector_form_invalid": connector_form_invalid,
            "dominio_connector": IntelligenceConnector.objects.filter(
                organization=office, mode=IntelligenceConnector.Mode.EDGE_AGENT
            ).first(),
            "dominio_agents": EdgeAgent.objects.filter(organization=office).order_by(
                "-last_seen_at", "-enrolled_at"
            ),
            "can_manage_dominio_agent": can_manage_dominio_agent,
            "enrollment_code": request.session.pop("dominio_enrollment_code", ""),
            "require_dominio_code": OfficeProfile.objects.filter(
                organization=office, require_dominio_code=True
            ).exists(),
            "companies_missing_dominio_code": ClientCompany.objects.filter(
                organization=office, dominio_code=""
            ).count(),
        }
    )
    return render(request, "hub/settings.html", context)


@office_required
@require_http_methods(["POST"])
def issue_dominio_agent_enrollment(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    membership = context["membership"]
    assert isinstance(office, Organization)
    if not context["support_can_mutate"]:
        return refuse(request, "Esta sessão é somente leitura.")
    if (
        context["support_session"] is not None
        or not isinstance(membership, Membership)
        or membership.role not in {Membership.Role.OWNER, Membership.Role.ADMIN}
    ):
        return refuse(request, "Somente owners e administradores podem parear um agente Domínio.")
    enrollment = issue_enrollment(
        organization=office, actor=cast(User, request.user), request=request
    )
    request.session["dominio_enrollment_code"] = enrollment.code
    messages.success(request, "Código de pareamento criado. Ele expira em 30 minutos.")
    return redirect("hub:settings")
