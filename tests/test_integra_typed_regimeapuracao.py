"""REGIMEAPURACAO 102 to 104 (consultas): typed requests and readers from the official pages.

Fixtures: tests/fixtures/integra/serpro/REGIMEAPURACAO.*.json, copied from the official examples.
"""

from __future__ import annotations

import base64
import copy
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from apps.integra.errors import IntegraPayloadError, IntegraRequestError
from apps.integra.typed.regimeapuracao import (
    TYPED_SERVICES,
    ConsultarOpcao,
    ConsultarResolucao,
    read_anos,
    read_opcao,
    read_resolucao,
)
from integra_fixtures import fixture_names, official_dados, official_payload, payload_with

BRT = timezone(timedelta(hours=-3))
NOT_A_PDF = base64.b64encode(b"isto nao e um pdf").decode()
TEXT = "Resolução CGSN nº 140, de 22 de maio de 2018."


# ---- requests ----------------------------------------------------------------------------


@pytest.mark.parametrize("request_type", [ConsultarOpcao, ConsultarResolucao])
def test_the_requests_of_the_official_examples_carry_the_calendar_year_as_a_number(
    request_type: type[ConsultarOpcao] | type[ConsultarResolucao],
) -> None:
    assert request_type(ano_calendario=2023).to_dados() == {"anoCalendario": 2023}
    assert request_type(ano_calendario=2021).to_dados() == {"anoCalendario": 2021}


@pytest.mark.parametrize("year", [23, 1899, 2101, True, "2023", 2023.5])
@pytest.mark.parametrize("request_type", [ConsultarOpcao, ConsultarResolucao])
def test_an_invalid_calendar_year_is_refused_before_any_call(
    request_type: type[ConsultarOpcao] | type[ConsultarResolucao], year: Any
) -> None:
    with pytest.raises(IntegraRequestError):
        request_type(ano_calendario=year)


def test_the_list_of_years_has_no_request_because_dados_stays_empty() -> None:
    by_key = {typed.key: typed for typed in TYPED_SERVICES}

    assert by_key["regimeapuracao.anos"].request is None


# ---- 102: years --------------------------------------------------------------------------


def test_the_years_with_an_option_are_read_with_their_regime() -> None:
    years = read_anos(official_payload("REGIMEAPURACAO.CONSULTARANOSCALENDARIOS102.anos"))

    assert len(years) == 9
    assert (years[0].ano_calendario, years[0].regime_apurado) == (2023, "CAIXA")
    assert (years[1].ano_calendario, years[1].regime_apurado) == (2017, "COMPETENCIA")
    assert (years[-1].ano_calendario, years[-1].regime_apurado) == (2010, "COMPETENCIA")


def test_a_broken_list_of_years_is_refused_with_the_path_of_the_field() -> None:
    good = official_dados("REGIMEAPURACAO.CONSULTARANOSCALENDARIOS102.anos")
    with pytest.raises(IntegraPayloadError, match="status 500"):
        read_anos(payload_with(good, status=500))
    with pytest.raises(IntegraPayloadError, match="uma lista"):
        read_anos(payload_with(good[0]))
    with pytest.raises(IntegraPayloadError, match="uma lista"):
        read_anos(payload_with(None))
    missing = copy.deepcopy(good)
    del missing[2]["regimeApurado"]
    with pytest.raises(IntegraPayloadError, match=r"dados\[2\]\.regimeApurado"):
        read_anos(payload_with(missing))
    bad_year = copy.deepcopy(good)
    bad_year[0]["anoCalendario"] = "dois mil"
    with pytest.raises(IntegraPayloadError, match=r"dados\[0\]\.anoCalendario"):
        read_anos(payload_with(bad_year))
    bad_regime = copy.deepcopy(good)
    bad_regime[0]["regimeApurado"] = 1
    with pytest.raises(IntegraPayloadError, match=r"dados\[0\]\.regimeApurado"):
        read_anos(payload_with(bad_regime))


# ---- 103: option -------------------------------------------------------------------------


def test_the_option_for_the_cash_regime_carries_the_statement_and_the_resolution() -> None:
    option = read_opcao(official_payload("REGIMEAPURACAO.CONSULTAROPCAOREGIME103.caixa"))

    assert option.cnpj_matriz == "00000000000000"
    assert option.ano_calendario == 2023
    assert option.regime_escolhido == "CAIXA"
    assert option.data_hora_opcao == datetime(2022, 12, 20, 2, 58, 18, tzinfo=BRT)
    assert option.demonstrativo_pdf is not None
    assert option.demonstrativo_pdf.startswith(b"%PDF-")
    assert option.texto_resolucao is not None
    assert option.texto_resolucao.startswith("Resolução CGSN nº 140, de 22 de maio de 2018.")
    assert len(option.texto_resolucao) == 9064


def test_an_option_without_resolution_text_leaves_it_empty() -> None:
    dados = official_dados("REGIMEAPURACAO.CONSULTAROPCAOREGIME103.caixa")
    dados["regimeEscolhido"] = "COMPETENCIA"
    del dados["textoResolucao"]

    option = read_opcao(payload_with(dados))

    assert option.regime_escolhido == "COMPETENCIA"
    assert option.texto_resolucao is None


