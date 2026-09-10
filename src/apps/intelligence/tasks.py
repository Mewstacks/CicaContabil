from __future__ import annotations

import base64
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.intelligence.models import ChatAttachment
from apps.intelligence.retention import purge_expired_conversations
from apps.intelligence.retrieval import refresh_knowledge_chunks, refresh_shared_knowledge_chunks
from apps.intelligence.services import _analyze_with_private_model
from apps.organizations.models import Organization


@shared_task(name="intelligence.refresh_knowledge_chunks")  # type: ignore[untyped-decorator]
def refresh_knowledge_chunks_task() -> dict[str, int]:
    """Daily RAG refresh; returns counts only and never logs source content."""
    created = removed = unchanged = 0
    for organization in Organization.objects.filter(is_active=True).iterator():
        result = refresh_knowledge_chunks(organization=organization)
        created += result.created
        removed += result.removed
        unchanged += result.unchanged
    return {"created": created, "removed": removed, "unchanged": unchanged}


@shared_task(name="intelligence.refresh_shared_knowledge_chunks")  # type: ignore[untyped-decorator]
def refresh_shared_knowledge_chunks_task() -> dict[str, int]:
    """Refresh global rules only; tenant databases are never read here."""
    result = refresh_shared_knowledge_chunks()
    return {"created": result.created, "removed": result.removed, "unchanged": result.unchanged}


@shared_task(name="intelligence.purge_expired_conversations")  # type: ignore[untyped-decorator]
def purge_expired_conversations_task() -> dict[str, int]:
    """Apply the retention policy without emitting conversation content."""
    eligible = deleted = 0
    for organization in Organization.objects.filter(is_active=True).iterator():
        result = purge_expired_conversations(organization=organization, apply=True)
        eligible += result.eligible
        deleted += result.deleted
    return {"eligible": eligible, "deleted": deleted}


@shared_task(name="intelligence.analyze_attachment")  # type: ignore[untyped-decorator]
def analyze_attachment_task(attachment_id: str) -> dict[str, object]:
    """Retry an existing local-only attachment analysis without logging content."""
    retry_limit = max(1, int(getattr(settings, "INTELLIGENCE_ATTACHMENT_RETRY_LIMIT", 6)))
    with transaction.atomic():
        attachment = (
            ChatAttachment.objects.select_for_update()
            .filter(id=attachment_id, status=ChatAttachment.Status.AWAITING_MODEL)
            .first()
        )
        if attachment is None:
            return {"status": "ignored"}
        attachment.analysis_attempts += 1
        attachment.status = ChatAttachment.Status.ANALYZING
        attachment.analysis_requested_at = timezone.now()
        attachment.save(
            update_fields=["status", "analysis_attempts", "analysis_requested_at", "updated_at"]
        )
        try:
            content = base64.b64decode(attachment.encrypted_content_b64, validate=True)
        except (ValueError, TypeError):
            content = b""
        content_type = attachment.content_type
        name = attachment.original_name
        attempts = attachment.analysis_attempts
    if not content:
        analysis = None
        invalid_attachment = True
    else:
        analysis = _analyze_with_private_model(
            content=content,
            content_type=content_type,
            name=name,
        )
        invalid_attachment = False
    with transaction.atomic():
        attachment = (
            ChatAttachment.objects.select_for_update()
            .filter(id=attachment_id, status=ChatAttachment.Status.ANALYZING)
            .first()
        )
        if attachment is None:
            return {"status": "ignored"}
        if invalid_attachment:
            attachment.status = ChatAttachment.Status.FAILED
            attachment.analysis_error = "anexo_invalido"
            attachment.save(update_fields=["status", "analysis_error", "updated_at"])
            return {"status": "failed", "reason": "attachment_invalid"}
        if analysis:
            attachment.analysis = analysis
            attachment.status = ChatAttachment.Status.ANALYZED
            attachment.analysis_error = ""
            attachment.analysis_requested_at = timezone.now()
            attachment.save(
                update_fields=[
                    "analysis",
                    "status",
                    "analysis_error",
                    "analysis_attempts",
                    "analysis_requested_at",
                    "updated_at",
                ]
            )
            return {"status": "analyzed", "attachment_id": str(attachment.id)}
        if attempts >= retry_limit:
            attachment.status = ChatAttachment.Status.FAILED
            attachment.analysis_error = "modelo_local_indisponivel"
        else:
            attachment.status = ChatAttachment.Status.AWAITING_MODEL
            attachment.analysis_error = "aguardando_modelo_local"
        attachment.save(
            update_fields=["status", "analysis_error", "analysis_attempts", "updated_at"]
        )
        return {"status": attachment.status, "attachment_id": str(attachment.id)}


@shared_task(name="intelligence.retry_pending_attachments")  # type: ignore[untyped-decorator]
def retry_pending_attachments_task() -> dict[str, int]:
    """Schedule a bounded batch; only identifiers pass through Celery."""
    if not str(getattr(settings, "LOCAL_MULTIMODAL_ENDPOINT", "")).strip():
        return {"scheduled": 0}
    limit = max(1, int(getattr(settings, "INTELLIGENCE_ATTACHMENT_RETRY_LIMIT", 6)))
    stale_before = timezone.now() - timedelta(minutes=10)
    ChatAttachment.objects.filter(
        status=ChatAttachment.Status.ANALYZING,
        analysis_requested_at__lt=stale_before,
    ).update(status=ChatAttachment.Status.AWAITING_MODEL, analysis_error="modelo_local_timeout")
    identifiers = list(
        ChatAttachment.objects.filter(
            status=ChatAttachment.Status.AWAITING_MODEL,
            analysis_attempts__lt=limit,
        )
        .order_by("updated_at")
        .values_list("id", flat=True)[:25]
    )
    for attachment_id in identifiers:
        analyze_attachment_task.delay(str(attachment_id))
    return {"scheduled": len(identifiers)}
