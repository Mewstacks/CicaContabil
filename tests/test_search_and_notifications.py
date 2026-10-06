"""D-277 phase 5: portfolio-scoped search and in-product notices."""

from datetime import date, timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    Notification,
    OperationalActivity,
    ProductModule,
)
from apps.hub.notifications import notify_due_activities
from apps.hub.services import create_document_and_artifact
from apps.organizations.models import Membership, Organization


class SearchAndNoticesTests(TestCase):
    def setUp(self) -> None:
        self.owner = User.objects.create_user(
            "owner@example.test", "safe-password-123", full_name="Dona"
        )
        self.operator = User.objects.create_user(
            "ana@example.test", "safe-password-123", full_name="Ana Martins"
        )
        self.office = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(
            organization=self.office, user=self.owner, role=Membership.Role.OWNER
        )
        self.operator_membership = Membership.objects.create(
            organization=self.office, user=self.operator, role=Membership.Role.OPERATOR
        )
        self.mine = ClientCompany.objects.create(
            organization=self.office,
            name="Padaria Vila Nova",
            cnpj_masked="12.345.678/0001-95",
            dominio_code="0101",
        )
        self.foreign = ClientCompany.objects.create(
            organization=self.office,
            name="Padaria Fora da Carteira",
            cnpj_masked="98.765.432/0001-10",
        )
        self.grant = CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=self.operator_membership,
            company=self.mine,
            modules=["nfse"],
            capabilities=["*"],
        )
        other_office = Organization.objects.create(name="Outro", slug="outro")
        ClientCompany.objects.create(organization=other_office, name="Padaria de Outro Escritório")

    def _login(self, user: User) -> None:
        self.client.force_login(user)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()

    def test_search_finds_company_by_cnpj_digits_only_inside_the_portfolio(self) -> None:
        self._login(self.operator)

        by_name = self.client.get(reverse("hub:search"), {"q": "Padaria"})
        by_digits = self.client.get(reverse("hub:search"), {"q": "12345678000195"})
        partial = self.client.get(reverse("hub:search"), {"q": "0101", "partial": "1"})

        self.assertContains(by_name, "Padaria Vila Nova")
        self.assertNotContains(by_name, "Padaria Fora da Carteira")
        self.assertNotContains(by_name, "Padaria de Outro Escritório")
        self.assertContains(by_digits, "Padaria Vila Nova")
        self.assertContains(partial, "Padaria Vila Nova")
        self.assertNotContains(partial, "<html")

    def test_search_finds_activities_and_notes_with_module_access(self) -> None:
        ProductModule.objects.create(
            organization=self.office, code=ProductModule.Code.NFSE, enabled=True
        )
        OperationalActivity.objects.create(
            organization=self.office,
            company=self.mine,
            code="folha",
            title="Conferir folha",
            area="payroll",
        )
        create_document_and_artifact(
            company=self.mine,
            original_xml="<nfse id='search' />",
            normalized_data={"number": "8812"},
            source_nsu="1",
        )
        self._login(self.operator)

        activity = self.client.get(reverse("hub:search"), {"q": "Conferir folha"})
        note = self.client.get(reverse("hub:search"), {"q": "8812"})

        self.assertContains(activity, "Conferir folha")
        self.assertContains(note, "NFS-e 8812")

    def test_assignment_creates_one_notice_for_the_new_owner(self) -> None:
        activity = OperationalActivity.objects.create(
            organization=self.office,
            company=self.mine,
            code="fiscal",
            title="Conferir apuração",
            area="fiscal",
        )
        self._login(self.owner)
        self.client.post(
            reverse("hub:activity-detail", args=[activity.pk]),
            {
                "action": "assign",
                "assignment-assignee": str(self.operator.pk),
                "assignment-expected_assignee": "",
                "assignment-reason": "Carteira da Ana",
            },
        )

        notice = Notification.objects.get(recipient=self.operator)
        self.assertEqual(notice.kind, Notification.Kind.ASSIGNED)
        self.assertFalse(Notification.objects.filter(recipient=self.owner).exists())

        self._login(self.operator)
        page = self.client.get(reverse("hub:dashboard"))
        self.assertContains(page, "workspace-badge")
        opened = self.client.get(reverse("hub:notification-open", args=[notice.pk]))
        self.assertRedirects(
            opened,
            reverse("hub:activity-detail", args=[activity.pk]),
            fetch_redirect_response=False,
        )
        notice.refresh_from_db()
        self.assertIsNotNone(notice.read_at)

    def test_due_reminders_are_deduplicated_and_unassigned_overdue_goes_to_admins(self) -> None:
        today = date(2026, 10, 6)
        OperationalActivity.objects.create(
            organization=self.office,
            company=self.mine,
            code="hoje",
            title="Vence hoje",
            area="fiscal",
            assigned_to=self.operator,
            internal_due_on=today,
        )
        OperationalActivity.objects.create(
            organization=self.office,
            company=self.mine,
            code="ontem",
            title="Venceu ontem",
            area="fiscal",
            internal_due_on=today - timedelta(days=1),
        )

        first = notify_due_activities(today=today)
        second = notify_due_activities(today=today)

        self.assertEqual(first["due_today"], 1)
        self.assertEqual(second["due_today"], 0)
        self.assertEqual(
            Notification.objects.filter(recipient=self.operator, kind="due_today").count(), 1
        )
        self.assertTrue(
            Notification.objects.filter(recipient=self.owner, kind="overdue").exists()
        )

    def test_notices_outside_the_current_portfolio_stay_hidden(self) -> None:
        notice = Notification.objects.create(
            organization=self.office,
            recipient=self.operator,
            kind=Notification.Kind.ASSIGNED,
            title="Conferir apuração · Padaria Fora da Carteira",
            company=self.foreign,
            dedupe_key="test",
        )
        self._login(self.operator)

        response = self.client.get(reverse("hub:notifications"))
        opened = self.client.get(reverse("hub:notification-open", args=[notice.pk]))

        self.assertNotContains(response, "Padaria Fora da Carteira")
        self.assertEqual(response.context["unread_notifications_count"], 0)
        self.assertEqual(opened.status_code, 404)
        notice.refresh_from_db()
        self.assertIsNone(notice.read_at)
        self.assertLess(notice.created_at, timezone.now() + timedelta(seconds=1))
