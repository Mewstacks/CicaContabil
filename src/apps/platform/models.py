from __future__ import annotations

import hashlib
import secrets

from django.conf import settings
from django.core.validators import EmailValidator
from django.db import models
from django.utils import timezone

from apps.common.encryption import EncryptedTextField
from apps.common.models import UUIDTimeStampedModel


class PlatformConfiguration(UUIDTimeStampedModel):
    """Platform-owned settings; never tenant-editable or a container for raw secrets."""

    key = models.CharField(max_length=32, unique=True, default="default", editable=False)
    provider_cnpj = models.CharField(max_length=14, default="68340160000113")
    provider_legal_name = models.CharField(max_length=180, blank=True)
    provider_trade_name = models.CharField(max_length=120, blank=True)
    provider_registration_status = models.CharField(max_length=60, blank=True)
    provider_opened_on = models.DateField(null=True, blank=True)
    provider_primary_activity = models.CharField(max_length=240, blank=True)
    provider_registry_source = models.CharField(max_length=60, blank=True)
    provider_registry_checked_at = models.DateTimeField(null=True, blank=True)
    support_email = models.EmailField(blank=True)
    support_phone = models.CharField(max_length=24, blank=True)
    privacy_email = models.EmailField(blank=True)
    support_hours = models.CharField(max_length=180, blank=True)
    legal_address = models.CharField(max_length=300, blank=True)
    # This is a product safeguard, not a commercial overage. Every self-service
    # test snapshots the value into its own contract before it becomes usable.
    trial_ai_included_requests = models.PositiveIntegerField(default=0)
    # The local Copilot runtime has not been released yet.  A commercial
    # entitlement alone must never expose it to an accounting office.
    copilot_available_for_offices = models.BooleanField(default=False)
    local_llm_endpoint = models.URLField(blank=True)
    local_llm_model = models.CharField(max_length=100, blank=True)
    local_llm_api_key = EncryptedTextField(blank=True)
    local_multimodal_endpoint = models.URLField(blank=True)
    # Cloud is a last-resort platform capability. The provider credential and
    # budget are never supplied by an accounting office.
    cloud_fallback_enabled = models.BooleanField(default=False)
    cloud_fallback_api_key = EncryptedTextField(blank=True)
    cloud_fallback_model = models.CharField(max_length=80, blank=True)
    cloud_fallback_max_request_cents = models.PositiveIntegerField(default=0)
    cloud_fallback_daily_limit_cents = models.PositiveIntegerField(default=0)
    cloud_fallback_monthly_limit_cents = models.PositiveIntegerField(default=0)
    # Transactional delivery belongs to the platform, never to an accounting office.
    # The password is write-only in the developer console and encrypted at rest.
    transactional_email_host = models.CharField(max_length=255, blank=True)
    transactional_email_port = models.PositiveIntegerField(default=587)
    transactional_email_username = models.CharField(max_length=255, blank=True)
    transactional_email_password = EncryptedTextField(blank=True)
    transactional_email_use_tls = models.BooleanField(default=True)
    transactional_email_from = models.EmailField(blank=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
    )

    @property
    def provider_cnpj_display(self) -> str:
        value = "".join(character for character in self.provider_cnpj if character.isdigit())
        if len(value) != 14:
            return self.provider_cnpj
        return f"{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:]}"


