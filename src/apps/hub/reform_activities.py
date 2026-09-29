"""Human-selected reviews of public updates; no inferred company applicability."""

import hashlib
import json
from uuid import UUID

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction

from apps.accounts.models import User
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    OperationalActivity,
    OperationalActivityEvent,
    OperationalEvidence,
    ProductModule,
    ReformAlert,
)
from apps.hub.operations import can_operate_activity
from apps.organizations.models import Membership


def reform_version(alert: ReformAlert) -> str:
    payload = [
        alert.title,
        alert.source_url,
        alert.summary,
        alert.relevance,
        alert.published_at.isoformat() if alert.published_at else None,
    ]
    return hashlib.sha256(json.dumps(payload, ensure_ascii=False).encode()).hexdigest()


def _sync_locked(activity: OperationalActivity, alert: ReformAlert) -> OperationalActivity:
    if activity.company.organization_id != activity.organization_id:
        raise ValidationError("A atividade deve pertencer ao escritório da empresa.")
    version = reform_version(alert)
    if activity.reform_version == version:
        return activity
    activity.reform_version = version
    if activity.work_status in {"completed", "waived"}:
        activity.work_status = "pending"
        activity.completed_at = None
        activity.completed_by = None
        activity.waived_reason = ""
    activity.save(
        update_fields=[
            "reform_version",
            "work_status",
            "completed_at",
            "completed_by",
            "waived_reason",
            "updated_at",
        ]
    )
    OperationalActivityEvent.objects.create(
        organization_id=activity.organization_id,
        activity=activity,
        event_type="reform_received",
        summary=f"Publicação observada ({version[:12]}): {alert.title}"[:500],
    )
    OperationalEvidence.objects.create(
        organization_id=activity.organization_id,
        activity=activity,
        kind="source",
        reference=f"radar:{alert.pk}:{version}",
        source_url=alert.source_url,
        summary=f"{alert.get_relevance_display()}: {alert.title}"[:500],
    )
    return activity


@transaction.atomic
def request_reform_analysis(
    *,
    alert_id: UUID,
    company_id: UUID,
    membership: Membership,
    actor: User,
    reason: str,
) -> OperationalActivity:
    # Same lock order as collection and recovery: publication, then activity.
    alert = ReformAlert.objects.select_for_update().get(pk=alert_id)
    company = ClientCompany.objects.select_related("organization").get(pk=company_id)
    candidate = OperationalActivity(organization=company.organization, company=company)
    if (
        membership.user_id != actor.pk
        or not actor.is_active
        or not can_operate_activity(membership=membership, activity=candidate)
        or company.organization.is_demo
    ):
        raise PermissionDenied("Você não pode criar uma análise para esta empresa.")
    if not ProductModule.objects.filter(
        organization=company.organization,
        code=ProductModule.Code.REFORM,
        enabled=True,
    ).exists():
        raise PermissionDenied("O Radar não está habilitado neste escritório.")
    if membership.role not in {Membership.Role.OWNER, Membership.Role.ADMIN}:
        grants = CompanyAccessGrant.objects.filter(
            organization=company.organization,
            membership=membership,
            company=company,
            is_active=True,
        )
        if not any(ProductModule.Code.REFORM in grant.modules for grant in grants):
            raise PermissionDenied("Seu acesso a esta empresa não inclui o Radar.")
    if not reason.strip() or len(reason.strip()) > 500:
        raise ValidationError("Informe uma justificativa de até 500 caracteres.")
    activity, created = OperationalActivity.objects.get_or_create(
        organization=company.organization,
        company=company,
        code=f"radar-{alert.pk}",
        competence=None,
        defaults={
            "source_reform_alert": alert,
            "title": "Analisar publicação do Radar",
            "area": "fiscal",
            "assigned_to": actor,
            "evidence_requirement": "human",
        },
    )
    activity = (
        OperationalActivity.objects.select_for_update()
        .select_related("company")
        .get(
            pk=activity.pk,
        )
    )
    if activity.source_reform_alert_id != alert.pk:
        raise ValidationError("O código já pertence a outra atividade.")
    if created:
        OperationalActivityEvent.objects.create(
            organization=company.organization,
            activity=activity,
            actor=actor,
            event_type="reform_requested",
            summary=reason.strip(),
        )
    return _sync_locked(activity, alert)


@transaction.atomic
def sync_reform_activities(alert_id: UUID, *, organization_id: UUID | None = None) -> int:
    alert = ReformAlert.objects.select_for_update().get(pk=alert_id)
    activities = (
        OperationalActivity.objects.select_for_update()
        .select_related("company")
        .filter(
            source_reform_alert=alert,
            organization__is_demo=False,
        )
    )
    if organization_id is not None:
        activities = activities.filter(organization_id=organization_id)
    count = 0
    for activity in activities:
        _sync_locked(activity, alert)
        count += 1
    return count
