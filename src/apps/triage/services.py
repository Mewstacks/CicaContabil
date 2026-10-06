"""Transactional, internal-only operations for the first usable Triagem flow."""

from __future__ import annotations

import hashlib
import mimetypes
import re
import uuid
from pathlib import Path, PureWindowsPath
from typing import BinaryIO, cast

from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany
from apps.hub.module_activities import sync_triage_activity
from apps.organizations.models import Organization
from apps.triage.models import (
    AgentFileJob,
    ChecklistEntry,
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
    company = item.company
    document_type = item.document_type
    if company is None or document_type is None:
        raise ValidationError("Identifique a empresa e o tipo de documento antes de aprovar.")
    if company.organization_id != item.organization_id or (
        document_type.organization_id != item.organization_id
    ):
        raise ValidationError("Empresa ou tipo de documento não pertence a este escritório.")


def _validate_upload(upload: UploadedFile) -> tuple[str, int, str]:
    name = upload.name
    if not name:
        raise ValidationError("O arquivo não possui nome.")
    suffix = Path(name).suffix.casefold()
    size = upload.size
    if suffix not in _ALLOWED_SUFFIXES:
        raise ValidationError("Envie PDF, CSV, XML, OFX ou XLSX.")
    if size is None or size <= 0:
        raise ValidationError("O arquivo está vazio.")
    if size > _MAX_BYTES:
        raise ValidationError("O arquivo excede o limite de 25 MB.")
    return suffix, size, name


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
    suffix, upload_size, upload_name = _validate_upload(upload)
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
                original_name=Path(upload_name).name[:255],
                content_hash=content_hash,
                byte_size=upload_size,
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
    sync_triage_activity(item.pk)


def retry_failed_extraction(
    *, item: TriageItem, actor: User | None = None, note: str = "Nova tentativa automática"
) -> TriageItem:
    """Put a failed extraction back in line. Idempotent: other states are returned as-is."""
    with transaction.atomic():
        item = TriageItem.objects.select_for_update(of=("self",)).get(
            pk=item.pk, organization=item.organization
        )
        if item.status != TriageStatus.FAILED:
            return item
        item.transition_to(TriageStatus.AWAITING_EXTRACTION)
        item.save(update_fields=["status", "updated_at"])
        TriageEvent.objects.create(
            organization=item.organization,
            triage_item=item,
            actor=actor,
            from_status=TriageStatus.FAILED,
            to_status=item.status,
            note=note[:500],
        )
    sync_triage_activity(item.pk)
    return item


def can_reprocess(item: TriageItem) -> bool:
    """Failed extraction, or a quarantine whose antimalware run errored."""
    if item.status == TriageStatus.FAILED:
        return True
    scan = getattr(item, "safety_scan", None)
    return (
        item.status == TriageStatus.QUARANTINED
        and scan is not None
        and scan.verdict == TriageSafetyScan.Verdict.ERROR
    )


def reprocess_item(*, item: TriageItem, actor: User, request: object | None = None) -> TriageItem:
    """A person restarts the automatic pipeline with a fresh attempt budget.

    The antimalware gate is never skipped: a quarantined item is scanned again, and a
    failed one only returns to extraction, which itself rechecks the clean verdict.
    """
    if item.organization.is_demo:
        raise ValidationError("Reprocessamento indisponível na demonstração.")
    with transaction.atomic():
        item = (
            TriageItem.objects.select_for_update(of=("self",))
            .select_related("safety_scan")
            .get(pk=item.pk, organization=item.organization)
        )
        if not can_reprocess(item):
            raise InvalidTransition("Este arquivo não pode ser reprocessado.")
        previous = item.status
        item.pipeline_attempts = 0
        if previous == TriageStatus.FAILED:
            item.transition_to(TriageStatus.AWAITING_EXTRACTION)
        item.save(update_fields=["status", "pipeline_attempts", "updated_at"])
        TriageEvent.objects.create(
            organization=item.organization,
            triage_item=item,
            actor=actor,
            from_status=previous,
            to_status=item.status,
            note="Reprocessamento solicitado",
        )
        from apps.triage.tasks import process_triage_item

        item_id = str(item.pk)
        transaction.on_commit(lambda: process_triage_item.delay(item_id))
    sync_triage_activity(item.pk)
    record_event(
        action="triage.item.reprocessed",
        actor=actor,
        organization=item.organization,
        target=item,
        request=request,
        metadata={"from_status": str(previous)},
    )
    return item


def record_checklist_delivery(item: TriageItem) -> ChecklistEntry | None:
    """Mark the expected document for this company/type/period as delivered.

    The first archived proof wins; a later duplicate never replaces it.
    """
    if (
        item.status != TriageStatus.ARCHIVED
        or item.company_id is None
        or item.document_type_id is None
        or not item.period_label
    ):
        return None
    entry, _created = ChecklistEntry.objects.get_or_create(
        organization=item.organization,
        company_id=item.company_id,
        document_type_id=item.document_type_id,
        period_label=item.period_label,
    )
    if entry.triage_item_id is None:
        entry.triage_item = item
        entry.received_at = item.received_at or item.archived_at or timezone.now()
        entry.save(update_fields=["triage_item", "received_at", "updated_at"])
    return entry


def _follow_company_correction(
    *, item: TriageItem, company: ClientCompany, actor: User, reason: str
) -> None:
    """Re-point the item's pending review task when the reviewer fixes the company.

    Extraction opens the task under the company it guessed. Without this, a correction
    would leave the task on the wrong company and ``sync_triage_activity`` would refuse
    every later step. Only an evidence-free, unfinished task moves, and the move is
    recorded on the task itself; anything with evidence stays put and blocks the change.
    """
    from apps.hub.models import OperationalActivity, OperationalActivityEvent

    activity = (
        OperationalActivity.objects.select_for_update()
        .select_related("company")
        .filter(source_triage_item=item)
        .first()
    )
    if activity is None or activity.company_id == company.pk:
        return
    if (
        activity.work_status == OperationalActivity.WorkStatus.COMPLETED
        or activity.evidence_items.exists()
    ):
        raise ValidationError("A atividade deste arquivo já tem evidência na empresa anterior.")
    previous = activity.company.name
    activity.company = company
    activity.save(update_fields=["company", "updated_at"])
    summary = f"Empresa corrigida na Triagem: {previous} → {company.name}"
    if reason:
        summary += f". Motivo: {reason}"
    OperationalActivityEvent.objects.create(
        organization_id=item.organization_id,
        activity=activity,
        event_type="triage_company_corrected",
        actor=actor,
        summary=summary[:500],
    )


def update_review_fields(
    *,
    item: TriageItem,
    actor: User,
    company: ClientCompany | None,
    document_type: DocumentType | None,
    period_label: str,
    counterparty_token: str,
    final_name: str,
    reason: str = "",
    request: object | None = None,
) -> TriageItem:
    """Let the reviewer correct what extraction suggested, with an evidence trail.

    Replacing a company or type that was already set (by extraction or a person) needs a
    reason; filling an empty one does not, since nothing is being overruled.
    """
    reason = " ".join(reason.split())
    if len(reason) > 500:
        raise ValidationError("O motivo aceita até 500 caracteres.")
    period_label = period_label.strip()
    counterparty_token = counterparty_token.strip()[:64]
    final_name = final_name.strip()
    if period_label and not re.fullmatch(r"20\d{2}(-(0[1-9]|1[0-2]))?", period_label):
        raise ValidationError("Use o período no formato AAAA-MM ou AAAA.")
    if final_name and (
        len(final_name) > 255
        or any(char in final_name for char in '/\\<>:"|?*\x00')
        or final_name.strip(".") == ""
    ):
        raise ValidationError("O nome final não pode conter / \\ < > : \" | ? *.")
    with transaction.atomic():
        item = TriageItem.objects.select_for_update().get(
            pk=item.pk, organization=item.organization
        )
        if item.status != TriageStatus.AWAITING_REVIEW:
            raise InvalidTransition("Este arquivo não está aguardando revisão.")
        if company is not None and company.organization_id != item.organization_id:
            raise ValidationError("A empresa não pertence a este escritório.")
        if document_type is not None and document_type.organization_id != item.organization_id:
            raise ValidationError("O tipo de documento não pertence a este escritório.")
        before = {
            "empresa": item.company.name if item.company else "",
            "tipo": item.document_type.label if item.document_type else "",
            "período": item.period_label,
            "contraparte": item.counterparty_token,
            "nome": item.final_name,
        }
        item.company = company
        item.document_type = document_type
        item.period_label = period_label
        item.counterparty_token = counterparty_token
        item.final_name = final_name
        after = {
            "empresa": company.name if company else "",
            "tipo": document_type.label if document_type else "",
            "período": period_label,
            "contraparte": counterparty_token,
            "nome": final_name,
        }
        changed = [key for key in before if before[key] != after[key]]
        if not changed:
            return item
        overruled = [key for key in ("empresa", "tipo") if key in changed and before[key]]
        if overruled and not reason:
            raise ValidationError("Informe o motivo da correção de empresa ou tipo.")
        item.save(
            update_fields=[
                "company", "document_type", "period_label", "counterparty_token",
                "final_name", "updated_at",
            ]
        )
        if "empresa" in changed and company is not None:
            # Same transaction: a refused move rolls the field change back too.
            _follow_company_correction(item=item, company=company, actor=actor, reason=reason)
        TriageEvent.objects.create(
            organization=item.organization,
            triage_item=item,
            actor=actor,
            from_status=item.status,
            to_status=item.status,
            note=("Corrigido: " + ", ".join(changed))[:500],
            reason=reason,
        )
    sync_triage_activity(item.pk)
    record_event(
        action="triage.item.review_fields_updated",
        actor=actor,
        organization=item.organization,
        target=item,
        request=request,
        metadata={"changed": changed, "reason": reason},
    )
    return item


def open_reviewable_blob(*, item: TriageItem) -> bytes:
    """Return released quarantine bytes for in-browser review, never unscanned ones."""
    released = TriageSafetyScan.objects.filter(
        organization=item.organization,
        triage_item=item,
        verdict=TriageSafetyScan.Verdict.CLEAN,
        format_verdict=TriageSafetyScan.FormatVerdict.VALID,
        content_hash=item.content_hash,
    ).exists()
    if not released or item.status in {TriageStatus.QUARANTINED, TriageStatus.RECEIVED}:
        raise ValidationError("O arquivo ainda não foi liberado pela verificação.")
    try:
        blob = item.blob
    except TriageBlob.DoesNotExist as exc:
        raise ValidationError("O arquivo de origem não está disponível.") from exc
    with blob.content.open("rb") as source:
        payload: bytes = source.read(_MAX_BYTES + 1)
    if len(payload) > _MAX_BYTES or hashlib.sha256(payload).hexdigest() != item.content_hash:
        raise ValidationError("O arquivo mudou depois da verificação.")
    return payload


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
    document_type = _windows_component(
        item.document_type.label if item.document_type else "Documentos",
        fallback="Documentos",
    )
    period = _windows_component(item.period_label or "Sem período", fallback="Sem período")
    filename = _windows_component(item.final_name, fallback="documento")
    template = profile.folder_template or "{company_name} [Domínio {dominio_code}]"
    try:
        folder = template.format(
            company_name=company,
            dominio_code=dominio,
            document_type=document_type,
            period=period,
        )
    except (KeyError, ValueError) as exc:
        raise ValidationError(
            "O formato de pastas Windows precisa ser configurado novamente."
        ) from exc
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
            TriageItem.objects.select_for_update(of=("self",))
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
            item = TriageItem.objects.select_for_update(of=("self",)).select_related(
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
            record_checklist_delivery(item)
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
    destination_path = item.destination_path
    if (
        item.status != TriageStatus.ARCHIVED
        or item.destination_kind != DestinationProfile.Mode.INTERNAL
        or not destination_path
        or not destination_path.startswith(
            f"private/triage/library/{item.organization_id}/{item.id}/"
        )
        or item.destination_hash != item.content_hash
        or not item.final_name
    ):
        raise ValidationError("Este arquivo ainda não está disponível na biblioteca.")
    storage = PrivateTriageStorage()
    if not storage.exists(destination_path):
        raise ValidationError("A cópia arquivada não está disponível. Solicite suporte.")
    digest = hashlib.sha256()
    with storage.open(destination_path, "rb") as archived:
        while chunk := archived.read(64 * 1024):
            digest.update(chunk)
    if digest.hexdigest() != item.content_hash:
        raise ValidationError("A cópia arquivada não passou na conferência de integridade.")
    return cast(BinaryIO, storage.open(destination_path, "rb"))


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
    return cast(BinaryIO, blob.content.open("rb"))
