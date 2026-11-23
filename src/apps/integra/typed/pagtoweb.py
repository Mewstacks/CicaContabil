"""PAGTOWEB: paid collection documents (DARF, DAS, DAE, DJE) of one taxpayer.

Services 71 (list of payments) and 73 (count of payments). Source of every field name:
https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/
integra-pagamento/pagtoweb/servicos/ (consulta_pagamento, conta_consulta_pagamento).
Service 72 (payment proof, PDF) is a document emission and is not read here.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any

from apps.integra.errors import IntegraRequestError
from apps.integra.typed.base import Fmt, J, Model, Request, open_envelope, read_int
from apps.integra.typed.registry import TypedService

# ---- requests ----------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class IntervaloData(Request):
    inicial: Annotated[date | None, J("dataInicial", fmt=Fmt.ISO_DATE)] = None
    final: Annotated[date | None, J("dataFinal", fmt=Fmt.ISO_DATE)] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.inicial and self.final and self.inicial > self.final:
            raise IntegraRequestError("O intervalo de datas está invertido.")


@dataclass(frozen=True, kw_only=True)
class IntervaloValor(Request):
    inicial: Annotated[Decimal | None, J("valorInicial")] = None
    final: Annotated[Decimal | None, J("valorFinal")] = None

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.inicial is not None and self.final is not None and self.inicial > self.final:
            raise IntegraRequestError("O intervalo de valores está invertido.")


@dataclass(frozen=True, kw_only=True)
class FiltroPagamentos(Request):
    """The filters shared by the list and the count; they can be combined."""

    numeros_documento: Annotated[
        tuple[str, ...], J("numeroDocumentoLista", pattern=r"\d{1,17}")
    ] = ()
    codigos_receita: Annotated[tuple[str, ...], J("codigoReceitaLista", pattern=r"\d{1,4}")] = ()
    intervalo_data_arrecadacao: Annotated[IntervaloData | None, J("intervaloDataArrecadacao")] = (
        None
    )
    intervalo_valor_total: Annotated[IntervaloValor | None, J("intervaloValorTotalDocumento")] = (
        None
    )
    codigos_tipo_documento: Annotated[
        tuple[str, ...], J("codigoTipoDocumentoLista", pattern=r"\d{1,2}")
    ] = ()


@dataclass(frozen=True, kw_only=True)
class ConsultarPagamentos(FiltroPagamentos):
    """PAGAMENTOS71: the page is mandatory (up to 100 documents, counting from 0)."""

    primeiro_da_pagina: Annotated[int, J("primeiroDaPagina", ge=0)] = 0
    tamanho_da_pagina: Annotated[int, J("tamanhoDaPagina", ge=1, le=100)] = 100


@dataclass(frozen=True, kw_only=True)
class ContarPagamentos(FiltroPagamentos):
    """CONTACONSDOCARRPG73: the same filters, answered with a number."""


# ---- responses ---------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class ExtensaoReceita(Model):
    codigo: Annotated[str, J("codigo")]
    descricao: Annotated[str | None, J("descricao")] = None


@dataclass(frozen=True, kw_only=True)
class Receita(Model):
    codigo: Annotated[str, J("codigo")]
    descricao: Annotated[str | None, J("descricao")] = None
    extensao: Annotated[ExtensaoReceita | None, J("extensaoReceita")] = None


@dataclass(frozen=True, kw_only=True)
class TipoDocumento(Model):
    codigo: Annotated[str, J("codigo")]
    descricao: Annotated[str | None, J("descricao")] = None
    descricao_abreviada: Annotated[str | None, J("descricaoAbreviada")] = None


@dataclass(frozen=True, kw_only=True)
class Desmembramento(Model):
    """One receita inside a collection document (a DAS carries several)."""

    sequencial: Annotated[str, J("sequencial")]
    receita_principal: Annotated[Receita | None, J("receitaPrincipal")] = None
    periodo_apuracao: Annotated[datetime | None, J("periodoApuracao", fmt=Fmt.ISO_DATETIME)] = None
    data_vencimento: Annotated[datetime | None, J("dataVencimento", fmt=Fmt.ISO_DATETIME)] = None
    valor_total: Annotated[Decimal | None, J("valorTotal")] = None
    valor_principal: Annotated[Decimal | None, J("valorPrincipal")] = None
    valor_multa: Annotated[Decimal | None, J("valorMulta")] = None
    valor_juros: Annotated[Decimal | None, J("valorJuros")] = None
    valor_saldo_total: Annotated[Decimal | None, J("valorSaldoTotal")] = None
    valor_saldo_principal: Annotated[Decimal | None, J("valorSaldoPrincipal")] = None
    valor_saldo_multa: Annotated[Decimal | None, J("valorSaldoMulta")] = None
    valor_saldo_juros: Annotated[Decimal | None, J("valorSaldoJuros")] = None
    cib: Annotated[str | None, J("cib")] = None


@dataclass(frozen=True, kw_only=True)
class DocumentoArrecadacao(Model):
    numero_documento: Annotated[str, J("numeroDocumento")]
    tipo: Annotated[TipoDocumento | None, J("tipo")] = None
    periodo_apuracao: Annotated[datetime | None, J("periodoApuracao", fmt=Fmt.ISO_DATETIME)] = None
    data_arrecadacao: Annotated[datetime | None, J("dataArrecadacao", fmt=Fmt.ISO_DATETIME)] = None
    data_vencimento: Annotated[datetime | None, J("dataVencimento", fmt=Fmt.ISO_DATETIME)] = None
    receita_principal: Annotated[Receita | None, J("receitaPrincipal")] = None
    referencia: Annotated[str | None, J("referencia")] = None
    valor_total: Annotated[Decimal | None, J("valorTotal")] = None
    valor_principal: Annotated[Decimal | None, J("valorPrincipal")] = None
    valor_multa: Annotated[Decimal | None, J("valorMulta")] = None
    valor_juros: Annotated[Decimal | None, J("valorJuros")] = None
    valor_saldo_total: Annotated[Decimal | None, J("valorSaldoTotal")] = None
    valor_saldo_principal: Annotated[Decimal | None, J("valorSaldoPrincipal")] = None
    valor_saldo_multa: Annotated[Decimal | None, J("valorSaldoMulta")] = None
    valor_saldo_juros: Annotated[Decimal | None, J("valorSaldoJuros")] = None
    desmembramentos: Annotated[tuple[Desmembramento, ...], J("desmembramentos")] = ()


def read_pagamentos(payload: Mapping[str, Any]) -> tuple[DocumentoArrecadacao, ...]:
    """PAGAMENTOS71: the `dados` is a list; a page without payments is an empty tuple."""

    dados = open_envelope(payload).dados
    return () if dados is None else DocumentoArrecadacao.parse_many(dados)


def read_contagem(payload: Mapping[str, Any]) -> int:
    """CONTACONSDOCARRPG73: the `dados` is the number of paid documents."""

    return read_int(open_envelope(payload).dados)


TYPED_SERVICES: tuple[TypedService, ...] = (
    TypedService("pagtoweb.pagamentos", ConsultarPagamentos, read_pagamentos),
    TypedService("pagtoweb.contagem", ContarPagamentos, read_contagem),
)
