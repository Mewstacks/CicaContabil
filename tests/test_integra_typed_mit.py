"""MIT 315 to 317 (consultas): typed requests and readers from the official pages.

Fixtures: tests/fixtures/integra/serpro/MIT.*.json. `encerrada`, `sem_movimento` and
`apuracoes` are the official examples; `em_edicao`, `com_debitos` and `com_suspensao` are built
from the tables of the pages (the notes of each file say so).
"""

from __future__ import annotations

import copy
from collections.abc import Callable, Mapping
from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from apps.integra.errors import IntegraPayloadError, IntegraRequestError
from apps.integra.typed.mit import (
    TYPED_SERVICES,
    ConsultarApuracao,
    ConsultarSituacaoEncerramento,
    ListarApuracoes,
    read_apuracao,
    read_apuracoes,
    read_situacao_encerramento,
)
from integra_fixtures import fixture_names, official_dados, official_payload, payload_with

# ---- requests ----------------------------------------------------------------------------


def test_the_requests_of_the_official_examples_are_built_field_by_field() -> None:
    assert ConsultarSituacaoEncerramento(
        protocolo_encerramento="2fc4NTscrGXWTl4xbCX9rw=="
    ).to_dados() == {"protocoloEncerramento": "2fc4NTscrGXWTl4xbCX9rw=="}
    assert ConsultarApuracao(id_apuracao=0).to_dados() == {"idApuracao": 0}
    assert ListarApuracoes(ano_apuracao=2025, mes_apuracao=2, situacao_apuracao=3).to_dados() == {
        "mesApuracao": 2,
        "anoApuracao": 2025,
        "situacaoApuracao": 3,
    }
    assert ListarApuracoes(ano_apuracao=2025).to_dados() == {"anoApuracao": 2025}


@pytest.mark.parametrize("protocol", ["", " ", "com espaço", "x" * 101, "a;b"])
def test_the_closing_protocol_is_refused_when_it_is_empty_or_has_odd_characters(
    protocol: str,
) -> None:
    with pytest.raises(IntegraRequestError):
        ConsultarSituacaoEncerramento(protocolo_encerramento=protocol)


@pytest.mark.parametrize("value", [-1, True, "1", 1.5])
def test_the_id_of_the_apuracao_must_be_a_non_negative_integer(value: Any) -> None:
    with pytest.raises(IntegraRequestError):
        ConsultarApuracao(id_apuracao=value)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"ano_apuracao": 25},
        {"ano_apuracao": 2101},
        {"ano_apuracao": 2025, "mes_apuracao": 0},
        {"ano_apuracao": 2025, "mes_apuracao": 13},
        {"ano_apuracao": 2025, "situacao_apuracao": 0},
        {"ano_apuracao": 2025, "situacao_apuracao": 5},
        {"ano_apuracao": "2025"},
    ],
)
def test_an_invalid_listing_request_is_refused_before_any_call(kwargs: dict[str, Any]) -> None:
    with pytest.raises(IntegraRequestError):
        ListarApuracoes(**kwargs)


def test_the_year_of_the_listing_is_mandatory() -> None:
    request: Any = ListarApuracoes
    with pytest.raises(TypeError):
        request(mes_apuracao=2)


# ---- 315: closing status -----------------------------------------------------------------


def test_a_closed_apuracao_has_its_status_and_closing_date() -> None:
    status = read_situacao_encerramento(official_payload("MIT.SITUACAOENC315.encerrada"))

    assert status.id_apuracao == 0
    assert status.situacao_apuracao == 3
    assert status.texto_situacao == "ENCERRADA"
    assert status.avisos_dctf == ()
    assert status.data_encerramento == date(2025, 3, 5)


def test_an_apuracao_refused_by_the_dctfweb_carries_the_warnings() -> None:
    status = read_situacao_encerramento(official_payload("MIT.SITUACAOENC315.em_edicao"))

    assert status.situacao_apuracao == 2
    assert status.texto_situacao == "EM_EDICAO"
    assert status.avisos_dctf == ("Aviso fictício da DCTFWeb.",)
    assert status.data_encerramento is None


def test_a_closing_still_in_progress_has_no_date_yet() -> None:
    dados = {"idApuracao": 7, "situacaoApuracao": 4, "textoSituacao": "ENCERRAMENTO_EM_CURSO"}

    status = read_situacao_encerramento(payload_with(dados))

    assert (status.id_apuracao, status.situacao_apuracao) == (7, 4)
    assert status.data_encerramento is None
    assert status.avisos_dctf == ()


