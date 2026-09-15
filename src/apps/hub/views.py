from __future__ import annotations

import hashlib
import json
import secrets
import uuid
from collections.abc import Callable
from datetime import timedelta
from decimal import Decimal
from functools import wraps
from typing import Concatenate, cast
from urllib.parse import quote, urlencode

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, QuerySet
from django.db.models.functions import Coalesce
from django.http import (
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import IdentifierAuthenticationForm
from apps.accounts.models import User
from apps.audit.services import record_event
from apps.common.cnpj import lookup_company, normalize_cnpj
from apps.common.network import client_ip
from apps.common.ratelimit import rate_limited
from apps.common.redirects import safe_next
from apps.hub.controlplane import (
    authorization_is_fresh,
    company_queryset_for_membership,
    module_codes_for_membership,
)
from apps.hub.dte_access import DteAccessError, open_message
from apps.hub.dte_payload import body_text
from apps.hub.forms import (
    ActivationForm,
    CertificateUploadForm,
    CollaboratorAccessForm,
    CollaboratorInvitationForm,
    CompanyForm,
    DataSourceForm,
    DtePreparationForm,
    JourneyForm,
    JourneyStepForm,
    OfxImportForm,
    PortalRequestForm,
    UnifiedImportForm,
    UsagePolicyForm,
)
from apps.hub.imports import ImportValidationError, confirm_import, create_import_preview
from apps.hub.models import (
    BankStatementImport,
    Certificate,
    ClientCompany,
    ClientJourney,
    CompanyAccessGrant,
    Connector,
    ControlPlaneBinding,
    DataSource,
    DominioBankEntry,
    DteMessage,
    DteMessageAccess,
    DteRun,
    DteRunItem,
    FiscalGuide,
    ImportBatch,
    IntegrationArtifact,
    JourneyStep,
    NfseDocument,
    OfficeProfile,
    PortalRequest,
    ProductModule,
    ReconciliationMatch,
    ReformAlert,
    ReformSourceStatus,
    ReviewCase,
    UsageAllowance,
)
from apps.hub.module_catalog import MODULES, OFFERED_MODULE_CODES, ModuleDefinition, definition
from apps.hub.reconciliation import OfxParseError, confirm_reconciliation_match, import_ofx
from apps.hub.services import (
    DTE_ACTION_CODE,
    DteRunTransitionError,
    FiscalGuideTransitionError,
    approve_dte_run,
    cancel_dte_run,
    issue_fiscal_guide,
    prepare_dte_run,
    store_certificate,
)
from apps.integra.client import IntegraConfigurationError, credentials_from_settings
from apps.intelligence.agents import issue_enrollment
from apps.intelligence.connectors import ReadOnlyDominoOdbc
from apps.intelligence.models import EdgeAgent, IntelligenceConnector
from apps.intelligence.sync import sync_bank_entries, sync_companies
from apps.organizations.models import Membership, Organization
from apps.platform.availability import copilot_is_available
from apps.platform.billing import BillingError, quote_usage
from apps.platform.forms import LegacyLeadForm, SelfServiceSignupForm, SignupPasswordForm
from apps.platform.models import (
    DominioSupportTicket,
    Invitation,
    Invoice,
    PlatformAccess,
    TenantContract,
    TenantLifecycle,
    TenantUsagePolicy,
    UsageMeter,
)
from apps.platform.notifications import TransactionalEmailError, send_invitation_email
from apps.platform.services import has_platform_role
from apps.platform.signup import (
    SignupError,
    issue_signup,
    provision_signup,
    send_verification_email,
    signup_intent_from_token,
)
from apps.platform.views import current_support
from apps.triage.forms import IMAPConnectionForm
from apps.triage.imap import MailboxIMAPError, encrypted_imap_credential, probe_imap_mailbox
from apps.triage.models import Mailbox, TriageItem
from apps.triage.oauth import (
    MailboxOAuthError,
    encrypted_refresh_credential,
    exchange_code,
    new_authorization,
    probe_mailbox,
)


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """Keep the one-use reset token out of every subsequent Referer header."""

    def dispatch(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        response = super().dispatch(request, *args, **kwargs)
        response["Referrer-Policy"] = "no-referrer"
        return response


def home(request: HttpRequest) -> HttpResponse:
    return render(request, "hub/home.html", {"copilot_available": copilot_is_available()})


@require_http_methods(["POST"])
def proposal_cnpj(request: HttpRequest) -> HttpResponse:
    if rate_limited(f"public-cnpj:{client_ip(request)}", limit=12, window_seconds=60):
        response = JsonResponse(
            {
                "status": "limited",
                "message": "Muitas consultas. Aguarde um minuto ou envie seu pedido.",
            },
            status=429,
        )
        response["Retry-After"] = "60"
    else:
        try:
            cnpj = normalize_cnpj(request.POST.get("cnpj", ""))
        except ValidationError:
            response = JsonResponse(
                {"status": "invalid", "message": "Confira o CNPJ informado."}, status=400
            )
        else:
            response = JsonResponse(lookup_company(cnpj))
    response["Cache-Control"] = "no-store"
    return response


@require_http_methods(["GET", "POST"])
def legacy_proposal(request: HttpRequest) -> HttpResponse:
    if request.method == "GET":
        return redirect("hub:signup")
    form = LegacyLeadForm(request.POST or None)
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
def signup(request: HttpRequest) -> HttpResponse:
    if request.user.is_authenticated:
        return redirect("hub:dashboard")
    form = SelfServiceSignupForm(request.POST or None)
    if request.method == "POST" and rate_limited(
        f"signup:{client_ip(request)}", limit=5, window_seconds=3600
    ):
        messages.error(request, "Muitas tentativas. Aguarde alguns minutos e tente novamente.")
        return render(request, "hub/signup.html", {"form": form}, status=429)
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                issued = issue_signup(
                    email=form.cleaned_data["email"],
                    full_name=form.cleaned_data["full_name"],
                    cnpj=form.cleaned_data["cnpj"],
                    terms_accepted=form.cleaned_data["accept_terms"],
                    marketing_opt_in=form.cleaned_data["accept_marketing"],
                    request=request,
                )
                send_verification_email(issued=issued, base_url=request.build_absolute_uri("/"))
        except SignupError as exc:
            form.add_error(None, str(exc))
        except TransactionalEmailError:
            form.add_error(
                None,
                "Não foi possível enviar a confirmação agora. Tente novamente em alguns minutos.",
            )
        else:
            return render(
                request, "hub/signup_pending.html", {"email": issued.intent.email}, status=202
            )
    return render(request, "hub/signup.html", {"form": form})


@require_http_methods(["GET", "POST"])
def verify_signup(request: HttpRequest, token: str) -> HttpResponse:
    try:
        intent = signup_intent_from_token(token=token)
    except SignupError as exc:
        return render(request, "hub/signup_invalid.html", {"reason": str(exc)}, status=410)
    form = SignupPasswordForm(request.POST or None)
    if request.method == "GET":
        return render(request, "hub/signup_password.html", {"form": form, "email": intent.email})
    if not form.is_valid():
        return render(request, "hub/signup_password.html", {"form": form, "email": intent.email})
    try:
        intent, user = provision_signup(
            token=token, password=form.cleaned_data["password"], request=request
        )
    except SignupError as exc:
        return render(request, "hub/signup_invalid.html", {"reason": str(exc)}, status=410)
    login(request, user, backend="django.contrib.auth.backends.ModelBackend")
    request.session["hub_organization_id"] = str(intent.organization_id)
    messages.success(request, "Escritório confirmado. Seus 14 dias grátis começaram agora.")
    return redirect("hub:setup")


@require_http_methods(["GET", "POST"])
def activate_invitation(request: HttpRequest, token: str) -> HttpResponse:
    invitation = Invitation.objects.filter(
        token_digest=hashlib.sha256(token.encode()).hexdigest()
    ).first()
    if invitation is None or not invitation.usable():
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
    profile, _ = OfficeProfile.objects.get_or_create(organization=invitation.organization)
    if (
        profile.contract_status == OfficeProfile.ContractStatus.TRIAL
        and profile.trial_started_at is None
    ):
        # First activation only; concurrent invitations cannot restart the trial.
        OfficeProfile.objects.filter(pk=profile.pk, trial_started_at__isnull=True).update(
            trial_started_at=(
                profile.created_at
                if invitation.organization.memberships.filter(is_active=True).exists()
                else timezone.now()
            )
        )
    membership, _ = Membership.objects.update_or_create(
        organization=invitation.organization,
        user=user,
        defaults={"role": invitation.role, "is_active": True},
    )
    # Invitations issued inside CICA are explicitly bounded by both company and
    # module. Older platform invitations deliberately have an empty module list
    # and keep their existing unrestricted behavior.
    if invitation.modules:
        selected_company_ids = {
            str(value) for value in invitation.company_ids if isinstance(value, str)
        }
        selected_modules = [str(value) for value in invitation.modules if isinstance(value, str)]
        scoped_companies = ClientCompany.objects.filter(
            organization=invitation.organization,
            id__in=selected_company_ids,
            active=True,
        )
        CompanyAccessGrant.objects.filter(
            organization=invitation.organization, membership=membership
        ).exclude(company__in=scoped_companies).delete()
        for company in scoped_companies:
            CompanyAccessGrant.objects.update_or_create(
                organization=invitation.organization,
                membership=membership,
                company=company,
                defaults={"modules": selected_modules, "capabilities": ["*"], "is_active": True},
            )
    invitation.status = Invitation.Status.ACCEPTED
    invitation.accepted_by = user
    invitation.save(update_fields=["status", "accepted_by", "updated_at"])
    # A platform-created office is deliberately activated by the Mewstack team,
    # after its commercial contract has been configured.  Accepting an owner
    # invitation proves the e-mail address, not that the office may operate.
    # Self-service signups are provisioned separately with their trial contract
    # and lifecycle already active.
    TenantLifecycle.objects.filter(
        organization=invitation.organization,
        state=TenantLifecycle.State.ACTIVATION_PENDING,
    ).filter(
        organization__contracts__status__in=[
            TenantContract.Status.TRIAL,
            TenantContract.Status.ACTIVE,
        ]
    ).update(state=TenantLifecycle.State.ACTIVE, changed_by=user)
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
        {
            "form": form,
            "next": safe_next(
                request, request.POST.get("next") or request.GET.get("next"), fallback=""
            ),
        },
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
INTEGRA_SERVICE_LABELS = {
    "caixapostal.mensagens": "Caixa Postal",
    "ai.answer": "Copiloto CICA",
}


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
    enabled_modules = [
        MODULES[row.code]
        for row in module_rows
        if row.code in MODULES and row.code in OFFERED_MODULE_CODES
    ]
    if not copilot_is_available():
        enabled_modules = [item for item in enabled_modules if item.code != ProductModule.Code.AI]
    # A support session is scoped to its target office, not to a Membership row.
    # Passing its deliberate ``None`` membership into the collaborator permission
    # resolver used to produce an empty set and silently hide every enabled module
    # (including NFS-e) from the support rail.
    permitted_module_codes = (
        None if support_session is not None else module_codes_for_membership(membership)
    )
    if permitted_module_codes is not None:
        enabled_modules = [item for item in enabled_modules if item.code in permitted_module_codes]
    # NFS-e is the original core workspace and remains visible for existing offices
    # that have not yet received a CRMew module snapshot.
    if (
        office
        and not ProductModule.objects.filter(
            organization=office, code=ProductModule.Code.NFSE
        ).exists()
        and (permitted_module_codes is None or ProductModule.Code.NFSE in permitted_module_codes)
    ):
        enabled_modules.insert(0, MODULES[ProductModule.Code.NFSE])
    copilot_enabled = any(item.code == ProductModule.Code.AI for item in enabled_modules)
    active_module_code = (
        ProductModule.Code.INTEGRA
        if request.resolver_match
        and request.resolver_match.url_name
        in {"integra", "dte-center", "dte-message-detail", "decide-dte-run"}
        else None
    )
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
        "copilot_enabled": copilot_enabled,
        "active_module_code": active_module_code,
        "permitted_module_codes": permitted_module_codes,
    }


def refuse(request: HttpRequest, reason: str) -> HttpResponse:
    """Refuse with a page the person can leave, not a bare sentence.

    ``HttpResponseForbidden`` renders unstyled text with no navigation: whoever just
    clicked a menu item or submitted a form lands on a blank page whose only way out is
    the browser's back button. The status stays 403; only the body becomes a page that
    says what happened and where to go.
    """

    return render(request, "hub/forbidden.html", {"reason": reason}, status=403)


def collaborator_can_use_module(context: dict[str, object], code: str) -> bool:
    """Keep module permission independent from menu visibility and URL guessing."""
    permitted = context.get("permitted_module_codes")
    return permitted is None or code in permitted


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
                {"reason": "A permissão precisa ser renovada pelo controle central da Mewstack."},
                status=403,
            )
        lifecycle = TenantLifecycle.objects.filter(organization=office).first()
        if support is None and lifecycle is not None:
            if lifecycle.state in {
                TenantLifecycle.State.PROVISIONING,
                TenantLifecycle.State.ACTIVATION_PENDING,
            }:
                return render(
                    request,
                    "hub/office_activation_pending.html",
                    {"office": office},
                    status=403,
                )
            if lifecycle.state == TenantLifecycle.State.ARCHIVED:
                return refuse(
                    request,
                    "Este escritório foi encerrado e não está disponível para acesso.",
                )
            if (
                lifecycle.state == TenantLifecycle.State.SUSPENDED
                and view.__name__ != "settings_view"
            ):
                return refuse(
                    request,
                    "O escritório está suspenso. Acesse Integrações para solicitar "
                    "suporte à Mewstack.",
                )
            if lifecycle.state == TenantLifecycle.State.GRACE and request.method not in {
                "GET",
                "HEAD",
                "OPTIONS",
            }:
                return refuse(
                    request,
                    "O período de carência permite consulta e suporte em Integrações, "
                    "mas não altera dados operacionais.",
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


@login_required
@require_http_methods(["POST"])
def set_theme(request: HttpRequest) -> HttpResponse:
    """Persist an appearance preference without client-side storage."""

    theme = request.POST.get("theme")
    if theme not in {"system", "light", "dark"}:
        return HttpResponseBadRequest("Tema inv\u00e1lido.")

    response = redirect(safe_next(request, request.POST.get("next"), fallback="hub:dashboard"))
    response.set_cookie(
        "hub_theme",
        theme,
        max_age=60 * 60 * 24 * 365,
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=True,
        samesite="Lax",
    )
    return response


def _can_manage_collaborators(context: dict[str, object]) -> bool:
    membership = context.get("membership")
    return bool(
        context.get("support_can_mutate")
        and isinstance(membership, Membership)
        and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
    )


def _office_module_codes(office: Organization) -> set[str]:
    codes = set(
        ProductModule.objects.filter(organization=office, enabled=True).values_list(
            "code", flat=True
        )
    )
    if not ProductModule.objects.filter(organization=office, code=ProductModule.Code.NFSE).exists():
        codes.add(ProductModule.Code.NFSE)
    return {code for code in codes if code in OFFERED_MODULE_CODES}


def _apply_collaborator_scope(
    *, membership: Membership, company_ids: list[str], modules: list[str]
) -> None:
    office = membership.organization
    companies = ClientCompany.objects.filter(organization=office, id__in=company_ids, active=True)
    CompanyAccessGrant.objects.filter(organization=office, membership=membership).exclude(
        company__in=companies
    ).delete()
    for company in companies:
        CompanyAccessGrant.objects.update_or_create(
            organization=office,
            membership=membership,
            company=company,
            defaults={"modules": modules, "capabilities": ["*"], "is_active": True},
        )


@office_required
@require_http_methods(["GET", "POST"])
def team(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    if not _can_manage_collaborators(context):
        return refuse(
            request,
            "A gest\u00e3o de equipe \u00e9 restrita a propriet\u00e1rios e administradores.",
        )
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    module_codes = _office_module_codes(office)
    form = CollaboratorInvitationForm(
        request.POST or None, companies=companies, module_codes=module_codes
    )
    if request.method == "POST" and form.is_valid():
        try:
            with transaction.atomic():
                raw_token, digest = Invitation.issue_token()
                email = form.cleaned_data["email"].casefold()
                Invitation.objects.filter(
                    organization=office, email__iexact=email, status=Invitation.Status.PENDING
                ).update(status=Invitation.Status.REVOKED)
                invitation = Invitation.objects.create(
                    organization=office,
                    email=email,
                    full_name=form.cleaned_data["full_name"],
                    role=form.cleaned_data["role"],
                    company_ids=form.cleaned_data["companies"],
                    modules=form.cleaned_data["modules"],
                    token_digest=digest,
                    expires_at=timezone.now() + timedelta(days=7),
                    created_by=request.user,
                )
                send_invitation_email(
                    invitation=invitation,
                    activation_url=request.build_absolute_uri(
                        reverse("hub:activate", args=[raw_token])
                    ),
                )
        except TransactionalEmailError:
            form.add_error(
                None,
                "Não foi possível enviar o convite agora. Tente novamente em alguns minutos.",
            )
        else:
            record_event(
                action="hub.collaborator.invited",
                actor=request.user,
                organization=office,
                target=invitation,
                request=request,
                metadata={
                    "company_count": len(invitation.company_ids),
                    "modules": invitation.modules,
                },
            )
            messages.success(request, f"Convite enviado para {invitation.email}.")
            return redirect("hub:team")

    collaborators = list(
        Membership.objects.filter(organization=office, is_active=True)
        .select_related("user")
        .prefetch_related("company_grants__company")
        .order_by("user__full_name", "user__email")
    )
    for item in collaborators:
        grants = list(item.company_grants.all())
        item.role_label = {  # type: ignore[attr-defined]
            Membership.Role.OWNER: "Dono",
            Membership.Role.ADMIN: "Administrador",
            Membership.Role.MANAGER: "Gestor",
            Membership.Role.OPERATOR: "Operador",
            Membership.Role.AUDITOR: "Auditor",
            Membership.Role.BILLING: "Financeiro",
            Membership.Role.MEMBER: "Membro",
        }.get(item.role, item.get_role_display())
        item.scope_modules = sorted(  # type: ignore[attr-defined]
            {str(code) for grant in grants for code in grant.modules if isinstance(code, str)}
        )
        item.scope_companies = [grant.company for grant in grants]  # type: ignore[attr-defined]
        item.scope_is_explicit = bool(grants)  # type: ignore[attr-defined]
        item.dte_science_permission = item.can_acknowledge_dte  # type: ignore[attr-defined]
    context.update(
        {
            "page_title": "Equipe e acessos",
            "collaborator_form": form,
            "collaborators": collaborators,
            "pending_invitations": Invitation.objects.filter(
                organization=office, status=Invitation.Status.PENDING
            ).order_by("-created_at"),
        }
    )
    return render(request, "hub/team.html", context)


@office_required
@require_http_methods(["POST"])
def resend_collaborator_invitation(request: HttpRequest, invitation_id: str) -> HttpResponse:
    context = workspace_context(request)
    if not _can_manage_collaborators(context):
        return refuse(
            request,
            "A gestão de equipe é restrita a proprietários e administradores.",
        )
    office = cast(Organization, context["office"])
    invitation = get_object_or_404(
        Invitation,
        organization=office,
        pk=invitation_id,
        status=Invitation.Status.PENDING,
    )
    try:
        with transaction.atomic():
            raw_token, digest = Invitation.issue_token()
            invitation.token_digest = digest
            invitation.expires_at = timezone.now() + timedelta(days=7)
            invitation.save(update_fields=["token_digest", "expires_at", "updated_at"])
            send_invitation_email(
                invitation=invitation,
                activation_url=request.build_absolute_uri(
                    reverse("hub:activate", args=[raw_token])
                ),
            )
    except TransactionalEmailError:
        messages.error(request, "Não foi possível reenviar o convite agora. Tente novamente.")
        return redirect("hub:team")
    record_event(
        action="hub.collaborator.invitation_resent",
        actor=request.user,
        organization=office,
        target=invitation,
        request=request,
    )
    messages.success(request, f"Novo convite enviado para {invitation.email}.")
    return redirect("hub:team")


@office_required
@require_http_methods(["POST"])
def revoke_collaborator_invitation(request: HttpRequest, invitation_id: str) -> HttpResponse:
    context = workspace_context(request)
    if not _can_manage_collaborators(context):
        return refuse(
            request,
            "A gestão de equipe é restrita a proprietários e administradores.",
        )
    office = cast(Organization, context["office"])
    invitation = get_object_or_404(
        Invitation,
        organization=office,
        pk=invitation_id,
        status=Invitation.Status.PENDING,
    )
    invitation.status = Invitation.Status.REVOKED
    invitation.save(update_fields=["status", "updated_at"])
    record_event(
        action="hub.collaborator.invitation_revoked",
        actor=request.user,
        organization=office,
        target=invitation,
        request=request,
    )
    messages.success(request, "Convite revogado.")
    return redirect("hub:team")


@office_required
@require_http_methods(["POST"])
def update_collaborator_access(request: HttpRequest, membership_id: str) -> HttpResponse:
    context = workspace_context(request)
    if not _can_manage_collaborators(context):
        return refuse(
            request,
            "A gest\u00e3o de equipe \u00e9 restrita a propriet\u00e1rios e administradores.",
        )
    office = cast(Organization, context["office"])
    target = get_object_or_404(Membership, organization=office, pk=membership_id, is_active=True)
    if target.role in {Membership.Role.OWNER, Membership.Role.ADMIN}:
        return refuse(
            request,
            "Proteja o acesso de propriet\u00e1rios e administradores pelo console da Mewstack.",
        )
    form = CollaboratorAccessForm(
        request.POST,
        companies=cast("QuerySet[ClientCompany]", context["companies"]),
        module_codes=_office_module_codes(office),
    )
    if not form.is_valid():
        messages.error(request, "Revise o escopo do colaborador e tente novamente.")
        return redirect("hub:team")
    with transaction.atomic():
        target.role = form.cleaned_data["role"]
        target.can_acknowledge_dte = bool(
            form.cleaned_data["can_acknowledge_dte"]
            and target.role == Membership.Role.OPERATOR
            and ProductModule.Code.INTEGRA in form.cleaned_data["modules"]
            and form.cleaned_data["companies"]
        )
        target.save(update_fields=["role", "can_acknowledge_dte", "updated_at"])
        _apply_collaborator_scope(
            membership=target,
            company_ids=form.cleaned_data["companies"],
            modules=form.cleaned_data["modules"],
        )
    record_event(
        action="hub.collaborator.scope_updated",
        actor=request.user,
        organization=office,
        target=target,
        request=request,
        metadata={
            "company_count": len(form.cleaned_data["companies"]),
            "modules": form.cleaned_data["modules"],
            "can_acknowledge_dte": target.can_acknowledge_dte,
        },
    )
    messages.success(request, "Acessos atualizados.")
    return redirect("hub:team")


@office_required
@require_http_methods(["POST"])
def deactivate_collaborator(request: HttpRequest, membership_id: str) -> HttpResponse:
    context = workspace_context(request)
    if not _can_manage_collaborators(context):
        return refuse(
            request,
            "A gest\u00e3o de equipe \u00e9 restrita a propriet\u00e1rios e administradores.",
        )
    office = cast(Organization, context["office"])
    target = get_object_or_404(Membership, organization=office, pk=membership_id, is_active=True)
    if target.user_id == request.user.id or target.role in {
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
    }:
        return refuse(request, "Este acesso n\u00e3o pode ser removido por esta tela.")
    target.is_active = False
    target.save(update_fields=["is_active", "updated_at"])
    CompanyAccessGrant.objects.filter(organization=office, membership=target).update(
        is_active=False
    )
    record_event(
        action="hub.collaborator.deactivated",
        actor=request.user,
        organization=office,
        target=target,
        request=request,
    )
    messages.success(request, "Acesso interno removido.")
    return redirect("hub:team")


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
@require_http_methods(["GET", "POST"])
def journey(request: HttpRequest) -> HttpResponse:
    """Internal operational workboard, deliberately scoped to the active office."""
    context, blocked = _module_page_context(request, definition(ProductModule.Code.JOURNEY))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    membership = context["membership"]
    can_manage = bool(
        context["support_can_mutate"]
        and isinstance(membership, Membership)
        and membership.role
        in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.MANAGER,
            Membership.Role.OPERATOR,
        }
    )
    allowed_companies = cast("QuerySet[ClientCompany]", context["companies"])
    selected_journey: ClientJourney | None = None
    selected_id = request.GET.get("j")
    if selected_id:
        selected_journey = get_object_or_404(
            ClientJourney.objects.select_related("company", "owner").prefetch_related(
                "steps", "requests"
            ),
            organization=office,
            company__in=allowed_companies,
            pk=selected_id,
        )
    if request.method == "POST":
        if not can_manage:
            return refuse(request, "Seu perfil pode acompanhar jornadas, mas não criar uma nova.")
        form = JourneyForm(request.POST, instance=ClientJourney(organization=office))
        cast(
            "forms.ModelChoiceField[ClientCompany]", form.fields["company"]
        ).queryset = allowed_companies
        if form.is_valid():
            created = form.save(commit=False)
            created.organization = office
            created.owner = request.user
            created.save()
            record_event(
                action="hub.journey.created",
                actor=request.user,
                organization=office,
                target=created,
                request=request,
                metadata={"company_id": str(created.company_id)},
            )
            messages.success(
                request,
                "Jornada criada. Agora você pode organizar as pendências internas.",
            )
            return redirect(f"{reverse('hub:journey')}?{urlencode({'j': created.id})}")
    else:
        form = JourneyForm(instance=ClientJourney(organization=office))
        cast(
            "forms.ModelChoiceField[ClientCompany]", form.fields["company"]
        ).queryset = allowed_companies
    journey_rows = list(
        ClientJourney.objects.filter(organization=office, company__in=allowed_companies)
        .select_related("company", "owner")
        .prefetch_related("steps", "requests")[:12]
    )
    context.update(
        {
            "page_title": "Jornadas",
            "journey_form": form,
            "journey_step_form": JourneyStepForm(prefix="step"),
            "portal_request_form": PortalRequestForm(prefix="request"),
            "selected_journey": selected_journey,
            "can_manage_journey": can_manage,
            "journey_rows": journey_rows,
            "journey_steps": (
                ("Onboarding", "Defina responsáveis, empresas e o primeiro prazo.", "Pronto"),
                (
                    "Pendências",
                    "Centralize o que precisa ser tratado pelo time.",
                    "Pronto",
                ),
                (
                    "Documentos",
                    "Mantenha o histórico operacional por empresa.",
                    "Pronto",
                ),
            ),
        }
    )
    return render(request, "hub/journey.html", context)


def _journey_can_manage(context: dict[str, object]) -> bool:
    membership = context["membership"]
    return bool(
        context["support_can_mutate"]
        and isinstance(membership, Membership)
        and membership.role
        in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
            Membership.Role.MANAGER,
            Membership.Role.OPERATOR,
        }
    )


