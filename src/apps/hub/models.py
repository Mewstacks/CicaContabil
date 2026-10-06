from __future__ import annotations

import uuid
from collections.abc import Iterable
from decimal import Decimal
from typing import Any, NoReturn, Protocol

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.base import ModelBase
from django.utils import timezone

from apps.common.cnpj import normalize_cnpj
from apps.common.encryption import EncryptedTextField
from apps.common.models import AppendOnlyQuerySet, UUIDTimeStampedModel
from apps.organizations.models import Membership, OrganizationScopedModel


def private_import_path(instance: ImportBatch, filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return f"private/imports/{instance.organization_id}/{instance.id}.{suffix}"


class ReconciliationUploadInstance(Protocol):
    organization_id: object
    pk: object | None


def private_reconciliation_path(instance: ReconciliationUploadInstance, filename: str) -> str:
    """Keep financial evidence private and unguessable in the configured storage."""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return (
        f"private/reconciliation/{instance.organization_id}/{instance.pk or uuid.uuid4()}.{suffix}"
    )


class NfseExportInstance(Protocol):
    organization_id: object
    pk: object | None


def private_nfse_export_path(instance: NfseExportInstance, filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "zip"
    return f"private/nfse-exports/{instance.organization_id}/{instance.pk or uuid.uuid4()}.{suffix}"


class FinancialReportExportInstance(Protocol):
    organization_id: object
    pk: object | None


def private_financial_report_path(instance: FinancialReportExportInstance, filename: str) -> str:
    """Keep rendered financial reports private and separate from source imports."""
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    identifier = instance.pk or uuid.uuid4()
    return f"private/financial-reports/{instance.organization_id}/{identifier}.{suffix}"


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
    class TaxRegime(models.TextChoices):
        MEI = "mei", "MEI"
        SIMPLES = "simples", "Simples Nacional"
        PRESUMIDO = "presumido", "Lucro Presumido"
        REAL = "real", "Lucro Real"
        IMUNE_ISENTA = "imune_isenta", "Imune ou isenta"
        OUTRO = "outro", "Outro"

    name = models.CharField(max_length=180)
    cnpj_masked = models.CharField(max_length=18, blank=True)
    commercial_root_cnpj = models.CharField(max_length=8, blank=True, db_index=True)
    dominio_code = models.CharField(max_length=64, blank=True, db_index=True)
    active = models.BooleanField(default=True)
    last_dominio_sync_at = models.DateTimeField(null=True, blank=True)
    data_source = models.ForeignKey(
        "DataSource", null=True, blank=True, on_delete=models.SET_NULL, related_name="companies"
    )
    external_key = models.CharField(max_length=160, blank=True, db_index=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    # D-277: the office's own profile of the client. Editable even when the identity (name,
    # CNPJ, code) comes from Domínio or the control plane. Contact is personal data.
    tax_regime = models.CharField(
        max_length=16, choices=TaxRegime.choices, blank=True, default="", db_default=""
    )
    state_registration = models.CharField(max_length=30, blank=True, default="", db_default="")
    municipal_registration = models.CharField(
        max_length=30, blank=True, default="", db_default=""
    )
    contact_name = models.CharField(max_length=120, blank=True, default="", db_default="")
    contact_email = models.EmailField(max_length=254, blank=True, default="", db_default="")
    contact_phone = models.CharField(max_length=30, blank=True, default="", db_default="")

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

    def save(
        self,
        *args: Any,
        force_insert: bool | tuple[ModelBase, ...] = False,
        force_update: bool = False,
        using: str | None = None,
        update_fields: Iterable[str] | None = None,
    ) -> None:
        try:
            self.commercial_root_cnpj = normalize_cnpj(self.cnpj_masked)[:8]
        except ValidationError:
            self.commercial_root_cnpj = ""
        fields = set(update_fields) if update_fields is not None else None
        if fields is not None:
            fields.add("commercial_root_cnpj")
        super().save(
            force_insert=force_insert,
            force_update=force_update,
            using=using,
            update_fields=fields,
        )


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
        QUEUED = "queued", "Na fila"
        RUNNING = "running", "Sincronizando"
        RETRY = "retry", "Nova tentativa agendada"
        ERROR = "error", "Requer atenção"

    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE, related_name="nfse_syncs")
    certificate = models.ForeignKey(Certificate, null=True, blank=True, on_delete=models.SET_NULL)
    enabled = models.BooleanField(default=False)
    checkpoint_nsu = models.CharField(max_length=80, blank=True)
    max_nsu = models.CharField(max_length=80, blank=True)
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


class NfseDocumentSide(OrganizationScopedModel):
    """Side of the note for the company, derived from its immutable XML.

    Notes captured before the normalization stored a direction keep that gap in the immutable
    evidence; filters, counters and the export read the side from here instead.
    """

    document = models.OneToOneField(NfseDocument, on_delete=models.CASCADE, related_name="side")
    direction = models.CharField(max_length=16, db_index=True)
    counterparty_ref = models.CharField(max_length=80, blank=True)
    counterparty_name = models.CharField(max_length=160, blank=True)

    class Meta:
        indexes = [models.Index(fields=("organization", "direction"))]


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
    class Direction(models.TextChoices):
        # Same vocabulary as ``normalized_data["direction"]`` produced by the ADN sync.
        UNKNOWN = "", "Sem direção"
        TAKEN = "taken", "Tomada (entrada)"
        PROVIDED = "provided", "Prestada (serviço)"

    company = models.ForeignKey(
        ClientCompany, on_delete=models.CASCADE, related_name="accumulator_observations"
    )
    accumulator_code = models.CharField(max_length=80)
    service_code = models.CharField(max_length=60, blank=True)
    counterparty_ref = models.CharField(max_length=80, blank=True)
    direction = models.CharField(
        max_length=16, choices=Direction.choices, blank=True, default=Direction.UNKNOWN
    )
    frequency = models.PositiveIntegerField(default=1)
    last_used_at = models.DateTimeField(db_index=True)


class AccumulatorCatalogEntry(ImmutableOrganizationModel):
    """One accumulator observed by the allowlisted Domínio Web backup reader."""

    company = models.ForeignKey(
        ClientCompany, on_delete=models.PROTECT, related_name="accumulator_catalog_entries"
    )
    data_source = models.ForeignKey("DataSource", on_delete=models.PROTECT)
    source_batch = models.ForeignKey("ImportBatch", on_delete=models.PROTECT)
    accumulator_code = models.CharField(max_length=80)
    name = models.CharField(max_length=180, blank=True)
    active = models.BooleanField(default=True)
    source_identifier = models.CharField(max_length=160, blank=True)
    source_snapshot_at = models.DateTimeField()

    class Meta:
        ordering = ("company_id", "accumulator_code")
        constraints = [
            models.UniqueConstraint(
                fields=("source_batch", "company", "accumulator_code"),
                name="hub_unique_backup_accumulator_catalog_entry",
            )
        ]


class AccumulatorHistoryEntry(ImmutableOrganizationModel):
    """Append-only record for every accumulator available or decided in the CICA."""

    class Source(models.TextChoices):
        BACKUP = "backup", "Fotografia do Dominio Web"
        MANUAL = "manual", "Cadastro manual"
        HUMAN_REVIEW = "human_review", "Decisao humana"

    company = models.ForeignKey(
        ClientCompany, on_delete=models.PROTECT, related_name="accumulator_history_entries"
    )
    accumulator_code = models.CharField(max_length=80)
    name = models.CharField(max_length=180, blank=True)
    source = models.CharField(max_length=16, choices=Source.choices)
    source_reference = models.CharField(max_length=80)
    occurred_at = models.DateTimeField(db_index=True)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="accumulator_history_entries",
    )
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ("-occurred_at", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "source", "source_reference"),
                name="hub_unique_accumulator_history_source_reference",
            )
        ]


