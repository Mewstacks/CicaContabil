"""PAGTOWEB 71 (pagamentos) and 73 (contagem): typed request and reader from the official pages.

Fixtures: tests/fixtures/integra/serpro/PAGTOWEB.*.json, copied from the official examples.
"""

from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from apps.integra.errors import IntegraPayloadError, IntegraRequestError
from apps.integra.typed.pagtoweb import (
    TYPED_SERVICES,
    ConsultarPagamentos,
    ContarPagamentos,
    IntervaloData,
    IntervaloValor,
    read_contagem,
    read_pagamentos,
)
from integra_fixtures import official_dados, official_payload, payload_with

BRT = timezone(timedelta(hours=-3))


def test_the_request_of_the_official_examples_is_built_field_by_field() -> None:
    by_document = ConsultarPagamentos(numeros_documento=("9999999999",))
    assert by_document.to_dados() == {
        "numeroDocumentoLista": ["9999999999"],
        "primeiroDaPagina": 0,
        "tamanhoDaPagina": 100,
    }
    by_year = ConsultarPagamentos(
        intervalo_data_arrecadacao=IntervaloData(
            inicial=date(2022, 1, 1), final=date(2022, 12, 31)
        ),
        tamanho_da_pagina=10,
    )
    assert by_year.to_dados() == {
        "intervaloDataArrecadacao": {"dataInicial": "2022-01-01", "dataFinal": "2022-12-31"},
        "primeiroDaPagina": 0,
        "tamanhoDaPagina": 10,
    }
    combined = ConsultarPagamentos(
        codigos_receita=("9999", "1162"),
        codigos_tipo_documento=("4", "9"),
        intervalo_valor_total=IntervaloValor(inicial=Decimal(600), final=Decimal(13000)),
        primeiro_da_pagina=100,
    )
    assert combined.to_dados() == {
        "codigoReceitaLista": ["9999", "1162"],
        "codigoTipoDocumentoLista": ["4", "9"],
        "intervaloValorTotalDocumento": {"valorInicial": 600, "valorFinal": 13000},
        "primeiroDaPagina": 100,
        "tamanhoDaPagina": 100,
    }


def test_the_count_takes_the_same_filters_without_paging() -> None:
    request = ContarPagamentos(
        intervalo_data_arrecadacao=IntervaloData(
            inicial=date(2019, 9, 1), final=date(2019, 11, 30)
        ),
        codigos_receita=("9999",),
    )

    assert request.to_dados() == {
        "intervaloDataArrecadacao": {"dataInicial": "2019-09-01", "dataFinal": "2019-11-30"},
        "codigoReceitaLista": ["9999"],
    }
    assert ContarPagamentos().to_dados() == {}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tamanho_da_pagina": 101},
        {"tamanho_da_pagina": 0},
        {"primeiro_da_pagina": -1},
        {"numeros_documento": ("1" * 18,)},
        {"numeros_documento": ("abc",)},
        {"codigos_receita": ("12345",)},
        {"codigos_tipo_documento": ("123",)},
    ],
)
def test_an_invalid_request_is_refused_before_any_call(kwargs: dict[str, object]) -> None:
    with pytest.raises(IntegraRequestError):
        ConsultarPagamentos(**kwargs)  # type: ignore[arg-type]


def test_inverted_intervals_are_refused() -> None:
    with pytest.raises(IntegraRequestError, match="intervalo"):
        IntervaloData(inicial=date(2022, 2, 1), final=date(2022, 1, 1))
    with pytest.raises(IntegraRequestError, match="intervalo"):
        IntervaloValor(inicial=Decimal(10), final=Decimal(5))


