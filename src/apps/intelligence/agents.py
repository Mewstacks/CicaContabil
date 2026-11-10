"""Enrollment and HMAC authentication for outbound-only Domínio edge agents."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

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
    sync_scope: dict[str, Any]


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def issue_enrollment(
    *,
    organization: Organization,
    actor: User | None = None,
    request: object = None,
    valid_for_minutes: int = 30,
    sync_scope: dict[str, Any] | None = None,
    replaces_agent: EdgeAgent | None = None,
) -> EnrollmentCredentials:
    from apps.intelligence.agent_scope import validate_sync_scope

    scope = validate_sync_scope(sync_scope, organization) if sync_scope is not None else {}
    if not 1 <= valid_for_minutes <= 60:
        raise ValueError("O código deve expirar entre 1 e 60 minutos.")
    code = secrets.token_urlsafe(24)
    expires_at = timezone.now() + timedelta(minutes=valid_for_minutes)
    with transaction.atomic():
        if replaces_agent is not None:
            Organization.objects.select_for_update(no_key=True).get(pk=organization.pk)
            previous = (
                EdgeAgent.objects.select_for_update()
                .filter(
                    pk=replaces_agent.pk,
                    organization=organization,
                    status=EdgeAgent.Status.ACTIVE,
                )
                .first()
            )
            if previous is None:
                raise ValueError("Agente anterior ativo não encontrado neste escritório.")
            # Replacement is deliberately limited to the scoped Domínio transport.
            if not previous.sync_scope or scope != previous.sync_scope:
                raise ValueError("A substituição deve preservar o manifesto do agente anterior.")
            validate_sync_scope(previous.sync_scope, organization)
            if (
                EdgeAgent.objects.filter(organization=organization, is_official=True)
                .exclude(pk=previous.pk)
                .exists()
            ):
                raise ValueError("Selecione o agente oficial atual para substituição.")
            if (
                AgentEnrollment.objects.filter(
                    replaces_agent=previous,
                    used_at__isnull=True,
                    expires_at__gt=timezone.now(),
                ).exists()
                or EdgeAgent.objects.filter(
                    replaces_agent=previous, status=EdgeAgent.Status.PENDING_ACTIVATION
                ).exists()
            ):
                raise ValueError("Já existe código válido ou candidato pendente para este agente.")
        enrollment = AgentEnrollment.objects.create(
            organization=organization,
            code_digest=_digest(code),
            sync_scope=scope,
            expires_at=expires_at,
            issued_by=actor,
            replaces_agent=replaces_agent,
        )
        record_event(
            action="intelligence.agent.enrollment_issued",
            actor=actor,
            organization=organization,
            target=enrollment,
            request=request,
            metadata={
                "valid_for_minutes": valid_for_minutes,
                "replaces_agent_id": str(replaces_agent.pk) if replaces_agent else None,
            },
        )
    return EnrollmentCredentials(code, expires_at)


def redeem_enrollment(
    *,
    code: str,
    label: str,
    fingerprint: str,
    mtls_certificate_sha256: str = "",
    request: object = None,
    allow_scoped: bool = False,
    allow_portfolio: bool = False,
    allow_replacement: bool = False,
) -> DeviceCredentials:
    certificate_sha256 = mtls_certificate_sha256.strip().lower().replace(":", "")
    if certificate_sha256 and not _SHA256_RE.fullmatch(certificate_sha256):
        raise ValueError("Fingerprint mTLS inválido.")
    if not code or not label.strip() or not fingerprint.strip():
        raise ValueError("Código, identificação e fingerprint são obrigatórios.")
    with transaction.atomic():
        enrollment = (
            AgentEnrollment.objects.select_for_update(of=("self",))
            .select_related("organization")
            .filter(code_digest=_digest(code), used_at__isnull=True, expires_at__gt=timezone.now())
            .first()
        )
        if enrollment is None:
            raise ValueError("Código de enrollment inválido ou expirado.")
        if enrollment.sync_scope:
            from apps.intelligence.agent_scope import PORTFOLIO_VERSION, validate_sync_scope

            if not allow_scoped:
                raise ValueError("Este código exige agente com protocolo de recorte financeiro.")
            if enrollment.sync_scope.get("version") == PORTFOLIO_VERSION and not allow_portfolio:
                raise ValueError("Este código exige agente com protocolo de carteira scoped-v2.")
            validate_sync_scope(enrollment.sync_scope, enrollment.organization)
        previous = None
        if enrollment.replaces_agent_id is not None:
            if not allow_replacement:
                raise ValueError("Este código exige agente com ativação em duas fases staged-v1.")
            Organization.objects.select_for_update(no_key=True).get(pk=enrollment.organization_id)
            previous = (
                EdgeAgent.objects.select_for_update()
                .filter(
                    pk=enrollment.replaces_agent_id,
                    organization=enrollment.organization,
                    status=EdgeAgent.Status.ACTIVE,
                )
                .first()
            )
            if previous is None or previous.sync_scope != enrollment.sync_scope:
                raise ValueError("Agente anterior ou manifesto mudou; revise a substituição.")
            if previous.fingerprint == fingerprint.strip()[:128]:
                raise ValueError("A substituição exige outro computador identificado.")
        shared_secret = secrets.token_urlsafe(48)
        agent = EdgeAgent.objects.create(
            organization=enrollment.organization,
            label=label.strip()[:120],
            fingerprint=fingerprint.strip()[:128],
            mtls_certificate_sha256=certificate_sha256,
            shared_secret=shared_secret,
            sync_scope=enrollment.sync_scope,
            replaces_agent=previous,
            status=(EdgeAgent.Status.PENDING_ACTIVATION if previous else EdgeAgent.Status.ACTIVE),
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
    return DeviceCredentials(str(agent.id), shared_secret, agent.sync_scope)


def verify_agent_signature(
    *,
    agent: EdgeAgent,
    timestamp: str,
    body: bytes,
    signature: str,
    allow_pending: bool = False,
) -> bool:
    if len(signature) != 64 or any(char not in "0123456789abcdef" for char in signature):
        return False
    try:
        timestamp_value = int(timestamp)
    except (TypeError, ValueError):
        return False
    now = int(timezone.now().timestamp())
    statuses = {EdgeAgent.Status.ACTIVE}
    if allow_pending:
        statuses.add(EdgeAgent.Status.PENDING_ACTIVATION)
    if abs(now - timestamp_value) > 300 or agent.status not in statuses:
        return False
    payload = timestamp.encode() + b"." + body
    expected = hmac.new(agent.shared_secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def revoke_agent(*, agent: EdgeAgent, actor: User | None = None, request: object = None) -> None:
    with transaction.atomic():
        Organization.objects.select_for_update(no_key=True).get(pk=agent.organization_id)
        locked = EdgeAgent.objects.select_for_update().get(pk=agent.pk)
        locked.status = EdgeAgent.Status.REVOKED
        locked.is_official = False
        locked.revoked_at = timezone.now()
        locked.save(update_fields=["status", "is_official", "revoked_at", "updated_at"])
        record_event(
            action="intelligence.agent.revoked",
            actor=actor,
            organization=locked.organization,
            target=locked,
            request=request,
        )
        agent.status, agent.is_official, agent.revoked_at = (
            locked.status,
            locked.is_official,
            locked.revoked_at,
        )


def activate_official_replacement(
    *,
    organization: Organization,
    candidate_id: str,
    previous_id: str,
    scope_revision: str,
    actor: User | None = None,
    request: object = None,
) -> EdgeAgent:
    """Explicit cutover after Windows verification; never inferred from enrollment."""
    from apps.intelligence.agent_scope import validate_sync_scope

    with transaction.atomic():
        Organization.objects.select_for_update(no_key=True).get(pk=organization.pk)
        agents = {
            str(agent.pk): agent
            for agent in EdgeAgent.objects.select_for_update()
            .filter(organization=organization, pk__in=[candidate_id, previous_id])
            .order_by("pk")
        }
        candidate, previous = agents.get(candidate_id), agents.get(previous_id)
        if candidate is None or previous is None or candidate.pk == previous.pk:
            raise ValueError("Os dois agentes devem ser distintos e pertencer ao escritório.")
        # A retry after an uncertain command result must not repeat the audit or cutover.
        if (
            candidate.status == EdgeAgent.Status.ACTIVE
            and candidate.is_official
            and candidate.replaces_agent_id == previous.pk
            and previous.status == EdgeAgent.Status.REVOKED
            and candidate.sync_scope.get("revision") == scope_revision
        ):
            return candidate
        if (
            candidate.status != EdgeAgent.Status.PENDING_ACTIVATION
            or candidate.replaces_agent_id != previous.pk
            or previous.status != EdgeAgent.Status.ACTIVE
        ):
            raise ValueError("Substituição pendente incompatível com o agente anterior ativo.")
        scope = validate_sync_scope(candidate.sync_scope, organization)
        if not scope or scope != previous.sync_scope or scope.get("revision") != scope_revision:
            raise ValueError("Manifesto mudou ou revisão não confere; revise antes do corte.")
        if candidate.fingerprint == previous.fingerprint:
            raise ValueError("A substituição exige outro computador identificado.")
        now = timezone.now()
        if candidate.last_seen_at is None or not (
            now - timedelta(minutes=5) <= candidate.last_seen_at <= now
        ):
            raise ValueError("O candidato precisa de heartbeat dos últimos cinco minutos.")
        if (
            EdgeAgent.objects.filter(organization=organization, is_official=True)
            .exclude(pk=previous.pk)
            .exists()
        ):
            raise ValueError("Outro agente já é oficial neste escritório.")
        previous.status = EdgeAgent.Status.REVOKED
        previous.is_official = False
        previous.revoked_at = now
        previous.save(update_fields=["status", "is_official", "revoked_at", "updated_at"])
        candidate.status = EdgeAgent.Status.ACTIVE
        candidate.is_official = True
        candidate.save(update_fields=["status", "is_official", "updated_at"])
        record_event(
            action="intelligence.agent.official_replaced",
            actor=actor,
            organization=organization,
            target=candidate,
            request=request,
            metadata={"previous_agent_id": str(previous.pk), "scope_revision": scope_revision},
        )
        return candidate
