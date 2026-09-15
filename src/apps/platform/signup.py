from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth.hashers import make_password
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.common.cnpj import lookup_company
from apps.common.encryption import blind_index
from apps.hub.models import OfficeProfile, ProductModule
from apps.hub.module_catalog import OFFERED_MODULE_CODES
from apps.organizations.models import Membership, Organization
from apps.platform.availability import copilot_is_available
from apps.platform.legal_versions import LEGAL_VERSION
from apps.platform.models import (
    Entitlement,
    Plan,
    PlanServiceRate,
    PlatformConfiguration,
    SignupIntent,
    TenantContract,
    TenantLifecycle,
    TenantServiceRate,
)
from apps.platform.notifications import send_transactional_email

TRIAL_DAYS = 14
TRIAL_PLAN_CODE = "cica-trial-v1"
AI_ANSWER_ACTION = "ai.answer"


class SignupError(ValueError):
    pass


@dataclass(frozen=True)
class SignupIssued:
    intent: SignupIntent
    token: str


def _trial_ai_allowance() -> int:
    if not copilot_is_available():
        return 0
    configuration = PlatformConfiguration.objects.filter(key="default").first()
    allowance = configuration.trial_ai_included_requests if configuration else 0
    if allowance < 1:
        raise SignupError(
            "O teste gratuito está temporariamente indisponível. Tente novamente mais tarde."
        )
    return allowance


def issue_signup(
    *,
    email: str,
    full_name: str,
    password: str | None = None,
    office_name: str | None = None,
    cnpj: str,
    company_count: int = 1,
    module_codes: list[str] | None = None,
    terms_accepted: bool = False,
    marketing_opt_in: bool = False,
    request: object = None,
) -> SignupIssued:
    if not terms_accepted:
        raise SignupError("Aceite os documentos obrigat\u00f3rios para iniciar o teste.")
    trial_ai_allowance = _trial_ai_allowance()
    normalized_email = email.strip().casefold()
    if User.objects.filter(email=normalized_email).exists():
        raise SignupError("Este e-mail já possui uma conta. Entre para continuar.")
    cnpj_hash = blind_index(cnpj, namespace="office-cnpj")
    if OfficeProfile.objects.filter(cnpj_hash=cnpj_hash).exists():
        raise SignupError("Este CNPJ já está vinculado a um escritório.")
    registry = lookup_company(cnpj)
    if registry.get("status") == "not_found":
        raise SignupError("Não encontramos este CNPJ. Confira o número e tente novamente.")
    resolved_office_name = (office_name or registry.get("razao_social") or f"CNPJ {cnpj}").strip()
    default_modules = [
        code
        for code in OFFERED_MODULE_CODES
        if copilot_is_available() or code != ProductModule.Code.AI
    ]
    requested_modules = module_codes or default_modules
    resolved_modules = [
        code
        for code in dict.fromkeys(requested_modules)
        if code in OFFERED_MODULE_CODES
        and (copilot_is_available() or code != ProductModule.Code.AI)
    ]
    if not resolved_modules:
        raise SignupError("Nenhum módulo disponível para iniciar o teste.")
    # A free trial cannot become an unapproved quote or charge from a draft catalogue.
    token, digest = SignupIntent.issue_token()
    accepted_at = timezone.now()
    request_meta = getattr(request, "META", {}) if request is not None else {}
    request_ip = str(request_meta.get("REMOTE_ADDR", ""))
    acceptance_ip_hash = (
        blind_index(request_ip, namespace="signup-legal-acceptance-ip") if request_ip else ""
    )
    intent = SignupIntent.objects.create(
        email=normalized_email,
        full_name=full_name.strip(),
        password_hash=make_password(password) if password else "",
        office_name=resolved_office_name,
        cnpj=cnpj,
        cnpj_hash=cnpj_hash,
        company_count=company_count,
        selected_modules=resolved_modules,
        trial_ai_included_requests=trial_ai_allowance,
        quoted_monthly_cents=0,
        terms_version=LEGAL_VERSION,
        privacy_version=LEGAL_VERSION,
        terms_accepted_at=accepted_at,
        terms_acceptance_ip_hash=acceptance_ip_hash,
        marketing_opt_in=marketing_opt_in,
        marketing_opted_in_at=accepted_at if marketing_opt_in else None,
        marketing_opt_in_ip_hash=acceptance_ip_hash if marketing_opt_in else "",
        token_digest=digest,
        expires_at=accepted_at + timedelta(hours=24),
    )
    record_event(
        action="platform.signup.issued",
        target=intent,
        request=request,
        metadata={
            "terms_version": LEGAL_VERSION,
            "privacy_version": LEGAL_VERSION,
            "terms_acceptance": "signup_checkbox",
            "marketing_opt_in": marketing_opt_in,
        },
    )
    return SignupIssued(intent, token)


