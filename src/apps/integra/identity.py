"""Which Serpro identity an office calls with (T10.3).

* `default`: the behavior before E10, the platform contract with no term. It is also what every
  office gets while `INTEGRA_OFFICE_IDENTITY_ENABLED` is off (the flag is off by default).
* `platform_termo`: the platform contract, plus the Termo de Autorização signed with the e-CNPJ
  of the office, sent as `autenticar_procurador_token`.
* `own_contract`: the office's own contract: its consumer key and secret, mTLS with its own
  e-CNPJ A1, and the office as contractor and author.
"""

from __future__ import annotations

import base64
from collections.abc import Callable
from dataclasses import dataclass, replace
from typing import Any

from django.conf import settings
from django.utils import timezone

from apps.hub.models import OfficeCertificate
from apps.integra.client import IntegraClient, credentials_from_settings
from apps.integra.envelope import BatchParty
from apps.integra.errors import IntegraConfigurationError
from apps.integra.governor import GovernedClient
from apps.integra.models import OfficeSerproIdentity
from apps.integra.termo import TermoSigner, obter_token
from apps.organizations.models import Organization


def identity_enabled() -> bool:
    return bool(getattr(settings, "INTEGRA_OFFICE_IDENTITY_ENABLED", False))


def _active_certificate(organization: Organization) -> OfficeCertificate:
    certificate = (
        OfficeCertificate.objects.filter(organization=organization, revoked_at__isnull=True)
        .order_by("-created_at")
        .first()
    )
    if certificate is None:
        raise IntegraConfigurationError("O escritório não enviou o e-CNPJ A1.")
    if certificate.valid_until is not None and certificate.valid_until <= timezone.now():
        raise IntegraConfigurationError("O e-CNPJ do escritório está vencido.")
    return certificate


def _common_name(subject: str) -> str:
    name = subject.split("CN=", 1)[-1].split(",", 1)[0]
    return name.split(":", 1)[0].strip() or "ESCRITORIO"


@dataclass
class OfficeAccess:
    """A governed client plus the way to get the token of the term, when the mode needs one."""

    governed: GovernedClient
    mode: str
    token_provider: Callable[[], str] | None = None
    author: str | None = None

    def call(
        self,
        service_key: str,
        *,
        contribuinte: str | BatchParty,
        dados: dict[str, Any] | str | None = None,
        autor_pedido: str | None = None,
    ) -> dict[str, Any]:
        token = self.token_provider() if self.token_provider else None
        return self.governed.call(
            service_key,
            contribuinte=contribuinte,
            dados=dados,
            autor_pedido=autor_pedido or self.author,
            autenticar_procurador_token=token,
        )


def office_access(
    organization: Organization,
    *,
    conversation_id: str = "",
    client_factory: Callable[..., IntegraClient] = IntegraClient,
) -> OfficeAccess:
    identity = OfficeSerproIdentity.objects.filter(organization=organization).first()
    mode = identity.mode if identity and identity_enabled() else OfficeSerproIdentity.Mode.DEFAULT
    if mode == OfficeSerproIdentity.Mode.DEFAULT or identity is None:
        client = client_factory()
        return OfficeAccess(
            GovernedClient(client, organization, conversation_id=conversation_id), str(mode)
        )

    certificate = _active_certificate(organization)
    pfx = base64.b64decode(certificate.pfx_blob)
    if mode == OfficeSerproIdentity.Mode.OWN_CONTRACT:
        platform = credentials_from_settings()
        credentials = replace(
            platform,
            consumer_key=identity.consumer_key,
            consumer_secret=identity.consumer_secret,
            contratante=certificate.cnpj,
            autor_pedido=certificate.cnpj,
            certificate_blob=pfx,
            certificate_password=certificate.password,
        )
        client = client_factory(credentials)
        return OfficeAccess(
            GovernedClient(client, organization, conversation_id=conversation_id),
            str(mode),
            author=certificate.cnpj,
        )

    client = client_factory()
    signer = TermoSigner(
        pfx_bytes=pfx,
        password=certificate.password,
        autor_numero=certificate.cnpj,
        autor_nome=_common_name(certificate.subject_name),
        destinatario_cnpj=client.credentials.contratante,
        destinatario_nome=str(getattr(settings, "INTEGRA_CONTRATANTE_NAME", "CONTRATANTE")),
    )
    return OfficeAccess(
        GovernedClient(client, organization, conversation_id=conversation_id),
        str(mode),
        token_provider=lambda: obter_token(client, signer),
        author=certificate.cnpj,
    )
