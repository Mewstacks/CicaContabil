"""PGDASD: consultas do Simples Nacional (declarações, recibos e extrato do DAS).

Serviços 13 (índice de declarações), 14 (última declaração e recibo), 15 (declaração e recibo
por número) e 16 (extrato do DAS). Fonte de todos os nomes de campo:
https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/
integra-sn/pgdasd/servicos/ (consultar_declaracao_por_ano_pa, consultar_ultima_declaracao_recibo,
consultar_declaracao_recibo, consultar_extrato_do_das).

Decisões não óbvias:

* O exemplo oficial do serviço 13 escreve `anocalendario` e `datahoraEmissaoDas` em minúsculas,
  e a tabela escreve `anoCalendario` e `dataHoraEmissaoDas`. O modelo lê as duas grafias em
  campos separados; as propriedades `ano_calendario` e `data_hora_emissao_das` devolvem a que veio.
* A tabela do serviço 13 prevê `periodos` (consulta por ano) ou `periodo` (consulta por mês).
* Os PDFs (recibo, declaração, extrato, MAED) chegam em base64 dentro do JSON e viram `bytes`.
  `maed` só existe quando a declaração original foi entregue fora do prazo.
* Sem resultado, o Serpro responde com mensagem de erro (MSG_ISN_005, 027, 028), não com
  `dados` vazio: o leitor deixa o motor recusar.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any

from apps.integra.errors import IntegraRequestError
from apps.integra.typed.base import Fmt, J, Model, Request, open_envelope
from apps.integra.typed.registry import TypedService

# ---- requests ----------------------------------------------------------------------------

_NUMERO_17 = r"\d{17}"


@dataclass(frozen=True, kw_only=True)
class ConsultarDeclaracoes(Request):
    """CONSDECLARACAO13: informe o ano-calendário OU o período de apuração, nunca os dois."""

    ano_calendario: Annotated[int | None, J("anoCalendario", ge=1900, le=2100, text=True)] = None
    periodo_apuracao: Annotated[
        int | None, J("periodoApuracao", fmt=Fmt.YEAR_MONTH, text=True)
    ] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if (self.ano_calendario is None) == (self.periodo_apuracao is None):
            raise IntegraRequestError(
                "Informe o ano-calendário ou o período de apuração, e só um deles."
            )


@dataclass(frozen=True, kw_only=True)
class ConsultarUltimaDeclaracao(Request):
    """CONSULTIMADECREC14: a última declaração e o recibo de um período (AAAAMM)."""

    periodo_apuracao: Annotated[int, J("periodoApuracao", fmt=Fmt.YEAR_MONTH, text=True)]


@dataclass(frozen=True, kw_only=True)
class ConsultarDeclaracao(Request):
    """CONSDECREC15: a declaração e o recibo de um número de declaração."""

    numero_declaracao: Annotated[str, J("numeroDeclaracao", pattern=_NUMERO_17)]


@dataclass(frozen=True, kw_only=True)
class ConsultarExtratoDas(Request):
    """CONSEXTRATO16: o extrato de um DAS gerado."""

    numero_das: Annotated[str, J("numeroDas", pattern=_NUMERO_17)]


# ---- responses ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class IndiceDeclaracao(Model):
    numero_declaracao: Annotated[str, J("numeroDeclaracao")]
    data_hora_transmissao: Annotated[
        datetime | None, J("dataHoraTransmissao", fmt=Fmt.DATETIME14)
    ] = None
    malha: Annotated[str | None, J("malha")] = None  # None quando fora de malha (null ou "")


@dataclass(frozen=True, kw_only=True)
class IndiceDas(Model):
    numero_das: Annotated[str, J("numeroDas")]
    data_hora_emissao_das_tabela: Annotated[
        datetime | None, J("dataHoraEmissaoDas", fmt=Fmt.DATETIME14)
    ] = None
    data_hora_emissao_das_exemplo: Annotated[
        datetime | None, J("datahoraEmissaoDas", fmt=Fmt.DATETIME14)
    ] = None
    das_pago: Annotated[bool | None, J("dasPago")] = None

    @property
    def data_hora_emissao_das(self) -> datetime | None:
        return self.data_hora_emissao_das_tabela or self.data_hora_emissao_das_exemplo


@dataclass(frozen=True, kw_only=True)
class Operacao(Model):
    tipo_operacao: Annotated[str, J("tipoOperacao")]
    indice_declaracao: Annotated[IndiceDeclaracao | None, J("indiceDeclaracao")] = None
    indice_das: Annotated[IndiceDas | None, J("indiceDas")] = None


@dataclass(frozen=True, kw_only=True)
class Periodo(Model):
    periodo_apuracao: Annotated[int, J("periodoApuracao", fmt=Fmt.YEAR_MONTH)]
    operacoes: Annotated[tuple[Operacao, ...], J("operacoes")] = ()


@dataclass(frozen=True, kw_only=True)
class DeclaracoesEntregues(Model):
    """Índice do serviço 13: `periodos` (consulta por ano) ou `periodo` (consulta por mês)."""

    ano_calendario_tabela: Annotated[int | None, J("anoCalendario")] = None
    ano_calendario_exemplo: Annotated[int | None, J("anocalendario")] = None
    periodos: Annotated[tuple[Periodo, ...], J("periodos")] = ()
    periodo: Annotated[Periodo | None, J("periodo")] = None

    @property
    def ano_calendario(self) -> int | None:
        if self.ano_calendario_tabela is not None:
            return self.ano_calendario_tabela
        return self.ano_calendario_exemplo


@dataclass(frozen=True, kw_only=True)
class ArquivoPdf(Model):
    """Um PDF com o nome sugerido (recibo, declaração ou extrato)."""

    nome_arquivo: Annotated[str | None, J("nomeArquivo")] = None
    pdf: Annotated[bytes, J("pdf", fmt=Fmt.PDF)]


@dataclass(frozen=True, kw_only=True)
class ArquivoMaed(Model):
    """Notificação e DARF da multa por atraso na entrega (MAED)."""

    nome_arquivo_notificacao: Annotated[str | None, J("nomeArquivoNotificacao")] = None
    pdf_notificacao: Annotated[bytes | None, J("pdfNotificacao", fmt=Fmt.PDF)] = None
    nome_arquivo_darf: Annotated[str | None, J("nomeArquivoDarf")] = None
    pdf_darf: Annotated[bytes | None, J("pdfDarf", fmt=Fmt.PDF)] = None


@dataclass(frozen=True, kw_only=True)
class Declaracao(Model):
    numero_declaracao: Annotated[str, J("numeroDeclaracao")]
    recibo: Annotated[ArquivoPdf, J("recibo")]
    declaracao: Annotated[ArquivoPdf, J("declaracao")]
    maed: Annotated[ArquivoMaed | None, J("maed")] = None


@dataclass(frozen=True, kw_only=True)
class ExtratoDas(Model):
    numero_das: Annotated[str, J("numeroDas")]
    extrato: Annotated[ArquivoPdf, J("extrato")]


def read_declaracoes(payload: Mapping[str, Any]) -> DeclaracoesEntregues:
    """CONSDECLARACAO13: o índice de declarações e DAS de um ano ou de um mês."""

    return DeclaracoesEntregues.parse(open_envelope(payload).dados)


def read_ultima_declaracao(payload: Mapping[str, Any]) -> Declaracao:
    """CONSULTIMADECREC14: a última declaração do período, com recibo e, se houver, MAED."""

    return Declaracao.parse(open_envelope(payload).dados)


def read_declaracao(payload: Mapping[str, Any]) -> Declaracao:
    """CONSDECREC15: a declaração pelo número, com recibo e, se houver, MAED."""

    return Declaracao.parse(open_envelope(payload).dados)


def read_extrato(payload: Mapping[str, Any]) -> ExtratoDas:
    """CONSEXTRATO16: o extrato do DAS em PDF."""

    return ExtratoDas.parse(open_envelope(payload).dados)


TYPED_SERVICES: tuple[TypedService, ...] = (
    TypedService("pgdasd.declaracoes", ConsultarDeclaracoes, read_declaracoes),
    TypedService("pgdasd.ultima_declaracao", ConsultarUltimaDeclaracao, read_ultima_declaracao),
    TypedService("pgdasd.declaracao", ConsultarDeclaracao, read_declaracao),
    TypedService("pgdasd.extrato", ConsultarExtratoDas, read_extrato),
)
