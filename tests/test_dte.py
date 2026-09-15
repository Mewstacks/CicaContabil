from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany, Connector, DteMessage, DteRun, DteRunItem, ProductModule
from apps.organizations.models import Membership, Organization


class DteCenterTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("dte@example.test", "safe-password-123")
        self.organization = Organization.objects.create(
            name="Escrit\u00f3rio DTE", slug="escritorio-dte"
        )
        self.membership = Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OPERATOR
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa DTE", cnpj_masked="12.345.678/0001-95"
        )
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.INTEGRA, enabled=True
        )
        Connector.objects.create(
            organization=self.organization,
            kind=Connector.Kind.INTEGRA,
            enabled=True,
            status="configured",
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

    def test_dte_screen_prepares_a_local_run_without_dispatching_a_request(self) -> None:
        response = self.client.get(reverse("hub:dte-center"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Caixa Postal e consultas fiscais no mesmo trabalho")
        self.assertContains(response, self.company.name)
        self.assertNotContains(response, "ClientCompany object")
        self.assertContains(response, "Conexão Serpro indisponível")
        self.assertNotContains(response, "Central CICA ativa")

        prepared = self.client.post(reverse("hub:dte-center"), {"companies": [self.company.id]})

        self.assertRedirects(prepared, reverse("hub:dte-center"))
        run = DteRun.objects.get(organization=self.organization)
        self.assertEqual(run.status, DteRun.Status.AWAITING_APPROVAL)
        self.assertEqual(run.total_companies, 1)
        self.assertTrue(DteRunItem.objects.filter(run=run, company=self.company).exists())

        refused = self.client.post(
            reverse("hub:decide-dte-run", args=[run.id]), {"decision": "approve"}, follow=True
        )
        self.assertRedirects(refused, reverse("hub:dte-center"))
        self.assertContains(refused, "A conexão central Serpro ainda não está configurada")
        run.refresh_from_db()
        self.assertEqual(run.status, DteRun.Status.AWAITING_APPROVAL)

    def test_dte_scope_does_not_accept_a_company_from_another_office(self) -> None:
        another_office = Organization.objects.create(name="Outro", slug="outro-dte")
        other_company = ClientCompany.objects.create(
            organization=another_office, name="N\u00e3o permitida"
        )

        response = self.client.post(reverse("hub:dte-center"), {"companies": [other_company.id]})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A empresa selecionada n\u00e3o est\u00e1 no seu escopo")
        self.assertFalse(DteRun.objects.filter(organization=self.organization).exists())

    def test_company_without_valid_cnpj_is_excluded_before_paid_preparation(self) -> None:
        missing = ClientCompany.objects.create(
            organization=self.organization, name="Empresa sem CNPJ", cnpj_masked=""
        )

        screen = self.client.get(reverse("hub:dte-center"))
        self.assertEqual(screen.context["dte_companies_count"], 1)
        self.assertEqual(screen.context["dte_scope_count"], 2)
        self.assertContains(screen, "Revise o cadastro das empresas")

        submitted = self.client.post(reverse("hub:dte-center"), {"companies": [missing.id]})
        self.assertEqual(submitted.status_code, 200)
        self.assertFalse(DteRun.objects.filter(organization=self.organization).exists())

    def test_all_companies_without_valid_cnpj_get_a_specific_empty_state(self) -> None:
        self.company.cnpj_masked = ""
        self.company.save(update_fields=["cnpj_masked"])

        screen = self.client.get(reverse("hub:dte-center"))

        self.assertEqual(screen.context["dte_companies_count"], 0)
        self.assertContains(screen, "Nenhuma empresa deste escopo tem CNPJ")
        self.assertContains(screen, "Revisar empresas")

    def test_message_summary_never_calls_provider_and_operator_cannot_acknowledge_by_default(
        self,
    ) -> None:
        message = DteMessage.objects.create(
            organization=self.organization,
            company=self.company,
            source_isn="0000082838",
            subject="Intimação de teste",
        )

        summary = self.client.get(reverse("hub:dte-message-detail", args=[message.id]))
        refused = self.client.post(
            reverse("hub:dte-message-detail", args=[message.id]),
            {"confirm_legal_notice": "on"},
        )

        self.assertEqual(summary.status_code, 200)
        self.assertContains(summary, "Teor ainda não consultado")
        self.assertNotContains(summary, "<form class=\"dte-legal-form\"")
        self.assertEqual(refused.status_code, 403)

    def test_operator_with_explicit_science_permission_reaches_configuration_gate(self) -> None:
        self.membership.can_acknowledge_dte = True
        self.membership.save(update_fields=["can_acknowledge_dte"])
        message = DteMessage.objects.create(
            organization=self.organization,
            company=self.company,
            source_isn="0000082840",
            subject="Mensagem com ciência controlada",
        )

        response = self.client.post(
            reverse("hub:dte-message-detail", args=[message.id]),
            {"confirm_legal_notice": "on"},
            follow=True,
        )

        self.assertRedirects(response, reverse("hub:dte-message-detail", args=[message.id]))
        self.assertContains(response, "A conexão central Serpro ainda não está configurada")

        self.membership.role = Membership.Role.MANAGER
        self.membership.save(update_fields=["role"])
        refused = self.client.post(
            reverse("hub:dte-message-detail", args=[message.id]),
            {"confirm_legal_notice": "on"},
        )
        self.assertEqual(refused.status_code, 403)