def test_an_empty_resolution_text_in_the_option_is_nothing_to_say() -> None:
    dados = official_dados("REGIMEAPURACAO.CONSULTAROPCAOREGIME103.caixa")
    dados["textoResolucao"] = ""

    assert read_opcao(payload_with(dados)).texto_resolucao is None


def test_the_cnpj_of_the_matriz_may_arrive_as_a_number() -> None:
    dados = official_dados("REGIMEAPURACAO.CONSULTAROPCAOREGIME103.caixa")
    dados["cnpjMatriz"] = 12345678000195
    assert read_opcao(payload_with(dados)).cnpj_matriz == "12345678000195"
    dados["cnpjMatriz"] = 345678000195
    assert read_opcao(payload_with(dados)).cnpj_matriz == "00345678000195"


def test_a_broken_option_is_refused_with_the_path_of_the_field() -> None:
    good = official_dados("REGIMEAPURACAO.CONSULTAROPCAOREGIME103.caixa")
    with pytest.raises(IntegraPayloadError, match="status 404"):
        read_opcao(payload_with(good, status=404))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_opcao(payload_with([good]))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_opcao(payload_with(None))
    missing = copy.deepcopy(good)
    del missing["regimeEscolhido"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.regimeEscolhido"):
        read_opcao(payload_with(missing))
    fake_pdf = copy.deepcopy(good)
    fake_pdf["demonstrativoPdf"] = NOT_A_PDF
    with pytest.raises(IntegraPayloadError, match=r"dados\.demonstrativoPdf deve ser um PDF"):
        read_opcao(payload_with(fake_pdf))
    no_pdf = copy.deepcopy(good)
    del no_pdf["demonstrativoPdf"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.demonstrativoPdf"):
        read_opcao(payload_with(no_pdf))
    bad_date = copy.deepcopy(good)
    bad_date["dataHoraOpcao"] = "ontem"
    with pytest.raises(IntegraPayloadError, match=r"dados\.dataHoraOpcao"):
        read_opcao(payload_with(bad_date))
    bad_cnpj = copy.deepcopy(good)
    bad_cnpj["cnpjMatriz"] = "12.345"
    with pytest.raises(IntegraPayloadError, match=r"dados\.cnpjMatriz"):
        read_opcao(payload_with(bad_cnpj))
    bad_text = copy.deepcopy(good)
    bad_text["textoResolucao"] = 123
    with pytest.raises(IntegraPayloadError, match=r"dados\.textoResolucao"):
        read_opcao(payload_with(bad_text))


# ---- 104: resolution ---------------------------------------------------------------------


def test_the_resolution_is_read_as_the_plain_text_of_the_official_example() -> None:
    resolution = read_resolucao(
        official_payload("REGIMEAPURACAO.CONSULTARRESOLUCAO104.resolucao")
    )

    assert resolution.texto_resolucao.startswith("Resolução CGSN nº 140, de 22 de maio de 2018.")
    assert resolution.texto_resolucao.endswith("art. 26, § 4º).")


def test_the_resolution_is_decoded_when_it_arrives_in_base64_as_the_table_says() -> None:
    encoded = base64.b64encode(TEXT.encode("utf-8")).decode()

    assert read_resolucao(payload_with({"textoResolucao": encoded})).texto_resolucao == TEXT
    wrapped = encoded[:20] + "\r\n" + encoded[20:]
    assert read_resolucao(payload_with({"textoResolucao": wrapped})).texto_resolucao == TEXT


def test_a_broken_resolution_is_refused() -> None:
    with pytest.raises(IntegraPayloadError, match="status 500"):
        read_resolucao(payload_with({"textoResolucao": TEXT}, status=500))
    with pytest.raises(IntegraPayloadError, match=r"dados\.textoResolucao: campo obrigatório"):
        read_resolucao(payload_with({}))
    with pytest.raises(IntegraPayloadError, match=r"dados\.textoResolucao"):
        read_resolucao(payload_with({"textoResolucao": 5}))
    with pytest.raises(IntegraPayloadError, match=r"dados\.textoResolucao"):
        read_resolucao(payload_with({"textoResolucao": "   "}))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_resolucao(payload_with([{"textoResolucao": TEXT}]))


# ---- registry ----------------------------------------------------------------------------


def test_every_fixture_of_the_module_is_read_by_its_reader() -> None:
    readers: dict[str, Callable[[Mapping[str, Any]], object]] = {
        "REGIMEAPURACAO.CONSULTARANOSCALENDARIOS102": read_anos,
        "REGIMEAPURACAO.CONSULTAROPCAOREGIME103": read_opcao,
        "REGIMEAPURACAO.CONSULTARRESOLUCAO104": read_resolucao,
    }
    for servico, reader in readers.items():
        names = fixture_names(servico)
        assert names, servico
        for name in names:
            assert reader(official_payload(name)) is not None, name


def test_the_module_registers_its_three_services() -> None:
    assert {typed.key: typed.request for typed in TYPED_SERVICES} == {
        "regimeapuracao.anos": None,
        "regimeapuracao.opcao": ConsultarOpcao,
        "regimeapuracao.resolucao": ConsultarResolucao,
    }
    assert {typed.key: typed.read for typed in TYPED_SERVICES} == {
        "regimeapuracao.anos": read_anos,
        "regimeapuracao.opcao": read_opcao,
        "regimeapuracao.resolucao": read_resolucao,
    }
