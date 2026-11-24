"""SICALC 52 (receitas) and 54 (consolidar): typed request and reader from the official pages.

Fixtures: tests/fixtures/integra/serpro/SICALC.*.json, from the official examples.
"""

from __future__ import annotations

import copy
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any

import pytest

from apps.integra.errors import IntegraPayloadError, IntegraRequestError
from apps.integra.typed.sicalc import (
    TYPED_SERVICES,
    ConsolidarDarf,
    ConsultarReceita,
    read_consolidado,
    read_receita,
)
from integra_fixtures import official_dados, official_payload, payload_with

BRT = timezone(timedelta(hours=-3))


def _escaped(text: str) -> dict[str, Any]:
    """The `dados` of an official input example (an escaped JSON string) as an object."""

    decoded: dict[str, Any] = json.loads(text)
    return decoded


def _darf(**changes: Any) -> ConsolidarDarf:
    base: dict[str, Any] = {
        "codigo_receita": "1162",
        "codigo_receita_extensao": "01",
        "data_pa": "01/2022",
        "valor_imposto": Decimal("1000.00"),
        "data_consolidacao": datetime(2022, 8, 8),
    }
    return ConsolidarDarf(**{**base, **changes})


def test_the_receita_request_is_the_code_of_the_official_example() -> None:
    assert ConsultarReceita(codigo_receita="6106").to_dados() == {"codigoReceita": "6106"}


@pytest.mark.parametrize("codigo", ["", "12345", "abc", "61 6"])
def test_a_receita_code_out_of_the_pattern_is_refused(codigo: str) -> None:
    with pytest.raises(IntegraRequestError):
        ConsultarReceita(codigo_receita=codigo)


def test_the_darf_request_of_the_individual_example_matches_the_official_dados() -> None:
    request = ConsolidarDarf(
        uf="SP",
        municipio="7107",
        codigo_receita="0190",
        codigo_receita_extensao="01",
        tipo_pa="ME",
        data_pa="12/2017",
        vencimento=datetime(2018, 1, 31),
        valor_imposto=Decimal("1000.00"),
        data_consolidacao=datetime(2022, 8, 8),
        observacao="Darf calculado",
    )
    assert request.to_dados() == _escaped(
        '{"uf": "SP", "municipio": "7107", "codigoReceita": "0190", "codigoReceitaExtensao": "01",'
        ' "tipoPA": "ME", "dataPA": "12/2017", "vencimento": "2018-01-31T00:00:00",'
        ' "valorImposto": "1000.00", "dataConsolidacao": "2022-08-08T00:00:00",'
        ' "observacao": "Darf calculado"}'
    )


def test_the_darf_request_with_a_quota_matches_the_official_dados() -> None:
    request = ConsolidarDarf(
        uf="SP",
        municipio="7107",
        codigo_receita="0220",
        codigo_receita_extensao="01",
        tipo_pa="TR",
        data_pa="04/2021",
        cota=1,
        valor_imposto=Decimal("1000.00"),
        data_consolidacao=datetime(2022, 8, 8),
        observacao="Darf calculado",
    )
    assert request.to_dados() == _escaped(
        '{"uf": "SP", "municipio": "7107", "codigoReceita": "0220", "codigoReceitaExtensao": "01",'
        ' "tipoPA": "TR", "dataPA": "04/2021", "cota": "1", "valorImposto": "1000.00",'
        ' "dataConsolidacao": "2022-08-08T00:00:00", "observacao": "Darf calculado"}'
    )


