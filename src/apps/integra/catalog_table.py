"""The Integra Contador registry as data: one row per production service.

Source: the official catalog of 15/10/2026 (99 services in production) and the page of each
service in the same documentation. Everything a caller may rely on is derived from this table
in `apps.integra.catalog`; nothing here talks to the network.

Columns: key, idSistema, idServico, verb, effect class, response format, label and the
documentation page (relative to .../api-integra-contador/pt/). `versao` is the
`versaoSistema` stated by that page or by its examples; `confirmada=False` marks the two services
(CCMEI 121 and PGMEI 21) where the documentation never states it: the version of the sibling
services is used until the first homologation call.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class Verb(StrEnum):
    """The five Integra Contador entry points. The service decides which one applies."""

    APOIAR = "Apoiar"
    CONSULTAR = "Consultar"
    DECLARAR = "Declarar"
    EMITIR = "Emitir"
    MONITORAR = "Monitorar"


class EffectClass(StrEnum):
    """What a call does to the taxpayer's situation (research report, section 1.3)."""

    READ = "A"  # pure reading
    READ_LEGAL = "B"  # reading that registers a legal effect (ciência da intimação)
    DOCUMENT = "C"  # issues a document without changing any situation
    GUIDE = "D"  # issues a payment guide (DAS, DARF, DAE)
    WRITE = "E"  # issues and writes (benefit update)
    DECLARE = "F"  # transmits a declaration or an option; changes the fiscal situation
    SUPPORT = "G"  # support and authentication; only creates a session token


class ResponseFormat(StrEnum):
    """What the useful part of `dados` is: structured JSON, or a base64 PDF/XML document."""

    JSON = "json"
    XML = "xml"
    PDF = "pdf"


@dataclass(frozen=True)
class Row:
    key: str
    id_sistema: str
    id_servico: str
    verb: Verb
    effect: EffectClass
    fmt: ResponseFormat
    label: str
    page: str
    versao: str = "1.0"
    confirmada: bool = True


A, B, C, D, E, F, G = (
    EffectClass.READ,
    EffectClass.READ_LEGAL,
    EffectClass.DOCUMENT,
    EffectClass.GUIDE,
    EffectClass.WRITE,
    EffectClass.DECLARE,
    EffectClass.SUPPORT,
)
JSON, XML, PDF = ResponseFormat.JSON, ResponseFormat.XML, ResponseFormat.PDF
APOIAR, CONSULTAR, DECLARAR, EMITIR, MONITORAR = (
    Verb.APOIAR,
    Verb.CONSULTAR,
    Verb.DECLARAR,
    Verb.EMITIR,
    Verb.MONITORAR,
)

_SN = "solucoes/integra-sn/"
_MEI = "solucoes/integra-mei/"
_DCTF = "solucoes/integra-dctfweb/"
_CAIXA = "solucoes/integra-caixapostal/"
_GEREN = "solucoes/integra-contador-gerenciador/"
_PGDASD = _SN + "pgdasd/servicos/"
_REGIME = _SN + "regime/servicos/"
_DEFIS = _SN + "defis/servicos/"
_PGMEI = _MEI + "pgmei/servicos/"
_CCMEI = _MEI + "ccmei/servicos/"
_DCTFWEB = _DCTF + "dctfweb/servicos/"
_MIT = _DCTF + "mit/servicos/"
_PROCURACOES = "solucoes/integra-procuracoes/procuracoes/servicos/"
_SICALC = "solucoes/integra-sicalc/sicalc/servicos/"
_SITFIS = "solucoes/integra-sitfis/sitfis/servicos/"
_PAGTOWEB = "solucoes/integra-pagamento/pagtoweb/servicos/"
_PNR = "solucoes/integra-redesim/pnrcontador/servicos/"
_EPROCESSO = "solucoes/integra-e-processo/eprocesso/servicos/"
_EVENTOS = _GEREN + "eventosatualizacao/servicos/"

