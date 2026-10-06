"""D-277: legal deadlines come only from approved rules and an approved business calendar."""

from datetime import date

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.fiscal_calendar.models import (
    BusinessCalendarYear,
    NonBusinessDay,
    ReferenceStatus,
    TaxDeadlineRule,
)
from apps.fiscal_calendar.reference import (
    easter_sunday,
    load_reference_drafts,
    national_non_business_days,
)
from apps.fiscal_calendar.services import BusinessCalendar, approved_rule, rule_due_date
from apps.hub.models import (
    ActivityTemplate,
    ActivityTemplateAssignment,
    ClientCompany,
    OperationalActivity,
)
from apps.hub.operations import compute_due_dates
from apps.hub.recurrence import generate_assignment
from apps.organizations.models import Organization

ANBIMA_2026 = [
    date(2026, 1, 1),
    date(2026, 2, 16),
    date(2026, 2, 17),
    date(2026, 4, 3),
    date(2026, 4, 21),
    date(2026, 5, 1),
    date(2026, 6, 4),
    date(2026, 9, 7),
    date(2026, 10, 12),
    date(2026, 11, 2),
    date(2026, 11, 15),
    date(2026, 11, 20),
    date(2026, 12, 25),
]


def test_easter_and_national_days_match_the_published_financial_calendar():
    assert [easter_sunday(year) for year in (2025, 2026, 2027, 2028)] == [
        date(2025, 4, 20),
        date(2026, 4, 5),
        date(2027, 3, 28),
        date(2028, 4, 16),
    ]
    assert [day for day, _name in national_non_business_days(2026)] == ANBIMA_2026


class FiscalCalendarTests(TestCase):
    def setUp(self) -> None:
        load_reference_drafts(BusinessCalendarYear, NonBusinessDay, TaxDeadlineRule)
        self.reviewer = User.objects.create_user("revisor@example.test", "safe-password-123")

    def _approve(self, item: BusinessCalendarYear | TaxDeadlineRule) -> None:
        item.status = ReferenceStatus.APPROVED
        item.approved_by = self.reviewer
        item.approved_at = timezone.now()
        item.save()

    def _approve_all(self) -> None:
        for calendar in BusinessCalendarYear.objects.all():
            self._approve(calendar)
        for rule in TaxDeadlineRule.objects.all():
            self._approve(rule)

    def test_drafts_produce_no_legal_date(self) -> None:
        self.assertIsNone(approved_rule("dctfweb", date(2026, 9, 1)))

    def test_rules_follow_their_legal_shift_over_weekends_and_holidays(self) -> None:
        self._approve_all()
        calendar = BusinessCalendar()

        def due(code: str, competence: date) -> date:
            rule = approved_rule(code, competence)
            assert rule is not None
            return rule_due_date(rule, competence, calendar)

        # DCTFWeb: last business day of the following month (28/02/2026 is a Saturday).
        self.assertEqual(due("dctfweb", date(2026, 1, 1)), date(2026, 2, 27))
        self.assertEqual(due("dctfweb", date(2026, 9, 1)), date(2026, 10, 30))
        # Contribuições previdenciárias: day 20, brought forward (20/09/2026 is a Sunday;
        # 20/11/2026 is Consciência Negra).
        self.assertEqual(due("contribuicao-previdenciaria", date(2026, 8, 1)), date(2026, 9, 18))
        self.assertEqual(due("contribuicao-previdenciaria", date(2026, 10, 1)), date(2026, 11, 19))
        # DAS: day 20, postponed.
        self.assertEqual(due("das-simples-nacional", date(2026, 8, 1)), date(2026, 9, 21))
        self.assertEqual(due("das-simples-nacional", date(2026, 10, 1)), date(2026, 11, 23))
        # DCTFWeb rule starts in 02/2025: January 2025 had its own extended deadline.
        self.assertIsNone(approved_rule("dctfweb", date(2025, 1, 1)))

    def test_approved_rule_is_frozen(self) -> None:
        rule = TaxDeadlineRule.objects.get(code="dctfweb", version=1)
        self._approve(rule)
        rule.day = 15
        with self.assertRaises(ValidationError):
            rule.save()

    def test_template_deadlines_use_rule_lead_time_and_never_pass_the_legal_date(self) -> None:
        self._approve_all()
        office = Organization.objects.create(name="Prazos", slug="prazos")
        template = ActivityTemplate.objects.create(
            organization=office,
            code="dctfweb",
            title="Transmitir DCTFWeb",
            area="fiscal",
            due_month_offset=1,
            legal_rule_code="dctfweb",
        )
        due = compute_due_dates(template=template, assignment=None, competence=date(2026, 9, 1))
        self.assertEqual(due.legal, date(2026, 10, 30))
        self.assertEqual(due.internal, date(2026, 10, 28))
        self.assertEqual(due.rule.code if due.rule else "", "dctfweb")

        template.internal_due_day = 31
        late = compute_due_dates(template=template, assignment=None, competence=date(2026, 9, 1))
        self.assertEqual(late.internal, date(2026, 10, 28))
        self.assertEqual([kind for kind, _summary in late.notes], ["internal_due_adjusted"])

    def test_missing_calendar_leaves_legal_date_empty_and_says_why(self) -> None:
        for rule in TaxDeadlineRule.objects.all():
            self._approve(rule)
        office = Organization.objects.create(name="Sem calendário", slug="sem-calendario")
        template = ActivityTemplate.objects.create(
            organization=office,
            code="inss",
            title="Pagar contribuições",
            area="payroll",
            due_month_offset=1,
            legal_rule_code="contribuicao-previdenciaria",
            internal_due_day=10,
        )
        due = compute_due_dates(template=template, assignment=None, competence=date(2026, 9, 1))
        self.assertIsNone(due.legal)
        self.assertEqual(due.internal, date(2026, 10, 10))
        self.assertEqual([kind for kind, _summary in due.notes], ["legal_due_unavailable"])


