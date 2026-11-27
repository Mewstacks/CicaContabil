"""Admissões: cadastro de empregado novo na Folha do Domínio pela interface nativa.

Módulo por escritório (``ProductModule.Code.ADMISSIONS``), desligado por padrão. A ficha é dado
pessoal: o conteúdo fica cifrado, o CPF só existe como HMAC (``cpf_hash``), a carga do trabalho
nunca grava a ficha (``transient_claim``) e tudo é apagado em 90 dias. Falha depois do clique de
gravar nunca reenfileira: vira ``uncertain`` e pede conferência humana.
"""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.common.encryption import EncryptedTextField
from apps.hub.models import ClientCompany
from apps.organizations.models import OrganizationScopedModel
from apps.rpa.models import RpaJob
from apps.triage.storage import PrivateTriageStorage

RETENTION = timedelta(days=90)


class AdmissionsSettings(OrganizationScopedModel):
    #: Códigos do Domínio das empresas em que a execução é permitida (lista vazia = nenhuma).
    allowed_codes = models.JSONField(default=list, blank=True)
    #: Chave da execução no escritório; desligada por padrão.
    execution_enabled = models.BooleanField(default=False)
    #: Código da empresa de EXEMPLO do Domínio, que só roda com confirmação de teste.
    example_code = models.CharField(max_length=64, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization",), name="admissions_one_settings_per_office"
            )
        ]


def _path(instance: Admission, filename: str) -> str:
    return f"admissions/{instance.organization_id}/{instance.pk}.bin"


class Admission(OrganizationScopedModel):
    class State(models.TextChoices):
        REVIEW = "review", "Aguardando revisão"
        QUEUED = "queued", "Aguardando o agente"
        RUNNING = "running", "Em execução"
        DONE = "done", "Cadastrado"
        FAILED = "failed", "Falhou sem gravar"
        UNCERTAIN = "uncertain", "Conferir no Domínio"
        CANCELLED = "cancelled", "Cancelada"
        EXPIRED = "expired", "Expirada"

    LIVE = (State.QUEUED, State.RUNNING, State.DONE, State.UNCERTAIN)

    company = models.ForeignKey(ClientCompany, on_delete=models.PROTECT, related_name="+")
    state = models.CharField(max_length=10, choices=State.choices, default=State.REVIEW)
    data_json = EncryptedTextField(blank=True, default="")
    pending = models.JSONField(default=list, blank=True)  # só nomes de campo, nunca valores
    cpf_hash = models.CharField(max_length=64, blank=True, db_index=True)
    example_confirmed = models.BooleanField(default=False)
    step = models.CharField(max_length=120, blank=True)
    error = models.CharField(max_length=500, blank=True)
    domain_code = models.CharField(max_length=30, blank=True)
    original_name = models.CharField(max_length=200, blank=True)
    sha256 = models.CharField(max_length=64, blank=True)
    file = models.FileField(upload_to=_path, storage=PrivateTriageStorage(), blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    job = models.ForeignKey(
        RpaJob, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        constraints = [
            # O mesmo CPF não entra duas vezes na mesma empresa enquanto houver pedido vivo.
            models.UniqueConstraint(
                fields=("company", "cpf_hash"),
                condition=Q(state__in=["queued", "running", "done", "uncertain"]) & ~Q(cpf_hash=""),
                name="admissions_one_live_cpf_per_company",
            )
        ]

    @property
    def data(self) -> dict[str, Any]:
        try:
            value = json.loads(self.data_json or "{}")
        except json.JSONDecodeError:
            return {}
        return value if isinstance(value, dict) else {}

    @data.setter
    def data(self, value: dict[str, Any]) -> None:
        self.data_json = json.dumps(value, ensure_ascii=False)

    def save(self, *args: Any, **kwargs: Any) -> None:
        if not self.expires_at:
            self.expires_at = timezone.now() + RETENTION
        super().save(*args, **kwargs)
