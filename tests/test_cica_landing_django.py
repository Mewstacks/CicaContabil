from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.organizations.models import Membership, Organization


class CICALandingTests(TestCase):
    databases = {"default", "knowledge"}

    def test_public_page_has_trial_but_no_calculator(self):
        response = self.client.get(reverse("hub:home"))
        self.assertContains(response, "Começar teste de 14 dias")
        self.assertContains(response, "CICA significa Central de Inteligência Contábil Avançada")
        self.assertContains(response, "data-cica-demo")
        for module in (
            "NFS-e Inteligente",
            "Guias e DCTFWeb",
            "Central Integra Contador",
            "Conciliação OFX x Domínio",
            "Radar da Reforma",
            "Triagem de Arquivos",
        ):
            self.assertContains(response, module)
        self.assertNotContains(response, "Copiloto CICA")
        self.assertNotContains(response, "Franquia do Copiloto")
        self.assertNotContains(response, "quote-total")
        self.assertNotContains(response, "data-motion-toggle")
        self.assertNotContains(response, "3 escritórios")
        self.assertContains(response, "sem cobrança automática")
        self.assertNotContains(response, "NFS-e, extratos e guias chegam")

    @override_settings(
        DEMO_ENTRY_ENABLED=True,
        DEMO_SESSION_ISOLATION_READY=True,
        DEMO_ORGANIZATION_SLUG="cica-demo",
    )
    def test_public_page_links_to_labeled_demo_only_when_ready(self):
        Organization.objects.create(name="CICA Demonstração", slug="cica-demo", is_demo=True)

        response = self.client.get(reverse("hub:home"))

        self.assertContains(response, reverse("hub:demo-entry"))
        self.assertContains(response, "Explorar demo fictícia")
        self.assertContains(response, "A demonstração consulta dados reais?")

    def test_plan_simulator_requires_authenticated_workspace(self):
        response = self.client.get(reverse("hub:settings"))
        self.assertEqual(response.status_code, 302)

    def test_workspace_does_not_publish_unapproved_hardcoded_prices(self):
        user = User.objects.create_user("plan-review@example.test", "local-test-only")
        office = Organization.objects.create(name="Escritório de teste", slug="plan-review")
        Membership.objects.create(organization=office, user=user, role=Membership.Role.OWNER)
        self.client.force_login(user)
        session = self.client.session
        session["hub_organization_id"] = str(office.id)
        session.save()
        response = self.client.get(reverse("hub:settings"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Condições do escritório")
        self.assertNotContains(response, "R$ 249")
        self.assertNotContains(response, "quote-total")
