"""CCMEI 122 (dados) and 123 (situação cadastral): typed readers from the official pages.

Fixtures: tests/fixtures/integra/serpro/CCMEI.*.json, from the official examples.
"""

from __future__ import annotations

import copy
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.integra.errors import IntegraPayloadError
from apps.integra.typed.ccmei import (
    TYPED_SERVICES,
    read_dados,
    read_situacoes,
)
from integra_fixtures import official_dados, official_payload, payload_with


def test_the_ccmei_of_the_official_example_is_read_with_all_its_objects() -> None:
    ccmei = read_dados(official_payload("CCMEI.DADOSCCMEI122.empresario"))

    assert ccmei.cnpj == "00000000000000"
    assert ccmei.nome_empresarial == "AQUI VAI O NOME EMPRESARIAL"
    assert ccmei.capital_social == Decimal("1000.00")
    assert ccmei.situacao_cadastral_vigente == "ATIVA"
    assert ccmei.data_inicio_atividades == date(2020, 1, 1)
    assert ccmei.data_inicio_situacao_cadastral == date(2020, 1, 1)
    assert ccmei.qr_code is None
    assert ccmei.empresario is not None
    assert ccmei.empresario.nome_civil == "AQUI VAI O NOME CIVIL"
    assert ccmei.empresario.nome_social is None
    assert ccmei.empresario.cpf == "99999999999"


def test_the_address_keeps_the_zip_as_text_and_an_empty_complement_as_none() -> None:
    endereco = read_dados(official_payload("CCMEI.DADOSCCMEI122.empresario")).endereco_comercial

    assert endereco is not None
    assert endereco.cep == "99999999"
    assert endereco.complemento is None
    assert (endereco.logradouro, endereco.numero) == ("AQUI VAI O NOME DO LOGRADOURO", "999")
    assert (endereco.bairro, endereco.municipio, endereco.uf) == (
        "AQUI VAI O BAIRRO",
        "NOME DO MUNICIPIO",
        "UF",
    )


def test_a_zip_that_arrives_as_a_number_gets_its_leading_zero_back() -> None:
    dados = official_dados("CCMEI.DADOSCCMEI122.empresario")
    dados["enderecoComercial"]["cep"] = 1310100

    endereco = read_dados(payload_with(dados)).endereco_comercial

    assert endereco is not None
    assert endereco.cep == "01310100"


def test_the_framing_periods_and_the_activity_are_read() -> None:
    ccmei = read_dados(official_payload("CCMEI.DADOSCCMEI122.empresario"))

    assert ccmei.enquadramento is not None
    assert ccmei.enquadramento.situacao == "Enquadrado na condição de MEI"
    assert ccmei.enquadramento.optante_mei is True
    (periodo,) = ccmei.enquadramento.periodos_mei
    assert (periodo.indice, periodo.data_inicio, periodo.data_fim) == (1, date(2020, 1, 1), None)
    atividade = ccmei.atividade
    assert atividade is not None
    assert atividade.formas_atuacao == ("Estabelecimento fixo", "Internet")
    assert atividade.optante_mei is None
    assert atividade.ocupacao_principal is not None
    assert atividade.ocupacao_principal.codigo_cnae == "9999-9/99"
    assert atividade.ocupacao_principal.descricao_cnae == "DESCRICAO DA CNAE"
    (secundaria,) = atividade.ocupacoes_secundarias
    assert (secundaria.descricao_ocupacao, secundaria.codigo_cnae) == (
        "DESCRICAO DA OCUPACAO",
        "9999999",
    )


def test_the_dispensation_term_is_read() -> None:
    termo = read_dados(official_payload("CCMEI.DADOSCCMEI122.empresario")).termo_ciencia_dispensa

    assert termo is not None
    assert termo.titulo.startswith("Termo de Ciência e Responsabilidade")
    assert termo.texto is not None
    assert termo.texto.startswith("Declaro, sob as penas da Lei")


@pytest.mark.parametrize("key", ["qrCode", "qrcode"])
def test_the_qr_code_is_kept_as_text_under_either_spelling(key: str) -> None:
    # The table says `qrcode` and the example says `qrCode`.
    dados = official_dados("CCMEI.DADOSCCMEI122.empresario")
    del dados["qrCode"]
    dados[key] = "aVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FB"

    assert read_dados(payload_with(dados)).qr_code == "aVZCT1J3MEtHZ29BQUFBTlNVaEVVZ0FB"


