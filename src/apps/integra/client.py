from __future__ import annotations

import base64
import binascii
import json
import os
import ssl
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    PrivateFormat,
    pkcs12,
)
from django.conf import settings
from django.core.cache import cache
from django.core.exceptions import SuspiciousOperation
from django.db import DatabaseError

from apps.integra.catalog import ServiceSpec, service
from apps.integra.envelope import Party, build
from apps.integra.errors import (
    IntegraAuthenticationError,
    IntegraConfigurationError,
    IntegraNotAuthorized,
    IntegraServiceError,
    IntegraTransportError,
)

AUTH_URL = "https://autenticacao.sapi.serpro.gov.br/authenticate"
BASE_URLS = {
    "trial": "https://gateway.apiserpro.serpro.gov.br/integra-contador-trial/v1",
    "production": "https://gateway.apiserpro.serpro.gov.br/integra-contador/v1",
}
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 4_000_000
# The store reports expires_in around 2008 seconds. Retire the token early so a call is
# never dispatched against one that expires in flight.
TOKEN_SAFETY_MARGIN_SECONDS = 120
TOKEN_CACHE_KEY = "integra:token"  # noqa: S105 - a cache key, not a credential


@dataclass(frozen=True)
class Token:
    access_token: str
    jwt_token: str


class Transport(Protocol):
    """Seam for tests, mirroring intelligence.connectors' connection_factory."""

    def __call__(
        self,
        url: str,
        *,
        data: bytes,
        headers: dict[str, str],
        context: ssl.SSLContext | None,
    ) -> tuple[int, bytes]: ...


def _urlopen_transport(
    url: str, *, data: bytes, headers: dict[str, str], context: ssl.SSLContext | None
) -> tuple[int, bytes]:
    request = Request(url, data=data, method="POST")  # noqa: S310 - fixed Serpro origins
    for name, value in headers.items():
        request.add_header(name, value)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS, context=context) as response:  # noqa: S310
            return int(response.status), response.read(MAX_RESPONSE_BYTES)
    except HTTPError as exc:
        return int(exc.code), exc.read(MAX_RESPONSE_BYTES)
    except (OSError, URLError) as exc:
        raise IntegraTransportError(f"Integra Contador indisponível: {exc}") from exc


@dataclass(frozen=True)
class Credentials:
    consumer_key: str
    consumer_secret: str
    certificate_path: Path
    certificate_password: str
    contratante: str
    autor_pedido: str
    environment: str
    certificate_blob: bytes | None = None

    @property
    def base_url(self) -> str:
        try:
            return BASE_URLS[self.environment]
        except KeyError as exc:
            raise IntegraConfigurationError(
                f"INTEGRA_ENVIRONMENT deve ser 'trial' ou 'production'; got {self.environment!r}."
            ) from exc


def credentials_from_settings() -> Credentials:
    certificate_blob: bytes | None = None
    certificate_password = settings.INTEGRA_CERTIFICATE_PASSWORD
    consumer_key = settings.INTEGRA_CONSUMER_KEY
    consumer_secret = settings.INTEGRA_CONSUMER_SECRET
    contratante = settings.INTEGRA_CONTRATANTE_CNPJ
    autor_pedido = settings.INTEGRA_AUTOR_PEDIDO_CNPJ
    environment = settings.INTEGRA_ENVIRONMENT
    try:
        from apps.platform.models import PlatformConfiguration

        platform_configuration = PlatformConfiguration.objects.filter(key="default").first()
        if platform_configuration and platform_configuration.integra_certificate_blob:
            certificate_blob = base64.b64decode(
                platform_configuration.integra_certificate_blob, validate=True
            )
            certificate_password = platform_configuration.integra_certificate_password
        if platform_configuration:
            consumer_key = platform_configuration.integra_consumer_key or consumer_key
            consumer_secret = platform_configuration.integra_consumer_secret or consumer_secret
            contratante = platform_configuration.integra_contratante_cnpj or contratante
            autor_pedido = platform_configuration.integra_autor_pedido_cnpj or autor_pedido
            environment = platform_configuration.integra_environment or environment
    except (DatabaseError, ValueError, binascii.Error, SuspiciousOperation) as exc:
        if not settings.INTEGRA_CERTIFICATE_PATH:
            raise IntegraConfigurationError(
                "Não foi possível carregar o certificado central armazenado."
            ) from exc
    missing = [
        name
        for name, value in (
            ("INTEGRA_CONSUMER_KEY", consumer_key),
            ("INTEGRA_CONSUMER_SECRET", consumer_secret),
            ("INTEGRA_CONTRATANTE_CNPJ", contratante),
        )
        if not value
    ]
    if certificate_blob is None and not settings.INTEGRA_CERTIFICATE_PATH:
        missing.append("certificado A1 da Mewstack")
    if missing:
        raise IntegraConfigurationError(f"Configuração ausente: {', '.join(missing)}.")
    return Credentials(
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        certificate_path=(
            Path(settings.INTEGRA_CERTIFICATE_PATH) if settings.INTEGRA_CERTIFICATE_PATH else Path()
        ),
        certificate_password=certificate_password,
        contratante=contratante,
        autor_pedido=autor_pedido or contratante,
        environment=environment,
        certificate_blob=certificate_blob,
    )


