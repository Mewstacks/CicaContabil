"""Queue human review of received payroll totals; never assert an official closing."""

from datetime import date
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.hub.models import (
    ClientCompany,
    OperationalActivity,
    OperationalActivityEvent,
    PayrollPeriodSnapshot,
)


@transaction.atomic
def sync_payroll_activity(*, company_id: UUID, competence: date) -> OperationalActivity | None:
    company = (
        ClientCompany.objects.select_for_update().select_related("organization").get(pk=company_id)
    )
    if company.organization.is_demo:
        return None
    latest = (
        PayrollPeriodSnapshot.objects.filter(
            organization_id=company.organization_id,
            company=company,
            competence=competence,
        )
        .order_by("-created_at", "-pk")
        .first()
    )
    if latest is None:
        return None
    activity, created = OperationalActivity.objects.get_or_create(
        organization_id=company.organization_id,
        company=company,
        competence=competence,
        code="payroll-review",
        defaults={
            "title": "Conferir totais e documentos da folha",
            "area": "payroll",
            "evidence_requirement": "human",
            "source_payroll_snapshot": latest,
        },
    )
    activity = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if not created and not activity.source_payroll_snapshot_id:
        raise ValidationError("O código da conferência já pertence a outra atividade.")
    if not created and activity.source_payroll_snapshot_id == latest.pk:
        return activity
    activity.source_payroll_snapshot = latest
    if activity.work_status in {"completed", "waived"}:
        activity.work_status = "pending"
        activity.completed_at = None
        activity.completed_by = None
        activity.waived_reason = ""
    activity.save(
        update_fields=[
            "source_payroll_snapshot",
            "work_status",
            "completed_at",
            "completed_by",
            "waived_reason",
            "updated_at",
        ]
    )
    OperationalActivityEvent.objects.create(
        organization_id=company.organization_id,
        activity=activity,
        event_type="payroll_received",
        summary=f"Fotografia {latest.pk} recebida. Confira os dados na ficha da empresa. "
        "Não comprova fechamento ou aceite oficial.",
    )
    return activity
