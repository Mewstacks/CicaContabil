from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Any, NoReturn

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.base import ModelBase
from django.utils import timezone

from apps.common.encryption import EncryptedTextField
from apps.common.models import AppendOnlyQuerySet, UUIDTimeStampedModel
from apps.organizations.models import Membership, OrganizationScopedModel


def private_import_path(instance: ImportBatch, filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"private/imports/{instance.organization_id}/{instance.id}.{suffix}"


def private_reconciliation_path(instance: models.Model, filename: str) -> str:
    """Keep financial evidence private and unguessable in the configured storage."""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return (
        f"private/reconciliation/{instance.organization_id}/{instance.pk or uuid.uuid4()}.{suffix}"
    )


class OfficeProfile(OrganizationScopedModel):
    class ContractStatus(models.TextChoices):
        TRIAL = "trial", "Em carência"
        ACTIVE = "active", "Ativo"
        SUSPENDED = "suspended", "Suspenso"

    organization = models.OneToOneField(
        "organizations.Organization", on_delete=models.CASCADE, related_name="hub_profile"
    )
    legal_name = models.CharField(max_length=180, blank=True)
    cnpj = EncryptedTextField(blank=True)
    cnpj_hash = models.CharField(max_length=64, blank=True, db_index=True)
    contract_status = models.CharField(
        max_length=16, choices=ContractStatus.choices, default=ContractStatus.TRIAL
    )
    grace_ends_at = models.DateField(null=True, blank=True)
    reference_invoice_note = models.CharField(max_length=240, blank=True)
    require_mfa = models.BooleanField(default=False)
    trial_started_at = models.DateTimeField(null=True, blank=True, editable=False)
    # The Domínio code is the identity every downstream integration joins on: the mirror
    # looks companies up by it, the NFS-e sync keys on it, and DTE evidence is filed under
    # it. An office that works against Domínio turns this on so a company cannot be
    # registered without the key that makes it addressable.
    require_dominio_code = models.BooleanField(default=False)


class ProductModule(OrganizationScopedModel):
    class Code(models.TextChoices):
        NFSE = "nfse", "NFS-e Inteligente"
        GUIDES = "guides", "Guias e DCTFWeb"
        INTEGRA = "integra", "Central Integra Contador"
        RECONCILIATION = "reconciliation", "Conciliação OFX x Domínio"
        REFORM = "reform", "Radar da Reforma Tributária"

        JOURNEY = "journey", "Jornadas"
        AI = "ai", "Copiloto CICA"
        TRIAGE = "triage", "Triagem de Arquivos"

    code = models.CharField(max_length=32, choices=Code.choices)
    enabled = models.BooleanField(default=False)
    enabled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "code"), name="hub_unique_module_per_office"
            )
        ]


class UsageAllowance(OrganizationScopedModel):
    class Metric(models.TextChoices):
        COMPANIES = "companies", "Empresas"
        USERS = "users", "Usuários"
        DOCUMENTS = "documents", "Documentos/mês"

    metric = models.CharField(max_length=24, choices=Metric.choices)
    included = models.PositiveIntegerField(default=0)
    consumed = models.PositiveIntegerField(default=0)
    period_start = models.DateField()
    period_end = models.DateField()

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "metric", "period_start"), name="hub_unique_usage_period"
            )
        ]


class ClientCompany(OrganizationScopedModel):
    name = models.CharField(max_length=180)
    cnpj_masked = models.CharField(max_length=18, blank=True)
    dominio_code = models.CharField(max_length=64, blank=True, db_index=True)
    active = models.BooleanField(default=True)
    last_dominio_sync_at = models.DateTimeField(null=True, blank=True)
    data_source = models.ForeignKey(
        "DataSource", null=True, blank=True, on_delete=models.SET_NULL, related_name="companies"
    )
    external_key = models.CharField(max_length=160, blank=True, db_index=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "dominio_code"),
                condition=models.Q(dominio_code__gt=""),
                name="hub_unique_dominio_company_code",
            ),
            models.UniqueConstraint(
                fields=("data_source", "external_key"),
                condition=models.Q(data_source__isnull=False, external_key__gt=""),
                name="hub_unique_company_source_key",
            ),
        ]

    def __str__(self) -> str:
        return self.name


class ClientJourney(OrganizationScopedModel):
    """An office-owned internal workboard with an explicit company boundary."""

    class Status(models.TextChoices):
        ACTIVE = "active", "Em andamento"
        PAUSED = "paused", "Pausada"
        COMPLETED = "completed", "Concluída"

    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE, related_name="journeys")
    title = models.CharField(max_length=160)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    owner = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="owned_journeys",
    )
    due_on = models.DateField(null=True, blank=True)
    portal_visible = models.BooleanField(default=False)

    class Meta:
        ordering = ("due_on", "-created_at")
        indexes = [models.Index(fields=("organization", "company", "status"))]

    def clean(self) -> None:
        super().clean()
        if self.company_id and self.company.organization_id != self.organization_id:
            raise ValidationError("A jornada precisa pertencer ao mesmo escritório da empresa.")


