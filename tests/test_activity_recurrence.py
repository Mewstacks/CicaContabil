from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

import pytest
from django.db import close_old_connections, connection, connections
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import (
    ActivityTemplate,
    ActivityTemplateAssignment,
    ClientCompany,
    CompanyAccessGrant,
    OperationalActivity,
    OperationalActivityEvent,
    ProductModule,
)
from apps.hub.module_catalog import OFFERED_MODULE_CODES
from apps.hub.recurrence import generate_assignment, generate_due_assignments
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantLifecycle


@pytest.mark.django_db(transaction=True)
def test_concurrent_recurrence_advances_cursor_once_without_duplicate_activities():
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks and independent transactions.")
    office = Organization.objects.create(name="Concurrent recurrence", slug="concurrent-recurrence")
    company = ClientCompany.objects.create(organization=office, name="Company")
    template = ActivityTemplate.objects.create(
        organization=office, code="concurrent-closing", title="Closing", area="fiscal",
        internal_due_day=8,
    )
    assignment = ActivityTemplateAssignment.objects.create(
        organization=office, company=company, template=template,
        next_generation_competence=date(2026, 7, 1),
    )
    barrier = Barrier(4)

    def generate_from_connection(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return generate_assignment(assignment.pk, today=date(2026, 9, 24))
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=4) as executor:
        counts = list(executor.map(generate_from_connection, range(4)))
    assert sorted(counts) == [0, 0, 0, 3]
    assignment.refresh_from_db()
    assert assignment.next_generation_competence == date(2026, 10, 1)
    assert list(OperationalActivity.objects.order_by("competence").values_list(
        "competence", flat=True,
    )) == [date(2026, 7, 1), date(2026, 8, 1), date(2026, 9, 1)]
    assert generate_assignment(assignment.pk, today=date(2026, 9, 24)) == 0


