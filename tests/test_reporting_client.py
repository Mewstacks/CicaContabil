from __future__ import annotations

import hashlib
from email.message import Message
from unittest.mock import patch

from django.test import SimpleTestCase
from django.test.utils import override_settings

from apps.intelligence.reporting_client import ReportingServiceUnavailable, render_snapshot


class _Response:
    def __init__(self, payload: bytes, content_type: str, output_hash: str) -> None:
        self._payload = payload
        self.headers = Message()
        self.headers["Content-Type"] = content_type
        self.headers["X-CICA-Report-Hash"] = output_hash

    def __enter__(self) -> _Response:
        return self

    def __exit__(self, exc_type: object, exc: object, traceback: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


class ReportingClientTests(SimpleTestCase):
    snapshot = {
        "organizationId": "office-test",
        "reportName": "Relatório",
        "generatedAt": "2026-09-23T14:00:00Z",
        "periodLabel": "09/2026",
        "preliminary": False,
        "pendingNotes": [],
        "rows": [],
    }

    @override_settings(CICA_REPORTING_URL="")
    def test_unconfigured_renderer_is_explicitly_unavailable(self) -> None:
        with self.assertRaises(ReportingServiceUnavailable):
            render_snapshot(snapshot=self.snapshot, export_format="pdf")

    @override_settings(CICA_REPORTING_URL="file:///tmp/renderer")
    def test_rejects_non_http_renderer_url(self) -> None:
        with self.assertRaises(ReportingServiceUnavailable):
            render_snapshot(snapshot=self.snapshot, export_format="pdf")

    @override_settings(CICA_REPORTING_URL="http://127.0.0.1:3080")
    def test_rejects_missing_service_secret(self) -> None:
        with self.assertRaises(ReportingServiceUnavailable):
            render_snapshot(snapshot=self.snapshot, export_format="pdf")

    @override_settings(
        CICA_REPORTING_URL="http://127.0.0.1:3080", CICA_REPORTING_SHARED_SECRET="test-secret"
    )
    @patch("apps.intelligence.reporting_client.urlopen")
    def test_accepts_only_matching_type_and_hash(self, urlopen: object) -> None:
        payload = b"%PDF-node"
        response = _Response(payload, "application/pdf", hashlib.sha256(payload).hexdigest())
        assert hasattr(urlopen, "return_value")
        urlopen.return_value = response  # type: ignore[attr-defined]

        result = render_snapshot(snapshot=self.snapshot, export_format="pdf")

        self.assertEqual(result, payload)
        request = urlopen.call_args.args[0]  # type: ignore[attr-defined]
        self.assertEqual(request.headers["X-cica-reporting-secret"], "test-secret")

    @override_settings(
        CICA_REPORTING_URL="http://127.0.0.1:3080",
        CICA_REPORTING_SHARED_SECRET="new-secret",
        CICA_REPORTING_PREVIOUS_SHARED_SECRET="old-secret",
    )
    @patch("apps.intelligence.reporting_client.urlopen")
    def test_django_uses_only_the_active_secret_during_rotation(self, urlopen: object) -> None:
        payload = b"%PDF-node"
        response = _Response(payload, "application/pdf", hashlib.sha256(payload).hexdigest())
        assert hasattr(urlopen, "return_value")
        urlopen.return_value = response  # type: ignore[attr-defined]

        self.assertEqual(render_snapshot(snapshot=self.snapshot, export_format="pdf"), payload)

        request = urlopen.call_args.args[0]  # type: ignore[attr-defined]
        self.assertEqual(request.headers["X-cica-reporting-secret"], "new-secret")

    @override_settings(
        CICA_REPORTING_URL="http://127.0.0.1:3080", CICA_REPORTING_SHARED_SECRET="test-secret"
    )
    @patch("apps.intelligence.reporting_client.urlopen")
    def test_rejects_mismatched_hash(self, urlopen: object) -> None:
        response = _Response(b"%PDF-node", "application/pdf", "0" * 64)
        assert hasattr(urlopen, "return_value")
        urlopen.return_value = response  # type: ignore[attr-defined]

        with self.assertRaises(ReportingServiceUnavailable):
            render_snapshot(snapshot=self.snapshot, export_format="pdf")
