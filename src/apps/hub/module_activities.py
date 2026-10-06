"""Idempotent projections of module outcomes; never infer external ERP acceptance."""

import hashlib
import json
from datetime import date, datetime
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.fiscal_calendar.services import BusinessCalendar, internal_before
from apps.hub.models import (
    DctfWebDocument,
    FiscalGuide,
    OperationalActivity,
    OperationalActivityEvent,
    OperationalEvidence,
    ParcelamentoOperation,
    ReviewCase,
)
from apps.hub.operations import DEFAULT_INTERNAL_LEAD_BUSINESS_DAYS
from apps.triage.models import TriageItem
from apps.triage.transitions import TriageStatus


def _month_competence(value: str) -> date | None:
    """Parse only the published MM/YYYY contract; unknown source formats stay unbound."""
    try:
        month, year = value.split("/", maxsplit=1)
        parsed = date(int(year), int(month), 1)
    except (TypeError, ValueError):
        return None
    return parsed if value == f"{parsed.month:02d}/{parsed.year:04d}" else None


def _source_evidence(
    *,
    activity: OperationalActivity,
    reference: str,
    observed_at: datetime,
    summary: str,
    recorded_by_id: UUID | str | None,
) -> None:
    """Keep a compact, idempotent pointer to a persisted provider outcome."""
    OperationalEvidence.objects.get_or_create(
        organization_id=activity.organization_id,
        activity=activity,
        kind=OperationalActivity.EvidenceKind.SOURCE,
        reference=reference[:180],
        defaults={
            "observed_at": observed_at,
            "summary": summary[:500],
            "recorded_by_id": recorded_by_id,
        },
    )


def _set_module_activity(
    *,
    activity: OperationalActivity,
    status: str,
    processing: str,
    obligation: str,
    payment: str,
    freshness: str,
    blocked_reason: str,
    completed_at: datetime | None,
    completed_by_id: UUID | str | None,
    event_type: str,
    summary: str,
) -> None:
    """Update a projection only when its observable state actually changed."""
    changed = (
        activity.work_status != status
        or activity.processing_status != processing
        or activity.obligation_status != obligation
        or activity.payment_status != payment
        or activity.freshness != freshness
        or activity.blocked_reason != blocked_reason
        or activity.completed_at != completed_at
        or activity.completed_by_id != completed_by_id
    )
    if not changed:
        return
    activity.work_status = status
    activity.processing_status = processing
    activity.obligation_status = obligation
    activity.payment_status = payment
    activity.freshness = freshness
    activity.blocked_reason = blocked_reason
    activity.completed_at = completed_at
    activity.completed_by_id = completed_by_id
    activity.save(
        update_fields=[
            "work_status",
            "processing_status",
            "obligation_status",
            "payment_status",
            "freshness",
            "blocked_reason",
            "completed_at",
            "completed_by",
            "updated_at",
        ]
    )
    OperationalActivityEvent.objects.create(
        organization_id=activity.organization_id,
        activity=activity,
        event_type=event_type,
        summary=summary[:500],
        actor_id=completed_by_id,
    )


def _assign_source_requester(
    *, activity: OperationalActivity, requester_id: UUID | str | None, label: str
) -> None:
    """Keep a deliberate office assignment; only fill an unassigned source activity."""
    if activity.assigned_to_id is not None or requester_id is None:
        return
    activity.assigned_to_id = requester_id
    activity.save(update_fields=["assigned_to", "updated_at"])
    OperationalActivityEvent.objects.create(
        organization_id=activity.organization_id,
        activity=activity,
        event_type="source_assigned",
        actor_id=requester_id,
        summary=f"Responsável inicial vinculado à solicitação de {label}.",
    )