def _journey_in_scope(
    office: Organization, companies: QuerySet[ClientCompany], journey_id: str | None
) -> ClientJourney:
    return get_object_or_404(
        ClientJourney.objects.select_related("company"),
        organization=office,
        company__in=companies,
        pk=journey_id,
    )


def _journey_redirect(journey: ClientJourney) -> HttpResponse:
    return redirect(f"{reverse('hub:journey')}?{urlencode({'j': journey.id})}")


@office_required
@require_http_methods(["POST"])
def create_journey_step(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.JOURNEY))
    if blocked:
        return blocked
    if not _journey_can_manage(context):
        return refuse(request, "Seu perfil pode acompanhar jornadas, mas não pode alterá-las.")
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    journey = _journey_in_scope(office, companies, request.POST.get("journey_id"))
    form = JourneyStepForm(request.POST, prefix="step")
    if not form.is_valid():
        messages.error(request, "Revise os campos da etapa e tente novamente.")
        return _journey_redirect(journey)
    with transaction.atomic():
        locked_journey = ClientJourney.objects.select_for_update().get(pk=journey.pk)
        last_position = (
            JourneyStep.objects.filter(journey=locked_journey)
            .order_by("-position")
            .values_list("position", flat=True)
            .first()
            or 0
        )
        step = form.save(commit=False)
        step.organization = office
        step.journey = locked_journey
        step.position = last_position + 1
        step.full_clean()
        step.save()
    record_event(
        action="hub.journey.step_created",
        actor=request.user,
        organization=office,
        target=step,
        request=request,
        metadata={"journey_id": str(journey.id)},
    )
    messages.success(request, "Etapa criada.")
    return _journey_redirect(journey)