class RecurrenceTests(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Recorrência", slug="recurrence")
        self.company = ClientCompany.objects.create(organization=self.office, name="Empresa")
        self.user = User.objects.create_user("recurrence@example.test", "local-test-password")
        self.membership = Membership.objects.create(
            organization=self.office,
            user=self.user,
            role=Membership.Role.OPERATOR,
        )
        self.grant = CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=self.membership,
            company=self.company,
        )
        self.template = ActivityTemplate.objects.create(
            organization=self.office,
            code="closing",
            title="Fechamento",
            area="fiscal",
            internal_due_day=8,
        )
        self.assignment = ActivityTemplateAssignment.objects.create(
            organization=self.office,
            company=self.company,
            template=self.template,
            assigned_to=self.user,
        )

    def test_first_execution_current_month_then_catch_up_and_repeat(self) -> None:
        first = generate_due_assignments(today=date(2026, 12, 24))
        self.assertEqual(first["created"], 1)
        self.assertEqual(generate_due_assignments(today=date(2026, 12, 25))["created"], 0)
        resumed = generate_due_assignments(today=date(2027, 3, 1))
        self.assertEqual(resumed["created"], 3)
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.next_generation_competence, date(2027, 4, 1))
        self.assertEqual(OperationalActivity.objects.count(), 4)
        self.assertEqual(
            OperationalActivity.objects.get(competence=date(2027, 2, 1)).internal_due_on,
            date(2027, 2, 8),
        )
        self.assertFalse(OperationalActivityEvent.objects.filter(actor__isnull=False).exists())

    def test_cursor_and_activities_roll_back_together_after_interruption(self) -> None:
        with patch(
            "apps.hub.recurrence.record_event", side_effect=[RuntimeError("private details"), None]
        ):
            result = generate_due_assignments(today=date(2026, 9, 1))
        self.assertEqual(result["failed"], 1)
        self.assertFalse(OperationalActivity.objects.exists())
        self.assignment.refresh_from_db()
        self.assertIsNone(self.assignment.next_generation_competence)
        self.assertEqual(generate_due_assignments(today=date(2026, 9, 1))["created"], 1)

    def test_invalid_assignment_is_audited_and_does_not_block_other_company(self) -> None:
        bad = ActivityTemplate.objects.create(
            organization=self.office,
            code="bad",
            title="Inválido",
            area="fiscal",
            internal_due_day=45,
        )
        ActivityTemplateAssignment.objects.create(
            organization=self.office,
            company=self.company,
            template=bad,
        )
        result = generate_due_assignments(today=date(2026, 9, 1))
        self.assertEqual(result["created"], 1)
        self.assertEqual(result["failed"], 1)
        failure = AuditEvent.objects.get(action="hub.activity.recurrence_failed")
        self.assertFalse(failure.success)
        self.assertEqual(set(failure.metadata), {"assignment_id", "error"})

    def test_revoked_responsible_becomes_unassigned_without_changing_template(self) -> None:
        self.grant.is_active = False
        self.grant.save()
        self.assertEqual(generate_due_assignments(today=date(2026, 9, 1))["created"], 1)
        activity = OperationalActivity.objects.get()
        self.assertIsNone(activity.assigned_to_id)
        self.assertTrue(activity.events.filter(event_type="assignment_unavailable").exists())
        self.assignment.refresh_from_db()
        self.assertEqual(self.assignment.assigned_to_id, self.user.id)

    def test_batch_limit_keeps_remaining_competences_for_next_execution(self) -> None:
        self.assignment.next_generation_competence = date(2025, 1, 1)
        self.assignment.save()
        self.assertEqual(generate_due_assignments(today=date(2026, 2, 1))["created"], 12)
        self.assertEqual(generate_due_assignments(today=date(2026, 2, 1))["created"], 2)
        self.assertEqual(generate_due_assignments(today=date(2026, 2, 1))["created"], 0)

    def test_pause_and_resume_reset_cursor_through_administrator_action(self) -> None:
        self.membership.role = Membership.Role.OWNER
        self.membership.save()
        self.assignment.next_generation_competence = date(2020, 1, 1)
        self.assignment.save()
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()
        for expected_active in (False, True):
            response = self.client.post(
                reverse("hub:activity-models"),
                {
                    "action": "assignment-toggle",
                    "assignment_id": str(self.assignment.id),
                },
            )
            self.assertEqual(response.status_code, 302)
            self.assignment.refresh_from_db()
            self.assertEqual(self.assignment.active, expected_active)
            self.assertEqual(
                self.assignment.next_generation_competence, timezone.localdate().replace(day=1)
            )
        result = generate_due_assignments()
        self.assertEqual(result["created"], 1)
        self.assertEqual(OperationalActivity.objects.count(), 1)

    def test_paused_demo_inactive_and_nfse_only_do_not_generate(self) -> None:
        for target, field in (
            (self.assignment, "active"),
            (self.company, "active"),
            (self.template, "active"),
            (self.office, "is_active"),
        ):
            with self.subTest(field=field, model=type(target).__name__):
                setattr(target, field, False)
                target.save()
                self.assertEqual(generate_due_assignments(today=date(2026, 9, 1))["created"], 0)
                setattr(target, field, True)
                target.save()
        self.office.is_demo = True
        self.office.save()
        self.assertEqual(generate_due_assignments(today=date(2026, 9, 1))["created"], 0)
        self.office.is_demo = False
        self.office.save()
        lifecycle = TenantLifecycle.objects.create(organization=self.office, state="suspended")
        self.assertEqual(generate_due_assignments(today=date(2026, 9, 1))["created"], 0)
        lifecycle.delete()
        for code in OFFERED_MODULE_CODES:
            ProductModule.objects.create(
                organization=self.office, code=code, enabled=code == ProductModule.Code.NFSE
            )
        self.assertEqual(generate_due_assignments(today=date(2026, 9, 1))["created"], 0)
