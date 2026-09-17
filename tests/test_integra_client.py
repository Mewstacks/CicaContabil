from __future__ import annotations

import json
import ssl
from pathlib import Path
from typing import Any

import pytest
from django.core.cache import cache

from apps.integra.catalog import SERVICES, Verb, service
from apps.integra.client import Credentials, IntegraClient
from apps.integra.envelope import Party
from apps.integra.errors import (
    IntegraAuthenticationError,
    IntegraNotAuthorized,
    IntegraServiceError,
    IntegraTransportError,
)

CREDENTIALS = Credentials(
    consumer_key="consumer-key",
    consumer_secret="consumer-secret",
    certificate_path=Path("unused-in-tests.pfx"),
    certificate_password="",
    contratante="11.111.111/1111-11",
    autor_pedido="11.111.111/1111-11",
    environment="trial",
)
TOKEN_RESPONSE = {
    "access_token": "access-token-value",
    "jwt_token": "jwt-token-value",
    "expires_in": 2008,
}


class RecordingTransport:
    """Stands in for the network the way connection_factory stands in for ODBC."""

    def __init__(self, *responses: tuple[int, dict[str, Any]]) -> None:
        self.queue = list(responses)
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self,
        url: str,
        *,
        data: bytes,
        headers: dict[str, str],
        context: ssl.SSLContext | None,
    ) -> tuple[int, bytes]:
        self.calls.append({"url": url, "data": data, "headers": headers})
        status, payload = self.queue.pop(0) if self.queue else (200, {})
        return status, json.dumps(payload).encode()


@pytest.fixture(autouse=True)
def _clear_token_cache() -> None:
    cache.clear()


def _client(*responses: tuple[int, dict[str, Any]]) -> tuple[IntegraClient, RecordingTransport]:
    transport = RecordingTransport((200, TOKEN_RESPONSE), *responses)
    return IntegraClient(CREDENTIALS, transport=transport), transport


def test_authentication_sends_the_basic_pair_and_the_terceiros_role() -> None:
    client, transport = _client()

    token = client.authenticate()

    call = transport.calls[0]
    assert call["url"] == "https://autenticacao.sapi.serpro.gov.br/authenticate"
    assert call["headers"]["Role-Type"] == "TERCEIROS"
    assert call["headers"]["Authorization"].startswith("Basic ")
    assert token.access_token == "access-token-value"


def test_the_token_is_reused_until_it_is_close_to_expiring() -> None:
    client, transport = _client((200, {}), (200, {}))

    client.call("dte.situacao", contribuinte="99999999999999")
    client.call("dte.situacao", contribuinte="99999999999999")

    authentications = [
        call for call in transport.calls if call["url"].startswith("https://autenticacao")
    ]
    assert len(authentications) == 1


def test_a_call_reaches_the_trial_gateway_with_the_documented_envelope() -> None:
    client, transport = _client((200, {"status": 200}))

    client.call("dte.situacao", contribuinte="99.999.999/9999-99")

    call = transport.calls[-1]
    assert call["url"] == (
        "https://gateway.apiserpro.serpro.gov.br/integra-contador-trial/v1/Consultar"
    )
    assert call["headers"]["Authorization"] == "Bearer access-token-value"
    assert call["headers"]["jwt_token"] == "jwt-token-value"

    envelope = json.loads(call["data"])
    assert envelope["contratante"] == {"numero": "11111111111111", "tipo": 2}
    assert envelope["contribuinte"] == {"numero": "99999999999999", "tipo": 2}
    assert envelope["autorPedidoDados"] == {"numero": "11111111111111", "tipo": 2}
    assert envelope["pedidoDados"] == {
        "idSistema": "DTE",
        "idServico": "CONSULTASITUACAODTE111",
        "versaoSistema": "1.0",
        "dados": "",
    }


def test_a_call_can_use_the_office_as_author_without_changing_contractor() -> None:
    client, transport = _client((200, {"status": 200}))

    client.call(
        "dte.situacao",
        contribuinte="99.999.999/9999-99",
        autor_pedido="22.222.222/2222-22",
    )

    envelope = json.loads(transport.calls[-1]["data"])
    assert envelope["contratante"] == {"numero": "11111111111111", "tipo": 2}
    assert envelope["autorPedidoDados"] == {"numero": "22222222222222", "tipo": 2}
    assert envelope["contribuinte"] == {"numero": "99999999999999", "tipo": 2}


