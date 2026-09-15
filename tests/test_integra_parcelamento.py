import json
from datetime import date

import pytest

from apps.integra.parcelamento import ParcelamentoPayloadError, pedidos


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
