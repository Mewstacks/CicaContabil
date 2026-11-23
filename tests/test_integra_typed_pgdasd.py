"""PGDASD 13 to 16 (consultas): typed requests and readers from the official pages.

Fixtures: tests/fixtures/integra/serpro/PGDASD.*.json, copied from the official examples
(`por_periodo` and `sem_maed` are built from the tables and the text of the pages).
"""

from __future__ import annotations

import base64
import copy
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from apps.integra.errors import IntegraPayloadError, IntegraRequestError
from apps.integra.typed.pgdasd import (
    TYPED_SERVICES,
    ConsultarDeclaracao,
    ConsultarDeclaracoes,
    ConsultarExtratoDas,
    ConsultarUltimaDeclaracao,
    Declaracao,
    read_declaracao,
    read_declaracoes,
    read_extrato,
    read_ultima_declaracao,
)
from integra_fixtures import fixture_names, official_dados, official_payload, payload_with

BRT = timezone(timedelta(hours=-3))
NOT_A_PDF = base64.b64encode(b"isto nao e um pdf").decode()


# ---- requests ----------------------------------------------------------------------------


def test_the_index_request_by_year_or_by_month_matches_the_official_examples() -> None:
    assert ConsultarDeclaracoes(ano_calendario=2018).to_dados() == {"anoCalendario": "2018"}
    assert ConsultarDeclaracoes(periodo_apuracao=201801).to_dados() == {
        "periodoApuracao": "201801"
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"ano_calendario": 2018, "periodo_apuracao": 201801},
        {"ano_calendario": 18},
        {"ano_calendario": 21000},
        {"periodo_apuracao": 201813},
        {"periodo_apuracao": 20181},
        {"periodo_apuracao": "201801"},
        {"ano_calendario": True},
    ],
)
def test_an_index_request_needs_exactly_one_valid_period(kwargs: dict[str, Any]) -> None:
    with pytest.raises(IntegraRequestError):
        ConsultarDeclaracoes(**kwargs)


def test_the_requests_by_period_declaration_and_das_match_the_official_examples() -> None:
    assert ConsultarUltimaDeclaracao(periodo_apuracao=201801).to_dados() == {
        "periodoApuracao": "201801"
    }
    assert ConsultarDeclaracao(numero_declaracao="00000000201801001").to_dados() == {
        "numeroDeclaracao": "00000000201801001"
    }
    assert ConsultarExtratoDas(numero_das="07202136999997159").to_dados() == {
        "numeroDas": "07202136999997159"
    }


@pytest.mark.parametrize("number", ["", "123", "0000000020180100", "000000002018010011", "x" * 17])
def test_a_declaration_or_das_number_must_have_seventeen_digits(number: str) -> None:
    with pytest.raises(IntegraRequestError):
        ConsultarDeclaracao(numero_declaracao=number)
    with pytest.raises(IntegraRequestError):
        ConsultarExtratoDas(numero_das=number)


def test_the_last_declaration_request_refuses_a_missing_or_invalid_month() -> None:
    request: Any = ConsultarUltimaDeclaracao
    with pytest.raises(TypeError):
        request()
    with pytest.raises(IntegraRequestError):
        ConsultarUltimaDeclaracao(periodo_apuracao=201800)


# ---- 13: index of declarations -----------------------------------------------------------


def test_the_index_by_year_lists_declarations_and_dases_by_month() -> None:
    answer = read_declaracoes(official_payload("PGDASD.CONSDECLARACAO13.por_ano"))

    assert answer.ano_calendario == 2018
    assert answer.periodo is None
    assert [period.periodo_apuracao for period in answer.periodos] == list(
        range(201801, 201813)
    )
    january = answer.periodos[0]
    assert [operation.tipo_operacao for operation in january.operacoes] == [
        "Original",
        "Geração de DAS",
    ]
    original = january.operacoes[0].indice_declaracao
    assert original is not None
    assert original.numero_declaracao == "00000000201801001"
    assert original.data_hora_transmissao == datetime(2022, 3, 31, 3, 25, 12, tzinfo=BRT)
    assert original.malha is None
    assert january.operacoes[0].indice_das is None
    das = january.operacoes[1].indice_das
    assert january.operacoes[1].indice_declaracao is None
    assert das is not None
    assert das.numero_das == "07202219799007800"
    assert das.data_hora_emissao_das == datetime(2022, 6, 6, 3, 34, 56, tzinfo=BRT)
    assert das.das_pago is False
    february = answer.periodos[1]
    assert [operation.tipo_operacao for operation in february.operacoes][:2] == [
        "Original",
        "Retificadora",
    ]
    assert len(february.operacoes) == 4


