"""Transactional, internal-only operations for the first usable Triagem flow."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage.models import DocumentType, TriageBlob, TriageEvent, TriageItem
from apps.triage.transitions import InvalidTransition, TriageStatus

_MAX_BYTES = 25 * 1024 * 1024
_ALLOWED_SUFFIXES = {".pdf", ".csv", ".xml", ".ofx", ".xlsx"}


def _validate_upload(upload: UploadedFile) -> str:
    suffix = Path(upload.name).suffix.casefold()
    if suffix not in _ALLOWED_SUFFIXES:
        raise ValidationError("Envie PDF, CSV, XML, OFX ou XLSX.")
    if upload.size <= 0:
        raise ValidationError("O arquivo está vazio.")
    if upload.size > _MAX_BYTES:
        raise ValidationError("O arquivo excede o limite de 25 MB.")
    return suffix


def intake_manual(
    *,
    organization: Organization,
    actor: User,
    company: ClientCompany,
    document_type: DocumentType | None,
    upload: UploadedFile,
    request: object | None = None,
) -> TriageItem:
    """Store a file privately and put it in a human review queue.

    This deliberately makes no claim of malware scanning or automatic extraction.
    """
    if company.organization_id != organization.id:
        raise ValidationError("A empresa não pertence a este escritório.")
    if document_type is not None and document_type.organization_id != organization.id:
        raise ValidationError("O tipo de documento não pertence a este escritório.")
    suffix = _validate_upload(upload)
    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    content_hash = digest.hexdigest()
    detected_type = mimetypes.guess_type(f"arquivo{suffix}")[0] or "application/octet-stream"
    try:
        with transaction.atomic():
            item = TriageItem.objects.create(
                organization=organization,
                company=company,
                document_type=document_type,
                original_name=Path(upload.name).name[:255],
                content_hash=content_hash,
                byte_size=upload.size,
                declared_type=upload.content_type or "",
                detected_type=detected_type,
            )
            TriageBlob.objects.create(
                organization=organization,
                triage_item=item,
                content=upload,
                content_type=detected_type,
            )
            _move(item=item, target=TriageStatus.QUARANTINED, actor=actor, note="Entrada manual")
            _move(
                item=item,
                target=TriageStatus.AWAITING_EXTRACTION,
                actor=actor,
                note="Aguardando revisão",
            )
            _move(
                item=item,
                target=TriageStatus.EXTRACTING,
                actor=actor,
                note="Preparado para revisão",
            )
            _move(
                item=item,
                target=TriageStatus.AWAITING_REVIEW,
                actor=actor,
                note="Revisão humana necessária",
            )
    except IntegrityError as exc:
        raise ValidationError("Este mesmo arquivo já foi recebido por este escritório.") from exc
    record_event(
        action="triage.item.received_manual",
        actor=actor,
        organization=organization,
        target=item,
        request=request,
        metadata={"content_hash": content_hash, "byte_size": upload.size},
    )
    return item


def _move(*, item: TriageItem, target: str, actor: User, note: str = "") -> None:
    previous = item.status
    item.transition_to(target)
    item.save(update_fields=["status", "updated_at"])
    TriageEvent.objects.create(
        organization=item.organization,
        triage_item=item,
        actor=actor,
        from_status=previous,
        to_status=target,
        note=note[:500],
    )


def decide_item(
    *, item: TriageItem, actor: User, decision: str, reason: str, request: object | None = None
) -> TriageItem:
    """Apply a reviewer decision through the state machine and append its evidence."""
    with transaction.atomic():
        item = TriageItem.objects.select_for_update().get(
            pk=item.pk, organization=item.organization
        )
        if item.status != TriageStatus.AWAITING_REVIEW:
            raise InvalidTransition("Este arquivo não está aguardando revisão.")
        item.reviewed_by = actor
        item.reviewed_at = timezone.now()
        item.rejection_reason = reason[:500] if decision == "reject" else ""
        if decision == "reject" and not item.rejection_reason.strip():
            raise ValidationError("Informe o motivo da rejeição.")
        item.save(update_fields=["reviewed_by", "reviewed_at", "rejection_reason", "updated_at"])
        if decision == "reject":
            _move(item=item, target=TriageStatus.REJECTED, actor=actor, note=item.rejection_reason)
        elif decision == "archive":
            _move(
                item=item,
                target=TriageStatus.READY_TO_ARCHIVE,
                actor=actor,
                note="Aprovado pelo revisor",
            )
            _move(item=item, target=TriageStatus.ARCHIVING, actor=actor, note="Biblioteca interna")
            item.destination_kind = "internal"
            item.destination_path = item.blob.content.name
            item.archived_at = timezone.now()
            item.save(
                update_fields=["destination_kind", "destination_path", "archived_at", "updated_at"]
            )
            _move(
                item=item,
                target=TriageStatus.ARCHIVED,
                actor=actor,
                note="Guardado na biblioteca interna",
            )
        else:
            raise ValidationError("Decisão de revisão inválida.")
    record_event(
        action=f"triage.item.{decision}",
        actor=actor,
        organization=item.organization,
        target=item,
        request=request,
        metadata={"reason": reason[:500]},
    )
    return item