class JourneyStep(OrganizationScopedModel):
    journey = models.ForeignKey(ClientJourney, on_delete=models.CASCADE, related_name="steps")
    title = models.CharField(max_length=160)
    description = models.TextField(blank=True)
    position = models.PositiveSmallIntegerField(default=1)
    due_on = models.DateField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    portal_visible = models.BooleanField(default=False)

    class Meta:
        ordering = ("position", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("journey", "position"),
                name="hub_unique_journey_step_position",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.journey_id and self.journey.organization_id != self.organization_id:
            raise ValidationError("A etapa precisa pertencer ao mesmo escritório da jornada.")


class PortalRequest(OrganizationScopedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Aberta"
        RECEIVED = "received", "Recebida"
        RESOLVED = "resolved", "Concluída"

    journey = models.ForeignKey(ClientJourney, on_delete=models.CASCADE, related_name="requests")
    title = models.CharField(max_length=160)
    details = models.TextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    due_on = models.DateField(null=True, blank=True)
    # Kept only for compatibility with historical records. CICA does not expose
    # a client-facing portal; every new internal pendency is private by default.
    portal_visible = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("due_on", "-created_at")

    def clean(self) -> None:
        super().clean()
        if self.journey_id and self.journey.organization_id != self.organization_id:
            raise ValidationError("A solicitação precisa pertencer ao mesmo escritório da jornada.")


class CompanyAccessGrant(OrganizationScopedModel):
    """The effective company boundary for a user, normally synchronized from CRMew."""

    membership = models.ForeignKey(
        Membership, on_delete=models.CASCADE, related_name="company_grants"
    )
    company = models.ForeignKey(
        ClientCompany, on_delete=models.CASCADE, related_name="access_grants"
    )
    modules = models.JSONField(default=list)
    capabilities = models.JSONField(default=list)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("membership", "company"), name="hub_unique_company_access_grant"
            )
        ]
        indexes = [models.Index(fields=("organization", "membership", "is_active"))]

    def clean(self) -> None:
        super().clean()
        if self.membership_id and self.membership.organization_id != self.organization_id:
            raise ValidationError("O acesso precisa pertencer ao mesmo escritório.")
        if self.company_id and self.company.organization_id != self.organization_id:
            raise ValidationError("A empresa precisa pertencer ao mesmo escritório.")


class ControlPlaneBinding(UUIDTimeStampedModel):
    """Local trust anchor and signed authorization cache for one CRMew-managed office."""

    organization = models.OneToOneField(
        "organizations.Organization", on_delete=models.CASCADE, related_name="control_plane_binding"
    )
    remote_installation_id = models.UUIDField(unique=True)
    controller_url = models.URLField()
    device_private_key = EncryptedTextField()
    controller_public_key = models.CharField(max_length=120)
    cached_control = models.JSONField(default=dict)
    cache_expires_at = models.DateTimeField(null=True, blank=True)
    applied_configuration_version = models.PositiveBigIntegerField(default=0)
    last_sync_at = models.DateTimeField(null=True, blank=True)
    last_sync_error = models.CharField(max_length=240, blank=True)


class RemoteSupportGrant(OrganizationScopedModel):
    """A short-lived CRMew authorization; it is not a permanent Hub membership."""

    subject = models.CharField(max_length=254)
    company_ids = models.JSONField(default=list)
    justification = models.CharField(max_length=500)
    expires_at = models.DateTimeField(db_index=True)
    source_hash = models.CharField(max_length=64, unique=True)


class Certificate(OrganizationScopedModel):
    """Central certificate custody; raw PFX and password are never sent back to the UI."""

    company = models.ForeignKey(
        ClientCompany, on_delete=models.CASCADE, related_name="certificates"
    )
    label = models.CharField(max_length=120)
    subject_name = models.CharField(max_length=240, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_until = models.DateTimeField(null=True, blank=True, db_index=True)
    pfx_blob = EncryptedTextField()
    password = EncryptedTextField()
    fingerprint_sha256 = models.CharField(max_length=64, db_index=True)
    uploaded_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="uploaded_certificates"
    )
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=("organization", "valid_until"))]


class NfseSync(OrganizationScopedModel):
    class Status(models.TextChoices):
        PAUSED = "paused", "Pausada"
        IDLE = "idle", "Aguardando"
        RUNNING = "running", "Sincronizando"
        RETRY = "retry", "Nova tentativa agendada"
        ERROR = "error", "Requer atenção"

    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE, related_name="nfse_syncs")
    certificate = models.ForeignKey(Certificate, null=True, blank=True, on_delete=models.SET_NULL)
    enabled = models.BooleanField(default=False)
    checkpoint_nsu = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.PAUSED)
    last_error_code = models.CharField(max_length=80, blank=True)
    last_error_message = models.CharField(max_length=500, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)
    last_batch_count = models.PositiveSmallIntegerField(default=0)
    failure_count = models.PositiveSmallIntegerField(default=0)
    lease_token = models.UUIDField(null=True, blank=True, editable=False)
    lease_until = models.DateTimeField(null=True, blank=True, editable=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company"), name="hub_unique_nfse_sync_company"
            )
        ]


class ImmutableOrganizationModel(OrganizationScopedModel):
    """Business evidence can be inserted, but never overwritten or erased in-app."""

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        abstract = True

    def save(
        self,
        *,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        if not self._state.adding:
            raise ValidationError("Fiscal evidence is immutable and cannot be changed.")
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=update_fields,
        )

    def delete(self, using: Any | None = None, keep_parents: bool = False) -> NoReturn:
        raise ValidationError("Fiscal evidence cannot be deleted through the application.")


class NfseDocument(ImmutableOrganizationModel):
    company = models.ForeignKey(
        ClientCompany, on_delete=models.PROTECT, related_name="nfse_documents"
    )
    source_nsu = models.CharField(max_length=80, blank=True, db_index=True)
    document_hash = models.CharField(max_length=64, db_index=True)
    original_xml = EncryptedTextField()
    normalized_data = models.JSONField(default=dict)
    issued_at = models.DateTimeField(null=True, blank=True)
    captured_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-captured_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "document_hash"),
                name="hub_unique_nfse_company_document_hash",
            ),
            models.UniqueConstraint(
                fields=("organization", "company", "source_nsu"),
                condition=models.Q(source_nsu__gt=""),
                name="hub_unique_nfse_company_source_nsu",
            ),
        ]


