"""PNRCONTADOR: accountant links (261), renunciations (263) and their status (265).

Source of every field name:
https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/
integra-redesim/pnrcontador/ (servicos/consultar_vinculos, consultar_renuncias,
situacao_solicitar_renuncia and the three exemplos/retorno_* pages). The renunciation request
(262) and the proof (264) are write/emission services and are not read here.

Decisions that are not obvious:

* The official input examples are not valid JSON (a missing comma or colon in 261, 263 and 265):
  the objects built here are the intended ones.
* The table of 261 lists `size` and `lastCnpj` as direct fields, but the example nests them in
  `pagination`: the example is followed. The table says "valor padrão: 10" and also "obrigatório
  SIM" for `size`: it is required here.
* `dtInicio`/`dtFim` are both or none ("é necessário informar tanto dtInicio quanto dtFim"); the
  page says the end date must be later than the start, but its own example uses the same day for
  both, so equal dates are accepted and only an end before the start is refused.
* `dataRenuncia` is a timestamp in milliseconds, text in the examples and Number in the tables:
  both are read and returned as a datetime in Brasília time.
* The page of 263 is a Spring Data page (`content`, `pageable`, `sort`, ...); the example is
  inconsistent (`last: false` on the only page), which is kept as received.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Annotated, Any

from apps.integra.errors import IntegraRequestError
from apps.integra.typed.base import BRASILIA, Fmt, J, Model, Request, open_envelope
from apps.integra.typed.registry import TypedService

_MAX_TIMESTAMP_MS = 4_102_444_800_000  # 2100-01-01
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def _timestamp_ms(raw: Any) -> datetime:
    """Milliseconds since the epoch, as a number or as text, in Brasília time."""

    if isinstance(raw, bool):
        raise ValueError("timestamp inválido")
    if isinstance(raw, str) and re.fullmatch(r"\d{1,15}", raw.strip()):
        raw = int(raw.strip())
    if not isinstance(raw, int) or not 0 <= raw <= _MAX_TIMESTAMP_MS:
        raise ValueError("timestamp inválido")
    return (_EPOCH + timedelta(milliseconds=raw)).astimezone(BRASILIA)


# ---- requests ----------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class PaginacaoVinculos(Request):
    """The cursor paging of CONSVINCULOS261: up to 50 companies per page."""

    tamanho: Annotated[int, J("size", ge=1, le=50)]
    ultimo_cnpj: Annotated[str | None, J("lastCnpj", pattern=r"[0-9A-Z]{14}")] = None


@dataclass(frozen=True, kw_only=True)
class ConsultarVinculos(Request):
    """CONSVINCULOS261: the companies the accountant is linked to."""

    paginacao: Annotated[PaginacaoVinculos, J("pagination")]


@dataclass(frozen=True, kw_only=True)
class ConsultarRenuncias(Request):
    """CONSRENUNCIA263: renunciations, by period (both dates) and page (from 0, up to 50)."""

    dt_inicio: Annotated[date | None, J("dtInicio", fmt=Fmt.ISO_DATE)] = None
    dt_fim: Annotated[date | None, J("dtFim", fmt=Fmt.ISO_DATE)] = None
    page: Annotated[int | None, J("page", ge=0)] = None
    page_size: Annotated[int | None, J("pageSize", ge=1, le=50)] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if (self.dt_inicio is None) != (self.dt_fim is None):
            raise IntegraRequestError("Informe as duas datas do período, ou nenhuma.")
        if self.dt_inicio and self.dt_fim and self.dt_fim < self.dt_inicio:
            raise IntegraRequestError("O período está invertido.")


@dataclass(frozen=True, kw_only=True)
class ConsultarSituacaoRenuncia(Request):
    """SITSOLICRENUNCIA265: the status of a solicitation (wait 30 s after requesting)."""

    id_solicitacao: Annotated[str, J("idSolicitacao", pattern=r"[A-Za-z0-9_-]{1,64}")]


# ---- responses ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class SituacaoCadastral(Model):
    codigo: Annotated[str, J("codigo")]
    descricao: Annotated[str | None, J("descricao")] = None


@dataclass(frozen=True, kw_only=True)
class Empresa(Model):
    cnpj: Annotated[str, J("cnpj")]
    tipo_estabelecimento: Annotated[str | None, J("tipoEstabelecimento")] = None
    situacao_cadastral: Annotated[SituacaoCadastral | None, J("situacaoCadastral")] = None
    uf: Annotated[str | None, J("uf")] = None
    codigo_municipio: Annotated[str | None, J("codigoMunicipio")] = None
    nome_municipio: Annotated[str | None, J("nomeMunicipio")] = None


@dataclass(frozen=True, kw_only=True)
class PaginaVinculos(Model):
    empresas: Annotated[tuple[Empresa, ...], J("cnpjs")] = ()
    total_na_pagina: Annotated[int | None, J("totalInThePage")] = None
    total_na_base: Annotated[int | None, J("totalInTheDatabase")] = None
    ultimo_cnpj: Annotated[str | None, J("lastCnpj")] = None


@dataclass(frozen=True, kw_only=True)
class Renuncia(Model):
    """One renunciation: at least one solicitant and one renouncer (CPF or CNPJ) are filled."""

    id: Annotated[int, J("id")]
    cnpj_renunciada: Annotated[str, J("cnpjRenunciada")]
    data_renuncia: Annotated[
        datetime, J("dataRenuncia", fmt=Fmt.ISO_DATETIME, parse=_timestamp_ms)
    ]
    cnpj_solicitante: Annotated[str | None, J("cnpjSolicitante")] = None
    cnpj_renunciante: Annotated[str | None, J("cnpjRenunciante")] = None
    cpf_solicitante: Annotated[str | None, J("cpfSolicitante")] = None
    cpf_renunciante: Annotated[str | None, J("cpfRenunciante")] = None
    cpf_logado: Annotated[str | None, J("cpfLogado")] = None


@dataclass(frozen=True, kw_only=True)
class Ordenacao(Model):
    ordenada: Annotated[bool | None, J("sorted")] = None
    nao_ordenada: Annotated[bool | None, J("unsorted")] = None
    vazia: Annotated[bool | None, J("empty")] = None


@dataclass(frozen=True, kw_only=True)
class InfoPaginacao(Model):
    deslocamento: Annotated[int | None, J("offset")] = None
    paginada: Annotated[bool | None, J("paged")] = None
    numero_da_pagina: Annotated[int | None, J("pageNumber")] = None
    tamanho_da_pagina: Annotated[int | None, J("pageSize")] = None
    ordenacao: Annotated[Ordenacao | None, J("sort")] = None
    sem_paginacao: Annotated[bool | None, J("unpaged")] = None


@dataclass(frozen=True, kw_only=True)
class PaginaRenuncias(Model):
    conteudo: Annotated[tuple[Renuncia, ...], J("content")] = ()
    vazia: Annotated[bool | None, J("empty")] = None
    primeira: Annotated[bool | None, J("first")] = None
    ultima: Annotated[bool | None, J("last")] = None
    numero: Annotated[int | None, J("number")] = None
    numero_de_elementos: Annotated[int | None, J("numberOfElements")] = None
    paginacao: Annotated[InfoPaginacao | None, J("pageable")] = None
    tamanho: Annotated[int | None, J("size")] = None
    ordenacao: Annotated[Ordenacao | None, J("sort")] = None
    total_de_elementos: Annotated[int | None, J("totalElements")] = None
    total_de_paginas: Annotated[int | None, J("totalPages")] = None


@dataclass(frozen=True, kw_only=True)
class SituacaoSolicitacao(Model):
    """`renuncia` is None while the renunciation is not effective, or when it was denied."""

    resultado: Annotated[bool, J("resultado")]
    mensagem_retorno: Annotated[str | None, J("mensagemRetorno")] = None
    renuncia: Annotated[Renuncia | None, J("renuncia")] = None


def read_vinculos(payload: Mapping[str, Any]) -> PaginaVinculos:
    """CONSVINCULOS261: a page of companies; follow `ultimo_cnpj` for the next one."""

    return PaginaVinculos.parse(open_envelope(payload).dados)


def read_renuncias(payload: Mapping[str, Any]) -> PaginaRenuncias:
    """CONSRENUNCIA263: a page of renunciations."""

    return PaginaRenuncias.parse(open_envelope(payload).dados)


def read_situacao_renuncia(payload: Mapping[str, Any]) -> SituacaoSolicitacao:
    """SITSOLICRENUNCIA265: whether the solicitation was approved, with the renunciation."""

    return SituacaoSolicitacao.parse(open_envelope(payload).dados)


TYPED_SERVICES: tuple[TypedService, ...] = (
    TypedService("pnrcontador.vinculos", ConsultarVinculos, read_vinculos),
    TypedService("pnrcontador.renuncias", ConsultarRenuncias, read_renuncias),
    TypedService(
        "pnrcontador.situacao_renuncia", ConsultarSituacaoRenuncia, read_situacao_renuncia
    ),
)