class ReviewCase(OrganizationScopedModel):
    class Status(models.TextChoices):
        OPEN = "open", "Aberta"
        RESOLVED = "resolved", "Resolvida"

    class ResolutionSource(models.TextChoices):
        HUMAN = "human", "Decisão humana"
        BACKUP = "backup", "Reclassificação pelo backup"

    document = models.OneToOneField(
        NfseDocument, on_delete=models.PROTECT, related_name="review_case"
    )
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.OPEN)
    reason = models.CharField(max_length=180)
    suggested_accumulator = models.CharField(max_length=80, blank=True)
    confidence = models.PositiveSmallIntegerField(default=0)
    resolved_accumulator = models.CharField(max_length=80, blank=True)
    resolution_source = models.CharField(
        max_length=16, choices=ResolutionSource.choices, blank=True
    )
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


class NfseExport(OrganizationScopedModel):
    documents: models.ManyToManyField[NfseDocument, Any] = models.ManyToManyField(
        "NfseDocument", related_name="exports", editable=False
    )

    class State(models.TextChoices):
        READY = "ready", "Arquivo gerado"
        DOWNLOADED = "downloaded", "Arquivo baixado"
        IMPORT_CONFIRMED = "import_confirmed", "Importação confirmada"

    state = models.CharField(max_length=24, choices=State.choices, default=State.READY)
    target = models.CharField(max_length=48, default="dominio_xml_routine_pending_homologation")
    adapter_version = models.CharField(max_length=48, default="nfse-xml-v1")
    content_hash = models.CharField(max_length=64)
    document_count = models.PositiveIntegerField()
    snapshot = models.JSONField(default=dict)
    content = models.FileField(upload_to=private_nfse_export_path)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="nfse_exports",
    )
    downloaded_at = models.DateTimeField(null=True, blank=True)
    downloaded_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="downloaded_nfse_exports",
    )
    confirmed_at = models.DateTimeField(null=True, blank=True)
    confirmed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="confirmed_nfse_exports",
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [models.Index(fields=("organization", "state", "created_at"))]


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
        ACCOUNTING_BALANCES = "accounting_balances", "Saldos para DRE"
        PAYROLL_TOTALS = "payroll_totals", "Totais da folha (documento informado)"
        CASH_SCENARIO = "cash_scenario", "Cenario de caixa"
        DRE_MAPPING = "dre_mapping", "Mapa DRE"
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
        UNKNOWN = "unknown", "Resultado a confirmar"
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