class AccumulatorRule(OrganizationScopedModel):
    company = models.ForeignKey(
        ClientCompany, on_delete=models.CASCADE, related_name="accumulator_rules"
    )
    name = models.CharField(max_length=120)
    priority = models.PositiveIntegerField(default=100)
    match = models.JSONField(default=dict)
    accumulator_code = models.CharField(max_length=80)
    active = models.BooleanField(default=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_until = models.DateField(null=True, blank=True)
    is_transitory = models.BooleanField(default=False)

    class Meta:
        ordering = ("priority", "name")


class AccumulatorObservation(OrganizationScopedModel):
    company = models.ForeignKey(
        ClientCompany, on_delete=models.CASCADE, related_name="accumulator_observations"
    )
    accumulator_code = models.CharField(max_length=80)
    service_code = models.CharField(max_length=60, blank=True)
    counterparty_ref = models.CharField(max_length=80, blank=True)
    frequency = models.PositiveIntegerField(default=1)
    last_used_at = models.DateTimeField(db_index=True)


class ReviewCase(OrganizationScopedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Aberta"
        RESOLVED = "resolved", "Resolvida"

    document = models.OneToOneField(
        NfseDocument, on_delete=models.PROTECT, related_name="review_case"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    reason = models.CharField(max_length=180)
    suggested_accumulator = models.CharField(max_length=80, blank=True)
    confidence = models.PositiveSmallIntegerField(default=0)
    resolved_accumulator = models.CharField(max_length=80, blank=True)
    resolved_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_nfse_cases",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)


class IntegrationArtifact(ImmutableOrganizationModel):
    document = models.ForeignKey(
        NfseDocument, on_delete=models.PROTECT, related_name="integration_artifacts"
    )
    accumulator_code = models.CharField(max_length=80)
    applied_rule = models.CharField(max_length=120, blank=True)
    confidence = models.PositiveSmallIntegerField(default=0)
    evidence = models.JSONField(default=dict)
    export_format = models.CharField(max_length=32, default="hub-nfse-v1")
    payload = models.JSONField(default=dict)


class DataSource(OrganizationScopedModel):
    """One office-owned source feeding normalized CICA records."""

    class Kind(models.TextChoices):
        DOMINIO_LOCAL_AGENT = "dominio_local_agent", "Domínio Local (agente)"
        DOMINIO_WEB_BACKUP = "dominio_web_backup", "Domínio Web (backup manual)"
        SIESCON = "siescon", "Siescon"
        OTHER_MANUAL = "other_manual", "Outro sistema (importação manual)"
        DOMINIO_OFFICIAL_API = "dominio_official_api", "Domínio API oficial"

    class Status(models.TextChoices):
        NOT_CONFIGURED = "not_configured", "Não configurada"
        READY = "ready", "Pronta"
        PROCESSING = "processing", "Processando"
        ATTENTION = "attention", "Requer atenção"
        DISABLED = "disabled", "Desativada"

    kind = models.CharField(max_length=32, choices=Kind.choices)
    label = models.CharField(max_length=120)
    status = models.CharField(max_length=24, choices=Status.choices, default=Status.NOT_CONFIGURED)
    capabilities = models.JSONField(default=list)
    last_import_at = models.DateTimeField(null=True, blank=True)
    source_snapshot_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    last_error_message = models.CharField(max_length=240, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "kind"), name="hub_unique_data_source_kind"
            )
        ]


class ImportBatch(OrganizationScopedModel):
    """A bounded, auditable manual import; raw files are discarded after processing."""

    class Kind(models.TextChoices):
        COMPANIES = "companies", "Empresas"
        OBLIGATIONS = "obligations", "Obrigações e guias"
        ACCOUNTING = "accounting", "Lançamentos contábeis"
        FISCAL_XML = "fiscal_xml", "Documentos fiscais XML"
        BANK_OFX = "bank_ofx", "Extratos bancários OFX"
        DOMINIO_BACKUP = "dominio_backup", "Backup completo Domínio Web"

    class Status(models.TextChoices):
        PREVIEW = "preview", "Aguardando confirmação"
        QUEUED = "queued", "Na fila de extração"
        PROCESSING = "processing", "Processando"
        COMPLETED = "completed", "Concluído"
        FAILED = "failed", "Falhou"

    data_source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="imports")
    kind = models.CharField(max_length=24, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PREVIEW)
    original_filename = models.CharField(max_length=255)
    content_hash = models.CharField(max_length=64)
    template_version = models.PositiveSmallIntegerField(default=1)
    mapping = models.JSONField(default=dict)
    encrypted_payload = EncryptedTextField(blank=True)
    source_file = models.FileField(upload_to=private_import_path, blank=True)
    backup_key = EncryptedTextField(blank=True)
    source_snapshot_at = models.DateTimeField(null=True, blank=True)
    row_count = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    ignored_count = models.PositiveIntegerField(default=0)
    errors = models.JSONField(default=list)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="imports"
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "data_source", "kind", "content_hash"),
                name="hub_unique_import_batch_content",
            )
        ]


class AccountingEntry(OrganizationScopedModel):
    """Source-neutral accounting entry used by reconciliation and future adapters."""

    data_source = models.ForeignKey(DataSource, on_delete=models.PROTECT, related_name="entries")
    source_batch = models.ForeignKey(
        ImportBatch, null=True, blank=True, on_delete=models.SET_NULL, related_name="entries"
    )
    company = models.ForeignKey(
        ClientCompany, null=True, blank=True, on_delete=models.SET_NULL, related_name="entries"
    )
    external_key = models.CharField(max_length=160)
    occurred_on = models.DateField(db_index=True)
    description = models.CharField(max_length=500, blank=True)
    amount_cents = models.BigIntegerField()
    direction = models.CharField(max_length=8, blank=True)
    is_linked = models.BooleanField(default=False)
    source_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-occurred_on", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("data_source", "external_key"), name="hub_unique_accounting_source_key"
            )
        ]
        indexes = [models.Index(fields=("organization", "company", "occurred_on"))]


class Connector(OrganizationScopedModel):
    class Kind(models.TextChoices):
        DOMINIO_AGENT = "dominio_agent", "Agente Domínio local"
        ONVIO = "onvio", "Onvio API"
        SIESCON = "siescon", "Siescon"
        INTEGRA = "integra", "Integra Contador"

    kind = models.CharField(max_length=32, choices=Kind.choices)
    enabled = models.BooleanField(default=False)
    status = models.CharField(max_length=24, default="not_configured")
    encrypted_configuration = EncryptedTextField(blank=True)
    last_checked_at = models.DateTimeField(null=True, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "kind"), name="hub_unique_connector_per_office"
            )
        ]


