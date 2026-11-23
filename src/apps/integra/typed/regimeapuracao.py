"""REGIMEAPURACAO: consultas do regime de apuração de receitas (caixa ou competência).

Serviços 102 (anos com opção efetivada), 103 (opção de um ano, com demonstrativo em PDF) e 104
(texto da resolução do regime de caixa). Fonte de todos os nomes de campo:
https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/
integra-sn/regime/servicos/ (consultar_anos_calendarios, consultar_opcao, consultar_resolucao).

Decisões não óbvias:

* O serviço 102 não leva `dados`: `request=None`. Seu `dados` é uma lista.
* `textoResolucao`: a tabela diz base64, mas o exemplo oficial traz o texto puro. O leitor
  decodifica quando o valor é base64 válido de um texto UTF-8 e, senão, devolve o texto como veio.
* `cnpjMatriz` é Number na tabela e texto de 14 posições no exemplo: o leitor devolve o texto.
* Na opção, `textoResolucao` só existe no regime de caixa (texto da página): opcional.
* Sem opção efetivada, o Serpro responde com aviso (MSG_ISN_055, 057), não com `dados` vazio.
"""

from __future__ import annotations

import base64
import binascii
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any

from apps.integra.typed.base import Fmt, J, Model, Request, open_envelope
from apps.integra.typed.registry import TypedService

_MAX_RESOLUCAO = 500_000
_CNPJ_SIZE = 14

# ---- requests ----------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class ConsultarOpcao(Request):
    """CONSULTAROPCAOREGIME103: a opção de um ano-calendário."""

    ano_calendario: Annotated[int, J("anoCalendario", ge=1900, le=2100)]


@dataclass(frozen=True, kw_only=True)
class ConsultarResolucao(Request):
    """CONSULTARRESOLUCAO104: a resolução do regime de caixa de um ano-calendário."""

    ano_calendario: Annotated[int, J("anoCalendario", ge=1900, le=2100)]


# ---- responses ---------------------------------------------------------------------------


def _texto_resolucao(raw: Any) -> str:
    """The resolution as text, whether it came in base64 (table) or plain (example)."""

    if not isinstance(raw, str) or not raw.strip() or len(raw) > _MAX_RESOLUCAO:
        raise ValueError("textoResolucao")
    if re.fullmatch(r"[A-Za-z0-9+/\r\n]+={0,2}", raw):
        try:
            return base64.b64decode(re.sub(r"\s+", "", raw), validate=True).decode("utf-8")
        except (binascii.Error, UnicodeDecodeError):
            pass
    return raw


def _texto_resolucao_opcional(raw: Any) -> str:
    """Same as `_texto_resolucao`, but an empty text is kept (the model turns it into None)."""

    return "" if raw == "" else _texto_resolucao(raw)


def _cnpj_matriz(raw: Any) -> str:
    """The CNPJ of the matriz as 14 characters (the table says Number, the example a text)."""

    if isinstance(raw, int) and not isinstance(raw, bool) and 0 <= raw < 10**_CNPJ_SIZE:
        return f"{raw:0{_CNPJ_SIZE}d}"
    if isinstance(raw, str) and re.fullmatch(rf"[0-9A-Z]{{{_CNPJ_SIZE}}}", raw.strip()):
        return raw.strip()
    raise ValueError("cnpjMatriz")


@dataclass(frozen=True, kw_only=True)
class RegimeDoAno(Model):
    """Um item da lista do serviço 102."""

    ano_calendario: Annotated[int, J("anoCalendario")]
    regime_apurado: Annotated[str, J("regimeApurado")]  # "COMPETENCIA" ou "CAIXA"


@dataclass(frozen=True, kw_only=True)
class OpcaoRegime(Model):
    cnpj_matriz: Annotated[str, J("cnpjMatriz", parse=_cnpj_matriz)]
    ano_calendario: Annotated[int, J("anoCalendario")]
    regime_escolhido: Annotated[str, J("regimeEscolhido")]  # "COMPETENCIA" ou "CAIXA"
    data_hora_opcao: Annotated[datetime, J("dataHoraOpcao", fmt=Fmt.DATETIME14)]
    demonstrativo_pdf: Annotated[bytes, J("demonstrativoPdf", fmt=Fmt.PDF)]
    texto_resolucao: Annotated[
        str | None, J("textoResolucao", parse=_texto_resolucao_opcional)
    ] = None


@dataclass(frozen=True, kw_only=True)
class ResolucaoCaixa(Model):
    texto_resolucao: Annotated[str, J("textoResolucao", parse=_texto_resolucao)]


def read_anos(payload: Mapping[str, Any]) -> tuple[RegimeDoAno, ...]:
    """CONSULTARANOSCALENDARIOS102: o regime de cada ano com opção efetivada."""

    return RegimeDoAno.parse_many(open_envelope(payload).dados)


def read_opcao(payload: Mapping[str, Any]) -> OpcaoRegime:
    """CONSULTAROPCAOREGIME103: a opção do ano, com o demonstrativo em PDF."""

    return OpcaoRegime.parse(open_envelope(payload).dados)


def read_resolucao(payload: Mapping[str, Any]) -> ResolucaoCaixa:
    """CONSULTARRESOLUCAO104: o texto da resolução do regime de caixa."""

    return ResolucaoCaixa.parse(open_envelope(payload).dados)


TYPED_SERVICES: tuple[TypedService, ...] = (
    TypedService("regimeapuracao.anos", None, read_anos),
    TypedService("regimeapuracao.opcao", ConsultarOpcao, read_opcao),
    TypedService("regimeapuracao.resolucao", ConsultarResolucao, read_resolucao),
)