def test_the_darf_request_with_an_alphanumeric_cnpj_matches_the_official_dados() -> None:
    request = ConsolidarDarf(
        uf="SP",
        municipio="7107",
        codigo_receita="1162",
        codigo_receita_extensao="1",
        data_pa="01/2021",
        valor_imposto=Decimal("1000.00"),
        cnpj_prestador="QZRC7JM7205500",
        data_consolidacao=datetime(2026, 6, 22),
    )
    assert request.to_dados() == _escaped(
        '{"uf": "SP", "municipio": "7107", "codigoReceita": "1162", "codigoReceitaExtensao": "1",'
        ' "dataPA": "01/2021", "valorImposto": "1000.00", "cnpjPrestador": "QZRC7JM7205500",'
        ' "dataConsolidacao": "2026-06-22T00:00:00"}'
    )


def test_a_manual_darf_with_all_the_optional_fields_is_built() -> None:
    request = _darf(
        valor_multa=Decimal("150.5"),
        valor_juros=Decimal("100"),
        ganho_capital=True,
        data_alienacao=datetime(2022, 1, 10),
        numero_referencia="1234567/ABCDEFGH",
        cno="123456789012",
    )
    assert request.to_dados() == {
        "codigoReceita": "1162",
        "codigoReceitaExtensao": "01",
        "numeroReferencia": "1234567/ABCDEFGH",
        "dataPA": "01/2022",
        "valorImposto": "1000.00",
        "valorMulta": "150.50",
        "valorJuros": "100.00",
        "ganhoCapital": True,
        "dataAlienacao": "2022-01-10T00:00:00",
        "dataConsolidacao": "2022-08-08T00:00:00",
        "cno": "123456789012",
    }


def test_a_quota_and_a_due_date_are_mutually_exclusive() -> None:
    with pytest.raises(IntegraRequestError, match="cota"):
        _darf(cota=1, vencimento=datetime(2022, 2, 18))


def test_the_required_fields_have_no_default() -> None:
    partial: dict[str, Any] = {"codigo_receita": "1162"}
    with pytest.raises(TypeError):
        ConsolidarDarf(**partial)
    with pytest.raises(TypeError):
        ConsultarReceita(**{})


@pytest.mark.parametrize(
    "changes",
    [
        {"uf": "sp"},
        {"uf": "SPP"},
        {"municipio": "71070"},
        {"municipio": "abcd"},
        {"codigo_receita": "12345"},
        {"codigo_receita_extensao": "123"},
        {"tipo_pa": "XX"},
        {"data_pa": "2022-01"},
        {"data_pa": "1/2022"},
        {"tipo_pa": "ME", "data_pa": "2022"},
        {"tipo_pa": "AN", "data_pa": "01/2022"},
        {"tipo_pa": "DI", "data_pa": "01/2022"},
        {"valor_imposto": Decimal("10.123")},
        {"valor_imposto": "1000.00"},
        {"valor_multa": Decimal("1.001")},
        {"cota": 0},
        {"cota": "1"},
        {"ganho_capital": "sim"},
        {"cnpj_prestador": "99999999999999"},
        {"cnpj_prestador": "123"},
        {"cno": "abc"},
        {"data_consolidacao": "2022-08-08"},
        {"vencimento": datetime(2022, 8, 8).date()},
    ],
)
def test_an_invalid_darf_request_is_refused_before_any_call(changes: dict[str, Any]) -> None:
    with pytest.raises(IntegraRequestError):
        _darf(**changes)


