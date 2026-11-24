"""DEFIS: consultas da declaração anual do Simples Nacional.

Serviços 142 (lista de declarações), 143 (última declaração do ano, com recibo) e 144 (declaração
por idDefis, com recibo). Fonte de todos os nomes de campo:
https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/
integra-sn/defis/servicos/ (consultar_declaracoes, consultar_ultimadeclaracaorecibo,
consultar_declaracaorecibo).

Decisões não óbvias:

* O serviço 142 não leva `dados` (a página manda `"Dados": ""`): `request=None`.
* A tabela chama os PDFs de `declaracao` e `recibo`; os exemplos oficiais chamam de
  `declaracaoPdf` e `reciboPdf`. O modelo lê as duas grafias; as propriedades `declaracao` e
  `recibo` devolvem os bytes do PDF. Um dos dois nomes de cada PDF é obrigatório.
* `idDefis` é Number na tabela e texto de 15 posições, com zeros à esquerda, no exemplo: o
  leitor devolve sempre o texto de 15 dígitos.
* `tipo` da lista: 1 original normal, 2 retificadora normal, 3 original de situação especial,
  4 retificadora de situação especial.
* Sem declaração, o Serpro responde com aviso (MSG_0042, 0044, 0045), não com `dados` vazio.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any

from apps.integra.errors import IntegraPayloadError
from apps.integra.typed.base import Fmt, J, Model, Request, open_envelope
from apps.integra.typed.registry import TypedService

_ID_DEFIS_SIZE = 15

# ---- requests ----------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class ConsultarUltimaDeclaracao(Request):
    """CONSULTIMADECREC143: a última declaração transmitida do ano-calendário."""

    ano: Annotated[int, J("ano", ge=1900, le=2100)]


@dataclass(frozen=True, kw_only=True)
class ConsultarDeclaracao(Request):
    """CONSDECREC144: uma declaração pelo idDefis (15 dígitos)."""

    id_defis: Annotated[str, J("idDefis", pattern=rf"\d{{{_ID_DEFIS_SIZE}}}")]


# ---- responses ---------------------------------------------------------------------------


def _id_defis(raw: Any) -> str:
    """The idDefis as a text of 15 digits (the example writes text, the table says Number)."""

    if isinstance(raw, int) and not isinstance(raw, bool) and 0 <= raw < 10**_ID_DEFIS_SIZE:
        return f"{raw:0{_ID_DEFIS_SIZE}d}"
    if isinstance(raw, str) and re.fullmatch(rf"\d{{{_ID_DEFIS_SIZE}}}", raw.strip()):
        return raw.strip()
    raise ValueError("idDefis")


@dataclass(frozen=True, kw_only=True)
class DeclaracaoTransmitida(Model):
    """Um item da lista do serviço 142."""

    ano_calendario: Annotated[int, J("anoCalendario")]
    id_defis: Annotated[str, J("idDefis", parse=_id_defis)]
    tipo: Annotated[int, J("tipo")]
    data_hora: Annotated[datetime, J("dataHora", fmt=Fmt.DATETIME14)]


@dataclass(frozen=True, kw_only=True)
class DeclaracaoComRecibo(Model):
    """Respostas 143 e 144: a declaração e o recibo em PDF (143 traz também o idDefis)."""

    id_defis: Annotated[str | None, J("idDefis", parse=_id_defis)] = None
    declaracao_pdf: Annotated[bytes | None, J("declaracaoPdf", fmt=Fmt.PDF)] = None
    declaracao_tabela: Annotated[bytes | None, J("declaracao", fmt=Fmt.PDF)] = None
    recibo_pdf: Annotated[bytes | None, J("reciboPdf", fmt=Fmt.PDF)] = None
    recibo_tabela: Annotated[bytes | None, J("recibo", fmt=Fmt.PDF)] = None

    def __post_init__(self) -> None:
        if self.declaracao_pdf is None and self.declaracao_tabela is None:
            raise IntegraPayloadError(
                "dados.declaracaoPdf (ou declaracao): campo obrigatório ausente."
            )
        if self.recibo_pdf is None and self.recibo_tabela is None:
            raise IntegraPayloadError("dados.reciboPdf (ou recibo): campo obrigatório ausente.")

    @property
    def declaracao(self) -> bytes:
        pdf = self.declaracao_pdf if self.declaracao_pdf is not None else self.declaracao_tabela
        if pdf is None:  # impossível depois do __post_init__
            raise IntegraPayloadError("dados.declaracaoPdf: campo obrigatório ausente.")
        return pdf

    @property
    def recibo(self) -> bytes:
        pdf = self.recibo_pdf if self.recibo_pdf is not None else self.recibo_tabela
        if pdf is None:  # impossível depois do __post_init__
            raise IntegraPayloadError("dados.reciboPdf: campo obrigatório ausente.")
        return pdf


def read_declaracoes(payload: Mapping[str, Any]) -> tuple[DeclaracaoTransmitida, ...]:
    """CONSDECLARACAO142: a lista de todas as declarações do período não decadente."""

    return DeclaracaoTransmitida.parse_many(open_envelope(payload).dados)


def read_ultima_declaracao(payload: Mapping[str, Any]) -> DeclaracaoComRecibo:
    """CONSULTIMADECREC143: a última declaração do ano, com recibo e idDefis."""

    return DeclaracaoComRecibo.parse(open_envelope(payload).dados)


def read_declaracao(payload: Mapping[str, Any]) -> DeclaracaoComRecibo:
    """CONSDECREC144: a declaração pedida, com recibo."""

    return DeclaracaoComRecibo.parse(open_envelope(payload).dados)


TYPED_SERVICES: tuple[TypedService, ...] = (
    TypedService("defis.declaracoes", None, read_declaracoes),
    TypedService("defis.ultima_declaracao", ConsultarUltimaDeclaracao, read_ultima_declaracao),
    TypedService("defis.declaracao", ConsultarDeclaracao, read_declaracao),
)
