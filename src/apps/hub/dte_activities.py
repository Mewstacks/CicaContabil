"""Project persisted Caixa Postal facts without contacting the provider."""

from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction

from apps.hub.models import (
    DteMessage,
    DteMessageAccess,
    OperationalActivity,
    OperationalActivityEvent,
    OperationalEvidence,
)
from apps.hub.notifications import notify_new_dte

UNCERTAIN_REASON = "Resultado da abertura DTE a confirmar; não repetir a chamada automaticamente."


@transaction.atomic
def sync_dte_activity(message_id: UUID) -> OperationalActivity | None:
    message = (
        DteMessage.objects.select_for_update()
        .select_related("organization", "company")
        .get(pk=message_id)
    )
    if message.organization.is_demo:
        return None
    if message.company.organization_id != message.organization_id:
        raise ValidationError("A comunicação precisa pertencer ao escritório da empresa.")
    activity, created = OperationalActivity.objects.get_or_create(
        source_dte_message=message,
        defaults={
            "organization_id": message.organization_id,
            "company_id": message.company_id,
            "code": f"dte-analysis-{message.pk}",
            "title": "Analisar comunicação da Caixa Postal",
            "area": "fiscal",
            "evidence_requirement": "human",
        },
    )
    activity = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if (
        activity.organization_id != message.organization_id
        or activity.company_id != message.company_id
    ):
        raise ValidationError("A atividade precisa corresponder à comunicação DTE.")
    if created:
        OperationalActivityEvent.objects.create(
            organization_id=message.organization_id,
            activity=activity,
            event_type="dte_received",
            summary="Comunicação identificada. Analise o teor e as providências; "
            "nenhuma ciência foi provocada por esta atividade.",
        )
        notify_new_dte(activity, message_id=message.pk)
    access = DteMessageAccess.objects.filter(
        message=message, organization_id=message.organization_id
    ).first()
    if access is None:
        return activity
    if access.status == "unknown" and activity.blocked_reason != UNCERTAIN_REASON:
        activity.work_status = "blocked"
        activity.blocked_reason = UNCERTAIN_REASON
        activity.completed_at = None
        activity.completed_by = None
        activity.save(
            update_fields=[
                "work_status",
                "blocked_reason",
                "completed_at",
                "completed_by",
                "updated_at",
            ]
        )
        OperationalActivityEvent.objects.create(
            organization_id=message.organization_id,
            activity=activity,
            event_type="dte_result_uncertain",
            summary=UNCERTAIN_REASON,
        )
    if access.status == "opened" and access.opened_at and access.provider_payload:
        reference = f"dte-access:{access.pk}:{access.attempt_count}"
        if not activity.evidence_items.filter(reference=reference).exists():
            OperationalEvidence.objects.create(
                organization_id=message.organization_id,
                activity=activity,
                kind="source",
                reference=reference,
                observed_at=access.opened_at,
                summary="Consulta do teor registrada. "
                "Não comprova análise nem cumprimento da demanda.",
            )
            if activity.work_status in {"completed", "waived"} and not (
                activity.evidence_items.filter(
                    organization_id=message.organization_id,
                    kind="human",
                    recorded_by__isnull=False,
                    observed_at__gte=access.opened_at,
                    created_at__gte=access.opened_at,
                ).exists()
            ):
                activity.work_status = "pending"
                activity.completed_at = None
                activity.completed_by = None
                activity.waived_reason = ""
                activity.save(
                    update_fields=[
                        "work_status",
                        "completed_at",
                        "completed_by",
                        "waived_reason",
                        "updated_at",
                    ]
                )
                OperationalActivityEvent.objects.create(
                    organization_id=message.organization_id,
                    activity=activity,
                    event_type="dte_analysis_reopened",
                    summary="Teor disponível após a confirmação anterior; refaça a análise humana.",
                )
        if activity.blocked_reason == UNCERTAIN_REASON:
            activity.work_status = "pending"
            activity.blocked_reason = ""
            activity.save(update_fields=["work_status", "blocked_reason", "updated_at"])
            OperationalActivityEvent.objects.create(
                organization_id=message.organization_id,
                activity=activity,
                event_type="dte_result_confirmed",
                summary="Teor disponível; análise humana pendente.",
            )
    return activity