class ConsumptionConfirmation(OrganizationScopedModel):
    """An explicit approval gate before a billable Serpro action can be dispatched."""

    # Serpro credentials belong to CICA. This nullable historic link only
    # preserves confirmations created before central contracting.
    connector = models.ForeignKey(
        Connector,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="confirmations",
    )
    action_code = models.CharField(max_length=100)
    scope_summary = models.CharField(max_length=240)
    estimated_units = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, default="pending")
    confirmed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="serpro_confirmations",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)


class DteRun(OrganizationScopedModel):
    """A prepared Caixa Postal consultation. Preparing a run never calls Serpro."""

    class Status(models.TextChoices):
        AWAITING_APPROVAL = "awaiting_approval", "Aguardando autoriza\u00e7\u00e3o"
        QUEUED = "queued", "Na fila"
        RUNNING = "running", "Em consulta"
        COMPLETED = "completed", "Conclu\u00edda"
        PARTIAL = "partial", "Conclu\u00edda com pend\u00eancias"
        FAILED = "failed", "N\u00e3o conclu\u00edda"
        CANCELLED = "cancelled", "Cancelada"

    connector = models.ForeignKey(
        Connector, null=True, blank=True, on_delete=models.SET_NULL, related_name="dte_runs"
    )
    status = models.CharField(
        max_length=24, choices=Status.choices, default=Status.AWAITING_APPROVAL
    )
    requested_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="dte_runs"
    )
    requested_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    total_companies = models.PositiveIntegerField(default=0)
    completed_companies = models.PositiveIntegerField(default=0)
    messages_found = models.PositiveIntegerField(default=0)
    error_summary = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ("-requested_at",)
        indexes = [
            models.Index(
                fields=["organization", "status", "requested_at"],
                name="hub_dterun_organiz_8421d3_idx",
            )
        ]


class DteRunItem(OrganizationScopedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Aguardando"
        RUNNING = "running", "Em consulta"
        COMPLETED = "completed", "Conclu\u00edda"
        FAILED = "failed", "Falhou"
        SKIPPED = "skipped", "Ignorada"

    run = models.ForeignKey(DteRun, on_delete=models.CASCADE, related_name="items")
    company = models.ForeignKey(
        ClientCompany, on_delete=models.PROTECT, related_name="dte_run_items"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    messages_found = models.PositiveIntegerField(default=0)
    more_available = models.BooleanField(default=False)
    requested_page_pointer = models.CharField(max_length=24, blank=True)
    next_page_pointer = models.CharField(max_length=24, blank=True)
    continued_from = models.OneToOneField(
        "self", null=True, blank=True, on_delete=models.PROTECT, related_name="continuation"
    )
    service_response_id = models.CharField(max_length=120, blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.CharField(max_length=240, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    token_usage_event = models.ForeignKey(
        "platform.TokenUsageEvent", null=True, blank=True, on_delete=models.PROTECT
    )
    usage_event = models.ForeignKey(
        "platform.UsageEvent", null=True, blank=True, on_delete=models.PROTECT
    )

    class Meta:
        ordering = ("company__name",)
        constraints = [
            models.UniqueConstraint(fields=("run", "company"), name="hub_unique_dte_run_company")
        ]
        indexes = [
            models.Index(
                fields=["organization", "company", "status"],
                name="hub_dteruni_organiz_4b0b65_idx",
            )
        ]


class DteMessage(ImmutableOrganizationModel):
    """Immutable first observation returned by the Caixa Postal service."""

    company = models.ForeignKey(
        ClientCompany, on_delete=models.PROTECT, related_name="dte_messages"
    )
    source_isn = models.CharField(max_length=120)
    subject = models.CharField(max_length=500)
    sender = models.CharField(max_length=240, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    read_at = models.DateTimeField(null=True, blank=True)
    source_science_at = models.DateTimeField(null=True, blank=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    raw_payload = EncryptedTextField(blank=True)

    class Meta:
        ordering = ("-sent_at", "-first_seen_at")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "source_isn"),
                name="hub_unique_dte_message_source",
            )
        ]
        indexes = [
            models.Index(
                fields=["organization", "company", "sent_at"],
                name="hub_dtemess_organiz_a0a7f2_idx",
            )
        ]


class DteMessageObservation(ImmutableOrganizationModel):
    """Append-only proof of each list response that mentioned a message."""

    message = models.ForeignKey(DteMessage, on_delete=models.PROTECT, related_name="observations")
    run_item = models.ForeignKey(
        DteRunItem, on_delete=models.PROTECT, related_name="message_observations"
    )
    observed_at = models.DateTimeField(default=timezone.now)
    read_at = models.DateTimeField(null=True, blank=True)
    science_at = models.DateTimeField(null=True, blank=True)
    raw_payload = EncryptedTextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("run_item", "message"), name="hub_unique_dte_list_observation"
            )
        ]


class DteMessageState(OrganizationScopedModel):
    """Current queue state, backed by immutable list observations."""

    message = models.OneToOneField(
        DteMessage, on_delete=models.PROTECT, related_name="current_state"
    )
    read_at = models.DateTimeField(null=True, blank=True)
    science_at = models.DateTimeField(null=True, blank=True)
    last_seen_at = models.DateTimeField(default=timezone.now)
    last_observation = models.ForeignKey(
        DteMessageObservation, null=True, blank=True, on_delete=models.PROTECT
    )


class DteMessageAccess(OrganizationScopedModel):
    """One auditable provider detail request, which itself may give legal notice."""

    class Status(models.TextChoices):
        READING = "reading", "Abertura em andamento"
        OPENED = "opened", "Teor consultado"
        FAILED = "failed", "Consulta recusada"
        UNKNOWN = "unknown", "Resultado a confirmar"

    message = models.OneToOneField(
        DteMessage, on_delete=models.PROTECT, related_name="access_receipt"
    )
    status = models.CharField(max_length=16, choices=Status.choices)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    requested_by = models.ForeignKey(
        "accounts.User", null=True, on_delete=models.SET_NULL, related_name="dte_detail_requests"
    )
    requested_at = models.DateTimeField(default=timezone.now)
    opened_at = models.DateTimeField(null=True, blank=True)
    provider_read_at = models.DateTimeField(null=True, blank=True)
    provider_science_at = models.DateTimeField(null=True, blank=True)
    provider_request_id = models.CharField(max_length=160, blank=True)
    provider_payload = EncryptedTextField(blank=True)
    error_message = models.CharField(max_length=240, blank=True)
    token_usage_event = models.ForeignKey(
        "platform.TokenUsageEvent", null=True, blank=True, on_delete=models.PROTECT
    )
    usage_event = models.ForeignKey(
        "platform.UsageEvent", null=True, blank=True, on_delete=models.PROTECT
    )

    class Meta:
        indexes = [models.Index(fields=("organization", "status", "requested_at"))]


class FiscalGuide(OrganizationScopedModel):
    """An obligation received from Domínio and optionally issued through the central API."""

    class Kind(models.TextChoices):
        DCTFWEB = "dctfweb", "DCTFWeb"
        DAS = "das", "DAS Simples Nacional"
        MEI = "mei", "DAS MEI"

    class Status(models.TextChoices):
        DISCOVERED = "discovered", "Apuração a conferir"
        READY = "ready", "Pronta para emitir"
        QUEUED = "queued", "Na fila"
        ISSUING = "issuing", "Emitindo"
        ISSUED = "issued", "Emitida"
        FAILED = "failed", "Não emitida"
        SKIPPED = "skipped", "Dispensada"

    company = models.ForeignKey(
        ClientCompany, on_delete=models.PROTECT, related_name="fiscal_guides"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.READY)
    reference = models.CharField(max_length=120)
    competence = models.CharField(max_length=7)
    due_on = models.DateField(db_index=True)
    amount_cents = models.PositiveIntegerField(default=0)
    integra_service_key = models.CharField(max_length=100)
    issue_attempt = models.PositiveSmallIntegerField(default=0)
    provider_request_id = models.CharField(max_length=160, blank=True)
    provider_payload = EncryptedTextField(blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.CharField(max_length=240, blank=True)
    issue_requested_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requested_fiscal_guides",
    )
    issue_requested_at = models.DateTimeField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    data_source = models.ForeignKey(
        DataSource, null=True, blank=True, on_delete=models.SET_NULL, related_name="fiscal_guides"
    )
    source_batch = models.ForeignKey(
        ImportBatch, null=True, blank=True, on_delete=models.SET_NULL, related_name="fiscal_guides"
    )
    external_key = models.CharField(max_length=160, blank=True, db_index=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("due_on", "company__name", "reference")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "reference"),
                name="hub_unique_fiscal_guide_reference",
            )
        ]
        indexes = [
            models.Index(
                fields=["organization", "status", "due_on"],
                name="hub_fguide_org_stat_due_idx",
            )
        ]