class FiscalGuideAttemptEvent(ImmutableOrganizationModel):
    """Observed attempt state; never infer missing historical transitions."""

    guide = models.ForeignKey(FiscalGuide, on_delete=models.PROTECT, related_name="attempt_events")
    attempt = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=16, choices=FiscalGuide.Status.choices)
    request_snapshot = models.JSONField(default=dict)
    requested_by_reference = models.CharField(max_length=36, blank=True)
    requested_at = models.DateTimeField(null=True, blank=True)
    issued_at = models.DateTimeField(null=True, blank=True)
    observed_at = models.DateTimeField(default=timezone.now)
    consumption_reference = models.CharField(max_length=100)
    provider_request_id = models.CharField(max_length=160, blank=True)
    provider_payload = EncryptedTextField(blank=True)
    error_code = models.CharField(max_length=80, blank=True)
    error_message = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ("attempt", "observed_at", "created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("guide", "attempt", "status"), name="hub_unique_guide_attempt_state"
            ),
        ]

    def save(self, **kwargs: Any) -> None:
        if not FiscalGuide.objects.filter(
            pk=self.guide_id,
            organization_id=self.organization_id,
            company__organization_id=self.organization_id,
        ).exists():
            raise ValidationError("Guide evidence must belong to its organization.")
        super().save(**kwargs)


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

    STAGE_LABELS = {
        "queued": "Na fila",
        "recovered": "Retomada",
        "extracting": "Lendo arquivo",
        "mapping": "Mapear colunas",
        "financial_account_review": "Escolher conta",
        "ocr_review": "Conferir leitura",
        "review": "Revisar movimentos",
        "rules_reapplied": "Regras reaplicadas",
        "completed": "Concluída",
        "failed": "Falhou",
        "canceled": "Cancelada",
    }

    @property
    def stage_label(self) -> str:
        """Operator-facing name of the internal pipeline stage code."""

        return self.STAGE_LABELS.get(self.stage, self.stage.replace("_", " ").capitalize())


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


class ReconciliationDecision(ImmutableOrganizationModel):
    reconciliation = models.ForeignKey(
        MovementReconciliation, on_delete=models.PROTECT, related_name="decisions"
    )
    state = models.CharField(max_length=12, choices=MovementReconciliation.State.choices)
    amount_cents = models.PositiveBigIntegerField()
    evidence = models.JSONField(default=dict)
    actor = models.ForeignKey("accounts.User", null=True, on_delete=models.SET_NULL)
    occurred_at = models.DateTimeField(null=True)
    is_legacy_snapshot = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=("organization", "created_at"))]


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


class PayrollPeriodSnapshot(OrganizationScopedModel):
    """Aggregated payroll facts for a company/competence; deliberately contains no worker PII."""

    class SourceKind(models.TextChoices):
        ERP = "erp", "ERP"
        DOCUMENT = "document", "Documento informado"
        OFFICIAL = "official", "Retorno oficial"
        MANUAL = "manual", "Confirmação humana"

    company = models.ForeignKey(
        "ClientCompany", on_delete=models.PROTECT, related_name="payroll_snapshots"
    )
    competence = models.DateField(db_index=True)
    source_kind = models.CharField(max_length=16, choices=SourceKind.choices)
    source_reference = models.CharField(max_length=240)
    observed_at = models.DateTimeField(default=timezone.now)
    workforce_count = models.PositiveIntegerField(null=True, blank=True)
    gross_pay_cents = models.BigIntegerField(null=True, blank=True)
    deductions_cents = models.BigIntegerField(null=True, blank=True)
    employer_charges_cents = models.BigIntegerField(null=True, blank=True)
    net_pay_cents = models.BigIntegerField(null=True, blank=True)
    data_source = models.ForeignKey(
        "DataSource",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="payroll_snapshots",
    )
    notes = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_payroll_snapshots",
    )

    class Meta:
        ordering = ("-competence", "-observed_at")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "competence", "source_kind", "source_reference"),
                name="hub_unique_payroll_snapshot_source_reference",
            )
        ]
        indexes = [models.Index(fields=("organization", "company", "competence"))]

    def clean(self) -> None:
        super().clean()
        if self.company_id and self.company.organization_id != self.organization_id:
            raise ValidationError(
                "A fotografia de folha precisa pertencer ao escritório da empresa."
            )
        if (
            self.data_source_id
            and self.data_source is not None
            and (self.data_source.organization_id != self.organization_id)
        ):
            raise ValidationError("A fonte da fotografia precisa pertencer ao mesmo escritório.")
        for field_name in (
            "gross_pay_cents",
            "deductions_cents",
            "employer_charges_cents",
            "net_pay_cents",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValidationError({field_name: "Informe um total agregado não negativo."})

    @property
    def gross_pay_amount(self) -> Decimal | None:
        return None if self.gross_pay_cents is None else Decimal(self.gross_pay_cents) / 100

    @property
    def deductions_amount(self) -> Decimal | None:
        return None if self.deductions_cents is None else Decimal(self.deductions_cents) / 100

    @property
    def employer_charges_amount(self) -> Decimal | None:
        return (
            None
            if self.employer_charges_cents is None
            else Decimal(self.employer_charges_cents) / 100
        )

    @property
    def net_pay_amount(self) -> Decimal | None:
        return None if self.net_pay_cents is None else Decimal(self.net_pay_cents) / 100


class AccountingBalanceSnapshot(OrganizationScopedModel):
    """One identified accounting balance observation, independent of its ERP adapter."""

    class SourceKind(models.TextChoices):
        ERP = "erp", "ERP"
        IMPORT = "import", "Importação conferida"
        DOCUMENT = "document", "Documento informado"
        MANUAL = "manual", "Confirmação humana"

    company = models.ForeignKey(
        "ClientCompany", on_delete=models.PROTECT, related_name="accounting_balance_snapshots"
    )
    competence = models.DateField(db_index=True)
    source_kind = models.CharField(max_length=16, choices=SourceKind.choices)
    source_reference = models.CharField(max_length=240)
    observed_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_accounting_balance_snapshots",
    )

    class Meta:
        ordering = ("-competence", "-observed_at")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "competence", "source_kind", "source_reference"),
                name="hub_unique_accounting_balance_snapshot_source",
            )
        ]
        indexes = [models.Index(fields=("organization", "company", "competence"))]

    def clean(self) -> None:
        super().clean()
        if self.company_id and self.company.organization_id != self.organization_id:
            raise ValidationError(
                "A fotografia contábil precisa pertencer ao escritório da empresa."
            )


