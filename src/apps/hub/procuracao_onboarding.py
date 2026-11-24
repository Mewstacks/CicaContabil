"""Passos do assistente de primeiros passos para escritório em modo procuração (D-304, E2).

Cada passo só aparece como feito quando o fato que ele nomeia é verdadeiro no banco: nada de
"visitou a tela" nem de passo concluído por clique. Escritório legado (A1 por empresa) continua com
a lista antiga de `setup_center`; esta lista só substitui a dele em modo `procuracao`.
"""

from __future__ import annotations

from typing import Any

from django.urls import reverse

from apps.hub.models import (
    ClientCompany,
    NfseDocument,
    NfseProcuracaoRequest,
    NfseSync,
    OfficeProfile,
)
from apps.hub.nfse_procuracao import current_office_certificate
from apps.organizations.models import Membership, Organization


def _plural(count: int, singular: str, plural: str) -> str:
    return f"{count} {singular if count == 1 else plural}"


def procuracao_setup_steps(
    *,
    office: Organization,
    profile: OfficeProfile,
    mfa_complete: bool,
    roster_available: bool = True,
    lane_on: bool = True,
) -> list[dict[str, Any]]:
    """Os passos, na ordem em que o escritório os percorre até a primeira NFS-e."""

    companies = ClientCompany.objects.filter(organization=office, active=True)
    syncs = NfseSync.objects.filter(
        organization=office,
        credential_mode=NfseSync.CredentialMode.PROCURACAO,
        company__active=True,
    )
    status = NfseSync.ProcuracaoStatus
    ok = syncs.filter(procuracao_status=status.OK).count()
    missing = syncs.filter(procuracao_status=status.MISSING).count()
    asked = NfseProcuracaoRequest.objects.filter(
        organization=office, status=NfseProcuracaoRequest.Status.SENT
    ).exists()
    has_documents = NfseDocument.objects.filter(organization=office).exists()
    has_certificate = current_office_certificate(office.pk) is not None
    has_companies = companies.exists()
    team = Membership.objects.filter(organization=office, is_active=True).count()

    procuracoes = reverse("hub:procuracoes")
    return [
        {
            "label": "Confirmar escritório",
            "done": bool(profile.cnpj_hash),
            "action_label": "Confirmar dados",
            "url": f"{reverse('hub:setup')}#office-heading",
        },
        {
            "label": "Enviar e-CNPJ",
            "done": has_certificate,
            "action_label": "Enviar e-CNPJ",
            "url": procuracoes,
        },
        {
            "label": "Importar carteira",
            "done": has_companies,
            "note": _plural(companies.count(), "empresa", "empresas") if has_companies else "",
            "action_label": "Importar carteira",
            "url": reverse("hub:roster") if roster_available else reverse("hub:companies"),
        },
        {
            "label": "Pedir procurações",
            "done": asked or ok > 0,
            "note": f"{missing} aguardando procuração" if missing else "",
            "action_label": "Pedir procurações",
            "url": f"{procuracoes}?status=missing",
        },
        {
            "label": "Receber a primeira NFS-e",
            "done": has_documents,
            "note": (
                ""
                if has_documents
                else (
                    f"{_plural(ok, 'empresa em dia', 'empresas em dia')}"
                    if ok
                    else ("" if lane_on else "Coleta desligada neste ambiente")
                )
            ),
            "action_label": "Ver notas",
            "url": reverse("hub:nfse-center"),
        },
        {
            "label": "Convidar sua equipe",
            "done": team > 1,
            "recommended": True,
            "action_label": "Gerenciar equipe",
            "url": reverse("hub:team"),
        },
        {
            "label": "Proteger sua conta",
            "done": mfa_complete,
            "recommended": True,
            "personal_action": True,
            "action_label": "Ativar MFA",
            "url": f"{reverse('accounts:mfa-setup')}?next={reverse('hub:setup')}",
        },
    ]