class DctfWebDocument(OrganizationScopedModel):
    """One paid DCTFWeb document consultation for a company and competence."""

    class Kind(models.TextChoices):
        DECLARATION = "declaration", "Declaração completa"
        RECEIPT = "receipt", "Recibo de transmissão"

    class Status(models.TextChoices):
        QUEUED = "queued", "Na fila"
        FETCHING = "fetching", "Consultando"
        AVAILABLE = "available", "Disponível"
        FAILED = "failed", "Não obtido"
        UNKNOWN = "unknown", "Resultado a confirmar"

    company = models.ForeignKey(
        ClientCompany, on_delete=models.PROTECT, related_name="dctfweb_documents"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    competence = models.CharField(max_length=7)
    service_key = models.CharField(max_length=100)
    attempt = models.PositiveSmallIntegerField(default=0)
    usage_event = models.ForeignKey(
        "platform.UsageEvent", null=True, blank=True, on_delete=models.PROTECT
    )
    token_usage_event = models.ForeignKey(
        "platform.TokenUsageEvent", null=True, blank=True, on_delete=models.PROTECT
    )
    requested_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="requested_dctfweb_documents",
    )
    requested_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    provider_request_id = models.CharField(max_length=160, blank=True)
    provider_payload = EncryptedTextField(blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ("-requested_at", "company__name", "competence", "kind")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "competence", "kind"),
                name="hub_unique_dctfweb_document",
            )
        ]
        indexes = [
            models.Index(
                fields=("organization", "status", "requested_at"),
                name="hub_dctfdoc_org_stat_req_idx",
            )
        ]


class ParcelamentoOperation(OrganizationScopedModel):
    """One explicitly authorized PARCSN request and its encrypted provider evidence."""

    class Kind(models.TextChoices):
        ORDERS = "orders", "Pedidos"
        DETAIL = "detail", "Detalhe do acordo"
        INSTALLMENTS = "installments", "Parcelas disponíveis"
        DAS = "das", "DAS da parcela"

    class Status(models.TextChoices):
        QUEUED = "queued", "Na fila"
        FETCHING = "fetching", "Consultando"
        AVAILABLE = "available", "Disponível"
        EMPTY = "empty", "Nenhum resultado"
        FAILED = "failed", "Não concluída"
        UNKNOWN = "unknown", "Resultado a confirmar"

    company = models.ForeignKey(
        ClientCompany, on_delete=models.PROTECT, related_name="parcelamento_operations"
    )
    kind = models.CharField(max_length=16, choices=Kind.choices)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    service_key = models.CharField(max_length=100)
    agreement_number = models.PositiveBigIntegerField(null=True, blank=True)
    competence = models.CharField(max_length=6, blank=True)
    attempt = models.PositiveSmallIntegerField(default=0)
    token_usage_event = models.ForeignKey(
        "platform.TokenUsageEvent", null=True, blank=True, on_delete=models.PROTECT
    )
    requested_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    requested_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    provider_request_id = models.CharField(max_length=160, blank=True)
    provider_payload = EncryptedTextField(blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ("-requested_at",)
        indexes = [
            models.Index(
                fields=("organization", "status", "requested_at"),
                name="hub_parcop_org_stat_req_idx",
            )
        ]


class ReformAlert(UUIDTimeStampedModel):
    """An official public update collected once for every office to consult."""

    class Source(models.TextChoices):
        RFB = "rfb", "Receita Federal"
        FAZENDA = "fazenda", "Ministério da Fazenda"
        PLANALTO = "planalto", "Planalto"

    class Relevance(models.TextChoices):
        REFORM = "reform", "Reforma tributária"
        FISCAL = "fiscal", "Fiscal"
        GENERAL = "general", "Geral"

    source = models.CharField(max_length=16, choices=Source.choices)
    external_key = models.CharField(max_length=64)
    title = models.CharField(max_length=360)
    source_url = models.URLField(max_length=1_500)
    summary = models.TextField(blank=True)
    published_at = models.DateTimeField(null=True, blank=True, db_index=True)
    relevance = models.CharField(
        max_length=16, choices=Relevance.choices, default=Relevance.GENERAL
    )
    content_hash = models.CharField(max_length=64)

    class Meta:
        ordering = ("-published_at", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("source", "external_key"), name="hub_unique_reform_alert_source"
            )
        ]
        indexes = [models.Index(fields=["source", "relevance", "published_at"])]


