"""The triage domain: mailboxes, the naming catalogue, items and their destination.

Every model here is ``OrganizationScopedModel`` — one office never sees another's mail,
catalogue, item or destination. Nothing in this module performs I/O: no mailbox is
polled, no AI adapter is called, no file is written. Those belong to later fronts
(see ``docs/plano-triagem-documental.md`` and the approved implementation plan) that
build services on top of this schema.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.common.encryption import EncryptedTextField
from apps.organizations.models import OrganizationScopedModel
from apps.triage.storage import PrivateTriageStorage
from apps.triage.transitions import TriageStatus, ensure_transition_allowed


def private_triage_path(instance: TriageBlob, filename: str) -> str:
    suffix = filename.rsplit(".", 1)[-1].lower() if "." in filename else "bin"
    return (
        f"private/triage/{instance.triage_item.organization_id}/{instance.triage_item_id}.{suffix}"
    )


class Mailbox(OrganizationScopedModel):
    """A connected inbox the triage poller reads attachments from."""

    class Provider(models.TextChoices):
        MS365_GRAPH = "ms365_graph", "Microsoft 365 (Graph)"
        GMAIL_API = "gmail_api", "Gmail / Google Workspace"
        IMAP = "imap", "IMAP"

    class Status(models.TextChoices):
        PENDING = "pending", "Aguardando autorização"
        ACTIVE = "active", "Ativa"
        ERROR = "error", "Com erro"
        DISABLED = "disabled", "Desativada"

    provider = models.CharField(max_length=16, choices=Provider.choices)
    address = models.EmailField()
    folder = models.CharField(max_length=160, default="INBOX")
    # OAuth token / app-password / refresh token, whichever the provider needs. Never
    # logged, never returned to a template — only decrypted inside the poller service.
    credential = EncryptedTextField(blank=True)
    # Provider checkpoints can be long and contain opaque tokens. Encrypt them at rest.
    cursor = EncryptedTextField(blank=True)
    since = models.DateTimeField(null=True, blank=True)
    sender_filter = models.CharField(max_length=255, blank=True)
    subject_filter = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    last_polled_at = models.DateTimeField(null=True, blank=True)
    last_error = models.CharField(max_length=500, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "provider", "address", "folder"),
                name="triage_unique_mailbox_per_office",
            )
        ]
        indexes = [models.Index(fields=("organization", "active"))]

    def __str__(self) -> str:
        return f"{self.address} ({self.get_provider_display()})"


class DocumentType(OrganizationScopedModel):
    """One row of the approved naming catalogue (the 19 entries from the photo)."""

    class PeriodKind(models.TextChoices):
        COMPETENCIA = "competencia", "Competência (mês)"
        INTERVALO = "intervalo", "Intervalo de datas"
        DATA_PAGAMENTO = "data_pagamento", "Data de pagamento"
        ANUAL = "anual", "Anual"

    class CounterpartyKind(models.TextChoices):
        NONE = "nenhuma", "Nenhuma"
        BANCO = "banco", "Banco"
        INSTITUICAO = "instituicao", "Instituição financeira"
        IMOBILIARIA = "imobiliaria", "Imobiliária"
        INQUILINO = "inquilino", "Inquilino"

    code = models.SlugField(max_length=64)
    label = models.CharField(max_length=160)
    # e.g. "{codigo}_EXTRATO_{contraparte}_{periodo}" — rendered by the naming front.
    name_template = models.CharField(max_length=200)
    folder_template = models.CharField(max_length=200, blank=True)
    period_kind = models.CharField(max_length=16, choices=PeriodKind.choices)
    counterparty_kind = models.CharField(
        max_length=16, choices=CounterpartyKind.choices, default=CounterpartyKind.NONE
    )
    active = models.BooleanField(default=True)
    revision = models.PositiveIntegerField(default=1)

    class Meta:
        ordering = ("label",)
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "code"), name="triage_unique_document_type_code"
            )
        ]

    def __str__(self) -> str:
        return self.label


class CounterpartyAlias(OrganizationScopedModel):
    """The approved lookup that fills a document name's BANCO/IMOBILIARIA/... marker.

    The AI never invents a token here — it can only match text in the document against
    an alias already registered by the office, per the plan's evidence requirement.
    """

    kind = models.CharField(max_length=16, choices=DocumentType.CounterpartyKind.choices)
    token = models.CharField(max_length=64)
    alias = models.CharField(max_length=160)

    class Meta:
        ordering = ("kind", "token")
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "kind", "alias"),
                name="triage_unique_counterparty_alias",
            )
        ]
        indexes = [models.Index(fields=("organization", "kind", "token"))]

    def __str__(self) -> str:
        return f"{self.token} ({self.alias})"


class DestinationProfile(OrganizationScopedModel):
    """Where an office's archived documents land — exclusive choice, not a mix."""

    class Mode(models.TextChoices):
        INTERNAL = "internal", "Biblioteca interna"
        WINDOWS = "windows", "Pastas Windows"

    organization = models.OneToOneField(
        "organizations.Organization", on_delete=models.CASCADE, related_name="triage_destination"
    )
    mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.INTERNAL)
    # Only meaningful when mode == WINDOWS: the root the agent is allowed to write under.
    windows_root = models.CharField(max_length=500, blank=True)
    folder_template = models.CharField(max_length=200, blank=True)

    def __str__(self) -> str:
        return f"{self.organization_id} -> {self.get_mode_display()}"