def signup_intent_from_token(*, token: str) -> SignupIntent:
    digest = hashlib.sha256(token.encode()).hexdigest()
    intent = SignupIntent.objects.filter(token_digest=digest).first()
    if intent is None or not intent.usable():
        raise SignupError("Este link de confirmação é inválido ou expirou.")
    return intent


def send_verification_email(*, issued: SignupIssued, base_url: str) -> None:
    url = base_url.rstrip("/") + reverse("hub:signup-verify", args=[issued.token])
    send_transactional_email(
        "Confirme seu escritório na CICA",
        f"Confirme seu e-mail e inicie os 14 dias grátis: {url}\n\nO link expira em 24 horas.",
        None,
        [issued.intent.email],
    )


@transaction.atomic
def provision_signup(
    *, token: str, password: str | None = None, request: object = None
) -> tuple[SignupIntent, User]:
    digest = hashlib.sha256(token.encode()).hexdigest()
    intent = SignupIntent.objects.select_for_update().filter(token_digest=digest).first()
    if intent is None or not intent.usable():
        raise SignupError("Este link de confirmação é inválido ou expirou.")
    password_hash = intent.password_hash or (make_password(password) if password else "")
    if not password_hash:
        raise SignupError("Defina uma senha para concluir o cadastro.")
    if User.objects.filter(email=intent.email).exists():
        raise SignupError("Este e-mail já foi usado em outra conta.")
    if OfficeProfile.objects.filter(cnpj_hash=intent.cnpj_hash).exists():
        raise SignupError("Este CNPJ já está vinculado a outro escritório.")
    slug_base = "cica-" + "".join(ch for ch in intent.office_name.casefold() if ch.isalnum())[:35]
    organization = Organization.objects.create(
        name=intent.office_name,
        slug=f"{slug_base or 'escritorio'}-{uuid4().hex[:10]}",
    )
    user = User(email=intent.email, full_name=intent.full_name, password=password_hash)
    user.full_clean(exclude={"password"})
    user.save()
    Membership.objects.create(
        organization=organization, user=user, role=Membership.Role.OWNER, is_active=True
    )
    now = timezone.now()
    today = timezone.localdate()
    trial_ends = today + timedelta(days=TRIAL_DAYS)
    OfficeProfile.objects.create(
        organization=organization,
        legal_name=intent.office_name,
        cnpj=intent.cnpj,
        cnpj_hash=intent.cnpj_hash,
        contract_status=OfficeProfile.ContractStatus.TRIAL,
        trial_started_at=now,
    )
    plan, _ = Plan.objects.get_or_create(
        code=TRIAL_PLAN_CODE,
        defaults={
            "name": "Teste CICA",
            "version": 1,
            "is_active": False,
            "modules": list(intent.selected_modules),
        },
    )
    if ProductModule.Code.AI in intent.selected_modules:
        PlanServiceRate.objects.update_or_create(
            plan=plan,
            action_code=AI_ANSWER_ACTION,
            defaults={
                "included_units": intent.trial_ai_included_requests,
                "overage_unit_price_cents": 0,
            },
        )
    contract = TenantContract.objects.create(
        organization=organization,
        plan=plan,
        monthly_price_cents=intent.quoted_monthly_cents,
        status=TenantContract.Status.TRIAL,
        reference=f"self-service:{intent.id}",
        starts_on=today,
        trial_ends_on=trial_ends,
        selected_modules=intent.selected_modules,
    )
    # A later developer change must affect only future tests, never this trial.
    if ProductModule.Code.AI in intent.selected_modules:
        TenantServiceRate.objects.update_or_create(
            contract=contract,
            action_code=AI_ANSWER_ACTION,
            defaults={
                "included_units": intent.trial_ai_included_requests,
                "overage_unit_price_cents": 0,
            },
        )
    TenantLifecycle.objects.create(
        organization=organization,
        state=TenantLifecycle.State.ACTIVE,
        changed_by=user,
        reason="Teste gratuito self-service iniciado.",
    )
    for code in intent.selected_modules:
        ProductModule.objects.create(
            organization=organization, code=code, enabled=True, enabled_at=now
        )
        Entitlement.objects.create(
            organization=organization, code=code, enabled=True, valid_until=trial_ends
        )
    intent.organization = organization
    intent.verified_at = now
    intent.save(update_fields=["organization", "verified_at", "updated_at"])
    record_event(
        action="platform.signup.provisioned",
        actor=user,
        organization=organization,
        target=intent,
        request=request,
        metadata={
            "modules": intent.selected_modules,
            "trial_days": TRIAL_DAYS,
            "trial_ai_included_requests": intent.trial_ai_included_requests,
        },
    )
    return intent, user
