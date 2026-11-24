"""T10.3: the identity mode of each office. Flag off by default; fake transport only."""

from __future__ import annotations

import base64
import json
import ssl
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.test import override_settings

from apps.hub.models import OfficeCertificate
from apps.integra import identity
from apps.integra.client import Credentials, IntegraClient
from apps.integra.errors import IntegraConfigurationError
from apps.integra.identity import office_access
from apps.integra.models import OfficeSerproIdentity
from apps.integra.termo import verify_termo
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db

OFFICE = "11444777000161"
PLATFORM = Credentials(
    consumer_key="platform-key",
    consumer_secret="platform-secret",
    certificate_path=Path("unused.pfx"),
    certificate_password="",
    contratante="11222333000181",
    autor_pedido="11222333000181",
    environment="trial",
)
TOKEN_ANSWER = {
    "autenticar_procurador_token": "tok",
    "data_hora_expiracao": "2099-01-01T00:00:00",
}


class Gateway:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self, url: str, *, data: bytes, headers: dict[str, str], context: ssl.SSLContext | None
    ) -> tuple[int, bytes]:
        if url.endswith("/authenticate"):
            body: dict[str, Any] = {"access_token": "a", "jwt_token": "j", "expires_in": 2008}
        else:
            envelope = json.loads(data)
            self.calls.append({"envelope": envelope, "headers": headers, "url": url})
            body = {"status": 200, "mensagens": [], "dados": json.dumps(TOKEN_ANSWER)}
        return 200, json.dumps(body).encode()


@pytest.fixture(autouse=True)
def _clean() -> None:
    cache.clear()


@pytest.fixture
def gateway(monkeypatch: pytest.MonkeyPatch) -> Gateway:
    monkeypatch.setattr(identity, "credentials_from_settings", lambda: PLATFORM)
    return Gateway()


def _factory(gateway: Gateway) -> Callable[..., IntegraClient]:
    def make(credentials: Credentials | None = None) -> IntegraClient:
        return IntegraClient(credentials or PLATFORM, transport=gateway)

    return make


def _certificate(organization: Organization) -> OfficeCertificate:
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"ESCRITORIO TESTE:{OFFICE}")])
    now = datetime.now(UTC)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=30))
        .sign(key, hashes.SHA256())
    )
    blob = pkcs12.serialize_key_and_certificates(
        b"e", key, cert, None, serialization.BestAvailableEncryption(b"senha")
    )
    return OfficeCertificate.objects.create(
        organization=organization,
        label="e-CNPJ",
        subject_name=name.rfc4514_string(),
        cnpj=OFFICE,
        valid_from=now - timedelta(days=1),
        valid_until=now + timedelta(days=30),
        pfx_blob=base64.b64encode(blob).decode(),
        password="senha",
        fingerprint_sha256="f" * 64,
    )


def test_the_flag_is_off_by_default_and_everything_stays_as_before(
    organization: Organization, gateway: Gateway
) -> None:
    OfficeSerproIdentity.objects.create(
        organization=organization, mode=OfficeSerproIdentity.Mode.PLATFORM_TERMO
    )

    access = office_access(organization, client_factory=_factory(gateway))
    access.call("sitfis.protocolo", contribuinte=OFFICE)

    assert access.mode == "default"
    assert "autenticar_procurador_token" not in gateway.calls[0]["headers"]
    assert gateway.calls[0]["envelope"]["autorPedidoDados"]["numero"] == PLATFORM.autor_pedido


@override_settings(INTEGRA_OFFICE_IDENTITY_ENABLED=True)
def test_an_office_without_identity_row_keeps_the_default(
    organization: Organization, gateway: Gateway
) -> None:
    assert office_access(organization, client_factory=_factory(gateway)).mode == "default"


@override_settings(INTEGRA_OFFICE_IDENTITY_ENABLED=True, INTEGRA_CONTRATANTE_NAME="MEWSTACK LTDA")
def test_platform_mode_signs_the_term_and_sends_the_token(
    organization: Organization, gateway: Gateway
) -> None:
    OfficeSerproIdentity.objects.create(
        organization=organization, mode=OfficeSerproIdentity.Mode.PLATFORM_TERMO
    )
    _certificate(organization)

    access = office_access(organization, client_factory=_factory(gateway))
    access.call("sitfis.protocolo", contribuinte="52998224725")

    term, request = gateway.calls
    sent = json.loads(term["envelope"]["pedidoDados"]["dados"])["xml"]
    signed = base64.b64decode(sent).decode()
    assert verify_termo(signed) and 'nome="MEWSTACK LTDA"' in signed
    assert request["headers"]["autenticar_procurador_token"] == "tok"
    assert request["envelope"]["autorPedidoDados"]["numero"] == OFFICE
    assert request["envelope"]["contratante"]["numero"] == PLATFORM.contratante


@override_settings(INTEGRA_OFFICE_IDENTITY_ENABLED=True)
def test_own_contract_mode_uses_the_office_credentials_and_no_term(
    organization: Organization, gateway: Gateway
) -> None:
    OfficeSerproIdentity.objects.create(
        organization=organization,
        mode=OfficeSerproIdentity.Mode.OWN_CONTRACT,
        consumer_key="office-key",
        consumer_secret="office-secret",
    )
    _certificate(organization)
    seen: list[Credentials] = []

    def make(credentials: Credentials | None = None) -> IntegraClient:
        assert credentials is not None
        seen.append(credentials)
        return IntegraClient(credentials, transport=gateway)

    office_access(organization, client_factory=make).call(
        "sitfis.protocolo", contribuinte="52998224725"
    )

    assert (seen[0].consumer_key, seen[0].consumer_secret) == ("office-key", "office-secret")
    assert seen[0].contratante == seen[0].autor_pedido == OFFICE
    assert "autenticar_procurador_token" not in gateway.calls[0]["headers"]


@override_settings(INTEGRA_OFFICE_IDENTITY_ENABLED=True)
def test_a_mode_that_needs_the_office_certificate_refuses_without_it(
    organization: Organization, gateway: Gateway
) -> None:
    OfficeSerproIdentity.objects.create(
        organization=organization, mode=OfficeSerproIdentity.Mode.PLATFORM_TERMO
    )

    with pytest.raises(IntegraConfigurationError, match="e-CNPJ"):
        office_access(organization, client_factory=_factory(gateway))


def test_an_own_contract_without_credentials_cannot_be_saved(organization: Organization) -> None:
    with pytest.raises(IntegrityError), transaction.atomic():
        OfficeSerproIdentity.objects.create(
            organization=organization, mode=OfficeSerproIdentity.Mode.OWN_CONTRACT
        )