class TriageItem(OrganizationScopedModel):
    """One received attachment moving through quarantine, classification and archiving."""

    Status = TriageStatus

    mailbox = models.ForeignKey(
        Mailbox, null=True, blank=True, on_delete=models.SET_NULL, related_name="items"
    )
    message_id = models.CharField(max_length=255, blank=True)
    part_id = models.CharField(max_length=64, blank=True)
    sender = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=500, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)

    original_name = models.CharField(max_length=255)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    byte_size = models.PositiveBigIntegerField(default=0)
    declared_type = models.CharField(max_length=100, blank=True)
    detected_type = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=24, choices=TriageStatus.choices, default=TriageStatus.RECEIVED
    )

    company = models.ForeignKey(
        "hub.ClientCompany", null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    document_type = models.ForeignKey(
        DocumentType, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    period_label = models.CharField(max_length=16, blank=True)
    counterparty_token = models.CharField(max_length=64, blank=True)
    final_name = models.CharField(max_length=255, blank=True)

    # {campo: {"valor": ..., "confianca": 0.0-1.0, "evidencia": "...", "pagina": int}}
    ai_fields = models.JSONField(default=dict, blank=True)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.CharField(max_length=500, blank=True)

    destination_kind = models.CharField(
        max_length=16, choices=DestinationProfile.Mode.choices, blank=True
    )
    destination_path = models.CharField(max_length=500, blank=True)
    destination_hash = models.CharField(max_length=64, blank=True)
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(
                fields=("mailbox", "message_id", "part_id"),
                condition=models.Q(mailbox__isnull=False) & ~models.Q(message_id=""),
                name="triage_unique_mailbox_message_part",
            ),
            models.UniqueConstraint(
                fields=("organization", "content_hash"),
                condition=models.Q(content_hash__gt=""),
                name="triage_unique_content_hash_per_office",
            ),
        ]
        indexes = [models.Index(fields=("organization", "status"))]

    def __str__(self) -> str:
        return self.final_name or self.original_name

    def transition_to(self, target: str) -> None:
        """Move to ``target`` or raise ``InvalidTransition``. Does not save()."""

        ensure_transition_allowed(self.status, target)
        self.status = target

    def clean(self) -> None:
        errors: dict[str, str] = {}
        for field in ("mailbox", "company", "document_type"):
            related = getattr(self, field, None)
            if related is not None and related.organization_id != self.organization_id:
                errors[field] = "Este registro pertence a outro escritório."
        if errors:
            raise ValidationError(errors)


class TriageBlob(OrganizationScopedModel):
    """The quarantined binary itself, kept apart from anything servable."""

    triage_item = models.OneToOneField(TriageItem, on_delete=models.CASCADE, related_name="blob")
    content = models.FileField(upload_to=private_triage_path, storage=PrivateTriageStorage())
    content_type = models.CharField(max_length=100, blank=True)

    def __str__(self) -> str:
        return f"blob for {self.triage_item_id}"

    def clean(self) -> None:
        if self.triage_item_id and self.triage_item.organization_id != self.organization_id:
            raise ValidationError({"triage_item": "O arquivo pertence a outro escritório."})


class TriageEvent(OrganizationScopedModel):
    """Append-only evidence of a state change or reviewer decision."""

    triage_item = models.ForeignKey(TriageItem, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    note = models.CharField(max_length=500, blank=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("organization", "triage_item", "created_at"))]

    def clean(self) -> None:
        if self.triage_item_id and self.triage_item.organization_id != self.organization_id:
            raise ValidationError({"triage_item": "O evento pertence a outro escritório."})


class ChecklistExpectation(OrganizationScopedModel):
    """What a company is expected to deliver, independent of any folder layout."""

    class Requirement(models.TextChoices):
        EXPECTED = "expected", "Esperado"
        OPTIONAL = "optional", "Opcional"
        WAIVED = "waived", "Dispensado"
        NOT_APPLICABLE = "not_applicable", "Não se aplica"

    company = models.ForeignKey(
        "hub.ClientCompany", on_delete=models.CASCADE, related_name="triage_expectations"
    )
    document_type = models.ForeignKey(
        DocumentType, on_delete=models.CASCADE, related_name="expectations"
    )
    requirement = models.CharField(
        max_length=16, choices=Requirement.choices, default=Requirement.EXPECTED
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("company", "document_type"), name="triage_unique_expectation"
            )
        ]

    def __str__(self) -> str:
        return f"{self.company_id}/{self.document_type_id}: {self.requirement}"


