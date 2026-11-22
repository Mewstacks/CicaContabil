from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from dominio_mcp.pack import Pack
from packs import build_demo_pack
from qhelp import VALID_CNPJ, compile_, refused


@pytest.fixture
def pack(tmp_path: Path) -> Pack:
    return build_demo_pack(tmp_path)


def test_plain_select_quotes_identifiers_and_pages_with_top_start_at(pack: Pack) -> None:
    c = compile_(
        pack,
        {
            "tabela": "GEEMPRE",
            "colunas": ["codi_emp", "nome_emp"],
            "limite": 10,
            "deslocamento": 20,
        },
    )
    assert c.sql == (
        'SELECT TOP 11 START AT 21 "t0"."codi_emp" AS "codi_emp", "t0"."nome_emp" AS "nome_emp"\n'
        'FROM "bethadba"."geempre" AS "t0"'
    )
    assert c.params == () and c.literal_sql == c.sql and c.limit == 10
    assert [col.header for col in c.columns] == ["codi_emp", "nome_emp"]
    assert c.tables == ("geempre",)


def test_filters_become_placeholders_and_literals_in_the_same_order(pack: Pack) -> None:
    c = compile_(
        pack,
        {
            "tabela": "efsaidas",
            "colunas": ["codi_sai"],
            "filtros": [
                {"coluna": "codi_emp", "op": "=", "valor": 560},
                {"coluna": "dsai_sai", "op": "between", "valor": ["2025-01-01", "2025-12-31"]},
                {"coluna": "vcon_sai", "op": ">=", "valor": "10.50"},
                {"coluna": "seg_sai", "op": "in", "valor": [1, 2]},
                {"coluna": "situ_sai", "op": "not_null"},
                {"coluna": "codi_sai", "op": "!=", "valor": 7},
            ],
        },
    )
    assert 'WHERE "t0"."codi_emp" = ? AND "t0"."dsai_sai" BETWEEN ? AND ?' in c.sql
    assert 'AND "t0"."vcon_sai" >= ? AND "t0"."seg_sai" IN (?, ?)' in c.sql
    assert 'AND "t0"."situ_sai" IS NOT NULL AND "t0"."codi_sai" != ?' in c.sql
    assert c.params == (560, date(2025, 1, 1), date(2025, 12, 31), Decimal("10.50"), 1, 2, 7)
    assert "?" not in c.literal_sql
    assert '"t0"."codi_emp" = 560' in c.literal_sql
    assert "BETWEEN '2025-01-01' AND '2025-12-31'" in c.literal_sql
    assert '"t0"."vcon_sai" >= 10.50 AND "t0"."seg_sai" IN (1, 2)' in c.literal_sql


def test_like_filters_escape_wildcards_and_bind_the_pattern(pack: Pack) -> None:
    # `nome_emp` e texto comum: texto livre (`obs_sai`) deixou de aceitar filtro (revisao, achado 5)
    c = compile_(
        pack,
        {
            "tabela": "geempre",
            "colunas": ["codi_emp"],
            "filtros": [
                {"coluna": "nome_emp", "op": "prefix", "valor": "50%_x!"},
                {"coluna": "nome_emp", "op": "contains", "valor": "frete"},
            ],
        },
    )
    assert c.sql.count("LIKE ? ESCAPE '!'") == 2
    assert c.params == ("50!%!_x!!%", "%frete%")
    assert "LIKE '50!%!_x!!%' ESCAPE '!'" in c.literal_sql


def test_null_filters_take_no_parameter(pack: Pack) -> None:
    c = compile_(
        pack,
        {
            "tabela": "geempre",
            "colunas": ["codi_emp"],
            "filtros": [{"coluna": "dina_emp", "op": "is_null"}],
        },
    )
    assert c.sql.endswith('WHERE "t0"."dina_emp" IS NULL') and c.params == ()


def test_adversarial_values_only_ever_travel_as_parameters(pack: Pack) -> None:
    nasty = "x'; DROP TABLE geempre; --"
    c = compile_(
        pack,
        {
            "tabela": "efclientes",
            "colunas": ["codi_cli"],
            "filtros": [{"coluna": "nome_cli", "op": "=", "valor": nasty}],
        },
    )
    assert nasty not in c.sql and "DROP" not in c.sql and c.params == (nasty,)
    assert (
        "'x''; DROP TABLE geempre; --'" in c.literal_sql
    )  # so no SQL de estimativa, aspas duplicadas


@pytest.mark.parametrize("value", ["barra\\invertida", "linha\ncom quebra", "x" * 201, "nul\x00"])
def test_values_that_cannot_be_encoded_refuse_the_whole_query(pack: Pack, value: str) -> None:
    err = refused(
        pack,
        {
            "tabela": "efclientes",
            "colunas": ["codi_cli"],
            "filtros": [{"coluna": "nome_cli", "op": "=", "valor": value}],
        },
    )
    assert err.code in {"valor_nao_codificavel", "valor_incompativel"}


def test_document_filter_value_is_a_parameter_too(pack: Pack) -> None:
    c = compile_(
        pack,
        {
            "tabela": "geempre",
            "colunas": ["codi_emp"],
            "filtros": [{"coluna": "cgce_emp", "op": "=", "valor": VALID_CNPJ}],
        },
    )
    assert c.params == (VALID_CNPJ,) and f"'{VALID_CNPJ}'" in c.literal_sql


