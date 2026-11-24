"""L3 (M9, A5): suite de ataque e consultas legitimas que precisam passar.

Duas camadas: a gramatica recusa o que nao reconhece (`translate`) e, para o que a gramatica
aceita, a politica de L2 continua valendo (coluna de segredo, pessoal, documento, tabela de
credencial, view, juncao fora da FK). Nada aqui toca o banco.
"""

# ruff: noqa: RUF001, S608
from __future__ import annotations

from pathlib import Path

import pytest

from dominio_mcp.compiler import compile_query
from dominio_mcp.pack import Pack
from dominio_mcp.query_spec import QueryRefused, validate_query
from dominio_mcp.rawsql import MAX_SQL_CHARS, RawSqlRefused, check_joins, tokenize, translate
from packs import build_demo_pack
from qhelp import POLICY, settings

ATTACKS = [
    # DML, DDL e execucao
    "INSERT INTO geempre (codi_emp) VALUES (1)",
    "UPDATE geempre SET nome_emp = 'x'",
    "DELETE FROM geempre",
    "DROP TABLE geempre",
    "ALTER TABLE geempre ADD x INT",
    "CREATE TABLE t (a INT)",
    "TRUNCATE TABLE geempre",
    "CALL sa_server_option('x', 'y')",
    "EXEC xp_cmdshell 'dir'",
    "EXECUTE sp_who",
    "MERGE INTO geempre USING x ON 1=1",
    "GRANT ALL ON geempre TO PUBLIC",
    "SET OPTION public.x = 'y'",
    "LOAD TABLE geempre FROM 'f.txt'",
    "UNLOAD SELECT * FROM geempre TO 'f.txt'",
    "BEGIN SELECT 1; END",
    # SELECT com efeito colateral ou fora da gramatica
    "SELECT codi_emp INTO tmp FROM geempre",
    "SELECT codi_emp FROM geempre FOR UPDATE",
    "SELECT codi_emp FROM geempre FOR XML RAW",
    "SELECT codi_emp FROM geempre LOCK TABLE",
    "SELECT * FROM geempre",
    "SELECT g.* FROM geempre g",
    "SELECT codi_emp FROM geempre; DROP TABLE geempre",
    "SELECT codi_emp FROM geempre;",
    "SELECT codi_emp FROM geempre -- comentario",
    "SELECT codi_emp /* x */ FROM geempre",
    "/* x */ SELECT codi_emp FROM geempre",
    "-- x\nSELECT codi_emp FROM geempre",
    "SELECT codi_emp FROM geempre WHERE 1=1 -- x",
    # estruturas que L3 nao tem
    "WITH t AS (SELECT codi_emp FROM geempre) SELECT codi_emp FROM t",
    "SELECT codi_emp FROM geempre UNION SELECT codi_emp FROM geempre",
    "SELECT codi_emp FROM geempre UNION ALL SELECT codi_emp FROM geempre",
    "SELECT codi_emp FROM geempre INTERSECT SELECT codi_emp FROM geempre",
    "SELECT codi_emp FROM geempre EXCEPT SELECT codi_emp FROM geempre",
    "SELECT (SELECT 1) FROM geempre",
    "SELECT codi_emp FROM (SELECT codi_emp FROM geempre) t",
    "SELECT codi_emp FROM geempre WHERE codi_emp IN (SELECT codi_emp FROM geempre)",
    "SELECT codi_emp FROM geempre WHERE EXISTS (SELECT 1)",
    "SELECT codi_emp FROM geempre WHERE codi_emp = 1 OR codi_emp = 2",
    "SELECT codi_emp FROM geempre WHERE NOT codi_emp = 1",
    "SELECT codi_emp FROM geempre WHERE (codi_emp = 1)",
    "SELECT codi_emp FROM geempre WHERE codi_emp NOT IN (1, 2)",
    "SELECT codi_emp FROM geempre WHERE nome_emp NOT LIKE 'A%'",
    "SELECT codi_emp FROM geempre WHERE codi_emp = NULL",
    "SELECT codi_emp FROM geempre WHERE codi_emp = codi_emp",
    "SELECT codi_emp FROM geempre WHERE 1 = 1",
    "SELECT codi_emp FROM geempre WHERE nome_emp LIKE '%A_B%'",
    "SELECT codi_emp FROM geempre WHERE nome_emp LIKE '[a-z]%'",
    "SELECT codi_emp FROM geempre WHERE nome_emp LIKE '%A'",
    "SELECT codi_emp FROM geempre WHERE nome_emp LIKE 'A'",
    "SELECT codi_emp FROM geempre WHERE nome_emp LIKE '%'",
    "SELECT codi_emp FROM geempre GROUP BY codi_emp HAVING COUNT(*) > 1",
    "SELECT codi_emp FROM geempre ORDER BY 1",
    "SELECT codi_emp FROM geempre LEFT JOIN efsaidas ON geempre.codi_emp = efsaidas.codi_emp",
    "SELECT codi_emp FROM geempre CROSS JOIN efsaidas",
    "SELECT codi_emp FROM geempre, efsaidas",
    "SELECT codi_emp FROM geempre TOP 5",
    # expressoes e funcoes
    "SELECT codi_emp + 1 FROM geempre",
    "SELECT codi_emp AS x FROM geempre",
    "SELECT UPPER(nome_emp) FROM geempre",
    "SELECT CASE WHEN codi_emp = 1 THEN 1 END FROM geempre",
    "SELECT SUM(vcon_sai + 1) AS t FROM efsaidas",
    "SELECT SUM(vcon_sai) FROM efsaidas",
    "SELECT SUM(DISTINCT vcon_sai) AS t FROM efsaidas",
    "SELECT AVG(*) AS t FROM efsaidas",
    "SELECT COUNT(DISTINCT *) AS t FROM efsaidas",
    "SELECT COUNT(*) FROM efsaidas",
    "SELECT STDDEV(vcon_sai) AS t FROM efsaidas",
    # identificadores e texto
    'SELECT "codi_emp" FROM geempre',
    'SELECT codi_emp FROM "geempre"',
    "SELECT [codi_emp] FROM geempre",
    "SELECT `codi_emp` FROM geempre",
    "SELECT codi_emp FROM bethadba.geempre",
    "SELECT codi_emp FROM sys.systable",
    "SELECT codi_emp FROM geempre WHERE nome_emp = 'abc",
    'SELECT codi_emp FROM geempre WHERE nome_emp = "abc"',
    "SELECT codi_emp FROM geempre WHERE nome_emp = 'a\x00b'",
    "SELECT codi_emp FROM geempre WHERE nome_emp = 'a\nb'",
    "SELECT codi_emp FROM geempre WHERE nome_emp = N'abc'",
    "SELECT codi_emp FROM geempre WHERE nome_emp = 0x41",
    "SELECT codi_emp FROM geempre WHERE codi_emp = 1abc",
    "SELECT codi_emp FROM geempre WHERE codi_emp = :p",
    "SELECT codi_emp FROM geempre WHERE codi_emp = ?",
    "SELECT codi_emp FROM geempre WHERE codi_emp = @v",
    "SELECT codi_emp FROM geempre WHERE codi_emp = $1",
    "SELECT codi_emp FROM geempre WHERE codi_emp = 1 \\ 2",
    # unicode e espacos que enganam
    "SELECT codi_emp FROM geempre WHERE codi_emp = 1; DROP TABLE x",  # ponto e virgula grego
    "SELECT codi_emp FROM geempre WHERE codi_emp = １",  # digito de largura total
    "SELECT codi_emp FROM geempre WHERE codi_emp = 1 ",  # separador de linha
    "SELECT codi_emp FROM geempre WHERE codi_emp = 1",  # espaco sem quebra
    "SELECT codі_emp FROM geempre",  # i cirilico
    "SELECT codi_emp FROM gee​mpre",  # espaco de largura zero
    # tamanho
    "SELECT codi_emp FROM geempre WHERE codi_emp IN (" + ",".join("1" for _ in range(500)) + ")",
    "SELECT " + "a" * (MAX_SQL_CHARS + 1),
    "",
    "   ",
    "SELECT",
    "SELECT FROM geempre",
    "SELECT codi_emp",
    "SELECT codi_emp FROM",
]