class AccountingBalanceLine(models.Model):
    """A source balance retained with its account identity for DRE drill-down."""

    snapshot = models.ForeignKey(
        AccountingBalanceSnapshot, on_delete=models.PROTECT, related_name="lines"
    )
    account_code = models.CharField(max_length=80)
    account_name = models.CharField(max_length=240, blank=True)
    balance_cents = models.BigIntegerField()

    class Meta:
        ordering = ("account_code",)
        constraints = [
            models.UniqueConstraint(
                fields=("snapshot", "account_code"),
                name="hub_unique_accounting_balance_line_account",
            )
        ]

    def __str__(self) -> str:
        return f"{self.snapshot_id}:{self.account_code}"


class DreMappingSet(OrganizationScopedModel):
    """Versioned office mapping; changing it never rewrites prior report snapshots."""

    version = models.PositiveIntegerField()
    label = models.CharField(max_length=160)
    is_active = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_dre_mapping_sets",
    )

    class Meta:
        ordering = ("-version",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "version"), name="hub_unique_dre_mapping_set_version"
            ),
        ]


class DreAccountMapping(models.Model):
    mapping_set = models.ForeignKey(
        DreMappingSet, on_delete=models.PROTECT, related_name="mappings"
    )
    account_code = models.CharField(max_length=80)
    group = models.CharField(max_length=160)
    sign = models.SmallIntegerField()

    class Meta:
        ordering = ("account_code",)
        constraints = [
            models.UniqueConstraint(
                fields=("mapping_set", "account_code"), name="hub_unique_dre_mapping_account"
            ),
            models.CheckConstraint(
                condition=models.Q(sign__in=(-1, 1)), name="hub_dre_mapping_sign_is_valid"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.mapping_set_id}:{self.account_code}"


class CashScenario(OrganizationScopedModel):
    """A separated simulation, projection, or realized cash view for one company."""

    class View(models.TextChoices):
        SIMULATION = "simulation", "Simulação"
        PROJECTION = "projection", "Projeção"
        REALIZED = "realized", "Realizado"

    company = models.ForeignKey(
        "ClientCompany", on_delete=models.PROTECT, related_name="cash_scenarios"
    )
    label = models.CharField(max_length=160)
    view = models.CharField(max_length=16, choices=View.choices)
    reference_date = models.DateField()
    opening_balance_cents = models.BigIntegerField()
    created_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="created_cash_scenarios",
    )

    class Meta:
        ordering = ("-reference_date", "-created_at")
        indexes = [models.Index(fields=("organization", "company", "view", "reference_date"))]

    def clean(self) -> None:
        super().clean()
        if self.company_id and self.company.organization_id != self.organization_id:
            raise ValidationError("O cenário de caixa precisa pertencer ao escritório da empresa.")


class CashScenarioMovement(models.Model):
    scenario = models.ForeignKey(CashScenario, on_delete=models.PROTECT, related_name="movements")
    occurred_on = models.DateField(db_index=True)
    description = models.CharField(max_length=240)
    gross_receipt_cents = models.BigIntegerField(default=0)
    payment_cents = models.BigIntegerField(default=0)
    retention_cents = models.BigIntegerField(default=0)
    provision_cents = models.BigIntegerField(default=0)
    retention_already_provisioned = models.BooleanField(default=False)
    source_reference = models.CharField(max_length=240, blank=True)

    class Meta:
        ordering = ("occurred_on", "id")
        constraints = [
            models.CheckConstraint(
                condition=(
                    models.Q(gross_receipt_cents__gte=0)
                    & models.Q(payment_cents__gte=0)
                    & models.Q(retention_cents__gte=0)
                    & models.Q(provision_cents__gte=0)
                ),
                name="hub_cash_movement_non_negative",
            ),
        ]

    def clean(self) -> None:
        super().clean()
        if self.retention_already_provisioned and self.retention_cents and self.provision_cents:
            raise ValidationError("A retenção já provisionada não pode ser deduzida novamente.")

    def __str__(self) -> str:
        return f"{self.scenario_id}:{self.occurred_on}:{self.description}"