@office_required
@require_http_methods(["POST"])
def create_portal_request(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.JOURNEY))
    if blocked:
        return blocked
    if not _journey_can_manage(context):
        return refuse(request, "Seu perfil pode acompanhar jornadas, mas não pode alterá-las.")
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    journey = _journey_in_scope(office, companies, request.POST.get("journey_id"))
    form = PortalRequestForm(request.POST, prefix="request")
    if not form.is_valid():
        messages.error(request, "Revise os campos da solicitação e tente novamente.")
        return _journey_redirect(journey)
    item = form.save(commit=False)
    item.organization = office
    item.journey = journey
    item.full_clean()
    item.save()
    record_event(
        action="hub.journey.request_created",
        actor=request.user,
        organization=office,
        target=item,
        request=request,
        metadata={"journey_id": str(journey.id)},
    )
    messages.success(request, "Solicitação criada.")
    return _journey_redirect(journey)


@office_required
@require_http_methods(["POST"])
def complete_journey_step(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.JOURNEY))
    if blocked:
        return blocked
    if not _journey_can_manage(context):
        return refuse(request, "Seu perfil pode acompanhar jornadas, mas não pode alterá-las.")
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    journey = _journey_in_scope(office, companies, request.POST.get("journey_id"))
    step = get_object_or_404(
        JourneyStep, organization=office, journey=journey, pk=request.POST.get("item_id")
    )
    if step.completed_at is None:
        step.completed_at = timezone.now()
        step.save(update_fields=["completed_at", "updated_at"])
        record_event(
            action="hub.journey.step_completed",
            actor=request.user,
            organization=office,
            target=step,
            request=request,
            metadata={"journey_id": str(journey.id)},
        )
        messages.success(request, "Etapa concluída.")
    else:
        messages.info(request, "Essa etapa já foi concluída.")
    return _journey_redirect(journey)


