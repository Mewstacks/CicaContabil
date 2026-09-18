from __future__ import annotations

import csv
import hashlib
import io
import json
import logging
import re
import secrets
import uuid
import zipfile
from collections.abc import Callable
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from functools import wraps
from pathlib import PurePath
from types import SimpleNamespace
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
from django.db import IntegrityError, models, transaction
from django.db.models import Case, F, IntegerField, Q, QuerySet, Sum, When
from django.db.models.functions import Coalesce
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import IdentifierAuthenticationForm
from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.common.cnpj import lookup_company, normalize_cnpj
from apps.common.network import client_ip
from apps.common.ratelimit import rate_limited
from apps.common.redirects import detail_redirect, safe_next
from apps.hub.controlplane import (
    authorization_is_fresh,
    company_queryset_for_membership,
    module_codes_for_membership,
)
from apps.hub.demo_session import (
    cleanup_stale_demo_visitors,
    get_progress,
    get_section,
    is_demo_visitor,
    put_progress,
)
from apps.hub.dte_access import DteAccessError, open_message
from apps.hub.dte_payload import body_text
from apps.hub.forms import (
    AccountingPeriodForm,
    ActivationForm,
    CertificateUploadForm,
    CollaboratorAccessForm,
    CollaboratorInvitationForm,
    CompanyForm,
    CostCenterForm,
    DataSourceForm,
    DtePreparationForm,
    FinancialAccountForm,
    JourneyForm,
    JourneyStepForm,
    LedgerAccountForm,
    OfxImportForm,
    PortalRequestForm,
    ReconciliationMovementForm,
    ReconciliationRuleForm,
    ReconciliationUploadForm,
    UnifiedImportForm,
)
from apps.hub.imports import ImportValidationError, confirm_import, create_import_preview
from apps.hub.models import (
    AccountingEntry,
    AccountingExport,
    AccountingPeriod,
    BankStatementImport,
    Certificate,
    ClientCompany,
    ClientJourney,
    CompanyAccessGrant,
    Connector,
    ControlPlaneBinding,
    CostCenter,
    DataSource,
    DctfWebDocument,
    DominioBankEntry,
    DteMessage,
    DteMessageAccess,
    DteRun,
    DteRunItem,
    FinancialAccount,
    FiscalGuide,
    ImportBatch,
    IntegrationArtifact,
    JournalEntry,
    JournalLine,
    JourneyStep,
    LedgerAccount,
    MovementReconciliation,
    NfseDocument,
    NfseSync,
    NormalizedMovement,
    OfficeProfile,
    ParcelamentoOperation,
    PortalRequest,
    ProductModule,
    ReconciliationLayout,
    ReconciliationMatch,
    ReconciliationRule,
    ReconciliationRun,
    ReconciliationSourceFile,
    ReformAlert,
    ReformSourceStatus,
    ReviewCase,
    UsageAllowance,
)
from apps.hub.module_catalog import MODULES, OFFERED_MODULE_CODES, ModuleDefinition, definition
from apps.hub.reconciliation import OfxParseError, confirm_reconciliation_match, import_ofx
from apps.hub.reconciliation_service import (
    ReconciliationError,
    approve_journal_entry,
    create_export,
    create_journal_entry_from_movement,
    create_source_file,
    local_ocr_available,
    prepare_run_for_layout,
    preview_tabular,
    save_layout,
    save_rule_from_movement,
)
from apps.hub.reconciliation_service import (
    confirm_reconciliation as confirm_normalized_reconciliation,
)
from apps.hub.reconciliation_service import (
    undo_reconciliation as undo_normalized_reconciliation,
)
from apps.hub.services import (
    DCTFWEB_DOCUMENT_SERVICE,
    DTE_ACTION_CODE,
    PARCELAMENTO_SERVICE,
    DctfWebDocumentTransitionError,
    DteRunTransitionError,
    FiscalGuideTransitionError,
    ParcelamentoTransitionError,
    approve_dte_run,
    cancel_dte_run,
    issue_fiscal_guide,
    prepare_dctfweb_guide_from_documents,
    prepare_dte_next_page,
    prepare_dte_run,
    request_dctfweb_document,
    request_parcelamento_operation,
    store_certificate,
)
from apps.integra.client import IntegraConfigurationError, credentials_from_settings
from apps.integra.dctfweb import extract_pdf
from apps.integra.errors import IntegraError
from apps.integra.parcelamento import detalhe, parcelas_disponiveis, pdf_das, pedidos
from apps.intelligence.agents import issue_enrollment
from apps.intelligence.connectors import ReadOnlyDominoOdbc
from apps.intelligence.models import EdgeAgent, IntelligenceConnector
from apps.intelligence.sync import sync_bank_entries, sync_companies
from apps.organizations.models import Membership, Organization
from apps.platform.availability import copilot_is_available
from apps.platform.billing import BillingError, UsageQuote, quote_usage
from apps.platform.forms import LegacyLeadForm, SelfServiceSignupForm, SignupPasswordForm
from apps.platform.models import (
    DominioSupportTicket,
    Invitation,
    Invoice,
    PlatformAccess,
    SupportSession,
    TenantContract,
    TenantLifecycle,
    TokenMeter,
    TokenPriceBook,
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
from apps.platform.token_billing import (
    TokenQuote,
    activate_token_book,
    quote_tokens,
)
from apps.platform.views import current_support
from apps.triage.forms import (
    DestinationProfileForm,
    IMAPConnectionForm,
    MailboxOperationForm,
    OfficeOAuthAppForm,
)
from apps.triage.imap import MailboxIMAPError, encrypted_imap_credential, probe_imap_mailbox
from apps.triage.models import DestinationProfile, Mailbox, MailboxOAuthApp, TriageItem
from apps.triage.oauth import (
    MailboxOAuthError,
    encrypted_refresh_credential,
    exchange_code,
    new_authorization,
    probe_mailbox,
    redirect_uri,
)
from apps.triage.presentation import present_mailbox
from apps.triage.services import (
    archive_internal,
    decide_item,
    open_verified_internal_copy,
    queue_windows_archive,
)
from apps.triage.transitions import InvalidTransition, TriageStatus

logger = logging.getLogger(__name__)


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """Keep the one-use reset token out of every subsequent Referer header."""

    def dispatch(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponse:
        response = super().dispatch(request, *args, **kwargs)
        # Django replaces the one-use token with "set-password" before rendering.
        # On that sanitized URL, preserve the same-origin POST context for CSRF;
        # no-referrer can produce Origin: null in browsers on local HTTP.
        response["Referrer-Policy"] = (
            "same-origin" if kwargs.get("token") == self.reset_url_token else "no-referrer"
        )
        return response


@require_http_methods(["GET", "POST"])
def demo_entry(request: HttpRequest) -> HttpResponse:
    """Dedicated demonstration entry; public access stays gated until session isolation."""

    office = Organization.objects.filter(slug=settings.DEMO_ORGANIZATION_SLUG, is_demo=True).first()
    available = bool(
        settings.DEMO_ENTRY_ENABLED and settings.DEMO_SESSION_ISOLATION_READY and office
    )
    if request.method == "POST":
        if not available:
            return HttpResponseBadRequest("A demonstração ainda não está disponível.")
        if rate_limited(f"demo-entry:{client_ip(request)}", limit=8, window_seconds=60):
            return HttpResponse("Aguarde um minuto antes de iniciar outra sessão.", status=429)
        if request.session.get("demo_visit_id") and request.user.is_authenticated:
            request.session.set_expiry(0)
            return redirect("hub:dashboard")
        cleanup_stale_demo_visitors(office)
        visitor_id = uuid.uuid4()
        user = User.objects.create_user(
            email=f"demo-{visitor_id}@example.test", full_name="Visitante da demonstração"
        )
        Membership.objects.create(organization=office, user=user, role=Membership.Role.OWNER)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        request.session["hub_organization_id"] = str(office.id)
        request.session["demo_visit_id"] = str(visitor_id)
        request.session.set_expiry(0)
        return redirect("hub:dashboard")
    return render(
        request,
        "hub/demo_entry.html",
        {"demo_available": available},
    )


def home(request: HttpRequest) -> HttpResponse:
    demo_available = bool(
        settings.DEMO_ENTRY_ENABLED
        and settings.DEMO_SESSION_ISOLATION_READY
        and Organization.objects.filter(
            slug=settings.DEMO_ORGANIZATION_SLUG, is_demo=True, is_active=True
        ).exists()
    )
    return render(
        request,
        "hub/home.html",
        {
            "copilot_available": copilot_is_available(),
            "demo_available": demo_available,
        },
    )


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
    "caixapostal.mensagens": "Consultar Caixa Postal de uma empresa",
    "caixapostal.detalhe": "Abrir teor e registrar eventual ciência DTE",
    "dctfweb.declaracao_completa": "Consultar declaração DCTFWeb",
    "dctfweb.recibo": "Consultar recibo DCTFWeb",
    "dctfweb.guia": "Emitir DARF DCTFWeb",
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
    support_can_mutate = (
        support_session.can_mutate
        if support_session is not None
        else membership is not None and membership.role != Membership.Role.AUDITOR
    )
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
    if not copilot_is_available() and not (office and office.is_demo):
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
        in {
            "integra",
            "parcelamentos",
            "dte-center",
            "dte-message-detail",
            "decide-dte-run",
        }
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
        if (
            is_demo_visitor(request, office)
            and request.method not in {"GET", "HEAD", "OPTIONS"}
            and view.__name__
            not in {
                "assistant",
                "dte_center",
                "decide_dte_run",
                "dte_message_detail",
                "dctfweb_bulk_consult",
                "issue_guide",
                "parcelamentos",
                "nfse_center",
                "confirm_reconciliation",
                "resolve_review",
                "triage_item_detail",
                "certificates",
            }
        ):
            return refuse(
                request,
                "Esta área pode ser vista na demonstração, mas não altera a configuração "
                "ou os dados do escritório-demo central.",
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


@require_http_methods(["POST"])
def set_theme(request: HttpRequest) -> HttpResponse:
    """Persist an appearance preference without client-side storage."""

    theme = request.POST.get("theme")
    if theme not in {"system", "light", "dark"}:
        return HttpResponseBadRequest("Tema inv\u00e1lido.")

    fallback = "hub:dashboard" if request.user.is_authenticated else "hub:home"
    response = redirect(safe_next(request, request.POST.get("next"), fallback=fallback))
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
    open_cases_query = ReviewCase.objects.filter(
        organization=office,
        status=ReviewCase.Status.OPEN,
        document__company__in=scope,
    ).select_related("document", "document__company")
    if is_demo_visitor(request, office):
        demo_open_cases = [
            _demo_review_for_view(request, review) for review in open_cases_query[:20]
        ]
        open_cases = [
            review for review in demo_open_cases if review.status == ReviewCase.Status.OPEN
        ][:8]
    else:
        open_cases = open_cases_query[:8]
    enabled_codes = {module.code for module in context["enabled_modules"]}
    review_count = (
        len([review for review in demo_open_cases if review.status == ReviewCase.Status.OPEN])
        if is_demo_visitor(request, office)
        else open_cases_query.count()
    )
    work_areas = []
    if ProductModule.Code.NFSE in enabled_codes:
        work_areas.append(
            {
                "label": "Revisões de NFS-e",
                "count": review_count,
                "note": "Decisões de classificação pendentes",
                "url": reverse("hub:reviews"),
            }
        )
    if ProductModule.Code.INTEGRA in enabled_codes:
        dte_query = DteMessage.objects.filter(organization=office, company__in=scope)
        if is_demo_visitor(request, office):
            opened_ids = set(get_section(request, "dte_messages"))
            dte_count = sum(
                message.read_at is None and str(message.id) not in opened_ids
                for message in dte_query.only("id", "read_at")
            )
        else:
            dte_count = dte_query.filter(read_at__isnull=True).count()
        work_areas.append(
            {
                "label": "Caixa DTE",
                "count": dte_count,
                "note": "Mensagens sem abertura registrada",
                "url": f"{reverse('hub:dte-center')}?status=unread",
            }
        )
    if ProductModule.Code.GUIDES in enabled_codes:
        guide_query = FiscalGuide.objects.filter(organization=office, company__in=scope)
        if is_demo_visitor(request, office):
            demo_guides = list(guide_query)
            for guide in demo_guides:
                _demo_guide_for_view(request, guide)
            guide_count = sum(
                guide.status in {FiscalGuide.Status.READY, FiscalGuide.Status.FAILED}
                for guide in demo_guides
            )
        else:
            guide_count = guide_query.filter(
                status__in=[FiscalGuide.Status.READY, FiscalGuide.Status.FAILED]
            ).count()
        work_areas.append(
            {
                "label": "Guias e DCTFWeb",
                "count": guide_count,
                "note": "Guias prontas ou com falha",
                "url": f"{reverse('hub:guides')}?status=pending",
            }
        )
    if ProductModule.Code.TRIAGE in enabled_codes:
        triage_query = TriageItem.objects.filter(organization=office).filter(
            Q(company__in=scope) | Q(company__isnull=True)
        )
        if is_demo_visitor(request, office):
            triage_count = sum(
                _demo_triage_for_view(request, item).status
                in {
                    TriageStatus.QUARANTINED,
                    TriageStatus.AWAITING_REVIEW,
                    TriageStatus.READY_TO_ARCHIVE,
                }
                for item in triage_query
                if _demo_triage_base_status(item) is not None
            )
        else:
            triage_count = triage_query.filter(
                status__in=[
                    TriageStatus.QUARANTINED,
                    TriageStatus.AWAITING_REVIEW,
                    TriageStatus.READY_TO_ARCHIVE,
                ]
            ).count()
        work_areas.append(
            {
                "label": "Triagem de arquivos",
                "count": triage_count,
                "note": "Anexos aguardando segurança ou decisão",
                "url": reverse("hub:triage"),
            }
        )
    if ProductModule.Code.RECONCILIATION in enabled_codes:
        reconciliation_count = ReconciliationMatch.objects.filter(
            organization=office,
            transaction__statement__company__in=scope,
            status__in=[
                ReconciliationMatch.Status.AMBIGUOUS,
                ReconciliationMatch.Status.UNMATCHED,
            ],
        ).count()
        work_areas.append(
            {
                "label": "Conciliação",
                "count": reconciliation_count,
                "note": "Lançamentos ambíguos ou sem correspondência",
                "url": f"{reverse('hub:reconciliation')}?status=attention",
            }
        )
    context.update(
        {
            "page_title": "Visão geral",
            "open_cases": open_cases,
            "work_areas": work_areas,
            "stats": {
                "companies": companies.count(),
                "documents": NfseDocument.objects.filter(
                    organization=office, company__in=scope
                ).count(),
                "pending": review_count,
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
@require_http_methods(["GET", "POST"])
def nfse_center(request: HttpRequest) -> HttpResponse:
    """Show only the fiscal documents belonging to the active company context."""

    context = workspace_context(request)
    if not collaborator_can_use_module(context, ProductModule.Code.NFSE):
        return refuse(request, "Seu acesso n\u00e3o inclui NFS-e Inteligente.")
    office = context["office"]
    assert isinstance(office, Organization)
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    membership = context["membership"]
    can_manage_sync = bool(
        is_demo_visitor(request, office)
        or (
            context["support_can_mutate"]
            and isinstance(membership, Membership)
            and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
        )
    )

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action in {"demo_download_issued", "demo_download_taken"}:
            if not is_demo_visitor(request, office):
                return refuse(
                    request, "O download em lote está disponível somente na demonstração."
                )
            selected_query = NfseDocument.objects.filter(
                organization=office, company__in=scope
            ).select_related("company")
            if request.POST.get("all_documents") == "1":
                selected_documents = list(selected_query.order_by("-issued_at", "-captured_at"))
            else:
                document_ids = list(dict.fromkeys(request.POST.getlist("documents")))
                selected_documents = list(selected_query.filter(id__in=document_ids))
            if not selected_documents:
                messages.error(request, "Selecione ao menos uma NFS-e para a demonstração.")
                return redirect(reverse("hub:nfse-center"))
            folder = "Tomadas" if action == "demo_download_taken" else "Emitidas"
            return _demo_nfse_bulk_download(
                selected_documents,
                folder=folder,
                classifications=_demo_nfse_download_classifications(request, selected_documents),
            )

        if not can_manage_sync:
            return refuse(request, "Somente dono ou administrador configura a coleta NFS-e.")
        target_ids = list(dict.fromkeys(request.POST.getlist("companies")))[:100]
        selected_companies = list(scope.filter(id__in=target_ids, active=True))
        if not selected_companies:
            messages.error(request, "Selecione ao menos uma empresa da sua carteira.")
            return redirect(
                reverse("hub:nfse-center")
                + ("?view=collection" if request.GET.get("view") == "collection" else "")
            )
        if is_demo_visitor(request, office):
            for company in selected_companies:
                put_progress(
                    request,
                    "nfse_syncs",
                    company.id,
                    {"status": "paused" if action == "pause" else "idle"},
                )
            messages.success(
                request,
                "Cenário fictício atualizado nesta sessão. Nenhum certificado ou ADN foi acionado.",
            )
            return redirect(
                reverse("hub:nfse-center")
                + ("?view=collection" if request.GET.get("view") == "collection" else "")
            )

        if action not in {"activate", "pause", "retry"}:
            return HttpResponseBadRequest("Ação de sincronização inválida.")
        changed = 0
        blocked = 0
        for company in selected_companies:
            sync = NfseSync.objects.filter(organization=office, company=company).first()
            if action == "pause":
                if sync is not None:
                    sync.enabled = False
                    sync.status = NfseSync.Status.PAUSED
                    sync.next_run_at = None
                    sync.save(update_fields=["enabled", "status", "next_run_at", "updated_at"])
                    changed += 1
                continue
            certificate = (
                Certificate.objects.filter(
                    organization=office,
                    company=company,
                    revoked_at__isnull=True,
                    valid_until__gt=timezone.now(),
                )
                .order_by("-valid_until", "-created_at")
                .first()
            )
            if certificate is None:
                blocked += 1
                continue
            try:
                from apps.hub.nfse_sync import certificate_ssl_context

                certificate_ssl_context(certificate)
            except ValidationError:
                blocked += 1
                continue
            sync, _created = NfseSync.objects.update_or_create(
                organization=office,
                company=company,
                defaults={
                    "certificate": certificate,
                    "enabled": True,
                    "status": NfseSync.Status.IDLE,
                    "last_error_code": "",
                    "last_error_message": "",
                    "last_error_at": None,
                    "failure_count": 0,
                    "next_run_at": timezone.now(),
                },
            )
            changed += 1
            if settings.NFSE_ADN_SYNC_ENABLED:
                from apps.hub.tasks import poll_nfse_sync

                transaction.on_commit(lambda sync_id=str(sync.id): poll_nfse_sync.delay(sync_id))
        record_event(
            action=f"hub.nfse.sync_{action}",
            actor=request.user,
            organization=office,
            target=office,
            request=request,
            metadata={"changed": changed, "blocked": blocked},
        )
        if changed:
            messages.success(
                request,
                f"{changed} empresa{'s' if changed != 1 else ''} "
                f"atualizada{'s' if changed != 1 else ''}.",
            )
        if blocked:
            messages.error(
                request,
                f"{blocked} empresa{'s' if blocked != 1 else ''} sem e-CNPJ válido e compatível.",
            )
        return redirect(
            reverse("hub:nfse-center")
            + ("?view=collection" if request.GET.get("view") == "collection" else "")
        )

    document_query = (
        NfseDocument.objects.filter(organization=office, company__in=scope)
        .select_related("review_case", "company")
        .prefetch_related("integration_artifacts")
    )
    document_search = request.GET.get("q", "").strip()[:100]
    document_status = request.GET.get("status", "all")
    document_date_filter = request.GET.get("date_filter", "competence")
    document_competence = request.GET.get("competence", "").strip()[:7]
    if "competence_month" in request.GET:
        month = request.GET.get("competence_month", "")
        year = request.GET.get("competence_year", "")
        document_competence = f"{year}-{month}" if month and year else ""
    issued_from = request.GET.get("issued_from", "").strip()[:10]
    issued_to = request.GET.get("issued_to", "").strip()[:10]
    if document_status not in {"all", "review", "classified", "received"}:
        document_status = "all"
    if document_date_filter not in {"competence", "issued"}:
        document_date_filter = "competence"
    documents = document_query
    if document_search:
        documents = documents.filter(
            Q(company__name__icontains=document_search)
            | Q(company__dominio_code__icontains=document_search)
            | Q(source_nsu__icontains=document_search)
            | Q(document_hash__icontains=document_search)
        )
    if document_status == "review":
        documents = documents.filter(review_case__status=ReviewCase.Status.OPEN)
    elif document_status == "classified":
        documents = documents.filter(integration_artifacts__isnull=False)
    elif document_status == "received":
        documents = documents.filter(integration_artifacts__isnull=True).exclude(
            review_case__status=ReviewCase.Status.OPEN
        )
    if document_date_filter == "competence" and re.fullmatch(
        r"\d{4}-(0[1-9]|1[0-2])", document_competence
    ):
        competence_year, competence_month = document_competence.split("-")
        if not office.is_demo:
            documents = documents.filter(
                issued_at__year=int(competence_year), issued_at__month=int(competence_month)
            )
    elif document_date_filter == "competence":
        document_competence = ""
    date_filter_error = ""

    def parse_filter_date(value):
        nonlocal date_filter_error
        if not value:
            return None
        try:
            return (
                datetime.strptime(value, "%d/%m/%Y").date()
                if "/" in value
                else date.fromisoformat(value)
            )
        except ValueError:
            if document_date_filter == "issued":
                date_filter_error = "Informe uma data válida no formato DD/MM/AAAA."
            return None

    issued_from_date = parse_filter_date(issued_from)
    issued_to_date = parse_filter_date(issued_to)
    if issued_from_date:
        issued_from = issued_from_date.strftime("%d/%m/%Y")
    if issued_to_date:
        issued_to = issued_to_date.strftime("%d/%m/%Y")
    if (
        document_date_filter == "issued"
        and issued_from_date
        and issued_to_date
        and issued_from_date > issued_to_date
    ):
        date_filter_error = "A data final deve ser igual ou posterior à inicial."
    if date_filter_error:
        documents = documents.none()
    if not office.is_demo and document_date_filter == "issued" and issued_from_date:
        documents = documents.filter(issued_at__date__gte=issued_from_date)
    if not office.is_demo and document_date_filter == "issued" and issued_to_date:
        documents = documents.filter(issued_at__date__lte=issued_to_date)
    documents = documents.distinct()
    document_total = documents.count()
    ordered_documents = documents.order_by("-issued_at", "-captured_at")
    if office.is_demo:
        # Old demo fixtures keep their emission date in the normalized XML data.
        # Filter against the same date shown in the table, before limiting rows.
        demo_documents = []
        for document in ordered_documents:
            issued = document.issued_at or _nfse_issued_at_from_normalized_data(document)
            if issued and timezone.is_aware(issued):
                issued = timezone.localtime(issued)
            issued_date = issued.date() if issued else None
            if (
                document_date_filter == "competence"
                and document_competence
                and (not issued_date or issued_date.strftime("%Y-%m") != document_competence)
            ):
                continue
            if document_date_filter == "issued":
                if issued_from_date and (not issued_date or issued_date < issued_from_date):
                    continue
                if issued_to_date and (not issued_date or issued_date > issued_to_date):
                    continue
            demo_documents.append(document)
        document_total = len(demo_documents)
        ordered_documents = demo_documents
    document_rows: list[dict[str, object]] = []
    for document in ordered_documents[:100]:
        artifact = next(iter(document.integration_artifacts.all()), None)
        review = getattr(document, "review_case", None)
        open_review = review if review and review.status == ReviewCase.Status.OPEN else None
        issued_at = document.issued_at or _nfse_issued_at_from_normalized_data(document)
        confidence = (
            97
            if office.is_demo and artifact and artifact.confidence <= 95
            else artifact.confidence
            if artifact
            else open_review.confidence
            if open_review
            else None
        )
        document_rows.append(
            {
                "document": document,
                "issued_at": issued_at,
                "review": open_review,
                "status": (
                    "Em revisão" if open_review else "Classificada" if artifact else "Recebida"
                ),
                "status_class": (
                    "attention" if open_review else "success" if artifact else "muted"
                ),
                "accumulator": artifact.accumulator_code if artifact else "—",
                "confidence": confidence,
                "artifact": artifact,
            }
        )

    now = timezone.now()
    certificates_by_company: dict[str, Certificate] = {}
    for certificate in (
        Certificate.objects.filter(
            organization=office,
            company__in=scope,
            revoked_at__isnull=True,
            valid_until__gt=now,
        )
        .select_related("company")
        .order_by("company_id", "-valid_until", "-created_at")
    ):
        certificates_by_company.setdefault(str(certificate.company_id), certificate)
    sync_by_company = {
        str(sync.company_id): sync
        for sync in NfseSync.objects.filter(organization=office, company__in=scope).select_related(
            "company", "certificate"
        )
    }
    demo_syncs = get_section(request, "nfse_syncs") if is_demo_visitor(request, office) else {}
    sync_rows: list[dict[str, object]] = []
    sync_search = document_search.casefold()
    for company in scope.order_by("name"):
        haystack = f"{company.name} {company.cnpj_masked} {company.dominio_code}".casefold()
        if sync_search and sync_search not in haystack:
            continue
        certificate = certificates_by_company.get(str(company.id))
        sync = sync_by_company.get(str(company.id))
        demo_state = demo_syncs.get(str(company.id), {})
        effective_status = str(demo_state.get("status", "")) or (sync.status if sync else "")
        sync_rows.append(
            {
                "company": company,
                "certificate": certificate,
                "sync": sync,
                "status": effective_status,
                "status_label": dict(NfseSync.Status.choices).get(
                    effective_status, "Não configurada"
                ),
                "attention": effective_status in {NfseSync.Status.ERROR, NfseSync.Status.RETRY},
            }
        )
        if len(sync_rows) >= 100:
            break

    context.update(
        {
            "page_title": "NFS-e",
            "nfse_view": "collection" if request.GET.get("view") == "collection" else "notes",
            "document_rows": document_rows,
            "document_filtered_total": document_total,
            "document_search": document_search,
            "document_status": document_status,
            "document_date_filter": document_date_filter,
            "document_competence": document_competence,
            "competence_months": list(
                enumerate(
                    [
                        "Janeiro",
                        "Fevereiro",
                        "Março",
                        "Abril",
                        "Maio",
                        "Junho",
                        "Julho",
                        "Agosto",
                        "Setembro",
                        "Outubro",
                        "Novembro",
                        "Dezembro",
                    ],
                    1,
                )
            ),
            "competence_year": document_competence[:4] or str(timezone.localdate().year),
            "date_filter_error": date_filter_error,
            "issued_from": issued_from,
            "issued_to": issued_to,
            "nfse_stats": {
                "received": document_query.count(),
                "pending": ReviewCase.objects.filter(
                    organization=office,
                    status=ReviewCase.Status.OPEN,
                    document__company__in=scope,
                ).count(),
                "classified": document_query.filter(integration_artifacts__isnull=False)
                .distinct()
                .count(),
            },
            "nfse_sync_rows": sync_rows,
            "nfse_sync_enabled": settings.NFSE_ADN_SYNC_ENABLED or office.is_demo,
            "nfse_sync_environment": settings.NFSE_ADN_ENVIRONMENT,
            "nfse_sync_environment_label": (
                "Produção"
                if settings.NFSE_ADN_ENVIRONMENT == "production"
                else "Produção restrita (homologação)"
            ),
            "nfse_sync_configured": sum(bool(sync.enabled) for sync in sync_by_company.values()),
            "nfse_sync_attention": sum(
                sync.status in {NfseSync.Status.ERROR, NfseSync.Status.RETRY}
                for sync in sync_by_company.values()
            ),
            "nfse_certificate_coverage": len(certificates_by_company),
            "can_manage_nfse_sync": can_manage_sync,
        }
    )
    return render(request, "hub/nfse_center.html", context)


def _demo_nfse_download_classifications(
    request: HttpRequest, documents: list[NfseDocument]
) -> dict[str, dict[str, object]]:
    """Build the demo manifest without changing the fiscal document or its review."""

    artifacts = {
        str(artifact.document_id): artifact
        for artifact in IntegrationArtifact.objects.filter(document__in=documents)
    }
    classifications: dict[str, dict[str, object]] = {}
    for document in documents:
        accumulator = request.POST.get(f"accumulator_{document.id}", "").strip()[:80]
        artifact = artifacts.get(str(document.id))
        confidence = int(artifact.confidence) if artifact and artifact.confidence is not None else 0
        if artifact and confidence <= 95:
            confidence = 97
        is_ai_classification = bool(
            artifact and artifact.accumulator_code == accumulator and confidence > 95
        )
        if is_ai_classification:
            classifications[str(document.id)] = {
                "accumulator": accumulator,
                "confidence": confidence,
                "status": "Classificada pela IA",
            }
        elif accumulator:
            classifications[str(document.id)] = {
                "accumulator": accumulator,
                "confidence": 100,
                "status": "Definida pelo contador",
            }
        else:
            classifications[str(document.id)] = {
                "accumulator": "Transitória",
                "confidence": 0,
                "status": "Transitória sem acumulador",
            }
    return classifications


def _nfse_issued_at_from_normalized_data(document: NfseDocument) -> datetime | None:
    """Use the issuance embedded in a legacy payload until the record is reimported."""

    raw_issued_at = document.normalized_data.get("issued_at")
    if not isinstance(raw_issued_at, str):
        return None
    parsed_datetime = parse_datetime(raw_issued_at)
    if parsed_datetime is not None:
        return parsed_datetime
    parsed_date = parse_date(raw_issued_at)
    return datetime.combine(parsed_date, time.min) if parsed_date else None


def _demo_nfse_bulk_download(
    documents: list[NfseDocument], *, folder: str, classifications: dict[str, dict[str, object]]
) -> FileResponse:
    """Return fictitious XML evidence and a non-persistent classification manifest."""

    archive = io.BytesIO()
    with zipfile.ZipFile(archive, mode="w", compression=zipfile.ZIP_DEFLATED) as bundle:
        manifest = io.StringIO(newline="")
        writer = csv.writer(manifest, delimiter=";")
        writer.writerow(
            [
                "Documento",
                "Empresa",
                "Código Domínio",
                "Pasta",
                "Acumulador",
                "Confiança",
                "Situação",
            ]
        )
        for document in documents:
            code = re.sub(r"[^A-Za-z0-9._-]", "_", document.company.dominio_code or "SEM-CODIGO")
            source = re.sub(r"[^A-Za-z0-9._-]", "_", document.source_nsu or str(document.id))
            classification = classifications[str(document.id)]
            bundle.writestr(
                f"{folder}/{code} -/NFS-e-{source}.xml",
                document.original_xml,
            )
            writer.writerow(
                [
                    document.source_nsu or str(document.id),
                    document.company.name,
                    document.company.dominio_code or "",
                    f"{folder}/{code} -",
                    classification["accumulator"],
                    classification["confidence"],
                    classification["status"],
                ]
            )
        bundle.writestr("manifesto-classificacao.csv", manifest.getvalue().encode("utf-8-sig"))
    archive.seek(0)
    response = FileResponse(
        archive,
        as_attachment=True,
        filename=f"nfse-demonstracao-{folder.casefold()}.zip",
        content_type="application/zip",
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _module_page_context(
    request: HttpRequest, module: ModuleDefinition
) -> tuple[dict[str, object], HttpResponse | None]:
    context = workspace_context(request)
    if (
        module.code == ProductModule.Code.AI
        and not copilot_is_available()
        and not (context["office"] and context["office"].is_demo)
    ):
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
        if office.is_demo:
            connected = True
        else:
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


def _demo_guide_for_view(request: HttpRequest, guide: FiscalGuide) -> FiscalGuide:
    """Overlay each visitor's fictitious issuance without modifying seed data."""

    if not is_demo_visitor(request, guide.organization):
        return guide
    entry = get_progress(request, "guides", guide.id)
    guide.status = FiscalGuide.Status.ISSUED if entry.get("issued") else FiscalGuide.Status.READY
    guide.provider_request_id = str(entry.get("protocol", ""))
    issued_at = parse_datetime(str(entry.get("issued_at", "")))
    guide.issued_at = issued_at if entry.get("issued") else None
    guide.issue_requested_at = guide.issued_at
    guide.issue_requested_by = request.user if entry.get("issued") else None
    return guide


@office_required
def guides(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.GUIDES))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    allowed_companies = cast("QuerySet[ClientCompany]", context["companies"])
    today = timezone.localdate()
    guide_query = FiscalGuide.objects.filter(
        organization=office, company__in=allowed_companies
    ).select_related("company")
    guide_search = request.GET.get("q", "").strip()[:100]
    guide_status = request.GET.get("status", "pending")
    if guide_status not in {"all", "pending", "issued", "failed"}:
        guide_status = "pending"
    guide_due = request.GET.get("due", "all")
    if guide_due not in {"all", "7", "overdue"}:
        guide_due = "all"
    filtered_guides = guide_query
    if guide_search:
        filtered_guides = filtered_guides.filter(
            Q(company__name__icontains=guide_search)
            | Q(company__cnpj_masked__icontains=guide_search)
            | Q(company__dominio_code__icontains=guide_search)
            | Q(reference__icontains=guide_search)
            | Q(competence__icontains=guide_search)
        )
    if guide_due == "7":
        filtered_guides = filtered_guides.filter(
            due_on__gte=today, due_on__lte=today + timedelta(days=7)
        )
    elif guide_due == "overdue":
        filtered_guides = filtered_guides.filter(due_on__lt=today)
    if is_demo_visitor(request, office):
        demo_guides = list(filtered_guides.order_by("due_on", "company__name"))
        for guide in demo_guides:
            _demo_guide_for_view(request, guide)
        if guide_status == "pending":
            demo_guides = [
                guide
                for guide in demo_guides
                if guide.status in [FiscalGuide.Status.READY, FiscalGuide.Status.FAILED]
            ]
        elif guide_status != "all":
            demo_guides = [guide for guide in demo_guides if guide.status == guide_status]
        guide_filtered_total = len(demo_guides)
        guide_list = demo_guides[:100]
    else:
        if guide_status == "pending":
            filtered_guides = filtered_guides.filter(
                status__in=[FiscalGuide.Status.READY, FiscalGuide.Status.FAILED]
            )
        elif guide_status != "all":
            filtered_guides = filtered_guides.filter(status=guide_status)
        guide_filtered_total = filtered_guides.count()
        guide_list = list(filtered_guides.order_by("due_on", "company__name")[:100])
    for guide in guide_list:
        guide.amount_brl = Decimal(guide.amount_cents) / 100  # type: ignore[attr-defined]
        guide.usage_quote = None  # type: ignore[attr-defined]
        guide.usage_error = ""  # type: ignore[attr-defined]
        if guide.status in {FiscalGuide.Status.READY, FiscalGuide.Status.FAILED}:
            if office.is_demo:
                guide.usage_quote = SimpleNamespace(  # type: ignore[attr-defined]
                    total_tokens=0,
                    additional_overage_cents=0,
                    additional_overage_tokens=0,
                )
            else:
                try:
                    guide.usage_quote = quote_tokens(  # type: ignore[attr-defined]
                        organization=office,
                        module_code="integra",
                        action_code=guide.integra_service_key,
                    )
                except BillingError as exc:
                    guide.usage_error = str(exc)  # type: ignore[attr-defined]
            if guide.usage_quote is not None:  # type: ignore[attr-defined]
                guide.usage_overage_brl = (  # type: ignore[attr-defined]
                    Decimal(guide.usage_quote.additional_overage_cents) / 100  # type: ignore[attr-defined]
                )
    source_connector = (
        IntelligenceConnector.objects.filter(organization=office)
        .order_by("-last_sync_at", "-created_at")
        .first()
    )
    dominio_calculations: list[dict[str, object]] = []
    dominio_calculation_error = ""
    dominio_calculation_total = 0
    dominio_calculation_companies = 0
    dominio_calculation_amount = Decimal("0")
    calculation_page = None
    if (
        not is_demo_visitor(request, office)
        and source_connector
        and source_connector.mode == IntelligenceConnector.Mode.DIRECT_ODBC
        and source_connector.odbc_dsn
    ):
        company_by_code = {
            company.dominio_code: company for company in allowed_companies if company.dominio_code
        }
        try:
            calculation_rows = ReadOnlyDominoOdbc(source_connector.odbc_dsn).execute(
                "guide_calculations"
            )
            grouped_calculations: dict[tuple[str, str], dict[str, object]] = {}
            for row in calculation_rows:
                company = company_by_code.get(str(row.get("company_code", "")))
                competence = row.get("competence")
                due_on = row.get("due_on")
                amount = row.get("amount")
                if (
                    company is None
                    or not isinstance(competence, date)
                    or not isinstance(due_on, date)
                ):
                    continue
                try:
                    amount_brl = Decimal(str(amount or "0"))
                except InvalidOperation:
                    continue
                competence_label = competence.strftime("%m/%Y")
                key = (str(company.id), competence_label)
                item = grouped_calculations.get(key)
                if item is None:
                    item = {
                        "company": company,
                        "company_code": str(row.get("company_code", "")),
                        "competence": competence,
                        "competence_label": competence_label,
                        "due_on": due_on,
                        "due_on_end": due_on,
                        "amount_brl": Decimal("0"),
                        "component_count": 0,
                        "source_ids": [],
                        "source_codes": set(),
                    }
                    grouped_calculations[key] = item
                item["amount_brl"] = cast(Decimal, item["amount_brl"]) + amount_brl
                item["component_count"] = int(item["component_count"]) + 1
                item["due_on"] = min(cast(date, item["due_on"]), due_on)
                item["due_on_end"] = max(cast(date, item["due_on_end"]), due_on)
                cast(list[str], item["source_ids"]).append(str(row.get("source_id", "")))
                cast(set[tuple[str, str, str]], item["source_codes"]).add(
                    (
                        str(row.get("guide_type_code", "")),
                        str(row.get("process_type_code", "")),
                        str(row.get("status_code", "")),
                    )
                )

            visible_calculations: list[dict[str, object]] = []
            for item in grouped_calculations.values():
                company = cast(ClientCompany, item["company"])
                due_on = cast(date, item["due_on"])
                due_on_end = cast(date, item["due_on_end"])
                haystack = " ".join(
                    [
                        company.name,
                        company.cnpj_masked,
                        company.dominio_code,
                        str(item["competence_label"]),
                        " ".join(cast(list[str], item["source_ids"])),
                    ]
                ).casefold()
                if guide_search and guide_search.casefold() not in haystack:
                    continue
                if guide_due == "7" and not (
                    due_on <= today + timedelta(days=7) and due_on_end >= today
                ):
                    continue
                if guide_due == "overdue" and due_on >= today:
                    continue
                item["source_codes"] = sorted(cast(set[tuple[str, str, str]], item["source_codes"]))
                visible_calculations.append(item)
            visible_calculations.sort(
                key=lambda item: (
                    cast(date, item["competence"]),
                    cast(date, item["due_on"]),
                    cast(ClientCompany, item["company"]).name.casefold(),
                ),
                reverse=True,
            )
            # Calculations are a discovery queue. Official states remain in FiscalGuide.
            if guide_status in {"pending", "all"}:
                dominio_calculation_total = len(visible_calculations)
                dominio_calculation_companies = len(
                    {str(item["company_code"]) for item in visible_calculations}
                )
                dominio_calculation_amount = sum(
                    (cast(Decimal, item["amount_brl"]) for item in visible_calculations),
                    Decimal("0"),
                )
                calculation_page = Paginator(visible_calculations, 30).get_page(
                    request.GET.get("apuracao_pagina")
                )
                dominio_calculations = list(calculation_page.object_list)
        except (RuntimeError, ValueError) as exc:
            dominio_calculation_error = str(exc)
        except Exception:
            logger.exception("Failed to read the governed Domínio guide calculation snapshot")
            dominio_calculation_error = (
                "O Domínio não respondeu à consulta de apurações. Tente novamente."
            )
    pending_statuses = [FiscalGuide.Status.READY, FiscalGuide.Status.FAILED]
    guide_data_available = guide_query.exists()
    if is_demo_visitor(request, office):
        metric_guides = list(guide_query)
        for metric_guide in metric_guides:
            _demo_guide_for_view(request, metric_guide)
        guide_stats = {
            "due_this_week": sum(
                guide.status in pending_statuses and 0 <= (guide.due_on - today).days <= 7
                for guide in metric_guides
            ),
            "pending": sum(guide.status in pending_statuses for guide in metric_guides),
            "issued": sum(guide.status == FiscalGuide.Status.ISSUED for guide in metric_guides),
        }
    else:
        guide_stats = {
            "due_this_week": guide_query.filter(
                status__in=pending_statuses,
                due_on__gte=today,
                due_on__lte=today + timedelta(days=7),
            ).count(),
            "pending": guide_query.filter(status__in=pending_statuses).count(),
            "issued": guide_query.filter(status=FiscalGuide.Status.ISSUED).count(),
        }
    context.update(
        {
            "page_title": "Guias e DCTFWeb",
            "guides": guide_list,
            "guide_data_available": guide_data_available,
            "guide_filtered_total": guide_filtered_total,
            "guide_search": guide_search,
            "guide_status": guide_status,
            "guide_due": guide_due,
            "guide_source_connector": source_connector,
            "dominio_calculations": dominio_calculations,
            "calculation_page": calculation_page,
            "calculation_query": urlencode(
                {"q": guide_search, "status": guide_status, "due": guide_due}
            ),
            "dominio_calculation_error": dominio_calculation_error,
            "dominio_calculation_total": dominio_calculation_total,
            "dominio_calculation_companies": dominio_calculation_companies,
            "dominio_calculation_amount": dominio_calculation_amount,
            "guide_source_company_count": len(allowed_companies),
            "guide_stats": guide_stats,
            "can_issue_guides": _can_prepare_dte(context),
        }
    )
    return render(request, "hub/guides_center.html", context)


def _dominio_dctfweb_calculation(
    *, organization: Organization, company: ClientCompany, competence: str
) -> dict[str, object] | None:
    """Reload one company/competence from the governed ODBC query, never form data."""

    match = re.fullmatch(r"(0[1-9]|1[0-2])/(\d{4})", competence)
    if match is None or not company.dominio_code:
        return None
    connector = (
        IntelligenceConnector.objects.filter(
            organization=organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
        )
        .exclude(odbc_dsn="")
        .order_by("-last_sync_at", "-created_at")
        .first()
    )
    if connector is None:
        return None
    expected = date(int(match.group(2)), int(match.group(1)), 1)
    rows = [
        row
        for row in ReadOnlyDominoOdbc(connector.odbc_dsn).execute("guide_calculations")
        if str(row.get("company_code", "")) == company.dominio_code
        and row.get("competence") == expected
    ]
    if not rows:
        return None
    due_dates = [row.get("due_on") for row in rows if isinstance(row.get("due_on"), date)]
    if not due_dates:
        return None
    amount = Decimal("0")
    source_ids: list[str] = []
    for row in rows:
        try:
            component = Decimal(str(row.get("amount") or "0"))
        except InvalidOperation:
            return None
        if component <= 0 or component.as_tuple().exponent < -2:
            return None
        amount += component
        source_ids.append(str(row.get("source_id", "")))
    if not source_ids or any(not source_id for source_id in source_ids):
        return None
    fingerprint = hashlib.sha256("|".join(sorted(source_ids)).encode()).hexdigest()
    return {
        "amount_brl": amount,
        "amount_cents": int(amount * 100),
        "due_on": min(cast(list[date], due_dates)),
        "due_on_end": max(cast(list[date], due_dates)),
        "component_count": len(rows),
        "source_reference": f"fovguiainss:{fingerprint}",
    }


@office_required
@require_http_methods(["GET", "POST"])
def dctfweb_consult(request: HttpRequest) -> HttpResponse:
    """Quote and explicitly authorize one declaration or receipt consultation."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.GUIDES))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    allowed_companies = cast("QuerySet[ClientCompany]", context["companies"])
    company_id = request.POST.get("company") or request.GET.get("company", "")
    competence = (request.POST.get("competence") or request.GET.get("competence", "")).strip()
    try:
        company_id = uuid.UUID(company_id)
    except (ValueError, TypeError):
        messages.error(request, "Escolha uma empresa e uma competência na carteira.")
        return redirect("hub:guides")
    company = get_object_or_404(
        allowed_companies,
        id=company_id,
        organization=office,
        active=True,
    )
    try:
        dominio_calculation = (
            None
            if office.is_demo
            else _dominio_dctfweb_calculation(
                organization=office,
                company=company,
                competence=competence,
            )
        )
    except (RuntimeError, ValueError):
        dominio_calculation = None
    if request.method == "POST":
        if not _can_prepare_dte(context):
            return refuse(
                request, "Seu perfil pode consultar resultados, mas não autorizar consumo."
            )
        if request.POST.get("action") == "prepare_guide":
            if dominio_calculation is None:
                messages.error(
                    request,
                    "A apuração não foi encontrada novamente no Domínio. Atualize a origem antes "
                    "de preparar a emissão.",
                )
            else:
                try:
                    guide = prepare_dctfweb_guide_from_documents(
                        organization=office,
                        company=company,
                        competence=competence,
                        due_on=cast(date, dominio_calculation["due_on"]),
                        amount_cents=int(dominio_calculation["amount_cents"]),
                        source_reference=str(dominio_calculation["source_reference"]),
                        actor=request.user,
                        request=request,
                    )
                except DctfWebDocumentTransitionError as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(
                        request,
                        "Competência conferida e preparada para a emissão oficial.",
                    )
                    return detail_redirect(request, "hub:guide-detail", guide_id=guide.id)
            target = reverse("hub:dctfweb-consult")
            return redirect(
                f"{target}?{urlencode({'company': company.id, 'competence': competence})}"
            )
        kind = request.POST.get("kind", "")
        try:
            service_key = DCTFWEB_DOCUMENT_SERVICE.get(kind)
            if service_key is None:
                raise DctfWebDocumentTransitionError("Escolha declaração completa ou recibo.")
            quote = (
                SimpleNamespace(additional_overage_cents=0)
                if office.is_demo
                else quote_tokens(
                    organization=office,
                    module_code="integra",
                    action_code=service_key,
                )
            )
            approved_cents = int(request.POST.get("approved_overage_cents", "0"))
            if approved_cents != quote.additional_overage_cents:
                raise DctfWebDocumentTransitionError(
                    "O custo mudou desde a abertura da tela. Revise e confirme novamente."
                )
            document = request_dctfweb_document(
                organization=office,
                company=company,
                competence=competence,
                kind=kind,
                actor=request.user,
                request=request,
                approved_overage_cents=approved_cents,
            )
        except (BillingError, DctfWebDocumentTransitionError, ValueError) as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Consulta autorizada e adicionada à fila da central.")
            target = reverse("hub:dctfweb-consult")
            return redirect(
                f"{target}?{urlencode({'company': company.id, 'competence': competence})}"
            )

    cards: list[dict[str, object]] = []
    for kind, service_key in DCTFWEB_DOCUMENT_SERVICE.items():
        quote: TokenQuote | SimpleNamespace | None = None
        error = ""
        if office.is_demo:
            quote = SimpleNamespace(
                included_remaining=0,
                tokens_per_operation=0,
                total_tokens=0,
                additional_overage_tokens=0,
                additional_overage_cents=0,
                token_price_cents=0,
            )
        else:
            try:
                quote = quote_tokens(
                    organization=office,
                    module_code="integra",
                    action_code=service_key,
                )
            except BillingError as exc:
                error = str(exc)
        document = DctfWebDocument.objects.filter(
            organization=office,
            company=company,
            competence=competence,
            kind=kind,
        ).first()
        cards.append(
            {
                "kind": kind,
                "label": DctfWebDocument.Kind(kind).label,
                "service_key": service_key,
                "quote": quote,
                "additional_overage_brl": (
                    Decimal(quote.additional_overage_cents) / 100 if quote else None
                ),
                "token_price_brl": (Decimal(quote.token_price_cents) / 100 if quote else None),
                "error": error,
                "document": document,
            }
        )
    context.update(
        {
            "page_title": "Consultar DCTFWeb",
            "consult_company": company,
            "consult_competence": competence,
            "consult_cards": cards,
            "can_authorize": _can_prepare_dte(context),
            "dominio_calculation": dominio_calculation,
            "dctfweb_documents_ready": all(
                any(
                    card["kind"] == required_kind
                    and card["document"] is not None
                    and card["document"].status == DctfWebDocument.Status.AVAILABLE
                    for card in cards
                )
                for required_kind in (
                    DctfWebDocument.Kind.DECLARATION,
                    DctfWebDocument.Kind.RECEIPT,
                )
            ),
            "prepared_guide": FiscalGuide.objects.filter(
                organization=office,
                company=company,
                competence=competence,
                kind=FiscalGuide.Kind.DCTFWEB,
                status__in=[
                    FiscalGuide.Status.READY,
                    FiscalGuide.Status.QUEUED,
                    FiscalGuide.Status.ISSUING,
                    FiscalGuide.Status.ISSUED,
                    FiscalGuide.Status.FAILED,
                ],
            ).first(),
        }
    )
    return render(request, "hub/dctfweb_consult.html", context)


def _dctfweb_bulk_targets(
    *, raw_targets: list[str], companies: QuerySet[ClientCompany]
) -> list[tuple[ClientCompany, str]]:
    """Validate and deduplicate a bounded set selected from the visible work queue."""

    if not raw_targets:
        raise DctfWebDocumentTransitionError("Selecione ao menos uma apuração da carteira.")
    if len(raw_targets) > 30:
        raise DctfWebDocumentTransitionError(
            "Esta etapa aceita até 30 empresas por vez. Refine os filtros e tente novamente."
        )
    parsed: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for raw in raw_targets:
        company_id, separator, competence = raw.partition("|")
        key = (company_id, competence)
        try:
            uuid.UUID(company_id)
        except ValueError as exc:
            raise DctfWebDocumentTransitionError("Uma seleção da carteira ficou inválida.") from exc
        if not separator or re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", competence) is None:
            raise DctfWebDocumentTransitionError("Uma seleção da carteira ficou inválida.")
        if key not in seen:
            seen.add(key)
            parsed.append(key)
    company_map = {
        str(company.id): company
        for company in companies.filter(id__in=[company_id for company_id, _ in parsed])
    }
    if len(company_map) != len({company_id for company_id, _ in parsed}):
        raise DctfWebDocumentTransitionError("Uma empresa selecionada não pertence ao seu acesso.")
    return [(company_map[company_id], competence) for company_id, competence in parsed]


@office_required
@require_http_methods(["POST"])
def dctfweb_bulk_consult(request: HttpRequest) -> HttpResponse:
    """Preview and authorize one bounded DCTFWeb operation for many companies."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.GUIDES))
    if blocked:
        return blocked
    if not _can_prepare_dte(context):
        return refuse(request, "Seu perfil pode consultar resultados, mas não autorizar consumo.")
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    kind = request.POST.get("kind", "")
    service_key = DCTFWEB_DOCUMENT_SERVICE.get(kind)
    if service_key is None:
        messages.error(request, "Escolha declaração completa ou recibo de transmissão.")
        return redirect("hub:guides")
    try:
        targets = _dctfweb_bulk_targets(
            raw_targets=request.POST.getlist("targets"), companies=companies
        )
    except DctfWebDocumentTransitionError as exc:
        messages.error(request, str(exc))
        return redirect("hub:guides")

    quote: TokenQuote | SimpleNamespace | None
    quote_error = ""
    if office.is_demo:
        quote = SimpleNamespace(
            total_tokens=0,
            tokens_per_operation=0,
            additional_overage_tokens=0,
            additional_overage_cents=0,
            included_remaining=0,
        )
    else:
        try:
            quote = quote_tokens(
                organization=office,
                module_code="integra",
                action_code=service_key,
                operations=len(targets),
            )
        except BillingError as exc:
            quote = None
            quote_error = str(exc)

    if request.POST.get("step") == "confirm":
        if quote is None:
            messages.error(request, quote_error or "Não foi possível cotar esta consulta.")
            return redirect("hub:guides")
        try:
            submitted_cents = int(request.POST.get("approved_overage_cents", "-1"))
        except ValueError:
            submitted_cents = -1
        if submitted_cents != quote.additional_overage_cents:
            messages.error(request, "O consumo mudou. Revise a seleção e confirme novamente.")
        elif is_demo_visitor(request, office):
            for company, competence in targets:
                put_progress(
                    request,
                    "dctfweb_bulk",
                    f"{kind}:{company.id}:{competence}",
                    {"completed": True, "completed_at": timezone.now().isoformat()},
                )
            messages.success(
                request,
                f"{len(targets)} consultas fictícias concluídas somente nesta sessão.",
            )
            return redirect("hub:guides")
        else:
            try:
                with transaction.atomic():
                    for company, competence in targets:
                        current_quote = (
                            SimpleNamespace(additional_overage_cents=0)
                            if office.is_demo
                            else quote_tokens(
                                organization=office,
                                module_code="integra",
                                action_code=service_key,
                            )
                        )
                        request_dctfweb_document(
                            organization=office,
                            company=company,
                            competence=competence,
                            kind=kind,
                            actor=request.user,
                            request=request,
                            approved_overage_cents=current_quote.additional_overage_cents,
                        )
            except (BillingError, DctfWebDocumentTransitionError) as exc:
                messages.error(request, f"O lote não foi enviado: {exc}")
            else:
                messages.success(
                    request,
                    f"{len(targets)} consultas autorizadas e adicionadas à fila da central.",
                )
                return redirect("hub:guides")

    context.update(
        {
            "page_title": "Confirmar consultas DCTFWeb",
            "bulk_targets": targets,
            "bulk_kind": kind,
            "bulk_kind_label": DctfWebDocument.Kind(kind).label,
            "bulk_quote": quote,
            "bulk_quote_error": quote_error,
            "bulk_overage_brl": (Decimal(quote.additional_overage_cents) / 100 if quote else None),
        }
    )
    return render(request, "hub/dctfweb_bulk.html", context)


@office_required
@require_http_methods(["GET"])
def dctfweb_document_pdf(request: HttpRequest, document_id: str) -> HttpResponse:
    """Download a persisted DCTFWeb result without another supplier call."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.GUIDES))
    if blocked:
        raise Http404
    office = cast(Organization, context["office"])
    document = get_object_or_404(
        DctfWebDocument.objects.select_related("company"),
        id=document_id,
        organization=office,
        company__in=context["companies"],
        status=DctfWebDocument.Status.AVAILABLE,
    )
    try:
        payload = json.loads(document.provider_payload)
        if not isinstance(payload, dict):
            raise ValueError
        content = extract_pdf(payload)
    except (TypeError, ValueError, json.JSONDecodeError, IntegraError) as exc:
        raise Http404 from exc
    response = HttpResponse(content, content_type="application/pdf")
    slug = "declaracao" if document.kind == DctfWebDocument.Kind.DECLARATION else "recibo"
    response["Content-Disposition"] = (
        f'attachment; filename="dctfweb-{slug}-{document.competence.replace("/", "-")}.pdf"'
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    record_event(
        action="hub.dctfweb.document_downloaded",
        actor=cast(User, request.user),
        organization=office,
        target=document,
        request=request,
    )
    return response


@office_required
@require_http_methods(["GET"])
def guide_detail(request: HttpRequest, guide_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.GUIDES))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    guide = get_object_or_404(
        FiscalGuide.objects.select_related("company", "issue_requested_by"),
        id=guide_id,
        organization=office,
        company__in=context["companies"],
    )
    _demo_guide_for_view(request, guide)
    context.update(
        {
            "page_title": "Resultado da guia",
            "guide": guide,
            "guide_amount_brl": Decimal(guide.amount_cents) / 100,
        }
    )
    return render(request, "hub/guide_detail.html", context)


@office_required
@require_http_methods(["GET"])
def demo_guide_pdf(request: HttpRequest, guide_id: str) -> HttpResponse:
    """Give the demo an unmistakably non-official PDF; never proxy a real guide."""

    from io import BytesIO

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    context, blocked = _module_page_context(request, definition(ProductModule.Code.GUIDES))
    if blocked:
        raise Http404
    office = cast(Organization, context["office"])
    if not office.is_demo:
        raise Http404
    guide = get_object_or_404(
        FiscalGuide.objects.select_related("company"),
        id=guide_id,
        organization=office,
        company__in=context["companies"],
    )
    _demo_guide_for_view(request, guide)
    if guide.status != FiscalGuide.Status.ISSUED:
        raise Http404
    buffer = BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    page.setTitle("Exemplo fictício de guia DCTFWeb - sem validade")
    page.setFont("Helvetica-Bold", 19)
    page.drawString(48, 790, "DEMONSTRACAO FICTICIA")
    page.setFont("Helvetica-Bold", 12)
    page.drawString(48, 760, "SEM VALIDADE FISCAL OU BANCARIA")
    page.setFont("Helvetica", 11)
    page.drawString(48, 710, f"Empresa: {guide.company.name[:70]}")
    page.drawString(48, 685, f"Competencia: {guide.competence}")
    page.drawString(48, 660, f"Valor de exemplo: R$ {guide.amount_cents / 100:.2f}")
    page.drawString(48, 635, f"Registro local: {guide.provider_request_id}")
    page.drawString(48, 595, "Nenhuma declaracao foi consultada ou guia emitida no Serpro.")
    page.drawString(48, 575, "Este PDF existe somente para demonstrar a tarefa no sistema CICA.")
    page.save()
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="exemplo-guia-{guide.id}.pdf"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    record_event(
        action="hub.guide.demo_pdf_downloaded",
        actor=cast(User, request.user),
        organization=office,
        target=guide,
        request=request,
    )
    return response


@office_required
@require_http_methods(["GET"])
def guide_pdf(request: HttpRequest, guide_id: str) -> HttpResponse:
    """Download the already-issued official DARF without another billable call."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.GUIDES))
    if blocked:
        raise Http404
    office = cast(Organization, context["office"])
    if office.is_demo:
        raise Http404
    guide = get_object_or_404(
        FiscalGuide.objects.select_related("company"),
        id=guide_id,
        organization=office,
        company__in=context["companies"],
        status=FiscalGuide.Status.ISSUED,
    )
    try:
        payload = json.loads(guide.provider_payload)
        if not isinstance(payload, dict):
            raise ValueError
        document = extract_pdf(payload)
    except (TypeError, ValueError, json.JSONDecodeError, IntegraError) as exc:
        logger.warning("Issued DCTFWeb guide has no valid PDF", extra={"guide_id": str(guide.id)})
        raise Http404 from exc
    response = HttpResponse(document, content_type="application/pdf")
    competence = guide.competence.replace("/", "-")
    response["Content-Disposition"] = f'attachment; filename="darf-dctfweb-{competence}.pdf"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    record_event(
        action="hub.guide.pdf_downloaded",
        actor=cast(User, request.user),
        organization=office,
        target=guide,
        request=request,
        metadata={"provider_request_id": guide.provider_request_id},
    )
    return response


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
    if is_demo_visitor(request, office):
        if not guide.reference.startswith("DEMO-"):
            raise Http404
        if get_progress(request, "guides", guide.id).get("issued"):
            messages.info(request, "Esta guia fictícia já foi emitida nesta sessão.")
        else:
            put_progress(
                request,
                "guides",
                guide.id,
                {
                    "issued": True,
                    "protocol": f"DEMO-{str(guide.id)[:12]}",
                    "issued_at": timezone.now().isoformat(),
                },
            )
            messages.success(request, "Resultado fictício da guia gerado nesta sessão.")
        return detail_redirect(request, "hub:guide-detail", guide_id=guide.id)
    try:
        approved_overage_cents = int(request.POST.get("approved_overage_cents", "0"))
        issue_fiscal_guide(
            guide=guide,
            actor=request.user,
            request=request,
            approved_overage_cents=approved_overage_cents,
        )
    except (FiscalGuideTransitionError, ValueError) as error:
        messages.error(request, str(error))
    else:
        messages.success(
            request,
            "Resultado fictício da guia gerado sem fornecedor externo."
            if office.is_demo
            else "Emissão autorizada. A guia entrou na fila da central.",
        )
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
            "integra_pending_count": (
                sum(
                    entry.get("status") == "prepared"
                    for entry in get_section(request, "dte_runs").values()
                )
                if is_demo_visitor(request, office)
                else DteRun.objects.filter(
                    organization=office, status=DteRun.Status.AWAITING_APPROVAL
                ).count()
            ),
            "integra_guides_enabled": ProductModule.objects.filter(
                organization=office, code=ProductModule.Code.GUIDES, enabled=True
            ).exists(),
        }
    )
    return render(request, "hub/integra_home.html", context)


def _demo_parcelamentos(company: ClientCompany) -> list[SimpleNamespace]:
    """Stable synthetic agreements for the shared demo, never provider evidence."""

    seed = int(hashlib.sha256(str(company.id).encode()).hexdigest()[:8], 16)
    current_month = timezone.localdate().replace(day=1)
    previous_month = (current_month - timedelta(days=1)).replace(day=1)
    agreement = 410000 + seed % 80000
    return [
        SimpleNamespace(
            number=agreement,
            modality="Parcelamento ordinário do Simples Nacional",
            status="Ativo",
            consolidated_on=current_month - timedelta(days=96),
            consolidated_brl=Decimal(780000 + seed % 540000) / 100,
            paid_count=5,
            installments=[
                SimpleNamespace(
                    competence=previous_month.strftime("%m/%Y"),
                    competence_key=previous_month.strftime("%Y%m"),
                    due_on=previous_month + timedelta(days=45),
                    amount_brl=Decimal(18400 + seed % 3600) / 100,
                    paid=True,
                ),
                SimpleNamespace(
                    competence=current_month.strftime("%m/%Y"),
                    competence_key=current_month.strftime("%Y%m"),
                    due_on=current_month + timedelta(days=19),
                    amount_brl=Decimal(18700 + seed % 3600) / 100,
                    paid=False,
                ),
            ],
        )
    ]


@office_required
@require_http_methods(["GET", "POST"])
def parcelamentos(request: HttpRequest) -> HttpResponse:
    """Searchable PARCSN workspace with quoted, explicit provider actions."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.INTEGRA))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    all_companies = cast("QuerySet[ClientCompany]", context["companies"]).filter(active=True)
    search = (request.POST.get("search") or request.GET.get("search", "")).strip()[:120]
    companies = all_companies
    if search:
        companies = companies.filter(
            Q(name__icontains=search)
            | Q(dominio_code__icontains=search)
            | Q(cnpj_masked__icontains=search)
        )
    company_id = (request.POST.get("company") or request.GET.get("company", "")).strip()
    try:
        company = companies.filter(id=uuid.UUID(company_id)).first() if company_id else None
    except ValueError:
        messages.error(request, "Selecione uma empresa válida.")
        return redirect("hub:parcelamentos")
    visitor = is_demo_visitor(request, office)

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "consult_selected":
            selected_ids = list(dict.fromkeys(request.POST.getlist("selected_company")))
            if not selected_ids:
                messages.error(request, "Marque ao menos uma empresa para consultar.")
                return redirect("hub:parcelamentos")
            if len(selected_ids) > 30:
                messages.error(request, "Consulte no máximo 30 empresas por lote.")
                return redirect("hub:parcelamentos")
            try:
                selected_ids = [uuid.UUID(value) for value in selected_ids]
            except ValueError:
                messages.error(request, "Selecione empresas válidas e tente novamente.")
                return redirect("hub:parcelamentos")
            selected = list(all_companies.filter(id__in=selected_ids).order_by("name"))
            if len(selected) != len(selected_ids):
                return refuse(request, "Uma empresa selecionada não pertence ao seu escopo.")
            if visitor:
                for selected_company in selected:
                    put_progress(
                        request,
                        "parcelamento_consultations",
                        selected_company.id,
                        {"consulted_at": timezone.now().isoformat()},
                    )
                messages.success(request, f"{len(selected)} consulta(s) fictícia(s) concluída(s).")
                return redirect("hub:parcelamentos")
            if not _can_prepare_dte(context):
                return refuse(
                    request, "Seu perfil pode consultar resultados, mas não autorizar consumo."
                )
            try:
                submitted = int(request.POST.get("approved_overage_cents", "-1"))
                service_key = PARCELAMENTO_SERVICE[ParcelamentoOperation.Kind.ORDERS]
                quote = quote_tokens(
                    organization=office,
                    module_code="integra",
                    action_code=service_key,
                    operations=len(selected),
                )
                if submitted != quote.additional_overage_cents:
                    raise ParcelamentoTransitionError(
                        "O custo do lote mudou. Revise a seleção e confirme novamente."
                    )
                with transaction.atomic():
                    for selected_company in selected:
                        one_quote = quote_tokens(
                            organization=office,
                            module_code="integra",
                            action_code=service_key,
                        )
                        request_parcelamento_operation(
                            organization=office,
                            company=selected_company,
                            kind=ParcelamentoOperation.Kind.ORDERS,
                            actor=request.user,
                            request=request,
                            approved_overage_cents=one_quote.additional_overage_cents,
                        )
            except (BillingError, ParcelamentoTransitionError, ValueError) as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, f"{len(selected)} consulta(s) adicionada(s) à fila.")
            return redirect("hub:parcelamentos")

        if company is None:
            messages.error(request, "Escolha uma empresa do seu escopo para continuar.")
            return redirect("hub:parcelamentos")
        if visitor and action == "consult":
            put_progress(
                request,
                "parcelamento_consultations",
                company.id,
                {"consulted_at": timezone.now().isoformat()},
            )
            messages.success(
                request,
                "Consulta fictícia concluída. Nenhum dado foi enviado ao Serpro e nenhum token "
                "foi consumido.",
            )
        elif visitor and action == "issue":
            agreement = request.POST.get("agreement", "")
            competence = request.POST.get("competence", "")
            available = {
                (str(item.number), installment.competence_key)
                for item in _demo_parcelamentos(company)
                for installment in item.installments
                if not installment.paid
            }
            if (agreement, competence) not in available:
                messages.error(request, "A parcela escolhida não está disponível para emissão.")
            else:
                key = f"{company.id}:{agreement}:{competence}"
                put_progress(
                    request,
                    "parcelamento_guides",
                    key,
                    {
                        "issued_at": timezone.now().isoformat(),
                        "protocol": f"DEMO-PARC-{secrets.token_hex(4).upper()}",
                    },
                )
                messages.success(
                    request,
                    "DAS fictício emitido para a demonstração, sem chamada externa ou cobrança.",
                )
        elif not visitor and action in {"consult", "detail", "installments", "issue"}:
            if not _can_prepare_dte(context):
                return refuse(
                    request, "Seu perfil pode consultar resultados, mas não autorizar consumo."
                )
            kind = {
                "consult": ParcelamentoOperation.Kind.ORDERS,
                "detail": ParcelamentoOperation.Kind.DETAIL,
                "installments": ParcelamentoOperation.Kind.INSTALLMENTS,
                "issue": ParcelamentoOperation.Kind.DAS,
            }[action]
            try:
                agreement_number = (
                    int(request.POST.get("agreement", ""))
                    if kind == ParcelamentoOperation.Kind.DETAIL
                    else None
                )
                competence = (
                    request.POST.get("competence", "").strip()
                    if kind == ParcelamentoOperation.Kind.DAS
                    else ""
                )
                quote = quote_tokens(
                    organization=office,
                    module_code="integra",
                    action_code=PARCELAMENTO_SERVICE[kind],
                )
                approved = int(request.POST.get("approved_overage_cents", "-1"))
                if approved != quote.additional_overage_cents:
                    raise ParcelamentoTransitionError(
                        "O custo mudou desde a abertura da tela. Revise e confirme novamente."
                    )
                request_parcelamento_operation(
                    organization=office,
                    company=company,
                    kind=kind,
                    agreement_number=agreement_number,
                    competence=competence,
                    actor=request.user,
                    request=request,
                    approved_overage_cents=approved,
                )
            except (BillingError, ParcelamentoTransitionError, ValueError) as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, "Operação autorizada e adicionada à fila da central.")
        else:
            messages.error(request, "Ação de parcelamento inválida.")
        return redirect(f"{reverse('hub:parcelamentos')}?company={company.id}")

    agreements: list[SimpleNamespace] = []
    consultation = (
        get_progress(request, "parcelamento_consultations", company.id) if company else {}
    )
    if visitor and company and consultation:
        agreements = _demo_parcelamentos(company)
        guide_progress = get_section(request, "parcelamento_guides")
        for agreement in agreements:
            for installment in agreement.installments:
                key = f"{company.id}:{agreement.number}:{installment.competence_key}"
                issued = guide_progress.get(key, {})
                installment.issued = bool(issued)
                installment.protocol = str(issued.get("protocol", ""))

    operations = ParcelamentoOperation.objects.filter(organization=office).select_related(
        "company", "token_usage_event"
    )
    latest_by_company: dict[str, ParcelamentoOperation] = {}
    for operation in operations.filter(kind=ParcelamentoOperation.Kind.ORDERS).order_by(
        "company_id", "-requested_at"
    ):
        latest_by_company.setdefault(str(operation.company_id), operation)

    available_installments: list[SimpleNamespace] = []
    if not visitor and company:
        order_result = operations.filter(
            company=company,
            kind=ParcelamentoOperation.Kind.ORDERS,
            status=ParcelamentoOperation.Status.AVAILABLE,
        ).first()
        if order_result and order_result.provider_payload:
            try:
                summaries = pedidos(json.loads(order_result.provider_payload))
            except (ValueError, TypeError, json.JSONDecodeError):
                summaries = []
            agreements = [
                SimpleNamespace(
                    number=item.numero,
                    status=item.situacao,
                    requested_on=item.data_pedido,
                    status_on=item.data_situacao,
                    detail_operation=operations.filter(
                        company=company,
                        kind=ParcelamentoOperation.Kind.DETAIL,
                        agreement_number=item.numero,
                    ).first(),
                )
                for item in summaries
            ]
            for agreement in agreements:
                agreement.detail = None
                detail_operation = agreement.detail_operation
                if (
                    detail_operation
                    and detail_operation.status == ParcelamentoOperation.Status.AVAILABLE
                    and detail_operation.provider_payload
                ):
                    try:
                        agreement.detail = detalhe(
                            json.loads(detail_operation.provider_payload),
                            numero_esperado=agreement.number,
                        )
                    except (ValueError, TypeError, json.JSONDecodeError):
                        agreement.detail = None
        installment_result = operations.filter(
            company=company,
            kind=ParcelamentoOperation.Kind.INSTALLMENTS,
            status=ParcelamentoOperation.Status.AVAILABLE,
        ).first()
        if installment_result and installment_result.provider_payload:
            try:
                parsed_installments = parcelas_disponiveis(
                    json.loads(installment_result.provider_payload)
                )
            except (ValueError, TypeError, json.JSONDecodeError):
                parsed_installments = []
            for item in parsed_installments:
                das_operation = operations.filter(
                    company=company,
                    kind=ParcelamentoOperation.Kind.DAS,
                    competence=str(item.ano_mes),
                ).first()
                available_installments.append(
                    SimpleNamespace(
                        competence=str(item.ano_mes),
                        competence_label=f"{str(item.ano_mes)[4:]}/{str(item.ano_mes)[:4]}",
                        amount=item.valor,
                        operation=das_operation,
                    )
                )

    portfolio = list(companies.order_by("name")[:100])
    for portfolio_company in portfolio:
        portfolio_company.parcelamento_operation = latest_by_company.get(  # type: ignore[attr-defined]
            str(portfolio_company.id)
        )
    orders_quote: TokenQuote | SimpleNamespace | None = None
    quote_error = ""
    if visitor:
        orders_quote = SimpleNamespace(total_tokens=0, additional_overage_cents=0)
    else:
        try:
            orders_quote = quote_tokens(
                organization=office,
                module_code="integra",
                action_code=PARCELAMENTO_SERVICE[ParcelamentoOperation.Kind.ORDERS],
            )
        except BillingError as exc:
            quote_error = str(exc)
    operation_quotes: dict[str, TokenQuote | SimpleNamespace] = {}
    if visitor:
        for kind in PARCELAMENTO_SERVICE:
            operation_quotes[kind] = SimpleNamespace(total_tokens=0, additional_overage_cents=0)
    else:
        for kind, service_key in PARCELAMENTO_SERVICE.items():
            try:
                operation_quotes[kind] = quote_tokens(
                    organization=office,
                    module_code="integra",
                    action_code=service_key,
                )
            except BillingError:
                continue

    context.update(
        {
            "page_title": "Parcelamentos",
            "parcelamento_companies": companies.order_by("name"),
            "parcelamento_portfolio": portfolio,
            "parcelamento_search": search,
            "parcelamento_company": company,
            "parcelamento_consultation": consultation,
            "parcelamento_agreements": agreements,
            "parcelamento_demo": visitor,
            "parcelamento_orders_quote": orders_quote,
            "parcelamento_quote_error": quote_error,
            "parcelamento_operations": operations.filter(company=company)[:20] if company else [],
            "parcelamento_available_installments": available_installments,
            "parcelamento_operation_quotes": operation_quotes,
            "parcelamento_detail_quote": operation_quotes.get(ParcelamentoOperation.Kind.DETAIL),
            "parcelamento_installments_quote": operation_quotes.get(
                ParcelamentoOperation.Kind.INSTALLMENTS
            ),
            "parcelamento_das_quote": operation_quotes.get(ParcelamentoOperation.Kind.DAS),
            "can_authorize": _can_prepare_dte(context),
        }
    )
    return render(request, "hub/parcelamentos.html", context)


@office_required
def parcelamento_das_pdf(request: HttpRequest, operation_id: uuid.UUID) -> HttpResponse:
    """Download a previously issued DAS without another paid provider call."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.INTEGRA))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    operation = get_object_or_404(
        ParcelamentoOperation,
        id=operation_id,
        organization=office,
        kind=ParcelamentoOperation.Kind.DAS,
        status=ParcelamentoOperation.Status.AVAILABLE,
    )
    try:
        document = pdf_das(json.loads(operation.provider_payload))
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise Http404("O DAS armazenado não está disponível.") from exc
    record_event(
        action="hub.parcelamento.das_downloaded",
        actor=request.user,
        organization=office,
        target=operation,
        request=request,
    )
    response = FileResponse(
        io.BytesIO(document),
        content_type="application/pdf",
        filename=f"DAS-{operation.company.dominio_code}-{operation.competence}.pdf",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


class _DemoDteItems:
    def __init__(self, companies: list[ClientCompany]) -> None:
        self.companies = companies

    def all(self) -> list[SimpleNamespace]:
        return [SimpleNamespace(company=company) for company in self.companies]


def _demo_dte_runs_for_view(
    request: HttpRequest, companies: QuerySet[ClientCompany], office: Organization
) -> tuple[list[SimpleNamespace], list[SimpleNamespace]]:
    """Build the DTE work queue from session progress, never from shared seed runs."""

    allowed = {str(company.id): company for company in companies}
    pending: list[SimpleNamespace] = []
    results: list[SimpleNamespace] = []
    for run_id, entry in get_section(request, "dte_runs").items():
        selected = [allowed[code] for code in entry.get("company_ids", []) if code in allowed]
        if not selected:
            continue
        run = SimpleNamespace(
            id=run_id,
            total_companies=len(selected),
            requested_at=parse_datetime(str(entry.get("requested_at", ""))) or timezone.now(),
            requested_by=request.user,
            usage_quote=UsageQuote(len(selected), len(selected), 0, 0),
            overage_brl=Decimal(0),
            items=_DemoDteItems(selected),
        )
        if entry.get("status") == "prepared":
            pending.append(run)
        elif entry.get("status") == "completed":
            for company in selected:
                found = DteMessage.objects.filter(organization=office, company=company).count()
                results.append(
                    SimpleNamespace(
                        company=company,
                        run=run,
                        status="completed",
                        get_status_display=lambda: "Consulta fictícia concluída",
                        error_message="",
                        more_available=False,
                        requested_page_pointer="",
                        messages_found=found,
                    )
                )
    pending.sort(key=lambda run: run.requested_at, reverse=True)
    results.sort(key=lambda item: item.run.requested_at, reverse=True)
    return pending, results


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
    visitor = is_demo_visitor(request, office)

    if request.method == "POST":
        if not context["support_can_mutate"]:
            return refuse(request, "Esta sessão é somente leitura.")
        if not _can_prepare_dte(context):
            return refuse(request, "Seu perfil pode consultar, mas não preparar consultas DTE.")
        if form.is_valid():
            if visitor:
                selected = list(form.cleaned_data["companies"])
                run_id = str(uuid.uuid4())
                put_progress(
                    request,
                    "dte_runs",
                    run_id,
                    {
                        "company_ids": [str(company.id) for company in selected],
                        "status": "prepared",
                        "requested_at": timezone.now().isoformat(),
                    },
                )
                messages.success(
                    request,
                    f"Consulta fictícia preparada para {len(selected)} "
                    f"{'empresa' if len(selected) == 1 else 'empresas'} nesta sessão.",
                )
                return redirect("hub:dte-center")
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

    if visitor:
        pending_runs, items = _demo_dte_runs_for_view(request, companies, office)
    else:
        items = (
            DteRunItem.objects.filter(organization=office, company_id__in=allowed_company_ids)
            .select_related("company", "run", "run__requested_by", "continuation")
            .order_by("-run__requested_at", "company__name")[:30]
        )
    message_filter = request.GET.get("status", "all")
    if message_filter not in {"all", "unread", "read", "uncertain"}:
        message_filter = "all"
    company_filter = request.GET.get("company", "")
    try:
        selected_company = (
            companies.filter(id=uuid.UUID(company_filter)).first() if company_filter else None
        )
    except ValueError:
        selected_company = None
    message_query = (
        DteMessage.objects.filter(organization=office, company_id__in=allowed_company_ids)
        .select_related("company", "access_receipt", "current_state")
        .annotate(
            display_read_at=Coalesce("current_state__read_at", "read_at"),
            display_science_at=Coalesce("current_state__science_at", "source_science_at"),
        )
    )
    search_term = request.GET.get("q", "").strip()[:100]
    if visitor:
        demo_messages = list(message_query.order_by("-sent_at", "-first_seen_at"))
        for message in demo_messages:
            opened = bool(get_progress(request, "dte_messages", message.id).get("opened"))
            message.access_receipt = DteMessageAccess(
                organization=office,
                message=message,
                status=DteMessageAccess.Status.OPENED if opened else "",
            )
            message.display_read_at = (
                None
                if message.source_isn.endswith("-0")
                else message.sent_at + timedelta(hours=5)
                if message.sent_at
                else None
            )
            message.display_science_at = None
        visitor_unread = sum(
            not message.display_read_at and message.access_receipt.status != "opened"
            for message in demo_messages
        )
        filtered_messages = [
            message
            for message in demo_messages
            if (not selected_company or message.company_id == selected_company.id)
            and (
                not search_term
                or search_term.casefold() in message.subject.casefold()
                or search_term.casefold() in message.sender.casefold()
            )
            and (
                message_filter == "all"
                or (
                    message_filter == "unread"
                    and not message.display_read_at
                    and message.access_receipt.status != "opened"
                )
                or (
                    message_filter == "read"
                    and (bool(message.display_read_at) or message.access_receipt.status == "opened")
                )
            )
        ]
        message_page = Paginator(filtered_messages, 25).get_page(request.GET.get("page"))
    else:
        if selected_company:
            message_query = message_query.filter(company=selected_company)
        if search_term:
            message_query = message_query.filter(
                Q(subject__icontains=search_term) | Q(sender__icontains=search_term)
            )
        if message_filter == "unread":
            message_query = message_query.filter(
                display_read_at__isnull=True, display_science_at__isnull=True
            ).exclude(
                access_receipt__status__in=(
                    DteMessageAccess.Status.OPENED,
                    DteMessageAccess.Status.READING,
                    DteMessageAccess.Status.UNKNOWN,
                )
            )
        elif message_filter == "read":
            message_query = message_query.exclude(
                access_receipt__status__in=(
                    DteMessageAccess.Status.READING,
                    DteMessageAccess.Status.UNKNOWN,
                )
            ).filter(
                Q(display_read_at__isnull=False)
                | Q(display_science_at__isnull=False)
                | Q(access_receipt__status=DteMessageAccess.Status.OPENED)
            )
        elif message_filter == "uncertain":
            message_query = message_query.filter(
                access_receipt__status__in=(
                    DteMessageAccess.Status.READING,
                    DteMessageAccess.Status.UNKNOWN,
                )
            )
        message_page = Paginator(message_query.order_by("-sent_at", "-first_seen_at"), 25).get_page(
            request.GET.get("page")
        )
    if not visitor:
        pending_runs = list(
            DteRun.objects.filter(organization=office, status=DteRun.Status.AWAITING_APPROVAL)
            .select_related("requested_by")
            .prefetch_related("items__company")
            .order_by("-requested_at")
        )
    for pending in pending_runs:
        if office.is_demo:
            pending.usage_quote = SimpleNamespace(  # type: ignore[attr-defined]
                total_tokens=0,
                included_remaining=0,
                additional_overage_tokens=0,
                additional_overage_cents=0,
            )
        else:
            try:
                pending.usage_quote = quote_tokens(  # type: ignore[attr-defined]
                    organization=office,
                    module_code="integra",
                    action_code=DTE_ACTION_CODE,
                    operations=pending.total_companies,
                )
            except BillingError:
                try:
                    pending.usage_quote = quote_usage(  # type: ignore[attr-defined]
                        organization=office,
                        action_code=DTE_ACTION_CODE,
                        units=pending.total_companies,
                    )
                except BillingError:
                    pending.usage_quote = None  # type: ignore[attr-defined]
        if pending.usage_quote is not None and not hasattr(pending.usage_quote, "total_tokens"):
            pending.usage_quote.total_tokens = pending.total_companies  # type: ignore[attr-defined]
            pending.usage_quote.additional_overage_tokens = (  # type: ignore[attr-defined]
                pending.usage_quote.additional_overage_units
            )
        pending.overage_brl = (  # type: ignore[attr-defined]
            Decimal(pending.usage_quote.additional_overage_cents) / 100
            if pending.usage_quote is not None
            else None
        )
    membership = context["membership"]
    can_authorize_overage = isinstance(membership, Membership) and membership.role in {
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
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
                "awaiting": (
                    len(pending_runs)
                    if visitor
                    else DteRun.objects.filter(
                        organization=office, status=DteRun.Status.AWAITING_APPROVAL
                    ).count()
                ),
                "unread": visitor_unread
                if visitor
                else DteMessage.objects.filter(
                    organization=office, company_id__in=allowed_company_ids
                )
                .annotate(
                    display_read_at=Coalesce("current_state__read_at", "read_at"),
                    display_science_at=Coalesce("current_state__science_at", "source_science_at"),
                )
                .filter(display_read_at__isnull=True, display_science_at__isnull=True)
                .exclude(
                    access_receipt__status__in=(
                        DteMessageAccess.Status.OPENED,
                        DteMessageAccess.Status.READING,
                        DteMessageAccess.Status.UNKNOWN,
                    )
                )
                .count(),
                "uncertain": 0
                if visitor
                else DteMessage.objects.filter(
                    organization=office,
                    company_id__in=allowed_company_ids,
                    access_receipt__status__in=(
                        DteMessageAccess.Status.READING,
                        DteMessageAccess.Status.UNKNOWN,
                    ),
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


@office_required
@require_http_methods(["POST"])
def prepare_dte_continuation(request: HttpRequest, item_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.INTEGRA))
    if blocked:
        return blocked
    if not _can_prepare_dte(context):
        return refuse(request, "Seu perfil não pode preparar consultas DTE.")
    office = cast(Organization, context["office"])
    if is_demo_visitor(request, office):
        return refuse(request, "A consulta fictícia não tem paginação externa para continuar.")
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    source = DteRunItem.objects.filter(
        id=item_id, organization=office, company_id__in=companies.values("id")
    ).first()
    if source is None:
        return refuse(request, "Consulta não encontrada neste escritório.")
    try:
        prepare_dte_next_page(source_item=source, actor=request.user, request=request)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(
            request, "Próxima página preparada. Confira uma consulta na fila e autorize o envio."
        )
    return redirect("hub:dte-center")


def _can_acknowledge_dte(context: dict[str, object]) -> bool:
    if not context["support_can_mutate"] or context["support_session"] is not None:
        return False
    membership = context["membership"]
    return isinstance(membership, Membership) and (
        membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
        or (membership.role == Membership.Role.OPERATOR and membership.can_acknowledge_dte)
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
    visitor = is_demo_visitor(request, office)
    if visitor:
        entry = get_progress(request, "dte_messages", message.id)
        access = (
            DteMessageAccess(
                organization=office,
                message=message,
                status=DteMessageAccess.Status.OPENED,
                attempt_count=1,
                requested_by=request.user,
                opened_at=parse_datetime(str(entry.get("opened_at", ""))),
                provider_request_id=str(entry.get("protocol", "")),
                provider_payload=json.dumps(
                    {
                        "corpoModelo": (
                            f"Mensagem fictícia para {message.company.name}. "
                            "A abertura nesta demonstração não registra ciência "
                            "oficial nem inicia prazo jurídico."
                        )
                    }
                ),
            )
            if entry.get("opened")
            else None
        )
    else:
        access = DteMessageAccess.objects.filter(organization=office, message=message).first()
    current_state = getattr(message, "current_state", None)
    can_acknowledge = _can_acknowledge_dte(context)
    try:
        detail_quote = (
            SimpleNamespace(total_tokens=0, additional_overage_tokens=0, additional_overage_cents=0)
            if office.is_demo
            else quote_tokens(
                organization=office,
                module_code="integra",
                action_code="caixapostal.detalhe",
            )
        )
    except BillingError:
        try:
            detail_quote = quote_usage(organization=office, action_code="caixapostal.detalhe")
        except BillingError:
            detail_quote = None
    if detail_quote is not None and not hasattr(detail_quote, "total_tokens"):
        detail_quote.total_tokens = 1
        detail_quote.additional_overage_tokens = detail_quote.additional_overage_units
    can_authorize_overage = isinstance(context["membership"], Membership) and context[
        "membership"
    ].role in {Membership.Role.OWNER, Membership.Role.ADMIN}
    if request.method == "POST":
        if not can_acknowledge:
            return refuse(request, "Este perfil não pode confirmar a ciência do DTE.")
        if not context["connector_ready"]:
            messages.error(request, "A conexão central Serpro ainda não está configurada.")
        elif not office.is_demo and detail_quote is None:
            messages.error(request, "O contrato não inclui a consulta de detalhes da Caixa Postal.")
        elif request.POST.get("confirm_legal_notice") != "on":
            messages.error(
                request, "Confirme que esta abertura pode registrar ciência e iniciar prazo."
            )
        elif detail_quote.additional_overage_cents and (
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
            approved_overage = (
                bool(detail_quote.additional_overage_cents)
                and isinstance(membership, Membership)
                and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
            )
            if visitor:
                if not get_progress(request, "dte_messages", message.id).get("opened"):
                    put_progress(
                        request,
                        "dte_messages",
                        message.id,
                        {
                            "opened": True,
                            "opened_at": timezone.now().isoformat(),
                            "protocol": f"DEMO-{str(message.id)[:12]}",
                        },
                    )
                messages.success(
                    request,
                    "Teor fictício aberto nesta sessão; nenhuma ciência oficial foi registrada.",
                )
            elif office.is_demo:
                access, _ = DteMessageAccess.objects.update_or_create(
                    organization=office,
                    message=message,
                    defaults={
                        "status": DteMessageAccess.Status.OPENED,
                        "attempt_count": 1,
                        "requested_by": request.user,
                        "opened_at": timezone.now(),
                        "provider_request_id": f"DEMO-{message.id}",
                        "provider_payload": json.dumps(
                            {
                                "corpoModelo": (
                                    f"Mensagem fictícia para {message.company.name}. "
                                    "A abertura nesta demonstração não registra ciência "
                                    "oficial nem inicia prazo jurídico."
                                )
                            }
                        ),
                    },
                )
                record_event(
                    action="hub.dte.demo_message_opened",
                    actor=request.user,
                    organization=office,
                    target=message,
                    request=request,
                )
                messages.success(
                    request, "Teor fictício aberto; nenhuma ciência oficial foi registrada."
                )
            else:
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
        return detail_redirect(request, "hub:dte-message-detail", message_id=message.id)
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
            "dte_detail_rate": detail_quote is not None,
            "dte_detail_quote": detail_quote,
            "dte_detail_overage_brl": (
                Decimal(detail_quote.additional_overage_cents) / 100 if detail_quote else None
            ),
            "can_open_dte_detail": can_acknowledge
            and bool(context["connector_ready"])
            and detail_quote is not None
            and (not detail_quote.additional_overage_cents or can_authorize_overage),
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
    if is_demo_visitor(request, office):
        entry = get_progress(request, "dte_runs", run_id)
        if entry.get("status") != "prepared":
            raise Http404
        selected = entry.get("company_ids", [])
        allowed = {str(company.id) for company in context["companies"]}
        if (
            not isinstance(selected, list)
            or not selected
            or any(code not in allowed for code in selected)
        ):
            raise Http404
        decision = request.POST.get("decision", "")
        if decision == "approve":
            entry["status"] = "completed"
            messages.success(
                request,
                f"Consulta fictícia concluída para {len(selected)} "
                f"{'empresa' if len(selected) == 1 else 'empresas'}, "
                "sem Serpro ou cobrança.",
            )
        elif decision == "cancel":
            entry["status"] = "cancelled"
            messages.success(request, "Consulta fictícia retirada desta sessão.")
        else:
            messages.error(request, "Escolha autorizar ou retirar.")
            return redirect("hub:dte-center")
        put_progress(request, "dte_runs", run_id, entry)
        return redirect("hub:dte-center")
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
                    int(request.POST["approved_overage_cents"]) if approved_overage else None
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
    visitor = is_demo_visitor(request, office)
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
    match_search = request.GET.get("q", "").strip()[:100]
    match_status = request.GET.get("status", "attention")
    if match_status not in {"attention", "all", *ReconciliationMatch.Status.values}:
        match_status = "attention"
    match_query = ReconciliationMatch.objects.filter(
        organization=office, transaction__statement__company__in=companies
    ).select_related(
        "transaction__statement__company",
        "dominio_entry",
        "accounting_entry__data_source",
    )
    if visitor:
        matches = _demo_reconciliation_matches(request, list(companies.filter(active=True)[:2]))
        if match_search:
            needle = match_search.casefold()
            matches = [
                match
                for match in matches
                if needle
                in " ".join(
                    (
                        match.transaction.statement.company.name,
                        match.transaction.statement.company.dominio_code,
                        match.transaction.description,
                    )
                ).casefold()
            ]
        if match_status == "attention":
            matches = [
                match
                for match in matches
                if match.status
                in {ReconciliationMatch.Status.AMBIGUOUS, ReconciliationMatch.Status.UNMATCHED}
            ]
        elif match_status != "all":
            matches = [match for match in matches if match.status == match_status]
        match_total = len(matches)
        imports = [
            SimpleNamespace(company=match.transaction.statement.company) for match in matches
        ]
        context.update(
            {
                "page_title": "Conciliação OFX x Domínio",
                "form": form,
                "imports": imports,
                "matches": matches,
                "match_total": match_total,
                "match_search": match_search,
                "match_status": match_status,
                "can_import_ofx": False,
                "can_confirm_matches": True,
                "reconciliation_demo": True,
                "reconciliation_stats": {
                    "attention": sum(
                        match.status
                        in {
                            ReconciliationMatch.Status.AMBIGUOUS,
                            ReconciliationMatch.Status.UNMATCHED,
                        }
                        for match in matches
                    ),
                    "ambiguous": sum(
                        match.status == ReconciliationMatch.Status.AMBIGUOUS for match in matches
                    ),
                    "matched": sum(
                        match.status == ReconciliationMatch.Status.MATCHED for match in matches
                    ),
                },
                "open_import_modal": False,
                **_reconciliation_v2_context(office, companies, request),
            }
        )
        return render(request, "hub/reconciliation.html", context)
    if match_search:
        match_query = match_query.filter(
            Q(transaction__statement__company__name__icontains=match_search)
            | Q(transaction__statement__company__dominio_code__icontains=match_search)
            | Q(transaction__description__icontains=match_search)
            | Q(dominio_entry__description__icontains=match_search)
            | Q(accounting_entry__description__icontains=match_search)
        )
    if match_status == "attention":
        match_query = match_query.filter(
            status__in=[
                ReconciliationMatch.Status.AMBIGUOUS,
                ReconciliationMatch.Status.UNMATCHED,
            ]
        )
    elif match_status != "all":
        match_query = match_query.filter(status=match_status)
    match_total = match_query.count()
    matches = list(match_query.order_by("-transaction__occurred_on", "-created_at")[:100])
    review_keys = {
        (match.transaction.statement.company_id, match.transaction.occurred_on)
        for match in matches
        if match.status == ReconciliationMatch.Status.AMBIGUOUS and not match.is_manual
    }
    candidate_entries = DominioBankEntry.objects.none()
    accounting_candidates = AccountingEntry.objects.none()
    if review_keys:
        pair_filter = Q()
        for candidate_company_id, occurred_on in review_keys:
            pair_filter |= Q(company_id=candidate_company_id, occurred_on=occurred_on)
        candidate_entries = DominioBankEntry.objects.filter(organization=office).filter(pair_filter)
        accounting_candidates = (
            AccountingEntry.objects.filter(organization=office)
            .filter(pair_filter)
            .select_related("data_source")
        )
    candidates_by_key: dict[tuple[object, object, int], list[object]] = {}
    for entry in candidate_entries:
        entry.amount_brl = Decimal(entry.amount_cents) / 100  # type: ignore[attr-defined]
        entry.candidate_token = f"dominio:{entry.id}"  # type: ignore[attr-defined]
        entry.source_label = "Espelho Domínio"  # type: ignore[attr-defined]
        candidates_by_key.setdefault(
            (entry.company_id, entry.occurred_on, entry.amount_cents), []
        ).append(entry)
    dominio_source_ids = {entry.source_id for entry in candidate_entries}
    for entry in accounting_candidates:
        # The direct ODBC sync mirrors the same row in both models. Present it
        # once, preferring the Domínio-specific record as operator evidence.
        if entry.external_key in dominio_source_ids:
            continue
        entry.amount_brl = Decimal(entry.amount_cents) / 100  # type: ignore[attr-defined]
        entry.candidate_token = f"accounting:{entry.id}"  # type: ignore[attr-defined]
        entry.source_label = entry.data_source.label  # type: ignore[attr-defined]
        candidates_by_key.setdefault(
            (entry.company_id, entry.occurred_on, entry.amount_cents), []
        ).append(entry)
    for match in matches:
        match.display_entry = match.dominio_entry or match.accounting_entry  # type: ignore[attr-defined]
        match.amount_brl = Decimal(abs(match.transaction.amount_cents)) / 100  # type: ignore[attr-defined]
        match.source_label = (  # type: ignore[attr-defined]
            "Espelho Domínio"
            if match.dominio_entry_id
            else match.accounting_entry.data_source.label
            if match.accounting_entry_id
            else "Sem correspondência"
        )
        match.display_reference = (  # type: ignore[attr-defined]
            getattr(match.display_entry, "source_id", "")
            or getattr(match.display_entry, "external_key", "")
        )
        match.candidates = candidates_by_key.get(  # type: ignore[attr-defined]
            (
                match.transaction.statement.company_id,
                match.transaction.occurred_on,
                abs(match.transaction.amount_cents),
            ),
            [],
        )
    all_matches = ReconciliationMatch.objects.filter(
        organization=office, transaction__statement__company__in=companies
    )
    reconciliation_stats = {
        "attention": all_matches.filter(
            status__in=[
                ReconciliationMatch.Status.AMBIGUOUS,
                ReconciliationMatch.Status.UNMATCHED,
            ]
        ).count(),
        "ambiguous": all_matches.filter(status=ReconciliationMatch.Status.AMBIGUOUS).count(),
        "matched": all_matches.filter(status=ReconciliationMatch.Status.MATCHED).count(),
    }
    context.update(
        {
            "page_title": "Conciliação OFX x Domínio",
            "form": form,
            "imports": BankStatementImport.objects.filter(
                organization=office, company__in=companies
            ).select_related("company")[:20],
            "matches": matches,
            "match_total": match_total,
            "match_search": match_search,
            "match_status": match_status,
            "can_import_ofx": _can_prepare_dte(context),
            "can_confirm_matches": _can_prepare_dte(context),
            "reconciliation_demo": False,
            "reconciliation_stats": reconciliation_stats,
            "open_import_modal": request.method == "POST" and bool(form.errors),
            **_reconciliation_v2_context(office, companies, request),
        }
    )
    return render(request, "hub/reconciliation.html", context)


def _demo_reconciliation_matches(
    request: HttpRequest, companies: list[ClientCompany]
) -> list[SimpleNamespace]:
    """Create stable, session-only examples without accepting a real bank file."""

    rows: list[SimpleNamespace] = []
    progress = get_section(request, "reconciliation")
    for index, company in enumerate(companies):
        match_id = uuid.uuid5(uuid.NAMESPACE_URL, f"cica-demo-match:{company.id}")
        candidates = [
            SimpleNamespace(
                id=uuid.uuid5(
                    uuid.NAMESPACE_URL, f"cica-demo-candidate:{company.id}:{candidate_index}"
                ),
                description=description,
                direction="Crédito",
                amount_brl=Decimal("1280.40") + candidate_index,
                source_label="Espelho Domínio fictício",
            )
            for candidate_index, description in enumerate(
                ("Recebimento de cliente", "Crédito bancário a identificar"), start=1
            )
        ]
        entry = progress.get(str(match_id), {})
        selected = next(
            (item for item in candidates if str(item.id) == entry.get("candidate_id")), None
        )
        status = (
            ReconciliationMatch.Status.MATCHED
            if selected
            else ReconciliationMatch.Status.AMBIGUOUS
            if index == 0
            else ReconciliationMatch.Status.UNMATCHED
        )
        rows.append(
            SimpleNamespace(
                id=match_id,
                transaction=SimpleNamespace(
                    occurred_on=timezone.localdate() - timedelta(days=index + 1),
                    description=(
                        "PIX recebido · Cliente demonstração"
                        if index == 0
                        else "TED recebida · Referência não identificada"
                    ),
                    statement=SimpleNamespace(company=company),
                ),
                dominio_entry=selected,
                accounting_entry=None,
                display_entry=selected,
                display_reference="",
                amount_brl=Decimal("1281.40") if index == 0 else Decimal("940.00"),
                source_label="Espelho Domínio fictício" if selected else "Sem correspondência",
                status=status,
                is_manual=bool(selected),
                candidates=candidates if status == ReconciliationMatch.Status.AMBIGUOUS else [],
                get_status_display=lambda current=status: dict(ReconciliationMatch.Status.choices)[
                    current
                ],
            )
        )
    return rows


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
    if is_demo_visitor(request, office):
        matches = {
            str(item.id): item
            for item in _demo_reconciliation_matches(
                request, list(companies.filter(active=True)[:2])
            )
        }
        match = matches.get(str(match_id))
        candidate_id = request.POST.get("dominio_entry_id", "")
        if match is None or candidate_id not in {str(item.id) for item in match.candidates}:
            return refuse(request, "A correspondência fictícia não está disponível nesta sessão.")
        put_progress(
            request,
            "reconciliation",
            match_id,
            {"candidate_id": candidate_id, "confirmed_at": timezone.now().isoformat()},
        )
        messages.success(
            request,
            "Conciliação fictícia confirmada nesta sessão; nenhum lançamento foi alterado.",
        )
        return redirect("hub:reconciliation")
    match = get_object_or_404(
        ReconciliationMatch.objects.select_related("transaction__statement"),
        id=match_id,
        organization=office,
        transaction__statement__company__in=companies,
    )
    candidate_token = request.POST.get("source_entry", request.POST.get("dominio_entry_id", ""))
    source_kind, separator, source_id = candidate_token.partition(":")
    if not separator:
        source_kind, source_id = "dominio", candidate_token
    dominio_entry = None
    accounting_entry = None
    if source_kind == "dominio":
        dominio_entry = get_object_or_404(DominioBankEntry, id=source_id, organization=office)
    elif source_kind == "accounting":
        accounting_entry = get_object_or_404(AccountingEntry, id=source_id, organization=office)
    else:
        return refuse(request, "A origem escolhida não é válida.")
    try:
        confirm_reconciliation_match(
            match=match,
            dominio_entry=dominio_entry,
            accounting_entry=accounting_entry,
            actor=request.user,
            request=request,
        )
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "Conciliação confirmada.")
    return redirect("hub:reconciliation")


def _can_manage_reconciliation(context: dict[str, object]) -> bool:
    membership = context.get("membership")
    return isinstance(membership, Membership) and membership.role in {
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
        Membership.Role.MANAGER,
        Membership.Role.OPERATOR,
    }


def _reconciliation_v2_context(
    office: Organization, companies: QuerySet[ClientCompany], request: HttpRequest | None = None
) -> dict[str, object]:
    runs = ReconciliationRun.objects.filter(
        organization=office, source_file__company__in=companies
    ).select_related("source_file", "source_file__company")[:12]
    all_movements = NormalizedMovement.objects.filter(organization=office, company__in=companies)
    movement_filters = {
        "company": request.GET.get("movement_company", "") if request else "",
        "review": request.GET.get("movement_review", "") if request else "",
        "classification": request.GET.get("movement_classification", "") if request else "",
        "query": (request.GET.get("movement_q", "").strip() if request else "")[:100],
    }
    filtered_movements = all_movements
    if movement_filters["company"]:
        filtered_movements = filtered_movements.filter(company_id=movement_filters["company"])
    if movement_filters["review"] in set(NormalizedMovement.ReviewState.values):
        filtered_movements = filtered_movements.filter(review_state=movement_filters["review"])
    if movement_filters["classification"] in set(NormalizedMovement.ClassificationSource.values):
        filtered_movements = filtered_movements.filter(
            classification_source=movement_filters["classification"]
        )
    if movement_filters["query"]:
        filtered_movements = filtered_movements.filter(
            Q(description__icontains=movement_filters["query"])
            | Q(original_description__icontains=movement_filters["query"])
            | Q(document_number__icontains=movement_filters["query"])
            | Q(counterparty__icontains=movement_filters["query"])
        )
    movement_page = Paginator(
        filtered_movements.select_related("company", "source_file", "applied_rule").order_by(
            "-occurred_on", "-created_at"
        ),
        50,
    ).get_page(request.GET.get("movement_page") if request else 1)
    movements = list(movement_page.object_list)
    for movement in movements:
        movement.amount_brl = Decimal(abs(movement.amount_cents)) / 100  # type: ignore[attr-defined]
    exports = AccountingExport.objects.filter(
        organization=office, company__in=companies
    ).select_related("company")[:8]
    allocation_stats = all_movements.annotate(
        confirmed_allocation=Coalesce(
            Sum(
                "reconciliations__amount_cents",
                filter=Q(reconciliations__state=MovementReconciliation.State.CONFIRMED),
            ),
            0,
        ),
        required_allocation=Case(
            When(amount_cents__lt=0, then=-F("amount_cents")),
            default=F("amount_cents"),
            output_field=IntegerField(),
        ),
    )
    return {
        "upload_form": ReconciliationUploadForm(companies=companies),
        "reconciliation_runs": runs,
        "normalized_movements": movements,
        "normalized_movement_page": movement_page,
        "normalized_movement_filters": movement_filters,
        "accounting_exports": exports,
        "reconciliation_v2_stats": {
            "imported": all_movements.count(),
            "classified": all_movements.exclude(
                classification_source=NormalizedMovement.ClassificationSource.NONE
            ).count(),
            "pending": all_movements.filter(
                review_state=NormalizedMovement.ReviewState.PENDING
            ).count(),
            "conflicts": all_movements.filter(
                review_state=NormalizedMovement.ReviewState.CONFLICT
            ).count(),
            "reconciled": allocation_stats.filter(confirmed_allocation__gt=0).count(),
            "partially_reconciled": allocation_stats.filter(
                confirmed_allocation__gt=0,
                confirmed_allocation__lt=F("required_allocation"),
            ).count(),
            "exported": JournalEntry.objects.filter(
                organization=office, company__in=companies, state=JournalEntry.State.EXPORTED
            ).count(),
        },
        "reconciliation_local_ocr_available": local_ocr_available(),
        "reconciliation_dominio_export_homologated": (
            settings.RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED
        ),
    }


@office_required
@require_http_methods(["GET", "POST"])
def reconciliation_configuration(request: HttpRequest) -> HttpResponse:
    """Manage the company-owned accounting reference data used by reconciliation."""
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    selected_company_id = request.POST.get("company") or request.GET.get("company")
    selected_company = (
        companies.filter(id=selected_company_id).first() if selected_company_id else None
    )
    if selected_company is None:
        selected_company = companies.order_by("name").first()
    if selected_company is None:
        return refuse(
            request, "Cadastre ou habilite uma empresa antes de configurar a conciliação."
        )

    action = request.POST.get("action", "")
    forms_by_action: dict[str, forms.BaseForm] = {
        "financial_account": FinancialAccountForm(
            request.POST if action == "financial_account" else None,
            companies=companies,
            initial={"company": selected_company},
        ),
        "ledger_account": LedgerAccountForm(
            request.POST if action == "ledger_account" else None,
            companies=companies,
            initial={"company": selected_company},
        ),
        "cost_center": CostCenterForm(
            request.POST if action == "cost_center" else None,
            companies=companies,
            initial={"company": selected_company},
        ),
        "accounting_period": AccountingPeriodForm(
            request.POST if action == "accounting_period" else None,
            companies=companies,
            initial={"company": selected_company},
        ),
        "reconciliation_rule": ReconciliationRuleForm(
            request.POST if action == "reconciliation_rule" else None,
            companies=companies,
            initial={"company": selected_company},
        ),
    }
    if request.method == "POST":
        if not context["support_can_mutate"] or not _can_manage_reconciliation(context):
            return refuse(request, "Seu perfil pode consultar, mas não alterar a configuração.")
        form = forms_by_action.get(action)
        if form is not None and form.is_valid():
            try:
                with transaction.atomic():
                    if action == "reconciliation_rule":
                        rule_form = cast(ReconciliationRuleForm, form)
                        all_conditions, any_conditions = rule_form.condition_groups()
                        configured = ReconciliationRule.objects.create(
                            organization=office,
                            company=rule_form.cleaned_data["company"],
                            name=rule_form.cleaned_data["name"],
                            priority=rule_form.cleaned_data["priority"],
                            state=rule_form.cleaned_data["state"],
                            all_conditions=all_conditions,
                            any_conditions=any_conditions,
                            actions=rule_form.actions(),
                            created_by=request.user,
                        )
                    else:
                        configured = cast(forms.ModelForm, form).save(commit=False)
                        configured.organization = office
                        configured.save()
                record_event(
                    action=f"hub.reconciliation.{action}.created",
                    actor=request.user,
                    organization=office,
                    target=configured,
                    request=request,
                    metadata={"company_id": str(configured.company_id)},
                )
            except IntegrityError:
                form.add_error(None, "Já existe um cadastro com estes dados para esta empresa.")
            else:
                messages.success(request, "Configuração salva.")
                return redirect(
                    f"{reverse('hub:reconciliation-configuration')}?company={configured.company_id}"
                )
        elif action == "toggle_rule":
            rule = get_object_or_404(
                ReconciliationRule,
                id=request.POST.get("rule_id"),
                organization=office,
                company=selected_company,
            )
            rule.state = (
                ReconciliationRule.State.DISABLED
                if rule.state == ReconciliationRule.State.ACTIVE
                else ReconciliationRule.State.ACTIVE
            )
            rule.save(update_fields=["state", "updated_at"])
            record_event(
                action="hub.reconciliation.rule.state_changed",
                actor=request.user,
                organization=office,
                target=rule,
                request=request,
                metadata={"state": rule.state},
            )
            messages.success(request, "Situação da regra atualizada.")
            return redirect(
                f"{reverse('hub:reconciliation-configuration')}?company={selected_company.id}"
            )
        elif action == "toggle_setup":
            setup_models: dict[str, type[models.Model]] = {
                "financial_account": FinancialAccount,
                "ledger_account": LedgerAccount,
                "cost_center": CostCenter,
                "layout": ReconciliationLayout,
            }
            setup_kind = request.POST.get("setup_kind", "")
            setup_model = setup_models.get(setup_kind)
            if setup_model is None:
                return refuse(request, "Item de configuração inválido.")
            configured = get_object_or_404(
                setup_model,
                id=request.POST.get("setup_id"),
                organization=office,
                company=selected_company,
            )
            configured.active = not configured.active
            configured.save(update_fields=["active", "updated_at"])
            record_event(
                action=f"hub.reconciliation.{setup_kind}.state_changed",
                actor=request.user,
                organization=office,
                target=configured,
                request=request,
                metadata={"active": configured.active},
            )
            messages.success(
                request,
                "Item ativado." if configured.active else "Item desativado para novos usos.",
            )
            return redirect(
                f"{reverse('hub:reconciliation-configuration')}?company={selected_company.id}"
            )
        elif action not in forms_by_action:
            period = get_object_or_404(
                AccountingPeriod,
                id=request.POST.get("period_id"),
                organization=office,
                company=selected_company,
            )
            reason = request.POST.get("reason", "").strip()
            if not reason:
                messages.error(request, "Informe o motivo para bloquear ou reabrir o período.")
            elif action == "lock_period":
                period.locked_at = timezone.now()
                period.locked_by = request.user
                period.lock_reason = reason[:240]
                period.save(update_fields=["locked_at", "locked_by", "lock_reason", "updated_at"])
                record_event(
                    action="hub.reconciliation.period.locked",
                    actor=request.user,
                    organization=office,
                    target=period,
                    request=request,
                    metadata={"reason": period.lock_reason},
                )
                messages.success(request, "Período bloqueado.")
                return redirect(
                    f"{reverse('hub:reconciliation-configuration')}?company={selected_company.id}"
                )
            elif action == "unlock_period":
                period.locked_at = None
                period.locked_by = None
                period.lock_reason = reason[:240]
                period.save(update_fields=["locked_at", "locked_by", "lock_reason", "updated_at"])
                record_event(
                    action="hub.reconciliation.period.unlocked",
                    actor=request.user,
                    organization=office,
                    target=period,
                    request=request,
                    metadata={"reason": reason[:240]},
                )
                messages.success(request, "Período reaberto.")
                return redirect(
                    f"{reverse('hub:reconciliation-configuration')}?company={selected_company.id}"
                )
            else:
                return refuse(request, "Ação de configuração inválida.")

    context.update(
        {
            "page_title": "Configuração da conciliação",
            "reconciliation_configuration_company": selected_company,
            "reconciliation_can_manage": (
                context["support_can_mutate"] and _can_manage_reconciliation(context)
            ),
            "financial_account_form": forms_by_action["financial_account"],
            "ledger_account_form": forms_by_action["ledger_account"],
            "cost_center_form": forms_by_action["cost_center"],
            "accounting_period_form": forms_by_action["accounting_period"],
            "reconciliation_rule_form": forms_by_action["reconciliation_rule"],
            "financial_accounts": FinancialAccount.objects.filter(
                organization=office, company=selected_company
            ).order_by("name"),
            "ledger_accounts": LedgerAccount.objects.filter(
                organization=office, company=selected_company
            ).order_by("code"),
            "cost_centers": CostCenter.objects.filter(
                organization=office, company=selected_company
            ).order_by("code"),
            "accounting_periods": AccountingPeriod.objects.filter(
                organization=office, company=selected_company
            ).order_by("-starts_on"),
            "reconciliation_layouts": ReconciliationLayout.objects.filter(
                organization=office, company=selected_company
            ).order_by("kind", "name", "-version"),
            "reconciliation_rules": ReconciliationRule.objects.filter(
                organization=office, company=selected_company
            ).order_by("priority", "name"),
            "reconciliation_setup_status": {
                "financial_accounts": FinancialAccount.objects.filter(
                    organization=office, company=selected_company, active=True
                ).count(),
                "ledger_accounts": LedgerAccount.objects.filter(
                    organization=office,
                    company=selected_company,
                    active=True,
                    accepts_entries=True,
                ).count(),
                "cost_centers_required": CostCenter.objects.filter(
                    organization=office, company=selected_company, active=True, required=True
                ).exists(),
                "open_periods": AccountingPeriod.objects.filter(
                    organization=office, company=selected_company, locked_at__isnull=True
                ).count(),
                "active_rules": ReconciliationRule.objects.filter(
                    organization=office,
                    company=selected_company,
                    state=ReconciliationRule.State.ACTIVE,
                ).count(),
                "active_layouts": ReconciliationLayout.objects.filter(
                    organization=office, company=selected_company, active=True
                ).count(),
            },
        }
    )
    return render(request, "hub/reconciliation_configuration.html", context)


@office_required
@require_http_methods(["GET"])
def reconciliation_audit(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    membership = context.get("membership")
    if not isinstance(membership, Membership) or membership.role not in {
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
        Membership.Role.MANAGER,
    }:
        return refuse(request, "Seu perfil não pode consultar a auditoria da conciliação.")
    office = cast(Organization, context["office"])
    action_prefix = "hub.reconciliation."
    events = AuditEvent.objects.filter(
        organization=office, action__startswith=action_prefix
    ).select_related("actor")
    event_action = request.GET.get("action", "")
    if event_action:
        events = events.filter(action=event_action)
    context.update(
        {
            "page_title": "Auditoria da conciliação",
            "reconciliation_audit_events": events[:200],
            "reconciliation_audit_actions": AuditEvent.objects.filter(
                organization=office, action__startswith=action_prefix
            )
            .order_by("action")
            .values_list("action", flat=True)
            .distinct(),
            "reconciliation_audit_action": event_action,
        }
    )
    return render(request, "hub/reconciliation_audit.html", context)


@office_required
@require_http_methods(["POST"])
def reconciliation_upload(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    if not context["support_can_mutate"] or not _can_manage_reconciliation(context):
        return refuse(request, "Seu perfil pode consultar, mas não importar arquivos.")
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    form = ReconciliationUploadForm(request.POST, request.FILES, companies=companies)
    files = request.FILES.getlist("files")
    if not form.is_valid() or not files:
        if not files:
            form.add_error("files", "Selecione ao menos um arquivo.")
        context.update(
            {
                **_reconciliation_v2_context(office, companies, request),
                "page_title": "Conciliação OFX x Domínio",
                "upload_form": form,
                "upload_error": True,
                "form": OfxImportForm(companies=companies),
                "imports": BankStatementImport.objects.filter(
                    organization=office, company__in=companies
                ).select_related("company")[:20],
                "matches": [],
                "match_total": 0,
                "match_search": "",
                "match_status": "attention",
                "can_import_ofx": False,
                "can_confirm_matches": False,
                "reconciliation_demo": False,
                "reconciliation_stats": {"attention": 0, "ambiguous": 0, "matched": 0},
            }
        )
        return render(request, "hub/reconciliation.html", context, status=400)
    if len(files) > 20:
        form.add_error("files", "Envie no máximo 20 arquivos por lote.")
        context.update(
            {
                **_reconciliation_v2_context(office, companies, request),
                "page_title": "Conciliação OFX x Domínio",
                "upload_form": form,
                "upload_error": True,
                "form": OfxImportForm(companies=companies),
                "imports": BankStatementImport.objects.filter(
                    organization=office, company__in=companies
                ).select_related("company")[:20],
                "matches": [],
                "match_total": 0,
                "match_search": "",
                "match_status": "attention",
                "can_import_ofx": False,
                "can_confirm_matches": False,
                "reconciliation_demo": False,
                "reconciliation_stats": {"attention": 0, "ambiguous": 0, "matched": 0},
            }
        )
        return render(request, "hub/reconciliation.html", context, status=400)
    created = 0
    duplicates = 0
    failures: list[str] = []
    for upload in files:
        try:
            _source, run, was_created = create_source_file(
                organization=office,
                company=form.cleaned_data["company"],
                filename=upload.name,
                content=upload.read(),
                origin=form.cleaned_data["origin"],
                actor=request.user,
                physical_batch=form.cleaned_data.get("physical_batch", ""),
                financial_account=form.cleaned_data.get("financial_account"),
                request=request,
            )
            if was_created:
                from apps.hub.tasks import process_reconciliation_run

                transaction.on_commit(
                    lambda value=str(run.id): process_reconciliation_run.delay(value)
                )
                created += 1
            else:
                duplicates += 1
        except ReconciliationError as exc:
            failures.append(f"{upload.name}: {exc}")
    if created:
        messages.success(request, f"{created} processamento(s) criado(s).")
    if duplicates:
        messages.info(
            request, f"{duplicates} arquivo(s) já tinham sido enviados e não foram duplicados."
        )
    for failure in failures:
        messages.error(request, failure)
    return redirect("hub:reconciliation")


@office_required
@require_http_methods(["GET"])
def reconciliation_run_status(request: HttpRequest, run_id: str) -> JsonResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return JsonResponse({"detail": "Acesso negado."}, status=403)
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    run = get_object_or_404(
        ReconciliationRun.objects.select_related("source_file__company"),
        id=run_id,
        organization=office,
        source_file__company__in=companies,
    )
    return JsonResponse(
        {
            "id": str(run.id),
            "state": run.state,
            "state_label": run.get_state_display(),
            "stage": run.stage,
            "total": run.total_count,
            "processed": run.processed_count,
            "created": run.created_count,
            "updated": run.updated_count,
            "errors": run.error_count,
            "cancel_requested": bool(run.cancel_requested_at),
        }
    )


@office_required
@require_http_methods(["POST"])
def reconciliation_run_action(request: HttpRequest, run_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    if not context["support_can_mutate"] or not _can_manage_reconciliation(context):
        return refuse(request, "Seu perfil pode consultar, mas não alterar processamentos.")
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    run = get_object_or_404(
        ReconciliationRun,
        id=run_id,
        organization=office,
        source_file__company__in=companies,
    )
    action = request.POST.get("action")
    if action == "cancel":
        if run.state in {ReconciliationRun.State.WAITING, ReconciliationRun.State.PROCESSING}:
            run.cancel_requested_at = timezone.now()
            run.save(update_fields=["cancel_requested_at", "updated_at"])
            messages.success(
                request,
                "Cancelamento solicitado; o trabalho será interrompido no próximo ponto seguro.",
            )
        else:
            messages.info(request, "Este processamento não está em execução.")
    elif action == "retry":
        retry = ReconciliationRun.objects.create(
            organization=office,
            source_file=run.source_file,
            continued_from=run,
            layout_version=run.layout_version,
            checkpoint=run.checkpoint,
            created_by=request.user,
        )
        from apps.hub.tasks import process_reconciliation_run

        transaction.on_commit(lambda value=str(retry.id): process_reconciliation_run.delay(value))
        messages.success(request, "Novo processamento criado a partir do checkpoint anterior.")
    elif action == "reapply_rules":
        if run.state in {ReconciliationRun.State.WAITING, ReconciliationRun.State.PROCESSING}:
            messages.info(
                request, "Aguarde o processamento atual terminar antes de reaplicar regras."
            )
            return redirect("hub:reconciliation")
        reapplication = ReconciliationRun.objects.create(
            organization=office,
            source_file=run.source_file,
            continued_from=run,
            layout_version=run.layout_version,
            checkpoint={"mode": "rules", "source_run_id": str(run.id)},
            created_by=request.user,
        )
        record_event(
            action="hub.reconciliation.rules_reapplication_requested",
            actor=request.user,
            organization=office,
            target=reapplication,
            request=request,
            metadata={"source_file_id": str(run.source_file_id), "continued_from": str(run.id)},
        )
        from apps.hub.tasks import process_reconciliation_run

        transaction.on_commit(
            lambda value=str(reapplication.id): process_reconciliation_run.delay(value)
        )
        messages.success(
            request,
            "Reaplicação criada. Revisões manuais, conciliações e lançamentos serão preservados.",
        )
    else:
        return refuse(request, "Ação de processamento inválida.")
    return redirect("hub:reconciliation")


@office_required
@require_http_methods(["GET", "POST"])
def reconciliation_mapping(request: HttpRequest, source_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    source = get_object_or_404(
        ReconciliationSourceFile, id=source_id, organization=office, company__in=companies
    )
    if source.kind not in {ReconciliationSourceFile.Kind.CSV, ReconciliationSourceFile.Kind.XLSX}:
        return refuse(request, "Este formato não usa mapeamento de colunas.")
    try:
        preview = preview_tabular(source)
    except ReconciliationError as exc:
        return refuse(request, str(exc))
    if request.method == "POST":
        if not context["support_can_mutate"] or not _can_manage_reconciliation(context):
            return refuse(request, "Seu perfil pode consultar, mas não salvar layouts.")
        mapping_fields = (
            "date",
            "amount",
            "debit",
            "credit",
            "description",
            "document",
            "counterparty",
        )
        submitted_mapping = {
            field: request.POST.get(f"map_{field}", "").strip()
            for field in mapping_fields
            if request.POST.get(f"map_{field}", "").strip()
        }
        try:
            mapping = submitted_mapping or json.loads(request.POST.get("mapping", "{}"))
            if not isinstance(mapping, dict):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            messages.error(request, "O mapeamento enviado não é válido.")
        else:
            name = request.POST.get("name", "Layout importado").strip() or "Layout importado"
            try:
                layout = save_layout(
                    source=source,
                    name=name,
                    configuration={"mapping": mapping, "sheet": preview.get("sheet", "")},
                    actor=request.user,
                )
                runnable_runs = prepare_run_for_layout(source=source, layout=layout)
            except ReconciliationError as exc:
                messages.error(request, str(exc))
            else:
                for run in runnable_runs:
                    from apps.hub.tasks import process_reconciliation_run

                    transaction.on_commit(
                        lambda value=str(run.id): process_reconciliation_run.delay(value)
                    )
                messages.success(
                    request,
                    f"Layout {layout.name} v{layout.version} salvo e processamento iniciado.",
                )
                return redirect("hub:reconciliation")
    context.update(
        {
            "page_title": "Mapear arquivo",
            "mapping_source": source,
            "mapping_preview": preview,
            "mapping_fields": tuple(
                (field, label, preview["mapping"].get(field, ""))
                for field, label in (
                    ("date", "Data"),
                    ("amount", "Valor com sinal"),
                    ("debit", "Débito / saída"),
                    ("credit", "Crédito / entrada"),
                    ("description", "Histórico"),
                    ("document", "Documento"),
                    ("counterparty", "Contraparte"),
                )
            ),
        }
    )
    return render(request, "hub/reconciliation_mapping.html", context)


@office_required
@require_http_methods(["GET"])
def reconciliation_source_download(request: HttpRequest, source_id: str) -> FileResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        raise Http404
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    source = get_object_or_404(
        ReconciliationSourceFile,
        id=source_id,
        organization=office,
        company__in=companies,
    )
    response = FileResponse(
        source.content.open("rb"),
        as_attachment=True,
        filename=source.original_filename,
    )
    response["Cache-Control"] = "no-store, private"
    response["X-Content-Type-Options"] = "nosniff"
    record_event(
        action="hub.reconciliation.source_downloaded",
        actor=request.user,
        organization=office,
        target=source,
        request=request,
        metadata={"content_hash": source.content_hash},
    )
    return response


@office_required
@require_http_methods(["GET"])
def reconciliation_source_preview(request: HttpRequest, source_id: str) -> FileResponse:
    """Serve an authenticated inline PDF; the browser handles its page fragment."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        raise Http404
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    source = get_object_or_404(
        ReconciliationSourceFile,
        id=source_id,
        organization=office,
        company__in=companies,
        kind=ReconciliationSourceFile.Kind.PDF,
    )
    response = FileResponse(
        source.content.open("rb"),
        as_attachment=False,
        filename=source.original_filename,
        content_type="application/pdf",
    )
    response["Cache-Control"] = "no-store, private"
    response["X-Content-Type-Options"] = "nosniff"
    record_event(
        action="hub.reconciliation.source_previewed",
        actor=request.user,
        organization=office,
        target=source,
        request=request,
        metadata={"content_hash": source.content_hash},
    )
    return response


@office_required
@require_http_methods(["POST"])
def reconciliation_movement_bulk_action(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    if not context["support_can_mutate"] or not _can_manage_reconciliation(context):
        return refuse(request, "Seu perfil pode consultar, mas não alterar movimentos em lote.")
    raw_ids = request.POST.getlist("movement_ids")
    movement_ids = list(dict.fromkeys(value for value in raw_ids if value))
    if not movement_ids:
        messages.error(request, "Selecione ao menos um movimento desta página.")
        return redirect(f"{reverse('hub:reconciliation')}#movimentos")
    if len(movement_ids) > 50:
        return refuse(request, "Ações em lote aceitam até 50 movimentos por vez.")
    action = request.POST.get("action", "")
    if action not in {"ignore", "review"}:
        return refuse(request, "Escolha uma ação em lote válida.")
    reason = request.POST.get("reason", "").strip()
    if not reason:
        messages.error(request, "Informe o motivo da alteração em lote.")
        return redirect(f"{reverse('hub:reconciliation')}#movimentos")
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    with transaction.atomic():
        movements = list(
            NormalizedMovement.objects.select_for_update()
            .filter(id__in=movement_ids, organization=office, company__in=companies)
            .order_by("id")
        )
        if len(movements) != len(movement_ids):
            return refuse(request, "Um ou mais movimentos não estão mais disponíveis para você.")
        if any(
            movement.journal_entries.filter(state=JournalEntry.State.EXPORTED).exists()
            for movement in movements
        ):
            return refuse(request, "Movimentos exportados exigem retificação auditada.")
        new_state = (
            NormalizedMovement.ReviewState.IGNORED
            if action == "ignore"
            else NormalizedMovement.ReviewState.PENDING
        )
        for movement in movements:
            movement.review_state = new_state
            movement.revision += 1
            movement.edited_by = request.user
            movement.save(update_fields=["review_state", "revision", "edited_by", "updated_at"])
            invalidated_entries = movement.journal_entries.filter(
                state__in=[JournalEntry.State.DRAFT, JournalEntry.State.APPROVED]
            ).update(state=JournalEntry.State.INVALID, updated_at=timezone.now())
            record_event(
                action=(
                    "hub.reconciliation.movements_ignored"
                    if action == "ignore"
                    else "hub.reconciliation.movements_returned_to_review"
                ),
                actor=request.user,
                organization=office,
                target=movement,
                request=request,
                metadata={
                    "reason": reason[:240],
                    "revision": movement.revision,
                    "invalidated_entries": invalidated_entries,
                    "bulk_size": len(movements),
                },
            )
    messages.success(
        request,
        (
            f"{len(movement_ids)} movimento(s) ignorado(s)."
            if action == "ignore"
            else f"{len(movement_ids)} movimento(s) devolvido(s) à revisão."
        ),
    )
    return redirect(f"{reverse('hub:reconciliation')}#movimentos")


@office_required
@require_http_methods(["GET", "POST"])
def reconciliation_movement_detail(request: HttpRequest, movement_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    movement = get_object_or_404(
        NormalizedMovement.objects.select_related("source_file", "company", "applied_rule"),
        id=movement_id,
        organization=office,
        company__in=companies,
    )
    form = ReconciliationMovementForm(
        request.POST or None,
        initial={
            "occurred_on": movement.occurred_on,
            "description": movement.description,
            "document_number": movement.document_number,
            "counterparty": movement.counterparty,
            "debit_account_code": movement.debit_account_code,
            "credit_account_code": movement.credit_account_code,
            "cost_center_code": movement.cost_center_code,
            "accounting_history": movement.accounting_history,
            "expected_revision": movement.revision,
        },
    )
    if request.method == "POST":
        if not context["support_can_mutate"] or not _can_manage_reconciliation(context):
            return refuse(request, "Seu perfil pode consultar, mas não revisar movimentos.")
        action = request.POST.get("action", "save")
        if action in {"ignore_movement", "restore_movement"}:
            if movement.journal_entries.filter(state=JournalEntry.State.EXPORTED).exists():
                messages.error(request, "Um movimento já exportado exige uma retificação auditada.")
                return redirect("hub:reconciliation-movement", movement_id=movement.id)
            reason = request.POST.get("reason", "").strip()
            if action == "ignore_movement" and not reason:
                messages.error(request, "Informe o motivo para ignorar o movimento.")
                return redirect("hub:reconciliation-movement", movement_id=movement.id)
            movement.review_state = (
                NormalizedMovement.ReviewState.IGNORED
                if action == "ignore_movement"
                else NormalizedMovement.ReviewState.PENDING
            )
            movement.revision += 1
            movement.edited_by = request.user
            movement.save(update_fields=["review_state", "revision", "edited_by", "updated_at"])
            invalidated_entries = movement.journal_entries.filter(
                state__in=[JournalEntry.State.DRAFT, JournalEntry.State.APPROVED]
            ).update(state=JournalEntry.State.INVALID, updated_at=timezone.now())
            record_event(
                action=(
                    "hub.reconciliation.movement_ignored"
                    if action == "ignore_movement"
                    else "hub.reconciliation.movement_restored"
                ),
                actor=request.user,
                organization=office,
                target=movement,
                request=request,
                metadata={
                    "reason": reason[:240],
                    "revision": movement.revision,
                    "invalidated_entries": invalidated_entries,
                },
            )
            messages.success(
                request,
                "Movimento ignorado."
                if action == "ignore_movement"
                else "Movimento devolvido à revisão.",
            )
            return redirect("hub:reconciliation-movement", movement_id=movement.id)
        if action == "generate_entry":
            try:
                entry = create_journal_entry_from_movement(movement=movement, actor=request.user)
            except ReconciliationError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, f"Lançamento {entry.id} gerado como rascunho.")
            return redirect("hub:reconciliation-movement", movement_id=movement.id)
        if action == "save_rule":
            try:
                rule = save_rule_from_movement(movement=movement, actor=request.user)
            except ReconciliationError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, f"Regra {rule.name} salva e ativada para esta empresa.")
            return redirect("hub:reconciliation-movement", movement_id=movement.id)
        if action == "approve_entry":
            entry = movement.journal_entries.exclude(state=JournalEntry.State.INVALID).first()
            if entry is None:
                messages.error(request, "Gere o lançamento antes de aprová-lo.")
            else:
                try:
                    approve_journal_entry(entry=entry, actor=request.user, request=request)
                except ReconciliationError as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(request, "Lançamento aprovado para exportação.")
            return redirect("hub:reconciliation-movement", movement_id=movement.id)
        if action == "confirm_reconciliation":
            try:
                entry = JournalEntry.objects.get(
                    id=request.POST.get("entry_id"),
                    organization=office,
                    company=movement.company,
                )
                amount_cents = int(
                    (Decimal(request.POST.get("amount_brl", "0")) * 100).quantize(Decimal("1"))
                )
                evidence_note = request.POST.get("evidence_note", "").strip()
                if not evidence_note:
                    raise ReconciliationError("Descreva a evidência que justifica a conciliação.")
                reconciliation = confirm_normalized_reconciliation(
                    movement=movement,
                    entry=entry,
                    amount_cents=amount_cents,
                    evidence={"note": evidence_note, "source": movement.source_reference},
                    actor=request.user,
                )
            except (
                JournalEntry.DoesNotExist,
                InvalidOperation,
                ValueError,
                ReconciliationError,
            ) as exc:
                messages.error(request, f"Não foi possível confirmar a conciliação: {exc}")
            else:
                record_event(
                    action="hub.reconciliation.reconciliation_confirmed",
                    actor=request.user,
                    organization=office,
                    target=reconciliation,
                    request=request,
                    metadata={
                        "movement_id": str(movement.id),
                        "entry_id": str(reconciliation.entry_id),
                        "amount_cents": reconciliation.amount_cents,
                    },
                )
                messages.success(
                    request,
                    (
                        "Conciliação de R$ "
                        f"{Decimal(reconciliation.amount_cents) / 100:.2f} registrada."
                    ),
                )
            return redirect("hub:reconciliation-movement", movement_id=movement.id)
        if action == "undo_reconciliation":
            reconciliation = get_object_or_404(
                MovementReconciliation,
                id=request.POST.get("reconciliation_id"),
                organization=office,
                movement=movement,
                state=MovementReconciliation.State.CONFIRMED,
            )
            undo_normalized_reconciliation(reconciliation=reconciliation, actor=request.user)
            record_event(
                action="hub.reconciliation.reconciliation_undone",
                actor=request.user,
                organization=office,
                target=reconciliation,
                request=request,
                metadata={
                    "movement_id": str(movement.id),
                    "amount_cents": reconciliation.amount_cents,
                },
            )
            messages.success(request, "Conciliação desfeita e valor liberado para nova revisão.")
            return redirect("hub:reconciliation-movement", movement_id=movement.id)
        if form.is_valid():
            for field_name in ("debit_account_code", "credit_account_code"):
                account_code = str(form.cleaned_data[field_name] or "").strip()
                if (
                    account_code
                    and not LedgerAccount.objects.filter(
                        organization=office,
                        company=movement.company,
                        code=account_code,
                        active=True,
                        accepts_entries=True,
                    ).exists()
                ):
                    form.add_error(
                        field_name,
                        "Escolha uma conta ativa que aceite lançamentos desta empresa.",
                    )
            cost_center_code = str(form.cleaned_data["cost_center_code"] or "").strip()
            if (
                cost_center_code
                and not CostCenter.objects.filter(
                    organization=office,
                    company=movement.company,
                    code=cost_center_code,
                    active=True,
                ).exists()
            ):
                form.add_error(
                    "cost_center_code",
                    "Escolha um centro de custo ativo desta empresa.",
                )
        if form.is_valid():
            if movement.journal_entries.filter(state=JournalEntry.State.EXPORTED).exists():
                form.add_error(
                    None,
                    "Este movimento j\u00e1 foi exportado; "
                    "crie uma retifica\u00e7\u00e3o auditada.",
                )
            elif form.cleaned_data["expected_revision"] != movement.revision:
                form.add_error(
                    None,
                    "O movimento foi alterado por outra pessoa. Atualize a página antes de salvar.",
                )
            else:
                for field in (
                    "occurred_on",
                    "description",
                    "document_number",
                    "counterparty",
                    "debit_account_code",
                    "credit_account_code",
                    "cost_center_code",
                    "accounting_history",
                ):
                    setattr(movement, field, form.cleaned_data[field])
                movement.classification_source = NormalizedMovement.ClassificationSource.MANUAL
                movement.revision += 1
                movement.edited_by = request.user
                movement.save()
                invalidated_entries = movement.journal_entries.filter(
                    state__in=[JournalEntry.State.DRAFT, JournalEntry.State.APPROVED]
                ).update(state=JournalEntry.State.INVALID, updated_at=timezone.now())
                record_event(
                    action="hub.reconciliation.movement_edited",
                    actor=request.user,
                    organization=office,
                    target=movement,
                    request=request,
                    metadata={
                        "revision": movement.revision,
                        "invalidated_entries": invalidated_entries,
                    },
                )
                messages.success(
                    request,
                    "Movimento revisado. A aprovação anterior, se houver, precisa ser refeita.",
                )
                return redirect("hub:reconciliation-movement", movement_id=movement.id)
    candidate_query = (
        JournalEntry.objects.filter(
            organization=office,
            company=movement.company,
            state__in=[JournalEntry.State.DRAFT, JournalEntry.State.APPROVED],
        )
        .exclude(movement=movement)
        .prefetch_related("lines")
    )
    if movement.occurred_on:
        candidate_query = candidate_query.filter(
            occurred_on__range=(
                movement.occurred_on - timedelta(days=3),
                movement.occurred_on + timedelta(days=3),
            )
        )
    candidate_entries = list(candidate_query.order_by("-occurred_on", "-created_at")[:50])
    movement.amount_brl = Decimal(abs(movement.amount_cents)) / 100  # type: ignore[attr-defined]
    reconciliations = list(
        movement.reconciliations.filter(state=MovementReconciliation.State.CONFIRMED)
        .select_related("entry")
        .order_by("created_at")
    )
    for reconciliation in reconciliations:
        reconciliation.amount_brl = Decimal(reconciliation.amount_cents) / 100  # type: ignore[attr-defined]
    movement.allocated_cents = sum(item.amount_cents for item in reconciliations)  # type: ignore[attr-defined]
    movement.remaining_cents = abs(movement.amount_cents) - movement.allocated_cents  # type: ignore[attr-defined]
    movement.allocated_brl = Decimal(movement.allocated_cents) / 100  # type: ignore[attr-defined]
    movement.remaining_brl = Decimal(movement.remaining_cents) / 100  # type: ignore[attr-defined]
    entry_used = {
        row["entry_id"]: row["allocated"]
        for row in MovementReconciliation.objects.filter(
            organization=office,
            entry__in=candidate_entries,
            state=MovementReconciliation.State.CONFIRMED,
        )
        .values("entry_id")
        .annotate(allocated=Sum("amount_cents"))
    }
    suggestions: list[dict[str, object]] = []
    normalized_document = movement.document_number.casefold().strip()
    normalized_counterparty = movement.counterparty.casefold().strip()
    for entry in candidate_entries:
        debits = sum(
            line.amount_cents for line in entry.lines.all() if line.side == JournalLine.Side.DEBIT
        )
        credits = sum(
            line.amount_cents for line in entry.lines.all() if line.side == JournalLine.Side.CREDIT
        )
        available = debits - int(entry_used.get(entry.id, 0) or 0)
        if debits <= 0 or debits != credits or available <= 0:
            continue
        score = 0
        reasons: list[str] = []
        if available == movement.remaining_cents:
            score += 50
            reasons.append("valor disponível igual")
        if entry.occurred_on == movement.occurred_on:
            score += 30
            reasons.append("mesma data")
        history = entry.history.casefold()
        if normalized_document and normalized_document in history:
            score += 20
            reasons.append("documento no histórico")
        if normalized_counterparty and normalized_counterparty in history:
            score += 15
            reasons.append("contraparte no histórico")
        if score:
            allocation_limit_cents = min(available, movement.remaining_cents)
            allocation_limit_brl = Decimal(allocation_limit_cents) / 100
            suggestions.append(
                {
                    "entry": entry,
                    "score": score,
                    "reasons": "; ".join(reasons),
                    "available_cents": available,
                    "allocation_limit_cents": allocation_limit_cents,
                    "allocation_limit_brl": allocation_limit_brl,
                    "allocation_limit_input": f"{allocation_limit_brl:.2f}",
                }
            )
    suggestions.sort(key=lambda item: (-int(item["score"]), str(item["entry"].id)))
    context.update(
        {
            "page_title": "Revisar movimento",
            "movement": movement,
            "movement_form": form,
            "journal_entry": movement.journal_entries.exclude(
                state=JournalEntry.State.INVALID
            ).first(),
            "reconciliation_candidates": suggestions,
            "movement_reconciliations": reconciliations,
            "reconciliation_suggestions": suggestions,
            "reconciliation_suggestion_state": (
                "unique" if len(suggestions) == 1 else "ambiguous" if suggestions else "none"
            ),
        }
    )
    return render(request, "hub/reconciliation_movement.html", context)


@office_required
@require_http_methods(["POST"])
def reconciliation_export_create(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    if not context["support_can_mutate"] or not _can_manage_reconciliation(context):
        return refuse(request, "Seu perfil pode consultar, mas não exportar lançamentos.")
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    company = get_object_or_404(companies, id=request.POST.get("company_id"))
    try:
        start = datetime.strptime(request.POST.get("period_start", ""), "%Y-%m-%d").date()
        end = datetime.strptime(request.POST.get("period_end", ""), "%Y-%m-%d").date()
        if end < start:
            raise ValueError
        reexport_of = None
        original_id = request.POST.get("reexport_of", "")
        if original_id:
            reexport_of = get_object_or_404(
                AccountingExport,
                id=original_id,
                organization=office,
                company=company,
            )
        export = create_export(
            organization=office,
            company=company,
            start=start,
            end=end,
            actor=request.user,
            reexport_of=reexport_of,
            reexport_reason=request.POST.get("reexport_reason", ""),
            request=request,
        )
    except (ValueError, ReconciliationError) as exc:
        messages.error(request, str(exc) or "Período inválido.")
    else:
        messages.success(request, f"Arquivo gerado com hash {export.content_hash[:12]}.")
    return redirect("hub:reconciliation")


@office_required
@require_http_methods(["GET"])
def reconciliation_export_download(request: HttpRequest, export_id: str) -> FileResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        raise Http404
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    export = get_object_or_404(
        AccountingExport,
        id=export_id,
        organization=office,
        company__in=companies,
        state=AccountingExport.State.READY,
    )
    response = FileResponse(
        export.content.open("rb"), as_attachment=True, filename=PurePath(export.content.name).name
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@office_required
def reform(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.REFORM))
    if blocked:
        return blocked
    source = request.GET.get("fonte", "")
    search_term = request.GET.get("q", "").strip()[:100]
    relevance = request.GET.get("relevancia", "")
    valid_sources = set(ReformAlert.Source.values)
    valid_relevance = {ReformAlert.Relevance.REFORM, ReformAlert.Relevance.FISCAL}
    office = cast(Organization, context["office"])
    if is_demo_visitor(request, office):
        demo_alerts = _demo_reform_alerts()
        if source in valid_sources:
            demo_alerts = [alert for alert in demo_alerts if alert.source == source]
        else:
            source = ""
        if relevance in valid_relevance:
            demo_alerts = [alert for alert in demo_alerts if alert.relevance == relevance]
        else:
            relevance = ""
        if search_term:
            needle = search_term.casefold()
            demo_alerts = [
                alert
                for alert in demo_alerts
                if needle in f"{alert.title} {alert.summary}".casefold()
            ]
        last_success = timezone.now() - timedelta(hours=3)
        demo_statuses = {
            value: SimpleNamespace(last_success_at=last_success, last_error="")
            for value in ReformAlert.Source.values
        }
        context.update(
            {
                "page_title": "Radar da Reforma Tributária",
                "alerts": demo_alerts,
                "alert_total": len(demo_alerts),
                "radar_search": search_term,
                "selected_source": source,
                "selected_relevance": relevance,
                "sources": ReformAlert.Source.choices,
                "relevances": [
                    (ReformAlert.Relevance.REFORM, ReformAlert.Relevance.REFORM.label),
                    (ReformAlert.Relevance.FISCAL, ReformAlert.Relevance.FISCAL.label),
                ],
                "source_health": [
                    (value, label, demo_statuses[value])
                    for value, label in ReformAlert.Source.choices
                ],
                "radar_demo": True,
            }
        )
        return render(request, "hub/reform.html", context)
    alerts = ReformAlert.objects.exclude(relevance=ReformAlert.Relevance.GENERAL)
    if source in valid_sources:
        alerts = alerts.filter(source=source)
    else:
        source = ""
    if relevance in valid_relevance:
        alerts = alerts.filter(relevance=relevance)
    else:
        relevance = ""
    if search_term:
        alerts = alerts.filter(Q(title__icontains=search_term) | Q(summary__icontains=search_term))
    alert_total = alerts.count()
    statuses_by_source = {status.source: status for status in ReformSourceStatus.objects.all()}
    context.update(
        {
            "page_title": "Radar da Reforma Tributária",
            "alerts": alerts[:80],
            "alert_total": alert_total,
            "radar_search": search_term,
            "selected_source": source,
            "selected_relevance": relevance,
            "sources": ReformAlert.Source.choices,
            "relevances": [
                (ReformAlert.Relevance.REFORM, ReformAlert.Relevance.REFORM.label),
                (ReformAlert.Relevance.FISCAL, ReformAlert.Relevance.FISCAL.label),
            ],
            "source_health": [
                (value, label, statuses_by_source.get(value))
                for value, label in ReformAlert.Source.choices
            ],
            "radar_demo": False,
        }
    )
    return render(request, "hub/reform.html", context)


def _demo_reform_alerts() -> list[SimpleNamespace]:
    """Synthetic headlines linked only to official source landing pages."""

    today = timezone.now()
    rows = (
        (
            ReformAlert.Source.RFB,
            ReformAlert.Relevance.REFORM,
            "Exemplo fictício: orientações operacionais sobre CBS",
            "Cenário demonstrativo para mostrar pesquisa, fonte e data.",
            "https://www.gov.br/receitafederal/pt-br/assuntos/noticias",
            1,
        ),
        (
            ReformAlert.Source.FAZENDA,
            ReformAlert.Relevance.REFORM,
            "Exemplo fictício: cronograma de implantação do IBS",
            "Cenário demonstrativo; confirme qualquer informação na fonte oficial.",
            "https://www.gov.br/fazenda/pt-br/canais_atendimento/imprensa",
            3,
        ),
        (
            ReformAlert.Source.PLANALTO,
            ReformAlert.Relevance.FISCAL,
            "Exemplo fictício: publicação de norma tributária",
            "Cenário demonstrativo sem valor jurídico ou atualização normativa.",
            "https://www.gov.br/planalto/pt-br/acompanhe-o-planalto/noticias",
            6,
        ),
    )
    source_labels = dict(ReformAlert.Source.choices)
    return [
        SimpleNamespace(
            source=source,
            relevance=relevance,
            title=title,
            summary=summary,
            source_url=source_url,
            published_at=today - timedelta(days=age),
            created_at=today - timedelta(days=age),
            get_source_display=lambda current=source: source_labels[current],
        )
        for source, relevance, title, summary, source_url, age in rows
    ]


@office_required
@require_http_methods(["GET"])
def triage(request: HttpRequest) -> HttpResponse:
    context, blocked = _triage_page_context(request)
    if blocked:
        return blocked
    context["imap_form"] = IMAPConnectionForm()
    return render(request, "hub/triage.html", context)


@office_required
@require_http_methods(["GET"])
def triage_connections(request: HttpRequest) -> HttpResponse:
    context, blocked = _triage_page_context(request)
    if blocked:
        return blocked
    context["page_title"] = "Caixas de e-mail da Triagem"
    context["imap_form"] = IMAPConnectionForm()
    return render(request, "hub/triage_connections.html", context)


def _demo_triage_base_status(item: TriageItem) -> str | None:
    if item.message_id == "demo-triage-1" and item.part_id == "1":
        return TriageStatus.AWAITING_REVIEW
    if item.message_id == "demo-triage-2" and item.part_id == "1":
        return TriageStatus.QUARANTINED
    return None


def _demo_triage_for_view(request: HttpRequest, item: TriageItem) -> TriageItem:
    """Present the immutable seed plus this visitor's private fictitious progress."""

    if not is_demo_visitor(request, item.organization):
        return item
    base_status = _demo_triage_base_status(item)
    if base_status is None:
        raise Http404
    entry = get_progress(request, "triage", item.id)
    status = entry.get("status")
    item.status = (
        status
        if status
        in {
            TriageStatus.READY_TO_ARCHIVE,
            TriageStatus.ARCHIVED,
            TriageStatus.REJECTED,
        }
        and base_status == TriageStatus.AWAITING_REVIEW
        else base_status
    )
    item.rejection_reason = str(entry.get("reason", ""))[:500]
    item.reviewed_by = request.user if item.status != base_status else None
    item.reviewed_at = parse_datetime(str(entry.get("reviewed_at", "")))
    item.archived_at = parse_datetime(str(entry.get("archived_at", "")))
    item.destination_kind = "internal" if item.status == TriageStatus.ARCHIVED else ""
    return item


def _triage_page_context(request: HttpRequest) -> tuple[dict[str, object], HttpResponse | None]:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return context, blocked
    office = context["office"]
    assert isinstance(office, Organization)
    mailboxes = Mailbox.objects.filter(organization=office).order_by("provider", "address")
    mailbox_rows = [
        present_mailbox(mailbox, poll_enabled=settings.TRIAGE_EMAIL_POLL_ENABLED)
        for mailbox in mailboxes
    ]
    for mailbox in mailboxes:
        mailbox.operation_form = MailboxOperationForm(  # type: ignore[attr-defined]
            mailbox=mailbox
        )
    queue_scope = Q(company__in=context["companies"])
    if _can_manage_collaborators(context):
        queue_scope |= Q(company__isnull=True)
    queue = (
        TriageItem.objects.filter(organization=office)
        .filter(queue_scope)
        .select_related("company", "mailbox", "safety_scan")
    )
    selected_status = request.GET.get("status", "")
    if selected_status not in TriageItem.Status.values:
        selected_status = ""
    queue_search = request.GET.get("q", "").strip()[:100]
    if is_demo_visitor(request, office):
        visible = [
            _demo_triage_for_view(request, item)
            for item in queue.order_by("-created_at", "-pk")
            if _demo_triage_base_status(item) is not None
        ]
        filtered_queue = [
            item
            for item in visible
            if (not selected_status or item.status == selected_status)
            and (
                not queue_search
                or queue_search.casefold()
                in " ".join(
                    [
                        item.original_name,
                        item.company.name if item.company else "",
                        item.company.dominio_code if item.company else "",
                        item.mailbox.address if item.mailbox else "",
                    ]
                ).casefold()
            )
        ]
        queue_total = len(visible)
        queue_quarantined = sum(item.status == TriageStatus.QUARANTINED for item in visible)
    else:
        filtered_queue = queue.filter(status=selected_status) if selected_status else queue
        if queue_search:
            filtered_queue = filtered_queue.filter(
                Q(original_name__icontains=queue_search)
                | Q(company__name__icontains=queue_search)
                | Q(company__dominio_code__icontains=queue_search)
                | Q(mailbox__address__icontains=queue_search)
            )
        filtered_queue = filtered_queue.order_by("-created_at", "-pk")
        queue_total = queue.count()
        queue_quarantined = queue.filter(status=TriageStatus.QUARANTINED).count()
    queue_page = Paginator(filtered_queue, 20).get_page(request.GET.get("page"))
    apps = {app.provider: app for app in MailboxOAuthApp.objects.filter(organization=office)}
    ms_app = apps.get(Mailbox.Provider.MS365_GRAPH)
    google_app = apps.get(Mailbox.Provider.GMAIL_API)
    try:
        ms_callback = redirect_uri(Mailbox.Provider.MS365_GRAPH)
        google_callback = redirect_uri(Mailbox.Provider.GMAIL_API)
    except MailboxOAuthError:
        ms_callback = google_callback = ""
    context.update(
        {
            "page_title": "Triagem de Arquivos",
            "mailboxes": mailboxes,
            "mailbox_rows": mailbox_rows,
            "triage_queue_page": queue_page,
            "triage_queue_total": queue_total,
            "triage_queue_quarantined": queue_quarantined,
            "triage_queue_selected_status": selected_status,
            "triage_queue_search": queue_search,
            "triage_queue_status_choices": TriageItem.Status.choices,
            "triage_email_poll_enabled": settings.TRIAGE_EMAIL_POLL_ENABLED,
            "authorized_mailboxes_exist": mailboxes.filter(status=Mailbox.Status.ACTIVE).exists(),
            "mailbox_error_exists": mailboxes.filter(status=Mailbox.Status.ERROR).exists(),
            "can_manage_mailboxes": _can_manage_collaborators(context),
            "ms_app": ms_app,
            "google_app": google_app,
            "ms_app_form": OfficeOAuthAppForm(provider=Mailbox.Provider.MS365_GRAPH),
            "google_app_form": OfficeOAuthAppForm(provider=Mailbox.Provider.GMAIL_API),
            "ms_callback": ms_callback,
            "google_callback": google_callback,
            "ms_oauth_ready": bool(ms_callback and ms_app is not None and ms_app.active),
            "google_oauth_ready": bool(
                google_callback
                and (
                    (google_app is not None and google_app.active)
                    or (
                        settings.TRIAGE_GOOGLE_OAUTH_ENABLED
                        and settings.TRIAGE_GOOGLE_CLIENT_ID
                        and settings.TRIAGE_GOOGLE_CLIENT_SECRET
                    )
                )
            ),
            "google_workspace_ready": bool(
                google_callback and google_app is not None and google_app.active
            ),
            "google_personal_ready": bool(
                google_callback
                and settings.TRIAGE_GOOGLE_OAUTH_ENABLED
                and settings.TRIAGE_GOOGLE_CLIENT_ID
                and settings.TRIAGE_GOOGLE_CLIENT_SECRET
                and settings.TRIAGE_GOOGLE_PERSONAL_VERIFIED
            ),
            "destination_profile": DestinationProfile.objects.filter(organization=office).first(),
        }
    )
    context["destination_form"] = DestinationProfileForm(  # type: ignore[assignment]
        profile=context["destination_profile"]
    )
    return context, None


@office_required
@require_http_methods(["POST"])
def triage_oauth_app_save(request: HttpRequest, provider: str) -> HttpResponse:
    context, blocked = _triage_page_context(request)
    if blocked:
        return blocked
    if context["office"].is_demo:
        return refuse(request, "A demonstração fictícia não aceita aplicativos ou caixas reais.")
    if not _can_manage_collaborators(context):
        return refuse(request, "Somente o administrador configura o aplicativo de e-mail.")
    if provider not in (Mailbox.Provider.MS365_GRAPH, Mailbox.Provider.GMAIL_API):
        raise Http404
    form = OfficeOAuthAppForm(request.POST, provider=provider)
    context["imap_form"] = IMAPConnectionForm()
    context["ms_app_form" if provider == Mailbox.Provider.MS365_GRAPH else "google_app_form"] = form
    if not form.is_valid():
        return render(request, "hub/triage_connections.html", context, status=400)
    office = context["office"]
    assert isinstance(office, Organization)
    if Mailbox.objects.filter(
        organization=office,
        provider=provider,
        oauth_app__isnull=False,
        status=Mailbox.Status.ACTIVE,
    ).exists():
        form.add_error(None, "Desconecte as caixas deste provedor antes de trocar o aplicativo.")
        return render(request, "hub/triage_connections.html", context, status=409)
    with transaction.atomic():
        app, _ = MailboxOAuthApp.objects.update_or_create(
            organization=office,
            provider=provider,
            defaults={
                "client_id": form.cleaned_data["client_id"],
                "client_secret": form.cleaned_data["client_secret"],
                "tenant_id": form.cleaned_data.get("tenant_id", ""),
                "active": True,
            },
        )
    record_event(
        action="triage.oauth_app.configured",
        actor=request.user,
        organization=office,
        target=app,
        request=request,
        metadata={"provider": provider},
    )
    callback_ready = context[
        "ms_callback" if provider == Mailbox.Provider.MS365_GRAPH else "google_callback"
    ]
    if callback_ready:
        messages.success(request, "Aplicativo salvo. Agora conecte a caixa deste provedor.")
    else:
        messages.success(
            request,
            "Aplicativo salvo. A conexão ficará disponível após a Mewstack "
            "definir o retorno HTTPS.",
        )
    return redirect("hub:triage-connections")


@office_required
@require_http_methods(["POST"])
def triage_imap_connect(request: HttpRequest) -> HttpResponse:
    context, blocked = _triage_page_context(request)
    if blocked:
        return blocked
    if context["office"].is_demo:
        return refuse(request, "A demonstração fictícia não testa servidores IMAP reais.")
    if not _can_manage_collaborators(context):
        return refuse(request, "Somente o administrador do escritório conecta caixas de e-mail.")
    form = IMAPConnectionForm(request.POST)
    context["imap_form"] = form
    if not form.is_valid():
        return render(request, "hub/triage_connections.html", context)
    if rate_limited(f"triage-imap:{request.user.id}", limit=5, window_seconds=60):
        form.add_error(None, "Muitas tentativas. Aguarde 1 minuto e tente novamente.")
        return render(request, "hub/triage_connections.html", context, status=429)
    host = str(form.cleaned_data["host"])
    address = str(form.cleaned_data["address"]).casefold()
    username = str(form.cleaned_data["username"] or address)
    password = str(form.cleaned_data["password"])
    folder = str(form.cleaned_data["folder"])
    try:
        probe_imap_mailbox(host=host, username=username, password=password, folder=folder)
    except MailboxIMAPError as exc:
        form.add_error(None, str(exc))
        return render(request, "hub/triage_connections.html", context)
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
    return redirect("hub:triage-connections")


@office_required
@require_http_methods(["POST"])
def triage_oauth_start(request: HttpRequest, provider: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    if context["office"].is_demo:
        return refuse(request, "A demonstração fictícia não solicita autorização de e-mail real.")
    if not _can_manage_collaborators(context):
        return refuse(request, "Somente o administrador do escritório conecta caixas de e-mail.")
    office = context["office"]
    assert isinstance(office, Organization)
    app = MailboxOAuthApp.objects.filter(
        organization=office, provider=provider, active=True
    ).first()
    source = request.POST.get("oauth_source", "").strip()
    if source and source not in {"office", "mewstack"}:
        messages.error(request, "Escolha uma conexão de e-mail válida.")
        return redirect("hub:triage-connections")
    if source == "office" and app is None:
        messages.error(request, "Configure o aplicativo deste escritório primeiro.")
        return redirect("hub:triage-connections")
    if source == "mewstack":
        if provider != Mailbox.Provider.GMAIL_API:
            messages.error(request, "O aplicativo compartilhado é reservado ao Gmail pessoal.")
            return redirect("hub:triage-connections")
        app = None
    source = source or ("office" if app is not None else "mewstack")
    if (
        source == "mewstack"
        and provider == Mailbox.Provider.GMAIL_API
        and not settings.TRIAGE_GOOGLE_PERSONAL_VERIFIED
    ):
        messages.error(request, "A conexão Gmail pessoal ainda aguarda verificação Google.")
        return redirect("hub:triage-connections")
    try:
        url, state, verifier = new_authorization(provider, app=app)
    except MailboxOAuthError as exc:
        messages.error(request, str(exc))
        return redirect("hub:triage-connections")
    request.session["triage_oauth_flow"] = {
        "provider": provider,
        "app_id": str(app.id) if app else "",
        "client_id": app.client_id if app else "",
        "oauth_source": source,
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
    if office.is_demo:
        messages.error(request, "A demonstração fictícia não recebe autorização de e-mail real.")
        return _triage_oauth_return()
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
    app = None
    if flow.get("app_id"):
        app = MailboxOAuthApp.objects.filter(
            id=flow["app_id"], organization=office, provider=provider, active=True
        ).first()
        if app is None or app.client_id != flow.get("client_id"):
            messages.error(request, "O aplicativo mudou durante a autorização. Conecte novamente.")
            return _triage_oauth_return()
    try:
        access_token, refresh_token = exchange_code(
            provider, code=request.GET.get("code", ""), verifier=flow["verifier"], app=app
        )
        address = probe_mailbox(provider, access_token=access_token, app=app)
        if (
            provider == Mailbox.Provider.GMAIL_API
            and flow.get("oauth_source") == "mewstack"
            and address.rsplit("@", 1)[-1] not in {"gmail.com", "googlemail.com"}
        ):
            raise MailboxOAuthError("Use uma conta Gmail pessoal neste caminho de conexão.")
        if (
            provider == Mailbox.Provider.GMAIL_API
            and flow.get("oauth_source") == "office"
            and address.rsplit("@", 1)[-1] in {"gmail.com", "googlemail.com"}
        ):
            raise MailboxOAuthError("Use a conexão Gmail pessoal da Mewstack para esta conta.")
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
                "oauth_app": app,
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
    response = redirect("hub:triage-connections")
    response["Cache-Control"] = "no-store"
    response["Referrer-Policy"] = "no-referrer"
    return response


@office_required
@require_http_methods(["POST"])
def triage_mailbox_configure(request: HttpRequest, mailbox_id: str) -> HttpResponse:
    context, blocked = _triage_page_context(request)
    if blocked:
        return blocked
    if context["office"].is_demo:
        return refuse(request, "A demonstração não configura caixas externas.")
    if not _can_manage_collaborators(context):
        return refuse(request, "Somente o administrador configura a leitura da caixa.")
    office = cast(Organization, context["office"])
    mailbox = get_object_or_404(Mailbox, organization=office, id=mailbox_id)
    form = MailboxOperationForm(request.POST, mailbox=mailbox)
    if not form.is_valid():
        for row in context["mailbox_rows"]:
            if row.mailbox.id == mailbox.id:
                row.mailbox.operation_form = form  # type: ignore[attr-defined]
                break
        return render(request, "hub/triage_connections.html", context, status=400)
    if (
        Mailbox.objects.filter(
            organization=office,
            provider=mailbox.provider,
            address=mailbox.address,
            folder=form.cleaned_data["folder"],
        )
        .exclude(id=mailbox.id)
        .exists()
    ):
        form.add_error("folder", "Esta caixa já usa essa pasta ou etiqueta.")
        for row in context["mailbox_rows"]:
            if row.mailbox.id == mailbox.id:
                row.mailbox.operation_form = form  # type: ignore[attr-defined]
                break
        return render(request, "hub/triage_connections.html", context, status=409)
    since = timezone.make_aware(datetime.combine(form.cleaned_data["since"], time.min))
    reset_checkpoint = mailbox.folder != form.cleaned_data["folder"] or mailbox.since != since
    mailbox.folder = form.cleaned_data["folder"]
    mailbox.since = since
    mailbox.sender_filter = str(form.cleaned_data["sender_filter"]).strip()
    mailbox.subject_filter = str(form.cleaned_data["subject_filter"]).strip()
    mailbox.active = bool(form.cleaned_data["active"])
    fields = [
        "folder",
        "since",
        "sender_filter",
        "subject_filter",
        "active",
        "updated_at",
    ]
    if reset_checkpoint:
        mailbox.cursor = ""
        mailbox.last_polled_at = None
        mailbox.poll_retry_after = None
        mailbox.poll_failure_count = 0
        mailbox.last_error = ""
        fields.extend(
            [
                "cursor",
                "last_polled_at",
                "poll_retry_after",
                "poll_failure_count",
                "last_error",
            ]
        )
    mailbox.save(update_fields=fields)
    record_event(
        action="triage.mailbox.operation_configured",
        actor=request.user,
        organization=office,
        target=mailbox,
        request=request,
        metadata={
            "provider": mailbox.provider,
            "active": mailbox.active,
            "folder": mailbox.folder,
            "since": mailbox.since.date().isoformat(),
            "sender_filter_enabled": bool(mailbox.sender_filter),
            "subject_filter_enabled": bool(mailbox.subject_filter),
            "checkpoint_reset": reset_checkpoint,
        },
    )
    if mailbox.active and settings.TRIAGE_EMAIL_POLL_ENABLED:
        messages.success(
            request, "Leitura ativada. A primeira execução entrará na fila automática."
        )
    elif mailbox.active:
        messages.success(
            request,
            "Caixa pronta para leitura. A execução periódica desta instalação "
            "ainda está desligada.",
        )
    else:
        messages.success(request, "Configuração salva e leitura pausada.")
    return redirect("hub:triage-connections")


@office_required
@require_http_methods(["POST"])
def triage_destination_configure(request: HttpRequest) -> HttpResponse:
    context, blocked = _triage_page_context(request)
    if blocked:
        return blocked
    if context["office"].is_demo:
        return refuse(request, "A demonstração não altera o destino do escritório.")
    if not _can_manage_collaborators(context):
        return refuse(request, "Somente o administrador define o destino dos arquivos.")
    office = cast(Organization, context["office"])
    current = DestinationProfile.objects.filter(organization=office).first()
    form = DestinationProfileForm(request.POST, profile=current)
    if not form.is_valid():
        context["destination_form"] = form
        return render(request, "hub/triage_connections.html", context, status=400)
    profile, _ = DestinationProfile.objects.update_or_create(
        organization=office,
        defaults={
            "mode": form.cleaned_data["mode"],
            "windows_root": form.cleaned_data["windows_root"],
            "folder_template": form.cleaned_data["folder_template"],
        },
    )
    record_event(
        action="triage.destination.configured",
        actor=request.user,
        organization=office,
        target=profile,
        request=request,
        metadata={"mode": profile.mode, "windows_root_configured": bool(profile.windows_root)},
    )
    if profile.mode == DestinationProfile.Mode.WINDOWS:
        messages.success(
            request,
            "Pasta Windows salva. A escrita só será liberada depois que o agente "
            "local validar essa raiz.",
        )
    else:
        messages.success(
            request, "Biblioteca interna definida como destino dos arquivos aprovados."
        )
    return redirect("hub:triage-connections")


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
    return redirect("hub:triage-connections")


@office_required
@require_http_methods(["GET", "POST"])
def triage_item_detail(request: HttpRequest, item_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = context["office"]
    assert isinstance(office, Organization)
    item_scope = Q(company__in=context["companies"])
    if _can_manage_collaborators(context):
        item_scope |= Q(company__isnull=True)
    item = get_object_or_404(
        TriageItem.objects.select_related(
            "company", "document_type", "reviewed_by", "blob", "mailbox", "safety_scan"
        )
        .prefetch_related("events__actor")
        .filter(item_scope),
        organization=office,
        id=item_id,
    )
    visitor = is_demo_visitor(request, office)
    if visitor:
        _demo_triage_for_view(request, item)
    if request.method == "POST":
        if not context["support_can_mutate"] or item.company is None:
            return refuse(request, "Este perfil não pode decidir o destino deste arquivo.")
        decision = request.POST.get("decision", "")
        success_message = "Decisão registrada com evidência no histórico do arquivo."
        try:
            if decision == "reject" and request.POST.get("confirm_rejection") != "on":
                raise ValidationError("Confirme a rejeição e registre o motivo antes de enviar.")
            if visitor:
                if item.message_id != "demo-triage-1":
                    raise InvalidTransition("Este anexo fictício permanece em quarentena.")
                if decision in {"archive", "reject"}:
                    if item.status != TriageStatus.AWAITING_REVIEW:
                        raise InvalidTransition("Este anexo já recebeu uma decisão nesta sessão.")
                    reason = request.POST.get("reason", "").strip()[:500]
                    if decision == "reject" and not reason:
                        raise ValidationError("Informe o motivo da rejeição.")
                    scan = item.safety_scan
                    if decision == "archive" and (
                        scan.verdict != scan.Verdict.CLEAN
                        or scan.format_verdict != scan.FormatVerdict.VALID
                    ):
                        raise ValidationError("A verificação fictícia ainda não liberou o anexo.")
                    status = (
                        TriageStatus.READY_TO_ARCHIVE
                        if decision == "archive"
                        else TriageStatus.REJECTED
                    )
                    entry = {
                        "status": status,
                        "reason": reason,
                        "reviewed_at": timezone.now().isoformat(),
                        "history": [{"status": status, "note": reason or "Aprovado pelo revisor"}],
                    }
                elif decision == "finish_archive":
                    if item.status != TriageStatus.READY_TO_ARCHIVE:
                        raise InvalidTransition("Aprove o anexo antes de arquivar.")
                    entry = dict(get_progress(request, "triage", item.id))
                    entry["status"] = TriageStatus.ARCHIVED
                    entry["archived_at"] = timezone.now().isoformat()
                    entry["history"] = [
                        *entry.get("history", []),
                        {
                            "status": TriageStatus.ARCHIVED,
                            "note": "Arquivo fictício pronto para download nesta sessão",
                        },
                    ]
                else:
                    raise ValidationError("Escolha uma decisão válida para o arquivo.")
                put_progress(request, "triage", item.id, entry)
            elif decision in {"archive", "reject"}:
                decide_item(
                    item=item,
                    actor=cast(User, request.user),
                    decision=decision,
                    reason=request.POST.get("reason", ""),
                    request=request,
                )
            elif decision == "finish_archive":
                destination = DestinationProfile.objects.filter(organization=office).first()
                if destination and destination.mode == DestinationProfile.Mode.WINDOWS:
                    queue_windows_archive(
                        item=item,
                        actor=cast(User, request.user),
                        request=request,
                    )
                    success_message = (
                        "Arquivo enviado ao agente Windows. A CICA só concluirá depois de "
                        "confirmar destino, tamanho e hash."
                    )
                else:
                    archive_internal(item=item, actor=cast(User, request.user))
                    success_message = "Arquivo gravado e conferido na biblioteca interna."
            else:
                raise ValidationError("Escolha uma decisão válida para o arquivo.")
        except (ValidationError, InvalidTransition) as exc:
            messages.error(request, str(exc))
        else:
            messages.success(
                request,
                "Decisão fictícia registrada nesta sessão." if visitor else success_message,
            )
        return detail_redirect(request, "hub:triage-item", item_id=item.id)
    demo_history: list[dict[str, object]] = []
    if visitor:
        demo_history = [
            {
                "label": event.get_to_status_display(),
                "at": event.created_at,
                "actor": "",
                "note": event.note,
            }
            for event in item.events.all()
            if event.actor_id is None and event.note == "Etapa simulada da demonstração fictícia"
        ]
        for step in get_progress(request, "triage", item.id).get("history", []):
            if not isinstance(step, dict) or step.get("status") not in TriageStatus.values:
                continue
            demo_history.append(
                {
                    "label": TriageStatus(step["status"]).label,
                    "at": item.reviewed_at if len(demo_history) < 4 else item.archived_at,
                    "actor": "Visitante desta demonstração",
                    "note": str(step.get("note", ""))[:500],
                }
            )
    context.update(
        {
            "page_title": "Arquivo em triagem",
            "item": item,
            "demo_history": demo_history,
            "demo_visitor": visitor,
            "triage_destination": DestinationProfile.objects.filter(organization=office).first(),
            "triage_agent_job": item.agent_jobs.order_by("-created_at").first(),
            "triage_agent_online": EdgeAgent.objects.filter(
                organization=office,
                status=EdgeAgent.Status.ACTIVE,
                last_seen_at__gte=timezone.now() - timedelta(minutes=5),
            ).exists(),
        }
    )
    return render(request, "hub/triage_item.html", context)


@office_required
@require_http_methods(["GET"])
def triage_download(request: HttpRequest, item_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        raise Http404
    office = context["office"]
    assert isinstance(office, Organization)
    item = get_object_or_404(
        TriageItem.objects.all(),
        organization=office,
        company__in=context["companies"],
        id=item_id,
    )
    if is_demo_visitor(request, office):
        _demo_triage_for_view(request, item)
        if item.status != TriageStatus.ARCHIVED or item.message_id != "demo-triage-1":
            raise Http404
        from io import BytesIO

        item = TriageItem.objects.select_related("blob", "safety_scan").get(pk=item.pk)
        if (
            item.safety_scan.verdict != item.safety_scan.Verdict.CLEAN
            or item.safety_scan.format_verdict != item.safety_scan.FormatVerdict.VALID
        ):
            raise Http404
        with item.blob.content.open("rb") as source:
            payload = source.read(10 * 1024 * 1024 + 1)
        if (
            len(payload) > 10 * 1024 * 1024
            or hashlib.sha256(payload).hexdigest() != item.content_hash
        ):
            raise Http404
        response = FileResponse(
            BytesIO(payload),
            as_attachment=True,
            filename=f"DEMO-{item.final_name}",
            content_type="application/octet-stream",
        )
        response["Cache-Control"] = "no-store, private"
        response["X-Content-Type-Options"] = "nosniff"
        return response
    try:
        stream = open_verified_internal_copy(item=item)
    except ValidationError:
        raise Http404 from None
    response = FileResponse(
        stream,
        as_attachment=True,
        filename=item.final_name,
        content_type="application/octet-stream",
    )
    response["Cache-Control"] = "no-store, private"
    response["X-Content-Type-Options"] = "nosniff"
    record_event(
        action="triage.item.downloaded_internal",
        actor=cast(User, request.user),
        organization=office,
        target=item,
        request=request,
        metadata={"content_hash": item.content_hash},
    )
    return response


@office_required
@require_http_methods(["GET", "POST"])
def companies(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    membership = context["membership"]
    can_manage_companies = bool(
        context["support_can_mutate"]
        and (
            (context["support_session"] is not None and _sees_every_company(context))
            or (
                isinstance(membership, Membership)
                and membership.role != Membership.Role.BILLING
                and (
                    membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
                    or _sees_every_company(context)
                )
            )
        )
    )
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
    if request.method == "POST" and not can_manage_companies:
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
        with transaction.atomic():
            company.save()
            if (
                isinstance(membership, Membership)
                and CompanyAccessGrant.objects.filter(
                    membership=membership, organization=office, is_active=True
                ).exists()
            ):
                CompanyAccessGrant.objects.create(
                    organization=office,
                    membership=membership,
                    company=company,
                    modules=list(OFFERED_MODULE_CODES),
                    capabilities=["*"],
                )
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
    scope_total = rows.count()
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
            "office_company_total": scope_total,
            "can_manage_companies": can_manage_companies,
            "require_dominio_code": require_dominio_code,
            "dominio_manages_companies": dominio_manages_companies,
            "form": form,
        }
    )
    return render(request, "hub/companies.html", context)


def _sees_every_company(context: dict[str, object]) -> bool:
    """Only widen the active portfolio for an explicitly unscoped workspace."""

    office = context["office"]
    support = context.get("support_session")
    if isinstance(support, SupportSession):
        return not support.company_ids
    return (
        isinstance(office, Organization)
        and not ControlPlaneBinding.objects.filter(organization=office).exists()
        and not CompanyAccessGrant.objects.filter(
            organization=office, membership=context.get("membership"), is_active=True
        ).exists()
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
    demo_certificate_mode = is_demo_visitor(request, office)
    form = CertificateUploadForm(
        request.POST or None,
        request.FILES or None,
        organization=office,
        companies=ClientCompany.objects.filter(
            id__in=[company.id for company in allowed_companies]
        ),
    )
    if request.method == "POST" and demo_certificate_mode:
        demo_company = allowed_companies.filter(
            id=request.POST.get("demo_company_id"), active=True
        ).first()
        if demo_company is None:
            messages.error(request, "Escolha uma empresa válida para simular o certificado.")
        else:
            put_progress(
                request,
                "certificates",
                demo_company.id,
                {"simulated": True, "created_at": timezone.now().isoformat()},
            )
            messages.success(
                request,
                f"Certificado fictício registrado para {demo_company.name} nesta sessão.",
            )
        return redirect("hub:certificates")
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
    now = timezone.now()
    expires_soon_at = now + timedelta(days=30)
    certificate_search = request.GET.get("q", "").strip()[:100]
    certificate_status = request.GET.get("status", "attention")
    valid_certificate_statuses = {
        "attention",
        "valid",
        "expiring",
        "expired",
        "revoked",
        "unknown",
        "all",
    }
    if certificate_status not in valid_certificate_statuses:
        certificate_status = "attention"
    certificate_base = Certificate.objects.filter(
        organization=office, company__in=allowed_companies
    ).select_related("company")
    certificates_query = certificate_base
    if certificate_search:
        certificates_query = certificates_query.filter(
            Q(company__name__icontains=certificate_search)
            | Q(company__cnpj_masked__icontains=certificate_search)
            | Q(company__dominio_code__icontains=certificate_search)
            | Q(label__icontains=certificate_search)
            | Q(subject_name__icontains=certificate_search)
        )
    if certificate_status == "attention":
        certificates_query = certificates_query.filter(
            Q(revoked_at__isnull=False)
            | Q(valid_until__lt=expires_soon_at)
            | Q(valid_until__isnull=True)
        )
    elif certificate_status == "valid":
        certificates_query = certificates_query.filter(
            revoked_at__isnull=True, valid_until__gte=expires_soon_at
        )
    elif certificate_status == "expiring":
        certificates_query = certificates_query.filter(
            revoked_at__isnull=True,
            valid_until__gte=now,
            valid_until__lt=expires_soon_at,
        )
    elif certificate_status == "expired":
        certificates_query = certificates_query.filter(revoked_at__isnull=True, valid_until__lt=now)
    elif certificate_status == "revoked":
        certificates_query = certificates_query.filter(revoked_at__isnull=False)
    elif certificate_status == "unknown":
        certificates_query = certificates_query.filter(
            revoked_at__isnull=True, valid_until__isnull=True
        )
    certificate_filtered_total = certificates_query.count()
    certificate_page = Paginator(
        certificates_query.order_by("valid_until", "company__name", "label"), 50
    ).get_page(request.GET.get("page"))
    usable_company_ids = list(
        certificate_base.filter(revoked_at__isnull=True, valid_until__gte=now).values_list(
            "company_id", flat=True
        )
    )
    simulated_company_ids: list[str] = []
    if demo_certificate_mode:
        simulated_company_ids = [
            company_id
            for company_id, entry in get_section(request, "certificates").items()
            if entry.get("simulated")
        ]
    missing_companies = allowed_companies.filter(active=True).exclude(id__in=usable_company_ids)
    if simulated_company_ids:
        missing_companies = missing_companies.exclude(id__in=simulated_company_ids)
    simulated_companies = list(
        allowed_companies.filter(id__in=simulated_company_ids).order_by("name")
    )
    certificate_filters = {"q": certificate_search, "status": certificate_status}
    context.update(
        {
            "page_title": "Certificados",
            "certificates": certificate_page,
            "certificate_page": certificate_page,
            "certificate_filtered_total": certificate_filtered_total,
            "certificate_search": certificate_search,
            "certificate_status": certificate_status,
            "certificate_query_without_page": urlencode(certificate_filters),
            "certificate_stats": {
                "valid": certificate_base.filter(
                    revoked_at__isnull=True, valid_until__gte=expires_soon_at
                ).count()
                + len(simulated_companies),
                "expiring": certificate_base.filter(
                    revoked_at__isnull=True,
                    valid_until__gte=now,
                    valid_until__lt=expires_soon_at,
                ).count(),
                "expired_or_revoked": certificate_base.filter(
                    Q(revoked_at__isnull=False) | Q(valid_until__lt=now)
                ).count(),
                "missing_companies": missing_companies.count(),
            },
            "missing_certificate_companies": missing_companies.order_by("name")[:20],
            "demo_certificate_mode": demo_certificate_mode,
            "demo_simulated_certificate_companies": simulated_companies,
            "form": form,
            "support_can_mutate": context["support_can_mutate"],
            "today": now,
            "expires_soon_at": expires_soon_at,
        }
    )
    return render(request, "hub/certificates.html", context)


@office_required
def reviews(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    review_search = request.GET.get("q", "").strip()[:100]
    review_status = request.GET.get("status", ReviewCase.Status.OPEN)
    if review_status not in {"all", *ReviewCase.Status.values}:
        review_status = ReviewCase.Status.OPEN
    confidence = request.GET.get("confidence", "all")
    if confidence not in {"all", "low", "high"}:
        confidence = "all"
    cases = ReviewCase.objects.filter(
        organization=office,
        document__company__in=scope,
    ).select_related("document", "document__company", "resolved_by")
    if review_search:
        cases = cases.filter(
            Q(document__company__name__icontains=review_search)
            | Q(document__company__dominio_code__icontains=review_search)
            | Q(document__source_nsu__icontains=review_search)
            | Q(reason__icontains=review_search)
            | Q(suggested_accumulator__icontains=review_search)
        )
    if confidence == "low":
        cases = cases.filter(confidence__lt=80)
    elif confidence == "high":
        cases = cases.filter(confidence__gte=80)
    if is_demo_visitor(request, office):
        demo_cases = [
            _demo_review_for_view(request, review)
            for review in cases.order_by("status", "confidence", "-created_at")
        ]
        if review_status != "all":
            demo_cases = [review for review in demo_cases if review.status == review_status]
        filtered_total = len(demo_cases)
        page = Paginator(demo_cases, 50).get_page(request.GET.get("page"))
    else:
        if review_status != "all":
            cases = cases.filter(status=review_status)
        filtered_total = cases.count()
        page = Paginator(cases.order_by("status", "confidence", "-created_at"), 50).get_page(
            request.GET.get("page")
        )
    context.update(
        {
            "page_title": "NFS-e",
            "cases": page,
            "review_page": page,
            "review_filtered_total": filtered_total,
            "review_search": review_search,
            "review_status": review_status,
            "review_confidence": confidence,
        }
    )
    return render(request, "hub/reviews.html", context)


def _demo_review_for_view(request: HttpRequest, review: ReviewCase) -> ReviewCase:
    """Overlay one visitor's NFS-e decision without changing the shared demo case."""

    if not is_demo_visitor(request, review.organization):
        return review
    entry = get_progress(request, "nfse_reviews", review.id)
    if entry.get("resolved"):
        review.status = ReviewCase.Status.RESOLVED
        review.resolved_accumulator = str(entry.get("accumulator", ""))[:80]
        review.resolved_by = cast(User, request.user)
        review.resolved_at = parse_datetime(str(entry.get("resolved_at", "")))
    return review


@office_required
def review_detail(request: HttpRequest, case_id: str) -> HttpResponse:
    context = workspace_context(request)
    office = cast(Organization, context["office"])
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    review = get_object_or_404(
        ReviewCase.objects.select_related("document", "document__company", "resolved_by"),
        pk=case_id,
        organization=office,
        document__company__in=scope,
    )
    _demo_review_for_view(request, review)
    membership = context["membership"]
    can_decide = bool(
        context["support_can_mutate"]
        and (
            context["support_session"] is not None
            or (
                isinstance(membership, Membership)
                and membership.role not in {Membership.Role.AUDITOR, Membership.Role.BILLING}
            )
        )
    )
    document = review.document
    evidence = document.normalized_data if isinstance(document.normalized_data, dict) else {}
    context.update(
        {
            "page_title": "Conferir NFS-e",
            "review": review,
            "can_decide_review": can_decide,
            "review_evidence": [
                ("Código de serviço", evidence.get("service_code")),
                ("Referência da contraparte", evidence.get("counterparty_ref")),
            ],
            "review_artifacts": IntegrationArtifact.objects.filter(
                organization=office, document=document
            ).order_by("created_at"),
        }
    )
    return render(request, "hub/review_detail.html", context)


@office_required
def review_original_xml(request: HttpRequest, case_id: str) -> HttpResponse:
    context = workspace_context(request)
    office = cast(Organization, context["office"])
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    review = get_object_or_404(
        ReviewCase.objects.select_related("document"),
        pk=case_id,
        organization=office,
        document__company__in=scope,
    )
    response = HttpResponse(
        review.document.original_xml, content_type="application/xml; charset=utf-8"
    )
    response["Content-Disposition"] = f'attachment; filename="nfse-{review.id}.xml"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    record_event(
        action="hub.nfse.review_original_downloaded",
        actor=request.user,
        organization=office,
        target=review,
        request=request,
    )
    return response


@office_required
@require_http_methods(["POST"])
def resolve_review(request: HttpRequest, case_id: str) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    membership = context["membership"]
    visitor = is_demo_visitor(request, office)
    if not context["support_can_mutate"] and not visitor:
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
        document__company__in=scope,
    )
    if visitor and get_progress(request, "nfse_reviews", review.id).get("resolved"):
        messages.info(request, "Esta decisão fictícia já foi registrada nesta sessão.")
        return detail_redirect(request, "hub:review-detail", case_id=review.id)
    if not visitor and review.status != ReviewCase.Status.OPEN:
        return refuse(request, "Este caso já recebeu uma decisão.")
    accumulator = request.POST.get("accumulator_code", "").strip()
    if not accumulator:
        messages.error(request, "Informe o acumulador usado para registrar a decisão.")
        return detail_redirect(request, "hub:review-detail", case_id=review.id)
    if visitor:
        put_progress(
            request,
            "nfse_reviews",
            review.id,
            {
                "resolved": True,
                "accumulator": accumulator,
                "resolved_at": timezone.now().isoformat(),
            },
        )
        messages.success(
            request,
            "Decisão fictícia registrada nesta sessão; nenhum lançamento foi alterado.",
        )
        return detail_redirect(request, "hub:review-detail", case_id=review.id)
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
    return detail_redirect(request, "hub:review-detail", case_id=review.id)


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
            "page_title": "Primeiros passos",
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
    token_book_in_effect = bool(
        active_token_book
        and active_token_book.effective_from
        and active_token_book.effective_from <= timezone.localdate()
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
    elif dominio_connector.status == "healthy" and dominio_connector.last_sync_at:
        dominio_sync_state = "synced"
    elif dominio_connector.status == "healthy":
        dominio_sync_state = "not_synced"
    else:
        dominio_sync_state = "attention"
    latest_bank_sync_metadata = (
        AuditEvent.objects.filter(
            organization=office,
            action="intelligence.dominio.bank_entries_synced",
        )
        .order_by("-occurred_at")
        .values_list("metadata", flat=True)
        .first()
        or {}
    )
    dominio_bank_entries_may_be_truncated = bool(latest_bank_sync_metadata.get("may_be_truncated"))
    if request.method == "POST" and request.POST.get("action") == "usage-policy":
        return refuse(
            request,
            "A cobrança por chamada foi descontinuada. Use uma proposta de tokens com "
            "franquia por módulo e teto mensal.",
        )
    if request.method == "POST" and request.POST.get("action") == "accept-token-offer":
        if not context["support_can_mutate"] or not can_manage_usage_policy:
            return refuse(
                request,
                "Somente o dono ou administrador do escritório pode aceitar estes termos.",
            )
        if token_draft is None:
            return refuse(request, "Não existe uma proposta de tokens aguardando aceite.")
        if request.POST.get("accept_token_terms") != "on":
            messages.error(request, "Confirme o valor, a franquia, os pesos e o teto mensal.")
            return redirect("hub:settings")
        try:
            effective_from = date.fromisoformat(request.POST.get("effective_from", ""))
            activated = activate_token_book(
                book=token_draft,
                accepted_by=request.user,
                effective_from=effective_from,
            )
        except (BillingError, ValueError) as exc:
            messages.error(request, str(exc))
        else:
            record_event(
                action="hub.office.token_offer_accepted",
                actor=request.user,
                organization=office,
                target=activated,
                request=request,
                metadata={"version": activated.version, "effective_from": str(effective_from)},
            )
            messages.success(
                request,
                f"Tabela de tokens aceita para vigorar em {effective_from:%m/%Y}.",
            )
        return redirect("hub:settings")
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
                if bank_entries.may_be_truncated:
                    messages.warning(
                        request,
                        "A atualizacao atingiu o limite de itens bancarios; "
                        "o historico pode estar parcial.",
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
    next_month = (current_period + timedelta(days=32)).replace(day=1)
    token_draft_rates = list(token_draft.module_rates.all()) if token_draft else []
    active_token_rates = list(active_token_book.module_rates.all()) if active_token_book else []
    for book in (token_draft, active_token_book):
        if book is not None:
            book.token_price_brl = Decimal(book.token_price_cents or 0) / 100  # type: ignore[attr-defined]
            book.monthly_overage_cap_brl = (  # type: ignore[attr-defined]
                Decimal(book.monthly_overage_cap_cents or 0) / 100
            )
    module_labels = {"integra": "Central Integra", "ai": "Copiloto"}
    for display_rate in [*token_draft_rates, *active_token_rates]:
        display_rate.label = module_labels.get(  # type: ignore[attr-defined]
            display_rate.module_code, display_rate.module_code.title()
        )
        display_rate.monthly_base_brl = (  # type: ignore[attr-defined]
            Decimal(display_rate.monthly_base_cents or 0) / 100
        )
        for weight in display_rate.action_weights.all():
            weight.label = INTEGRA_SERVICE_LABELS.get(  # type: ignore[attr-defined]
                weight.action_code, weight.action_code
            )
    token_active_meters = list(
        TokenMeter.objects.filter(
            organization=office,
            period_start=current_period,
        ).order_by("module_code")
        if active_token_book
        else TokenMeter.objects.none()
    )
    for meter in token_active_meters:
        meter.overage_brl = Decimal(meter.overage_tokens * meter.token_price_cents) / 100  # type: ignore[attr-defined]
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
            "token_draft": token_draft,
            "active_token_book": active_token_book,
            "active_token_rates": active_token_rates,
            "token_book_in_effect": token_book_in_effect,
            "token_effective_min": next_month.isoformat(),
            "token_draft_rates": token_draft_rates,
            "token_active_meters": token_active_meters,
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
            "dominio_bank_entries_may_be_truncated": dominio_bank_entries_may_be_truncated,
            "can_request_dominio_sync": bool(
                can_manage_dominio_agent
                and dominio_connector
                and dominio_sync_state in {"synced", "failed", "not_synced"}
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
