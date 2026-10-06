from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import Client, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.demo_scenario import persona_email, populate_operations
from apps.hub.models import (
    ActivityTemplate,
    OperationalActivity,
    OperationalActivityEvent,
    OperationalEvidence,
)
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def demo():
    with override_settings(DEBUG=True):
        call_command("seed_demo", password="fixture-only-secret-123", verbosity=0)
    return Organization.objects.get(slug="escritorio-demo")


def test_operational_scenario_is_complete_and_replay_preserves_evidence(demo):
    query = OperationalActivity.objects.filter(organization=demo)
    assert query.count() == 84
    assert set(query.values_list("area", flat=True)) == {
        "accounting",
        "fiscal",
        "payroll",
        "general",
    }
    assert set(query.values_list("work_status", flat=True)) == set(
        OperationalActivity.WorkStatus.values
    )
    assert query.filter(assigned_to__isnull=True).exists()
    assert query.filter(freshness="unavailable").exists()
    assert ActivityTemplate.objects.filter(organization=demo).count() == 6
    snapshots = list(query.order_by("pk").values())
    evidence = OperationalEvidence.objects.count()
    history = OperationalActivityEvent.objects.count()
    assert populate_operations(demo)["created"] == 0
    assert list(query.order_by("pk").values()) == snapshots
    assert OperationalEvidence.objects.count() == evidence
    assert OperationalActivityEvent.objects.count() == history
    assert not User.objects.get(email=persona_email(demo)).has_usable_password()


def test_operations_refuse_real_tenant_without_writes():
    real = Organization.objects.create(name="Real", slug="real")
    with pytest.raises(ValidationError):
        populate_operations(real)
    with pytest.raises(CommandError):
        call_command("seed_demo_operations", slug="real")
    assert not OperationalActivity.objects.exists()
    assert not User.objects.exists()


@override_settings(DEMO_ENTRY_ENABLED=True, DEMO_SESSION_ISOLATION_READY=True)
def test_public_demo_has_personal_agenda_and_private_visitors(demo):
    first, second = Client(), Client()
    for visitor in (first, second):
        assert visitor.post(reverse("hub:demo-entry")).status_code == 302
        response = visitor.get(reverse("hub:dashboard"))
        assert response.status_code == 200
        assert response.context["agenda_page"].paginator.count > 0
        assert response.context["demo_persona_name"] == "Ana Martins"
        assert all(
            a.assigned_to.email == persona_email(demo)
            for a in response.context["dashboard_activities"]
        )
    response = first.get(reverse("hub:dashboard"), {"view": "management"})
    assert not any(m.user.email.startswith("demo-") for m in response.context["admin_workload"])
    activity = OperationalActivity.objects.filter(organization=demo, work_status="pending").first()
    before = activity.work_status
    for client in (first, second):
        detail = client.get(reverse("hub:activity-detail", args=[activity.pk]))
        assert not detail.context["can_manage_activity"]
        assert not detail.context["can_assign_activity"]
        assert client.post(reverse("hub:activity-complete", args=[activity.pk])).status_code == 403
    member = Client()
    member.force_login(User.objects.get(email="demo@hubcontador.local"))
    assert member.get(reverse("hub:dashboard")).context["agenda_page"].paginator.count > 0
    assert member.post(reverse("hub:activity-complete", args=[activity.pk])).status_code == 403
    activity.refresh_from_db()
    assert activity.work_status == before


def test_new_month_adds_only_missing_competences(demo):
    first = populate_operations(demo, today=date(2027, 1, 1))
    assert first["created"] == 84
    second = populate_operations(demo, today=date(2027, 2, 1))
    assert second["created"] == 42


def test_demo_window_keeps_every_date_after_its_competence(demo):
    """D-277: the demonstration closes the month that ended; no due date precedes it."""

    from apps.hub.demo_scenario import refresh_demo_guides
    from apps.hub.models import FiscalGuide

    populate_operations(demo, today=date(2026, 10, 6))
    refresh_demo_guides(demo, today=date(2026, 10, 6))

    open_work = OperationalActivity.objects.filter(
        organization=demo, work_status__in=["pending", "in_progress", "blocked"]
    )
    assert set(open_work.values_list("competence", flat=True)) == {date(2026, 9, 1)}
    assert all(
        due >= date(2026, 10, 1)
        for due in open_work.values_list("internal_due_on", flat=True)
        if due
    )
    history = OperationalActivity.objects.filter(organization=demo, competence=date(2026, 8, 1))
    assert set(history.values_list("work_status", flat=True)) == {"completed"}
    guides = FiscalGuide.objects.filter(organization=demo, status=FiscalGuide.Status.READY)
    assert set(guides.values_list("competence", flat=True)) == {"09/2026"}
    assert set(guides.values_list("due_on", flat=True)) == {date(2026, 10, 20)}