def test_dados_travels_as_a_json_string_not_a_nested_object() -> None:
    client, transport = _client((200, {}))

    client.call(
        "caixapostal.mensagens",
        contribuinte="99999999999999",
        dados={"cnpjMatriz": "99999999999999"},
    )

    envelope = json.loads(transport.calls[-1]["data"])
    assert envelope["pedidoDados"]["dados"] == '{"cnpjMatriz":"99999999999999"}'


def test_an_unknown_service_never_reaches_the_network() -> None:
    client, transport = _client()

    with pytest.raises(ValueError, match="não está no catálogo"):
        client.call("dctfweb.qualquer-coisa", contribuinte="99999999999999")

    assert transport.calls == []


def test_a_missing_power_of_attorney_is_its_own_error() -> None:
    client, _ = _client((403, {"mensagem": "Procuração não encontrada."}))

    with pytest.raises(IntegraNotAuthorized, match="procuração"):
        client.call("dte.situacao", contribuinte="99999999999999")


def test_a_refusal_carries_the_service_message() -> None:
    client, _ = _client((422, {"mensagens": [{"texto": "Competência inválida."}]}))

    with pytest.raises(IntegraServiceError) as raised:
        client.call("dctfweb.guia", contribuinte="99999999999999")

    assert "Competência inválida." in str(raised.value)
    assert raised.value.status == 422


def test_rejected_credentials_surface_as_an_authentication_error() -> None:
    transport = RecordingTransport((401, {"error": "invalid_client"}))
    client = IntegraClient(CREDENTIALS, transport=transport)

    with pytest.raises(IntegraAuthenticationError):
        client.authenticate()


def test_an_unreadable_answer_is_a_transport_error() -> None:
    class BrokenTransport(RecordingTransport):
        def __call__(self, url: str, **kwargs: Any) -> tuple[int, bytes]:
            return 200, b"<html>gateway</html>"

    client = IntegraClient(CREDENTIALS, transport=BrokenTransport())

    with pytest.raises(IntegraTransportError):
        client.authenticate()


def test_production_and_trial_are_the_only_environments() -> None:
    assert CREDENTIALS.base_url.endswith("/integra-contador-trial/v1")

    production = Credentials(**{**CREDENTIALS.__dict__, "environment": "production"})
    assert production.base_url.endswith("/integra-contador/v1")


def test_every_catalogued_service_declares_a_real_verb() -> None:
    for key, spec in SERVICES.items():
        assert spec.key == key
        assert spec.verb in set(Verb)
        assert spec.id_sistema.isupper()
        assert spec.id_servico.isupper()


def test_initial_central_services_match_official_serpro_identifiers() -> None:
    assert service("parcelamento.parcsn.pedidos").id_servico == "PEDIDOSPARC163"
    assert service("parcelamento.parcsn.detalhe").id_servico == "OBTERPARC164"
    assert service("parcelamento.parcsn.pagamento").id_servico == "DETPAGTOPARC165"
    assert service("parcelamento.parcsn.parcelas").id_servico == "PARCELASPARAGERAR162"
    assert service("parcelamento.parcsn.das").id_servico == "GERARDAS161"
    assert service("dctfweb.recibo").id_servico == "CONSRECIBO32"
    assert service("dctfweb.declaracao_completa").id_servico == "CONSDECCOMPLETA33"


def test_a_party_number_decides_its_own_type() -> None:
    assert Party("11.111.111/1111-11").tipo == 2
    assert Party("123.456.789-09").tipo == 1
    assert Party("00.000.000/E08G-12").as_payload() == {
        "numero": "00000000E08G12",
        "tipo": 2,
    }
    with pytest.raises(ValueError, match="não é um CPF nem um CNPJ"):
        assert Party("123").tipo


def test_the_cheap_mailbox_poll_is_marked_as_not_billable() -> None:
    """INNOVAMSG63 is the one that may run on a schedule; the rest cost money per call."""

    assert service("caixapostal.indicador").billable is False
    assert service("caixapostal.mensagens").billable is True
