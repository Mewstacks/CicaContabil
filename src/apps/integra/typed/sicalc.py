"""SICALC: support table of receitas (52) and the consolidation of a DARF (54).

Source of every field name:
https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/
integra-sicalc/sicalc/ (servicos/apoio_consulta_receitas_do_sicalc,
servicos/consolidar_emitir_um_darf, exemplos/retorno_apoio_consulta_receitas_do_sicalc,
exemplos/retorno_consolidado_alfa, dados_de_dominio).

Decisions that are not obvious:

* Service 54 has no page of its own: its input is the table "Dados de Entrada" of service 51 and
  its answer is only the `consolidado` object (section "Diferença entre serviços"). `ConsolidarDarf`
  is that table; the PDF of service 51 is not read here.
* The pages say "numérico" for codes, but the examples send text ("0190", "01", "7107"):
  they are text with a pattern, so leading zeros survive. The table calls the municipality
  `município` and the example `municipio`: the example is followed.
* Amounts are text in the request ("1000.00") and text or number in the answer: both are read
  as `Decimal`. Dates are ISO without offset (Brasília time).
* `extensoes` of service 52: the example page puts `obrigatorios`, `opcionais` and `informacoes`
  inside each array element; the service page shows one element per object. Both are read, as
  elements with the three objects optional. `codigoReceita` and `codigoReceitaExtensao` come as
  number in the examples and text in the table: both are read as text.
* Status 404 of service 52 ("a receita consultada não existe") is refused by the engine.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from apps.integra.errors import IntegraRequestError
from apps.integra.typed.base import Fmt, J, Model, Request, open_envelope
from apps.integra.typed.registry import TypedService

# The shape of dataPA per tipoPA (dados_de_dominio): aaaa, mm/aaaa or xx/mm/aaaa.
_DATA_PA = {
    "AN": r"\d{4}",
    "TR": r"\d{2}/\d{4}",
    "ME": r"\d{2}/\d{4}",
    "QZ": r"\d{2}/\d{2}/\d{4}",
    "DC": r"\d{2}/\d{2}/\d{4}",
    "SM": r"\d{2}/\d{2}/\d{4}",
    "DI": r"\d{2}/\d{2}/\d{4}",
}


def _texto(raw: Any) -> str:
    """A code that the examples send as a number and the tables document as text."""

    if isinstance(raw, bool) or not isinstance(raw, str | int):
        raise ValueError("texto ou número esperado")
    return str(raw)


# ---- requests ----------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class ConsultarReceita(Request):
    """CONSULTAAPOIORECEITAS52: the receita code (up to four digits)."""

    codigo_receita: Annotated[str, J("codigoReceita", pattern=r"\d{1,4}")]


@dataclass(frozen=True, kw_only=True)
class ConsolidarDarf(Request):
    """The input of CONSOLIDAR54 (and CONSOLIDARGERARDARF51): the debit to consolidate.

    `cota` and `vencimento` are mutually exclusive; a receita that has no quota needs the due
    date, which depends on the receita and is not checked here (see service 52).
    """

    uf: Annotated[str | None, J("uf", pattern=r"[A-Z]{2}")] = None
    municipio: Annotated[str | None, J("municipio", pattern=r"\d{1,4}")] = None
    codigo_receita: Annotated[str, J("codigoReceita", pattern=r"\d{1,4}")]
    codigo_receita_extensao: Annotated[str, J("codigoReceitaExtensao", pattern=r"\d{1,2}")]
    numero_referencia: Annotated[
        str | None, J("numeroReferencia", pattern=r"[0-9A-Za-z/]{1,30}")
    ] = None
    tipo_pa: Annotated[str | None, J("tipoPA", pattern=r"AN|TR|ME|QZ|DC|SM|DI")] = None
    data_pa: Annotated[str, J("dataPA", pattern=r"\d{4}|\d{2}/\d{4}|\d{2}/\d{2}/\d{4}")]
    vencimento: Annotated[datetime | None, J("vencimento", fmt=Fmt.ISO_DATETIME)] = None
    cota: Annotated[int | None, J("cota", ge=1, text=True)] = None
    valor_imposto: Annotated[Decimal, J("valorImposto", fmt=Fmt.MONEY_STR)]
    valor_multa: Annotated[Decimal | None, J("valorMulta", fmt=Fmt.MONEY_STR)] = None
    valor_juros: Annotated[Decimal | None, J("valorJuros", fmt=Fmt.MONEY_STR)] = None
    ganho_capital: Annotated[bool | None, J("ganhoCapital")] = None
    data_alienacao: Annotated[datetime | None, J("dataAlienacao", fmt=Fmt.ISO_DATETIME)] = None
    data_consolidacao: Annotated[datetime, J("dataConsolidacao", fmt=Fmt.ISO_DATETIME)]
    observacao: Annotated[str | None, J("observacao")] = None
    cno: Annotated[str | None, J("cno", pattern=r"\d{1,12}")] = None
    cnpj_prestador: Annotated[str | None, J("cnpjPrestador", fmt=Fmt.CNPJ)] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.cota is not None and self.vencimento is not None:
            raise IntegraRequestError("Informe a cota ou o vencimento, não os dois.")
        if self.tipo_pa is not None and not re.fullmatch(_DATA_PA[self.tipo_pa], self.data_pa):
            raise IntegraRequestError("O período de apuração não segue o formato do tipo.")


# ---- responses ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class CamposObrigatorios(Model):
    """Which fields of the DARF request the receita requires."""

    codigo_receita: Annotated[bool | None, J("codigoReceita")] = None
    codigo_receita_extensao: Annotated[bool | None, J("codigoReceitaExtensao")] = None
    cota: Annotated[bool | None, J("cota")] = None
    data_consolidacao: Annotated[bool | None, J("dataConsolidacao")] = None
    data_pa: Annotated[bool | None, J("dataPA")] = None
    referencia: Annotated[bool | None, J("referencia")] = None
    tipo_pa: Annotated[bool | None, J("tipoPA")] = None
    valor_imposto: Annotated[bool | None, J("valorImposto")] = None
    vencimento: Annotated[bool | None, J("vencimento")] = None


@dataclass(frozen=True, kw_only=True)
class CamposOpcionais(Model):
    """Which fields of the DARF request the receita accepts."""

    cno: Annotated[bool | None, J("cno")] = None
    cnpj_prestador: Annotated[bool | None, J("cnpjPrestador")] = None
    data_alienacao: Annotated[bool | None, J("dataAlienacao")] = None
    ganho_capital: Annotated[bool | None, J("ganhoCapital")] = None
    municipio: Annotated[bool | None, J("municipio")] = None
    observacao: Annotated[bool | None, J("observacao")] = None
    referencia: Annotated[bool | None, J("referencia")] = None
    uf: Annotated[bool | None, J("uf")] = None
    valor_juros: Annotated[bool | None, J("valorJuros")] = None
    valor_multa: Annotated[bool | None, J("valorMulta")] = None


@dataclass(frozen=True, kw_only=True)
class InformacoesReceita(Model):
    """What the receita allows (bar code, automatic calculation, person or company)."""

    calculado: Annotated[bool | None, J("calculado")] = None
    codigo_barras: Annotated[bool | None, J("codigoBarras")] = None
    codigo_receita_extensao: Annotated[
        str | None, J("codigoReceitaExtensao", parse=_texto)
    ] = None
    criacao: Annotated[datetime | None, J("criacao", fmt=Fmt.ISO_DATETIME)] = None
    descricao_receita_extensao: Annotated[str | None, J("descricaoReceitaExtensao")] = None
    descricao_referencia: Annotated[str | None, J("descricaoReferencia")] = None
    exige_matriz: Annotated[bool | None, J("exigeMatriz")] = None
    extincao: Annotated[datetime | None, J("extincao", fmt=Fmt.ISO_DATETIME)] = None
    manual: Annotated[bool | None, J("manual")] = None
    pf: Annotated[bool | None, J("pf")] = None
    pj: Annotated[bool | None, J("pj")] = None
    tipo_periodo_apuracao: Annotated[str | None, J("tipoPeriodoApuracao")] = None
    veda_valor: Annotated[bool | None, J("vedaValor")] = None


@dataclass(frozen=True, kw_only=True)
class ExtensaoReceita(Model):
    """One element of `extensoes`: with one object or with the three, see the module doc."""

    obrigatorios: Annotated[CamposObrigatorios | None, J("obrigatorios")] = None
    opcionais: Annotated[CamposOpcionais | None, J("opcionais")] = None
    informacoes: Annotated[InformacoesReceita | None, J("informacoes")] = None


@dataclass(frozen=True, kw_only=True)
class Receita(Model):
    codigo_receita: Annotated[str, J("codigoReceita", parse=_texto)]
    descricao_receita: Annotated[str | None, J("descricaoReceita")] = None
    extensoes: Annotated[tuple[ExtensaoReceita, ...], J("extensoes")] = ()


@dataclass(frozen=True, kw_only=True)
class RespostaReceita(Model):
    receita: Annotated[Receita, J("receita")]


@dataclass(frozen=True, kw_only=True)
class Consolidado(Model):
    """The consolidated debit: principal, fine, interest and the validity of the calculation."""

    valor_principal_moeda_corrente: Annotated[Decimal, J("valorPrincipalMoedaCorrente")]
    valor_total_consolidado: Annotated[Decimal, J("valorTotalConsolidado")]
    valor_multa_mora: Annotated[Decimal | None, J("valorMultaMora")] = None
    percentual_multa_mora: Annotated[Decimal | None, J("percentualMultaMora")] = None
    valor_juros: Annotated[Decimal | None, J("valorJuros")] = None
    percentual_juros: Annotated[Decimal | None, J("percentualJuros")] = None
    termo_inicial_juros: Annotated[
        datetime | None, J("termoInicialJuros", fmt=Fmt.ISO_DATETIME)
    ] = None
    data_arrecadacao_consolidacao: Annotated[
        datetime | None, J("dataArrecadacaoConsolidacao", fmt=Fmt.ISO_DATETIME)
    ] = None
    data_validade_calculo: Annotated[
        datetime | None, J("dataValidadeCalculo", fmt=Fmt.ISO_DATETIME)
    ] = None


@dataclass(frozen=True, kw_only=True)
class RespostaConsolidacao(Model):
    consolidado: Annotated[Consolidado, J("consolidado")]


def read_receita(payload: Mapping[str, Any]) -> Receita:
    """CONSULTAAPOIORECEITAS52: the `dados` is `{"receita": {...}}`."""

    return RespostaReceita.parse(open_envelope(payload).dados).receita


def read_consolidado(payload: Mapping[str, Any]) -> Consolidado:
    """CONSOLIDAR54: the `dados` is `{"consolidado": {...}}` (51 and 53 add a darf and more)."""

    return RespostaConsolidacao.parse(open_envelope(payload).dados).consolidado


TYPED_SERVICES: tuple[TypedService, ...] = (
    TypedService("sicalc.receitas", ConsultarReceita, read_receita),
    TypedService("sicalc.consolidar", ConsolidarDarf, read_consolidado),
)