class ActivityTemplate(OrganizationScopedModel):
    """A versioned office rule that creates expected work without changing past work."""

    class Area(models.TextChoices):
        ACCOUNTING = "accounting", "Contábil"
        FISCAL = "fiscal", "Fiscal"
        PAYROLL = "payroll", "Folha"
        GENERAL = "general", "Geral"

    class EvidenceRequirement(models.TextChoices):
        SOURCE_OR_HUMAN = "source_or_human", "Fonte ou confirmação humana"
        SOURCE = "source", "Fonte integrada"
        HUMAN = "human", "Confirmação humana"

    class Frequency(models.TextChoices):
        MONTHLY = "monthly", "Mensal"
        AD_HOC = "ad_hoc", "Sob demanda"

    code = models.CharField(max_length=80)
    title = models.CharField(max_length=180)
    area = models.CharField(max_length=16, choices=Area.choices)
    description = models.TextField(blank=True)
    evidence_requirement = models.CharField(
        max_length=24,
        choices=EvidenceRequirement.choices,
        default=EvidenceRequirement.SOURCE_OR_HUMAN,
    )
    frequency = models.CharField(
        max_length=16, choices=Frequency.choices, default=Frequency.MONTHLY
    )
    legal_due_day = models.PositiveSmallIntegerField(null=True, blank=True)
    internal_due_day = models.PositiveSmallIntegerField(null=True, blank=True)
    # D-277: work for competência M is due in M + offset. Existing rows keep the old
    # same-month behaviour; the template form proposes the next month for new versions.
    due_month_offset = models.PositiveSmallIntegerField(default=0, db_default=0)
    legal_rule_code = models.CharField(max_length=64, blank=True, default="", db_default="")
    internal_lead_business_days = models.PositiveSmallIntegerField(null=True, blank=True)
    requires_processing_closed = models.BooleanField(default=False)
    requires_accepted_obligation = models.BooleanField(default=False)
    version = models.PositiveIntegerField(default=1)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ("area", "code", "-version")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "code", "version"),
                name="hub_unique_activity_template_version",
            )
        ]

    def clean(self) -> None:
        super().clean()
        for field_name in ("legal_due_day", "internal_due_day"):
            day = getattr(self, field_name)
            if day is not None and not 1 <= day <= 31:
                raise ValidationError(
                    {field_name: "Informe um dia entre 1 e 31; meses curtos usam o último dia."}
                )
        if self.due_month_offset is not None and self.due_month_offset > 12:
            raise ValidationError({"due_month_offset": "Use no máximo 12 meses."})
        if self.internal_lead_business_days is not None and self.internal_lead_business_days > 30:
            raise ValidationError({"internal_lead_business_days": "Use no máximo 30 dias úteis."})

    def __str__(self) -> str:
        return f"{self.title} ({self.code} · v{self.version})"


class ActivityTemplateAssignment(OrganizationScopedModel):
    """Explicit company scope and default owner for a versioned activity template."""

    template = models.ForeignKey(
        ActivityTemplate, on_delete=models.PROTECT, related_name="company_assignments"
    )
    company = models.ForeignKey(
        ClientCompany, on_delete=models.CASCADE, related_name="activity_template_assignments"
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="activity_template_assignments",
    )
    legal_due_day = models.PositiveSmallIntegerField(null=True, blank=True)
    internal_due_day = models.PositiveSmallIntegerField(null=True, blank=True)
    active = models.BooleanField(default=True)
    next_generation_competence = models.DateField(null=True, blank=True, editable=False)

    class Meta:
        ordering = ("template__area", "template__code", "company__name")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "template", "company"),
                name="hub_unique_activity_template_company_assignment",
            )
        ]

    def clean(self) -> None:
        super().clean()
        if self.template_id and self.template.organization_id != self.organization_id:
            raise ValidationError("O modelo precisa pertencer ao mesmo escritório.")
        if self.company_id and self.company.organization_id != self.organization_id:
            raise ValidationError("A empresa precisa pertencer ao mesmo escritório.")
        if (
            self.assigned_to_id
            and not Membership.objects.filter(
                organization_id=self.organization_id, user_id=self.assigned_to_id, is_active=True
            ).exists()
        ):
            raise ValidationError("O responsável precisa ser membro ativo do escritório.")
        for field_name in ("legal_due_day", "internal_due_day"):
            day = getattr(self, field_name)
            if day is not None and not 1 <= day <= 31:
                raise ValidationError(
                    {field_name: "Informe um dia entre 1 e 31; meses curtos usam o último dia."}
                )


class CompanyAreaResponsible(OrganizationScopedModel):
    """Default person for one area of one client (D-277); assignments without an owner use it."""

    company = models.ForeignKey(
        ClientCompany, on_delete=models.CASCADE, related_name="area_responsibles"
    )
    area = models.CharField(max_length=16, choices=ActivityTemplate.Area.choices)
    user = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ("company__name", "area")
        constraints = [
            models.UniqueConstraint(
                fields=("company", "area"), name="hub_unique_company_area_responsible"
            )
        ]

    def __str__(self) -> str:
        return f"{self.company} · {self.get_area_display()}"