@transaction.atomic
def sync_fiscal_guide_activity(guide_id: UUID) -> OperationalActivity | None:
    """Project one guide state without treating issuance as payment or acceptance."""
    guide = (
        FiscalGuide.objects.select_for_update(of=("self",))
        .select_related("organization", "company", "issue_requested_by")
        .filter(pk=guide_id)
        .first()
    )
    if guide is None or guide.organization.is_demo:
        return None
    activity, created = OperationalActivity.objects.get_or_create(
        source_fiscal_guide=guide,
        defaults={
            "organization_id": guide.organization_id,
            "company_id": guide.company_id,
            "code": f"serpro-guide-{guide.pk}",
            "title": f"Acompanhar emissão de {guide.get_kind_display()}",
            "area": "fiscal",
            "competence": _month_competence(guide.competence),
            "legal_due_on": guide.due_on,
            # The guide's due date is the source's; the office works ahead of it (D-277).
            "internal_due_on": (
                internal_before(
                    guide.due_on, DEFAULT_INTERNAL_LEAD_BUSINESS_DAYS, BusinessCalendar()
                )
                if guide.due_on
                else None
            ),
            "assigned_to": guide.issue_requested_by,
            "evidence_requirement": "source",
            "freshness": OperationalActivity.Freshness.CURRENT,
        },
    )
    activity = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if activity.organization_id != guide.organization_id or activity.company_id != guide.company_id:
        raise ValidationError("A guia e sua atividade precisam pertencer à mesma empresa.")
    if created:
        OperationalActivityEvent.objects.create(
            organization_id=guide.organization_id,
            activity=activity,
            event_type="guide_pending",
            summary=f"Guia observada: {guide.get_status_display()}.",
            actor_id=guide.issue_requested_by_id,
        )
    _assign_source_requester(
        activity=activity, requester_id=guide.issue_requested_by_id, label="emissão de guia"
    )
    pending = OperationalActivity.WorkStatus.PENDING
    in_progress = OperationalActivity.WorkStatus.IN_PROGRESS
    blocked = OperationalActivity.WorkStatus.BLOCKED
    state = guide.status
    if state in {FiscalGuide.Status.QUEUED, FiscalGuide.Status.ISSUING}:
        _set_module_activity(
            activity=activity,
            status=in_progress,
            processing=OperationalActivity.ProcessingStatus.NOT_VERIFIED,
            obligation=OperationalActivity.ObligationStatus.NOT_APPLICABLE,
            payment=OperationalActivity.PaymentStatus.EXPECTED,
            freshness=OperationalActivity.Freshness.CURRENT,
            blocked_reason="",
            completed_at=None,
            completed_by_id=None,
            event_type="guide_observed",
            summary=f"Emissão de guia em andamento: {guide.get_status_display()}.",
        )
    elif state == FiscalGuide.Status.ISSUED:
        _source_evidence(
            activity=activity,
            reference=f"guide:{guide.pk}:{guide.issue_attempt}:issued",
            observed_at=guide.issued_at or timezone.now(),
            recorded_by_id=guide.issue_requested_by_id,
            summary=(
                "Guia disponível pela operação registrada no CICA. "
                "Não comprova pagamento, aceite ou fechamento."
            ),
        )
        _set_module_activity(
            activity=activity,
            status=pending,
            processing=OperationalActivity.ProcessingStatus.NOT_VERIFIED,
            obligation=OperationalActivity.ObligationStatus.NOT_APPLICABLE,
            payment=OperationalActivity.PaymentStatus.GUIDE_AVAILABLE,
            freshness=OperationalActivity.Freshness.CURRENT,
            blocked_reason="",
            completed_at=None,
            completed_by_id=None,
            event_type="guide_issued",
            summary="Guia disponível; conferência e pagamento permanecem separados.",
        )
    elif state in {
        FiscalGuide.Status.UNKNOWN,
        FiscalGuide.Status.FAILED,
        FiscalGuide.Status.SKIPPED,
    }:
        description = (
            "Resultado da emissão precisa ser confirmado antes de nova ação."
            if state == FiscalGuide.Status.UNKNOWN
            else "Emissão não concluída; confira o retorno e a cobrança antes de nova ação."
            if state == FiscalGuide.Status.FAILED
            else "A fonte informou dispensa; confirme motivo e evidência antes de encerrar."
        )
        _set_module_activity(
            activity=activity,
            status=blocked,
            processing=OperationalActivity.ProcessingStatus.NOT_VERIFIED,
            obligation=OperationalActivity.ObligationStatus.NOT_APPLICABLE,
            payment=OperationalActivity.PaymentStatus.EXPECTED,
            freshness=OperationalActivity.Freshness.CURRENT,
            blocked_reason=description,
            completed_at=None,
            completed_by_id=None,
            event_type="guide_blocked",
            summary=description,
        )
    else:
        _set_module_activity(
            activity=activity,
            status=pending,
            processing=OperationalActivity.ProcessingStatus.NOT_VERIFIED,
            obligation=OperationalActivity.ObligationStatus.NOT_APPLICABLE,
            payment=OperationalActivity.PaymentStatus.EXPECTED,
            freshness=OperationalActivity.Freshness.CURRENT,
            blocked_reason="",
            completed_at=None,
            completed_by_id=None,
            event_type="guide_observed",
            summary=f"Guia aguardando ação: {guide.get_status_display()}.",
        )
    return activity


