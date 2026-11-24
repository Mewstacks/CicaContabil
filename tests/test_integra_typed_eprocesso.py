"""EPROCESSO 271 (processos por interessado): typed reader from the official pages.

Fixtures: tests/fixtures/integra/serpro/EPROCESSO.*.json, from the official examples.
"""

from __future__ import annotations

import copy
from datetime import date

import pytest

from apps.integra.errors import IntegraPayloadError
from apps.integra.typed.eprocesso import TYPED_SERVICES, read_processos
from integra_fixtures import official_dados, official_payload, payload_with


def test_the_official_example_lists_the_processes_in_the_order_received() -> None:
    processos = read_processos(official_payload("EPROCESSO.CONSPROCPORINTER271.processos"))

    assert [processo.numero_do_processo for processo in processos] == [
        "00000000000000001",
        "00000000000000002",
    ]
    first = processos[0]
    assert first.relacao_do_interessado_com_o_processo == "INTERESSADO"
    assert first.data_de_protocolo == date(2020, 1, 1)
    assert (first.tipo_do_processo, first.subtipo_do_processo) == ("AÇÃO FISCAL", "MEMORIAL")
    assert (first.localizacao, first.situacao) == ("DRJ", "CONFIRMADO")
    assert first.ultimo_encaminhamento_externo is None
    assert processos[1].localizacao == "CARF"


def test_the_status_may_arrive_as_text_as_in_the_official_example() -> None:
    payload = official_payload("EPROCESSO.CONSPROCPORINTER271.processos")
    assert payload["status"] == "200"

    as_number = dict(payload, status=200)

    assert read_processos(payload) == read_processos(as_number)


@pytest.mark.parametrize("status", ["500", 500, "404"])
def test_a_failed_status_is_refused_in_both_spellings(status: str | int) -> None:
    payload = official_payload("EPROCESSO.CONSPROCPORINTER271.processos")
    with pytest.raises(IntegraPayloadError, match=f"status {status}"):
        read_processos(dict(payload, status=status))


@pytest.mark.parametrize("status", ["ok", "2000", "", " ", True, None, 200.5, "20 0"])
def test_a_status_that_is_not_a_three_digit_code_is_refused(status: object) -> None:
    payload = official_payload("EPROCESSO.CONSPROCPORINTER271.processos")
    with pytest.raises(IntegraPayloadError, match="status"):
        read_processos(dict(payload, status=status))


def test_a_taxpayer_without_processes_gets_an_empty_list() -> None:
    assert read_processos(official_payload("EPROCESSO.CONSPROCPORINTER271.sem_processos")) == ()
    assert read_processos(payload_with([])) == ()


def test_the_optional_fields_may_be_absent_or_null_but_the_number_is_required() -> None:
    dados = official_dados("EPROCESSO.CONSPROCPORINTER271.processos")
    del dados[0]["situacao"]
    dados[0]["ultimoEncaminhamentoExterno"] = "DRF SAO PAULO"
    dados[1]["dataDeProtocolo"] = None

    processos = read_processos(payload_with(dados))

    assert processos[0].situacao is None
    assert processos[0].ultimo_encaminhamento_externo == "DRF SAO PAULO"
    assert processos[1].data_de_protocolo is None
    del dados[1]["numeroDoProcesso"]
    with pytest.raises(IntegraPayloadError, match=r"dados\[1\]\.numeroDoProcesso"):
        read_processos(payload_with(dados))


def test_a_broken_answer_is_refused_with_the_field_path() -> None:
    good = official_dados("EPROCESSO.CONSPROCPORINTER271.processos")
    with pytest.raises(IntegraPayloadError, match="uma lista"):
        read_processos(payload_with(good[0]))
    with pytest.raises(IntegraPayloadError, match="uma lista"):
        read_processos({"status": 200, "mensagens": [], "dados": ""})
    bad_date = copy.deepcopy(good)
    bad_date[1]["dataDeProtocolo"] = "2020-01-01"
    with pytest.raises(IntegraPayloadError, match=r"dados\[1\]\.dataDeProtocolo"):
        read_processos(payload_with(bad_date))
    impossible = copy.deepcopy(good)
    impossible[0]["dataDeProtocolo"] = "31/02/2020"
    with pytest.raises(IntegraPayloadError, match=r"dados\[0\]\.dataDeProtocolo"):
        read_processos(payload_with(impossible))
    wrong = copy.deepcopy(good)
    wrong[0]["localizacao"] = 7
    with pytest.raises(IntegraPayloadError, match=r"dados\[0\]\.localizacao"):
        read_processos(payload_with(wrong))
    hole = [good[0], None]
    with pytest.raises(IntegraPayloadError, match=r"dados\[1\]"):
        read_processos(payload_with(hole))


def test_the_service_has_no_request_because_dados_goes_empty() -> None:
    (typed,) = TYPED_SERVICES
    assert typed.key == "eprocesso.processos"
    assert typed.request is None
    assert typed.read is read_processos
