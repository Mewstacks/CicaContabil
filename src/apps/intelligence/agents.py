"""Enrollment and HMAC authentication for outbound-only Domínio edge agents."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta

from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.intelligence.models import AgentEnrollment, EdgeAgent
from apps.organizations.models import Organization

_SHA256_RE = re.compile(r"[0-9a-f]{64}")


@dataclass(frozen=True)
class EnrollmentCredentials:
    code: str
    expires_at: datetime


@dataclass(frozen=True)
class DeviceCredentials:
    agent_id: str
    shared_secret: str


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def issue_enrollment(
    *,
    organization: Organization,
    actor: User | None = None,
    request: object = None,
    valid_for_minutes: int = 30,
) -> EnrollmentCredentials:
    if not 1 <= valid_for_minutes <= 60:
        raise ValueError("O código deve expirar entre 1 e 60 minutos.")
    code = secrets.token_urlsafe(24)
    expires_at = timezone.now() + timedelta(minutes=valid_for_minutes)
    enrollment = AgentEnrollment.objects.create(
        organization=organization,
        code_digest=_digest(code),
        expires_at=expires_at,
        issued_by=actor,
    )
    record_event(
        action="intelligence.agent.enrollment_issued",
        actor=actor,
        organization=organization,
        target=enrollment,
        request=request,
        metadata={"valid_for_minutes": valid_for_minutes},
    )
    return EnrollmentCredentials(code, expires_at)


def redeem_enrollment(
    *,
    code: str,
    label: str,
    fingerprint: str,
    mtls_certificate_sha256: str = "",
    request: object = None,
) -> DeviceCredentials:
    certificate_sha256 = mtls_certificate_sha256.strip().lower().replace(":", "")
    if certificate_sha256 and not _SHA256_RE.fullmatch(certificate_sha256):
        raise ValueError("Fingerprint mTLS inválido.")
    if not code or not label.strip() or not fingerprint.strip():
        raise ValueError("Código, identificação e fingerprint são obrigatórios.")
    with transaction.atomic():
        enrollment = (
            AgentEnrollment.objects.select_for_update()
            .select_related("organization")
            .filter(code_digest=_digest(code), used_at__isnull=True, expires_at__gt=timezone.now())
            .first()
        )
        if enrollment is None:
            raise ValueError("Código de enrollment inválido ou expirado.")
        shared_secret = secrets.token_urlsafe(48)
        agent = EdgeAgent.objects.create(
            organization=enrollment.organization,
            label=label.strip()[:120],
            fingerprint=fingerprint.strip()[:128],
            mtls_certificate_sha256=certificate_sha256,
            shared_secret=shared_secret,
        )
        enrollment.used_at = timezone.now()
        enrollment.save(update_fields=["used_at", "updated_at"])
        record_event(
            action="intelligence.agent.enrolled",
            organization=enrollment.organization,
            target=agent,
            request=request,
            metadata={"fingerprint_present": True},
        )
    return DeviceCredentials(str(agent.id), shared_secret)


def verify_agent_signature(
    *, agent: EdgeAgent, timestamp: str, body: bytes, signature: str
) -> bool:
    try:
        timestamp_value = int(timestamp)
    except (TypeError, ValueError):
        return False
    now = int(timezone.now().timestamp())
    if abs(now - timestamp_value) > 300 or agent.status != EdgeAgent.Status.ACTIVE:
        return False
    payload = timestamp.encode() + b"." + body
    expected = hmac.new(agent.shared_secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def revoke_agent(*, agent: EdgeAgent, actor: User | None = None, request: object = None) -> None:
    agent.status = EdgeAgent.Status.REVOKED
    agent.revoked_at = timezone.now()
    agent.save(update_fields=["status", "revoked_at", "updated_at"])
    record_event(
        action="intelligence.agent.revoked",
        actor=actor,
        organization=agent.organization,
        target=agent,
        request=request,
    )