@transaction.atomic
def sync_dctfweb_document_activity(document_id: UUID) -> OperationalActivity | None:
    """Project document retrieval only; a retrieved receipt is not a declared acceptance."""
    document = (
        DctfWebDocument.objects.select_for_update(of=("self",))
        .select_related("organization", "company", "requested_by")
        .filter(pk=document_id)
        .first()
    )
    if document is None or document.organization.is_demo:
        return None
    activity, created = OperationalActivity.objects.get_or_create(
        source_dctfweb_document=document,
        defaults={
            "organization_id": document.organization_id,
            "company_id": document.company_id,
            "code": f"serpro-dctfweb-{document.pk}",
            "title": f"Obter {document.get_kind_display()} DCTFWeb",
            "area": "fiscal",
            "competence": _month_competence(document.competence),
            "assigned_to": document.requested_by,
            "evidence_requirement": "source",
            "freshness": OperationalActivity.Freshness.CURRENT,
        },
    )
    activity = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if (
        activity.organization_id != document.organization_id
        or activity.company_id != document.company_id
    ):
        raise ValidationError("O documento e sua atividade precisam pertencer à mesma empresa.")
    if created:
        OperationalActivityEvent.objects.create(
            organization_id=document.organization_id,
            activity=activity,
            event_type="dctfweb_pending",
            summary=f"Consulta DCTFWeb criada: {document.get_status_display()}.",
            actor_id=document.requested_by_id,
        )
    _assign_source_requester(
        activity=activity, requester_id=document.requested_by_id, label="documento DCTFWeb"
    )
    if document.status == DctfWebDocument.Status.AVAILABLE:
        _source_evidence(
            activity=activity,
            reference=f"dctfweb:{document.pk}:{document.attempt}:available",
            observed_at=document.completed_at or timezone.now(),
            recorded_by_id=document.requested_by_id,
            summary=(
                "Documento DCTFWeb disponível pela consulta registrada. "
                "Não comprova transmissão ou aceite."
            ),
        )
        _set_module_activity(
            activity=activity,
            status=OperationalActivity.WorkStatus.COMPLETED,
            processing=OperationalActivity.ProcessingStatus.NOT_VERIFIED,
            obligation=OperationalActivity.ObligationStatus.NOT_APPLICABLE,
            payment=OperationalActivity.PaymentStatus.NOT_APPLICABLE,
            freshness=OperationalActivity.Freshness.CURRENT,
            blocked_reason="",
            completed_at=document.completed_at or timezone.now(),
            completed_by_id=document.requested_by_id,
            event_type="dctfweb_available",
            summary="Documento DCTFWeb disponível; obtenção concluída sem inferir aceite.",
        )
    elif document.status in {DctfWebDocument.Status.FAILED, DctfWebDocument.Status.UNKNOWN}:
        reason = (
            "Resultado da consulta DCTFWeb precisa ser confirmado."
            if document.status == DctfWebDocument.Status.UNKNOWN
            else "Documento DCTFWeb não obtido; confira o retorno e o consumo."
        )
        _set_module_activity(
            activity=activity,
            status=OperationalActivity.WorkStatus.BLOCKED,
            processing=OperationalActivity.ProcessingStatus.NOT_VERIFIED,
            obligation=OperationalActivity.ObligationStatus.NOT_APPLICABLE,
            payment=OperationalActivity.PaymentStatus.NOT_APPLICABLE,
            freshness=OperationalActivity.Freshness.CURRENT,
            blocked_reason=reason,
            completed_at=None,
            completed_by_id=None,
            event_type="dctfweb_blocked",
            summary=reason,
        )
    else:
        _set_module_activity(
            activity=activity,
            status=OperationalActivity.WorkStatus.IN_PROGRESS,
            processing=OperationalActivity.ProcessingStatus.NOT_VERIFIED,
            obligation=OperationalActivity.ObligationStatus.NOT_APPLICABLE,
            payment=OperationalActivity.PaymentStatus.NOT_APPLICABLE,
            freshness=OperationalActivity.Freshness.CURRENT,
            blocked_reason="",
            completed_at=None,
            completed_by_id=None,
            event_type="dctfweb_observed",
            summary=f"Consulta DCTFWeb em andamento: {document.get_status_display()}.",
        )
    return activity


