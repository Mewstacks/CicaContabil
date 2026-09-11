from __future__ import annotations

import hmac
import json
from collections.abc import Mapping
from typing import Any
from urllib.parse import unquote

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from django.conf import settings
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.intelligence.agents import redeem_enrollment, verify_agent_signature
from apps.intelligence.models import EdgeAgent, IntelligenceConnector
from apps.intelligence.sync import sync_companies


def _json_error(detail: str, status: int) -> JsonResponse:
    response = JsonResponse({"error": detail}, status=status)
    response["Cache-Control"] = "no-store"
    return response


def _body(request: HttpRequest, limit: int) -> dict[str, Any] | None:
    if len(request.body) > limit:
        return None
    try:
        payload = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _valid_mtls_client(request: HttpRequest, agent: EdgeAgent) -> bool:
    """Bind the proxy-verified client certificate to its enrolled agent."""
    if not settings.EDGE_AGENT_MTLS_REQUIRED:
        return True
    verified = request.headers.get("X-Hub-MTLS-Verified", "")
    encoded_certificate = request.headers.get("X-Hub-MTLS-Client-Cert", "")
    try:
        observed = (
            x509.load_pem_x509_certificate(unquote(encoded_certificate).encode("ascii"))
            .fingerprint(hashes.SHA256())
            .hex()
        )
    except (TypeError, ValueError):
        return False
    return (
        verified == "SUCCESS"
        and bool(agent.mtls_certificate_sha256)
        and hmac.compare_digest(observed, agent.mtls_certificate_sha256)
    )


@csrf_exempt
@require_POST
def enroll(request: HttpRequest) -> JsonResponse:
    payload = _body(request, 16_384)
    if payload is None:
        return _json_error("Payload de enrollment inválido.", 400)
    if (
        settings.EDGE_AGENT_MTLS_REQUIRED
        and not str(payload.get("mtls_certificate_sha256", "")).strip()
    ):
        return _json_error("Enrollment exige fingerprint do certificado mTLS.", 403)
    try:
        credentials = redeem_enrollment(
            code=str(payload.get("code", "")),
            label=str(payload.get("label", "")),
            fingerprint=str(payload.get("fingerprint", "")),
            mtls_certificate_sha256=str(payload.get("mtls_certificate_sha256", "")),
            request=request,
        )
    except ValueError as exc:
        return _json_error(str(exc), 403)
    response = JsonResponse(
        {"agent_id": credentials.agent_id, "shared_secret": credentials.shared_secret}
    )
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_POST
def sync(request: HttpRequest) -> JsonResponse:
    agent_id = request.headers.get("X-Hub-Agent-ID", "")
    timestamp = request.headers.get("X-Hub-Agent-Timestamp", "")
    signature = request.headers.get("X-Hub-Agent-Signature", "")
    try:
        agent = EdgeAgent.objects.select_related("organization").filter(id=agent_id).first()
    except (ValueError, TypeError):
        agent = None
    if (
        agent is None
        or not _valid_mtls_client(request, agent)
        or not verify_agent_signature(
            agent=agent, timestamp=timestamp, body=request.body, signature=signature
        )
    ):
        return _json_error("Agente não autorizado.", 401)
    payload = _body(request, 512_000)
    rows = payload.get("companies") if payload else None
    full_snapshot = bool(payload.get("full_snapshot", False)) if payload else False
    if (
        not isinstance(rows, list)
        or len(rows) > 500
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        return _json_error("Snapshot de empresas inválido.", 400)
    connector, _ = IntelligenceConnector.objects.get_or_create(
        organization=agent.organization,
        mode=IntelligenceConnector.Mode.EDGE_AGENT,
        defaults={"status": "healthy", "device_fingerprint": agent.fingerprint[:64]},
    )
    result = sync_companies(
        organization=agent.organization,
        connector=connector,
        rows=rows,
        request=request,
        full_snapshot=full_snapshot,
    )
    agent.last_seen_at = timezone.now()
    agent.save(update_fields=["last_seen_at", "updated_at"])
    response = JsonResponse(
        {
            "created": result.created,
            "updated": result.updated,
            "ignored": result.ignored,
            "deactivated": result.deactivated,
        }
    )
    response["Cache-Control"] = "no-store"
    return response
