"""CCMEI: data of the MEI certificate (122) and registration status of MEI CNPJs (123).

Source: https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/
integra-mei/ccmei/ (servicos/consultar_dados_ccmei, consultar_situacao_cadastral_ccmei and the
two exemplos/retorno_* pages). The emission of the certificate (PDF) is not read here.

Decisions that are not obvious:

* Neither service takes `dados` ("Não se aplica"; the example sends ""), so there is no request.
* The table names `qrcode` and `PeriodosMei` (an object); the example uses `qrCode` and
  `periodosMei` (a list of periods, with a datetime text in `dataInicio`). The example is followed
  for the periods; both spellings of the QR code are read. The QR code is the base64 text of an
  image, kept as `str` and never decoded.
* `cep` is Number in the table and text in the example: it is kept as text with eight digits.
* The `dados` of 123 is a list of CNPJs; an empty list (CPF without MEI) is an empty tuple.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from apps.integra.typed.base import Fmt, J, Model, open_envelope
from apps.integra.typed.registry import TypedService


def _cep(raw: Any) -> str:
    if isinstance(raw, bool) or not isinstance(raw, str | int):
        raise ValueError("CEP inválido")
    return f"{raw:08d}" if isinstance(raw, int) else raw


@dataclass(frozen=True, kw_only=True)
class Empresario(Model):
    nome_civil: Annotated[str, J("nomeCivil")]
    nome_social: Annotated[str | None, J("nomeSocial")] = None
    cpf: Annotated[str, J("cpf")]


@dataclass(frozen=True, kw_only=True)
class EnderecoComercial(Model):
    cep: Annotated[str, J("cep", parse=_cep)]
    logradouro: Annotated[str | None, J("logradouro")] = None
    numero: Annotated[str, J("numero")]
    complemento: Annotated[str | None, J("complemento")] = None
    bairro: Annotated[str, J("bairro")]
    municipio: Annotated[str, J("municipio")]
    uf: Annotated[str, J("uf")]


@dataclass(frozen=True, kw_only=True)
class PeriodoMei(Model):
    indice: Annotated[int, J("indice")]
    data_inicio: Annotated[date | None, J("dataInicio", fmt=Fmt.ISO_DATE)] = None
    data_fim: Annotated[date | None, J("dataFim", fmt=Fmt.ISO_DATE)] = None


@dataclass(frozen=True, kw_only=True)
class Enquadramento(Model):
    periodos_mei: Annotated[tuple[PeriodoMei, ...], J("periodosMei")] = ()
    situacao: Annotated[str, J("situacao")]
    optante_mei: Annotated[bool, J("optanteMei")]


@dataclass(frozen=True, kw_only=True)
class Ocupacao(Model):
    """The main occupation and each secondary one have the same fields."""

    descricao_ocupacao: Annotated[str, J("descricaoOcupacao")]
    codigo_cnae: Annotated[str | None, J("codigoCNAE")] = None
    descricao_cnae: Annotated[str | None, J("descricaoCNAE")] = None


@dataclass(frozen=True, kw_only=True)
class Atividade(Model):
    formas_atuacao: Annotated[tuple[str, ...], J("formasAtuacao")] = ()
    ocupacao_principal: Annotated[Ocupacao | None, J("ocupacaoPrincipal")] = None
    ocupacoes_secundarias: Annotated[tuple[Ocupacao, ...], J("ocupacoesSecundarias")] = ()
    optante_mei: Annotated[bool | None, J("optanteMei")] = None


@dataclass(frozen=True, kw_only=True)
class TermoCienciaDispensa(Model):
    titulo: Annotated[str, J("titulo")]
    texto: Annotated[str | None, J("texto")] = None


@dataclass(frozen=True, kw_only=True)
class DadosCcmei(Model):
    cnpj: Annotated[str, J("cnpj")]
    empresario: Annotated[Empresario | None, J("empresario")] = None
    data_inicio_atividades: Annotated[
        date | None, J("dataInicioAtividades", fmt=Fmt.ISO_DATE)
    ] = None
    nome_empresarial: Annotated[str | None, J("nomeEmpresarial")] = None
    capital_social: Annotated[Decimal | None, J("capitalSocial")] = None
    situacao_cadastral_vigente: Annotated[str | None, J("situacaoCadastralVigente")] = None
    data_inicio_situacao_cadastral: Annotated[
        date | None, J("dataInicioSituacaoCadastral", fmt=Fmt.ISO_DATE)
    ] = None
    endereco_comercial: Annotated[EnderecoComercial | None, J("enderecoComercial")] = None
    enquadramento: Annotated[Enquadramento | None, J("enquadramento")] = None
    atividade: Annotated[Atividade | None, J("atividade")] = None
    termo_ciencia_dispensa: Annotated[
        TermoCienciaDispensa | None, J("termoCienciaDispensa")
    ] = None
    qr_code: Annotated[str | None, J("qrCode")] = None


@dataclass(frozen=True, kw_only=True)
class SituacaoCnpj(Model):
    cnpj: Annotated[str, J("cnpj")]
    situacao: Annotated[str | None, J("situacao")] = None
    enquadrado_mei: Annotated[bool | None, J("enquadradoMei")] = None


def read_dados(payload: Mapping[str, Any]) -> DadosCcmei:
    """DADOSCCMEI122: the data of the certificate of the CNPJ."""

    dados = open_envelope(payload).dados
    if isinstance(dados, dict) and "qrCode" not in dados and "qrcode" in dados:
        dados = {**dados, "qrCode": dados["qrcode"]}
    return DadosCcmei.parse(dados)


def read_situacoes(payload: Mapping[str, Any]) -> tuple[SituacaoCnpj, ...]:
    """CCMEISITCADASTRAL123: the MEI CNPJs of a CPF; none is an empty tuple."""

    return SituacaoCnpj.parse_many(open_envelope(payload).dados)


TYPED_SERVICES: tuple[TypedService, ...] = (
    TypedService("ccmei.dados", None, read_dados),
    TypedService("ccmei.situacao_cadastral", None, read_situacoes),
)
