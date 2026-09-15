from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import quote

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.intelligence.agents import issue_enrollment, revoke_agent
from apps.intelligence.models import EdgeAgent, IntelligenceConnector
from apps.organizations.models import Organization


class EdgeAgentTests(TestCase):
    def setUp(self) -> None:
        self.organization = Organization.objects.create(name="Acme", slug="acme")
        self.client = Client()

    def test_enrollment_is_single_use_and_sync_requires_valid_signature(self) -> None:
        enrollment = issue_enrollment(organization=self.organization)
        enrolled = self.client.post(
            reverse("intelligence-agent-enroll"),
            data=json.dumps(
                {"code": enrollment.code, "label": "Servidor Domínio", "fingerprint": "device-fp"}
            ),
            content_type="application/json",
        )
        self.assertEqual(enrolled.status_code, 200)
        credentials = enrolled.json()
        reused = self.client.post(
            reverse("intelligence-agent-enroll"),
            data=json.dumps(
                {"code": enrollment.code, "label": "Outro", "fingerprint": "device-fp-2"}
            ),
            content_type="application/json",
        )
        self.assertEqual(reused.status_code, 403)

        body = json.dumps(
            {
                "companies": [
                    {"codigo": "001", "nome": "Empresa Agente", "cnpj_masked": "12.345.678/0001-90"}
                ]
            }
        ).encode()
        timestamp = str(int(timezone.now().timestamp()))
        signature = hmac.new(
            credentials["shared_secret"].encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        response = self.client.post(
            reverse("intelligence-agent-sync"),
            data=body,
            content_type="application/json",
            headers={
                "X-Hub-Agent-ID": credentials["agent_id"],
                "X-Hub-Agent-Timestamp": timestamp,
                "X-Hub-Agent-Signature": signature,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["created"], 1)

    def test_sync_completes_a_pending_on_demand_update(self) -> None:
        enrollment = issue_enrollment(organization=self.organization)
        credentials = self.client.post(
            reverse("intelligence-agent-enroll"),
            data=json.dumps({"code": enrollment.code, "label": "Servidor", "fingerprint": "fp"}),
            content_type="application/json",
        ).json()
        connector = IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.EDGE_AGENT,
            status="healthy",
            sync_requested_at=timezone.now(),
        )
        body = b'{"companies": []}'
        timestamp = str(int(timezone.now().timestamp()))
        signature = hmac.new(
            credentials["shared_secret"].encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            reverse("intelligence-agent-sync"),
            data=body,
            content_type="application/json",
            headers={
                "X-Hub-Agent-ID": credentials["agent_id"],
                "X-Hub-Agent-Timestamp": timestamp,
                "X-Hub-Agent-Signature": signature,
            },
        )

        connector.refresh_from_db()
        self.assertTrue(response.json()["requested_sync_completed"])
        self.assertIsNone(connector.sync_requested_at)
        self.assertIsNotNone(connector.sync_request_completed_at)

    def test_revoked_agent_cannot_sync(self) -> None:
        enrollment = issue_enrollment(organization=self.organization)
        enrolled = self.client.post(
            reverse("intelligence-agent-enroll"),
            data=json.dumps({"code": enrollment.code, "label": "Servidor", "fingerprint": "fp"}),
            content_type="application/json",
        ).json()
        agent = EdgeAgent.objects.get(id=enrolled["agent_id"])
        revoke_agent(agent=agent)
        body = b'{"companies": []}'
        timestamp = str(int(timezone.now().timestamp()))
        signature = hmac.new(
            enrolled["shared_secret"].encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()

        response = self.client.post(
            reverse("intelligence-agent-sync"),
            data=body,
            content_type="application/json",
            headers={
                "X-Hub-Agent-ID": enrolled["agent_id"],
                "X-Hub-Agent-Timestamp": timestamp,
                "X-Hub-Agent-Signature": signature,
            },
        )

        self.assertEqual(response.status_code, 401)

    @staticmethod
    def _client_certificate() -> tuple[str, str]:
        key = ed25519.Ed25519PrivateKey.generate()
        now = datetime.now(UTC)
        certificate = (
            x509.CertificateBuilder()
            .subject_name(
                x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "hub-agent-test")])
            )
            .issuer_name(
                x509.Name([x509.NameAttribute(x509.NameOID.COMMON_NAME, "hub-agent-test")])
            )
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(days=1))
            .sign(key, algorithm=None)
        )
        return (
            certificate.public_bytes(serialization.Encoding.PEM).decode(),
            certificate.fingerprint(hashes.SHA256()).hex(),
        )

    @override_settings(EDGE_AGENT_MTLS_REQUIRED=True)
    def test_sync_requires_the_proxy_verified_enrolled_client_certificate(self) -> None:
        certificate_pem, certificate_sha256 = self._client_certificate()
        enrollment = issue_enrollment(organization=self.organization)
        enrolled = self.client.post(
            reverse("intelligence-agent-enroll"),
            data=json.dumps(
                {
                    "code": enrollment.code,
                    "label": "Servidor mTLS",
                    "fingerprint": "device-fp",
                    "mtls_certificate_sha256": certificate_sha256,
                }
            ),
            content_type="application/json",
        ).json()
        body = b'{"companies": []}'
        timestamp = str(int(timezone.now().timestamp()))
        signature = hmac.new(
            enrolled["shared_secret"].encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        headers = {
            "X-Hub-Agent-ID": enrolled["agent_id"],
            "X-Hub-Agent-Timestamp": timestamp,
            "X-Hub-Agent-Signature": signature,
        }
        without_certificate = self.client.post(
            reverse("intelligence-agent-sync"),
            data=body,
            content_type="application/json",
            headers=headers,
        )
        accepted = self.client.post(
            reverse("intelligence-agent-sync"),
            data=body,
            content_type="application/json",
            headers={
                **headers,
                "X-Hub-MTLS-Verified": "SUCCESS",
                "X-Hub-MTLS-Client-Cert": quote(certificate_pem),
            },
        )

        self.assertEqual(without_certificate.status_code, 401)
        self.assertEqual(accepted.status_code, 200)
