"""Transactional, internal-only operations for the first usable Triagem flow."""

from __future__ import annotations

import hashlib
import mimetypes
import re
import uuid
from pathlib import Path, PureWindowsPath
from typing import BinaryIO

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage.models import (
    AgentFileJob,
    DestinationProfile,
    DocumentType,
    TriageBlob,
    TriageEvent,
    TriageItem,
    TriageSafetyScan,
)
from apps.triage.storage import PrivateTriageStorage
from apps.triage.transitions import InvalidTransition, TriageStatus

_MAX_BYTES = 25 * 1024 * 1024
_ALLOWED_SUFFIXES = {".pdf", ".csv", ".xml", ".ofx", ".xlsx"}
_WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


def _require_verified_email_item(item: TriageItem) -> None:
    verdict = TriageSafetyScan.objects.filter(
        organization=item.organization, triage_item=item,
        verdict=TriageSafetyScan.Verdict.CLEAN,
        format_verdict=TriageSafetyScan.FormatVerdict.VALID,
        content_hash=item.content_hash,
    ).first()
    if item.mailbox_id is None or verdict is None:
        raise ValidationError(
            "Somente anexos de e-mail com antimalware e formato validados podem ser aprovados."
        )
    if item.company_id is None or item.document_type_id is None:
        raise ValidationError("Identifique a empresa e o tipo de documento antes de aprovar.")
    if item.company.organization_id != item.organization_id or (
        item.document_type.organization_id != item.organization_id
    ):
        raise ValidationError("Empresa ou tipo de documento não pertence a este escritório.")


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
        raise ValidationError("O arquivo não pôde ser registrado. Tente novamente.") from exc
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
        if decision == "archive":
            _require_verified_email_item(item)
            profile = DestinationProfile.objects.filter(organization=item.organization).first()
            if profile is None:
                raise ValidationError(
                    "Configure a biblioteca ou as pastas Windows antes de aprovar."
                )
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


def _windows_component(value: str, *, fallback: str) -> str:
    """Return one portable Windows path component without accepting separators."""
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "-", value).strip().rstrip(". ")
    cleaned = re.sub(r"\s+", " ", cleaned)[:120].rstrip(". ") or fallback
    if cleaned.split(".", 1)[0].upper() in _WINDOWS_RESERVED:
        cleaned = f"_{cleaned}"
    return cleaned


def windows_relative_destination(item: TriageItem, profile: DestinationProfile) -> str:
    """Build the office-standard relative path; the agent owns the absolute root."""
    if item.company is None or not item.company.dominio_code.strip():
        raise ValidationError("Informe o código Domínio da empresa antes de arquivar.")
    if (
        not item.final_name
        or len(item.final_name) > 255
        or any(char in item.final_name for char in "/\\\x00")
        or item.final_name in {".", ".."}
    ):
        raise ValidationError("Revise e confirme um nome final de arquivo válido.")
    company = _windows_component(item.company.name, fallback="Empresa")
    dominio = _windows_component(item.company.dominio_code, fallback="sem-codigo")
    document_type = _windows_component(item.document_type.label if item.document_type else "Documentos", fallback="Documentos")
    period = _windows_component(item.period_label or "Sem período", fallback="Sem período")
    filename = _windows_component(item.final_name, fallback="documento")
    template = profile.folder_template or "{company_name} [Domínio {dominio_code}]"
    try:
        folder = template.format(company_name=company, dominio_code=dominio, document_type=document_type, period=period)
    except (KeyError, ValueError) as exc:
        raise ValidationError("O formato de pastas Windows precisa ser configurado novamente.") from exc
    relative = PureWindowsPath(folder)
    if relative.is_absolute() or ".." in relative.parts or any(not part for part in relative.parts):
        raise ValidationError("O formato de pastas Windows gerou um destino inválido.")
    return str(relative / filename)


