from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from dominio_mcp.pack import Pack
from dominio_mcp.readable import ReadableReport
from packs import build_demo_pack
from qhelp import OTHER_VALID_CNPJ, VALID_CNPJ, refused, validate


@pytest.fixture
def pack(tmp_path: Path) -> Pack:
    return build_demo_pack(tmp_path)


def test_a_plain_valid_query_gets_defaults(pack: Pack) -> None:
    vq = validate(pack, {"tabela": "GEEMPRE", "colunas": ["codi_emp", "nome_emp"]})
    assert [s.header for s in vq.select] == ["codi_emp", "nome_emp"]
    assert (vq.limit, vq.offset, vq.aggregated, vq.suppress_small_groups) == (50, 0, False, False)
    assert vq.tables[0].alias == "t0" and vq.tables[0].has_company is True


def test_unknown_blocked_and_unreadable_tables(tmp_path: Path) -> None:
    pack = build_demo_pack(tmp_path)
    assert refused(pack, {"tabela": "nao_existe", "colunas": ["x"]}).code == "tabela_desconhecida"
    cred = refused(pack, {"tabela": "gecertificadosdigitais", "colunas": ["nome"]})
    assert cred.code == "tabela_bloqueada" and "credencial" not in cred.message
    view = refused(pack, {"tabela": "vw_totais", "colunas": ["total"]})
    assert view.code == "tabela_bloqueada" and "view" in view.message
    report = ReadableReport(frozenset({"geempre"}), {"efclientes": "sem_permissao"}, True)
    other = build_demo_pack(tmp_path, readable=report, name="b.sqlite3")
    denied = refused(other, {"tabela": "efclientes", "colunas": ["codi_emp"]})
    assert denied.code == "tabela_bloqueada" and "sem_permissao" in denied.message


def test_unknown_column_bad_reference_and_unjoined_alias(pack: Pack) -> None:
    assert refused(pack, {"tabela": "geempre", "colunas": ["nada"]}).code == "coluna_desconhecida"
    assert refused(pack, {"tabela": "geempre", "colunas": ["a b"]}).code == "referencia_invalida"
    assert refused(pack, {"tabela": "geempre", "colunas": ["emp.nome_emp"]}).code == (
        "tabela_nao_juntada"
    )
    assert refused(pack, {"tabela": "geempre"}).code == "sem_colunas"


def test_unclassified_columns_are_blocked_until_accepted(tmp_path: Path) -> None:
    skip = frozenset({("geempre", "nome_emp")})
    pack = build_demo_pack(tmp_path, skip=skip)
    err = refused(pack, {"tabela": "geempre", "colunas": ["nome_emp"]})
    assert err.code == "coluna_bloqueada" and err.details["motivo"] == "nao_classificada"
    assert validate(pack, {"tabela": "geempre", "colunas": ["codi_emp"]})


def test_personal_data_needs_release_and_is_never_filterable_groupable_or_sortable(
    pack: Pack,
) -> None:
    err = refused(pack, {"tabela": "foempregados", "colunas": ["salario"]})
    assert err.code == "coluna_bloqueada" and err.details["motivo"] == "pessoal_nao_liberado:folha"
    folha = frozenset({"folha"})
    ok = validate(pack, {"tabela": "foempregados", "colunas": ["salario"]}, allow_pii=folha)
    assert ok.select[0].ref is not None and ok.select[0].ref.access.mask == "pessoal"
    for spec in (
        {
            "tabela": "foempregados",
            "colunas": ["codi_emp"],
            "filtros": [{"coluna": "salario", "op": ">", "valor": 1}],
        },
        {
            "tabela": "foempregados",
            "agrupar_por": ["salario"],
            "agregacoes": [{"funcao": "count", "coluna": "*", "alias": "n"}],
        },
        {"tabela": "foempregados", "colunas": ["codi_emp"], "ordenar_por": [{"coluna": "salario"}]},
    ):
        assert refused(pack, spec, allow_pii=folha).code == "coluna_bloqueada"
    agg = validate(
        pack,
        {
            "tabela": "foempregados",
            "agregacoes": [{"funcao": "sum", "coluna": "salario", "alias": "total"}],
        },
        allow_pii=folha,
    )
    assert agg.aggregated is True and agg.suppress_small_groups is True
    for func in ("min", "max"):
        spec = {
            "tabela": "foempregados",
            "agregacoes": [{"funcao": func, "coluna": "salario", "alias": "x"}],
        }
        assert refused(pack, spec, allow_pii=folha).code == "coluna_bloqueada"


