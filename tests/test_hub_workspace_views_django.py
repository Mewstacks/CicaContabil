from __future__ import annotations

from datetime import timedelta
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.db import connection
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.controlplane import company_queryset_for_membership, module_codes_for_membership
from apps.hub.models import (
    Certificate,
    ClientCompany,
    CompanyAccessGrant,
    Connector,
    ControlPlaneBinding,
    NfseSync,
    ProductModule,
    ReformAlert,
    ReformSourceStatus,
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
from apps.triage.ingest import receive_email_attachment
from apps.triage.models import (
    DestinationProfile,
    DocumentType,
    Mailbox,
    TriageItem,
    TriageSafetyScan,
)
from apps.triage.security import ScanVerdict, scan_quarantined_item
from apps.triage.storage import PrivateTriageStorage
from apps.triage.transitions import TriageStatus
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

    def test_certificate_workspace_prioritizes_expiry_and_missing_companies(self) -> None:
        valid_company = ClientCompany.objects.create(
            organization=self.organization,
            name="Empresa com certificado longo",
            dominio_code="090",
        )
        expiring_company = ClientCompany.objects.create(
            organization=self.organization,
            name="Empresa vencendo logo",
            dominio_code="091",
        )
        Certificate.objects.create(
            organization=self.organization,
            company=valid_company,
            label="A1 matriz",
            pfx_blob="encrypted-valid",
            password="encrypted-password",
            fingerprint_sha256="a" * 64,
            valid_until=timezone.now() + timedelta(days=90),
        )
        Certificate.objects.create(
            organization=self.organization,
            company=expiring_company,
            label="A1 filial",
            pfx_blob="encrypted-expiring",
            password="encrypted-password",
            fingerprint_sha256="b" * 64,
            valid_until=timezone.now() + timedelta(days=5),
        )

        attention = self.client.get(reverse("hub:certificates"))

        self.assertContains(attention, "Empresa vencendo logo")
        self.assertNotContains(attention, "A1 matriz")
        self.assertContains(attention, "Vence em breve")
        self.assertContains(attention, "Empresas sem certificado A1 válido")
        self.assertContains(attention, self.company.name)

        searched = self.client.get(
            reverse("hub:certificates"), {"q": "090", "status": "all"}
        )
        self.assertContains(searched, "Empresa com certificado longo")
        self.assertEqual(
            [certificate.company for certificate in searched.context["certificates"]],
            [valid_company],
        )
        self.assertContains(searched, "1 resultado")

    def test_demo_certificate_action_is_session_only_and_never_stores_a_pfx(self) -> None:
        self.organization.is_demo = True
        self.organization.save(update_fields=["is_demo"])
        session = self.client.session
        session["demo_visit_id"] = "certificate-demo-visitor"
        session.save()

        response = self.client.post(
            reverse("hub:certificates"), {"demo_company_id": str(self.company.id)}, follow=True
        )

        self.assertContains(response, "Certificado fictício registrado")
        self.assertContains(response, "Nenhum arquivo ou senha foi recebido")
        self.assertEqual(response.context["certificate_stats"]["missing_companies"], 0)
        self.assertFalse(Certificate.objects.filter(organization=self.organization).exists())
        self.assertTrue(
            self.client.session["demo_progress"]["certificates"][str(self.company.id)][
                "simulated"
            ]
        )

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
            title="Crédito tributário da CBS",
            source_url="https://www.gov.br/fazenda/noticia",
            relevance=ReformAlert.Relevance.FISCAL,
            content_hash="hash-2",
        )

        response = self.client.get(reverse("hub:reform"), {"fonte": "rfb"})

        self.assertContains(response, "Cronograma IBS")
        self.assertNotContains(response, "Crédito tributário da CBS")
        self.assertContains(response, "Pesquisar publicações")
        self.assertContains(response, "Saúde das fontes")
        self.assertContains(response, "Aguardando a primeira coleta")

        unfiltered = self.client.get(reverse("hub:reform"))
        self.assertContains(unfiltered, "Cronograma IBS")
        self.assertContains(unfiltered, "Crédito tributário da CBS")

        searched = self.client.get(
            reverse("hub:reform"), {"q": "crédito", "relevancia": "fiscal"}
        )
        self.assertContains(searched, "Crédito tributário da CBS")
        self.assertNotContains(searched, "Cronograma IBS")
        self.assertContains(searched, "1 resultado")

    def test_reform_radar_shows_a_source_collection_failure_without_raw_error(self) -> None:
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.REFORM, enabled=True
        )
        ReformSourceStatus.objects.create(
            source=ReformAlert.Source.RFB,
            last_error="upstream timeout with internal trace 9d1f",
        )

        response = self.client.get(reverse("hub:reform"))

        self.assertContains(response, "Falha na coleta")
        self.assertContains(response, "a próxima coleta tentará novamente")
        self.assertNotContains(response, "internal trace 9d1f")

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

    @patch("apps.hub.views.send_invitation_email")
    def test_owner_invites_a_collaborator_with_company_and_module_scope(self, send_email) -> None:
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.TRIAGE, enabled=True
        )
        response = self.client.post(
            reverse("hub:team"),
            {
                "full_name": "Ana Fiscal",
                "email": "ana@example.test",
                "role": Membership.Role.OPERATOR,
                "modules": [ProductModule.Code.NFSE, ProductModule.Code.TRIAGE],
                "companies": [str(self.company.id)],
            },
        )

        self.assertRedirects(response, reverse("hub:team"))
        invitation = Invitation.objects.get(email="ana@example.test")
        self.assertEqual(invitation.company_ids, [str(self.company.id)])
        self.assertEqual(
            set(invitation.modules), {ProductModule.Code.NFSE, ProductModule.Code.TRIAGE}
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
        self.assertContains(page, "Aguardando primeira atualização")

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

    def test_settings_exposes_a_bank_snapshot_limit_warning(self) -> None:
        IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="healthy",
            last_sync_at=timezone.now(),
            odbc_dsn="Contabil",
        )
        AuditEvent.objects.create(
            organization=self.organization,
            action="intelligence.dominio.bank_entries_synced",
            metadata={"may_be_truncated": True},
        )

        response = self.client.get(reverse("hub:settings"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cobertura parcial de itens bancarios.")
        self.assertTrue(response.context["dominio_bank_entries_may_be_truncated"])

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
        self.assertEqual(integra.status_code, 200)
        self.assertContains(integra, "Caixa DTE")
        self.assertContains(integra, "Parcelamentos")
        self.assertContains(integra, "DCTFWeb")
        self.assertContains(integra, reverse("hub:dte-center"))

        nav = self.client.get(reverse("hub:dashboard"))
        self.assertContains(nav, reverse("hub:guides"))
        self.assertContains(nav, reverse("hub:integra"))

    def test_triage_module_requires_an_email_mailbox_when_enabled(self) -> None:
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.TRIAGE, enabled=True
        )

        response = self.client.get(reverse("hub:triage"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Triagem de Arquivos")
        self.assertContains(response, "Caixa de e-mail não configurada")
        self.assertContains(response, reverse("hub:triage-connections"))
        self.assertNotContains(response, "Pronto para receber dados")

        connections = self.client.get(reverse("hub:triage-connections"))
        self.assertEqual(connections.status_code, 200)
        self.assertContains(connections, "Nenhuma caixa de e-mail conectada")

        nav = self.client.get(reverse("hub:dashboard"))
        self.assertContains(nav, reverse("hub:triage"))

    def test_triage_item_routes_respect_the_collaborators_company_scope(self) -> None:
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.TRIAGE, enabled=True
        )
        restricted_company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa restrita", dominio_code="002"
        )
        restricted_item = TriageItem.objects.create(
            organization=self.organization,
            company=restricted_company,
            original_name="documento.pdf",
        )
        collaborator = User.objects.create_user(
            email="triage-scoped@example.test", password="a-safe-password-123"
        )
        membership = Membership.objects.create(
            organization=self.organization, user=collaborator, role=Membership.Role.OPERATOR
        )
        CompanyAccessGrant.objects.create(
            organization=self.organization,
            membership=membership,
            company=self.company,
            modules=[ProductModule.Code.TRIAGE],
            capabilities=["read"],
        )
        self.client.force_login(collaborator)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()

        for endpoint in ("hub:triage-item", "hub:triage-download"):
            self.assertEqual(
                self.client.get(reverse(endpoint, args=[restricted_item.id])).status_code,
                404,
            )

    def test_triage_queue_shows_unassigned_mail_only_to_admin_and_filters_by_stage(self) -> None:
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.TRIAGE, enabled=True
        )
        unknown = TriageItem.objects.create(
            organization=self.organization,
            original_name="pendente-de-identificacao.pdf",
            status=TriageItem.Status.QUARANTINED,
        )
        assigned = TriageItem.objects.create(
            organization=self.organization,
            company=self.company,
            original_name="documento-atribuido.xml",
            status=TriageItem.Status.AWAITING_REVIEW,
        )
        response = self.client.get(reverse("hub:triage"))
        self.assertContains(response, unknown.original_name)
        self.assertContains(response, assigned.original_name)
        self.assertContains(response, "1 em quarentena")
        self.assertEqual(
            self.client.get(reverse("hub:triage-item", args=[unknown.id])).status_code, 200
        )
        filtered = self.client.get(reverse("hub:triage"), {"status": TriageItem.Status.QUARANTINED})
        self.assertContains(filtered, unknown.original_name)
        self.assertNotContains(filtered, assigned.original_name)

        collaborator = User.objects.create_user(
            email="triage-queue-scope@example.test", password="a-safe-password-123"
        )
        membership = Membership.objects.create(
            organization=self.organization, user=collaborator, role=Membership.Role.OPERATOR
        )
        CompanyAccessGrant.objects.create(
            organization=self.organization,
            membership=membership,
            company=self.company,
            modules=[ProductModule.Code.TRIAGE],
            capabilities=["read"],
        )
        self.client.force_login(collaborator)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session.save()
        operator_page = self.client.get(reverse("hub:triage"))
        self.assertContains(operator_page, assigned.original_name)
        self.assertNotContains(operator_page, unknown.original_name)
        self.assertEqual(
            self.client.get(reverse("hub:triage-item", args=[unknown.id])).status_code, 404
        )

    def test_triage_prototype_cannot_review_or_download_unscanned_files(self) -> None:
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.TRIAGE, enabled=True
        )
        item = TriageItem.objects.create(
            organization=self.organization,
            company=self.company,
            original_name="anexo-nao-verificado.pdf",
        )

        detail = self.client.get(reverse("hub:triage-item", args=[item.id]))
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, "verificação de segurança")
        self.assertNotContains(detail, "Baixar arquivo")
        refused = self.client.post(reverse("hub:triage-item", args=[item.id]), {}, follow=True)
        self.assertContains(refused, "Escolha uma decisão válida")
        self.assertEqual(
            self.client.get(reverse("hub:triage-download", args=[item.id])).status_code,
            404,
        )

    def test_internal_library_download_uses_verified_copy_and_refuses_tampering(self) -> None:
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.TRIAGE, enabled=True
        )
        mailbox = Mailbox.objects.create(
            organization=self.organization, provider=Mailbox.Provider.IMAP,
            address="arquivo@acme.test", active=True, status=Mailbox.Status.ACTIVE,
        )
        payload = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
        item = receive_email_attachment(
            mailbox=mailbox, message_id="download-test", part_id="1",
            filename="documento.pdf", payload=payload,
        ).item

        class CleanScanner:
            def scan(self, stream: object) -> ScanVerdict:
                return ScanVerdict(TriageSafetyScan.Verdict.CLEAN, "test-scanner")

        scan_quarantined_item(item=item, scanner=CleanScanner())
        item.refresh_from_db()
        doc_type = DocumentType.objects.create(
            organization=self.organization, code="documento", label="Documento",
            name_template="{codigo}_DOCUMENTO_{periodo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
        )
        DestinationProfile.objects.create(
            organization=self.organization, mode=DestinationProfile.Mode.INTERNAL
        )
        item.company = self.company
        item.document_type = doc_type
        item.final_name = "001_DOCUMENTO_082026.pdf"
        item.transition_to(TriageStatus.EXTRACTING)
        item.transition_to(TriageStatus.AWAITING_REVIEW)
        item.save()
        detail_url = reverse("hub:triage-item", args=[item.id])
        self.assertContains(self.client.get(detail_url), "Aprovar para arquivamento")
        approved = self.client.post(detail_url, {"decision": "archive"}, follow=True)
        self.assertContains(approved, "Arquivar na biblioteca interna")
        item.refresh_from_db()
        archived = self.client.post(detail_url, {"decision": "finish_archive"}, follow=True)
        self.assertContains(archived, "Baixar arquivo da biblioteca")
        item.refresh_from_db()
        detail = self.client.get(reverse("hub:triage-item", args=[item.id]))
        self.assertContains(detail, "Baixar arquivo da biblioteca")
        self.assertContains(detail, "Aguardando extração")
        self.assertContains(detail, "Cópia interna íntegra confirmada")
        download = self.client.get(reverse("hub:triage-download", args=[item.id]))
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b"".join(download.streaming_content), payload)
        self.assertEqual(download["Cache-Control"], "no-store, private")
        self.assertIn("attachment", download["Content-Disposition"])
        download.close()
        with PrivateTriageStorage().open(item.destination_path, "wb") as copy:
            copy.write(b"tampered")
        self.assertEqual(
            self.client.get(reverse("hub:triage-download", args=[item.id])).status_code,
            404,
        )

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

    def test_retired_journey_routes_and_navigation_are_unavailable(self) -> None:
        ProductModule.objects.create(
            organization=self.organization,
            code=ProductModule.Code.JOURNEY,
            enabled=True,
        )
        for path in (
            "/app/jornada/",
            "/app/jornada/etapas/criar/",
            "/app/jornada/pedidos/criar/",
            "/app/jornada/etapas/concluir/",
            "/app/jornada/pedidos/transicionar/",
        ):
            self.assertEqual(self.client.get(path).status_code, 404, path)
            self.assertEqual(self.client.post(path, {}).status_code, 404, path)
        self.assertNotContains(self.client.get(reverse("hub:dashboard")), "/app/jornada/")

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

    def test_legacy_per_call_usage_rule_is_rejected_in_favor_of_tokens(
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

        self.assertEqual(response.status_code, 403)
        self.assertContains(response, "cobrança por chamada foi descontinuada", status_code=403)
        self.assertFalse(TenantUsagePolicy.objects.filter(organization=self.organization).exists())
        self.assertFalse(
            Connector.objects.filter(organization=self.organization, kind=Connector.Kind.INTEGRA)
        )

        page = self.client.get(reverse("hub:settings"))
        self.assertNotContains(page, "chamadas incluídas")
        self.assertNotContains(page, "por chamada")
        self.assertContains(page, "proposta com valor do token")

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

        self.assertContains(response, "<h1>NFS-e</h1>", html=True)
        self.assertContains(response, "owned")
        self.assertContains(response, "other")

        scoped = self.client.get(reverse("hub:company-detail", args=[self.company.id]))

        self.assertContains(scoped, "owned")
        self.assertNotContains(scoped, "other")

    def test_nfse_center_is_an_operational_bulk_sync_workspace(self) -> None:
        response = self.client.get(reverse("hub:nfse-center"), {"view": "collection"})

        self.assertContains(response, "Coleta por empresa")
        self.assertContains(response, "Selecionar todas as empresas exibidas")
        self.assertContains(response, "Ativar coleta")
        self.assertContains(response, "Coleta externa ainda desligada neste ambiente")
        self.assertContains(response, self.company.name)

    def test_nfse_activation_without_a_valid_company_certificate_is_blocked(self) -> None:
        response = self.client.post(
            reverse("hub:nfse-center"),
            {"action": "activate", "companies": [str(self.company.id)]},
            follow=True,
        )

        self.assertRedirects(response, reverse("hub:nfse-center"))
        self.assertFalse(
            NfseSync.objects.filter(organization=self.organization, company=self.company).exists()
        )
        self.assertContains(response, "sem e-CNPJ válido e compatível")

    def test_nfse_bulk_pause_stops_scheduling_without_removing_history(self) -> None:
        sync = NfseSync.objects.create(
            organization=self.organization,
            company=self.company,
            enabled=True,
            status=NfseSync.Status.IDLE,
            checkpoint_nsu="981",
            next_run_at=timezone.now(),
        )

        response = self.client.post(
            reverse("hub:nfse-center"),
            {"action": "pause", "companies": [str(self.company.id)]},
        )

        self.assertRedirects(response, reverse("hub:nfse-center"))
        sync.refresh_from_db()
        self.assertFalse(sync.enabled)
        self.assertEqual(sync.status, NfseSync.Status.PAUSED)
        self.assertEqual(sync.checkpoint_nsu, "981")

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

    def test_nfse_center_searches_the_portfolio_and_links_the_exact_review(self) -> None:
        other_company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa pesquisável", dominio_code="0888"
        )
        _document, _artifact, review = create_document_and_artifact(
            company=other_company,
            original_xml="<nfse id='search-review' />",
            normalized_data={"service_code": "sem-regra"},
            source_nsu="NSU-PESQUISA",
        )
        assert review is not None

        response = self.client.get(
            reverse("hub:nfse-center"), {"q": "0888", "status": "review"}
        )

        self.assertContains(response, other_company.name)
        self.assertContains(response, "NSU-PESQUISA")
        self.assertContains(response, reverse("hub:review-detail", args=[review.id]))
        self.assertNotContains(response, self.company.name)

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

        detail_url = reverse("hub:review-detail", args=[review.id])
        self.assertRedirects(missing, detail_url)
        self.assertRedirects(resolved, detail_url)
        review.refresh_from_db()
        self.assertEqual(review.status, ReviewCase.Status.RESOLVED)
        self.assertEqual(review.resolved_accumulator, "AC-200")
        self.assertEqual(review.resolved_by, self.user)

    def test_review_queue_searches_the_portfolio_and_defaults_to_open_cases(self) -> None:
        _document, _artifact, open_review = create_document_and_artifact(
            company=self.company,
            original_xml="<nfse id='open-filter' />",
            normalized_data={"service_code": "1401"},
        )
        assert open_review is not None
        resolved_company = ClientCompany.objects.create(
            organization=self.organization,
            name="Empresa já conferida",
            dominio_code="0777",
        )
        _document, _artifact, resolved_review = create_document_and_artifact(
            company=resolved_company,
            original_xml="<nfse id='resolved-filter' />",
            normalized_data={"service_code": "1702"},
        )
        assert resolved_review is not None
        resolved_review.status = ReviewCase.Status.RESOLVED
        resolved_review.resolved_accumulator = "AC-777"
        resolved_review.resolved_by = self.user
        resolved_review.resolved_at = timezone.now()
        resolved_review.save()

        default_queue = self.client.get(reverse("hub:reviews"))
        self.assertContains(default_queue, self.company.name)
        self.assertNotContains(default_queue, resolved_company.name)
        resolved_queue = self.client.get(
            reverse("hub:reviews"), {"status": "resolved", "q": "0777"}
        )
        self.assertContains(resolved_queue, resolved_company.name)
        self.assertNotContains(resolved_queue, self.company.name)

    def test_dashboard_exposes_exact_operational_queues(self) -> None:
        for code in (
            ProductModule.Code.INTEGRA,
            ProductModule.Code.GUIDES,
            ProductModule.Code.TRIAGE,
            ProductModule.Code.RECONCILIATION,
        ):
            ProductModule.objects.update_or_create(
                organization=self.organization,
                code=code,
                defaults={"enabled": True, "enabled_at": timezone.now()},
            )
        response = self.client.get(reverse("hub:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pendências por área")
        self.assertContains(response, f'{reverse("hub:reviews")}')
        self.assertContains(response, f'{reverse("hub:dte-center")}?status=unread')
        self.assertContains(response, f'{reverse("hub:guides")}?status=pending')

    def test_review_detail_links_to_exact_case_and_scopes_original_xml(self) -> None:
        original = "<nfse id='case-owned' />"
        _document, _artifact, review = create_document_and_artifact(
            company=self.company,
            original_xml=original,
            normalized_data={"service_code": "1401"},
        )
        assert review is not None
        detail_url = reverse("hub:review-detail", args=[review.id])
        xml_url = reverse("hub:review-original-xml", args=[review.id])

        dashboard = self.client.get(reverse("hub:dashboard"))
        detail = self.client.get(detail_url)
        downloaded = self.client.get(xml_url)

        self.assertContains(dashboard, detail_url)
        self.assertContains(detail, "Código de serviço")
        self.assertContains(detail, "1401")
        self.assertContains(detail, xml_url)
        self.assertEqual(downloaded.status_code, 200)
        self.assertEqual(downloaded.content.decode(), original)
        self.assertIn("attachment", downloaded["Content-Disposition"])
        self.assertEqual(downloaded["Cache-Control"], "private, no-store")

        other_office = Organization.objects.create(
            name="Outro escritório", slug="review-other-office"
        )
        other_company = ClientCompany.objects.create(
            organization=other_office, name="Outra empresa", dominio_code="899"
        )
        _other_document, _other_artifact, other_review = create_document_and_artifact(
            company=other_company,
            original_xml="<nfse id='case-other' />",
            normalized_data={},
        )
        assert other_review is not None
        self.assertEqual(
            self.client.get(reverse("hub:review-detail", args=[other_review.id])).status_code,
            404,
        )
        self.assertEqual(
            self.client.get(reverse("hub:review-original-xml", args=[other_review.id])).status_code,
            404,
        )

    def test_the_anonymous_workspace_is_blocked(self) -> None:
        self.client.logout()
        anonymous = self.client.get(reverse("hub:dashboard"))
        self.assertEqual(anonymous.status_code, 302)
        self.assertIn(reverse("hub:login"), anonymous["Location"])
