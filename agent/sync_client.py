from __future__ import annotations

import hashlib
import hmac
import json
import ssl
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

from cryptography import x509
from cryptography.hazmat.primitives import hashes


@dataclass(frozen=True)
class EdgeAgentConfig:
    hub_url: str
    agent_id: str
    shared_secret: str
    client_ca_file: str = ""
    client_certificate_file: str = ""
    client_private_key_file: str = ""

    def sync_url(self) -> str:
        base = self.hub_url.rstrip("/")
        if not base.startswith("https://"):
            raise ValueError("O agente exige URL HTTPS do Hub.")
        return f"{base}/api/v1/intelligence/agent/sync/"

    def enrollment_url(self) -> str:
        base = self.hub_url.rstrip("/")
        if not base.startswith("https://"):
            raise ValueError("O agente exige URL HTTPS do Hub.")
        return f"{base}/api/v1/intelligence/agent/enroll/"

    def mtls_context(self) -> ssl.SSLContext:
        """Build a pinned client-certificate context; no insecure TLS fallback exists."""
        if not all(
            (self.client_ca_file, self.client_certificate_file, self.client_private_key_file)
        ):
            raise ValueError("O agente exige CA, certificado e chave privada para mTLS.")
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH, cafile=self.client_ca_file)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(
            certfile=self.client_certificate_file,
            keyfile=self.client_private_key_file,
        )
        return context

    def certificate_sha256(self) -> str:
        certificate = x509.load_pem_x509_certificate(
            Path(self.client_certificate_file).read_bytes()
        )
        return certificate.fingerprint(hashes.SHA256()).hex()

    def enrollment_identity(self, *, code: str, label: str, fingerprint: str) -> dict[str, str]:
        """Payload for the one-time enrollment endpoint; it never includes the private key."""
        return {
            "code": code,
            "label": label,
            "fingerprint": fingerprint,
            "mtls_certificate_sha256": self.certificate_sha256(),
        }


def post_snapshot(
    config: EdgeAgentConfig, payload: dict[str, Any], timeout_seconds: int = 20
) -> dict[str, Any]:
    body = json.dumps(payload, separators=(",", ":")).encode()
    timestamp = str(int(time.time()))
    signature = hmac.new(
        config.shared_secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    request = Request(  # noqa: S310 - sync_url accepts only HTTPS
        config.sync_url(),
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Hub-Agent-ID": config.agent_id,
            "X-Hub-Agent-Timestamp": timestamp,
            "X-Hub-Agent-Signature": signature,
        },
        method="POST",
    )
    try:
        with urlopen(  # noqa: S310 - sync_url accepts only HTTPS and mTLS validates the peer
            request, timeout=timeout_seconds, context=config.mtls_context()
        ) as response:
            return json.loads(response.read())
    except (URLError, TimeoutError, ssl.SSLError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Não foi possível enviar o snapshot ao Hub.") from exc


def enroll_agent(
    config: EdgeAgentConfig,
    *,
    code: str,
    label: str,
    fingerprint: str,
    timeout_seconds: int = 20,
) -> tuple[str, str]:
    """Redeem a one-time code without ever transmitting the private key."""
    body = json.dumps(
        config.enrollment_identity(code=code, label=label, fingerprint=fingerprint),
        separators=(",", ":"),
    ).encode()
    request = Request(  # noqa: S310 - enrollment_url accepts only HTTPS
        config.enrollment_url(),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(  # noqa: S310 - HTTPS plus configured CA validation
            request, timeout=timeout_seconds, context=config.mtls_context()
        ) as response:
            payload = json.loads(response.read())
    except (URLError, TimeoutError, ssl.SSLError, OSError, json.JSONDecodeError) as exc:
        raise RuntimeError("Não foi possível concluir o enrollment do agente.") from exc
    if not isinstance(payload, dict):
        raise RuntimeError("Resposta de enrollment inválida.")
    agent_id = payload.get("agent_id")
    shared_secret = payload.get("shared_secret")
    if not isinstance(agent_id, str) or not isinstance(shared_secret, str):
        raise RuntimeError("Resposta de enrollment sem identidade do agente.")
    if not agent_id.strip() or not shared_secret.strip():
        raise RuntimeError("Resposta de enrollment sem identidade do agente.")
    return agent_id, shared_secret
