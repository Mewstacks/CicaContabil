"""Models that must never contain tenant identifiers or operational data."""

from __future__ import annotations

from typing import Any

from django.db import models

from apps.common.encryption import EncryptedTextField
from apps.common.knowledge_safety import validate_knowledge_source


class SharedKnowledgeSource(models.Model):
    class Kind(models.TextChoices):
        MANUAL = "manual", "Manual oficial"
        REGULATION = "regulation", "Norma/regra"
        PROCEDURE = "procedure", "Procedimento geral aprovado"
        VALIDATED_CASE = "validated_case", "Caso anonimizado validado"

    class Status(models.TextChoices):
        DRAFT = "draft", "Em curadoria"
        APPROVED = "approved", "Aprovado"
        RETIRED = "retired", "Retirado"

    kind = models.CharField(max_length=24, choices=Kind.choices)
    title = models.CharField(max_length=180)
    version = models.CharField(max_length=80)
    source_reference = models.CharField(max_length=300)
    content = EncryptedTextField()
    content_hash = models.CharField(max_length=64, unique=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.DRAFT)
    approved_by_subject_hash = models.CharField(max_length=64, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("title", "version")

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

    def __str__(self) -> str:
        return f"{self.title} · {self.version}"


class SharedKnowledgeChunk(models.Model):
    source = models.ForeignKey(
        SharedKnowledgeSource, on_delete=models.CASCADE, related_name="chunks"
    )
    ordinal = models.PositiveIntegerField()
    content = EncryptedTextField()
    content_hash = models.CharField(max_length=64, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source", "content_hash"), name="knowledge_unique_shared_chunk"
            )
        ]
        ordering = ("source", "ordinal")

    def __str__(self) -> str:
        return f"{self.source_id}:{self.ordinal}"


class GlobalLearningPromotion(models.Model):
    """An approved, scrubbed correction promoted from a tenant without a cross-DB FK."""

    class Status(models.TextChoices):
        CANDIDATE = "candidate", "Em curadoria"
        APPROVED = "approved", "Aprovado"
        PUBLISHED = "published", "Publicado"
        REJECTED = "rejected", "Rejeitado"

    origin_fingerprint = models.CharField(max_length=64, db_index=True)
    source_reference = models.CharField(max_length=300)
    sanitized_correction = EncryptedTextField()
    correction_hash = models.CharField(max_length=64, unique=True)
    evaluation_specification = models.JSONField(default=dict)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.CANDIDATE)
    reviewed_by_subject_hash = models.CharField(max_length=64, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self) -> str:
        return self.source_reference
