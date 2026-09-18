"""Official Domínio/Onvio invoice API adapter.

This adapter implements only the endpoints documented by Thomson Reuters for
ERP integrations: OAuth client credentials, activation, XML batch submission,
and batch status. It deliberately does not claim to read accounting, fiscal,
or payroll records because that capability is not part of this public API.
"""

from __future__ import annotations

import base64
import json
import mimetypes
import secrets
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

AUTH_URL = "https://auth.thomsonreuters.com/oauth/token"
API_BASE_URL = "https://api.onvio.com.br/dominio"
ONVIO_AUDIENCE = "409f91f6-dc17-44c8-a5d8-e0a1bafd8b67"


class DominioApiError(RuntimeError):
    """A safe API failure message that never includes credentials or XML."""


@dataclass(frozen=True)
class HttpResponse:
    status: int
    body: bytes


HttpTransport = Callable[[str, str, Mapping[str, str], bytes | None], HttpResponse]


@dataclass(frozen=True)
class DominioApiCredentials:
    client_id: str
    client_secret: str
    office_integration_key: str
    integration_key: str = ""

    def validate(self) -> None:
        if not self.client_id.strip() or not self.client_secret.strip():
            raise DominioApiError("Informe Client ID e Client Secret da API Domínio.")
        if not self.office_integration_key.strip():
            raise DominioApiError("Informe a chave de integração fornecida pelo escritório.")


@dataclass(frozen=True)
class AccessToken:
    value: str
    expires_at: float

    def usable(self, now: float) -> bool:
        return bool(self.value) and self.expires_at > now + 60


