"""T10.1: the table-driven registry holds exactly the 99 production services of the official
Integra Contador catalog (15/10/2026), classified by effect, with the safe defaults of the
research report (docs/pesquisa/serpro-integra-contador-mcp.md, section 1.3 and appendix A)."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

import pytest

from apps.integra.catalog import (
    SERVICES,
    EffectClass,
    ResponseFormat,
    ServiceSpec,
    Verb,
    copilot_services,
    service,
    service_by_ids,
    services_by_effect,
)
from apps.integra.catalog_check import OfficialStatus, parse_catalog_html

OFFICIAL_PAGE = (
    Path(__file__).parent / "fixtures" / "integra" / "catalogo_de_servicos_2026-10-15.html"
)

# The 19 keys that existed before E10. Callers (hub tasks, views, platform form) name these.
LEGACY_KEYS: dict[str, tuple[str, str, Verb, str, bool]] = {
    "procuracao.obter": (
        "PROCURACOES", "OBTERPROCURACAO41", Verb.CONSULTAR, "Procuração eletrônica", True
    ),
    "dte.situacao": ("DTE", "CONSULTASITUACAODTE111", Verb.CONSULTAR, "Situação do DTE", True),
    "caixapostal.indicador": (
        "CAIXAPOSTAL", "INNOVAMSG63", Verb.MONITORAR, "Indicador de mensagem nova", False
    ),
    "caixapostal.mensagens": (
        "CAIXAPOSTAL", "MSGCONTRIBUINTE61", Verb.CONSULTAR, "Mensagens do contribuinte", True
    ),
    "caixapostal.detalhe": (
        "CAIXAPOSTAL", "MSGDETALHAMENTO62", Verb.CONSULTAR, "Detalhe da mensagem", True
    ),
    "dctfweb.guia": ("DCTFWEB", "GERARGUIA31", Verb.EMITIR, "Guia da DCTFWeb", True),
    "dctfweb.xml": (
        "DCTFWEB", "CONSXMLDECLARACAO38", Verb.CONSULTAR, "XML da declaração DCTFWeb", True
    ),
    "dctfweb.recibo": (
        "DCTFWEB", "CONSRECIBO32", Verb.CONSULTAR, "Recibo de transmissão DCTFWeb", True
    ),
    "dctfweb.declaracao_completa": (
        "DCTFWEB", "CONSDECCOMPLETA33", Verb.CONSULTAR, "Relatório da declaração DCTFWeb", True
    ),
    "parcelamento.parcsn.pedidos": (
        "PARCSN", "PEDIDOSPARC163", Verb.CONSULTAR,
        "Pedidos de parcelamento do Simples Nacional", True,
    ),
    "parcelamento.parcsn.detalhe": (
        "PARCSN", "OBTERPARC164", Verb.CONSULTAR,
        "Detalhe de parcelamento do Simples Nacional", True,
    ),
    "parcelamento.parcsn.pagamento": (
        "PARCSN", "DETPAGTOPARC165", Verb.CONSULTAR,
        "Pagamento de parcela do Simples Nacional", True,
    ),
    "parcelamento.parcsn.parcelas": (
        "PARCSN", "PARCELASPARAGERAR162", Verb.CONSULTAR,
        "Parcelas disponíveis do Simples Nacional", True,
    ),
    "parcelamento.parcsn.das": (
        "PARCSN", "GERARDAS161", Verb.EMITIR, "DAS de parcela do Simples Nacional", True
    ),
    "pgdasd.das": ("PGDASD", "GERARDAS12", Verb.EMITIR, "DAS do Simples", True),
    "pgmei.das": ("PGMEI", "GERARDASPDF21", Verb.EMITIR, "DAS do MEI", True),
    "pgmei.divida": ("PGMEI", "DIVIDAATIVA24", Verb.CONSULTAR, "Dívida ativa do MEI", True),
    "sitfis.protocolo": (
        "SITFIS", "SOLICITARPROTOCOLO91", Verb.APOIAR, "Protocolo da situação fiscal", False
    ),
    "sitfis.relatorio": (
        "SITFIS", "RELATORIOSITFIS92", Verb.EMITIR, "Relatório da situação fiscal", True
    ),
}

PARCELAMENTO_MODALITIES = {
    "PARCSN": 16, "PARCSN-ESP": 17, "PERTSN": 18, "RELPSN": 19,
    "PARCMEI": 20, "PARCMEI-ESP": 21, "PERTMEI": 22, "RELPMEI": 23,
}
PARCELAMENTO_READS = ("PARCELASPARAGERAR", "PEDIDOSPARC", "OBTERPARC", "DETPAGTOPARC")

# Appendix A of the research report: read-only allowlist (68), by (idSistema, idServico).
ALLOWLIST = {
    ("PGDASD", "CONSDECLARACAO13"), ("PGDASD", "CONSULTIMADECREC14"),
    ("PGDASD", "CONSDECREC15"), ("PGDASD", "CONSEXTRATO16"),
    ("REGIMEAPURACAO", "CONSULTARANOSCALENDARIOS102"),
    ("REGIMEAPURACAO", "CONSULTAROPCAOREGIME103"), ("REGIMEAPURACAO", "CONSULTARRESOLUCAO104"),
    ("DEFIS", "CONSDECLARACAO142"), ("DEFIS", "CONSULTIMADECREC143"),
    ("DEFIS", "CONSDECREC144"),
    ("PGMEI", "DIVIDAATIVA24"),
    ("CCMEI", "DADOSCCMEI122"), ("CCMEI", "CCMEISITCADASTRAL123"),
    ("DCTFWEB", "CONSRECIBO32"), ("DCTFWEB", "CONSDECCOMPLETA33"),
    ("DCTFWEB", "CONSXMLDECLARACAO38"),
    ("MIT", "CONSAPURACAO316"), ("MIT", "LISTAAPURACOES317"), ("MIT", "SITUACAOENC315"),
    ("PROCURACOES", "OBTERPROCURACAO41"),
    ("SICALC", "CONSOLIDAR54"), ("SICALC", "CONSULTAAPOIORECEITAS52"),
    ("CAIXAPOSTAL", "MSGCONTRIBUINTE61"), ("CAIXAPOSTAL", "INNOVAMSG63"),
    ("DTE", "CONSULTASITUACAODTE111"),
    ("PAGTOWEB", "PAGAMENTOS71"), ("PAGTOWEB", "CONTACONSDOCARRPG73"),
    ("PNRCONTADOR", "CONSVINCULOS261"), ("PNRCONTADOR", "CONSRENUNCIA263"),
    ("PNRCONTADOR", "SITSOLICRENUNCIA265"),
    ("EPROCESSO", "CONSPROCPORINTER271"),
    ("EVENTOSATUALIZACAO", "SOLICEVENTOSPF131"), ("EVENTOSATUALIZACAO", "SOLICEVENTOSPJ132"),
    ("EVENTOSATUALIZACAO", "OBTEREVENTOSPF133"), ("EVENTOSATUALIZACAO", "OBTEREVENTOSPJ134"),
    ("SITFIS", "SOLICITARPROTOCOLO91"),
} | {
    (modalidade, f"{nome}{base * 10 + posicao}")
    for modalidade, base in PARCELAMENTO_MODALITIES.items()
    for nome, posicao in zip(PARCELAMENTO_READS, (2, 3, 4, 5), strict=True)
}

# Charged as "Emitir" but with read-only effect: the report leaves them optional. SITFIS 92 is
# released (the cross-check "debts x paid guides" needs it); the other three stay off.
OPTIONAL_RELEASED = {("SITFIS", "RELATORIOSITFIS92")}
OPTIONAL_HELD = {
    ("PAGTOWEB", "COMPARRECADACAO72"),
    ("CCMEI", "EMITIRCCMEI121"),
    ("PNRCONTADOR", "COMPRENUNCIA264"),
}

# Blocklist (27): legal effect, writes, guides, declarations and the authentication token.
BLOCKLIST = {
    ("CAIXAPOSTAL", "MSGDETALHAMENTO62"),
    ("AUTENTICAPROCURADOR", "ENVIOXMLASSINADO81"),
    ("PGMEI", "ATUBENEFICIO23"),
    ("PGDASD", "GERARDAS12"), ("PGDASD", "GERARDASCOBRANCA17"),
    ("PGDASD", "GERARDASPROCESSO18"), ("PGDASD", "GERARDASAVULSO19"),
    ("PGMEI", "GERARDASPDF21"), ("PGMEI", "GERARDASCODBARRA22"),
    ("DCTFWEB", "GERARGUIA31"), ("DCTFWEB", "GERARGUIAANDAMENTO313"),
    ("SICALC", "CONSOLIDARGERARDARF51"), ("SICALC", "GERARDARFCODBARRA53"),
    ("PGDASD", "TRANSDECLARACAO11"), ("DEFIS", "TRANSDECLARACAO141"),
    ("DCTFWEB", "TRANSDECLARACAO310"), ("MIT", "ENCAPURACAO314"),
    ("REGIMEAPURACAO", "EFETUAROPCAOREGIME101"), ("PNRCONTADOR", "SOLICRENUNCIA262"),
} | {
    (modalidade, f"GERARDAS{base * 10 + 1}")
    for modalidade, base in PARCELAMENTO_MODALITIES.items()
}


def _ids(spec: ServiceSpec) -> tuple[str, str]:
    return spec.id_sistema, spec.id_servico


def _official_production() -> dict[tuple[str, str], str]:
    rows = parse_catalog_html(OFFICIAL_PAGE.read_text(encoding="utf-8"))
    return {
        (row.id_sistema, row.id_servico): row.tipo
        for row in rows
        if row.status is OfficialStatus.PRODUCTION
    }


def test_appendix_a_lists_add_up_to_99() -> None:
    assert len(ALLOWLIST) == 68
    assert len(OPTIONAL_RELEASED | OPTIONAL_HELD) == 4
    assert len(BLOCKLIST) == 27
    assert not (ALLOWLIST & BLOCKLIST)
    assert not ((OPTIONAL_RELEASED | OPTIONAL_HELD) & (ALLOWLIST | BLOCKLIST))


def test_registry_is_exactly_the_99_production_services_of_the_official_catalog() -> None:
    official = _official_production()

    assert len(official) == 99
    assert len(SERVICES) == 99
    assert {_ids(spec) for spec in SERVICES.values()} == set(official)


def test_each_key_and_each_official_id_pair_appears_once() -> None:
    pairs = [_ids(spec) for spec in SERVICES.values()]
    assert len(pairs) == len(set(pairs))
    assert len({spec.label for spec in SERVICES.values()}) == 99
    for key, spec in SERVICES.items():
        assert spec.key == key
        assert re.fullmatch(r"[a-z0-9]+(\.[a-z0-9_]+){1,2}", key), key
        assert spec.label and not spec.label.endswith(".")


def test_the_verb_is_the_type_published_by_serpro() -> None:
    official = _official_production()

    for spec in SERVICES.values():
        assert spec.verb.value == official[_ids(spec)], spec.key
    assert Counter(spec.verb for spec in SERVICES.values()) == {
        Verb.CONSULTAR: 61, Verb.EMITIR: 23, Verb.DECLARAR: 6, Verb.MONITORAR: 5, Verb.APOIAR: 4,
    }


def test_effect_classes_add_up_to_99_with_the_counts_of_the_report() -> None:
    counts = Counter(spec.effect_class for spec in SERVICES.values())

    assert counts == {
        EffectClass.READ: 68, EffectClass.READ_LEGAL: 1, EffectClass.DOCUMENT: 4,
        EffectClass.GUIDE: 18, EffectClass.WRITE: 1, EffectClass.DECLARE: 6,
        EffectClass.SUPPORT: 1,
    }
    assert sum(counts.values()) == 99
    for effect_class in EffectClass:
        assert len(services_by_effect(effect_class)) == counts[effect_class]


def test_effect_class_agrees_with_the_verb() -> None:
    allowed = {
        Verb.CONSULTAR: {EffectClass.READ, EffectClass.READ_LEGAL},
        Verb.MONITORAR: {EffectClass.READ},
        Verb.APOIAR: {EffectClass.READ, EffectClass.SUPPORT},
        Verb.EMITIR: {EffectClass.DOCUMENT, EffectClass.GUIDE, EffectClass.WRITE},
        Verb.DECLARAR: {EffectClass.DECLARE},
    }
    for spec in SERVICES.values():
        assert spec.effect_class in allowed[spec.verb], spec.key


def test_known_classifications_of_the_report() -> None:
    assert service_by_ids("CAIXAPOSTAL", "MSGDETALHAMENTO62").effect_class is EffectClass.READ_LEGAL
    assert service_by_ids("PGMEI", "ATUBENEFICIO23").effect_class is EffectClass.WRITE
    assert service_by_ids("AUTENTICAPROCURADOR", "ENVIOXMLASSINADO81").effect_class is (
        EffectClass.SUPPORT
    )
    assert service_by_ids("SITFIS", "SOLICITARPROTOCOLO91").effect_class is EffectClass.READ
    assert service_by_ids("MIT", "SITUACAOENC315").effect_class is EffectClass.READ
    assert service_by_ids("SICALC", "CONSULTAAPOIORECEITAS52").effect_class is EffectClass.READ
    assert service_by_ids("SITFIS", "RELATORIOSITFIS92").effect_class is EffectClass.DOCUMENT
    assert service_by_ids("PGDASD", "GERARDAS12").effect_class is EffectClass.GUIDE
    assert service_by_ids("PGDASD", "TRANSDECLARACAO11").effect_class is EffectClass.DECLARE


def test_support_and_monitor_calls_are_not_billed_and_the_rest_is() -> None:
    for spec in SERVICES.values():
        assert spec.billable is (spec.verb not in {Verb.APOIAR, Verb.MONITORAR}), spec.key
    assert sum(spec.billable for spec in SERVICES.values()) == 90


def test_unknown_services_are_refused() -> None:
    with pytest.raises(ValueError, match="não está no catálogo"):
        service("pgdasd.nao_existe")
    with pytest.raises(ValueError, match="não está no catálogo"):
        service_by_ids("PGDASD", "NAOEXISTE99")
    with pytest.raises(ValueError, match="não está no catálogo"):
        service_by_ids("NAOEXISTE", "CONSDECLARACAO13")
    # Cancelled, under construction and prospecting services are not production services.
    for id_sistema, id_servico in (
        ("AUTENTICAPROCURADOR", "EXPIRARAUTORIZACAO82"),
        ("CAIXAPOSTAL", "QTQMSG64"),
        ("DASNSIMEI", "TRANSDECLARACAO151"),
        ("EPROCESSO", "CONSCOMUNINTIM274"),
        ("PARC-PAEX", "OBTEREXTRATOPDF171"),
        ("DCTFWEB", "CONSRELCREDITO34"),
    ):
        with pytest.raises(ValueError, match="não está no catálogo"):
            service_by_ids(id_sistema, id_servico)


def test_lookup_by_ids_returns_the_same_object_as_lookup_by_key() -> None:
    for spec in SERVICES.values():
        assert service_by_ids(spec.id_sistema, spec.id_servico) is spec
        assert service(spec.key) is spec


def test_the_19_legacy_keys_keep_their_identity() -> None:
    assert len(LEGACY_KEYS) == 19
    for key, (id_sistema, id_servico, verb, label, billable) in LEGACY_KEYS.items():
        spec = service(key)
        assert (spec.id_sistema, spec.id_servico, spec.verb, spec.label, spec.billable) == (
            id_sistema, id_servico, verb, label, billable,
        ), key


def test_copilot_allowed_matches_the_allowlist_and_blocklist_of_appendix_a() -> None:
    for spec in SERVICES.values():
        ids = _ids(spec)
        if ids in ALLOWLIST or ids in OPTIONAL_RELEASED:
            assert spec.copilot_allowed, spec.key
        else:
            assert ids in BLOCKLIST or ids in OPTIONAL_HELD, spec.key
            assert not spec.copilot_allowed, spec.key
    assert {spec.key for spec in copilot_services()} == {
        spec.key for spec in SERVICES.values() if spec.copilot_allowed
    }
    assert len(copilot_services()) == 69


def test_copilot_allowed_services_never_have_an_effect_beyond_reading_and_documents() -> None:
    for spec in copilot_services():
        assert spec.effect_class in {EffectClass.READ, EffectClass.DOCUMENT}, spec.key
        assert spec.verb is not Verb.DECLARAR


def test_ciencia_of_the_intimation_requires_a_human_confirmation() -> None:
    detail = service_by_ids("CAIXAPOSTAL", "MSGDETALHAMENTO62")

    assert detail.key == "caixapostal.detalhe"
    assert detail.needs_confirmation is True
    assert detail.copilot_allowed is False


def test_confirmation_is_required_exactly_when_the_copilot_may_not_call_alone() -> None:
    for spec in SERVICES.values():
        assert spec.needs_confirmation is (not spec.copilot_allowed), spec.key
        if spec.effect_class is EffectClass.READ:
            assert spec.needs_confirmation is False, spec.key


def test_response_formats_follow_the_official_pages() -> None:
    expected = {
        ("PGDASD", "CONSDECLARACAO13"): ResponseFormat.JSON,
        ("PGDASD", "CONSEXTRATO16"): ResponseFormat.PDF,
        ("PGDASD", "GERARDAS12"): ResponseFormat.PDF,
        ("DCTFWEB", "CONSXMLDECLARACAO38"): ResponseFormat.XML,
        ("DCTFWEB", "CONSDECCOMPLETA33"): ResponseFormat.PDF,
        ("DCTFWEB", "GERARGUIA31"): ResponseFormat.PDF,
        ("SITFIS", "RELATORIOSITFIS92"): ResponseFormat.PDF,
        ("SITFIS", "SOLICITARPROTOCOLO91"): ResponseFormat.JSON,
        ("PAGTOWEB", "PAGAMENTOS71"): ResponseFormat.JSON,
        ("PAGTOWEB", "COMPARRECADACAO72"): ResponseFormat.PDF,
        ("PGMEI", "GERARDASCODBARRA22"): ResponseFormat.JSON,
        ("PGMEI", "GERARDASPDF21"): ResponseFormat.PDF,
        ("SICALC", "GERARDARFCODBARRA53"): ResponseFormat.JSON,
        ("SICALC", "CONSOLIDARGERARDARF51"): ResponseFormat.PDF,
        ("PARCSN", "GERARDAS161"): ResponseFormat.PDF,
        ("RELPMEI", "GERARDAS231"): ResponseFormat.PDF,
        ("PARCMEI", "PEDIDOSPARC203"): ResponseFormat.JSON,
        ("MIT", "ENCAPURACAO314"): ResponseFormat.JSON,
    }
    for ids, response_format in expected.items():
        assert service_by_ids(*ids).response_format is response_format, ids
    assert {spec.response_format for spec in SERVICES.values()} == set(ResponseFormat)


def test_versions_are_the_ones_stated_by_the_official_service_pages() -> None:
    non_default = {
        ("SITFIS", "SOLICITARPROTOCOLO91"): "2.0",
        ("SITFIS", "RELATORIOSITFIS92"): "2.0",
        ("EPROCESSO", "CONSPROCPORINTER271"): "2.0",
        ("PROCURACOES", "OBTERPROCURACAO41"): "1",
        ("SICALC", "CONSOLIDARGERARDARF51"): "2.9",
        ("SICALC", "CONSULTAAPOIORECEITAS52"): "2.9",
        ("SICALC", "GERARDARFCODBARRA53"): "2.9",
        ("SICALC", "CONSOLIDAR54"): "2.9",
    }
    for spec in SERVICES.values():
        assert spec.versao == spec.versao_sistema
        assert spec.versao == non_default.get(_ids(spec), "1.0"), spec.key


def test_services_whose_documentation_never_states_the_version_are_listed() -> None:
    """CCMEI 121 and PGMEI 21 omit versaoSistema in their page and in their examples. They
    reuse the version of their system and stay flagged for the first homologation call."""

    unconfirmed = {_ids(spec) for spec in SERVICES.values() if not spec.versao_confirmada}

    assert unconfirmed == {("CCMEI", "EMITIRCCMEI121"), ("PGMEI", "GERARDASPDF21")}


def test_parcelamento_modalities_come_from_one_table() -> None:
    parcelamento = [spec for spec in SERVICES.values() if spec.key.startswith("parcelamento.")]

    assert len(parcelamento) == 40
    for modalidade, base in PARCELAMENTO_MODALITIES.items():
        specs = [spec for spec in parcelamento if spec.id_sistema == modalidade]
        reads = zip(PARCELAMENTO_READS, (2, 3, 4, 5), strict=True)
        assert sorted(spec.id_servico for spec in specs) == sorted(
            [f"GERARDAS{base * 10 + 1}"] + [f"{nome}{base * 10 + n}" for nome, n in reads]
        )
        slugs = {spec.key.split(".")[1] for spec in specs}
        assert len(slugs) == 1
        assert {spec.key.split(".")[2] for spec in specs} == {
            "pedidos", "detalhe", "pagamento", "parcelas", "das",
        }


def test_every_service_points_to_its_official_documentation_page() -> None:
    for spec in SERVICES.values():
        assert re.fullmatch(
            r"solucoes/[a-z0-9_-]+/[a-z0-9_-]+/servicos/[a-z0-9_-]+", spec.doc_page
        ), spec.key
    assert service("pgdasd.declaracoes").doc_page == (
        "solucoes/integra-sn/pgdasd/servicos/consultar_declaracao_por_ano_pa"
    )


def test_the_registry_table_is_immutable_at_runtime() -> None:
    spec = service("pgdasd.das")
    with pytest.raises(AttributeError):
        spec.billable = False  # type: ignore[misc]