def test_the_index_by_month_has_a_single_period_with_malha_and_paid_das() -> None:
    answer = read_declaracoes(official_payload("PGDASD.CONSDECLARACAO13.por_periodo"))

    assert answer.ano_calendario == 2018
    assert answer.periodos == ()
    assert answer.periodo is not None
    assert answer.periodo.periodo_apuracao == 201801
    declaration, das = (operation for operation in answer.periodo.operacoes)
    assert declaration.indice_declaracao is not None
    assert declaration.indice_declaracao.malha == "Retida em Malha"
    assert das.indice_das is not None
    assert das.indice_das.das_pago is True
    assert das.indice_das.data_hora_emissao_das == datetime(2022, 6, 6, 3, 34, 56, tzinfo=BRT)


def test_the_index_reads_the_year_and_the_emission_in_both_spellings() -> None:
    by_year = official_dados("PGDASD.CONSDECLARACAO13.por_ano")
    by_table = copy.deepcopy(by_year)
    by_table["anoCalendario"] = by_table.pop("anocalendario")
    for period in by_table["periodos"]:
        for operation in period["operacoes"]:
            if operation["indiceDas"]:
                das = operation["indiceDas"]
                das["dataHoraEmissaoDas"] = das.pop("datahoraEmissaoDas")

    from_example = read_declaracoes(payload_with(by_year))
    from_table = read_declaracoes(payload_with(by_table))

    assert from_example.ano_calendario == from_table.ano_calendario == 2018
    for answer in (from_example, from_table):
        das_index = answer.periodos[0].operacoes[1].indice_das
        assert das_index is not None
        assert das_index.data_hora_emissao_das == datetime(2022, 6, 6, 3, 34, 56, tzinfo=BRT)


def test_the_index_refuses_broken_answers_with_the_path_of_the_field() -> None:
    good = official_dados("PGDASD.CONSDECLARACAO13.por_ano")
    with pytest.raises(IntegraPayloadError, match="status 500"):
        read_declaracoes(payload_with(good, status=500))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_declaracoes(payload_with([good]))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_declaracoes(payload_with(None))
    not_a_list = copy.deepcopy(good)
    not_a_list["periodos"] = good["periodos"][0]
    with pytest.raises(IntegraPayloadError, match=r"dados\.periodos deve ser uma lista"):
        read_declaracoes(payload_with(not_a_list))
    missing = copy.deepcopy(good)
    del missing["periodos"][0]["operacoes"][0]["indiceDeclaracao"]["numeroDeclaracao"]
    path = r"dados\.periodos\[0\]\.operacoes\[0\]\.indiceDeclaracao\.numeroDeclaracao"
    with pytest.raises(IntegraPayloadError, match=path):
        read_declaracoes(payload_with(missing))
    bad_flag = copy.deepcopy(good)
    bad_flag["periodos"][0]["operacoes"][1]["indiceDas"]["dasPago"] = "talvez"
    with pytest.raises(IntegraPayloadError, match=r"indiceDas\.dasPago"):
        read_declaracoes(payload_with(bad_flag))
    bad_date = copy.deepcopy(good)
    bad_date["periodos"][0]["operacoes"][0]["indiceDeclaracao"]["dataHoraTransmissao"] = "ontem"
    with pytest.raises(IntegraPayloadError, match=r"indiceDeclaracao\.dataHoraTransmissao"):
        read_declaracoes(payload_with(bad_date))


# ---- 14 and 15: declaration and receipt --------------------------------------------------


@pytest.mark.parametrize(
    ("reader", "name"),
    [
        (read_ultima_declaracao, "PGDASD.CONSULTIMADECREC14.com_maed"),
        (read_declaracao, "PGDASD.CONSDECREC15.com_maed"),
    ],
)
def test_a_declaration_late_in_delivery_comes_with_the_maed_documents(
    reader: Callable[[Mapping[str, Any]], Declaracao], name: str
) -> None:
    declaration = reader(official_payload(name))

    assert declaration.numero_declaracao == "00000000201801001"
    assert declaration.recibo.nome_arquivo == "PGDASD-RECIBO-00000000201801001.pdf"
    assert declaration.recibo.pdf.startswith(b"%PDF-")
    assert declaration.declaracao.nome_arquivo == "PGDASD-DECLARACAO-00000000201801001.pdf"
    assert declaration.declaracao.pdf.startswith(b"%PDF-")
    maed = declaration.maed
    assert maed is not None
    assert maed.nome_arquivo_notificacao == "PGDASD-NOTIFICACAO-MAED-00000000201801001.pdf"
    assert maed.pdf_notificacao is not None
    assert maed.pdf_notificacao.startswith(b"%PDF-")
    assert maed.nome_arquivo_darf == "PGDASD-DARF-MAED-00000000201801001.pdf"
    assert maed.pdf_darf is not None
    assert maed.pdf_darf.startswith(b"%PDF-")


