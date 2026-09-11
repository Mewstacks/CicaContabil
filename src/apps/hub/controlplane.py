"""Signed CRMew control-plane client and local authorization projection."""

from __future__ import annotations

import base64
import hashlib
import json
import re
import secrets
import time
from datetime import datetime, timedelta
from typing import Any
from urllib.error import URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from django.conf import settings
from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    ControlPlaneBinding,
    ProductModule,
    RemoteSupportGrant,
)
from apps.organizations.models import Membership, Organization

CONTROL_CACHE_TTL = timedelta(minutes=15)
NETWORK_TIMEOUT_SECONDS = 10
_CLAUDE_MODEL_RE = re.compile(r"claude-[a-z0-9._-]{1,72}")
_MAX_CENTS = 1_000_000


class ControlPlaneError(RuntimeError):
    pass


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def _b64decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value.encode() + b"=" * (-len(value) % 4))


def normalize_controller_url(value: str) -> str:
    """Accept only a CRMew HTTPS origin (or loopback HTTP in local development)."""
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").casefold()
    is_local_development = (
        settings.DEBUG and parsed.scheme == "http" and host in {"localhost", "127.0.0.1", "::1"}
    )
    has_acceptable_scheme = parsed.scheme == "https" or is_local_development
    if (
        not has_acceptable_scheme
        or not host
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.params
        or parsed.query
        or parsed.fragment
    ):
        raise ControlPlaneError("URL do CRMew deve ser uma origem HTTPS válida.")
    return f"{parsed.scheme}://{parsed.netloc}"


