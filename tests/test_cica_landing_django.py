from django.test import TestCase, override_settings
from django.urls import reverse

from apps.accounts.models import User
from apps.organizations.models import Membership, Organization


class CICALandingTests(TestCase):
    databases = {"default", "knowledge"}

    def test_public_page_has_trial_but_no_calculator(self):
        response = self.client.get(reverse("hub:home"))
        self.assertContains(response, "Começar teste de 14 dias")
        self.assertContains(response, "Feche o mês sem caçar informação.")
        self.assertContains(response, "O trabalho aparece antes de virar urgência.")
        self.assertContains(
            response,
            "Exemplo ilustrativo com empresas, pessoas e atividades fictícias.",
        )
        self.assertContains(response, "Nenhum dado real é consultado nesta tela.")
        self.assertContains(response, "A equipe entra e já sabe onde continuar.")
        self.assertContains(response, "As fontes já trabalham dentro da mesma rotina.")
        self.assertContains(response, "Domínio, Integra Contador, e-mail e Siescon")
        self.assertNotContains(response, "Cada pessoa começa pelo que é dela.")
        self.assertNotContains(response, "Disponível por configuração")
        self.assertNotContains(response, "Em preparação")
        self.assertNotContains(response, reverse("hub:demo-entry"))
        self.assertNotContains(response, "A demonstração consulta dados reais?")
        for module in (
            "NFS-e Inteligente",
            "Guias e DCTFWeb",
            "Central Integra Contador",
            "Conciliação entre extrato OFX e registros do Domínio.",
            "Radar da Reforma",
            "Triagem por empresa, competência e origem do anexo.",
        ):
            self.assertContains(response, module)
        self.assertNotContains(response, "Copiloto CICA")
        self.assertNotContains(response, "Franquia do Copiloto")
        self.assertNotContains(response, "quote-total")
        self.assertNotContains(response, "cica-scene.js")
        self.assertNotContains(response, "data-motion-toggle")
        self.assertNotContains(response, "3 escritórios")
        self.assertContains(response, "sem cobrança automática")
        self.assertNotContains(response, "NFS-e, extratos e guias chegam")
        self.assertContains(response, 'data-product-demo')
        self.assertContains(response, 'data-demo-target="central"')
        self.assertContains(response, 'data-demo-target="trabalho"')
        self.assertContains(response, 'data-demo-target="empresas"')
        self.assertContains(response, 'data-demo-target="documentos"')
        self.assertContains(response, 'data-demo-target="fiscal"')
        self.assertContains(response, 'data-demo-target="conciliacao"')
        self.assertContains(response, 'cica-product-demo.js')

    @override_settings(
        DEMO_ENTRY_ENABLED=True,
        DEMO_SESSION_ISOLATION_READY=True,
        DEMO_ORGANIZATION_SLUG="cica-demo",
    )
    def test_public_page_links_to_labeled_demo_only_when_ready(self):
        Organization.objects.create(name="CICA Demonstração", slug="cica-demo", is_demo=True)

        response = self.client.get(reverse("hub:home"))

        self.assertContains(response, reverse("hub:demo-entry"))
        self.assertContains(response, "Explorar a demonstração completa")
        self.assertContains(response, "A demonstração consulta dados reais?")
        self.assertContains(response, "não realiza operações em fontes externas.")

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
