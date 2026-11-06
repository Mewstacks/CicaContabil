"""Bind proxy-verified TLS identity to the enrolled agent, never to public headers."""

from __future__ import annotations

import hmac
from urllib.parse import unquote

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from django.conf import settings
from django.http import HttpRequest
from django.utils import timezone

from apps.intelligence.models import EdgeAgent


def valid_mtls_client(request: HttpRequest, agent: EdgeAgent) -> bool:
    if not settings.EDGE_AGENT_MTLS_REQUIRED:
        return True
    gateway_secret = settings.EDGE_AGENT_MTLS_PROXY_SECRET
    if (
        len(gateway_secret) < 32
        or not hmac.compare_digest(
            request.headers.get("X-Hub-MTLS-Gateway", "").encode(), gateway_secret.encode()
        )
        or request.headers.get("X-Hub-MTLS-Verified") != "SUCCESS"
    ):
        return False
    try:
        certificate = x509.load_pem_x509_certificate(
            unquote(request.headers.get("X-Hub-MTLS-Client-Cert", "")).encode("ascii")
        )
    except (TypeError, ValueError, UnicodeError):
        return False
    now = timezone.now()
    return bool(
        agent.mtls_certificate_sha256
        and certificate.not_valid_before_utc <= now < certificate.not_valid_after_utc
        and hmac.compare_digest(
            certificate.fingerprint(hashes.SHA256()).hex(), agent.mtls_certificate_sha256
        )
    )
