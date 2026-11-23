"""DEFIS 142 to 144 (consultas): typed requests and readers from the official pages.

Fixtures: tests/fixtures/integra/serpro/DEFIS.*.json, copied from the official examples (the
list of 142 had lost its punctuation on the page and was rebuilt, with a note in the file).
"""

from __future__ import annotations

import base64
import copy
from collections.abc import Callable, Mapping
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from apps.integra.errors import IntegraPayloadError, IntegraRequestError
from apps.integra.typed.defis import (
    TYPED_SERVICES,
    ConsultarDeclaracao,
    ConsultarUltimaDeclaracao,
    DeclaracaoComRecibo,
    read_declaracao,
    read_declaracoes,
    read_ultima_declaracao,
)
from integra_fixtures import (
    MINIMAL_PDF_B64,
    fixture_names,
    official_dados,
    official_payload,
    payload_with,
)

BRT = timezone(timedelta(hours=-3))
NOT_A_PDF = base64.b64encode(b"isto nao e um pdf").decode()
Reader = Callable[[Mapping[str, Any]], DeclaracaoComRecibo]


# ---- requests ----------------------------------------------------------------------------


def test_the_requests_of_the_official_examples_are_built_field_by_field() -> None:
    assert ConsultarUltimaDeclaracao(ano=2021).to_dados() == {"ano": 2021}
    assert ConsultarDeclaracao(id_defis="000000002021002").to_dados() == {
        "idDefis": "000000002021002"
    }


@pytest.mark.parametrize("year", [21, 1899, 2101, True, "2021"])
def test_the_year_of_the_last_declaration_must_be_a_calendar_year(year: Any) -> None:
    with pytest.raises(IntegraRequestError):
        ConsultarUltimaDeclaracao(ano=year)


@pytest.mark.parametrize(
    "id_defis", ["", "2021002", "00000000202100", "0000000020210021", "x" * 15]
)
def test_the_id_defis_must_have_fifteen_digits(id_defis: str) -> None:
    with pytest.raises(IntegraRequestError):
        ConsultarDeclaracao(id_defis=id_defis)


def test_the_list_of_declarations_has_no_request_because_dados_stays_empty() -> None:
    by_key = {typed.key: typed for typed in TYPED_SERVICES}

    assert by_key["defis.declaracoes"].request is None


# ---- 142: list of declarations -----------------------------------------------------------


def test_the_list_of_transmitted_declarations_is_read_item_by_item() -> None:
    declarations = read_declaracoes(official_payload("DEFIS.CONSDECLARACAO142.declaracoes"))

    assert [item.id_defis for item in declarations] == [
        "000000002019001",
        "000000002018003",
        "000000002019002",
    ]
    first = declarations[0]
    assert first.ano_calendario == 2019
    assert first.tipo == 1
    assert first.data_hora == datetime(2023, 7, 25, 10, 24, 10, tzinfo=BRT)
    assert [item.tipo for item in declarations] == [1, 2, 2]


def test_the_id_and_the_type_are_read_as_the_page_and_the_example_write_them() -> None:
    dados = official_dados("DEFIS.CONSDECLARACAO142.declaracoes")
    dados[0]["idDefis"] = 2019001  # the table says Number
    dados[0]["tipo"] = "3"  # the table says String

    first = read_declaracoes(payload_with(dados))[0]

    assert first.id_defis == "000000002019001"
    assert first.tipo == 3


def test_a_broken_list_of_declarations_is_refused_with_the_path_of_the_field() -> None:
    good = official_dados("DEFIS.CONSDECLARACAO142.declaracoes")
    with pytest.raises(IntegraPayloadError, match="status 500"):
        read_declaracoes(payload_with(good, status=500))
    with pytest.raises(IntegraPayloadError, match="uma lista"):
        read_declaracoes(payload_with(good[0]))
    with pytest.raises(IntegraPayloadError, match="uma lista"):
        read_declaracoes(payload_with(None))
    missing = copy.deepcopy(good)
    del missing[1]["anoCalendario"]
    with pytest.raises(IntegraPayloadError, match=r"dados\[1\]\.anoCalendario"):
        read_declaracoes(payload_with(missing))
    bad_id = copy.deepcopy(good)
    bad_id[0]["idDefis"] = "123"
    with pytest.raises(IntegraPayloadError, match=r"dados\[0\]\.idDefis"):
        read_declaracoes(payload_with(bad_id))
    bad_date = copy.deepcopy(good)
    bad_date[2]["dataHora"] = "ontem"
    with pytest.raises(IntegraPayloadError, match=r"dados\[2\]\.dataHora"):
        read_declaracoes(payload_with(bad_date))
    bad_year = copy.deepcopy(good)
    bad_year[0]["anoCalendario"] = "dois mil"
    with pytest.raises(IntegraPayloadError, match=r"dados\[0\]\.anoCalendario"):
        read_declaracoes(payload_with(bad_year))


