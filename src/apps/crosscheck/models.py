"""Modelos do Contraprova: a conferência, seus arquivos e seus achados.

Molde de `ReconciliationRun`/`FinancialReportExport`: arrendamento por UPDATE condicional,
fila por `on_commit`, recuperador no Beat. O que muda é o que fica guardado: os arquivos de
entrada são apagados 24 h depois do fim (D-302) e os achados e o relatório, em 90 dias; o
cabeçalho da conferência permanece como trilha.
"""

from __future__ import annotations

import uuid
from typing import Any

from django.core.exceptions import ValidationError
from django.core.files.storage import Storage, storages
from django.db import models

from apps.organizations.models import OrganizationScopedModel

from .engine.tools import TOOLS, ToolDef, choices


def crosscheck_storage() -> Storage:
    """Armazenamento privado do módulo (alias `crosscheck`; leitura em disco no S3)."""

    return storages["crosscheck"]


def _suffix(filename: str, default: str) -> str:
    return filename.rsplit(".", 1)[-1].lower() if "." in filename else default


def private_input_path(instance: CrosscheckInput, filename: str) -> str:
    """Caminho imprevisível e por escritório: o nome original nunca entra no caminho."""

    return (
        f"private/crosscheck/{instance.organization_id}/{instance.run_id}/"
        f"{instance.pk or uuid.uuid4()}.{_suffix(filename, 'bin')}"
    )


def private_result_path(instance: CrosscheckRun, filename: str) -> str:
    return (
        f"private/crosscheck/{instance.organization_id}/{instance.pk}/"
        f"resultado.{_suffix(filename, 'xlsx')}"
    )


class CrosscheckRun(OrganizationScopedModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        QUEUED = "queued", "Na fila"
        PROCESSING = "processing", "Conferindo"
        DONE = "done", "Concluída"
        FAILED = "failed", "Falhou"
        CANCELED = "canceled", "Cancelada"
        EXPIRED = "expired", "Expirada"

    ACTIVE_STATES = (State.QUEUED, State.PROCESSING)
    TERMINAL_STATES = (State.DONE, State.FAILED, State.CANCELED, State.EXPIRED)

    STAGE_LABELS = {
        "queued": "Na fila",
        "Preparando": "Preparando",
        "Lendo SPED": "Lendo o SPED",
        "Lendo XML": "Lendo os XML",
        "Comparando": "Comparando",
        "Gravando": "Gravando o resultado",
        "Relatório": "Gerando o relatório",
        "done": "Concluída",
    }

    company = models.ForeignKey(
        "hub.ClientCompany", on_delete=models.PROTECT, related_name="crosscheck_runs"
    )
    tool = models.CharField(max_length=16, choices=choices())
    #: Primeiro dia do mês da competência.
    competence = models.DateField()
    state = models.CharField(max_length=12, choices=State.choices, default=State.DRAFT)
    stage = models.CharField(max_length=40, blank=True)
    progress_done = models.PositiveIntegerField(default=0)
    progress_total = models.PositiveIntegerField(null=True, blank=True)
    options = models.JSONField(default=dict)
    rules_snapshot = models.JSONField(default=dict)
    #: Contagens, relatório dos arquivos, avisos e ingestão (JSON puro, sem CNPJ em chave).
    summary = models.JSONField(default=dict)
    #: Problemas que impediram a conferência (erro) ou ressalvas (aviso).
    problems = models.JSONField(default=list)
    error_code = models.CharField(max_length=60, blank=True)
    inputs_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    finding_count = models.PositiveIntegerField(default=0)
    divergent_count = models.PositiveIntegerField(default=0)
    ignored_count = models.PositiveIntegerField(default=0)
    matched_count = models.PositiveIntegerField(default=0)
    findings_truncated = models.BooleanField(default=False)
    result_file = models.FileField(
        upload_to=private_result_path, storage=crosscheck_storage, blank=True, max_length=300
    )
    result_sha256 = models.CharField(max_length=64, blank=True)
    result_size = models.PositiveBigIntegerField(default=0)
    attempts = models.PositiveSmallIntegerField(default=0)
    lease_token = models.UUIDField(null=True, blank=True, editable=False)
    lease_until = models.DateTimeField(null=True, blank=True, editable=False)
    cancel_requested_at = models.DateTimeField(null=True, blank=True)
    queued_at = models.DateTimeField(null=True, blank=True)
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    inputs_purged_at = models.DateTimeField(null=True, blank=True)
    results_expire_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("organization", "company", "created_at")),
            models.Index(fields=("organization", "state", "created_at")),
            models.Index(fields=("lease_until",)),
            models.Index(fields=("state", "finished_at")),
        ]

    def __str__(self) -> str:
        return f"{self.tool} {self.competence:%Y-%m} {self.state}"

    @property
    def tool_def(self) -> ToolDef:
        return TOOLS[self.tool]

    @property
    def competence_label(self) -> str:
        return f"{self.competence:%m/%Y}"

    @property
    def is_active(self) -> bool:
        return self.state in self.ACTIVE_STATES

    @property
    def is_terminal(self) -> bool:
        return self.state in self.TERMINAL_STATES

    @property
    def stage_label(self) -> str:
        return self.STAGE_LABELS.get(self.stage, self.stage)

    @property
    def has_result(self) -> bool:
        return self.state == self.State.DONE and bool(self.result_file)

    @property
    def inputs_available(self) -> bool:
        return self.inputs_purged_at is None

    def clean(self) -> None:
        super().clean()
        if self.company_id and self.company.organization_id != self.organization_id:
            raise ValidationError("A conferência precisa pertencer ao escritório da empresa.")
        if self.competence and self.competence.day != 1:
            raise ValidationError("A competência é o primeiro dia do mês.")

    def problem_messages(self, severity: str | None = None) -> list[dict[str, Any]]:
        items = [item for item in self.problems if isinstance(item, dict)]
        if severity is None:
            return items
        return [item for item in items if item.get("severity") == severity]