def test_the_receita_of_the_official_example_groups_the_three_objects_per_extension() -> None:
    receita = read_receita(official_payload("SICALC.CONSULTAAPOIORECEITAS52.receita_6106"))

    assert receita.codigo_receita == "6106"
    assert receita.descricao_receita == (
        "Simples - Pagamento de Micro Empresa e Empresa de Pequeno Porte"
    )
    assert len(receita.extensoes) == 2
    first, second = receita.extensoes
    assert first.obrigatorios is not None
    assert first.obrigatorios.valor_imposto is True
    assert first.obrigatorios.cota is False
    assert first.obrigatorios.vencimento is False
    assert second.obrigatorios is not None
    assert second.obrigatorios.vencimento is True
    assert first.opcionais is not None
    assert (first.opcionais.municipio, first.opcionais.valor_juros) == (True, False)
    info = first.informacoes
    assert info is not None
    assert info.codigo_receita_extensao == "1"
    assert second.informacoes is not None
    assert second.informacoes.codigo_receita_extensao == "2"
    assert info.descricao_receita_extensao == "SIMPLES - PAGAMENTO ME/EPP"
    assert info.descricao_referencia == "SEM REFERÊNCIA"
    assert info.criacao == datetime(1997, 1, 1, tzinfo=BRT)
    assert info.extincao == datetime(2007, 6, 30, tzinfo=BRT)
    assert info.tipo_periodo_apuracao == "ME"
    assert (info.calculado, info.codigo_barras, info.exige_matriz) == (True, True, True)
    assert (info.manual, info.pf, info.pj, info.veda_valor) == (False, False, False, True)


def test_the_receita_of_the_service_page_has_one_object_per_array_element() -> None:
    receita = read_receita(official_payload("SICALC.CONSULTAAPOIORECEITAS52.extensoes_separadas"))

    assert receita.codigo_receita == "6106"
    assert receita.descricao_receita == "IRPF - Ganhos de Capital"
    obrigatorios, opcionais, informacoes = receita.extensoes
    assert obrigatorios.obrigatorios is not None
    assert obrigatorios.obrigatorios.data_pa is True
    assert obrigatorios.obrigatorios.cota is None
    assert obrigatorios.opcionais is None
    assert opcionais.opcionais is not None
    assert opcionais.opcionais.data_alienacao is True
    assert opcionais.opcionais.cno is None
    assert informacoes.informacoes is not None
    assert (informacoes.informacoes.pf, informacoes.informacoes.pj) == (True, False)
    assert informacoes.informacoes.criacao is None
    assert informacoes.informacoes.codigo_receita_extensao is None


def test_the_receita_code_keeps_its_leading_zeros_when_it_arrives_as_text() -> None:
    receita = read_receita(payload_with({"receita": {"codigoReceita": "0190"}}))

    assert receita.codigo_receita == "0190"
    assert receita.descricao_receita is None
    assert receita.extensoes == ()


def test_a_receita_that_does_not_exist_is_refused_by_status() -> None:
    with pytest.raises(IntegraPayloadError, match="status 404"):
        read_receita(payload_with({"receita": {}}, status=404))


def test_a_malformed_receita_answer_is_refused_with_the_field_path() -> None:
    good = official_dados("SICALC.CONSULTAAPOIORECEITAS52.receita_6106")
    with pytest.raises(IntegraPayloadError, match=r"dados\.receita.*campo obrigatório ausente"):
        read_receita(payload_with({}))
    with pytest.raises(IntegraPayloadError, match=r"dados\.receita\.codigoReceita"):
        read_receita(payload_with({"receita": {"descricaoReceita": "x"}}))
    for bad in (["6106"], True, {"a": 1}):
        wrong = copy.deepcopy(good)
        wrong["receita"]["codigoReceita"] = bad
        with pytest.raises(IntegraPayloadError, match=r"dados\.receita\.codigoReceita"):
            read_receita(payload_with(wrong))
    flag = copy.deepcopy(good)
    flag["receita"]["extensoes"][0]["obrigatorios"]["cota"] = "talvez"
    with pytest.raises(IntegraPayloadError, match=r"extensoes\[0\]\.obrigatorios\.cota"):
        read_receita(payload_with(flag))
    date_ = copy.deepcopy(good)
    date_["receita"]["extensoes"][1]["informacoes"]["criacao"] = "ontem"
    with pytest.raises(IntegraPayloadError, match=r"extensoes\[1\]\.informacoes\.criacao"):
        read_receita(payload_with(date_))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_receita(payload_with([good]))