class OperationalActivity(OrganizationScopedModel):
    """One expected activity for a company and competence, with independent evidence states."""

    class WorkStatus(models.TextChoices):
        PENDING = "pending", "Pendente"
        IN_PROGRESS = "in_progress", "Em andamento"
        BLOCKED = "blocked", "Impedida"
        COMPLETED = "completed", "Concluída"
        WAIVED = "waived", "Dispensada"

    class ProcessingStatus(models.TextChoices):
        NOT_VERIFIED = "not_verified", "Não verificado"
        OPEN = "open", "Aberto"
        PROCESSED = "processed", "Processado"
        CLOSED = "closed", "Fechado"
        REOPENED = "reopened", "Reaberto"

    class ObligationStatus(models.TextChoices):
        NOT_APPLICABLE = "not_applicable", "Não aplicável"
        NOT_PREPARED = "not_prepared", "Não preparada"
        PREPARED = "prepared", "Preparada"
        SUBMITTED = "submitted", "Transmitida"
        ACCEPTED = "accepted", "Aceita"
        REJECTED = "rejected", "Rejeitada"
        UNKNOWN = "unknown", "Resultado a confirmar"

    class PaymentStatus(models.TextChoices):
        NOT_APPLICABLE = "not_applicable", "Não aplicável"
        EXPECTED = "expected", "Previsto"
        GUIDE_AVAILABLE = "guide_available", "Guia disponível"
        INFORMED = "informed", "Pagamento informado"
        CONFIRMED = "confirmed", "Pagamento comprovado"

    class Freshness(models.TextChoices):
        CURRENT = "current", "Atualizado"
        STALE = "stale", "Desatualizado"
        UNAVAILABLE = "unavailable", "Fonte indisponível"
        NOT_CONFIGURED = "not_configured", "Integração não configurada"

    class EvidenceKind(models.TextChoices):
        SOURCE = "source", "Fonte integrada"
        DOCUMENT = "document", "Documento"
        HUMAN = "human", "Confirmação humana"
        OFFICIAL = "official", "Retorno oficial"

    source_nfse_review = models.OneToOneField(
        ReviewCase,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="operational_activity",
    )
    source_triage_item = models.OneToOneField(
        "triage.TriageItem",
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="operational_activity",
    )
    source_reconciliation_file = models.OneToOneField(
        ReconciliationSourceFile,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="operational_activity",
    )
    source_payroll_snapshot = models.ForeignKey(
        PayrollPeriodSnapshot,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="review_activities",
    )
    source_dte_message = models.OneToOneField(
        DteMessage,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="analysis_activity",
    )
    source_reform_alert = models.ForeignKey(
        ReformAlert,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="analysis_activities",
    )
    source_fiscal_guide = models.OneToOneField(
        FiscalGuide,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="operational_activity",
    )
    source_dctfweb_document = models.OneToOneField(
        DctfWebDocument,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="operational_activity",
    )
    source_parcelamento_operation = models.OneToOneField(
        ParcelamentoOperation,
        null=True,
        blank=True,
        editable=False,
        on_delete=models.PROTECT,
        related_name="operational_activity",
    )
    reform_version = models.CharField(max_length=64, blank=True, editable=False)
    company = models.ForeignKey(ClientCompany, on_delete=models.PROTECT, related_name="activities")
    template = models.ForeignKey(
        ActivityTemplate,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="activities",
    )
    template_version = models.PositiveIntegerField(default=1)
    code = models.CharField(max_length=80)
    title = models.CharField(max_length=180)
    area = models.CharField(max_length=16, choices=ActivityTemplate.Area.choices)
    competence = models.DateField(null=True, blank=True, db_index=True)
    legal_due_on = models.DateField(null=True, blank=True, db_index=True)
    internal_due_on = models.DateField(null=True, blank=True, db_index=True)
    # Which approved rule produced legal_due_on; empty for dates from a source or typed by hand.
    legal_due_rule = models.ForeignKey(
        "fiscal_calendar.TaxDeadlineRule",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="+",
    )
    assigned_to = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="assigned_operational_activities",
    )
    work_status = models.CharField(
        max_length=16, choices=WorkStatus.choices, default=WorkStatus.PENDING
    )
    processing_status = models.CharField(
        max_length=16, choices=ProcessingStatus.choices, default=ProcessingStatus.NOT_VERIFIED
    )
    obligation_status = models.CharField(
        max_length=20,
        choices=ObligationStatus.choices,
        default=ObligationStatus.NOT_APPLICABLE,
    )
    payment_status = models.CharField(
        max_length=20, choices=PaymentStatus.choices, default=PaymentStatus.NOT_APPLICABLE
    )
    freshness = models.CharField(
        max_length=20, choices=Freshness.choices, default=Freshness.NOT_CONFIGURED
    )
    requires_processing_closed = models.BooleanField(default=False)
    requires_accepted_obligation = models.BooleanField(default=False)
    evidence_requirement = models.CharField(
        max_length=24,
        choices=ActivityTemplate.EvidenceRequirement.choices,
        default=ActivityTemplate.EvidenceRequirement.SOURCE_OR_HUMAN,
    )
    blocked_reason = models.CharField(max_length=500, blank=True)
    waived_reason = models.CharField(max_length=500, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by = models.ForeignKey(
        "accounts.User",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="completed_operational_activities",
    )

    class Meta:
        ordering = ("internal_due_on", "legal_due_on", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "company", "code", "competence", "template_version"),
                name="hub_unique_operational_activity_competence",
            ),
            models.UniqueConstraint(
                fields=("organization", "company", "code", "template_version"),
                condition=models.Q(competence__isnull=True),
                name="hub_unique_operational_activity_without_competence",
            ),
        ]
        indexes = [
            models.Index(fields=("organization", "assigned_to", "work_status", "internal_due_on")),
            models.Index(fields=("organization", "company", "competence")),
        ]

    def clean(self) -> None:
        super().clean()
        if self.company_id and self.company.organization_id != self.organization_id:
            raise ValidationError("A atividade precisa pertencer ao mesmo escritório da empresa.")
        review = self.source_nfse_review
        if review is not None and (
            review.organization_id != self.organization_id
            or review.document.company_id != self.company_id
        ):
            raise ValidationError("A revisão precisa pertencer ao mesmo escritório e empresa.")
        triage_item = self.source_triage_item
        if triage_item is not None and (
            triage_item.organization_id != self.organization_id
            or triage_item.company_id != self.company_id
            or self.source_nfse_review_id
        ):
            raise ValidationError(
                "O arquivo precisa ser a única origem e pertencer à mesma empresa."
            )
        template = self.template if self.template_id else None
        payroll = self.source_payroll_snapshot
        dte = self.source_dte_message
        source_count = sum(
            bool(value)
            for value in (
                self.source_nfse_review_id,
                self.source_triage_item_id,
                self.source_reconciliation_file_id,
                self.source_payroll_snapshot_id,
                self.source_dte_message_id,
                self.source_reform_alert_id,
                self.source_fiscal_guide_id,
                self.source_dctfweb_document_id,
                self.source_parcelamento_operation_id,
            )
        )
        if source_count > 1:
            raise ValidationError("Uma atividade de módulo deve ter uma única origem.")
        if self.source_reform_alert_id and any(
            (
                self.source_nfse_review_id,
                self.source_triage_item_id,
                self.source_reconciliation_file_id,
                self.source_payroll_snapshot_id,
                self.source_dte_message_id,
                self.source_fiscal_guide_id,
                self.source_dctfweb_document_id,
                self.source_parcelamento_operation_id,
            )
        ):
            raise ValidationError("A publicação deve ser a única origem da atividade.")
        if dte is not None and (
            dte.organization_id != self.organization_id
            or dte.company_id != self.company_id
            or self.source_nfse_review_id
            or self.source_triage_item_id
            or self.source_reconciliation_file_id
            or self.source_payroll_snapshot_id
        ):
            raise ValidationError("A comunicação DTE precisa corresponder à atividade.")
        if payroll is not None and (
            payroll.organization_id != self.organization_id
            or payroll.company_id != self.company_id
            or payroll.competence != self.competence
            or self.source_nfse_review_id
            or self.source_triage_item_id
            or self.source_reconciliation_file_id
        ):
            raise ValidationError("A fotografia da folha precisa corresponder à atividade.")
        reconciliation_file = self.source_reconciliation_file
        if reconciliation_file is not None and (
            reconciliation_file.organization_id != self.organization_id
            or reconciliation_file.company_id != self.company_id
            or self.source_nfse_review_id
            or self.source_triage_item_id
        ):
            raise ValidationError(
                "A origem da Conciliação precisa corresponder à empresa da atividade."
            )
        for source, label in (
            (self.source_fiscal_guide, "A guia"),
            (self.source_dctfweb_document, "O documento DCTFWeb"),
            (self.source_parcelamento_operation, "A operação PARCSN"),
        ):
            if source is not None and (
                source.organization_id != self.organization_id
                or source.company_id != self.company_id
            ):
                raise ValidationError(f"{label} precisa pertencer ao mesmo escritório e empresa.")
        if template is not None and template.organization_id != self.organization_id:
            raise ValidationError("O modelo precisa pertencer ao mesmo escritório.")
        if (
            self.assigned_to_id
            and not Membership.objects.filter(
                organization_id=self.organization_id, user_id=self.assigned_to_id, is_active=True
            ).exists()
        ):
            raise ValidationError("O responsável precisa ser membro ativo do escritório.")


