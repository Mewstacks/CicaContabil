"""The triage domain: mailboxes, the naming catalogue, items and their destination.

Every model here is ``OrganizationScopedModel`` — one office never sees another's mail,
catalogue, item or destination. I/O belongs in services, never in these models.
"""

from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.common.encryption import EncryptedTextField
from apps.organizations.models import OrganizationScopedModel
from apps.triage.storage import PrivateTriageStorage
from apps.triage.transitions import TriageStatus, ensure_transition_allowed


def private_triage_path(instance: TriageBlob, filename: str) -> str:
    # The original name is metadata. Never let an untrusted extension shape a storage path.
    return f"private/triage/{instance.triage_item.organization_id}/{instance.triage_item_id}.bin"


class MailboxOAuthApp(OrganizationScopedModel):
    """OAuth application registered and controlled by one office."""

    class Provider(models.TextChoices):
        MS365_GRAPH = "ms365_graph", "Microsoft 365"
        GMAIL_API = "gmail_api", "Gmail / Google Workspace"

    provider = models.CharField(max_length=16, choices=Provider.choices)
    client_id = models.CharField(max_length=255)
    client_secret = EncryptedTextField()
    # Microsoft single-tenant registration uses its Directory (tenant) ID.
    tenant_id = models.CharField(max_length=64, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "provider"), name="triage_one_oauth_app_per_office_provider"
            )
        ]


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
    oauth_app = models.ForeignKey(
        MailboxOAuthApp, null=True, blank=True, on_delete=models.SET_NULL, related_name="mailboxes"
    )
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
    # Database lease prevents overlapping Celery workers from polling one mailbox.
    # Expiration permits recovery after a worker crash.
    poll_lease_until = models.DateTimeField(null=True, blank=True)
    poll_lease_token = models.UUIDField(null=True, blank=True)
    poll_retry_after = models.DateTimeField(null=True, blank=True)
    poll_failure_count = models.PositiveSmallIntegerField(default=0)
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

    def clean(self) -> None:
        oauth_app = self.oauth_app
        if self.oauth_app_id and oauth_app is not None and (
            oauth_app.organization_id != self.organization_id or oauth_app.provider != self.provider
        ):
            raise ValidationError(
                {"oauth_app": "O aplicativo não pertence a esta caixa e escritório."}
            )


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
    # Words that identify the type. ``@word`` only counts in the file name and the subject
    # (it is too common in running text). Matching is whole-word and accent-blind.
    keywords = models.JSONField(default=list, blank=True, db_default=[])
    # Expected in the checklist: for every company, or only for these tax regimes
    # (``ClientCompany.TaxRegime`` values). A ``ChecklistExpectation`` of one company wins.
    expected_default = models.BooleanField(default=False, db_default=False)
    expected_regimes = models.JSONField(default=list, blank=True, db_default=[])

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


class TriagePolicy(OrganizationScopedModel):
    """Per-office switches for the v2 intake. Every default keeps the v1 behaviour."""

    organization = models.OneToOneField(
        "organizations.Organization", on_delete=models.CASCADE, related_name="triage_policy"
    )
    # Images, HTML, TXT and legacy XLS beside the base PDF/CSV/XML/OFX/XLSX set.
    extended_formats = models.BooleanField(default=False, db_default=False)
    # Open ZIP packages (bounded: entries, bytes, ratio, depth) into one item per file.
    open_archives = models.BooleanField(default=False, db_default=False)
    # OCR for scanned PDFs and images; also needs ``TRIAGE_OCR_ENABLED`` and a free budget.
    ocr_enabled = models.BooleanField(default=False, db_default=False)
    ocr_monthly_pages = models.PositiveIntegerField(default=100, db_default=100)

    def __str__(self) -> str:
        return f"triage policy {self.organization_id}"


