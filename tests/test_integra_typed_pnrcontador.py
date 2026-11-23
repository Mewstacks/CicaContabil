"""PNRCONTADOR 261, 263 and 265: typed request and reader from the official pages.

Fixtures: tests/fixtures/integra/serpro/PNRCONTADOR.*.json, from the official examples.
"""

from __future__ import annotations

import copy
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest

from apps.integra.errors import IntegraPayloadError, IntegraRequestError
from apps.integra.typed.pnrcontador import (
    TYPED_SERVICES,
    ConsultarRenuncias,
    ConsultarSituacaoRenuncia,
    ConsultarVinculos,
    PaginacaoVinculos,
    read_renuncias,
    read_situacao_renuncia,
    read_vinculos,
)
from integra_fixtures import official_dados, official_payload, payload_with

BRT = timezone(timedelta(hours=-3))


def test_the_vinculos_request_nests_the_paging_under_pagination() -> None:
    # The page shows `{"pagination": {"size": 50}}` and the same with `lastCnpj`; the official
    # example of the second form lacks a colon, the object built here is the intended one.
    first = ConsultarVinculos(paginacao=PaginacaoVinculos(tamanho=50))
    assert first.to_dados() == {"pagination": {"size": 50}}
    next_page = ConsultarVinculos(
        paginacao=PaginacaoVinculos(tamanho=50, ultimo_cnpj="99999999999999")
    )
    assert next_page.to_dados() == {"pagination": {"size": 50, "lastCnpj": "99999999999999"}}
    assert ConsultarVinculos(paginacao=PaginacaoVinculos(tamanho=5)).to_dados() == {
        "pagination": {"size": 5}
    }


@pytest.mark.parametrize(
    "kwargs",
    [
        {"tamanho": 0},
        {"tamanho": 51},
        {"tamanho": "10"},
        {"tamanho": True},
        {"tamanho": 10, "ultimo_cnpj": "123"},
        {"tamanho": 10, "ultimo_cnpj": "abcdefghijklmn"},
        {"tamanho": 10, "ultimo_cnpj": 99999999999999},
    ],
)
def test_an_invalid_paging_is_refused_before_any_call(kwargs: dict[str, Any]) -> None:
    with pytest.raises(IntegraRequestError):
        PaginacaoVinculos(**kwargs)


def test_the_size_of_the_page_and_the_paging_are_required() -> None:
    empty: dict[str, Any] = {}
    with pytest.raises(TypeError):
        PaginacaoVinculos(**empty)
    with pytest.raises(TypeError):
        ConsultarVinculos(**empty)


def test_the_renuncias_request_of_the_official_example_matches_field_by_field() -> None:
    request = ConsultarRenuncias(
        page=0, page_size=10, dt_inicio=date(2000, 1, 30), dt_fim=date(2000, 1, 30)
    )
    # The official example lacks a comma between dtInicio and dtFim; this is the intended object.
    assert request.to_dados() == {
        "page": 0,
        "pageSize": 10,
        "dtInicio": "2000-01-30",
        "dtFim": "2000-01-30",
    }
    assert ConsultarRenuncias().to_dados() == {}
    assert ConsultarRenuncias(page=2, page_size=50).to_dados() == {"page": 2, "pageSize": 50}


@pytest.mark.parametrize(
    "kwargs",
    [
        {"page": -1},
        {"page_size": 0},
        {"page_size": 51},
        {"page": "0"},
        {"dt_inicio": date(2000, 1, 30)},
        {"dt_fim": date(2000, 1, 30)},
        {"dt_inicio": date(2000, 2, 1), "dt_fim": date(2000, 1, 30)},
        {"dt_inicio": "2000-01-30", "dt_fim": "2000-01-30"},
        {"dt_inicio": datetime(2000, 1, 30), "dt_fim": datetime(2000, 1, 30)},
    ],
)
def test_an_invalid_renuncias_request_is_refused_before_any_call(kwargs: dict[str, Any]) -> None:
    with pytest.raises(IntegraRequestError):
        ConsultarRenuncias(**kwargs)


