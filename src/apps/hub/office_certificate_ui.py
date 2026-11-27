"""e-CNPJ do escritório na tela: estado e ações, uma só implementação.

Configurações é a casa do envio, da troca e da revogação. Procurações só mostra o estado
(`certificate_summary`) e aponta para lá. A senha do .pfx existe só dentro do envio: nunca
volta ao template, nunca vai para mensagem nem log.
"""

from __future__ import annotations

from typing import Any

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import reverse

from apps.hub.models import OfficeCertificate
from apps.hub.nfse_procuracao import current_office_certificate
from apps.hub.office_certificate import (
    OfficeCertificateError,
    revoke_office_certificate,
    store_office_certificate,
)
from apps.organizations.models import Membership, Organization

MAX_PFX_BYTES = 512_000
EXPIRING_DAYS = 30
CERTIFICATE_MANAGERS = {Membership.Role.OWNER, Membership.Role.ADMIN}
ACTIONS = {"upload-certificate", "revoke-certificate"}
REFUSAL = "Somente owners e administradores cuidam do e-CNPJ."


def mask_cnpj(cnpj: str) -> str:
    digits = "".join(ch for ch in cnpj if ch.isalnum())
    if len(digits) != 14:
        return cnpj
    return f"{digits[:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:]}"


def can_manage_certificate(context: dict[str, object]) -> bool:
    """Owner or admin of the office, never a support session."""

    membership = context.get("membership")
    return bool(
        context.get("support_session") is None
        and isinstance(membership, Membership)
        and membership.role in CERTIFICATE_MANAGERS
    )


def certificate_summary(office: Organization, now: Any) -> dict[str, Any]:
    current = current_office_certificate(office.pk, now=now)
    if current is not None:
        days = (current.valid_until - now).days
        expiring = days <= EXPIRING_DAYS
        return {
            "certificate": current,
            "state": "expiring" if expiring else "valid",
            "label": "vence em breve" if expiring else "válido",
            "tone": "is-warning" if expiring else "is-active",
            "days_left": days,
            "cnpj": mask_cnpj(current.cnpj),
            "quarantined": bool(current.quarantined_until and current.quarantined_until > now),
        }
    latest = OfficeCertificate.objects.filter(organization=office).order_by("-valid_until").first()
    if latest is None:
        return {"certificate": None, "state": "none", "label": "ausente", "tone": "is-danger"}
    revoked = latest.revoked_at is not None
    return {
        "certificate": None,
        "state": "revoked" if revoked else "expired",
        "label": "revogado" if revoked else "vencido",
        "tone": "is-danger",
        "cnpj": mask_cnpj(latest.cnpj),
    }


def handle_certificate_post(
    request: HttpRequest, office: Organization, context: dict[str, object], refuse: Any
) -> HttpResponse:
    """Upload or revoke. `refuse` is the workspace's own 403 page renderer."""

    if not context.get("support_can_mutate") or not can_manage_certificate(context):
        return refuse(request, REFUSAL)  # type: ignore[no-any-return]
    target = redirect(f"{reverse('hub:settings')}#ecnpj")
    if request.POST.get("action") == "revoke-certificate":
        certificate = current_office_certificate(office.pk)
        if certificate is not None:
            revoke_office_certificate(certificate, actor=request.user, request=request)
            messages.success(request, "e-CNPJ revogado. A coleta do escritório parou.")
        return target
    upload = request.FILES.get("pfx")
    if upload is None or not (upload.name or "").lower().endswith((".pfx", ".p12")):
        messages.error(request, "Selecione o arquivo .pfx ou .p12 do e-CNPJ.")
    elif (upload.size or 0) > MAX_PFX_BYTES:
        messages.error(request, "O arquivo é maior que o esperado para um e-CNPJ A1.")
    else:
        try:
            stored = store_office_certificate(
                organization=office,
                pfx_bytes=upload.read(),
                password=request.POST.get("password", ""),
                actor=request.user,
                request=request,
            )
        except OfficeCertificateError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"e-CNPJ enviado, válido até {stored.valid_until:%d/%m/%Y}.")
    return target
