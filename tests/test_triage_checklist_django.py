"""AC-11.7: checklist empresa x tipo x competência, prazo, completude e rascunho de pedido."""

from __future__ import annotations

from datetime import date
from typing import Any

from django.core import mail
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ClientCompany, CompanyAccessGrant, ProductModule
from apps.organizations.models import Membership
from apps.triage.checklist import build_checklist, due_date, request_draft
from apps.triage.models import ChecklistEntry, ChecklistExpectation, DocumentType, TriageItem
from apps.triage.transitions import TriageStatus
from triage_v2_support import TriageV2Case


class ChecklistCase(TriageV2Case):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        super().setUp()
        self.extrato = self.make_type("extrato", "Extrato bancário", expected_default=True)
        self.guia = self.make_type(
            "guia", "Guia de imposto", expected_regimes=["simples", "mei"], due_day=20
        )
        self.opcional = self.make_type("contrato", "Contrato")

    def make_type(self, code: str, label: str, **extra: Any) -> DocumentType:
        return DocumentType.objects.create(
            organization=self.office,
            code=code,
            label=label,
            name_template="{codigo}_X_{periodo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
            **extra,
        )

    def deliver(self, company: ClientCompany, document_type: DocumentType, period: str) -> None:
        item = TriageItem.objects.create(
            organization=self.office,
            company=company,
            document_type=document_type,
            period_label=period,
            original_name="e.pdf",
            status=TriageStatus.ARCHIVED,
            archived_at=timezone.now(),
        )
        ChecklistEntry.objects.create(
            organization=self.office,
            company=company,
            document_type=document_type,
            period_label=period,
            triage_item=item,
            received_at=timezone.now(),
        )

    def operator(self) -> User:
        user = User.objects.create_user("op-ck@office.test", "safe-password-123")
        membership = Membership.objects.create(
            organization=self.office, user=user, role=Membership.Role.OPERATOR
        )
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=membership,
            company=self.company,
            modules=[ProductModule.Code.TRIAGE],
            capabilities=["read"],
        )
        return user


class ChecklistDomainTests(ChecklistCase):
    TODAY = date(2026, 10, 25)

    def rows(self, period: str = "2026-09", today: date | None = None) -> Any:
        companies = ClientCompany.objects.filter(organization=self.office)
        return build_checklist(self.office, companies, period, today or self.TODAY)

    def test_expected_types_come_from_default_regime_and_company_exception(self) -> None:
        other = ClientCompany.objects.create(
            organization=self.office,
            name="Real SA",
            dominio_code="8",
            tax_regime=ClientCompany.TaxRegime.REAL,
        )
        ChecklistExpectation.objects.create(
            organization=self.office,
            company=other,
            document_type=self.opcional,
            requirement="expected",
        )
        by_name = {row.company.name: row for row in self.rows().rows}
        self.assertEqual(
            {c.document_type.code for c in by_name["Padaria Sol"].cells}, {"extrato", "guia"}
        )
        self.assertEqual(
            {c.document_type.code for c in by_name["Real SA"].cells}, {"extrato", "contrato"}
        )

    def test_waived_exception_removes_the_type(self) -> None:
        ChecklistExpectation.objects.create(
            organization=self.office,
            company=self.company,
            document_type=self.extrato,
            requirement="waived",
        )
        row = self.rows().rows[0]
        self.assertEqual({c.document_type.code for c in row.cells}, {"guia"})

    def test_delivered_missing_late_and_not_yet_due(self) -> None:
        self.deliver(self.company, self.extrato, "2026-09")
        row = self.rows().rows[0]
        cells = {c.document_type.code: c for c in row.cells}
        self.assertEqual(cells["extrato"].status, "delivered")
        # guia is due on the 20th of the following month: 25/10 - 20/10 = 5 days late
        self.assertEqual((cells["guia"].status, cells["guia"].days_late), ("late", 5))
        early = self.rows(today=date(2026, 10, 10)).rows[0]
        guia = {c.document_type.code: c for c in early.cells}["guia"]
        self.assertEqual((guia.status, guia.days_late), ("pending", 0))

    def test_default_due_day_is_the_tenth(self) -> None:
        self.assertEqual(due_date(self.extrato, "2026-09"), date(2026, 10, 10))
        self.assertEqual(due_date(self.guia, "2026-09"), date(2026, 10, 20))
        self.assertEqual(due_date(self.guia, "2026-12"), date(2027, 1, 20))

    def test_due_day_is_clamped_to_the_month(self) -> None:
        late = self.make_type("fatura", "Fatura", due_day=31)
        self.assertEqual(due_date(late, "2026-01"), date(2026, 2, 28))

    def test_completeness_percentage_and_totals(self) -> None:
        self.deliver(self.company, self.extrato, "2026-09")
        result = self.rows()
        self.assertEqual(result.rows[0].delivered, 1)
        self.assertEqual(result.rows[0].expected, 2)
        self.assertEqual(result.rows[0].percent, 50)
        self.assertEqual(result.percent, 50)

    def test_other_period_deliveries_do_not_count(self) -> None:
        self.deliver(self.company, self.extrato, "2026-08")
        self.assertEqual(self.rows().rows[0].delivered, 0)

    def test_company_without_expected_types_is_complete_not_zero(self) -> None:
        DocumentType.objects.filter(organization=self.office).update(
            expected_default=False, expected_regimes=[]
        )
        row = self.rows().rows[0]
        self.assertEqual((row.expected, row.percent), (0, 100))

    def test_never_mixes_offices(self) -> None:
        other = self.make_office("e11-ck-other")
        stranger = ClientCompany.objects.create(organization=other, name="Y", dominio_code="1")
        DocumentType.objects.create(
            organization=other,
            code="x",
            label="X",
            name_template="{codigo}",
            period_kind="competencia",
            expected_default=True,
        )
        names = {row.company.name for row in self.rows().rows}
        self.assertNotIn(stranger.name, names)
        row = next(r for r in self.rows().rows if r.company == self.company)
        self.assertNotIn("x", {c.document_type.code for c in row.cells})

    def test_request_draft_lists_only_what_is_missing(self) -> None:
        self.deliver(self.company, self.extrato, "2026-09")
        self.company.contact_name = "Maria"
        self.company.contact_email = "maria@padaria.example"
        self.company.save()
        row = self.rows().rows[0]
        draft = request_draft(row, "2026-09")
        self.assertIn("Guia de imposto", draft.body)
        self.assertNotIn("Extrato bancário", draft.body)
        self.assertIn("09/2026", draft.subject)
        self.assertIn("Maria", draft.body)
        self.assertEqual(draft.to, "maria@padaria.example")
        self.assertIn("há 5 dias", draft.body)


