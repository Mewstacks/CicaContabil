"""MIT (Módulo de Inclusão de Tributos da DCTFWeb): consultas de apuração.

Serviços 315 (situação do encerramento, gratuito, consulta assíncrona), 316 (apuração) e 317
(lista de apurações por ano ou mês). Fonte de todos os nomes de campo:
https://apicenter.estaleiro.serpro.gov.br/documentacao/api-integra-contador/pt/solucoes/
integra-dctfweb/mit/servicos/ (consultar_situacao_encerramento, consultar_apuracao,
consultar_apuracao_ano_mes) e dados_de_dominio (situacaoApuracao: 1 em edição com pendências,
2 em edição, 3 encerrada, 4 encerramento em curso).

Decisões não óbvias:

* `dadosApuracaoMit` (316): a tabela diz "Array de Object", o exemplo oficial traz um objeto, e
  é o objeto que o modelo lê. Os nomes dentro dele começam com maiúscula (`PeriodoApuracao`).
  A página fala em "pendências" sem documentar a estrutura: só `situacaoApuracao` e
  `textoSituacao` são obrigatórios, e `dadosApuracaoMit` é opcional.
* Dentro de `dadosApuracaoMit`, só o que a tabela marca como obrigatório sempre (sim, sem
  condição) é obrigatório; o resto depende de regras de negócio (por exemplo `Debitos` só
  existe com movimento) e fica opcional. `TransmissaoImediata` aparece no nível de
  `dadosApuracaoMit`, como no exemplo.
* 315 é consulta assíncrona: `situacaoApuracao` 4 (encerramento em curso) é uma resposta 200
  válida, sem `dataEncerramento`; quem chama decide esperar e consultar de novo.
* `periodoApuracao` (317) é String na tabela e número no exemplo: o leitor aceita os dois.
* Sem apuração, o Serpro responde com mensagem de erro (MSG_0023, 0025), não com `dados` vazio.
* Só o status 200 é aceito: as páginas não documentam 202 nem 204 para estes serviços.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from apps.integra.typed.base import Fmt, J, Model, Request, open_envelope
from apps.integra.typed.registry import TypedService

# ---- requests ----------------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class ConsultarSituacaoEncerramento(Request):
    """SITUACAOENC315: o protocolo devolvido pelo serviço Encerrar Apuração."""

    protocolo_encerramento: Annotated[
        str, J("protocoloEncerramento", pattern=r"[A-Za-z0-9+/=_-]{1,100}")
    ]


@dataclass(frozen=True, kw_only=True)
class ConsultarApuracao(Request):
    """CONSAPURACAO316: o idApuracao devolvido pelo serviço de encerramento."""

    id_apuracao: Annotated[int, J("idApuracao", ge=0)]


@dataclass(frozen=True, kw_only=True)
class ListarApuracoes(Request):
    """LISTAAPURACOES317: as apurações de um ano, ou de um mês, ou de uma situação."""

    ano_apuracao: Annotated[int, J("anoApuracao", ge=2000, le=2100)]
    mes_apuracao: Annotated[int | None, J("mesApuracao", ge=1, le=12)] = None
    situacao_apuracao: Annotated[int | None, J("situacaoApuracao", ge=1, le=4)] = None


# ---- 315: closing status -----------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class SituacaoEncerramento(Model):
    id_apuracao: Annotated[int, J("idApuracao")]
    situacao_apuracao: Annotated[int, J("situacaoApuracao")]
    texto_situacao: Annotated[str, J("textoSituacao")]
    avisos_dctf: Annotated[tuple[str, ...], J("avisosDctf")] = ()
    data_encerramento: Annotated[date | None, J("dataEncerramento", fmt=Fmt.DATE8)] = None


# ---- 316: apuracao -----------------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class PeriodoApuracao(Model):
    mes_apuracao: Annotated[int, J("MesApuracao")]
    ano_apuracao: Annotated[int, J("AnoApuracao")]


@dataclass(frozen=True, kw_only=True)
class EventoEspecial(Model):
    """Tipo: 1 extinção, 2 fusão, 3 cisão total, 4 cisão parcial, 5 e 6 incorporação."""

    id_evento: Annotated[int, J("IdEvento")]
    dia_evento: Annotated[int, J("DiaEvento")]
    tipo_evento: Annotated[int, J("TipoEvento")]


@dataclass(frozen=True, kw_only=True)
class TelefoneResponsavel(Model):
    ddd: Annotated[str, J("Ddd")]
    num_telefone: Annotated[str, J("NumTelefone")]


@dataclass(frozen=True, kw_only=True)
class RegistroCrc(Model):
    uf_registro: Annotated[str, J("UfRegistro")]
    num_registro: Annotated[str, J("NumRegistro")]


@dataclass(frozen=True, kw_only=True)
class ResponsavelApuracao(Model):
    cpf_responsavel: Annotated[str, J("CpfResponsavel")]
    tel_responsavel: Annotated[TelefoneResponsavel | None, J("TelResponsavel")] = None
    email_responsavel: Annotated[str | None, J("EmailResponsavel")] = None
    registro_crc: Annotated[RegistroCrc | None, J("RegistroCrc")] = None


@dataclass(frozen=True, kw_only=True)
class DadosIniciais(Model):
    """`qualificacao_pj` 1 a 12, `tributacao_lucro` 1 a 7, `variacoes_monetarias` 1 a 3 e
    `regime_pis_cofins` 1 a 4, como nas tabelas da página."""

    sem_movimento: Annotated[bool, J("SemMovimento")]
    qualificacao_pj: Annotated[int, J("QualificacaoPj")]
    responsavel_apuracao: Annotated[ResponsavelApuracao, J("ResponsavelApuracao")]
    tributacao_lucro: Annotated[int | None, J("TributacaoLucro")] = None
    variacoes_monetarias: Annotated[int | None, J("VariacoesMonetarias")] = None
    regime_pis_cofins: Annotated[int | None, J("RegimePisCofins")] = None


@dataclass(frozen=True, kw_only=True)
class Debito(Model):
    id_debito: Annotated[int, J("IdDebito")]
    codigo_debito: Annotated[str, J("CodigoDebito")]
    valor_debito: Annotated[Decimal, J("ValorDebito")]
    id_evento_debito: Annotated[int | None, J("IdEventoDebito")] = None
    pa_debito: Annotated[int | None, J("PaDebito")] = None
    ano_postergado: Annotated[int | None, J("AnoPostergado")] = None
    trim_postergado: Annotated[int | None, J("TrimPostergado")] = None
    ano_debito: Annotated[int | None, J("AnoDebito")] = None
    cnpj_estabelecimento: Annotated[str | None, J("CnpjEstabelecimento")] = None
    cnpj_incorporacao: Annotated[str | None, J("CnpjIncorporacao")] = None
    cnpj_scp: Annotated[str | None, J("CnpjScp")] = None
    codigo_municipio_ouro: Annotated[str | None, J("CodigoMunicipioOuro")] = None


@dataclass(frozen=True, kw_only=True)
class GrupoDebitos(Model):
    """Os débitos de um grupo de tributo; `apos_evento` são os de fato gerador depois do evento."""

    lista_debitos: Annotated[tuple[Debito, ...], J("ListaDebitos")] = ()
    lista_debitos_apos_evento: Annotated[tuple[Debito, ...], J("ListaDebitosAposEvento")] = ()


@dataclass(frozen=True, kw_only=True)
class Debitos(Model):
    balanco_lucro_real: Annotated[bool | None, J("BalancoLucroReal")] = None
    irpj: Annotated[GrupoDebitos | None, J("Irpj")] = None
    csll: Annotated[GrupoDebitos | None, J("Csll")] = None
    irrf: Annotated[GrupoDebitos | None, J("Irrf")] = None
    ipi: Annotated[GrupoDebitos | None, J("Ipi")] = None
    iof: Annotated[GrupoDebitos | None, J("Iof")] = None
    pis_pasep: Annotated[GrupoDebitos | None, J("PisPasep")] = None
    cofins: Annotated[GrupoDebitos | None, J("Cofins")] = None
    contribuicoes_diversas: Annotated[GrupoDebitos | None, J("ContribuicoesDiversas")] = None
    cpss: Annotated[GrupoDebitos | None, J("Cpss")] = None
    ret_pagamento_unificado: Annotated[GrupoDebitos | None, J("RetPagamentoUnificado")] = None


@dataclass(frozen=True, kw_only=True)
class DebitoSuspenso(Model):
    id_debito_suspenso: Annotated[int, J("IdDebitoSuspenso")]
    valor_suspenso: Annotated[Decimal, J("ValorSuspenso")]


@dataclass(frozen=True, kw_only=True)
class Suspensao(Model):
    """Tipo: 1 administrativa, 2 judicial (só a judicial tem motivo, decisão e vara)."""

    tipo_suspensao: Annotated[int, J("TipoSuspensao")]
    numero_processo: Annotated[str, J("NumeroProcesso")]
    motivo_suspensao: Annotated[int | None, J("MotivoSuspensao")] = None
    com_deposito: Annotated[bool | None, J("ComDeposito")] = None
    processo_terceiro: Annotated[bool | None, J("ProcessoTerceiro")] = None
    data_decisao: Annotated[date | None, J("DataDecisao", fmt=Fmt.DATE8)] = None
    vara_judiciaria: Annotated[int | None, J("VaraJudiciaria")] = None
    codigo_municipio_sj: Annotated[str | None, J("CodigoMunicipioSj")] = None
    lista_debitos_suspensos: Annotated[tuple[DebitoSuspenso, ...], J("ListaDebitosSuspensos")] = ()


@dataclass(frozen=True, kw_only=True)
class DadosApuracaoMit(Model):
    periodo_apuracao: Annotated[PeriodoApuracao, J("PeriodoApuracao")]
    dados_iniciais: Annotated[DadosIniciais, J("DadosIniciais")]
    lista_eventos_especiais: Annotated[tuple[EventoEspecial, ...], J("ListaEventosEspeciais")] = ()
    debitos: Annotated[Debitos | None, J("Debitos")] = None
    lista_suspensoes: Annotated[tuple[Suspensao, ...], J("ListaSuspensoes")] = ()
    transmissao_imediata: Annotated[bool | None, J("TransmissaoImediata")] = None


@dataclass(frozen=True, kw_only=True)
class Apuracao(Model):
    situacao_apuracao: Annotated[int, J("situacaoApuracao")]
    texto_situacao: Annotated[str, J("textoSituacao")]
    dados_apuracao_mit: Annotated[DadosApuracaoMit | None, J("dadosApuracaoMit")] = None


# ---- 317: list of apuracoes --------------------------------------------------------------


@dataclass(frozen=True, kw_only=True)
class ApuracaoResumo(Model):
    periodo_apuracao: Annotated[int, J("periodoApuracao", fmt=Fmt.YEAR_MONTH)]
    id_apuracao: Annotated[int, J("idApuracao")]
    situacao: Annotated[int, J("situacao")]
    data_encerramento: Annotated[date | None, J("dataEncerramento", fmt=Fmt.DATE8)] = None
    evento_especial: Annotated[bool | None, J("eventoEspecial")] = None
    valor_total_apurado: Annotated[Decimal | None, J("valorTotalApurado")] = None


@dataclass(frozen=True, kw_only=True)
class ApuracoesDoPeriodo(Model):
    apuracoes: Annotated[tuple[ApuracaoResumo, ...], J("Apuracoes")] = ()


def read_situacao_encerramento(payload: Mapping[str, Any]) -> SituacaoEncerramento:
    """SITUACAOENC315: a situação do encerramento (4 = em curso, 3 = encerrada)."""

    return SituacaoEncerramento.parse(open_envelope(payload).dados)


def read_apuracao(payload: Mapping[str, Any]) -> Apuracao:
    """CONSAPURACAO316: a apuração, com os dados do arquivo de importação."""

    return Apuracao.parse(open_envelope(payload).dados)


def read_apuracoes(payload: Mapping[str, Any]) -> ApuracoesDoPeriodo:
    """LISTAAPURACOES317: as apurações do ano ou do mês pedido."""

    return ApuracoesDoPeriodo.parse(open_envelope(payload).dados)


TYPED_SERVICES: tuple[TypedService, ...] = (
    TypedService(
        "mit.situacao_encerramento", ConsultarSituacaoEncerramento, read_situacao_encerramento
    ),
    TypedService("mit.apuracao", ConsultarApuracao, read_apuracao),
    TypedService("mit.apuracoes", ListarApuracoes, read_apuracoes),
)