class DominioOfficialApiClient:
    """Narrow, testable client for the documented Domínio invoice workflow."""

    def __init__(
        self,
        credentials: DominioApiCredentials,
        *,
        transport: HttpTransport | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        credentials.validate()
        self.credentials = credentials
        self._transport = transport or _urlopen_transport
        self._clock = clock
        self._token: AccessToken | None = None

    def access_token(self) -> str:
        if self._token and self._token.usable(self._clock()):
            return self._token.value
        basic = base64.b64encode(
            f"{self.credentials.client_id}:{self.credentials.client_secret}".encode()
        ).decode()
        response = self._request(
            "POST",
            AUTH_URL,
            {
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            urlencode({"grant_type": "client_credentials"}).encode(),
        )
        payload = _json_object(response.body, "token")
        token = str(payload.get("access_token") or "")
        expires_in = int(payload.get("expires_in") or 0)
        if not token or expires_in <= 60:
            raise DominioApiError("A API Domínio não retornou um token utilizável.")
        self._token = AccessToken(token, self._clock() + expires_in)
        return token

    def activation_info(self) -> dict[str, Any]:
        """Confirm that the office-provided key belongs to the expected company."""
        response = self._authorized_request(
            "GET", "/integration/v1/activation/info", self.credentials.office_integration_key
        )
        return _json_object(response.body, "ativação")

    def enable_integration(self) -> str:
        """Exchange the office key for the per-company integration key."""
        response = self._authorized_request(
            "POST",
            "/integration/v1/activation/enable",
            self.credentials.office_integration_key,
            b"{}",
        )
        key = str(_json_object(response.body, "ativação").get("integrationKey") or "")
        if not key:
            raise DominioApiError("A API Domínio não retornou a Integration Key.")
        return key

    def submit_invoice_xml(
        self,
        *,
        filename: str,
        xml: bytes,
        boxe_file: bool,
        integration_key: str | None = None,
        complement_filename: str | None = None,
        complement: bytes | None = None,
    ) -> dict[str, Any]:
        """Send one XML batch; callers persist the returned batch identifier for polling."""
        key = (integration_key or self.credentials.integration_key).strip()
        if not key:
            raise DominioApiError("Ative a empresa para obter a Integration Key antes do envio.")
        if not filename.lower().endswith(".xml") or not xml.strip():
            raise DominioApiError("Envie um XML fiscal não vazio.")
        body, content_type = _multipart(
            files=[("file[]", filename, xml, "application/xml")]
            + (
                [
                    (
                        "fileComplement[]",
                        complement_filename or "complement.xml",
                        complement,
                        "application/xml",
                    )
                ]
                if complement
                else []
            ),
            fields={"query": json.dumps({"boxeFile": bool(boxe_file)}, separators=(",", ":"))},
        )
        response = self._authorized_request(
            "POST", "/invoice/v3/batches", key, body, content_type=content_type
        )
        return _json_object(response.body, "envio de XML")

    def batch_status(self, batch_id: str, *, integration_key: str | None = None) -> dict[str, Any]:
        key = (integration_key or self.credentials.integration_key).strip()
        if not key or not batch_id.strip():
            raise DominioApiError("Informe Integration Key e identificador do lote.")
        response = self._authorized_request(
            "GET", f"/invoice/v3/batches/{quote(batch_id.strip(), safe='')}", key
        )
        return _json_object(response.body, "consulta do lote")

    def _authorized_request(
        self,
        method: str,
        path: str,
        integration_key: str,
        body: bytes | None = None,
        *,
        content_type: str | None = None,
    ) -> HttpResponse:
        headers = {
            "Authorization": f"Bearer {self.access_token()}",
            "x-integration-key": integration_key,
            "Accept": "application/json",
        }
        if content_type:
            headers["Content-Type"] = content_type
        elif body is not None:
            headers["Content-Type"] = "application/json"
        return self._request(method, API_BASE_URL + path, headers, body)

    def _request(
        self, method: str, url: str, headers: Mapping[str, str], body: bytes | None
    ) -> HttpResponse:
        response = self._transport(method, url, headers, body)
        if not 200 <= response.status < 300:
            raise DominioApiError(f"A API Domínio respondeu com HTTP {response.status}.")
        return response


@dataclass(frozen=True)
class OnvioOAuthCredentials:
    """Partner OAuth credentials registered with Thomson Reuters."""

    client_id: str
    client_secret: str
    redirect_uri: str

    def validate(self) -> None:
        if not self.client_id.strip() or not self.client_secret.strip():
            raise DominioApiError("Informe Client ID e Client Secret da Onvio API.")
        if not self.redirect_uri.startswith("https://"):
            raise DominioApiError("O callback da Onvio API deve usar HTTPS.")


class OnvioAccountingApiClient:
    """OAuth and read-only discovery endpoints from the published Onvio v2 spec."""

    def __init__(
        self, credentials: OnvioOAuthCredentials, *, transport: HttpTransport | None = None
    ) -> None:
        credentials.validate()
        self.credentials = credentials
        self._transport = transport or _urlopen_transport

    def authorization_url(self, state: str) -> str:
        if len(state) < 16:
            raise DominioApiError("O estado OAuth da Onvio é inválido.")
        return "https://auth.thomsonreuters.com/authorize?" + urlencode(
            {
                "client_id": self.credentials.client_id,
                "response_type": "code",
                "audience": ONVIO_AUDIENCE,
                "redirect_uri": self.credentials.redirect_uri,
                "scope": "openid profile email offline_access",
                "state": state,
            }
        )

    def exchange_code(self, code: str) -> dict[str, Any]:
        if not code.strip():
            raise DominioApiError("O código de autorização Onvio está ausente.")
        return self._token_request(
            {
                "grant_type": "authorization_code",
                "redirect_uri": self.credentials.redirect_uri,
                "code": code,
            }
        )

    def refresh_token(self, refresh_token: str) -> dict[str, Any]:
        if not refresh_token.strip():
            raise DominioApiError("O refresh token Onvio está ausente.")
        return self._token_request(
            {"grant_type": "refresh_token", "refresh_token": refresh_token}
        )

    def list_clients(self, access_token: str, *, page_index: int = 1) -> dict[str, Any]:
        if page_index < 1:
            raise DominioApiError("A página de clientes Onvio deve começar em 1.")
        return self._get_json(
            f"/integration/v2/client/info?pageIndex={page_index}",
            access_token,
            "clientes integráveis",
        )

    def integration_status(self, access_token: str) -> dict[str, Any]:
        return self._get_json("/status/v2/integration/info", access_token, "estado da integração")

    def _token_request(self, fields: Mapping[str, str]) -> dict[str, Any]:
        basic = base64.b64encode(
            f"{self.credentials.client_id}:{self.credentials.client_secret}".encode()
        ).decode()
        response = self._request(
            "POST",
            AUTH_URL,
            {
                "Authorization": f"Basic {basic}",
                "Content-Type": "application/x-www-form-urlencoded",
                "Accept": "application/json",
            },
            urlencode(fields).encode(),
        )
        payload = _json_object(response.body, "OAuth Onvio")
        if not str(payload.get("access_token") or ""):
            raise DominioApiError("A Onvio API não retornou access token.")
        return payload

    def _get_json(self, path: str, access_token: str, operation: str) -> dict[str, Any]:
        if not access_token.strip():
            raise DominioApiError("O access token Onvio está ausente.")
        response = self._request(
            "GET",
            API_BASE_URL + path,
            {"Authorization": f"Bearer {access_token}", "Accept": "application/json"},
            None,
        )
        return _json_object(response.body, operation)

    def _request(
        self, method: str, url: str, headers: Mapping[str, str], body: bytes | None
    ) -> HttpResponse:
        response = self._transport(method, url, headers, body)
        if not 200 <= response.status < 300:
            raise DominioApiError(f"A Onvio API respondeu com HTTP {response.status}.")
        return response


def _urlopen_transport(
    method: str, url: str, headers: Mapping[str, str], body: bytes | None
) -> HttpResponse:
    request = Request(url, data=body, headers=dict(headers), method=method)  # noqa: S310
    try:
        with urlopen(request, timeout=30) as response:  # noqa: S310 - fixed official URLs only
            return HttpResponse(response.status, response.read())
    except Exception as exc:  # pragma: no cover - exercised in integration environment
        raise DominioApiError("Não foi possível comunicar com a API Domínio.") from exc


def _json_object(body: bytes, operation: str) -> dict[str, Any]:
    try:
        value = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DominioApiError(
            f"A API Domínio retornou uma resposta inválida em {operation}."
        ) from exc
    if not isinstance(value, dict):
        raise DominioApiError(f"A API Domínio retornou um formato inválido em {operation}.")
    return value


def _multipart(
    *, files: list[tuple[str, str, bytes, str]], fields: Mapping[str, str]
) -> tuple[bytes, str]:
    boundary = "----cica-" + secrets.token_hex(16)
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                value.encode(),
                b"\r\n",
            ]
        )
    for field, filename, value, content_type in files:
        safe_filename = filename.replace('"', "").replace("\r", "").replace("\n", "")
        resolved_content_type = (
            content_type
            or mimetypes.guess_type(filename)[0]
            or "application/octet-stream"
        )
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                (
                    f'Content-Disposition: form-data; name="{field}"; '
                    f'filename="{safe_filename}"\r\n'
                ).encode(),
                f"Content-Type: {resolved_content_type}\r\n\r\n".encode(),
                value,
                b"\r\n",
            ]
        )
    chunks.append(f"--{boundary}--\r\n".encode())
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"