# Rows outside the parcelamento modalities, in the order of the official catalog.
ROWS: tuple[Row, ...] = (
    # PGDASD (Simples Nacional)
    Row("pgdasd.transmitir", "PGDASD", "TRANSDECLARACAO11", DECLARAR, F, JSON,
        "Declaração mensal do Simples", _PGDASD + "entregar_declaracao_mensal_entrada"),
    Row("pgdasd.das", "PGDASD", "GERARDAS12", EMITIR, D, PDF,
        "DAS do Simples", _PGDASD + "gerar_das"),
    Row("pgdasd.declaracoes", "PGDASD", "CONSDECLARACAO13", CONSULTAR, A, JSON,
        "Declarações do Simples", _PGDASD + "consultar_declaracao_por_ano_pa"),
    Row("pgdasd.ultima_declaracao", "PGDASD", "CONSULTIMADECREC14", CONSULTAR, A, PDF,
        "Última declaração do Simples", _PGDASD + "consultar_ultima_declaracao_recibo"),
    Row("pgdasd.declaracao", "PGDASD", "CONSDECREC15", CONSULTAR, A, PDF,
        "Declaração do Simples", _PGDASD + "consultar_declaracao_recibo"),
    Row("pgdasd.extrato", "PGDASD", "CONSEXTRATO16", CONSULTAR, A, PDF,
        "Extrato do DAS", _PGDASD + "consultar_extrato_do_das"),
    Row("pgdasd.das_cobranca", "PGDASD", "GERARDASCOBRANCA17", EMITIR, D, PDF,
        "DAS de cobrança do Simples", _PGDASD + "gerar_dascobranca"),
    Row("pgdasd.das_processo", "PGDASD", "GERARDASPROCESSO18", EMITIR, D, PDF,
        "DAS de processo do Simples", _PGDASD + "gerar_dasprocesso"),
    Row("pgdasd.das_avulso", "PGDASD", "GERARDASAVULSO19", EMITIR, D, PDF,
        "DAS avulso do Simples", _PGDASD + "gerar_dasavulso"),
    # Regime de apuração de receitas
    Row("regimeapuracao.efetuar_opcao", "REGIMEAPURACAO", "EFETUAROPCAOREGIME101", DECLARAR, F,
        JSON, "Opção pelo regime de apuração", _REGIME + "efetuar_opcao"),
    Row("regimeapuracao.anos", "REGIMEAPURACAO", "CONSULTARANOSCALENDARIOS102", CONSULTAR, A,
        JSON, "Anos com opção de regime", _REGIME + "consultar_anos_calendarios"),
    Row("regimeapuracao.opcao", "REGIMEAPURACAO", "CONSULTAROPCAOREGIME103", CONSULTAR, A,
        JSON, "Opção de regime de apuração", _REGIME + "consultar_opcao"),
    Row("regimeapuracao.resolucao", "REGIMEAPURACAO", "CONSULTARRESOLUCAO104", CONSULTAR, A,
        JSON, "Resolução do regime de caixa", _REGIME + "consultar_resolucao"),
    # DEFIS
    Row("defis.transmitir", "DEFIS", "TRANSDECLARACAO141", DECLARAR, F, JSON,
        "Transmissão da DEFIS", _DEFIS + "entregar_entrada"),
    Row("defis.declaracoes", "DEFIS", "CONSDECLARACAO142", CONSULTAR, A, JSON,
        "Declarações DEFIS", _DEFIS + "consultar_declaracoes"),
    Row("defis.ultima_declaracao", "DEFIS", "CONSULTIMADECREC143", CONSULTAR, A, PDF,
        "Última declaração DEFIS", _DEFIS + "consultar_ultimadeclaracaorecibo"),
    Row("defis.declaracao", "DEFIS", "CONSDECREC144", CONSULTAR, A, PDF,
        "Declaração DEFIS", _DEFIS + "consultar_declaracaorecibo"),
    # PGMEI and CCMEI
    Row("pgmei.das", "PGMEI", "GERARDASPDF21", EMITIR, D, PDF,
        "DAS do MEI", _PGMEI + "gerar_das", confirmada=False),
    Row("pgmei.das_codigo_barras", "PGMEI", "GERARDASCODBARRA22", EMITIR, D, JSON,
        "Código de barras do DAS do MEI", _PGMEI + "gerar_das_cod_barras"),
    Row("pgmei.beneficio", "PGMEI", "ATUBENEFICIO23", EMITIR, E, JSON,
        "Benefício do MEI", _PGMEI + "atualizar_beneficio"),
    Row("pgmei.divida", "PGMEI", "DIVIDAATIVA24", CONSULTAR, A, JSON,
        "Dívida ativa do MEI", _PGMEI + "consultar_divida_ativa"),
    Row("ccmei.emitir", "CCMEI", "EMITIRCCMEI121", EMITIR, C, PDF,
        "Certificado do MEI", _CCMEI + "emitir_ccmei", confirmada=False),
    Row("ccmei.dados", "CCMEI", "DADOSCCMEI122", CONSULTAR, A, JSON,
        "Dados do certificado do MEI", _CCMEI + "consultar_dados_ccmei"),
    Row("ccmei.situacao_cadastral", "CCMEI", "CCMEISITCADASTRAL123", CONSULTAR, A, JSON,
        "Situação cadastral do MEI", _CCMEI + "consultar_situacao_cadastral_ccmei"),
    # DCTFWeb and MIT
    Row("dctfweb.guia", "DCTFWEB", "GERARGUIA31", EMITIR, D, PDF,
        "Guia da DCTFWeb", _DCTFWEB + "gerar_guia"),
    Row("dctfweb.recibo", "DCTFWEB", "CONSRECIBO32", CONSULTAR, A, PDF,
        "Recibo de transmissão DCTFWeb", _DCTFWEB + "consultar_recibo"),
    Row("dctfweb.declaracao_completa", "DCTFWEB", "CONSDECCOMPLETA33", CONSULTAR, A, PDF,
        "Relatório da declaração DCTFWeb", _DCTFWEB + "consultar_declaracao_completa"),
    Row("dctfweb.xml", "DCTFWEB", "CONSXMLDECLARACAO38", CONSULTAR, A, XML,
        "XML da declaração DCTFWeb", _DCTFWEB + "consultar_xml_declaracao"),
    Row("dctfweb.transmitir", "DCTFWEB", "TRANSDECLARACAO310", DECLARAR, F, JSON,
        "Transmissão da DCTFWeb", _DCTFWEB + "entregar_declaracao"),
    Row("dctfweb.guia_andamento", "DCTFWEB", "GERARGUIAANDAMENTO313", EMITIR, D, PDF,
        "Guia da DCTFWeb em andamento", _DCTFWEB + "gerar_guia_andamento"),
    Row("mit.encerrar", "MIT", "ENCAPURACAO314", DECLARAR, F, JSON,
        "Encerramento da apuração MIT", _MIT + "encerrar_apuracao"),
    Row("mit.situacao_encerramento", "MIT", "SITUACAOENC315", APOIAR, A, JSON,
        "Situação do encerramento MIT", _MIT + "consultar_situacao_encerramento"),
    Row("mit.apuracao", "MIT", "CONSAPURACAO316", CONSULTAR, A, JSON,
        "Apuração MIT", _MIT + "consultar_apuracao"),
    Row("mit.apuracoes", "MIT", "LISTAAPURACOES317", CONSULTAR, A, JSON,
        "Apurações MIT", _MIT + "consultar_apuracao_ano_mes"),
    # Procurações (note: the official page states versaoSistema "1", not "1.0")
    Row("procuracao.obter", "PROCURACOES", "OBTERPROCURACAO41", CONSULTAR, A, JSON,
        "Procuração eletrônica", _PROCURACOES + "obter_procuracao", versao="1"),
    # Sicalc (version 2.9; CONSOLIDAR54 is documented inside the page of service 51)
    Row("sicalc.darf", "SICALC", "CONSOLIDARGERARDARF51", EMITIR, D, PDF,
        "DARF do Sicalc", _SICALC + "consolidar_emitir_um_darf", versao="2.9"),
    Row("sicalc.receitas", "SICALC", "CONSULTAAPOIORECEITAS52", APOIAR, A, JSON,
        "Receitas do Sicalc", _SICALC + "apoio_consulta_receitas_do_sicalc", versao="2.9"),
    Row("sicalc.darf_codigo_barras", "SICALC", "GERARDARFCODBARRA53", EMITIR, D, JSON,
        "Código de barras do DARF", _SICALC + "consolidar_emitir_codbarras", versao="2.9"),
    Row("sicalc.consolidar", "SICALC", "CONSOLIDAR54", CONSULTAR, A, JSON,
        "Consolidação do débito", _SICALC + "consolidar_emitir_um_darf", versao="2.9"),
    # Caixa postal and DTE
    Row("caixapostal.mensagens", "CAIXAPOSTAL", "MSGCONTRIBUINTE61", CONSULTAR, A, JSON,
        "Mensagens do contribuinte",
        _CAIXA + "caixapostal/servicos/obter_lista_de_mensagens_por_contribuintes"),
    Row("caixapostal.detalhe", "CAIXAPOSTAL", "MSGDETALHAMENTO62", CONSULTAR, B, JSON,
        "Detalhe da mensagem",
        _CAIXA + "caixapostal/servicos/obter_detalhes_de_uma_mensagem_especifica"),
    Row("caixapostal.indicador", "CAIXAPOSTAL", "INNOVAMSG63", MONITORAR, A, JSON,
        "Indicador de mensagem nova",
        _CAIXA + "caixapostal/servicos/obter_indicador_de_novas_mensagens"),
    Row("dte.situacao", "DTE", "CONSULTASITUACAODTE111", CONSULTAR, A, JSON,
        "Situação do DTE", _CAIXA + "dte/servicos/obter_indicador_dte"),
    # Pagamentos
    Row("pagtoweb.pagamentos", "PAGTOWEB", "PAGAMENTOS71", CONSULTAR, A, JSON,
        "Pagamentos", _PAGTOWEB + "consulta_pagamento"),
    Row("pagtoweb.comprovante", "PAGTOWEB", "COMPARRECADACAO72", EMITIR, C, PDF,
        "Comprovante de arrecadação", _PAGTOWEB + "emite_comprovante_pagamento"),
    Row("pagtoweb.contagem", "PAGTOWEB", "CONTACONSDOCARRPG73", CONSULTAR, A, JSON,
        "Contagem de documentos pagos", _PAGTOWEB + "conta_consulta_pagamento"),
    # Gerenciador: Termo de Autorização and update events (free of charge)
    Row("autenticaprocurador.termo", "AUTENTICAPROCURADOR", "ENVIOXMLASSINADO81", APOIAR, G,
        JSON, "Termo de autorização",
        _GEREN + "autenticaprocurador/servicos/envio_de_xml_assinado"),
    Row("eventosatualizacao.solicitar_pf", "EVENTOSATUALIZACAO", "SOLICEVENTOSPF131", MONITORAR,
        A, JSON, "Solicitação de eventos de pessoa física", _EVENTOS + "solicitar_eventos_pf"),
    Row("eventosatualizacao.solicitar_pj", "EVENTOSATUALIZACAO", "SOLICEVENTOSPJ132", MONITORAR,
        A, JSON, "Solicitação de eventos de pessoa jurídica", _EVENTOS + "solicitar_eventos_pj"),
    Row("eventosatualizacao.obter_pf", "EVENTOSATUALIZACAO", "OBTEREVENTOSPF133", MONITORAR, A,
        JSON, "Eventos de pessoa física", _EVENTOS + "obter_eventos_pf"),
    Row("eventosatualizacao.obter_pj", "EVENTOSATUALIZACAO", "OBTEREVENTOSPJ134", MONITORAR, A,
        JSON, "Eventos de pessoa jurídica", _EVENTOS + "obter_eventos_pj"),
    # SITFIS (version 2.0)
    Row("sitfis.protocolo", "SITFIS", "SOLICITARPROTOCOLO91", APOIAR, A, JSON,
        "Protocolo da situação fiscal", _SITFIS + "apoiar_relatorio", versao="2.0"),
    Row("sitfis.relatorio", "SITFIS", "RELATORIOSITFIS92", EMITIR, C, PDF,
        "Relatório da situação fiscal", _SITFIS + "emitir_relatorio", versao="2.0"),
    # Pedido de renúncia de vínculo do contador (PNR)
    Row("pnrcontador.vinculos", "PNRCONTADOR", "CONSVINCULOS261", CONSULTAR, A, JSON,
        "Vínculos do contador", _PNR + "consultar_vinculos"),
    Row("pnrcontador.renunciar", "PNRCONTADOR", "SOLICRENUNCIA262", DECLARAR, F, JSON,
        "Renúncia de vínculo", _PNR + "solicitar_renuncia"),
    Row("pnrcontador.renuncias", "PNRCONTADOR", "CONSRENUNCIA263", CONSULTAR, A, JSON,
        "Renúncias do contador", _PNR + "consultar_renuncias"),
    Row("pnrcontador.comprovante_renuncia", "PNRCONTADOR", "COMPRENUNCIA264", EMITIR, C, PDF,
        "Comprovante de renúncia", _PNR + "emitir_comprovante"),
    Row("pnrcontador.situacao_renuncia", "PNRCONTADOR", "SITSOLICRENUNCIA265", CONSULTAR, A,
        JSON, "Situação da renúncia", _PNR + "situacao_solicitar_renuncia"),
    # e-Processo (version 2.0)
    Row("eprocesso.processos", "EPROCESSO", "CONSPROCPORINTER271", CONSULTAR, A, JSON,
        "Processos por interessado", _EPROCESSO + "consultar_processos", versao="2.0"),
)


