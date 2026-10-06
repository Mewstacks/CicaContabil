"""In-product notices (D-277): deduplicated, scoped by portfolio, never sent outside CICA."""

from __future__ import annotations

from datetime import date, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.controlplane import company_queryset_for_membership
from apps.hub.models import (
    Certificate,
    ClientCompany,
    Notification,
    OperationalActivity,
)
from apps.organizations.models import Membership, Organization

CLOSED_STATES = (
    OperationalActivity.WorkStatus.COMPLETED,
    OperationalActivity.WorkStatus.WAIVED,
)


def notify(
    *,
    organization: Organization,
    recipient: User | None,
    kind: str,
    title: str,
    dedupe_key: str,
    activity: OperationalActivity | None = None,
    company: ClientCompany | None = None,
) -> Notification | None:
    """Create once per recipient and key; returns the notice only when it is new."""

    if recipient is None or not recipient.is_active:
        return None
    notice, created = Notification.objects.get_or_create(
        organization=organization,
        recipient=recipient,
        dedupe_key=dedupe_key[:160],
        defaults={
            "kind": kind,
            "title": title[:200],
            "activity": activity,
            "company": company or (activity.company if activity else None),
        },
    )
    return notice if created else None


def notify_activity_owner(
    activity: OperationalActivity, *, kind: str, dedupe_key: str, actor: User | None = None
) -> Notification | None:
    """Tell whoever owns the activity, except the person who caused the change."""

    if activity.assigned_to_id is None or activity.assigned_to_id == getattr(actor, "pk", None):
        return None
    return notify(
        organization=activity.organization,
        recipient=activity.assigned_to,
        kind=kind,
        title=f"{activity.title} · {activity.company.name}",
        dedupe_key=dedupe_key,
        activity=activity,
    )


def _administrators(organization: Organization, company: ClientCompany) -> list[User]:
    people = []
    for membership in Membership.objects.filter(
        organization=organization,
        role__in=[Membership.Role.OWNER, Membership.Role.ADMIN],
        is_active=True,
        user__is_active=True,
    ).select_related("user"):
        if company_queryset_for_membership(membership).filter(pk=company.pk).exists():
            people.append(membership.user)
    return people


def notify_due_activities(*, today: date | None = None) -> dict[str, int]:
    """Daily: due today, due tomorrow and first day overdue; unassigned overdue goes to admins."""

    today = today or timezone.localdate()
    counts = {"due_today": 0, "due_soon": 0, "overdue": 0}
    due = (
        OperationalActivity.objects.filter(
            organization__is_active=True, organization__is_demo=False
        )
        .exclude(work_status__in=CLOSED_STATES)
        .select_related("organization", "company", "assigned_to")
    )
    windows = (
        ("due_today", Notification.Kind.DUE_TODAY, today),
        ("due_soon", Notification.Kind.DUE_SOON, today + timedelta(days=1)),
        ("overdue", Notification.Kind.OVERDUE, today - timedelta(days=1)),
    )
    for key, kind, day in windows:
        matches = due.filter(
            Q(internal_due_on=day) | Q(internal_due_on__isnull=True, legal_due_on=day)
        )
        # One day's window is small; no server-side cursor (PgBouncer in production).
        for activity in list(matches):
            dedupe = f"{key}:{activity.pk}:{day.isoformat()}"
            if activity.assigned_to_id:
                created = notify_activity_owner(activity, kind=kind, dedupe_key=dedupe)
                counts[key] += int(created is not None)
            elif kind == Notification.Kind.OVERDUE:
                for person in _administrators(activity.organization, activity.company):
                    notify(
                        organization=activity.organization,
                        recipient=person,
                        kind=kind,
                        title=f"Sem responsável · {activity.title} · {activity.company.name}",
                        dedupe_key=dedupe,
                        activity=activity,
                    )
                    counts[key] += 1
    return counts


def notify_expiring_certificates(*, today: date | None = None) -> int:
    """Certificates that stop being valid within 30 days; one notice per certificate and date."""

    today = today or timezone.localdate()
    created = 0
    for certificate in Certificate.objects.filter(
        company__organization__is_active=True,
        company__organization__is_demo=False,
        company__active=True,
        revoked_at__isnull=True,
        valid_until__date__gte=today,
        valid_until__date__lte=today + timedelta(days=30),
    ).select_related("company", "company__organization"):
        company = certificate.company
        for person in _administrators(company.organization, company):
            notify(
                organization=company.organization,
                recipient=person,
                kind=Notification.Kind.CERTIFICATE_EXPIRING,
                title=f"{company.name} · A1 vence em {certificate.valid_until:%d/%m/%Y}",
                dedupe_key=f"certificate:{certificate.pk}:{certificate.valid_until:%Y%m%d}",
                company=company,
            )
            created += 1
    return created


def purge_read_notifications(*, days: int = 90) -> int:
    limit = timezone.now() - timedelta(days=days)
    deleted, _rows = Notification.objects.filter(read_at__lt=limit).delete()
    return deleted


def notify_new_dte(activity: OperationalActivity, *, message_id: object) -> int:
    """A new Caixa Postal message: its owner, or the administration when nobody owns it."""

    dedupe = f"dte:{message_id}"
    if activity.assigned_to_id:
        return int(
            notify_activity_owner(
                activity, kind=Notification.Kind.DTE_RECEIVED, dedupe_key=dedupe
            )
            is not None
        )
    people = _administrators(activity.organization, activity.company)
    for person in people:
        notify(
            organization=activity.organization,
            recipient=person,
            kind=Notification.Kind.DTE_RECEIVED,
            title=f"{activity.company.name} · nova mensagem na Caixa DTE",
            dedupe_key=dedupe,
            activity=activity,
        )
    return len(people)
