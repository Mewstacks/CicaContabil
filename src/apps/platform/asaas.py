"""Small, explicit Asaas API client used by the billing orchestration.

It deliberately has no settings-based credential lookup: production/sandbox
activation belongs to the final homologation stage.  Callers inject a key and a
transport, which makes the request contract testable without network access.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URLS = {
    "sandbox": "https://api-sandbox.asaas.com/v3",
    "production": "https://api.asaas.com/v3",
}
MAX_RESPONSE_BYTES = 1_000_000
TIMEOUT_SECONDS = 60


class AsaasConfigurationError(ValueError):
    """The caller did not provide a safe, complete local API configuration."""


class AsaasResponseError(ValueError):
    """Asaas returned an unusable or non-successful response."""

    def __init__(self, status: int, detail: str = "") -> None:
        self.status = status
        super().__init__(f"Asaas recusou a operação (HTTP {status}).{detail}")


class AsaasTransportError(ConnectionError):
    """The provider response is unavailable or incomplete; never retry blindly."""


class Transport(Protocol):
    def __call__(
        self,
        url: str,
        *,
        method: str,
        data: bytes | None,
        headers: dict[str, str],
    ) -> tuple[int, bytes]: ...


def _urlopen_transport(
    url: str,
    *,
    method: str,
    data: bytes | None,
    headers: dict[str, str],
) -> tuple[int, bytes]:
    request = Request(url, data=data, method=method)  # noqa: S310 - fixed Asaas origins
    for name, value in headers.items():
        request.add_header(name, value)
    try:
        with urlopen(request, timeout=TIMEOUT_SECONDS) as response:  # noqa: S310
            return int(response.status), response.read(MAX_RESPONSE_BYTES)
    except HTTPError as exc:
        return int(exc.code), exc.read(MAX_RESPONSE_BYTES)
    except (OSError, URLError) as exc:
        raise AsaasTransportError(
            "Asaas indisponível; consulte a operação antes de tentar novamente."
        ) from exc


@dataclass(frozen=True)
class Credentials:
    api_key: str
    environment: str

    @property
    def base_url(self) -> str:
        if not self.api_key.strip():
            raise AsaasConfigurationError("A chave Asaas deve ser fornecida explicitamente.")
        try:
            return BASE_URLS[self.environment]
        except KeyError as exc:
            raise AsaasConfigurationError(
                "O ambiente Asaas deve ser 'sandbox' ou 'production'."
            ) from exc


@dataclass(frozen=True)
class Customer:
    external_id: str
    name: str


@dataclass(frozen=True)
class Payment:
    external_id: str
    checkout_url: str
    status: str


def _text(value: object, *, field: str, limit: int) -> str:
    if not isinstance(value, str):
        raise AsaasConfigurationError(f"{field} deve ser texto.")
    normalized = value.strip()
    if not normalized or len(normalized) > limit:
        raise AsaasConfigurationError(f"{field} está ausente ou excede o limite permitido.")
    return normalized


def _response_payload(raw: bytes, *, status: int) -> dict[str, Any]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AsaasResponseError(status, " Resposta inválida.") from exc
    if not isinstance(payload, dict):
        raise AsaasResponseError(status, " Resposta inválida.")
    return payload


def _error_detail(payload: dict[str, Any]) -> str:
    errors = payload.get("errors")
    if not isinstance(errors, list) or not errors:
        return ""
    first = errors[0]
    if not isinstance(first, dict):
        return ""
    description = first.get("description")
    return f" {str(description)[:240]}" if description else ""


def _customer(payload: dict[str, Any]) -> Customer:
    return Customer(
        external_id=_text(payload.get("id"), field="id do cliente Asaas", limit=80),
        name=_text(payload.get("name"), field="nome do cliente Asaas", limit=255),
    )


def _payment(payload: dict[str, Any]) -> Payment:
    checkout_url = payload.get("invoiceUrl")
    if checkout_url is None:
        checkout_url = ""
    if not isinstance(checkout_url, str) or len(checkout_url) > 2_000:
        raise AsaasResponseError(200, " URL de cobrança inválida.")
    return Payment(
        external_id=_text(payload.get("id"), field="id da cobrança Asaas", limit=160),
        checkout_url=checkout_url,
        status=_text(payload.get("status"), field="status da cobrança Asaas", limit=80),
    )


class AsaasClient:
    """Asaas customers and one-off payments, with no automatic POST retry."""

    def __init__(self, credentials: Credentials, *, transport: Transport | None = None) -> None:
        self.credentials = credentials
        self._transport = transport or _urlopen_transport

    def _request(
        self, *, method: str, path: str, payload: dict[str, object] | None = None
    ) -> dict[str, Any]:
        if not path.startswith("/"):
            raise ValueError("O caminho Asaas deve começar com '/'.")
        data = json.dumps(payload, separators=(",", ":")).encode("utf-8") if payload else None
        status, raw = self._transport(
            f"{self.credentials.base_url}{path}",
            method=method,
            data=data,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json",
                "User-Agent": "CICA/1.0",
                "access_token": self.credentials.api_key,
            },
        )
        response = _response_payload(raw, status=status)
        if not 200 <= status < 300:
            raise AsaasResponseError(status, _error_detail(response))
        return response

    def find_customer_by_reference(self, external_reference: str) -> Customer | None:
        reference = _text(external_reference, field="referência externa", limit=255)
        response = self._request(
            method="GET",
            path=f"/customers?{urlencode({'externalReference': reference, 'limit': 1})}",
        )
        rows = response.get("data")
        if not isinstance(rows, list) or not rows:
            return None
        first = rows[0]
        if not isinstance(first, dict):
            raise AsaasResponseError(200, " Cliente retornado em formato inválido.")
        return _customer(first)

    def create_customer(
        self,
        *,
        name: str,
        cpf_cnpj: str,
        external_reference: str,
        email: str = "",
    ) -> Customer:
        request: dict[str, object] = {
            "name": _text(name, field="nome", limit=255),
            "cpfCnpj": _text(cpf_cnpj, field="CPF/CNPJ", limit=20),
            "externalReference": _text(
                external_reference, field="referência externa", limit=255
            ),
            "notificationDisabled": True,
        }
        if email.strip():
            request["email"] = _text(email, field="e-mail", limit=255)
        return _customer(self._request(method="POST", path="/customers", payload=request))

    def find_or_create_customer(
        self,
        *,
        name: str,
        cpf_cnpj: str,
        external_reference: str,
        email: str = "",
    ) -> Customer:
        """Avoid provider duplicates; a transport failure must be reconciled, not retried."""

        existing = self.find_customer_by_reference(external_reference)
        if existing is not None:
            return existing
        return self.create_customer(
            name=name,
            cpf_cnpj=cpf_cnpj,
            external_reference=external_reference,
            email=email,
        )

    def create_payment(
        self,
        *,
        customer_id: str,
        billing_type: str,
        amount_cents: int,
        due_on: date,
        description: str,
        external_reference: str,
    ) -> Payment:
        if billing_type not in {"PIX", "BOLETO", "CREDIT_CARD"}:
            raise AsaasConfigurationError("Forma de cobrança Asaas não permitida.")
        if amount_cents <= 0:
            raise AsaasConfigurationError("O valor da cobrança deve ser maior que zero.")
        request = {
            "customer": _text(customer_id, field="cliente Asaas", limit=80),
            "billingType": billing_type,
            "value": round(amount_cents / 100, 2),
            "dueDate": due_on.isoformat(),
            "description": _text(description, field="descrição", limit=500),
            "externalReference": _text(
                external_reference, field="referência externa", limit=255
            ),
        }
        return _payment(self._request(method="POST", path="/payments", payload=request))
