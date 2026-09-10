from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Concatenate, cast

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction
from django.http import HttpRequest, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.controlplane import authorization_is_fresh, companies_for_membership
from apps.hub.forms import ActivationForm, CertificateUploadForm, CompanyForm
from apps.hub.models import (
    Certificate,
    ClientCompany,
    Connector,
    ControlPlaneBinding,
    NfseDocument,
    ProductModule,
    ReviewCase,
    UsageAllowance,
)
from apps.hub.services import store_certificate
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
    form = AuthenticationForm(request, data=request.POST or None)
    form.fields["username"].widget.attrs.update(
        {"type": "email", "autocomplete": "email", "spellcheck": "false"}
    )
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
    membership = active_membership(request)
    support_session = current_support(request) if request.user.is_authenticated else None
    office = (
        membership.organization
        if membership
        else support_session.organization
        if support_session
        else None
    )
    if membership:
        companies = companies_for_membership(membership)
    elif support_session:
        companies_query = ClientCompany.objects.filter(
            organization=support_session.organization, active=True
        )
        companies = list(
            companies_query.filter(id__in=support_session.company_ids)
            if support_session.company_ids
            else companies_query
        )
    else:
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
        membership = active_membership(request)
        support = current_support(request)
        office = (
            membership.organization if membership else support.organization if support else None
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
            "module_states": ProductModule.objects.filter(
                organization=office, enabled=True
            ).order_by("code"),
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
def settings_view(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    context.update(
        {
            "page_title": "Integrações",
            "modules": ProductModule.objects.filter(organization=office),
            "allowances": UsageAllowance.objects.filter(organization=office).order_by("metric"),
            "connectors": Connector.objects.filter(organization=office),
        }
    )
    return render(request, "hub/settings.html", context)
