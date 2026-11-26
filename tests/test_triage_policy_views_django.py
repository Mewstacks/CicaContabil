"""Interruptores de entrada por escritório: só o administrador muda; um não afeta outro."""

from __future__ import annotations

from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import CompanyAccessGrant, ProductModule
from apps.organizations.models import Membership
from apps.triage.intake_policy import policy_for
from apps.triage.models import DestinationProfile, TriagePolicy
from triage_v2_support import TriageV2Case


class PolicyViewTests(TriageV2Case):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        super().setUp()
        self.login()
        self.url = reverse("hub:triage-policy")

    def test_defaults_keep_everything_off(self) -> None:
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        policy = policy_for(self.office)
        self.assertFalse(policy.extended_formats or policy.open_archives or policy.ocr_enabled)

    def test_admin_saves_and_the_policy_takes_effect(self) -> None:
        response = self.client.post(self.url, {"open_archives": "on", "ocr_monthly_pages": "50"})
        self.assertRedirects(response, self.url)
        policy = TriagePolicy.objects.get(organization=self.office)
        self.assertTrue(policy.open_archives)
        self.assertFalse(policy.extended_formats)
        self.assertEqual(policy.ocr_monthly_pages, 50)
        self.assertIn(".zip", policy_for(self.office).suffixes)

    def test_other_office_is_unaffected(self) -> None:
        other = self.make_office("e11-policy-other")
        self.client.post(self.url, {"open_archives": "on", "extended_formats": "on"})
        self.assertNotIn(".zip", policy_for(other).suffixes)
        self.assertFalse(TriagePolicy.objects.filter(organization=other).exists())

    def test_invalid_budget_is_refused(self) -> None:
        self.assertEqual(self.client.post(self.url, {"ocr_monthly_pages": "-1"}).status_code, 400)
        self.assertFalse(TriagePolicy.objects.exists())

    def test_inbox_folder_needs_a_path_and_is_saved_with_its_window(self) -> None:
        self.assertEqual(self.client.post(self.url, {"inbox_watch_enabled": "on"}).status_code, 400)
        DestinationProfile.objects.filter(organization=self.office).update(
            mode=DestinationProfile.Mode.WINDOWS, windows_root=r"D:\Clientes"
        )
        outside = self.client.post(
            self.url, {"inbox_watch_enabled": "on", "inbox_watch_path": r"C:\Windows"}
        )
        self.assertEqual(outside.status_code, 400)
        response = self.client.post(
            self.url,
            {
                "inbox_watch_enabled": "on",
                "inbox_watch_path": r"D:\Clientes\Entrada",
                "inbox_stable_seconds": "45",
            },
        )
        self.assertRedirects(response, self.url)
        policy = TriagePolicy.objects.get(organization=self.office)
        self.assertTrue(policy.inbox_watch_enabled)
        self.assertEqual(policy.inbox_stable_seconds, 45)

    def test_scanner_state_is_shown_and_off_without_a_daemon(self) -> None:
        response = self.client.get(self.url)
        self.assertContains(response, 'data-scanner-state="off"')

    def test_operator_cannot_change_it(self) -> None:
        user = User.objects.create_user("op-pol@office.test", "safe-password-123")
        membership = Membership.objects.create(
            organization=self.office, user=user, role=Membership.Role.OPERATOR
        )
        CompanyAccessGrant.objects.create(
            organization=self.office,
            membership=membership,
            company=self.company,
            modules=[ProductModule.Code.TRIAGE],
            capabilities=["read"],
        )
        self.login(user)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.client.post(self.url, {"open_archives": "on"}).status_code, 403)
        self.assertFalse(TriagePolicy.objects.exists())

    def test_demo_office_is_read_only(self) -> None:
        self.office.is_demo = True
        self.office.save()
        self.assertEqual(self.client.post(self.url, {"open_archives": "on"}).status_code, 403)


class PolicyAutoAndEngineTests(TriageV2Case):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        super().setUp()
        self.login()
        self.url = reverse("hub:triage-policy")

    def test_auto_approval_defaults_off_and_is_saved_per_office(self) -> None:
        self.assertFalse(policy_for(self.office).auto_approve)
        self.client.post(
            self.url, {"auto_approve": "on", "auto_sample_every": "5", "auto_warmup": "12"}
        )
        policy = policy_for(self.office)
        self.assertEqual(
            (policy.auto_approve, policy.auto_sample_every, policy.auto_warmup), (True, 5, 12)
        )
        other = self.make_office("e11-policy-auto-other")
        self.assertFalse(policy_for(other).auto_approve)

    def test_invalid_sample_is_refused(self) -> None:
        self.assertEqual(self.client.post(self.url, {"auto_sample_every": "0"}).status_code, 400)

    def test_reclassify_bumps_the_engine_version_of_this_office_only(self) -> None:
        other = self.make_office("e11-policy-engine-other")
        self.client.post(self.url, {"action": "reclassify"})
        self.assertEqual(policy_for(self.office).engine_version, 2)
        self.assertEqual(policy_for(other).engine_version, 1)

    def test_reclassify_is_admin_only(self) -> None:
        user = User.objects.create_user("op-eng@office.test", "safe-password-123")
        Membership.objects.create(
            organization=self.office, user=user, role=Membership.Role.OPERATOR
        )
        self.login(user)
        self.assertEqual(self.client.post(self.url, {"action": "reclassify"}).status_code, 403)
        self.assertEqual(policy_for(self.office).engine_version, 1)
