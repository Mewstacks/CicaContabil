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
from apps.organizations.models import Membership, Organization
from apps.platform.models import Invitation, PlatformAccess, SupportSession
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

    def test_platform_account_menu_has_only_account_actions(self):
        response = self.client.get(reverse("platform:dashboard"))

        self.assertContains(response, 'data-popover-toggle="account-list"')
        self.assertContains(response, "Sair")
        self.assertNotContains(response, "Abrir Hub")

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

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Invitation.objects.filter(email="owner@new.test").exists())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@new.test"])
        self.assertIn("/ativar/", mail.outbox[0].body)
        self.assertNotContains(response, "/ativar/")

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