class ChecklistViewTests(ChecklistCase):
    def setUp(self) -> None:
        super().setUp()
        self.login()
        self.url = reverse("hub:triage-checklist")

    def test_page_lists_company_expected_types_and_completeness(self) -> None:
        self.deliver(self.company, self.extrato, "2026-09")
        response = self.client.get(self.url, {"periodo": "2026-09"})
        self.assertContains(response, "Padaria Sol")
        self.assertContains(response, "Extrato bancário")
        self.assertContains(response, "Recebido")
        self.assertContains(response, "50%")

    def test_invalid_period_falls_back_to_the_current_month(self) -> None:
        response = self.client.get(self.url, {"periodo": "lixo"})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, timezone.localdate().strftime("%m/%Y"))

    def test_pending_filter_hides_complete_companies(self) -> None:
        complete = ClientCompany.objects.create(
            organization=self.office, name="Completa Ltda", dominio_code="55"
        )
        self.deliver(complete, self.extrato, "2026-09")
        response = self.client.get(self.url, {"periodo": "2026-09", "pendentes": "1"})
        self.assertNotContains(response, "Completa Ltda")
        self.assertContains(response, "Padaria Sol")

    def test_empty_state_has_a_way_out(self) -> None:
        DocumentType.objects.filter(organization=self.office).delete()
        response = self.client.get(self.url)
        self.assertContains(response, reverse("hub:triage-catalog"))

    def test_other_offices_data_never_appears(self) -> None:
        other = self.make_office("e11-ck-view-other")
        ClientCompany.objects.create(organization=other, name="Empresa Secreta", dominio_code="9")
        self.assertNotContains(self.client.get(self.url), "Empresa Secreta")

    def test_operator_sees_only_companies_of_the_grant(self) -> None:
        ClientCompany.objects.create(
            organization=self.office, name="Fora do Escopo", dominio_code="77"
        )
        self.login(self.operator())
        response = self.client.get(self.url, {"periodo": "2026-09"})
        self.assertContains(response, "Padaria Sol")
        self.assertNotContains(response, "Fora do Escopo")

    def test_login_and_module_are_required(self) -> None:
        ProductModule.objects.filter(organization=self.office).update(enabled=False)
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)


class ChecklistDraftViewTests(ChecklistCase):
    def setUp(self) -> None:
        super().setUp()
        self.login()
        self.company.contact_email = "maria@padaria.example"
        self.company.save()
        self.url = reverse("hub:triage-checklist-request", args=[self.company.pk])

    def test_draft_shows_text_and_a_mailto_and_sends_nothing(self) -> None:
        response = self.client.get(self.url, {"periodo": "2026-09"})
        self.assertContains(response, "Guia de imposto")
        self.assertContains(response, "mailto:maria@padaria.example")
        self.assertEqual(len(mail.outbox), 0)

    def test_draft_without_a_contact_email_has_no_mailto(self) -> None:
        ClientCompany.objects.filter(pk=self.company.pk).update(contact_email="")
        response = self.client.get(self.url, {"periodo": "2026-09"})
        self.assertNotContains(response, "mailto:")
        self.assertContains(response, "Guia de imposto")

    def test_nothing_missing_means_no_draft_text(self) -> None:
        self.deliver(self.company, self.extrato, "2026-09")
        self.deliver(self.company, self.guia, "2026-09")
        response = self.client.get(self.url, {"periodo": "2026-09"})
        self.assertNotContains(response, "mailto:")

    def test_company_of_another_office_is_a_404(self) -> None:
        other = self.make_office("e11-ck-draft-other")
        stranger = ClientCompany.objects.create(organization=other, name="Z", dominio_code="2")
        url = reverse("hub:triage-checklist-request", args=[stranger.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_company_outside_the_operators_grant_is_a_404(self) -> None:
        outside = ClientCompany.objects.create(
            organization=self.office, name="Fora", dominio_code="78"
        )
        self.login(self.operator())
        url = reverse("hub:triage-checklist-request", args=[outside.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_post_is_not_allowed(self) -> None:
        self.assertEqual(self.client.post(self.url).status_code, 405)
