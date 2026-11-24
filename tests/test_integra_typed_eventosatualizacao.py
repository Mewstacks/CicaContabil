"""EVENTOSATUALIZACAO 131 a 134: typed request and reader from the official pages.

Fixtures: tests/fixtures/integra/serpro/EVENTOSATUALIZACAO.*.json, from the official examples.
"""

from __future__ import annotations

import copy
from datetime import date
from typing import Any

import pytest

from apps.integra.errors import IntegraPayloadError, IntegraRequestError
from apps.integra.typed.eventosatualizacao import (
    EVENTO_CAIXA_POSTAL,
    EVENTO_DCTFWEB,
    EVENTO_PAGAMENTOS,
    TYPED_SERVICES,
    ObterEventos,
    SolicitarEventos,
    read_eventos,
    read_solicitacao,
)
from integra_fixtures import official_dados, official_payload, payload_with

PROTOCOLO_PF = "a65f3455-fa91-419b-b0ad-c4ac50695abf"
PROTOCOLO_PJ = "q90n3455-fa91-419c-c0ad-a4ms50215acl"


def test_the_known_event_codes_are_constants() -> None:
    assert (EVENTO_DCTFWEB, EVENTO_CAIXA_POSTAL, EVENTO_PAGAMENTOS) == (
        "E0301",
        "E0601",
        "E0701",
    )


def test_the_request_of_the_official_examples_carries_only_the_event_and_the_protocol() -> None:
    # The list of CPFs/CNPJs goes in the `contribuinte` of the envelope, never in `dados`.
    assert SolicitarEventos(evento=EVENTO_DCTFWEB).to_dados() == {"evento": "E0301"}
    assert ObterEventos(protocolo=PROTOCOLO_PF, evento="E0301").to_dados() == {
        "protocolo": PROTOCOLO_PF,
        "evento": "E0301",
    }
    assert ObterEventos(protocolo=PROTOCOLO_PJ, evento=EVENTO_DCTFWEB).to_dados() == {
        "protocolo": PROTOCOLO_PJ,
        "evento": "E0301",
    }


@pytest.mark.parametrize("evento", ["", "e0301", "E301", "E03011", "X0301", "E03 1"])
def test_an_event_code_out_of_the_pattern_is_refused(evento: str) -> None:
    with pytest.raises(IntegraRequestError):
        SolicitarEventos(evento=evento)


@pytest.mark.parametrize(
    "protocolo", ["", "a65f3455", "a65f3455-fa91-419b-b0ad-c4ac50695ab", "x" * 37]
)
def test_a_protocol_that_is_not_36_characters_is_refused(protocolo: str) -> None:
    with pytest.raises(IntegraRequestError):
        ObterEventos(protocolo=protocolo, evento="E0301")


def test_a_protocol_with_forbidden_characters_is_refused() -> None:
    with pytest.raises(IntegraRequestError):
        ObterEventos(protocolo="a65f3455 fa91 419b b0ad c4ac50695abf", evento="E0301")


def test_the_required_fields_have_no_default() -> None:
    kwargs: dict[str, Any] = {"evento": "E0301"}
    with pytest.raises(TypeError):
        ObterEventos(**kwargs)
    with pytest.raises(TypeError):
        SolicitarEventos()


def test_the_protocol_of_a_pf_request_is_read_with_its_waiting_times() -> None:
    protocolo = read_solicitacao(official_payload("EVENTOSATUALIZACAO.SOLICEVENTOSPF131.protocolo"))

    assert protocolo.protocolo == PROTOCOLO_PF
    assert protocolo.tempo_espera_medio_ms == 5000
    assert protocolo.tempo_limite_min == 20


def test_the_protocol_of_a_pj_request_is_read_by_the_same_reader() -> None:
    protocolo = read_solicitacao(official_payload("EVENTOSATUALIZACAO.SOLICEVENTOSPJ132.protocolo"))

    assert protocolo.protocolo == PROTOCOLO_PJ
    assert protocolo.tempo_espera_medio_ms == 3000
    assert protocolo.tempo_limite_min == 20


def test_the_events_of_four_cpfs_keep_the_date_the_empty_cell_and_the_missing_power() -> None:
    result = read_eventos(official_payload("EVENTOSATUALIZACAO.OBTEREVENTOSPF133.eventos"))

    assert result.em_processamento is False
    assert [line.ni for line in result.linhas] == [
        "00000000000",
        "11111111111",
        "22222222222",
        "33333333333",
    ]
    assert [line.data for line in result.linhas] == [None, date(2023, 4, 7), date(2023, 4, 8), None]
    assert [line.sem_procuracao for line in result.linhas] == [False, False, False, True]
    assert [message.codigo for message in result.mensagens] == [
        "[Sucesso-EVENTOSATUALIZACAO]",
        "[Aviso-EVENTOSATUALIZACAO-001]",
    ]


def test_the_events_of_four_cnpjs_are_read_by_the_same_reader() -> None:
    result = read_eventos(official_payload("EVENTOSATUALIZACAO.OBTEREVENTOSPJ134.eventos"))

    assert [line.ni for line in result.linhas][1] == "11111111111111"
    assert [line.data for line in result.linhas] == [
        None,
        date(2023, 3, 27),
        date(2023, 3, 28),
        None,
    ]
    assert result.linhas[3].sem_procuracao is True
    assert result.linhas[0].sem_procuracao is False


