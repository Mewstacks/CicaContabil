"""Folha: ciclos de relatórios no Domínio desktop, envio ao cliente e marcação da planilha.

Módulo por escritório (``ProductModule.Code.FOLHA``), desligado por padrão. O trabalho no
Domínio é executado pelo agente Windows através da fila ``apps.rpa``; aqui ficam o ciclo, as
tarefas por empresa/item, a conferência, o envio e a planilha. Portado do ``relatorios_folha`` do
HubFedrizzi sem o motor 32-bit (que continua fora, como executor do agente).
"""

from __future__ import annotations

from django.conf import settings
from django.db import models
from django.db.models import Q

from apps.hub.models import ClientCompany
from apps.organizations.models import OrganizationScopedModel
from apps.rpa.models import RpaJob

ITEMS = ("calculo", "extrato", "recibo_folha", "liquidos", "programacao_ferias")
ITEM_LABELS = {
    "calculo": "Cálculo da folha",
    "extrato": "Extrato",
    "recibo_folha": "Recibo de pagamento",
    "liquidos": "Líquidos",
    "programacao_ferias": "Programação de férias",
}
#: O cálculo ALTERA dados no Domínio: nunca anexa, nunca vai ao cliente, exige confirmação.
NEVER_ATTACH = frozenset({"calculo"})


class FolhaSettings(OrganizationScopedModel):
    """Travas e agenda do escritório. Sem linha ou lista vazia, nenhuma empresa é autorizada."""

    authorized_codes = models.JSONField(default=list, blank=True)
    schedule_enabled = models.BooleanField(default=False)
    schedule_day = models.PositiveSmallIntegerField(default=5)
    schedule_codes = models.JSONField(default=list, blank=True)
    schedule_items = models.JSONField(default=list, blank=True)
    last_scheduled_competence = models.DateField(null=True, blank=True)
    sheets_enabled = models.BooleanField(default=False)
    sheets_spreadsheet_id = models.CharField(max_length=120, blank=True)
    sheets_tab_template = models.CharField(max_length=60, blank=True)
    sheets_ignore_codes = models.JSONField(default=list, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("organization",), name="folha_one_settings_per_office"),
            models.CheckConstraint(
                condition=Q(schedule_day__gte=1, schedule_day__lte=28),
                name="folha_schedule_day_1_28",
            ),
        ]


class FolhaCycle(OrganizationScopedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        QUEUED = "queued", "Na fila"
        RUNNING = "running", "Em execução"
        PARTIAL = "partial", "Parcial"
        REVIEW = "review", "Aguardando conferência"
        APPROVAL = "approval", "Aguardando aprovação"
        DONE = "done", "Concluído"
        CANCELLED = "cancelled", "Cancelado"

    competence = models.DateField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    note = models.CharField(max_length=200, blank=True)
    from_schedule = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    confirmed_calc = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=("organization", "competence"))]


class FolhaTask(OrganizationScopedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        RUNNING = "running", "Em execução"
        OK = "ok", "Salvo"
        FAILED = "failed", "Falhou"
        EMPTY = "empty", "Sem dados"
        CANCELLED = "cancelled", "Cancelado"

    ACTIVE = (Status.PENDING, Status.RUNNING)
    FINISHED = (Status.OK, Status.FAILED, Status.EMPTY, Status.CANCELLED)

    cycle = models.ForeignKey(FolhaCycle, on_delete=models.CASCADE, related_name="tasks")
    company = models.ForeignKey(ClientCompany, on_delete=models.PROTECT, related_name="+")
    item = models.CharField(max_length=24)
    competence = models.DateField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING)
    job = models.ForeignKey(
        RpaJob, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    validation = models.CharField(max_length=24, blank=True)
    output_name = models.CharField(max_length=200, blank=True)
    sha256 = models.CharField(max_length=64, blank=True)
    byte_size = models.PositiveIntegerField(default=0)
    error = models.CharField(max_length=500, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    finished_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            # No máximo uma tarefa ativa por empresa/item/competência (idempotência do pedido).
            models.UniqueConstraint(
                fields=("organization", "company", "item", "competence"),
                condition=Q(status__in=["pending", "running"]),
                name="folha_one_active_task",
            )
        ]
        indexes = [models.Index(fields=("cycle", "status"))]


class FolhaTitle(OrganizationScopedModel):
    """Nome de arquivo de cada relatório; o motor usa o rótulo padrão quando não há linha."""

    key = models.CharField(max_length=24)
    name = models.CharField(max_length=120)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("organization", "key"), name="folha_one_title_per_key")
        ]