def generate_device_private_key() -> str:
    raw = Ed25519PrivateKey.generate().private_bytes_raw()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def public_key_for_private(private_key: str) -> str:
    raw = (
        Ed25519PrivateKey.from_private_bytes(_b64decode(private_key))
        .public_key()
        .public_bytes_raw()
    )
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _parse_datetime(value: object) -> datetime:
    if not isinstance(value, str):
        raise ControlPlaneError("Controle sem data de expiração.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ControlPlaneError("Data do controle inválida.") from exc
    if timezone.is_naive(parsed):
        raise ControlPlaneError("Data do controle precisa incluir fuso horário.")
    return parsed


def _signed_request(
    binding: ControlPlaneBinding, *, method: str, path: str, body: bytes = b""
) -> Request:
    timestamp = str(int(time.time()))
    nonce = secrets.token_urlsafe(18)
    material = b"\n".join(
        [
            method.encode(),
            path.encode(),
            timestamp.encode(),
            nonce.encode(),
            hashlib.sha256(body).hexdigest().encode(),
        ]
    )
    signature = Ed25519PrivateKey.from_private_bytes(_b64decode(binding.device_private_key)).sign(
        material
    )
    root = normalize_controller_url(binding.controller_url)
    request = Request(f"{root}{path}", data=body or None, method=method)  # noqa: S310 - origin is normalized above
    request.add_header("Accept", "application/json")
    request.add_header("X-Hub-Installation", str(binding.remote_installation_id))
    request.add_header("X-Hub-Timestamp", timestamp)
    request.add_header("X-Hub-Nonce", nonce)
    request.add_header("X-Hub-Signature", base64.urlsafe_b64encode(signature).decode().rstrip("="))
    if body:
        request.add_header("Content-Type", "application/json")
    return request


def _fetch_json(request: Request) -> dict[str, Any]:
    try:
        with urlopen(request, timeout=NETWORK_TIMEOUT_SECONDS) as response:  # noqa: S310 - validated controller origin
            raw = response.read(256_000)
    except (OSError, URLError) as exc:
        raise ControlPlaneError(f"CRMew indisponível: {exc}") from exc
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ControlPlaneError("CRMew devolveu JSON inválido.") from exc
    if not isinstance(payload, dict):
        raise ControlPlaneError("CRMew devolveu payload inválido.")
    return payload


def _verify_signature(
    binding: ControlPlaneBinding, control: dict[str, Any], signature: object
) -> None:
    if not isinstance(signature, str):
        raise ControlPlaneError("Controle sem assinatura.")
    try:
        Ed25519PublicKey.from_public_bytes(_b64decode(binding.controller_public_key)).verify(
            _b64decode(signature), canonical_json(control)
        )
    except Exception as exc:
        raise ControlPlaneError("Assinatura do CRMew inválida.") from exc


def authorization_is_fresh(organization: Organization) -> bool:
    binding = (
        ControlPlaneBinding.objects.filter(organization=organization)
        .only("cache_expires_at")
        .first()
    )
    return binding is None or bool(
        binding.cache_expires_at and binding.cache_expires_at > timezone.now()
    )


def company_queryset_for_membership(
    membership: Membership | None,
) -> QuerySet[ClientCompany]:
    if membership is None:
        return ClientCompany.objects.none()
    organization = membership.organization
    binding_exists = ControlPlaneBinding.objects.filter(organization=organization).exists()
    companies = ClientCompany.objects.filter(organization=organization, active=True)
    if not binding_exists:
        return companies
    if not authorization_is_fresh(organization):
        return ClientCompany.objects.none()
    return companies.filter(
        access_grants__membership=membership,
        access_grants__is_active=True,
    ).distinct()


def companies_for_membership(membership: Membership | None) -> list[ClientCompany]:
    return list(company_queryset_for_membership(membership))


def company_is_allowed(*, membership: Membership | None, company: ClientCompany) -> bool:
    return any(item.id == company.id for item in companies_for_membership(membership))


def company_has_capability(
    *, membership: Membership | None, company: ClientCompany, capability: str
) -> bool:
    """Apply CRMew capabilities at the company boundary, with no implicit write privilege."""
    if membership is None or membership.organization_id != company.organization_id:
        return False
    organization = membership.organization
    if not ControlPlaneBinding.objects.filter(organization=organization).exists():
        return True
    if not authorization_is_fresh(organization):
        return False
    grant = (
        CompanyAccessGrant.objects.filter(
            organization=organization,
            membership=membership,
            company=company,
            is_active=True,
        )
        .only("capabilities")
        .first()
    )
    if grant is None:
        return False
    capabilities = {str(value).casefold() for value in grant.capabilities if isinstance(value, str)}
    return capability.casefold() in capabilities or "*" in capabilities


def membership_has_capability(*, membership: Membership | None, capability: str) -> bool:
    """Check an office-level action through any currently allowed company grant."""
    if membership is None:
        return False
    if not ControlPlaneBinding.objects.filter(organization=membership.organization).exists():
        return True
    return any(
        company_has_capability(membership=membership, company=company, capability=capability)
        for company in companies_for_membership(membership)
    )


def _sync_grants(organization: Organization, control: dict[str, Any]) -> None:
    raw_grants = control.get("access_grants")
    if not isinstance(raw_grants, list):
        raise ControlPlaneError("Controle sem grants de acesso.")
    subject_rows = [
        row for row in raw_grants if isinstance(row, dict) and isinstance(row.get("subject"), str)
    ]
    subjects = {str(row["subject"]).casefold() for row in subject_rows}
    memberships = {
        membership.user.email.casefold(): membership
        for membership in Membership.objects.select_related("user").filter(
            organization=organization
        )
    }
    disabled_membership_ids = [
        membership.id for email, membership in memberships.items() if email not in subjects
    ]
    if disabled_membership_ids:
        Membership.objects.filter(id__in=disabled_membership_ids).update(is_active=False)
    CompanyAccessGrant.objects.filter(organization=organization).delete()
    known_company_ids = {
        str(value)
        for value in ClientCompany.objects.filter(organization=organization).values_list(
            "id", flat=True
        )
    }
    known_roles = set(Membership.Role.values)
    for row in subject_rows:
        membership = memberships.get(str(row["subject"]).casefold())
        role = str(row.get("role", ""))
        if membership is None or role not in known_roles:
            continue
        membership.role = role
        membership.is_active = True
        membership.save(update_fields=["role", "is_active", "updated_at"])
        raw_modules = row.get("modules")
        raw_capabilities = row.get("capabilities")
        raw_company_ids = row.get("company_ids")
        modules: list[object] = raw_modules if isinstance(raw_modules, list) else []
        capabilities: list[object] = raw_capabilities if isinstance(raw_capabilities, list) else []
        company_ids: list[object] = raw_company_ids if isinstance(raw_company_ids, list) else []
        for company_id in company_ids:
            if str(company_id) not in known_company_ids:
                continue
            CompanyAccessGrant.objects.create(
                organization=organization,
                membership=membership,
                company_id=str(company_id),
                modules=[str(item)[:64] for item in modules[:80]],
                capabilities=[str(item)[:64] for item in capabilities[:80]],
            )


def _sync_modules(organization: Organization, control: dict[str, Any]) -> None:
    configuration = control.get("configuration")
    if not isinstance(configuration, dict):
        return
    enabled_modules = configuration.get("modules")
    if not isinstance(enabled_modules, list):
        return
    accepted = {str(code) for code in ProductModule.Code.values}
    requested = {str(code) for code in enabled_modules if str(code) in accepted}
    for code in accepted:
        ProductModule.objects.update_or_create(
            organization=organization,
            code=code,
            defaults={
                "enabled": code in requested,
                "enabled_at": timezone.now() if code in requested else None,
            },
        )


def _policy_bool(value: object, *, field: str, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ControlPlaneError(f"Política de IA inválida em {field}.")
    return value


def _policy_cents(value: object, *, field: str, default: int = 0) -> int:
    if value is None:
        return default
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= _MAX_CENTS:
        raise ControlPlaneError(f"Política de IA inválida em {field}.")
    return value


def _sync_intelligence_policy(organization: Organization, control: dict[str, Any]) -> None:
    """Project only signed, non-secret AI policy from CRMew into the local Hub.

    The local encrypted Claude key is deliberately absent from this contract. A
    missing policy revokes cloud egress, so an older cache can never keep a
    previously enabled fallback alive after CRMew has removed it.
    """
    from apps.intelligence.models import AssistantSettings, ClaudeFallbackApproval

    configuration = control.get("configuration")
    if not isinstance(configuration, dict):
        configuration = {}
    intelligence = configuration.get("intelligence", {})
    if not isinstance(intelligence, dict):
        raise ControlPlaneError("Política de IA inválida.")
    claude = intelligence.get("claude", {})
    if not isinstance(claude, dict):
        raise ControlPlaneError("Política Claude inválida.")

    enabled = _policy_bool(claude.get("enabled"), field="claude.enabled")
    allow_full_data = _policy_bool(claude.get("allow_full_data"), field="claude.allow_full_data")
    raw_roles = claude.get("allowed_roles", [])
    if not isinstance(raw_roles, list) or len(raw_roles) > len(Membership.Role.values):
        raise ControlPlaneError("Política de IA inválida em claude.allowed_roles.")
    allowed_roles = [str(role) for role in raw_roles]
    if len(set(allowed_roles)) != len(allowed_roles) or any(
        role not in Membership.Role.values for role in allowed_roles
    ):
        raise ControlPlaneError("Política de IA contém perfil inválido.")

    model = str(claude.get("model") or "")
    if model and not _CLAUDE_MODEL_RE.fullmatch(model):
        raise ControlPlaneError("Política de IA contém modelo Claude inválido.")
    max_request_cents = _policy_cents(
        claude.get("max_request_cents"), field="claude.max_request_cents"
    )
    offline_curation_enabled = _policy_bool(
        claude.get("offline_curation_enabled"), field="claude.offline_curation_enabled"
    )
    max_batch_requests = _policy_cents(
        claude.get("curation_max_batch_requests"), field="claude.curation_max_batch_requests"
    )
    if max_batch_requests > 1_000:
        raise ControlPlaneError("Política de IA excede o limite de lote de curadoria.")

    approval = claude.get("approval", {})
    if not isinstance(approval, dict):
        raise ControlPlaneError("Política de aprovação Claude inválida.")
    status = approval.get("status", ClaudeFallbackApproval.Status.REVOKED)
    if status not in ClaudeFallbackApproval.Status.values:
        raise ControlPlaneError("Política de aprovação Claude contém status inválido.")
    daily_limit_cents = _policy_cents(
        approval.get("daily_limit_cents"), field="claude.approval.daily_limit_cents"
    )
    monthly_limit_cents = _policy_cents(
        approval.get("monthly_limit_cents"), field="claude.approval.monthly_limit_cents"
    )
    raw_valid_until = approval.get("valid_until")
    valid_until = _parse_datetime(raw_valid_until) if raw_valid_until is not None else None

    # Disabled or incomplete policy is a revocation, not a dormant permission.
    if not enabled:
        allow_full_data = False
        allowed_roles = []
        model = ""
        max_request_cents = 0
        offline_curation_enabled = False
        max_batch_requests = 0
        status = ClaudeFallbackApproval.Status.REVOKED
        daily_limit_cents = 0
        monthly_limit_cents = 0
        valid_until = None

    AssistantSettings.objects.update_or_create(
        organization=organization,
        defaults={
            "claude_fallback_enabled": enabled,
            "claude_full_data_allowed": allow_full_data,
            "claude_allowed_roles": allowed_roles,
            "claude_model": model,
            "claude_max_request_cents": max_request_cents,
            "claude_offline_curation_enabled": offline_curation_enabled,
            "claude_curation_max_batch_requests": max_batch_requests,
            # claude_api_key is local-only and must never be written by CRMew.
        },
    )
    ClaudeFallbackApproval.objects.update_or_create(
        organization=organization,
        defaults={
            "status": status,
            "daily_limit_cents": daily_limit_cents,
            "monthly_limit_cents": monthly_limit_cents,
            "valid_until": valid_until,
            "approved_by": None,
            # CRMew is the approving authority; do not falsely attribute its
            # approval timestamp or actor to a local Hub user.
            "approved_at": None,
        },
    )


def _sync_support_grants(organization: Organization, control: dict[str, Any]) -> None:
    raw_grants = control.get("support_grants")
    if not isinstance(raw_grants, list):
        return
    active_hashes: list[str] = []
    for row in raw_grants:
        if not isinstance(row, dict):
            continue
        subject = row.get("subject")
        justification = row.get("justification")
        if not isinstance(subject, str) or not isinstance(justification, str):
            continue
        expires_at = _parse_datetime(row.get("expires_at"))
        if expires_at <= timezone.now():
            continue
        source_hash = hashlib.sha256(canonical_json(row)).hexdigest()
        active_hashes.append(source_hash)
        raw_company_ids = row.get("company_ids")
        company_ids: list[object] = raw_company_ids if isinstance(raw_company_ids, list) else []
        RemoteSupportGrant.objects.update_or_create(
            source_hash=source_hash,
            defaults={
                "organization": organization,
                "subject": subject.casefold(),
                "company_ids": [str(item) for item in company_ids[:200]],
                "justification": justification[:500],
                "expires_at": expires_at,
            },
        )
    RemoteSupportGrant.objects.filter(organization=organization).exclude(
        source_hash__in=active_hashes
    ).delete()


def apply_control(binding: ControlPlaneBinding, control: dict[str, Any], signature: object) -> None:
    _verify_signature(binding, control, signature)
    if str(control.get("installation_id")) != str(binding.remote_installation_id):
        raise ControlPlaneError("Controle destinado a outra instalação.")
    if str(control.get("hub_organization_id")) != str(binding.organization_id):
        raise ControlPlaneError("Controle destinado a outro escritório.")
    expires_at = _parse_datetime(control.get("expires_at"))
    now = timezone.now()
    if expires_at <= now or expires_at > now + CONTROL_CACHE_TTL + timedelta(minutes=1):
        raise ControlPlaneError("Expiração do controle fora da política.")
    version = control.get("configuration_version")
    if not isinstance(version, int) or version < binding.applied_configuration_version:
        raise ControlPlaneError("Versão de controle inválida ou regressiva.")
    if control.get("status") != "active":
        raise ControlPlaneError("Instalação revogada ou suspensa pelo CRMew.")
    with transaction.atomic():
        _sync_grants(binding.organization, control)
        _sync_modules(binding.organization, control)
        _sync_intelligence_policy(binding.organization, control)
        _sync_support_grants(binding.organization, control)
        binding.cached_control = control
        binding.cache_expires_at = expires_at
        binding.applied_configuration_version = version
        binding.last_sync_at = now
        binding.last_sync_error = ""
        binding.save(
            update_fields=[
                "cached_control",
                "cache_expires_at",
                "applied_configuration_version",
                "last_sync_at",
                "last_sync_error",
                "updated_at",
            ]
        )


def sync_binding(binding: ControlPlaneBinding) -> None:
    try:
        payload = _fetch_json(_signed_request(binding, method="GET", path="/control/v1/state/"))
        control = payload.get("control")
        if not isinstance(control, dict):
            raise ControlPlaneError("CRMew não enviou controle.")
        apply_control(binding, control, payload.get("signature"))
        acknowledge_control(binding)
    except ControlPlaneError as exc:
        binding.last_sync_error = str(exc)[:240]
        binding.save(update_fields=["last_sync_error", "updated_at"])
        raise


def acknowledge_control(binding: ControlPlaneBinding) -> None:
    """Confirm the exact signed configuration version applied by this installation."""
    payload = canonical_json({"configuration_version": binding.applied_configuration_version})
    response = _fetch_json(
        _signed_request(
            binding,
            method="POST",
            path="/control/v1/configuration-ack/",
            body=payload,
        )
    )
    if response.get("status") != "accepted":
        raise ControlPlaneError("CRMew não confirmou a aplicação da configuração.")


def send_heartbeat(
    binding: ControlPlaneBinding,
    *,
    release: str,
    health: str,
    sync_lag_seconds: int,
    error_fingerprint: str = "",
) -> None:
    """Send metadata-only operational state. A failed heartbeat never affects fiscal work."""
    payload = canonical_json(
        {
            "release": release[:120],
            "applied_configuration_version": max(0, binding.applied_configuration_version),
            "health": health[:24],
            "sync_lag_seconds": max(0, int(sync_lag_seconds)),
            "error_fingerprint": error_fingerprint[:128],
        }
    )
    response = _fetch_json(
        _signed_request(binding, method="POST", path="/control/v1/heartbeat/", body=payload)
    )
    if response.get("status") != "accepted":
        raise ControlPlaneError("CRMew não confirmou o heartbeat.")


def acknowledge_release(
    binding: ControlPlaneBinding,
    *,
    version: str,
    outcome: str,
    diagnostics: dict[str, str] | None = None,
) -> None:
    """Confirm a release result through the installation's existing Ed25519 identity."""
    if not version.strip() or outcome not in {"released", "failed", "rolled_back"}:
        raise ControlPlaneError("Confirmação de release inválida.")
    payload = canonical_json(
        {
            "version": version[:120],
            "outcome": outcome,
            "diagnostics": dict(diagnostics or {}),
        }
    )
    response = _fetch_json(
        _signed_request(binding, method="POST", path="/control/v1/release-ack/", body=payload)
    )
    if response.get("status") != "accepted":
        raise ControlPlaneError("CRMew não confirmou o status da release.")
