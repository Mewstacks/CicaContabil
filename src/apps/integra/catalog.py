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


@dataclass(frozen=True)
class ServiceSpec:
    key: str
    id_sistema: str
    id_servico: str
    versao_sistema: str
    verb: Verb
    label: str
    billable: bool


def _spec(
    key: str,
    id_sistema: str,
    id_servico: str,
    verb: Verb,
    label: str,
    *,
    versao: str = "1.0",
    billable: bool = True,
) -> ServiceSpec:
    return ServiceSpec(
        key=key,
        id_sistema=id_sistema,
        id_servico=id_servico,
        versao_sistema=versao,
        verb=verb,
        label=label,
        billable=billable,
    )


# A closed registry, deliberately shaped like intelligence.connectors.QUERY_REGISTRY: a
# caller names a service, never an endpoint or a payload of its own. That is what keeps the
# ODBC adapter free of any injection surface, and the same reasoning applies to a paid API
# where a forged request costs the office money.
SERVICES: dict[str, ServiceSpec] = {
    # Nothing else is authorized without an electronic power of attorney in e-CAC.
    "procuracao.obter": _spec(
        "procuracao.obter",
        "PROCURACOES",
        "OBTERPROCURACAO41",
        Verb.CONSULTAR,
        "Procuração eletrônica",
    ),
    "dte.situacao": _spec(
        "dte.situacao",
        "DTE",
        "CONSULTASITUACAODTE111",
        Verb.CONSULTAR,
        "Situação do DTE",
    ),
    # The cheap poll: it only answers whether anything new arrived.
    "caixapostal.indicador": _spec(
        "caixapostal.indicador",
        "CAIXAPOSTAL",
        "INNOVAMSG63",
        Verb.MONITORAR,
        "Indicador de mensagem nova",
        billable=False,
    ),
    "caixapostal.mensagens": _spec(
        "caixapostal.mensagens",
        "CAIXAPOSTAL",
        "MSGCONTRIBUINTE61",
        Verb.CONSULTAR,
        "Mensagens do contribuinte",
    ),
    "caixapostal.detalhe": _spec(
        "caixapostal.detalhe",
        "CAIXAPOSTAL",
        "MSGDETALHAMENTO62",
        Verb.CONSULTAR,
        "Detalhe da mensagem",
    ),
    "dctfweb.guia": _spec("dctfweb.guia", "DCTFWEB", "GERARGUIA31", Verb.EMITIR, "Guia da DCTFWeb"),
    "dctfweb.xml": _spec(
        "dctfweb.xml",
        "DCTFWEB",
        "CONSXMLDECLARACAO38",
        Verb.CONSULTAR,
        "XML da declaração DCTFWeb",
    ),
    "pgdasd.das": _spec("pgdasd.das", "PGDASD", "GERARDAS12", Verb.EMITIR, "DAS do Simples"),
    "pgmei.das": _spec("pgmei.das", "PGMEI", "GERARDASPDF21", Verb.EMITIR, "DAS do MEI"),
    "pgmei.divida": _spec(
        "pgmei.divida", "PGMEI", "DIVIDAATIVA24", Verb.CONSULTAR, "Dívida ativa do MEI"
    ),
    # SITFIS answers in two steps: ask for a protocol, then collect the report.
    "sitfis.protocolo": _spec(
        "sitfis.protocolo",
        "SITFIS",
        "SOLICITARPROTOCOLO91",
        Verb.APOIAR,
        "Protocolo da situação fiscal",
        billable=False,
    ),
    "sitfis.relatorio": _spec(
        "sitfis.relatorio",
        "SITFIS",
        "RELATORIOSITFIS92",
        Verb.EMITIR,
        "Relatório da situação fiscal",
    ),
}


def service(key: str) -> ServiceSpec:
    try:
        return SERVICES[key]
    except KeyError as exc:
        raise ValueError(f"Serviço {key!r} não está no catálogo.") from exc
