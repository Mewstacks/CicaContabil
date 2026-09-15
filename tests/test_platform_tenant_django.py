from datetime import timedelta

from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import (
    Certificate,
    ClientCompany,
    ControlPlaneBinding,
    ProductModule,
    RemoteSupportGrant,
)
from apps.intelligence.models import (
    AssistantSettings,
    ClaudeFallbackApproval,
    IntelligenceConnector,
)
from apps.organizations.models import Membership, Organization
from apps.platform.models import (
    DominioSupportTicket,
    Invitation,
    Plan,
    PlatformAccess,
    PlatformConfiguration,
    SupportSession,
    TenantContract,
    TenantLifecycle,
    TenantServiceRate,
    TenantUsagePolicy,
)
from conftest import complete_mfa


class PlatformTenantViewTests(TestCase):
    def setUp(self):
        self.developer = User.objects.create_user(
            email="developer@example.test", password="safe-password-123"
        )
        PlatformAccess.objects.create(user=self.developer, role=PlatformAccess.Role.DEVELOPER)
        self.office = Organization.objects.create(name="Escritório Demo", slug="escritorio-demo")
        self.client.force_login(self.developer)
        complete_mfa(self.client)

    def test_developer_can_select_systems_without_a_contract_form(self):
        self.assertEqual(self.client.get(reverse("platform:tenants")).status_code, 200)
        detail_url = reverse("platform:tenant-detail", args=[self.office.id])

        response = self.client.get(detail_url)

        self.assertContains(response, "Sistemas")
        self.assertContains(response, "Abrir área do escritório")
        self.assertNotContains(response, "Registrar contrato")

        response = self.client.post(
            detail_url,
            {"action": "modules", "modules": [ProductModule.Code.INTEGRA]},
        )

        self.assertRedirects(response, detail_url)
        enabled = ProductModule.objects.get(
            organization=self.office, code=ProductModule.Code.INTEGRA
        )
        self.assertTrue(enabled.enabled)

    def test_developer_moves_operational_access_with_reason_and_confirmation(self):
        detail_url = reverse("platform:tenant-detail", args=[self.office.id])
        plan = Plan.objects.create(code="lifecycle-plan", name="Lifecycle")
        TenantContract.objects.create(
            organization=self.office,
            plan=plan,
            status=TenantContract.Status.ACTIVE,
        )

        first = self.client.post(
            detail_url,
            {
                "action": "lifecycle",
                "state": TenantLifecycle.State.ACTIVATION_PENDING,
                "reason": "Aguardando a ativação do proprietário.",
            },
        )
        self.assertRedirects(first, detail_url)
        lifecycle = TenantLifecycle.objects.get(organization=self.office)
        self.assertEqual(lifecycle.state, TenantLifecycle.State.ACTIVATION_PENDING)

        self.client.post(
            detail_url,
            {
                "action": "lifecycle",
                "state": TenantLifecycle.State.ACTIVE,
                "reason": "Ativação concluída.",
            },
        )
        denied = self.client.post(
            detail_url,
            {
                "action": "lifecycle",
                "state": TenantLifecycle.State.SUSPENDED,
                "reason": "Acesso temporariamente bloqueado.",
            },
        )
        self.assertRedirects(denied, detail_url)
        lifecycle.refresh_from_db()
        self.assertEqual(lifecycle.state, TenantLifecycle.State.ACTIVE)

        confirmed = self.client.post(
            detail_url,
            {
                "action": "lifecycle",
                "state": TenantLifecycle.State.SUSPENDED,
                "reason": "Acesso temporariamente bloqueado.",
                "confirm_lifecycle": "on",
            },
        )
        self.assertRedirects(confirmed, detail_url)
        lifecycle.refresh_from_db()
        self.assertEqual(lifecycle.state, TenantLifecycle.State.SUSPENDED)

    def test_reactivation_of_a_commercially_blocked_office_reactivates_contract_too(self):
        plan = Plan.objects.create(code="reactivation-plan", name="Reativação")
        contract = TenantContract.objects.create(
            organization=self.office,
            plan=plan,
            status=TenantContract.Status.SUSPENDED,
        )
        TenantLifecycle.objects.create(
            organization=self.office,
            state=TenantLifecycle.State.SUSPENDED,
        )

        response = self.client.post(
            reverse("platform:tenant-detail", args=[self.office.id]),
            {
                "action": "lifecycle",
                "state": TenantLifecycle.State.ACTIVE,
                "reason": "Cobrança regularizada fora da CICA.",
            },
        )

        self.assertEqual(response.status_code, 302)
        contract.refresh_from_db()
        self.assertEqual(contract.status, TenantContract.Status.ACTIVE)
        self.assertEqual(
            TenantLifecycle.objects.get(organization=self.office).state,
            TenantLifecycle.State.ACTIVE,
        )

    def test_developer_configures_a_time_bounded_office_quota_without_provider_key(self):
        detail_url = reverse("platform:tenant-detail", args=[self.office.id])
        valid_until = (timezone.now() + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
        PlatformConfiguration.objects.update_or_create(
            key="default", defaults={"cloud_fallback_model": "claude-sonnet-5"}
        )

        response = self.client.post(
            detail_url,
            {
                "action": "ai-fallback",
                "enabled": "on",
                "allow_full_data": "on",
                "allowed_roles": [Membership.Role.OWNER, Membership.Role.ADMIN],
                "api_key": "tenant-fallback-key-must-be-ignored",
                "max_request_brl": "0.75",
                "daily_limit_brl": "15.00",
                "monthly_limit_brl": "120.00",
                "valid_until": valid_until,
            },
        )

        self.assertRedirects(response, detail_url)
        policy = AssistantSettings.objects.get(organization=self.office)
        approval = ClaudeFallbackApproval.objects.get(organization=self.office)
        self.assertTrue(policy.claude_fallback_enabled)
        self.assertEqual(policy.claude_api_key, "")
        self.assertEqual(policy.claude_model, "claude-sonnet-5")
        self.assertEqual(policy.claude_max_request_cents, 75)
        self.assertEqual(approval.status, ClaudeFallbackApproval.Status.APPROVED)
        self.assertEqual(approval.daily_limit_cents, 1500)
        self.assertEqual(approval.monthly_limit_cents, 12000)
        self.assertNotContains(
            self.client.get(detail_url), "Chave do provedor"
        )

    def test_developer_controls_copilot_retention_and_confirms_shortening(self):
        detail_url = reverse("platform:tenant-detail", args=[self.office.id])

        initial = self.client.post(
            detail_url,
            {"action": "ai-retention", "retention_days": "30"},
        )
        self.assertEqual(initial.status_code, 200)
        self.assertContains(initial, "Confirme a redução")
        self.assertFalse(AssistantSettings.objects.filter(organization=self.office).exists())

        configured = self.client.post(
            detail_url,
            {
                "action": "ai-retention",
                "retention_days": "30",
                "confirm_shortening": "on",
            },
        )
        self.assertRedirects(configured, detail_url)
        self.assertEqual(
            AssistantSettings.objects.get(organization=self.office).retention_days,
            30,
        )

        shorter = self.client.post(
            detail_url,
            {"action": "ai-retention", "retention_days": "7"},
        )
        self.assertEqual(shorter.status_code, 200)
        self.assertEqual(
            AssistantSettings.objects.get(organization=self.office).retention_days,
            30,
        )

    def test_office_claude_policy_requires_a_time_bound(self):
        response = self.client.post(
            reverse("platform:tenant-detail", args=[self.office.id]),
            {
                "action": "ai-fallback",
                "enabled": "on",
                "allowed_roles": [Membership.Role.OWNER],
                "model": "claude-test-model",
                "max_request_brl": "0.75",
                "daily_limit_brl": "15.00",
                "monthly_limit_brl": "120.00",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Defina quando essa aprovação expira")
        self.assertFalse(AssistantSettings.objects.filter(organization=self.office).exists())

    def test_office_credential_action_cannot_replace_mewstack_key(self):
        ControlPlaneBinding.objects.create(
            organization=self.office,
            remote_installation_id="5b3dd36b-4da4-4b7a-9f12-8e933c2ed0e4",
            controller_url="https://crmew.example.test",
            device_private_key="local-control-key",
            controller_public_key="controller-key",
        )
        AssistantSettings.objects.create(
            organization=self.office,
            claude_fallback_enabled=True,
            claude_allowed_roles=[Membership.Role.OWNER],
            claude_model="claude-test-model",
            claude_max_request_cents=75,
        )
        approval = ClaudeFallbackApproval.objects.create(
            organization=self.office,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=1500,
            monthly_limit_cents=12000,
            valid_until=timezone.now() + timedelta(days=7),
        )
        detail_url = reverse("platform:tenant-detail", args=[self.office.id])

        response = self.client.post(
            detail_url,
            {"action": "ai-fallback-credential", "api_key": "local-secret-not-rendered"},
        )

        policy = AssistantSettings.objects.get(organization=self.office)
        approval.refresh_from_db()
        self.assertEqual(response.status_code, 403)
        self.assertEqual(policy.claude_api_key, "")
        self.assertTrue(policy.claude_fallback_enabled)
        self.assertEqual(approval.status, ClaudeFallbackApproval.Status.APPROVED)
        page = self.client.get(detail_url)
        self.assertNotContains(page, "Chave do provedor")
        self.assertNotContains(page, "local-secret-not-rendered")

    def test_office_credential_action_cannot_remove_legacy_key(self):
        ControlPlaneBinding.objects.create(
            organization=self.office,
            remote_installation_id="5b3dd36b-4da4-4b7a-9f12-8e933c2ed0e4",
            controller_url="https://crmew.example.test",
            device_private_key="local-control-key",
            controller_public_key="controller-key",
        )
        AssistantSettings.objects.create(
            organization=self.office,
            claude_api_key="to-be-removed",
        )

        response = self.client.post(
            reverse("platform:tenant-detail", args=[self.office.id]),
            {"action": "ai-fallback-credential", "clear_api_key": "on"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(
            AssistantSettings.objects.get(organization=self.office).claude_api_key,
            "to-be-removed",
        )

    def test_platform_account_menu_has_only_account_actions(self):
        response = self.client.get(reverse("platform:dashboard"))

        self.assertContains(response, 'data-popover-toggle="account-list"')
        self.assertContains(response, "Sair")
        self.assertNotContains(response, "Abrir Hub")

    def test_recent_offices_are_sorted_by_creation_date_not_alphabet(self):
        old_date = timezone.now() - timedelta(days=3)
        for index in range(8):
            old = Organization.objects.create(name=f"A escritório {index}", slug=f"old-{index}")
            Organization.objects.filter(pk=old.pk).update(created_at=old_date)
        fedrizzi = Organization.objects.create(
            name="Fedrizzi Contabilidade", slug="fedrizzi-contabilidade"
        )

        response = self.client.get(reverse("platform:dashboard"))

        self.assertContains(response, "Fedrizzi Contabilidade")
        self.assertEqual(next(iter(response.context["tenants"])), fedrizzi)

    def test_developer_sees_open_dominio_tickets_on_the_dashboard(self):
        connector = IntelligenceConnector.objects.create(
            organization=self.office,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="error",
        )
        DominioSupportTicket.objects.create(
            organization=self.office,
            connector=connector,
            error_code="odbc_sync",
            opened_by=self.developer,
        )

        response = self.client.get(reverse("platform:dashboard"))

        self.assertContains(response, "Chamados Domínio")
        self.assertContains(response, "odbc_sync")

    def test_developer_enters_the_office_without_impersonating_a_member(self):
        response = self.client.post(
            reverse("platform:start-support", args=[self.office.id]),
            {"justification": "Abertura operacional pela plataforma."},
        )

        self.assertRedirects(response, reverse("hub:dashboard"))
        self.assertTrue(
            SupportSession.objects.filter(
                organization=self.office, support_user=self.developer
            ).exists()
        )
        support = SupportSession.objects.get(organization=self.office, support_user=self.developer)
        self.assertEqual(support.access_mode, SupportSession.AccessMode.FULL)
        self.assertFalse(
            Membership.objects.filter(user=self.developer, organization=self.office).exists()
        )

    def test_support_session_overrides_an_unrelated_active_membership(self):
        qa_office = Organization.objects.create(name="Escritório QA", slug="escritorio-qa")
        Membership.objects.create(
            organization=qa_office,
            user=self.developer,
            role=Membership.Role.OWNER,
        )
        ClientCompany.objects.create(
            organization=qa_office,
            name="Empresa QA",
            dominio_code="QA01",
        )
        ClientCompany.objects.create(
            organization=self.office,
            name="Empresa Fedrizzi",
            dominio_code="FD01",
        )
        session = self.client.session
        session["hub_organization_id"] = str(qa_office.id)
        session.save()

        entered = self.client.post(
            reverse("platform:start-support", args=[self.office.id]),
            {"justification": "Abertura operacional pela plataforma."},
        )
        page = self.client.get(reverse("hub:companies"))

        self.assertRedirects(entered, reverse("hub:dashboard"), fetch_redirect_response=False)
        self.assertEqual(self.client.session["hub_organization_id"], str(self.office.id))
        self.assertContains(page, "Acesso de suporte")
        self.assertContains(page, "Escritório Demo")
        self.assertContains(page, "Empresa Fedrizzi")
        self.assertNotContains(page, "Empresa QA")

    def test_commercial_provisions_an_office_but_cannot_issue_its_activation(self):
        commercial = User.objects.create_user(
            email="commercial@example.test", password="safe-password-123"
        )
        PlatformAccess.objects.create(user=commercial, role=PlatformAccess.Role.COMMERCIAL)
        self.client.force_login(commercial)
        complete_mfa(self.client)
        created = self.client.post(
            reverse("platform:tenants"), {"name": "Novo escritório", "slug": "novo-escritorio"}
        )
        new_office = Organization.objects.get(slug="novo-escritorio")
        detail_url = reverse("platform:tenant-detail", args=[new_office.id])

        invitation = self.client.post(
            detail_url,
            {
                "action": "invite",
                "invite-email": "owner@new.test",
                "invite-full_name": "Owner New",
                "invite-role": Membership.Role.OWNER,
            },
        )

        self.assertRedirects(created, detail_url)
        self.assertEqual(invitation.status_code, 403)
        self.assertFalse(Invitation.objects.filter(email="owner@new.test").exists())

    def test_commercial_configures_the_monthly_contract_in_the_tenant_modal(self):
        commercial = User.objects.create_user(
            email="commercial-contract@example.test", password="safe-password-123"
        )
        PlatformAccess.objects.create(user=commercial, role=PlatformAccess.Role.COMMERCIAL)
        plan = Plan.objects.create(code="integra", name="Integra")
        self.client.force_login(commercial)
        complete_mfa(self.client)
        detail_url = reverse("platform:tenant-detail", args=[self.office.id])

        response = self.client.post(
            detail_url,
            {
                "action": "contract",
                "plan": plan.id,
                "status": TenantContract.Status.ACTIVE,
                "monthly_price_brl": "249.90",
                "reference": "Proposta 1",
            },
        )

        contract = TenantContract.objects.get(organization=self.office)
        self.assertRedirects(response, detail_url)
        self.assertEqual(contract.monthly_price_cents, 24990)
        self.assertEqual(contract.status, TenantContract.Status.ACTIVE)

    def test_commercial_can_approve_a_zero_price_without_inheriting_the_plan_price(self):
        commercial = User.objects.create_user(
            email="commercial-zero@example.test", password="safe-password-123"
        )
        PlatformAccess.objects.create(user=commercial, role=PlatformAccess.Role.COMMERCIAL)
        plan = Plan.objects.create(code="trial-zero", name="Teste", monthly_price_cents=19_900)
        self.client.force_login(commercial)
        complete_mfa(self.client)

        response = self.client.post(
            reverse("platform:tenant-detail", args=[self.office.id]),
            {
                "action": "contract",
                "plan": plan.id,
                "status": TenantContract.Status.TRIAL,
                "monthly_price_brl": "0.00",
                "reference": "Teste aprovado",
            },
        )

        self.assertEqual(response.status_code, 302)
        contract = TenantContract.objects.get(organization=self.office)
        self.assertEqual(contract.monthly_price_cents, 0)
        self.assertTrue(contract.monthly_price_locked)

    def test_commercial_plan_change_updates_the_explicit_contract_module_snapshot(self):
        commercial = User.objects.create_user(
            email="commercial-snapshot@example.test", password="safe-password-123"
        )
        PlatformAccess.objects.create(user=commercial, role=PlatformAccess.Role.COMMERCIAL)
        previous_plan = Plan.objects.create(code="old-snapshot", name="Anterior", modules=["nfse"])
        new_plan = Plan.objects.create(code="new-snapshot", name="Novo", modules=["journey"])
        contract = TenantContract.objects.create(
            organization=self.office, plan=previous_plan, status=TenantContract.Status.ACTIVE
        )
        self.client.force_login(commercial)
        complete_mfa(self.client)

        response = self.client.post(
            reverse("platform:tenant-detail", args=[self.office.id]),
            {
                "action": "contract",
                "plan": new_plan.id,
                "status": TenantContract.Status.ACTIVE,
                "monthly_price_brl": "249.90",
                "reference": "Proposta atualizada",
            },
        )

        self.assertEqual(response.status_code, 302)
        contract.refresh_from_db()
        self.assertEqual(contract.plan_id, new_plan.id)
        self.assertEqual(contract.selected_modules, ["journey"])

    def test_commercial_configures_a_service_allowance_and_overage_cap(self):
        commercial = User.objects.create_user(
            email="commercial-rate@example.test", password="safe-password-123"
        )
        PlatformAccess.objects.create(user=commercial, role=PlatformAccess.Role.COMMERCIAL)
        plan = Plan.objects.create(code="integra-rate", name="Integra")
        TenantContract.objects.create(
            organization=self.office, plan=plan, status=TenantContract.Status.ACTIVE
        )
        self.client.force_login(commercial)
        complete_mfa(self.client)

        response = self.client.post(
            reverse("platform:tenant-detail", args=[self.office.id]),
            {
                "action": "service-rate",
                "service": "caixapostal.mensagens",
                "included_units": "100",
                "overage_price_brl": "1.25",
                "overage_cap_brl": "250.00",
                "overage_mode": TenantUsagePolicy.OverageMode.REQUIRE_APPROVAL,
            },
        )

        rate = TenantServiceRate.objects.get(
            contract__organization=self.office, action_code="caixapostal.mensagens"
        )
        policy = TenantUsagePolicy.objects.get(
            organization=self.office, action_code="caixapostal.mensagens"
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(rate.included_units, 100)
        self.assertEqual(rate.overage_unit_price_cents, 125)
        self.assertEqual(policy.monthly_overage_cap_cents, 25000)

    def test_support_issues_an_activation_that_is_delivered_by_email(self):
        detail_url = reverse("platform:tenant-detail", args=[self.office.id])

        response = self.client.post(
            detail_url,
            {
                "action": "invite",
                "invite-email": "owner@new.test",
                "invite-full_name": "Owner New",
                "invite-role": Membership.Role.OWNER,
            },
        )

        self.assertRedirects(response, detail_url)
        self.assertTrue(Invitation.objects.filter(email="owner@new.test").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@new.test"])
        self.assertIn("/ativar/", mail.outbox[0].body)
        self.assertNotIn("/ativar/", response.content.decode())

    def test_crmew_managed_support_needs_a_temporary_controller_grant(self):
        ControlPlaneBinding.objects.create(
            organization=self.office,
            remote_installation_id="5b3dd36b-4da4-4b7a-9f12-8e933c2ed0e4",
            controller_url="https://crmew.example.test",
            device_private_key="local-key",
            controller_public_key="controller-key",
        )
        endpoint = reverse("platform:start-support", args=[self.office.id])
        denied = self.client.post(endpoint, {"justification": "Diagnóstico autorizado."})
        RemoteSupportGrant.objects.create(
            organization=self.office,
            subject=self.developer.email,
            company_ids=[],
            justification="Incidente autorizado pelo CRMew",
            expires_at=timezone.now() + timedelta(minutes=10),
            source_hash="b" * 64,
        )
        granted = self.client.post(endpoint, {"justification": "Diagnóstico autorizado."})

        self.assertRedirects(denied, reverse("platform:tenant-detail", args=[self.office.id]))
        self.assertRedirects(granted, reverse("hub:dashboard"), fetch_redirect_response=False)
        self.assertTrue(SupportSession.objects.filter(organization=self.office).exists())

    def test_read_only_support_can_inspect_certificate_metadata_without_upload_controls(self):
        support_user = User.objects.create_user(
            email="support@example.test", password="safe-password-123"
        )
        PlatformAccess.objects.create(user=support_user, role=PlatformAccess.Role.SUPPORT)
        company = ClientCompany.objects.create(
            organization=self.office, name="Empresa para suporte", dominio_code="001"
        )
        Certificate.objects.create(
            organization=self.office,
            company=company,
            label="A1 produção",
            pfx_blob="encrypted-pfx-placeholder",
            password="encrypted-password-placeholder",
            fingerprint_sha256="a" * 64,
        )
        support = SupportSession.objects.create(
            organization=self.office,
            support_user=support_user,
            justification="Análise solicitada pelo escritório.",
            expires_at=timezone.now() + timedelta(minutes=20),
        )
        self.client.force_login(support_user)
        complete_mfa(self.client)
        session = self.client.session
        session["hub_support_session_id"] = str(support.id)
        session.save()

        page = self.client.get(reverse("hub:certificates"))
        blocked_post = self.client.post(reverse("hub:certificates"), {})

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "A1 produção")
        self.assertNotContains(page, 'data-modal-open="certificate-dialog"')
        self.assertEqual(blocked_post.status_code, 403)
        self.assertContains(blocked_post, "somente leitura", status_code=403)
        self.assertNotContains(blocked_post, "não manipula certificados", status_code=403)
