"""Parcelamento: the 4 consultations of the 8 modalities come from one table (T10.2).

The official pages of the 8 modalities have the same fields for the list of requests, the
available installments and the payment detail (checked table by table); only the consolidation
block of the agreement detail differs by modality. So one reader serves all modalities and the
registry is generated from the modality table. Fixtures: official examples that are valid JSON
(the others lost characters in the page and cannot be recovered).
"""

from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from apps.integra.catalog import SERVICES
from apps.integra.catalog_table import MODALIDADES
from apps.integra.errors import IntegraRequestError
from apps.integra.parcelamento import (
    TYPED_SERVICES,
    ConsultarPagamentoParcela,
    ConsultarParcelamento,
    ParcelamentoPayloadError,
    detalhe,
    pagamento_parcela,
    parcelas_disponiveis,
    pedidos,
)
from integra_fixtures import official_dados, official_payload, payload_with

BRT = timezone(timedelta(hours=-3))
OPERATIONS = ("pedidos", "detalhe", "pagamento", "parcelas")


def test_the_registry_has_the_4_consultations_of_each_of_the_8_modalities() -> None:
    expected = {
        f"parcelamento.{modalidade.slug}.{operation}"
        for modalidade in MODALIDADES
        for operation in OPERATIONS
    }

    assert len(expected) == 32
    assert {typed.key for typed in TYPED_SERVICES} == expected
    for typed in TYPED_SERVICES:
        assert typed.key in SERVICES
        assert SERVICES[typed.key].copilot_allowed, typed.key


def test_each_operation_has_the_same_request_and_reader_in_every_modality() -> None:
    by_operation: dict[str, set[tuple[object, object]]] = {}
    for typed in TYPED_SERVICES:
        by_operation.setdefault(typed.key.rsplit(".", 1)[1], set()).add((typed.request, typed.read))

    assert {operation: len(shapes) for operation, shapes in by_operation.items()} == {
        "pedidos": 1, "detalhe": 1, "pagamento": 1, "parcelas": 1,
    }
    assert by_operation["detalhe"] == {(ConsultarParcelamento, detalhe)}
    assert by_operation["pagamento"] == {(ConsultarPagamentoParcela, pagamento_parcela)}
    assert by_operation["pedidos"] == {(None, pedidos)}
    assert by_operation["parcelas"] == {(None, parcelas_disponiveis)}


def test_the_requests_match_the_official_inputs() -> None:
    assert ConsultarParcelamento(numero_parcelamento=1).to_dados() == {"numeroParcelamento": 1}
    assert ConsultarPagamentoParcela(
        numero_parcelamento=1, ano_mes_parcela=201612
    ).to_dados() == {"numeroParcelamento": 1, "anoMesParcela": 201612}
    for bad in (0, -1):
        with pytest.raises(IntegraRequestError):
            ConsultarParcelamento(numero_parcelamento=bad)
    with pytest.raises(IntegraRequestError):
        ConsultarPagamentoParcela(numero_parcelamento=1, ano_mes_parcela=201613)


def test_the_list_of_requests_reads_for_the_ordinary_and_the_special_modality() -> None:
    ordinary = pedidos(official_payload("PARCSN.PEDIDOSPARC163.ordinario"))
    special = pedidos(official_payload("PARCSN-ESP.PEDIDOSPARC173.especial"))

    assert ordinary[0].numero == 1
    assert ordinary[0].data_pedido == date(2016, 2, 11)
    assert ordinary[0].situacao == "Encerrado a Pedido do Contribuinte"
    assert [(item.numero, item.situacao) for item in special] == [(9001, "Em parcelamento")]
    assert special[0].data_situacao == date(2016, 12, 27)


def test_the_available_installments_read_for_pertmei() -> None:
    result = parcelas_disponiveis(official_payload("PERTMEI.PARCELASPARAGERAR222.parcelas"))

    assert [(item.ano_mes, item.valor) for item in result] == [(202306, Decimal("68.13"))]


