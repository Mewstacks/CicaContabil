"""Fila genérica de trabalhos RPA para o agente Windows.

Todo modelo é ``OrganizationScopedModel``. O trabalho descreve *o quê* (carga sem segredo); o
agente executa na máquina do escritório e devolve resultado e artefatos com hash. A reserva é um
``lease`` com token que gira a cada reivindicação: um agente atrasado, cuja reserva foi dada a
outro, não consegue mais renovar nem fechar.
"""

from __future__ import annotations

from django.db import models
from django.db.models import Q

from apps.organizations.models import OrganizationScopedModel
from apps.triage.storage import PrivateTriageStorage


class RpaJob(OrganizationScopedModel):
    class State(models.TextChoices):
        QUEUED = "queued", "Na fila"
        LEASED = "leased", "Em execução"
        SUCCEEDED = "succeeded", "Concluído"
        FAILED = "failed", "Falhou"
        UNCERTAIN = "uncertain", "Incerto"
        CANCELLED = "cancelled", "Cancelado"

    TERMINAL = (State.SUCCEEDED, State.FAILED, State.UNCERTAIN, State.CANCELLED)

    kind = models.CharField(max_length=48)
    idempotency_key = models.CharField(max_length=120)
    payload = models.JSONField(default=dict, blank=True)
    state = models.CharField(max_length=12, choices=State.choices, default=State.QUEUED)
    attempts = models.PositiveSmallIntegerField(default=0)
    max_attempts = models.PositiveSmallIntegerField(default=3)
    not_before = models.DateTimeField(null=True, blank=True)
    leased_by = models.CharField(max_length=64, blank=True)
    lease_token_hash = models.CharField(max_length=64, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    last_heartbeat_at = models.DateTimeField(null=True, blank=True)
    phase = models.CharField(max_length=40, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.JSONField(default=dict, blank=True)
    error_code = models.CharField(max_length=40, blank=True)
    error_detail = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "kind", "idempotency_key"),
                name="rpa_unique_job_key_per_office",
            ),
            models.CheckConstraint(
                condition=~Q(state="leased") | ~Q(lease_token_hash=""),
                name="rpa_leased_has_token",
            ),
        ]
        indexes = [
            models.Index(fields=("organization", "state", "not_before")),
            models.Index(fields=("kind", "state")),
        ]

    def __str__(self) -> str:
        return f"{self.kind}:{self.idempotency_key} ({self.state})"


class RpaJobEvent(OrganizationScopedModel):
    """Trilha do que aconteceu com o trabalho; texto sempre passa por ``redact_text``."""

    job = models.ForeignKey(RpaJob, on_delete=models.CASCADE, related_name="events")
    event = models.CharField(max_length=32)
    detail = models.CharField(max_length=500, blank=True)

    class Meta:
        indexes = [models.Index(fields=("job", "created_at"))]


def _artifact_path(instance: RpaArtifact, filename: str) -> str:
    return f"rpa/{instance.organization_id}/{instance.job_id}/{instance.id}.bin"


class RpaArtifact(OrganizationScopedModel):
    """Arquivo produzido na máquina do agente (relatório, guia, comprovante), com hash conferido."""

    job = models.ForeignKey(RpaJob, on_delete=models.CASCADE, related_name="artifacts")
    name = models.CharField(max_length=200)
    sha256 = models.CharField(max_length=64)
    byte_size = models.PositiveIntegerField()
    content_type = models.CharField(max_length=80, blank=True)
    file = models.FileField(upload_to=_artifact_path, storage=PrivateTriageStorage())

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("job", "sha256"), name="rpa_artifact_once_per_job")
        ]
