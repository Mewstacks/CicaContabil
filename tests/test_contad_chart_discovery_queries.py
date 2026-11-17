"""Prove complete catalogue selection and bounded code-only usage against source-shaped rows."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "agent-windows/inspect-contad-chart-discovery.ps1"


def queries():
    raw = re.findall(r"@'\n(.*?)\n'@", SCRIPT.read_text(), re.S)
    business = [sql for sql in raw if "FROM bethadba." in sql]
    assert len(business) == 10
    result = {}
    for sql in business:
        match = re.search(r"SELECT TOP (\d+) ", sql)
        assert match
        assert not re.search(
            r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|CALL|CTEXTRATO|VLOR_LAN|CHIS_LAN|NDOC_LAN|SALDO(?:_INICIAL)?|CGCE_EMP)\b",
            sql,
            re.I,
        )
        table = re.search(r"FROM bethadba\.(\w+)", sql)[1].lower()
        result[table] = (
            re.sub(r"SELECT TOP \d+ ", "SELECT ", sql).replace("__OWNERS__", "?,?,?")
            + f" LIMIT {match[1]}"
        )
    return result


@pytest.fixture
def source():
    db = sqlite3.connect(":memory:")
    db.execute("ATTACH DATABASE ':memory:' AS bethadba")
    db.create_function("YEAR", 1, lambda v: int(v[:4]))
    db.create_function("MONTH", 1, lambda v: int(v[5:7]))
    db.executescript("""
      CREATE TABLE bethadba.geempre(codi_emp INTEGER,stat_emp TEXT);
      CREATE TABLE bethadba.ctparmto(codi_emp INTEGER,codi_pad INTEGER,comp_pad TEXT,
            I_PLANOCONTAS INTEGER,ccxa_par INTEGER,fili_par TEXT);
      CREATE TABLE bethadba.ctcontas(codi_emp INTEGER,codi_cta INTEGER,nome_cta TEXT,
            clas_cta TEXT,tipo_cta TEXT,SITUACAO_CTA TEXT,DATAINATIVA_CTA TEXT);
      CREATE TABLE bethadba.ctlancto(codi_emp INTEGER,CODI_EMP_PLANO INTEGER,fili_lan INTEGER,
            data_lan TEXT);
      CREATE TABLE bethadba.CTPLANOCONTAS(CODI_EMP INTEGER,I_PLANOCONTAS INTEGER,
            CODI_CTA INTEGER,NOME_CTA TEXT,CLAS_CTA TEXT,TIPO_CTA TEXT,SITUACAO_CTA TEXT,
            DATAINATIVA_CTA TEXT);
      CREATE TABLE bethadba.ctnatureza_conta(codi_emp INTEGER,ordem INTEGER,clas_cta TEXT,
            natureza TEXT,grupo TEXT);
      CREATE TABLE bethadba.CTCONTAS_EQUIVALENTES(CODI_EMP INTEGER,CODI_EMP_PLANO INTEGER,
            CODI_CTA INTEGER);
      INSERT INTO bethadba.geempre VALUES(1,'A'),(2,'A'),(3,'M'),(4,'I');
      INSERT INTO bethadba.ctparmto VALUES(1,99,'N',2,0,'N'),(3,3,'S',1,NULL,NULL);
      INSERT INTO bethadba.ctcontas VALUES
        (1,8,'Same own code','9 ','S','I','2026-10-01'),
        (99,8,'Shared chart account','001.0008 ','A','A',NULL),
        (99,999,'Unconfigured account','001.0999 ','A','A',NULL),
        (90,1,'Other referenced owner','2 ','S','A',NULL),
        (3,1,'Outside','3','A','A',NULL);
      INSERT INTO bethadba.CTPLANOCONTAS VALUES
        (99,1,8,'Template one','1 ','A','A',NULL),
        (99,2,8,'Template two','2 ','S','I','2026-09-01'),
        (3,1,8,'Outside','3','A','A',NULL);
      INSERT INTO bethadba.ctnatureza_conta VALUES
        (99,0,'001 ','X','Z'),(99,1,'001.008 ','D','A'),(3,0,'3','Y','Y');
      INSERT INTO bethadba.CTCONTAS_EQUIVALENTES VALUES(1,90,1),(2,99,999),(3,3,1);
      INSERT INTO bethadba.ctlancto VALUES
        (1,99,0,'2026-08-31'),(1,99,0,'2026-09-01'),(1,99,0,'2026-09-30'),
        (1,1,0,'2026-10-01'),(1,99,1,'2026-10-02'),(1,90,2,'2026-11-30'),
        (1,99,0,'2026-12-01'),(3,3,0,'2026-09-01');
    """)
    yield db
    db.close()


def test_missing_parameters_and_raw_shared_reference_are_not_resolved(source):
    assert source.execute(queries()["geempre"], ["A"]).fetchall() == [
        (1, 1, 99, "N", 2, 0, "N"),
        (2, None, None, None, None, None, None),
    ]


def test_catalogue_is_complete_even_without_conciliation_configuration(source):
    rows = source.execute(queries()["ctcontas"], [1, 99, 90]).fetchall()
    assert len(rows) == 4
    assert rows[0] == (1, 8, "Same own code", "9 ", "S", "I", "2026-10-01")
    assert rows[-1][1] == 999  # No CTCONCILIACAO row is needed to discover this account.
    assert rows[-2][0:2] == (99, 8)
    assert "ctconciliacao" not in queries()["ctcontas"].lower()


def test_usage_keeps_month_plan_branch_multiplicity_and_half_open_window(source):
    sql = queries()["ctlancto"]
    assert source.execute(sql, ["A", "2026-09-01", "2026-12-01"]).fetchall() == [
        (1, 1, 0, 2026, 10, 1),
        (1, 90, 2, 2026, 11, 1),
        (1, 99, 0, 2026, 9, 2),
        (1, 99, 1, 2026, 10, 1),
    ]
    select = sql.split("FROM")[0]
    assert "l.data_lan," not in select
    assert "COUNT(*)" in select


def test_templates_and_nature_rules_are_literal_independent_catalogues(source):
    templates = source.execute(queries()["ctplanocontas"], [1, 99, 90]).fetchall()
    assert [row[:3] for row in templates] == [(99, 1, 8), (99, 2, 8)]
    assert source.execute(queries()["ctnatureza_conta"], [1, 99, 90]).fetchall() == [
        (99, 0, "001 ", "X", "Z"),
        (99, 1, "001.008 ", "D", "A"),
    ]
    for name in ["ctplanocontas", "ctnatureza_conta"]:
        assert " JOIN " not in queries()[name]


def test_equivalent_reference_preserves_active_company_without_parameters(source):
    assert source.execute(queries()["ctcontas_equivalentes"], ["A"]).fetchall() == [
        (1, 90, 1),
        (2, 99, 999),
    ]


def test_duplicate_parameters_are_visible_to_reader_cardinality_rejection(source):
    source.execute("INSERT INTO bethadba.ctparmto VALUES(1,90,'S',1,NULL,NULL)")
    assert len(source.execute(queries()["geempre"], ["A"]).fetchall()) == 3


@pytest.mark.parametrize(
    "table,count,insert,params",
    [
        (
            "ctcontas",
            100001,
            "INSERT INTO bethadba.ctcontas VALUES(99,?,'Name','1','A','A',NULL)",
            [1, 99, 90],
        ),
        (
            "ctplanocontas",
            100001,
            "INSERT INTO bethadba.CTPLANOCONTAS VALUES(99,1,?,'Name','1','A','A',NULL)",
            [1, 99, 90],
        ),
        (
            "ctnatureza_conta",
            10001,
            "INSERT INTO bethadba.ctnatureza_conta VALUES(99,?,'1','X','Z')",
            [1, 99, 90],
        ),
        (
            "ctcontas_equivalentes",
            20001,
            "INSERT INTO bethadba.CTCONTAS_EQUIVALENTES VALUES(1,99,?)",
            ["A"],
        ),
        (
            "ctlancto",
            10001,
            "INSERT INTO bethadba.ctlancto VALUES(1,99,?,'2026-09-01')",
            ["A", "2026-09-01", "2026-12-01"],
        ),
    ],
)
def test_limit_plus_one_exposes_overflow_instead_of_silent_truncation(
    source, table, count, insert, params
):
    source.executemany(insert, ((i,) for i in range(1000, 1000 + count)))
    assert len(source.execute(queries()[table], params).fetchall()) == count


def test_fixed_metadata_queries_are_bounded_and_not_business_sql():
    metadata = [
        sql for sql in re.findall(r"@'\n(.*?)\n'@", SCRIPT.read_text(), re.S) if "FROM SYS." in sql
    ]
    assert len(metadata) == 3
    assert all("u.user_name=?" in sql or "fu.user_name=?" in sql for sql in metadata)
    assert all("SELECT TOP " in sql and "ORDER BY" in sql for sql in metadata)
    assert all("bethadba." not in sql for sql in metadata)
