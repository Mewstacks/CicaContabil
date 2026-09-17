from __future__ import annotations

from typing import Any

from django.conf import settings
from django.db import models

from apps.common.encryption import EncryptedTextField
from apps.common.knowledge_safety import validate_knowledge_source
from apps.organizations.models import OrganizationScopedModel


class AssistantSettings(OrganizationScopedModel):
    """Per-office policy. Cloud egress is deliberately disabled by default."""

    claude_fallback_enabled = models.BooleanField(default=False)
    claude_full_data_allowed = models.BooleanField(default=False)
    claude_allowed_roles = models.JSONField(default=list)
    claude_api_key = EncryptedTextField(blank=True)
    claude_model = models.CharField(max_length=80, blank=True)
    claude_max_request_cents = models.PositiveIntegerField(default=0)
    claude_offline_curation_enabled = models.BooleanField(default=False)
    claude_curation_max_batch_requests = models.PositiveSmallIntegerField(default=0)
    retention_days = models.PositiveSmallIntegerField(default=90)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization",), name="intelligence_settings_per_organization"
            )
        ]


class ClaudeFallbackApproval(OrganizationScopedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente"
        APPROVED = "approved", "Aprovado"
        REVOKED = "revoked", "Revogado"

    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    daily_limit_cents = models.PositiveIntegerField(default=0)
    monthly_limit_cents = models.PositiveIntegerField(default=0)
    valid_until = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization",), name="intelligence_claude_approval_per_org"
            )
        ]


class DataCatalogEntry(OrganizationScopedModel):
    class Sensitivity(models.TextChoices):
        OPERATIONAL = "operational", "Operacional"
        PERSONAL = "personal", "Pessoal"
        RESTRICTED = "restricted", "Restrito"
        EXCLUDED = "excluded", "Excluído"

    module = models.CharField(max_length=64)
    business_name = models.CharField(max_length=140)
    description = models.TextField()
    sensitivity = models.CharField(max_length=20, choices=Sensitivity.choices)
    source_reference = models.CharField(max_length=240)
    enabled = models.BooleanField(default=False)

    class Meta:
        ordering = ("module", "business_name")
        indexes = [models.Index(fields=("organization", "module", "enabled"))]


class DominioSchemaObject(OrganizationScopedModel):
    """Private schema inventory used to review a semantic package before enabling it."""

    class ObjectKind(models.TextChoices):
        TABLE = "table", "Tabela"
        VIEW = "view", "Visão"

    schema_name = models.CharField(max_length=128, blank=True)
    object_name = models.CharField(max_length=128)
    object_kind = models.CharField(max_length=12, choices=ObjectKind.choices)
    columns = models.JSONField(default=list)
    structure_hash = models.CharField(max_length=64, db_index=True)
    sensitivity = models.CharField(
        max_length=20,
        choices=DataCatalogEntry.Sensitivity.choices,
        default=DataCatalogEntry.Sensitivity.RESTRICTED,
    )
    approved_for_package = models.BooleanField(default=False)
    last_discovered_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "schema_name", "object_name", "object_kind"),
                name="intelligence_unique_dominio_schema_object",
            )
        ]
        indexes = [
            models.Index(fields=("organization", "approved_for_package", "sensitivity")),
        ]


class SemanticPackage(OrganizationScopedModel):
    """A reviewed business contract, never a model-provided database query."""

    class UpdateStrategy(models.TextChoices):
        WATERMARK = "watermark", "Marca de atualização"
        SNAPSHOT_HASH = "snapshot_hash", "Snapshot com hash"

    module = models.CharField(max_length=64)
    tool_name = models.CharField(max_length=80)
    query_name = models.CharField(max_length=80, blank=True)
    source_reference = models.CharField(max_length=300)
    data_classification = models.CharField(max_length=24)
    company_key = models.CharField(max_length=120)
    primary_key = models.CharField(max_length=120)
    update_strategy = models.CharField(max_length=20, choices=UpdateStrategy.choices)
    max_rows = models.PositiveSmallIntegerField(default=100)
    max_period_days = models.PositiveSmallIntegerField(default=366)
    max_staleness_seconds = models.PositiveIntegerField(default=86_400)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    schema_dependencies = models.JSONField(default=list)
    test_specification = models.JSONField(default=dict)
    enabled = models.BooleanField(default=False)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "tool_name", "query_name"),
                name="intelligence_unique_semantic_package",
            )
        ]
        indexes = [models.Index(fields=("organization", "tool_name", "enabled"))]