class ReformSourceStatus(UUIDTimeStampedModel):
    """Latest daily collection result per public source, without storing raw fetches."""

    source = models.CharField(max_length=16, choices=ReformAlert.Source.choices, unique=True)
    last_collected_at = models.DateTimeField(null=True, blank=True)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=240, blank=True)
    items_seen = models.PositiveIntegerField(default=0)


class BankStatementImport(OrganizationScopedModel):
    """A parsed OFX file; source bytes are discarded after validation and extraction."""

    company = models.ForeignKey(
        ClientCompany, on_delete=models.PROTECT, related_name="bank_statement_imports"
    )
    original_filename = models.CharField(max_length=255)
    content_hash = models.CharField(max_length=64)
    account_reference = models.CharField(max_length=160, blank=True)
    transaction_count = models.PositiveIntegerField(default=0)
    imported_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ofx_imports",
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "content_hash"),
                name="hub_unique_bank_statement_content",
            )
        ]


class BankTransaction(OrganizationScopedModel):
    """Normalized OFX transaction ready to be matched to an approved Domínio ledger source."""

    statement = models.ForeignKey(
        BankStatementImport, on_delete=models.CASCADE, related_name="transactions"
    )
    external_id = models.CharField(max_length=160)
    occurred_on = models.DateField(db_index=True)
    description = models.CharField(max_length=500)
    amount_cents = models.BigIntegerField()

    class Meta:
        ordering = ("-occurred_on", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("statement", "external_id"), name="hub_unique_bank_transaction_source"
            )
        ]
        indexes = [models.Index(fields=["organization", "occurred_on"])]


class DominioBankEntry(OrganizationScopedModel):
    """Read-only mirror of a Domínio bank-statement item, never a journal assumption."""

    company = models.ForeignKey(
        ClientCompany,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="dominio_bank_entries",
    )
    source_id = models.CharField(max_length=160)
    occurred_on = models.DateField(db_index=True)
    description = models.CharField(max_length=500, blank=True)
    amount_cents = models.BigIntegerField()
    direction = models.CharField(max_length=8, blank=True)
    is_linked = models.BooleanField(default=False)

    class Meta:
        ordering = ("-occurred_on", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "source_id"), name="hub_unique_dominio_bank_entry"
            )
        ]
        indexes = [
            models.Index(fields=["organization", "company", "occurred_on"]),
            models.Index(fields=["organization", "occurred_on", "amount_cents"]),
        ]


class ReconciliationMatch(OrganizationScopedModel):
    """Deterministic OFX-to-Domínio result; ambiguous rows remain untouched."""

    class Status(models.TextChoices):
        MATCHED = "matched", "Conciliado"
        AMBIGUOUS = "ambiguous", "Revisar"
        UNMATCHED = "unmatched", "Sem correspondência"

    transaction = models.OneToOneField(
        BankTransaction, on_delete=models.CASCADE, related_name="reconciliation_match"
    )
    dominio_entry = models.ForeignKey(
        DominioBankEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reconciliation_matches",
    )
    accounting_entry = models.ForeignKey(
        AccountingEntry,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reconciliation_matches",
    )
    status = models.CharField(max_length=16, choices=Status.choices)
    is_manual = models.BooleanField(default=False)
    resolved_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="resolved_reconciliation_matches",
    )
    resolved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "status"])]


# The models below are intentionally separate from the legacy OFX x Domínio mirror.
# A source document, a financial movement and an accounting entry are different facts;
# keeping them separate prevents a receipt, invoice and bank debit from becoming three
# expenses merely because they describe the same business event.
class ReconciliationSourceFile(OrganizationScopedModel):
    class Kind(models.TextChoices):
        OFX = "ofx", "OFX"
        CSV = "csv", "CSV"
        XLSX = "xlsx", "XLSX"
        PDF = "pdf", "PDF"

    class Origin(models.TextChoices):
        BANK_STATEMENT = "bank_statement", "Extrato bancário"
        ACCOUNTING = "accounting", "Registros contábeis"
        OBLIGATION = "obligation", "Títulos ou obrigações"
        DOCUMENT = "document", "Documento comprobatório"

    company = models.ForeignKey(
        "ClientCompany", on_delete=models.PROTECT, related_name="reconciliation_files"
    )
    financial_account = models.ForeignKey(
        "FinancialAccount",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="source_files",
    )
    kind = models.CharField(max_length=12, choices=Kind.choices)
    origin = models.CharField(max_length=20, choices=Origin.choices)
    original_filename = models.CharField(max_length=255)
    content_hash = models.CharField(max_length=64)
    content_type = models.CharField(max_length=120, blank=True)
    size_bytes = models.PositiveIntegerField()
    content = models.FileField(upload_to=private_reconciliation_path)
    uploaded_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reconciliation_files",
    )

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "content_hash"),
                name="hub_unique_reconciliation_file_hash",
            )
        ]
        indexes = [models.Index(fields=("organization", "company", "created_at"))]


