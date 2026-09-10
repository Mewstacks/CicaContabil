from __future__ import annotations

import json
from unittest.mock import patch
from urllib.error import URLError

from django.test import SimpleTestCase, override_settings

from apps.hub.monitoring import _clean_tags, send_mewguard_posture, send_mewpulse_event


class _Response:
    def __enter__(self) -> _Response:
        return self

    def __exit__(self, *args: object) -> None:
        return None


class HubMonitoringTests(SimpleTestCase):
    def test_sensitive_tag_names_are_dropped(self) -> None:
        self.assertEqual(
            _clean_tags({"component": "hub", "cpf": "hidden", "token_hint": "hidden"}),
            {"component": "hub"},
        )

    def test_unconfigured_telemetry_is_a_non_blocking_noop(self) -> None:
        self.assertFalse(send_mewpulse_event(component="hub", event="sync"))
        self.assertFalse(send_mewguard_posture(component="hub", release="test", dependency_count=1))

    @override_settings(MEWPULSE_INGEST_URL="https://pulse.example.test", MEWPULSE_INGEST_TOKEN="t")
    @patch("apps.hub.monitoring.urlopen", return_value=_Response())
    def test_mewpulse_sends_metadata_without_sensitive_fields(self, mocked_urlopen) -> None:
        self.assertTrue(
            send_mewpulse_event(
                component="connector", event="failed", tenant_ref="tenant", release="v1"
            )
        )

        request = mocked_urlopen.call_args.args[0]
        payload = json.loads(request.data)
        self.assertEqual(payload["events"][0]["tags"]["component"], "connector")
        self.assertNotIn("payload", json.dumps(payload))

    @override_settings(MEWGUARD_POSTURE_URL="https://guard.example.test", MEWPULSE_INGEST_TOKEN="t")
    @patch("apps.hub.monitoring.urlopen", side_effect=URLError("offline"))
    def test_mewguard_network_failure_never_raises(self, _mocked_urlopen) -> None:
        self.assertFalse(send_mewguard_posture(component="hub", release="v1", dependency_count=42))

    @override_settings(MEWGUARD_POSTURE_URL="https://guard.example.test", MEWPULSE_INGEST_TOKEN="t")
    @patch("apps.hub.monitoring.urlopen", return_value=_Response())
    def test_mewguard_posts_only_runtime_posture(self, mocked_urlopen) -> None:
        self.assertTrue(send_mewguard_posture(component="hub", release="v1", dependency_count=42))

        payload = json.loads(mocked_urlopen.call_args.args[0].data)
        self.assertEqual(payload["dependencies"], {"count": 42})
        self.assertNotIn("secret", json.dumps(payload))