def test_a_darf_payment_is_read_with_its_receita_and_breakdown() -> None:
    documents = read_pagamentos(official_payload("PAGTOWEB.PAGAMENTOS71.darf"))

    assert len(documents) == 1
    darf = documents[0]
    assert darf.numero_documento == "9999999999"
    assert darf.tipo is not None
    assert (darf.tipo.codigo, darf.tipo.descricao_abreviada) == ("4", "DARF")
    assert darf.data_arrecadacao == datetime(2019, 9, 30, tzinfo=BRT)
    assert darf.data_vencimento == datetime(2019, 9, 30, tzinfo=BRT)
    assert darf.receita_principal is not None
    assert darf.receita_principal.codigo == "481"
    assert darf.receita_principal.extensao is None
    assert darf.referencia is None
    assert darf.valor_total == Decimal("369176.53")
    assert darf.valor_multa is None
    assert len(darf.desmembramentos) == 1
    assert darf.desmembramentos[0].sequencial == "1"
    assert darf.desmembramentos[0].valor_total is None


def test_das_mei_payments_carry_the_breakdown_by_receita_and_extension() -> None:
    documents = read_pagamentos(official_payload("PAGTOWEB.PAGAMENTOS71.das_mei"))

    assert [document.numero_documento for document in documents] == [
        "7082207696788000", "7082226956119000", "7082221013370000",
    ]
    first = documents[0]
    assert first.periodo_apuracao == datetime(2022, 3, 1, tzinfo=BRT)
    assert first.valor_total == Decimal("66.6")
    assert first.valor_saldo_total == Decimal(0)
    receitas = [item.receita_principal for item in first.desmembramentos]
    assert [receita.codigo for receita in receitas if receita] == ["151", "83", "125"]
    inss = first.desmembramentos[0]
    assert inss.receita_principal is not None and inss.receita_principal.extensao is not None
    assert inss.receita_principal.extensao.codigo == "1"
    assert inss.valor_principal == Decimal("60.6")
    assert inss.cib is None
    assert documents[1].valor_multa == Decimal(3)
    assert documents[1].valor_juros is None


def test_a_page_without_payments_is_empty() -> None:
    assert read_pagamentos(payload_with([])) == ()
    assert read_pagamentos({"status": 200, "mensagens": [], "dados": ""}) == ()


def test_the_count_of_paid_documents_is_an_integer() -> None:
    assert read_contagem(official_payload("PAGTOWEB.CONTACONSDOCARRPG73.contagem")) == 1
    assert read_contagem(payload_with("17")) == 17


@pytest.mark.parametrize(
    "payload", [payload_with(None), payload_with({"quantidade": 1}), payload_with("x")]
)
def test_a_count_that_is_not_an_integer_is_refused(payload: dict[str, object]) -> None:
    with pytest.raises(IntegraPayloadError):
        read_contagem(payload)


def test_a_failed_or_broken_answer_is_not_presented_as_payments() -> None:
    good = official_dados("PAGTOWEB.PAGAMENTOS71.darf")
    with pytest.raises(IntegraPayloadError, match="status 500"):
        read_pagamentos(payload_with(good, status=500))
    with pytest.raises(IntegraPayloadError, match="uma lista"):
        read_pagamentos(payload_with(good[0]))
    missing = copy.deepcopy(good)
    del missing[0]["numeroDocumento"]
    with pytest.raises(IntegraPayloadError, match=r"dados\[0\]\.numeroDocumento"):
        read_pagamentos(payload_with(missing))
    bad_date = copy.deepcopy(good)
    bad_date[0]["dataArrecadacao"] = "ontem"
    with pytest.raises(IntegraPayloadError, match=r"dados\[0\]\.dataArrecadacao"):
        read_pagamentos(payload_with(bad_date))
    bad_value = copy.deepcopy(good)
    bad_value[0]["valorTotal"] = "caro"
    with pytest.raises(IntegraPayloadError, match=r"dados\[0\]\.valorTotal"):
        read_pagamentos(payload_with(bad_value))


def test_the_module_registers_its_two_services() -> None:
    assert {typed.key: typed.request for typed in TYPED_SERVICES} == {
        "pagtoweb.pagamentos": ConsultarPagamentos,
        "pagtoweb.contagem": ContarPagamentos,
    }
    assert {typed.key: typed.read for typed in TYPED_SERVICES} == {
        "pagtoweb.pagamentos": read_pagamentos,
        "pagtoweb.contagem": read_contagem,
    }
