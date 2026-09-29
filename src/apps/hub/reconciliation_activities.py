"""Project local treatment of a source file, never an ERP import confirmation."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import BigIntegerField, Exists, F, OuterRef, Q, Sum, Value
from django.db.models.functions import Abs, Coalesce
from django.utils import timezone

from apps.hub.models import (
    JournalEntry,
    OperationalActivity,
    OperationalActivityEvent,
    OperationalEvidence,
    ReconciliationSourceFile,
)


def reconciliation_file_pending(source: ReconciliationSourceFile) -> tuple[int, str]:
    run = source.runs.order_by("-created_at", "-pk").first()
    if run is None or run.state in {"waiting", "processing"}:
        return 1, "Aguardando processamento do arquivo."
    if run.state in {"failed", "canceled"} or run.error_count:
        return 1, "A execução exige correção ou retomada."
    movements = source.movements.all()
    if movements.exclude(
        organization_id=source.organization_id, company_id=source.company_id
    ).exists():
        raise ValidationError("Os movimentos precisam pertencer à empresa do arquivo.")
    if not movements.exists():
        return 1, "Nenhum movimento disponível para comprovar o tratamento."
    approved = JournalEntry.objects.filter(
        movement_id=OuterRef("pk"),
        organization_id=source.organization_id,
        company_id=source.company_id,
        source_movement_revision=OuterRef("revision"),
        state__in=["approved", "exported"],
        approved_at__isnull=False,
    )
    movements = movements.annotate(
        has_approved_entry=Exists(approved),
        confirmed=Coalesce(
            Sum(
                "reconciliations__amount_cents",
                filter=Q(
                    reconciliations__state="confirmed", reconciliations__confirmed_at__isnull=False
                )
                & ~Q(reconciliations__evidence={}),
            ),
            Value(0),
            output_field=BigIntegerField(),
        ),
    )
    treated = Q(has_approved_entry=True) | (
        Q(confirmed=Abs(F("amount_cents"))) & ~Q(amount_cents=0)
    )
    treated |= Q(review_state="ignored") & (
        Q(edited_by__isnull=False) | Q(applied_rule__isnull=False)
    )
    pending = movements.exclude(treated).count()
    return pending, f"{pending} movimento(s) aguardando tratamento local." if pending else ""


@transaction.atomic
def sync_reconciliation_activity(source_id: UUID) -> OperationalActivity | None:
    source = (
        ReconciliationSourceFile.objects.select_for_update()
        .select_related("organization")
        .get(pk=source_id)
    )
    if source.organization.is_demo:
        return None
    if source.company.organization_id != source.organization_id:
        raise ValidationError("A empresa precisa pertencer ao escritório do arquivo.")
    pending, reason = reconciliation_file_pending(source)
    activity, created = OperationalActivity.objects.get_or_create(
        source_reconciliation_file=source,
        defaults={
            "organization_id": source.organization_id,
            "company_id": source.company_id,
            "code": f"reconciliation-{source.pk}",
            "title": "Conferir movimentos da Conciliação",
            "area": "accounting",
            "evidence_requirement": "source",
            "freshness": "current",
        },
    )
    activity = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if (
        activity.organization_id != source.organization_id
        or activity.company_id != source.company_id
    ):
        raise ValidationError("A atividade não corresponde à empresa do arquivo.")
    run = source.runs.order_by("-created_at", "-pk").first()
    target = (
        "completed"
        if not pending
        else "blocked"
        if run and (run.state in {"failed", "canceled"} or run.error_count)
        else "pending"
    )
    blocked_reason = reason if target == "blocked" else ""
    processing = (
        "processed"
        if run
        and run.stage in {"review", "completed", "rules_reapplied"}
        and run.state not in {"waiting", "processing", "failed", "canceled"}
        and not run.error_count
        else "not_verified"
    )
    if (
        created
        or activity.work_status != target
        or activity.blocked_reason != blocked_reason
        or activity.processing_status != processing
    ):
        activity.work_status = target
        activity.blocked_reason = blocked_reason
        activity.completed_at = timezone.now() if target == "completed" else None
        activity.completed_by = None
        activity.processing_status = processing
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
        event = OperationalActivityEvent.objects.create(
            organization_id=source.organization_id,
            activity=activity,
            event_type="reconciliation_observed",
            summary=reason or "Tratamento local concluído; importação no ERP não confirmada.",
        )
        if target == "completed":
            OperationalEvidence.objects.create(
                organization_id=source.organization_id,
                activity=activity,
                kind="source",
                reference=f"reconciliation-event:{event.pk}",
                observed_at=event.occurred_at,
                summary="Movimentos tratados no CICA. Não comprova importação no ERP.",
            )
    return activity
