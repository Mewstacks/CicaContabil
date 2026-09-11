from __future__ import annotations

from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany, OperationalTask
from apps.organizations.models import Membership, Organization


class OperationalTaskTests(TestCase):
    def setUp(self) -> None:
        self.user = User.objects.create_user("owner@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Acme Ltda"
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

    def test_owner_can_create_and_complete_a_company_task(self) -> None:
        created = self.client.post(
            reverse("hub:tasks"),
            {
                "company": str(self.company.id),
                "title": "Conferir guia",
                "details": "Antes do vencimento",
                "due_on": "2026-09-15",
                "priority": OperationalTask.Priority.HIGH,
            },
        )
        self.assertRedirects(created, reverse("hub:tasks"))
        task = OperationalTask.objects.get(organization=self.organization)
        self.assertEqual(task.created_by, self.user)

        completed = self.client.post(reverse("hub:complete-task", args=[task.id]))
        self.assertRedirects(completed, reverse("hub:tasks"))
        task.refresh_from_db()
        self.assertEqual(task.status, OperationalTask.Status.COMPLETED)
        self.assertEqual(task.completed_by, self.user)

    def test_auditor_can_view_but_cannot_change_tasks(self) -> None:
        Membership.objects.filter(user=self.user, organization=self.organization).update(
            role=Membership.Role.AUDITOR
        )
        task = OperationalTask.objects.create(
            organization=self.organization, company=self.company, title="Somente leitura"
        )
        response = self.client.post(reverse("hub:complete-task", args=[task.id]))
        self.assertEqual(response.status_code, 403)
