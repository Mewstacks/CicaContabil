"""Envio de guias e relatórios ao cliente por e-mail, com histórico por entrega.

Cada escritório tem uma conta de envio própria (SMTP ou Microsoft Graph); o segredo é cifrado
em repouso como o resto do CICA e nunca volta a um template. O remetente é sempre a conta
autenticada: o escritório não escolhe um `From` diferente do que o provedor aceita.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.encryption import EncryptedTextField
from apps.organizations.models import OrganizationScopedModel
from apps.triage.storage import PrivateTriageStorage

# Limite somado dos anexos de uma entrega. Exchange Online recusa acima de ~35 MB de mensagem
# (anexos em base64 crescem ~37 %), então 30 MB de arquivo já é o teto prático.
MAX_ATTACHMENT_BYTES = 30 * 1024 * 1024


def private_delivery_path(instance: DeliveryAttachment, filename: str) -> str:
    # O nome original é metadado: nunca deixa uma extensão não confiável moldar o caminho.
    return (
        f"private/delivery/{instance.delivery.organization_id}/"
        f"{instance.delivery_id}/{instance.id}.bin"
    )


class DeliveryAccount(OrganizationScopedModel):
    """Conta de envio do escritório: uma por escritório."""

    class Provider(models.TextChoices):
        SMTP = "smtp", "SMTP"
        GRAPH = "graph", "Microsoft 365 (Graph)"

    class Security(models.TextChoices):
        SSL = "ssl", "SSL/TLS (465)"
        STARTTLS = "starttls", "STARTTLS (587)"

    provider = models.CharField(max_length=8, choices=Provider.choices, default=Provider.SMTP)
    from_name = models.CharField(max_length=120, blank=True, default="", db_default="")
    # Para SMTP é o login (quando for e-mail); para Graph é a caixa que envia.
    from_address = models.EmailField()
    smtp_host = models.CharField(max_length=200, blank=True, default="", db_default="")
    smtp_port = models.PositiveIntegerField(default=465, db_default=465)
    smtp_security = models.CharField(
        max_length=10, choices=Security.choices, default=Security.SSL, db_default=Security.SSL
    )
    smtp_username = models.CharField(max_length=254, blank=True, default="", db_default="")
    smtp_password = EncryptedTextField(blank=True)
    graph_tenant_id = models.CharField(max_length=64, blank=True, default="", db_default="")
    graph_client_id = models.CharField(max_length=64, blank=True, default="", db_default="")
    graph_client_secret = EncryptedTextField(blank=True)
    active = models.BooleanField(default=True)
    last_test_at = models.DateTimeField(null=True, blank=True)
    last_test_error = models.CharField(max_length=500, blank=True, default="", db_default="")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization",), name="delivery_one_account_per_office"
            )
        ]

    def __str__(self) -> str:
        return f"{self.from_address} ({self.get_provider_display()})"

    @property
    def sender_address(self) -> str:
        """O remetente efetivo: a conta autenticada, nunca outro endereço."""

        if self.provider == self.Provider.SMTP and "@" in self.smtp_username:
            return self.smtp_username
        return self.from_address

    def clean(self) -> None:
        if self.provider == self.Provider.SMTP:
            if not self.smtp_host:
                raise ValidationError({"smtp_host": "Informe o servidor."})
            if "@" in self.smtp_username and (
                self.smtp_username.casefold() != self.from_address.casefold()
            ):
                raise ValidationError(
                    {"from_address": "O remetente precisa ser a conta autenticada."}
                )
        elif not (self.graph_tenant_id and self.graph_client_id):
            raise ValidationError({"graph_tenant_id": "Informe diretório e aplicativo."})


class Delivery(OrganizationScopedModel):
    """Uma entrega ao cliente: um e-mail, seus destinatários, anexos e desfecho."""

    class Status(models.TextChoices):
        SCHEDULED = "scheduled", "Aguardando liberação"
        QUEUED = "queued", "Na fila"
        SENDING = "sending", "Enviando"
        SENT = "sent", "Enviado"
        FAILED = "failed", "Falhou"
        CANCELLED = "cancelled", "Cancelado"

    company = models.ForeignKey(
        "hub.ClientCompany", on_delete=models.CASCADE, related_name="deliveries"
    )
    obligation_delivery = models.ForeignKey(
        "hub.ObligationDelivery",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="email_deliveries",
    )
    competence = models.DateField(null=True, blank=True)
    recipients = models.JSONField(default=list)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    # Dia a partir do qual a entrega pode sair (dia de liberação da empresa); vazio = já.
    release_on = models.DateField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    lease_until = models.DateTimeField(null=True, blank=True)
    lease_token = models.UUIDField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True, default="", db_default="")
    sent_at = models.DateTimeField(null=True, blank=True)
    sender = models.CharField(max_length=254, blank=True, default="", db_default="")
    total_bytes = models.PositiveBigIntegerField(default=0)
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    resend_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="resends"
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("organization", "status", "-created_at")),
            models.Index(fields=("status", "release_on")),
        ]

    def __str__(self) -> str:
        return f"{self.subject} ({self.status})"

    def clean(self) -> None:
        if self.company_id and self.company.organization_id != self.organization_id:
            raise ValidationError({"company": "A empresa pertence a outro escritório."})


class DeliveryAttachment(OrganizationScopedModel):
    delivery = models.ForeignKey(Delivery, on_delete=models.CASCADE, related_name="attachments")
    filename = models.CharField(max_length=255)
    content = models.FileField(
        upload_to=private_delivery_path, storage=PrivateTriageStorage(), max_length=500
    )
    sha256 = models.CharField(max_length=64)
    byte_size = models.PositiveBigIntegerField()

    class Meta:
        ordering = ("created_at", "filename")

    def __str__(self) -> str:
        return self.filename
