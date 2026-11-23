"""Envio do e-CNPJ A1 do escritório, o procurador no ADN (D-305)."""

from __future__ import annotations

import base64
import hashlib
from typing import Any

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives.serialization import pkcs12
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.cnpj import normalize_cnpj
from apps.hub.models import OfficeCertificate, OfficeProfile
from apps.hub.services import certificate_cnpjs
from apps.organizations.models import Organization


class OfficeCertificateError(ValueError):
    """Message safe to show to the person who uploaded the file."""


def office_cnpj(organization: Organization) -> str | None:
    """The office CNPJ from its profile, or None while the identity step is pending."""

    profile = OfficeProfile.objects.filter(organization=organization).first()
    if profile is None or not profile.cnpj:
        return None
    try:
        return normalize_cnpj(profile.cnpj)
    except ValidationError:
        return None


def uses_procuracao(organization: Organization) -> bool:
    return OfficeProfile.objects.filter(
        organization=organization,
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
    ).exists()


@transaction.atomic
def store_office_certificate(
    *,
    organization: Organization,
    pfx_bytes: bytes,
    password: str,
    actor: Any = None,
    request: Any = None,
) -> OfficeCertificate:
    """Validate and keep the office e-CNPJ. The file and the password never leave this call."""

    if not uses_procuracao(organization):
        raise OfficeCertificateError("Este escritório coleta com o A1 de cada empresa.")
    expected = office_cnpj(organization)
    if expected is None:
        raise OfficeCertificateError("Informe o CNPJ do escritório antes de enviar o e-CNPJ.")
    try:
        key, parsed, _chain = pkcs12.load_key_and_certificates(pfx_bytes, password.encode() or None)
    except (TypeError, ValueError, UnsupportedAlgorithm) as exc:
        raise OfficeCertificateError("Não foi possível abrir o arquivo com esta senha.") from exc
    if key is None or parsed is None:
        raise OfficeCertificateError("O arquivo não contém um e-CNPJ A1 com chave privada.")
    now = timezone.now()
    valid_from = parsed.not_valid_before_utc
    valid_until = parsed.not_valid_after_utc
    if valid_until <= now:
        raise OfficeCertificateError("Este e-CNPJ está vencido.")
    if valid_from > now:
        raise OfficeCertificateError("Este e-CNPJ ainda não é válido.")
    candidates = certificate_cnpjs(parsed)
    if not candidates:
        raise OfficeCertificateError("O certificado não informa um CNPJ. Use um e-CNPJ ICP-Brasil.")
    matching = sorted(item for item in candidates if item[:8] == expected[:8])
    if not matching:
        raise OfficeCertificateError("O CNPJ do certificado não é o do escritório.")
    cnpj = expected if expected in matching else matching[0]
    fingerprint = hashlib.sha256(pfx_bytes).hexdigest()
    existing = OfficeCertificate.objects.filter(
        organization=organization, fingerprint_sha256=fingerprint
    ).first()
    if existing is not None:
        if existing.revoked_at is None:
            return existing
        existing.revoked_at = None
        existing.quarantined_until = None
        existing.password = password
        existing.save(update_fields=["revoked_at", "quarantined_until", "password", "updated_at"])
        certificate = existing
    else:
        certificate = OfficeCertificate.objects.create(
            organization=organization,
            label=parsed.subject.rfc4514_string()[:120] or "e-CNPJ do escritório",
            subject_name=parsed.subject.rfc4514_string()[:240],
            cnpj=cnpj,
            valid_from=valid_from,
            valid_until=valid_until,
            pfx_blob=base64.b64encode(pfx_bytes).decode("ascii"),
            password=password,
            fingerprint_sha256=fingerprint,
            uploaded_by=actor if getattr(actor, "is_authenticated", False) else None,
        )
    record_event(
        action="hub.office_certificate.uploaded",
        actor=actor,
        organization=organization,
        target=certificate,
        request=request,
        metadata={"fingerprint_prefix": fingerprint[:12]},
    )
    from apps.hub.nfse_procuracao import seed_procuracao_syncs

    seed_procuracao_syncs(organization_id=organization.pk)
    if settings.NFSE_PROCURACAO_SYNC_ENABLED:
        from apps.hub.tasks_procuracao import dispatch_procuracao_syncs

        transaction.on_commit(dispatch_procuracao_syncs.delay)
    return certificate


@transaction.atomic
def revoke_office_certificate(
    certificate: OfficeCertificate, *, actor: Any = None, request: Any = None
) -> None:
    """Take the e-CNPJ out of use. Collection of every company of the office stops with it."""

    if certificate.revoked_at is not None:
        return
    certificate.revoked_at = timezone.now()
    certificate.save(update_fields=["revoked_at", "updated_at"])
    record_event(
        action="hub.office_certificate.revoked",
        actor=actor,
        organization=certificate.organization,
        target=certificate,
        request=request,
        metadata={"fingerprint_prefix": certificate.fingerprint_sha256[:12]},
    )
