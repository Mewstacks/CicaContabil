from __future__ import annotations

import base64
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.controlplane import (
    ControlPlaneError,
    acknowledge_release,
    apply_control,
    authorization_is_fresh,
    canonical_json,
    companies_for_membership,
    company_has_capability,
    generate_device_private_key,
    normalize_controller_url,
    send_heartbeat,
    sync_binding,
)
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    ControlPlaneBinding,
    ProductModule,
    RemoteSupportGrant,
)
from apps.intelligence.models import AssistantSettings, ClaudeFallbackApproval
from apps.organizations.models import Membership, Organization


class ControlPlaneIntelligencePolicyTests(TestCase):
    databases = {"default", "knowledge"}

    def test_controller_url_requires_https_without_embedded_path_or_credentials(self) -> None:
        self.assertEqual(
            normalize_controller_url("https://crmew.example.test/"),
            "https://crmew.example.test",
        )
        for unsafe_url in (
            "file:///etc/passwd",
            "https://user:password@crmew.example.test",
            "https://crmew.example.test/control/v1",
            "http://crmew.example.test",
        ):
            with self.assertRaises(ControlPlaneError):
                normalize_controller_url(unsafe_url)

    @override_settings(DEBUG=True)
    def test_controller_url_allows_loopback_http_only_for_local_development(self) -> None:
        self.assertEqual(
            normalize_controller_url("http://127.0.0.1:8000"),
            "http://127.0.0.1:8000",
        )

    def setUp(self) -> None:
        self.user = User.objects.create_user("owner@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        self.controller_key = Ed25519PrivateKey.generate()
        controller_public = (
            base64.urlsafe_b64encode(self.controller_key.public_key().public_bytes_raw())
            .decode()
            .rstrip("=")
        )
        self.binding = ControlPlaneBinding.objects.create(
            organization=self.organization,
            remote_installation_id="993c7a48-8ac1-4d51-8d64-3c741c12f2fd",
            controller_url="https://crmew.example.test",
            device_private_key=generate_device_private_key(),
            controller_public_key=controller_public,
        )

    def control(self, *, intelligence: object | None, version: int = 1) -> dict[str, object]:
        configuration: dict[str, object] = {"modules": []}
        if intelligence is not None:
            configuration["intelligence"] = intelligence
        return {
            "installation_id": str(self.binding.remote_installation_id),
            "hub_organization_id": str(self.organization.id),
            "expires_at": (timezone.now() + timedelta(minutes=10)).isoformat(),
            "configuration_version": version,
            "status": "active",
            "access_grants": [],
            "configuration": configuration,
            "support_grants": [],
        }

    def apply(self, control: dict[str, object]) -> None:
        signature = (
            base64.urlsafe_b64encode(self.controller_key.sign(canonical_json(control)))
            .decode()
            .rstrip("=")
        )
        apply_control(self.binding, control, signature)

    def test_signed_policy_projects_limits_but_keeps_local_key_local(self) -> None:
        AssistantSettings.objects.create(
            organization=self.organization,
            claude_api_key="local-key-never-sent-to-crmew",
        )
        self.apply(
            self.control(
                intelligence={
                    "claude": {
                        "enabled": True,
                        "allow_full_data": False,
                        "allowed_roles": [Membership.Role.OWNER, Membership.Role.ADMIN],
                        "model": "claude-sonnet-4-20250514",
                        "max_request_cents": 35,
                        "offline_curation_enabled": True,
                        "curation_max_batch_requests": 100,
                        "approval": {
                            "status": "approved",
                            "daily_limit_cents": 500,
                            "monthly_limit_cents": 4_000,
                            "valid_until": (timezone.now() + timedelta(days=30)).isoformat(),
                        },
                    }
                }
            )
        )

        policy = AssistantSettings.objects.get(organization=self.organization)
        approval = ClaudeFallbackApproval.objects.get(organization=self.organization)
        self.assertTrue(policy.claude_fallback_enabled)
        self.assertEqual(policy.claude_api_key, "local-key-never-sent-to-crmew")
        self.assertEqual(
            policy.claude_allowed_roles, [Membership.Role.OWNER, Membership.Role.ADMIN]
        )
        self.assertEqual(policy.claude_model, "claude-sonnet-4-20250514")
        self.assertEqual(policy.claude_max_request_cents, 35)
        self.assertTrue(policy.claude_offline_curation_enabled)
        self.assertEqual(policy.claude_curation_max_batch_requests, 100)
        self.assertEqual(approval.status, ClaudeFallbackApproval.Status.APPROVED)
        self.assertEqual(approval.daily_limit_cents, 500)
        self.assertIsNone(approval.approved_by)

    def test_missing_policy_revokes_a_previously_enabled_fallback(self) -> None:
        AssistantSettings.objects.create(
            organization=self.organization,
            claude_fallback_enabled=True,
            claude_allowed_roles=[Membership.Role.OWNER],
            claude_api_key="local-key-stays-local",
            claude_model="claude-sonnet-4-20250514",
            claude_max_request_cents=35,
        )
        ClaudeFallbackApproval.objects.create(
            organization=self.organization,
            status=ClaudeFallbackApproval.Status.APPROVED,
            daily_limit_cents=500,
            monthly_limit_cents=4_000,
        )
        self.apply(self.control(intelligence=None))

        policy = AssistantSettings.objects.get(organization=self.organization)
        approval = ClaudeFallbackApproval.objects.get(organization=self.organization)
        self.assertFalse(policy.claude_fallback_enabled)
        self.assertEqual(policy.claude_api_key, "local-key-stays-local")
        self.assertEqual(policy.claude_allowed_roles, [])
        self.assertEqual(policy.claude_model, "")
        self.assertFalse(policy.claude_offline_curation_enabled)
        self.assertEqual(policy.claude_curation_max_batch_requests, 0)
        self.assertEqual(approval.status, ClaudeFallbackApproval.Status.REVOKED)
        self.assertEqual(approval.daily_limit_cents, 0)

    def test_invalid_signed_policy_is_rejected_without_changing_existing_policy(self) -> None:
        settings = AssistantSettings.objects.create(
            organization=self.organization,
            claude_fallback_enabled=True,
            claude_model="claude-sonnet-4-20250514",
        )
        invalid = self.control(
            intelligence={
                "claude": {
                    "enabled": True,
                    "allowed_roles": ["not-a-role"],
                    "model": "claude-sonnet-4-20250514",
                    "max_request_cents": 35,
                }
            }
        )

        with self.assertRaises(ControlPlaneError):
            self.apply(invalid)

        settings.refresh_from_db()
        self.assertTrue(settings.claude_fallback_enabled)
        self.assertEqual(settings.claude_model, "claude-sonnet-4-20250514")

    def test_signed_control_syncs_modules_company_grants_and_expiring_support(self) -> None:
        company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa atendida", dominio_code="001"
        )
        support_expiry = timezone.now() + timedelta(minutes=5)
        self.apply(
            {
                **self.control(intelligence=None),
                "configuration": {"modules": [ProductModule.Code.GUIDES]},
                "access_grants": [
                    {
                        "subject": self.user.email,
                        "role": Membership.Role.MANAGER,
                        "company_ids": [str(company.id)],
                        "modules": [ProductModule.Code.GUIDES],
                        "capabilities": ["read"],
                    }
                ],
                "support_grants": [
                    {
                        "subject": "support@hubcontador.test",
                        "justification": "Incidente de sincronização",
                        "company_ids": [str(company.id)],
                        "expires_at": support_expiry.isoformat(),
                    }
                ],
            }
        )

        self.membership = Membership.objects.get(organization=self.organization, user=self.user)
        self.assertEqual(self.membership.role, Membership.Role.MANAGER)
        self.assertEqual(companies_for_membership(self.membership), [company])
        self.assertTrue(
            ProductModule.objects.get(
                organization=self.organization, code=ProductModule.Code.GUIDES
            ).enabled
        )
        self.assertFalse(
            ProductModule.objects.get(
                organization=self.organization, code=ProductModule.Code.NFSE
            ).enabled
        )
        self.assertEqual(
            CompanyAccessGrant.objects.get(organization=self.organization).capabilities, ["read"]
        )
        self.assertEqual(
            RemoteSupportGrant.objects.filter(organization=self.organization).count(), 1
        )

    def test_control_rejects_expired_wrong_target_and_regressive_versions(self) -> None:
        invalid_controls = [
            {**self.control(intelligence=None), "installation_id": str(uuid4())},
            {**self.control(intelligence=None), "hub_organization_id": str(uuid4())},
            {
                **self.control(intelligence=None),
                "expires_at": (timezone.now() - timedelta(seconds=1)).isoformat(),
            },
        ]
        for control in invalid_controls:
            with self.assertRaises(ControlPlaneError):
                self.apply(control)

        self.binding.applied_configuration_version = 2
        self.binding.save(update_fields=["applied_configuration_version"])
        with self.assertRaises(ControlPlaneError):
            self.apply(self.control(intelligence=None, version=1))

    def test_authorization_freshness_and_unmanaged_company_access(self) -> None:
        self.binding.delete()
        member = Membership.objects.get(organization=self.organization, user=self.user)
        company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa local", dominio_code="local"
        )
        self.assertTrue(authorization_is_fresh(self.organization))
        self.assertEqual(companies_for_membership(member), [company])

        ControlPlaneBinding.objects.create(
            organization=self.organization,
            remote_installation_id=uuid4(),
            controller_url="https://crmew.example.test",
            device_private_key=generate_device_private_key(),
            controller_public_key="controller-key",
            cache_expires_at=timezone.now() - timedelta(seconds=1),
        )
        self.assertFalse(authorization_is_fresh(self.organization))
        self.assertEqual(companies_for_membership(member), [])

    def test_expired_control_cache_revokes_previously_projected_company_grants(self) -> None:
        company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa autorizada", dominio_code="001"
        )
        membership = Membership.objects.get(organization=self.organization, user=self.user)
        CompanyAccessGrant.objects.create(
            organization=self.organization,
            membership=membership,
            company=company,
            modules=[ProductModule.Code.GUIDES],
            capabilities=["read"],
        )
        self.binding.cache_expires_at = timezone.now() - timedelta(seconds=1)
        self.binding.save(update_fields=["cache_expires_at"])

        self.assertEqual(companies_for_membership(membership), [])

    def test_managed_grant_requires_an_explicit_capability(self) -> None:
        company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa autorizada", dominio_code="001"
        )
        membership = Membership.objects.get(organization=self.organization, user=self.user)
        self.binding.cache_expires_at = timezone.now() + timedelta(minutes=10)
        self.binding.save(update_fields=["cache_expires_at"])
        CompanyAccessGrant.objects.create(
            organization=self.organization,
            membership=membership,
            company=company,
            modules=[ProductModule.Code.GUIDES],
            capabilities=["read"],
        )

        self.assertTrue(
            company_has_capability(membership=membership, company=company, capability="read")
        )
        self.assertFalse(
            company_has_capability(membership=membership, company=company, capability="draft")
        )

    @patch("apps.hub.controlplane._fetch_json")
    def test_sync_and_heartbeat_use_signed_transport_and_persist_only_error_metadata(
        self, mocked_fetch
    ) -> None:
        control = self.control(intelligence=None)
        signature = (
            base64.urlsafe_b64encode(self.controller_key.sign(canonical_json(control)))
            .decode()
            .rstrip("=")
        )
        mocked_fetch.side_effect = [
            {"control": control, "signature": signature},
            {"status": "accepted"},
            {"status": "accepted"},
        ]

        sync_binding(self.binding)
        send_heartbeat(
            self.binding,
            release="release-1",
            health="healthy",
            sync_lag_seconds=-10,
            error_fingerprint="connector-error",
        )

        state_request = mocked_fetch.call_args_list[0].args[0]
        acknowledgement_request = mocked_fetch.call_args_list[1].args[0]
        heartbeat_request = mocked_fetch.call_args_list[2].args[0]
        self.assertTrue(state_request.full_url.endswith("/control/v1/state/"))
        self.assertTrue(acknowledgement_request.full_url.endswith("/control/v1/configuration-ack/"))
        self.assertIn(b'"configuration_version":1', acknowledgement_request.data)
        self.assertTrue(heartbeat_request.full_url.endswith("/control/v1/heartbeat/"))
        self.assertIn("X-hub-signature", heartbeat_request.headers)
        self.assertIn(b'"applied_configuration_version":1', heartbeat_request.data)
        self.assertIn(b'"sync_lag_seconds":0', heartbeat_request.data)

    @patch("apps.hub.controlplane._fetch_json", side_effect=ControlPlaneError("offline"))
    def test_sync_failure_is_recorded_without_disabling_local_data(self, _mocked_fetch) -> None:
        with self.assertRaises(ControlPlaneError):
            sync_binding(self.binding)
        self.binding.refresh_from_db()
        self.assertEqual(self.binding.last_sync_error, "offline")

    @patch("apps.hub.controlplane._fetch_json", return_value={"status": "accepted"})
    def test_release_ack_is_signed_and_contains_only_release_metadata(self, mocked_fetch) -> None:
        acknowledge_release(
            self.binding,
            version="ghcr.io/acme/hub@sha256:" + "a" * 64,
            outcome="rolled_back",
            diagnostics={"health": "failed"},
        )

        request = mocked_fetch.call_args.args[0]
        self.assertTrue(request.full_url.endswith("/control/v1/release-ack/"))
        self.assertIn(b'"outcome":"rolled_back"', request.data)
        self.assertIn(b'"health":"failed"', request.data)
        self.assertIn("X-hub-signature", request.headers)

    @patch("apps.hub.controlplane._fetch_json", return_value={"status": "rejected"})
    def test_release_ack_rejects_invalid_input_and_controller_rejection(
        self, _mocked_fetch
    ) -> None:
        with self.assertRaises(ControlPlaneError):
            acknowledge_release(self.binding, version="", outcome="released")
        with self.assertRaises(ControlPlaneError):
            acknowledge_release(self.binding, version="release-1", outcome="unknown")
        with self.assertRaises(ControlPlaneError):
            acknowledge_release(self.binding, version="release-1", outcome="failed")