def test_other_released_category_does_not_open_this_one(pack: Pack) -> None:
    err = refused(
        pack, {"tabela": "geempre", "colunas": ["ende_emp"]}, allow_pii=frozenset({"folha"})
    )
    assert err.details["motivo"] == "pessoal_nao_liberado:endereco"


def test_document_column_rules(pack: Pack) -> None:
    ok = validate(
        pack,
        {
            "tabela": "geempre",
            "colunas": ["cgce_emp"],
            "filtros": [{"coluna": "cgce_emp", "op": "=", "valor": VALID_CNPJ}],
        },
    )
    assert ok.select[0].ref is not None and ok.select[0].ref.access.mask == "documento"
    bad = refused(
        pack,
        {
            "tabela": "geempre",
            "colunas": ["codi_emp"],
            "filtros": [{"coluna": "cgce_emp", "op": "=", "valor": "11222333000182"}],
        },
    )
    assert bad.code == "documento_invalido"
    assert validate(
        pack,
        {
            "tabela": "geempre",
            "colunas": ["codi_emp"],
            "filtros": [
                {"coluna": "cgce_emp", "op": "in", "valor": [VALID_CNPJ, OTHER_VALID_CNPJ]}
            ],
        },
    )
    for spec in (
        {
            "tabela": "geempre",
            "colunas": ["codi_emp"],
            "filtros": [{"coluna": "cgce_emp", "op": "contains", "valor": "112"}],
        },
        {
            "tabela": "geempre",
            "agrupar_por": ["cgce_emp"],
            "agregacoes": [{"funcao": "count", "coluna": "*", "alias": "n"}],
        },
        {"tabela": "geempre", "colunas": ["cgce_emp"], "ordenar_por": [{"coluna": "cgce_emp"}]},
        {
            "tabela": "geempre",
            "agregacoes": [{"funcao": "count", "coluna": "cgce_emp", "alias": "n"}],
        },
    ):
        assert refused(pack, spec).code == "coluna_bloqueada"
    released = validate(
        pack, {"tabela": "geempre", "colunas": ["cgce_emp"]}, allow_pii=frozenset({"documento"})
    )
    assert released.select[0].ref is not None and released.select[0].ref.access.mask == "none"


def test_free_text_is_selectable_but_never_a_filter(pack: Pack) -> None:
    ok = validate(pack, {"tabela": "efsaidas", "colunas": ["obs_sai"]})
    assert ok.select[0].ref is not None and ok.select[0].ref.access.mask == "texto"
    # qualquer filtro em texto livre confirmaria por contagem o que a mascara esconde
    for op, value in (
        ("contains", "frete"),
        ("contains", "529.982.247-25"),
        ("prefix", "a@b.com"),
        ("=", "x"),
    ):
        err = refused(
            pack,
            {
                "tabela": "efsaidas",
                "colunas": ["codi_sai"],
                "filtros": [{"coluna": "obs_sai", "op": op, "valor": value}],
            },
        )
        assert err.code == "coluna_bloqueada"


@pytest.mark.parametrize(
    ("column", "op", "value"),
    [
        ("codi_emp", "=", "abc"),
        ("codi_emp", "=", True),
        ("codi_emp", "=", 1.5),
        ("dsai_sai", "=", "2025-13-40"),
        ("dsai_sai", "=", 20250101),
        ("vcon_sai", ">", "dez"),
        ("vcon_sai", ">", float("nan")),
        ("codi_emp", "between", [1]),
        ("codi_emp", "between", 1),
        ("codi_emp", "in", []),
        ("codi_emp", "in", list(range(101))),
        ("codi_emp", "in", 5),
        ("codi_sai", "prefix", "x"),
        ("seg_sai", "contains", 1),
    ],
)
def test_filter_values_must_fit_the_column_type(
    pack: Pack, column: str, op: str, value: object
) -> None:
    spec = {
        "tabela": "efsaidas",
        "colunas": ["codi_emp"],
        "filtros": [{"coluna": column, "op": op, "valor": value}],
    }
    assert refused(pack, spec).code in {"valor_incompativel", "coluna_bloqueada"}