class OperationalRun(UUIDTimeStampedModel):
    """A durable, content-free outcome for an automatically scheduled operation."""

    class Task(models.TextChoices):
        ADVANCE_LIFECYCLES = "advance_lifecycles", "Ciclo de testes e contratos"
        CLOSE_COMPETENCE = "close_competence", "Fechamento de competência"
        REFRESH_KNOWLEDGE = "refresh_knowledge", "Conhecimento dos escritórios"
        REFRESH_SHARED_KNOWLEDGE = "refresh_shared_knowledge", "Conhecimento compartilhado"
        PURGE_INTELLIGENCE = "purge_intelligence", "Retenção do Copiloto"
        RETRY_ATTACHMENTS = "retry_attachments", "Anexos pendentes"
        REFRESH_REFORM = "refresh_reform", "Radar da Reforma"

    class State(models.TextChoices):
        RUNNING = "running", "Em execução"
        SUCCEEDED = "succeeded", "Concluída"
        FAILED = "failed", "Falhou"

    task = models.CharField(max_length=48, choices=Task.choices, db_index=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.RUNNING)
    started_at = models.DateTimeField(default=timezone.now, db_index=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.CharField(max_length=240, blank=True)

    class Meta:
        indexes = [models.Index(fields=("task", "-started_at"))]


class PlatformAccess(UUIDTimeStampedModel):
    class Role(models.TextChoices):
        DEVELOPER = "developer", "Desenvolvedor"
        SUPPORT = "support", "Suporte"
        COMMERCIAL = "commercial", "Comercial"
        ADMIN = "admin", "Administrador da plataforma"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    role = models.CharField(max_length=16, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    mfa_required = models.BooleanField(default=True)


class TenantLifecycle(UUIDTimeStampedModel):
    class State(models.TextChoices):
        PROVISIONING = "provisioning", "Provisionamento"
        ACTIVATION_PENDING = "activation_pending", "Ativação pendente"
        ACTIVE = "active", "Ativo"
        GRACE = "grace", "Carência"
        SUSPENDED = "suspended", "Suspenso"
        ARCHIVED = "archived", "Arquivado"

    organization = models.OneToOneField(
        "organizations.Organization", on_delete=models.PROTECT, related_name="lifecycle"
    )
    state = models.CharField(max_length=24, choices=State.choices, default=State.PROVISIONING)
    retention_until = models.DateField(null=True, blank=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    reason = models.CharField(max_length=240, blank=True)


class DominioSupportTicket(UUIDTimeStampedModel):
    """A concise, auditable request created after a Domínio sync failure."""

    class Status(models.TextChoices):
        OPEN = "open", "Aberto"
        IN_PROGRESS = "in_progress", "Em atendimento"
        RESOLVED = "resolved", "Resolvido"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="dominio_tickets"
    )
    connector = models.ForeignKey(
        "intelligence.IntelligenceConnector",
        on_delete=models.PROTECT,
        related_name="support_tickets",
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = EncryptedTextField(blank=True)
    opened_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="dominio_tickets",
    )

    class Meta:
        indexes = [models.Index(fields=("status", "created_at"))]


class Plan(UUIDTimeStampedModel):
    code = models.SlugField(unique=True, max_length=40)
    name = models.CharField(max_length=100)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    monthly_price_cents = models.PositiveIntegerField(default=0)
    limits = models.JSONField(default=dict)
    modules = models.JSONField(default=list)


class PlanServiceRate(UUIDTimeStampedModel):
    """The contracted allowance and overage price of one central API service."""

    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name="service_rates")
    action_code = models.CharField(max_length=100)
    included_units = models.PositiveIntegerField(default=0)
    overage_unit_price_cents = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("plan", "action_code"), name="platform_unique_plan_service_rate"
            )
        ]


class TenantContract(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        TRIAL = "trial", "Teste gratuito"
        ACTIVE = "active", "Ativo"
        GRACE = "grace", "Carência"
        SUSPENDED = "suspended", "Suspenso"
        ARCHIVED = "archived", "Arquivado"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="contracts"
    )
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.PROTECT)
    # Copied from the plan when the commercial contract is created.  It deliberately
    # never follows later plan-price edits, which keeps an already agreed competence
    # and every invoice reproducible.
    monthly_price_cents = models.PositiveIntegerField(default=0)
    # Distinguishes an approved R$ 0,00 agreement from a new contract that still
    # needs to inherit the catalogue price exactly once.
    monthly_price_locked = models.BooleanField(default=False)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    reference = models.CharField(max_length=120, blank=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    grace_ends_on = models.DateField(null=True, blank=True)
    trial_ends_on = models.DateField(null=True, blank=True)
    renews_on = models.DateField(null=True, blank=True)
    selected_modules = models.JSONField(default=list)
    pending_modules = models.JSONField(default=list)
    cancel_at_period_end = models.BooleanField(default=False)
    asaas_customer_id = models.CharField(max_length=80, blank=True)
    asaas_subscription_id = models.CharField(max_length=80, blank=True)
    notes = models.CharField(max_length=240, blank=True)


class TenantServiceRate(UUIDTimeStampedModel):
    """Price and allowance snapshot agreed in one office contract."""

    contract = models.ForeignKey(
        TenantContract, on_delete=models.CASCADE, related_name="service_rates"
    )
    action_code = models.CharField(max_length=100)
    included_units = models.PositiveIntegerField(default=0)
    overage_unit_price_cents = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("contract", "action_code"),
                name="platform_unique_contract_service_rate",
            )
        ]


class TenantUsagePolicy(UUIDTimeStampedModel):
    """Office-controlled guardrails, constrained by the plan's service rates."""

    class OverageMode(models.TextChoices):
        BLOCK = "block", "Bloquear no limite"
        REQUIRE_APPROVAL = "approval", "Exigir aprovação"
        ALLOW = "allow", "Autorizar excedente"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="usage_policies"
    )
    action_code = models.CharField(max_length=100)
    overage_mode = models.CharField(
        max_length=12, choices=OverageMode.choices, default=OverageMode.BLOCK
    )
    warning_percent = models.PositiveSmallIntegerField(default=80)
    monthly_overage_cap_cents = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "action_code"), name="platform_unique_tenant_usage_policy"
            )
        ]


