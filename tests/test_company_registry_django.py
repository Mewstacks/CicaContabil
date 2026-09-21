from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ClientCompany, DteMessage, OfficeProfile, ProductModule, ReviewCase
from apps.hub.services import create_document_and_artifact
from apps.intelligence.models import IntelligenceConnector
from apps.organizations.models import Membership, Organization
from apps.platform.models import PlatformAccess, SupportSession


class CompanyRegistryTests(TestCase):
    """An office can hold hundreds of companies; the registry has to stay usable."""

    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("registro@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Registro", slug="registro")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        OfficeProfile.objects.create(organization=self.organization, legal_name="Registro Ltda")
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.NFSE, enabled=True
        )
        self.linked = ClientCompany.objects.create(
            organization=self.organization,
            name="Padaria Vila Nova",
            cnpj_masked="12.345.678/0001-90",
            dominio_code="0101",
        )
        self.unlinked = ClientCompany.objects.create(
            organization=self.organization, name="Transportes Guaiba", dominio_code=""
        )
        self.paused = ClientCompany.objects.create(
            organization=self.organization,
            name="Clinica Parada",
            dominio_code="0103",
            active=False,
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

    def _names(self, response: object) -> set[str]:
        rows = response.context["companies"]  # type: ignore[attr-defined]
        return {company.name for company in rows}

    def test_search_matches_name_cnpj_and_dominio_code(self) -> None:
        for term, expected in (
            ("Padaria", {self.linked.name}),
            ("12.345", {self.linked.name}),
            ("0103", {self.paused.name}),
        ):
            response = self.client.get(reverse("hub:companies"), {"q": term})

            self.assertEqual(response.status_code, 200)
            self.assertEqual(self._names(response), expected, term)

    def test_the_registry_can_isolate_companies_with_a_dominio_code(self) -> None:
        linked = self.client.get(reverse("hub:companies"), {"vinculo": "com"})

        self.assertEqual(self._names(linked), {self.linked.name, self.paused.name})

    def test_the_registry_filters_by_situation(self) -> None:
        response = self.client.get(reverse("hub:companies"), {"situacao": "pausada"})

        self.assertEqual(self._names(response), {self.paused.name})

    def test_a_filter_with_no_result_offers_the_way_back(self) -> None:
        response = self.client.get(reverse("hub:companies"), {"q": "inexistente"})

        self.assertEqual(self._names(response), set())
        self.assertContains(response, "Ver todas")

    def test_the_registry_paginates_instead_of_rendering_every_row(self) -> None:
        ClientCompany.objects.bulk_create(
            [
                ClientCompany(
                    organization=self.organization, name=f"Empresa {index:03d}", dominio_code=""
                )
                for index in range(60)
            ]
        )

        response = self.client.get(reverse("hub:companies"))

        page = response.context["page_obj"]
        self.assertEqual(page.number, 1)
        self.assertEqual(len(page.object_list), 25)
        self.assertEqual(response.context["total_companies"], 63)
        self.assertTrue(page.has_next())

    def test_the_registry_never_shows_another_office(self) -> None:
        other = Organization.objects.create(name="Outro", slug="outro-registro")
        ClientCompany.objects.create(organization=other, name="Empresa Alheia")

        response = self.client.get(reverse("hub:companies"), {"q": "Alheia"})

        self.assertEqual(self._names(response), set())

    def test_a_dominio_connected_office_cannot_add_companies_manually(self) -> None:
        for mode in IntelligenceConnector.Mode.values:
            with self.subTest(mode=mode):
                IntelligenceConnector.objects.filter(organization=self.organization).delete()
                IntelligenceConnector.objects.create(
                    organization=self.organization,
                    mode=mode,
                    status="healthy",
                )

                page = self.client.get(reverse("hub:companies"))
                response = self.client.post(
                    reverse("hub:companies"),
                    {"name": "Cadastro manual", "cnpj_masked": "", "dominio_code": ""},
                )

                self.assertNotContains(page, "Adicionar empresa")
                self.assertContains(page, "Domínio")
                self.assertEqual(response.status_code, 403)
                self.assertFalse(ClientCompany.objects.filter(name="Cadastro manual").exists())


class DominioCodePolicyTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("politica@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Politica", slug="politica")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        self.profile = OfficeProfile.objects.create(organization=self.organization)
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.NFSE, enabled=True
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

    def test_the_code_is_optional_until_the_office_demands_it(self) -> None:
        response = self.client.post(
            reverse("hub:companies"), {"name": "Sem codigo", "cnpj_masked": "", "dominio_code": ""}
        )

        self.assertRedirects(response, reverse("hub:companies"))
        self.assertTrue(ClientCompany.objects.filter(name="Sem codigo").exists())

    def test_when_demanded_a_company_cannot_be_registered_without_the_code(self) -> None:
        self.profile.require_dominio_code = True
        self.profile.save(update_fields=["require_dominio_code"])

        response = self.client.post(
            reverse("hub:companies"), {"name": "Sem codigo", "cnpj_masked": "", "dominio_code": ""}
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Este escritório exige o código do Domínio.")
        self.assertFalse(ClientCompany.objects.filter(name="Sem codigo").exists())

    def test_two_companies_in_one_office_cannot_share_a_code(self) -> None:
        ClientCompany.objects.create(
            organization=self.organization, name="Primeira", dominio_code="0101"
        )

        response = self.client.post(
            reverse("hub:companies"),
            {"name": "Segunda", "cnpj_masked": "", "dominio_code": "0101"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Outra empresa já usa este código.")
        self.assertFalse(ClientCompany.objects.filter(name="Segunda").exists())

    def test_the_same_code_may_exist_in_a_different_office(self) -> None:
        other = Organization.objects.create(name="Outro", slug="outro-politica")
        ClientCompany.objects.create(organization=other, name="Alheia", dominio_code="0101")

        response = self.client.post(
            reverse("hub:companies"),
            {"name": "Minha", "cnpj_masked": "", "dominio_code": "0101"},
        )

        self.assertRedirects(response, reverse("hub:companies"))
        self.assertTrue(
            ClientCompany.objects.filter(organization=self.organization, name="Minha").exists()
        )

    def test_an_owner_turns_the_requirement_on_from_the_settings_screen(self) -> None:
        response = self.client.post(
            reverse("hub:settings"),
            {"action": "dominio-policy", "require_dominio_code": "on"},
        )

        self.assertRedirects(response, reverse("hub:settings"))
        self.profile.refresh_from_db()
        self.assertTrue(self.profile.require_dominio_code)

    def test_an_operator_cannot_change_the_office_policy(self) -> None:
        Membership.objects.filter(organization=self.organization, user=self.user).update(
            role=Membership.Role.OPERATOR
        )

        response = self.client.post(
            reverse("hub:settings"),
            {"action": "dominio-policy", "require_dominio_code": "on"},
        )

        self.assertEqual(response.status_code, 403)
        self.profile.refresh_from_db()
        self.assertFalse(self.profile.require_dominio_code)


class CompanyDetailTests(TestCase):
    """One company is a page you open, not a global mode you enter."""

    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("detalhe@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Detalhe", slug="detalhe")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        OfficeProfile.objects.create(organization=self.organization)
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.NFSE, enabled=True
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa Detalhe", dominio_code="0101"
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

    def test_the_registry_links_straight_to_the_company_page(self) -> None:
        response = self.client.get(reverse("hub:companies"))

        self.assertContains(response, reverse("hub:company-detail", args=[self.company.id]))

    def test_the_company_page_shows_the_identity_and_honest_empty_states(self) -> None:
        response = self.client.get(reverse("hub:company-detail", args=[self.company.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["company"], self.company)
        self.assertContains(response, "0101")
        self.assertContains(response, "Nenhuma NFS-e desta empresa")
        self.assertContains(response, "Sem certificado A1")

    def test_the_company_page_paginates_each_history_without_losing_the_others(self) -> None:
        for index in range(21):
            document, _, review_case = create_document_and_artifact(
                company=self.company,
                original_xml=f"<nfse id='detail-{index:03d}' />",
                normalized_data={},
                source_nsu=f"document-{index:03d}",
            )
            if review_case is None:
                ReviewCase.objects.create(
                    organization=self.organization,
                    document=document,
                    reason="Revisão sintética para paginação",
                    confidence=0,
                )
            DteMessage.objects.create(
                organization=self.organization,
                company=self.company,
                source_isn=f"detail-dte-{index:03d}",
                subject=f"Mensagem DTE {index:03d}",
                sent_at=timezone.now() - timedelta(minutes=index),
            )

        first_page = self.client.get(reverse("hub:company-detail", args=[self.company.id]))
        second_page = self.client.get(
            reverse("hub:company-detail", args=[self.company.id]),
            {
                "documents_page": "2",
                "reviews_page": "2",
                "dte_page": "2",
                "return_to": "/app/empresas/?q=Detalhe",
            },
        )

        self.assertEqual(first_page.context["document_count"], 21)
        self.assertEqual(first_page.context["open_cases_count"], 21)
        self.assertEqual(first_page.context["dte_messages_count"], 21)
        self.assertEqual(first_page.context["document_page"].number, 1)
        self.assertEqual(first_page.context["open_cases_page"].number, 1)
        self.assertEqual(first_page.context["dte_messages_page"].number, 1)
        self.assertEqual(second_page.context["document_page"].number, 2)
        self.assertEqual(second_page.context["open_cases_page"].number, 2)
        self.assertEqual(second_page.context["dte_messages_page"].number, 2)
        self.assertEqual(
            [document.source_nsu for document in second_page.context["documents"]],
            ["document-000"],
        )
        self.assertEqual(
            [message.subject for message in second_page.context["dte_messages"]],
            ["Mensagem DTE 020"],
        )
        self.assertEqual(
            second_page.context["document_querystring"],
            "reviews_page=2&dte_page=2&return_to=%2Fapp%2Fempresas%2F%3Fq%3DDetalhe",
        )
        self.assertContains(second_page, "Página 2 de 2")
        self.assertContains(
            second_page,
            "documents_page=1#documentos-nfse",
            html=False,
        )
        self.assertContains(second_page, "reviews_page=1#revisoes-abertas", html=False)
        self.assertContains(second_page, "dte_page=1#caixa-dte", html=False)

    def test_a_company_from_another_office_is_not_found(self) -> None:
        other = Organization.objects.create(name="Outro", slug="outro-detalhe")
        alien = ClientCompany.objects.create(organization=other, name="Empresa Alheia")

        response = self.client.get(reverse("hub:company-detail", args=[alien.id]))

        self.assertEqual(response.status_code, 404)


class SupportSessionOnOwnOfficeTests(TestCase):
    """A platform operator who belongs to the office is not a visitor to it."""

    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("duplo@example.test", "safe-password-123")
        PlatformAccess.objects.create(
            user=self.user, role=PlatformAccess.Role.DEVELOPER, mfa_required=False
        )
        self.organization = Organization.objects.create(name="Proprio", slug="proprio")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        OfficeProfile.objects.create(organization=self.organization)
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.NFSE, enabled=True
        )
        ClientCompany.objects.create(organization=self.organization, name="Empresa Propria")
        self.client.force_login(self.user)

    def test_opening_a_support_session_on_your_own_office_is_refused(self) -> None:
        response = self.client.post(
            reverse("platform:start-support", args=[self.organization.id]),
            {"justification": "Motivo suficientemente longo"},
            follow=True,
        )

        self.assertContains(response, "Você já faz parte deste escritório")
        self.assertFalse(SupportSession.objects.filter(organization=self.organization).exists())

    def test_a_stale_support_session_never_masks_your_own_membership(self) -> None:
        support = SupportSession.objects.create(
            organization=self.organization,
            support_user=self.user,
            justification="Sessao antiga desta instalacao",
            access_mode=SupportSession.AccessMode.READ_ONLY,
            expires_at=timezone.now() + timedelta(minutes=30),
        )
        session = self.client.session
        session["hub_support_session_id"] = str(support.id)
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

        response = self.client.get(reverse("hub:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.context["support_session"])
        self.assertIsNotNone(response.context["membership"])
        # Read-only would have removed every action from the page.
        self.assertTrue(response.context["support_can_mutate"])