def test_good_typed_values_are_coerced(pack: Pack) -> None:
    vq = validate(
        pack,
        {
            "tabela": "efsaidas",
            "colunas": ["codi_emp"],
            "filtros": [
                {"coluna": "codi_emp", "op": "=", "valor": "560"},
                {"coluna": "dsai_sai", "op": "between", "valor": ["2025-01-01", "2025-12-31"]},
                {"coluna": "vcon_sai", "op": ">=", "valor": "10.50"},
                {"coluna": "seg_sai", "op": "in", "valor": [1, 2]},
                {"coluna": "situ_sai", "op": "not_null"},
            ],
        },
    )
    assert vq.filters[0].values == (560,)
    assert [str(v) for v in vq.filters[1].values] == ["2025-01-01", "2025-12-31"]
    assert str(vq.filters[2].values[0]) == "10.50"
    assert vq.filters[4].values == ()


def test_aggregated_queries_follow_sql_grouping_rules(pack: Pack) -> None:
    base = {
        "tabela": "efsaidas",
        "agrupar_por": ["codi_emp"],
        "agregacoes": [{"funcao": "sum", "coluna": "vcon_sai", "alias": "total"}],
    }
    vq = validate(pack, base)
    assert [s.header for s in vq.select] == ["codi_emp", "total"] and vq.aggregated
    assert refused(pack, {**base, "colunas": ["dsai_sai"]}).code == "coluna_fora_do_agrupamento"
    bad_sum = {
        "tabela": "geempre",
        "agregacoes": [{"funcao": "sum", "coluna": "nome_emp", "alias": "x"}],
    }
    assert refused(pack, bad_sum).code == "funcao_incompativel"
    star_sum = {"tabela": "geempre", "agregacoes": [{"funcao": "sum", "coluna": "*", "alias": "x"}]}
    assert refused(pack, star_sum).code == "funcao_incompativel"
    bad_alias = {
        "tabela": "geempre",
        "agregacoes": [{"funcao": "count", "coluna": "*", "alias": "1 x"}],
    }
    assert refused(pack, bad_alias).code == "apelido_invalido"
    dup = {
        "tabela": "efsaidas",
        "agrupar_por": ["codi_emp"],
        "agregacoes": [{"funcao": "count", "coluna": "*", "alias": "codi_emp"}],
    }
    assert refused(pack, dup).code == "saida_duplicada"


def test_ordering_rules(pack: Pack) -> None:
    ok = validate(
        pack,
        {
            "tabela": "efsaidas",
            "agrupar_por": ["codi_emp"],
            "agregacoes": [{"funcao": "sum", "coluna": "vcon_sai", "alias": "total"}],
            "ordenar_por": [{"coluna": "total", "ordem": "desc"}],
        },
    )
    assert ok.order_by[0].header == "total" and ok.order_by[0].desc is True
    err = refused(
        pack,
        {
            "tabela": "efsaidas",
            "agrupar_por": ["codi_emp"],
            "agregacoes": [{"funcao": "count", "coluna": "*", "alias": "n"}],
            "ordenar_por": [{"coluna": "dsai_sai"}],
        },
    )
    assert err.code == "ordenacao_fora_do_agrupamento"
    err2 = refused(
        pack,
        {
            "tabela": "efsaidas",
            "colunas": ["codi_emp"],
            "distinto": True,
            "ordenar_por": [{"coluna": "dsai_sai"}],
        },
    )
    assert err2.code == "ordenacao_fora_da_selecao"
    fine = validate(
        pack,
        {
            "tabela": "efsaidas",
            "colunas": ["codi_emp"],
            "distinto": True,
            "ordenar_por": [{"coluna": "codi_emp"}],
        },
    )
    assert fine.distinct is True


