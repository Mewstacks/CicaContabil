from __future__ import annotations

from datetime import timedelta

from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ClientCompany, Connector, ControlPlaneBinding, ProductModule, ReviewCase
from apps.hub.services import create_document_and_artifact
from apps.organizations.models import Membership, Organization
from apps.platform.models import PlatformAccess
from conftest import complete_mfa


class HubWorkspaceViewTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("owner@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa Acme", dominio_code="001"
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

    def test_the_workspace_opens_on_the_whole_portfolio_not_one_arbitrary_company(
        self,
    ) -> None:
        """An office works across its clients; nothing is pinned until somebody picks."""

        endpoints = [
            "hub:dashboard",
            "hub:nfse-center",
            "hub:companies",
            "hub:certificates",
            "hub:reviews",
            "hub:settings",
        ]

        for endpoint in endpoints:
            response = self.client.get(reverse(endpoint))
            self.assertEqual(response.status_code, 200, endpoint)
            self.assertIsNone(response.context["active_company"], endpoint)

        self.assertNotIn("hub_company_id", self.client.session)

    def test_choosing_a_company_pins_it_and_clearing_returns_to_the_portfolio(self) -> None:
        chosen = self.client.post(
            reverse("hub:switch-company"), {"company_id": str(self.company.id)}
        )

        self.assertRedirects(chosen, reverse("hub:dashboard"))
        self.assertEqual(self.client.session["hub_company_id"], str(self.company.id))

        cleared = self.client.post(reverse("hub:switch-company"), {"company_id": ""})

        self.assertRedirects(cleared, reverse("hub:dashboard"))
        self.assertNotIn("hub_company_id", self.client.session)

    def test_companies_page_identifies_the_active_office(self) -> None:
        response = self.client.get(reverse("hub:companies"))

        self.assertContains(response, self.organization.name)
        self.assertContains(response, self.company.name)

    def test_enabled_product_modules_have_company_scoped_screens(self) -> None:
        for code in (
            ProductModule.Code.GUIDES,
            ProductModule.Code.INTEGRA,
            ProductModule.Code.RECONCILIATION,
            ProductModule.Code.REFORM,
        ):
            ProductModule.objects.create(organization=self.organization, code=code, enabled=True)

        for endpoint, heading in (
            ("hub:guides", "Guias e DCTFWeb"),
            ("hub:reconciliation", "Conciliação OFX x Domínio"),
            ("hub:reform", "Radar da Reforma Tributária"),
        ):
            response = self.client.get(reverse(endpoint))
            self.assertEqual(response.status_code, 200, endpoint)
            self.assertContains(response, heading)
            self.assertContains(response, self.company.name)

        integra = self.client.get(reverse("hub:integra"))
        self.assertRedirects(integra, reverse("hub:dte-center"))

        nav = self.client.get(reverse("hub:dashboard"))
        self.assertContains(nav, reverse("hub:guides"))
        self.assertContains(nav, reverse("hub:integra"))

    def test_disabled_product_module_is_not_available(self) -> None:
        ProductModule.objects.create(
            organization=self.organization,
            code=ProductModule.Code.RECONCILIATION,
            enabled=False,
        )
        response = self.client.get(reverse("hub:reconciliation"))
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "não está habilitado", status_code=403)
        self.assertNotContains(
            self.client.get(reverse("hub:dashboard")), reverse("hub:reconciliation")
        )

    def test_external_connector_setup_is_encrypted_and_audited(self) -> None:
        response = self.client.post(
            reverse("hub:settings"),
            {
                "kind": Connector.Kind.INTEGRA,
                "label": "Domínio QA",
                "endpoint": "",
                "database_alias": "DOMINIO_QA",
                "secret": "local-secret",
            },
        )
        self.assertRedirects(response, reverse("hub:settings"))
        connector = Connector.objects.get(
            organization=self.organization, kind=Connector.Kind.INTEGRA
        )
        self.assertTrue(connector.enabled)
        self.assertEqual(connector.status, "configured")
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT encrypted_configuration FROM hub_connector WHERE id = %s",
                [connector._meta.pk.get_db_prep_value(connector.id, connection=connection)],
            )
            stored_value = cursor.fetchone()[0]
        self.assertNotIn("local-secret", stored_value)
        self.assertTrue(stored_value.startswith("enc:v1:"))

    def test_dominio_is_not_configured_through_the_generic_connector_form(self) -> None:
        response = self.client.post(
            reverse("hub:settings"),
            {"kind": Connector.Kind.DOMINIO_AGENT, "label": "Domínio", "secret": "x"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Configurações avançadas")
        self.assertFalse(
            Connector.objects.filter(
                organization=self.organization, kind=Connector.Kind.DOMINIO_AGENT
            ).exists()
        )

    def test_settings_survives_a_legacy_connector_with_an_unavailable_key(self) -> None:
        connector = Connector.objects.create(
            organization=self.organization,
            kind=Connector.Kind.INTEGRA,
            enabled=True,
            status="configured",
            encrypted_configuration="initial configuration",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "UPDATE hub_connector SET encrypted_configuration = %s WHERE id = %s",
                [
                    "enc:v1:test-v1:AAAAAAAAAAAAAAAA:AAAAAAAAAAAAAAAAAAAAAA==",
                    connector._meta.pk.get_db_prep_value(connector.id, connection=connection),
                ],
            )

        response = self.client.get(reverse("hub:settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Integra")

    def test_nfse_center_is_scoped_to_the_active_company(self) -> None:
        other_company = ClientCompany.objects.create(
            organization=self.organization, name="Outra empresa", dominio_code="002"
        )
        create_document_and_artifact(
            company=self.company,
            original_xml="<nfse id='owned' />",
            normalized_data={},
            source_nsu="owned",
        )
        create_document_and_artifact(
            company=other_company,
            original_xml="<nfse id='other' />",
            normalized_data={},
            source_nsu="other",
        )

        self.client.post(reverse("hub:switch-company"), {"company_id": str(self.company.id)})

        response = self.client.get(reverse("hub:nfse-center"))

        self.assertContains(response, "Central NFS-e")
        self.assertContains(response, "owned")
        self.assertNotContains(response, "other")

    def test_nfse_center_shows_the_whole_portfolio_when_no_company_is_chosen(self) -> None:
        other_company = ClientCompany.objects.create(
            organization=self.organization, name="Outra empresa", dominio_code="002"
        )
        create_document_and_artifact(
            company=self.company,
            original_xml="<nfse id='owned' />",
            normalized_data={},
            source_nsu="owned",
        )
        create_document_and_artifact(
            company=other_company,
            original_xml="<nfse id='other' />",
            normalized_data={},
            source_nsu="other",
        )

        response = self.client.get(reverse("hub:nfse-center"))

        self.assertContains(response, "owned")
        self.assertContains(response, "other")

    def test_logout_uses_post_and_ends_the_workspace_session(self) -> None:
        response = self.client.post(reverse("hub:logout"))

        self.assertRedirects(response, reverse("hub:home"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_platform_user_gets_a_return_link_in_the_account_menu(self) -> None:
        PlatformAccess.objects.create(user=self.user, role=PlatformAccess.Role.DEVELOPER)
        complete_mfa(self.client)

        response = self.client.get(reverse("hub:dashboard"))

        self.assertContains(response, reverse("platform:dashboard"))
        self.assertContains(response, "Voltar à plataforma")

    def test_company_and_office_switches_are_scoped_to_active_membership(self) -> None:
        second_company = ClientCompany.objects.create(
            organization=self.organization, name="Outra empresa", dominio_code="002"
        )
        other_organization = Organization.objects.create(name="Outra", slug="outra")
        Membership.objects.create(
            organization=other_organization, user=self.user, role=Membership.Role.MANAGER
        )

        company_response = self.client.post(
            reverse("hub:switch-company"), {"company_id": str(second_company.id)}
        )
        office_response = self.client.post(
            reverse("hub:switch-office"), {"organization_id": str(other_organization.id)}
        )

        self.assertRedirects(company_response, reverse("hub:dashboard"))
        self.assertRedirects(office_response, reverse("hub:dashboard"))
        self.assertEqual(self.client.session["hub_organization_id"], str(other_organization.id))
        self.assertNotIn("hub_company_id", self.client.session)

    def test_company_creation_is_available_only_to_unmanaged_installations(self) -> None:
        response = self.client.post(
            reverse("hub:companies"), {"name": "Criada no Hub", "dominio_code": "003"}
        )
        self.assertRedirects(response, reverse("hub:companies"))
        self.assertTrue(
            ClientCompany.objects.filter(
                organization=self.organization, dominio_code="003"
            ).exists()
        )

        ControlPlaneBinding.objects.create(
            organization=self.organization,
            remote_installation_id="5b3dd36b-4da4-4b7a-9f12-8e933c2ed0e4",
            controller_url="https://crmew.example.test",
            device_private_key="local-key",
            controller_public_key="controller-key",
            cache_expires_at=timezone.now() + timedelta(minutes=10),
        )
        blocked = self.client.post(
            reverse("hub:companies"), {"name": "Nunca criada", "dominio_code": "004"}
        )
        self.assertEqual(blocked.status_code, 403)
        self.assertFalse(
            ClientCompany.objects.filter(
                organization=self.organization, dominio_code="004"
            ).exists()
        )

    def test_review_resolution_requires_an_accumulator_and_records_a_human_decision(self) -> None:
        document, _artifact, review = create_document_and_artifact(
            company=self.company,
            original_xml="<nfse id='pending' />",
            normalized_data={"service_code": "unmatched"},
        )
        self.assertIsNotNone(document)
        assert review is not None
        url = reverse("hub:resolve-review", args=[review.id])

        missing = self.client.post(url, {})
        resolved = self.client.post(url, {"accumulator_code": "AC-200"})

        self.assertRedirects(missing, reverse("hub:reviews"))
        self.assertRedirects(resolved, reverse("hub:reviews"))
        review.refresh_from_db()
        self.assertEqual(review.status, ReviewCase.Status.RESOLVED)
        self.assertEqual(review.resolved_accumulator, "AC-200")
        self.assertEqual(review.resolved_by, self.user)

    def test_unknown_company_switch_and_anonymous_workspace_are_blocked(self) -> None:
        unknown = self.client.post(reverse("hub:switch-company"), {"company_id": "not-an-id"})
        self.assertEqual(unknown.status_code, 403)

        self.client.logout()
        anonymous = self.client.get(reverse("hub:dashboard"))
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn(reverse("hub:login"), anonymous["Location"])