def test_a_declaration_delivered_on_time_has_no_maed() -> None:
    declaration = read_ultima_declaracao(official_payload("PGDASD.CONSULTIMADECREC14.sem_maed"))

    assert declaration.numero_declaracao == "00000000201802002"
    assert declaration.maed is None
    assert declaration.recibo.pdf.startswith(b"%PDF-")


def test_the_maed_may_carry_only_one_of_its_two_documents() -> None:
    dados = official_dados("PGDASD.CONSULTIMADECREC14.com_maed")
    del dados["maed"]["pdfDarf"], dados["maed"]["nomeArquivoDarf"]

    maed = read_ultima_declaracao(payload_with(dados)).maed

    assert maed is not None
    assert maed.pdf_notificacao is not None
    assert maed.pdf_darf is None
    assert maed.nome_arquivo_darf is None


@pytest.mark.parametrize("reader", [read_ultima_declaracao, read_declaracao])
def test_a_declaration_answer_that_breaks_the_contract_is_refused(
    reader: Callable[[Mapping[str, Any]], Declaracao],
) -> None:
    good = official_dados("PGDASD.CONSULTIMADECREC14.com_maed")
    with pytest.raises(IntegraPayloadError, match="status 400"):
        reader(payload_with(good, status=400))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        reader(payload_with([good]))
    missing = copy.deepcopy(good)
    del missing["numeroDeclaracao"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.numeroDeclaracao"):
        reader(payload_with(missing))
    no_pdf = copy.deepcopy(good)
    del no_pdf["recibo"]["pdf"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.recibo\.pdf"):
        reader(payload_with(no_pdf))
    fake_pdf = copy.deepcopy(good)
    fake_pdf["declaracao"]["pdf"] = NOT_A_PDF
    with pytest.raises(IntegraPayloadError, match=r"dados\.declaracao\.pdf deve ser um PDF"):
        reader(payload_with(fake_pdf))
    fake_maed = copy.deepcopy(good)
    fake_maed["maed"]["pdfDarf"] = "isto não é base64!"
    with pytest.raises(IntegraPayloadError, match=r"dados\.maed\.pdfDarf"):
        reader(payload_with(fake_maed))
    wrong_type = copy.deepcopy(good)
    wrong_type["recibo"] = "JVBERi0="
    with pytest.raises(IntegraPayloadError, match=r"dados\.recibo deve ser um objeto"):
        reader(payload_with(wrong_type))


# ---- 16: DAS statement -------------------------------------------------------------------


def test_the_das_statement_is_a_pdf_with_its_name() -> None:
    answer = read_extrato(official_payload("PGDASD.CONSEXTRATO16.extrato"))

    assert answer.numero_das == "07202136999997159"
    assert answer.extrato.nome_arquivo == "PGDASD-EXTRATO-07202136999997159.pdf"
    assert answer.extrato.pdf.startswith(b"%PDF-")


def test_a_broken_das_statement_is_refused() -> None:
    good = official_dados("PGDASD.CONSEXTRATO16.extrato")
    with pytest.raises(IntegraPayloadError, match="status 500"):
        read_extrato(payload_with(good, status=500))
    missing = copy.deepcopy(good)
    del missing["extrato"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.extrato"):
        read_extrato(payload_with(missing))
    fake_pdf = copy.deepcopy(good)
    fake_pdf["extrato"]["pdf"] = NOT_A_PDF
    with pytest.raises(IntegraPayloadError, match=r"dados\.extrato\.pdf"):
        read_extrato(payload_with(fake_pdf))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_extrato(payload_with([good]))


# ---- registry ----------------------------------------------------------------------------


def test_every_fixture_of_the_module_is_read_by_its_reader() -> None:
    readers = {
        "PGDASD.CONSDECLARACAO13": read_declaracoes,
        "PGDASD.CONSULTIMADECREC14": read_ultima_declaracao,
        "PGDASD.CONSDECREC15": read_declaracao,
        "PGDASD.CONSEXTRATO16": read_extrato,
    }
    for servico, reader in readers.items():
        names = fixture_names(servico)
        assert names, servico
        for name in names:
            assert reader(official_payload(name)) is not None, name


def test_the_module_registers_its_four_services() -> None:
    assert {typed.key: typed.request for typed in TYPED_SERVICES} == {
        "pgdasd.declaracoes": ConsultarDeclaracoes,
        "pgdasd.ultima_declaracao": ConsultarUltimaDeclaracao,
        "pgdasd.declaracao": ConsultarDeclaracao,
        "pgdasd.extrato": ConsultarExtratoDas,
    }
    assert {typed.key: typed.read for typed in TYPED_SERVICES} == {
        "pgdasd.declaracoes": read_declaracoes,
        "pgdasd.ultima_declaracao": read_ultima_declaracao,
        "pgdasd.declaracao": read_declaracao,
        "pgdasd.extrato": read_extrato,
    }
