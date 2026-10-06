"""D-277 phase 3: bulk work, deadlines, notes and claiming in the activity center."""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    OperationalActivity,
    OperationalEvidence,
)
from apps.organizations.models import Membership, Organization


class DailyRoutineTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            "owner@example.test", "safe-password-123", full_name="Dona"
        )
        self.operator = User.objects.create_user(
            "operator@example.test", "safe-password-123", full_name="Ana Martins"
        )
        self.auditor = User.objects.create_user("auditor@example.test", "safe-password-123")
        self.office = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(
            organization=self.office, user=self.owner, role=Membership.Role.OWNER
        )
        operator_membership = Membership.objects.create(
            organization=self.office, user=self.operator, role=Membership.Role.OPERATOR
        )
        auditor_membership = Membership.objects.create(
            organization=self.office, user=self.auditor, role=Membership.Role.AUDITOR
        )
        self.company = ClientCompany.objects.create(organization=self.office, name="Empresa A")
        self.other = ClientCompany.objects.create(organization=self.office, name="Empresa B")
        for membership in (operator_membership, auditor_membership):
            CompanyAccessGrant.objects.create(
                organization=self.office,
                membership=membership,
                company=self.company,
                capabilities=["*"],
            )
        today = timezone.localdate()
        self.activities = [
            OperationalActivity.objects.create(
                organization=self.office,
                company=self.company,
                code=f"rotina-{index}",
                title=f"Rotina {index}",
                area="fiscal",
                competence=date(2026, 9, 1),
                internal_due_on=today + timedelta(days=index),
                legal_due_on=today + timedelta(days=10),
                evidence_requirement="human",
            )
            for index in range(3)
        ]

    def _login(self, user: User) -> None:
        self.client.force_login(user)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()

    def _bulk(self, action: str, **extra: str):  # type: ignore[no-untyped-def]
        payload: dict[str, object] = {
            "action": action,
            "activity_ids": [str(activity.pk) for activity in self.activities],
            "reason": "Redistribuição da semana",
            **extra,
        }
        for activity in self.activities:
            activity.refresh_from_db()
            payload[f"expected_assignee_{activity.pk}"] = str(activity.assigned_to_id or "")
            payload[f"expected_due_{activity.pk}"] = (
                activity.internal_due_on.isoformat() if activity.internal_due_on else ""
            )
        return self.client.post(reverse("hub:activity-bulk-action"), payload)

    def test_owner_assigns_and_reschedules_in_one_step_with_history(self) -> None:
        self._login(self.owner)

        self.assertEqual(self._bulk("assign", assignee=str(self.operator.pk)).status_code, 302)
        for activity in self.activities:
            activity.refresh_from_db()
            self.assertEqual(activity.assigned_to, self.operator)
            self.assertTrue(activity.events.filter(event_type="assigned").exists())

        new_due = timezone.localdate() + timedelta(days=5)
        self._bulk("reschedule", internal_due_on=new_due.isoformat())
        for activity in self.activities:
            activity.refresh_from_db()
            self.assertEqual(activity.internal_due_on, new_due)
        self.assertEqual(AuditEvent.objects.filter(action="hub.activity.rescheduled").count(), 3)

    def test_reschedule_after_legal_deadline_changes_nothing(self) -> None:
        self._login(self.owner)
        before = [activity.internal_due_on for activity in self.activities]
        late = timezone.localdate() + timedelta(days=30)

        self._bulk("reschedule", internal_due_on=late.isoformat())

        for activity, previous in zip(self.activities, before, strict=True):
            activity.refresh_from_db()
            self.assertEqual(activity.internal_due_on, previous)

    def test_stale_assignee_refuses_the_whole_batch(self) -> None:
        self._login(self.owner)
        payload: dict[str, object] = {
            "action": "assign",
            "assignee": str(self.operator.pk),
            "reason": "Distribuição",
            "activity_ids": [str(activity.pk) for activity in self.activities],
        }
        for activity in self.activities:
            payload[f"expected_assignee_{activity.pk}"] = str(self.owner.pk)

        self.client.post(reverse("hub:activity-bulk-action"), payload)

        self.assertFalse(OperationalActivity.objects.filter(assigned_to=self.operator).exists())

    def test_complete_finishes_ready_items_and_reports_the_rest(self) -> None:
        ready = self.activities[0]
        OperationalEvidence.objects.create(
            organization=self.office,
            activity=ready,
            kind="human",
            reference="conf-1",
            summary="Conferido",
            recorded_by=self.owner,
            observed_at=timezone.now(),
        )
        self._login(self.owner)

        response = self._bulk("complete")

        self.assertEqual(response.status_code, 302)
        statuses = {
            activity.pk: OperationalActivity.objects.get(pk=activity.pk).work_status
            for activity in self.activities
        }
        self.assertEqual(statuses[ready.pk], OperationalActivity.WorkStatus.COMPLETED)
        self.assertEqual(
            [status for pk, status in statuses.items() if pk != ready.pk],
            [OperationalActivity.WorkStatus.PENDING] * 2,
        )

    def test_bulk_refuses_activities_outside_the_portfolio_and_over_the_limit(self) -> None:
        foreign = OperationalActivity.objects.create(
            organization=self.office,
            company=self.other,
            code="fora",
            title="Fora da carteira",
            area="fiscal",
        )
        self._login(self.operator)
        self.client.post(
            reverse("hub:activity-bulk-action"),
            {"action": "complete", "activity_ids": [str(foreign.pk)]},
        )
        foreign.refresh_from_db()
        self.assertEqual(foreign.work_status, OperationalActivity.WorkStatus.PENDING)

        self._login(self.owner)
        too_many = [
            str(
                OperationalActivity.objects.create(
                    organization=self.office,
                    company=self.company,
                    code=f"extra-{index}",
                    title="Extra",
                    area="fiscal",
                ).pk
            )
            for index in range(51)
        ]
        response = self.client.post(
            reverse("hub:activity-bulk-action"),
            {"action": "assign", "activity_ids": too_many, "reason": "x", "assignee": ""},
            follow=True,
        )
        self.assertContains(response, "até 50 atividades")

    def test_operator_cannot_reschedule_but_can_claim_and_note(self) -> None:
        activity = self.activities[0]
        self._login(self.operator)

        self.client.post(
            reverse("hub:activity-reschedule", args=[activity.pk]),
            {
                "internal_due_on": (timezone.localdate() + timedelta(days=4)).isoformat(),
                "expected_internal_due_on": activity.internal_due_on.isoformat(),
                "reason": "Cliente atrasou",
            },
        )
        activity.refresh_from_db()
        self.assertEqual(activity.internal_due_on, timezone.localdate())

        self.client.post(reverse("hub:activity-claim", args=[activity.pk]))
        activity.refresh_from_db()
        self.assertEqual(activity.assigned_to, self.operator)

        note_text = "Cliente prometeu o extrato na sexta."
        self.client.post(reverse("hub:activity-note", args=[activity.pk]), {"note": note_text})
        note = activity.events.get(event_type="note")
        self.assertEqual(note.actor, self.operator)
        self.assertEqual(
            AuditEvent.objects.get(action="hub.activity.note_added").metadata,
            {"length": len(note_text)},
        )

    def test_auditor_reads_but_cannot_note_or_claim(self) -> None:
        activity = self.activities[1]
        self._login(self.auditor)

        self.client.post(reverse("hub:activity-claim", args=[activity.pk]))
        self.client.post(reverse("hub:activity-note", args=[activity.pk]), {"note": "teste"})

        activity.refresh_from_db()
        self.assertIsNone(activity.assigned_to)
        self.assertFalse(activity.events.filter(event_type="note").exists())