@transaction.atomic
def sync_parcelamento_operation_activity(operation_id: UUID) -> OperationalActivity | None:
    """Project PARCSN work without equating a DAS file with payment."""
    operation = (
        ParcelamentoOperation.objects.select_for_update(of=("self",))
        .select_related("organization", "company", "requested_by")
        .filter(pk=operation_id)
        .first()
    )
    if operation is None or operation.organization.is_demo:
        return None
    activity, created = OperationalActivity.objects.get_or_create(
        source_parcelamento_operation=operation,
        defaults={
            "organization_id": operation.organization_id,
            "company_id": operation.company_id,
            "code": f"serpro-parcsn-{operation.pk}",
            "title": f"PARCSN: {operation.get_kind_display()}",
            "area": "fiscal",
            "assigned_to": operation.requested_by,
            "evidence_requirement": "source",
            "freshness": OperationalActivity.Freshness.CURRENT,
        },
    )
    activity = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if (
        activity.organization_id != operation.organization_id
        or activity.company_id != operation.company_id
    ):
        raise ValidationError(
            "A operação PARCSN e sua atividade precisam pertencer à mesma empresa."
        )
    if created:
        OperationalActivityEvent.objects.create(
            organization_id=operation.organization_id,
            activity=activity,
            event_type="parcsn_pending",
            summary=f"Operação PARCSN criada: {operation.get_status_display()}.",
            actor_id=operation.requested_by_id,
        )
    _assign_source_requester(
        activity=activity, requester_id=operation.requested_by_id, label="PARCSN"
    )
    terminal = operation.status in {
        ParcelamentoOperation.Status.AVAILABLE,
        ParcelamentoOperation.Status.EMPTY,
    }
    if terminal:
        _source_evidence(
            activity=activity,
            reference=f"parcsn:{operation.pk}:{operation.attempt}:{operation.status}",
            observed_at=operation.completed_at or timezone.now(),
            recorded_by_id=operation.requested_by_id,
            summary=f"Operação PARCSN concluída: {operation.get_status_display()}.",
        )
        is_das = operation.kind == ParcelamentoOperation.Kind.DAS
        _set_module_activity(
            activity=activity,
            status=(
                OperationalActivity.WorkStatus.PENDING
                if is_das
                else OperationalActivity.WorkStatus.COMPLETED
            ),
            processing=OperationalActivity.ProcessingStatus.NOT_VERIFIED,
            obligation=OperationalActivity.ObligationStatus.NOT_APPLICABLE,
            payment=(
                OperationalActivity.PaymentStatus.GUIDE_AVAILABLE
                if is_das and operation.status == ParcelamentoOperation.Status.AVAILABLE
                else OperationalActivity.PaymentStatus.NOT_APPLICABLE
            ),
            freshness=OperationalActivity.Freshness.CURRENT,
            blocked_reason="",
            completed_at=(None if is_das else operation.completed_at or timezone.now()),
            completed_by_id=(None if is_das else operation.requested_by_id),
            event_type="parcsn_available",
            summary=(
                "DAS disponível; conferência e pagamento permanecem separados."
                if is_das
                else f"Consulta PARCSN concluída: {operation.get_status_display()}."
            ),
        )
    elif operation.status in {
        ParcelamentoOperation.Status.FAILED,
        ParcelamentoOperation.Status.UNKNOWN,
    }:
        reason = (
            "Resultado da operação PARCSN precisa ser confirmado."
            if operation.status == ParcelamentoOperation.Status.UNKNOWN
            else "Operação PARCSN não concluída; confira o retorno e o consumo."
        )
        _set_module_activity(
            activity=activity,
            status=OperationalActivity.WorkStatus.BLOCKED,
            processing=OperationalActivity.ProcessingStatus.NOT_VERIFIED,
            obligation=OperationalActivity.ObligationStatus.NOT_APPLICABLE,
            payment=OperationalActivity.PaymentStatus.NOT_APPLICABLE,
            freshness=OperationalActivity.Freshness.CURRENT,
            blocked_reason=reason,
            completed_at=None,
            completed_by_id=None,
            event_type="parcsn_blocked",
            summary=reason,
        )
    else:
        _set_module_activity(
            activity=activity,
            status=OperationalActivity.WorkStatus.IN_PROGRESS,
            processing=OperationalActivity.ProcessingStatus.NOT_VERIFIED,
            obligation=OperationalActivity.ObligationStatus.NOT_APPLICABLE,
            payment=OperationalActivity.PaymentStatus.NOT_APPLICABLE,
            freshness=OperationalActivity.Freshness.CURRENT,
            blocked_reason="",
            completed_at=None,
            completed_by_id=None,
            event_type="parcsn_observed",
            summary=f"Operação PARCSN em andamento: {operation.get_status_display()}.",
        )
    return activity


