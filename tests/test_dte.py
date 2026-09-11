from django.test import TestCase
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany, Connector, DteRun, DteRunItem, ProductModule
from apps.organizations.models import Membership, Organization


class DteCenterTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("dte@example.test", "safe-password-123")
        self.organization = Organization.objects.create(
            name="Escrit\u00f3rio DTE", slug="escritorio-dte"
        )
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OPERATOR
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa DTE", cnpj_masked="12.345.678/0001-90"
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
        self.assertContains(response, "Consulte as mensagens das empresas sem planilhas")
        self.assertContains(response, self.company.name)
        self.assertNotContains(response, "ClientCompany object")

        prepared = self.client.post(reverse("hub:dte-center"), {"companies": [self.company.id]})

        self.assertRedirects(prepared, reverse("hub:dte-center"))
        run = DteRun.objects.get(organization=self.organization)
        self.assertEqual(run.status, DteRun.Status.AWAITING_APPROVAL)
        self.assertEqual(run.total_companies, 1)
        self.assertTrue(DteRunItem.objects.filter(run=run, company=self.company).exists())

    def test_dte_scope_does_not_accept_a_company_from_another_office(self) -> None:
        another_office = Organization.objects.create(name="Outro", slug="outro-dte")
        other_company = ClientCompany.objects.create(
            organization=another_office, name="N\u00e3o permitida"
        )

        response = self.client.post(reverse("hub:dte-center"), {"companies": [other_company.id]})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A empresa selecionada n\u00e3o est\u00e1 no seu escopo")
        self.assertFalse(DteRun.objects.filter(organization=self.organization).exists())