class UsageMeter(UUIDTimeStampedModel):
    """A monthly, price-snapshotted balance for one office and billable action."""

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="usage_meters"
    )
    action_code = models.CharField(max_length=100)
    period_start = models.DateField()
    period_end = models.DateField()
    included_units = models.PositiveIntegerField(default=0)
    overage_unit_price_cents = models.PositiveIntegerField(default=0)
    reserved_units = models.PositiveIntegerField(default=0)
    consumed_units = models.PositiveIntegerField(default=0)
    overage_units = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "action_code", "period_start"),
                name="platform_unique_usage_meter_period",
            )
        ]


class UsageEvent(UUIDTimeStampedModel):
    """Append-only reservation and settlement record for a central Serpro call."""

    class Status(models.TextChoices):
        RESERVED = "reserved", "Reservado"
        SETTLED = "settled", "Consumido"
        RELEASED = "released", "Liberado"

    meter = models.ForeignKey(UsageMeter, on_delete=models.PROTECT, related_name="events")
    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT)
    action_code = models.CharField(max_length=100)
    idempotency_key = models.CharField(max_length=160, unique=True)
    provider_request_id = models.CharField(max_length=160, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.RESERVED)
    units = models.PositiveIntegerField(default=1)
    overage_cents = models.PositiveIntegerField(default=0)
    provider_http_status = models.PositiveSmallIntegerField(null=True, blank=True)


class Invoice(UUIDTimeStampedModel):
    """One monthly charge: base subscription plus every settled overage in the period."""

    class Status(models.TextChoices):
        OPEN = "open", "Em aberto"
        PAID = "paid", "Paga"
        OVERDUE = "overdue", "Vencida"
        VOID = "void", "Cancelada"
        DISPUTED = "disputed", "Em contestação"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="invoices"
    )
    contract = models.ForeignKey(TenantContract, on_delete=models.PROTECT, related_name="invoices")
    period_start = models.DateField()
    period_end = models.DateField()
    due_on = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.OPEN)
    base_amount_cents = models.PositiveIntegerField(default=0)
    overage_amount_cents = models.PositiveIntegerField(default=0)
    adjustment_amount_cents = models.IntegerField(default=0)
    total_amount_cents = models.PositiveIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "period_start"), name="platform_unique_invoice_competence"
            )
        ]


class InvoiceLine(UUIDTimeStampedModel):
    class Kind(models.TextChoices):
        SUBSCRIPTION = "subscription", "Mensalidade"
        OVERAGE = "overage", "Excedente"
        ADJUSTMENT = "adjustment", "Ajuste"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="lines")
    kind = models.CharField(max_length=16, choices=Kind.choices)
    action_code = models.CharField(max_length=100, blank=True)
    description = models.CharField(max_length=240)
    quantity = models.PositiveIntegerField(default=1)
    unit_amount_cents = models.IntegerField(default=0)
    total_amount_cents = models.IntegerField(default=0)


class PaymentAttempt(UUIDTimeStampedModel):
    class Provider(models.TextChoices):
        INTER = "inter", "Banco Inter"
        ASAAS = "asaas", "Asaas"

    class Method(models.TextChoices):
        PIX = "pix", "Pix"
        BOLETO = "boleto", "Boleto"
        CARD = "card", "Cartão"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        PAID = "paid", "Paga"
        FAILED = "failed", "Falhou"
        CANCELLED = "cancelled", "Cancelada"

    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="payment_attempts")
    provider = models.CharField(max_length=12, choices=Provider.choices)
    method = models.CharField(max_length=12, choices=Method.choices)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    idempotency_key = models.CharField(max_length=160, unique=True)
    external_id = models.CharField(max_length=160, blank=True, db_index=True)
    checkout_url = models.URLField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "external_id"),
                condition=~models.Q(external_id=""),
                name="platform_unique_provider_payment_external_id",
            )
        ]


class PaymentWebhookDelivery(UUIDTimeStampedModel):
    """Provider event receipt ledger; the provider event id is the idempotency boundary."""

    provider = models.CharField(max_length=12, choices=PaymentAttempt.Provider.choices)
    event_id = models.CharField(max_length=160)
    event_name = models.CharField(max_length=80)
    external_id = models.CharField(max_length=160)
    payment_attempt = models.ForeignKey(
        PaymentAttempt,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="webhook_deliveries",
    )

    class ProcessingStatus(models.TextChoices):
        PROCESSED = "processed", "Processado"
        IGNORED = "ignored", "Ignorado"
        FAILED = "failed", "Falhou"

    processing_status = models.CharField(
        max_length=12, choices=ProcessingStatus.choices, default=ProcessingStatus.PROCESSED
    )
    error_code = models.CharField(max_length=80, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("provider", "event_id"), name="platform_unique_payment_webhook_event"
            )
        ]