class MirrorRecord(OrganizationScopedModel):
    """Encrypted operational mirror record; never a direct model-to-Domínio bridge."""

    semantic_package = models.ForeignKey(
        SemanticPackage, on_delete=models.PROTECT, related_name="records"
    )
    company = models.ForeignKey(
        "hub.ClientCompany", null=True, blank=True, on_delete=models.SET_NULL
    )
    external_key = models.CharField(max_length=160)
    payload = EncryptedTextField()
    payload_hash = models.CharField(max_length=64, db_index=True)
    source_updated_at = models.DateTimeField(null=True, blank=True)
    synchronized_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("semantic_package", "external_key"),
                name="intelligence_unique_mirror_record",
            )
        ]
        indexes = [
            models.Index(fields=("organization", "semantic_package", "company", "synchronized_at"))
        ]


class KnowledgeSource(OrganizationScopedModel):
    class Kind(models.TextChoices):
        MANUAL = "manual", "Manual Domínio"
        PROCEDURE = "procedure", "Procedimento aprovado"
        DATA_DICTIONARY = "dictionary", "Dicionário de dados"
        VALIDATED_CASE = "validated_case", "Caso histórico validado"

    class Status(models.TextChoices):
        DRAFT = "draft", "Em curadoria"
        APPROVED = "approved", "Aprovada"
        RETIRED = "retired", "Retirada"

    kind = models.CharField(max_length=20, choices=Kind.choices)
    title = models.CharField(max_length=180)
    version = models.CharField(max_length=80)
    source_reference = models.CharField(max_length=300)
    content = EncryptedTextField()
    content_hash = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    approved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "content_hash"),
                name="intelligence_unique_knowledge_content",
            )
        ]

    def clean(self) -> None:
        super().clean()
        validate_knowledge_source(
            source_reference=self.source_reference,
            version=self.version,
            content=self.content,
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class KnowledgeChunk(OrganizationScopedModel):
    """Small encrypted retrieval unit rebuilt from one approved knowledge source."""

    source = models.ForeignKey(KnowledgeSource, on_delete=models.CASCADE, related_name="chunks")
    ordinal = models.PositiveIntegerField()
    content = EncryptedTextField()
    content_hash = models.CharField(max_length=64, db_index=True)

    class Meta:
        ordering = ("source_id", "ordinal")
        constraints = [
            models.UniqueConstraint(
                fields=("source", "content_hash"), name="intelligence_unique_knowledge_chunk"
            )
        ]
        indexes = [models.Index(fields=("organization", "source", "ordinal"))]


class TrainingExample(OrganizationScopedModel):
    class Category(models.TextChoices):
        RISK = "risk", "Risco"
        CLASSIFICATION = "classification", "Classificação"
        OBLIGATION = "obligation", "Obrigação"
        SAFETY = "safety", "Segurança"

    class Status(models.TextChoices):
        DRAFT = "draft", "Em curadoria"
        VALIDATED = "validated", "Validado"
        RETIRED = "retired", "Retirado"

    category = models.CharField(max_length=20, choices=Category.choices)
    question = EncryptedTextField()
    expected_answer = EncryptedTextField()
    source_references = models.JSONField(default=list)
    scenario_hash = models.CharField(max_length=64, db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "scenario_hash"),
                name="intelligence_unique_training_scenario",
            )
        ]


class EvaluationRun(OrganizationScopedModel):
    suite_name = models.CharField(max_length=100)
    model_name = models.CharField(max_length=100)
    corpus_version = models.CharField(max_length=80)
    total_cases = models.PositiveIntegerField(default=0)
    correct_cases = models.PositiveIntegerField(default=0)
    sourced_cases = models.PositiveIntegerField(default=0)
    safety_regressions = models.PositiveIntegerField(default=0)
    passed = models.BooleanField(default=False)
    results = models.JSONField(default=dict)


