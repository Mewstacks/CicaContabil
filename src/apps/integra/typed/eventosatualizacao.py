"""EVENTOSATUALIZACAO: last-update events of up to 1000 CPFs or CNPJs per batch.

Services 131 and 132 (request a batch, answered with a protocol and waiting times) and 133 and 134
(retrieve the batch). Source of every field name:
https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/
integra-contador-gerenciador/eventosatualizacao/ (servicos, exemplos, mensagens, changelog).

Decisions that are not obvious:

* The list of CPFs/CNPJs travels in the `contribuinte` of the envelope (tipo 3 or 4, separated by
  commas), never in `dados`. The retrieval sends an empty `contribuinte.numero`.
* The page of 132 documents the field as `eventValue`, but every example (and 131, 133, 134) uses
  `evento`: `evento` is used.
* The matrix of 133/134 is documented as an object with `elementos` but the examples show a bare
  list of rows. Both are read. Each row is [NI, AAMMDD]: "" means no update, "x" means no power
  of attorney (access denied, nothing was consulted).
* The changelog 1.0.1 added status 202 ("still in process", Aviso-EVENTOSATUALIZACAO-007): the
  retrieval accepts 200 and 202 and exposes `em_processamento`; poll again with the same protocol.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from typing import Annotated, Any

from apps.integra.typed.base import J, Message, Model, Request, open_envelope
from apps.integra.typed.registry import TypedService

EVENTO_DCTFWEB = "E0301"
EVENTO_CAIXA_POSTAL = "E0601"
EVENTO_PAGAMENTOS = "E0701"

MAX_LINHAS = 1_000
_NI = re.compile(r"\d{11}|[0-9A-Z]{14}")
_AAMMDD = re.compile(r"\d{6}")

# ---- requests ----------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class SolicitarEventos(Request):
    """SOLICEVENTOSPF131 and SOLICEVENTOSPJ132: the batch itself goes in the envelope."""

    evento: Annotated[str, J("evento", pattern=r"E\d{4}")]


@dataclass(frozen=True, kw_only=True)
class ObterEventos(Request):
    """OBTEREVENTOSPF133 and OBTEREVENTOSPJ134: the protocol (36 characters) and the event."""

    protocolo: Annotated[str, J("protocolo", pattern=r"[0-9A-Za-z-]{36}")]
    evento: Annotated[str, J("evento", pattern=r"E\d{4}")]


# ---- responses ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class ProtocoloEventos(Model):
    """The answer of a request: wait `tempo_espera_medio_ms`, then retrieve within the limit."""

    protocolo: Annotated[str, J("protocolo")]
    tempo_espera_medio_ms: Annotated[int, J("TempoEsperaMedioEmMs")]
    tempo_limite_min: Annotated[int, J("TempoLimiteEmMin")]


@dataclass(frozen=True)
class LinhaEvento:
    """One row of the matrix: `data` is None without an update or without power of attorney."""

    ni: str
    data: date | None
    sem_procuracao: bool


def _linha(raw: Any) -> LinhaEvento:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError("linha fora do formato [NI, data]")
    ni, valor = raw
    if not isinstance(ni, str) or not _NI.fullmatch(ni):
        raise ValueError("NI fora do formato")
    if not isinstance(valor, str):
        raise ValueError("data fora do formato")
    if valor == "":
        return LinhaEvento(ni, None, False)
    if valor in ("x", "X"):
        return LinhaEvento(ni, None, True)
    if not _AAMMDD.fullmatch(valor):
        raise ValueError("data fora do formato AAMMDD")
    return LinhaEvento(ni, date(2000 + int(valor[:2]), int(valor[2:4]), int(valor[4:])), False)


def _linhas(raw: Any) -> tuple[LinhaEvento, ...]:
    if not isinstance(raw, list) or len(raw) > MAX_LINHAS:
        raise ValueError("matriz fora do formato ou do limite")
    return tuple(_linha(item) for item in raw)


@dataclass(frozen=True, kw_only=True)
class MatrizEventos(Model):
    elementos: Annotated[Any, J("elementos", parse=_linhas)]


@dataclass(frozen=True)
class EventosObtidos:
    """The retrieval: `em_processamento` (status 202) means to ask again with the protocol."""

    em_processamento: bool
    linhas: tuple[LinhaEvento, ...]
    mensagens: tuple[Message, ...]


def read_solicitacao(payload: Mapping[str, Any]) -> ProtocoloEventos:
    """SOLICEVENTOSPF131 / SOLICEVENTOSPJ132: the `dados` is the protocol object."""

    return ProtocoloEventos.parse(open_envelope(payload).dados)


def read_eventos(payload: Mapping[str, Any]) -> EventosObtidos:
    """OBTEREVENTOSPF133 / OBTEREVENTOSPJ134: 200 with the matrix, or 202 still in process."""

    envelope = open_envelope(payload, accept=(200, 202))
    em_processamento = envelope.status == 202
    dados = envelope.dados
    if dados is None and em_processamento:
        return EventosObtidos(True, (), envelope.mensagens)
    if isinstance(dados, list):
        dados = {"elementos": dados}
    matriz = MatrizEventos.parse(dados)
    return EventosObtidos(em_processamento, matriz.elementos, envelope.mensagens)


TYPED_SERVICES: tuple[TypedService, ...] = (
    TypedService("eventosatualizacao.solicitar_pf", SolicitarEventos, read_solicitacao),
    TypedService("eventosatualizacao.solicitar_pj", SolicitarEventos, read_solicitacao),
    TypedService("eventosatualizacao.obter_pf", ObterEventos, read_eventos),
    TypedService("eventosatualizacao.obter_pj", ObterEventos, read_eventos),
)