class Entitlement(UUIDTimeStampedModel):
    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.CASCADE, related_name="entitlements"
    )
    code = models.CharField(max_length=48)
    enabled = models.BooleanField(default=False)
    limit = models.PositiveIntegerField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "code"), name="platform_unique_entitlement"
            )
        ]


class FeatureFlag(UUIDTimeStampedModel):
    key = models.SlugField(unique=True, max_length=64)
    enabled = models.BooleanField(default=False)
    organization = models.ForeignKey(
        "organizations.Organization", null=True, blank=True, on_delete=models.CASCADE
    )
    expires_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=200, blank=True)


class Invitation(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        ACCEPTED = "accepted", "Aceito"
        REVOKED = "revoked", "Revogado"
        EXPIRED = "expired", "Expirado"

    organization = models.ForeignKey("organizations.Organization", on_delete=models.CASCADE)
    email = models.EmailField()
    full_name = models.CharField(max_length=150, blank=True)
    role = models.CharField(max_length=16)
    company_ids = models.JSONField(default=list)
    # Empty means an unrestricted legacy/platform invitation. Workspace-issued
    # collaborator invitations always carry their explicit module scope here.
    modules = models.JSONField(default=list)
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    accepted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="accepted_hub_invitations",
    )

    @classmethod
    def issue_token(cls) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        return token, hashlib.sha256(token.encode()).hexdigest()

    def usable(self) -> bool:
        return self.status == self.Status.PENDING and self.expires_at > timezone.now()


class SupportSession(UUIDTimeStampedModel):
    class AccessMode(models.TextChoices):
        READ_ONLY = "read_only", "Somente leitura"
        FULL = "full", "Teste completo"

    class Status(models.TextChoices):
        OPEN = "open", "Aberta"
        CLOSED = "closed", "Encerrada"
        EXPIRED = "expired", "Expirada"

    organization = models.ForeignKey("organizations.Organization", on_delete=models.PROTECT)
    support_user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    justification = models.CharField(max_length=500)
    company_ids = models.JSONField(default=list)
    control_grant_hash = models.CharField(max_length=64, blank=True)
    access_mode = models.CharField(
        max_length=16, choices=AccessMode.choices, default=AccessMode.READ_ONLY
    )
    expires_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    closed_at = models.DateTimeField(null=True, blank=True)

    def usable(self) -> bool:
        return self.status == self.Status.OPEN and self.expires_at > timezone.now()

    @property
    def can_mutate(self) -> bool:
        return self.access_mode == self.AccessMode.FULL


class Lead(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        NEW = "new", "Novo"
        QUALIFIED = "qualified", "Qualificado"
        CLOSED = "closed", "Encerrado"

    # A lead is written by an anonymous visitor and read by nobody in the product, so
    # its contact details get the same custody as every other personal field here.
    office_name = EncryptedTextField()
    contact_name = EncryptedTextField()
    contact_email = EncryptedTextField(validators=[EmailValidator()])
    cnpj = EncryptedTextField(blank=True, default="")
    registry_data = EncryptedTextField(blank=True, default="")
    company_count = models.PositiveIntegerField(null=True, blank=True)
    message = EncryptedTextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)


class SignupIntent(UUIDTimeStampedModel):
    """Verified, single-use public signup state; no plaintext password is retained."""

    email = models.EmailField(max_length=254, db_index=True)
    full_name = models.CharField(max_length=150)
    password_hash = models.CharField(max_length=256)
    office_name = models.CharField(max_length=180)
    cnpj = EncryptedTextField()
    cnpj_hash = models.CharField(max_length=64, db_index=True)
    company_count = models.PositiveIntegerField()
    selected_modules = models.JSONField(default=list)
    trial_ai_included_requests = models.PositiveIntegerField(default=0)
    quoted_monthly_cents = models.PositiveIntegerField()
    terms_version = models.CharField(max_length=32)
    privacy_version = models.CharField(max_length=32, blank=True)
    terms_accepted_at = models.DateTimeField(null=True, blank=True)
    terms_acceptance_ip_hash = models.CharField(max_length=64, blank=True)
    marketing_opt_in = models.BooleanField(default=False)
    marketing_opted_in_at = models.DateTimeField(null=True, blank=True)
    marketing_opt_in_ip_hash = models.CharField(max_length=64, blank=True)
    token_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    verified_at = models.DateTimeField(null=True, blank=True)
    organization = models.OneToOneField(
        "organizations.Organization", null=True, blank=True, on_delete=models.SET_NULL
    )

    @classmethod
    def issue_token(cls) -> tuple[str, str]:
        token = secrets.token_urlsafe(32)
        return token, hashlib.sha256(token.encode()).hexdigest()

    def usable(self) -> bool:
        return (
            self.verified_at is None
            and self.organization_id is None
            and self.expires_at > timezone.now()
        )