def test_a_202_is_a_request_still_in_process_and_not_an_error() -> None:
    result = read_eventos(official_payload("EVENTOSATUALIZACAO.OBTEREVENTOSPF133.em_processamento"))

    assert result.em_processamento is True
    assert result.linhas == ()
    assert result.mensagens[0].codigo == "[Aviso-EVENTOSATUALIZACAO-007]"


def test_a_202_with_an_empty_object_is_also_in_process() -> None:
    payload = payload_with(None, status=202)
    payload["dados"] = ""
    assert read_eventos(payload).em_processamento is True


def test_the_matrix_may_also_arrive_inside_the_elementos_field_of_the_documented_object() -> None:
    rows = official_dados("EVENTOSATUALIZACAO.OBTEREVENTOSPF133.eventos")

    wrapped = read_eventos(payload_with({"elementos": rows}))
    bare = read_eventos(payload_with(rows))

    assert wrapped.linhas == bare.linhas
    assert len(wrapped.linhas) == 4


def test_a_cell_with_a_capital_x_is_also_a_missing_power() -> None:
    result = read_eventos(payload_with([["11111111111", "X"]]))

    assert result.linhas[0].sem_procuracao is True
    assert result.linhas[0].data is None


def test_an_alphanumeric_cnpj_is_accepted_as_the_identifier_of_a_row() -> None:
    result = read_eventos(payload_with([["YV9IAOAXNTRV65", "260115"]]))

    assert result.linhas[0].ni == "YV9IAOAXNTRV65"
    assert result.linhas[0].data == date(2026, 1, 15)


def test_a_failed_answer_is_not_presented_as_events_or_as_a_protocol() -> None:
    good = official_dados("EVENTOSATUALIZACAO.OBTEREVENTOSPF133.eventos")
    with pytest.raises(IntegraPayloadError, match="status 429"):
        read_eventos(payload_with(good, status=429))
    with pytest.raises(IntegraPayloadError, match="status 400"):
        read_eventos(payload_with(good, status=400))
    protocolo = official_dados("EVENTOSATUALIZACAO.SOLICEVENTOSPF131.protocolo")
    with pytest.raises(IntegraPayloadError, match="status 500"):
        read_solicitacao(payload_with(protocolo, status=500))
    # only the retrieval is asynchronous: the request of a batch never answers 202
    with pytest.raises(IntegraPayloadError, match="status 202"):
        read_solicitacao(payload_with(protocolo, status=202))


@pytest.mark.parametrize(
    "row",
    [
        ["111", "230407"],  # not a CPF/CNPJ size
        ["11111111111", "230407", "extra"],  # three columns
        ["11111111111"],  # one column
        ["11111111111", "231340"],  # month 13
        ["11111111111", "23-04-07"],  # not AAMMDD
        ["11111111111", "y"],
        ["11111111111", None],
        [11111111111, "230407"],
        "11111111111",
    ],
)
def test_a_row_out_of_the_documented_shape_is_refused_with_the_field_path(row: Any) -> None:
    with pytest.raises(IntegraPayloadError, match=r"dados\.elementos"):
        read_eventos(payload_with([row]))


def test_a_matrix_over_the_documented_limit_of_1000_rows_is_refused() -> None:
    rows = [[f"{index:011d}", ""] for index in range(1001)]
    with pytest.raises(IntegraPayloadError, match=r"dados\.elementos"):
        read_eventos(payload_with(rows))
    assert len(read_eventos(payload_with(rows[:1000])).linhas) == 1000


def test_a_matrix_of_the_wrong_kind_is_refused() -> None:
    with pytest.raises(IntegraPayloadError, match=r"dados\.elementos"):
        read_eventos(payload_with({"elementos": "x"}))
    with pytest.raises(IntegraPayloadError, match=r"dados\.elementos.*campo obrigatório ausente"):
        read_eventos(payload_with({}))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_eventos(payload_with(5))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_eventos({"status": 200, "mensagens": [], "dados": ""})


def test_a_protocol_answer_without_its_fields_or_with_the_wrong_type_is_refused() -> None:
    good = official_dados("EVENTOSATUALIZACAO.SOLICEVENTOSPF131.protocolo")
    missing = copy.deepcopy(good)
    del missing["protocolo"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.protocolo.*campo obrigatório ausente"):
        read_solicitacao(payload_with(missing))
    wrong = copy.deepcopy(good)
    wrong["TempoEsperaMedioEmMs"] = "rápido"
    with pytest.raises(IntegraPayloadError, match=r"dados\.TempoEsperaMedioEmMs"):
        read_solicitacao(payload_with(wrong))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_solicitacao(payload_with([good]))


def test_the_error_of_a_bad_row_never_echoes_the_received_value() -> None:
    with pytest.raises(IntegraPayloadError) as error:
        read_eventos(payload_with([["11111111111", "segredo-que-nao-deve-aparecer"]]))
    assert "segredo" not in str(error.value)


def test_the_module_registers_its_four_services() -> None:
    assert {typed.key: typed.request for typed in TYPED_SERVICES} == {
        "eventosatualizacao.solicitar_pf": SolicitarEventos,
        "eventosatualizacao.solicitar_pj": SolicitarEventos,
        "eventosatualizacao.obter_pf": ObterEventos,
        "eventosatualizacao.obter_pj": ObterEventos,
    }
    assert {typed.key: typed.read for typed in TYPED_SERVICES} == {
        "eventosatualizacao.solicitar_pf": read_solicitacao,
        "eventosatualizacao.solicitar_pj": read_solicitacao,
        "eventosatualizacao.obter_pf": read_eventos,
        "eventosatualizacao.obter_pj": read_eventos,
    }
