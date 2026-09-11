from __future__ import annotations

import json
from collections.abc import Callable
from datetime import timedelta
from functools import wraps
from typing import Concatenate, cast

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import IdentifierAuthenticationForm
from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.controlplane import authorization_is_fresh, companies_for_membership
from apps.hub.forms import (
    ActivationForm,
    CertificateUploadForm,
    CompanyForm,
    ConnectorConfigForm,
    DtePreparationForm,
    OperationalTaskForm,
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
    OperationalTask,
    ProductModule,
    ReviewCase,
    UsageAllowance,
)
from apps.hub.module_catalog import MODULES, ModuleDefinition, definition
from apps.hub.services import prepare_dte_run, store_certificate
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
    import hashlib

    invitation = get_object_or_404(
        Invitation, token_digest=hashlib.sha256(token.encode()).hexdigest()
    )
    if not invitation.usable():
        return render(request, "hub/activation_invalid.html", status=410)
    form = ActivationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user, created = User.objects.get_or_create(
                email=invitation.email,
                defaults={"full_name": invitation.full_name},
            )
            if (
                not created
                and Membership.objects.filter(
                    organization=invitation.organization, user=user, is_active=True
                ).exists()
            ):
                form.add_error(None, "Este acesso já foi ativado.")
                return render(request, "hub/activate.html", {"form": form})
            user.set_password(form.cleaned_data["password"])
            if invitation.full_name and not user.full_name:
                user.full_name = invitation.full_name
            user.is_active = True
            user.save()
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
            )
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session["hub_organization_id"] = str(invitation.organization_id)
        return redirect("hub:dashboard")
    return render(request, "hub/activate.html", {"form": form})


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
            return redirect(target)
        if has_platform_role(
            user,
            PlatformAccess.Role.DEVELOPER,
            PlatformAccess.Role.SUPPORT,
            PlatformAccess.Role.COMMERCIAL,
        ):
            return redirect("platform:dashboard")
        return redirect("hub:dashboard")
    return render(request, "hub/login.html", {"form": form})


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
        companies = list(
            companies_query.filter(id__in=support_session.company_ids)
            if support_session.company_ids
            else companies_query
        )
    elif membership:
        office = membership.organization
        companies = companies_for_membership(membership)
    else:
        office = None
        companies = []
    selected_company_id = request.session.get("hub_company_id")
    active_company = next(
        (company for company in companies if str(company.id) == selected_company_id), None
    )
    if active_company is None and companies:
        active_company = companies[0]
        request.session["hub_company_id"] = str(active_company.id)
    company_scope = [active_company] if active_company else companies
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
        "active_company": active_company,
        "can_access_platform": has_platform_role(
            user,
            PlatformAccess.Role.DEVELOPER,
            PlatformAccess.Role.SUPPORT,
            PlatformAccess.Role.COMMERCIAL,
        ),
        "open_reviews_count": ReviewCase.objects.filter(
            organization=office, status=ReviewCase.Status.OPEN, document__company__in=company_scope
        ).count()
        if office
        else 0,
        "enabled_modules": enabled_modules,
    }


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
            return render(request, "hub/no_office.html", status=403)
        if not authorization_is_fresh(office):
            return render(
                request,
                "hub/forbidden.html",
                {"reason": "A permissÃ£o precisa ser renovada pelo CRMew."},
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
    request.session.pop("hub_company_id", None)
    return redirect(request.POST.get("next") or "hub:dashboard")


@office_required
@require_http_methods(["POST"])
def switch_company(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    selected = str(request.POST.get("company_id", ""))
    companies = cast(list[ClientCompany], context["companies"])
    company = next((item for item in companies if str(item.id) == selected), None)
    if company is None:
        return HttpResponseForbidden("Empresa fora do seu escopo.")
    request.session["hub_company_id"] = str(company.id)
    return redirect(request.POST.get("next") or "hub:dashboard")


@office_required
def dashboard(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    active_company = cast(ClientCompany | None, context["active_company"])
    companies = cast(list[ClientCompany], context["companies"])
    open_cases = ReviewCase.objects.filter(
        organization=office, status=ReviewCase.Status.OPEN, document__company=active_company
    ).select_related("document", "document__company")[:8]
    context.update(
        {
            "page_title": "Visão geral",
            "open_cases": open_cases,
            "stats": {
                "companies": len(companies),
                "documents": NfseDocument.objects.filter(
                    organization=office, company=active_company
                ).count()
                if active_company
                else 0,
                "pending": ReviewCase.objects.filter(
                    organization=office,
                    status=ReviewCase.Status.OPEN,
                    document__company=active_company,
                ).count(),
                "certificates": Certificate.objects.filter(
                    organization=office, company=active_company, revoked_at__isnull=True
                ).count()
                if active_company
                else 0,
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
    active_company = cast(ClientCompany | None, context["active_company"])
    assert isinstance(office, Organization)

    documents = NfseDocument.objects.none()
    document_rows: list[dict[str, object]] = []
    if active_company:
        documents = (
            NfseDocument.objects.filter(organization=office, company=active_company)
            .select_related("review_case")
            .prefetch_related("integration_artifacts")
            .order_by("-captured_at")
        )
        for document in documents[:100]:
            artifact = next(iter(document.integration_artifacts.all()), None)
            review = getattr(document, "review_case", None)
            document_rows.append(
                {
                    "document": document,
                    "status": "Em revisão"
                    if review
                    else "Classificada"
                    if artifact
                    else "Recebida",
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
                "received": documents.count() if active_company else 0,
                "pending": ReviewCase.objects.filter(
                    organization=office,
                    status=ReviewCase.Status.OPEN,
                    document__company=active_company,
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
    active_company = cast(ClientCompany | None, context["active_company"])
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
            "active_company": active_company,
        }
    )
    return context, None


def _operational_module(request: HttpRequest, code: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(code))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    company = cast(ClientCompany | None, context["active_company"])
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
            "company_name": company.name if company else "Nenhuma empresa selecionada",
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
    allowed_companies = cast(list[ClientCompany], context["companies"])
    allowed_company_ids = [company.id for company in allowed_companies]
    companies = ClientCompany.objects.filter(id__in=allowed_company_ids, active=True)
    connector = cast(Connector | None, context["connector"])
    form = DtePreparationForm(request.POST or None, companies=companies)

    if request.method == "POST":
        if not context["support_can_mutate"]:
            return HttpResponseForbidden("Esta sess\u00e3o \u00e9 somente leitura.")
        membership = context["membership"]
        if context["support_session"] is None and (
            not isinstance(membership, Membership)
            or membership.role in {Membership.Role.AUDITOR, Membership.Role.BILLING}
        ):
            return HttpResponseForbidden(
                "Seu perfil pode consultar, mas n\u00e3o preparar consultas DTE."
            )
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
        }
    )
    return render(request, "hub/dte_center.html", context)


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
    form = CompanyForm(request.POST or None)
    if request.method == "POST" and not context["support_can_mutate"]:
        return HttpResponseForbidden("Esta sessão é somente leitura.")
    if (
        request.method == "POST"
        and ControlPlaneBinding.objects.filter(organization=office).exists()
    ):
        return HttpResponseForbidden("As empresas desta instalação são controladas pelo CRMew.")
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
    context.update(
        {
            "page_title": "Empresas",
            "companies": context["companies"],
            "form": form,
        }
    )
    return render(request, "hub/companies.html", context)


def _can_manage_operations(context: dict[str, object]) -> bool:
    membership = context["membership"]
    return bool(
        context["support_can_mutate"]
        and (
            context["support_session"] is not None
            or (
                isinstance(membership, Membership)
                and membership.role not in {Membership.Role.AUDITOR, Membership.Role.BILLING}
            )
        )
    )


@office_required
@require_http_methods(["GET", "POST"])
def operational_tasks(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    allowed_companies = cast(list[ClientCompany], context["companies"])
    allowed_company_ids = [company.id for company in allowed_companies]
    form = OperationalTaskForm(
        request.POST or None,
        companies=ClientCompany.objects.filter(id__in=allowed_company_ids, active=True),
    )
    can_manage = _can_manage_operations(context)
    if request.method == "POST" and not can_manage:
        return HttpResponseForbidden("Seu perfil pode consultar, mas não alterar pendências.")
    if request.method == "POST" and form.is_valid():
        task = form.save(commit=False)
        task.organization = office
        task.created_by = cast(User, request.user)
        task.save()
        record_event(
            action="hub.operational_task.created",
            actor=request.user,
            organization=office,
            target=task,
            request=request,
        )
        messages.success(request, "Pendência adicionada à rotina do escritório.")
        return redirect("hub:tasks")
    tasks = OperationalTask.objects.filter(
        organization=office, company_id__in=allowed_company_ids
    ).select_related("company", "completed_by")
    today = timezone.localdate()
    context.update(
        {
            "page_title": "Pendências e rotinas",
            "task_form": form,
            "tasks": tasks,
            "open_tasks": tasks.filter(status=OperationalTask.Status.OPEN),
            "completed_tasks": tasks.filter(status=OperationalTask.Status.COMPLETED)[:8],
            "can_manage_operations": can_manage,
            "today": today,
        }
    )
    return render(request, "hub/operational_tasks.html", context)


@office_required
@require_http_methods(["POST"])
def complete_operational_task(request: HttpRequest, task_id: str) -> HttpResponse:
    context = workspace_context(request)
    if not _can_manage_operations(context):
        return HttpResponseForbidden("Seu perfil pode consultar, mas não alterar pendências.")
    office = context["office"]
    assert isinstance(office, Organization)
    task = get_object_or_404(
        OperationalTask,
        id=task_id,
        organization=office,
        status=OperationalTask.Status.OPEN,
        company_id__in=[company.id for company in cast(list[ClientCompany], context["companies"])],
    )
    task.status = OperationalTask.Status.COMPLETED
    task.completed_by = cast(User, request.user)
    task.completed_at = timezone.now()
    task.save(update_fields=["status", "completed_by", "completed_at", "updated_at"])
    record_event(
        action="hub.operational_task.completed",
        actor=request.user,
        organization=office,
        target=task,
        request=request,
    )
    messages.success(request, "Pendência concluída e registrada na auditoria.")
    return redirect("hub:tasks")


@office_required
@require_http_methods(["GET", "POST"])
def certificates(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    if request.method == "POST" and not context["support_can_mutate"]:
        return HttpResponseForbidden("Esta sessão é somente leitura.")
    allowed_companies = cast(list[ClientCompany], context["companies"])
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
    active_company = cast(ClientCompany | None, context["active_company"])
    context.update(
        {
            "page_title": "Revisão de NFS-e",
            "cases": ReviewCase.objects.filter(
                organization=office,
                document__company=active_company,
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
    active_company = cast(ClientCompany | None, context["active_company"])
    membership = context["membership"]
    if not context["support_can_mutate"]:
        return HttpResponseForbidden("Esta sessão é somente leitura.")
    if context["support_session"] is None and (
        not isinstance(membership, Membership)
        or membership.role
        in {
            Membership.Role.AUDITOR,
            Membership.Role.BILLING,
        }
    ):
        return HttpResponseForbidden("Seu perfil pode consultar, mas não classificar documentos.")
    review = get_object_or_404(
        ReviewCase,
        id=case_id,
        organization=office,
        status=ReviewCase.Status.OPEN,
        document__company=active_company,
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
    if request.method == "POST":
        if not context["support_can_mutate"]:
            return HttpResponseForbidden("Esta sessão é somente leitura.")
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
        return HttpResponseForbidden("Esta sess\u00e3o \u00e9 somente leitura.")
    if (
        context["support_session"] is not None
        or not isinstance(membership, Membership)
        or membership.role not in {Membership.Role.OWNER, Membership.Role.ADMIN}
    ):
        return HttpResponseForbidden(
            "Somente owners e administradores podem parear um agente Dom\u00ednio."
        )
    enrollment = issue_enrollment(
        organization=office, actor=cast(User, request.user), request=request
    )
    request.session["dominio_enrollment_code"] = enrollment.code
    messages.success(request, "C\u00f3digo de pareamento criado. Ele expira em 30 minutos.")
    return redirect("hub:settings")
