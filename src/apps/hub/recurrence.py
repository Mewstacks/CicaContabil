"""Restartable monthly materialization of administrator-approved assignments."""

from __future__ import annotations

from datetime import date
from uuid import UUID

from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.audit.services import record_event
from apps.hub.controlplane import authorization_is_fresh, company_queryset_for_membership
from apps.hub.models import ActivityTemplateAssignment, OperationalActivityEvent, ProductModule
from apps.hub.module_catalog import OFFERED_MODULE_CODES
from apps.hub.operations import competence_ready_until, generate_monthly_activities
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantLifecycle


def next_month(value: date) -> date:
    return date(value.year + (value.month == 12), value.month % 12 + 1, 1)


@transaction.atomic
def generate_assignment(assignment_id: UUID, *, today: date) -> int:
    assignment = ActivityTemplateAssignment.objects.select_for_update().get(pk=assignment_id)
    office = assignment.organization
    if (
        not assignment.active
        or not assignment.template.active
        or assignment.template.frequency != "monthly"
        or not office.is_active
        or office.is_demo
        or not assignment.company.active
        or not authorization_is_fresh(office)
    ):
        return 0
    if (
        TenantLifecycle.objects.filter(organization=office)
        .exclude(state__in=[TenantLifecycle.State.ACTIVE, TenantLifecycle.State.GRACE])
        .exists()
    ):
        return 0
    modules = dict(
        ProductModule.objects.filter(
            organization=office, code__in=OFFERED_MODULE_CODES
        ).values_list("code", "enabled")
    )
    if set(modules) == set(OFFERED_MODULE_CODES) and {
        code for code, enabled in modules.items() if enabled
    } == {ProductModule.Code.NFSE}:
        return 0
    # Competência M opens on the first day of M + offset (D-277): September's closing is
    # generated on 1 October when the template is due in the following month.
    current = competence_ready_until(today, assignment.template)
    cursor = assignment.next_generation_competence or current
    cursor = cursor.replace(day=1)
    if cursor > current:
        return 0
    responsible = assignment.assigned_to
    if responsible is not None:
        membership = Membership.objects.filter(
            organization=office, user=responsible, is_active=True, user__is_active=True
        ).first()
        if (
            not company_queryset_for_membership(membership)
            .filter(pk=assignment.company_id)
            .exists()
        ):
            assignment.assigned_to = None
    assignment.full_clean()
    created_count = 0
    for _ in range(12):
        if cursor > current:
            break
        created, _ignored = generate_monthly_activities(
            assignments=[assignment], competence=cursor, actor=None, request=None
        )
        for activity in created:
            if responsible is not None and assignment.assigned_to is None:
                OperationalActivityEvent.objects.create(
                    organization=office,
                    activity=activity,
                    event_type="assignment_unavailable",
                    summary=(
                        "Gerada sem responsável: a atribuição anterior "
                        "não tem acesso ativo à empresa."
                    ),
                )
        created_count += len(created)
        cursor = next_month(cursor)
    assignment.next_generation_competence = cursor
    assignment.save(update_fields=["next_generation_competence", "updated_at"])
    record_event(
        action="hub.activity.recurrence_advanced",
        organization=office,
        target=assignment,
        metadata={"next_competence": cursor.isoformat(), "created": created_count},
    )
    return created_count


def generate_due_assignments(*, today: date | None = None) -> dict[str, int]:
    reference = today or timezone.localdate()
    counts = {"created": 0, "failed": 0, "examined": 0}
    assignments = (
        ActivityTemplateAssignment.objects.filter(
            active=True,
            template__active=True,
            template__frequency="monthly",
            company__active=True,
            organization__is_active=True,
            organization__is_demo=False,
        )
        .filter(
            Q(next_generation_competence__isnull=True)
            | Q(next_generation_competence__lte=reference.replace(day=1))
        )
        .values_list("pk", "organization_id")
        .iterator(chunk_size=200)
    )
    for assignment_id, organization_id in assignments:
        counts["examined"] += 1
        try:
            counts["created"] += generate_assignment(assignment_id, today=reference)
        except Exception as exc:
            counts["failed"] += 1
            record_event(
                action="hub.activity.recurrence_failed",
                organization=Organization(pk=organization_id),
                success=False,
                metadata={"assignment_id": str(assignment_id), "error": type(exc).__name__},
            )
    return counts