def test_the_alphanumeric_cnpj_example_is_read_with_text_amounts() -> None:
    consolidado = read_consolidado(official_payload("SICALC.CONSOLIDAR54.cnpj_alfanumerico"))

    assert consolidado.valor_principal_moeda_corrente == Decimal("1000.00")
    assert consolidado.valor_total_consolidado == Decimal("1784.90")
    assert consolidado.valor_multa_mora == Decimal("200.00")
    assert consolidado.percentual_multa_mora == Decimal("20.00")
    assert consolidado.valor_juros == Decimal("584.90")
    assert consolidado.percentual_juros == Decimal("58.49")
    assert consolidado.termo_inicial_juros == datetime(2021, 3, 1, tzinfo=BRT)
    assert consolidado.data_arrecadacao_consolidacao == datetime(2026, 6, 22, tzinfo=BRT)
    assert consolidado.data_validade_calculo == datetime(2026, 6, 30, tzinfo=BRT)


def test_the_numeric_amounts_of_the_service_page_are_read_as_decimals() -> None:
    consolidado = read_consolidado(official_payload("SICALC.CONSOLIDAR54.valores_numericos"))

    assert consolidado.valor_total_consolidado == Decimal("1250.00")
    assert consolidado.valor_multa_mora == Decimal(150)
    assert consolidado.percentual_juros == Decimal(10)
    assert consolidado.data_validade_calculo == datetime(2022, 8, 9, tzinfo=BRT)


def test_the_full_answer_of_service_51_is_read_ignoring_the_darf_it_carries() -> None:
    dados = official_dados("SICALC.CONSOLIDAR54.valores_numericos")
    dados["numeroDocumento"] = "22080812345678901234"
    dados["darf"] = "JVBERi0xLjQK"

    assert read_consolidado(payload_with(dados)).valor_juros == Decimal(100)


def test_an_amount_that_is_null_or_absent_is_none_but_the_principal_is_required() -> None:
    dados = official_dados("SICALC.CONSOLIDAR54.cnpj_alfanumerico")
    dados["consolidado"]["valorJuros"] = None
    del dados["consolidado"]["dataValidadeCalculo"]

    consolidado = read_consolidado(payload_with(dados))

    assert consolidado.valor_juros is None
    assert consolidado.data_validade_calculo is None
    del dados["consolidado"]["valorTotalConsolidado"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.consolidado\.valorTotalConsolidado"):
        read_consolidado(payload_with(dados))


def test_a_failed_or_broken_consolidation_is_not_presented_as_values() -> None:
    good = official_dados("SICALC.CONSOLIDAR54.cnpj_alfanumerico")
    with pytest.raises(IntegraPayloadError, match="status 400"):
        read_consolidado(payload_with(good, status=400))
    with pytest.raises(IntegraPayloadError, match=r"dados\.consolidado.*campo obrigatório"):
        read_consolidado(payload_with({"darf": "x"}))
    bad_value = copy.deepcopy(good)
    bad_value["consolidado"]["valorMultaMora"] = "caro"
    with pytest.raises(IntegraPayloadError, match=r"dados\.consolidado\.valorMultaMora"):
        read_consolidado(payload_with(bad_value))
    bad_date = copy.deepcopy(good)
    bad_date["consolidado"]["termoInicialJuros"] = "01/03/2021"
    with pytest.raises(IntegraPayloadError, match=r"dados\.consolidado\.termoInicialJuros"):
        read_consolidado(payload_with(bad_date))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_consolidado(payload_with([good]))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_consolidado({"status": 200, "mensagens": [], "dados": ""})


def test_the_module_registers_its_two_services() -> None:
    assert {typed.key: typed.request for typed in TYPED_SERVICES} == {
        "sicalc.receitas": ConsultarReceita,
        "sicalc.consolidar": ConsolidarDarf,
    }
    assert {typed.key: typed.read for typed in TYPED_SERVICES} == {
        "sicalc.receitas": read_receita,
        "sicalc.consolidar": read_consolidado,
    }
