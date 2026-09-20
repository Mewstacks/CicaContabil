from __future__ import annotations

import json
from datetime import date

import pytest

from apps.platform.asaas import (
    AsaasClient,
    AsaasConfigurationError,
    AsaasResponseError,
    Credentials,
)


class RecordedTransport:
    def __init__(self, responses: list[tuple[int, bytes]]) -> None:
        self.responses = responses
        self.calls: list[dict[str, object]] = []

    def __call__(
        self,
        url: str,
        *,
        method: str,
        data: bytes | None,
        headers: dict[str, str],
    ) -> tuple[int, bytes]:
        self.calls.append({"url": url, "method": method, "data": data, "headers": headers})
        return self.responses.pop(0)


def _client(transport: RecordedTransport, environment: str = "sandbox") -> AsaasClient:
    credentials = Credentials(api_key="$aact_hmlg_test", environment=environment)
    return AsaasClient(credentials, transport=transport)


def test_client_uses_the_sandbox_contract_and_reuses_existing_customer() -> None:
    transport = RecordedTransport(
        [(200, b'{"data":[{"id":"cus_existing","name":"Escritorio CICA"}]}')]
    )

    customer = _client(transport).find_or_create_customer(
        name="Escritório CICA",
        cpf_cnpj="12345678000199",
        external_reference="organization:123",
        email="financeiro@example.test",
    )

    assert customer.external_id == "cus_existing"
    assert len(transport.calls) == 1
    call = transport.calls[0]
    assert call["method"] == "GET"
    assert call["data"] is None
    assert call["url"] == (
        "https://api-sandbox.asaas.com/v3/customers?externalReference=organization%3A123&limit=1"
    )
    assert call["headers"] == {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "CICA/1.0",
        "access_token": "$aact_hmlg_test",
    }


def test_client_creates_customer_only_after_an_empty_lookup() -> None:
    transport = RecordedTransport(
        [
            (200, b'{"data":[]}'),
            (200, '{"id":"cus_new","name":"Escritório CICA"}'.encode()),
        ]
    )

    customer = _client(transport).find_or_create_customer(
        name="Escritório CICA",
        cpf_cnpj="12345678000199",
        external_reference="organization:123",
        email="financeiro@example.test",
    )

    assert customer.external_id == "cus_new"
    assert [call["method"] for call in transport.calls] == ["GET", "POST"]
    payload = json.loads(transport.calls[1]["data"] or b"{}")
    assert payload == {
        "name": "Escritório CICA",
        "cpfCnpj": "12345678000199",
        "externalReference": "organization:123",
        "notificationDisabled": True,
        "email": "financeiro@example.test",
    }


def test_payment_is_a_one_off_charge_without_card_data_or_automatic_retry() -> None:
    transport = RecordedTransport(
        [
            (
                200,
                b'{"id":"pay_123","status":"PENDING","invoiceUrl":"https://sandbox.asaas.test/i/1"}',
            )
        ]
    )

    payment = _client(transport, environment="production").create_payment(
        customer_id="cus_123",
        billing_type="PIX",
        amount_cents=19_990,
        due_on=date(2026, 10, 10),
        description="Mensalidade CICA",
        external_reference="invoice:123",
    )

    assert payment.external_id == "pay_123"
    assert payment.checkout_url == "https://sandbox.asaas.test/i/1"
    assert transport.calls[0]["url"] == "https://api.asaas.com/v3/payments"
    assert json.loads(transport.calls[0]["data"] or b"{}") == {
        "customer": "cus_123",
        "billingType": "PIX",
        "value": 199.9,
        "dueDate": "2026-10-10",
        "description": "Mensalidade CICA",
        "externalReference": "invoice:123",
    }


def test_client_refuses_unsafe_inputs_and_surfaces_provider_error_without_retry() -> None:
    transport = RecordedTransport(
        [(400, b'{"errors":[{"description":"Documento invalido"}]}')]
    )
    client = _client(transport)

    with pytest.raises(AsaasConfigurationError):
        client.create_payment(
            customer_id="cus_123",
            billing_type="CARD",
            amount_cents=100,
            due_on=date(2026, 10, 10),
            description="Teste",
            external_reference="invoice:123",
        )
    with pytest.raises(AsaasResponseError, match="Documento invalido"):
        client.create_customer(
            name="Escritório CICA",
            cpf_cnpj="12345678000199",
            external_reference="organization:123",
        )
    assert len(transport.calls) == 1


def test_credentials_require_explicit_key_and_known_environment() -> None:
    with pytest.raises(AsaasConfigurationError, match="chave Asaas"):
        _ = Credentials(api_key="", environment="sandbox").base_url
    with pytest.raises(AsaasConfigurationError, match="ambiente Asaas"):
        _ = Credentials(api_key="test", environment="other").base_url
