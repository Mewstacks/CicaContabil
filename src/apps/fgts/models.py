"""FGTS Digital: apuração lida no Domínio, conferência no portal e emissão da guia.

Módulo por escritório (``ProductModule.Code.FGTS``), desligado por padrão. A emissão tem três
travas independentes, todas desligadas por padrão: a chave global ``FGTS_EMISSAO_HABILITADA``, a
validação da fonte (``source_validated``) e a liberação da emissão (``emission_enabled``) do
escritório. Sem as três, o item termina em ``prepared`` e nenhum clique de emitir é autorizado.
Valores em centavos inteiros; nunca ponto flutuante.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.hub.models import ClientCompany
from apps.organizations.models import OrganizationScopedModel
from apps.rpa.models import RpaArtifact, RpaJob


class FgtsSettings(OrganizationScopedModel):
    #: A leitura do Domínio foi comparada com guias reais em duas ou mais competências.
    source_validated = models.BooleanField(default=False)
    #: O escritório liberou o clique de emitir (depois do piloto com poucos grupos).
    emission_enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("organization",), name="fgts_one_settings_per_office")
        ]


class FgtsSource(OrganizationScopedModel):
    """Apuração do mês como a máquina do agente leu no Domínio (uma linha por grupo/raiz)."""

    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    groups = models.JSONField(default=list)
    pendencies = models.JSONField(default=list)
    job = models.ForeignKey(
        RpaJob, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        indexes = [models.Index(fields=("organization", "year", "month"))]


class FgtsBatch(OrganizationScopedModel):
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    deadline = models.DateField()
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )

    @property
    def competence(self) -> str:
        return f"{self.month:02d}/{self.year}"


class FgtsItem(OrganizationScopedModel):
    class State(models.TextChoices):
        QUEUED = "queued", "Na fila"
        CHECKING = "checking", "Conferindo no portal"
        PREPARED = "prepared", "Conferido; sem emissão"
        DIVERGENCE = "divergence", "Divergência"
        EMITTING = "emitting", "Emitindo"
        UNCERTAIN = "uncertain", "Incerto; conferir no portal"
        REVIEW = "review", "Guia para revisão"
        FAILED = "failed", "Falhou antes da emissão"

    BLOCKING = (
        State.QUEUED,
        State.CHECKING,
        State.PREPARED,
        State.EMITTING,
        State.UNCERTAIN,
        State.REVIEW,
    )

    batch = models.ForeignKey(FgtsBatch, on_delete=models.CASCADE, related_name="items")
    root = models.CharField(max_length=8)
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    company = models.ForeignKey(
        ClientCompany, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    company_name = models.CharField(max_length=255, blank=True)
    representative_cnpj = models.CharField(max_length=14, blank=True)
    codes = models.JSONField(default=list)
    expected_cents = models.BigIntegerField()
    portal_cents = models.BigIntegerField(null=True, blank=True)
    portal_due = models.DateField(null=True, blank=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.QUEUED)
    message = models.CharField(max_length=500, blank=True)
    check_job = models.ForeignKey(
        RpaJob, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    emit_job = models.ForeignKey(
        RpaJob, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    pdf = models.ForeignKey(
        RpaArtifact, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    sha256 = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("batch", "root"), name="fgts_one_item_per_root_in_batch"
            ),
            # Um só pedido ou guia vivo por raiz e competência no escritório inteiro.
            models.UniqueConstraint(
                fields=("organization", "root", "year", "month"),
                condition=Q(
                    state__in=["queued", "checking", "prepared", "emitting", "uncertain", "review"]
                ),
                name="fgts_one_live_item_per_root_month",
            ),
        ]
