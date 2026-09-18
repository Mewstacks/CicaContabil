from __future__ import annotations

from dataclasses import dataclass, field

import pytest

from apps.hub.dominio_api import (
    API_BASE_URL,
    AUTH_URL,
    DominioApiCredentials,
    DominioApiError,
    DominioOfficialApiClient,
    HttpResponse,
    OnvioAccountingApiClient,
    OnvioOAuthCredentials,
)


@dataclass
class FakeTransport:
    calls: list[tuple[str, str, dict[str, str], bytes | None]] = field(default_factory=list)

    def __call__(
        self, method: str, url: str, headers: dict[str, str], body: bytes | None
    ) -> HttpResponse:
        self.calls.append((method, url, dict(headers), body))
        if url == AUTH_URL:
            return HttpResponse(200, b'{"access_token":"token","expires_in":3600}')
        if url.endswith("/activation/info"):
            return HttpResponse(200, b'{"companyName":"Cliente"}')
        if url.endswith("/activation/enable"):
            return HttpResponse(200, b'{"integrationKey":"company-key"}')
        if url.endswith("/batches"):
            return HttpResponse(202, b'{"id":"batch-1"}')
        return HttpResponse(200, b'{"status":"processed"}')


def client(
    transport: FakeTransport | None = None,
) -> tuple[DominioOfficialApiClient, FakeTransport]:
    fake = transport or FakeTransport()
    return (
        DominioOfficialApiClient(
            DominioApiCredentials("client", "secret", "office-key"),
            transport=fake,
            clock=lambda: 1000,
        ),
        fake,
    )


def test_official_workflow_uses_documented_auth_activation_and_batch_contract() -> None:
    api, fake = client()
    assert api.activation_info()["companyName"] == "Cliente"
    assert api.enable_integration() == "company-key"
    result = api.submit_invoice_xml(
        filename="nota.xml",
        xml=b"<nfe/>",
        boxe_file=False,
        integration_key="company-key",
    )
    assert result["id"] == "batch-1"
    assert api.batch_status("batch-1", integration_key="company-key")["status"] == "processed"
    assert [call[1] for call in fake.calls] == [
        AUTH_URL,
        API_BASE_URL + "/integration/v1/activation/info",
        API_BASE_URL + "/integration/v1/activation/enable",
        API_BASE_URL + "/invoice/v3/batches",
        API_BASE_URL + "/invoice/v3/batches/batch-1",
    ]
    upload = fake.calls[3]
    assert upload[2]["x-integration-key"] == "company-key"
    assert b'"boxeFile":false' in upload[3]
    assert b"<nfe/>" in upload[3]


def test_token_is_cached_until_near_expiry() -> None:
    api, fake = client()
    api.activation_info()
    api.batch_status("batch-1", integration_key="company-key")
    assert sum(call[1] == AUTH_URL for call in fake.calls) == 1


def test_missing_key_and_bad_api_status_are_safe() -> None:
    api, _ = client()
    with pytest.raises(DominioApiError, match="Integration Key"):
        api.submit_invoice_xml(filename="nota.xml", xml=b"<nfe/>", boxe_file=False)
    def denied(*_: object) -> HttpResponse:
        return HttpResponse(401, b"no secret")

    with pytest.raises(DominioApiError, match="HTTP 401"):
        DominioOfficialApiClient(
            DominioApiCredentials("client", "secret", "office-key"), transport=denied
        ).access_token()


def test_onvio_oauth_and_documented_read_only_discovery_endpoints() -> None:
    fake = FakeTransport()
    api = OnvioAccountingApiClient(
        OnvioOAuthCredentials("client", "secret", "https://cica.example/callback"), transport=fake
    )
    url = api.authorization_url("a" * 24)
    assert "response_type=code" in url
    assert "offline_access" in url
    token = api.exchange_code("code")
    assert token["access_token"] == "token"
    clients = api.list_clients("token", page_index=2)
    status = api.integration_status("token")
    assert clients["status"] == "processed"
    assert status["status"] == "processed"
    assert fake.calls[1][1] == API_BASE_URL + "/integration/v2/client/info?pageIndex=2"
    assert fake.calls[2][1] == API_BASE_URL + "/status/v2/integration/info"