@pytest.fixture
def pack(tmp_path: Path) -> Pack:
    return build_demo_pack(tmp_path)


def _end_to_end(pack: Pack, sql: str) -> None:
    raw = translate(sql)
    vq = validate_query(raw.spec, pack, settings(), POLICY)
    check_joins(raw, vq)
    compile_query(vq, "bethadba")


def test_the_attack_suite_has_at_least_sixty_cases() -> None:
    assert len(ATTACKS) >= 60


@pytest.mark.parametrize("sql", ATTACKS)
def test_every_attack_is_refused_before_any_sql_is_built(pack: Pack, sql: str) -> None:
    with pytest.raises(QueryRefused) as raised:
        _end_to_end(pack, sql)
    assert raised.value.code in {"sql_recusado", "especificacao_invalida"}
    assert len(raised.value.message) < 400


def test_a_refusal_never_echoes_a_long_input() -> None:
    with pytest.raises(RawSqlRefused) as raised:
        translate("SELECT codi_emp FROM geempre WHERE codi_emp = " + "9" * 3000 + "x")
    assert len(raised.value.message) < 400


def test_tokens_that_hide_dml_stay_inside_quoted_text() -> None:
    raw = translate("SELECT codi_emp FROM geempre WHERE nome_emp = '; DROP TABLE x -- /* '")
    assert raw.spec.filtros[0].valor == "; DROP TABLE x -- /* "
    tokens = tokenize("SELECT 'a''b' FROM t")
    assert [t.kind for t in tokens[:3]] == ["word", "str", "word"] and tokens[1].text == "a'b"


