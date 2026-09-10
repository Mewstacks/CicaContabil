from __future__ import annotations

from collections.abc import Iterable
from typing import Any, NoReturn

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models.base import ModelBase

from apps.common.encryption import EncryptedTextField
from apps.common.models import AppendOnlyQuerySet, UUIDTimeStampedModel
from apps.organizations.models import Membership, OrganizationScopedModel


class OfficeProfile(OrganizationScopedModel):
    class ContractStatus(models.TextChoices):
        TRIAL = "trial", "Em carência"
        ACTIVE = "active", "Ativo"
        SUSPENDED = "suspended", "Suspenso"

    organization = models.OneToOneField(
        "organizations.Organization", on_delete=models.CASCADE, related_name="hub_profile"
    )
    legal_name = models.CharField(max_length=180, blank=True)
    contract_status = models.CharField(
        max_length=16, choices=ContractStatus.choices, default=ContractStatus.TRIAL
    )
    grace_ends_at = models.DateField(null=True, blank=True)
    reference_invoice_note = models.CharField(max_length=240, blank=True)


class ProductModule(OrganizationScopedModel):
    class Code(models.TextChoices):
        NFSE = "nfse", "NFS-e Inteligente"
        GUIDES = "guides", "Guias e DCTFWeb"
        INTEGRA = "integra", "Central Integra Contador"
        RECONCILIATION = "reconciliation", "Conciliação OFX x Domínio"
        REFORM = "reform", "Radar da Reforma Tributária"

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

    class Meta:
        ordering = ("name",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "dominio_code"),
                condition=models.Q(dominio_code__gt=""),
                name="hub_unique_dominio_company_code",
            )
        ]


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
            raise ValidationError("O acesso precisa pertencer ao mesmo escritÃ³rio.")
        if self.company_id and self.company.organization_id != self.organization_id:
            raise ValidationError("A empresa precisa pertencer ao mesmo escritÃ³rio.")


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
    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE, related_name="nfse_syncs")
    certificate = models.ForeignKey(Certificate, null=True, blank=True, on_delete=models.SET_NULL)
    checkpoint_nsu = models.CharField(max_length=80, blank=True)
    status = models.CharField(max_length=24, default="idle")
    last_error_code = models.CharField(max_length=80, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)
    next_run_at = models.DateTimeField(null=True, blank=True)

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
                fields=("organization", "document_hash"), name="hub_unique_nfse_document_hash"
            )
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


class Connector(OrganizationScopedModel):
    class Kind(models.TextChoices):
        DOMINIO_AGENT = "dominio_agent", "Agente Domínio local"
        ONVIO = "onvio", "Onvio API"
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

    connector = models.ForeignKey(Connector, on_delete=models.PROTECT, related_name="confirmations")
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