class CrosscheckInput(OrganizationScopedModel):
    class Kind(models.TextChoices):
        EFD = "efd", "SPED"
        XML = "xml", "XML"
        DOMINIO = "dominio", "Domínio"

    run = models.ForeignKey(CrosscheckRun, on_delete=models.CASCADE, related_name="inputs")
    role = models.CharField(max_length=16)
    kind = models.CharField(max_length=10, choices=Kind.choices)
    original_name = models.CharField(max_length=255)
    size_bytes = models.PositiveBigIntegerField()
    sha256 = models.CharField(max_length=64)
    content = models.FileField(
        upload_to=private_input_path, storage=crosscheck_storage, max_length=300, blank=True
    )
    #: O que o servidor viu ao receber: cabeçalho da EFD, contagem do ZIP, fonte do Domínio.
    detected = models.JSONField(default=dict)
    xml_count = models.PositiveIntegerField(default=0)
    uploaded_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    purged_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("run", "role"))]

    def __str__(self) -> str:
        return f"{self.role}:{self.original_name}"

    def clean(self) -> None:
        super().clean()
        if self.run_id and self.run.organization_id != self.organization_id:
            raise ValidationError("O arquivo precisa pertencer ao escritório da conferência.")


class CrosscheckFinding(models.Model):
    """Um achado da conferência. Só o que diverge ou foi ignorado por regra vai para o banco."""

    run = models.ForeignKey(CrosscheckRun, on_delete=models.CASCADE, related_name="findings")
    seq = models.PositiveIntegerField()
    kind = models.CharField(max_length=32)
    status = models.CharField(max_length=10)
    doc_key = models.CharField(max_length=80, blank=True)
    doc_type = models.CharField(max_length=8, blank=True)
    number = models.CharField(max_length=20, blank=True)
    field = models.CharField(max_length=40, blank=True)
    field_label = models.CharField(max_length=120, blank=True)
    left_cents = models.BigIntegerField(null=True, blank=True)
    right_cents = models.BigIntegerField(null=True, blank=True)
    left_text = models.CharField(max_length=120, blank=True)
    right_text = models.CharField(max_length=120, blank=True)
    cfop = models.CharField(max_length=60, blank=True)
    operation = models.CharField(max_length=1, blank=True)
    message = models.CharField(max_length=300, blank=True)
    detail = models.JSONField(default=dict)

    class Meta:
        ordering = ("seq",)
        indexes = [
            models.Index(fields=("run", "kind", "status")),
            models.Index(fields=("run", "doc_key")),
        ]

    @property
    def delta_cents(self) -> int | None:
        if self.left_cents is None or self.right_cents is None:
            return None
        return self.left_cents - self.right_cents

    def __str__(self) -> str:
        return f"{self.kind} {self.doc_key[:12]}"