class OperationalEvidence(ImmutableOrganizationModel):
    """An immutable, intentionally small proof attached to an operational activity."""

    source_url = models.URLField(max_length=1500, blank=True)
    activity = models.ForeignKey(
        OperationalActivity, on_delete=models.PROTECT, related_name="evidence_items"
    )
    kind = models.CharField(max_length=16, choices=OperationalActivity.EvidenceKind.choices)
    reference = models.CharField(max_length=180, blank=True)
    summary = models.CharField(max_length=500, blank=True)
    observed_at = models.DateTimeField(default=timezone.now)
    recorded_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ("-observed_at", "-created_at")
        indexes = [models.Index(fields=("organization", "activity", "kind"))]

    def clean(self) -> None:
        super().clean()
        if self.activity_id and self.activity.organization_id != self.organization_id:
            raise ValidationError("A evidência precisa pertencer ao mesmo escritório da atividade.")


class OperationalSourceObservation(ImmutableOrganizationModel):
    """Append-only outcome of a source read, including failures that leave prior data stale."""

    data_source = models.ForeignKey(
        DataSource, on_delete=models.PROTECT, related_name="operational_observations"
    )
    activity = models.ForeignKey(
        OperationalActivity, on_delete=models.PROTECT, related_name="source_observations"
    )
    successful = models.BooleanField()
    external_reference = models.CharField(max_length=180, blank=True)
    source_version = models.CharField(max_length=120, blank=True)
    processing_status = models.CharField(
        max_length=16, choices=OperationalActivity.ProcessingStatus.choices, blank=True
    )
    obligation_status = models.CharField(
        max_length=20, choices=OperationalActivity.ObligationStatus.choices, blank=True
    )
    summary = models.CharField(max_length=500, blank=True)
    observed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-observed_at", "-created_at")
        indexes = [
            models.Index(fields=("organization", "activity", "successful", "observed_at")),
            models.Index(fields=("organization", "data_source", "observed_at")),
        ]

    def clean(self) -> None:
        super().clean()
        if self.data_source_id and self.data_source.organization_id != self.organization_id:
            raise ValidationError("A fonte precisa pertencer ao mesmo escritório da atividade.")
        if self.activity_id and self.activity.organization_id != self.organization_id:
            raise ValidationError("A atividade precisa pertencer ao mesmo escritório da fonte.")
        if self.processing_status and self.processing_status not in set(
            OperationalActivity.ProcessingStatus.values
        ):
            raise ValidationError({"processing_status": "Situação de processamento inválida."})
        if self.obligation_status and self.obligation_status not in set(
            OperationalActivity.ObligationStatus.values
        ):
            raise ValidationError({"obligation_status": "Situação de obrigação inválida."})