class ReconciliationRun(OrganizationScopedModel):
    class State(models.TextChoices):
        WAITING = "waiting", "Aguardando"
        PROCESSING = "processing", "Processando"
        REVIEW = "review", "Aguardando revisão"
        COMPLETED = "completed", "Concluída"
        COMPLETED_ALERTS = "completed_alerts", "Concluída com alertas"
        FAILED = "failed", "Falhou"
        CANCELED = "canceled", "Cancelada"

    source_file = models.ForeignKey(
        ReconciliationSourceFile, on_delete=models.PROTECT, related_name="runs"
    )
    continued_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="retries"
    )
    state = models.CharField(max_length=24, choices=State.choices, default=State.WAITING)
    stage = models.CharField(max_length=48, default="queued")
    total_count = models.PositiveIntegerField(default=0)
    processed_count = models.PositiveIntegerField(default=0)
    created_count = models.PositiveIntegerField(default=0)
    updated_count = models.PositiveIntegerField(default=0)
    ignored_count = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    checkpoint = models.JSONField(default=dict)
    errors = models.JSONField(default=list)
    layout_version = models.ForeignKey(
        "ReconciliationLayout",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="runs",
    )
    lease_token = models.UUIDField(null=True, blank=True, editable=False)
    lease_until = models.DateTimeField(null=True, blank=True, editable=False)
    cancel_requested_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reconciliation_runs",
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("organization", "state", "created_at")),
            models.Index(fields=("lease_until",)),
        ]


class ReconciliationLayout(OrganizationScopedModel):
    company = models.ForeignKey(
        "ClientCompany", on_delete=models.CASCADE, related_name="reconciliation_layouts"
    )
    kind = models.CharField(max_length=12, choices=ReconciliationSourceFile.Kind.choices)
    name = models.CharField(max_length=120)
    version = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)
    header_signature = models.CharField(max_length=64, blank=True)
    configuration = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reconciliation_layouts",
    )

    class Meta:
        ordering = ("company_id", "kind", "name", "-version")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "kind", "name", "version"),
                name="hub_unique_reconciliation_layout_version",
            )
        ]


class FinancialAccount(OrganizationScopedModel):
    company = models.ForeignKey(
        "ClientCompany", on_delete=models.CASCADE, related_name="financial_accounts"
    )
    name = models.CharField(max_length=160)
    bank_code = models.CharField(max_length=20, blank=True)
    account_reference = models.CharField(max_length=160, blank=True)
    ledger_code = models.CharField(max_length=64, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "account_reference"),
                name="hub_unique_financial_account_reference",
            )
        ]


class LedgerAccount(OrganizationScopedModel):
    company = models.ForeignKey(
        "ClientCompany", on_delete=models.CASCADE, related_name="ledger_accounts"
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=200)
    nature = models.CharField(max_length=12, blank=True)
    active = models.BooleanField(default=True)
    accepts_entries = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "code"), name="hub_unique_ledger_account_code"
            )
        ]


class CostCenter(OrganizationScopedModel):
    company = models.ForeignKey(
        "ClientCompany", on_delete=models.CASCADE, related_name="cost_centers"
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=160)
    active = models.BooleanField(default=True)
    required = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "code"), name="hub_unique_cost_center_code"
            )
        ]


class AccountingPeriod(OrganizationScopedModel):
    company = models.ForeignKey(
        "ClientCompany", on_delete=models.CASCADE, related_name="accounting_periods"
    )
    starts_on = models.DateField()
    ends_on = models.DateField()
    locked_at = models.DateTimeField(null=True, blank=True)
    locked_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="locked_accounting_periods",
    )
    lock_reason = models.CharField(max_length=240, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "starts_on", "ends_on"),
                name="hub_unique_accounting_period",
            )
        ]


class ReconciliationRule(OrganizationScopedModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        ACTIVE = "active", "Ativa"
        DISABLED = "disabled", "Desativada"

    company = models.ForeignKey(
        "ClientCompany", on_delete=models.CASCADE, related_name="reconciliation_rules"
    )
    name = models.CharField(max_length=160)
    priority = models.PositiveIntegerField(default=100)
    version = models.PositiveIntegerField(default=1)
    state = models.CharField(max_length=12, choices=State.choices, default=State.DRAFT)
    all_conditions = models.JSONField(default=list)
    any_conditions = models.JSONField(default=list)
    actions = models.JSONField(default=dict)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reconciliation_rules",
    )

    class Meta:
        ordering = ("priority", "created_at", "id")
        indexes = [models.Index(fields=("organization", "company", "state", "priority"))]