class IntelligenceConnector(OrganizationScopedModel):
    class Mode(models.TextChoices):
        DIRECT_ODBC = "direct_odbc", "ODBC interno"
        EDGE_AGENT = "edge_agent", "Agente de borda"

    mode = models.CharField(max_length=20, choices=Mode.choices)
    status = models.CharField(max_length=24, default="not_configured")
    last_sync_at = models.DateTimeField(null=True, blank=True)
    sync_lag_seconds = models.PositiveIntegerField(default=0)
    sync_requested_at = models.DateTimeField(null=True, blank=True)
    sync_request_completed_at = models.DateTimeField(null=True, blank=True)
    # A DSN may contain a server path or credentials. It is only read by the local,
    # allowlisted connector and must never be stored as plain database text.
    odbc_dsn = EncryptedTextField(blank=True)
    device_fingerprint = models.CharField(max_length=64, blank=True)
    last_error_code = models.CharField(max_length=80, blank=True)
    last_error_message = models.CharField(max_length=240, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "mode"), name="intelligence_connector_per_mode"
            )
        ]


class DominioCommunication(OrganizationScopedModel):
    """Minimal encrypted mirror of a Domínio notification, excluding personal fields."""

    connector = models.ForeignKey(
        IntelligenceConnector, on_delete=models.PROTECT, related_name="communications"
    )
    company = models.ForeignKey(
        "hub.ClientCompany", null=True, blank=True, on_delete=models.SET_NULL
    )
    source_id = models.CharField(max_length=64)
    subject = EncryptedTextField(blank=True)
    type_code = models.CharField(max_length=32, blank=True)
    status_code = models.CharField(max_length=32, blank=True)
    is_read = models.BooleanField(default=False)
    source_captured_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "source_id"),
                name="intelligence_unique_dominio_communication",
            )
        ]
        indexes = [
            models.Index(fields=("organization", "company", "is_read", "source_captured_at")),
        ]


class AgentEnrollment(OrganizationScopedModel):
    """Single-use bootstrap code; only its digest is stored."""

    code_digest = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(db_index=True)
    used_at = models.DateTimeField(null=True, blank=True)
    issued_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )


class EdgeAgent(OrganizationScopedModel):
    class Status(models.TextChoices):
        ACTIVE = "active", "Ativo"
        REVOKED = "revoked", "Revogado"

    label = models.CharField(max_length=120)
    fingerprint = models.CharField(max_length=128)
    mtls_certificate_sha256 = models.CharField(max_length=64, blank=True, db_index=True)
    shared_secret = EncryptedTextField()
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=("organization", "status", "last_seen_at"))]


class Conversation(OrganizationScopedModel):
    company = models.ForeignKey(
        "hub.ClientCompany", null=True, blank=True, on_delete=models.SET_NULL
    )
    title = models.CharField(max_length=160, blank=True)
    summary = EncryptedTextField(blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-updated_at",)


class Message(OrganizationScopedModel):
    class Role(models.TextChoices):
        USER = "user", "Usuário"
        ASSISTANT = "assistant", "Assistente"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    request_id = models.UUIDField(null=True, blank=True, unique=True)
    in_reply_to = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="replies"
    )
    role = models.CharField(max_length=12, choices=Role.choices)
    content = EncryptedTextField()
    evidence = models.JSONField(default=list)
    model_version = models.CharField(max_length=80, default="grounded-rules-v1")
    context_hash = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [models.Index(fields=("organization", "conversation", "created_at"))]


class ChatAttachment(OrganizationScopedModel):
    """Encrypted, tenant-scoped input for the local multimodal runtime."""

    class Status(models.TextChoices):
        RECEIVED = "received", "Recebido"
        ANALYZED = "analyzed", "Analisado"
        AWAITING_MODEL = "awaiting_model", "Aguardando modelo local"
        ANALYZING = "analyzing", "Analisando localmente"
        FAILED = "failed", "Análise indisponível"
        REJECTED = "rejected", "Recusado"

    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="attachments"
    )
    message = models.ForeignKey(
        Message, null=True, blank=True, on_delete=models.SET_NULL, related_name="attachments"
    )
    original_name = models.CharField(max_length=180)
    content_type = models.CharField(max_length=100)
    byte_size = models.PositiveIntegerField()
    content_hash = models.CharField(max_length=64, db_index=True)
    encrypted_content_b64 = EncryptedTextField()
    analysis = EncryptedTextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.RECEIVED)
    analysis_attempts = models.PositiveSmallIntegerField(default=0)
    analysis_error = models.CharField(max_length=160, blank=True)
    analysis_requested_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=("organization", "conversation", "status"))]