@dataclass(frozen=True)
class Modalidade:
    """One parcelamento modality of the Simples Nacional or of the MEI."""

    slug: str  # in the key and in the documentation path
    id_sistema: str
    base: int  # the services are base0..base5: GERARDAS is base1, the four queries 2..5
    label: str  # completes the label of each operation


@dataclass(frozen=True)
class Operacao:
    slug: str
    id_servico: str
    posicao: int
    verb: Verb
    effect: EffectClass
    fmt: ResponseFormat
    label: str  # "{}" receives the label of the modality
    page: str


MODALIDADES: tuple[Modalidade, ...] = (
    Modalidade("parcsn", "PARCSN", 16, "Simples Nacional"),
    Modalidade("parcsn_esp", "PARCSN-ESP", 17, "Simples Nacional especial"),
    Modalidade("pertsn", "PERTSN", 18, "PERT-SN"),
    Modalidade("relpsn", "RELPSN", 19, "RELP-SN"),
    Modalidade("parcmei", "PARCMEI", 20, "MEI"),
    Modalidade("parcmei_esp", "PARCMEI-ESP", 21, "MEI especial"),
    Modalidade("pertmei", "PERTMEI", 22, "PERT-MEI"),
    Modalidade("relpmei", "RELPMEI", 23, "RELP-MEI"),
)

