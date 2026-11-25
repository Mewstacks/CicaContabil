from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models
from oauth2_provider.settings import oauth2_settings

from apps.organizations.models import Organization


class McpConsent(models.Model):
    """Escritorio que a pessoa escolheu ao autorizar um cliente MCP (D-333).

    O token do DOT sabe a pessoa e o cliente, nao o escritorio. Esta linha fecha a lacuna:
    uma por (pessoa, cliente), e trocar o escritorio revoga os tokens que existiam. Nada aqui
    guarda segredo; a linha so aponta para o escritorio e some junto com a pessoa ou o cliente.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="mcp_consents"
    )
    application = models.ForeignKey(
        oauth2_settings.APPLICATION_MODEL, on_delete=models.CASCADE, related_name="mcp_consents"
    )
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="mcp_consents"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "application"], name="mcp_consent_unique")
        ]
        indexes = [models.Index(fields=["organization"], name="mcp_consent_org_idx")]

    def __str__(self) -> str:
        return f"{self.user_id} -> {self.organization_id} ({self.application_id})"


class McpSetting(models.Model):
    """Chave do escritorio: o conector so responde se o dono ligou (default desligado)."""

    organization = models.OneToOneField(
        Organization, on_delete=models.CASCADE, related_name="mcp_setting"
    )
    enabled = models.BooleanField(default=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.organization_id}: {'ligado' if self.enabled else 'desligado'}"


class McpJob(models.Model):
    """Um pedido do gateway para o computador do escritorio (Fase 2, peca 3, D-332).

    O corpo e o contrato do `relay-job`: ferramenta e argumentos, nunca SQL. O agente do
    escritorio puxa so a fila do proprio escritorio, executa e devolve o envelope. Nada daqui
    guarda segredo; o resultado ja vem moldado e mascarado pelo servidor local (<= 16 KB).
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Na fila"
        CLAIMED = "claimed", "Em execução"
        DONE = "done", "Concluído"
        FAILED = "failed", "Recusado"
        EXPIRED = "expired", "Expirado"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organization = models.ForeignKey(
        Organization, on_delete=models.CASCADE, related_name="mcp_jobs"
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    agent = models.ForeignKey(
        "intelligence.EdgeAgent", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    tool = models.CharField(max_length=64)
    arguments = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    result = models.JSONField(null=True, blank=True)
    error_code = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["organization", "status", "created_at"])]
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"{self.tool} ({self.status})"
