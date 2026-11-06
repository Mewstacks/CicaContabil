"""Synthetic CA/enrollment/mTLS verification, with no business endpoints or secrets."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import timedelta
from urllib.parse import quote

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.intelligence.agents import issue_enrollment, revoke_agent
from apps.intelligence.models import AgentEnrollment, EdgeAgent

pytestmark = pytest.mark.django_db
GATEWAY = "synthetic-private-gateway-secret-over-32"


def private_bytes(key):
    return key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    )


def ca_certificate(key, *, expired=False, ca=True):
    now = timezone.now()
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic test CA")])
    return (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=2))
        .not_valid_after(now + timedelta(days=-1 if expired else 30))
        .add_extension(x509.BasicConstraints(ca=ca, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=False,
                content_commitment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=None,
                decipher_only=None,
            ),
            critical=True,
        )
        .sign(key, hashes.SHA256())
    )


@pytest.fixture
def authority(tmp_path, settings):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    cert = ca_certificate(key)
    cert_path = tmp_path / "ca.pem"
    key_path = tmp_path / "key.pem"
    cert_path.write_bytes(cert.public_bytes(serialization.Encoding.PEM))
    key_path.write_bytes(private_bytes(key))
    settings.EDGE_AGENT_CA_CERT_PATH = str(cert_path)
    settings.EDGE_AGENT_CA_KEY_PATH = str(key_path)
    return key, cert, cert_path, key_path


def csr(key_size=2048):
    key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
    request = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Synthetic Windows")]))
        .sign(key, hashes.SHA256())
    )
    return key, request.public_bytes(serialization.Encoding.PEM).decode()


def enroll(organization, request):
    enrollment = issue_enrollment(organization=organization)
    payload = {
        "code": enrollment.code,
        "label": "Windows synthetic",
        "fingerprint": "test",
        "csr": request,
    }
    response = Client().post(
        reverse("agent-v2-enroll"), data=json.dumps(payload), content_type="application/json",
        secure=True,
    )
    return enrollment, payload, response


def signed(credentials, payload=None, headers=None):
    body = json.dumps(payload or {}).encode()
    timestamp = str(int(timezone.now().timestamp()))
    signature = hmac.new(
        credentials["shared_secret"].encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return Client().post(
        reverse("agent-v2-heartbeat"),
        data=body,
        content_type="application/json",
        headers={
            "X-Hub-Agent-ID": credentials["agent_id"],
            "X-Hub-Agent-Timestamp": timestamp,
            "X-Hub-Agent-Signature": signature,
            **(headers or {}),
        },
        secure=True,
    )


def test_v2_enrollment_is_single_use_issues_client_certificate_and_caps_ca_lifetime(
    authority, organization
):
    _, ca, _, _ = authority
    _, request = csr()
    _, payload, response = enroll(organization, request)
    assert response.status_code == 200
    issued = x509.load_pem_x509_certificate(response.json()["certificate"].encode())
    assert issued.not_valid_after_utc <= ca.not_valid_after_utc
    assert not issued.extensions.get_extension_for_class(x509.BasicConstraints).value.ca
    assert (
        Client()
        .post(
            reverse("agent-v2-enroll"), data=json.dumps(payload),
            content_type="application/json", secure=True,
        )
        .status_code
        == 403
    )
    assert EdgeAgent.objects.count() == 1


@pytest.mark.parametrize("csr_text", ["not-a-csr", "", None])
def test_invalid_csr_does_not_consume_enrollment(authority, organization, csr_text):
    _, _, response = enroll(organization, csr_text)
    assert response.status_code == 400
    assert not EdgeAgent.objects.exists()
    assert AgentEnrollment.objects.filter(used_at__isnull=True).count() == 1


def test_weak_key_is_refused_before_enrollment(authority, organization):
    _, request = csr(1024)
    assert enroll(organization, request)[2].status_code == 400
    assert not EdgeAgent.objects.exists()


@pytest.mark.parametrize("failure", ["missing", "malformed", "expired", "mismatched", "not_ca"])
def test_invalid_ca_never_creates_agent_or_consumes_code(authority, organization, failure):
    key, _, cert_path, key_path = authority
    if failure == "missing":
        key_path.unlink()
    elif failure == "malformed":
        cert_path.write_bytes(b"invalid-ca")
    elif failure == "mismatched":
        key_path.write_bytes(private_bytes(csr()[0]))
    else:
        cert_path.write_bytes(
            ca_certificate(key, expired=failure == "expired", ca=failure != "not_ca").public_bytes(
                serialization.Encoding.PEM
            )
        )
    _, request = csr()
    assert enroll(organization, request)[2].status_code == 503
    assert not EdgeAgent.objects.exists()
    assert AgentEnrollment.objects.filter(used_at__isnull=True).count() == 1


def test_expired_code_is_refused_without_creating_agent(authority, organization):
    _, request = csr()
    enrollment = issue_enrollment(organization=organization)
    AgentEnrollment.objects.update(expires_at=timezone.now() - timedelta(minutes=1))
    response = Client().post(
        reverse("agent-v2-enroll"),
        data=json.dumps(
            {"code": enrollment.code, "label": "Test", "fingerprint": "test", "csr": request}
        ),
        content_type="application/json",
        secure=True,
    )
    assert response.status_code == 403 and not EdgeAgent.objects.exists()


def test_public_certificate_headers_cannot_impersonate_the_private_mtls_gateway(
    authority, organization, settings
):
    _, request = csr()
    credentials = enroll(organization, request)[2].json()
    settings.EDGE_AGENT_MTLS_REQUIRED = True
    settings.EDGE_AGENT_MTLS_PROXY_SECRET = GATEWAY
    forged = {
        "X-Hub-MTLS-Verified": "SUCCESS",
        "X-Hub-MTLS-Client-Cert": quote(credentials["certificate"]),
    }
    assert signed(credentials, headers=forged).status_code == 401
    assert signed(credentials, headers={**forged, "X-Hub-MTLS-Gateway": "wrong"}).status_code == 401
    non_ascii_gateway = {**forged, "X-Hub-MTLS-Gateway": "forjado-ç"}
    assert signed(credentials, headers=non_ascii_gateway).status_code == 401
    assert signed(credentials, headers={**forged, "X-Hub-MTLS-Gateway": GATEWAY}).status_code == 200
    _, other_request = csr()
    other = enroll(organization, other_request)[2].json()
    assert (
        signed(
            credentials,
            headers={
                **forged,
                "X-Hub-MTLS-Gateway": GATEWAY,
                "X-Hub-MTLS-Client-Cert": quote(other["certificate"]),
            },
        ).status_code
        == 401
    )
    settings.EDGE_AGENT_MTLS_PROXY_SECRET = ""
    assert signed(credentials, headers={**forged, "X-Hub-MTLS-Gateway": GATEWAY}).status_code == 401


def test_certificate_renewal_keeps_identity_and_revocation_stops_it(
    authority, organization, settings
):
    key, request = csr()
    credentials = enroll(organization, request)[2].json()
    settings.EDGE_AGENT_MTLS_REQUIRED = True
    settings.EDGE_AGENT_MTLS_PROXY_SECRET = GATEWAY
    body = json.dumps({"csr": request}).encode()
    timestamp = str(int(timezone.now().timestamp()))
    signature = hmac.new(
        credentials["shared_secret"].encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    headers = {
        "X-Hub-Agent-ID": credentials["agent_id"],
        "X-Hub-Agent-Timestamp": timestamp,
        "X-Hub-Agent-Signature": signature,
        "X-Hub-MTLS-Gateway": GATEWAY,
        "X-Hub-MTLS-Verified": "SUCCESS",
        "X-Hub-MTLS-Client-Cert": quote(credentials["certificate"]),
    }
    response = Client().post(
        reverse("agent-v2-renew"), data=body, content_type="application/json", headers=headers,
        secure=True,
    )
    assert response.status_code == 200
    renewed = x509.load_pem_x509_certificate(response.json()["certificate"].encode())
    assert renewed.public_key().public_numbers() == key.public_key().public_numbers()
    agent = EdgeAgent.objects.get(pk=credentials["agent_id"])
    assert agent.mtls_certificate_sha256 == renewed.fingerprint(hashes.SHA256()).hex()
    headers["X-Hub-MTLS-Client-Cert"] = quote(response.json()["certificate"])
    revoke_agent(agent=agent)
    assert (
        Client()
        .post(
            reverse("agent-v2-renew"), data=body, content_type="application/json", headers=headers,
            secure=True,
        )
        .status_code
        == 401
    )


def test_real_loopback_tls_requires_a_trusted_unexpired_client_certificate(authority, tmp_path):
    import ssl
    import urllib.error
    import urllib.request
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    from ipaddress import ip_address
    from threading import Thread

    from cryptography.x509.oid import ExtendedKeyUsageOID

    ca_key, ca, ca_path, _ = authority

    def leaf(name, key, issuer_key, issuer, *, server=False, expired=False):
        now = timezone.now()
        return (
            x509.CertificateBuilder()
            .subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)]))
            .issuer_name(issuer.subject)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(now - timedelta(days=2))
            .not_valid_after(now + timedelta(days=-1 if expired else 1))
            .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
            .add_extension(
                x509.SubjectAlternativeName([x509.IPAddress(ip_address("127.0.0.1"))]),
                critical=False,
            )
            .add_extension(
                x509.ExtendedKeyUsage(
                    [ExtendedKeyUsageOID.SERVER_AUTH if server else ExtendedKeyUsageOID.CLIENT_AUTH]
                ),
                critical=False,
            )
            .sign(issuer_key, hashes.SHA256())
        )

    server_key = csr()[0]
    server_cert = leaf("localhost", server_key, ca_key, ca, server=True)
    server_path = tmp_path / "server.pem"
    server_path.write_bytes(
        server_cert.public_bytes(serialization.Encoding.PEM) + private_bytes(server_key)
    )

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            assert self.connection.getpeercert(binary_form=True)
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"verified-client")

        def log_message(self, *args):
            pass

    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    context.load_cert_chain(server_path)
    context.load_verify_locations(cafile=str(ca_path))
    context.verify_mode = ssl.CERT_REQUIRED
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"https://127.0.0.1:{server.server_port}/"
        client = ssl.create_default_context(cafile=str(ca_path))
        with pytest.raises((urllib.error.URLError, ssl.SSLError, OSError)):
            urllib.request.urlopen(url, context=client, timeout=5)
        for kind in ["valid", "expired", "unknown"]:
            key = csr()[0]
            issuer_key = csr()[0] if kind == "unknown" else ca_key
            issuer = ca_certificate(issuer_key) if kind == "unknown" else ca
            certificate = leaf(kind, key, issuer_key, issuer, expired=kind == "expired")
            path = tmp_path / f"{kind}.pem"
            path.write_bytes(
                certificate.public_bytes(serialization.Encoding.PEM) + private_bytes(key)
            )
            client = ssl.create_default_context(cafile=str(ca_path))
            client.load_cert_chain(path)
            if kind == "valid":
                with urllib.request.urlopen(url, context=client, timeout=5) as response:
                    assert response.read() == b"verified-client"
            else:
                with pytest.raises((urllib.error.URLError, ssl.SSLError, OSError)):
                    urllib.request.urlopen(url, context=client, timeout=5)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