def test_aggregation_group_by_order_by_and_count_star(pack: Pack) -> None:
    c = compile_(
        pack,
        {
            "tabela": "efsaidas",
            "agrupar_por": ["codi_emp", "seg_sai"],
            "agregacoes": [
                {"funcao": "sum", "coluna": "vcon_sai", "alias": "total"},
                {"funcao": "count", "coluna": "*", "alias": "n"},
                {"funcao": "count_distinct", "coluna": "codi_sai", "alias": "notas"},
                {"funcao": "avg", "coluna": "vcon_sai", "alias": "media"},
                {"funcao": "min", "coluna": "dsai_sai", "alias": "primeira"},
                {"funcao": "max", "coluna": "dsai_sai", "alias": "ultima"},
            ],
            "ordenar_por": [{"coluna": "total", "ordem": "desc"}, {"coluna": "codi_emp"}],
            "limite": 100,
        },
    )
    assert c.sql.splitlines()[0] == (
        'SELECT TOP 101 START AT 1 "t0"."codi_emp" AS "codi_emp", "t0"."seg_sai" AS "seg_sai", '
        'SUM("t0"."vcon_sai") AS "total", COUNT(*) AS "n", '
        'COUNT(DISTINCT "t0"."codi_sai") AS "notas", AVG("t0"."vcon_sai") AS "media", '
        'MIN("t0"."dsai_sai") AS "primeira", MAX("t0"."dsai_sai") AS "ultima"'
    )
    assert 'GROUP BY "t0"."codi_emp", "t0"."seg_sai"' in c.sql
    assert 'ORDER BY "total" DESC, "t0"."codi_emp"' in c.sql
    assert [col.from_aggregate for col in c.columns] == [False, False] + [True] * 6


def test_distinct_orders_by_the_select_alias(pack: Pack) -> None:
    c = compile_(
        pack,
        {
            "tabela": "efsaidas",
            "colunas": ["codi_emp"],
            "distinto": True,
            "ordenar_por": [{"coluna": "codi_emp", "ordem": "desc"}],
        },
    )
    assert c.sql.splitlines()[0].startswith("SELECT DISTINCT TOP 51 START AT 1 ")
    assert c.sql.endswith('ORDER BY "codi_emp" DESC')


def test_personal_aggregates_add_the_hidden_group_size_column(pack: Pack) -> None:
    c = compile_(
        pack,
        {
            "tabela": "foempregados",
            "agrupar_por": ["codi_emp"],
            "agregacoes": [{"funcao": "avg", "coluna": "salario", "alias": "media"}],
        },
        allow_pii=frozenset({"folha"}),
    )
    assert 'COUNT(*) AS "__k"' in c.sql
    assert c.count_index == 2 and c.columns[-1].hidden is True
    assert c.columns[1].mask == "none" and c.columns[1].from_aggregate is True


def test_output_columns_carry_the_mask_to_apply(pack: Pack) -> None:
    c = compile_(pack, {"tabela": "efsaidas", "colunas": ["codi_sai", "obs_sai", "cgce_cli"]})
    assert [(col.header, col.mask) for col in c.columns] == [
        ("codi_sai", "none"),
        ("obs_sai", "texto"),
        ("cgce_cli", "documento"),
    ]
    released = compile_(
        pack, {"tabela": "efsaidas", "colunas": ["cgce_cli"]}, allow_pii=frozenset({"documento"})
    )
    assert released.columns[0].mask == "none"
    pessoal = compile_(
        pack, {"tabela": "geempre", "colunas": ["ende_emp"]}, allow_pii=frozenset({"endereco"})
    )
    assert (pessoal.columns[0].mask, pessoal.columns[0].category) == ("pessoal", "endereco")


def test_joins_use_the_declared_composite_keys(pack: Pack) -> None:
    c = compile_(
        pack,
        {
            "tabela": "efmvspro",
            "juntar": [{"tabela": "geempre", "apelido": "emp"}],
            "colunas": ["nume_mvs", "efsaidas.dsai_sai", "emp.nome_emp"],
        },
    )
    assert c.sql == "\n".join(
        [
            'SELECT TOP 51 START AT 1 "t0"."nume_mvs" AS "nume_mvs", '
            '"t1"."dsai_sai" AS "efsaidas.dsai_sai", "t2"."nome_emp" AS "emp.nome_emp"',
            'FROM "bethadba"."efmvspro" AS "t0"',
            'INNER JOIN "bethadba"."efsaidas" AS "t1" ON "t0"."codi_emp" = "t1"."codi_emp" '
            'AND "t0"."codi_sai" = "t1"."codi_sai" AND "t0"."seg_sai" = "t1"."seg_sai"',
            'INNER JOIN "bethadba"."geempre" AS "t2" ON "t1"."codi_emp" = "t2"."codi_emp"',
        ]
    )
    assert c.tables == ("efmvspro", "efsaidas", "geempre")


def test_filter_on_a_joined_table_uses_its_alias(pack: Pack) -> None:
    c = compile_(
        pack,
        {
            "tabela": "efsaidas",
            "juntar": [{"tabela": "geempre", "apelido": "emp"}],
            "colunas": ["codi_sai"],
            "filtros": [{"coluna": "emp.nome_emp", "op": "prefix", "valor": "ACME"}],
        },
    )
    assert 'WHERE "t1"."nome_emp" LIKE ? ESCAPE' in c.sql