def build_ssl_context(credentials: Credentials) -> ssl.SSLContext:
    """Present the e-CNPJ A1 certificate as the TLS client identity.

    ssl only loads a chain from a file, so the PKCS#12 is converted to a PEM pair in a
    private temporary file that is removed as soon as the context holds it. The passphrase
    protecting that temporary file is random and never leaves this function.
    """

    if credentials.certificate_blob is not None:
        blob = credentials.certificate_blob
    elif credentials.certificate_path.is_file():
        blob = credentials.certificate_path.read_bytes()
    else:
        raise IntegraConfigurationError("Certificado A1 da Mewstack não configurado.")
    password = credentials.certificate_password.encode() or None
    try:
        key, certificate, extra = pkcs12.load_key_and_certificates(blob, password)
    except ValueError as exc:
        raise IntegraConfigurationError(
            "Não foi possível abrir o certificado com esta senha."
        ) from exc
    if key is None or certificate is None:
        raise IntegraConfigurationError("O arquivo não contém um par certificado/chave.")

    passphrase = base64.urlsafe_b64encode(os.urandom(24))
    pem = key.private_bytes(
        Encoding.PEM, PrivateFormat.PKCS8, BestAvailableEncryption(passphrase)
    ) + certificate.public_bytes(Encoding.PEM)
    for issuer in extra or []:
        pem += issuer.public_bytes(Encoding.PEM)

    context = ssl.create_default_context()
    context.minimum_version = ssl.TLSVersion.TLSv1_2
    handle, name = tempfile.mkstemp(suffix=".pem")
    try:
        with os.fdopen(handle, "wb") as chain:
            chain.write(pem)
        context.load_cert_chain(name, password=passphrase)
    finally:
        os.unlink(name)
    return context


class IntegraClient:
    def __init__(
        self,
        credentials: Credentials | None = None,
        *,
        transport: Transport | None = None,
        ssl_context: ssl.SSLContext | None = None,
    ) -> None:
        self.credentials = credentials or credentials_from_settings()
        self._transport: Transport = transport or _urlopen_transport
        self._ssl_context = ssl_context
        self._explicit_context = ssl_context is not None or transport is not None

    @property
    def ssl_context(self) -> ssl.SSLContext | None:
        if self._ssl_context is None and not self._explicit_context:
            self._ssl_context = build_ssl_context(self.credentials)
        return self._ssl_context

    def authenticate(self, *, force: bool = False) -> Token:
        if not force:
            cached = cache.get(TOKEN_CACHE_KEY)
            if isinstance(cached, dict):
                return Token(cached["access_token"], cached["jwt_token"])

        pair = f"{self.credentials.consumer_key}:{self.credentials.consumer_secret}"
        status, raw = self._transport(
            AUTH_URL,
            data=urlencode({"grant_type": "client_credentials"}).encode(),
            headers={
                "Authorization": f"Basic {base64.b64encode(pair.encode()).decode()}",
                "Role-Type": "TERCEIROS",
                "Content-Type": "application/x-www-form-urlencoded",
            },
            context=self.ssl_context,
        )
        payload = _decode(raw)
        if status != 200 or "access_token" not in payload:
            raise IntegraAuthenticationError(
                f"A loja do Serpro recusou as credenciais (HTTP {status})."
            )
        token = Token(str(payload["access_token"]), str(payload.get("jwt_token", "")))
        expires_in = int(payload.get("expires_in", 0))
        ttl = max(expires_in - TOKEN_SAFETY_MARGIN_SECONDS, 0)
        if ttl:
            cache.set(
                TOKEN_CACHE_KEY,
                {"access_token": token.access_token, "jwt_token": token.jwt_token},
                ttl,
            )
        return token

    def call(
        self,
        service_key: str,
        *,
        contribuinte: str,
        autor_pedido: str | None = None,
        dados: dict[str, Any] | str | None = None,
    ) -> dict[str, Any]:
        """Dispatch one catalogued service. There is no way to name an arbitrary endpoint."""

        spec = service(service_key)
        envelope = build(
            spec=spec,
            contratante=Party(self.credentials.contratante),
            autor_pedido=Party(autor_pedido or self.credentials.autor_pedido),
            contribuinte=Party(contribuinte),
            dados=dados,
        )
        return self._dispatch(spec, envelope)

    def _dispatch(self, spec: ServiceSpec, envelope: dict[str, Any]) -> dict[str, Any]:
        token = self.authenticate()
        headers = {
            "Authorization": f"Bearer {token.access_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if token.jwt_token:
            headers["jwt_token"] = token.jwt_token
        status, raw = self._transport(
            f"{self.credentials.base_url}/{spec.verb.value}",
            data=json.dumps(envelope, ensure_ascii=False).encode(),
            headers=headers,
            context=self.ssl_context,
        )
        payload = _decode(raw)
        if status == 401:
            raise IntegraAuthenticationError("Token recusado pelo gateway.")
        if status == 403:
            raise IntegraNotAuthorized(
                "Sem autorização para este contribuinte. Verifique a procuração no e-CAC.",
                status=status,
                payload=payload,
            )
        if status >= 400:
            raise IntegraServiceError(
                _message(payload) or f"Integra Contador recusou a chamada (HTTP {status}).",
                status=status,
                code=str(payload.get("codigo", "")),
                payload=payload,
            )
        return payload


def _decode(raw: bytes) -> dict[str, Any]:
    try:
        payload = json.loads(raw or b"{}")
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IntegraTransportError("Integra Contador devolveu uma resposta ilegível.") from exc
    if not isinstance(payload, dict):
        raise IntegraTransportError("Integra Contador devolveu um payload inesperado.")
    return payload


def _message(payload: dict[str, Any]) -> str:
    for key in ("mensagem", "message", "erro", "error_description"):
        value = payload.get(key)
        if isinstance(value, str) and value:
            return value
    mensagens = payload.get("mensagens")
    if isinstance(mensagens, list) and mensagens:
        first = mensagens[0]
        if isinstance(first, dict):
            text = first.get("texto") or first.get("mensagem")
            if isinstance(text, str):
                return text
    return ""
