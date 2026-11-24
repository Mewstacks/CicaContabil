from __future__ import annotations

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
