"""Provider-independent receipt of one email attachment into private quarantine.

This service does not classify, scan, expose or archive a received binary. Pollers may
only call it for an office-authorized mailbox. A separate scanner must move the item
out of quarantine before the human-review and download routes can use it.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from pathlib import PurePosixPath

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.triage.models import Mailbox, TriageBlob, TriageEvent, TriageItem
from apps.triage.transitions import TriageStatus

MAX_EMAIL_ATTACHMENT_BYTES = 25 * 1024 * 1024


@dataclass(frozen=True)
class AttachmentReceipt:
    item: TriageItem
    created: bool
    duplicate_kind: str = ""


def mailbox_accepts_message(*, mailbox: Mailbox, sender: str, subject: str) -> bool:
    """Apply optional office filters before an attachment is downloaded."""

    sender_filter = mailbox.sender_filter.strip().casefold()
    subject_filter = mailbox.subject_filter.strip().casefold()
    return (not sender_filter or sender_filter in sender.casefold()) and (
        not subject_filter or subject_filter in subject.casefold()
    )


def receive_email_attachment(
    *,
    mailbox: Mailbox,
    message_id: str,
    part_id: str,
    filename: str,
    payload: bytes,
    sender: str = "",
    subject: str = "",
    received_at: datetime | None = None,
    declared_type: str = "",
) -> AttachmentReceipt:
    """Persist one bounded binary, with delivery and content deduplication.

    Nothing here guesses a company or accepts a MIME declaration as a safe file type.
    The binary stays in ``em_quarentena`` and has no public URL.
    """
    if not mailbox.active or mailbox.status != Mailbox.Status.ACTIVE:
        raise ValidationError("Ative e autorize esta caixa antes de receber anexos.")
    if not message_id or len(message_id) > 255 or not part_id or len(part_id) > 64:
        raise ValidationError("O provedor não identificou a mensagem e o anexo.")
    if not payload:
        raise ValidationError("O anexo recebido está vazio.")
    if len(payload) > MAX_EMAIL_ATTACHMENT_BYTES:
        raise ValidationError("O anexo excede o limite de 25 MB e não foi armazenado.")
    if received_at is not None and timezone.is_naive(received_at):
        raise ValidationError("A data de recebimento precisa incluir o fuso horário.")

    safe_name = PurePosixPath(filename.replace("\\", "/")).name[:255] or "anexo-sem-nome.bin"
    digest = hashlib.sha256(payload).hexdigest()
    organization = mailbox.organization
    existing_delivery = TriageItem.objects.filter(
        mailbox=mailbox, message_id=message_id, part_id=part_id
    ).first()
    if existing_delivery:
        return AttachmentReceipt(existing_delivery, False, "delivery")
    saved_path = ""
    try:
        with transaction.atomic():
            item = TriageItem.objects.create(
                organization=organization,
                mailbox=mailbox,
                message_id=message_id,
                part_id=part_id,
                sender=sender[:255],
                subject=subject[:500],
                received_at=received_at,
                original_name=safe_name,
                content_hash=digest,
                byte_size=len(payload),
                declared_type=declared_type[:100],
            )
            blob = TriageBlob(
                organization=organization,
                triage_item=item,
            )
            blob.content.save("quarantine.bin", ContentFile(payload), save=False)
            saved_path = str(blob.content.name or "")
            blob.save()
            item.transition_to(TriageStatus.QUARANTINED)
            item.save(update_fields=["status", "updated_at"])
            TriageEvent.objects.create(
                organization=organization,
                triage_item=item,
                actor=None,
                from_status=TriageStatus.RECEIVED,
                to_status=TriageStatus.QUARANTINED,
                note="Anexo recebido da caixa; validação de segurança pendente",
            )
    except IntegrityError:
        if saved_path:
            TriageBlob._meta.get_field("content").storage.delete(saved_path)
        same_delivery = TriageItem.objects.filter(
            mailbox=mailbox, message_id=message_id, part_id=part_id
        ).first()
        if same_delivery:
            return AttachmentReceipt(same_delivery, False, "delivery")
        raise
    except Exception:
        if saved_path:
            TriageBlob._meta.get_field("content").storage.delete(saved_path)
        raise
    record_event(
        action="triage.item.received_email",
        actor=None,
        organization=organization,
        target=item,
        metadata={"mailbox_id": str(mailbox.id), "byte_size": len(payload)},
    )
    return AttachmentReceipt(item, True)