class OffsetRecurrenceTests(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Offset", slug="offset")
        self.company = ClientCompany.objects.create(organization=self.office, name="Empresa")

    def _assignment(self, offset: int) -> ActivityTemplateAssignment:
        template = ActivityTemplate.objects.create(
            organization=self.office,
            code=f"fechamento-{offset}",
            title="Conferir fechamento",
            area="accounting",
            internal_due_day=10,
            due_month_offset=offset,
        )
        return ActivityTemplateAssignment.objects.create(
            organization=self.office, company=self.company, template=template
        )

    def test_next_month_template_opens_the_closed_month_with_dates_after_it(self) -> None:
        assignment = self._assignment(1)

        self.assertEqual(generate_assignment(assignment.pk, today=date(2026, 10, 1)), 1)

        activity = OperationalActivity.objects.get()
        self.assertEqual(activity.competence, date(2026, 9, 1))
        self.assertEqual(activity.internal_due_on, date(2026, 10, 10))
        self.assertEqual(generate_assignment(assignment.pk, today=date(2026, 10, 31)), 0)
        self.assertEqual(generate_assignment(assignment.pk, today=date(2026, 11, 1)), 1)

    def test_same_month_templates_keep_their_previous_behaviour(self) -> None:
        assignment = self._assignment(0)

        self.assertEqual(generate_assignment(assignment.pk, today=date(2026, 10, 1)), 1)

        activity = OperationalActivity.objects.get()
        self.assertEqual(activity.competence, date(2026, 10, 1))
        self.assertEqual(activity.internal_due_on, date(2026, 10, 10))


class FiscalCalendarReviewTests(TestCase):
    def setUp(self) -> None:
        from django.test import Client

        from apps.platform.models import PlatformAccess
        from conftest import complete_mfa

        load_reference_drafts(BusinessCalendarYear, NonBusinessDay, TaxDeadlineRule)
        self.developer = User.objects.create_user("dev@example.test", "safe-password-123")
        PlatformAccess.objects.create(user=self.developer, role=PlatformAccess.Role.DEVELOPER)
        self.client = Client()
        self.client.force_login(self.developer)
        complete_mfa(self.client)

    def test_platform_reviewer_approves_and_retires_with_audit(self) -> None:
        from django.urls import reverse

        from apps.audit.models import AuditEvent

        rule = TaxDeadlineRule.objects.get(code="dctfweb", version=1)
        url = reverse("platform:fiscal-calendar")
        page = self.client.get(url)
        self.assertContains(page, "DCTFWeb — transmissão")
        self.assertContains(page, "IN RFB 2.237/2024")

        self.client.post(url, {"kind": "rule", "id": rule.pk, "decision": "approve"})
        rule.refresh_from_db()
        self.assertEqual(rule.status, ReferenceStatus.APPROVED)
        self.assertEqual(rule.approved_by, self.developer)
        self.assertTrue(AuditEvent.objects.filter(action="fiscal_calendar.rule_approved").exists())

        self.client.post(url, {"kind": "rule", "id": rule.pk, "decision": "retire"})
        rule.refresh_from_db()
        self.assertEqual(rule.status, ReferenceStatus.RETIRED)

    def test_office_users_cannot_review_deadlines(self) -> None:
        from django.test import Client
        from django.urls import reverse

        office_user = User.objects.create_user("office@example.test", "safe-password-123")
        client = Client()
        client.force_login(office_user)
        response = client.get(reverse("platform:fiscal-calendar"))
        self.assertIn(response.status_code, {302, 403})
        self.assertFalse(TaxDeadlineRule.objects.filter(status=ReferenceStatus.APPROVED).exists())


class MoveTemplateToNextMonthTests(TestCase):
    def setUp(self) -> None:
        from apps.organizations.models import Membership

        self.owner = User.objects.create_user("dono@example.test", "safe-password-123")
        self.office = Organization.objects.create(name="Mover", slug="mover")
        Membership.objects.create(
            organization=self.office, user=self.owner, role=Membership.Role.OWNER
        )
        self.company = ClientCompany.objects.create(organization=self.office, name="Empresa")
        self.template = ActivityTemplate.objects.create(
            organization=self.office,
            code="fechamento",
            title="Conferir fechamento",
            area="accounting",
            internal_due_day=10,
        )
        self.assignment = ActivityTemplateAssignment.objects.create(
            organization=self.office,
            company=self.company,
            template=self.template,
            next_generation_competence=date(2026, 11, 1),
        )
        self.client.force_login(self.owner)
        session = self.client.session
        session["hub_organization_id"] = str(self.office.id)
        session.save()

    def test_new_version_continues_from_the_same_cursor_without_duplicates(self) -> None:
        from django.urls import reverse

        page = self.client.get(reverse("hub:activity-models"))
        self.assertContains(page, "Vence no mês da competência")

        response = self.client.post(
            reverse("hub:activity-models"),
            {"action": "template-next-month", "template_id": str(self.template.id)},
        )

        self.assertEqual(response.status_code, 302)
        self.template.refresh_from_db()
        self.assignment.refresh_from_db()
        self.assertFalse(self.template.active)
        self.assertFalse(self.assignment.active)
        moved = ActivityTemplate.objects.get(code="fechamento", version=2)
        self.assertEqual(moved.due_month_offset, 1)
        moved_assignment = moved.company_assignments.get()
        self.assertEqual(moved_assignment.next_generation_competence, date(2026, 11, 1))
        self.assertEqual(generate_assignment(moved_assignment.pk, today=date(2026, 11, 15)), 0)
        self.assertEqual(generate_assignment(moved_assignment.pk, today=date(2026, 12, 1)), 1)
        activity = OperationalActivity.objects.get()
        self.assertEqual(activity.competence, date(2026, 11, 1))
        self.assertEqual(activity.internal_due_on, date(2026, 12, 10))
