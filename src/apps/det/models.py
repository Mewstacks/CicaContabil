"""DET (Domicílio Eletrônico Trabalhista): leitura somente da lista de mensagens NÃO LIDAS.

Regra central, herdada do HubFedrizzi: o agente nunca abre mensagem, link ou anexo (abrir pode
registrar ciência). O servidor guarda só o que a lista mostra e recusa o resultado quando a
contagem do portal não bate com as linhas lidas.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.organizations.models import OrganizationScopedModel
from apps.rpa.models import RpaJob


class DetQuery(OrganizationScopedModel):
    class State(models.TextChoices):
        QUEUED = "queued", "Na fila"
        RUNNING = "running", "Em execução"
        DONE = "done", "Concluída"
        FAILED = "failed", "Falhou"
        CANCELLED = "cancelled", "Cancelada"

    state = models.CharField(max_length=10, choices=State.choices, default=State.QUEUED)
    companies = models.JSONField(default=list)  # [{code, name, cnpj}] — o que foi autorizado
    total_messages = models.PositiveIntegerField(default=0)
    notice = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL, related_name="+"
    )


class DetChunk(OrganizationScopedModel):
    """Um pedaço da consulta (poucas empresas) entregue ao agente como um trabalho."""

    query = models.ForeignKey(DetQuery, on_delete=models.CASCADE, related_name="chunks")
    position = models.PositiveSmallIntegerField()
    job = models.ForeignKey(
        RpaJob, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("query", "position"), name="det_one_chunk_position")
        ]


class DetResult(OrganizationScopedModel):
    class Situation(models.TextChoices):
        UNREAD = "unread", "Com mensagens não lidas"
        NONE = "none", "Sem mensagens não lidas"
        NO_PROXY = "no_proxy", "Sem procuração"
        NOT_FOUND = "not_found", "CNPJ não encontrado no DET"
        PENDING_SETUP = "pending_setup", "Cadastro pendente no DET"
        CEI_ONLY = "cei_only", "Empregador com CEI, sem CPF"
        ERROR = "error", "Erro na consulta"

    query = models.ForeignKey(DetQuery, on_delete=models.CASCADE, related_name="results")
    company_code = models.CharField(max_length=64)
    company_name = models.CharField(max_length=255, blank=True)
    cnpj = models.CharField(max_length=14)
    situation = models.CharField(max_length=14, choices=Situation.choices)
    messages = models.JSONField(default=list, blank=True)
    detail = models.CharField(max_length=1000, blank=True)

    class Meta:
        constraints = [
            # O reenvio de uma empresa (perda de rede, tentativa nova) substitui, não duplica.
            models.UniqueConstraint(
                fields=("query", "company_code"), name="det_one_result_per_company"
            )
        ]
