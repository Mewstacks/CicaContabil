from __future__ import annotations

import base64
import os
from io import StringIO
from unittest.mock import patch
from uuid import uuid4

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase

from apps.hub.controlplane import ControlPlaneError, generate_device_private_key
from apps.hub.models import ControlPlaneBinding
from apps.intelligence.models import IntelligenceConnector
from apps.organizations.models import Organization


class HubOperationsCommandTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        self.binding = ControlPlaneBinding.objects.create(
            organization=self.organization,
            remote_installation_id=uuid4(),
            controller_url="https://crmew.example.test",
            device_private_key=generate_device_private_key(),
            controller_public_key=base64.urlsafe_b64encode(
                Ed25519PrivateKey.generate().public_key().public_bytes_raw()
            )
            .decode()
            .rstrip("="),
        )

    @patch("apps.hub.management.commands.sync_control_plane.sync_binding")
    def test_sync_command_updates_every_binding(self, mocked_sync) -> None:
        output = StringIO()

        call_command("sync_control_plane", stdout=output)

        mocked_sync.assert_called_once_with(self.binding)
        self.assertIn("controle atualizado", output.getvalue())

    @patch(
        "apps.hub.management.commands.sync_control_plane.sync_binding",
        side_effect=ControlPlaneError("offline"),
    )
    def test_sync_command_reports_failed_installation(self, _mocked_sync) -> None:
        with self.assertRaises(CommandError):
            call_command("sync_control_plane", stderr=StringIO())

    @patch("apps.hub.management.commands.heartbeat_control_plane.send_heartbeat")
    def test_heartbeat_reports_only_health_metadata(self, mocked_heartbeat) -> None:
        IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="error",
            sync_lag_seconds=72,
        )
        previous_release = os.environ.get("SENTRY_RELEASE")
        os.environ["SENTRY_RELEASE"] = "test-release"
        try:
            call_command("heartbeat_control_plane", stdout=StringIO())
        finally:
            if previous_release is None:
                os.environ.pop("SENTRY_RELEASE", None)
            else:
                os.environ["SENTRY_RELEASE"] = previous_release

        mocked_heartbeat.assert_called_once_with(
            self.binding,
            release="test-release",
            health="degraded",
            sync_lag_seconds=72,
            error_fingerprint="connector-unhealthy",
        )

    @patch("apps.hub.management.commands.heartbeat_control_plane.send_heartbeat")
    def test_heartbeat_failure_is_non_fatal(self, mocked_heartbeat) -> None:
        mocked_heartbeat.side_effect = ControlPlaneError("offline")
        errors = StringIO()

        call_command("heartbeat_control_plane", stderr=errors)

        self.assertIn("heartbeat", errors.getvalue())

    @patch("apps.hub.management.commands.acknowledge_control_release.acknowledge_release")
    def test_release_ack_reports_an_outcome_without_customer_content(
        self, mocked_acknowledge
    ) -> None:
        call_command(
            "acknowledge_control_release",
            release="ghcr.io/acme/hub@sha256:" + "a" * 64,
            outcome="released",
            stdout=StringIO(),
        )

        mocked_acknowledge.assert_called_once_with(
            self.binding,
            version="ghcr.io/acme/hub@sha256:" + "a" * 64,
            outcome="released",
        )

    @patch(
        "apps.hub.management.commands.acknowledge_control_release.acknowledge_release",
        side_effect=ControlPlaneError("offline"),
    )
    def test_release_ack_reports_controller_failure(self, _mocked_acknowledge) -> None:
        errors = StringIO()

        with self.assertRaises(CommandError):
            call_command(
                "acknowledge_control_release",
                release="release-1",
                outcome="failed",
                stderr=errors,
            )

        self.assertIn("offline", errors.getvalue())

    @patch("apps.hub.management.commands.enroll_control_plane.apply_control")
    @patch("apps.hub.management.commands.enroll_control_plane._fetch_json")
    def test_enrollment_creates_a_local_trust_anchor_from_controller_response(
        self, mocked_fetch, mocked_apply
    ) -> None:
        self.binding.delete()
        controller_key = Ed25519PrivateKey.generate()
        mocked_fetch.return_value = {
            "installation_id": str(uuid4()),
            "controller_public_key": base64.urlsafe_b64encode(
                controller_key.public_key().public_bytes_raw()
            )
            .decode()
            .rstrip("="),
            "control": {"safe": "signed-by-controller"},
            "signature": "signature",
        }
        previous_code = os.environ.get("HUB_CONTROL_ENROLLMENT_CODE")
        os.environ["HUB_CONTROL_ENROLLMENT_CODE"] = "one-time-code"
        try:
            call_command(
                "enroll_control_plane",
                organization=str(self.organization.id),
                controller_url="https://crmew.example.test",
                stdout=StringIO(),
            )
        finally:
            if previous_code is None:
                os.environ.pop("HUB_CONTROL_ENROLLMENT_CODE", None)
            else:
                os.environ["HUB_CONTROL_ENROLLMENT_CODE"] = previous_code

        binding = ControlPlaneBinding.objects.get(organization=self.organization)
        self.assertEqual(binding.controller_url, "https://crmew.example.test")
        mocked_apply.assert_called_once()
        request = mocked_fetch.call_args.args[0]
        self.assertNotIn("one-time-code", request.full_url)
        self.assertIn(b'"code":"one-time-code"', request.data)

    def test_enrollment_requires_environment_secret_and_valid_origin(self) -> None:
        with self.assertRaises(CommandError):
            call_command(
                "enroll_control_plane",
                organization=str(self.organization.id),
                controller_url="https://crmew.example.test",
            )

        os.environ["HUB_CONTROL_ENROLLMENT_CODE"] = "one-time-code"
        try:
            with self.assertRaises(CommandError):
                call_command(
                    "enroll_control_plane",
                    organization=str(self.organization.id),
                    controller_url="http://untrusted.example.test",
                )
        finally:
            os.environ.pop("HUB_CONTROL_ENROLLMENT_CODE", None)