class ChecklistEntry(OrganizationScopedModel):
    """One period's delivery status for one expected document type."""

    company = models.ForeignKey(
        "hub.ClientCompany", on_delete=models.CASCADE, related_name="triage_checklist_entries"
    )
    document_type = models.ForeignKey(
        DocumentType, on_delete=models.CASCADE, related_name="checklist_entries"
    )
    period_label = models.CharField(max_length=16)
    triage_item = models.ForeignKey(
        TriageItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-period_label",)
        constraints = [
            models.UniqueConstraint(
                fields=("company", "document_type", "period_label"),
                name="triage_unique_checklist_entry",
            )
        ]

    def __str__(self) -> str:
        return f"{self.company_id}/{self.document_type_id}/{self.period_label}"


class AgentFileJob(OrganizationScopedModel):
    """A move-file instruction dispatched to the office's local Windows agent.

    Schema only in this front: the claim/dispatch endpoints, the path allowlist and the
    .NET handler are a later, higher-risk front (see the plan doc, front 10).
    """

    class Status(models.TextChoices):
        QUEUED = "queued", "Na fila"
        CLAIMED = "claimed", "Reivindicado pelo agente"
        DONE = "done", "Concluído"
        FAILED = "failed", "Falhou"

    triage_item = models.ForeignKey(TriageItem, on_delete=models.CASCADE, related_name="agent_jobs")
    destination_path = models.CharField(max_length=500)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.QUEUED)
    claimed_by = models.CharField(max_length=64, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    result = models.CharField(max_length=500, blank=True)

    class Meta:
        indexes = [models.Index(fields=("organization", "status"))]

    def __str__(self) -> str:
        return f"{self.triage_item_id} -> {self.destination_path} ({self.status})"