# ---- 143 and 144: declaration and receipt ------------------------------------------------


def test_the_last_declaration_carries_its_id_and_both_pdfs() -> None:
    answer = read_ultima_declaracao(official_payload("DEFIS.CONSULTIMADECREC143.ultima"))

    assert answer.id_defis == "000000002021002"
    assert answer.declaracao.startswith(b"%PDF-")
    assert answer.recibo.startswith(b"%PDF-")


def test_a_specific_declaration_has_both_pdfs_and_no_id() -> None:
    answer = read_declaracao(official_payload("DEFIS.CONSDECREC144.declaracao"))

    assert answer.id_defis is None
    assert answer.declaracao.startswith(b"%PDF-")
    assert answer.recibo.startswith(b"%PDF-")


def test_the_pdfs_are_read_under_the_names_of_the_table_too() -> None:
    dados = {
        "idDefis": 2021002,  # the table says Number, the example a text of 15 digits
        "declaracao": MINIMAL_PDF_B64,
        "recibo": MINIMAL_PDF_B64,
    }

    answer = read_ultima_declaracao(payload_with(dados))

    assert answer.id_defis == "000000002021002"
    assert answer.declaracao.startswith(b"%PDF-")
    assert answer.recibo.startswith(b"%PDF-")


@pytest.mark.parametrize("reader", [read_ultima_declaracao, read_declaracao])
def test_an_answer_without_a_pdf_or_with_a_fake_one_is_refused(reader: Reader) -> None:
    good = official_dados("DEFIS.CONSULTIMADECREC143.ultima")
    with pytest.raises(IntegraPayloadError, match="status 400"):
        reader(payload_with(good, status=400))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        reader(payload_with([good]))
    no_declaration = copy.deepcopy(good)
    del no_declaration["declaracaoPdf"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.declaracaoPdf"):
        reader(payload_with(no_declaration))
    no_receipt = copy.deepcopy(good)
    del no_receipt["reciboPdf"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.reciboPdf"):
        reader(payload_with(no_receipt))
    fake_pdf = copy.deepcopy(good)
    fake_pdf["reciboPdf"] = NOT_A_PDF
    with pytest.raises(IntegraPayloadError, match=r"dados\.reciboPdf deve ser um PDF"):
        reader(payload_with(fake_pdf))
    not_base64 = copy.deepcopy(good)
    not_base64["declaracaoPdf"] = "isto não é base64!"
    with pytest.raises(IntegraPayloadError, match=r"dados\.declaracaoPdf"):
        reader(payload_with(not_base64))
    bad_id = copy.deepcopy(good)
    bad_id["idDefis"] = "abc"
    with pytest.raises(IntegraPayloadError, match=r"dados\.idDefis"):
        reader(payload_with(bad_id))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        reader(payload_with(None))


# ---- registry ----------------------------------------------------------------------------


def test_every_fixture_of_the_module_is_read_by_its_reader() -> None:
    readers: dict[str, Callable[[Mapping[str, Any]], object]] = {
        "DEFIS.CONSDECLARACAO142": read_declaracoes,
        "DEFIS.CONSULTIMADECREC143": read_ultima_declaracao,
        "DEFIS.CONSDECREC144": read_declaracao,
    }
    for servico, reader in readers.items():
        names = fixture_names(servico)
        assert names, servico
        for name in names:
            assert reader(official_payload(name)) is not None, name


def test_the_module_registers_its_three_services() -> None:
    assert {typed.key: typed.request for typed in TYPED_SERVICES} == {
        "defis.declaracoes": None,
        "defis.ultima_declaracao": ConsultarUltimaDeclaracao,
        "defis.declaracao": ConsultarDeclaracao,
    }
    assert {typed.key: typed.read for typed in TYPED_SERVICES} == {
        "defis.declaracoes": read_declaracoes,
        "defis.ultima_declaracao": read_ultima_declaracao,
        "defis.declaracao": read_declaracao,
    }