@office_required
@require_http_methods(["POST"])
def transition_portal_request(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.JOURNEY))
    if blocked:
        return blocked
    if not _journey_can_manage(context):
        return refuse(request, "Seu perfil pode acompanhar jornadas, mas não pode alterá-las.")
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    journey = _journey_in_scope(office, companies, request.POST.get("journey_id"))
    item = get_object_or_404(
        PortalRequest, organization=office, journey=journey, pk=request.POST.get("item_id")
    )
    action = request.POST.get("action")
    if action == "received":
        item.status = PortalRequest.Status.RECEIVED
        item.resolved_at = None
        event_action, feedback = (
            "hub.journey.request_received",
            "Solicitação marcada como recebida.",
        )
    elif action == "resolve":
        item.status = PortalRequest.Status.RESOLVED
        item.resolved_at = timezone.now()
        event_action, feedback = "hub.journey.request_resolved", "Solicitação concluída."
    else:
        return HttpResponseBadRequest("Ação de solicitação inválida.")
    item.save(update_fields=["status", "resolved_at", "updated_at"])
    record_event(
        action=event_action,
        actor=request.user,
        organization=office,
        target=item,
        request=request,
        metadata={"journey_id": str(journey.id)},
    )
    messages.success(request, feedback)
    return _journey_redirect(journey)


@office_required
def nfse_center(request: HttpRequest) -> HttpResponse:
    """Show only the fiscal documents belonging to the active company context."""

    context = workspace_context(request)
    if not collaborator_can_use_module(context, ProductModule.Code.NFSE):
        return refuse(request, "Seu acesso n\u00e3o inclui NFS-e Inteligente.")
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
    if module.code == ProductModule.Code.AI and not copilot_is_available():
        return context, HttpResponse(status=404)
    if not collaborator_can_use_module(context, module.code):
        return context, refuse(request, f"Seu acesso n\u00e3o inclui {module.label}.")
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
    if module.code == ProductModule.Code.INTEGRA:
        # The platform is the sole Serpro contractor.  A tenant never configures
        # credentials, certificate, endpoint, or a duplicate connector record.
        connector = None
        try:
            credentials = credentials_from_settings()
            connected = credentials.certificate_path.is_file() and bool(
                credentials.base_url
            )  # Validate the environment without a provider call.
        except IntegraConfigurationError:
            connected = False
    else:
        connector = None
        from apps.hub.models import DataSource

        capabilities: set[str] = set()
        for source_capabilities in DataSource.objects.filter(
            organization=office, status=DataSource.Status.READY
        ).values_list("capabilities", flat=True):
            capabilities.update(source_capabilities)
        legacy_connected = IntelligenceConnector.objects.filter(
            organization=office,
            status="healthy",
            mode__in=[
                IntelligenceConnector.Mode.DIRECT_ODBC,
                IntelligenceConnector.Mode.EDGE_AGENT,
            ],
        ).exists()
        connected = legacy_connected or all(
            item in capabilities for item in module.required_capabilities
        )
    context.update(
        {
            "page_title": module.label,
            "module": module,
            "connector": connector,
            "connector_ready": connected,
            "missing_capabilities": [
                item for item in module.required_capabilities if item not in capabilities
            ]
            if module.code != ProductModule.Code.INTEGRA
            else [],
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
    context, blocked = _module_page_context(request, definition(ProductModule.Code.GUIDES))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    allowed_companies = cast("QuerySet[ClientCompany]", context["companies"])
    today = timezone.localdate()
    guide_list = list(
        FiscalGuide.objects.filter(organization=office, company__in=allowed_companies)
        .select_related("company")
        .order_by("due_on", "company__name")[:60]
    )
    for guide in guide_list:
        guide.amount_brl = Decimal(guide.amount_cents) / 100  # type: ignore[attr-defined]
    pending_statuses = [FiscalGuide.Status.READY, FiscalGuide.Status.FAILED]
    context.update(
        {
            "page_title": "Guias e DCTFWeb",
            "guides": guide_list,
            "guide_stats": {
                "due_this_week": sum(
                    guide.status in pending_statuses and 0 <= (guide.due_on - today).days <= 7
                    for guide in guide_list
                ),
                "pending": sum(guide.status in pending_statuses for guide in guide_list),
                "issued": sum(guide.status == FiscalGuide.Status.ISSUED for guide in guide_list),
            },
            "can_issue_guides": _can_prepare_dte(context),
        }
    )
    return render(request, "hub/guides_center.html", context)


@office_required
@require_http_methods(["POST"])
def issue_guide(request: HttpRequest, guide_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.GUIDES))
    if blocked:
        return blocked
    if not _can_prepare_dte(context):
        return refuse(request, "Seu perfil pode consultar, mas não emitir guias.")
    office = cast(Organization, context["office"])
    allowed_companies = cast("QuerySet[ClientCompany]", context["companies"])
    guide = get_object_or_404(
        FiscalGuide,
        id=guide_id,
        organization=office,
        company__in=allowed_companies,
    )
    try:
        membership = context["membership"]
        approved_overage = isinstance(membership, Membership) and membership.role in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
        }
        issue_fiscal_guide(
            guide=guide,
            actor=request.user,
            request=request,
            approved_overage=approved_overage,
        )
    except FiscalGuideTransitionError as error:
        messages.error(request, str(error))
    else:
        messages.success(request, "Emissão autorizada. A guia entrou na fila da central.")
    return redirect("hub:guides")


@office_required
def integra(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.INTEGRA))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    allowed_companies = cast("QuerySet[ClientCompany]", context["companies"])
    allowed_company_ids = [company.id for company in allowed_companies]
    context.update(
        {
            "page_title": "Central Integra Contador",
            "integra_company_count": ClientCompany.objects.filter(
                id__in=allowed_company_ids, active=True
            ).count(),
            "integra_message_count": DteMessage.objects.filter(
                organization=office, company_id__in=allowed_company_ids
            ).count(),
            "integra_pending_count": DteRun.objects.filter(
                organization=office, status=DteRun.Status.AWAITING_APPROVAL
            ).count(),
            "integra_guides_enabled": ProductModule.objects.filter(
                organization=office, code=ProductModule.Code.GUIDES, enabled=True
            ).exists(),
        }
    )
    return render(request, "hub/integra_home.html", context)


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
    message_filter = request.GET.get("status", "all")
    if message_filter not in {"all", "unread", "read"}:
        message_filter = "all"
    company_filter = request.GET.get("company", "")
    try:
        selected_company = (
            companies.filter(id=uuid.UUID(company_filter)).first() if company_filter else None
        )
    except ValueError:
        selected_company = None
    message_query = DteMessage.objects.filter(
        organization=office, company_id__in=allowed_company_ids
    ).select_related("company", "access_receipt", "current_state").annotate(
        display_read_at=Coalesce("current_state__read_at", "read_at"),
        display_science_at=Coalesce("current_state__science_at", "source_science_at"),
    )
    if selected_company:
        message_query = message_query.filter(company=selected_company)
    search_term = request.GET.get("q", "").strip()[:100]
    if search_term:
        message_query = message_query.filter(
            Q(subject__icontains=search_term) | Q(sender__icontains=search_term)
        )
    if message_filter == "unread":
        message_query = message_query.filter(display_read_at__isnull=True).exclude(
            access_receipt__status=DteMessageAccess.Status.OPENED
        )
    elif message_filter == "read":
        message_query = message_query.filter(
            Q(display_read_at__isnull=False)
            | Q(access_receipt__status=DteMessageAccess.Status.OPENED)
        )
    message_page = Paginator(
        message_query.order_by("-sent_at", "-first_seen_at"), 25
    ).get_page(request.GET.get("page"))
    week_ago = timezone.now() - timedelta(days=7)
    pending_runs = list(
        DteRun.objects.filter(organization=office, status=DteRun.Status.AWAITING_APPROVAL)
        .select_related("requested_by")
        .prefetch_related("items__company")
        .order_by("-requested_at")
    )
    for pending in pending_runs:
        try:
            pending.usage_quote = quote_usage(  # type: ignore[attr-defined]
                organization=office, action_code=DTE_ACTION_CODE, units=pending.total_companies
            )
        except BillingError:
            pending.usage_quote = None  # type: ignore[attr-defined]
        pending.overage_brl = (  # type: ignore[attr-defined]
            Decimal(pending.usage_quote.additional_overage_cents) / 100
            if pending.usage_quote is not None
            else None
        )
    membership = context["membership"]
    can_authorize_overage = isinstance(membership, Membership) and membership.role in {
        Membership.Role.OWNER, Membership.Role.ADMIN
    }
    context.update(
        {
            "page_title": (
                "Central Integra Contador"
                if request.resolver_match and request.resolver_match.url_name == "integra"
                else "Caixa Postal DTE"
            ),
            "dte_form": form,
            "dte_companies_count": form.scope_count - form.ineligible_count,
            "dte_scope_count": form.scope_count,
            "dte_ineligible_count": form.ineligible_count,
            "dte_items": items,
            "dte_message_page": message_page,
            "dte_message_filter": message_filter,
            "dte_selected_company": selected_company,
            "dte_search_term": search_term,
            "dte_companies": companies.order_by("name"),
            "dte_stats": {
                "awaiting": DteRun.objects.filter(
                    organization=office, status=DteRun.Status.AWAITING_APPROVAL
                ).count(),
                "unread": DteMessage.objects.filter(
                    organization=office, company_id__in=allowed_company_ids
                ).annotate(
                    display_read_at=Coalesce("current_state__read_at", "read_at")
                ).filter(display_read_at__isnull=True).exclude(
                    access_receipt__status=DteMessageAccess.Status.OPENED
                ).count(),
                "new_this_week": DteMessage.objects.filter(
                    organization=office, company_id__in=allowed_company_ids, sent_at__gte=week_ago
                ).count(),
            },
            "pending_runs": pending_runs,
            "can_prepare_dte": _can_prepare_dte(context),
            "can_authorize_overage": can_authorize_overage,
            "integra_guides_enabled": ProductModule.objects.filter(
                organization=office, code=ProductModule.Code.GUIDES, enabled=True
            ).exists(),
        }
    )
    return render(request, "hub/dte_center.html", context)