class CrosscheckAgentJob(OrganizationScopedModel):
    """Pedido de consulta de UF ao Domínio pelo agente Windows (fila "pull", D-300).

    O id do job é a chave de idempotência do protocolo: a nuvem nunca manda SQL, só o código do
    dataset, a versão, o hash e os parâmetros que o contrato declara.
    """

    class State(models.TextChoices):
        QUEUED = "queued", "Na fila"
        CLAIMED = "claimed", "Agente consultando"
        RECEIVING = "receiving", "Recebendo"
        SUCCEEDED = "succeeded", "Recebido"
        FAILED = "failed", "Falhou"
        EXPIRED = "expired", "Expirado"

    ACTIVE_STATES = (State.QUEUED, State.CLAIMED, State.RECEIVING)

    run = models.ForeignKey(CrosscheckRun, on_delete=models.CASCADE, related_name="agent_jobs")
    state = models.CharField(max_length=10, choices=State.choices, default=State.QUEUED)
    dataset_code = models.CharField(max_length=64)
    schema_version = models.PositiveSmallIntegerField()
    query_sha256 = models.CharField(max_length=64)
    #: Lista ordenada de {name, value, odbc_type}: a ordem é a do manifesto (vínculo posicional).
    parameters = models.JSONField(default=list)
    codi_emp = models.PositiveIntegerField()
    window_start = models.DateField()
    window_end = models.DateField()
    row_limit = models.PositiveIntegerField()
    claimed_by = models.CharField(max_length=64, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    last_activity_at = models.DateTimeField(null=True, blank=True)
    next_sequence = models.PositiveIntegerField(default=0)
    rows_received = models.PositiveIntegerField(default=0)
    error_code = models.CharField(max_length=40, blank=True)
    error_detail = models.CharField(max_length=200, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    requested_by = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("organization", "state", "created_at")),
            models.Index(fields=("run", "state")),
        ]

    def __str__(self) -> str:
        return f"{self.dataset_code} {self.state}"

    @property
    def is_active(self) -> bool:
        return self.state in self.ACTIVE_STATES


class CrosscheckDominioRow(models.Model):
    """Uma chave, a direção e a UF que o Domínio tem. Apagada com as entradas (D-302)."""

    run = models.ForeignKey(CrosscheckRun, on_delete=models.CASCADE, related_name="dominio_rows")
    job = models.ForeignKey(CrosscheckAgentJob, on_delete=models.CASCADE, related_name="rows")
    chave = models.CharField(max_length=44)
    direcao = models.CharField(max_length=1)
    uf = models.CharField(max_length=2, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("run", "chave", "direcao"), name="crosscheck_unique_dominio_row"
            )
        ]
        indexes = [models.Index(fields=("run", "id"))]

    def __str__(self) -> str:
        return f"{self.direcao} {self.chave[:12]} {self.uf}"
