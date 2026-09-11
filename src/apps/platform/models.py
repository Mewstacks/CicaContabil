from __future__ import annotations

import hashlib
import secrets

from django.conf import settings
from django.core.validators import EmailValidator
from django.db import models
from django.utils import timezone

from apps.common.encryption import EncryptedTextField
from apps.common.models import UUIDTimeStampedModel


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


class Plan(UUIDTimeStampedModel):
    code = models.SlugField(unique=True, max_length=40)
    name = models.CharField(max_length=100)
    version = models.PositiveIntegerField(default=1)
    is_active = models.BooleanField(default=True)
    limits = models.JSONField(default=dict)
    modules = models.JSONField(default=list)


class TenantContract(UUIDTimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        ACTIVE = "active", "Ativo"
        GRACE = "grace", "Carência"
        SUSPENDED = "suspended", "Suspenso"
        ARCHIVED = "archived", "Arquivado"

    organization = models.ForeignKey(
        "organizations.Organization", on_delete=models.PROTECT, related_name="contracts"
    )
    plan = models.ForeignKey(Plan, null=True, blank=True, on_delete=models.PROTECT)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    reference = models.CharField(max_length=120, blank=True)
    starts_on = models.DateField(null=True, blank=True)
    ends_on = models.DateField(null=True, blank=True)
    grace_ends_on = models.DateField(null=True, blank=True)
    notes = models.CharField(max_length=240, blank=True)


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
    company_count = models.PositiveIntegerField(null=True, blank=True)
    message = EncryptedTextField(blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.NEW)
