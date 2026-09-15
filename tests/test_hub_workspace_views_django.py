from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.controlplane import company_queryset_for_membership, module_codes_for_membership
from apps.hub.models import (
    ClientCompany,
    ClientJourney,
    CompanyAccessGrant,
    Connector,
    ControlPlaneBinding,
    JourneyStep,
    PortalRequest,
    ProductModule,
    ReformAlert,
    ReviewCase,
)
from apps.hub.services import create_document_and_artifact
from apps.intelligence.models import EdgeAgent, IntelligenceConnector
from apps.organizations.models import Membership, Organization
from apps.platform.models import (
    DominioSupportTicket,
    Invitation,
    Plan,
    PlanServiceRate,
    PlatformAccess,
    SupportSession,
    TenantContract,
    TenantUsagePolicy,
)
from apps.platform.notifications import TransactionalEmailError
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
            self.assertNotIn("active_company", response.context, endpoint)

    def test_support_session_keeps_the_target_office_enabled_modules_in_navigation(self) -> None:
        """Support is tenant-scoped, but is not a collaborator with module grants."""

        ProductModule.objects.create(
            organization=self.organization,
            code=ProductModule.Code.NFSE,
            enabled=True,
        )
        support_user = User.objects.create_user("support@example.test", "safe-password-123")
        support = SupportSession.objects.create(
            organization=self.organization,
            support_user=support_user,
            justification="Verificação autorizada da configuração fiscal.",
            expires_at=timezone.now() + timedelta(minutes=20),
        )
        self.client.force_login(support_user)
        session = self.client.session
        session["hub_support_session_id"] = str(support.id)
        session.save()

        response = self.client.get(reverse("hub:certificates"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "NFS-e")
        self.assertContains(response, reverse("hub:nfse-center"))

    def test_companies_page_identifies_the_active_office(self) -> None:
        response = self.client.get(reverse("hub:companies"))

        self.assertContains(response, self.organization.name)
        self.assertContains(response, self.company.name)

    def test_nfse_empty_states_do_not_claim_that_a_certificate_activates_capture(self) -> None:
        """A stored A1 is not a substitute for an unimplemented external NFS-e connector."""

        certificates = self.client.get(reverse("hub:certificates"))
        company = self.client.get(reverse("hub:company-detail", args=[self.company.id]))

        self.assertContains(certificates, "conexão homologada")
        self.assertNotContains(certificates, "ativar a consulta de NFS-e")
        self.assertContains(company, "conexão NFS-e desta empresa ser homologada")
        self.assertNotContains(company, "certificado não há consulta de NFS-e nem DTE")

    def test_reform_radar_filters_official_alerts_without_an_extra_page(self) -> None:
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.REFORM, enabled=True
        )
        ReformAlert.objects.create(
            source=ReformAlert.Source.RFB,
            external_key="rfb-1",
            title="Cronograma IBS",
            source_url="https://www.gov.br/receitafederal/noticia",
            relevance=ReformAlert.Relevance.REFORM,
            content_hash="hash-1",
        )
        ReformAlert.objects.create(
            source=ReformAlert.Source.FAZENDA,
            external_key="fazenda-1",
            title="Nota econômica",
            source_url="https://www.gov.br/fazenda/noticia",
            content_hash="hash-2",
        )

        response = self.client.get(reverse("hub:reform"), {"fonte": "rfb"})

        self.assertContains(response, "Cronograma IBS")
        self.assertNotContains(response, "Nota econômica")
        self.assertContains(response, "data-auto-filter")

    def test_account_menu_persists_an_explicit_theme_choice(self) -> None:
        response = self.client.post(
            reverse("hub:set-theme"), {"theme": "dark", "next": reverse("hub:companies")}
        )

        self.assertRedirects(response, reverse("hub:companies"))
        self.assertEqual(response.cookies["hub_theme"].value, "dark")
        page = self.client.get(reverse("hub:companies"))
        self.assertContains(page, 'data-theme="dark"')
        self.assertContains(page, 'aria-pressed="true"')

    def test_account_menu_rejects_an_unknown_theme_choice(self) -> None:
        response = self.client.post(reverse("hub:set-theme"), {"theme": "rainbow"})

        self.assertEqual(response.status_code, 400)

    def test_journey_workboard_creates_and_updates_items_with_audit_scope(self) -> None:
        ProductModule.objects.create(
            organization=self.organization,
            code=ProductModule.Code.JOURNEY,
            enabled=True,
        )
        journey = ClientJourney.objects.create(
            organization=self.organization,
            company=self.company,
            title="Entrada fiscal",
            owner=self.user,
        )
        create_step = self.client.post(
            reverse("hub:journey-step-create"),
            {
                "journey_id": journey.id,
                "step-title": "Conferir documentos",
            },
        )
        self.assertRedirects(create_step, f"{reverse('hub:journey')}?j={journey.id}")
        step = JourneyStep.objects.get(journey=journey)
        self.assertEqual(step.organization, self.organization)
        self.assertEqual(step.position, 1)

        complete = self.client.post(
            reverse("hub:journey-step-complete"),
            {"journey_id": journey.id, "item_id": step.id},
        )
        self.assertEqual(complete.status_code, 302)
        step.refresh_from_db()
        self.assertIsNotNone(step.completed_at)

        create_request = self.client.post(
            reverse("hub:portal-request-create"),
            {
                "journey_id": journey.id,
                "request-title": "Extrato bancário",
            },
        )
        self.assertEqual(create_request.status_code, 302)
        request_item = PortalRequest.objects.get(journey=journey)
        transition = self.client.post(
            reverse("hub:portal-request-transition"),
            {"journey_id": journey.id, "item_id": request_item.id, "action": "resolve"},
        )
        self.assertEqual(transition.status_code, 302)
        request_item.refresh_from_db()
        self.assertEqual(request_item.status, PortalRequest.Status.RESOLVED)
        self.assertIsNotNone(request_item.resolved_at)

    def test_journey_creation_assigns_its_office_before_model_validation(self) -> None:
        ProductModule.objects.create(
            organization=self.organization,
            code=ProductModule.Code.JOURNEY,
            enabled=True,
        )
        response = self.client.post(
            reverse("hub:journey"),
            {"company": self.company.id, "title": "Onboarding fiscal"},
        )

        self.assertEqual(response.status_code, 302)
        journey = ClientJourney.objects.get(organization=self.organization)
        self.assertEqual(journey.company, self.company)
        self.assertEqual(journey.owner, self.user)

    def test_journey_mutations_cannot_cross_the_active_office_boundary(self) -> None:
        ProductModule.objects.create(
            organization=self.organization,
            code=ProductModule.Code.JOURNEY,
            enabled=True,
        )
        other = Organization.objects.create(name="Outro escritório", slug="outro-escritorio")
        other_company = ClientCompany.objects.create(
            organization=other, name="Empresa externa", dominio_code="OUT-1"
        )
        other_journey = ClientJourney.objects.create(
            organization=other, company=other_company, title="Fora do escopo"
        )

        response = self.client.post(
            reverse("hub:journey-step-create"),
            {"journey_id": other_journey.id, "step-title": "Não pode criar"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertFalse(JourneyStep.objects.filter(journey=other_journey).exists())

    @patch("apps.hub.views.send_invitation_email")
    def test_owner_invites_a_collaborator_with_company_and_module_scope(self, send_email) -> None:
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.JOURNEY, enabled=True
        )
        response = self.client.post(
            reverse("hub:team"),
            {
                "full_name": "Ana Fiscal",
                "email": "ana@example.test",
                "role": Membership.Role.OPERATOR,
                "modules": [ProductModule.Code.NFSE, ProductModule.Code.JOURNEY],
                "companies": [str(self.company.id)],
            },
        )

        self.assertRedirects(response, reverse("hub:team"))
        invitation = Invitation.objects.get(email="ana@example.test")
        self.assertEqual(invitation.company_ids, [str(self.company.id)])
        self.assertEqual(
            set(invitation.modules), {ProductModule.Code.NFSE, ProductModule.Code.JOURNEY}
        )
        send_email.assert_called_once()

    @patch(
        "apps.hub.views.send_invitation_email",
        side_effect=TransactionalEmailError("offline"),
    )
    def test_invitation_is_not_created_when_delivery_fails(self, _send_email) -> None:
        response = self.client.post(
            reverse("hub:team"),
            {
                "full_name": "Ana Fiscal",
                "email": "ana@example.test",
                "role": Membership.Role.OPERATOR,
                "modules": [ProductModule.Code.NFSE],
                "companies": [str(self.company.id)],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Não foi possível enviar o convite")
        self.assertFalse(Invitation.objects.filter(email="ana@example.test").exists())

    @patch("apps.hub.views.send_invitation_email")
    def test_owner_can_resend_a_pending_collaborator_invitation(self, send_email) -> None:
        token, digest = Invitation.issue_token()
        invitation = Invitation.objects.create(
            organization=self.organization,
            email="ana@example.test",
            role=Membership.Role.OPERATOR,
            company_ids=[str(self.company.id)],
            modules=[ProductModule.Code.NFSE],
            token_digest=digest,
            expires_at=timezone.now() - timedelta(hours=1),
        )

        response = self.client.post(
            reverse("hub:collaborator-invitation-resend", args=[invitation.id])
        )

        self.assertRedirects(response, reverse("hub:team"))
        invitation.refresh_from_db()
        self.assertNotEqual(invitation.token_digest, digest)
        self.assertTrue(invitation.usable())
        send_email.assert_called_once()
        self.assertNotIn(token, str(send_email.call_args))

    def test_owner_can_revoke_a_pending_collaborator_invitation(self) -> None:
        _token, digest = Invitation.issue_token()
        invitation = Invitation.objects.create(
            organization=self.organization,
            email="ana@example.test",
            role=Membership.Role.OPERATOR,
            company_ids=[str(self.company.id)],
            modules=[ProductModule.Code.NFSE],
            token_digest=digest,
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.post(
            reverse("hub:collaborator-invitation-revoke", args=[invitation.id])
        )

        self.assertRedirects(response, reverse("hub:team"))
        invitation.refresh_from_db()
        self.assertEqual(invitation.status, Invitation.Status.REVOKED)
        self.assertFalse(invitation.usable())

    def test_collaborator_acceptance_limits_companies_and_modules(self) -> None:
        other_company = ClientCompany.objects.create(
            organization=self.organization, name="Outra empresa", dominio_code="002"
        )
        token, digest = Invitation.issue_token()
        Invitation.objects.create(
            organization=self.organization,
            email="operador@example.test",
            full_name="Operador",
            role=Membership.Role.OPERATOR,
            company_ids=[str(self.company.id)],
            modules=[ProductModule.Code.NFSE],
            token_digest=digest,
            expires_at=timezone.now() + timedelta(days=1),
        )

        response = self.client.post(
            reverse("hub:activate", args=[token]),
            {"password": "a-safe-password-123", "password_confirm": "a-safe-password-123"},
        )

        self.assertEqual(response.status_code, 302)
        invited = User.objects.get(email="operador@example.test")
        membership = Membership.objects.get(organization=self.organization, user=invited)
        self.assertEqual(list(company_queryset_for_membership(membership)), [self.company])
        self.assertEqual(module_codes_for_membership(membership), {ProductModule.Code.NFSE})
        grant = CompanyAccessGrant.objects.get(membership=membership, company=self.company)
        self.assertEqual(grant.modules, [ProductModule.Code.NFSE])
        self.assertFalse(
            CompanyAccessGrant.objects.filter(membership=membership, company=other_company).exists()
        )

    def test_collaborator_cannot_bypass_module_scope_by_opening_a_url(self) -> None:
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.GUIDES, enabled=True
        )
        collaborator = User.objects.create_user(
            email="scoped@example.test", password="a-safe-password-123"
        )
        membership = Membership.objects.create(
            organization=self.organization, user=collaborator, role=Membership.Role.OPERATOR
        )
        CompanyAccessGrant.objects.create(
            organization=self.organization,
            membership=membership,
            company=self.company,
            modules=[ProductModule.Code.NFSE],
            capabilities=["*"],
        )
        self.client.force_login(collaborator)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

        self.assertEqual(self.client.get(reverse("hub:nfse-center")).status_code, 200)
        self.assertEqual(self.client.get(reverse("hub:guides")).status_code, 403)
        self.assertEqual(self.client.get(reverse("hub:team")).status_code, 403)

    def test_owner_can_request_an_update_only_when_the_dominio_agent_is_online(self) -> None:
        connector = IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.EDGE_AGENT,
            status="healthy",
        )
        EdgeAgent.objects.create(
            organization=self.organization,
            label="Servidor Domínio",
            fingerprint="agent-online",
            shared_secret="shared-secret",
            last_seen_at=timezone.now(),
        )

        page = self.client.get(reverse("hub:settings"))
        self.assertContains(page, "Atualizar agora")
        self.assertContains(page, "Sincronizado")

        response = self.client.post(reverse("hub:settings"), {"action": "request-dominio-sync"})

        connector.refresh_from_db()
        self.assertRedirects(response, reverse("hub:settings"))
        self.assertIsNotNone(connector.sync_requested_at)

    def test_direct_dominio_dsn_is_encrypted_at_rest(self) -> None:
        connector = IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            odbc_dsn="DSN=Contabil;UID=readonly;PWD=not-a-real-password",
        )
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT odbc_dsn FROM intelligence_intelligenceconnector WHERE id = %s",
                [connector._meta.pk.get_db_prep_value(connector.id, connection=connection)],
            )
            stored_value = cursor.fetchone()[0]
        self.assertNotIn("readonly", stored_value)
        self.assertNotIn("not-a-real-password", stored_value)
        self.assertTrue(stored_value.startswith("enc:v1:"))
        connector.refresh_from_db()
        self.assertEqual(
            connector.odbc_dsn,
            "DSN=Contabil;UID=readonly;PWD=not-a-real-password",
        )

    @patch("apps.hub.views.ReadOnlyDominoOdbc")
    def test_owner_can_update_a_direct_dominio_connection_now(self, mocked_odbc) -> None:
        connector = IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="healthy",
            odbc_dsn="Contabil",
        )
        mocked_odbc.return_value.execute.side_effect = lambda query: (
            [
                {
                    "codigo": "001",
                    "nome": "Empresa Acme",
                    "cnpj_masked": "12.345.678/0001-90",
                }
            ]
            if query == "companies"
            else []
        )

        self.assertContains(self.client.get(reverse("hub:settings")), "Atualizar agora")
        response = self.client.post(
            reverse("hub:settings"), {"action": "request-dominio-sync"}, follow=True
        )

        self.company.refresh_from_db()
        connector.refresh_from_db()
        mocked_odbc.assert_called_once_with("Contabil")
        self.assertEqual(
            [call.args for call in mocked_odbc.return_value.execute.call_args_list],
            [("companies",), ("bank_entries",)],
        )
        self.assertEqual(self.company.cnpj_masked, "12.345.678/0001-90")
        self.assertContains(response, "Domínio atualizado: 1 empresa(s) e 0 item(ns) bancários.")
        self.assertIsNone(connector.sync_requested_at)

    def test_direct_dominio_connection_is_ready_for_dominio_modules(self) -> None:
        IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="healthy",
            odbc_dsn="Contabil",
        )
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.RECONCILIATION, enabled=True
        )

        response = self.client.get(reverse("hub:reconciliation"))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["connector_ready"])

    def test_ofx_validation_reopens_the_import_modal(self) -> None:
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.RECONCILIATION, enabled=True
        )

        response = self.client.post(reverse("hub:reconciliation"), {"company": self.company.pk})

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["open_import_modal"])
        self.assertContains(response, "data-company-picker")
        self.assertContains(response, 'class="sr-only"')

    @patch("apps.hub.views.ReadOnlyDominoOdbc")
    def test_a_failed_direct_sync_offers_resolution_and_a_developer_ticket(
        self, mocked_odbc
    ) -> None:
        connector = IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="healthy",
            odbc_dsn="Contabil",
        )
        mocked_odbc.return_value.execute.side_effect = RuntimeError("ODBC indisponível")

        self.client.post(reverse("hub:settings"), {"action": "request-dominio-sync"})
        connector.refresh_from_db()
        page = self.client.get(reverse("hub:settings"))
        response = self.client.post(
            reverse("hub:settings"), {"action": "dominio-support-ticket"}, follow=True
        )

        self.assertEqual(connector.status, "error")
        self.assertEqual(connector.last_error_code, "odbc_sync")
        self.assertContains(page, "Atenção")
        self.assertContains(page, "Resolver")
        self.assertContains(response, "Chamado aberto para desenvolvimento.")
        self.assertTrue(
            DominioSupportTicket.objects.filter(
                organization=self.organization, connector=connector
            ).exists()
        )

    def test_enabled_product_modules_render_for_the_office(self) -> None:
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
            self.assertContains(response, self.organization.name)

        integra = self.client.get(reverse("hub:integra"))
        self.assertRedirects(integra, reverse("hub:dte-center"))

        nav = self.client.get(reverse("hub:dashboard"))
        self.assertContains(nav, reverse("hub:guides"))
        self.assertContains(nav, reverse("hub:integra"))

    def test_triage_module_renders_its_empty_state_when_enabled(self) -> None:
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.TRIAGE, enabled=True
        )

        response = self.client.get(reverse("hub:triage"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Triagem de Arquivos")
        self.assertContains(response, "Nenhuma caixa de e-mail conectada")

        nav = self.client.get(reverse("hub:dashboard"))
        self.assertContains(nav, reverse("hub:triage"))

    def test_triage_module_is_unavailable_until_the_office_enables_it(self) -> None:
        response = self.client.get(reverse("hub:triage"))

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "não está habilitado", status_code=403)
        self.assertNotContains(self.client.get(reverse("hub:dashboard")), reverse("hub:triage"))

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

    def test_disabled_journey_module_blocks_its_direct_urls(self) -> None:
        """A hidden menu item is not an authorization boundary for internal work."""

        journey = ClientJourney.objects.create(
            organization=self.organization,
            company=self.company,
            title="Fechamento interno",
            owner=self.user,
        )
        step = JourneyStep.objects.create(
            organization=self.organization,
            journey=journey,
            title="Conferir",
            position=1,
        )
        request_item = PortalRequest.objects.create(
            organization=self.organization,
            journey=journey,
            title="Extrato",
        )
        ProductModule.objects.create(
            organization=self.organization,
            code=ProductModule.Code.JOURNEY,
            enabled=False,
        )

        attempts = (
            ("get", reverse("hub:journey"), {}),
            (
                "post",
                reverse("hub:journey-step-create"),
                {"journey_id": journey.id, "step-title": "Não criar"},
            ),
            (
                "post",
                reverse("hub:portal-request-create"),
                {"journey_id": journey.id, "request-title": "Não criar"},
            ),
            (
                "post",
                reverse("hub:journey-step-complete"),
                {"journey_id": journey.id, "item_id": step.id},
            ),
            (
                "post",
                reverse("hub:portal-request-transition"),
                {"journey_id": journey.id, "item_id": request_item.id, "action": "resolve"},
            ),
        )
        for method, url, data in attempts:
            response = getattr(self.client, method)(url, data)
            self.assertEqual(response.status_code, 403, url)
            self.assertContains(response, "não está habilitado", status_code=403)

        self.assertEqual(JourneyStep.objects.filter(journey=journey).count(), 1)
        step.refresh_from_db()
        request_item.refresh_from_db()
        self.assertIsNone(step.completed_at)
        self.assertEqual(request_item.status, PortalRequest.Status.OPEN)
        self.assertNotContains(self.client.get(reverse("hub:dashboard")), reverse("hub:journey"))

    def test_anonymous_request_cannot_use_internal_journey_urls(self) -> None:
        """Jornadas is an authenticated office feature, never a client portal."""

        ProductModule.objects.create(
            organization=self.organization,
            code=ProductModule.Code.JOURNEY,
            enabled=True,
        )
        self.client.logout()

        for method, url in (
            ("get", reverse("hub:journey")),
            ("post", reverse("hub:journey-step-create")),
            ("post", reverse("hub:portal-request-create")),
            ("post", reverse("hub:journey-step-complete")),
            ("post", reverse("hub:portal-request-transition")),
        ):
            response = getattr(self.client, method)(url, {})
            self.assertEqual(response.status_code, 302, url)
            self.assertIn(reverse("hub:login"), response.url)

    def test_unavailable_external_connector_rejects_credentials(self) -> None:
        response = self.client.post(
            reverse("hub:settings"),
            {
                "kind": Connector.Kind.ONVIO,
                "label": "Onvio QA",
                "endpoint": "",
                "database_alias": "DOMINIO_QA",
                "secret": "local-secret",
            },
        )
        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "Não informe credenciais.", status_code=403)
        self.assertFalse(
            Connector.objects.filter(
                organization=self.organization, kind=Connector.Kind.ONVIO
            ).exists()
        )

    def test_owner_can_set_a_central_usage_rule_without_creating_an_integra_connector(
        self,
    ) -> None:
        plan = Plan.objects.create(code="usage", name="Uso", monthly_price_cents=9_900)
        PlanServiceRate.objects.create(
            plan=plan,
            action_code="caixapostal.mensagens",
            included_units=50,
            overage_unit_price_cents=125,
        )
        contract = TenantContract.objects.create(
            organization=self.organization, plan=plan, status=TenantContract.Status.ACTIVE
        )
        rate = contract.service_rates.get(action_code="caixapostal.mensagens")
        prefix = f"usage_{rate.id}"
        complete_mfa(self.client)

        response = self.client.post(
            reverse("hub:settings"),
            {
                "action": "usage-policy",
                "rate_id": rate.id,
                f"{prefix}-overage_mode": TenantUsagePolicy.OverageMode.ALLOW,
                f"{prefix}-warning_percent": 80,
                f"{prefix}-monthly_overage_cap_brl": "35.50",
            },
        )

        self.assertRedirects(response, reverse("hub:settings"))
        policy = TenantUsagePolicy.objects.get(organization=self.organization)
        self.assertEqual(policy.monthly_overage_cap_cents, 3_550)
        self.assertFalse(
            Connector.objects.filter(organization=self.organization, kind=Connector.Kind.INTEGRA)
        )

    def test_generic_connector_posts_are_not_accepted(self) -> None:
        response = self.client.post(
            reverse("hub:settings"),
            {"kind": Connector.Kind.DOMINIO_AGENT, "label": "Domínio", "secret": "x"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "ainda não está disponível", status_code=403)
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

    def test_nfse_center_shows_the_whole_portfolio(self) -> None:
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

        self.assertContains(response, "Central NFS-e")
        self.assertContains(response, "owned")
        self.assertContains(response, "other")

        scoped = self.client.get(reverse("hub:company-detail", args=[self.company.id]))

        self.assertContains(scoped, "owned")
        self.assertNotContains(scoped, "other")

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

        office_response = self.client.post(
            reverse("hub:switch-office"), {"organization_id": str(other_organization.id)}
        )

        self.assertRedirects(office_response, reverse("hub:dashboard"))
        self.assertEqual(self.client.session["hub_organization_id"], str(other_organization.id))
        portfolio = self.client.get(reverse("hub:companies")).context["companies"]
        self.assertNotIn(second_company, portfolio)

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

    def test_the_anonymous_workspace_is_blocked(self) -> None:
        self.client.logout()
        anonymous = self.client.get(reverse("hub:dashboard"))
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn(reverse("hub:login"), anonymous["Location"])
