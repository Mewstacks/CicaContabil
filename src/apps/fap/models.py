"""FAP (Fator Acidentário de Prevenção): consulta ao FAPWeb e guarda do PDF oficial.

Módulo por escritório (``ProductModule.Code.FAP``), desligado por padrão. Duas travas do escritório
(``enabled`` e ``portal_validated``) precisam estar ligadas para qualquer consulta ser entregue ao
agente. O PDF só vale depois que o SERVIDOR confere CNPJ e vigência no texto do arquivo.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.hub.models import ClientCompany
from apps.organizations.models import OrganizationScopedModel
from apps.rpa.models import RpaArtifact, RpaJob


class FapSettings(OrganizationScopedModel):
    enabled = models.BooleanField(default=False)
    #: Os seletores do portal real foram observados e conferidos (sem isso o agente não baixa).
    portal_validated = models.BooleanField(default=False)
    #: Teto de empresas por lote (3 → 10 → 0 conforme a confiança); 0 = sem teto.
    batch_limit = models.PositiveSmallIntegerField(default=3)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("organization",), name="fap_one_settings_per_office")
        ]


class FapBatch(OrganizationScopedModel):
    class State(models.TextChoices):
        QUEUED = "queued", "Na fila"
        RUNNING = "running", "Em execução"
        PAUSED = "paused", "Pausado"
        DONE = "done", "Concluído"
        ATTENTION = "attention", "Com pendências"

    year = models.PositiveSmallIntegerField()
    state = models.CharField(max_length=10, choices=State.choices, default=State.QUEUED)
    notice = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )


class FapItem(OrganizationScopedModel):
    class State(models.TextChoices):
        PENDING = "pending", "Pendente"
        QUERYING = "querying", "Consultando"
        DONE = "done", "Concluído"
        NO_REPORT = "no_report", "Sem relatório"
        NO_PERMISSION = "no_permission", "Sem permissão"
        ROOT_MISSING = "root_missing", "Raiz ausente no portal"
        REVIEW = "review", "PDF para revisão"
        REGISTRY = "registry", "Cadastro a corrigir"
        FAILED = "failed", "Falhou"

    ACTIVE = (State.PENDING, State.QUERYING)
    SUCCESS = (State.DONE,)

    batch = models.ForeignKey(FapBatch, on_delete=models.CASCADE, related_name="items")
    company = models.ForeignKey(
        ClientCompany, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    code = models.CharField(max_length=64)
    name = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=14, blank=True)
    year = models.PositiveSmallIntegerField()
    state = models.CharField(max_length=14, choices=State.choices, default=State.PENDING)
    message = models.CharField(max_length=500, blank=True)
    generation = models.PositiveSmallIntegerField(default=1)
    job = models.ForeignKey(
        RpaJob, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    pdf = models.ForeignKey(
        RpaArtifact, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    sha256 = models.CharField(max_length=64, blank=True)
    validated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("batch", "code"), name="fap_one_item_per_company_in_batch"
            ),
            # Nunca duas consultas vivas do mesmo CNPJ e vigência no escritório.
            models.UniqueConstraint(
                fields=("organization", "cnpj", "year"),
                condition=Q(state__in=["pending", "querying"]) & ~Q(cnpj=""),
                name="fap_one_active_query_per_cnpj_year",
            ),
        ]