def test_limits_and_pagination(pack: Pack) -> None:
    assert (
        validate(pack, {"tabela": "geempre", "colunas": ["codi_emp"], "limite": 500}).limit == 500
    )
    assert refused(pack, {"tabela": "geempre", "colunas": ["codi_emp"], "limite": 501}).code == (
        "limite_acima_do_teto"
    )
    agg = {
        "tabela": "efsaidas",
        "agrupar_por": ["codi_emp"],
        "limite": 2000,
        "agregacoes": [{"funcao": "count", "coluna": "*", "alias": "n"}],
    }
    assert validate(pack, agg).limit == 2000
    assert refused(pack, {**agg, "limite": 2001}).code == "limite_acima_do_teto"
    deep = refused(pack, {"tabela": "geempre", "colunas": ["codi_emp"], "deslocamento": 100_001})
    assert deep.code == "deslocamento_alto"
    small = validate(pack, {"tabela": "geempre", "colunas": ["codi_emp"]}, default_rows=10)
    assert small.limit == 10
    with pytest.raises(ValidationError):
        validate(pack, {"tabela": "geempre", "colunas": ["codi_emp"], "limite": 0})
    with pytest.raises(ValidationError):
        validate(pack, {"tabela": "geempre", "colunas": ["codi_emp"], "sql": "SELECT 1"})


def test_output_column_cap(pack: Pack) -> None:
    err = refused(
        pack, {"tabela": "geempre", "colunas": ["codi_emp", "nome_emp", "dina_emp"]}, max_columns=2
    )
    assert err.code == "colunas_demais"


def test_joins_resolve_by_declared_foreign_key_only(pack: Pack) -> None:
    vq = validate(
        pack,
        {
            "tabela": "efsaidas",
            "juntar": [{"tabela": "geempre", "apelido": "emp"}],
            "colunas": ["codi_sai", "emp.nome_emp"],
        },
    )
    assert [t.alias for t in vq.tables] == ["t0", "t1"]
    assert [s.header for s in vq.select] == ["codi_sai", "emp.nome_emp"]
    via = validate(
        pack,
        {
            "tabela": "efmvspro",
            "juntar": [{"tabela": "geempre"}],
            "colunas": ["nume_mvs", "efsaidas.codi_sai", "geempre.nome_emp"],
        },
    )
    assert [t.row.key for t in via.tables] == ["efmvspro", "efsaidas", "geempre"]
    sibling = refused(
        pack, {"tabela": "efsaidas", "juntar": [{"tabela": "efclientes"}], "colunas": ["codi_sai"]}
    )
    assert sibling.code == "juncao_sem_fk"
    assert (
        refused(
            pack,
            {"tabela": "efsaidas", "juntar": [{"tabela": "vw_totais"}], "colunas": ["codi_sai"]},
        ).code
        == "tabela_bloqueada"
    )
    assert (
        refused(
            pack,
            {
                "tabela": "efsaidas",
                "juntar": [{"tabela": "geempre", "apelido": "1x"}],
                "colunas": ["codi_sai"],
            },
        ).code
        == "apelido_invalido"
    )


def test_blocked_column_of_a_joined_table_is_still_blocked(pack: Pack) -> None:
    err = refused(
        pack,
        {
            "tabela": "efsaidas",
            "juntar": [{"tabela": "geempre", "apelido": "e"}],
            "colunas": ["codi_sai", "e.ende_emp"],
        },
    )
    assert err.code == "coluna_bloqueada" and err.details["motivo"].startswith("pessoal")
    err2 = refused(
        pack,
        {
            "tabela": "efsaidas",
            "juntar": [{"tabela": "geempre", "apelido": "e"}],
            "colunas": ["codi_sai"],
            "filtros": [{"coluna": "e.ende_emp", "op": "=", "valor": "x"}],
        },
    )
    assert err2.code == "coluna_bloqueada"
