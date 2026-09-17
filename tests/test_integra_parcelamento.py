import base64
import json
from datetime import date
from decimal import Decimal

import pytest

from apps.integra.parcelamento import (
    ParcelamentoPayloadError,
    detalhe,
    parcelas_disponiveis,
    pdf_das,
    pedidos,
)


def test_official_escaped_parcelment_list_including_empty_is_readable() -> None:
    payload = {
        "status": 200,
        "dados": json.dumps(
            {"parcelamentos": [{
                "numero": 6, "dataDoPedido": 20230131,
                "situacao": "Encerrado a Pedido do Contribuinte",
                "dataDaSituacao": 20230209,
            }]}
        ),
    }

    result = pedidos(payload)

    assert result[0].numero == 6
    assert result[0].data_pedido == date(2023, 1, 31)
    assert result[0].data_situacao == date(2023, 2, 9)
    assert pedidos({"status": 200, "dados": '{"parcelamentos":[]}'}) == []


@pytest.mark.parametrize("payload", [
    {"status": 500, "dados": '{"parcelamentos":[]}'},
    {"status": 200, "dados": "{broken"},
    {"status": 200, "dados": '{"parcelamentos":{}}'},
    {"status": 200, "dados": '{"parcelamentos":[{"numero":true}]}'},
])
def test_invalid_provider_payload_is_not_presented_as_verified(payload: dict) -> None:
    with pytest.raises(ParcelamentoPayloadError):
        pedidos(payload)


def test_selected_agreement_detail_shows_consolidation_and_paid_months() -> None:
    payload = {"status": 200, "dados": json.dumps({"parcelamento": {
        "numero": 6, "situacao": "Ativo", "dataDoPedido": 20230131,
        "consolidacaoOriginal": {
            "valorTotalConsolidado": 1200.42,
            "quantidadeParcelas": 12,
            "parcelaBasica": 100.03,
        },
        "demonstrativoPagamentos": [{
            "mesDaParcela": 202304, "vencimentoDoDas": 20230430,
            "dataDeArrecadacao": 20230415, "valorPago": 100.03,
        }],
    }})}
    result = detalhe(payload, numero_esperado=6)
    assert result.resumo.numero == 6
    assert result.resumo.data_pedido == date(2023, 1, 31)
    assert result.valor_consolidado == Decimal("1200.42")
    assert result.quantidade_parcelas == 12
    assert result.pagamentos[0].mes_parcela == 202304
    assert result.pagamentos[0].valor_pago == Decimal("100.03")
    with pytest.raises(ParcelamentoPayloadError, match="outro parcelamento"):
        detalhe(payload, numero_esperado=7)


@pytest.mark.parametrize("key", ["listaParcela", "listaParcelas"])
def test_available_installments_accept_official_schema_and_example_keys(key: str) -> None:
    payload = {"status": 200, "dados": json.dumps({key: [
        {"parcela": 202304, "valor": 441.83},
        {"parcela": 202305, "valor": 441.83},
    ]})}
    result = parcelas_disponiveis(payload)
    assert [row.ano_mes for row in result] == [202304, 202305]
    assert result[0].valor == Decimal("441.83")


def test_das_decoder_accepts_pdf_and_rejects_arbitrary_bytes() -> None:
    valid = {"status": 200, "dados": json.dumps({
        "docArrecadacaoPdfB64": base64.b64encode(b"%PDF-1.7\n%%EOF").decode()
    })}
    assert pdf_das(valid).startswith(b"%PDF-")
    invalid = {"status": 200, "dados": json.dumps({
        "docArrecadacaoPdfB64": base64.b64encode(b"<html>fake</html>").decode()
    })}
    with pytest.raises(ParcelamentoPayloadError, match="PDF válido"):
        pdf_das(invalid)
    truncated = {"status": 200, "dados": json.dumps({
        "docArrecadacaoPdfB64": base64.b64encode(b"%PDF-1.7\ntruncated").decode()
    })}
    with pytest.raises(ParcelamentoPayloadError, match="PDF válido"):
        pdf_das(truncated)