class FolhaCatalog(OrganizationScopedModel):
    """Catálogo de campos (validado inteiro antes de usar). Só um ativo por escritório."""

    version = models.CharField(max_length=40)
    rules = models.JSONField(default=dict)
    active = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization",),
                condition=Q(active=True),
                name="folha_one_active_catalog",
            )
        ]


class FolhaReport(OrganizationScopedModel):
    """Conferência de um relatório salvo: campos lidos, correção humana e aprovação."""

    class State(models.TextChoices):
        PENDING = "pending", "A conferir"
        APPROVED = "approved", "Aprovado"
        REJECTED = "rejected", "Reprovado"

    task = models.OneToOneField(FolhaTask, on_delete=models.CASCADE, related_name="report")
    state = models.CharField(max_length=10, choices=State.choices, default=State.PENDING)
    parser_version = models.CharField(max_length=40, blank=True)
    fields = models.JSONField(default=list, blank=True)
    problems = models.JSONField(default=list, blank=True)


class FolhaContact(OrganizationScopedModel):
    """Contato da empresa como lido no cadastro do Domínio (fonte da decisão do destinatário)."""

    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE, related_name="+")
    emails = models.JSONField(default=list)
    note = models.CharField(max_length=300, blank=True)
    synced_at = models.DateTimeField(auto_now=True)


class FolhaEmail(OrganizationScopedModel):
    class State(models.TextChoices):
        DRAFT = "draft", "Rascunho"
        APPROVED = "approved", "Aprovado"
        SENDING = "sending", "Enviando"
        SENT = "sent", "Enviado"
        FAILED = "failed", "Falhou"
        VOID = "void", "Invalidado"

    cycle = models.ForeignKey(FolhaCycle, on_delete=models.CASCADE, related_name="emails")
    company = models.ForeignKey(ClientCompany, on_delete=models.PROTECT, related_name="+")
    idempotency_key = models.CharField(max_length=120)
    state = models.CharField(max_length=10, choices=State.choices, default=State.DRAFT)
    sender = models.CharField(max_length=254)
    recipients = models.JSONField(default=list)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    attachments = models.JSONField(default=list)  # [{artifact, name, sha256}]
    payment_date = models.DateField(null=True, blank=True)
    inss_due_date = models.DateField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    message_id = models.CharField(max_length=200, blank=True)
    error = models.CharField(max_length=500, blank=True)
    reconciled_note = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "idempotency_key"), name="folha_one_email_per_key"
            )
        ]


class FolhaSheetMark(OrganizationScopedModel):
    """Caixa de saída da planilha: uma marcação por (competência, empresa, etapa)."""

    class Stage(models.TextChoices):
        CALC = "calc", "Cálculo"
        REPORTS = "reports", "Relatórios"
        EMAIL = "email", "E-mail"

    class State(models.TextChoices):
        PENDING = "pending", "Pendente"
        DONE = "done", "Gravado"
        ERROR = "error", "Erro (tenta de novo)"
        FINAL_ERROR = "final_error", "Erro final"

    competence = models.DateField()
    company_code = models.CharField(max_length=64)
    company = models.ForeignKey(ClientCompany, on_delete=models.CASCADE, related_name="+")
    stage = models.CharField(max_length=8, choices=Stage.choices)
    state = models.CharField(max_length=12, choices=State.choices, default=State.PENDING)
    attempts = models.PositiveSmallIntegerField(default=0)
    error = models.CharField(max_length=300, blank=True)
    tab = models.CharField(max_length=60, blank=True)
    cell = models.CharField(max_length=20, blank=True)
    next_try_at = models.DateTimeField(null=True, blank=True)
    written_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "competence", "company_code", "stage"),
                name="folha_one_mark_per_stage",
            )
        ]