def test_the_ccmei_without_the_optional_objects_is_still_read() -> None:
    ccmei = read_dados(payload_with({"cnpj": "00000000000000"}))

    assert ccmei.cnpj == "00000000000000"
    assert ccmei.empresario is None
    assert ccmei.enquadramento is None
    assert ccmei.atividade is None
    assert ccmei.capital_social is None
    assert ccmei.qr_code is None


def test_a_broken_ccmei_answer_is_refused_with_the_field_path() -> None:
    good = official_dados("CCMEI.DADOSCCMEI122.empresario")
    with pytest.raises(IntegraPayloadError, match="status 404"):
        read_dados(payload_with(good, status=404))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_dados(payload_with([good]))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_dados({"status": 200, "mensagens": [], "dados": ""})
    cases: list[tuple[list[str | int], Any, str]] = [
        (["cnpj"], None, r"dados\.cnpj.*campo obrigatório ausente"),
        (["empresario", "nomeCivil"], None, r"dados\.empresario\.nomeCivil"),
        (["empresario", "cpf"], 12, r"dados\.empresario\.cpf"),
        (["capitalSocial"], "muito", r"dados\.capitalSocial"),
        (["dataInicioAtividades"], "01/01/2020", r"dados\.dataInicioAtividades"),
        (["enderecoComercial", "uf"], None, r"dados\.enderecoComercial\.uf"),
        (["enquadramento", "optanteMei"], "talvez", r"dados\.enquadramento\.optanteMei"),
        (["enquadramento", "periodosMei"], {"indice": 1}, r"periodosMei.*uma lista"),
        (["enquadramento", "periodosMei", 0, "dataFim"], "fim", r"periodosMei\[0\]\.dataFim"),
        (["atividade", "formasAtuacao"], "Internet", r"formasAtuacao.*uma lista"),
        (
            ["atividade", "ocupacaoPrincipal", "descricaoOcupacao"],
            None,
            r"ocupacaoPrincipal\.descricaoOcupacao",
        ),
        (["termoCienciaDispensa", "titulo"], None, r"termoCienciaDispensa\.titulo"),
    ]
    for path, value, message in cases:
        broken = copy.deepcopy(good)
        target: Any = broken
        for step in path[:-1]:
            target = target[step]
        if value is None and path[-1] in target:
            del target[path[-1]]
        else:
            target[path[-1]] = value
        with pytest.raises(IntegraPayloadError, match=message):
            read_dados(payload_with(broken))


def test_the_situations_of_the_two_cnpjs_are_read() -> None:
    situacoes = read_situacoes(official_payload("CCMEI.CCMEISITCADASTRAL123.cnpjs"))

    assert [(item.cnpj, item.situacao, item.enquadrado_mei) for item in situacoes] == [
        ("00000000000000", "BAIXADA", True),
        ("11111111111111", "ATIVA", True),
    ]


def test_a_cpf_without_cnpjs_gets_an_empty_list() -> None:
    assert read_situacoes(payload_with([])) == ()


def test_a_broken_situation_answer_is_refused_with_the_field_path() -> None:
    good = official_dados("CCMEI.CCMEISITCADASTRAL123.cnpjs")
    with pytest.raises(IntegraPayloadError, match="status 500"):
        read_situacoes(payload_with(good, status=500))
    with pytest.raises(IntegraPayloadError, match="uma lista"):
        read_situacoes(payload_with(good[0]))
    with pytest.raises(IntegraPayloadError, match="uma lista"):
        read_situacoes({"status": 200, "mensagens": [], "dados": ""})
    missing = copy.deepcopy(good)
    del missing[0]["cnpj"]
    with pytest.raises(IntegraPayloadError, match=r"dados\[0\]\.cnpj"):
        read_situacoes(payload_with(missing))
    wrong = copy.deepcopy(good)
    wrong[1]["enquadradoMei"] = "sim"
    with pytest.raises(IntegraPayloadError, match=r"dados\[1\]\.enquadradoMei"):
        read_situacoes(payload_with(wrong))
    wrong_type = copy.deepcopy(good)
    wrong_type[1]["situacao"] = 3
    with pytest.raises(IntegraPayloadError, match=r"dados\[1\]\.situacao"):
        read_situacoes(payload_with(wrong_type))


def test_the_module_registers_its_two_services_without_a_request_model() -> None:
    assert {typed.key: typed.request for typed in TYPED_SERVICES} == {
        "ccmei.dados": None,
        "ccmei.situacao_cadastral": None,
    }
    assert {typed.key: typed.read for typed in TYPED_SERVICES} == {
        "ccmei.dados": read_dados,
        "ccmei.situacao_cadastral": read_situacoes,
    }