@pytest.mark.parametrize(
    ("fixture", "numero", "pedido", "pagos", "consolidado"),
    [
        ("PARCMEI-ESP.OBTERPARC214.parcelamento", 9001, date(2017, 10, 2), 5, Decimal("3524.16")),
        ("RELPMEI.OBTERPARC234.parcelamento", 9131, date(2022, 5, 19), 5, None),
    ],
)
def test_the_agreement_detail_reads_the_flat_official_answer_of_every_modality(
    fixture: str, numero: int, pedido: date, pagos: int, consolidado: Decimal | None
) -> None:
    result = detalhe(official_payload(fixture), numero_esperado=numero)

    assert result.resumo.numero == numero
    assert result.resumo.data_pedido == pedido
    assert result.resumo.situacao == "Em parcelamento"
    assert len(result.pagamentos) == pagos
    assert result.pagamentos[0].valor_pago is not None
    # The consolidation block differs by modality (RELPMEI names its values "de entrada").
    assert result.valor_consolidado == consolidado
    assert detalhe(official_payload(fixture)).resumo.numero == numero


def test_the_agreement_detail_still_refuses_another_agreement() -> None:
    with pytest.raises(ParcelamentoPayloadError, match="outro parcelamento"):
        detalhe(official_payload("RELPMEI.OBTERPARC234.parcelamento"), numero_esperado=1)


def test_the_wrapped_shape_of_the_first_reader_keeps_working() -> None:
    flat = official_dados("PARCMEI-ESP.OBTERPARC214.parcelamento")
    wrapped = payload_with({"parcelamento": flat})

    assert detalhe(wrapped, numero_esperado=9001).resumo.numero == 9001


def test_an_answer_without_the_agreement_is_refused() -> None:
    with pytest.raises(ParcelamentoPayloadError):
        detalhe(payload_with({"outra": 1}))
    with pytest.raises(ParcelamentoPayloadError):
        detalhe(payload_with([1]))


@pytest.mark.parametrize(
    ("fixture", "das", "vencimento", "parcela", "valor", "debitos", "entes"),
    [
        (
            "PARCSN-ESP.DETPAGTOPARC175.pagamento", "00000000000000000", date(2016, 12, 29),
            "11", Decimal("334.84"), 1, {"União"},
        ),
        (
            "PERTMEI.DETPAGTOPARC225.pagamento", "07181922816516181", date(2019, 7, 31),
            "13", Decimal("54.64"), 2, {"União", "SAO PAULO"},
        ),
    ],
)
def test_the_payment_detail_of_an_installment_is_read(
    fixture: str,
    das: str,
    vencimento: date,
    parcela: str,
    valor: Decimal,
    debitos: int,
    entes: set[str],
) -> None:
    result = pagamento_parcela(official_payload(fixture))

    assert result.numero_das == das
    assert result.data_vencimento == vencimento
    assert result.numero_parcela == parcela
    assert result.valor_pago_arrecadacao == valor
    assert len(result.pagamento_debitos) == debitos
    assert {
        item.ente_federado_destino
        for debito in result.pagamento_debitos
        for item in debito.discriminacoes
    } == entes


def test_the_payment_detail_carries_the_breakdown_by_tributo() -> None:
    result = pagamento_parcela(official_payload("PARCSN-ESP.DETPAGTOPARC175.pagamento"))

    assert result.pa_das_gerado == 201612
    assert result.gerado_em == datetime(2016, 12, 13, 12, 58, 56, tzinfo=BRT)
    assert result.data_limite_acolhimento == date(2016, 12, 29)
    assert result.data_pagamento == date(2016, 12, 28)
    assert result.banco_agencia == "0/49"
    debito = result.pagamento_debitos[0]
    assert debito.pa_debito == 201512
    assert debito.processo is None
    assert [item.tributo for item in debito.discriminacoes] == [
        "IRPJ", "CSLL", "COFINS", "PIS", "INSS",
    ]
    irpj = debito.discriminacoes[0]
    assert (irpj.principal, irpj.multa, irpj.juros, irpj.total) == (
        Decimal("17.68"), Decimal("3.54"), Decimal("2.12"), Decimal("23.34"),
    )


def test_a_broken_payment_detail_is_not_presented_as_verified() -> None:
    good = official_dados("PERTSN.DETPAGTOPARC185.pagamento")
    with pytest.raises(ParcelamentoPayloadError, match="status 500"):
        pagamento_parcela(payload_with(good, status=500))
    missing = copy.deepcopy(good)
    del missing["numeroDas"]
    with pytest.raises(ParcelamentoPayloadError, match="numeroDas"):
        pagamento_parcela(payload_with(missing))
    bad = copy.deepcopy(good)
    bad["pagamentoDebitos"][0]["discriminacoesDebito"][0]["total"] = "muito"
    with pytest.raises(ParcelamentoPayloadError, match="total"):
        pagamento_parcela(payload_with(bad))
    with pytest.raises(ParcelamentoPayloadError):
        pagamento_parcela(payload_with([good]))