# -- politica de L2 continua valendo por tras da gramatica ----------------------------------
POLICY_ATTACKS = [
    ("SELECT nome FROM gecertificadosdigitais", "tabela_bloqueada"),
    ("SELECT total FROM vw_totais", "tabela_bloqueada"),
    ("SELECT ende_emp FROM geempre", "coluna_bloqueada"),
    ("SELECT salario FROM foempregados", "coluna_bloqueada"),
    ("SELECT codi_emp FROM geempre WHERE ende_emp = 'rua'", "coluna_bloqueada"),
    ("SELECT codi_emp FROM geempre ORDER BY ende_emp", "coluna_bloqueada"),
    ("SELECT ende_emp FROM geempre GROUP BY ende_emp", "coluna_bloqueada"),
    ("SELECT nao_existe FROM geempre", "coluna_desconhecida"),
    ("SELECT codi_emp FROM nao_existe", "tabela_desconhecida"),
    ("SELECT cgce_emp FROM geempre WHERE cgce_emp LIKE '11%'", "coluna_bloqueada"),
    ("SELECT cgce_emp FROM geempre WHERE cgce_emp = '123'", "documento_invalido"),
    ("SELECT obs_sai FROM efsaidas WHERE obs_sai LIKE '%x%'", "coluna_bloqueada"),
    ("SELECT g.codi_emp FROM geempre g JOIN foempregados f ON g.codi_emp = f.codi_emp "
     "WHERE f.salario > 1", "coluna_bloqueada"),
]  # fmt: skip


@pytest.mark.parametrize(("sql", "code"), POLICY_ATTACKS)
def test_policy_still_applies_behind_the_grammar(pack: Pack, sql: str, code: str) -> None:
    with pytest.raises(QueryRefused) as raised:
        _end_to_end(pack, sql)
    assert raised.value.code == code


JOIN_ATTACKS = [
    # ON ligando outras colunas
    "SELECT g.codi_emp FROM geempre g JOIN efsaidas s ON g.codi_emp = s.codi_sai",
    # ON incompleto para FK composta
    "SELECT s.codi_sai FROM efsaidas s JOIN efmvspro m ON s.codi_emp = m.codi_emp",
    # ON que nao e igualdade
    "SELECT g.codi_emp FROM geempre g JOIN efsaidas s ON g.codi_emp < s.codi_emp",
    # ON com valor fixo
    "SELECT g.codi_emp FROM geempre g JOIN efsaidas s ON g.codi_emp = 1",
    # ON ligando a mesma tabela
    "SELECT g.codi_emp FROM geempre g JOIN efsaidas s ON g.codi_emp = g.codi_emp",
    # sem ON
    "SELECT g.codi_emp FROM geempre g JOIN efsaidas s",
    # coluna sem apelido quando ha juncao
    "SELECT codi_emp FROM geempre g JOIN efsaidas s ON g.codi_emp = s.codi_emp",
    # apelido repetido ou ausente
    "SELECT g.codi_emp FROM geempre g JOIN efsaidas g ON g.codi_emp = g.codi_emp",
    "SELECT x.codi_emp FROM geempre g JOIN efsaidas s ON g.codi_emp = s.codi_emp",
    # ON extra alem da FK
    "SELECT g.codi_emp FROM geempre g JOIN efsaidas s ON g.codi_emp = s.codi_emp "
    "AND g.codi_emp = s.codi_sai",
    # tabelas sem FK entre si
    "SELECT g.codi_emp FROM efsaidas g JOIN efclientes c ON g.codi_emp = c.codi_emp",
    # caminho que passa por tabela nao juntada (efmvspro -> geempre exige efsaidas)
    "SELECT m.nume_mvs FROM efmvspro m JOIN geempre g ON m.codi_emp = g.codi_emp",
]  # fmt: skip


@pytest.mark.parametrize("sql", JOIN_ATTACKS)
def test_a_join_that_is_not_exactly_the_declared_fk_is_refused(pack: Pack, sql: str) -> None:
    with pytest.raises(QueryRefused):
        _end_to_end(pack, sql)


