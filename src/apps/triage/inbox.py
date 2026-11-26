"""Watched intake folder: files the Windows agent found stable are quarantined here.

The agent never decides what a document is; it only proves the bytes (sha256) and the size.
Everything else follows the manual-upload path: quarantine, antimalware, extraction, review.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import PurePosixPath, PureWindowsPath

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.organizations.models import Organization
from apps.triage.intake_policy import policy_for, suffix_of
from apps.triage.models import (
    DestinationProfile,
    TriageBlob,
    TriageEvent,
    TriageItem,
    TriagePolicy,
)
from apps.triage.transitions import TriageStatus

# One signed request carries the whole file and Django buffers it (DATA_UPLOAD_MAX_MEMORY_SIZE).
INBOX_MAX_BYTES = 8 * 1024 * 1024
MIN_STABLE_SECONDS = 5
MAX_STABLE_SECONDS = 3600


@dataclass(frozen=True)
class InboxResult:
    item: TriageItem
    duplicate: bool


_SYSTEM_DIRS = ("windows", "program files", "program files (x86)", "programdata", "users")


def inbox_path_error(organization: Organization, path: str) -> str | None:
    """Why ``path`` cannot be a watched folder; it must sit strictly under the office's root."""

    profile = DestinationProfile.objects.filter(organization=organization).first()
    if profile is None or profile.mode != DestinationProfile.Mode.WINDOWS:
        return "Ative as pastas Windows antes."
    root = PureWindowsPath(profile.windows_root.strip())
    candidate = PureWindowsPath(path.strip())
    if not root.is_absolute() or not candidate.is_absolute() or ".." in candidate.parts:
        return "Use um caminho absoluto sem “..”."
    root_parts = [part.casefold() for part in root.parts]
    parts = [part.casefold() for part in candidate.parts]
    if len(parts) <= len(root_parts) or parts[: len(root_parts)] != root_parts:
        return "A pasta precisa ficar dentro da pasta raiz do escritório."
    if any(part in _SYSTEM_DIRS for part in parts[1:2]):
        return "Pasta de sistema não é permitida."
    return None


def inbox_config(organization: Organization) -> dict[str, object]:
    """What the agent may watch; disabled unless the office switched it on and set a path."""

    policy = TriagePolicy.objects.filter(organization=organization).first()
    if (
        policy is None
        or not policy.inbox_watch_enabled
        or not policy.inbox_watch_path.strip()
        or inbox_path_error(organization, policy.inbox_watch_path) is not None
    ):
        return {"enabled": False, "path": "", "stable_seconds": 30, "max_bytes": INBOX_MAX_BYTES}
    return {
        "enabled": True,
        "path": policy.inbox_watch_path.strip(),
        "stable_seconds": min(
            max(policy.inbox_stable_seconds, MIN_STABLE_SECONDS), MAX_STABLE_SECONDS
        ),
        "max_bytes": INBOX_MAX_BYTES,
    }


def receive_inbox_file(
    *, organization: Organization, filename: str, payload: bytes, claimed_sha256: str
) -> InboxResult:
    """Quarantine one file; the same bytes sent twice return the first item untouched."""

    if not inbox_config(organization)["enabled"]:
        raise ValidationError("A pasta de entrada está desligada.")
    name = PurePosixPath(filename.replace("\\", "/")).name[:255]
    if not name:
        raise ValidationError("O arquivo não possui nome.")
    size = len(payload)
    if size <= 0:
        raise ValidationError(f"{name}: arquivo vazio.")
    if size > INBOX_MAX_BYTES:
        raise ValidationError(f"{name}: arquivo acima de 8 MB.")
    suffix = suffix_of(name)
    if suffix not in policy_for(organization).suffixes:
        raise ValidationError(f"{name}: formato {suffix or 'sem extensão'} não aceito.")
    digest = hashlib.sha256(payload).hexdigest()
    if digest != claimed_sha256.lower():
        raise ValidationError(f"{name}: o hash enviado não confere com o conteúdo.")
    existing = (
        TriageItem.objects.filter(
            organization=organization,
            content_hash=digest,
            origin=TriageItem.Origin.UPLOAD,
            original_name=name,
        )
        .order_by("created_at", "pk")
        .first()
    )
    if existing is not None:
        return InboxResult(item=existing, duplicate=True)
    saved_path = ""
    try:
        with transaction.atomic():
            item = TriageItem.objects.create(
                organization=organization,
                origin=TriageItem.Origin.UPLOAD,
                original_name=name,
                content_hash=digest,
                byte_size=size,
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
                actor=None,
                from_status=TriageStatus.RECEIVED,
                to_status=TriageStatus.QUARANTINED,
                note="Pasta de entrada; validação de segurança pendente",
            )
    except Exception:
        if saved_path:
            TriageBlob._meta.get_field("content").storage.delete(saved_path)
        raise
    record_event(
        action="triage.item.received_inbox",
        actor=None,
        organization=organization,
        target=item,
        metadata={"content_hash": digest, "byte_size": size},
    )
    if not organization.is_demo:
        from apps.triage.tasks import process_triage_item

        item_id = str(item.pk)
        transaction.on_commit(lambda: process_triage_item.delay(item_id))
    return InboxResult(item=item, duplicate=False)