def queue_windows_archive(
    *, item: TriageItem, actor: User, request: object | None = None
) -> AgentFileJob:
    """Queue one verified copy and wait until the agent proves the final hash."""
    with transaction.atomic():
        item = (
            TriageItem.objects.select_for_update()
            .select_related("company", "document_type", "blob")
            .get(pk=item.pk, organization=item.organization)
        )
        if item.status == TriageStatus.ARCHIVED:
            completed = (
                item.agent_jobs.filter(status=AgentFileJob.Status.DONE)
                .order_by("-completed_at")
                .first()
            )
            if (
                item.destination_kind == DestinationProfile.Mode.WINDOWS
                and completed is not None
                and item.destination_hash == item.content_hash
            ):
                return completed
            raise ValidationError("O registro arquivado não possui confirmação íntegra do agente.")
        if item.status not in {
            TriageStatus.READY_TO_ARCHIVE,
            TriageStatus.ARCHIVE_FAILED,
            TriageStatus.ARCHIVING,
        }:
            raise InvalidTransition("Este anexo ainda não foi aprovado para arquivamento.")
        _require_verified_email_item(item)
        profile = DestinationProfile.objects.filter(organization=item.organization).first()
        if profile is None or profile.mode != DestinationProfile.Mode.WINDOWS:
            raise ValidationError("Escolha as pastas Windows para arquivar este anexo.")
        root = PureWindowsPath(profile.windows_root)
        if not profile.windows_root or not root.is_absolute() or ".." in root.parts:
            raise ValidationError("A pasta raiz Windows precisa ser configurada novamente.")
        relative_path = windows_relative_destination(item, profile)
        active = (
            item.agent_jobs.filter(
                status__in=[AgentFileJob.Status.QUEUED, AgentFileJob.Status.CLAIMED]
            )
            .order_by("-created_at")
            .first()
        )
        if active is not None:
            if active.destination_path != relative_path:
                raise ValidationError("A empresa ou o nome mudou depois do envio ao agente.")
            return active
        if item.status != TriageStatus.ARCHIVING:
            _move(
                item=item,
                target=TriageStatus.ARCHIVING,
                actor=actor,
                note="Enviado ao agente Windows",
            )
        job = AgentFileJob.objects.create(
            organization=item.organization,
            triage_item=item,
            destination_path=relative_path,
        )
    record_event(
        action="triage.item.windows_archive_queued",
        actor=actor,
        organization=item.organization,
        target=item,
        request=request,
        metadata={"job_id": str(job.id), "destination_path": relative_path},
    )
    return job