OPERACOES: tuple[Operacao, ...] = (
    Operacao("pedidos", "PEDIDOSPARC", 3, CONSULTAR, A, JSON,
             "Pedidos de parcelamento do {}", "consulta_pedidos"),
    Operacao("detalhe", "OBTERPARC", 4, CONSULTAR, A, JSON,
             "Detalhe de parcelamento do {}", "consulta_parcelamento"),
    Operacao("pagamento", "DETPAGTOPARC", 5, CONSULTAR, A, JSON,
             "Pagamento de parcela do {}", "consulta_detalhe_pagamento"),
    Operacao("parcelas", "PARCELASPARAGERAR", 2, CONSULTAR, A, JSON,
             "Parcelas disponíveis do {}", "consulta_parcelas_impressao"),
    Operacao("das", "GERARDAS", 1, EMITIR, D, PDF,
             "DAS de parcela do {}", "emite_das"),
)


def parcelamento_rows() -> tuple[Row, ...]:
    """The 40 parcelamento services, generated from the modality and operation tables."""

    return tuple(
        Row(
            key=f"parcelamento.{modalidade.slug}.{operacao.slug}",
            id_sistema=modalidade.id_sistema,
            id_servico=f"{operacao.id_servico}{modalidade.base * 10 + operacao.posicao}",
            verb=operacao.verb,
            effect=operacao.effect,
            fmt=operacao.fmt,
            label=operacao.label.format(modalidade.label),
            page=(
                f"solucoes/integra-parcelamento/{modalidade.slug}/servicos/{operacao.page}"
            ),
        )
        for modalidade in MODALIDADES
        for operacao in OPERACOES
    )
