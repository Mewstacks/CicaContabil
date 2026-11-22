from __future__ import annotations

from pathlib import Path

import pytest

from dominio_mcp.catalog import Catalog, Column, ForeignKey, Table
from dominio_mcp.overlay import Overlay, overlay_from_files
from dominio_mcp.pack import Pack, build_pack
from dominio_mcp.policy import load_policy
from dominio_mcp.readable import ReadableReport
from dominio_mcp.search import SchemaSearch, tokens

POLICY = load_policy()

GLOSSARY = """
version: 1
stopwords: [de, da, do, das, dos, e, o, a, para, quais, qual, como, os, as, sobre]
synonyms:
  vendas: [saidas]
  fornecedor: [fornecedores]
"""
CORE = """
version: 1
tables:
  - {name: geempre, titulo: Empresas, aliases: [carteira, cadastro de empresas]}
  - {name: naoexiste, titulo: Fantasma, aliases: [fantasma]}
"""
OVERLAY = overlay_from_files({"glossary.yaml": GLOSSARY, "core_tables.yaml": CORE})


def table(name: str, comment: str, rows: int = 100, cols: int = 2) -> Table:
    columns = tuple(
        Column(f"c{i}" if i else "codi_emp", i + 1, "integer", 4, 0, False, None)
        for i in range(cols)
    )
    return Table(name, "BASE", rows, comment, columns, ("codi_emp",), (), None)


def make(
    tmp_path: Path,
    tables: list[Table],
    fks: list[ForeignKey] | None = None,
    *,
    readable: ReadableReport | None = None,
    overlay: Overlay = OVERLAY,
) -> SchemaSearch:
    catalog = Catalog("bethadba", {t.key: t for t in tables}, tuple(fks or ()))
    build_pack(
        tmp_path / "p.sqlite3", catalog=catalog, policy=POLICY, overlay=overlay, readable=readable
    )
    return SchemaSearch(Pack(tmp_path / "p.sqlite3"), overlay)


def fk(child: str, parent: str) -> ForeignKey:
    return ForeignKey(child, ("codi_emp",), parent, ("codi_emp",))


def names(hits: list) -> list[str]:  # type: ignore[type-arg]
    return [h.key for h in hits]


def base_tables() -> list[Table]:
    return [
        table("geempre", "Cadastro de empresas do escritorio", 600),
        table("usconfempresas", "Configuracao por empresas do usuario", 5),
        table("efsaidas", "Notas fiscais de saida", 386290),
        table("efsaidas_itens_historico_x", "Notas fiscais de saida - historico", 10),
        table("efentradas", "Notas fiscais de entrada", 31691),
        table("effornece", "Fornecedores - Cadastro", 5789),
    ]


def test_glossary_synonym_finds_the_table_named_by_the_accountant(tmp_path: Path) -> None:
    search = make(tmp_path, base_tables())
    assert names(search.search("vendas do mes"))[0] == "efsaidas"
    assert names(search.search("fornecedor"))[0] == "effornece"


def test_terms_drop_stopwords_and_expand_synonyms(tmp_path: Path) -> None:
    search = make(tmp_path, base_tables())
    assert search.terms("quais as vendas do escritorio") == ["venda", "saida", "escritorio"]
    assert search.terms("de da do") == []


def test_trigram_finds_pieces_of_names_and_accents_do_not_matter(tmp_path: Path) -> None:
    search = make(tmp_path, base_tables())
    assert "efsaidas" in names(search.search("efsaid"))
    assert names(search.search("notas fiscais de saída"))[0] == "efsaidas"


def test_core_alias_lifts_a_table_the_text_alone_would_miss(tmp_path: Path) -> None:
    search = make(tmp_path, base_tables())
    hits = search.search("carteira")
    assert names(hits) == ["geempre"]
    assert "apelido" in hits[0].why and hits[0].titulo == "Empresas"
    multi = search.search("cadastro de empresas")
    assert names(multi)[0] == "geempre"


