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
from contextlib import suppress
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from functools import partial, wraps
from pathlib import PurePath
from types import SimpleNamespace
from typing import Any, Concatenate, cast
from urllib.parse import quote, urlencode, urlparse

from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import IntegrityError, models, transaction
from django.db.models import (
    Case,
    Count,
    Exists,
    F,
    IntegerField,
    Max,
    Min,
    OuterRef,
    Prefetch,
    Q,
    QuerySet,
    Sum,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Replace
from django.http import (
    FileResponse,
    Http404,
    HttpRequest,
    HttpResponse,
    HttpResponseBadRequest,
    HttpResponseBase,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date, parse_datetime
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.http import require_http_methods

from apps.accounts import mfa
from apps.accounts.forms import IdentifierAuthenticationForm
from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.common.cnpj import lookup_company, normalize_cnpj
from apps.common.network import client_ip
from apps.common.ratelimit import rate_limited
from apps.common.redirects import detail_redirect, safe_next
from apps.fiscal_calendar.models import ReferenceStatus, TaxDeadlineRule
from apps.fiscal_calendar.services import add_months
from apps.hub.closing_dashboard import closing_dashboard_context
from apps.hub.controlplane import (
    authorization_is_fresh,
    company_queryset_for_membership,
    company_queryset_for_module,
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
    ActivityGenerationForm,
    ActivityTemplateAssignmentForm,
    ActivityTemplateForm,
    CertificateUploadForm,
    CollaboratorAccessForm,
    CollaboratorInvitationForm,
    CompanyForm,
    CompanyProfileForm,
    CostCenterForm,
    DataSourceForm,
    DreMappingFormSet,
    DtePreparationForm,
    EightCharacterSetPasswordForm,
    FinancialAccountForm,
    LedgerAccountForm,
    OfficeIdentityForm,
    OperationalAssignmentForm,
    OperationalBlockForm,
    OperationalEvidenceForm,
    PayrollComparisonForm,
    ReconciliationMovementForm,
    ReconciliationRuleForm,
    ReconciliationUploadForm,
    UnifiedImportForm,
)
from apps.hub.imports import (
    ImportValidationError,
    confirm_import,
    create_import_preview,
    payroll_preview_rows,
)
from apps.hub.models import (
    AccountingBalanceSnapshot,
    AccountingEntry,
    AccountingExport,
    AccountingPeriod,
    AccumulatorCatalogEntry,
    AccumulatorHistoryEntry,
    AccumulatorObservation,
    AccumulatorRule,
    ActivityTemplate,
    ActivityTemplateAssignment,
    BankStatementImport,
    CashScenario,
    Certificate,
    ClientCompany,
    CompanyAccessGrant,
    Connector,
    ControlPlaneBinding,
    CostCenter,
    DataSource,
    DctfWebDocument,
    DominioBankEntry,
    DreAccountMapping,
    DreMappingSet,
    DteMessage,
    DteMessageAccess,
    DteRun,
    DteRunItem,
    FinancialAccount,
    FinancialReportExport,
    FiscalGuide,
    ImportBatch,
    IntegrationArtifact,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    MovementReconciliation,
    NfseDocument,
    NfseDocumentSide,
    NfseExport,
    NfseSync,
    NormalizedMovement,
    Notification,
    OfficeProfile,
    OnboardingProgress,
    OperationalActivity,
    ParcelamentoOperation,
    PayrollPeriodSnapshot,
    ProductModule,
    ReconciliationDecision,
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
from apps.hub.module_activities import nfse_resolution_reference, sync_nfse_review_activity
from apps.hub.module_catalog import MODULES, OFFERED_MODULE_CODES, ModuleDefinition, definition
from apps.hub.nfse_reports import (
    build_retention_report_rows,
    generate_retention_pdf,
    generate_retention_xlsx,
)
from apps.hub.onboarding import TOURS_BY_ID, tour_for_url_name
from apps.hub.operations import (
    activity_is_overdue,
    add_activity_note,
    add_human_evidence,
    assign_activity,
    block_activity,
    can_operate_activity,
    can_reschedule_activity,
    claim_activity,
    competence_ready_until,
    complete_activity,
    completion_requirements,
    generate_monthly_activities,
    reschedule_activity,
)
from apps.hub.payroll import compare_payroll_snapshots
from apps.hub.reconciliation import OfxParseError, confirm_reconciliation_match, import_ofx
from apps.hub.reconciliation_activities import sync_reconciliation_activity
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
from apps.hub.reporting_exports import FinancialReportExportError, prepare_export
from apps.hub.search import search_workspace
from apps.hub.services import (
    DCTFWEB_DOCUMENT_SERVICE,
    DTE_ACTION_CODE,
    PARCELAMENTO_SERVICE,
    DctfWebDocumentTransitionError,
    DteRunTransitionError,
    FiscalGuideTransitionError,
    ParcelamentoTransitionError,
    _xml_with_dominio_accumulator,
    active_catalog_codes,
    approve_dte_run,
    cancel_dte_run,
    create_nfse_export,
    import_certificate_upload,
    issue_fiscal_guide,
    nfse_company_archive_folder,
    prepare_dctfweb_guide_from_documents,
    prepare_dte_next_page,
    prepare_dte_run,
    record_human_observation,
    release_uncertain_parcelamento_operation,
    request_dctfweb_document,
    request_parcelamento_operation,
)
from apps.integra.client import credentials_from_settings
from apps.integra.dctfweb import extract_pdf
from apps.integra.errors import IntegraConfigurationError, IntegraError
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
    TriageFieldsForm,
)
from apps.triage.imap import MailboxIMAPError, encrypted_imap_credential, probe_imap_mailbox
from apps.triage.models import (
    AgentFileJob,
    DestinationProfile,
    Mailbox,
    MailboxOAuthApp,
    TriageItem,
)
from apps.triage.oauth import (
    MailboxOAuthError,
    encrypted_refresh_credential,
    exchange_code,
    new_authorization,
    probe_mailbox,
    redirect_uri,
)
from apps.triage.presentation import MailboxPresentation, present_mailbox
from apps.triage.services import (
    archive_internal,
    decide_item,
    open_reviewable_blob,
    open_verified_internal_copy,
    queue_windows_archive,
    update_review_fields,
)
from apps.triage.transitions import InvalidTransition, TriageStatus

logger = logging.getLogger(__name__)


class SignOutView(auth_views.LogoutView):
    """Answer a bookmarked GET /sair/ with a page instead of a bare 405.

    Django 5.0 removed logout over GET (release notes, "Features removed in 5.0"), so the
    stock view replies 405 with no body: whoever typed or bookmarked the URL lands on an
    empty page with no way back. GET now renders the confirmation; the logout itself
    stays a POST.
    """

    http_method_names = ["get", "post", "options"]
    template_name = "hub/logout_confirm.html"


class PasswordResetConfirmView(auth_views.PasswordResetConfirmView):
    """Keep the one-use reset token out of every subsequent Referer header."""

    form_class = EightCharacterSetPasswordForm

    def dispatch(self, request: HttpRequest, *args: object, **kwargs: object) -> HttpResponseBase:
        response = super().dispatch(request, *args, **kwargs)
        # Django replaces the one-use token with "set-password" before rendering.
        # On that sanitized URL, preserve the same-origin POST context for CSRF;
        # no-referrer can produce Origin: null in browsers on local HTTP.
        response["Referrer-Policy"] = (
            "same-origin" if kwargs.get("token") == self.reset_url_token else "no-referrer"
        )
        return response


def demo_office() -> Organization | None:
    """Resolve the demonstration office by what it is, not by a string that can drift.

    The configured slug stays authoritative when it matches. When it does not -- a stale
    value in the environment, a renamed organization -- the entry falls back to the single
    active organization flagged ``is_demo``. Two of them is a configuration problem, not a
    guess to make, so nothing is returned in that case.
    """

    configured = Organization.objects.filter(
        slug=settings.DEMO_ORGANIZATION_SLUG, is_demo=True, is_active=True
    ).first()
    if configured is not None:
        return configured
    flagged = list(Organization.objects.filter(is_demo=True, is_active=True)[:2])
    return flagged[0] if len(flagged) == 1 else None


@require_http_methods(["GET", "POST"])
def demo_entry(request: HttpRequest) -> HttpResponse:
    """Dedicated demonstration entry; public access stays gated until session isolation."""

    office = demo_office()
    available = bool(
        settings.DEMO_ENTRY_ENABLED and settings.DEMO_SESSION_ISOLATION_READY and office
    )
    if request.method == "POST":
        if not available:
            return HttpResponseBadRequest("A demonstração ainda não está disponível.")
        if rate_limited(f"demo-entry:{client_ip(request)}", limit=8, window_seconds=60):
            return HttpResponse("Aguarde um minuto antes de iniciar outra sessão.", status=429)
        assert office is not None
        from apps.hub.demo_scenario import ensure_demo_window

        ensure_demo_window(office)
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
        and demo_office() is not None
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
    module_records = list(
        ProductModule.objects.filter(organization=office).order_by("code")
        if office
        else ProductModule.objects.none()
    )
    module_rows = [row for row in module_records if row.enabled]
    explicit_enabled_module_codes = {
        row.code for row in module_rows if row.code in MODULES and row.code in OFFERED_MODULE_CODES
    }
    explicit_module_codes = {row.code for row in module_records if row.code in OFFERED_MODULE_CODES}
    # Legacy offices can have only the historic NFS-e row. Treat the reduced surface
    # as a commercial choice only after the control plane recorded every offered module.
    is_nfse_only_subscription = explicit_enabled_module_codes == {
        ProductModule.Code.NFSE
    } and explicit_module_codes == set(OFFERED_MODULE_CODES)
    enabled_modules = [
        MODULES[row.code] for row in module_rows if row.code in explicit_enabled_module_codes
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
        "mfa_enrolled": mfa.is_enrolled(user),
        "mfa_recommendation_available": not PlatformAccess.objects.filter(user=user).exists(),
        "open_reviews_count": ReviewCase.objects.filter(
            organization=office, status=ReviewCase.Status.OPEN, document__company__in=companies
        ).count()
        if office
        else 0,
        "unread_notifications_count": Notification.objects.filter(
            organization=office, recipient=user, read_at__isnull=True
        )
        .filter(Q(company__isnull=True) | Q(company__in=companies))
        .count()
        if office
        else 0,
        "enabled_modules": enabled_modules,
        "is_nfse_only_subscription": is_nfse_only_subscription,
        "copilot_enabled": copilot_enabled,
        "active_module_code": active_module_code,
        "permitted_module_codes": permitted_module_codes,
        **_onboarding_context(request, office, membership, support_session),
    }


def _onboarding_context(
    request: HttpRequest,
    office: Organization | None,
    membership: Membership | None,
    support_session: SupportSession | None,
) -> dict[str, object]:
    """Pick the optional orientation for this screen.

    Guidance never covers the task automatically. A support visit is somebody else's
    workspace, so it does not expose the tour at all. Only the identifier, version,
    role and completion state cross into the template.
    """

    url_name = request.resolver_match.url_name if request.resolver_match else None
    tour = tour_for_url_name(url_name)
    role = membership.role if isinstance(membership, Membership) else None
    if tour is None or support_session is not None or not tour.visible_for(role):
        return {"onboarding_tour": None, "onboarding_tour_done": True}
    demo = bool(office and office.is_demo)
    done = False
    if not demo and getattr(request.user, "is_authenticated", False):
        actor = cast(User, request.user)
        done = OnboardingProgress.objects.filter(
            user=actor, tour_id=tour.identifier, version__gte=tour.version
        ).exists()
    return {
        "onboarding_tour": tour,
        "onboarding_tour_done": done,
        "onboarding_auto_open": False,
        "onboarding_session_only": demo,
    }


@login_required
@require_http_methods(["POST"])
def onboarding_complete(request: HttpRequest, tour_id: str) -> HttpResponse:
    """Record that this person finished one orientation, at the version they saw."""

    tour = TOURS_BY_ID.get(tour_id)
    if tour is None:
        return HttpResponseBadRequest("Orientação desconhecida.")
    OnboardingProgress.objects.update_or_create(
        user=cast(User, request.user),
        tour_id=tour.identifier,
        defaults={"version": tour.version, "completed_at": timezone.now()},
    )
    return HttpResponse(status=204)


def refuse(request: HttpRequest, reason: str, *, kind: str = "permission") -> HttpResponse:
    """Refuse with a page the person can leave, not a bare sentence.

    ``HttpResponseForbidden`` renders unstyled text with no navigation: whoever just
    clicked a menu item or submitted a form lands on a blank page whose only way out is
    the browser's back button. The status stays 403; only the body becomes a page that
    says what happened and where to go.

    ``kind="unavailable"`` keeps the status but stops labelling "sem permissão" a refusal
    that has nothing to do with the person's role, which sends them hunting for an access
    problem that does not exist.
    """

    return render(
        request,
        "hub/forbidden.html",
        {"reason": reason, "refusal_kind": kind},
        status=403,
    )


def _user_error_message(exc: Exception) -> str:
    """Render Django validation errors as human text, never Python list syntax."""

    if isinstance(exc, ValidationError):
        return " ".join(str(message) for message in exc.messages)
    return str(exc)


def collaborator_can_use_module(context: dict[str, object], code: str) -> bool:
    """Keep module permission independent from menu visibility and URL guessing."""
    permitted = context.get("permitted_module_codes")
    return permitted is None or (isinstance(permitted, set) and code in permitted)


def is_nfse_only_subscription(context: dict[str, object]) -> bool:
    """Identify an explicit NFS-e-only subscription, never a legacy implicit scope."""
    return context.get("is_nfse_only_subscription") is True


def office_required[**ViewParams](
    view: Callable[Concatenate[HttpRequest, ViewParams], HttpResponseBase],
) -> Callable[Concatenate[HttpRequest, ViewParams], HttpResponseBase]:
    @wraps(view)
    def wrapped(
        request: HttpRequest,
        *args: ViewParams.args,
        **kwargs: ViewParams.kwargs,
    ) -> HttpResponseBase:
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
        # The advanced reconciliation route family has no session-backed demo.
        # Deny reads as well as writes before entering a view: hiding the tabs
        # alone must not expose shared files, settings or operational records.
        if office.is_demo and view.__name__.startswith("reconciliation_"):
            return render(
                request,
                "hub/forbidden.html",
                {
                    "reason": "A demonstração oferece somente a comparação fictícia. "
                    "Configurações, arquivos, processamentos, movimentos e exportações "
                    "não estão disponíveis neste escritório demo.",
                    "refusal_kind": "unavailable",
                    "reconciliation_demo_unavailable": True,
                },
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
                "dctfweb_consult",
                "issue_guide",
                "parcelamentos",
                "nfse_center",
                "nfse_queue_retry",
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
                kind="unavailable",
            )
        if (
            office.is_demo
            and request.method not in {"GET", "HEAD", "OPTIONS"}
            and view.__name__
            in {
                "activity_detail",
                "activity_add_evidence",
                "activity_block",
                "activity_complete",
                "activity_models",
            }
        ):
            return refuse(
                request,
                "As atividades da demonstração são cenários fictícios de consulta.",
                kind="unavailable",
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
                    created_by=cast(User, request.user),
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

    collaborator_rows = (
        Membership.objects.filter(organization=office, is_active=True)
        .select_related("user")
        .prefetch_related("company_grants__company")
        .order_by("user__full_name", "user__email")
    )
    if office.is_demo:
        # One visitor must not see the throwaway accounts of every other visitor: the
        # demonstration office keeps its seeded personas, plus whoever is looking.
        collaborator_rows = collaborator_rows.exclude(
            Q(user__email__startswith="demo-", user__email__endswith="@example.test")
            & ~Q(user=request.user)
        )
    collaborators = list(collaborator_rows)
    for item in collaborators:
        grants = list(item.company_grants.all())
        item.role_label = item.get_role_display()  # type: ignore[attr-defined]
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
        return refuse(
            request,
            "Este acesso n\u00e3o pode ser removido por esta tela.",
            kind="unavailable",
        )
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
@require_http_methods(["GET", "POST"])
def company_detail(request: HttpRequest, company_id: str) -> HttpResponse:
    """Everything the office holds about one client, on one page.

    This replaces the header's "current company" switch. A single company is a place
    you open from the registry and leave again, not a global mode that quietly
    reinterprets every other screen.
    """

    context = workspace_context(request)
    office = cast(Organization, context["office"])
    companies = _company_history_scope(context)
    company = get_object_or_404(companies, id=company_id)
    original_company_values = {
        "name": company.name,
        "cnpj_masked": company.cnpj_masked,
        "dominio_code": company.dominio_code,
    }

    can_manage_companies = _can_manage_companies(context)
    require_dominio_code = OfficeProfile.objects.filter(
        organization=office, require_dominio_code=True
    ).exists()
    dominio_manages_companies = (
        IntelligenceConnector.objects.filter(organization=office)
        .exclude(status="not_configured")
        .exists()
    )
    centrally_managed = ControlPlaneBinding.objects.filter(organization=office).exists()
    company_has_external_source = bool(company.data_source_id or company.external_key)
    # The public demonstration is shared by every visitor: its records stay read-only.
    can_manage_companies = can_manage_companies and not office.is_demo
    can_edit_company = bool(
        can_manage_companies
        and not dominio_manages_companies
        and not centrally_managed
        and not company_has_external_source
    )
    company_form = CompanyForm(
        request.POST if request.POST.get("action") == "update_company" else None,
        instance=company,
        organization=office,
        require_dominio_code=require_dominio_code,
    )
    profile_candidates = _company_responsible_candidates(office, company)
    profile_form = CompanyProfileForm(
        request.POST if request.POST.get("action") == "update_profile" else None,
        instance=company,
        organization=office,
        candidates=profile_candidates,
        prefix="profile",
    )
    if request.method == "POST" and request.POST.get("action") == "update_profile":
        if not can_manage_companies:
            return refuse(request, "Esta sessão é somente leitura.")
        before = {field: getattr(company, field) for field in profile_form.Meta.fields}
        if profile_form.is_valid():
            with transaction.atomic():
                saved = profile_form.save()
                changed_areas = profile_form.save_area_responsibles()
            changed_fields = [
                field for field, value in before.items() if value != getattr(saved, field)
            ]
            record_event(
                action="hub.company.profile_updated",
                actor=request.user,
                organization=office,
                target=saved,
                request=request,
                metadata={"changed_fields": changed_fields, "changed_areas": changed_areas},
            )
            messages.success(request, "Perfil da empresa atualizado.")
            return redirect("hub:company-detail", company_id=company.id)
        messages.error(request, "Revise o perfil da empresa.")
    if request.method == "POST" and request.POST.get("action") != "update_profile":
        if request.POST.get("action") != "update_company":
            return HttpResponseBadRequest("Ação de cadastro inválida.")
        if not can_manage_companies:
            return refuse(request, "Esta sessão é somente leitura.")
        if not can_edit_company:
            return refuse(
                request,
                "Este cadastro é controlado pela origem e deve ser corrigido nela.",
                kind="unavailable",
            )
        if company_form.is_valid():
            updated_company = company_form.save()
            changed_fields = [
                field
                for field, value in original_company_values.items()
                if value != getattr(updated_company, field)
            ]
            record_event(
                action="hub.company.updated",
                actor=request.user,
                organization=office,
                target=updated_company,
                request=request,
                metadata={"changed_fields": changed_fields},
            )
            messages.success(request, "Cadastro da empresa atualizado.")
            return redirect("hub:company-detail", company_id=company.id)

    documents_query = (
        NfseDocument.objects.filter(organization=office, company=company)
        .select_related("review_case", "side")
        .order_by("-captured_at")
    )
    document_page = Paginator(documents_query, 20).get_page(request.GET.get("documents_page"))
    for document in document_page.object_list:
        # The accountant looks for the fiscal number, the date and the other party; the
        # transport NSU and hash stay available only as technical detail.
        normalized = document.normalized_data if isinstance(document.normalized_data, dict) else {}
        side = _nfse_side(document)
        document.display_number = _nfse_document_number(document)  # type: ignore[attr-defined]
        document.display_issued_at = (  # type: ignore[attr-defined]
            document.issued_at or _nfse_issued_at_from_normalized_data(document)
        )
        document.display_counterparty = str(  # type: ignore[attr-defined]
            normalized.get("counterparty_name") or (side.counterparty_name if side else "")
        ).strip()[:160]
    open_cases_query = (
        ReviewCase.objects.filter(
            organization=office, status=ReviewCase.Status.OPEN, document__company=company
        )
        .select_related("document")
        .order_by("-created_at")
    )
    open_cases_page = Paginator(open_cases_query, 20).get_page(request.GET.get("reviews_page"))
    for case in open_cases_page.object_list:
        case.document.display_number = _nfse_document_number(case.document)  # type: ignore[attr-defined]
    dte_messages_query = DteMessage.objects.filter(organization=office, company=company).order_by(
        "-sent_at", "-first_seen_at"
    )
    dte_messages_page = Paginator(dte_messages_query, 20).get_page(request.GET.get("dte_page"))
    activities_query = (
        OperationalActivity.objects.filter(organization=office, company=company)
        .select_related("assigned_to")
        .order_by(
            Coalesce("internal_due_on", "legal_due_on").asc(nulls_last=True),
            "-created_at",
            "pk",
        )
    )
    closed_activity_states = [
        OperationalActivity.WorkStatus.COMPLETED,
        OperationalActivity.WorkStatus.WAIVED,
    ]
    today = timezone.localdate()
    overdue_condition = Q(internal_due_on__lt=today) | Q(
        internal_due_on__isnull=True, legal_due_on__lt=today
    )
    activity_stats = activities_query.aggregate(
        total=Count("pk"),
        open=Count("pk", filter=~Q(work_status__in=closed_activity_states)),
        blocked=Count("pk", filter=Q(work_status=OperationalActivity.WorkStatus.BLOCKED)),
        overdue=Count(
            "pk",
            filter=~Q(work_status__in=closed_activity_states) & overdue_condition,
        ),
    )
    priority_activity = (
        activities_query.exclude(work_status__in=closed_activity_states)
        .annotate(
            attention_order=Case(
                When(work_status=OperationalActivity.WorkStatus.BLOCKED, then=Value(0)),
                When(overdue_condition, then=Value(1)),
                default=Value(2),
                output_field=IntegerField(),
            )
        )
        .order_by(
            "attention_order",
            Coalesce("internal_due_on", "legal_due_on").asc(nulls_last=True),
            "created_at",
        )
        .first()
    )
    activities_page = Paginator(activities_query, 5).get_page(request.GET.get("activities_page"))
    payroll_snapshots_base = PayrollPeriodSnapshot.objects.filter(
        organization=office, company=company
    ).order_by("-competence", "-observed_at")
    payroll_snapshots_total = payroll_snapshots_base.count()
    payroll_snapshots_query = payroll_snapshots_base
    payroll_period = None
    if request.GET.get("payroll_competence"):
        try:
            payroll_period = date.fromisoformat(request.GET["payroll_competence"])
        except ValueError:
            raise Http404("Competência da folha inválida.") from None
        if payroll_period.day != 1:
            raise Http404("Competência da folha inválida.")
        payroll_snapshots_query = payroll_snapshots_query.filter(competence=payroll_period)
    elif request.GET.get("left_snapshot"):
        try:
            left_snapshot_id = uuid.UUID(request.GET["left_snapshot"])
        except (ValueError, AttributeError):
            left_snapshot_id = None
        payroll_period = (
            payroll_snapshots_base.filter(pk=left_snapshot_id)
            .values_list("competence", flat=True)
            .first()
            if left_snapshot_id
            else None
        )
        if payroll_period is not None:
            payroll_snapshots_query = payroll_snapshots_query.filter(competence=payroll_period)
    payroll_review_activity = (
        activities_query.filter(
            competence=payroll_period,
            source_payroll_snapshot__isnull=False,
        ).first()
        if payroll_period
        else None
    )
    payroll_snapshots_page = Paginator(payroll_snapshots_query, 20).get_page(
        request.GET.get("payroll_page")
    )
    payroll_snapshots = list(payroll_snapshots_page.object_list)
    visible_payroll_competences = {snapshot.competence for snapshot in payroll_snapshots}
    payroll_comparable_competences = set(
        payroll_snapshots_base.filter(competence__in=visible_payroll_competences)
        .order_by()
        .values("competence")
        .annotate(source_count=Count("pk"))
        .filter(source_count__gte=2)
        .values_list("competence", flat=True)
    )
    return_to = request.GET.get("return_to", "")
    payroll_snapshot_rows = []
    linked_payroll_competences: set[date] = set()
    for snapshot in payroll_snapshots:
        is_comparable = snapshot.competence in payroll_comparable_competences
        can_compare = is_comparable and snapshot.competence not in linked_payroll_competences
        if can_compare:
            linked_payroll_competences.add(snapshot.competence)
        compare_params = {"payroll_competence": snapshot.competence.isoformat()}
        if return_to:
            compare_params["return_to"] = return_to
        payroll_snapshot_rows.append(
            {
                "snapshot": snapshot,
                "can_compare": can_compare,
                "is_comparable": is_comparable,
                "compare_url": (
                    f"{reverse('hub:company-detail', args=[company.pk])}?"
                    f"{urlencode(compare_params)}#folha"
                ),
            }
        )
    payroll_comparison: Any | None = None
    payroll_comparison_variances: list[dict[str, Any]] = []
    payroll_comparison_missing: list[str] = []
    payroll_comparison_competence: date | None = None
    payroll_comparison_initial: dict[str, object] = {}
    if payroll_period and payroll_snapshots_page.paginator.count == 2:
        payroll_comparison_initial = {
            "left_snapshot": payroll_snapshots[1],
            "right_snapshot": payroll_snapshots[0],
            "money_tolerance": Decimal("0"),
        }
    payroll_comparison_form = PayrollComparisonForm(
        request.GET if "left_snapshot" in request.GET else None,
        snapshots=payroll_snapshots_query,
        initial=payroll_comparison_initial,
    )
    if payroll_comparison_form.is_bound and payroll_comparison_form.is_valid():
        payroll_comparison = compare_payroll_snapshots(
            left=payroll_comparison_form.cleaned_data["left_snapshot"],
            right=payroll_comparison_form.cleaned_data["right_snapshot"],
            money_tolerance_cents=payroll_comparison_form.tolerance_cents(),
        )
        payroll_comparison_competence = payroll_comparison_form.cleaned_data[
            "left_snapshot"
        ].competence
        metric_labels = {
            "workforce_count": "Quadro de pessoas",
            "gross_pay_cents": "Total bruto",
            "deductions_cents": "Descontos",
            "employer_charges_cents": "Encargos do empregador",
            "net_pay_cents": "Total líquido",
        }
        payroll_comparison_variances = [
            {
                "label": metric_labels[variance.metric],
                "left_value": variance.left_value
                if variance.metric == "workforce_count"
                else Decimal(variance.left_value) / 100,
                "right_value": variance.right_value
                if variance.metric == "workforce_count"
                else Decimal(variance.right_value) / 100,
                "difference": variance.difference
                if variance.metric == "workforce_count"
                else Decimal(variance.difference) / 100,
                "difference_abs": abs(variance.difference)
                if variance.metric == "workforce_count"
                else Decimal(abs(variance.difference)) / 100,
                "direction_label": "a mais" if variance.difference > 0 else "a menos",
                "direction_class": "is-more" if variance.difference > 0 else "is-less",
                "is_money": variance.metric != "workforce_count",
            }
            for variance in payroll_comparison.variances
        ]
        payroll_comparison_missing = [
            metric_labels[metric] for metric in payroll_comparison.missing_metrics
        ]
    accounting_snapshots = list(
        AccountingBalanceSnapshot.objects.filter(organization=office, company=company).order_by(
            "-competence", "-observed_at"
        )[:5]
    )
    active_dre_mapping = (
        DreMappingSet.objects.filter(organization=office, is_active=True)
        .order_by("-version")
        .first()
    )
    cash_scenarios = list(
        CashScenario.objects.filter(organization=office, company=company).order_by(
            "-reference_date", "-created_at"
        )[:5]
    )
    financial_report_exports = list(
        FinancialReportExport.objects.filter(organization=office, company=company)
        .select_related("requested_by")
        .order_by("-created_at")[:10]
    )
    triage_available = bool(
        collaborator_can_use_module(context, ProductModule.Code.TRIAGE)
        and ProductModule.objects.filter(
            organization=office, code=ProductModule.Code.TRIAGE, enabled=True
        ).exists()
    )
    triage_items_query = TriageItem.objects.none()
    if triage_available:
        triage_items_query = TriageItem.objects.filter(
            organization=office, company=company
        ).select_related("document_type")
    triage_items_page = Paginator(triage_items_query, 20).get_page(request.GET.get("triage_page"))
    company_detail_query_params = request.GET.copy()
    company_detail_querystrings: dict[str, str] = {}
    for page_parameter in (
        "documents_page",
        "reviews_page",
        "dte_page",
        "activities_page",
        "payroll_page",
        "triage_page",
    ):
        page_query_params = company_detail_query_params.copy()
        page_query_params.pop(page_parameter, None)
        company_detail_querystrings[page_parameter] = page_query_params.urlencode()

    certificates = list(
        Certificate.objects.filter(
            organization=office, company=company, revoked_at__isnull=True
        ).order_by("-valid_until")
    )
    now = timezone.now()
    valid_certificates = [
        certificate
        for certificate in certificates
        if certificate.valid_until is not None and certificate.valid_until > now
    ]
    certificate_expiring = any(
        certificate.valid_until is not None
        and certificate.valid_until <= now + timedelta(days=30)
        for certificate in valid_certificates
    )
    company_source_label = "Cadastro local"
    if centrally_managed:
        company_source_label = "Controle central Mewstack"
    elif dominio_manages_companies or company_has_external_source:
        company_source_label = (
            company.data_source.label
            if company.data_source_id and company.data_source is not None
            else "Domínio"
        )

    next_action: dict[str, object]
    if not company.active:
        next_action = {
            "tone": "muted",
            "eyebrow": "Somente histórico",
            "title": "Empresa pausada na origem",
            "description": (
                "Documentos e histórico continuam disponíveis, sem novas ações operacionais."
            ),
            "label": "Ver documentos NFS-e",
            "url": "#documentos-nfse",
            "opens_details": True,
        }
    elif priority_activity is not None and (
        priority_activity.work_status == OperationalActivity.WorkStatus.BLOCKED
        or activity_is_overdue(priority_activity, today=today)
    ):
        is_blocked = priority_activity.work_status == OperationalActivity.WorkStatus.BLOCKED
        next_action = {
            "tone": "danger",
            "eyebrow": "Precisa de atenção",
            "title": priority_activity.title,
            "description": (
                "Resolva o impedimento registrado para o trabalho voltar a avançar."
                if is_blocked
                else "O prazo desta atividade passou; confira a situação e registre o tratamento."
            ),
            "label": "Conferir atividade",
            "url": reverse("hub:activity-detail", args=[priority_activity.pk]),
        }
    elif open_cases_page.paginator.count:
        next_action = {
            "tone": "warning",
            "eyebrow": "Revisão fiscal",
            "title": f"{open_cases_page.paginator.count} NFS-e aguardando classificação",
            "description": "Revise o acumulador antes de usar as notas no fechamento.",
            "label": "Classificar NFS-e",
            "url": f"{reverse('hub:nfse-center')}?status=unclassified&company={company.id}",
        }
    elif not valid_certificates or certificate_expiring:
        next_action = {
            "tone": "warning",
            "eyebrow": "Certificado A1",
            "title": "Enviar certificado" if not valid_certificates else "Renovar certificado",
            "description": (
                "A coleta automática depende de um A1 válido vinculado à empresa."
                if not valid_certificates
                else "Há um certificado válido que vence nos próximos 30 dias."
            ),
            "label": "Abrir certificados",
            "url": f"{reverse('hub:certificates')}?company={company.id}",
        }
    elif priority_activity is not None:
        next_action = {
            "tone": "active",
            "eyebrow": "Próximo trabalho",
            "title": priority_activity.title,
            "description": "Abra a atividade para conferir requisitos, responsável e evidências.",
            "label": "Conferir atividade",
            "url": reverse("hub:activity-detail", args=[priority_activity.pk]),
        }
    elif not company.dominio_code and can_edit_company:
        next_action = {
            "tone": "warning",
            "eyebrow": "Cadastro incompleto",
            "title": "Informar o código no Domínio",
            "description": "O código exato evita associação ambígua nas importações do escritório.",
            "label": "Editar cadastro",
            "url": "#company-edit-dialog",
            "opens_modal": True,
        }
    else:
        next_action = {
            "tone": "active",
            "eyebrow": "Sem pendência prioritária",
            "title": "Cadastro pronto para consulta",
            "description": "Use as áreas abaixo para consultar trabalho, documentos e histórico.",
            "label": "Ver atividades",
            "url": "#atividades",
            "opens_details": True,
        }
    area_owner_names = dict(profile_candidates)
    company_area_owners = [
        {
            "label": label,
            "name": area_owner_names.get(str(row.user_id), "") if row.user_id else "",
        }
        for area, label in ActivityTemplate.Area.choices
        for row in company.area_responsibles.all()
        if row.area == area and row.user_id
    ]
    context.update(
        {
            "page_title": company.name,
            "company": company,
            "profile_form": profile_form,
            "can_edit_profile": can_manage_companies,
            "company_area_owners": company_area_owners,
            "documents": list(document_page.object_list),
            "document_page": document_page,
            "document_querystring": company_detail_querystrings["documents_page"],
            "open_cases": list(open_cases_page.object_list),
            "open_cases_page": open_cases_page,
            "open_cases_querystring": company_detail_querystrings["reviews_page"],
            "certificates": certificates,
            "dte_messages": list(dte_messages_page.object_list),
            "dte_messages_page": dte_messages_page,
            "dte_messages_querystring": company_detail_querystrings["dte_page"],
            "activities": list(activities_page.object_list),
            "activities_page": activities_page,
            "activities_querystring": company_detail_querystrings["activities_page"],
            "activities_count": activity_stats["total"],
            "open_activity_count": activity_stats["open"],
            "blocked_activity_count": activity_stats["blocked"],
            "overdue_activity_count": activity_stats["overdue"],
            "payroll_snapshots": payroll_snapshots,
            "payroll_snapshot_rows": payroll_snapshot_rows,
            "payroll_period": payroll_period,
            "payroll_review_activity": payroll_review_activity,
            "payroll_snapshots_page": payroll_snapshots_page,
            "payroll_querystring": company_detail_querystrings["payroll_page"],
            "payroll_snapshots_count": payroll_snapshots_page.paginator.count,
            "payroll_snapshots_total": payroll_snapshots_total,
            "payroll_comparison_form": payroll_comparison_form,
            "payroll_comparison": payroll_comparison,
            "payroll_comparison_variances": payroll_comparison_variances,
            "payroll_comparison_missing": payroll_comparison_missing,
            "payroll_comparison_competence": payroll_comparison_competence,
            "accounting_snapshots": accounting_snapshots,
            "accounting_snapshots_count": len(accounting_snapshots),
            "active_dre_mapping": active_dre_mapping,
            "cash_scenarios": cash_scenarios,
            "cash_scenarios_count": len(cash_scenarios),
            "financial_report_exports": financial_report_exports,
            "triage_available": triage_available,
            "triage_items": list(triage_items_page.object_list),
            "triage_items_page": triage_items_page,
            "triage_items_querystring": company_detail_querystrings["triage_page"],
            "triage_items_count": triage_items_page.paginator.count,
            "document_count": document_page.paginator.count,
            "open_cases_count": open_cases_page.paginator.count,
            "dte_messages_count": dte_messages_page.paginator.count,
            "today": now,
            "company_form": company_form,
            "can_edit_company": can_edit_company,
            "company_source_label": company_source_label,
            "company_managed_externally": not can_edit_company and (
                dominio_manages_companies or centrally_managed or company_has_external_source
            ),
            "next_action": next_action,
            "certificate_attention": not valid_certificates or certificate_expiring,
        }
    )
    return render(
        request,
        "hub/company_detail.html",
        context,
        status=400 if request.method == "POST" and company_form.errors else 200,
    )


@office_required
@require_http_methods(["POST"])
def company_financial_report(
    request: HttpRequest, company_id: str, resource: str, resource_id: uuid.UUID, export_format: str
) -> HttpResponse:
    """Queue a private report from a fixed authorized photograph.

    Rendering never blocks the web request.
    """

    context = workspace_context(request)
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    company = get_object_or_404(companies, id=company_id)
    if resource not in set(FinancialReportExport.Resource.values):
        return HttpResponseBadRequest("Recurso de relatorio invalido.")
    if export_format not in set(FinancialReportExport.Format.values):
        return HttpResponseBadRequest("Formato de relatorio invalido.")
    if (
        resource == FinancialReportExport.Resource.DRE
        and not DreMappingSet.objects.filter(organization=office, is_active=True).exists()
    ):
        return HttpResponse("Nenhum mapa DRE ativo esta configurado.", status=409)
    if not settings.CICA_REPORTING_URL or not settings.CICA_REPORTING_SHARED_SECRET:
        return HttpResponse("Servico interno de relatorios nao esta configurado.", status=503)
    try:
        export = prepare_export(
            organization=office,
            company_id=company.id,
            resource=resource,
            resource_id=resource_id,
            export_format=export_format,
            actor=cast(User, request.user),
            request=request,
        )
    except (FinancialReportExportError, ValueError) as exc:
        message = str(exc)
        if "mapa DRE" in message:
            return HttpResponse(message, status=409)
        return HttpResponseBadRequest(message)

    from apps.hub.tasks import process_financial_report_export

    transaction.on_commit(partial(process_financial_report_export.delay, str(export.id)))
    messages.success(
        request, "Relatorio solicitado. O arquivo aparecera nesta empresa quando estiver pronto."
    )
    return redirect(f"{reverse('hub:company-detail', args=[company.id])}#relatorios-financeiros")


@office_required
@require_http_methods(["GET"])
def download_financial_report_export(request: HttpRequest, export_id: str) -> HttpResponseBase:
    """Revalidate current company access before exposing a private rendered file."""

    context = workspace_context(request)
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    export = get_object_or_404(
        FinancialReportExport,
        id=export_id,
        organization=office,
        company__in=companies,
        state=FinancialReportExport.State.READY,
    )
    content_name = export.content.name if export.content else ""
    if not content_name or not export.content.storage.exists(content_name):
        FinancialReportExport.objects.filter(id=export.id).update(
            state=FinancialReportExport.State.FAILED,
            failure_code="artifact_missing",
        )
        messages.error(
            request, "O arquivo privado deste relatorio nao esta mais disponivel. Solicite outro."
        )
        detail_url = reverse("hub:company-detail", args=[export.company_id])
        return redirect(f"{detail_url}#relatorios-financeiros")
    response = FileResponse(
        export.content.open("rb"),
        as_attachment=True,
        filename=PurePath(content_name).name,
        content_type=export.content_type or None,
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    return response


@office_required
def dashboard(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    if is_nfse_only_subscription(context):
        return redirect("hub:nfse-center")
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
        open_cases = list(open_cases_query[:8])
    enabled_modules = cast(list[ProductModule], context["enabled_modules"])
    enabled_codes = {module.code for module in enabled_modules}
    review_count = (
        len([review for review in demo_open_cases if review.status == ReviewCase.Status.OPEN])
        if is_demo_visitor(request, office)
        else open_cases_query.count()
    )
    activity_query = OperationalActivity.objects.filter(organization=office, company__in=scope)
    dashboard_membership = context["membership"]
    is_dashboard_administrator = isinstance(dashboard_membership, Membership) and (
        dashboard_membership.role
        in {
            Membership.Role.OWNER,
            Membership.Role.ADMIN,
        }
    )
    dashboard_view = request.GET.get("view", "mine")
    if dashboard_view not in {"mine", "portfolio", "management"}:
        dashboard_view = "mine"
    if dashboard_view == "management" and not is_dashboard_administrator:
        return refuse(request, "A gestão da operação exige perfil de administrador.")
    if dashboard_view == "mine":
        if office.is_demo and (is_demo_visitor(request, office) or is_dashboard_administrator):
            from apps.hub.demo_scenario import persona_email

            activity_query = activity_query.filter(assigned_to__email=persona_email(office))
            context["demo_persona_name"] = "Ana Martins"
        else:
            activity_query = activity_query.filter(assigned_to=cast(User, request.user))
    today = timezone.localdate()
    context.update(
        closing_dashboard_context(
            companies=scope,
            month=request.GET.get("closing_month", ""),
            page=request.GET.get("closing_page", "1"),
            today=today,
        )
    )
    open_activity_query = activity_query.exclude(
        work_status__in=[
            OperationalActivity.WorkStatus.COMPLETED,
            OperationalActivity.WorkStatus.WAIVED,
        ]
    )
    due_today = Q(internal_due_on=today) | Q(internal_due_on__isnull=True, legal_due_on=today)
    due_next_seven_days = Q(
        internal_due_on__gt=today, internal_due_on__lte=today + timedelta(days=7)
    ) | Q(
        internal_due_on__isnull=True,
        legal_due_on__gt=today,
        legal_due_on__lte=today + timedelta(days=7),
    )
    overdue_activities = open_activity_query.filter(
        Q(internal_due_on__lt=today) | Q(internal_due_on__isnull=True, legal_due_on__lt=today)
    )
    activity_attention = [
        {
            "label": "Em atraso",
            "count": overdue_activities.count(),
            "note": "Revisar atrasadas",
            "url": f"{reverse('hub:activities')}?overdue=1",
            "tone": "attention",
        },
        {
            "label": "Para hoje",
            "count": open_activity_query.filter(due_today).count(),
            "note": "Abrir agenda de hoje",
            "url": f"{reverse('hub:activities')}?due=today",
            "tone": "attention",
        },
        {
            "label": "Próximos 7 dias",
            "count": open_activity_query.filter(due_next_seven_days).count(),
            "note": "Planejar a semana",
            "url": f"{reverse('hub:activities')}?due=next_7_days",
            "tone": "",
        },
        {
            "label": "Impedidas",
            "count": open_activity_query.filter(
                work_status=OperationalActivity.WorkStatus.BLOCKED
            ).count(),
            "note": "Resolver impedimentos",
            "url": f"{reverse('hub:activities')}?status=blocked",
            "tone": "attention",
        },
        {
            "label": "Fonte indisponível",
            "count": open_activity_query.filter(
                freshness=OperationalActivity.Freshness.UNAVAILABLE
            ).count(),
            "note": "Ver falhas de origem",
            "url": f"{reverse('hub:activities')}?freshness=unavailable",
            "tone": "attention",
        },
    ]
    agenda_filters = {
        "overdue": Q(internal_due_on__lt=today)
        | Q(internal_due_on__isnull=True, legal_due_on__lt=today),
        "today": due_today,
        "next_7_days": due_next_seven_days,
        "blocked": Q(work_status=OperationalActivity.WorkStatus.BLOCKED),
        "unavailable": Q(freshness=OperationalActivity.Freshness.UNAVAILABLE),
    }
    for item, key in zip(activity_attention, agenda_filters, strict=True):
        item["url"] = f"{reverse('hub:dashboard')}?view={dashboard_view}&filter={key}"
    selected_agenda_filter = request.GET.get("filter", "")
    agenda_query = open_activity_query
    if selected_agenda_filter in agenda_filters:
        agenda_query = agenda_query.filter(agenda_filters[selected_agenda_filter])
    else:
        selected_agenda_filter = ""
    for item, key in zip(activity_attention, agenda_filters, strict=True):
        item["selected"] = key == selected_agenda_filter
    agenda_page = Paginator(
        agenda_query.select_related("company", "assigned_to").order_by(
            Coalesce("internal_due_on", "legal_due_on").asc(nulls_last=True),
            "-created_at",
            "pk",
        ),
        10,
    ).get_page(request.GET.get("page"))
    dashboard_activities = cast(list[OperationalActivity], list(agenda_page.object_list))
    for activity in dashboard_activities:
        activity.is_overdue = activity_is_overdue(activity, today=today)  # type: ignore[attr-defined]
        due_on = activity.internal_due_on or activity.legal_due_on
        activity.dashboard_due_on = due_on  # type: ignore[attr-defined]
        activity.dashboard_due_kind = (  # type: ignore[attr-defined]
            "Prazo interno" if activity.internal_due_on else "Prazo legal"
        )
        if due_on is None:
            group = "Sem prazo"
            due_label = "Sem prazo definido"
        elif due_on < today:
            group = "Em atraso"
            overdue_days = (today - due_on).days
            due_label = "1 dia em atraso" if overdue_days == 1 else f"{overdue_days} dias em atraso"
        elif due_on == today:
            group = "Para hoje"
            due_label = "Vence hoje"
        elif due_on == today + timedelta(days=1):
            group = "Próximos 7 dias"
            due_label = "Vence amanhã"
        elif due_on <= today + timedelta(days=7):
            group = "Próximos 7 dias"
            due_label = f"Vence em {(due_on - today).days} dias"
        else:
            group = "Mais adiante"
            due_label = "Prazo futuro"
        activity.agenda_group = group  # type: ignore[attr-defined]
        activity.dashboard_due_label = due_label  # type: ignore[attr-defined]
    dashboard_overdue_count = activity_attention[0]["count"]
    dashboard_today_count = activity_attention[1]["count"]
    dashboard_open_count = agenda_query.count()
    if selected_agenda_filter:
        filter_copy = {
            "overdue": ("Atividades em atraso", "Priorize as tarefas cujo prazo já passou."),
            "today": ("Atividades para hoje", "Conclua ou encaminhe o que vence hoje."),
            "next_7_days": (
                "Próximos 7 dias",
                "Antecipe as tarefas com prazo nesta semana.",
            ),
            "blocked": ("Atividades impedidas", "Veja o motivo antes de decidir o próximo passo."),
            "unavailable": (
                "Fontes indisponíveis",
                "Confira as tarefas cujo dado de origem não está disponível.",
            ),
        }
        agenda_heading, agenda_description = filter_copy[selected_agenda_filter]
    else:
        agenda_heading = "Próximas atividades"
        agenda_description = "Ordenadas pelo prazo para você começar pelo que exige atenção."
    if dashboard_overdue_count:
        dashboard_summary_title = (
            f"Comece por {dashboard_overdue_count} atividade em atraso"
            if dashboard_overdue_count == 1
            else f"Comece por {dashboard_overdue_count} atividades em atraso"
        )
        dashboard_summary_text = "Depois, avance para o que vence hoje e planeje os próximos dias."
        dashboard_summary_url = f"{reverse('hub:dashboard')}?view={dashboard_view}&filter=overdue"
        dashboard_summary_action = "Revisar atrasadas"
    elif dashboard_today_count:
        dashboard_summary_title = (
            "Há 1 atividade para hoje"
            if dashboard_today_count == 1
            else f"Há {dashboard_today_count} atividades para hoje"
        )
        dashboard_summary_text = "Sua fila abaixo já está ordenada para facilitar a decisão."
        dashboard_summary_url = f"{reverse('hub:dashboard')}?view={dashboard_view}&filter=today"
        dashboard_summary_action = "Ver agenda de hoje"
    elif dashboard_open_count:
        dashboard_summary_title = (
            "Sua fila está sob controle"
            if dashboard_view == "mine"
            else "A carteira está sem prazos críticos"
        )
        dashboard_summary_text = "Confira a próxima atividade e antecipe o trabalho da semana."
        dashboard_summary_url = (
            f"{reverse('hub:dashboard')}?view={dashboard_view}&filter=next_7_days"
        )
        dashboard_summary_action = "Planejar a semana"
    else:
        dashboard_summary_title = "Nenhuma atividade aberta neste recorte"
        dashboard_summary_text = (
            "Consulte a Carteira para verificar trabalho compartilhado."
            if dashboard_view == "mine"
            else "Quando uma rotina gerar trabalho, ele aparecerá aqui com prazo e responsável."
        )
        dashboard_summary_url = (
            f"{reverse('hub:dashboard')}?view=portfolio"
            if dashboard_view == "mine"
            else reverse("hub:activities")
        )
        dashboard_summary_action = (
            "Ver carteira" if dashboard_view == "mine" else "Abrir central de atividades"
        )
    admin_workload: list[Membership] = []
    unassigned_activity_count = 0
    if dashboard_view == "management":
        active_activity_filter = Q(
            user__assigned_operational_activities__organization=office,
            user__assigned_operational_activities__company__in=scope,
        ) & ~Q(
            user__assigned_operational_activities__work_status__in=[
                OperationalActivity.WorkStatus.COMPLETED,
                OperationalActivity.WorkStatus.WAIVED,
            ]
        )
        overdue_activity_filter = active_activity_filter & (
            Q(user__assigned_operational_activities__internal_due_on__lt=today)
            | Q(
                user__assigned_operational_activities__internal_due_on__isnull=True,
                user__assigned_operational_activities__legal_due_on__lt=today,
            )
        )
        admin_workload = list(
            Membership.objects.filter(organization=office, is_active=True)
            .exclude(
                Q(user__email__startswith="demo-", user__email__endswith="@example.test")
                if office.is_demo
                else Q(pk__isnull=True)
            )
            .select_related("user")
            .annotate(
                open_activity_count=Count(
                    "user__assigned_operational_activities", filter=active_activity_filter
                ),
                overdue_activity_count=Count(
                    "user__assigned_operational_activities", filter=overdue_activity_filter
                ),
                blocked_activity_count=Count(
                    "user__assigned_operational_activities",
                    filter=active_activity_filter
                    & Q(
                        user__assigned_operational_activities__work_status=OperationalActivity.WorkStatus.BLOCKED
                    ),
                ),
            )
            .order_by("-open_activity_count", "user__full_name", "user__email")
        )
        unassigned_activity_count = open_activity_query.filter(assigned_to__isnull=True).count()
    work_areas = []
    if ProductModule.Code.NFSE in enabled_codes:
        work_areas.append(
            {
                "label": "Revisões de NFS-e",
                "count": review_count,
                "note": "Decisões de classificação pendentes",
                "url": reverse("hub:nfse-center") + "?status=unclassified",
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
            "page_title": {
                "mine": "Meu trabalho",
                "portfolio": "Carteira de trabalho",
                "management": "Gestão da operação",
            }[dashboard_view],
            "open_cases": open_cases,
            "dashboard_activities": dashboard_activities,
            "dashboard_view": dashboard_view,
            "agenda_page": agenda_page,
            "selected_agenda_filter": selected_agenda_filter,
            "agenda_heading": agenda_heading,
            "agenda_description": agenda_description,
            "agenda_today": today,
            "dashboard_overdue_count": dashboard_overdue_count,
            "dashboard_summary_title": dashboard_summary_title,
            "dashboard_summary_text": dashboard_summary_text,
            "dashboard_summary_url": dashboard_summary_url,
            "dashboard_summary_action": dashboard_summary_action,
            "closing_expanded": request.GET.get("closing_open") == "1",
            "activity_attention": activity_attention,
            "is_dashboard_administrator": is_dashboard_administrator,
            "admin_workload": admin_workload,
            "unassigned_activity_count": unassigned_activity_count,
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


def _can_configure_activity_models(membership: object) -> bool:
    return isinstance(membership, Membership) and membership.role in {
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
    }


@transaction.atomic
def _move_template_to_next_month(
    source: ActivityTemplate, *, actor: User, request: HttpRequest
) -> ActivityTemplate:
    """New version due in the month after the competência; assignments keep their cursor.

    The cursor already points past the competências generated by the old version, so the new
    one continues without duplicating or skipping a month (D-277).
    """

    source = ActivityTemplate.objects.select_for_update().get(pk=source.pk)
    latest = (
        ActivityTemplate.objects.filter(organization=source.organization, code=source.code)
        .aggregate(latest=models.Max("version"))["latest"]
        or source.version
    )
    moved = ActivityTemplate(
        organization=source.organization,
        code=source.code,
        title=source.title,
        area=source.area,
        description=source.description,
        evidence_requirement=source.evidence_requirement,
        frequency=source.frequency,
        legal_due_day=source.legal_due_day,
        internal_due_day=source.internal_due_day,
        legal_rule_code=source.legal_rule_code,
        internal_lead_business_days=source.internal_lead_business_days,
        requires_processing_closed=source.requires_processing_closed,
        requires_accepted_obligation=source.requires_accepted_obligation,
        due_month_offset=1,
        version=latest + 1,
    )
    moved.full_clean()
    moved.save()
    moved_assignments = 0
    for assignment in source.company_assignments.filter(active=True).select_for_update():
        ActivityTemplateAssignment.objects.create(
            organization=source.organization,
            template=moved,
            company=assignment.company,
            assigned_to=assignment.assigned_to,
            legal_due_day=assignment.legal_due_day,
            internal_due_day=assignment.internal_due_day,
            next_generation_competence=assignment.next_generation_competence,
        )
        assignment.active = False
        assignment.save(update_fields=["active", "updated_at"])
        moved_assignments += 1
    source.active = False
    source.save(update_fields=["active", "updated_at"])
    record_event(
        action="hub.activity_template.moved_to_next_month",
        actor=actor,
        organization=source.organization,
        target=moved,
        request=request,
        metadata={
            "code": moved.code,
            "from_version": source.version,
            "to_version": moved.version,
            "assignments": moved_assignments,
        },
    )
    return moved


@office_required
@require_http_methods(["GET", "POST"])
def activity_models(request: HttpRequest) -> HttpResponse:
    """Admin-only configuration for versioned templates and company assignments."""

    context = workspace_context(request)
    if is_nfse_only_subscription(context):
        return refuse(request, "Este contrato disponibiliza somente o fluxo NFS-e.")
    office = context["office"]
    membership = context["membership"]
    assert isinstance(office, Organization)
    if not _can_configure_activity_models(membership):
        raise PermissionDenied("Somente a administração configura modelos de atividades.")

    template_form = ActivityTemplateForm(prefix="template")
    assignment_form = ActivityTemplateAssignmentForm(organization=office, prefix="assignment")
    # The month an accountant closes is the previous one; generating it is the common case.
    generation_form = ActivityGenerationForm(
        initial={"competence": add_months(timezone.localdate().replace(day=1), -1)},
        prefix="generation",
    )
    invalid_action = ""
    response_status = 200
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "template":
            template_form = ActivityTemplateForm(request.POST, prefix="template")
            if template_form.is_valid():
                template = template_form.save(commit=False)
                template.organization = office
                template.version = (
                    ActivityTemplate.objects.filter(
                        organization=office, code=template.code
                    ).aggregate(latest=models.Max("version"))["latest"]
                    or 0
                ) + 1
                template.full_clean()
                template.save()
                record_event(
                    action="hub.activity_template.created",
                    actor=cast(User, request.user),
                    organization=office,
                    target=template,
                    request=request,
                    metadata={"code": template.code, "version": template.version},
                )
                messages.success(request, f"Modelo {template.code} v{template.version} criado.")
                return redirect(f"{reverse('hub:activity-models')}#model-library")
            invalid_action = "template"
            response_status = 400
            messages.error(request, "Revise os dados do modelo.")
        elif action == "assignment":
            assignment_form = ActivityTemplateAssignmentForm(
                request.POST, organization=office, prefix="assignment"
            )
            if assignment_form.is_valid():
                assignment = assignment_form.save(commit=False)
                assignment.organization = office
                assignment.full_clean()
                assignment.save()
                record_event(
                    action="hub.activity_template.assigned",
                    actor=cast(User, request.user),
                    organization=office,
                    target=assignment,
                    request=request,
                    metadata={
                        "template_id": str(assignment.template_id),
                        "company_id": str(assignment.company_id),
                    },
                )
                messages.success(request, "Modelo atribuído à empresa.")
                return redirect(f"{reverse('hub:activity-models')}#assignment-library")
            invalid_action = "assignment"
            response_status = 400
            messages.error(request, "Revise a atribuição do modelo.")
        elif action == "template-toggle":
            template = get_object_or_404(
                ActivityTemplate,
                id=request.POST.get("template_id"),
                organization=office,
            )
            template.active = not template.active
            template.save(update_fields=["active", "updated_at"])
            record_event(
                action="hub.activity_template.toggled",
                actor=cast(User, request.user),
                organization=office,
                target=template,
                request=request,
                metadata={
                    "code": template.code,
                    "version": template.version,
                    "active": template.active,
                },
            )
            state = "retomado" if template.active else "pausado"
            messages.success(request, f"Modelo {template.code} v{template.version} {state}.")
            return redirect(f"{reverse('hub:activity-models')}#model-library")
        elif action == "template-next-month":
            source = get_object_or_404(
                ActivityTemplate,
                id=request.POST.get("template_id"),
                organization=office,
                active=True,
                due_month_offset=0,
            )
            moved_template = _move_template_to_next_month(
                source, actor=cast(User, request.user), request=request
            )
            messages.success(
                request,
                f"Modelo {moved_template.code} v{moved_template.version}: "
                "prazo no mês seguinte à competência.",
            )
            return redirect(f"{reverse('hub:activity-models')}#model-library")
        elif action == "assignment-toggle":
            assignment = get_object_or_404(
                ActivityTemplateAssignment,
                id=request.POST.get("assignment_id"),
                organization=office,
            )
            assignment.active = not assignment.active
            assignment.next_generation_competence = competence_ready_until(
                timezone.localdate(), assignment.template
            )
            assignment.save(update_fields=["active", "next_generation_competence", "updated_at"])
            record_event(
                action="hub.activity_template.assignment_toggled",
                actor=cast(User, request.user),
                organization=office,
                target=assignment,
                request=request,
                metadata={
                    "template_id": str(assignment.template_id),
                    "company_id": str(assignment.company_id),
                    "active": assignment.active,
                },
            )
            state = "reativada" if assignment.active else "pausada"
            messages.success(request, f"A atribuição foi {state}.")
            return redirect(f"{reverse('hub:activity-models')}#assignment-library")
        elif action == "generate":
            generation_form = ActivityGenerationForm(request.POST, prefix="generation")
            if generation_form.is_valid():
                assignments = list(
                    ActivityTemplateAssignment.objects.filter(
                        organization=office,
                        active=True,
                        template__active=True,
                        template__frequency=ActivityTemplate.Frequency.MONTHLY,
                    ).select_related("template", "company", "assigned_to")
                )
                generated, ignored = generate_monthly_activities(
                    assignments=assignments,
                    competence=generation_form.cleaned_data["competence"],
                    actor=cast(User, request.user),
                    request=request,
                )
                messages.success(
                    request,
                    (
                        f"{len(generated)} atividade(s) gerada(s); {ignored} ocorrência(s) "
                        "já existente(s) ou inativa(s)."
                    ),
                )
                return redirect(f"{reverse('hub:activity-models')}#generation-step")
            invalid_action = "generate"
            response_status = 400
            messages.error(request, "Informe uma competência válida.")
        else:
            raise Http404

    template_query = ActivityTemplate.objects.filter(organization=office).annotate(
        assignment_count=Count("company_assignments"),
        active_assignment_count=Count(
            "company_assignments",
            filter=Q(company_assignments__active=True),
        ),
        company_count=Count("company_assignments__company", distinct=True),
    ).order_by("area", "code", "-version")
    assignment_query = ActivityTemplateAssignment.objects.filter(
        organization=office
    ).select_related("template", "company", "assigned_to")
    template_page = Paginator(template_query, 20).get_page(request.GET.get("templates_page"))
    rule_codes = {template.legal_rule_code for template in template_page.object_list}
    approved_rules: dict[str, TaxDeadlineRule] = {}
    for rule in TaxDeadlineRule.objects.filter(
        code__in=rule_codes - {""}, status=ReferenceStatus.APPROVED
    ).order_by("code", "-version"):
        approved_rules.setdefault(rule.code, rule)
    for template in template_page.object_list:
        template.legal_rule = approved_rules.get(template.legal_rule_code)  # type: ignore[attr-defined]
    assignment_page = Paginator(assignment_query, 30).get_page(
        request.GET.get("assignments_page")
    )
    template_params = request.GET.copy()
    template_params.pop("templates_page", None)
    assignment_params = request.GET.copy()
    assignment_params.pop("assignments_page", None)
    active_assignments = assignment_query.filter(active=True, template__active=True)
    active_template_count = template_query.filter(active=True).count()
    active_assignment_count = active_assignments.count()
    covered_company_count = active_assignments.values("company_id").distinct().count()
    ready_generation_count = active_assignments.filter(
        template__frequency=ActivityTemplate.Frequency.MONTHLY
    ).count()
    if active_template_count == 0:
        recommended_step = "template"
    elif active_assignment_count == 0:
        recommended_step = "assignment"
    else:
        recommended_step = "generate"
    context.update(
        {
            "page_title": "Modelos de atividades",
            "template_form": template_form,
            "assignment_form": assignment_form,
            "generation_form": generation_form,
            "activity_templates": template_page.object_list,
            "activity_template_page": template_page,
            "activity_assignment_page": assignment_page,
            "template_querystring": template_params.urlencode(),
            "assignment_querystring": assignment_params.urlencode(),
            "active_template_count": active_template_count,
            "active_assignment_count": active_assignment_count,
            "covered_company_count": covered_company_count,
            "ready_generation_count": ready_generation_count,
            "recommended_step": recommended_step,
            "invalid_action": invalid_action,
        }
    )
    return render(request, "hub/activity_models.html", context, status=response_status)


@office_required
def activities(request: HttpRequest) -> HttpResponse:
    """The personal operational queue, sourced only from explicit expected activities."""

    context = workspace_context(request)
    if is_nfse_only_subscription(context):
        return refuse(request, "Este contrato disponibiliza somente o fluxo NFS-e.")
    office = context["office"]
    assert isinstance(office, Organization)
    membership = context["membership"]
    active_membership_row = membership if isinstance(membership, Membership) else None
    if active_membership_row is None:
        raise Http404
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    queue = activity_queue_scope(context, cast(User, request.user)).select_related(
        "company", "assigned_to"
    )
    is_administrator = active_membership_row.role in {
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
    }
    base_queue = queue
    open_queue = base_queue.exclude(
        work_status__in=[
            OperationalActivity.WorkStatus.COMPLETED,
            OperationalActivity.WorkStatus.WAIVED,
        ]
    )
    area = request.GET.get("area", "")
    status = request.GET.get("status", "")
    freshness = request.GET.get("freshness", "")
    due = request.GET.get("due", "")
    overdue = request.GET.get("overdue", "")
    company_id = request.GET.get("company", "")
    assignee_id = request.GET.get("assignee", "")
    competence_value = request.GET.get("competence", "").strip()
    selected_area = ""
    selected_status = ""
    selected_freshness = ""
    selected_company = ""
    selected_company_label = ""
    selected_competence = competence_value
    selected_competence_date: date | None = None
    invalid_competence = False
    selected_assignee = ""
    selected_assignee_label = ""
    unassigned_value = request.GET.get("unassigned", "")
    selected_unassigned = unassigned_value == "1"
    invalid_filter_messages: list[str] = []
    if area:
        if area in ActivityTemplate.Area.values:
            queue = queue.filter(area=area)
            selected_area = area
        else:
            invalid_filter_messages.append("A área informada não existe.")
    if status:
        if status in OperationalActivity.WorkStatus.values:
            queue = queue.filter(work_status=status)
            selected_status = status
        elif status == "all":
            selected_status = status
        else:
            invalid_filter_messages.append("A situação informada não existe.")
    else:
        queue = queue.exclude(
            work_status__in=[
                OperationalActivity.WorkStatus.COMPLETED,
                OperationalActivity.WorkStatus.WAIVED,
            ]
        )
    if freshness:
        if freshness in OperationalActivity.Freshness.values:
            queue = queue.filter(freshness=freshness)
            selected_freshness = freshness
        else:
            invalid_filter_messages.append("A atualização informada não existe.")
    if company_id:
        try:
            selected_company_id = uuid.UUID(company_id)
        except ValueError:
            selected_company_id = None
        selected_company_row = (
            scope.filter(pk=selected_company_id).only("id", "name").first()
            if selected_company_id is not None
            else None
        )
        if selected_company_row is not None:
            queue = queue.filter(company_id=selected_company_id)
            selected_company = str(selected_company_id)
            selected_company_label = selected_company_row.name
        else:
            invalid_filter_messages.append("A empresa informada não pertence à sua carteira.")
    activity_assignees = User.objects.none()
    if is_administrator:
        activity_assignees = User.objects.filter(
            organization_memberships__organization=office,
            organization_memberships__is_active=True,
        ).distinct()
        if office.is_demo:
            activity_assignees = activity_assignees.exclude(
                email__startswith="demo-", email__endswith="@example.test"
            )
        try:
            selected_assignee_id = uuid.UUID(assignee_id)
        except ValueError:
            selected_assignee_id = None
        if (
            selected_assignee_id is not None
            and activity_assignees.filter(id=selected_assignee_id).exists()
        ):
            queue = queue.filter(assigned_to_id=selected_assignee_id)
            selected_assignee = str(selected_assignee_id)
            selected_assignee_row = activity_assignees.get(id=selected_assignee_id)
            selected_assignee_label = selected_assignee_row.full_name or selected_assignee_row.email
        elif assignee_id:
            invalid_filter_messages.append("O responsável informado não pertence a esta equipe.")
        if selected_unassigned:
            queue = queue.filter(assigned_to__isnull=True)
        elif unassigned_value:
            invalid_filter_messages.append("O filtro de responsabilidade é inválido.")
        if selected_assignee and selected_unassigned:
            invalid_filter_messages.append(
                "Escolha um responsável ou atividades sem responsável, não os dois."
            )
    elif assignee_id or unassigned_value:
        invalid_filter_messages.append("Seu perfil não pode filtrar a operação por responsável.")
    if re.fullmatch(r"\d{4}-\d{2}", competence_value):
        try:
            selected_competence_date = parse_date(f"{competence_value}-01")
        except ValueError:
            selected_competence_date = None
        if selected_competence_date is not None:
            queue = queue.filter(competence=selected_competence_date)
            selected_competence = competence_value
        else:
            invalid_competence = True
    elif competence_value:
        invalid_competence = True
    search_value = request.GET.get("q", "").strip()[:80]
    search_filter = (
        Q(title__icontains=search_value)
        | Q(company__name__icontains=search_value)
        | Q(company__dominio_code=search_value)
        if search_value
        else Q()
    )
    if search_value:
        queue = queue.filter(search_filter)
    today = timezone.localdate()
    due_today = Q(internal_due_on=today) | Q(internal_due_on__isnull=True, legal_due_on=today)
    due_next_seven_days = Q(
        internal_due_on__gt=today, internal_due_on__lte=today + timedelta(days=7)
    ) | Q(
        internal_due_on__isnull=True,
        legal_due_on__gt=today,
        legal_due_on__lte=today + timedelta(days=7),
    )
    if due == "today":
        queue = queue.filter(due_today)
    elif due == "next_7_days":
        queue = queue.filter(due_next_seven_days)
    elif due:
        invalid_filter_messages.append("O período de prazo informado não existe.")
    if overdue == "1":
        queue = queue.filter(
            Q(internal_due_on__lt=today) | Q(internal_due_on__isnull=True, legal_due_on__lt=today)
        )
    elif overdue:
        invalid_filter_messages.append("O filtro de atraso é inválido.")
    if due and overdue:
        invalid_filter_messages.append("Escolha apenas um recorte de prazo por vez.")
    if invalid_competence:
        invalid_filter_messages.append("Informe uma competência válida no formato mês/ano.")
    if invalid_filter_messages:
        queue = queue.none()

    def activity_filter_url(**updates: str | None) -> str:
        query = request.GET.copy()
        query.pop("page", None)
        for key in list(query):
            if not query.get(key):
                query.pop(key, None)
        for key, value in updates.items():
            if value:
                query[key] = value
            else:
                query.pop(key, None)
        encoded = query.urlencode()
        base = reverse("hub:activities")
        return f"{base}?{encoded}" if encoded else base

    priority_queue = open_queue.filter(search_filter)
    if selected_area:
        priority_queue = priority_queue.filter(area=selected_area)
    if selected_company:
        priority_queue = priority_queue.filter(company_id=uuid.UUID(selected_company))
    if selected_competence_date is not None:
        priority_queue = priority_queue.filter(competence=selected_competence_date)
    if selected_assignee:
        priority_queue = priority_queue.filter(assigned_to_id=uuid.UUID(selected_assignee))
    if selected_unassigned:
        priority_queue = priority_queue.filter(assigned_to__isnull=True)
    if invalid_filter_messages:
        priority_queue = priority_queue.none()
    priority_counts = priority_queue.aggregate(
        total=Count("pk"),
        overdue=Count(
            "pk",
            filter=Q(internal_due_on__lt=today)
            | Q(internal_due_on__isnull=True, legal_due_on__lt=today),
        ),
        today=Count("pk", filter=due_today),
        next_seven=Count("pk", filter=due_next_seven_days),
        blocked=Count(
            "pk", filter=Q(work_status=OperationalActivity.WorkStatus.BLOCKED)
        ),
        unavailable=Count(
            "pk", filter=Q(freshness=OperationalActivity.Freshness.UNAVAILABLE)
        ),
    )
    priority_filters = [
        {
            "label": "Em aberto",
            "count": priority_counts["total"],
            "url": activity_filter_url(status=None, freshness=None, due=None, overdue=None),
            "selected": not status and not freshness and not due and not overdue,
        },
        {
            "label": "Em atraso",
            "count": priority_counts["overdue"],
            "url": activity_filter_url(status=None, freshness=None, due=None, overdue="1"),
            "selected": overdue == "1" and not due,
        },
        {
            "label": "Para hoje",
            "count": priority_counts["today"],
            "url": activity_filter_url(status=None, freshness=None, due="today", overdue=None),
            "selected": due == "today" and not overdue,
        },
        {
            "label": "Próximos 7 dias",
            "count": priority_counts["next_seven"],
            "url": activity_filter_url(
                status=None, freshness=None, due="next_7_days", overdue=None
            ),
            "selected": due == "next_7_days" and not overdue,
        },
        {
            "label": "Impedidas",
            "count": priority_counts["blocked"],
            "url": activity_filter_url(
                status=OperationalActivity.WorkStatus.BLOCKED,
                freshness=None,
                due=None,
                overdue=None,
            ),
            "selected": status == OperationalActivity.WorkStatus.BLOCKED,
        },
        {
            "label": "Fonte indisponível",
            "count": priority_counts["unavailable"],
            "url": activity_filter_url(
                status=None,
                freshness=OperationalActivity.Freshness.UNAVAILABLE,
                due=None,
                overdue=None,
            ),
            "selected": freshness == OperationalActivity.Freshness.UNAVAILABLE,
        },
    ]

    area_labels = dict(ActivityTemplate.Area.choices)
    status_labels = dict(OperationalActivity.WorkStatus.choices)
    freshness_labels = dict(OperationalActivity.Freshness.choices)
    active_filters: list[dict[str, str]] = []

    def add_active_filter(label: str, key: str) -> None:
        active_filters.append({"label": label, "url": activity_filter_url(**{key: None})})

    if search_value:
        add_active_filter(f"Busca: {search_value}", "q")
    if selected_area:
        add_active_filter(f"Área: {area_labels[selected_area]}", "area")
    if selected_status:
        add_active_filter(
            "Situação: "
            + (
                "Todas, inclusive encerradas"
                if selected_status == "all"
                else status_labels[selected_status]
            ),
            "status",
        )
    if selected_freshness:
        add_active_filter(f"Atualização: {freshness_labels[selected_freshness]}", "freshness")
    if selected_company:
        add_active_filter(f"Empresa: {selected_company_label}", "company")
    if selected_competence_date is not None and not invalid_competence:
        add_active_filter(f"Competência: {selected_competence_date:%m/%Y}", "competence")
    if selected_assignee:
        add_active_filter(f"Responsável: {selected_assignee_label}", "assignee")
    if selected_unassigned:
        add_active_filter("Sem responsável", "unassigned")
    if due == "today":
        add_active_filter("Prazo: hoje", "due")
    elif due == "next_7_days":
        add_active_filter("Prazo: próximos 7 dias", "due")
    if overdue == "1":
        add_active_filter("Prazo: em atraso", "overdue")

    page = Paginator(
        queue.order_by(
            Coalesce("internal_due_on", "legal_due_on").asc(nulls_last=True), "-created_at", "pk"
        ),
        30,
    ).get_page(request.GET.get("page"))
    page_items = list(page.object_list)
    for item in page_items:
        item.is_overdue = activity_is_overdue(item, today=today)
        due_on = item.internal_due_on or item.legal_due_on
        item.queue_due_on = due_on
        item.queue_due_kind = (
            "Prazo interno" if item.internal_due_on else "Prazo legal"
        )
        if due_on is None:
            item.queue_due_label = "Sem prazo definido"
        elif due_on < today:
            overdue_days = (today - due_on).days
            item.queue_due_label = (
                "1 dia em atraso" if overdue_days == 1 else f"{overdue_days} dias em atraso"
            )
        elif due_on == today:
            item.queue_due_label = "Vence hoje"
        elif due_on == today + timedelta(days=1):
            item.queue_due_label = "Vence amanhã"
        elif due_on <= today + timedelta(days=7):
            item.queue_due_label = f"Vence em {(due_on - today).days} dias"
        else:
            item.queue_due_label = "Prazo futuro"
        # Only a specific step earns the cell; "open and check" is what the row link does.
        if item.work_status == OperationalActivity.WorkStatus.BLOCKED:
            item.queue_next_step = item.blocked_reason or "Resolver impedimento"
        elif item.freshness == OperationalActivity.Freshness.UNAVAILABLE:
            item.queue_next_step = "Fonte indisponível"
        elif item.assigned_to_id is None:
            item.queue_next_step = "Sem responsável"
        elif item.source_nfse_review_id:
            item.queue_next_step = "Classificar NFS-e"
        elif item.source_triage_item_id:
            item.queue_next_step = "Conferir na Triagem"
        elif item.source_fiscal_guide_id:
            item.queue_next_step = "Acompanhar guia"
        elif item.source_dte_message_id:
            item.queue_next_step = "Ler mensagem DTE"
        else:
            item.queue_next_step = ""
    pagination_query = request.GET.copy()
    pagination_query.pop("page", None)
    context.update(
        {
            "page_title": ("Atividades do escritório" if is_administrator else "Minhas atividades"),
            "activities": page_items,
            "activities_page": page,
            "activity_areas": ActivityTemplate.Area.choices,
            "activity_statuses": OperationalActivity.WorkStatus.choices,
            "selected_area": selected_area,
            "selected_status": selected_status,
            "selected_freshness": selected_freshness,
            "selected_due": due,
            "selected_overdue": overdue,
            "activity_freshnesses": OperationalActivity.Freshness.choices,
            "selected_company": selected_company,
            "activity_assignees": activity_assignees,
            "selected_assignee": selected_assignee,
            "selected_unassigned": selected_unassigned,
            "selected_competence": selected_competence,
            "invalid_competence": invalid_competence,
            "invalid_filter_messages": invalid_filter_messages,
            "is_activity_administrator": is_administrator,
            "selected_search": search_value,
            "secondary_filters_active": bool(
                selected_area or selected_status or selected_freshness or selected_unassigned
            ),
            "can_bulk_activities": bool(context["support_can_mutate"])
            and active_membership_row.role
            not in {Membership.Role.AUDITOR, Membership.Role.BILLING},
            "can_bulk_assign": is_administrator,
            "can_bulk_reschedule": active_membership_row.role
            in {Membership.Role.OWNER, Membership.Role.ADMIN, Membership.Role.MANAGER},
            "priority_filters": priority_filters,
            "active_filters": active_filters,
            "filters_expanded": bool(
                invalid_filter_messages
                or selected_area
                or selected_status
                or selected_freshness
                or selected_company
                or competence_value
                or selected_assignee
                or selected_unassigned
            ),
            "is_activity_filtered": bool(active_filters or invalid_filter_messages),
            "clear_activity_filters_url": reverse("hub:activities"),
            "activities_querystring": pagination_query.urlencode(),
            "open_activity_count": priority_counts["total"],
        }
    )
    return render(request, "hub/activities.html", context)


def activity_queue_scope(
    context: dict[str, object], user: User
) -> QuerySet[OperationalActivity]:
    """Activities a person may see in the queue: the portfolio for the administration,
    otherwise their own work plus unassigned work in their portfolio."""

    office = context["office"]
    membership = context["membership"]
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    queue = OperationalActivity.objects.filter(organization=office, company__in=scope)
    if not (
        isinstance(membership, Membership)
        and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
    ):
        queue = queue.filter(Q(assigned_to=user) | Q(assigned_to__isnull=True))
    return queue


@office_required
@require_http_methods(["GET"])
def workspace_search(request: HttpRequest) -> HttpResponse:
    """Search inside the person's portfolio and modules (D-277); results open the record."""

    context = workspace_context(request)
    user = cast(User, request.user)
    query = request.GET.get("q", "").strip()[:80]
    if rate_limited(f"workspace-search:{user.pk}", limit=60, window_seconds=60):
        return HttpResponse("Aguarde um minuto antes de buscar novamente.", status=429)
    membership = context["membership"]
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    documents = None
    if collaborator_can_use_module(context, ProductModule.Code.NFSE):
        nfse_companies = (
            company_queryset_for_module(membership, ProductModule.Code.NFSE)
            if isinstance(membership, Membership)
            else companies
        )
        documents = NfseDocument.objects.filter(
            organization=context["office"], company__in=nfse_companies.filter(pk__in=companies)
        )
    groups = (
        search_workspace(
            query=query,
            companies=companies,
            activities=(
                activity_queue_scope(context, user)
                if not is_nfse_only_subscription(context)
                else OperationalActivity.objects.none()
            ),
            documents=documents,
        )
        if query
        else []
    )
    context.update({"page_title": "Busca", "search_query": query, "search_groups": groups})
    template = (
        "hub/partials/search_results.html"
        if request.GET.get("partial") == "1"
        else "hub/search.html"
    )
    return render(request, template, context)


@office_required
@require_http_methods(["GET", "POST"])
def notifications_center(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    user = cast(User, request.user)
    office = context["office"]
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    visible = Notification.objects.filter(organization=office, recipient=user).filter(
        Q(company__isnull=True) | Q(company__in=companies)
    )
    if request.method == "POST":
        if request.POST.get("action") == "read-all":
            visible.filter(read_at__isnull=True).update(read_at=timezone.now())
            messages.success(request, "Avisos marcados como lidos.")
        return redirect("hub:notifications")
    show = request.GET.get("mostrar", "")
    rows = visible.select_related("activity", "company")
    if show != "todos":
        rows = rows.filter(read_at__isnull=True)
    page = Paginator(rows.order_by("-created_at"), 30).get_page(request.GET.get("pagina"))
    context.update(
        {
            "page_title": "Avisos",
            "notifications": page.object_list,
            "notifications_page": page,
            "notifications_show_all": show == "todos",
        }
    )
    return render(request, "hub/notifications.html", context)


@office_required
@require_http_methods(["GET"])
def notification_open(request: HttpRequest, notification_id: uuid.UUID) -> HttpResponse:
    """Mark as read and go to the record; access is checked again on arrival."""

    context = workspace_context(request)
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    notice = get_object_or_404(
        Notification.objects.filter(Q(company__isnull=True) | Q(company__in=companies)),
        pk=notification_id,
        organization=context["office"],
        recipient=request.user,
    )
    if notice.read_at is None:
        notice.read_at = timezone.now()
        notice.save(update_fields=["read_at", "updated_at"])
    if notice.activity_id:
        return redirect("hub:activity-detail", activity_id=notice.activity_id)
    if notice.kind == Notification.Kind.CERTIFICATE_EXPIRING:
        return redirect("hub:certificates")
    if notice.company_id:
        return redirect("hub:company-detail", company_id=notice.company_id)
    return redirect("hub:notifications")


ACTIVITY_BULK_LIMIT = 50


@office_required
@require_http_methods(["POST"])
def activity_bulk_action(request: HttpRequest) -> HttpResponse:
    """Assign, reschedule or complete up to 50 activities (D-277); all checks per item."""

    context = workspace_context(request)
    if is_nfse_only_subscription(context):
        raise Http404
    membership = context["membership"]
    office = context["office"]
    if not isinstance(membership, Membership) or not isinstance(office, Organization):
        raise Http404
    back = request.POST.get("next") or reverse("hub:activities")
    if not url_has_allowed_host_and_scheme(back, allowed_hosts={request.get_host()}):
        back = reverse("hub:activities")
    if office.is_demo:
        messages.info(request, "Demonstração: ações em lote não gravam alterações.")
        return redirect(back)
    if not context["support_can_mutate"]:
        return refuse(request, "Sessão de suporte somente leitura.")
    activity_ids = list(
        dict.fromkeys(value for value in request.POST.getlist("activity_ids") if value)
    )
    if not activity_ids:
        messages.error(request, "Selecione ao menos uma atividade.")
        return redirect(back)
    if len(activity_ids) > ACTIVITY_BULK_LIMIT:
        messages.error(request, f"Ações em lote aceitam até {ACTIVITY_BULK_LIMIT} atividades.")
        return redirect(back)
    action = request.POST.get("action", "")
    if action not in {"assign", "reschedule", "complete"}:
        messages.error(request, "Escolha uma ação.")
        return redirect(back)
    reason = request.POST.get("reason", "").strip()
    if action != "complete" and not reason:
        messages.error(request, "Informe o motivo da alteração em lote.")
        return redirect(back)
    try:
        parsed_ids = [uuid.UUID(value) for value in activity_ids]
    except ValueError:
        messages.error(request, "Seleção inválida. Recarregue a lista.")
        return redirect(back)
    due_value: date | None = None
    if action == "reschedule":
        due_value = parse_date(request.POST.get("internal_due_on", ""))
        if due_value is None:
            messages.error(request, "Informe o novo prazo interno.")
            return redirect(back)
    actor = cast(User, request.user)
    activities = list(
        activity_queue_scope(context, actor)
        .filter(pk__in=parsed_ids)
        .select_related("company", "assigned_to")
        .order_by("pk")
    )
    if len(activities) != len(parsed_ids):
        messages.error(request, "Uma ou mais atividades não estão mais disponíveis para você.")
        return redirect(back)
    if action == "complete":
        completed = 0
        skipped: list[str] = []
        for activity in activities:
            try:
                with transaction.atomic():
                    complete_activity(
                        activity=activity, membership=membership, actor=actor, request=request
                    )
            except (PermissionDenied, ValidationError) as error:
                detail = error.messages[0] if isinstance(error, ValidationError) else str(error)
                skipped.append(f"{activity.title} · {activity.company.name}: {detail}")
            else:
                completed += 1
        if completed:
            messages.success(request, f"{completed} atividade(s) concluída(s).")
        for line in skipped[:5]:
            messages.warning(request, f"Não concluída — {line}")
        if len(skipped) > 5:
            messages.warning(request, f"Outras {len(skipped) - 5} não puderam ser concluídas.")
        return redirect(back)
    try:
        with transaction.atomic():
            for activity in activities:
                if action == "assign":
                    assign_activity(
                        activity=activity,
                        membership=membership,
                        actor=actor,
                        assignee_id=request.POST.get("assignee", ""),
                        expected_assignee_id=request.POST.get(
                            f"expected_assignee_{activity.pk}", ""
                        ),
                        reason=reason,
                        request=request,
                    )
                else:
                    assert due_value is not None
                    reschedule_activity(
                        activity=activity,
                        membership=membership,
                        actor=actor,
                        internal_due_on=due_value,
                        expected_internal_due_on=request.POST.get(
                            f"expected_due_{activity.pk}", ""
                        ),
                        reason=reason,
                        request=request,
                    )
    except (PermissionDenied, ValidationError) as error:
        detail = error.messages[0] if isinstance(error, ValidationError) else str(error)
        messages.error(request, f"Nada foi alterado: {detail}")
        return redirect(back)
    messages.success(
        request,
        f"{len(activities)} atividade(s) "
        + ("redistribuída(s)." if action == "assign" else "com novo prazo interno."),
    )
    return redirect(back)


@office_required
@require_http_methods(["POST"])
def activity_reschedule(request: HttpRequest, activity_id: uuid.UUID) -> HttpResponse:
    context = workspace_context(request)
    activity, membership = _activity_in_scope_or_404(context=context, activity_id=activity_id)
    if activity.organization.is_demo or not context["support_can_mutate"]:
        return refuse(request, "Este acesso não altera prazos.")
    due_value = parse_date(request.POST.get("internal_due_on", ""))
    if due_value is None:
        messages.error(request, "Informe o novo prazo interno.")
        return redirect("hub:activity-detail", activity_id=activity.pk)
    try:
        reschedule_activity(
            activity=activity,
            membership=membership,
            actor=cast(User, request.user),
            internal_due_on=due_value,
            expected_internal_due_on=request.POST.get("expected_internal_due_on", ""),
            reason=request.POST.get("reason", ""),
            request=request,
        )
    except PermissionDenied as error:
        return refuse(request, str(error))
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Prazo interno atualizado.")
    return redirect("hub:activity-detail", activity_id=activity.pk)


@office_required
@require_http_methods(["POST"])
def activity_note(request: HttpRequest, activity_id: uuid.UUID) -> HttpResponse:
    context = workspace_context(request)
    activity, membership = _activity_in_scope_or_404(context=context, activity_id=activity_id)
    if activity.organization.is_demo or not context["support_can_mutate"]:
        return refuse(request, "Este acesso não registra observações.")
    try:
        add_activity_note(
            activity=activity,
            membership=membership,
            actor=cast(User, request.user),
            note=request.POST.get("note", ""),
            request=request,
        )
    except PermissionDenied as error:
        return refuse(request, str(error))
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Observação registrada.")
    return redirect(f"{reverse('hub:activity-detail', args=[activity.pk])}#historico")


@office_required
@require_http_methods(["POST"])
def activity_claim(request: HttpRequest, activity_id: uuid.UUID) -> HttpResponse:
    context = workspace_context(request)
    activity, membership = _activity_in_scope_or_404(context=context, activity_id=activity_id)
    if activity.organization.is_demo or not context["support_can_mutate"]:
        return refuse(request, "Este acesso não assume atividades.")
    try:
        claim_activity(
            activity=activity,
            membership=membership,
            actor=cast(User, request.user),
            request=request,
        )
    except PermissionDenied as error:
        return refuse(request, str(error))
    except ValidationError as error:
        messages.error(request, error.messages[0])
    else:
        messages.success(request, "Atividade assumida.")
    return redirect("hub:activity-detail", activity_id=activity.pk)


def _activity_in_scope_or_404(
    *, context: dict[str, object], activity_id: uuid.UUID
) -> tuple[OperationalActivity, Membership]:
    if is_nfse_only_subscription(context):
        raise Http404
    membership = context["membership"]
    if not isinstance(membership, Membership):
        raise Http404
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    activity = get_object_or_404(
        OperationalActivity.objects.select_related(
            "company",
            "assigned_to",
            "source_fiscal_guide",
            "source_dctfweb_document",
            "source_parcelamento_operation",
        ),
        pk=activity_id,
        organization=context["office"],
        company__in=scope,
    )
    return activity, membership


@office_required
@require_http_methods(["GET", "POST"])
def activity_detail(request: HttpRequest, activity_id: uuid.UUID) -> HttpResponse:
    context = workspace_context(request)
    activity, membership = _activity_in_scope_or_404(context=context, activity_id=activity_id)
    can_assign = (
        bool(context["support_can_mutate"])
        and not activity.organization.is_demo
        and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
        and can_operate_activity(membership=membership, activity=activity)
        and activity.work_status not in {"completed", "waived"}
    )
    inline_rerender = bool(getattr(request, "_activity_inline_rerender", False))
    assignment_form = OperationalAssignmentForm(
        request.POST if request.method == "POST" and not inline_rerender else None,
        initial={
            "assignee": str(activity.assigned_to_id or ""),
            "expected_assignee": str(activity.assigned_to_id or ""),
        },
        prefix="assignment",
    )
    choices = [("", "Sem responsável")]
    if can_assign:
        for candidate in (
            Membership.objects.filter(
                organization_id=membership.organization_id,
                is_active=True,
                user__is_active=True,
            )
            .select_related("user", "organization")
            .order_by("user__email")
        ):
            if can_operate_activity(membership=candidate, activity=activity):
                choices.append(
                    (str(candidate.user_id), candidate.user.full_name or candidate.user.email)
                )
    assignment_form.fields["assignee"].choices = choices  # type: ignore[attr-defined]
    if request.method == "POST" and not inline_rerender:
        if not can_assign or request.POST.get("action") != "assign":
            return refuse(request, "Este perfil ou estado não permite redistribuir a atividade.")
        if assignment_form.is_valid():
            try:
                assign_activity(
                    activity=activity,
                    membership=membership,
                    actor=cast(User, request.user),
                    assignee_id=assignment_form.cleaned_data["assignee"],
                    expected_assignee_id=assignment_form.cleaned_data["expected_assignee"],
                    reason=assignment_form.cleaned_data["reason"],
                    request=request,
                )
            except (PermissionDenied, ValidationError) as exc:
                assignment_form.add_error(None, str(exc))
            else:
                messages.success(
                    request, "Responsável atualizado e alteração registrada no histórico."
                )
                return redirect("hub:activity-detail", activity_id=activity.pk)
    origin = None
    if activity.source_nfse_review_id:
        review = activity.source_nfse_review
        if (
            review
            and review.organization_id == activity.organization_id
            and review.document.company_id == activity.company_id
        ):
            origin = {
                "label": "Classificar NFS-e na lista",
                "status": review.get_status_display(),
                "url": reverse("hub:nfse-center")
                + "?status=unclassified&q="
                + quote(review.document.company.name),
                "allowed": collaborator_can_use_module(context, ProductModule.Code.NFSE),
            }
    elif activity.source_triage_item_id:
        item = activity.source_triage_item
        if (
            item
            and item.organization_id == activity.organization_id
            and item.company_id == activity.company_id
        ):
            origin = {
                "label": "Abrir arquivo na Triagem",
                "status": item.get_status_display(),
                "url": reverse("hub:triage-item", args=[item.pk]),
                "allowed": collaborator_can_use_module(context, ProductModule.Code.TRIAGE),
            }
    elif activity.source_reconciliation_file_id:
        source = activity.source_reconciliation_file
        if (
            source
            and source.organization_id == activity.organization_id
            and source.company_id == activity.company_id
        ):
            run = source.runs.order_by("-created_at", "-pk").first()
            origin = {
                "label": "Abrir arquivo na Conciliação",
                "status": run.get_state_display() if run else "Aguardando processamento",
                "url": f"{reverse('hub:reconciliation')}?source_file={source.pk}#processamentos",
                "allowed": collaborator_can_use_module(context, ProductModule.Code.RECONCILIATION)
                and ProductModule.objects.filter(
                    organization_id=activity.organization_id,
                    code=ProductModule.Code.RECONCILIATION,
                    enabled=True,
                ).exists(),
            }
    elif activity.source_fiscal_guide_id:
        guide = activity.source_fiscal_guide
        if (
            guide
            and guide.organization_id == activity.organization_id
            and guide.company_id == activity.company_id
        ):
            origin = {
                "label": "Abrir guia",
                "status": guide.get_status_display(),
                "url": reverse("hub:guide-detail", args=[guide.pk]),
                "allowed": collaborator_can_use_module(context, ProductModule.Code.GUIDES),
            }
    elif activity.source_dctfweb_document_id:
        document = activity.source_dctfweb_document
        if (
            document
            and document.organization_id == activity.organization_id
            and document.company_id == activity.company_id
        ):
            origin = {
                "label": "Abrir central de Guias e DCTFWeb",
                "status": document.get_status_display(),
                "url": reverse("hub:guides"),
                "allowed": collaborator_can_use_module(context, ProductModule.Code.GUIDES),
            }
    elif activity.source_parcelamento_operation_id:
        operation = activity.source_parcelamento_operation
        if (
            operation
            and operation.organization_id == activity.organization_id
            and operation.company_id == activity.company_id
        ):
            origin = {
                "label": "Abrir parcelamentos",
                "status": operation.get_status_display(),
                "url": reverse("hub:parcelamentos"),
                "allowed": collaborator_can_use_module(context, ProductModule.Code.INTEGRA),
            }
    dte_summary_url = None
    dte_source = activity.source_dte_message
    if (
        dte_source
        and dte_source.organization_id == activity.organization_id
        and dte_source.company_id == activity.company_id
        and collaborator_can_use_module(context, ProductModule.Code.INTEGRA)
        and ProductModule.objects.filter(
            organization_id=activity.organization_id,
            code=ProductModule.Code.INTEGRA,
            enabled=True,
        ).exists()
    ):
        dte_summary_url = reverse("hub:dte-message-detail", args=[dte_source.pk])
    payroll_review_url = None
    payroll_source = activity.source_payroll_snapshot
    if payroll_source is not None and (
        payroll_source.organization_id == activity.organization_id
        and payroll_source.company_id == activity.company_id
        and payroll_source.competence == activity.competence
    ):
        payroll_review_url = (
            f"{reverse('hub:company-detail', args=[activity.company_id])}"
            f"?payroll_competence={payroll_source.competence.isoformat()}#folha"
        )
    completion_missing = completion_requirements(activity)
    event_labels = {
        "assigned": "Responsável atualizado",
        "blocked": "Impedimento registrado",
        "completed": "Atividade concluída",
        "evidence_recorded": "Evidência registrada",
        "reopened_from_source": "Reaberta pela fonte",
        "dte_received": "Comunicação recebida",
        "dte_result_uncertain": "Resultado a confirmar",
        "dte_result_confirmed": "Resultado confirmado",
        "dte_analysis_reopened": "Análise reaberta",
        "reform_received": "Publicação recebida",
        "payroll_received": "Folha recebida",
        "generated": "Atividade gerada",
        "due_changed": "Prazo alterado",
        "note": "Observação",
        "legal_due_unavailable": "Prazo legal ausente",
        "internal_due_adjusted": "Prazo interno ajustado",
    }
    activity_events = list(activity.events.select_related("actor").all())
    # Assignments recorded before 06/10/2026 kept user identifiers in the text. History is
    # immutable, so the identifiers are translated to names of this office when shown.
    legacy_ids = {
        match
        for event in activity_events
        if event.event_type == "assigned"
        for match in _UUID_PATTERN.findall(event.summary)
    }
    legacy_names = (
        {
            str(user.pk): user.display_name
            for user in User.objects.filter(
                pk__in=legacy_ids,
                organization_memberships__organization_id=activity.organization_id,
            ).distinct()
        }
        if legacy_ids
        else {}
    )
    for event in activity_events:
        event.display_label = event_labels.get(  # type: ignore[attr-defined]
            event.event_type,
            "Atualização registrada",
        )
        if legacy_ids and event.event_type == "assigned":
            event.summary = _UUID_PATTERN.sub(
                lambda match: legacy_names.get(match.group(0), "pessoa removida"),
                event.summary,
            )
    is_closed = activity.work_status in {
        OperationalActivity.WorkStatus.COMPLETED,
        OperationalActivity.WorkStatus.WAIVED,
    }
    can_manage_activity = (
        bool(context["support_can_mutate"])
        and not activity.organization.is_demo
        and can_operate_activity(membership=membership, activity=activity)
    )
    if is_closed:
        next_action = {
            "title": "Atividade encerrada",
            "description": (
                "Consulte as evidências e a trilha preservada. Uma nova pendência precisa "
                "vir da fonte ou de uma revisão aplicável."
            ),
            "state": "done",
        }
    elif origin:
        next_action = {
            "title": "Continue no módulo de origem",
            "description": (
                "Resolva a etapa indicada na origem; o resultado volta para esta atividade "
                "sem perder o histórico."
            ),
            "state": "attention",
        }
    elif activity.work_status == OperationalActivity.WorkStatus.BLOCKED:
        next_action = {
            "title": "Resolva o impedimento registrado",
            "description": activity.blocked_reason
            or "Confira o impedimento e registre nova evidência quando o trabalho puder continuar.",
            "state": "attention",
        }
    elif completion_missing:
        next_action = {
            "title": "Cumpra a condição para concluir",
            "description": completion_missing[0],
            "state": "attention",
        }
    else:
        next_action = {
            "title": "Revise e conclua a atividade",
            "description": (
                "As condições conhecidas estão atendidas. Confira a evidência antes de "
                "confirmar a conclusão."
            ),
            "state": "ready",
        }
    context.update(
        {
            "page_title": activity.title,
            "payroll_review_url": payroll_review_url,
            "dte_summary_url": dte_summary_url,
            "activity_origin": origin,
            "assignment_form": assignment_form,
            "can_assign_activity": can_assign,
            "activity": activity,
            "activity_evidence": activity.evidence_items.select_related("recorded_by").all(),
            "activity_source_observations": activity.source_observations.select_related(
                "data_source"
            ).all(),
            "activity_events": activity_events,
            "evidence_form": getattr(
                request,
                "_activity_evidence_form",
                OperationalEvidenceForm(),
            ),
            "block_form": getattr(
                request,
                "_activity_block_form",
                OperationalBlockForm(),
            ),
            "activity_active_action": getattr(request, "_activity_active_action", ""),
            "activity_action_error": getattr(request, "_activity_action_error", ""),
            "activity_completion_missing": completion_missing,
            "activity_next_action": next_action,
            "activity_is_closed": is_closed,
            "can_manage_activity": can_manage_activity,
            "can_reschedule_activity": can_manage_activity
            and not is_closed
            and can_reschedule_activity(membership=membership, activity=activity),
            "can_claim_activity": can_manage_activity
            and not is_closed
            and activity.assigned_to_id is None,
            "is_overdue": activity_is_overdue(activity),
        }
    )
    return render(
        request,
        "hub/activity_detail.html",
        context,
        status=(
            400
            if bool(assignment_form.errors)
            or bool(getattr(request, "_activity_action_error", ""))
            else 200
        ),
    )


@office_required
@require_http_methods(["POST"])
def activity_add_evidence(request: HttpRequest, activity_id: uuid.UUID) -> HttpResponseBase:
    context = workspace_context(request)
    activity, membership = _activity_in_scope_or_404(context=context, activity_id=activity_id)
    if not context["support_can_mutate"]:
        return refuse(request, "Esta sessão permite somente consulta.")
    form = OperationalEvidenceForm(request.POST)
    if not form.is_valid():
        request._activity_inline_rerender = True  # type: ignore[attr-defined]
        request._activity_evidence_form = form  # type: ignore[attr-defined]
        request._activity_active_action = "evidence"  # type: ignore[attr-defined]
        request._activity_action_error = "Revise a evidência antes de registrar."  # type: ignore[attr-defined]
        return activity_detail(request, activity.id)
    try:
        add_human_evidence(
            activity=activity,
            membership=membership,
            actor=cast(User, request.user),
            request=request,
            reference=form.cleaned_data["reference"],
            summary=form.cleaned_data["summary"],
        )
    except (PermissionDenied, ValidationError) as exc:
        form.add_error(None, _user_error_message(exc))
        request._activity_inline_rerender = True  # type: ignore[attr-defined]
        request._activity_evidence_form = form  # type: ignore[attr-defined]
        request._activity_active_action = "evidence"  # type: ignore[attr-defined]
        request._activity_action_error = "Não foi possível registrar a evidência."  # type: ignore[attr-defined]
        return activity_detail(request, activity.id)
    else:
        messages.success(request, "Evidência registrada na trilha da atividade.")
    return redirect("hub:activity-detail", activity_id=activity.id)


@office_required
@require_http_methods(["POST"])
def activity_block(request: HttpRequest, activity_id: uuid.UUID) -> HttpResponseBase:
    context = workspace_context(request)
    activity, membership = _activity_in_scope_or_404(context=context, activity_id=activity_id)
    if not context["support_can_mutate"]:
        return refuse(request, "Esta sessão permite somente consulta.")
    form = OperationalBlockForm(request.POST)
    if not form.is_valid():
        request._activity_inline_rerender = True  # type: ignore[attr-defined]
        request._activity_block_form = form  # type: ignore[attr-defined]
        request._activity_active_action = "block"  # type: ignore[attr-defined]
        request._activity_action_error = "Descreva o impedimento para registrá-lo."  # type: ignore[attr-defined]
        return activity_detail(request, activity.id)
    try:
        block_activity(
            activity=activity,
            membership=membership,
            actor=cast(User, request.user),
            request=request,
            reason=form.cleaned_data["reason"],
        )
    except (PermissionDenied, ValidationError) as exc:
        form.add_error(None, _user_error_message(exc))
        request._activity_inline_rerender = True  # type: ignore[attr-defined]
        request._activity_block_form = form  # type: ignore[attr-defined]
        request._activity_active_action = "block"  # type: ignore[attr-defined]
        request._activity_action_error = "Não foi possível registrar o impedimento."  # type: ignore[attr-defined]
        return activity_detail(request, activity.id)
    else:
        messages.success(request, "Impedimento registrado e visível para o escritório.")
    return redirect("hub:activity-detail", activity_id=activity.id)


@office_required
@require_http_methods(["POST"])
def activity_complete(request: HttpRequest, activity_id: uuid.UUID) -> HttpResponse:
    context = workspace_context(request)
    activity, membership = _activity_in_scope_or_404(context=context, activity_id=activity_id)
    if not context["support_can_mutate"]:
        return refuse(request, "Esta sessão permite somente consulta.")
    try:
        complete_activity(
            activity=activity,
            membership=membership,
            actor=cast(User, request.user),
            request=request,
        )
    except (PermissionDenied, ValidationError) as exc:
        messages.error(request, _user_error_message(exc))
    else:
        messages.success(request, "Atividade concluída com a evidência registrada.")
    return redirect("hub:activity-detail", activity_id=activity.id)


@office_required
@require_http_methods(["GET", "POST"])
def nfse_center(request: HttpRequest) -> HttpResponseBase:
    """Show only the fiscal documents belonging to the active company context."""

    context = workspace_context(request)
    if not collaborator_can_use_module(context, ProductModule.Code.NFSE):
        return refuse(request, "Seu acesso n\u00e3o inclui NFS-e Inteligente.")
    office = context["office"]
    assert isinstance(office, Organization)
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    selected_company = None
    company_filter = request.GET.get("company", "")
    if company_filter:
        try:
            company_uuid = uuid.UUID(company_filter)
        except ValueError as exc:
            raise Http404 from exc
        history_scope = _company_history_scope(context)
        selected_company = get_object_or_404(history_scope, pk=company_uuid)
        scope = history_scope.filter(pk=selected_company.pk)
    membership = context["membership"]
    can_manage_sync = bool(
        is_demo_visitor(request, office)
        or (
            context["support_can_mutate"]
            and isinstance(membership, Membership)
            and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
        )
    )
    can_export_nfse = bool(
        context["support_can_mutate"]
        and (
            context["support_session"] is not None
            or (
                isinstance(membership, Membership)
                and membership.role in {
                    Membership.Role.OWNER, Membership.Role.ADMIN,
                    Membership.Role.MANAGER, Membership.Role.OPERATOR,
                }
            )
        )
    )
    can_classify_nfse = bool(is_demo_visitor(request, office) or can_export_nfse)
    if selected_company is not None and not selected_company.active:
        can_classify_nfse = False
    can_demo_download_nfse = bool(
        office.is_demo and (is_demo_visitor(request, office) or can_export_nfse)
    )
    can_download_nfse = bool(
        can_demo_download_nfse
        or (not office.is_demo and (
            can_export_nfse or context["support_session"] is not None
            or (isinstance(membership, Membership) and membership.role == Membership.Role.AUDITOR)
        ))
    )

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action in {"retention_report_pdf", "retention_report_xlsx", "download_original_xmls"}:
            if not can_download_nfse:
                return refuse(request, "Seu perfil não pode baixar relatórios desta carteira.")
            report_query = (
                NfseDocument.objects.filter(organization=office, company__in=scope)
                .select_related("company", "review_case", "side")
                .prefetch_related("integration_artifacts")
            )
            try:
                report_documents = _filter_nfse_retention_report_documents(
                    report_query, request.POST, demo=office.is_demo
                )
            except ValueError as exc:
                messages.error(request, str(exc))
                return redirect(request.get_full_path())
            if not report_documents:
                messages.error(request, "Nenhuma NFS-e corresponde ao recorte do relatório.")
                return redirect(request.get_full_path())
            if action == "download_original_xmls":
                archive = io.BytesIO()
                with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
                    for document in report_documents:
                        direction = _nfse_document_direction(document, demo=office.is_demo)
                        folder = nfse_company_archive_folder(
                            root={"provided": "Emitidas", "taken": "Tomadas"}.get(
                                direction, "Tipo-a-confirmar"
                            ),
                            dominio_code=document.company.dominio_code,
                        )
                        bundle.writestr(
                            f"{folder}/NFS-e-{document.id}.xml",
                            document.original_xml.encode("utf-8"),
                        )
                response = HttpResponse(archive.getvalue(), content_type="application/zip")
                response["Content-Disposition"] = 'attachment; filename="nfse-xmls-originais.zip"'
                response["Cache-Control"] = "private, no-store"
                response["X-Content-Type-Options"] = "nosniff"
                record_event(
                    action="hub.nfse.original_xmls_downloaded",
                    actor=cast(User, request.user), organization=office, target=office,
                    request=request, metadata={"document_count": len(report_documents)},
                )
                return response
            report_rows = build_retention_report_rows(report_documents, demo=office.is_demo)
            report_format = "pdf" if action == "retention_report_pdf" else "xlsx"
            report_bytes = (
                generate_retention_pdf(report_rows, demo=office.is_demo)
                if report_format == "pdf"
                else generate_retention_xlsx(report_rows, demo=office.is_demo)
            )
            generated_on = timezone.localdate().isoformat()
            response = HttpResponse(
                report_bytes,
                content_type=(
                    "application/pdf"
                    if report_format == "pdf"
                    else "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
            )
            response["Content-Disposition"] = (
                f'attachment; filename="retencoes-nfse-{generated_on}.{report_format}"'
            )
            response["Cache-Control"] = "private, no-store"
            response["X-Content-Type-Options"] = "nosniff"
            record_event(
                action=f"hub.nfse.retention_report_{report_format}_downloaded",
                actor=cast(User, request.user),
                organization=office,
                target=office,
                request=request,
                metadata={
                    "document_count": len(report_documents),
                    "demo": office.is_demo,
                    "direction": str(request.POST.get("report_direction", "all")),
                },
            )
            return response
        if action in {"demo_download_issued", "demo_download_taken", "demo_download_selected"}:
            if not can_demo_download_nfse:
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
            folder = (
                "Tomadas"
                if action == "demo_download_taken"
                else "Emitidas"
                if action == "demo_download_issued"
                else ""
            )
            return _demo_nfse_bulk_download(
                selected_documents,
                folder=folder,
                classifications=_demo_nfse_download_classifications(request, selected_documents),
            )

        if action == "export_dominio_xml":
            if is_demo_visitor(request, office) or not can_export_nfse:
                return refuse(request, "Seu perfil não pode gerar o pacote NFS-e desta carteira.")
            selected_query = (
                NfseDocument.objects.filter(
                    organization=office, company__in=scope, integration_artifacts__isnull=False
                )
                .select_related("company")
                .distinct()
            )
            try:
                if request.POST.get("all_filtered_classified") == "1":
                    selected_documents = list(
                        _filter_nfse_export_documents(selected_query, request.POST).order_by(
                            "company__name", "-issued_at", "-captured_at"
                        )
                    )
                else:
                    document_ids = list(
                        dict.fromkeys(
                            str(uuid.UUID(value)) for value in request.POST.getlist("documents")
                        )
                    )
                    selected_documents = list(selected_query.filter(id__in=document_ids))
                    if len(selected_documents) != len(document_ids):
                        raise ValueError("Seleção desatualizada. Selecione as notas novamente.")
            except (ValueError, ValidationError):
                messages.error(
                    request,
                    "Não foi possível preparar o lote. Confira o período "
                    "e selecione novamente as notas disponíveis.",
                )
                return redirect(request.get_full_path())
            if not selected_documents:
                messages.error(request, "Selecione ao menos uma NFS-e classificada para exportar.")
                return redirect(reverse("hub:nfse-center"))
            try:
                export = create_nfse_export(
                    organization=office,
                    documents=selected_documents,
                    actor=cast(User, request.user),
                )
            except ValueError as exc:
                messages.error(request, str(exc))
            else:
                record_event(
                    action="hub.nfse.export_created",
                    actor=request.user,
                    organization=office,
                    target=export,
                    request=request,
                    metadata={
                        "document_count": export.document_count,
                        "hash": export.content_hash[:12],
                    },
                )
                messages.success(
                    request,
                    (
                        f"Pacote gerado com {export.document_count} NFS-e "
                        f"e hash {export.content_hash[:12]}."
                    ),
                )
                return download_nfse_export(request, str(export.id))
            return redirect(request.get_full_path())

        if action == "add_accumulator_rule":
            if is_demo_visitor(request, office) or not can_export_nfse:
                return refuse(request, "Seu perfil não pode cadastrar acumuladores nesta carteira.")
            company_id = request.POST.get("company_id")
            company = (
                scope.filter(id=company_id).filter(active=True).first() if company_id else None
            )
            accumulator = request.POST.get("accumulator_code", "").strip()
            name = request.POST.get("name", "").strip()
            if company is None or not accumulator or len(accumulator) > 80 or len(name) > 160:
                messages.error(
                    request, "Informe a empresa e um acumulador válido de até 80 caracteres."
                )
            elif AccumulatorRule.objects.filter(
                organization=office, company=company, accumulator_code=accumulator, active=True
            ).exists():
                messages.info(request, "Esse acumulador já está ativo para a empresa selecionada.")
            else:
                rule = AccumulatorRule.objects.create(
                    organization=office,
                    company=company,
                    name=name or f"Acumulador incluído em {timezone.localdate():%d/%m/%Y}",
                    accumulator_code=accumulator,
                    priority=100,
                    match={},
                )
                AccumulatorHistoryEntry.objects.create(
                    organization=office,
                    company=company,
                    accumulator_code=accumulator,
                    name=rule.name,
                    source=AccumulatorHistoryEntry.Source.MANUAL,
                    source_reference=str(rule.id),
                    occurred_at=timezone.now(),
                    created_by=cast(User, request.user),
                    metadata={"rule_id": str(rule.id)},
                )
                record_event(
                    action="hub.nfse.accumulator_rule_created",
                    actor=request.user,
                    organization=office,
                    target=rule,
                    request=request,
                    metadata={"company_id": str(company.id), "has_accumulator": True},
                )
                messages.success(
                    request,
                    "Acumulador incluído. Ele já pode ser escolhido nas próximas "
                    "classificações, mas não classifica notas automaticamente.",
                )
            return redirect(reverse("hub:nfse-center") + "?view=catalog")

        if not can_manage_sync:
            return refuse(request, "Somente dono ou administrador configura a coleta NFS-e.")
        target_ids = list(dict.fromkeys(request.POST.getlist("companies")))[:100]
        selected_companies = list(scope.filter(id__in=target_ids, active=True))
        if not selected_companies:
            messages.error(request, "Selecione ao menos uma empresa da sua carteira.")
            return redirect(
                reverse("hub:nfse-center")
                + (
                    "?view=collection&configure=1#nfse-sync-settings"
                    if request.GET.get("view") == "collection"
                    else ""
                )
            )
        if action not in {"activate", "pause", "retry"}:
            return HttpResponseBadRequest("Ação de sincronização inválida.")
        if is_demo_visitor(request, office):
            valid_certificate_company_ids = set(
                Certificate.objects.filter(
                    organization=office,
                    company__in=selected_companies,
                    revoked_at__isnull=True,
                    valid_until__gt=timezone.now(),
                ).values_list("company_id", flat=True)
            )
            changed = 0
            blocked = 0
            for company in selected_companies:
                if action != "pause" and company.id not in valid_certificate_company_ids:
                    blocked += 1
                    continue
                put_progress(
                    request,
                    "nfse_syncs",
                    company.id,
                    {"status": "paused" if action == "pause" else "idle"},
                )
                changed += 1
            if changed:
                messages.success(
                    request,
                    f"Cenário fictício atualizado para {changed} empresa"
                    f"{'s' if changed != 1 else ''} nesta sessão. Nenhum certificado ou ADN "
                    "foi acionado.",
                )
            if blocked:
                messages.warning(
                    request,
                    f"{blocked} empresa{'s' if blocked != 1 else ''} precisa"
                    f"{'m' if blocked != 1 else ''} de A1 válido antes de ativar a coleta.",
                )
            return redirect(
                reverse("hub:nfse-center")
                + (
                    "?view=collection&configure=1#nfse-sync-settings"
                    if request.GET.get("view") == "collection"
                    else ""
                )
            )

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
                from apps.hub.tasks import dispatch_active_nfse_syncs

                transaction.on_commit(dispatch_active_nfse_syncs.delay)
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
            messages.warning(
                request,
                f"{blocked} empresa{'s' if blocked != 1 else ''} ignorada"
                f"{'s' if blocked != 1 else ''} por não ter e-CNPJ válido. "
                "As empresas com certificado válido continuam normalmente.",
            )
        return redirect(
            reverse("hub:nfse-center")
            + (
                "?view=collection&configure=1#nfse-sync-settings"
                if request.GET.get("view") == "collection"
                else ""
            )
        )

    document_query = (
        NfseDocument.objects.filter(organization=office, company__in=scope)
        .select_related("review_case", "company")
        .prefetch_related(
            Prefetch(
                "integration_artifacts",
                queryset=IntegrationArtifact.objects.order_by("-created_at"),
            )
        )
    )
    document_search = request.GET.get("q", "").strip()[:100]
    document_status = request.GET.get("status", "all")
    document_direction = request.GET.get("direction", "all")
    document_date_filter = request.GET.get("date_filter", "competence")
    document_competence = request.GET.get("competence", "").strip()[:7]
    if not request.GET:
        current_month = timezone.localdate().replace(day=1)
        previous_month = current_month - timedelta(days=1)
        document_competence = previous_month.strftime("%Y-%m")
    if "competence_month" in request.GET:
        month = request.GET.get("competence_month", "")
        year = request.GET.get("competence_year", "")
        document_competence = f"{year}-{month}" if month and year else ""
    issued_from = request.GET.get("issued_from", "").strip()[:10]
    issued_to = request.GET.get("issued_to", "").strip()[:10]
    if document_status in {"review", "received"}:
        document_status = "unclassified"
    if document_status not in {"all", "classified", "unclassified"}:
        document_status = "all"
    if document_direction not in {"all", "provided", "taken", "unknown"}:
        document_direction = "all"
    if document_date_filter not in {"competence", "issued"}:
        document_date_filter = "competence"
    scoped_documents = document_query
    if document_search:
        scoped_documents = scoped_documents.filter(
            Q(company__name__icontains=document_search)
            | Q(company__dominio_code__icontains=document_search)
            | Q(normalized_data__number__icontains=document_search)
        )
    if document_date_filter == "competence" and re.fullmatch(
        r"\d{4}-(0[1-9]|1[0-2])", document_competence
    ):
        competence_year, competence_month = document_competence.split("-")
        if not office.is_demo:
            scoped_documents = scoped_documents.filter(
                issued_at__year=int(competence_year), issued_at__month=int(competence_month)
            )
    elif document_date_filter == "competence":
        document_competence = ""
    date_filter_error = ""

    def parse_filter_date(value: str) -> date | None:
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
        scoped_documents = scoped_documents.none()
    if not office.is_demo and document_date_filter == "issued" and issued_from_date:
        scoped_documents = scoped_documents.filter(issued_at__date__gte=issued_from_date)
    if not office.is_demo and document_date_filter == "issued" and issued_to_date:
        scoped_documents = scoped_documents.filter(issued_at__date__lte=issued_to_date)
    scoped_documents = scoped_documents.distinct()

    def filter_nfse_status(
        query: QuerySet[NfseDocument], status: str
    ) -> QuerySet[NfseDocument]:
        if status == "classified":
            return query.filter(integration_artifacts__isnull=False).distinct()
        if status == "unclassified":
            return query.filter(integration_artifacts__isnull=True).distinct()
        return query

    def filter_nfse_direction(
        query: QuerySet[NfseDocument], direction: str
    ) -> QuerySet[NfseDocument]:
        return _filter_nfse_side(query, direction)

    documents = filter_nfse_direction(
        filter_nfse_status(scoped_documents, document_status), document_direction
    ).distinct()
    document_total = documents.count()
    exportable_documents = documents.filter(integration_artifacts__isnull=False).distinct()
    document_exportable_total = exportable_documents.count()
    document_exportable_company_total = exportable_documents.values("company_id").distinct().count()
    ordered_documents: QuerySet[NfseDocument] | list[NfseDocument] = documents.select_related(
        "side"
    ).order_by("company__name", "-issued_at", "-captured_at")
    demo_accumulators: dict[object, str] = {}
    direction_stats: dict[str, int]
    pending_stat: int
    classified_stat: int
    if office.is_demo:
        # Old demo fixtures keep their emission date in the normalized XML data.
        # Filter against the same date shown in the table, before applying facets or limiting rows.
        demo_scope: list[tuple[NfseDocument, bool, str, str]] = []
        for document in scoped_documents.order_by("company__name", "-issued_at", "-captured_at"):
            artifact = _latest_nfse_artifact(list(document.integration_artifacts.all()))
            review = getattr(document, "review_case", None)
            if review is not None:
                _demo_review_for_view(request, review)
            demo_accumulator = (
                review.resolved_accumulator
                if review is not None and review.status == ReviewCase.Status.RESOLVED
                else ""
            )
            classified = bool((artifact and artifact.accumulator_code) or demo_accumulator)
            effective_direction = _nfse_document_direction(document, demo=True)
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
            demo_scope.append(
                (document, classified, effective_direction, demo_accumulator or "")
            )
            if demo_accumulator:
                demo_accumulators[document.pk] = demo_accumulator

        def demo_status_matches(classified: bool, status: str) -> bool:
            return (
                status == "all"
                or (status == "classified" and classified)
                or (status == "unclassified" and not classified)
            )

        def demo_direction_matches(effective_direction: str, direction: str) -> bool:
            return direction == "all" or effective_direction == direction

        direction_stats = {
            direction: sum(
                demo_status_matches(classified, document_status)
                and effective_direction == direction
                for _document, classified, effective_direction, _accumulator in demo_scope
            )
            for direction in ("provided", "taken", "unknown")
        }
        status_scope = [
            item
            for item in demo_scope
            if demo_direction_matches(item[2], document_direction)
        ]
        pending_stat = sum(not item[1] for item in status_scope)
        classified_stat = sum(item[1] for item in status_scope)
        filtered_demo_scope = [
            item
            for item in status_scope
            if demo_status_matches(item[1], document_status)
        ]
        document_total = len(filtered_demo_scope)
        ordered_documents = [item[0] for item in filtered_demo_scope]
    else:
        direction_scope = filter_nfse_status(scoped_documents, document_status)
        direction_stats = {
            "provided": filter_nfse_direction(direction_scope, "provided").count(),
            "taken": filter_nfse_direction(direction_scope, "taken").count(),
            "unknown": filter_nfse_direction(direction_scope, "unknown").count(),
        }
        status_scope = filter_nfse_direction(scoped_documents, document_direction)
        pending_stat = filter_nfse_status(status_scope, "unclassified").count()
        classified_stat = filter_nfse_status(status_scope, "classified").count()

    def nfse_filter_url(*, status: str, direction: str) -> str:
        params: dict[str, object] = {
            "status": status,
            "direction": direction,
            "date_filter": document_date_filter,
        }
        if selected_company is not None:
            params["company"] = selected_company.id
        if document_search:
            params["q"] = document_search
        if document_date_filter == "competence" and document_competence:
            params["competence_month"] = document_competence[5:7]
            params["competence_year"] = document_competence[:4]
        elif document_date_filter == "issued":
            if issued_from:
                params["issued_from"] = issued_from
            if issued_to:
                params["issued_to"] = issued_to
        return f"{reverse('hub:nfse-center')}?{urlencode(params)}#nfse-results"

    nfse_stat_urls = {
        "received": nfse_filter_url(status=document_status, direction=document_direction),
        "provided": nfse_filter_url(status=document_status, direction="provided"),
        "taken": nfse_filter_url(status=document_status, direction="taken"),
        "pending": nfse_filter_url(status="unclassified", direction=document_direction),
    }
    # Status and movement are tabs over the list (Stripe-like): each count already ignores
    # its own facet, so a tab shows what selecting it would return.
    nfse_status_tabs = [
        {"value": value, "label": label, "count": count}
        for value, label, count in (
            ("all", "Todas", pending_stat + classified_stat),
            ("unclassified", "Para classificar", pending_stat),
            ("classified", "Classificadas", classified_stat),
        )
    ]
    for tab in nfse_status_tabs:
        tab["url"] = nfse_filter_url(status=str(tab["value"]), direction=document_direction)
        tab["selected"] = document_status == tab["value"]
    nfse_direction_tabs = [
        {"value": value, "label": label, "count": count}
        for value, label, count in (
            ("all", "Todas", sum(direction_stats.values())),
            ("provided", "Saídas", direction_stats["provided"]),
            ("taken", "Entradas", direction_stats["taken"]),
            ("unknown", "A confirmar", direction_stats["unknown"]),
        )
        if value != "unknown" or count or document_direction == "unknown"
    ]
    for tab in nfse_direction_tabs:
        tab["url"] = nfse_filter_url(status=document_status, direction=str(tab["value"]))
        tab["selected"] = document_direction == tab["value"]
    competence_cursor = timezone.localdate().replace(day=1)
    nfse_competence_options: list[tuple[str, str]] = []
    for _offset in range(18):
        nfse_competence_options.append(
            (competence_cursor.strftime("%Y-%m"), competence_cursor.strftime("%m/%Y"))
        )
        competence_cursor = add_months(competence_cursor, -1)
    if document_competence and document_competence not in dict(nfse_competence_options):
        nfse_competence_options.append(
            (document_competence, f"{document_competence[5:7]}/{document_competence[:4]}")
        )
    document_page = Paginator(ordered_documents, 100).get_page(request.GET.get("page"))
    document_query_params = request.GET.copy()
    document_query_params.pop("page", None)
    document_rows: list[dict[str, object]] = []
    accumulator_codes_cache: dict[tuple[object, date], list[tuple[str, str]]] = {}
    for document in document_page.object_list:
        artifact = _latest_nfse_artifact(list(document.integration_artifacts.all()))
        review = getattr(document, "review_case", None)
        open_review = review if review and review.status == ReviewCase.Status.OPEN else None
        issued_at = document.issued_at or _nfse_issued_at_from_normalized_data(document)
        # A note is classified or it is not: the accumulator either came from the catalogue
        # or nobody chose one yet. No percentage is shown, because none of them describes a
        # state an accountant can act on.
        demo_accumulator = demo_accumulators.get(document.pk, "")
        classified = bool((artifact and artifact.accumulator_code) or demo_accumulator)
        direction = _nfse_document_direction(document, demo=office.is_demo)
        direction_labels = {
            "provided": ("Saída", "Serviço prestado", "provided", "Tomador"),
            "taken": ("Entrada", "Serviço tomado", "taken", "Prestador"),
            "unknown": ("A confirmar", "Tipo não identificado", "unknown", "Contraparte"),
        }
        direction_label, direction_detail, direction_class, counterparty_role = direction_labels[
            direction
        ]
        normalized_data = (
            document.normalized_data if isinstance(document.normalized_data, dict) else {}
        )
        side = _nfse_side(document)
        counterparty_name = str(
            normalized_data.get("counterparty_name") or (side.counterparty_name if side else "")
        ).strip()[:160]
        if office.is_demo and not counterparty_name:
            counterparty_name = (
                "Cliente fictício"
                if direction == "provided"
                else "Fornecedor fictício"
                if direction == "taken"
                else "Não identificada"
            )
        competence = _nfse_review_text(normalized_data.get("competence"), limit=40)
        if not competence and issued_at:
            competence = issued_at.strftime("%m/%Y")
        elif re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", competence):
            competence = f"{competence[5:7]}/{competence[:4]}"
        retention_items, retained_total = _nfse_retention_summary(normalized_data)
        accumulator_options: list[tuple[str, str]] = []
        if can_classify_nfse and (open_review or classified):
            document_day = document.issued_at.date() if document.issued_at else timezone.localdate()
            cache_key = (document.company_id, document_day)
            if cache_key not in accumulator_codes_cache:
                accumulator_codes_cache[cache_key] = _review_accumulator_options(document)
            accumulator_options = accumulator_codes_cache[cache_key]
        accumulator_codes = [code for code, _name in accumulator_options]
        document_rows.append(
            {
                "document": document,
                "number": _nfse_document_number(document),
                "issued_at": issued_at,
                "competence": competence or "—",
                "direction": direction,
                "direction_label": direction_label,
                "direction_detail": direction_detail,
                "direction_class": direction_class,
                "counterparty_role": counterparty_role,
                "counterparty_name": counterparty_name or "Não identificada",
                "service_code": str(normalized_data.get("service_code") or "").strip()[:80],
                "service_description": str(
                    normalized_data.get("service_description") or ""
                ).strip()[:240],
                "amount": _nfse_review_amount(normalized_data.get("amount")),
                "retention_items": retention_items,
                "retained_total": retained_total,
                "review": open_review,
                "status": "Não classificada",
                "status_class": "attention" if open_review else "muted",
                "accumulator": (artifact.accumulator_code if artifact else demo_accumulator or "—"),
                "classified": classified,
                "artifact": artifact,
                "accumulator_codes": accumulator_codes,
                "accumulator_options": accumulator_options,
                "review_evidence": _nfse_review_evidence(document) if open_review else [],
            }
        )
    document_groups: list[dict[str, object]] = []
    for row in document_rows:
        document = cast(NfseDocument, row["document"])
        if not document_groups or document_groups[-1]["company_id"] != document.company_id:
            document_groups.append(
                {
                    "company": document.company,
                    "company_id": document.company_id,
                    "rows": [],
                    "classified_count": 0,
                    "pending_count": 0,
                }
            )
        group = document_groups[-1]
        cast(list[dict[str, object]], group["rows"]).append(row)
        if row["classified"]:
            group["classified_count"] = cast(int, group["classified_count"]) + 1
        if row["review"] and not row["classified"]:
            group["pending_count"] = cast(int, group["pending_count"]) + 1

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
        if sync is not None and not sync.enabled and not demo_state:
            effective_status = NfseSync.Status.PAUSED
        display_status = effective_status if certificate is not None else "blocked"
        display_enabled = bool(
            certificate is not None
            and (
                effective_status != NfseSync.Status.PAUSED if demo_state else sync and sync.enabled
            )
        )
        sync_rows.append(
            {
                "company": company,
                "certificate": certificate,
                "sync": sync,
                "status": display_status,
                "enabled": display_enabled,
                "status_label": (
                    "Certificado necessário"
                    if certificate is None
                    else dict(NfseSync.Status.choices).get(effective_status, "Não configurada")
                ),
                "attention": certificate is not None
                and effective_status in {NfseSync.Status.ERROR, NfseSync.Status.RETRY},
            }
        )
        if len(sync_rows) >= 100:
            break

    catalog_search = request.GET.get("catalog_q", "").strip()[:100]
    catalog_source = request.GET.get("catalog_source", "all")
    valid_catalog_sources = {value for value, _label in AccumulatorHistoryEntry.Source.choices}
    if catalog_source not in {*valid_catalog_sources, "all"}:
        catalog_source = "all"
    history_query = AccumulatorHistoryEntry.objects.filter(
        organization=office, company__in=scope
    ).select_related("company", "created_by")
    catalog_snapshot_query = AccumulatorCatalogEntry.objects.filter(
        organization=office, company__in=scope
    ).select_related("company", "data_source", "source_batch")
    legacy_rule_query = AccumulatorRule.objects.filter(
        organization=office, company__in=scope, active=True
    ).select_related("company")
    if catalog_search:
        history_query = history_query.filter(
            Q(company__name__icontains=catalog_search)
            | Q(company__dominio_code__icontains=catalog_search)
            | Q(accumulator_code__icontains=catalog_search)
            | Q(name__icontains=catalog_search)
        )
        catalog_snapshot_query = catalog_snapshot_query.filter(
            Q(company__name__icontains=catalog_search)
            | Q(company__dominio_code__icontains=catalog_search)
            | Q(accumulator_code__icontains=catalog_search)
            | Q(name__icontains=catalog_search)
        )
        legacy_rule_query = legacy_rule_query.filter(
            Q(company__name__icontains=catalog_search)
            | Q(company__dominio_code__icontains=catalog_search)
            | Q(accumulator_code__icontains=catalog_search)
            | Q(name__icontains=catalog_search)
        )
    if catalog_source != "all":
        history_query = history_query.filter(source=catalog_source)
        if catalog_source != AccumulatorHistoryEntry.Source.BACKUP:
            catalog_snapshot_query = catalog_snapshot_query.none()

    history_count = history_query.count()
    catalog_snapshot_count = catalog_snapshot_query.count()
    # Imports create history and catalog together. The snapshot fallback keeps old databases
    # readable without rebuilding both complete datasets in Python on every request.
    catalog_uses_snapshot_fallback = (
        history_count == 0
        and catalog_snapshot_count > 0
        and catalog_source
        in {
            "all",
            AccumulatorHistoryEntry.Source.BACKUP,
        }
    )
    catalog_uses_rule_fallback = (
        history_count == 0
        and catalog_snapshot_count == 0
        and catalog_source
        in {
            "all",
            AccumulatorHistoryEntry.Source.MANUAL,
        }
    )
    source_labels = {
        AccumulatorHistoryEntry.Source.BACKUP: "Fotografia do Domínio Web",
        AccumulatorHistoryEntry.Source.MANUAL: "Cadastro manual",
        AccumulatorHistoryEntry.Source.HUMAN_REVIEW: "Decisão humana",
    }
    catalog_source_options = [
        ("all", "Todas as origens"),
        (AccumulatorHistoryEntry.Source.BACKUP, "Fotografia do Domínio Web"),
        (AccumulatorHistoryEntry.Source.MANUAL, "Cadastro manual"),
        (AccumulatorHistoryEntry.Source.HUMAN_REVIEW, "Decisão humana"),
    ]
    raw_catalog_page: Any
    if catalog_uses_snapshot_fallback:
        raw_catalog_page = Paginator(
            catalog_snapshot_query.order_by(
                "-source_snapshot_at", "company__name", "accumulator_code"
            ),
            50,
        ).get_page(request.GET.get("catalog_page"))
        history_rows = [
            {
                "company": entry.company,
                "accumulator_code": entry.accumulator_code,
                "name": entry.name,
                "occurred_at": entry.source_snapshot_at,
                "source_label": "Fotografia do Domínio Web",
                "state_label": "Disponível" if entry.active else "Inativo na fotografia",
                "state_class": "success" if entry.active else "muted",
                "detail": entry.source_batch.original_filename,
            }
            for entry in raw_catalog_page.object_list
        ]
    elif catalog_uses_rule_fallback:
        raw_catalog_page = Paginator(
            legacy_rule_query.order_by("company__name", "priority", "accumulator_code"), 50
        ).get_page(request.GET.get("catalog_page"))
        history_rows = [
            {
                "company": entry.company,
                "accumulator_code": entry.accumulator_code,
                "name": entry.name,
                "occurred_at": entry.created_at,
                "source_label": "Cadastro existente",
                "state_label": "Disponível para classificar",
                "state_class": "success",
                "detail": "Regra cadastrada antes da trilha auditável",
            }
            for entry in raw_catalog_page.object_list
        ]
    else:
        raw_catalog_page = Paginator(
            history_query.order_by("-occurred_at", "-created_at"), 50
        ).get_page(request.GET.get("catalog_page"))
        history_rows = [
            {
                "company": entry.company,
                "accumulator_code": entry.accumulator_code,
                "name": entry.name,
                "occurred_at": entry.occurred_at,
                "source_label": source_labels[entry.source],
                "state_label": "Disponível para classificar",
                "state_class": "success",
                "detail": (
                    entry.metadata.get("source_batch_id", "")
                    if isinstance(entry.metadata, dict)
                    else ""
                ),
            }
            for entry in raw_catalog_page.object_list
        ]
    raw_catalog_page.object_list = history_rows
    catalog_page = raw_catalog_page
    unfiltered_history = AccumulatorHistoryEntry.objects.filter(
        organization=office, company__in=scope
    )
    history_total = unfiltered_history.count()
    snapshot_total = AccumulatorCatalogEntry.objects.filter(
        organization=office, company__in=scope
    ).count()
    legacy_rule_total = AccumulatorRule.objects.filter(
        organization=office, company__in=scope, active=True
    ).count()
    catalog_stats = {
        "total": history_total or snapshot_total or legacy_rule_total,
        "backup": (
            unfiltered_history.filter(source=AccumulatorHistoryEntry.Source.BACKUP).count()
            if history_total
            else snapshot_total
        ),
        "manual": (
            unfiltered_history.filter(source=AccumulatorHistoryEntry.Source.MANUAL).count()
            if history_total
            else legacy_rule_total
            if not snapshot_total
            else 0
        ),
        "human": unfiltered_history.filter(
            source=AccumulatorHistoryEntry.Source.HUMAN_REVIEW
        ).count(),
    }
    catalog_query_params = request.GET.copy()
    catalog_query_params.pop("catalog_page", None)
    requested_nfse_view = request.GET.get("view")
    nfse_view = (
        requested_nfse_view
        if requested_nfse_view in {"collection", "catalog", "exports"}
        else "notes"
    )
    export_search = request.GET.get("export_q", "").strip()[:100]
    export_state = request.GET.get("export_state", "all")
    if export_state not in {"all", NfseExport.State.READY, NfseExport.State.DOWNLOADED}:
        export_state = "all"
    visible_exports = _visible_nfse_exports(context)
    export_stats = {
        "total": visible_exports.count(),
        "ready": visible_exports.filter(state=NfseExport.State.READY).count(),
        "downloaded": visible_exports.filter(state=NfseExport.State.DOWNLOADED).count(),
    }
    export_query = visible_exports
    if export_search:
        matching_export_documents = NfseDocument.objects.filter(
            exports=OuterRef("pk"), organization=office
        ).filter(
            Q(company__name__icontains=export_search)
            | Q(company__dominio_code__icontains=export_search)
        )
        export_query = export_query.filter(
            Q(content_hash__icontains=export_search)
            | Q(created_by__full_name__icontains=export_search)
            | Q(created_by__email__icontains=export_search)
            | Exists(matching_export_documents)
        )
    if export_state != "all":
        export_query = export_query.filter(state=export_state)
    exports_page = Paginator(
        export_query.select_related("created_by", "downloaded_by")
        .annotate(
            company_count=Count("documents__company", distinct=True),
            issued_from=Min("documents__issued_at"),
            issued_to=Max("documents__issued_at"),
        )
        .defer("snapshot")
        .order_by("-created_at", "-id"),
        50,
    ).get_page(request.GET.get("exports_page"))
    exports_query_params = request.GET.copy()
    exports_query_params.pop("exports_page", None)

    effective_sync_configured = sum(bool(row["enabled"]) for row in sync_rows)
    effective_sync_attention = sum(bool(row["attention"]) for row in sync_rows)
    missing_certificate_count = sum(row["certificate"] is None for row in sync_rows)
    ready_to_activate_count = sum(
        row["certificate"] is not None and not row["enabled"] and not row["status"]
        for row in sync_rows
    )
    context.update(
        {
            "page_title": "NFS-e",
            "nfse_view": nfse_view,
            "document_rows": document_rows,
            "document_page": document_page,
            "document_querystring": document_query_params.urlencode(),
            "document_filtered_total": document_total,
            "retention_report_too_large": document_total > 5000,
            "document_exportable_total": document_exportable_total,
            "document_exportable_company_total": document_exportable_company_total,
            "document_search": document_search,
            "nfse_selected_company": selected_company,
            "document_status": document_status,
            "document_direction": document_direction,
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
                "received": document_total,
                **direction_stats,
                "pending": pending_stat,
                "classified": classified_stat,
            },
            "nfse_stat_urls": nfse_stat_urls,
            "nfse_status_tabs": nfse_status_tabs,
            "nfse_direction_tabs": nfse_direction_tabs,
            "nfse_competence_options": nfse_competence_options,
            "nfse_sync_rows": sync_rows,
            "nfse_exports": exports_page,
            "exports_querystring": exports_query_params.urlencode(),
            "export_search": export_search,
            "export_state": export_state,
            "nfse_export_stats": export_stats,
            "can_export_nfse": can_export_nfse,
            "can_classify_nfse": can_classify_nfse,
            "can_demo_download_nfse": can_demo_download_nfse,
            "can_download_nfse": can_download_nfse,
            "document_groups": document_groups,
            "accumulator_catalog_page": catalog_page,
            "accumulator_catalog_querystring": catalog_query_params.urlencode(),
            "accumulator_catalog_search": catalog_search,
            "accumulator_catalog_source": catalog_source,
            "accumulator_catalog_sources": catalog_source_options,
            "accumulator_catalog_stats": catalog_stats,
            "catalog_companies": scope.filter(active=True).order_by("name"),
            "can_add_nfse_accumulator": can_export_nfse and not office.is_demo,
            "nfse_sync_enabled": settings.NFSE_ADN_SYNC_ENABLED or office.is_demo,
            "nfse_sync_environment": settings.NFSE_ADN_ENVIRONMENT,
            "nfse_sync_environment_label": (
                "Produção"
                if settings.NFSE_ADN_ENVIRONMENT == "production"
                else "Produção restrita (homologação)"
            ),
            "nfse_sync_configured": effective_sync_configured,
            "nfse_sync_attention": effective_sync_attention,
            "nfse_sync_missing_certificate": missing_certificate_count,
            "nfse_sync_ready_to_activate": ready_to_activate_count,
            "nfse_sync_requires_action": (
                effective_sync_attention + missing_certificate_count + ready_to_activate_count
            ),
            "nfse_sync_settings_open": request.GET.get("configure") == "1",
            "nfse_certificate_coverage": len(certificates_by_company),
            "can_manage_nfse_sync": can_manage_sync,
        }
    )
    return render(request, "hub/nfse_center.html", context)


@office_required
@require_http_methods(["GET"])
def nfse_queue_status(request: HttpRequest) -> JsonResponse:
    """Return a tenant-scoped, non-sensitive snapshot for the live collection queue."""

    context = workspace_context(request)
    if not collaborator_can_use_module(context, ProductModule.Code.NFSE):
        return JsonResponse({"detail": "Acesso negado."}, status=403)
    office = cast(Organization, context["office"])
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    now = timezone.now()
    companies = list(scope.filter(active=True).order_by("name"))
    company_ids = [company.id for company in companies]
    valid_certificate_company_ids = set(
        Certificate.objects.filter(
            organization=office,
            company_id__in=company_ids,
            revoked_at__isnull=True,
            valid_until__gt=now,
        ).values_list("company_id", flat=True)
    )
    sync_by_company = {
        sync.company_id: sync
        for sync in NfseSync.objects.filter(
            organization=office, company_id__in=company_ids
        ).select_related("company")
    }

    demo_syncs = get_section(request, "nfse_syncs") if is_demo_visitor(request, office) else {}
    items: list[dict[str, object]] = []
    counts = {
        "queued": 0,
        "running": 0,
        "done": 0,
        "attention": 0,
        "skipped": 0,
        "requires_action": 0,
    }
    priority = {
        "running": 0,
        "failed": 1,
        "retry": 2,
        "queued": 3,
        "blocked": 4,
        "ready": 5,
        "paused": 6,
        "done": 7,
    }
    for company in companies:
        sync = sync_by_company.get(company.id)
        demo_state = demo_syncs.get(str(company.id), {})
        effective_status = str(demo_state.get("status", "")) or (sync.status if sync else "")
        if sync is not None and not sync.enabled and not demo_state:
            effective_status = NfseSync.Status.PAUSED
        has_valid_certificate = company.id in valid_certificate_company_ids
        state = "queued"
        label = "Na fila"
        detail = "Primeira coleta aguardando processamento."
        changed_at = sync.updated_at if sync else None
        if not has_valid_certificate:
            state = "blocked"
            label = "Certificado necessário"
            detail = "Adicione um A1 válido para esta empresa começar a receber notas."
            counts["skipped"] += 1
            counts["requires_action"] += 1
        elif sync is None:
            if effective_status == NfseSync.Status.PAUSED:
                state = "paused"
                label = "Pausada"
                detail = "A coleta está pausada somente para esta empresa."
                counts["skipped"] += 1
            elif effective_status in {NfseSync.Status.IDLE, NfseSync.Status.QUEUED}:
                state = "queued"
                label = "Na fila"
                detail = "Aguardando a empresa anterior terminar."
                counts["queued"] += 1
            else:
                state = "ready"
                label = "Pronta para ativar"
                detail = "O certificado está válido; ative a coleta na configuração."
                counts["requires_action"] += 1
        elif effective_status == NfseSync.Status.RUNNING:
            state = "running"
            label = "Coletando agora"
            detail = (
                f"NSU {sync.checkpoint_nsu} de {sync.max_nsu}."
                if sync.checkpoint_nsu and sync.max_nsu
                else "Consultando novas NFS-e desta empresa."
            )
            counts["running"] += 1
            changed_at = sync.last_run_at or sync.updated_at
        elif effective_status in {NfseSync.Status.IDLE, NfseSync.Status.QUEUED}:
            state = "queued"
            label = "Na fila"
            detail = "Aguardando a empresa anterior terminar."
            counts["queued"] += 1
        elif effective_status == NfseSync.Status.RETRY:
            state = "retry"
            label = "Nova tentativa"
            detail = "Falha temporária; nova tentativa já agendada."
            counts["attention"] += 1
            counts["requires_action"] += 1
            changed_at = sync.last_error_at or sync.updated_at
        elif effective_status == NfseSync.Status.ERROR:
            state = "failed"
            label = "Falhou"
            detail = sync.last_error_message or "Revise a configuração desta empresa."
            counts["attention"] += 1
            counts["requires_action"] += 1
            changed_at = sync.last_error_at or sync.updated_at
        elif effective_status == NfseSync.Status.PAUSED or not sync.enabled:
            state = "paused"
            label = "Pausada"
            detail = "Coleta pausada somente para esta empresa."
            counts["skipped"] += 1
        elif sync.last_success_at:
            state = "done"
            label = "Concluída"
            detail = (
                f"Atualizada até o NSU {sync.checkpoint_nsu} de {sync.max_nsu}."
                if sync.checkpoint_nsu and sync.max_nsu
                else (
                    f"{sync.last_batch_count} documento"
                    f"{'s' if sync.last_batch_count != 1 else ''} na última coleta."
                )
            )
            counts["done"] += 1
            changed_at = sync.last_success_at
        else:
            counts["queued"] += 1

        items.append(
            {
                "company_id": str(company.id),
                "company": company.name,
                "state": state,
                "label": label,
                "detail": detail,
                "updated_at": changed_at.isoformat() if changed_at else None,
                "priority": priority[state],
            }
        )

    items.sort(key=lambda item: (cast(int, item["priority"]), cast(str, item["company"])))
    for item in items:
        item.pop("priority", None)
    response = JsonResponse(
        {
            "counts": counts,
            "items": items,
            "updated_at": now.isoformat(),
            "simulated": office.is_demo,
        }
    )
    response["Cache-Control"] = "private, no-store"
    return response


@office_required
@require_http_methods(["POST"])
def nfse_queue_retry(request: HttpRequest) -> JsonResponse:
    """Retry failed company feeds without reloading or restarting successful work."""

    context = workspace_context(request)
    if not collaborator_can_use_module(context, ProductModule.Code.NFSE):
        return JsonResponse({"detail": "Acesso negado."}, status=403)
    office = cast(Organization, context["office"])
    membership = context.get("membership")
    demo_visitor = is_demo_visitor(request, office)
    can_manage = bool(
        demo_visitor
        or (
            context["support_can_mutate"]
            and isinstance(membership, Membership)
            and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
        )
    )
    if not can_manage:
        return JsonResponse(
            {"detail": "Somente dono ou administrador pode repetir coletas."}, status=403
        )
    scope = cast("QuerySet[ClientCompany]", context["companies"]).filter(active=True)
    company_id = request.POST.get("company_id", "").strip()
    if company_id:
        try:
            company_uuid = uuid.UUID(company_id)
        except ValueError:
            return JsonResponse({"detail": "Empresa inválida."}, status=400)
        scope = scope.filter(id=company_uuid)
    elif request.POST.get("all_failed") != "1":
        return JsonResponse(
            {"detail": "Informe a empresa ou escolha repetir as falhas."}, status=400
        )

    if demo_visitor:
        demo_syncs = get_section(request, "nfse_syncs")
        persisted_syncs = {
            sync.company_id: sync
            for sync in NfseSync.objects.filter(organization=office, company__in=scope)
        }
        valid_certificate_company_ids = set(
            Certificate.objects.filter(
                organization=office,
                company__in=scope,
                revoked_at__isnull=True,
                valid_until__gt=timezone.now(),
            ).values_list("company_id", flat=True)
        )
        changed = 0
        for company in scope:
            sync = persisted_syncs.get(company.id)
            demo_state = demo_syncs.get(str(company.id), {})
            effective_status = str(demo_state.get("status", "")) or (sync.status if sync else "")
            if company.id in valid_certificate_company_ids and effective_status in {
                NfseSync.Status.ERROR,
                NfseSync.Status.RETRY,
            }:
                put_progress(request, "nfse_syncs", company.id, {"status": "idle"})
                changed += 1
        return JsonResponse({"changed": changed})

    now = timezone.now()
    syncs = list(
        NfseSync.objects.filter(
            organization=office,
            company__in=scope,
            enabled=True,
            status__in=[NfseSync.Status.ERROR, NfseSync.Status.RETRY],
            certificate__revoked_at__isnull=True,
            certificate__valid_until__gt=now,
        ).values_list("id", flat=True)
    )
    if syncs:
        NfseSync.objects.filter(id__in=syncs).update(
            status=NfseSync.Status.RETRY,
            next_run_at=now,
            failure_count=0,
            last_error_code="",
            last_error_message="",
            last_error_at=None,
            lease_token=None,
            lease_until=None,
        )
        from apps.hub.tasks import dispatch_active_nfse_syncs

        transaction.on_commit(dispatch_active_nfse_syncs.delay)
    record_event(
        action="hub.nfse.queue_retry_requested",
        actor=request.user,
        organization=office,
        target=office,
        request=request,
        metadata={"changed": len(syncs), "company_id": company_id or None},
    )
    return JsonResponse({"changed": len(syncs)})


def _visible_nfse_exports(context: dict[str, object]) -> QuerySet[NfseExport]:
    office = cast(Organization, context["office"])
    return (
        NfseExport.objects.filter(organization=office, document_count__gt=0)
        .annotate(
            accessible_documents=Count(
                "documents",
                filter=Q(
                    documents__organization=office,
                    documents__company__in=_company_history_scope(context),
                ),
                distinct=True,
            ),
            linked_documents=Count("documents", distinct=True),
        )
        .filter(accessible_documents=F("document_count"), linked_documents=F("document_count"))
    )


def _nfse_export_context(
    request: HttpRequest, export_id: str
) -> tuple[dict[str, object], NfseExport, list[NfseDocument]]:
    context = workspace_context(request)
    if not collaborator_can_use_module(context, ProductModule.Code.NFSE):
        raise Http404
    office = context["office"]
    assert isinstance(office, Organization)
    export = get_object_or_404(_visible_nfse_exports(context), id=export_id)
    try:
        document_ids = [uuid.UUID(item["document_id"]) for item in export.snapshot["documents"]]
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise Http404 from exc
    if len(document_ids) != export.document_count or len(set(document_ids)) != len(document_ids):
        raise Http404
    scope = _company_history_scope(context)
    documents = list(
        NfseDocument.objects.filter(
            organization=office, company__in=scope, id__in=document_ids
        ).select_related("company")
    )
    if len(documents) != len(document_ids):
        raise Http404
    return context, export, documents


@office_required
@require_http_methods(["POST"])
def download_nfse_export(request: HttpRequest, export_id: str) -> HttpResponseBase:
    context, export, _documents = _nfse_export_context(request, export_id)
    office = cast(Organization, context["office"])
    content_name = export.content.name if export.content else ""
    try:
        if not content_name:
            raise FileNotFoundError
        archive = export.content.open("rb")
    except OSError:
        messages.error(
            request,
            "Não foi possível abrir este arquivo. Tente baixar novamente. "
            "Se o problema continuar, use Preparar novo download para gerar outro pacote.",
        )
        return redirect(reverse("hub:nfse-center") + "?view=exports")
    with transaction.atomic():
        export = NfseExport.objects.select_for_update().get(id=export.id)
        if export.state == NfseExport.State.READY:
            export.state = NfseExport.State.DOWNLOADED
            export.downloaded_at = timezone.now()
            export.downloaded_by = cast(User, request.user)
            export.save(update_fields=["state", "downloaded_at", "downloaded_by", "updated_at"])
            record_event(
                action="hub.nfse.export_downloaded",
                actor=request.user,
                organization=office,
                target=export,
                request=request,
                metadata={
                    "document_count": export.document_count,
                    "hash": export.content_hash[:12],
                },
            )
    response = FileResponse(
        archive,
        as_attachment=True,
        filename=PurePath(export.content.name or "pacote-nfse.zip").name,
        content_type="application/zip",
    )
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "no-store"
    return response


@office_required
@require_http_methods(["POST"])
def confirm_nfse_export_import(request: HttpRequest, export_id: str) -> HttpResponse:
    # Resolve the package first, so a caller never learns whether an out-of-scope ID exists.
    _nfse_export_context(request, export_id)
    return refuse(
        request,
        "A importacao esta bloqueada ate o layout e o retorno da rotina Dominio serem homologados.",
        kind="unavailable",
    )


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
        is_ai_classification = bool(artifact and artifact.accumulator_code == accumulator)
        if is_ai_classification:
            classifications[str(document.id)] = {
                "accumulator": accumulator,
                "status": "Classificada pela IA",
            }
        elif accumulator:
            classifications[str(document.id)] = {
                "accumulator": accumulator,
                "status": "Definida pelo contador",
            }
        else:
            classifications[str(document.id)] = {
                "accumulator": "Transitória",
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


_UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
)


def _nfse_document_number(document: NfseDocument) -> str:
    """Return the fiscal number an operator recognizes, never the transport NSU."""

    normalized = document.normalized_data if isinstance(document.normalized_data, dict) else {}
    value = normalized.get("number")
    return str(value).strip()[:80] if value not in (None, "") else ""


def _nfse_side(document: NfseDocument) -> NfseDocumentSide | None:
    try:
        return document.side
    except NfseDocumentSide.DoesNotExist:
        return None


def _filter_nfse_side(query: QuerySet[NfseDocument], direction: str) -> QuerySet[NfseDocument]:
    """Filter by the persisted side; notes without one fall back to their normalization."""

    sides = ["provided", "taken"]
    if direction in sides:
        return query.filter(
            Q(side__direction=direction)
            | Q(side__isnull=True, normalized_data__direction=direction)
        )
    if direction == "unknown":
        return query.exclude(
            Q(side__direction__in=sides)
            | Q(side__isnull=True, normalized_data__direction__in=sides)
        )
    return query


def _nfse_document_direction(document: NfseDocument, *, demo: bool = False) -> str:
    """Present only persisted fiscal direction; demo legacy rows get a stable synthetic split."""

    side = _nfse_side(document)
    if side is not None and side.direction in {"provided", "taken"}:
        return side.direction
    normalized = document.normalized_data if isinstance(document.normalized_data, dict) else {}
    direction = str(normalized.get("direction") or "")
    if direction in {"provided", "taken"}:
        return direction
    if demo:
        digits = re.sub(r"\D", "", document.source_nsu)
        if digits:
            return "provided" if int(digits[-1]) % 2 == 0 else "taken"
    return "unknown"


def _nfse_retention_summary(
    normalized_data: dict[str, object],
) -> tuple[list[tuple[str, str]], str]:
    """Format only explicit retained amounts without inventing tax calculations."""

    raw = normalized_data.get("retentions")
    if not isinstance(raw, dict):
        return [], ""
    labels = {
        "iss": "ISS",
        "pis": "PIS",
        "cofins": "COFINS",
        "csll": "CSLL",
        "irrf": "IRRF",
        "inss": "INSS",
    }
    items = [
        (label, formatted)
        for key, label in labels.items()
        if (formatted := _nfse_review_amount(raw.get(key)))
    ]
    total = _nfse_review_amount(normalized_data.get("retained_total"))
    return items, total


def _latest_nfse_artifact(
    artifacts: list[IntegrationArtifact],
) -> IntegrationArtifact | None:
    """Return the terminal immutable decision in a correction chain."""

    superseded_ids = {
        str(artifact.payload.get("previous_artifact_id"))
        for artifact in artifacts
        if isinstance(artifact.payload, dict) and artifact.payload.get("previous_artifact_id")
    }
    return next(
        (artifact for artifact in artifacts if str(artifact.id) not in superseded_ids),
        None,
    )


def _filter_nfse_export_documents(
    documents: QuerySet[NfseDocument], data: Any
) -> QuerySet[NfseDocument]:
    """Rebuild the visible production filter for a cross-page classified export."""

    query = str(data.get("export_q", "")).strip()[:100]
    if query:
        documents = documents.filter(
            Q(company__name__icontains=query)
            | Q(company__dominio_code__icontains=query)
            | Q(normalized_data__number__icontains=query)
        )
    direction = str(data.get("export_direction", "all"))
    if direction not in {"all", "provided", "taken", "unknown"}:
        raise ValueError("Tipo de movimento inválido.")
    documents = _filter_nfse_side(documents, direction)
    date_filter = str(data.get("export_date_filter", "competence"))
    competence = str(data.get("export_competence", ""))[:7]
    if date_filter not in {"competence", "issued"}:
        raise ValueError("Filtro de período inválido.")
    if (
        date_filter == "competence"
        and competence
        and not re.fullmatch(r"[1-9]\d{3}-(0[1-9]|1[0-2])", competence)
    ):
        raise ValueError("Competência inválida.")
    if date_filter == "competence" and re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", competence):
        year, month = competence.split("-")
        documents = documents.filter(issued_at__year=int(year), issued_at__month=int(month))
    elif date_filter == "issued":
        parsed_dates = []
        for field, lookup in (
            ("export_issued_from", "issued_at__date__gte"),
            ("export_issued_to", "issued_at__date__lte"),
        ):
            raw = str(data.get(field, ""))[:10]
            try:
                parsed = datetime.strptime(raw, "%d/%m/%Y").date() if raw else None
            except ValueError as exc:
                raise ValueError("Data inválida no filtro do lote.") from exc
            parsed_dates.append(parsed)
            if parsed is not None:
                documents = documents.filter(**{lookup: parsed})
        start, end = parsed_dates
        if start is not None and end is not None and start > end:
            raise ValueError("O período final deve ser posterior ao inicial.")
    return documents.distinct()


def _filter_nfse_retention_report_documents(
    documents: QuerySet[NfseDocument], data: Any, *, demo: bool
) -> list[NfseDocument]:
    """Apply the visible note filters without allowing a broader report scope."""

    query = str(data.get("report_q", "")).strip()[:100]
    if query:
        documents = documents.filter(
            Q(company__name__icontains=query)
            | Q(company__dominio_code__icontains=query)
            | Q(normalized_data__number__icontains=query)
        )
    status = str(data.get("report_status", "all"))
    direction = str(data.get("report_direction", "all"))
    date_filter = str(data.get("report_date_filter", "competence"))
    competence = str(data.get("report_competence", ""))[:7]
    if status not in {"all", "classified", "unclassified"}:
        raise ValueError("Situação inválida no filtro do relatório.")
    if direction not in {"all", "provided", "taken", "unknown"}:
        raise ValueError("Movimento inválido no filtro do relatório.")
    if date_filter not in {"competence", "issued"}:
        raise ValueError("Período inválido no filtro do relatório.")
    if competence and not re.fullmatch(r"[1-9]\d{3}-(0[1-9]|1[0-2])", competence):
        raise ValueError("Competência inválida no filtro do relatório.")
    parsed_dates: list[date | None] = []
    for field in ("report_issued_from", "report_issued_to"):
        raw = str(data.get(field, ""))[:10]
        try:
            parsed_dates.append(datetime.strptime(raw, "%d/%m/%Y").date() if raw else None)
        except ValueError as exc:
            raise ValueError("Data inválida no filtro do relatório.") from exc
    issued_from, issued_to = parsed_dates
    if issued_from and issued_to and issued_from > issued_to:
        raise ValueError("A data final do relatório deve ser igual ou posterior à inicial.")

    if not demo:
        if status == "classified":
            documents = documents.filter(integration_artifacts__isnull=False)
        elif status == "unclassified":
            documents = documents.filter(integration_artifacts__isnull=True)
        documents = _filter_nfse_side(documents, direction)
        if date_filter == "competence" and competence:
            year, month = competence.split("-")
            documents = documents.filter(issued_at__year=int(year), issued_at__month=int(month))
        elif date_filter == "issued":
            if issued_from:
                documents = documents.filter(issued_at__date__gte=issued_from)
            if issued_to:
                documents = documents.filter(issued_at__date__lte=issued_to)
        selected = list(
            documents.distinct().order_by("company__name", "-issued_at", "-captured_at")[:5001]
        )
    else:
        selected = []
        candidates = documents.distinct().order_by("company__name", "-issued_at", "-captured_at")
        for document in candidates:
            artifacts = list(document.integration_artifacts.all())
            review = getattr(document, "review_case", None)
            classified = bool(
                _latest_nfse_artifact(artifacts)
                or (review and review.status == ReviewCase.Status.RESOLVED)
            )
            if status == "classified" and not classified:
                continue
            if status == "unclassified" and classified:
                continue
            if direction != "all" and _nfse_document_direction(document, demo=True) != direction:
                continue
            issued_at = document.issued_at or _nfse_issued_at_from_normalized_data(document)
            issued_date = issued_at.date() if issued_at else None
            if date_filter == "competence" and competence:
                if not issued_date or issued_date.strftime("%Y-%m") != competence:
                    continue
            elif date_filter == "issued":
                if issued_from and (not issued_date or issued_date < issued_from):
                    continue
                if issued_to and (not issued_date or issued_date > issued_to):
                    continue
            selected.append(document)
            if len(selected) > 5000:
                break
    if len(selected) > 5000:
        raise ValueError(
            "O download aceita até 5.000 notas. Refine por empresa, movimento ou período."
        )
    return selected


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
                "Situação",
            ]
        )
        for document in documents:
            source = re.sub(r"[^A-Za-z0-9._-]", "_", document.source_nsu or str(document.id))
            classification = classifications[str(document.id)]
            document_folder = folder or (
                "Tomadas"
                if _nfse_document_direction(document, demo=True) == "taken"
                else "Emitidas"
            )
            company_folder = nfse_company_archive_folder(
                root=document_folder,
                dominio_code=document.company.dominio_code,
            )
            bundle.writestr(
                f"{company_folder}/NFS-e-{source}.xml",
                document.original_xml,
            )
            writer.writerow(
                [
                    document.source_nsu or str(document.id),
                    document.company.name,
                    document.company.dominio_code or "",
                    company_folder,
                    classification["accumulator"],
                    classification["status"],
                ]
            )
        bundle.writestr("manifesto-classificacao.csv", manifest.getvalue().encode("utf-8-sig"))
    archive.seek(0)
    response = FileResponse(
        archive,
        as_attachment=True,
        filename=f"nfse-demonstracao-{folder.casefold() if folder else 'separadas'}.zip",
        content_type="application/zip",
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


def _module_page_context(
    request: HttpRequest, module: ModuleDefinition
) -> tuple[dict[str, object], HttpResponse | None]:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    if module.code == ProductModule.Code.AI and not copilot_is_available() and not office.is_demo:
        return context, HttpResponse(status=404)
    if not collaborator_can_use_module(context, module.code):
        return context, refuse(request, f"Seu acesso n\u00e3o inclui {module.label}.")
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
    membership = context.get("membership")
    if module.code in {ProductModule.Code.GUIDES, ProductModule.Code.INTEGRA} and isinstance(
        membership, Membership
    ):
        context["companies"] = company_queryset_for_module(membership, module.code)
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

    if not guide.organization.is_demo or guide.status == FiscalGuide.Status.SKIPPED:
        # Retired demonstration guides (an earlier competência) stay out of the queue.
        return guide
    entry = get_progress(request, "guides", guide.id)
    guide.status = FiscalGuide.Status.ISSUED if entry.get("issued") else FiscalGuide.Status.READY
    guide.provider_request_id = str(entry.get("protocol", ""))
    issued_at = parse_datetime(str(entry.get("issued_at", "")))
    guide.issued_at = issued_at if entry.get("issued") else None
    guide.issue_requested_at = guide.issued_at
    guide.issue_requested_by = cast(User, request.user) if entry.get("issued") else None
    return guide


def _guide_state_guidance(status: str, error_code: str = "") -> str:
    """Return an operator-safe next step without reflecting provider exceptions."""

    if status == FiscalGuide.Status.READY:
        return "Confira o valor, o vencimento e o consumo antes de emitir."
    if status == FiscalGuide.Status.QUEUED:
        return "Emissão autorizada e aguardando processamento."
    if status == FiscalGuide.Status.ISSUING:
        return "O Serpro está processando a emissão. Atualize para acompanhar."
    if status == FiscalGuide.Status.ISSUED:
        return "DARF disponível para baixar sem gerar uma nova consulta."
    if status == FiscalGuide.Status.UNKNOWN:
        return "O provedor não confirmou o resultado. Aguarde a conciliação antes de repetir."
    if status == FiscalGuide.Status.SKIPPED:
        return (
            "A obrigação foi marcada como dispensada. "
            "Consulte o histórico antes de alterar a decisão."
        )
    if status == FiscalGuide.Status.DISCOVERED:
        return "Confira as provas da DCTFWeb antes de preparar a emissão."
    if error_code == "invalid_cnpj":
        return "Corrija o CNPJ da empresa e tente novamente. Nenhuma emissão foi concluída."
    if error_code == "authorization_revoked":
        return "O acesso operacional foi revogado. Revise a carteira antes de tentar novamente."
    if error_code == "usage_missing":
        return "A reserva de consumo não foi localizada. Revise o custo antes de tentar novamente."
    return "A emissão não foi concluída. Revise os dados e o custo antes de tentar novamente."


def _document_state_guidance(status: str, error_code: str = "") -> str:
    if status == DctfWebDocument.Status.AVAILABLE:
        return "Documento disponível para baixar sem gerar uma nova consulta."
    if status == DctfWebDocument.Status.QUEUED:
        return "Consulta autorizada e aguardando processamento."
    if status == DctfWebDocument.Status.FETCHING:
        return "Consulta em processamento. Atualize para acompanhar."
    if status == DctfWebDocument.Status.UNKNOWN:
        return "O provedor não confirmou o resultado. Não repita até a conciliação."
    if error_code == "authorization_revoked":
        return "O acesso operacional foi revogado. Revise a carteira antes de tentar novamente."
    if error_code == "invalid_cnpj":
        return "Corrija o CNPJ da empresa antes de tentar novamente."
    return "A consulta não foi concluída. Revise o acesso e o custo antes de tentar novamente."


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
    if guide_status not in {"all", "pending", "issued", "failed", "unknown"}:
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
    if office.is_demo:
        demo_guides = list(filtered_guides.order_by("due_on", "company__name"))
        for guide in demo_guides:
            _demo_guide_for_view(request, guide)
        if guide_status == "pending":
            demo_guides = [
                guide
                for guide in demo_guides
                if guide.status
                in [
                    FiscalGuide.Status.READY,
                    FiscalGuide.Status.FAILED,
                    FiscalGuide.Status.UNKNOWN,
                ]
            ]
        elif guide_status != "all":
            demo_guides = [guide for guide in demo_guides if guide.status == guide_status]
        guide_filtered_total = len(demo_guides)
        guide_items: QuerySet[FiscalGuide] | list[FiscalGuide] = demo_guides
    else:
        if guide_status == "pending":
            filtered_guides = filtered_guides.filter(
                status__in=[
                    FiscalGuide.Status.READY,
                    FiscalGuide.Status.FAILED,
                    FiscalGuide.Status.UNKNOWN,
                ]
            )
        elif guide_status != "all":
            filtered_guides = filtered_guides.filter(status=guide_status)
        guide_filtered_total = filtered_guides.count()
        guide_items = filtered_guides.order_by("due_on", "company__name")
    guide_page = Paginator(guide_items, 100).get_page(request.GET.get("page"))
    guide_list = list(guide_page.object_list)
    guide_querystring = urlencode({"q": guide_search, "status": guide_status, "due": guide_due})
    uncertain_periods = set(
        guide_query.filter(status=FiscalGuide.Status.UNKNOWN).values_list(
            "company_id",
            "kind",
            "competence",
        )
    )
    can_issue_guides = _can_prepare_dte(context)
    for guide in guide_list:
        guide.amount_brl = Decimal(guide.amount_cents) / 100
        guide.usage_quote = None
        guide.usage_error = ""
        guide.ui_guidance = _guide_state_guidance(guide.status, guide.error_code)
        days_until_due = (guide.due_on - today).days
        if guide.status in {FiscalGuide.Status.ISSUED, FiscalGuide.Status.SKIPPED}:
            guide.due_context = ""
            guide.due_tone = ""
        elif days_until_due < 0:
            guide.due_context = f"Prazo passou há {abs(days_until_due)} dia" + (
                "" if days_until_due == -1 else "s"
            )
            guide.due_tone = "is-danger"
        elif days_until_due == 0:
            guide.due_context = "Vence hoje"
            guide.due_tone = "is-warning"
        elif days_until_due == 1:
            guide.due_context = "Vence amanhã"
            guide.due_tone = "is-warning"
        elif days_until_due <= 7:
            guide.due_context = f"Vence em {days_until_due} dias"
            guide.due_tone = "is-warning"
        else:
            guide.due_context = ""
            guide.due_tone = ""
        if guide.status in {FiscalGuide.Status.READY, FiscalGuide.Status.FAILED}:
            if (guide.company_id, guide.kind, guide.competence) in uncertain_periods:
                guide.usage_error = "Há emissão anterior a confirmar nesta competência."
                continue
            if office.is_demo:
                guide.usage_quote = SimpleNamespace(
                    total_tokens=0,
                    additional_overage_cents=0,
                    additional_overage_tokens=0,
                )
            else:
                try:
                    guide.usage_quote = quote_tokens(
                        organization=office,
                        module_code="integra",
                        action_code=guide.integra_service_key,
                    )
                except BillingError as exc:
                    guide.usage_error = str(exc)
        if guide.usage_quote is not None:
            guide.usage_overage_brl = Decimal(guide.usage_quote.additional_overage_cents) / 100
        guide.can_issue_now = bool(
            can_issue_guides
            and guide.usage_quote is not None
            and guide.status in {FiscalGuide.Status.READY, FiscalGuide.Status.FAILED}
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
        not office.is_demo
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
                item["component_count"] = cast(int, item["component_count"]) + 1
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
        except (RuntimeError, ValueError):
            logger.warning(
                "The governed Domínio guide snapshot could not be read",
                exc_info=True,
                extra={"organization_id": str(office.id)},
            )
            dominio_calculation_error = (
                "A origem não respondeu à leitura. Verifique a conexão e tente novamente."
            )
        except Exception:
            logger.exception("Failed to read the governed Domínio guide calculation snapshot")
            dominio_calculation_error = (
                "O Domínio não respondeu à consulta de apurações. Tente novamente."
            )
    pending_statuses = [
        FiscalGuide.Status.READY,
        FiscalGuide.Status.FAILED,
        FiscalGuide.Status.UNKNOWN,
    ]
    guide_data_available = guide_query.exists()
    if office.is_demo:
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
            "guide_page": guide_page,
            "guide_querystring": guide_querystring,
            "guide_data_available": guide_data_available,
            "guide_filtered_total": guide_filtered_total,
            "guide_search": guide_search,
            "guide_status": guide_status,
            "guide_due": guide_due,
            "guide_source_connector": source_connector,
            "guide_source_read_attempted": bool(
                source_connector
                and source_connector.mode == IntelligenceConnector.Mode.DIRECT_ODBC
                and source_connector.odbc_dsn
            ),
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
            "can_issue_guides": can_issue_guides,
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
        exponent = component.as_tuple().exponent
        if component <= 0 or not isinstance(exponent, int) or exponent < -2:
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
    company_id_raw = request.POST.get("company") or request.GET.get("company", "")
    competence = (request.POST.get("competence") or request.GET.get("competence", "")).strip()
    if re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", competence) is None or competence.endswith("/0000"):
        messages.error(request, "Escolha uma competência válida (MM/AAAA) na carteira.")
        return redirect("hub:guides")
    try:
        company_id = uuid.UUID(company_id_raw)
    except (ValueError, TypeError):
        messages.error(request, "Escolha uma empresa e uma competência na carteira.")
        return redirect("hub:guides")
    company = get_object_or_404(
        allowed_companies,
        id=company_id,
        organization=office,
        active=True,
    )
    dominio_calculation_unavailable = False
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
        logger.warning(
            "The governed Domínio calculation could not be reloaded",
            exc_info=True,
            extra={"organization_id": str(office.id), "company_id": str(company.id)},
        )
        dominio_calculation = None
        dominio_calculation_unavailable = True
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
                        amount_cents=cast(int, dominio_calculation["amount_cents"]),
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
            request_quote = (
                SimpleNamespace(additional_overage_cents=0)
                if office.is_demo
                else quote_tokens(
                    organization=office,
                    module_code="integra",
                    action_code=service_key,
                )
            )
            approved_cents = int(request.POST.get("approved_overage_cents", "0"))
            if approved_cents != request_quote.additional_overage_cents:
                raise DctfWebDocumentTransitionError(
                    "O custo mudou desde a abertura da tela. Revise e confirme novamente."
                )
            if office.is_demo:
                put_progress(
                    request,
                    "dctfweb_bulk",
                    f"{kind}:{company.id}:{competence}",
                    {"completed": True, "completed_at": timezone.now().isoformat()},
                )
            else:
                request_dctfweb_document(
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
            messages.success(
                request,
                "Simulação concluída somente nesta sessão, sem cobrança ou documento oficial."
                if office.is_demo
                else "Consulta autorizada e adicionada à fila da central.",
            )
            target = reverse("hub:dctfweb-consult")
            return redirect(
                f"{target}?{urlencode({'company': company.id, 'competence': competence})}"
            )

    cards: list[dict[str, object]] = []
    for position, (kind, service_key) in enumerate(DCTFWEB_DOCUMENT_SERVICE.items(), start=1):
        card_quote: TokenQuote | SimpleNamespace | None = None
        error = ""
        if office.is_demo:
            card_quote = SimpleNamespace(
                included_remaining=0,
                tokens_per_operation=0,
                total_tokens=0,
                additional_overage_tokens=0,
                additional_overage_cents=0,
                token_price_cents=0,
            )
        else:
            try:
                card_quote = quote_tokens(
                    organization=office,
                    module_code="integra",
                    action_code=service_key,
                )
            except BillingError as exc:
                error = str(exc)
        existing_document = (
            None
            if office.is_demo
            else DctfWebDocument.objects.filter(
                organization=office,
                company=company,
                competence=competence,
                kind=kind,
            ).first()
        )
        demo_completed = office.is_demo and bool(
            get_progress(request, "dctfweb_bulk", f"{kind}:{company.id}:{competence}").get(
                "completed"
            )
        )
        cards.append(
            {
                "kind": kind,
                "label": DctfWebDocument.Kind(kind).label,
                "position": position,
                "quote": card_quote,
                "additional_overage_brl": (
                    Decimal(card_quote.additional_overage_cents) / 100 if card_quote else None
                ),
                "token_price_brl": (
                    Decimal(card_quote.token_price_cents) / 100 if card_quote else None
                ),
                "error": error,
                "document": existing_document,
                "status_guidance": (
                    _document_state_guidance(
                        existing_document.status,
                        existing_document.error_code,
                    )
                    if existing_document
                    else "Consulte este documento para conferir a competência."
                ),
                "demo_completed": demo_completed,
            }
        )
    documents_completed = sum(
        bool(card["demo_completed"])
        or (
            isinstance(card["document"], DctfWebDocument)
            and card["document"].status == DctfWebDocument.Status.AVAILABLE
        )
        for card in cards
    )
    context.update(
        {
            "page_title": "Consultar DCTFWeb",
            "consult_company": company,
            "consult_competence": competence,
            "consult_cards": cards,
            "documents_completed": documents_completed,
            "can_authorize": _can_prepare_dte(context),
            "dominio_calculation": dominio_calculation,
            "dominio_calculation_unavailable": dominio_calculation_unavailable,
            "dctfweb_documents_ready": all(
                any(
                    card["kind"] == required_kind
                    and isinstance(card["document"], DctfWebDocument)
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
                    FiscalGuide.Status.UNKNOWN,
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
        try:
            company_id = str(uuid.UUID(company_id))
        except ValueError as exc:
            raise DctfWebDocumentTransitionError("Uma seleção da carteira ficou inválida.") from exc
        if (
            not separator
            or re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", competence) is None
            or competence.endswith("/0000")
        ):
            raise DctfWebDocumentTransitionError("Uma seleção da carteira ficou inválida.")
        key = (company_id, competence)
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
        elif office.is_demo:
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


def _review_result_redirect(request: HttpRequest, case_id: object) -> HttpResponseBase:
    return_to = request.POST.get("return_to") or request.GET.get("return_to")
    if return_to:
        return redirect(safe_next(request, return_to, fallback=reverse("hub:nfse-center")))
    return detail_redirect(request, "hub:review-detail", case_id=case_id)


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
    can_issue = _can_prepare_dte(context)
    guide_view = cast(Any, guide)
    guide_view.amount_brl = Decimal(guide.amount_cents) / 100
    guide_view.ui_guidance = _guide_state_guidance(guide.status, guide.error_code)
    guide_view.usage_quote = None
    guide_view.usage_error = ""
    has_uncertain_attempt = FiscalGuide.objects.filter(
        organization=office,
        company_id=guide.company_id,
        kind=guide.kind,
        competence=guide.competence,
        status=FiscalGuide.Status.UNKNOWN,
    ).exclude(pk=guide.pk).exists()
    if guide.status in {FiscalGuide.Status.READY, FiscalGuide.Status.FAILED}:
        if has_uncertain_attempt:
            guide_view.usage_error = "Há uma emissão anterior a confirmar nesta competência."
        elif office.is_demo:
            guide_view.usage_quote = SimpleNamespace(
                total_tokens=0,
                additional_overage_cents=0,
                additional_overage_tokens=0,
            )
        else:
            try:
                guide_view.usage_quote = quote_tokens(
                    organization=office,
                    module_code="integra",
                    action_code=guide.integra_service_key,
                )
            except BillingError as exc:
                guide_view.usage_error = str(exc)
    if guide_view.usage_quote is not None:
        guide_view.usage_overage_brl = (
            Decimal(guide_view.usage_quote.additional_overage_cents) / 100
        )
    guide_view.can_issue_now = bool(
        can_issue
        and guide_view.usage_quote is not None
        and guide.status in {FiscalGuide.Status.READY, FiscalGuide.Status.FAILED}
    )
    history_page = Paginator(
        guide.attempt_events.filter(organization=office)
        .defer("provider_payload")
        .order_by("-attempt", "-observed_at", "-created_at", "-pk"),
        20,
    ).get_page(request.GET.get("history_page"))
    requester_ids = []
    for event in history_page:
        with suppress(ValueError, AttributeError):
            requester_ids.append(uuid.UUID(event.requested_by_reference))
    requester_names = {
        str(member.user_id): member.user.full_name or member.user.email
        for member in Membership.objects.filter(
            organization=office,
            user_id__in=requester_ids,
        ).select_related("user")
    }
    history_rows = [
        {
            "event": event,
            "requester": requester_names.get(event.requested_by_reference, ""),
            "guidance": _guide_state_guidance(event.status, event.error_code),
        }
        for event in history_page
    ]
    history_query = request.GET.copy()
    history_query.pop("history_page", None)
    context.update(
        {
            "page_title": "Detalhes da guia",
            "guide": guide,
            "guide_history_page": history_page,
            "guide_history_rows": history_rows,
            "guide_history_query": history_query.urlencode(),
            "guide_amount_brl": guide_view.amount_brl,
            "can_issue_guides": can_issue,
        }
    )
    return render(request, "hub/guide_detail.html", context)


@office_required
@require_http_methods(["GET"])
def demo_guide_pdf(request: HttpRequest, guide_id: str) -> HttpResponse:
    """Give the demo an unmistakably non-official PDF; never proxy a real guide."""

    from io import BytesIO

    from reportlab.lib.pagesizes import A4  # type: ignore[import-untyped]
    from reportlab.pdfgen import canvas  # type: ignore[import-untyped]

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
@require_http_methods(["GET"])
def guide_attempt_pdf(request: HttpRequest, guide_id: str, event_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.GUIDES))
    if blocked:
        raise Http404
    office = cast(Organization, context["office"])
    if office.is_demo:
        raise Http404
    guide = get_object_or_404(
        FiscalGuide,
        pk=guide_id,
        organization=office,
        company__in=context["companies"],
    )
    event = get_object_or_404(
        guide.attempt_events,
        pk=event_id,
        organization=office,
        status=FiscalGuide.Status.ISSUED,
    )
    if event.request_snapshot.get("simulated"):
        raise Http404
    try:
        payload = json.loads(event.provider_payload)
        if not isinstance(payload, dict):
            raise ValueError
        document = extract_pdf(payload)
    except (TypeError, ValueError, IntegraError) as exc:
        raise Http404 from exc
    response = HttpResponse(document, content_type="application/pdf")
    response["Content-Disposition"] = f'attachment; filename="guia-tentativa-{event.attempt}.pdf"'
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    record_event(
        action="hub.guide.attempt_pdf_downloaded",
        actor=cast(User, request.user),
        organization=office,
        target=event,
        request=request,
        metadata={"guide_id": str(guide.pk), "attempt": event.attempt},
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
    if office.is_demo:
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
                len(
                    _demo_dte_runs_for_view(
                        request,
                        allowed_companies.filter(active=True),
                        office,
                        include_results=False,
                    )[0]
                )
                if office.is_demo
                else _visible_pending_dte_runs(context).count()
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


def _parcelamento_state_guidance(
    status: str, *, error_code: str = "", kind: str = ""
) -> str:
    """Return safe, actionable copy without reflecting provider messages."""

    if status == ParcelamentoOperation.Status.QUEUED:
        return "A solicitação entrou na fila. Acompanhe sem enviar outra vez."
    if status == ParcelamentoOperation.Status.FETCHING:
        return "A central está consultando o fornecedor. Acompanhe sem repetir."
    if status == ParcelamentoOperation.Status.AVAILABLE:
        return (
            "O DAS está pronto para baixar."
            if kind == ParcelamentoOperation.Kind.DAS
            else "O resultado está disponível para conferência."
        )
    if status == ParcelamentoOperation.Status.EMPTY:
        return "A consulta terminou sem parcelamentos para esta empresa."
    if status == ParcelamentoOperation.Status.UNKNOWN:
        return "O fornecedor não confirmou o resultado. Confira no e-CAC antes de prosseguir."
    if status == ParcelamentoOperation.Status.FAILED:
        if error_code == "authorization_revoked":
            return "O acesso mudou antes da consulta. Revise permissões e responsável."
        if error_code == "manual_review":
            return "A conferência no e-CAC foi registrada. Uma nova tentativa pode ser revisada."
        return "A operação não foi concluída. Revise acesso e custo antes de tentar novamente."
    return "Confira a situação antes de escolher o próximo passo."


def _prepare_parcelamento_operation_for_view(
    operation: ParcelamentoOperation | None,
) -> ParcelamentoOperation | None:
    if operation is not None:
        operation_view = cast(Any, operation)
        operation_view.ui_guidance = _parcelamento_state_guidance(
            operation.status,
            error_code=operation.error_code,
            kind=operation.kind,
        )
    return operation


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
    visitor = office.is_demo

    if request.method == "POST":
        if not _can_prepare_dte(context):
            return refuse(request, "Seu perfil pode consultar resultados, mas não executar ações.")
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
                selected_company_ids = [uuid.UUID(value) for value in selected_ids]
            except ValueError:
                messages.error(request, "Selecione empresas válidas e tente novamente.")
                return redirect("hub:parcelamentos")
            selected = list(all_companies.filter(id__in=selected_company_ids).order_by("name"))
            if len(selected) != len(selected_company_ids):
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
                if len(selected) == 1:
                    return redirect(
                        f"{reverse('hub:parcelamentos')}?company={selected[0].id}#company-heading"
                    )
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
                if len(selected) == 1:
                    return redirect(
                        f"{reverse('hub:parcelamentos')}?company={selected[0].id}#company-heading"
                    )
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
        elif not visitor and action == "release_uncertain":
            if not _can_prepare_dte(context):
                return refuse(
                    request, "Seu perfil pode consultar resultados, mas não autorizar consumo."
                )
            if request.POST.get("confirmed") != "yes":
                messages.error(
                    request,
                    "Confirme que o resultado foi conferido no e-CAC antes de liberar a tentativa.",
                )
                return redirect(
                    f"{reverse('hub:parcelamentos')}?company={company.id}#history-heading"
                )
            try:
                operation_uuid = uuid.UUID(request.POST.get("operation", ""))
                release_uncertain_parcelamento_operation(
                    organization=office,
                    company=company,
                    operation_id=operation_uuid,
                    actor=request.user,
                    request=request,
                )
            except (ParcelamentoTransitionError, ValueError) as exc:
                messages.error(
                    request,
                    str(exc)
                    if isinstance(exc, ParcelamentoTransitionError)
                    else "Operação inválida.",
                )
            else:
                messages.success(request, "Conferência registrada. Nova tentativa liberada.")
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
        return redirect(f"{reverse('hub:parcelamentos')}?company={company.id}#company-heading")

    consultation = (
        get_progress(request, "parcelamento_consultations", company.id) if company else {}
    )
    operations = ParcelamentoOperation.objects.filter(
        organization=office, company__in=all_companies
    ).select_related("company", "token_usage_event")
    if visitor:
        operations = operations.none()
    latest_by_company: dict[str, ParcelamentoOperation] = {}
    for operation in operations.filter(kind=ParcelamentoOperation.Kind.ORDERS).order_by(
        "company_id", "-requested_at"
    ):
        latest_by_company.setdefault(str(operation.company_id), operation)

    current_year_month = int(timezone.localdate().strftime("%Y%m"))

    def installment_timing(year_month: int) -> str:
        if year_month < current_year_month:
            return "overdue"
        return "current" if year_month == current_year_month else "future"

    agreements: list[Any] = []
    available_installments: list[Any] = []
    orders_result: ParcelamentoOperation | None = None
    if visitor and company and consultation:
        guide_progress = get_section(request, "parcelamento_guides")
        for demo_agreement in _demo_parcelamentos(company):
            payments = []
            for installment in demo_agreement.installments:
                key = f"{company.id}:{demo_agreement.number}:{installment.competence_key}"
                guide_state = guide_progress.get(key, {})
                if installment.paid:
                    payments.append(
                        SimpleNamespace(
                            label=installment.competence,
                            due_on=installment.due_on,
                            paid_on=installment.due_on - timedelta(days=2),
                            amount=installment.amount_brl,
                        )
                    )
                    continue
                available_installments.append(
                    SimpleNamespace(
                        agreement=demo_agreement.number,
                        competence=installment.competence_key,
                        competence_label=installment.competence,
                        due_on=installment.due_on,
                        amount=installment.amount_brl,
                        timing=(
                            "overdue"
                            if installment.due_on < timezone.localdate()
                            else installment_timing(int(installment.competence_key))
                        ),
                        operation=None,
                        demo_protocol=str(guide_state.get("protocol", "")),
                    )
                )
            agreements.append(
                SimpleNamespace(
                    number=demo_agreement.number,
                    status=demo_agreement.status,
                    requested_on=demo_agreement.consolidated_on,
                    status_on=demo_agreement.consolidated_on,
                    detail_operation=None,
                    detail=SimpleNamespace(
                        consolidated=demo_agreement.consolidated_brl,
                        installments_count=60,
                        basic_installment=demo_agreement.installments[0].amount_brl,
                        payments=payments,
                    ),
                )
            )

    if not visitor and company:
        orders_result = (
            operations.filter(
                company=company,
                kind=ParcelamentoOperation.Kind.ORDERS,
                status__in=[
                    ParcelamentoOperation.Status.AVAILABLE,
                    ParcelamentoOperation.Status.EMPTY,
                ],
            )
            .order_by("-requested_at")
            .first()
        )
        if (
            orders_result
            and orders_result.status == ParcelamentoOperation.Status.AVAILABLE
            and orders_result.provider_payload
        ):
            try:
                summaries = pedidos(json.loads(orders_result.provider_payload))
            except (ValueError, TypeError, json.JSONDecodeError):
                summaries = []
            for item in summaries:
                detail_operation = (
                    operations.filter(
                        company=company,
                        kind=ParcelamentoOperation.Kind.DETAIL,
                        agreement_number=item.numero,
                    )
                    .order_by("-requested_at")
                    .first()
                )
                _prepare_parcelamento_operation_for_view(detail_operation)
                detail = None
                if (
                    detail_operation
                    and detail_operation.status == ParcelamentoOperation.Status.AVAILABLE
                    and detail_operation.provider_payload
                ):
                    try:
                        parsed = detalhe(
                            json.loads(detail_operation.provider_payload),
                            numero_esperado=item.numero,
                        )
                    except (ValueError, TypeError, json.JSONDecodeError):
                        parsed = None
                    if parsed is not None:
                        detail = SimpleNamespace(
                            consolidated=parsed.valor_consolidado,
                            installments_count=parsed.quantidade_parcelas,
                            basic_installment=parsed.parcela_basica,
                            payments=[
                                SimpleNamespace(
                                    label=(
                                        f"{str(payment.mes_parcela)[4:]}/"
                                        f"{str(payment.mes_parcela)[:4]}"
                                    ),
                                    due_on=payment.vencimento,
                                    paid_on=payment.arrecadado_em,
                                    amount=payment.valor_pago,
                                )
                                for payment in parsed.pagamentos
                            ],
                        )
                agreements.append(
                    SimpleNamespace(
                        number=item.numero,
                        status=item.situacao,
                        requested_on=item.data_pedido,
                        status_on=item.data_situacao,
                        detail_operation=detail_operation,
                        detail=detail,
                    )
                )
        installment_result = (
            operations.filter(
                company=company,
                kind=ParcelamentoOperation.Kind.INSTALLMENTS,
                status=ParcelamentoOperation.Status.AVAILABLE,
            )
            .order_by("-requested_at")
            .first()
        )
        if installment_result and installment_result.provider_payload:
            try:
                parsed_installments = parcelas_disponiveis(
                    json.loads(installment_result.provider_payload)
                )
            except (ValueError, TypeError, json.JSONDecodeError):
                parsed_installments = []
            for parcel in parsed_installments:
                das_operation = (
                    operations.filter(
                        company=company,
                        kind=ParcelamentoOperation.Kind.DAS,
                        competence=str(parcel.ano_mes),
                    )
                    .order_by("-requested_at")
                    .first()
                )
                _prepare_parcelamento_operation_for_view(das_operation)
                available_installments.append(
                    SimpleNamespace(
                        agreement=None,
                        competence=str(parcel.ano_mes),
                        competence_label=f"{str(parcel.ano_mes)[4:]}/{str(parcel.ano_mes)[:4]}",
                        due_on=None,
                        amount=parcel.valor,
                        timing=installment_timing(parcel.ano_mes),
                        operation=das_operation,
                        demo_protocol="",
                    )
                )
        available_installments.sort(key=lambda parcel: parcel.competence)

    pending_statuses = {
        ParcelamentoOperation.Status.QUEUED,
        ParcelamentoOperation.Status.FETCHING,
    }
    company_pending = bool(
        company
        and not visitor
        and operations.filter(company=company, status__in=pending_statuses).exists()
    )
    company_orders_operation = (
        latest_by_company.get(str(company.id)) if company and not visitor else None
    )
    _prepare_parcelamento_operation_for_view(company_orders_operation)
    portfolio_page = Paginator(companies.order_by("name"), 30).get_page(request.GET.get("page"))
    portfolio = list(portfolio_page.object_list)
    portfolio_querystring = urlencode({"search": search}) if search else ""
    for portfolio_company in portfolio:
        portfolio_company.parcelamento_operation = latest_by_company.get(str(portfolio_company.id))
        _prepare_parcelamento_operation_for_view(portfolio_company.parcelamento_operation)
        portfolio_company.parcelamento_demo_consulted_at = None
        if visitor:
            demo_state = get_progress(request, "parcelamento_consultations", portfolio_company.id)
            if demo_state.get("consulted_at"):
                portfolio_company.parcelamento_demo_consulted_at = parse_datetime(
                    str(demo_state["consulted_at"])
                )
    portfolio_pending = any(
        getattr(item.parcelamento_operation, "status", "") in pending_statuses for item in portfolio
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
        for operation_kind in PARCELAMENTO_SERVICE:
            operation_quotes[str(operation_kind)] = SimpleNamespace(
                total_tokens=0, additional_overage_cents=0
            )
    else:
        for operation_kind, service_key in PARCELAMENTO_SERVICE.items():
            try:
                operation_quotes[str(operation_kind)] = quote_tokens(
                    organization=office,
                    module_code="integra",
                    action_code=service_key,
                )
            except BillingError:
                continue
    parcelamento_operations: list[ParcelamentoOperation] = []
    parcelamento_operations_page: object | None = None
    parcelamento_operations_querystring = ""
    if company:
        parcelamento_operations_page = Paginator(operations.filter(company=company), 20).get_page(
            request.GET.get("operation_page")
        )
        parcelamento_operations = list(parcelamento_operations_page.object_list)
        for operation in parcelamento_operations:
            _prepare_parcelamento_operation_for_view(operation)
        operation_query_params = request.GET.copy()
        operation_query_params.pop("operation_page", None)
        parcelamento_operations_querystring = operation_query_params.urlencode()

    context.update(
        {
            "page_title": "Parcelamentos",
            "parcelamento_companies": companies.order_by("name"),
            "parcelamento_portfolio": portfolio,
            "parcelamento_portfolio_page": portfolio_page,
            "parcelamento_portfolio_total": portfolio_page.paginator.count,
            "parcelamento_portfolio_querystring": portfolio_querystring,
            "parcelamento_search": search,
            "parcelamento_company": company,
            "parcelamento_consultation": consultation,
            "parcelamento_agreements": agreements,
            "parcelamento_demo": visitor,
            "parcelamento_orders_quote": orders_quote,
            "parcelamento_quote_error": quote_error,
            "parcelamento_operations": parcelamento_operations,
            "parcelamento_operations_page": parcelamento_operations_page,
            "parcelamento_operations_querystring": parcelamento_operations_querystring,
            "parcelamento_available_installments": available_installments,
            "parcelamento_operation_quotes": operation_quotes,
            "parcelamento_detail_quote": operation_quotes.get(ParcelamentoOperation.Kind.DETAIL),
            "parcelamento_installments_quote": operation_quotes.get(
                ParcelamentoOperation.Kind.INSTALLMENTS
            ),
            "parcelamento_das_quote": operation_quotes.get(ParcelamentoOperation.Kind.DAS),
            "parcelamento_consult_quote": operation_quotes.get(ParcelamentoOperation.Kind.ORDERS),
            "parcelamento_detail_overage_brl": (
                Decimal(operation_quotes[ParcelamentoOperation.Kind.DETAIL].additional_overage_cents)
                / 100
                if ParcelamentoOperation.Kind.DETAIL in operation_quotes
                else None
            ),
            "parcelamento_installments_overage_brl": (
                Decimal(
                    operation_quotes[
                        ParcelamentoOperation.Kind.INSTALLMENTS
                    ].additional_overage_cents
                )
                / 100
                if ParcelamentoOperation.Kind.INSTALLMENTS in operation_quotes
                else None
            ),
            "parcelamento_das_overage_brl": (
                Decimal(operation_quotes[ParcelamentoOperation.Kind.DAS].additional_overage_cents)
                / 100
                if ParcelamentoOperation.Kind.DAS in operation_quotes
                else None
            ),
            "parcelamento_consult_overage_brl": (
                Decimal(operation_quotes[ParcelamentoOperation.Kind.ORDERS].additional_overage_cents)
                / 100
                if ParcelamentoOperation.Kind.ORDERS in operation_quotes
                else None
            ),
            "parcelamento_orders_result": orders_result,
            "parcelamento_company_orders_operation": company_orders_operation,
            "parcelamento_pending": company_pending or portfolio_pending,
            "can_authorize": _can_prepare_dte(context),
        }
    )
    return render(request, "hub/parcelamentos.html", context)


@office_required
@require_http_methods(["GET"])
def demo_parcelamento_das_pdf(
    request: HttpRequest,
    company_id: uuid.UUID,
    agreement: int,
    competence: str,
) -> HttpResponse:
    """Download a session-owned and unmistakably fictitious DAS."""

    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas

    context, blocked = _module_page_context(request, definition(ProductModule.Code.INTEGRA))
    if blocked:
        raise Http404
    office = cast(Organization, context["office"])
    if not office.is_demo or not re.fullmatch(r"\d{6}", competence):
        raise Http404
    company = get_object_or_404(
        cast("QuerySet[ClientCompany]", context["companies"]).filter(active=True),
        id=company_id,
    )
    installments = {
        (item.number, installment.competence_key): installment
        for item in _demo_parcelamentos(company)
        for installment in item.installments
        if not installment.paid
    }
    installment = installments.get((agreement, competence))
    key = f"{company.id}:{agreement}:{competence}"
    protocol = str(get_progress(request, "parcelamento_guides", key).get("protocol", ""))
    if installment is None or not protocol:
        raise Http404

    amount = f"{installment.amount_brl:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")
    buffer = io.BytesIO()
    page = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    page.setTitle("DAS ficticio - demonstracao CICA")
    page.setFont("Helvetica-Bold", 18)
    page.drawString(48, height - 64, "DAS FICTICIO - SEM VALIDADE FISCAL")
    page.setFont("Helvetica", 11)
    lines = [
        "Documento gerado somente para demonstrar a jornada do CICA.",
        f"Empresa: {company.name}",
        f"CNPJ: {company.cnpj_masked or '-'}",
        f"Acordo: {agreement}",
        f"Competencia: {installment.competence}",
        f"Vencimento demonstrativo: {installment.due_on:%d/%m/%Y}",
        f"Valor demonstrativo: R$ {amount}",
        f"Protocolo ficticio: {protocol}",
        "Nao pague, contabilize ou use este arquivo como comprovante oficial.",
    ]
    y = height - 104
    for line in lines:
        page.drawString(48, y, line)
        y -= 24
    page.setStrokeColorRGB(0.72, 0.2, 0.16)
    page.rect(36, 36, width - 72, height - 72)
    page.save()
    response = HttpResponse(buffer.getvalue(), content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="DAS-FICTICIO-{company.dominio_code or "empresa"}-{competence}.pdf"'
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@office_required
def parcelamento_das_pdf(request: HttpRequest, operation_id: uuid.UUID) -> HttpResponseBase:
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
    request: HttpRequest,
    companies: QuerySet[ClientCompany],
    office: Organization,
    *,
    include_results: bool = True,
) -> tuple[list[SimpleNamespace], list[SimpleNamespace]]:
    """Build the DTE work queue from session progress, never from shared seed runs."""

    allowed = {str(company.id): company for company in companies}
    pending: list[SimpleNamespace] = []
    results: list[SimpleNamespace] = []
    for run_id, entry in get_section(request, "dte_runs").items():
        if not include_results and entry.get("status") != "prepared":
            continue
        selected_ids = entry.get("company_ids", [])
        if not isinstance(selected_ids, list) or any(
            not isinstance(code, str) for code in selected_ids
        ):
            continue
        if entry.get("status") == "prepared" and (
            len(set(selected_ids)) != len(selected_ids)
            or any(code not in allowed for code in selected_ids)
        ):
            continue
        selected = [allowed[code] for code in selected_ids if code in allowed]
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


def _visible_pending_dte_runs(context: dict[str, object]) -> QuerySet[DteRun]:
    """A prepared batch is visible/actionable only within its complete current scope."""
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    return (
        DteRun.objects.filter(organization=office, status=DteRun.Status.AWAITING_APPROVAL)
        .annotate(
            scoped_items=Count(
                "items",
                filter=Q(
                    items__organization=office,
                    items__company__organization=office,
                    items__company__in=companies,
                ),
                distinct=True,
            ),
            actual_items=Count("items", distinct=True),
        )
        .filter(
            actual_items__gt=0,
            actual_items=F("total_companies"),
            scoped_items=F("actual_items"),
        )
    )


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
    visitor = office.is_demo

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

    dte_history_query_params = request.GET.copy()
    dte_history_query_params.pop("history_page", None)
    pending_runs: list[Any]
    dte_history_context: dict[str, object]
    if visitor:
        pending_runs, demo_items = _demo_dte_runs_for_view(request, companies, office)
        demo_dte_items_page = Paginator(demo_items, 30).get_page(request.GET.get("history_page"))
        dte_history_context = {
            "dte_items": list(demo_dte_items_page.object_list),
            "dte_items_page": demo_dte_items_page,
            "dte_items_querystring": dte_history_query_params.urlencode(),
            "dte_items_total": demo_dte_items_page.paginator.count,
        }
    else:
        stored_dte_items_page = Paginator(
            DteRunItem.objects.filter(organization=office, company_id__in=allowed_company_ids)
            .select_related("company", "run", "run__requested_by", "continuation")
            .order_by("-run__requested_at", "company__name"),
            30,
        ).get_page(request.GET.get("history_page"))
        dte_history_context = {
            "dte_items": list(stored_dte_items_page.object_list),
            "dte_items_page": stored_dte_items_page,
            "dte_items_querystring": dte_history_query_params.urlencode(),
            "dte_items_total": stored_dte_items_page.paginator.count,
        }
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
    dte_message_query_params = request.GET.copy()
    dte_message_query_params.pop("page", None)
    dte_message_query_params["status"] = message_filter
    dte_message_query_params["company"] = str(selected_company.id) if selected_company else ""
    dte_message_query_params["q"] = search_term
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
            _visible_pending_dte_runs(context)
            .select_related("requested_by")
            .prefetch_related("items__company")
            .order_by("-requested_at")
        )
    for pending in pending_runs:
        if office.is_demo:
            pending.usage_quote = SimpleNamespace(
                total_tokens=0,
                included_remaining=0,
                additional_overage_tokens=0,
                additional_overage_cents=0,
            )
        else:
            try:
                pending.usage_quote = quote_tokens(
                    organization=office,
                    module_code="integra",
                    action_code=DTE_ACTION_CODE,
                    operations=pending.total_companies,
                )
            except BillingError:
                try:
                    pending.usage_quote = quote_usage(
                        organization=office,
                        action_code=DTE_ACTION_CODE,
                        units=pending.total_companies,
                    )
                except BillingError:
                    pending.usage_quote = None
        if pending.usage_quote is not None and not hasattr(pending.usage_quote, "total_tokens"):
            pending.usage_quote.total_tokens = pending.total_companies
            pending.usage_quote.additional_overage_tokens = (
                pending.usage_quote.additional_overage_units
            )
        pending.overage_brl = (
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
            **dte_history_context,
            "dte_message_page": message_page,
            "dte_message_querystring": dte_message_query_params.urlencode(),
            "dte_message_filter": message_filter,
            "dte_selected_company": selected_company,
            "dte_search_term": search_term,
            "dte_companies": companies.order_by("name"),
            "dte_stats": {
                "awaiting": len(pending_runs),
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
    if office.is_demo:
        return refuse(
            request,
            "A consulta fictícia não tem paginação externa para continuar.",
            kind="unavailable",
        )
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


def _can_acknowledge_dte(context: dict[str, object], *, company: ClientCompany) -> bool:
    if not context["support_can_mutate"] or context["support_session"] is not None:
        return False
    membership = context["membership"]
    if not isinstance(membership, Membership):
        return False
    if membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}:
        return True
    if membership.role == Membership.Role.OPERATOR and membership.can_acknowledge_dte:
        return True
    return (
        membership.role not in {Membership.Role.AUDITOR, Membership.Role.BILLING}
        and CompanyAccessGrant.objects.filter(
            organization=membership.organization,
            membership=membership,
            company=company,
            is_active=True,
        ).exists()
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
    visitor = office.is_demo
    if visitor:
        entry = get_progress(request, "dte_messages", message.id)
        access = (
            DteMessageAccess(
                organization=office,
                message=message,
                status=DteMessageAccess.Status.OPENED,
                attempt_count=1,
                requested_by=cast(User, request.user),
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
    can_acknowledge = _can_acknowledge_dte(context, company=message.company)
    try:
        detail_quote: TokenQuote | UsageQuote | SimpleNamespace | None = (
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
    if isinstance(detail_quote, UsageQuote):
        detail_quote = SimpleNamespace(
            total_tokens=1,
            additional_overage_tokens=detail_quote.additional_overage_units,
            additional_overage_cents=detail_quote.additional_overage_cents,
        )
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
        elif (
            detail_quote is not None
            and detail_quote.additional_overage_cents
            and (
                not can_authorize_overage
                or request.POST.get("confirm_overage") != "on"
                or request.POST.get("approved_overage_cents")
                != str(detail_quote.additional_overage_cents)
            )
        ):
            messages.error(
                request,
                "O valor do excedente precisa ser conferido e autorizado por um dono "
                "ou administrador antes da abertura.",
            )
        else:
            assert detail_quote is not None
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
            "dte_analysis_activity": OperationalActivity.objects.filter(
                organization=office,
                company=message.company,
                source_dte_message=message,
            ).first(),
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
    if office.is_demo:
        entry = get_progress(request, "dte_runs", run_id)
        if entry.get("status") != "prepared":
            raise Http404
        selected = entry.get("company_ids", [])
        allowed = {
            str(company.id) for company in cast(QuerySet[ClientCompany], context["companies"])
        }
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
    run = get_object_or_404(_visible_pending_dte_runs(context), id=run_id)
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
@require_http_methods(["GET"])
def reconciliation(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    visitor = office.is_demo
    match_search = request.GET.get("q", "").strip()[:100]
    match_status = request.GET.get("status", "attention")
    if match_status not in {"attention", "all", *ReconciliationMatch.Status.values}:
        match_status = "attention"
    match_query_params = request.GET.copy()
    match_query_params.pop("page", None)
    match_query_params["q"] = match_search
    match_query_params["status"] = match_status
    match_querystring = match_query_params.urlencode()
    match_query = ReconciliationMatch.objects.filter(
        organization=office, transaction__statement__company__in=companies
    ).select_related(
        "transaction__statement__company",
        "dominio_entry",
        "accounting_entry__data_source",
    )
    matches: list[Any]
    if visitor:
        matches = _demo_reconciliation_matches(request, list(companies.filter(active=True)[:2]))
        all_demo_matches = list(matches)
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
        match_page = Paginator(matches, 50).get_page(request.GET.get("page"))
        matches = list(match_page.object_list)
        imports = [
            SimpleNamespace(company=match.transaction.statement.company)
            for match in all_demo_matches
        ]
        context.update(
            {
                "page_title": "Conciliação OFX x Domínio",
                "imports": imports,
                "matches": matches,
                "match_page": match_page,
                "match_querystring": match_querystring,
                "match_total": match_total,
                "match_search": match_search,
                "match_status": match_status,
                "can_confirm_matches": _can_prepare_dte(context),
                "reconciliation_demo": True,
                "reconciliation_stats": {
                    "attention": sum(
                        match.status
                        in {
                            ReconciliationMatch.Status.AMBIGUOUS,
                            ReconciliationMatch.Status.UNMATCHED,
                        }
                        for match in all_demo_matches
                    ),
                    "ambiguous": sum(
                        match.status == ReconciliationMatch.Status.AMBIGUOUS
                        for match in all_demo_matches
                    ),
                    "matched": sum(
                        match.status == ReconciliationMatch.Status.MATCHED
                        for match in all_demo_matches
                    ),
                },
                "can_upload_reconciliation": False,
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
    match_page = Paginator(
        match_query.order_by("-transaction__occurred_on", "-created_at"), 50
    ).get_page(request.GET.get("page"))
    matches = list(match_page.object_list)
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
    for accounting_entry in accounting_candidates:
        # The direct ODBC sync mirrors the same row in both models. Present it
        # once, preferring the Domínio-specific record as operator evidence.
        if accounting_entry.external_key in dominio_source_ids:
            continue
        accounting_entry.amount_brl = Decimal(accounting_entry.amount_cents) / 100  # type: ignore[attr-defined]
        accounting_entry.candidate_token = f"accounting:{accounting_entry.id}"  # type: ignore[attr-defined]
        accounting_entry.source_label = accounting_entry.data_source.label  # type: ignore[attr-defined]
        candidates_by_key.setdefault(
            (
                accounting_entry.company_id,
                accounting_entry.occurred_on,
                accounting_entry.amount_cents,
            ),
            [],
        ).append(accounting_entry)
    for match in matches:
        match.display_entry = match.dominio_entry or match.accounting_entry
        match.amount_brl = Decimal(abs(match.transaction.amount_cents)) / 100
        match.source_label = (
            "Espelho Domínio"
            if match.dominio_entry_id
            else match.accounting_entry.data_source.label
            if match.accounting_entry_id
            else "Sem correspondência"
        )
        match.display_reference = getattr(match.display_entry, "source_id", "") or getattr(
            match.display_entry, "external_key", ""
        )
        match.candidates = candidates_by_key.get(
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
            "imports": BankStatementImport.objects.filter(
                organization=office, company__in=companies
            ).select_related("company")[:20],
            "matches": matches,
            "match_page": match_page,
            "match_querystring": match_querystring,
            "match_total": match_total,
            "match_search": match_search,
            "match_status": match_status,
            "can_confirm_matches": _can_prepare_dte(context),
            "reconciliation_demo": False,
            "reconciliation_stats": reconciliation_stats,
            "can_upload_reconciliation": bool(
                context["support_can_mutate"] and _can_manage_reconciliation(context)
            ),
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
    if office.is_demo:
        matches = {
            str(item.id): item
            for item in _demo_reconciliation_matches(
                request, list(companies.filter(active=True)[:2])
            )
        }
        match = matches.get(str(match_id))
        candidate_id = request.POST.get("dominio_entry_id", "")
        if match is None or candidate_id not in {str(item.id) for item in match.candidates}:
            return refuse(
                request,
                "A correspondência fictícia não está disponível nesta sessão.",
                kind="unavailable",
            )
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
    real_match = get_object_or_404(
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
        return refuse(request, "A origem escolhida não é válida.", kind="unavailable")
    try:
        confirm_reconciliation_match(
            match=real_match,
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


def _reconciliation_run_guidance(
    run: ReconciliationRun, *, local_ocr_available: bool
) -> dict[str, str]:
    """Return safe, actionable copy without reflecting raw processing exceptions."""

    if run.stage == "mapping":
        return {
            "summary": "O arquivo aguarda a associação das colunas antes de ser processado.",
            "label": "Mapear colunas",
            "href": reverse("hub:reconciliation-mapping", args=[run.source_file_id]),
        }
    if run.stage == "financial_account_review":
        return {
            "summary": "A conta do arquivo não corresponde à conta financeira selecionada.",
            "label": "Configurar conta",
            "href": (
                f"{reverse('hub:reconciliation-configuration')}"
                f"?company={run.source_file.company_id}"
            ),
        }
    if run.stage == "ocr_review":
        detail = (
            "A leitura local não encontrou texto. Confira o PDF ou envie OFX, CSV ou XLSX."
            if local_ocr_available
            else "A leitura local de PDF não está disponível. Envie OFX, CSV ou XLSX."
        )
        return {"summary": detail, "label": "Ver importações", "href": "#processamentos"}
    if run.state == ReconciliationRun.State.FAILED:
        return {
            "summary": (
                "O arquivo não pôde ser processado. Confira o formato e reprocesse; "
                "se a falha continuar, informe o nome do arquivo ao suporte."
            ),
            "label": "Ver falha e reprocessar",
            "href": "#processamentos",
        }
    if run.state == ReconciliationRun.State.COMPLETED_ALERTS:
        return {
            "summary": f"{run.error_count} linha(s) precisam de conferência antes de continuar.",
            "label": "Abrir movimentos do arquivo",
            "href": f"?source_file={run.source_file_id}#movimentos",
        }
    if run.state == ReconciliationRun.State.REVIEW:
        return {
            "summary": "Os movimentos estão prontos para a conferência humana.",
            "label": "Abrir movimentos do arquivo",
            "href": f"?source_file={run.source_file_id}#movimentos",
        }
    return {"summary": "", "label": "", "href": ""}


def _reconciliation_v2_context(
    office: Organization, companies: QuerySet[ClientCompany], request: HttpRequest | None = None
) -> dict[str, object]:
    selected_source = None
    source_id = request.GET.get("source_file", "") if request else ""
    if source_id:
        try:
            source_uuid = uuid.UUID(source_id)
        except ValueError:
            raise Http404("Arquivo indisponível.") from None
        selected_source = get_object_or_404(
            ReconciliationSourceFile.objects.select_related("company"),
            pk=source_uuid,
            organization=office,
            company__in=companies,
        )
    history_query_params = request.GET.copy() if request else None
    processing_query_params = history_query_params.copy() if history_query_params else None
    export_query_params = history_query_params.copy() if history_query_params else None
    movement_query_params = history_query_params.copy() if history_query_params else None
    if processing_query_params is not None:
        processing_query_params.pop("processing_page", None)
    if export_query_params is not None:
        export_query_params.pop("export_page", None)
    if movement_query_params is not None:
        movement_query_params.pop("movement_page", None)
    runs = ReconciliationRun.objects.filter(organization=office, source_file__company__in=companies)
    if selected_source:
        runs = runs.filter(source_file=selected_source)
    runs_page = Paginator(
        runs.select_related("source_file", "source_file__company").order_by("-created_at"),
        20,
    ).get_page(request.GET.get("processing_page") if request else 1)
    local_ocr_is_available = local_ocr_available()
    visible_runs = list(runs_page.object_list)
    for run in visible_runs:
        run.guidance = _reconciliation_run_guidance(run, local_ocr_available=local_ocr_is_available)
    all_movements = NormalizedMovement.objects.filter(organization=office, company__in=companies)
    if selected_source:
        all_movements = all_movements.filter(source_file=selected_source)
    movement_filters = {
        "company": request.GET.get("movement_company", "") if request else "",
        "review": request.GET.get("movement_review", "") if request else "",
        "classification": request.GET.get("movement_classification", "") if request else "",
        "query": (request.GET.get("movement_q", "").strip() if request else "")[:100],
    }
    filtered_movements = all_movements
    movement_filter_error = ""
    if movement_filters["company"]:
        try:
            movement_company_id = uuid.UUID(movement_filters["company"])
        except ValueError:
            movement_company_id = None
        if movement_company_id is None:
            movement_filter_error = (
                "A empresa informada no filtro não é válida. Nenhum movimento foi exibido."
            )
            filtered_movements = filtered_movements.none()
        elif not companies.filter(id=movement_company_id).exists():
            movement_filter_error = (
                "A empresa informada não está disponível na sua carteira. "
                "Nenhum movimento foi exibido."
            )
            filtered_movements = filtered_movements.none()
        else:
            filtered_movements = filtered_movements.filter(company_id=movement_company_id)
    if movement_filters["review"] and movement_filters["review"] not in set(
        NormalizedMovement.ReviewState.values
    ):
        movement_filter_error = (
            "A situação de revisão informada não é válida. Nenhum movimento foi exibido."
        )
        filtered_movements = filtered_movements.none()
    elif movement_filters["review"]:
        filtered_movements = filtered_movements.filter(review_state=movement_filters["review"])
    if movement_filters["classification"] and movement_filters["classification"] not in set(
        NormalizedMovement.ClassificationSource.values
    ):
        movement_filter_error = (
            "A classificação informada não é válida. Nenhum movimento foi exibido."
        )
        filtered_movements = filtered_movements.none()
    elif movement_filters["classification"]:
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
        movement.amount_brl = Decimal(abs(movement.amount_cents)) / 100
    exports_page = Paginator(
        AccountingExport.objects.filter(organization=office, company__in=companies)
        .select_related("company", "confirmed_by")
        .order_by("-created_at"),
        20,
    ).get_page(request.GET.get("export_page") if request else 1)
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
    absolute_amount = Case(
        When(amount_cents__lt=0, then=-F("amount_cents")),
        default=F("amount_cents"),
        output_field=IntegerField(),
    )

    def _total_brl(queryset: object) -> Decimal:
        total = queryset.aggregate(  # type: ignore[attr-defined]
            total=Coalesce(Sum(absolute_amount), 0)
        )["total"]
        return Decimal(total) / 100

    dominio_entries = DominioBankEntry.objects.filter(organization=office, company__in=companies)
    stats = {
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
        "imported_amount": _total_brl(all_movements),
        "pending_amount": _total_brl(
            all_movements.filter(
                review_state__in=[
                    NormalizedMovement.ReviewState.PENDING,
                    NormalizedMovement.ReviewState.CONFLICT,
                ]
            )
        ),
        "dominio_entries": dominio_entries.count(),
        "dominio_amount": _total_brl(dominio_entries),
    }
    active_run_count = runs.filter(
        state__in=[ReconciliationRun.State.WAITING, ReconciliationRun.State.PROCESSING]
    ).count()
    blocked_run = (
        runs.filter(
            Q(state=ReconciliationRun.State.FAILED)
            | Q(
                state=ReconciliationRun.State.REVIEW,
                stage__in={"mapping", "financial_account_review", "ocr_review"},
            )
        )
        .select_related("source_file", "source_file__company")
        .order_by("created_at")
        .first()
    )
    if blocked_run:
        guidance = _reconciliation_run_guidance(
            blocked_run, local_ocr_available=local_ocr_is_available
        )
        next_action = {
            "kind": "link",
            "eyebrow": "IMPORTAÇÃO INTERROMPIDA",
            "title": f"Corrigir {blocked_run.source_file.original_filename}",
            "description": guidance["summary"],
            "label": guidance["label"],
            "href": guidance["href"],
        }
    elif stats["conflicts"]:
        next_action = {
            "kind": "link",
            "eyebrow": "COMECE PELOS CONFLITOS",
            "title": f"Resolver {stats['conflicts']} conflito(s) de classificação",
            "description": (
                "Há regras ou evidências incompatíveis. Confira esses movimentos antes dos "
                "demais para não levar divergências adiante."
            ),
            "label": "Revisar conflitos",
            "href": "?movement_review=conflict#movimentos",
        }
    elif stats["pending"]:
        next_action = {
            "kind": "link",
            "eyebrow": "PRÓXIMA AÇÃO",
            "title": f"Revisar {stats['pending']} movimento(s) pendente(s)",
            "description": (
                "Comece pelo que a automação não concluiu. Cada movimento mantém a origem e "
                "as evidências para a decisão humana."
            ),
            "label": "Abrir pendências",
            "href": "?movement_review=pending#movimentos",
        }
    elif active_run_count:
        next_action = {
            "kind": "link",
            "eyebrow": "PROCESSAMENTO EM CURSO",
            "title": f"Acompanhar {active_run_count} importação(ões)",
            "description": "O resultado aparecerá na revisão quando cada arquivo terminar.",
            "label": "Ver processamentos",
            "href": "#processamentos",
        }
    elif not stats["imported"]:
        next_action = {
            "kind": "upload",
            "eyebrow": "PRIMEIRO PASSO",
            "title": "Importar o primeiro extrato ou documento",
            "description": (
                "Escolha a empresa e envie OFX, CSV, XLSX ou PDF. Nada é lançado no Domínio "
                "durante a importação."
            ),
            "label": "Selecionar arquivos",
            "href": "",
        }
    else:
        next_action = {
            "kind": "upload",
            "eyebrow": "CARTEIRA EM DIA",
            "title": "Nenhuma exceção exige revisão agora",
            "description": (
                "Você pode trazer novos arquivos. A exportação continua bloqueada até a "
                "homologação real do layout Domínio."
            ),
            "label": "Nova importação",
            "href": "",
        }
    return {
        "selected_reconciliation_source": selected_source,
        "selected_reconciliation_activity": (
            OperationalActivity.objects.filter(
                source_reconciliation_file=selected_source,
                organization=office,
                company=selected_source.company,
            ).first()
            if selected_source
            else None
        ),
        "upload_form": ReconciliationUploadForm(companies=companies),
        "reconciliation_runs": visible_runs,
        "reconciliation_runs_page": runs_page,
        "reconciliation_runs_querystring": (
            processing_query_params.urlencode() if processing_query_params else ""
        ),
        "reconciliation_runs_total": runs_page.paginator.count,
        "normalized_movements": movements,
        "normalized_movement_page": movement_page,
        "normalized_movement_filters": movement_filters,
        "reconciliation_movement_filter_error": movement_filter_error,
        "normalized_movement_querystring": (
            movement_query_params.urlencode() if movement_query_params else ""
        ),
        "accounting_exports": list(exports_page.object_list),
        "accounting_exports_page": exports_page,
        "accounting_exports_querystring": (
            export_query_params.urlencode() if export_query_params else ""
        ),
        "accounting_exports_total": exports_page.paginator.count,
        "reconciliation_v2_stats": stats,
        "reconciliation_active_run_count": active_run_count,
        "reconciliation_next_action": next_action,
        "reconciliation_local_ocr_available": local_ocr_is_available,
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
    if request.method == "POST" and (
        not context["support_can_mutate"] or not _can_manage_reconciliation(context)
    ):
        return refuse(request, "Seu perfil pode consultar, mas não alterar a configuração.")
    selection = request.POST if request.method == "POST" else request.GET
    company_ids = selection.getlist("company")
    selected_company = None
    if request.method == "GET" and not company_ids:
        selected_company = companies.order_by("name").first()
    elif len(company_ids) == 1:
        try:
            selected_company = companies.filter(id=uuid.UUID(company_ids[0])).first()
        except ValueError:
            selected_company = None
    if selected_company is None:
        if not companies.exists():
            return refuse(
                request, "Cadastre ou habilite uma empresa antes de configurar a conciliação."
            )
        context.update(
            {
                "page_title": "Confira a empresa — Configuração da conciliação",
                "reconciliation_configuration_company": None,
                "reconciliation_company_error": (
                    "Não foi possível abrir a empresa solicitada. Escolha uma empresa "
                    "disponível abaixo. Nenhuma configuração foi alterada."
                ),
            }
        )
        return render(request, "hub/reconciliation_configuration.html", context, status=400)

    def configuration_redirect(section: str) -> HttpResponse:
        return redirect(
            f"{reverse('hub:reconciliation-configuration')}?company={selected_company.id}#{section}"
        )

    action = request.POST.get("action", "")
    forms_by_action: dict[str, forms.BaseForm] = {
        "financial_account": FinancialAccountForm(
            request.POST if action == "financial_account" else None,
            companies=companies,
            initial={"company": selected_company},
            auto_id="id_financial_account_%s",
        ),
        "ledger_account": LedgerAccountForm(
            request.POST if action == "ledger_account" else None,
            companies=companies,
            initial={"company": selected_company},
            auto_id="id_ledger_account_%s",
        ),
        "cost_center": CostCenterForm(
            request.POST if action == "cost_center" else None,
            companies=companies,
            initial={"company": selected_company},
            auto_id="id_cost_center_%s",
        ),
        "accounting_period": AccountingPeriodForm(
            request.POST if action == "accounting_period" else None,
            companies=companies,
            initial={"company": selected_company},
            auto_id="id_accounting_period_%s",
        ),
        "reconciliation_rule": ReconciliationRuleForm(
            request.POST if action == "reconciliation_rule" else None,
            companies=companies,
            initial={"company": selected_company},
            auto_id="id_reconciliation_rule_%s",
        ),
    }
    if request.method == "POST":
        identifier_fields = {
            "toggle_rule": "rule_id",
            "toggle_setup": "setup_id",
            "lock_period": "period_id",
            "unlock_period": "period_id",
        }
        if action not in forms_by_action and action not in identifier_fields:
            return refuse(request, "Ação de configuração inválida.", kind="unavailable")
        if identifier_field := identifier_fields.get(action):
            identifiers = request.POST.getlist(identifier_field)
            try:
                if len(identifiers) != 1:
                    raise ValueError
                uuid.UUID(identifiers[0])
            except ValueError:
                return refuse(
                    request,
                    "O item de configuração não é válido. Reabra a configuração da empresa "
                    "antes de tentar novamente. Nenhuma alteração foi salva.",
                    kind="unavailable",
                )
        configured: Any
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
                            created_by=cast(User, request.user),
                        )
                    else:
                        configured = cast("forms.ModelForm[models.Model]", form).save(commit=False)
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
                section_by_action = {
                    "financial_account": "contas-financeiras",
                    "ledger_account": "plano-contas",
                    "cost_center": "centros-custo",
                    "accounting_period": "periodos",
                    "reconciliation_rule": "regras-layouts",
                }
                return configuration_redirect(section_by_action[action])
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
            return configuration_redirect("regras-layouts")
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
                return refuse(request, "Item de configuração inválido.", kind="unavailable")
            configured = cast(
                Any,
                get_object_or_404(
                    setup_model,
                    id=request.POST.get("setup_id"),
                    organization=office,
                    company=selected_company,
                ),
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
            section_by_kind = {
                "financial_account": "contas-financeiras",
                "ledger_account": "plano-contas",
                "cost_center": "centros-custo",
                "layout": "regras-layouts",
            }
            return configuration_redirect(section_by_kind[setup_kind])
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
                period.locked_by = cast(User, request.user)
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
                return configuration_redirect("periodos")
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
                return configuration_redirect("periodos")
            else:
                return refuse(request, "Ação de configuração inválida.", kind="unavailable")

    financial_accounts_query = FinancialAccount.objects.filter(
        organization=office, company=selected_company
    ).order_by("name")
    ledger_accounts_query = LedgerAccount.objects.filter(
        organization=office, company=selected_company
    ).order_by("code")
    cost_centers_query = CostCenter.objects.filter(
        organization=office, company=selected_company
    ).order_by("code")
    accounting_periods_query = AccountingPeriod.objects.filter(
        organization=office, company=selected_company
    ).order_by("-starts_on")
    reconciliation_layouts_query = ReconciliationLayout.objects.filter(
        organization=office, company=selected_company
    ).order_by("kind", "name", "-version")
    reconciliation_rules_query = ReconciliationRule.objects.filter(
        organization=office, company=selected_company
    ).order_by("priority", "name")

    list_definitions = {
        "financial_accounts": (financial_accounts_query, "financial_page"),
        "ledger_accounts": (ledger_accounts_query, "ledger_page"),
        "cost_centers": (cost_centers_query, "cost_center_page"),
        "accounting_periods": (accounting_periods_query, "period_page"),
        "reconciliation_layouts": (reconciliation_layouts_query, "layout_page"),
        "reconciliation_rules": (reconciliation_rules_query, "rule_page"),
    }
    paginated_lists: dict[str, object] = {}
    for key, (queryset, parameter) in list_definitions.items():
        page = Paginator(queryset, 25).get_page(request.GET.get(parameter))
        params = request.GET.copy()
        params.pop(parameter, None)
        params["company"] = str(selected_company.id)
        paginated_lists[key] = list(page.object_list)
        paginated_lists[f"{key}_page"] = page
        paginated_lists[f"{key}_querystring"] = params.urlencode()

    ledger_account_count = ledger_accounts_query.filter(active=True, accepts_entries=True).count()
    financial_account_count = financial_accounts_query.filter(active=True).count()
    accounting_period_count = accounting_periods_query.count()
    locked_period_count = accounting_periods_query.filter(locked_at__isnull=False).count()
    active_rule_count = reconciliation_rules_query.filter(
        state=ReconciliationRule.State.ACTIVE
    ).count()
    active_layout_count = reconciliation_layouts_query.filter(active=True).count()
    if not ledger_account_count:
        setup_next_action = {
            "state": "blocked",
            "eyebrow": "COMECE PELO ESSENCIAL",
            "title": "Cadastre a primeira conta contábil",
            "description": (
                "Sem uma conta ativa que aceite lançamentos, a CICA não pode validar débitos "
                "e créditos desta empresa."
            ),
            "label": "Cadastrar conta contábil",
            "href": "#plano-contas-form",
            "section": "plano-contas",
        }
    elif not financial_account_count:
        setup_next_action = {
            "state": "recommended",
            "eyebrow": "PRÓXIMO PASSO RECOMENDADO",
            "title": "Vincule o banco antes de importar extratos",
            "description": (
                "CSV, XLSX e documentos gerais já podem ser revisados. Para OFX e extratos "
                "bancários, cadastre a conta que identifica a origem dos movimentos."
            ),
            "label": "Cadastrar conta financeira",
            "href": "#contas-financeiras-form",
            "section": "contas-financeiras",
        }
    else:
        setup_next_action = {
            "state": "ready",
            "eyebrow": "BASE ESSENCIAL PRONTA",
            "title": "A empresa pode iniciar uma importação",
            "description": (
                "Plano de contas e origem bancária estão disponíveis. Períodos, centros de "
                "custo e automações continuam opcionais e podem ser configurados quando "
                "necessários."
            ),
            "label": "Voltar e importar arquivos",
            "href": f"{reverse('hub:reconciliation')}#visao-geral",
            "section": "",
        }

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
            **paginated_lists,
            "reconciliation_setup_next_action": setup_next_action,
            "reconciliation_setup_status": {
                "financial_accounts": financial_account_count,
                "ledger_accounts": ledger_account_count,
                "cost_centers_required": CostCenter.objects.filter(
                    organization=office, company=selected_company, active=True, required=True
                ).exists(),
                "periods": accounting_period_count,
                "locked_periods": locked_period_count,
                "active_rules": active_rule_count,
                "active_layouts": active_layout_count,
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
    base_events = AuditEvent.objects.filter(
        organization=office, action__startswith=action_prefix
    ).select_related("actor")
    action_details = {
        "hub.reconciliation.source_uploaded": (
            "Arquivo recebido",
            "Importação",
            "Um arquivo entrou na fila de conciliação.",
        ),
        "hub.reconciliation.source_downloaded": (
            "Arquivo original baixado",
            "Consulta",
            "Uma cópia do arquivo de origem foi baixada.",
        ),
        "hub.reconciliation.source_previewed": (
            "Arquivo original visualizado",
            "Consulta",
            "A evidência de origem foi aberta para conferência.",
        ),
        "hub.reconciliation.ofx_imported": (
            "Extrato OFX importado",
            "Importação",
            "As transações do extrato foram registradas.",
        ),
        "hub.reconciliation.financial_account.created": (
            "Conta financeira cadastrada",
            "Configuração",
            "Uma conta financeira foi adicionada à empresa.",
        ),
        "hub.reconciliation.financial_account.state_changed": (
            "Situação da conta financeira alterada",
            "Configuração",
            "A disponibilidade da conta financeira mudou.",
        ),
        "hub.reconciliation.ledger_account.created": (
            "Conta contábil cadastrada",
            "Configuração",
            "Uma conta do plano contábil foi adicionada.",
        ),
        "hub.reconciliation.ledger_account.state_changed": (
            "Situação da conta contábil alterada",
            "Configuração",
            "A disponibilidade da conta contábil mudou.",
        ),
        "hub.reconciliation.cost_center.created": (
            "Centro de custo cadastrado",
            "Configuração",
            "Um centro de custo foi adicionado.",
        ),
        "hub.reconciliation.cost_center.state_changed": (
            "Situação do centro de custo alterada",
            "Configuração",
            "A disponibilidade do centro de custo mudou.",
        ),
        "hub.reconciliation.accounting_period.created": (
            "Período contábil cadastrado",
            "Configuração",
            "Um intervalo de controle foi adicionado.",
        ),
        "hub.reconciliation.period.locked": (
            "Período contábil bloqueado",
            "Configuração",
            "Alterações no intervalo passaram a ser impedidas.",
        ),
        "hub.reconciliation.period.unlocked": (
            "Período contábil reaberto",
            "Configuração",
            "O intervalo voltou a aceitar alterações.",
        ),
        "hub.reconciliation.reconciliation_rule.created": (
            "Regra de conciliação criada",
            "Automação",
            "Uma nova regra foi salva para a empresa.",
        ),
        "hub.reconciliation.rule.state_changed": (
            "Situação da regra alterada",
            "Automação",
            "A regra foi ativada ou desativada.",
        ),
        "hub.reconciliation.layout.state_changed": (
            "Situação do layout alterada",
            "Automação",
            "O layout foi ativado ou desativado.",
        ),
        "hub.reconciliation.rules_reapplication_requested": (
            "Reaplicação de regras solicitada",
            "Automação",
            "Os movimentos elegíveis voltaram à fila de regras.",
        ),
        "hub.reconciliation.movement_edited": (
            "Movimento revisado",
            "Revisão",
            "A classificação contábil do movimento foi alterada.",
        ),
        "hub.reconciliation.movement_ignored": (
            "Movimento ignorado",
            "Revisão",
            "O movimento saiu da fila de revisão.",
        ),
        "hub.reconciliation.movement_restored": (
            "Movimento restaurado",
            "Revisão",
            "O movimento voltou para a fila de revisão.",
        ),
        "hub.reconciliation.movements_ignored": (
            "Movimentos ignorados em lote",
            "Revisão",
            "Um conjunto de movimentos saiu da fila de revisão.",
        ),
        "hub.reconciliation.movements_returned_to_review": (
            "Movimentos devolvidos à revisão",
            "Revisão",
            "Um conjunto de movimentos voltou para revisão.",
        ),
        "hub.reconciliation.match_confirmed": (
            "Correspondência confirmada",
            "Conciliação",
            "Uma correspondência foi confirmada manualmente.",
        ),
        "hub.reconciliation.auto_confirmed": (
            "Correspondência automática confirmada",
            "Conciliação",
            "Uma correspondência segura foi confirmada pelo sistema.",
        ),
        "hub.reconciliation.reconciliation_confirmed": (
            "Conciliação confirmada",
            "Conciliação",
            "Movimento e lançamento foram vinculados.",
        ),
        "hub.reconciliation.reconciliation_undone": (
            "Conciliação desfeita",
            "Conciliação",
            "O vínculo foi removido e o valor liberado.",
        ),
        "hub.reconciliation.journal_approved": (
            "Lançamento aprovado",
            "Aprovação",
            "O lançamento ficou disponível para exportação.",
        ),
        "hub.reconciliation.export_created": (
            "Exportação contábil criada",
            "Exportação",
            "Um arquivo contábil foi preparado.",
        ),
        "hub.reconciliation.export_downloaded": (
            "Exportação contábil baixada",
            "Exportação",
            "O arquivo contábil foi baixado.",
        ),
        "hub.reconciliation.export_import_confirmed": (
            "Importação no Domínio confirmada",
            "Exportação",
            "A importação externa foi confirmada por uma pessoa.",
        ),
        "hub.reconciliation.export_integrity_failed": (
            "Integridade da exportação falhou",
            "Segurança",
            "O arquivo armazenado não correspondeu ao registro original.",
        ),
    }
    target_labels = {
        "hub.reconciliationsourcefile": "Arquivo de origem",
        "hub.bankstatementimport": "Extrato bancário",
        "hub.financialaccount": "Conta financeira",
        "hub.ledgeraccount": "Conta contábil",
        "hub.costcenter": "Centro de custo",
        "hub.accountingperiod": "Período contábil",
        "hub.reconciliationrule": "Regra",
        "hub.reconciliationlayout": "Layout",
        "hub.normalizedmovement": "Movimento",
        "hub.movementreconciliation": "Conciliação",
        "hub.journalentry": "Lançamento",
        "hub.accountingexport": "Exportação",
    }
    available_actions = list(
        base_events.order_by("action").values_list("action", flat=True).distinct()
    )
    events = base_events
    filter_errors: list[str] = []
    event_action = request.GET.get("action", "").strip()
    result_filter = request.GET.get("result", "all").strip()
    audit_query = request.GET.get("q", "").strip()
    date_from_raw = request.GET.get("date_from", "").strip()
    date_to_raw = request.GET.get("date_to", "").strip()
    date_from = parse_date(date_from_raw) if date_from_raw else None
    date_to = parse_date(date_to_raw) if date_to_raw else None
    if event_action:
        if event_action in available_actions:
            events = events.filter(action=event_action)
        else:
            filter_errors.append("A atividade escolhida não existe nesta trilha.")
    if result_filter == "success":
        events = events.filter(success=True)
    elif result_filter == "failure":
        events = events.filter(success=False)
    elif result_filter != "all":
        filter_errors.append("O resultado escolhido não é válido.")
    if len(audit_query) > 100:
        filter_errors.append("A busca deve ter no máximo 100 caracteres.")
    elif audit_query:
        matching_actions = [
            action
            for action, (title, category, _description) in action_details.items()
            if audit_query.casefold() in f"{title} {category}".casefold()
        ]
        events = events.filter(
            Q(actor__full_name__icontains=audit_query)
            | Q(actor__email__icontains=audit_query)
            | Q(target_id__icontains=audit_query)
            | Q(action__icontains=audit_query)
            | Q(action__in=matching_actions)
        )
    if date_from_raw and date_from is None:
        filter_errors.append("A data inicial não é válida.")
    if date_to_raw and date_to is None:
        filter_errors.append("A data final não é válida.")
    current_timezone = timezone.get_current_timezone()
    if date_from and date_to and date_from > date_to:
        filter_errors.append("A data inicial deve ser anterior ou igual à data final.")
    elif date_from and date_to:
        events = events.filter(
            occurred_at__gte=timezone.make_aware(
                datetime.combine(date_from, time.min), current_timezone
            ),
            occurred_at__lte=timezone.make_aware(
                datetime.combine(date_to, time.max), current_timezone
            ),
        )
    elif date_from:
        events = events.filter(
            occurred_at__gte=timezone.make_aware(
                datetime.combine(date_from, time.min), current_timezone
            )
        )
    elif date_to:
        events = events.filter(
            occurred_at__lte=timezone.make_aware(
                datetime.combine(date_to, time.max), current_timezone
            )
        )
    if filter_errors:
        events = events.none()
    reconciliation_audit_page = Paginator(events.order_by("-occurred_at"), 50).get_page(
        request.GET.get("page")
    )
    displayed_events = list(reconciliation_audit_page.object_list)
    metadata_labels = {
        "reason": "Motivo",
        "state": "Nova situação",
        "active": "Ativo",
        "transactions": "Transações",
        "entries": "Lançamentos",
        "entry_count": "Lançamentos",
        "line_count": "Linhas",
        "bulk_size": "Movimentos no lote",
        "revision": "Revisão",
        "invalidated_entries": "Lançamentos invalidados",
        "origin": "Origem",
        "kind": "Tipo de arquivo",
        "size_bytes": "Tamanho",
        "amount_cents": "Valor conciliado",
    }

    def present_metadata(event: AuditEvent) -> list[SimpleNamespace]:
        presented: list[SimpleNamespace] = []
        for key, label in metadata_labels.items():
            if key not in event.metadata:
                continue
            value = event.metadata[key]
            if key == "amount_cents" and isinstance(value, int):
                amount = (
                    f"{Decimal(value) / 100:,.2f}".replace(",", "X")
                    .replace(".", ",")
                    .replace("X", ".")
                )
                value = f"R$ {amount}"
            elif key == "size_bytes" and isinstance(value, int):
                value = f"{value / 1024:.1f} KB" if value >= 1024 else f"{value} bytes"
            elif isinstance(value, bool):
                value = "Sim" if value else "Não"
            presented.append(SimpleNamespace(label=label, value=value))
        return presented

    for event in displayed_events:
        title, category, description = action_details.get(
            event.action,
            ("Evento de conciliação", "Outros", "Uma atividade foi registrada nesta trilha."),
        )
        event.display_title = title
        event.display_category = category
        event.display_description = description
        event.display_target = target_labels.get(event.target_type, "Registro relacionado")
        event.display_metadata = present_metadata(event)
    audit_totals = base_events.aggregate(
        total=Count("id"), failures=Count("id", filter=Q(success=False))
    )
    reconciliation_audit_query_params = request.GET.copy()
    reconciliation_audit_query_params.pop("page", None)
    context.update(
        {
            "page_title": "Auditoria da conciliação",
            "reconciliation_audit_events": displayed_events,
            "reconciliation_audit_page": reconciliation_audit_page,
            "reconciliation_audit_querystring": reconciliation_audit_query_params.urlencode(),
            "reconciliation_audit_total": reconciliation_audit_page.paginator.count,
            "reconciliation_audit_all_total": audit_totals["total"],
            "reconciliation_audit_failure_total": audit_totals["failures"],
            "reconciliation_audit_actions": [
                SimpleNamespace(
                    value=action,
                    label=action_details.get(action, ("Evento de conciliação", "Outros", ""))[0],
                )
                for action in sorted(
                    available_actions,
                    key=lambda item: action_details.get(
                        item, ("Evento de conciliação", "Outros", "")
                    )[0],
                )
            ],
            "reconciliation_audit_action": event_action,
            "reconciliation_audit_result": result_filter,
            "reconciliation_audit_search": audit_query,
            "reconciliation_audit_date_from": date_from_raw,
            "reconciliation_audit_date_to": date_to_raw,
            "reconciliation_audit_filter_errors": filter_errors,
            "reconciliation_audit_has_filters": bool(
                event_action
                or audit_query
                or date_from_raw
                or date_to_raw
                or result_filter != "all"
            ),
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
    if office.is_demo:
        return refuse(request, "A demonstração não recebe arquivos.")
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
                "can_upload_reconciliation": True,
                "imports": BankStatementImport.objects.filter(
                    organization=office, company__in=companies
                ).select_related("company")[:20],
                "matches": [],
                "match_total": 0,
                "match_search": "",
                "match_status": "attention",
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
                "can_upload_reconciliation": True,
                "imports": BankStatementImport.objects.filter(
                    organization=office, company__in=companies
                ).select_related("company")[:20],
                "matches": [],
                "match_total": 0,
                "match_search": "",
                "match_status": "attention",
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
        filename = upload.name
        if not filename:
            failures.append("Arquivo sem nome não pode ser processado.")
            continue
        try:
            content = upload.read()
            source, run, was_created = create_source_file(
                organization=office,
                company=form.cleaned_data["company"],
                filename=filename,
                content=content,
                origin=form.cleaned_data["origin"],
                actor=request.user,
                physical_batch=form.cleaned_data.get("physical_batch", ""),
                financial_account=form.cleaned_data.get("financial_account"),
                request=request,
            )
            if (
                source.kind == ReconciliationSourceFile.Kind.OFX
                and source.origin == ReconciliationSourceFile.Origin.BANK_STATEMENT
            ):
                # The OFX x Domínio queue reads bank statements; one upload feeds both
                # views. import_ofx is idempotent by content hash, and a parse failure
                # here is already reported by the processing run of the same file.
                with suppress(OfxParseError):
                    import_ofx(
                        organization=office,
                        company=form.cleaned_data["company"],
                        filename=filename,
                        content=content,
                        actor=request.user,
                        request=request,
                    )
            if was_created:
                from apps.hub.tasks import process_reconciliation_run

                transaction.on_commit(partial(process_reconciliation_run.delay, str(run.id)))
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
    if created or duplicates:
        return redirect(f"{reverse('hub:reconciliation')}#processamentos")
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
            created_by=cast(User, request.user),
        )
        from apps.hub.tasks import process_reconciliation_run

        transaction.on_commit(partial(process_reconciliation_run.delay, str(retry.id)))
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
            created_by=cast(User, request.user),
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

        transaction.on_commit(partial(process_reconciliation_run.delay, str(reapplication.id)))
        messages.success(
            request,
            "Reaplicação criada. Revisões manuais, conciliações e lançamentos serão preservados.",
        )
    else:
        return refuse(request, "Ação de processamento inválida.", kind="unavailable")
    sync_reconciliation_activity(run.source_file_id)
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
        return refuse(request, "Este formato não usa mapeamento de colunas.", kind="unavailable")
    try:
        preview = preview_tabular(source)
    except ReconciliationError as exc:
        return refuse(request, str(exc), kind="unavailable")
    mapping_field_definitions = (
        ("date", "Data", True),
        ("amount", "Valor com sinal", False),
        ("debit", "Débito / saída", False),
        ("credit", "Crédito / entrada", False),
        ("description", "Histórico", True),
        ("document", "Documento", False),
        ("counterparty", "Contraparte", False),
    )
    mapping_values = {
        field: str(preview["mapping"].get(field, ""))
        for field, _label, _required in mapping_field_definitions
    }
    mapping_name = source.original_filename.rsplit(".", 1)[0][:120]
    mapping_errors: list[tuple[str, str]] = []
    if request.method == "POST":
        if not context["support_can_mutate"] or not _can_manage_reconciliation(context):
            return refuse(request, "Seu perfil pode consultar, mas não salvar layouts.")
        mapping_name = request.POST.get("name", "").strip()[:120]
        mapping_values = {
            field: request.POST.get(f"map_{field}", "").strip()
            for field, _label, _required in mapping_field_definitions
        }
        submitted_mapping = {field: value for field, value in mapping_values.items() if value}
        if not mapping_name:
            mapping_errors.append(("layout-name", "Dê um nome para reconhecer este layout."))
        if not mapping_values["date"]:
            mapping_errors.append(("map-date", "Escolha a coluna que contém a data."))
        if not mapping_values["description"]:
            mapping_errors.append(("map-description", "Escolha a coluna que contém o histórico."))
        has_signed_amount = bool(mapping_values["amount"])
        has_split_amount = bool(mapping_values["debit"] or mapping_values["credit"])
        if not has_signed_amount and not has_split_amount:
            mapping_errors.append(
                (
                    "map-amount",
                    "Escolha Valor com sinal ou pelo menos uma coluna de débito/crédito.",
                )
            )
        elif has_signed_amount and has_split_amount:
            mapping_errors.append(
                (
                    "map-amount",
                    "Use uma única estratégia: Valor com sinal ou Débito/Crédito.",
                )
            )
        duplicate_columns = {
            value
            for value in submitted_mapping.values()
            if list(submitted_mapping.values()).count(value) > 1
        }
        if duplicate_columns:
            for field, value in submitted_mapping.items():
                if value in duplicate_columns:
                    mapping_errors.append(
                        (f"map-{field}", f"A coluna “{value}” foi escolhida mais de uma vez.")
                    )
        try:
            mapping = submitted_mapping or json.loads(request.POST.get("mapping", "{}"))
            if not isinstance(mapping, dict):
                raise ValueError
        except (ValueError, json.JSONDecodeError):
            mapping_errors.append(("mapping-error-summary", "O mapeamento enviado não é válido."))
        else:
            if mapping_errors:
                mapping = {}
            try:
                if mapping:
                    layout = save_layout(
                        source=source,
                        name=mapping_name,
                        configuration={"mapping": mapping, "sheet": preview.get("sheet", "")},
                        actor=request.user,
                    )
                    runnable_runs = prepare_run_for_layout(source=source, layout=layout)
            except ReconciliationError as exc:
                mapping_errors.append(("mapping-error-summary", str(exc)))
            else:
                if not mapping:
                    runnable_runs = []
                for run in runnable_runs:
                    from apps.hub.tasks import process_reconciliation_run

                    transaction.on_commit(partial(process_reconciliation_run.delay, str(run.id)))
                if mapping:
                    if runnable_runs:
                        messages.success(
                            request,
                            (
                                f"Layout {layout.name} v{layout.version} salvo e "
                                "processamento iniciado."
                            ),
                        )
                    else:
                        messages.success(
                            request,
                            (
                                f"Layout {layout.name} v{layout.version} salvo para arquivos "
                                "futuros. Nenhum processamento foi iniciado agora."
                            ),
                        )
                    return redirect(f"{reverse('hub:reconciliation')}#processamentos")
    field_errors: dict[str, list[str]] = {}
    for target, message in mapping_errors:
        field_errors.setdefault(target, []).append(message)
    context.update(
        {
            "page_title": "Mapear arquivo",
            "mapping_source": source,
            "mapping_preview": preview,
            "mapping_name": mapping_name,
            "mapping_errors": mapping_errors,
            "mapping_fields": tuple(
                (
                    field,
                    label,
                    required,
                    mapping_values.get(field, ""),
                    field_errors.get(f"map-{field}", []),
                )
                for field, label, required in mapping_field_definitions
            ),
            "mapping_name_errors": field_errors.get("layout-name", []),
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
        return refuse(
            request,
            "Ações em lote aceitam até 50 movimentos por vez.",
            kind="unavailable",
        )
    action = request.POST.get("action", "")
    if action not in {"ignore", "review"}:
        return refuse(request, "Escolha uma ação em lote válida.", kind="unavailable")
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
            return refuse(
                request,
                "Um ou mais movimentos não estão mais disponíveis para você.",
                kind="unavailable",
            )
        if any(
            movement.journal_entries.filter(state=JournalEntry.State.EXPORTED).exists()
            for movement in movements
        ):
            return refuse(
                request,
                "Movimentos exportados exigem retificação auditada.",
                kind="unavailable",
            )
        new_state = (
            NormalizedMovement.ReviewState.IGNORED
            if action == "ignore"
            else NormalizedMovement.ReviewState.PENDING
        )
        for movement in movements:
            movement.review_state = new_state
            movement.revision += 1
            movement.edited_by = cast(User, request.user)
            movement.save(update_fields=["review_state", "revision", "edited_by", "updated_at"])
            invalidated_entries = movement.journal_entries.filter(
                state__in=[JournalEntry.State.DRAFT, JournalEntry.State.APPROVED]
            ).update(state=JournalEntry.State.INVALID, updated_at=timezone.now())
            sync_reconciliation_activity(movement.source_file_id)
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
            movement.edited_by = cast(User, request.user)
            movement.save(update_fields=["review_state", "revision", "edited_by", "updated_at"])
            invalidated_entries = movement.journal_entries.filter(
                state__in=[JournalEntry.State.DRAFT, JournalEntry.State.APPROVED]
            ).update(state=JournalEntry.State.INVALID, updated_at=timezone.now())
            sync_reconciliation_activity(movement.source_file_id)
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
                journal_entry = create_journal_entry_from_movement(
                    movement=movement, actor=cast(User, request.user)
                )
            except ReconciliationError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, f"Lançamento {journal_entry.id} gerado como rascunho.")
            return redirect("hub:reconciliation-movement", movement_id=movement.id)
        if action == "save_rule":
            try:
                rule = save_rule_from_movement(movement=movement, actor=cast(User, request.user))
            except ReconciliationError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, f"Regra {rule.name} salva e ativada para esta empresa.")
            return redirect("hub:reconciliation-movement", movement_id=movement.id)
        if action == "approve_entry":
            draft_entry = movement.journal_entries.exclude(state=JournalEntry.State.INVALID).first()
            if draft_entry is None:
                messages.error(request, "Gere o lançamento antes de aprová-lo.")
            else:
                try:
                    approve_journal_entry(
                        entry=draft_entry, actor=cast(User, request.user), request=request
                    )
                except ReconciliationError as exc:
                    messages.error(request, str(exc))
                else:
                    messages.success(request, "Lançamento aprovado para exportação.")
            return redirect("hub:reconciliation-movement", movement_id=movement.id)
        if action == "confirm_reconciliation":
            try:
                entry_id = request.POST.get("entry_id")
                if not entry_id:
                    raise ReconciliationError("Escolha um lançamento para confirmar a conciliação.")
                confirmed_entry = JournalEntry.objects.get(
                    id=entry_id,
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
                    entry=confirmed_entry,
                    amount_cents=amount_cents,
                    evidence={"note": evidence_note, "source": movement.source_reference},
                    actor=cast(User, request.user),
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
            undo_normalized_reconciliation(
                reconciliation=reconciliation, actor=cast(User, request.user)
            )
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
                movement.edited_by = cast(User, request.user)
                movement.save()
                invalidated_entries = movement.journal_entries.filter(
                    state__in=[JournalEntry.State.DRAFT, JournalEntry.State.APPROVED]
                ).update(state=JournalEntry.State.INVALID, updated_at=timezone.now())
                sync_reconciliation_activity(movement.source_file_id)
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
    candidate_query_params = request.GET.copy()
    candidate_query_params.pop("candidate_page", None)
    candidate_page = Paginator(
        candidate_query.order_by("-occurred_on", "-created_at"), 25
    ).get_page(request.GET.get("candidate_page"))
    candidate_entries = list(candidate_page.object_list)
    movement.amount_brl = Decimal(abs(movement.amount_cents)) / 100  # type: ignore[attr-defined]
    decision_params = request.GET.copy()
    decision_params.pop("decision_page", None)
    decision_page = Paginator(
        ReconciliationDecision.objects.filter(
            organization=office,
            reconciliation__movement=movement,
            reconciliation__organization=office,
            reconciliation__entry__organization=office,
            reconciliation__entry__company=movement.company,
        )
        .select_related("actor", "reconciliation__entry")
        .order_by("-created_at", "-pk"),
        20,
    ).get_page(request.GET.get("decision_page"))
    for decision in decision_page:
        decision.amount_brl = Decimal(decision.amount_cents) / 100  # type: ignore[attr-defined]
        decision.evidence_text = json.dumps(  # type: ignore[attr-defined]
            decision.evidence, ensure_ascii=False, indent=2
        )
    reconciliations = list(
        movement.reconciliations.filter(state=MovementReconciliation.State.CONFIRMED)
        .select_related("entry")
        .order_by("created_at")
    )
    remaining_cents = abs(movement.amount_cents) - sum(
        item.amount_cents for item in reconciliations
    )
    for reconciliation in reconciliations:
        reconciliation.amount_brl = Decimal(reconciliation.amount_cents) / 100  # type: ignore[attr-defined]
    allocated_cents = sum(item.amount_cents for item in reconciliations)
    movement.allocated_cents = allocated_cents  # type: ignore[attr-defined]
    movement.remaining_cents = remaining_cents  # type: ignore[attr-defined]
    movement.allocated_brl = Decimal(allocated_cents) / 100  # type: ignore[attr-defined]
    movement.remaining_brl = Decimal(remaining_cents) / 100  # type: ignore[attr-defined]
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
        if available == remaining_cents:
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
            allocation_limit_cents = min(available, remaining_cents)
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
    suggestions.sort(
        key=lambda item: (
            -cast(int, item["score"]),
            str(cast(JournalEntry, item["entry"]).id),
        )
    )
    current_journal_entry = movement.journal_entries.exclude(
        state=JournalEntry.State.INVALID
    ).first()
    missing_entry_fields = []
    if movement.occurred_on is None:
        missing_entry_fields.append("data")
    if not movement.debit_account_code:
        missing_entry_fields.append("conta de débito")
    if not movement.credit_account_code:
        missing_entry_fields.append("conta de crédito")
    if movement.amount_cents == 0:
        missing_entry_fields.append("valor diferente de zero")
    if movement.review_state == NormalizedMovement.ReviewState.IGNORED:
        movement_workflow = {
            "state": "ignored",
            "eyebrow": "MOVIMENTO IGNORADO",
            "title": "Restaurar para voltar à revisão",
            "description": "O movimento não gera lançamento enquanto estiver ignorado.",
            "label": "Ver opção de restauração",
            "href": "#movement-secondary-actions",
        }
    elif current_journal_entry and current_journal_entry.state == JournalEntry.State.EXPORTED:
        movement_workflow = {
            "state": "exported",
            "eyebrow": "CONCLUÍDO",
            "title": "Lançamento já incluído em uma exportação",
            "description": "Alterações posteriores exigem retificação auditada.",
            "label": "Voltar aos movimentos",
            "href": f"{reverse('hub:reconciliation')}#movimentos",
        }
    elif current_journal_entry and current_journal_entry.state == JournalEntry.State.APPROVED:
        movement_workflow = {
            "state": "approved",
            "eyebrow": "PRONTO PARA EXPORTAR",
            "title": "Revisão e lançamento aprovados",
            "description": "O lançamento entrará no próximo arquivo desta empresa e período.",
            "label": "Ver exportações",
            "href": f"{reverse('hub:reconciliation')}#exportacoes",
        }
    elif current_journal_entry and current_journal_entry.state == JournalEntry.State.DRAFT:
        movement_workflow = {
            "state": "draft",
            "eyebrow": "PRÓXIMO PASSO",
            "title": "Validar e aprovar o lançamento",
            "description": "Confira as contas e o histórico antes de liberar para exportação.",
            "label": "Ir para aprovação",
            "href": "#movement-entry-action",
        }
    elif missing_entry_fields:
        movement_workflow = {
            "state": "incomplete",
            "eyebrow": "PRÓXIMO PASSO",
            "title": "Completar os dados obrigatórios",
            "description": "Falta informar " + ", ".join(missing_entry_fields) + ".",
            "label": "Completar revisão",
            "href": "#movement-review-form",
        }
    else:
        movement_workflow = {
            "state": "reviewed",
            "eyebrow": "PRÓXIMO PASSO",
            "title": "Gerar o lançamento rascunho",
            "description": "Os dados mínimos estão preenchidos; gere e confira o lançamento.",
            "label": "Gerar lançamento",
            "href": "#movement-entry-action",
        }
    context.update(
        {
            "page_title": "Revisar movimento",
            "can_review_movement": bool(context["support_can_mutate"])
            and _can_manage_reconciliation(context),
            "movement": movement,
            "movement_form": form,
            "journal_entry": current_journal_entry,
            "movement_workflow": movement_workflow,
            "reconciliation_candidates": suggestions,
            "reconciliation_candidate_page": candidate_page,
            "reconciliation_candidate_querystring": candidate_query_params.urlencode(),
            "reconciliation_candidate_total": candidate_page.paginator.count,
            "movement_reconciliations": reconciliations,
            "reconciliation_decision_page": decision_page,
            "reconciliation_decision_querystring": decision_params.urlencode(),
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
        state__in=[AccountingExport.State.READY, AccountingExport.State.CONFIRMED],
    )
    content_name = export.content.name if export.content else ""
    if not content_name or not export.content.storage.exists(content_name):
        raise Http404("Arquivo de exportação indisponível.")
    digest = hashlib.sha256()
    export.content.open("rb")
    for chunk in export.content.chunks():
        digest.update(chunk)
    export.content.close()
    if not secrets.compare_digest(digest.hexdigest(), export.content_hash):
        record_event(
            action="hub.reconciliation.export_integrity_failed",
            actor=request.user,
            organization=office,
            target=export,
            request=request,
            metadata={"expected_hash": export.content_hash[:12]},
        )
        raise Http404("Arquivo de exportação indisponível.")
    record_event(
        action="hub.reconciliation.export_downloaded",
        actor=request.user,
        organization=office,
        target=export,
        request=request,
        metadata={"hash": export.content_hash[:12]},
    )
    response = FileResponse(
        export.content.open("rb"),
        as_attachment=True,
        filename=PurePath(export.content.name or "exportacao-contabil").name,
    )
    response["X-Content-Type-Options"] = "nosniff"
    return response


@office_required
@require_http_methods(["POST"])
def reconciliation_export_confirm(request: HttpRequest, export_id: str) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.RECONCILIATION))
    if blocked:
        return blocked
    if not context["support_can_mutate"] or not _can_manage_reconciliation(context):
        return refuse(request, "Seu perfil pode consultar, mas não confirmar importações.")
    if not settings.RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED:
        return refuse(
            request,
            "A confirmação continua bloqueada até a homologação real do layout Domínio.",
            kind="unavailable",
        )
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    with transaction.atomic():
        export = get_object_or_404(
            AccountingExport.objects.select_for_update(),
            id=export_id,
            organization=office,
            company__in=companies,
            state__in=[AccountingExport.State.READY, AccountingExport.State.CONFIRMED],
        )
        if export.state == AccountingExport.State.CONFIRMED:
            messages.info(request, "Esta importação já estava confirmada.")
            return redirect(f"{reverse('hub:reconciliation')}#exportacoes")
        posted_hash = request.POST.get("content_hash", "")
        if (
            request.POST.get("confirm_import") != "yes"
            or not posted_hash
            or not secrets.compare_digest(posted_hash, export.content_hash)
        ):
            messages.error(request, "Confirme a importação do arquivo e o hash exibido.")
            return redirect(f"{reverse('hub:reconciliation')}#exportacoes")
        content_name = export.content.name if export.content else ""
        if not content_name or not export.content.storage.exists(content_name):
            messages.error(request, "O arquivo original não está disponível; nada foi confirmado.")
            return redirect(f"{reverse('hub:reconciliation')}#exportacoes")
        digest = hashlib.sha256()
        export.content.open("rb")
        for chunk in export.content.chunks():
            digest.update(chunk)
        export.content.close()
        if not secrets.compare_digest(digest.hexdigest(), export.content_hash):
            record_event(
                action="hub.reconciliation.export_integrity_failed",
                actor=request.user,
                organization=office,
                target=export,
                request=request,
                metadata={"expected_hash": export.content_hash[:12]},
            )
            messages.error(request, "O arquivo armazenado diverge do hash; nada foi confirmado.")
            return redirect(f"{reverse('hub:reconciliation')}#exportacoes")
        export.state = AccountingExport.State.CONFIRMED
        export.confirmed_at = timezone.now()
        export.confirmed_by = cast(User, request.user)
        export.save(update_fields=["state", "confirmed_at", "confirmed_by", "updated_at"])
        record_event(
            action="hub.reconciliation.export_import_confirmed",
            actor=request.user,
            organization=office,
            target=export,
            request=request,
            metadata={"hash": export.content_hash[:12], "entry_count": len(export.entry_ids)},
        )
    messages.success(request, "Importação no Domínio confirmada e registrada na auditoria.")
    return redirect(f"{reverse('hub:reconciliation')}#exportacoes")


@office_required
def reform(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.REFORM))
    if blocked:
        return blocked
    source = request.GET.get("fonte", "")
    search_term = request.GET.get("q", "").strip()[:100]
    relevance = request.GET.get("relevancia", "")
    period = request.GET.get("periodo", "")
    valid_periods = {"7": 7, "30": 30, "90": 90}
    if period not in valid_periods:
        period = ""
    period_start = timezone.now() - timedelta(days=valid_periods[period]) if period else None
    valid_sources = set(ReformAlert.Source.values)
    valid_relevance = {ReformAlert.Relevance.REFORM, ReformAlert.Relevance.FISCAL}
    if source not in valid_sources:
        source = ""
    if relevance not in valid_relevance:
        relevance = ""
    radar_query_params = request.GET.copy()
    radar_query_params.clear()
    if search_term:
        radar_query_params["q"] = search_term
    if source:
        radar_query_params["fonte"] = source
    if relevance:
        radar_query_params["relevancia"] = relevance
    if period:
        radar_query_params["periodo"] = period
    office = cast(Organization, context["office"])
    membership = context["membership"]
    can_request_analysis = (
        isinstance(membership, Membership)
        and membership.role not in {Membership.Role.AUDITOR, Membership.Role.BILLING}
        and bool(context["support_can_mutate"])
    )
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
        if period_start is not None:
            demo_alerts = [
                alert
                for alert in demo_alerts
                if alert.published_at and alert.published_at >= period_start
            ]
        demo_alert_page = Paginator(demo_alerts, 50).get_page(request.GET.get("page"))
        last_success = timezone.now() - timedelta(hours=3)
        demo_statuses = {
            value: SimpleNamespace(last_success_at=last_success, last_error="")
            for value in ReformAlert.Source.values
        }
        context.update(
            {
                "page_title": "Radar da Reforma Tributária",
                "alerts": list(demo_alert_page.object_list),
                "alert_page": demo_alert_page,
                "alert_querystring": radar_query_params.urlencode(),
                "alert_total": demo_alert_page.paginator.count,
                "radar_search": search_term,
                "selected_source": source,
                "selected_relevance": relevance,
                "selected_period": period,
                "sources": ReformAlert.Source.choices,
                "relevances": [
                    (ReformAlert.Relevance.REFORM, ReformAlert.Relevance.REFORM.label),
                    (ReformAlert.Relevance.FISCAL, ReformAlert.Relevance.FISCAL.label),
                ],
                "source_health": [
                    (value, label, demo_statuses[value])
                    for value, label in ReformAlert.Source.choices
                ],
                "radar_source_has_error": False,
                "radar_can_request_analysis": False,
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
    if period_start is not None:
        alerts = alerts.filter(published_at__gte=period_start)
    reform_alert_page = Paginator(alerts, 50).get_page(request.GET.get("page"))
    statuses_by_source = {status.source: status for status in ReformSourceStatus.objects.all()}
    context.update(
        {
            "page_title": "Radar da Reforma Tributária",
            "alerts": list(reform_alert_page.object_list),
            "alert_page": reform_alert_page,
            "alert_querystring": radar_query_params.urlencode(),
            "alert_total": reform_alert_page.paginator.count,
            "radar_search": search_term,
            "selected_source": source,
            "selected_relevance": relevance,
            "selected_period": period,
            "sources": ReformAlert.Source.choices,
            "relevances": [
                (ReformAlert.Relevance.REFORM, ReformAlert.Relevance.REFORM.label),
                (ReformAlert.Relevance.FISCAL, ReformAlert.Relevance.FISCAL.label),
            ],
            "source_health": [
                (value, label, statuses_by_source.get(value))
                for value, label in ReformAlert.Source.choices
            ],
            "radar_source_has_error": any(
                bool(status.last_error) for status in statuses_by_source.values()
            ),
            "radar_can_request_analysis": can_request_analysis,
            "radar_demo": False,
        }
    )
    return render(request, "hub/reform.html", context)


@office_required
@require_http_methods(["GET", "POST"])
def reform_analysis(request: HttpRequest, alert_id: uuid.UUID) -> HttpResponse:
    from apps.hub.forms import ReformAnalysisForm
    from apps.hub.reform_activities import request_reform_analysis

    context, blocked = _module_page_context(request, definition(ProductModule.Code.REFORM))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    membership = context["membership"]
    if office.is_demo or is_nfse_only_subscription(context):
        raise Http404
    alert = get_object_or_404(ReformAlert, pk=alert_id)
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    can_request = (
        isinstance(membership, Membership)
        and membership.role not in {Membership.Role.AUDITOR, Membership.Role.BILLING}
        and bool(context["support_can_mutate"])
    )
    if isinstance(membership, Membership) and membership.role not in {
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
    }:
        ids = [
            grant.company_id
            for grant in CompanyAccessGrant.objects.filter(
                organization=office,
                membership=membership,
                is_active=True,
            )
            if ProductModule.Code.REFORM in grant.modules
        ]
        companies = companies.filter(pk__in=ids)
    form = ReformAnalysisForm(request.POST if request.method == "POST" else None)
    form.fields["company"].queryset = companies  # type: ignore[attr-defined]
    if request.method == "POST":
        if not can_request:
            return refuse(request, "Este perfil permite apenas consulta do Radar.")
        if form.is_valid():
            assert isinstance(membership, Membership)
            try:
                activity = request_reform_analysis(
                    alert_id=alert.pk,
                    company_id=form.cleaned_data["company"].pk,
                    membership=membership,
                    actor=cast(User, request.user),
                    reason=form.cleaned_data["reason"],
                )
            except (PermissionDenied, ValidationError) as exc:
                form.add_error(None, str(exc))
            else:
                return redirect("hub:activity-detail", activity_id=activity.pk)
    context.update(
        {
            "page_title": "Analisar publicação do Radar",
            "radar_alert": alert,
            "analysis_form": form,
            "can_request_analysis": can_request,
            "radar_source_url": alert.source_url
            if (
                urlparse(alert.source_url).scheme == "https"
                and urlparse(alert.source_url).netloc == "www.gov.br"
            )
            else "",
            "radar_activity_page": Paginator(
                OperationalActivity.objects.filter(
                    organization=office,
                    company__in=companies,
                    source_reform_alert=alert,
                )
                .select_related("company")
                .order_by("company__name", "pk"),
                20,
            ).get_page(request.GET.get("page")),
        }
    )
    return render(request, "hub/reform_analysis.html", context, status=400 if form.errors else 200)


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
    item.reviewed_by = cast(User, request.user) if item.status != base_status else None
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
    mailbox_rows: list[MailboxPresentation] = [
        present_mailbox(mailbox, poll_enabled=settings.TRIAGE_EMAIL_POLL_ENABLED)
        for mailbox in mailboxes
    ]
    for mailbox in mailboxes:
        mailbox.operation_form = MailboxOperationForm(mailbox=mailbox)  # type: ignore[attr-defined]
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
    filtered_queue: list[TriageItem] | QuerySet[TriageItem]
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
        query_filtered_queue = queue.filter(status=selected_status) if selected_status else queue
        if queue_search:
            query_filtered_queue = query_filtered_queue.filter(
                Q(original_name__icontains=queue_search)
                | Q(company__name__icontains=queue_search)
                | Q(company__dominio_code__icontains=queue_search)
                | Q(mailbox__address__icontains=queue_search)
            )
        filtered_queue = query_filtered_queue.order_by("-created_at", "-pk")
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
    context["destination_form"] = DestinationProfileForm(
        profile=cast(DestinationProfile | None, context["destination_profile"])
    )
    # A Windows root is only trustworthy with the agent behind it: show the last signal
    # and the last confirmed write, not just the path someone typed.
    context["destination_agent"] = (
        EdgeAgent.objects.filter(organization=office, status=EdgeAgent.Status.ACTIVE)
        .order_by("-last_seen_at")
        .first()
    )
    context["destination_agent_online"] = EdgeAgent.objects.filter(
        organization=office,
        status=EdgeAgent.Status.ACTIVE,
        last_seen_at__gte=timezone.now() - timedelta(minutes=5),
    ).exists()
    context["destination_last_write"] = (
        AgentFileJob.objects.filter(organization=office, status=AgentFileJob.Status.DONE)
        .order_by("-completed_at")
        .first()
    )
    context["destination_failed_write"] = (
        AgentFileJob.objects.filter(organization=office, status=AgentFileJob.Status.FAILED)
        .order_by("-completed_at", "-created_at")
        .first()
    )
    return context, None


@office_required
@require_http_methods(["POST"])
def triage_oauth_app_save(request: HttpRequest, provider: str) -> HttpResponse:
    context, blocked = _triage_page_context(request)
    if blocked:
        return blocked
    if cast(Organization, context["office"]).is_demo:
        return refuse(
            request,
            "A demonstração fictícia não aceita aplicativos ou caixas reais.",
            kind="unavailable",
        )
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
    if cast(Organization, context["office"]).is_demo:
        return refuse(
            request,
            "A demonstração fictícia não testa servidores IMAP reais.",
            kind="unavailable",
        )
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
    if cast(Organization, context["office"]).is_demo:
        return refuse(
            request,
            "A demonstração fictícia não solicita autorização de e-mail real.",
            kind="unavailable",
        )
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
    if cast(Organization, context["office"]).is_demo:
        return refuse(request, "A demonstração não configura caixas externas.", kind="unavailable")
    if not _can_manage_collaborators(context):
        return refuse(request, "Somente o administrador configura a leitura da caixa.")
    office = cast(Organization, context["office"])
    mailbox = get_object_or_404(Mailbox, organization=office, id=mailbox_id)
    form = MailboxOperationForm(request.POST, mailbox=mailbox)
    if not form.is_valid():
        for row in cast(list[MailboxPresentation], context["mailbox_rows"]):
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
        for row in cast(list[MailboxPresentation], context["mailbox_rows"]):
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
    if cast(Organization, context["office"]).is_demo:
        return refuse(
            request,
            "A demonstração não altera o destino do escritório.",
            kind="unavailable",
        )
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
        ).filter(item_scope),
        organization=office,
        id=item_id,
    )
    visitor = is_demo_visitor(request, office)
    if visitor:
        _demo_triage_for_view(request, item)
    if request.method == "POST":
        decision = request.POST.get("decision", "")
        if not context["support_can_mutate"] or (
            item.company is None and decision not in {"update_fields", "reject"}
        ):
            return refuse(request, "Este perfil não pode decidir o destino deste arquivo.")
        success_message = "Decisão registrada com evidência no histórico do arquivo."
        try:
            if decision == "update_fields":
                if visitor:
                    raise ValidationError("Na demonstração, os dados do anexo são fixos.")
                review_form = TriageFieldsForm(
                    request.POST, organization=office, companies=context["companies"]
                )
                if not review_form.is_valid():
                    raise ValidationError(
                        next(iter(review_form.errors.values()))[0]
                    )
                update_review_fields(
                    item=item,
                    actor=cast(User, request.user),
                    company=review_form.cleaned_data["company"],
                    document_type=review_form.cleaned_data["document_type"],
                    period_label=review_form.cleaned_data["period_label"],
                    counterparty_token=review_form.cleaned_data["counterparty_token"],
                    final_name=review_form.cleaned_data["final_name"],
                    request=request,
                )
                messages.success(request, "Dados do arquivo atualizados.")
                return detail_redirect(request, "hub:triage-item", item_id=item.id)
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
    triage_history_events = []
    triage_history_page = None
    triage_history_total = 0
    triage_history_query_params = request.GET.copy()
    triage_history_query_params.pop("history_page", None)
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
        triage_history_total = len(demo_history)
    else:
        triage_history_page = Paginator(
            item.events.select_related("actor").order_by("created_at"), 20
        ).get_page(request.GET.get("history_page"))
        triage_history_events = list(triage_history_page.object_list)
        triage_history_total = triage_history_page.paginator.count
    context.update(
        {
            "page_title": "Arquivo em triagem",
            "item": item,
            "triage_field_rows": [
                (field, (item.ai_fields.get(label) or {}).get("evidencia", ""))
                for field, label in zip(
                    TriageFieldsForm(
                        organization=office,
                        companies=context["companies"],
                        initial={
                            "company": item.company_id,
                            "document_type": item.document_type_id,
                            "period_label": item.period_label,
                            "counterparty_token": item.counterparty_token,
                            "final_name": item.final_name,
                        },
                        auto_id="triage-%s",
                    ),
                    ("Empresa", "Tipo", "Período", "Contraparte", ""),
                    strict=True,
                )
            ],
            "triage_can_preview": (
                not visitor
                and PurePath(item.original_name).suffix.casefold() in _TRIAGE_PREVIEW_TYPES
                and item.status
                not in {TriageStatus.RECEIVED, TriageStatus.QUARANTINED, TriageStatus.REJECTED}
                and getattr(item, "safety_scan", None) is not None
                and item.safety_scan.verdict == "clean"
                and item.safety_scan.format_verdict == "valid"
            ),
            "demo_history": demo_history,
            "demo_visitor": visitor,
            "triage_history_events": triage_history_events,
            "triage_history_page": triage_history_page,
            "triage_history_querystring": triage_history_query_params.urlencode(),
            "triage_history_total": triage_history_total,
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


_TRIAGE_PREVIEW_TYPES = {
    ".pdf": "application/pdf",
    ".xml": "text/plain; charset=utf-8",
    ".csv": "text/plain; charset=utf-8",
    ".ofx": "text/plain; charset=utf-8",
}


@office_required
@require_http_methods(["GET"])
@xframe_options_sameorigin
def triage_preview(request: HttpRequest, item_id: str) -> HttpResponseBase:
    """Show released bytes inline so the reviewer can check before deciding."""
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        raise Http404
    office = context["office"]
    assert isinstance(office, Organization)
    item_scope = Q(company__in=context["companies"])
    if _can_manage_collaborators(context):
        item_scope |= Q(company__isnull=True)
    item = get_object_or_404(
        TriageItem.objects.select_related("blob").filter(item_scope),
        organization=office,
        id=item_id,
    )
    content_type = _TRIAGE_PREVIEW_TYPES.get(PurePath(item.original_name).suffix.casefold())
    if content_type is None or is_demo_visitor(request, office):
        raise Http404
    try:
        payload = open_reviewable_blob(item=item)
    except ValidationError:
        raise Http404 from None
    if content_type.startswith("text/"):
        try:
            payload = payload.decode("utf-8").encode("utf-8")
        except UnicodeDecodeError:
            payload = payload.decode("latin-1").encode("utf-8")
    response = HttpResponse(payload, content_type=content_type)
    response["Content-Disposition"] = "inline"
    response["Cache-Control"] = "no-store, private"
    response["X-Content-Type-Options"] = "nosniff"
    # Chromium's PDF viewer needs object-src; text gets a scriptless sandbox.
    response["Content-Security-Policy"] = (
        "default-src 'none'; object-src 'self'; frame-ancestors 'self'"
        if content_type == "application/pdf"
        else "default-src 'none'; sandbox; frame-ancestors 'self'"
    )
    record_event(
        action="triage.item.previewed",
        actor=cast(User, request.user),
        organization=office,
        target=item,
        request=request,
        metadata={"content_hash": item.content_hash},
    )
    return response


@office_required
@require_http_methods(["GET"])
def triage_download(request: HttpRequest, item_id: str) -> HttpResponseBase:
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
    # Shared public demonstration: visitors explore, they do not add companies for others.
    can_manage_companies = _can_manage_companies(context) and not office.is_demo
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
        return refuse(
            request,
            "As empresas deste escritório são sincronizadas pelo Domínio.",
            kind="unavailable",
        )
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
    query = request.GET.get("q", "").strip()[:100]
    priority = request.GET.get("prioridade", "")
    situation = request.GET.get("situacao", "")
    link = request.GET.get("vinculo", "")
    certificate_filter = request.GET.get("certificado", "")
    pending_filter = request.GET.get("pendencia", "")
    regime_filter = request.GET.get("regime", "")

    valid_filters = {
        "prioridade": {"", "atencao", "revisao", "certificado", "sem_codigo"},
        "situacao": {"", "ativa", "pausada"},
        "vinculo": {"", "com", "sem"},
        "certificado": {"", "valido", "vencendo", "ausente"},
        "pendencia": {"", "com", "sem"},
        "regime": {"", "nao_informado", *ClientCompany.TaxRegime.values},
    }
    filter_values = {
        "prioridade": priority,
        "situacao": situation,
        "vinculo": link,
        "certificado": certificate_filter,
        "pendencia": pending_filter,
        "regime": regime_filter,
    }
    invalid_filter = next(
        (name for name, value in filter_values.items() if value not in valid_filters[name]),
        "",
    )

    now = timezone.now()
    expiring_until = now + timedelta(days=30)
    valid_certificates = Certificate.objects.filter(
        company_id=OuterRef("pk"), revoked_at__isnull=True, valid_until__gt=now
    )
    expiring_certificates = valid_certificates.filter(valid_until__lte=expiring_until)
    open_reviews = ReviewCase.objects.filter(
        organization=office, status=ReviewCase.Status.OPEN, document__company_id=OuterRef("pk")
    )
    scoped_rows = _company_history_scope(context).annotate(
        has_certificate=Exists(valid_certificates),
        certificate_expiring=Exists(expiring_certificates),
        has_open_review=Exists(open_reviews),
    )
    scope_total = scoped_rows.count()
    active_rows = scoped_rows.filter(active=True)
    attention_condition = (
        Q(has_open_review=True)
        | Q(has_certificate=False)
        | Q(certificate_expiring=True)
        | Q(dominio_code="")
    )
    priority_counts = {
        "": scope_total,
        "atencao": active_rows.filter(attention_condition).count(),
        "revisao": active_rows.filter(has_open_review=True).count(),
        "certificado": active_rows.filter(
            Q(has_certificate=False) | Q(certificate_expiring=True)
        ).count(),
        "sem_codigo": active_rows.filter(dominio_code="").count(),
    }
    priority_filters = [
        {"value": "", "label": "Todas", "count": priority_counts[""]},
        {
            "value": "atencao",
            "label": "Precisam de atenção",
            "count": priority_counts["atencao"],
        },
        {
            "value": "revisao",
            "label": "Revisões NFS-e",
            "count": priority_counts["revisao"],
        },
        {
            "value": "certificado",
            "label": "Certificado A1",
            "count": priority_counts["certificado"],
        },
        {
            "value": "sem_codigo",
            "label": "Sem código Domínio",
            "count": priority_counts["sem_codigo"],
        },
    ]
    for item in priority_filters:
        item["selected"] = item["value"] == priority
        item["url"] = (
            reverse("hub:companies")
            + (f"?prioridade={item['value']}" if item["value"] else "")
        )

    rows = scoped_rows
    if invalid_filter:
        rows = rows.none()
    elif priority == "atencao":
        rows = rows.filter(active=True).filter(attention_condition)
    elif priority == "revisao":
        rows = rows.filter(active=True, has_open_review=True)
    elif priority == "certificado":
        rows = rows.filter(active=True).filter(
            Q(has_certificate=False) | Q(certificate_expiring=True)
        )
    elif priority == "sem_codigo":
        rows = rows.filter(active=True, dominio_code="")
    if query:
        search = (
            Q(name__icontains=query)
            | Q(cnpj_masked__icontains=query)
            | Q(dominio_code__icontains=query)
        )
        identifier = re.sub(r"[./\s-]", "", query).upper()
        if re.fullmatch(r"\d+|[A-Z0-9]{12}\d{2}", identifier):
            rows = rows.annotate(
                searchable_cnpj=Replace(
                    Replace(Replace("cnpj_masked", Value("."), Value("")), Value("/"), Value("")),
                    Value("-"),
                    Value(""),
                )
            )
            search |= Q(searchable_cnpj__icontains=identifier)
        rows = rows.filter(search)
    if situation == "pausada":
        rows = rows.filter(active=False)
    elif situation == "ativa":
        rows = rows.filter(active=True)
    if regime_filter == "nao_informado":
        rows = rows.filter(tax_regime="")
    elif regime_filter:
        rows = rows.filter(tax_regime=regime_filter)
    if link == "com":
        rows = rows.exclude(dominio_code="")
    elif link == "sem":
        rows = rows.filter(dominio_code="")

    rows = rows.annotate(
        open_review_total=Count(
            "nfse_documents__review_case",
            filter=Q(nfse_documents__review_case__status=ReviewCase.Status.OPEN),
            distinct=True,
        ),
    )
    if certificate_filter == "valido":
        rows = rows.filter(has_certificate=True, certificate_expiring=False)
    elif certificate_filter == "vencendo":
        rows = rows.filter(certificate_expiring=True)
    elif certificate_filter == "ausente":
        rows = rows.filter(has_certificate=False)
    if pending_filter == "com":
        rows = rows.filter(Exists(open_reviews))
    elif pending_filter == "sem":
        rows = rows.filter(~Exists(open_reviews))

    paginator = Paginator(rows.order_by("name"), COMPANIES_PER_PAGE)
    page = paginator.get_page(request.GET.get("pagina"))
    filters = {
        "q": query,
        "prioridade": priority,
        "situacao": situation,
        "vinculo": link,
        "certificado": certificate_filter,
        "pendencia": pending_filter,
        "regime": regime_filter,
    }
    context.update(
        {
            "page_title": "Empresas",
            "tax_regimes": ClientCompany.TaxRegime.choices,
            "companies": page.object_list,
            "page_obj": page,
            "paginator": paginator,
            "total_companies": paginator.count,
            "filters": filters,
            "filters_applied": any(filters.values()),
            "filter_error": (
                "Um dos filtros não é válido. Limpe o recorte e escolha uma opção disponível."
                if invalid_filter
                else ""
            ),
            "priority_filters": priority_filters,
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
    return render(
        request,
        "hub/companies.html",
        context,
        status=400 if request.method == "POST" and form.errors else 200,
    )


def _company_history_scope(context: dict[str, object]) -> QuerySet[ClientCompany]:
    """Match registry visibility without widening restricted operational scopes."""
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    if _sees_every_company(context):
        return ClientCompany.objects.filter(organization=cast(Organization, context["office"]))
    return scope


def _company_responsible_candidates(
    office: Organization, company: ClientCompany
) -> list[tuple[str, str]]:
    """People who can operate this client's work: active, operational and with access."""

    candidates: list[tuple[str, str]] = []
    for membership in (
        Membership.objects.filter(organization=office, is_active=True, user__is_active=True)
        .exclude(role__in=[Membership.Role.AUDITOR, Membership.Role.BILLING])
        .select_related("user")
        .order_by("user__full_name", "user__email")
    ):
        if office.is_demo and membership.user.email.startswith("demo-"):
            continue
        if company_queryset_for_membership(membership).filter(pk=company.pk).exists():
            candidates.append((str(membership.user_id), membership.user.display_name))
    return candidates


def _can_manage_companies(context: dict[str, object]) -> bool:
    """Keep company mutations behind the same full-portfolio boundary everywhere."""

    membership = context.get("membership")
    return bool(
        context.get("support_can_mutate")
        and (
            (context.get("support_session") is not None and _sees_every_company(context))
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


def _sees_every_company(context: dict[str, object]) -> bool:
    """Only widen the active portfolio for an explicitly unscoped workspace."""

    office = context["office"]
    support = context.get("support_session")
    if isinstance(support, SupportSession):
        return not support.company_ids
    membership = context.get("membership")
    return (
        isinstance(office, Organization)
        and isinstance(membership, Membership)
        and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
        and not ControlPlaneBinding.objects.filter(organization=office).exists()
        and not CompanyAccessGrant.objects.filter(
            organization=office,
            membership=membership,
            is_active=True,
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
    is_queue_upload = (
        request.headers.get("X-CICA-CERTIFICATE-QUEUE") == "1"
        or request.POST.get("queue_upload") == "1"
    )
    form = CertificateUploadForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and demo_certificate_mode:
        demo_company_id = request.POST.get("demo_company_id")
        demo_company = (
            allowed_companies.filter(id=demo_company_id, active=True).first()
            if demo_company_id
            else None
        )
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
        scoped_companies = list(allowed_companies.filter(active=True))
        results = []
        for index, upload in enumerate(form.cleaned_data["pfx_files"], start=1):
            result = import_certificate_upload(
                filename=upload.name,
                pfx_bytes=upload.read(),
                common_password=form.cleaned_data["common_password"],
                companies=scoped_companies,
                actor=request.user,
                request=request,
            )
            results.append(
                {
                    "position": index,
                    "status": result.status,
                    "title": result.title,
                    "detail": result.detail,
                    "company_name": result.company_name,
                    "reason": result.reason,
                }
            )
        if is_queue_upload:
            try:
                queue_position = max(1, int(request.POST.get("queue_position", "1")))
            except ValueError:
                queue_position = 1
            queued_results = (
                {}
                if queue_position == 1
                else dict(request.session.get("certificate_import_queue", {}))
            )
            queued_results[str(queue_position)] = results[0]
            request.session["certificate_import_queue"] = queued_results
            request.session["certificate_import_results"] = [
                queued_results[key] for key in sorted(queued_results, key=int)
            ]
            return JsonResponse({"result": results[0]})
        request.session["certificate_import_results"] = results
        recognized = sum(result["status"] == "recognized" for result in results)
        unrecognized = len(results) - recognized
        if recognized:
            messages.success(
                request,
                f"{recognized} certificado{'s' if recognized != 1 else ''} vinculado"
                f"{'s' if recognized != 1 else ''} automaticamente.",
            )
        if unrecognized:
            messages.warning(
                request,
                f"{unrecognized} arquivo{'s' if unrecognized != 1 else ''} ficou"
                f"{'ram' if unrecognized != 1 else ''} como não reconhecido.",
            )
        return redirect("hub:certificates")
    if request.method == "POST" and is_queue_upload:
        return JsonResponse(
            {"error": "Selecione um arquivo .pfx ou .p12 válido para continuar."}, status=400
        )
    now = timezone.now()
    expires_soon_at = now + timedelta(days=30)
    certificate_search = request.GET.get("q", "").strip()[:100]
    certificate_status = request.GET.get("status", "all")
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
        certificate_status = "all"
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
    missing_certificate_page = Paginator(missing_companies.order_by("name"), 20).get_page(
        request.GET.get("missing_page")
    )
    missing_certificate_query_params = request.GET.copy()
    missing_certificate_query_params.pop("missing_page", None)
    simulated_companies = list(
        allowed_companies.filter(id__in=simulated_company_ids).order_by("name")
    )
    certificate_filters = {"q": certificate_search, "status": certificate_status}
    certificate_import_results = request.session.pop("certificate_import_results", [])
    request.session.pop("certificate_import_queue", None)
    certificate_import_summary = {
        "total": len(certificate_import_results),
        "recognized": sum(
            result.get("status") == "recognized" for result in certificate_import_results
        ),
        "open_failed": sum(
            result.get("reason") == "open_failed" for result in certificate_import_results
        ),
        "duplicate": sum(
            result.get("reason") == "duplicate" for result in certificate_import_results
        ),
    }
    certificate_import_summary["unrecognized"] = (
        certificate_import_summary["total"] - certificate_import_summary["recognized"]
    )
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
                "covered_companies": certificate_base.filter(
                    revoked_at__isnull=True, valid_until__gte=now
                )
                .values("company_id")
                .distinct()
                .count()
                + len(simulated_companies),
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
            "missing_certificate_companies": list(missing_certificate_page.object_list),
            "missing_certificate_page": missing_certificate_page,
            "missing_certificate_query_without_page": missing_certificate_query_params.urlencode(),
            "demo_certificate_mode": demo_certificate_mode,
            "demo_simulated_certificate_companies": simulated_companies,
            "certificate_import_results": certificate_import_results,
            "certificate_import_summary": certificate_import_summary,
            "nfse_sync_runtime_enabled": settings.NFSE_ADN_SYNC_ENABLED,
            "form": form,
            "support_can_mutate": context["support_can_mutate"],
            "today": now,
            "expires_soon_at": expires_soon_at,
        }
    )
    return render(request, "hub/certificates.html", context)


@office_required
def reviews(request: HttpRequest) -> HttpResponse:
    """Redirect old review bookmarks to the unified NFS-e document list."""

    query = request.GET.copy()
    query["status"] = "unclassified"
    query.pop("page", None)
    return redirect(f"{reverse('hub:nfse-center')}?{query.urlencode()}")


@office_required
def legacy_reviews(request: HttpRequest) -> HttpResponse:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    review_search = request.GET.get("q", "").strip()[:100]
    review_status = request.GET.get("status", ReviewCase.Status.OPEN)
    if review_status not in {"all", *ReviewCase.Status.values}:
        review_status = ReviewCase.Status.OPEN
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
    if is_demo_visitor(request, office):
        demo_cases = [
            _demo_review_for_view(request, review)
            for review in cases.order_by("status", "created_at")
        ]
        if review_status != "all":
            demo_cases = [review for review in demo_cases if review.status == review_status]
        filtered_total = len(demo_cases)
        page = Paginator(demo_cases, 50).get_page(request.GET.get("page"))
    else:
        if review_status != "all":
            cases = cases.filter(status=review_status)
        filtered_total = cases.count()
        page = Paginator(cases.order_by("status", "created_at"), 50).get_page(
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
        review.resolution_source = ReviewCase.ResolutionSource.HUMAN
        review.resolved_by = cast(User, request.user)
        review.resolved_at = parse_datetime(str(entry.get("resolved_at", "")))
    return review


def _nfse_review_text(value: object, *, limit: int = 500) -> str:
    """Render bounded normalized evidence without treating arbitrary JSON as markup."""

    if isinstance(value, str):
        return value.strip()[:limit]
    if isinstance(value, (int, float, Decimal)) and not isinstance(value, bool):
        return str(value)[:limit]
    return ""


def _nfse_review_amount(value: object) -> str:
    """Format the normalized fiscal amount for a reviewer without changing its source."""

    raw = _nfse_review_text(value, limit=80)
    if not raw:
        return ""
    try:
        amount = Decimal(raw)
        if not amount.is_finite() or amount < 0:
            return ""
        formatted = f"{amount.quantize(Decimal('0.01')):,.2f}"
    except (InvalidOperation, ValueError):
        return ""
    return f"R$ {formatted.replace(',', '_').replace('.', ',').replace('_', '.')}"


def _nfse_review_issued_at(document: NfseDocument, evidence: dict[str, object]) -> str:
    """Prefer the parsed issuance timestamp and retain a bounded source fallback."""

    if document.issued_at is not None:
        issued_at = document.issued_at
        if timezone.is_aware(issued_at):
            issued_at = timezone.localtime(issued_at)
        return issued_at.strftime("%d/%m/%Y")
    raw = _nfse_review_text(evidence.get("issued_at"), limit=40)
    if not raw:
        return ""
    parsed_datetime = parse_datetime(raw)
    if parsed_datetime is not None:
        if timezone.is_aware(parsed_datetime):
            parsed_datetime = timezone.localtime(parsed_datetime)
        return parsed_datetime.strftime("%d/%m/%Y")
    parsed_date = parse_date(raw)
    return parsed_date.strftime("%d/%m/%Y") if parsed_date is not None else raw


def _nfse_review_evidence(document: NfseDocument) -> list[tuple[str, str]]:
    """Expose the normalized facts needed to review one NFS-e, not raw XML."""

    evidence = document.normalized_data if isinstance(document.normalized_data, dict) else {}
    return [
        ("Número da NFS-e", _nfse_review_text(evidence.get("number"), limit=80)),
        ("Emissão / competência", _nfse_review_issued_at(document, evidence)),
        ("Código de serviço", _nfse_review_text(evidence.get("service_code"), limit=80)),
        (
            "Descrição do serviço",
            _nfse_review_text(evidence.get("service_description"), limit=500),
        ),
        ("Valor do serviço", _nfse_review_amount(evidence.get("amount"))),
        (
            "Referência da contraparte",
            _nfse_review_text(evidence.get("counterparty_ref"), limit=80),
        ),
    ]


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
    context.update(
        {
            "page_title": "Conferir NFS-e",
            "review": review,
            "can_decide_review": can_decide,
            "review_evidence": _nfse_review_evidence(document),
            "review_artifacts": IntegrationArtifact.objects.filter(
                organization=office, document=document
            ).order_by("created_at"),
            "review_accumulator_codes": _review_accumulator_codes(document),
            "review_accumulator_options": _review_accumulator_options(document),
            "review_dominio_accumulator": _effective_nfse_accumulator(document),
        }
    )
    return render(request, "hub/review_detail.html", context)


def _effective_nfse_accumulator(document: NfseDocument) -> str:
    from apps.hub.nfse_reclassification import _effective_artifact

    artifact = _effective_artifact(
        list(IntegrationArtifact.objects.filter(document=document).order_by("created_at"))
    )
    return artifact.accumulator_code if artifact is not None else ""


def _review_accumulator_options(document: NfseDocument) -> list[tuple[str, str]]:
    """Codes an operator may choose, with the Domínio name so nobody picks a number blind.

    When the company has a Domínio catalog, only its active accumulators (and ones registered
    by hand) are offered: anything else would be refused by the export and by Domínio.
    """

    codes = _review_accumulator_candidates(document)
    allowed = active_catalog_codes([document.company]).get(document.company_id)
    if allowed is not None:
        codes = [code for code in codes if code in allowed]
    names: dict[str, str] = {}
    for code, name in (
        AccumulatorCatalogEntry.objects.filter(
            organization=document.organization, company=document.company, accumulator_code__in=codes
        )
        .order_by("-source_snapshot_at")
        .values_list("accumulator_code", "name")
    ):
        names.setdefault(code, name)
    for code, name in AccumulatorRule.objects.filter(
        organization=document.organization, company=document.company, accumulator_code__in=codes
    ).values_list("accumulator_code", "name"):
        names.setdefault(code, name)

    def order(code: str) -> tuple[int, str]:
        return (int(code), "") if code.isdigit() else (10**9, code)

    return [(code, names.get(code, "")) for code in sorted(codes, key=order)]


def _review_accumulator_codes(document: NfseDocument) -> list[str]:
    return [code for code, _name in _review_accumulator_options(document)]


def _review_accumulator_candidates(document: NfseDocument) -> list[str]:
    """Return only company-scoped codes that an operator may select for a review."""

    document_day = document.issued_at.date() if document.issued_at else timezone.localdate()
    configured_codes = (
        AccumulatorRule.objects.filter(
            organization=document.organization,
            company=document.company,
            active=True,
        )
        .filter(
            Q(valid_from__isnull=True) | Q(valid_from__lte=document_day),
            Q(valid_until__isnull=True) | Q(valid_until__gte=document_day),
        )
        .order_by("priority", "name")
        .values_list("accumulator_code", flat=True)
    )
    observed_codes = (
        AccumulatorObservation.objects.filter(
            organization=document.organization,
            company=document.company,
        )
        .order_by("-last_used_at")
        .values_list("accumulator_code", flat=True)
    )
    catalog_codes = (
        AccumulatorCatalogEntry.objects.filter(
            organization=document.organization,
            company=document.company,
            active=True,
        )
        .order_by("-source_snapshot_at", "accumulator_code")
        .values_list("accumulator_code", flat=True)
    )
    return list(dict.fromkeys([*configured_codes, *catalog_codes, *observed_codes]))


@office_required
def review_dominio_xml(request: HttpRequest, case_id: str) -> HttpResponse:
    """The note's XML as Domínio imports it: original bytes plus ``infNFSe/valores/acum``."""

    context = workspace_context(request)
    office = cast(Organization, context["office"])
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    review = get_object_or_404(
        ReviewCase.objects.select_related("document"),
        pk=case_id,
        organization=office,
        document__company__in=scope,
    )
    accumulator = _effective_nfse_accumulator(review.document)
    if not accumulator:
        return refuse(
            request, "Classifique a nota antes de baixar o XML para a Domínio.", kind="unavailable"
        )
    try:
        xml = _xml_with_dominio_accumulator(review.document.original_xml, accumulator)
    except ValueError as exc:
        return refuse(request, str(exc), kind="unavailable")
    response = HttpResponse(xml, content_type="application/xml; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="nfse-{review.id}-dominio.xml"'
    response["X-Content-Type-Options"] = "nosniff"
    response["Cache-Control"] = "private, no-store"
    record_event(
        action="hub.nfse.review_dominio_xml_downloaded",
        actor=request.user,
        organization=office,
        target=review,
        request=request,
        metadata={"accumulator": accumulator},
    )
    return response


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
@transaction.atomic
def update_nfse_accumulator(request: HttpRequest, document_id: str) -> HttpResponse:
    """Append a corrected accumulator without rewriting prior fiscal evidence."""

    context = workspace_context(request)
    office = cast(Organization, context["office"])
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    membership = context["membership"]
    can_classify = bool(
        context["support_can_mutate"]
        and (
            context["support_session"] is not None
            or (
                isinstance(membership, Membership)
                and membership.role in {
                    Membership.Role.OWNER, Membership.Role.ADMIN,
                    Membership.Role.MANAGER, Membership.Role.OPERATOR,
                }
            )
        )
    )
    if not can_classify:
        return refuse(request, "Seu perfil pode consultar, mas não corrigir acumuladores.")
    document = get_object_or_404(
        NfseDocument.objects.select_for_update().select_related("company"),
        id=document_id,
        organization=office,
        company__in=scope,
    )
    accumulator = request.POST.get("accumulator_code", "").strip()
    return_to = safe_next(
        request, request.POST.get("return_to"), fallback=reverse("hub:nfse-center")
    )
    asynchronous = request.headers.get("X-Requested-With") == "XMLHttpRequest"

    def finish(ok: bool, message: str, *, status: int = 200) -> HttpResponse:
        if asynchronous:
            return JsonResponse(
                {"ok": ok, "message": message, "accumulator": accumulator if ok else ""},
                status=status,
            )
        (messages.success if ok else messages.error)(request, message)
        return redirect(return_to)

    if not accumulator:
        return finish(False, "Escolha o acumulador antes de salvar.", status=400)
    if accumulator not in _review_accumulator_codes(document):
        return finish(
            False,
            "Escolha um acumulador cadastrado para esta empresa antes de salvar.",
            status=400,
        )
    previous = (
        IntegrationArtifact.objects.filter(organization=office, document=document)
        .order_by("-created_at")
        .first()
    )
    if previous is None:
        return finish(False, "Classifique esta nota antes de corrigir o acumulador.", status=409)
    if previous.accumulator_code == accumulator:
        return finish(True, "O acumulador desta nota já está atualizado.")

    changed_at = timezone.now()
    artifact = IntegrationArtifact.objects.create(
        organization=office,
        document=document,
        accumulator_code=accumulator,
        applied_rule="Correção humana",
        confidence=100,
        evidence={
            "source": "human_correction",
            "previous_artifact_id": str(previous.id),
        },
        payload={
            "corrected_at": changed_at.isoformat(),
            "previous_artifact_id": str(previous.id),
        },
    )
    review = ReviewCase.objects.select_for_update().filter(document=document).first()
    if review is not None:
        review.status = ReviewCase.Status.RESOLVED
        review.resolved_accumulator = accumulator
        review.resolution_source = ReviewCase.ResolutionSource.HUMAN
        review.resolved_by = cast(User, request.user)
        review.resolved_at = changed_at
        review.save(
            update_fields=[
                "status",
                "resolved_accumulator",
                "resolution_source",
                "resolved_by",
                "resolved_at",
                "updated_at",
            ]
        )
    record_human_observation(
        document=document, accumulator_code=accumulator, observed_at=changed_at
    )
    AccumulatorHistoryEntry.objects.create(
        organization=office,
        company=document.company,
        accumulator_code=accumulator,
        source=AccumulatorHistoryEntry.Source.HUMAN_REVIEW,
        source_reference=f"nfse-artifact:{artifact.id}",
        occurred_at=changed_at,
        created_by=cast(User, request.user),
        metadata={
            "document_id": str(document.id),
            "artifact_id": str(artifact.id),
            "previous_artifact_id": str(previous.id),
        },
    )
    record_event(
        action="hub.nfse.accumulator_corrected",
        actor=request.user,
        organization=office,
        target=document,
        request=request,
        metadata={"artifact_id": str(artifact.id), "changed": True},
    )
    if review is not None:
        sync_nfse_review_activity(review.pk)
    return finish(True, "Acumulador atualizado. A decisão anterior foi preservada.")


@office_required
@require_http_methods(["POST"])
@transaction.atomic
def resolve_review(request: HttpRequest, case_id: str) -> HttpResponseBase:
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
        ReviewCase.objects.select_for_update(),
        id=case_id,
        organization=office,
        document__company__in=scope,
    )
    if visitor and get_progress(request, "nfse_reviews", review.id).get("resolved"):
        messages.info(request, "Esta decisão fictícia já foi registrada nesta sessão.")
        return _review_result_redirect(request, review.id)
    if not visitor and review.status != ReviewCase.Status.OPEN:
        return refuse(request, "Este caso já recebeu uma decisão.", kind="unavailable")
    accumulator = request.POST.get("accumulator_code", "").strip()
    if not accumulator:
        messages.error(request, "Informe o acumulador usado para registrar a decisão.")
        return _review_result_redirect(request, review.id)
    if not visitor and accumulator not in _review_accumulator_codes(review.document):
        messages.error(
            request,
            "Escolha um acumulador cadastrado para esta empresa antes de registrar a decisão.",
        )
        return _review_result_redirect(request, review.id)
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
        return _review_result_redirect(request, review.id)
    review.status = ReviewCase.Status.RESOLVED
    review.resolved_accumulator = accumulator
    review.resolution_source = ReviewCase.ResolutionSource.HUMAN
    review.resolved_by = cast(User, request.user)
    review.resolved_at = timezone.now()
    review.save(
        update_fields=[
            "status",
            "resolved_accumulator",
            "resolution_source",
            "resolved_by",
            "resolved_at",
            "updated_at",
        ]
    )
    observed_at = review.resolved_at or timezone.now()
    record_human_observation(
        document=review.document, accumulator_code=accumulator, observed_at=observed_at
    )
    AccumulatorHistoryEntry.objects.create(
        organization=office,
        company=review.document.company,
        accumulator_code=accumulator,
        source=AccumulatorHistoryEntry.Source.HUMAN_REVIEW,
        source_reference=nfse_resolution_reference(review),
        occurred_at=observed_at,
        created_by=cast(User, request.user),
        metadata={"review_id": str(review.id), "document_id": str(review.document_id)},
    )
    IntegrationArtifact.objects.create(
        organization=office,
        document=review.document,
        accumulator_code=accumulator,
        applied_rule="Decisão humana",
        confidence=100,
        evidence={"source": "human_review", "review_id": str(review.id)},
        payload={"review_id": str(review.id), "resolved_at": review.resolved_at.isoformat()},
    )
    record_event(
        action="hub.nfse.review_resolved",
        actor=request.user,
        organization=office,
        target=review,
        request=request,
        metadata={"has_accumulator": True},
    )
    sync_nfse_review_activity(review.pk)
    messages.success(request, "Decisão registrada e preservada na auditoria.")
    return _review_result_redirect(request, review.id)


@office_required
@require_http_methods(["GET", "POST"])
def dre_mapping_editor(request: HttpRequest) -> HttpResponse:
    """Save complete DRE mappings as immutable office versions."""

    context = workspace_context(request)
    office = cast(Organization, context["office"])
    membership = context["membership"]
    can_manage = bool(
        context["support_session"] is None
        and isinstance(membership, Membership)
        and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN}
        and context["support_can_mutate"]
    )
    active_mapping = (
        DreMappingSet.objects.filter(organization=office, is_active=True)
        .prefetch_related("mappings")
        .order_by("-version")
        .first()
    )
    initial = (
        [
            {"account_code": row.account_code, "group": row.group, "sign": row.sign}
            for row in active_mapping.mappings.all()
        ]
        if active_mapping is not None
        else []
    )
    formset = DreMappingFormSet(request.POST or None, prefix="mapping", initial=initial)
    if request.method == "POST":
        if not can_manage:
            return refuse(request, "Somente owners e administradores alteram o mapa DRE.")
        if formset.is_valid():
            rows = [
                (
                    str(form.cleaned_data["account_code"]),
                    str(form.cleaned_data["group"]),
                    int(form.cleaned_data["sign"]),
                )
                for form in formset.forms
                if form.cleaned_data.get("account_code")
            ]
            with transaction.atomic():
                Organization.objects.select_for_update().get(pk=office.id)
                mappings = DreMappingSet.objects.select_for_update().filter(organization=office)
                current_version = (
                    mappings.order_by("-version").values_list("version", flat=True).first() or 0
                )
                next_version = current_version + 1
                mappings.filter(is_active=True).update(is_active=False)
                mapping_set = DreMappingSet.objects.create(
                    organization=office,
                    version=next_version,
                    label=f"Configurado no CICA v{next_version}",
                    is_active=True,
                    created_by=cast(User, request.user),
                )
                DreAccountMapping.objects.bulk_create(
                    [
                        DreAccountMapping(
                            mapping_set=mapping_set,
                            account_code=code,
                            group=group,
                            sign=sign,
                        )
                        for code, group, sign in rows
                    ]
                )
            record_event(
                action="hub.dre_mapping.version_created",
                actor=request.user,
                organization=office,
                target=mapping_set,
                request=request,
                metadata={"version": mapping_set.version, "mapping_count": len(rows)},
            )
            messages.success(request, f"Mapa DRE v{mapping_set.version} salvo e ativado.")
            return redirect("hub:dre-mapping-editor")
    versions = DreMappingSet.objects.filter(organization=office).order_by("-version")[:12]
    context.update(
        {
            "page_title": "Mapa DRE",
            "can_manage_dre_mapping": can_manage,
            "active_dre_mapping": active_mapping,
            "dre_mapping_formset": formset,
            "dre_mapping_versions": versions,
        }
    )
    return render(request, "hub/dre_mapping_editor.html", context)


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
    source_id = request.GET.get("source")
    selected_source = sources.filter(id=source_id).first() if source_id else None
    if selected_source is None:
        selected_source = sources.first()
    posted_source_id = request.POST.get("source_id")
    posted_source = sources.filter(id=posted_source_id).first() if posted_source_id else None
    if posted_source is not None:
        selected_source = posted_source
    action = request.POST.get("action", "") if request.method == "POST" else ""
    source_form = DataSourceForm(
        request.POST if action == "choose-source" else None,
        prefix="source",
    )
    profile, _ = OfficeProfile.objects.get_or_create(organization=office)
    identity_form = OfficeIdentityForm(
        request.POST if action == "save-office" else None,
        instance=profile,
        prefix="office",
    )
    import_form = UnifiedImportForm(
        request.POST if action == "upload" else None,
        request.FILES if action == "upload" else None,
        prefix="import",
        companies=cast("QuerySet[ClientCompany]", context["companies"]),
        source_kind=selected_source.kind if selected_source else "",
    )
    if request.method == "POST":
        if not can_manage:
            return refuse(request, "Somente owners e administradores alteram a configuração.")
        if action == "save-office" and identity_form.is_valid():
            profile = identity_form.save(commit=False)
            profile.cnpj_hash = identity_form.cnpj_hash
            profile.save(update_fields=["legal_name", "cnpj", "cnpj_hash"])
            record_event(
                action="hub.office.identity_confirmed",
                actor=request.user,
                organization=office,
                target=profile,
                request=request,
            )
            messages.success(request, "Dados do escritório confirmados.")
            return redirect(f"{reverse('hub:setup')}#office-heading")
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
        if action == "reactivate-source":
            selected_source = get_object_or_404(
                DataSource,
                id=request.POST.get("source_id"),
                organization=office,
                status=DataSource.Status.DISABLED,
            )
            if request.POST.get("confirm_reactivate") != "yes":
                messages.error(request, "Confirme a reativação antes de alterar a fonte.")
            else:
                previous_status = selected_source.status
                selected_source.status = DataSource.Status.NOT_CONFIGURED
                selected_source.last_error_code = ""
                selected_source.last_error_message = ""
                selected_source.save(
                    update_fields=[
                        "status",
                        "last_error_code",
                        "last_error_message",
                        "updated_at",
                    ]
                )
                record_event(
                    action="hub.data_source.reactivated",
                    actor=request.user,
                    organization=office,
                    target=selected_source,
                    request=request,
                    metadata={
                        "previous_status": previous_status,
                        "current_status": selected_source.status,
                    },
                )
                messages.success(
                    request,
                    "Fonte reativada. Execute uma nova sincronização antes de confiar nos dados.",
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
                if not created and batch.status != ImportBatch.Status.PREVIEW:
                    messages.info(
                        request,
                        "Este arquivo já foi processado. Consulte o resultado no histórico abaixo.",
                    )
                    return redirect(
                        f"{reverse('hub:setup')}?source={selected_source.id}#history-heading"
                    )
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
    preview_id = request.GET.get("preview")
    preview = (
        ImportBatch.objects.filter(
            id=preview_id, organization=office, status=ImportBatch.Status.PREVIEW
        ).first()
        if preview_id
        else None
    )
    import_history_query_params = request.GET.copy()
    payroll_preview_page = None
    payroll_preview = []
    if can_manage and preview and preview.kind == ImportBatch.Kind.PAYROLL_TOTALS:
        payroll_preview_page = Paginator(json.loads(preview.encrypted_payload), 20).get_page(
            request.GET.get("preview_page")
        )
        payroll_preview = payroll_preview_rows(
            batch=preview,
            rows=list(payroll_preview_page.object_list),
            first_line=payroll_preview_page.start_index() + 1,
        )
    preview_params = request.GET.copy()
    preview_params.pop("preview_page", None)
    import_history_query_params.pop("imports_page", None)
    recent_imports_page = Paginator(
        ImportBatch.objects.filter(organization=office)
        .select_related("data_source")
        .order_by("-created_at"),
        20,
    ).get_page(request.GET.get("imports_page"))
    try:
        mfa_complete = cast(User, request.user).totp_device.is_confirmed
    except (AttributeError, ObjectDoesNotExist):
        mfa_complete = False
    context.update(
        {
            "page_title": "Primeiros passos",
            "source_form": source_form,
            "identity_form": identity_form,
            "import_form": import_form,
            "data_sources": sources,
            "selected_source": selected_source,
            "preview_batch": preview,
            "payroll_preview_page": payroll_preview_page,
            "payroll_preview_rows": payroll_preview,
            "payroll_preview_issue_count": (
                int(preview.mapping.get("preview_issue_count", 0))
                if preview and preview.kind == ImportBatch.Kind.PAYROLL_TOTALS
                else 0
            ),
            "payroll_preview_querystring": preview_params.urlencode(),
            "recent_imports": list(recent_imports_page.object_list),
            "recent_imports_page": recent_imports_page,
            "recent_imports_querystring": import_history_query_params.urlencode(),
            "recent_imports_total": recent_imports_page.paginator.count,
            "can_manage_setup": can_manage,
            "agent_installer_url": getattr(settings, "EDGE_AGENT_INSTALLER_URL", ""),
            "setup_diagnostics": [
                {
                    "label": "Operação independente",
                    "detail": "Empresas e atividades podem operar sem ERP conectado.",
                    "ready": ClientCompany.objects.filter(
                        organization=office, active=True
                    ).exists(),
                },
                {
                    "label": "Modelos de atividades",
                    "detail": (
                        "Defina responsáveis, prazos e evidências antes de gerar competências."
                    ),
                    "ready": ActivityTemplate.objects.filter(
                        organization=office, active=True
                    ).exists(),
                },
                {
                    "label": "Fonte de dados",
                    "detail": (
                        "Uma fonte pronta permite atualizar estados observados; fonte pendente "
                        "não bloqueia o restante."
                    ),
                    "ready": sources.filter(status=DataSource.Status.READY).exists(),
                },
                {
                    "label": "Equipe atribuída",
                    "detail": (
                        "Convide colaboradores e atribua empresas para limitar a carteira "
                        "operacional."
                    ),
                    "ready": Membership.objects.filter(organization=office, is_active=True).count()
                    > 1,
                },
                {
                    "label": "Limites contratados",
                    "detail": (
                        "Configure franquias e tetos aprovados antes de ativar consumo cobrado."
                    ),
                    "ready": UsageAllowance.objects.filter(organization=office).exists(),
                },
            ],
            "setup_steps": [
                {
                    "label": "Confirmar escritório",
                    "detail": "Revise as condições cadastradas antes de liberar o consumo.",
                    "done": bool(profile and profile.cnpj_hash),
                    "action_label": "Ver condições",
                    "url": f"{reverse('hub:settings')}#meu-plano",
                },
                {
                    "label": "Escolher fonte de dados",
                    "detail": "Domínio, Siescon quando homologado, ou operação independente.",
                    "done": sources.exists(),
                    "action_label": "Escolher fonte",
                    "url": f"{reverse('hub:setup')}#source-heading",
                },
                {
                    "label": "Cadastrar ou importar empresas",
                    "detail": "Crie a carteira manualmente ou importe uma prévia conferível.",
                    "done": ClientCompany.objects.filter(organization=office, active=True).exists(),
                    "action_label": "Abrir empresas",
                    "url": reverse("hub:companies"),
                },
                {
                    "label": "Aplicar modelos de atividades",
                    "detail": (
                        "Defina prazos, responsáveis e evidências antes de gerar competências."
                    ),
                    "done": ActivityTemplate.objects.filter(
                        organization=office, active=True
                    ).exists(),
                    "action_label": "Configurar modelos",
                    "url": reverse("hub:activity-models"),
                },
                {
                    "label": "Configurar os serviços desejados",
                    "detail": (
                        "Confira módulos e termos; nada é ativado ou cobrado automaticamente."
                    ),
                    "done": ProductModule.objects.filter(
                        organization=office, enabled=True
                    ).exists(),
                    "action_label": "Ver módulos",
                    "url": f"{reverse('hub:settings')}#meu-plano",
                },
                {
                    "label": "Convidar sua equipe",
                    "detail": "Atribua empresas e módulos no convite de cada pessoa.",
                    "done": Membership.objects.filter(organization=office, is_active=True).count()
                    > 1,
                    "action_label": "Gerenciar equipe",
                    "url": reverse("hub:team"),
                },
                {
                    "label": "Definir franquias e limites",
                    "detail": "Revise franquias, saldo e teto mensal aprovados para o escritório.",
                    "done": UsageAllowance.objects.filter(organization=office).exists(),
                    "action_label": "Ver consumo",
                    "url": f"{reverse('hub:settings')}#consumo",
                },
                {
                    "label": "Proteger sua conta",
                    "detail": (
                        "MFA ativo: os próximos logins também pedem o código do aplicativo."
                        if mfa_complete
                        else (
                            "Recomendado: ative o aplicativo autenticador para impedir acesso "
                            "só com a senha."
                        )
                    ),
                    "done": mfa_complete,
                    "recommended": True,
                    "personal_action": True,
                    "action_label": "Ativar MFA recomendado",
                    "url": f"{reverse('accounts:mfa-setup')}?next={reverse('hub:setup')}",
                },
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
            return refuse(
                request,
                "Não existe uma proposta de tokens aguardando aceite.",
                kind="unavailable",
            )
        if request.POST.get("accept_token_terms") != "on":
            messages.error(request, "Confirme o valor, a franquia, os pesos e o teto mensal.")
            return redirect("hub:settings")
        try:
            effective_from = date.fromisoformat(request.POST.get("effective_from", ""))
            activated = activate_token_book(
                book=token_draft,
                accepted_by=cast(User, request.user),
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
            return refuse(request, "O Domínio não está conectado.", kind="unavailable")
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
            return refuse(
                request,
                "Não há uma falha de sincronização para encaminhar.",
                kind="unavailable",
            )
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