def nfse_resolution_reference(review: ReviewCase) -> str:
    """Stable identity for an exact human or backup-backed resolution."""
    backup_resolution = review.resolution_source == ReviewCase.ResolutionSource.BACKUP
    if (
        not review.resolved_at
        or not review.resolved_accumulator
        or (not backup_resolution and not review.resolved_by_id)
    ):
        raise ValidationError("A revisão resolvida precisa de origem, data e acumulador.")
    resolution = json.dumps(
        {
            "review": str(review.pk),
            "actor": str(review.resolved_by_id) if review.resolved_by_id else "backup",
            "source": review.resolution_source or ReviewCase.ResolutionSource.HUMAN,
            "at": review.resolved_at.isoformat(),
            "accumulator": review.resolved_accumulator,
        },
        sort_keys=True,
    )
    fingerprint = hashlib.sha256(resolution.encode()).hexdigest()
    return f"nfse-review:{fingerprint}"


@transaction.atomic
def sync_nfse_review_activity(review_id: UUID) -> OperationalActivity | None:
    review = (
        ReviewCase.objects.select_for_update()
        .select_related(
            "document__company",
            "organization",
        )
        .get(pk=review_id)
    )
    if review.organization.is_demo:
        return None
    document = review.document
    if document.organization_id != review.organization_id or (
        document.company.organization_id != review.organization_id
    ):
        raise ValidationError("A revisão e o documento precisam pertencer ao mesmo escritório.")
    competence = None
    if document.issued_at:
        try:
            issued_on = date.fromisoformat(str(document.normalized_data.get("issued_at", ""))[:10])
        except ValueError:
            issued_on = timezone.localtime(document.issued_at).date()
        competence = issued_on.replace(day=1)
    activity, created = OperationalActivity.objects.get_or_create(
        source_nfse_review=review,
        defaults={
            "organization_id": review.organization_id,
            "company_id": document.company_id,
            "code": f"nfse-review-{review.pk}",
            "title": "Revisar classificação de NFS-e",
            "area": "fiscal",
            "competence": competence,
            "evidence_requirement": "human",
            "freshness": OperationalActivity.Freshness.CURRENT,
        },
    )
    activity = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if (
        activity.company_id != document.company_id
        or activity.organization_id != review.organization_id
    ):
        raise ValidationError("O vínculo operacional não corresponde à empresa da revisão.")
    if created:
        OperationalActivityEvent.objects.create(
            organization_id=review.organization_id,
            activity=activity,
            event_type="module_pending",
            summary=f"Revisão NFS-e {review.pk}: {review.reason}",
        )
    if review.status == ReviewCase.Status.OPEN and activity.work_status in {
        OperationalActivity.WorkStatus.COMPLETED,
        OperationalActivity.WorkStatus.WAIVED,
    }:
        activity.work_status = OperationalActivity.WorkStatus.PENDING
        activity.completed_at = None
        activity.completed_by = None
        activity.save(update_fields=["work_status", "completed_at", "completed_by", "updated_at"])
        OperationalActivityEvent.objects.create(
            organization_id=review.organization_id,
            activity=activity,
            event_type="module_reopened",
            summary="O caso NFS-e está aberto; conclusão reavaliada.",
        )
    if review.status == ReviewCase.Status.RESOLVED:
        backup_resolution = review.resolution_source == ReviewCase.ResolutionSource.BACKUP
        if (
            not review.resolved_at
            or not review.resolved_accumulator
            or (not backup_resolution and not review.resolved_by_id)
        ):
            raise ValidationError("A revisão resolvida precisa de origem, data e acumulador.")
        _, evidence_created = OperationalEvidence.objects.get_or_create(
            organization_id=review.organization_id,
            activity=activity,
            kind=(
                OperationalActivity.EvidenceKind.SOURCE
                if backup_resolution
                else OperationalActivity.EvidenceKind.HUMAN
            ),
            reference=nfse_resolution_reference(review),
            defaults={
                "recorded_by_id": review.resolved_by_id,
                "observed_at": review.resolved_at,
                "summary": (
                    "Classificação "
                    f"{'reaplicada pelo backup' if backup_resolution else 'revisada no CICA'}: "
                    f"acumulador {review.resolved_accumulator}. Não comprova importação no ERP."
                )[:500],
            },
        )
        if activity.work_status != OperationalActivity.WorkStatus.COMPLETED or evidence_created:
            activity.work_status = OperationalActivity.WorkStatus.COMPLETED
            activity.processing_status = OperationalActivity.ProcessingStatus.PROCESSED
            activity.completed_at = review.resolved_at
            activity.completed_by_id = review.resolved_by_id
            activity.blocked_reason = ""
            activity.save(
                update_fields=[
                    "work_status",
                    "processing_status",
                    "completed_at",
                    "completed_by",
                    "blocked_reason",
                    "updated_at",
                ]
            )
            OperationalActivityEvent.objects.create(
                organization_id=review.organization_id,
                activity=activity,
                event_type="module_completed",
                actor_id=review.resolved_by_id,
                summary=(
                    "Classificação reaplicada pelo backup no módulo NFS-e; "
                    "importação no ERP é separada."
                    if backup_resolution
                    else "Revisão humana concluída no módulo NFS-e; importação no ERP é separada."
                ),
            )
    return activity


