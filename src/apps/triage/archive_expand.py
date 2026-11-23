"""Open a released ZIP into one quarantined item per file; the package itself closes.

Runs inside ``extract_item``'s transaction, only after the antimalware scan and the format
check released the package. Each member enters quarantine like any attachment (scan, read,
classify) with the package's provenance. The package closes as *Rejeitado* with the reason
"Pacote aberto: N arquivos" (a new status would need an ``AlterField``). Nothing is written
outside the office's private storage.
"""

from __future__ import annotations

import hashlib

from django.core.files.base import ContentFile
from django.db import transaction

from apps.triage.archives import ArchiveRejected, Member, read_zip_members
from apps.triage.ingest import _content_original
from apps.triage.intake_policy import policy_for
from apps.triage.models import TriageBlob, TriageEvent, TriageItem
from apps.triage.transitions import TriageStatus


def is_archive(item: TriageItem) -> bool:
    return item.original_name.casefold().endswith(".zip")


def _close(item: TriageItem, reason: str, note: str) -> None:
    previous = item.status
    item.transition_to(TriageStatus.REJECTED)
    item.rejection_reason = reason[:500]
    item.save(update_fields=["status", "rejection_reason", "updated_at"])
    TriageEvent.objects.create(
        organization=item.organization,
        triage_item=item,
        actor=None,
        from_status=previous,
        to_status=item.status,
        note=note[:500],
    )


def _member_item(parent: TriageItem, index: int, member: Member) -> TriageItem:
    digest = hashlib.sha256(member.data).hexdigest()
    key = hashlib.sha256(f"{parent.pk}>{index}:{member.path}".encode()).hexdigest()
    body = parent.body_excerpt
    if member.folder:
        body = f"Pasta no pacote: {member.folder}\n{body}"[:6000]
    child = TriageItem.objects.create(
        organization=parent.organization,
        mailbox=parent.mailbox,
        message_id=parent.message_id,
        part_id=key if parent.mailbox_id else "",
        sender=parent.sender,
        subject=parent.subject,
        received_at=parent.received_at,
        origin=TriageItem.Origin.ARCHIVE,
        archive_parent=parent,
        body_excerpt=body,
        original_sender=parent.original_sender,
        original_name=member.name,
        content_hash=digest,
        byte_size=len(member.data),
    )
    blob = TriageBlob(organization=parent.organization, triage_item=child)
    blob.content.save("quarantine.bin", ContentFile(member.data), save=False)
    blob.save()
    child.transition_to(TriageStatus.QUARANTINED)
    child.save(update_fields=["status", "updated_at"])
    TriageEvent.objects.create(
        organization=parent.organization,
        triage_item=child,
        actor=None,
        from_status=TriageStatus.RECEIVED,
        to_status=TriageStatus.QUARANTINED,
        note=f"Aberto do pacote {parent.original_name}"[:500],
    )
    original = _content_original(child)
    if original is not None:
        child.duplicate_of = original
        child.rejection_reason = f"Duplicado de {original.original_name}"[:500]
        child.transition_to(TriageStatus.REJECTED)
        child.save(update_fields=["duplicate_of", "rejection_reason", "status", "updated_at"])
        TriageEvent.objects.create(
            organization=parent.organization,
            triage_item=child,
            actor=None,
            from_status=TriageStatus.QUARANTINED,
            to_status=TriageStatus.REJECTED,
            note=child.rejection_reason,
        )
    return child


def expand_archive_item(item: TriageItem) -> TriageItem:
    """Create the members and close the package. ``item`` is locked and EXTRACTING."""

    with item.blob.content.open("rb") as source:
        data = source.read()
    if hashlib.sha256(data).hexdigest() != item.content_hash:
        _close(item, "O arquivo mudou depois da verificação.", "Pacote recusado")
        return item
    try:
        reading = read_zip_members(data, allowed_suffixes=policy_for(item.organization).suffixes)
    except ArchiveRejected as exc:
        _close(item, str(exc), f"Pacote recusado: {exc}")
        return item
    children = [_member_item(item, index, member) for index, member in enumerate(reading.members)]
    count = len(children)
    detail = f" Ignorados: {reading.summary()}." if reading.ignored else ""
    _close(
        item,
        f"Pacote aberto: {count} arquivo{'s' if count != 1 else ''}.",
        f"Pacote aberto: {count} arquivo{'s' if count != 1 else ''}.{detail}",
    )
    if not item.organization.is_demo:
        from apps.triage.tasks import process_triage_item

        for child in children:
            if child.status == TriageStatus.QUARANTINED:
                child_id = str(child.pk)
                transaction.on_commit(lambda cid=child_id: process_triage_item.delay(cid))
    return item