def test_the_situacao_request_carries_the_id_of_the_solicitation() -> None:
    # The official example lacks a colon after idSolicitacao; this is the intended object.
    request = ConsultarSituacaoRenuncia(id_solicitacao="PNRCONTADOR-20250212-af81730aeb29c9fdac15")
    assert request.to_dados() == {"idSolicitacao": "PNRCONTADOR-20250212-af81730aeb29c9fdac15"}


@pytest.mark.parametrize("identifier", ["", "a b", "x" * 65, "PNR;DROP", 'a"b'])
def test_an_invalid_solicitation_id_is_refused(identifier: str) -> None:
    with pytest.raises(IntegraRequestError):
        ConsultarSituacaoRenuncia(id_solicitacao=identifier)


def test_a_page_of_vinculos_is_read_with_the_cursor_and_the_totals() -> None:
    page = read_vinculos(official_payload("PNRCONTADOR.CONSVINCULOS261.pagina"))

    assert len(page.empresas) == 5
    assert (page.total_na_pagina, page.total_na_base, page.ultimo_cnpj) == (
        5,
        16,
        "99999999999999",
    )
    first = page.empresas[0]
    assert first.cnpj == "99999999999999"
    assert first.tipo_estabelecimento == "Matriz"
    assert (first.uf, first.codigo_municipio, first.nome_municipio) == ("BA", "3287", None)
    assert first.situacao_cadastral is not None
    assert (first.situacao_cadastral.codigo, first.situacao_cadastral.descricao) == ("02", "Ativa")
    assert [empresa.uf for empresa in page.empresas] == ["BA", "AP", "AP", "AM", "AM"]
    assert page.empresas[1].codigo_municipio == "0667"


def test_the_last_page_has_no_cursor_and_a_missing_description_is_none() -> None:
    dados = official_dados("PNRCONTADOR.CONSVINCULOS261.pagina")
    del dados["lastCnpj"]
    dados["cnpjs"][0]["situacaoCadastral"]["descricao"] = None
    dados["cnpjs"][1]["situacaoCadastral"] = None

    page = read_vinculos(payload_with(dados))

    assert page.ultimo_cnpj is None
    assert page.empresas[0].situacao_cadastral is not None
    assert page.empresas[0].situacao_cadastral.descricao is None
    assert page.empresas[1].situacao_cadastral is None
    assert read_vinculos(payload_with({})).empresas == ()