@transaction.atomic
def sync_triage_activity(item_id: UUID) -> OperationalActivity | None:
    item = (
        TriageItem.objects.select_for_update(of=("self",))
        .select_related("organization", "company")
        .get(pk=item_id)
    )
    if item.organization.is_demo or item.company is None:
        return None
    if item.company.organization_id != item.organization_id:
        raise ValidationError("A empresa do arquivo pertence a outro escritório.")
    activity, created = OperationalActivity.objects.get_or_create(
        source_triage_item=item,
        defaults={
            "organization_id": item.organization_id,
            "company_id": item.company.pk,
            "code": f"triage-{item.pk}",
            "title": "Conferir e arquivar documento da Triagem",
            "area": "general",
            "competence": item.period_start.replace(day=1) if item.period_start else None,
            "evidence_requirement": "source",
            "freshness": "current",
        },
    )
    activity = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if activity.organization_id != item.organization_id or activity.company_id != item.company_id:
        raise ValidationError("A atividade não pode transferir histórico entre empresas.")
    previous = activity.work_status
    proof = bool(
        item.archived_at
        and item.destination_path
        and item.content_hash
        and item.destination_hash == item.content_hash
    )
    if item.status == TriageStatus.ARCHIVED and proof:
        assert item.archived_at is not None
        target = OperationalActivity.WorkStatus.COMPLETED
        OperationalEvidence.objects.get_or_create(
            organization_id=item.organization_id,
            activity=activity,
            kind="source",
            reference=f"triage:{item.pk}:{item.destination_hash}",
            defaults={
                "observed_at": item.archived_at,
                "summary": "Arquivamento confirmado pela Triagem com hash do conteúdo conferido.",
            },
        )
        activity.processing_status = OperationalActivity.ProcessingStatus.PROCESSED
        activity.completed_at = item.archived_at
    elif item.status in {
        TriageStatus.REJECTED,
        TriageStatus.FAILED,
        TriageStatus.ARCHIVE_FAILED,
        TriageStatus.ARCHIVED,
    }:
        target = OperationalActivity.WorkStatus.BLOCKED
        activity.completed_at = None
    else:
        target = OperationalActivity.WorkStatus.PENDING
        activity.completed_at = None
    reason = (
        f"Triagem: {item.get_status_display()}. Confira o histórico do arquivo."
        if target == "blocked"
        else ""
    )
    changed = created or previous != target or activity.blocked_reason != reason
    if changed:
        activity.work_status = target
        activity.blocked_reason = reason
        activity.completed_by = None
        activity.save(
            update_fields=[
                "work_status",
                "blocked_reason",
                "completed_at",
                "completed_by",
                "processing_status",
                "updated_at",
            ]
        )
        OperationalActivityEvent.objects.create(
            organization_id=item.organization_id,
            activity=activity,
            event_type="triage_observed",
            summary=f"Estado local da Triagem: {item.get_status_display()}.",
        )
    return activity