class TriageItem(OrganizationScopedModel):
    """One received attachment moving through quarantine, classification and archiving."""

    Status = TriageStatus

    class Origin(models.TextChoices):
        EMAIL = "email", "E-mail"
        UPLOAD = "upload", "Envio manual"
        ARCHIVE = "archive", "Pacote"

    mailbox = models.ForeignKey(
        Mailbox, null=True, blank=True, on_delete=models.SET_NULL, related_name="items"
    )
    message_id = models.CharField(max_length=255, blank=True)
    part_id = models.CharField(max_length=64, blank=True)
    sender = models.CharField(max_length=255, blank=True)
    subject = models.CharField(max_length=500, blank=True)
    received_at = models.DateTimeField(null=True, blank=True)
    origin = models.CharField(
        max_length=16, choices=Origin.choices, blank=True, default="", db_default=""
    )
    # Plain-text start of the e-mail body (bounded) and, for a forwarded message, the one
    # external author found in it. Personal data: never logged, never sent out.
    body_excerpt = models.TextField(blank=True, default="", db_default="")
    original_sender = models.CharField(max_length=254, blank=True, default="", db_default="")
    # The package this file was opened from (one level only).
    archive_parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="archive_members"
    )

    original_name = models.CharField(max_length=255)
    content_hash = models.CharField(max_length=64, blank=True, db_index=True)
    byte_size = models.PositiveBigIntegerField(default=0)
    declared_type = models.CharField(max_length=100, blank=True)
    detected_type = models.CharField(max_length=100, blank=True)

    status = models.CharField(
        max_length=24, choices=TriageStatus.choices, default=TriageStatus.RECEIVED
    )
    # Automatic scan/extraction runs started for this item. The recovery job stops at a
    # cap so a deterministic failure does not loop; a person can reset it (Reprocessar).
    pipeline_attempts = models.PositiveSmallIntegerField(default=0, db_default=0)
    # Same bytes already received by this office: the copy is closed, not classified again.
    duplicate_of = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="duplicates"
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
    # OCR runs on its own queue: "" never needed, queued, done, skipped (flag/budget/engine),
    # failed. ``ocr_text`` keeps the bounded result so reclassifying never repeats the OCR.
    ocr_state = models.CharField(max_length=12, blank=True, default="", db_default="")
    ocr_text = models.TextField(blank=True, default="", db_default="")

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
        ]
        indexes = [
            models.Index(fields=("organization", "status")),
            models.Index(fields=("organization", "content_hash")),
        ]

    def __str__(self) -> str:
        return self.final_name or self.original_name

    def transition_to(self, target: str) -> None:
        """Move to ``target`` or raise ``InvalidTransition``. Does not save()."""

        ensure_transition_allowed(self.status, target)
        self.status = target

    def clean(self) -> None:
        errors: dict[str, str] = {}
        for field in ("mailbox", "company", "document_type", "duplicate_of", "archive_parent"):
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


class TriageSafetyScan(OrganizationScopedModel):
    """Last antimalware verdict for the exact bytes held in quarantine."""

    class Verdict(models.TextChoices):
        CLEAN = "clean", "Sem detecção"
        INFECTED = "infected", "Ameaça detectada"
        ERROR = "error", "Varredura falhou"

    class FormatVerdict(models.TextChoices):
        PENDING = "pending", "Formato pendente"
        VALID = "valid", "Formato validado"
        INVALID = "invalid", "Formato recusado"

    triage_item = models.OneToOneField(
        TriageItem, on_delete=models.CASCADE, related_name="safety_scan"
    )
    engine = models.CharField(max_length=40, blank=True)
    verdict = models.CharField(max_length=16, choices=Verdict.choices)
    content_hash = models.CharField(max_length=64)
    scanned_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=200, blank=True)
    format_verdict = models.CharField(
        max_length=16, choices=FormatVerdict.choices, default=FormatVerdict.PENDING
    )
    format_note = models.CharField(max_length=200, blank=True)

    def clean(self) -> None:
        if self.triage_item_id and self.triage_item.organization_id != self.organization_id:
            raise ValidationError({"triage_item": "A varredura pertence a outro escritório."})


class TriageEvent(OrganizationScopedModel):
    """Append-only evidence of a state change or reviewer decision."""

    triage_item = models.ForeignKey(TriageItem, on_delete=models.CASCADE, related_name="events")
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    from_status = models.CharField(max_length=24, choices=TriageStatus.choices)
    to_status = models.CharField(max_length=24, choices=TriageStatus.choices)
    note = models.CharField(max_length=500, blank=True)
    # Why a reviewer overrode the classification; kept apart so the note never truncates it.
    reason = models.CharField(max_length=500, blank=True, default="", db_default="")

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


class TriageOcrUsage(OrganizationScopedModel):
    """Pages sent to OCR, the unit of the office's monthly budget."""

    triage_item = models.ForeignKey(
        TriageItem, null=True, blank=True, on_delete=models.SET_NULL, related_name="+"
    )
    pages = models.PositiveSmallIntegerField()

    class Meta:
        indexes = [models.Index(fields=("organization", "created_at"))]

    def clean(self) -> None:
        item = self.triage_item
        if item is not None and item.organization_id != self.organization_id:
            raise ValidationError({"triage_item": "O arquivo pertence a outro escritório."})


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