def test_a_broken_vinculos_answer_is_refused_with_the_field_path() -> None:
    good = official_dados("PNRCONTADOR.CONSVINCULOS261.pagina")
    with pytest.raises(IntegraPayloadError, match="status 403"):
        read_vinculos(payload_with(good, status=403))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_vinculos(payload_with(good["cnpjs"]))
    with pytest.raises(IntegraPayloadError, match=r"dados\.cnpjs.*uma lista"):
        read_vinculos(payload_with({"cnpjs": {"cnpj": "1"}}))
    missing = copy.deepcopy(good)
    del missing["cnpjs"][2]["cnpj"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.cnpjs\[2\]\.cnpj"):
        read_vinculos(payload_with(missing))
    wrong = copy.deepcopy(good)
    wrong["totalInThePage"] = "muitos"
    with pytest.raises(IntegraPayloadError, match=r"dados\.totalInThePage"):
        read_vinculos(payload_with(wrong))
    hole = copy.deepcopy(good)
    hole["cnpjs"][0] = None
    with pytest.raises(IntegraPayloadError, match=r"dados\.cnpjs\[0\]"):
        read_vinculos(payload_with(hole))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_vinculos({"status": 200, "mensagens": [], "dados": ""})


def test_a_page_of_renuncias_is_read_with_the_spring_paging_objects() -> None:
    page = read_renuncias(official_payload("PNRCONTADOR.CONSRENUNCIA263.pagina"))

    assert len(page.conteudo) == 1
    renuncia = page.conteudo[0]
    assert renuncia.id == 1234
    assert renuncia.cnpj_renunciada == "99999999999999"
    # 1739242800000 ms since the epoch is midnight in Brasília on 2025-02-11
    assert renuncia.data_renuncia == datetime(2025, 2, 11, tzinfo=BRT)
    assert (renuncia.cnpj_solicitante, renuncia.cnpj_renunciante) == (None, None)
    assert (renuncia.cpf_solicitante, renuncia.cpf_renunciante) == ("00000000011", "00000000011")
    assert renuncia.cpf_logado == "00000000011"
    assert (page.vazia, page.primeira, page.ultima) == (False, True, False)
    assert (page.numero, page.numero_de_elementos, page.tamanho) == (0, 1, 10)
    assert (page.total_de_elementos, page.total_de_paginas) == (1, 1)
    assert page.paginacao is not None
    assert (page.paginacao.numero_da_pagina, page.paginacao.tamanho_da_pagina) == (0, 10)
    assert (page.paginacao.deslocamento, page.paginacao.paginada) == (0, True)
    assert page.paginacao.sem_paginacao is False
    assert page.paginacao.ordenacao is not None
    assert page.paginacao.ordenacao.ordenada is False
    assert page.ordenacao is not None
    assert (page.ordenacao.ordenada, page.ordenacao.nao_ordenada, page.ordenacao.vazia) == (
        False,
        True,
        True,
    )


def test_a_page_without_renuncias_is_empty() -> None:
    page = read_renuncias(official_payload("PNRCONTADOR.CONSRENUNCIA263.vazia"))

    assert page.conteudo == ()
    assert (page.vazia, page.primeira, page.ultima) == (True, True, True)
    assert page.total_de_elementos == 0


def test_a_renuncia_by_a_company_keeps_the_cnpj_and_none_for_the_cpf() -> None:
    dados = official_dados("PNRCONTADOR.CONSRENUNCIA263.pagina")
    item = dados["content"][0]
    item.update(
        cnpjSolicitante="11111111111111",
        cnpjRenunciante="22222222222222",
        cpfSolicitante=None,
        cpfRenunciante=None,
    )

    renuncia = read_renuncias(payload_with(dados)).conteudo[0]

    assert (renuncia.cnpj_solicitante, renuncia.cnpj_renunciante) == (
        "11111111111111",
        "22222222222222",
    )
    assert (renuncia.cpf_solicitante, renuncia.cpf_renunciante) == (None, None)


def test_the_timestamp_may_arrive_as_a_number() -> None:
    dados = official_dados("PNRCONTADOR.CONSRENUNCIA263.pagina")
    dados["content"][0]["dataRenuncia"] = 1739242800000

    assert read_renuncias(payload_with(dados)).conteudo[0].data_renuncia == datetime(
        2025, 2, 11, tzinfo=BRT
    )


@pytest.mark.parametrize("value", ["ontem", "", "12.5", -1, True, [1], "99999999999999999"])
def test_a_timestamp_out_of_the_documented_shape_is_refused(value: Any) -> None:
    dados = official_dados("PNRCONTADOR.CONSRENUNCIA263.pagina")
    dados["content"][0]["dataRenuncia"] = value
    with pytest.raises(IntegraPayloadError, match=r"dados\.content\[0\]\.dataRenuncia"):
        read_renuncias(payload_with(dados))


def test_a_broken_renuncias_answer_is_refused_with_the_field_path() -> None:
    good = official_dados("PNRCONTADOR.CONSRENUNCIA263.pagina")
    with pytest.raises(IntegraPayloadError, match="status 500"):
        read_renuncias(payload_with(good, status=500))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_renuncias(payload_with(good["content"]))
    missing = copy.deepcopy(good)
    del missing["content"][0]["id"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.content\[0\]\.id"):
        read_renuncias(payload_with(missing))
    wrong = copy.deepcopy(good)
    wrong["last"] = "talvez"
    with pytest.raises(IntegraPayloadError, match=r"dados\.last"):
        read_renuncias(payload_with(wrong))
    nested = copy.deepcopy(good)
    nested["pageable"]["sort"]["sorted"] = "sim"
    with pytest.raises(IntegraPayloadError, match=r"dados\.pageable\.sort\.sorted"):
        read_renuncias(payload_with(nested))
    listed = copy.deepcopy(good)
    listed["content"] = {"id": 1}
    with pytest.raises(IntegraPayloadError, match=r"dados\.content.*uma lista"):
        read_renuncias(payload_with(listed))


def test_an_effective_renuncia_is_read_with_its_timestamp_to_the_millisecond() -> None:
    situacao = read_situacao_renuncia(
        official_payload("PNRCONTADOR.SITSOLICRENUNCIA265.efetivada")
    )

    assert situacao.resultado is True
    assert situacao.mensagem_retorno is not None
    assert situacao.mensagem_retorno.startswith("Sua renúncia à empresa 99999999999999")
    renuncia = situacao.renuncia
    assert renuncia is not None
    assert (renuncia.id, renuncia.cnpj_renunciada) == (123, "99999999999999")
    # 1740682249338 ms is 18:50:49.338 UTC
    assert renuncia.data_renuncia == datetime(2025, 2, 27, 15, 50, 49, 338000, tzinfo=BRT)
    assert (renuncia.cnpj_solicitante, renuncia.cnpj_renunciante) == (None, None)
    assert renuncia.cpf_solicitante == "00000000011"
    assert renuncia.cpf_logado == "00000000011"


def test_a_denied_or_pending_renuncia_has_no_renuncia_object() -> None:
    situacao = read_situacao_renuncia(official_payload("PNRCONTADOR.SITSOLICRENUNCIA265.negada"))

    assert situacao.resultado is False
    assert situacao.renuncia is None
    assert situacao.mensagem_retorno == "A solicitação de renúncia não foi efetivada."
    omitted = read_situacao_renuncia(payload_with({"resultado": False}))
    assert (omitted.renuncia, omitted.mensagem_retorno) == (None, None)


def test_a_broken_situacao_answer_is_refused_with_the_field_path() -> None:
    good = official_dados("PNRCONTADOR.SITSOLICRENUNCIA265.efetivada")
    with pytest.raises(IntegraPayloadError, match="status 404"):
        read_situacao_renuncia(payload_with(good, status=404))
    with pytest.raises(IntegraPayloadError, match="um objeto"):
        read_situacao_renuncia(payload_with([good]))
    with pytest.raises(IntegraPayloadError, match=r"dados\.resultado.*campo obrigatório"):
        read_situacao_renuncia(payload_with({"mensagemRetorno": "x"}))
    wrong = copy.deepcopy(good)
    wrong["resultado"] = "aprovado"
    with pytest.raises(IntegraPayloadError, match=r"dados\.resultado"):
        read_situacao_renuncia(payload_with(wrong))
    nested = copy.deepcopy(good)
    del nested["renuncia"]["cnpjRenunciada"]
    with pytest.raises(IntegraPayloadError, match=r"dados\.renuncia\.cnpjRenunciada"):
        read_situacao_renuncia(payload_with(nested))
    listed = copy.deepcopy(good)
    listed["renuncia"] = [listed["renuncia"]]
    with pytest.raises(IntegraPayloadError, match=r"dados\.renuncia.*um objeto"):
        read_situacao_renuncia(payload_with(listed))


def test_the_module_registers_its_three_services() -> None:
    assert {typed.key: typed.request for typed in TYPED_SERVICES} == {
        "pnrcontador.vinculos": ConsultarVinculos,
        "pnrcontador.renuncias": ConsultarRenuncias,
        "pnrcontador.situacao_renuncia": ConsultarSituacaoRenuncia,
    }
    assert {typed.key: typed.read for typed in TYPED_SERVICES} == {
        "pnrcontador.vinculos": read_vinculos,
        "pnrcontador.renuncias": read_renuncias,
        "pnrcontador.situacao_renuncia": read_situacao_renuncia,
    }