# -- o que precisa passar --------------------------------------------------------------------
LEGIT = [
    "SELECT codi_emp, nome_emp FROM geempre",
    "select codi_emp, nome_emp from geempre where codi_emp = 10",
    "SELECT DISTINCT uf_cli FROM efclientes WHERE codi_emp = 1",
    "SELECT TOP 20 codi_sai, vcon_sai FROM efsaidas WHERE codi_emp = 1 AND dsai_sai >= '2026-01-01'"
    " AND dsai_sai <= '2026-03-31' ORDER BY dsai_sai DESC",
    "SELECT codi_sai FROM efsaidas WHERE codi_emp = 1 AND dsai_sai BETWEEN '2026-01-01' AND "
    "'2026-01-31' LIMIT 10 OFFSET 5",
    "SELECT codi_sai FROM efsaidas WHERE codi_emp = 1 AND dsai_sai >= '2026-01-01' AND situ_sai IN "
    "(1, 2)",
    "SELECT nome_cli FROM efclientes WHERE codi_emp = 1 AND nome_cli LIKE 'ACME%'",
    "SELECT codi_cli FROM efclientes WHERE codi_emp = 1 AND uf_cli IS NOT NULL",
    "SELECT seg_sai, COUNT(*) AS n, SUM(vcon_sai) AS total FROM efsaidas WHERE codi_emp = 1 AND "
    "dsai_sai >= '2026-01-01' AND dsai_sai <= '2026-12-31' GROUP BY seg_sai ORDER BY total DESC",
    "SELECT COUNT(DISTINCT codi_cli) AS clientes FROM efclientes WHERE codi_emp = 1",
    "SELECT g.nome_emp, s.vcon_sai FROM geempre g INNER JOIN efsaidas s ON g.codi_emp = "
    "s.codi_emp WHERE g.codi_emp = 1 AND s.dsai_sai >= '2026-01-01' AND s.dsai_sai <= '2026-01-31'",
    "SELECT s.codi_sai, m.vlor_mvs FROM efsaidas AS s JOIN efmvspro AS m ON s.codi_emp = "
    "m.codi_emp AND s.codi_sai = m.codi_sai AND s.seg_sai = m.seg_sai WHERE s.codi_emp = 1 AND "
    "s.dsai_sai >= '2026-01-01' AND s.dsai_sai <= '2026-01-31'",
    "SELECT   codi_emp ,\n nome_emp\tFROM geempre",
]  # fmt: skip


@pytest.mark.parametrize("sql", LEGIT)
def test_legitimate_queries_pass_the_whole_chain(pack: Pack, sql: str) -> None:
    _end_to_end(pack, sql)


def test_translation_maps_to_the_expected_structured_query() -> None:
    raw = translate(
        "SELECT TOP 5 seg_sai, SUM(vcon_sai) AS total FROM efsaidas WHERE codi_emp = 1 AND "
        "dsai_sai >= '2026-01-01' GROUP BY seg_sai ORDER BY total DESC"
    )
    spec = raw.spec.model_dump(mode="json", exclude_defaults=True)
    assert spec == {
        "tabela": "efsaidas",
        "colunas": ["seg_sai"],
        "agregacoes": [{"funcao": "sum", "coluna": "vcon_sai", "alias": "total"}],
        "filtros": [
            {"coluna": "codi_emp", "op": "=", "valor": 1},
            {"coluna": "dsai_sai", "op": ">=", "valor": "2026-01-01"},
        ],
        "agrupar_por": ["seg_sai"],
        "ordenar_por": [{"coluna": "total", "ordem": "desc"}],
        "limite": 5,
    }


def test_like_becomes_prefix_or_contains_and_never_a_raw_pattern() -> None:
    prefix = translate("SELECT a FROM t WHERE a LIKE 'ab%'").spec.filtros[0]
    contains = translate("SELECT a FROM t WHERE a LIKE '%ab%'").spec.filtros[0]
    assert (prefix.op, prefix.valor) == ("prefix", "ab")
    assert (contains.op, contains.valor) == ("contains", "ab")


def test_a_reserved_word_is_not_a_name_and_keywords_are_case_insensitive() -> None:
    with pytest.raises(RawSqlRefused):
        translate("SELECT select FROM geempre")
    with pytest.raises(RawSqlRefused):
        translate("SELECT a FROM geempre order")
    assert translate("sElEcT a fRoM t wHeRe a iS nUlL").spec.filtros[0].op == "is_null"


def test_where_clause_after_a_between_still_accepts_more_predicates() -> None:
    raw = translate("SELECT a FROM t WHERE a BETWEEN 1 AND 2 AND b = 3")
    assert [f.op for f in raw.spec.filtros] == ["between", "="]


def test_negative_and_decimal_literals() -> None:
    raw = translate("SELECT a FROM t WHERE a >= -5 AND b = 1.50")
    assert [f.valor for f in raw.spec.filtros] == [-5, "1.50"]
    with pytest.raises(RawSqlRefused):
        translate("SELECT a FROM t WHERE a = - 'x'")