def test_alias_pointing_to_a_missing_table_is_ignored(tmp_path: Path) -> None:
    search = make(tmp_path, base_tables())
    assert search.search("fantasma") == []


def test_structural_prior_ranks_the_hub_above_a_longer_lookalike(tmp_path: Path) -> None:
    tables = [
        table("efsaidas", "Notas fiscais de saida", 386290),
        table("efsaidas_itens_historico_x", "Notas fiscais de saida", 10),
        table("efsaidas_outros_dados_y", "Notas fiscais de saida", 10),
    ]
    fks = [fk("efentradas", "efsaidas"), fk("x", "efsaidas"), fk("y", "efsaidas")]
    search = make(tmp_path, tables, fks)
    assert names(search.search("notas fiscais de saida"))[0] == "efsaidas"


def test_obsolete_and_unreadable_objects_lose_position(tmp_path: Path) -> None:
    tables = [
        table("efsaidas_antiga", "Notas fiscais de saida - tabela obsoleta", 500),
        table("efsaidas_atual", "Notas fiscais de saida - versao atual", 500),
    ]
    search = make(tmp_path, tables)
    assert names(search.search("notas fiscais de saida"))[0] == "efsaidas_atual"
    assert search.search("notas fiscais de saida")[1].obsolete is True

    twins = [
        table("efsaidas_a", "Notas fiscais de saida", 500),
        table("efsaidas_b", "Notas fiscais de saida", 500),
    ]
    report = ReadableReport(frozenset({"efsaidas_b"}), {"efsaidas_a": "sem_permissao"}, True)
    (tmp_path / "b").mkdir()
    search2 = make(tmp_path / "b", twins, readable=report)
    hits = search2.search("notas fiscais de saida")
    assert names(hits) == ["efsaidas_b", "efsaidas_a"]
    assert hits[1].queryable is False and hits[1].blocked_reason == "ilegivel:sem_permissao"


@pytest.mark.parametrize(
    "query",
    [
        'saida" OR "x',
        "NEAR(saida entrada)",
        "saida*",
        "AND OR NOT",
        "'; DROP TABLE tables; --",
        "saida ^ entrada",
        "col:saida",
        "(((",
        '"',
        "\x00\x01",
        "сайда",
    ],
)
def test_query_text_cannot_inject_fts_operators_or_sql(tmp_path: Path, query: str) -> None:
    search = make(tmp_path, base_tables())
    result = search.search(query)
    assert isinstance(result, list)
    assert len(search._pack.tables()) == 6


def test_empty_and_stopword_only_queries_return_nothing(tmp_path: Path) -> None:
    search = make(tmp_path, base_tables())
    assert search.search("") == []
    assert search.search("   ") == []
    assert search.search("de da do") == []


def test_limit_is_respected_and_capped(tmp_path: Path) -> None:
    tables = [table(f"efnota{i}", "Notas fiscais variadas", 10 + i) for i in range(30)]
    search = make(tmp_path, tables)
    assert len(search.search("notas fiscais", limit=3)) == 3
    assert len(search.search("notas fiscais", limit=500)) == 20
    assert len(search.search("notas fiscais", limit=0)) == 1


def test_credential_tables_never_show_up(tmp_path: Path) -> None:
    tables = [table("gecertificadosdigitais", "Certificados digitais de empresas"), *base_tables()]
    search = make(tmp_path, tables)
    assert "gecertificadosdigitais" not in names(search.search("certificados digitais empresas"))
    assert "gecertificadosdigitais" not in names(search.search("certificadosdigitais"))


def test_results_are_deterministic_and_carry_the_card_fields(tmp_path: Path) -> None:
    search = make(tmp_path, base_tables())
    first = search.search("notas fiscais")
    assert first == search.search("notas fiscais")
    hit = first[0]
    assert hit.name and hit.module in {"ef", "ge", "us"} and hit.score > 0
    assert hit.queryable is True and hit.kind == "BASE" and hit.why


def test_tokens_fold_accents_and_case() -> None:
    assert tokens("Notas FISCAIS de Saída 2026") == ["nota", "fiscal", "de", "saida", "2026"]