def test_a_broken_closing_status_is_refused_with_the_path_of_the_field() -> None:
    good = official_dados("MIT.SITUACAOENC315.em_edicao")
    with pytest.raises(IntegraPayloadError, match="status 500"):
        read_situacao_encerramento(payload_with(good, status=500))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_situacao_encerramento(payload_with([good]))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_situacao_encerramento(payload_with(None))
    missing = copy.deepcopy(good)
    del missing["situacaoApuracao"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.situacaoApuracao"):
        read_situacao_encerramento(payload_with(missing))
    warnings_as_text = copy.deepcopy(good)
    warnings_as_text["avisosDctf"] = "um aviso"
    with pytest.raises(IntegraPayloadError, match=r"dados\.avisosDctf deve ser uma lista"):
        read_situacao_encerramento(payload_with(warnings_as_text))
    warning_as_number = copy.deepcopy(good)
    warning_as_number["avisosDctf"] = [1]
    with pytest.raises(IntegraPayloadError, match=r"dados\.avisosDctf\[0\]"):
        read_situacao_encerramento(payload_with(warning_as_number))
    bad_date = copy.deepcopy(good)
    bad_date["dataEncerramento"] = "ontem"
    with pytest.raises(IntegraPayloadError, match=r"dados\.dataEncerramento"):
        read_situacao_encerramento(payload_with(bad_date))


# ---- 316: apuracao -----------------------------------------------------------------------


def test_an_apuracao_without_movement_has_only_the_initial_data() -> None:
    answer = read_apuracao(official_payload("MIT.CONSAPURACAO316.sem_movimento"))

    assert (answer.situacao_apuracao, answer.texto_situacao) == (3, "ENCERRADA")
    apuracao = answer.dados_apuracao_mit
    assert apuracao is not None
    assert (apuracao.periodo_apuracao.mes_apuracao, apuracao.periodo_apuracao.ano_apuracao) == (
        2,
        2025,
    )
    assert apuracao.lista_eventos_especiais == ()
    assert apuracao.dados_iniciais.sem_movimento is True
    assert apuracao.dados_iniciais.qualificacao_pj == 1
    assert apuracao.dados_iniciais.tributacao_lucro is None
    responsible = apuracao.dados_iniciais.responsavel_apuracao
    assert responsible.cpf_responsavel == "00000000000"
    assert responsible.tel_responsavel is None
    assert responsible.registro_crc is None
    assert apuracao.debitos is None
    assert apuracao.lista_suspensoes == ()
    assert apuracao.transmissao_imediata is False


def test_an_apuracao_with_movement_carries_events_responsible_and_debits_by_group() -> None:
    answer = read_apuracao(official_payload("MIT.CONSAPURACAO316.com_debitos"))

    apuracao = answer.dados_apuracao_mit
    assert apuracao is not None
    events = apuracao.lista_eventos_especiais
    assert [(e.id_evento, e.dia_evento, e.tipo_evento) for e in events] == [(1, 13, 4)]
    initial = apuracao.dados_iniciais
    assert initial.sem_movimento is False
    assert (initial.tributacao_lucro, initial.variacoes_monetarias, initial.regime_pis_cofins) == (
        1,
        2,
        1,
    )
    responsible = initial.responsavel_apuracao
    assert responsible.tel_responsavel is not None
    assert (responsible.tel_responsavel.ddd, responsible.tel_responsavel.num_telefone) == (
        "31",
        "999999999",
    )
    assert responsible.email_responsavel == "responsavel@mail.com"
    assert responsible.registro_crc is not None
    assert (responsible.registro_crc.uf_registro, responsible.registro_crc.num_registro) == (
        "SP",
        "SP123456",
    )
    debits = apuracao.debitos
    assert debits is not None
    assert debits.balanco_lucro_real is True
    assert debits.csll is None
    assert debits.irpj is not None
    before, after = debits.irpj.lista_debitos[0], debits.irpj.lista_debitos_apos_evento[0]
    assert (before.id_debito, before.id_evento_debito, before.codigo_debito) == (1, 1, "022012")
    assert (before.ano_postergado, before.trim_postergado, before.ano_debito) == (2020, 2, 2024)
    assert before.cnpj_scp == "12345678000195"
    assert before.valor_debito == Decimal("777.55")
    assert after.pa_debito == 2
    assert after.valor_debito == Decimal("100.1")
    assert debits.ipi is not None
    assert debits.ipi.lista_debitos[0].cnpj_estabelecimento == "000100"
    assert debits.ipi.lista_debitos[0].valor_debito == Decimal(50)
    assert debits.ipi.lista_debitos_apos_evento == ()
    assert debits.pis_pasep is not None
    assert debits.pis_pasep.lista_debitos[0].codigo_municipio_ouro == "3550308"
    assert debits.ret_pagamento_unificado is not None
    assert debits.ret_pagamento_unificado.lista_debitos[0].cnpj_incorporacao == "000100"
    assert debits.ret_pagamento_unificado.lista_debitos[0].valor_debito == Decimal(1000)


def test_a_judicial_suspension_lists_its_suspended_debits() -> None:
    answer = read_apuracao(official_payload("MIT.CONSAPURACAO316.com_suspensao"))

    apuracao = answer.dados_apuracao_mit
    assert apuracao is not None
    assert apuracao.debitos is not None
    assert apuracao.debitos.csll is not None
    assert apuracao.debitos.csll.lista_debitos[0].valor_debito == Decimal("1500.5")
    (suspension,) = apuracao.lista_suspensoes
    assert (suspension.tipo_suspensao, suspension.motivo_suspensao) == (2, 1)
    assert suspension.com_deposito is False
    assert suspension.processo_terceiro is False
    assert suspension.numero_processo == "98765431220251017777"
    assert suspension.data_decisao == date(2024, 9, 20)
    assert (suspension.vara_judiciaria, suspension.codigo_municipio_sj) == (1, "5002704")
    (suspended,) = suspension.lista_debitos_suspensos
    assert (suspended.id_debito_suspenso, suspended.valor_suspenso) == (1, Decimal(1000))


def test_an_apuracao_that_is_still_being_edited_may_come_without_its_data() -> None:
    answer = read_apuracao(payload_with({"situacaoApuracao": 2, "textoSituacao": "EM_EDICAO"}))

    assert answer.situacao_apuracao == 2
    assert answer.dados_apuracao_mit is None


def test_a_broken_apuracao_is_refused_with_the_path_of_the_field() -> None:
    good = official_dados("MIT.CONSAPURACAO316.com_debitos")
    with pytest.raises(IntegraPayloadError, match="status 404"):
        read_apuracao(payload_with(good, status=404))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_apuracao(payload_with([good]))
    as_list = copy.deepcopy(good)
    as_list["dadosApuracaoMit"] = [good["dadosApuracaoMit"]]
    with pytest.raises(IntegraPayloadError, match=r"dados\.dadosApuracaoMit deve ser um objeto"):
        read_apuracao(payload_with(as_list))
    no_period = copy.deepcopy(good)
    del no_period["dadosApuracaoMit"]["PeriodoApuracao"]
    with pytest.raises(IntegraPayloadError, match=r"dadosApuracaoMit\.PeriodoApuracao"):
        read_apuracao(payload_with(no_period))
    no_year = copy.deepcopy(good)
    del no_year["dadosApuracaoMit"]["PeriodoApuracao"]["AnoApuracao"]
    with pytest.raises(IntegraPayloadError, match=r"PeriodoApuracao\.AnoApuracao"):
        read_apuracao(payload_with(no_year))
    bad_flag = copy.deepcopy(good)
    bad_flag["dadosApuracaoMit"]["DadosIniciais"]["SemMovimento"] = "talvez"
    with pytest.raises(IntegraPayloadError, match=r"DadosIniciais\.SemMovimento"):
        read_apuracao(payload_with(bad_flag))
    bad_value = copy.deepcopy(good)
    bad_value["dadosApuracaoMit"]["Debitos"]["Irpj"]["ListaDebitos"][0]["ValorDebito"] = "caro"
    with pytest.raises(IntegraPayloadError, match=r"Irpj\.ListaDebitos\[0\]\.ValorDebito"):
        read_apuracao(payload_with(bad_value))
    no_code = copy.deepcopy(good)
    del no_code["dadosApuracaoMit"]["Debitos"]["Ipi"]["ListaDebitos"][0]["CodigoDebito"]
    with pytest.raises(IntegraPayloadError, match=r"Ipi\.ListaDebitos\[0\]\.CodigoDebito"):
        read_apuracao(payload_with(no_code))
    debits_as_list = copy.deepcopy(good)
    debits_as_list["dadosApuracaoMit"]["Debitos"] = []
    with pytest.raises(IntegraPayloadError, match=r"dadosApuracaoMit\.Debitos deve ser um objeto"):
        read_apuracao(payload_with(debits_as_list))
    bad_decision = official_dados("MIT.CONSAPURACAO316.com_suspensao")
    bad_decision["dadosApuracaoMit"]["ListaSuspensoes"][0]["DataDecisao"] = 20241399
    with pytest.raises(IntegraPayloadError, match=r"ListaSuspensoes\[0\]\.DataDecisao"):
        read_apuracao(payload_with(bad_decision))


# ---- 317: list of apuracoes --------------------------------------------------------------


def test_the_apuracoes_of_a_period_are_listed_with_status_and_total() -> None:
    answer = read_apuracoes(official_payload("MIT.LISTAAPURACOES317.apuracoes"))

    assert [item.id_apuracao for item in answer.apuracoes] == [0, 1]
    first, second = answer.apuracoes
    assert first.periodo_apuracao == 202512
    assert first.situacao == 3
    assert first.data_encerramento == date(2025, 2, 18)
    assert first.evento_especial is False
    assert first.valor_total_apurado == Decimal("1000.0")
    assert second.data_encerramento == date(2025, 2, 19)
    assert second.valor_total_apurado == Decimal("1500")


def test_an_apuracao_not_yet_closed_has_no_closing_date_or_total() -> None:
    dados = {"Apuracoes": [{"periodoApuracao": "202502", "idApuracao": 5, "situacao": 2}]}

    (item,) = read_apuracoes(payload_with(dados)).apuracoes

    assert item.periodo_apuracao == 202502
    assert item.data_encerramento is None
    assert item.evento_especial is None
    assert item.valor_total_apurado is None


def test_a_broken_list_of_apuracoes_is_refused_with_the_path_of_the_field() -> None:
    good = official_dados("MIT.LISTAAPURACOES317.apuracoes")
    with pytest.raises(IntegraPayloadError, match="status 500"):
        read_apuracoes(payload_with(good, status=500))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_apuracoes(payload_with(good["Apuracoes"]))
    not_a_list = copy.deepcopy(good)
    not_a_list["Apuracoes"] = good["Apuracoes"][0]
    with pytest.raises(IntegraPayloadError, match=r"dados\.Apuracoes deve ser uma lista"):
        read_apuracoes(payload_with(not_a_list))
    missing = copy.deepcopy(good)
    del missing["Apuracoes"][1]["idApuracao"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.Apuracoes\[1\]\.idApuracao"):
        read_apuracoes(payload_with(missing))
    bad_period = copy.deepcopy(good)
    bad_period["Apuracoes"][0]["periodoApuracao"] = 202513
    with pytest.raises(IntegraPayloadError, match=r"dados\.Apuracoes\[0\]\.periodoApuracao"):
        read_apuracoes(payload_with(bad_period))
    bad_total = copy.deepcopy(good)
    bad_total["Apuracoes"][0]["valorTotalApurado"] = "mil"
    with pytest.raises(IntegraPayloadError, match=r"dados\.Apuracoes\[0\]\.valorTotalApurado"):
        read_apuracoes(payload_with(bad_total))


# ---- registry ----------------------------------------------------------------------------


def test_every_fixture_of_the_module_is_read_by_its_reader() -> None:
    readers: dict[str, Callable[[Mapping[str, Any]], object]] = {
        "MIT.SITUACAOENC315": read_situacao_encerramento,
        "MIT.CONSAPURACAO316": read_apuracao,
        "MIT.LISTAAPURACOES317": read_apuracoes,
    }
    for servico, reader in readers.items():
        names = fixture_names(servico)
        assert names, servico
        for name in names:
            assert reader(official_payload(name)) is not None, name


def test_the_module_registers_its_three_services() -> None:
    assert {typed.key: typed.request for typed in TYPED_SERVICES} == {
        "mit.situacao_encerramento": ConsultarSituacaoEncerramento,
        "mit.apuracao": ConsultarApuracao,
        "mit.apuracoes": ListarApuracoes,
    }
    assert {typed.key: typed.read for typed in TYPED_SERVICES} == {
        "mit.situacao_encerramento": read_situacao_encerramento,
        "mit.apuracao": read_apuracao,
        "mit.apuracoes": read_apuracoes,
    }