class ClassificationDraft(OrganizationScopedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Pendente de revisão"
        APPROVED = "approved", "Aprovado"
        REJECTED = "rejected", "Rejeitado"

    conversation = models.ForeignKey(Conversation, on_delete=models.PROTECT, related_name="drafts")
    company = models.ForeignKey("hub.ClientCompany", on_delete=models.PROTECT)
    suggested_code = models.CharField(max_length=80)
    rationale = EncryptedTextField()
    evidence = models.JSONField(default=list)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)


class AnswerFeedback(OrganizationScopedModel):
    class Verdict(models.TextChoices):
        HELPFUL = "helpful", "Resolveu"
        NOT_HELPFUL = "not_helpful", "Não resolveu"

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="feedbacks")
    verdict = models.CharField(max_length=16, choices=Verdict.choices)
    comment = EncryptedTextField(blank=True)
    submitted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("message", "submitted_by"), name="intelligence_one_feedback_per_user"
            )
        ]


class LearningCandidate(OrganizationScopedModel):
    class Status(models.TextChoices):
        PENDING = "pending", "Aguardando revisão"
        APPROVED = "approved", "Aprovado"
        REJECTED = "rejected", "Rejeitado"
        PUBLISHED = "published", "Publicado"

    feedback = models.OneToOneField(
        AnswerFeedback, on_delete=models.PROTECT, related_name="candidate"
    )
    source_summary = EncryptedTextField()
    prior_answer = EncryptedTextField()
    candidate_answer = EncryptedTextField()
    evaluation = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.PENDING)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )


class ModelVersion(OrganizationScopedModel):
    name = models.CharField(max_length=80)
    corpus_version = models.CharField(max_length=80)
    adapter_version = models.CharField(max_length=80, blank=True)
    metrics = models.JSONField(default=dict)
    is_active = models.BooleanField(default=False)
    published_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "name"), name="intelligence_model_version_per_org"
            )
        ]


class EgressAudit(OrganizationScopedModel):
    """Metadata-only proof for a permitted external fallback, never the payload."""

    class CallState(models.TextChoices):
        DENIED = "denied", "Bloqueada"
        RESERVED = "reserved", "Reservada"
        SUCCEEDED = "succeeded", "Respondida"
        UNKNOWN = "unknown", "Resultado incerto"

    provider = models.CharField(max_length=40)
    purpose = models.CharField(max_length=80)
    payload_hash = models.CharField(max_length=64)
    user_message = models.ForeignKey(
        Message, null=True, blank=True, on_delete=models.SET_NULL, related_name="egress_attempts"
    )
    usage_event = models.ForeignKey(
        "platform.UsageEvent", null=True, blank=True, on_delete=models.SET_NULL
    )
    token_usage_event = models.ForeignKey(
        "platform.TokenUsageEvent", null=True, blank=True, on_delete=models.SET_NULL
    )
    actor = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    role = models.CharField(max_length=16)
    allowed = models.BooleanField(default=False)
    model = models.CharField(max_length=80, blank=True)
    estimated_cost_cents = models.PositiveIntegerField(default=0)
    provider_request_id = models.CharField(max_length=120, blank=True)
    provider_http_status = models.PositiveSmallIntegerField(null=True, blank=True)
    call_state = models.CharField(
        max_length=16, choices=CallState.choices, default=CallState.DENIED
    )
    input_tokens = models.PositiveIntegerField(default=0)
    output_tokens = models.PositiveIntegerField(default=0)
    cache_creation_input_tokens = models.PositiveIntegerField(default=0)
    cache_read_input_tokens = models.PositiveIntegerField(default=0)
    completed_at = models.DateTimeField(null=True, blank=True)