class NormalizedMovement(OrganizationScopedModel):
    class Direction(models.TextChoices):
        INFLOW = "inflow", "Entrada"
        OUTFLOW = "outflow", "Saída"

    class ClassificationSource(models.TextChoices):
        NONE = "none", "Sem classificação"
        RULE = "rule", "Regra"
        SUGGESTION = "suggestion", "Sugestão"
        MANUAL = "manual", "Manual"

    class ReviewState(models.TextChoices):
        PENDING = "pending", "Pendente"
        READY = "ready", "Pronto"
        IGNORED = "ignored", "Ignorado"
        CONFLICT = "conflict", "Conflito"

    run = models.ForeignKey(ReconciliationRun, on_delete=models.PROTECT, related_name="movements")
    source_file = models.ForeignKey(
        ReconciliationSourceFile, on_delete=models.PROTECT, related_name="movements"
    )
    company = models.ForeignKey(
        "ClientCompany", on_delete=models.PROTECT, related_name="normalized_movements"
    )
    financial_account = models.ForeignKey(
        FinancialAccount, null=True, blank=True, on_delete=models.SET_NULL, related_name="movements"
    )
    source_key = models.CharField(max_length=255)
    source_reference = models.JSONField(default=dict)
    original_date = models.CharField(max_length=64, blank=True)
    occurred_on = models.DateField(null=True, blank=True, db_index=True)
    original_amount = models.CharField(max_length=64, blank=True)
    amount_cents = models.BigIntegerField(default=0)
    currency = models.CharField(max_length=3, default="BRL")
    direction = models.CharField(max_length=12, choices=Direction.choices)
    original_description = models.CharField(max_length=1000, blank=True)
    description = models.CharField(max_length=1000, blank=True)
    document_number = models.CharField(max_length=160, blank=True)
    counterparty = models.CharField(max_length=255, blank=True)
    debit_account_code = models.CharField(max_length=64, blank=True)
    credit_account_code = models.CharField(max_length=64, blank=True)
    cost_center_code = models.CharField(max_length=64, blank=True)
    accounting_history = models.CharField(max_length=500, blank=True)
    review_state = models.CharField(
        max_length=12, choices=ReviewState.choices, default=ReviewState.PENDING
    )
    classification_source = models.CharField(
        max_length=12, choices=ClassificationSource.choices, default=ClassificationSource.NONE
    )
    confidence = models.PositiveSmallIntegerField(default=0)
    confidence_details = models.JSONField(default=dict)
    applied_rule = models.ForeignKey(
        ReconciliationRule,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="applied_movements",
    )
    revision = models.PositiveIntegerField(default=1)
    edited_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="edited_movements",
    )

    class Meta:
        ordering = ("-occurred_on", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("source_file", "source_key"), name="hub_unique_normalized_source_key"
            )
        ]
        indexes = [
            models.Index(fields=("organization", "company", "occurred_on")),
            models.Index(fields=("organization", "company", "review_state")),
        ]


class JournalEntry(OrganizationScopedModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        APPROVED = "approved", "Aprovado"
        EXPORTED = "exported", "Exportado"
        INVALID = "invalid", "Inválido"

    company = models.ForeignKey(
        "ClientCompany", on_delete=models.PROTECT, related_name="journal_entries"
    )
    movement = models.ForeignKey(
        NormalizedMovement,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="journal_entries",
    )
    source_movement_revision = models.PositiveIntegerField(null=True, blank=True)
    occurred_on = models.DateField()
    history = models.CharField(max_length=500)
    purpose = models.CharField(max_length=24)
    state = models.CharField(max_length=12, choices=State.choices, default=State.DRAFT)
    revision = models.PositiveIntegerField(default=1)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="approved_journal_entries",
    )

    class Meta:
        indexes = [models.Index(fields=("organization", "company", "occurred_on", "state"))]


class JournalLine(OrganizationScopedModel):
    class Side(models.TextChoices):
        DEBIT = "debit", "Débito"
        CREDIT = "credit", "Crédito"

    entry = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name="lines")
    account_code = models.CharField(max_length=64)
    side = models.CharField(max_length=8, choices=Side.choices)
    amount_cents = models.PositiveBigIntegerField()
    cost_center_code = models.CharField(max_length=64, blank=True)
    history = models.CharField(max_length=500, blank=True)


class MovementReconciliation(OrganizationScopedModel):
    class State(models.TextChoices):
        SUGGESTED = "suggested", "Sugerida"
        CONFIRMED = "confirmed", "Confirmada"
        UNDONE = "undone", "Desfeita"

    movement = models.ForeignKey(
        NormalizedMovement, on_delete=models.CASCADE, related_name="reconciliations"
    )
    entry = models.ForeignKey(
        JournalEntry, on_delete=models.PROTECT, related_name="movement_reconciliations"
    )
    amount_cents = models.PositiveBigIntegerField()
    state = models.CharField(max_length=12, choices=State.choices, default=State.SUGGESTED)
    evidence = models.JSONField(default=dict)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="confirmed_movement_reconciliations",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("movement", "entry"), name="hub_unique_movement_entry_reconciliation"
            )
        ]


class AccountingExport(OrganizationScopedModel):
    class Target(models.TextChoices):
        DOMINIO = "dominio", "Domínio"
        SIESCON = "siescon", "Siescon"

    class State(models.TextChoices):
        GENERATING = "generating", "Gerando"
        READY = "ready", "Arquivo gerado"
        CONFIRMED = "confirmed", "Importação confirmada"
        FAILED = "failed", "Falhou"

    company = models.ForeignKey(
        "ClientCompany", on_delete=models.PROTECT, related_name="accounting_exports"
    )
    period_start = models.DateField()
    period_end = models.DateField()
    target = models.CharField(max_length=24, choices=Target.choices, default=Target.DOMINIO)
    state = models.CharField(max_length=16, choices=State.choices, default=State.GENERATING)
    adapter_version = models.CharField(max_length=32, default="dominio-3.1-pending-homologation")
    content_hash = models.CharField(max_length=64, blank=True)
    content = models.FileField(upload_to=private_reconciliation_path, blank=True)
    entry_ids = models.JSONField(default=list)
    reexport_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="reexports"
    )
    reexport_reason = models.CharField(max_length=240, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="accounting_exports",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="confirmed_accounting_exports",
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("organization", "company", "period_start", "period_end"))]


class OperationalTask(OrganizationScopedModel):
    """An office-owned operational follow-up, optionally tied to a client company."""

    class Status(models.TextChoices):
        OPEN = "open", "Em aberto"
        COMPLETED = "completed", "Concluída"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        HIGH = "high", "Alta"

    company = models.ForeignKey(
        ClientCompany, on_delete=models.PROTECT, related_name="operational_tasks"
    )
    title = models.CharField(max_length=180)
    details = models.TextField(blank=True)
    due_on = models.DateField(null=True, blank=True, db_index=True)
    priority = models.CharField(max_length=12, choices=Priority.choices, default=Priority.NORMAL)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        on_delete=models.SET_NULL,
        related_name="created_operational_tasks",
    )
    completed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_operational_tasks",
    )
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("status", "due_on", "-created_at")
        indexes = [models.Index(fields=["organization", "status", "due_on"])]
