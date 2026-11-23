"""Manual upload: the same quarantine, scan, read and review path as an e-mail attachment.

Unlike ``services.intake_manual`` (kept for its callers: no scan, review only), an upload
here waits in quarantine for the antimalware gate and can be archived afterwards.
"""

from __future__ import annotations

import hashlib
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage import intake_policy
from apps.triage.ingest import _content_original
from apps.triage.intake_policy import policy_for, suffix_of
from apps.triage.models import DocumentType, TriageBlob, TriageEvent, TriageItem
from apps.triage.transitions import TriageStatus


def receive_upload(
    *,
    organization: Organization,
    actor: User,
    upload: UploadedFile,
    company: ClientCompany | None,
    document_type: DocumentType | None,
    request: object | None = None,
) -> TriageItem:
    if company is not None and company.organization_id != organization.id:
        raise ValidationError("A empresa não pertence a este escritório.")
    if document_type is not None and document_type.organization_id != organization.id:
        raise ValidationError("O tipo de documento não pertence a este escritório.")
    name = PurePosixPath((upload.name or "").replace("\\", "/")).name[:255]
    if not name:
        raise ValidationError("O arquivo não possui nome.")
    size = upload.size or 0
    if size <= 0:
        raise ValidationError(f"{name}: arquivo vazio.")
    if size > intake_policy.MAX_ATTACHMENT_BYTES:
        raise ValidationError(f"{name}: arquivo acima de 25 MB.")
    suffix = suffix_of(name)
    if suffix not in policy_for(organization).suffixes:
        raise ValidationError(f"{name}: formato {suffix or 'sem extensão'} não aceito.")
    digest = hashlib.sha256()
    chunks: list[bytes] = []
    total = 0
    for chunk in upload.chunks():
        total += len(chunk)
        if total > intake_policy.MAX_ATTACHMENT_BYTES:
            raise ValidationError(f"{name}: arquivo acima de 25 MB.")
        digest.update(chunk)
        chunks.append(chunk)
    payload = b"".join(chunks)
    saved_path = ""
    try:
        with transaction.atomic():
            item = TriageItem.objects.create(
                organization=organization,
                company=company,
                document_type=document_type,
                origin=TriageItem.Origin.UPLOAD,
                original_name=name,
                content_hash=digest.hexdigest(),
                byte_size=total,
                declared_type=(upload.content_type or "")[:100],
                received_at=timezone.now(),
            )
            blob = TriageBlob(organization=organization, triage_item=item)
            blob.content.save("quarantine.bin", ContentFile(payload), save=False)
            saved_path = str(blob.content.name or "")
            blob.save()
            item.transition_to(TriageStatus.QUARANTINED)
            item.save(update_fields=["status", "updated_at"])
            TriageEvent.objects.create(
                organization=organization,
                triage_item=item,
                actor=actor,
                from_status=TriageStatus.RECEIVED,
                to_status=TriageStatus.QUARANTINED,
                note="Envio manual; validação de segurança pendente",
            )
            original = _content_original(item)
            if original is not None:
                item.duplicate_of = original
                item.rejection_reason = f"Duplicado de {original.original_name}"[:500]
                item.transition_to(TriageStatus.REJECTED)
                item.save(
                    update_fields=["duplicate_of", "rejection_reason", "status", "updated_at"]
                )
                TriageEvent.objects.create(
                    organization=organization,
                    triage_item=item,
                    actor=actor,
                    from_status=TriageStatus.QUARANTINED,
                    to_status=TriageStatus.REJECTED,
                    note=item.rejection_reason,
                )
    except Exception:
        if saved_path:
            TriageBlob._meta.get_field("content").storage.delete(saved_path)
        raise
    record_event(
        action="triage.item.received_upload",
        actor=actor,
        organization=organization,
        target=item,
        request=request,
        metadata={"content_hash": item.content_hash, "byte_size": total},
    )
    if item.duplicate_of_id is None and not organization.is_demo:
        from apps.triage.tasks import process_triage_item

        item_id = str(item.pk)
        transaction.on_commit(lambda: process_triage_item.delay(item_id))
    return item