class OperationalActivityEvent(ImmutableOrganizationModel):
    """Append-only operational history that explains attribution, action and outcome."""

    activity = models.ForeignKey(
        OperationalActivity, on_delete=models.PROTECT, related_name="events"
    )
    event_type = models.CharField(max_length=48)
    summary = models.CharField(max_length=500, blank=True)
    actor = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    occurred_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ("-occurred_at", "-created_at")
        indexes = [models.Index(fields=("organization", "activity", "occurred_at"))]

    def clean(self) -> None:
        super().clean()
        if self.activity_id and self.activity.organization_id != self.organization_id:
            raise ValidationError("O evento precisa pertencer ao mesmo escritório da atividade.")


class OnboardingProgress(UUIDTimeStampedModel):
    """One person's completion of one guided orientation, tied to its version.

    The row holds no fiscal content, no company and no answer: only which orientation
    the person finished and which version it was, so a materially changed flow can show
    the new version once. Demonstration visitors never reach this table; their progress
    stays in the browser session.
    """

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, related_name="onboarding_progress"
    )
    tour_id = models.CharField(max_length=40)
    version = models.PositiveSmallIntegerField()
    completed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "tour_id"), name="hub_unique_onboarding_progress"
            )
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.tour_id}@{self.version}"


class FinancialReportExport(OrganizationScopedModel):
    """Durable, private rendering request for an immutable financial report snapshot."""

    class Resource(models.TextChoices):
        DRE = "dre", "DRE"
        CASH = "cash", "Caixa"

    class Format(models.TextChoices):
        PDF = "pdf", "PDF"
        XLSX = "xlsx", "XLSX"

    class State(models.TextChoices):
        WAITING = "waiting", "Aguardando"
        RENDERING = "rendering", "Gerando"
        READY = "ready", "Disponivel"
        FAILED = "failed", "Falhou"

    company = models.ForeignKey(
        ClientCompany, on_delete=models.PROTECT, related_name="financial_report_exports"
    )
    requested_by = models.ForeignKey(
        "accounts.User", on_delete=models.PROTECT, related_name="financial_report_exports"
    )
    resource = models.CharField(max_length=12, choices=Resource.choices)
    source_id = models.UUIDField()
    export_format = models.CharField(max_length=8, choices=Format.choices)
    filename_stem = models.CharField(max_length=180)
    snapshot = EncryptedTextField()
    snapshot_sha256 = models.CharField(max_length=64, db_index=True)
    state = models.CharField(max_length=16, choices=State.choices, default=State.WAITING)
    content = models.FileField(upload_to=private_financial_report_path, blank=True)
    content_type = models.CharField(max_length=120, blank=True)
    output_sha256 = models.CharField(max_length=64, blank=True)
    failure_code = models.CharField(max_length=80, blank=True)
    lease_token = models.UUIDField(null=True, blank=True, editable=False)
    lease_until = models.DateTimeField(null=True, blank=True, editable=False)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("organization", "company", "created_at")),
            models.Index(fields=("organization", "state", "created_at")),
            models.Index(fields=("lease_until",)),
        ]

    def clean(self) -> None:
        super().clean()
        if self.company_id and self.company.organization_id != self.organization_id:
            raise ValidationError("O relatorio precisa pertencer ao escritorio da empresa.")
        if self.requested_by_id and not self.requested_by.is_active:
            raise ValidationError("O solicitante do relatorio precisa estar ativo.")