def _can_acknowledge_dte(context: dict[str, object]) -> bool:
    if not context["support_can_mutate"] or context["support_session"] is not None:
        return False
    membership = context["membership"]
    return isinstance(membership, Membership) and (
        membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
        or (
            membership.role == Membership.Role.OPERATOR
            and membership.can_acknowledge_dte
        )
    )


@office_required
@require_http_methods(["GET", "POST"])
def dte_message_detail(request: HttpRequest, message_id: str) -> HttpResponse:
    """Show metadata safely; only the confirmed POST opens the legal provider detail."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.INTEGRA))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    allowed_companies = cast("QuerySet[ClientCompany]", context["companies"])
    message = get_object_or_404(
        DteMessage.objects.select_related("company", "current_state"),
        pk=message_id,
        organization=office,
        company__in=allowed_companies,
    )
    access = DteMessageAccess.objects.filter(organization=office, message=message).first()
    current_state = getattr(message, "current_state", None)
    can_acknowledge = _can_acknowledge_dte(context)
    contract = TenantContract.objects.filter(
        organization=office, status__in=[TenantContract.Status.TRIAL, TenantContract.Status.ACTIVE]
    ).select_related("plan").order_by("-created_at").first()
    detail_rate = None
    if contract:
        detail_rate = contract.service_rates.filter(action_code="caixapostal.detalhe").first()
        if detail_rate is None and contract.plan:
            detail_rate = contract.plan.service_rates.filter(
                action_code="caixapostal.detalhe"
            ).first()
    try:
        detail_quote = (
            quote_usage(organization=office, action_code="caixapostal.detalhe")
            if detail_rate is not None
            else None
        )
    except BillingError:
        detail_quote = None
    can_authorize_overage = isinstance(context["membership"], Membership) and context[
        "membership"
    ].role in {Membership.Role.OWNER, Membership.Role.ADMIN}
    if request.method == "POST":
        if not can_acknowledge:
            return refuse(request, "Este perfil não pode confirmar a ciência do DTE.")
        if not context["connector_ready"]:
            messages.error(request, "A conexão central Serpro ainda não está configurada.")
        elif detail_rate is None or detail_quote is None:
            messages.error(request, "O contrato não inclui a consulta de detalhes da Caixa Postal.")
        elif request.POST.get("confirm_legal_notice") != "on":
            messages.error(
                request, "Confirme que esta abertura pode registrar ciência e iniciar prazo."
            )
        elif detail_quote.additional_overage_units and (
            not can_authorize_overage
            or request.POST.get("confirm_overage") != "on"
            or request.POST.get("approved_overage_cents")
            != str(detail_quote.additional_overage_cents)
        ):
            messages.error(
                request,
                "O valor do excedente precisa ser conferido e autorizado por um dono "
                "ou administrador antes da abertura.",
            )
        else:
            membership = context["membership"]
            approved_overage = bool(detail_quote.additional_overage_units) and isinstance(
                membership, Membership
            ) and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
            try:
                access = open_message(
                    message=message,
                    actor=request.user,
                    request=request,
                    approved_overage=approved_overage,
                    approved_overage_cents=(
                        detail_quote.additional_overage_cents if approved_overage else None
                    ),
                )
            except DteAccessError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(
                    request, "Teor recuperado. Confira a ciência e os prazos indicados."
                )
        return redirect("hub:dte-message-detail", message_id=message.id)
    content = ""
    if access and access.status == DteMessageAccess.Status.OPENED and access.provider_payload:
        try:
            provider_row = json.loads(access.provider_payload)
        except json.JSONDecodeError:
            provider_row = {}
        if isinstance(provider_row, dict):
            content = body_text(provider_row)
    context.update(
        {
            "page_title": "Mensagem da Caixa Postal",
            "dte_message": message,
            "dte_access": access,
            "dte_body_text": content,
            "dte_latest_read_at": (
                current_state.read_at
                if current_state and current_state.read_at
                else message.read_at
            ),
            "dte_latest_science_at": (
                current_state.science_at
                if current_state and current_state.science_at
                else message.source_science_at
            ),
            "can_acknowledge_dte": can_acknowledge,
            "dte_detail_rate": detail_rate,
            "dte_detail_quote": detail_quote,
            "dte_detail_overage_brl": (
                Decimal(detail_quote.additional_overage_cents) / 100 if detail_quote else None
            ),
            "can_open_dte_detail": can_acknowledge
            and bool(context["connector_ready"])
            and detail_rate is not None
            and detail_quote is not None
            and (not detail_quote.additional_overage_units or can_authorize_overage),
        }
    )
    return render(request, "hub/dte_message_detail.html", context)


def _can_prepare_dte(context: dict[str, object]) -> bool:
    if not context["support_can_mutate"]:
        return False
    if context["support_session"] is not None:
        return False
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
            if not context["connector_ready"]:
                messages.error(
                    request,
                    "A conexão central Serpro ainda não está configurada. "
                    "A Mewstack precisa ativá-la antes de autorizar a consulta.",
                )
                return redirect("hub:dte-center")
            membership = context["membership"]
            approved_overage = (
                isinstance(membership, Membership)
                and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
                and request.POST.get("confirm_overage") == "on"
            )
            try:
                approved_overage_total_cents = (
                    int(request.POST["approved_overage_cents"])
                    if approved_overage
                    else None
                )
            except (KeyError, ValueError):
                approved_overage_total_cents = None
            confirmation = approve_dte_run(
                run=run,
                actor=request.user,
                request=request,
                approved_overage=approved_overage,
                approved_overage_total_cents=approved_overage_total_cents,
            )
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
@require_http_methods(["GET", "POST"])
def reconciliation(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    form = OfxImportForm(request.POST or None, request.FILES or None, companies=companies)
    if request.method == "POST" and not context["support_can_mutate"]:
        return refuse(request, "Esta sessão é somente leitura.")
    if request.method == "POST" and form.is_valid():
        upload = form.cleaned_data["ofx_file"]
        if upload.size > 5_000_000:
            form.add_error("ofx_file", "O arquivo deve ter no máximo 5 MB.")
        else:
            try:
                _statement, created = import_ofx(
                    organization=office,
                    company=form.cleaned_data["company"],
                    filename=upload.name,
                    content=upload.read(),
                    actor=request.user,
                    request=request,
                )
            except OfxParseError as exc:
                form.add_error("ofx_file", str(exc))
            else:
                messages.success(
                    request, "OFX importado." if created else "Este OFX já foi importado."
                )
                return redirect("hub:reconciliation")
    matches = list(
        ReconciliationMatch.objects.filter(
            organization=office, transaction__statement__company__in=companies
        )
        .select_related("transaction__statement__company", "dominio_entry")
        .order_by("-transaction__occurred_on", "-created_at")[:100]
    )
    review_keys = {
        (match.transaction.statement.company_id, match.transaction.occurred_on)
        for match in matches
        if match.status == ReconciliationMatch.Status.AMBIGUOUS and not match.is_manual
    }
    candidate_entries = DominioBankEntry.objects.none()
    if review_keys:
        pair_filter = Q()
        for candidate_company_id, occurred_on in review_keys:
            pair_filter |= Q(company_id=candidate_company_id, occurred_on=occurred_on)
        candidate_entries = DominioBankEntry.objects.filter(organization=office).filter(pair_filter)
    candidates_by_key: dict[tuple[object, object, int], list[DominioBankEntry]] = {}
    for entry in candidate_entries:
        entry.amount_brl = Decimal(entry.amount_cents) / 100  # type: ignore[attr-defined]
        candidates_by_key.setdefault(
            (entry.company_id, entry.occurred_on, entry.amount_cents), []
        ).append(entry)
    for match in matches:
        match.candidates = candidates_by_key.get(  # type: ignore[attr-defined]
            (
                match.transaction.statement.company_id,
                match.transaction.occurred_on,
                abs(match.transaction.amount_cents),
            ),
            [],
        )
    context.update(
        {
            "page_title": "Conciliação OFX x Domínio",
            "form": form,
            "imports": BankStatementImport.objects.filter(
                organization=office, company__in=companies
            ).select_related("company")[:20],
            "matches": matches,
            "can_import_ofx": _can_prepare_dte(context),
            "open_import_modal": request.method == "POST" and bool(form.errors),
        }
    )
    return render(request, "hub/reconciliation.html", context)


@office_required
@require_http_methods(["POST"])
def confirm_reconciliation(request: HttpRequest, match_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    if not context["support_can_mutate"] or not _can_prepare_dte(context):
        return refuse(request, "Seu perfil pode consultar, mas não confirmar conciliações.")
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    match = get_object_or_404(
        ReconciliationMatch.objects.select_related("transaction__statement"),
        id=match_id,
        organization=office,
        transaction__statement__company__in=companies,
    )
    entry = get_object_or_404(
        DominioBankEntry,
        id=request.POST.get("dominio_entry_id"),
        organization=office,
    )
    try:
        confirm_reconciliation_match(
            match=match, dominio_entry=entry, actor=request.user, request=request
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Conciliação confirmada.")
    return redirect("hub:reconciliation")


@office_required
def reform(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.REFORM))
    if blocked:
        return blocked
    source = request.GET.get("fonte", "")
    valid_sources = set(ReformAlert.Source.values)
    alerts = ReformAlert.objects.exclude(relevance=ReformAlert.Relevance.GENERAL)
    if source in valid_sources:
        alerts = alerts.filter(source=source)
    else:
        source = ""
    statuses_by_source = {
        status.source: status for status in ReformSourceStatus.objects.all()
    }
    context.update(
        {
            "page_title": "Radar da Reforma Tributária",
            "alerts": alerts[:80],
            "selected_source": source,
            "sources": ReformAlert.Source.choices,
            "source_health": [
                (value, label, statuses_by_source.get(value))
                for value, label in ReformAlert.Source.choices
            ],
        }
    )
    return render(request, "hub/reform.html", context)


@office_required
@require_http_methods(["GET"])
def triage(request: HttpRequest) -> HttpResponse:
    context, blocked = _triage_page_context(request)
    if blocked:
        return blocked
    context["imap_form"] = IMAPConnectionForm()
    return render(request, "hub/triage.html", context)


def _triage_page_context(request: HttpRequest) -> tuple[dict[str, object], HttpResponse | None]:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return context, blocked
    office = context["office"]
    assert isinstance(office, Organization)
    mailboxes = Mailbox.objects.filter(organization=office).order_by("provider", "address")
    context.update(
        {
            "page_title": "Triagem de Arquivos",
            "mailboxes": mailboxes,
            "authorized_mailboxes_exist": mailboxes.filter(status=Mailbox.Status.ACTIVE).exists(),
            "mailbox_error_exists": mailboxes.filter(status=Mailbox.Status.ERROR).exists(),
            "can_manage_mailboxes": _can_manage_collaborators(context),
            "ms_oauth_ready": bool(
                settings.TRIAGE_MS_OAUTH_ENABLED
                and settings.TRIAGE_MS_CLIENT_ID
                and settings.TRIAGE_MS_CLIENT_SECRET
                and settings.TRIAGE_OAUTH_BASE_URL
            ),
            "google_oauth_ready": bool(
                settings.TRIAGE_GOOGLE_OAUTH_ENABLED
                and settings.TRIAGE_GOOGLE_CLIENT_ID
                and settings.TRIAGE_GOOGLE_CLIENT_SECRET
                and settings.TRIAGE_OAUTH_BASE_URL
            ),
        }
    )
    return context, None


@office_required
@require_http_methods(["POST"])
def triage_imap_connect(request: HttpRequest) -> HttpResponse:
    context, blocked = _triage_page_context(request)
    if blocked:
        return blocked
    if not _can_manage_collaborators(context):
        return refuse(request, "Somente o administrador do escritório conecta caixas de e-mail.")
    form = IMAPConnectionForm(request.POST)
    context["imap_form"] = form
    if not form.is_valid():
        return render(request, "hub/triage.html", context)
    if rate_limited(f"triage-imap:{request.user.id}", limit=5, window_seconds=60):
        form.add_error(None, "Muitas tentativas. Aguarde 1 minuto e tente novamente.")
        return render(request, "hub/triage.html", context, status=429)
    host = str(form.cleaned_data["host"])
    address = str(form.cleaned_data["address"]).casefold()
    username = str(form.cleaned_data["username"] or address)
    password = str(form.cleaned_data["password"])
    folder = str(form.cleaned_data["folder"])
    try:
        probe_imap_mailbox(host=host, username=username, password=password, folder=folder)
    except MailboxIMAPError as exc:
        form.add_error(None, str(exc))
        return render(request, "hub/triage.html", context)
    office = context["office"]
    assert isinstance(office, Organization)
    with transaction.atomic():
        mailbox, _ = Mailbox.objects.update_or_create(
            organization=office,
            provider=Mailbox.Provider.IMAP,
            address=address,
            folder=folder,
            defaults={
                "credential": encrypted_imap_credential(
                    host=host, username=username, password=password
                ),
                "cursor": "",
                "since": None,
                "status": Mailbox.Status.ACTIVE,
                "active": False,
                "last_error": "",
            },
        )
    record_event(
        action="triage.mailbox.authorized",
        actor=request.user,
        organization=office,
        target=mailbox,
        request=request,
        metadata={"provider": "imap"},
    )
    messages.success(
        request, "Caixa IMAP autorizada e leitura testada. O recebimento continua desligado."
    )
    return redirect("hub:triage")


@office_required
@require_http_methods(["POST"])
def triage_oauth_start(request: HttpRequest, provider: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    if not _can_manage_collaborators(context):
        return refuse(request, "Somente o administrador do escritório conecta caixas de e-mail.")
    office = context["office"]
    assert isinstance(office, Organization)
    try:
        url, state, verifier = new_authorization(provider)
    except MailboxOAuthError as exc:
        messages.error(request, str(exc))
        return redirect("hub:triage")
    request.session["triage_oauth_flow"] = {
        "provider": provider,
        "state": state,
        "verifier": verifier,
        "office_id": str(office.id),
        "user_id": str(request.user.id),
        "started_at": timezone.now().timestamp(),
    }
    response = redirect(url)
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@office_required
@require_http_methods(["GET"])
def triage_oauth_callback(request: HttpRequest, provider: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    flow = request.session.pop("triage_oauth_flow", None)
    office = context["office"]
    assert isinstance(office, Organization)
    valid = (
        isinstance(flow, dict)
        and flow.get("provider") == provider
        and flow.get("office_id") == str(office.id)
        and flow.get("user_id") == str(request.user.id)
        and isinstance(flow.get("state"), str)
        and isinstance(flow.get("verifier"), str)
        and secrets.compare_digest(flow["state"], request.GET.get("state", ""))
        and isinstance(flow.get("started_at"), (int, float))
        and 0 <= timezone.now().timestamp() - flow["started_at"] <= 600
        and _can_manage_collaborators(context)
    )
    if not valid:
        messages.error(request, "A autorização expirou ou pertence a outra sessão.")
        return _triage_oauth_return()
    if request.GET.get("error"):
        messages.error(
            request,
            "O provedor não autorizou a caixa. Entre novamente com a conta correta; se o "
            "escritório bloquear aplicativos, peça a liberação ao administrador do e-mail.",
        )
        return _triage_oauth_return()
    try:
        access_token, refresh_token = exchange_code(
            provider, code=request.GET.get("code", ""), verifier=flow["verifier"]
        )
        address = probe_mailbox(provider, access_token=access_token)
    except MailboxOAuthError as exc:
        messages.error(request, str(exc))
        return _triage_oauth_return()
    with transaction.atomic():
        mailbox, _ = Mailbox.objects.update_or_create(
            organization=office,
            provider=provider,
            address=address,
            folder="INBOX",
            defaults={
                "credential": encrypted_refresh_credential(provider, refresh_token),
                "status": Mailbox.Status.ACTIVE,
                "active": False,
                "last_error": "",
            },
        )
    record_event(
        action="triage.mailbox.authorized",
        actor=request.user,
        organization=office,
        target=mailbox,
        request=request,
        metadata={"provider": provider},
    )
    messages.success(
        request,
        "Caixa autorizada e leitura testada. A sincronização aguarda o corte inicial.",
    )
    return _triage_oauth_return()


def _triage_oauth_return() -> HttpResponse:
    """Keep the provider authorization code out of caches and referrers."""
    response = redirect("hub:triage")
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@office_required
@require_http_methods(["POST"])
def triage_mailbox_disconnect(request: HttpRequest, mailbox_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    if not _can_manage_collaborators(context):
        return refuse(request, "Somente o administrador do escritório desconecta caixas.")
    office = context["office"]
    assert isinstance(office, Organization)
    mailbox = get_object_or_404(Mailbox, organization=office, id=mailbox_id)
    mailbox.credential = ""
    mailbox.cursor = ""
    mailbox.active = False
    mailbox.status = Mailbox.Status.DISABLED
    mailbox.save(update_fields=["credential", "cursor", "active", "status", "updated_at"])
    record_event(
        action="triage.mailbox.disconnected",
        actor=request.user,
        organization=office,
        target=mailbox,
        request=request,
        metadata={"provider": mailbox.provider},
    )
    messages.success(request, "Caixa desconectada deste escritório.")
    return redirect("hub:triage")

@office_required
@require_http_methods(["GET"])
def triage_item_detail(request: HttpRequest, item_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = context["office"]
    assert isinstance(office, Organization)
    item = get_object_or_404(
        TriageItem.objects.select_related(
            "company", "document_type", "reviewed_by", "blob"
        ).prefetch_related("events__actor"),
        organization=office,
        company__in=context["companies"],
        id=item_id,
    )
    context.update({"page_title": "Arquivo em triagem", "item": item})
    return render(request, "hub/triage_item.html", context)


@office_required
@require_http_methods(["GET"])
def triage_download(request: HttpRequest, item_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        raise Http404
    office = context["office"]
    assert isinstance(office, Organization)
    get_object_or_404(
        TriageItem.objects.all(),
        organization=office,
        company__in=context["companies"],
        id=item_id,
    )
    # There is no verified malware scan in this worktree. Never serve a quarantined
    # attachment, including one marked archived by the older manual prototype.
    raise Http404


@office_required
@require_http_methods(["GET", "POST"])
def companies(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    require_dominio_code = OfficeProfile.objects.filter(
        organization=office, require_dominio_code=True
    ).exists()
    dominio_manages_companies = (
        IntelligenceConnector.objects.filter(
            organization=office,
        )
        .exclude(status="not_configured")
        .exists()
    )
    form = CompanyForm(
        request.POST or None,
        organization=office,
        require_dominio_code=require_dominio_code,
    )
    if request.method == "POST" and not context["support_can_mutate"]:
        return refuse(request, "Esta sessão é somente leitura.")
    if request.method == "POST" and dominio_manages_companies:
        return refuse(request, "As empresas deste escritório são sincronizadas pelo Domínio.")
    if (
        request.method == "POST"
        and ControlPlaneBinding.objects.filter(organization=office).exists()
    ):
        return refuse(
            request,
            "As empresas desta instalação são controladas pelo controle central da Mewstack.",
        )
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
    if link == "com":
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
            "require_dominio_code": require_dominio_code,
            "dominio_manages_companies": dominio_manages_companies,
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
def setup_center(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = cast(Organization, context["office"])
    membership = context["membership"]
    can_manage = bool(
        context["support_session"] is None
        and isinstance(membership, Membership)
        and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
        and context["support_can_mutate"]
    )
    sources = DataSource.objects.filter(organization=office).order_by("created_at")
    selected_source = sources.filter(id=request.GET.get("source")).first()
    if selected_source is None:
        selected_source = sources.first()
    posted_source = sources.filter(id=request.POST.get("source_id")).first()
    if posted_source is not None:
        selected_source = posted_source
    source_form = DataSourceForm(request.POST or None, prefix="source")
    import_form = UnifiedImportForm(
        request.POST or None,
        request.FILES or None,
        prefix="import",
        companies=cast("QuerySet[ClientCompany]", context["companies"]),
        source_kind=selected_source.kind if selected_source else "",
    )
    if request.method == "POST":
        if not can_manage:
            return refuse(request, "Somente owners e administradores alteram a configuração.")
        action = request.POST.get("action")
        if action == "choose-source" and source_form.is_valid():
            kind = source_form.cleaned_data["kind"]
            labels = dict(DataSource.Kind.choices)
            selected_source, _ = DataSource.objects.get_or_create(
                organization=office, kind=kind, defaults={"label": labels[kind]}
            )
            record_event(
                action="hub.data_source.selected",
                actor=request.user,
                organization=office,
                target=selected_source,
                request=request,
                metadata={"kind": kind},
            )
            return redirect(f"{reverse('hub:setup')}?source={selected_source.id}")
        if action == "upload" and import_form.is_valid():
            selected_source = get_object_or_404(
                DataSource, id=request.POST.get("source_id"), organization=office
            )
            try:
                batch, created = create_import_preview(
                    organization=office,
                    data_source=selected_source,
                    kind=import_form.cleaned_data["kind"],
                    upload=import_form.cleaned_data["upload"],
                    actor=cast(User, request.user),
                    company=import_form.cleaned_data.get("company"),
                    source_snapshot_at=import_form.cleaned_data.get("source_snapshot_at"),
                    backup_key=import_form.cleaned_data.get("backup_key", ""),
                    request=request,
                )
            except ImportValidationError as exc:
                import_form.add_error("upload", str(exc))
            else:
                messages.info(
                    request,
                    "Arquivo analisado. Confira e confirme a importação."
                    if created
                    else "Este mesmo arquivo já foi enviado anteriormente.",
                )
                return redirect(
                    f"{reverse('hub:setup')}?source={selected_source.id}&preview={batch.id}"
                )
        if action == "confirm-import":
            batch = get_object_or_404(
                ImportBatch,
                id=request.POST.get("batch_id"),
                organization=office,
                status=ImportBatch.Status.PREVIEW,
            )
            try:
                confirm_import(batch=batch, actor=cast(User, request.user), request=request)
            except (ImportValidationError, ValueError) as exc:
                messages.error(request, f"Não foi possível importar: {exc}")
            else:
                messages.success(
                    request,
                    "Backup enviado para extração. Você pode fechar esta página."
                    if batch.kind == ImportBatch.Kind.DOMINIO_BACKUP
                    else "Importação concluída.",
                )
            return redirect(f"{reverse('hub:setup')}?source={batch.data_source_id}")
        if action == "retry-backup":
            batch = get_object_or_404(
                ImportBatch,
                id=request.POST.get("batch_id"),
                organization=office,
                kind=ImportBatch.Kind.DOMINIO_BACKUP,
                status__in=[ImportBatch.Status.FAILED, ImportBatch.Status.PROCESSING],
            )
            if not batch.source_file or not batch.backup_key:
                messages.error(request, "Envie o backup e a chave novamente para tentar outra vez.")
            else:
                batch.status = ImportBatch.Status.QUEUED
                batch.mapping = {
                    key: value
                    for key, value in batch.mapping.items()
                    if key not in {"claimed_by", "claimed_at"}
                }
                batch.errors = []
                batch.completed_at = None
                batch.save(
                    update_fields=["status", "mapping", "errors", "completed_at", "updated_at"]
                )
                messages.success(request, "Nova tentativa colocada na fila.")
            return redirect(f"{reverse('hub:setup')}?source={batch.data_source_id}")
    preview = ImportBatch.objects.filter(
        id=request.GET.get("preview"), organization=office, status=ImportBatch.Status.PREVIEW
    ).first()
    profile = OfficeProfile.objects.filter(organization=office).first()
    try:
        mfa_complete = request.user.totp_device.is_confirmed
    except (AttributeError, ObjectDoesNotExist):
        mfa_complete = False
    context.update(
        {
            "page_title": "Configuração",
            "source_form": source_form,
            "import_form": import_form,
            "data_sources": sources,
            "selected_source": selected_source,
            "preview_batch": preview,
            "recent_imports": ImportBatch.objects.filter(organization=office)[:8],
            "can_manage_setup": can_manage,
            "agent_installer_url": getattr(settings, "EDGE_AGENT_INSTALLER_URL", ""),
            "setup_steps": [
                {"label": "Confirmar escritório", "done": bool(profile and profile.cnpj_hash)},
                {"label": "Escolher fonte de dados", "done": sources.exists()},
                {
                    "label": "Cadastrar ou importar empresas",
                    "done": ClientCompany.objects.filter(organization=office, active=True).exists(),
                },
                {
                    "label": "Configurar os módulos",
                    "done": ProductModule.objects.filter(
                        organization=office, enabled=True
                    ).exists(),
                },
                {
                    "label": "Convidar sua equipe",
                    "done": Membership.objects.filter(organization=office, is_active=True).count()
                    > 1,
                },
                {"label": "Ativar MFA", "done": mfa_complete},
            ],
        }
    )
    return render(request, "hub/setup.html", context)


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
    can_manage_usage_policy = can_manage_dominio_agent
    contract = (
        TenantContract.objects.filter(
            organization=office,
            status__in=[
                TenantContract.Status.TRIAL,
                TenantContract.Status.ACTIVE,
                TenantContract.Status.GRACE,
                TenantContract.Status.SUSPENDED,
            ],
        )
        .prefetch_related("service_rates")
        .order_by("-created_at")
        .first()
    )
    dominio_connector = (
        IntelligenceConnector.objects.filter(
            organization=office, mode=IntelligenceConnector.Mode.EDGE_AGENT
        ).first()
        or IntelligenceConnector.objects.filter(
            organization=office, mode=IntelligenceConnector.Mode.DIRECT_ODBC
        ).first()
    )
    edge_agent_online = EdgeAgent.objects.filter(
        organization=office,
        status=EdgeAgent.Status.ACTIVE,
        last_seen_at__gte=timezone.now() - timedelta(minutes=2),
    ).exists()
    if dominio_connector is None:
        dominio_sync_state = "not_configured"
    elif dominio_connector.sync_requested_at:
        dominio_sync_state = "syncing"
    elif dominio_connector.status == "error" or dominio_connector.last_error_at:
        dominio_sync_state = "failed"
    elif dominio_connector.mode == IntelligenceConnector.Mode.EDGE_AGENT and not edge_agent_online:
        dominio_sync_state = "attention"
    elif dominio_connector.status == "healthy":
        dominio_sync_state = "synced"
    else:
        dominio_sync_state = "attention"
    policy_form_invalid = False
    policy_form = UsagePolicyForm()
    policy_error_rate_id = ""
    if request.method == "POST" and request.POST.get("action") == "usage-policy":
        if not context["support_can_mutate"]:
            return refuse(request, "Esta sessão é somente leitura.")
        if not can_manage_usage_policy:
            return refuse(request, "Somente owners e administradores mudam o limite de consumo.")
        rate_id = request.POST.get("rate_id", "")
        rate = contract.service_rates.filter(id=rate_id).first() if contract else None
        if rate is None:
            return refuse(request, "Esse serviço não faz parte do contrato deste escritório.")
        if rate.action_code == "ai.answer" and not copilot_is_available():
            return HttpResponse(status=404)
        policy_form = UsagePolicyForm(request.POST, prefix=f"usage_{rate.id}")
        if policy_form.is_valid():
            saved_policy, _ = TenantUsagePolicy.objects.update_or_create(
                organization=office,
                action_code=rate.action_code,
                defaults={
                    "overage_mode": policy_form.cleaned_data["overage_mode"],
                    "warning_percent": policy_form.cleaned_data["warning_percent"],
                    "monthly_overage_cap_cents": policy_form.cap_cents(),
                },
            )
            record_event(
                action="hub.office.usage_policy_changed",
                actor=request.user,
                organization=office,
                target=saved_policy,
                request=request,
                metadata={"action_code": rate.action_code, "mode": saved_policy.overage_mode},
            )
            messages.success(request, "Regra de consumo atualizada.")
            return redirect("hub:settings")
        policy_form_invalid = True
        policy_error_rate_id = str(rate.id)
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
    if request.method == "POST" and request.POST.get("action") == "request-dominio-sync":
        if not context["support_can_mutate"]:
            return refuse(request, "Esta sessão é somente leitura.")
        if not can_manage_dominio_agent:
            return refuse(request, "Somente owners e administradores podem atualizar o Domínio.")
        if dominio_connector is None or dominio_connector.status not in {"healthy", "error"}:
            return refuse(request, "O Domínio não está conectado.")
        if dominio_connector.mode == IntelligenceConnector.Mode.DIRECT_ODBC:
            if not dominio_connector.odbc_dsn:
                return refuse(
                    request, "Conclua a configuração local do Domínio antes de atualizar."
                )
            try:
                adapter = ReadOnlyDominoOdbc(dominio_connector.odbc_dsn)
                result = sync_companies(
                    organization=office,
                    connector=dominio_connector,
                    rows=adapter.execute("companies"),
                )
                bank_entries = sync_bank_entries(
                    organization=office,
                    connector=dominio_connector,
                    rows=adapter.execute("bank_entries"),
                )
            except (RuntimeError, ValueError) as error:
                dominio_connector.status = "error"
                dominio_connector.last_error_code = "odbc_sync"
                dominio_connector.last_error_message = str(error)[:240]
                dominio_connector.last_error_at = timezone.now()
                dominio_connector.save(
                    update_fields=[
                        "status",
                        "last_error_code",
                        "last_error_message",
                        "last_error_at",
                        "updated_at",
                    ]
                )
                messages.error(request, f"Não foi possível atualizar o Domínio: {error}")
            else:
                messages.success(
                    request,
                    "Domínio atualizado: "
                    f"{result.created + result.updated} empresa(s) e "
                    f"{bank_entries.created + bank_entries.updated} item(ns) bancários.",
                )
        else:
            dominio_connector.sync_requested_at = timezone.now()
            dominio_connector.save(update_fields=["sync_requested_at", "updated_at"])
        record_event(
            action="hub.dominio.sync_requested",
            actor=request.user,
            organization=office,
            target=dominio_connector,
            request=request,
        )
        if dominio_connector.mode == IntelligenceConnector.Mode.EDGE_AGENT:
            messages.success(
                request, "Atualização solicitada. O agente consulta o Domínio no próximo ciclo."
            )
        return redirect("hub:settings")
    if request.method == "POST" and request.POST.get("action") == "dominio-support-ticket":
        if not context["support_can_mutate"]:
            return refuse(request, "Esta sessão é somente leitura.")
        if not can_manage_dominio_agent:
            return refuse(request, "Somente owners e administradores podem abrir um chamado.")
        if dominio_connector is None or dominio_sync_state != "failed":
            return refuse(request, "Não há uma falha de sincronização para encaminhar.")
        ticket, created = DominioSupportTicket.objects.get_or_create(
            organization=office,
            connector=dominio_connector,
            status=DominioSupportTicket.Status.OPEN,
            defaults={
                "error_code": dominio_connector.last_error_code,
                "error_message": dominio_connector.last_error_message,
                "opened_by": request.user if isinstance(request.user, User) else None,
            },
        )
        record_event(
            action="hub.dominio.support_ticket_created",
            actor=request.user,
            organization=office,
            target=ticket,
            request=request,
            metadata={"created": created, "error_code": dominio_connector.last_error_code},
        )
        messages.success(
            request,
            "Chamado aberto para desenvolvimento."
            if created
            else "Já existe um chamado aberto para esta falha.",
        )
        return redirect("hub:settings")
    if request.method == "POST":
        # The legacy generic form accepted credentials for connectors that have no
        # adapter or verification path. Refuse direct posts too, so the UI is not
        # the only protection against collecting unusable secrets.
        return refuse(
            request,
            "Esta integração ainda não está disponível. Não informe credenciais.",
        )
    current_period = timezone.localdate().replace(day=1)
    meters_by_action = {
        meter.action_code: meter
        for meter in UsageMeter.objects.filter(organization=office, period_start=current_period)
    }
    policies_by_action = {
        policy.action_code: policy
        for policy in TenantUsagePolicy.objects.filter(organization=office)
    }
    usage_cards = []
    if contract:
        for rate in contract.service_rates.all().order_by("action_code"):
            if rate.action_code == "ai.answer" and not copilot_is_available():
                continue
            meter = meters_by_action.get(rate.action_code)
            policy = policies_by_action.get(rate.action_code)
            usage_cards.append(
                {
                    "action_code": rate.action_code,
                    "label": INTEGRA_SERVICE_LABELS.get(rate.action_code, rate.action_code),
                    "included_units": rate.included_units,
                    "consumed_units": meter.consumed_units if meter else 0,
                    "reserved_units": meter.reserved_units if meter else 0,
                    "overage_units": meter.overage_units if meter else 0,
                    "remaining_units": max(
                        0,
                        rate.included_units
                        - (meter.consumed_units if meter else 0)
                        - (meter.reserved_units if meter else 0),
                    ),
                    "overage_price_cents": rate.overage_unit_price_cents,
                    "overage_price_brl": Decimal(rate.overage_unit_price_cents) / 100,
                    "usage_percent": min(
                        100,
                        round(
                            (
                                (meter.consumed_units if meter else 0)
                                + (meter.reserved_units if meter else 0)
                            )
                            / rate.included_units
                            * 100,
                        )
                        if rate.included_units
                        else 100,
                    ),
                    "policy": policy,
                    "policy_form": (
                        policy_form
                        if policy_form_invalid and policy_error_rate_id == str(rate.id)
                        else UsagePolicyForm(
                            prefix=f"usage_{rate.id}",
                            initial={
                                "overage_mode": (
                                    policy.overage_mode
                                    if policy
                                    else TenantUsagePolicy.OverageMode.BLOCK
                                ),
                                "warning_percent": policy.warning_percent if policy else 80,
                                "monthly_overage_cap_brl": (
                                    Decimal(policy.monthly_overage_cap_cents) / 100
                                    if policy and policy.monthly_overage_cap_cents
                                    else None
                                ),
                            },
                        )
                    ),
                    "rate_id": rate.id,
                    "has_policy_error": policy_form_invalid
                    and policy_error_rate_id == str(rate.id),
                }
            )
    context.update(
        {
            "page_title": "Integrações",
            "modules": ProductModule.objects.filter(organization=office),
            "allowances": UsageAllowance.objects.filter(organization=office).order_by("metric"),
            "connector_cards": [
                {
                    "kind": kind,
                    "label": label,
                }
                for kind, label in Connector.Kind.choices
                if kind not in {Connector.Kind.DOMINIO_AGENT, Connector.Kind.INTEGRA}
            ],
            "usage_cards": usage_cards,
            "can_manage_usage_policy": can_manage_usage_policy,
            "recent_invoices": [
                {
                    "period_start": invoice.period_start,
                    "due_on": invoice.due_on,
                    "status": invoice.status,
                    "status_label": invoice.get_status_display(),
                    "total_brl": Decimal(invoice.total_amount_cents) / 100,
                }
                for invoice in Invoice.objects.filter(organization=office).order_by(
                    "-period_start"
                )[:4]
            ],
            "dominio_connector": dominio_connector,
            "dominio_agents": EdgeAgent.objects.filter(organization=office).order_by(
                "-last_seen_at", "-enrolled_at"
            ),
            "dominio_sync_state": dominio_sync_state,
            "can_request_dominio_sync": bool(
                can_manage_dominio_agent
                and dominio_connector
                and dominio_sync_state in {"synced", "failed"}
                and (
                    (
                        dominio_connector.mode == IntelligenceConnector.Mode.DIRECT_ODBC
                        and dominio_connector.odbc_dsn
                    )
                    or (
                        dominio_connector.mode == IntelligenceConnector.Mode.EDGE_AGENT
                        and edge_agent_online
                    )
                )
            ),
            "can_manage_dominio_agent": can_manage_dominio_agent,
            "enrollment_code": request.session.pop("dominio_enrollment_code", ""),
            "require_dominio_code": OfficeProfile.objects.filter(
                organization=office, require_dominio_code=True
            ).exists(),
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