def archive_internal(*, item: TriageItem, actor: User) -> TriageItem:
    """Copy approved bytes to the private library and verify before claiming archive."""
    storage = PrivateTriageStorage()
    saved_path = ""
    try:
        with transaction.atomic():
            item = TriageItem.objects.select_for_update().select_related(
                "company", "document_type", "blob"
            ).get(pk=item.pk, organization=item.organization)
            if item.status == TriageStatus.ARCHIVED:
                if (
                    item.destination_kind != DestinationProfile.Mode.INTERNAL
                    or not item.destination_path.startswith(
                        f"private/triage/library/{item.organization_id}/{item.id}/"
                    )
                    or item.destination_hash != item.content_hash
                    or not storage.exists(item.destination_path)
                ):
                    raise ValidationError(
                        "O registro antigo não comprova uma cópia íntegra na biblioteca."
                    )
                existing_digest = hashlib.sha256()
                with storage.open(item.destination_path, "rb") as existing:
                    while chunk := existing.read(64 * 1024):
                        existing_digest.update(chunk)
                if existing_digest.hexdigest() != item.content_hash:
                    raise ValidationError("A cópia da biblioteca perdeu integridade.")
                return item
            if item.status != TriageStatus.READY_TO_ARCHIVE:
                raise InvalidTransition("Este anexo ainda não foi aprovado para arquivamento.")
            _require_verified_email_item(item)
            profile = DestinationProfile.objects.filter(organization=item.organization).first()
            if profile is None or profile.mode != DestinationProfile.Mode.INTERNAL:
                raise ValidationError("Escolha a biblioteca interna para arquivar este anexo.")
            if (
                not item.final_name
                or len(item.final_name) > 255
                or any(char in item.final_name for char in "/\\\x00")
                or item.final_name in {".", ".."}
            ):
                raise ValidationError("Revise e confirme um nome final de arquivo válido.")
            with item.blob.content.open("rb") as source:
                payload = source.read(_MAX_BYTES + 1)
            if (
                len(payload) > _MAX_BYTES
                or hashlib.sha256(payload).hexdigest() != item.content_hash
            ):
                raise ValidationError("O arquivo mudou após a verificação; mantenha em revisão.")
            path = (
                f"private/triage/library/{item.organization_id}/{item.id}/"
                f"{uuid.uuid4().hex}.bin"
            )
            saved_path = storage.save(path, ContentFile(payload))
            digest = hashlib.sha256()
            with storage.open(saved_path, "rb") as archived:
                while chunk := archived.read(64 * 1024):
                    digest.update(chunk)
            if digest.hexdigest() != item.content_hash:
                raise ValidationError(
                    "A cópia na biblioteca não passou na verificação de integridade."
                )
            _move(item=item, target=TriageStatus.ARCHIVING, actor=actor,
                  note="Copiando para biblioteca interna")
            item.destination_kind = DestinationProfile.Mode.INTERNAL
            item.destination_path = saved_path
            item.destination_hash = digest.hexdigest()
            item.archived_at = timezone.now()
            item.save(update_fields=[
                "destination_kind", "destination_path", "destination_hash", "archived_at",
                "updated_at",
            ])
            _move(item=item, target=TriageStatus.ARCHIVED, actor=actor,
                  note="Cópia interna íntegra confirmada")
    except Exception:
        if saved_path:
            storage.delete(saved_path)
        raise
    record_event(
        action="triage.item.archived_internal", actor=actor,
        organization=item.organization, target=item,
        metadata={"content_hash": item.content_hash},
    )
    return item


def open_verified_internal_copy(*, item: TriageItem) -> BinaryIO:
    """Open only a proven library copy; never fall back to the quarantine blob."""
    _require_verified_email_item(item)
    if (
        item.status != TriageStatus.ARCHIVED
        or item.destination_kind != DestinationProfile.Mode.INTERNAL
        or not item.destination_path.startswith(
            f"private/triage/library/{item.organization_id}/{item.id}/"
        )
        or item.destination_hash != item.content_hash
        or not item.final_name
    ):
        raise ValidationError("Este arquivo ainda não está disponível na biblioteca.")
    storage = PrivateTriageStorage()
    if not storage.exists(item.destination_path):
        raise ValidationError("A cópia arquivada não está disponível. Solicite suporte.")
    digest = hashlib.sha256()
    with storage.open(item.destination_path, "rb") as archived:
        while chunk := archived.read(64 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != item.content_hash:
        raise ValidationError("A cópia arquivada não passou na conferência de integridade.")
    return storage.open(item.destination_path, "rb")


def open_verified_quarantine_for_agent(*, item: TriageItem) -> BinaryIO:
    """Open the reviewed quarantine bytes only after rechecking their digest."""
    _require_verified_email_item(item)
    if item.status != TriageStatus.ARCHIVING or not item.content_hash:
        raise ValidationError("Este arquivo não está aguardando o agente Windows.")
    try:
        blob = item.blob
    except TriageBlob.DoesNotExist as exc:
        raise ValidationError("O arquivo de origem não está disponível.") from exc
    digest = hashlib.sha256()
    with blob.content.open("rb") as source:
        while chunk := source.read(64 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != item.content_hash:
        raise ValidationError("O arquivo de origem mudou depois da verificação.")
    return blob.content.open("rb")
