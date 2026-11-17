"""Execute the fixed cadastral SQL against isolated, adversarial source-shaped rows."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parents[1] / "agent-windows/inspect-contad-account-details.ps1"


def queries():
    statements = re.findall(r"-Query @'\n(.*?)\n'@", SCRIPT.read_text(), re.S)
    assert len(statements) == 4
    result = []
    for sql in statements:
        match = re.search(r"SELECT TOP (\d+) ", sql)
        assert match and sql.count("?") == 1
        assert "WHERE g.stat_emp=?" in sql
        assert not re.search(
            r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|EXEC|CALL|CTLANCTO|CTEXTRATO|VALOR|SALDO)\b",
            sql, re.I,
        )
        result.append(re.sub(r"SELECT TOP \d+ ", "SELECT ", sql) + f" LIMIT {match[1]}")
    return result


@pytest.fixture
def source():
    db = sqlite3.connect(":memory:")
    db.execute("ATTACH DATABASE ':memory:' AS bethadba")
    db.executescript("""
        CREATE TABLE bethadba.geempre(codi_emp INTEGER, stat_emp TEXT);
        CREATE TABLE bethadba.CTCONCILIACAO_CONTA(CODI_EMP INTEGER,
            CODI_EMP_PLANO INTEGER,CODI_CTA INTEGER);
        CREATE TABLE bethadba.ctcontas(codi_emp INTEGER,codi_cta INTEGER,nome_cta TEXT,
            clas_cta TEXT,tipo_cta TEXT,SITUACAO_CTA TEXT,DATAINATIVA_CTA TEXT);
        CREATE TABLE bethadba.ctcontacaixa(codi_emp INTEGER,codi_cta INTEGER,
            sele_cta TEXT,TIPO_CONTA_CAIXA INTEGER);
        CREATE TABLE bethadba.CTCONTACAIXA_CONTA_BANCARIA(CODI_EMP INTEGER,I_CONTA_CAIXA INTEGER,
            I_SEQUENCIAL_CONTA_BANCARIA INTEGER,AGENCIA TEXT,
            IDENTIFICADOR_CONTA TEXT,I_BANCO INTEGER);
        CREATE TABLE bethadba.CTLISTA_BANCOS_BANCO_CENTRAL(I_BANCO INTEGER,
            CODIGO_BANCO INTEGER,DESCRICAO_BANCO TEXT);
        INSERT INTO bethadba.geempre VALUES(1,'A'),(2,'A'),(3,'M'),(4,'I');
        INSERT INTO bethadba.CTCONCILIACAO_CONTA VALUES(1,99,8),(2,2,8),(3,3,8);
        INSERT INTO bethadba.ctcontas VALUES
            (99,8,'Shared chart','001.008 ','A','A',NULL),
            (1,8,'Wrong own chart','2','A','A',NULL),(3,8,'Excluded','3','A','A',NULL);
        INSERT INTO bethadba.ctcontacaixa VALUES(1,8,'S',0),(2,8,'N',NULL),(3,8,'S',1);
        INSERT INTO bethadba.CTLISTA_BANCOS_BANCO_CENTRAL VALUES(7,0,'Synthetic bank');
        INSERT INTO bethadba.CTCONTACAIXA_CONTA_BANCARIA VALUES
            (1,8,0,'0001','0000123-0',7),(1,8,1,'0002','0000124-0',NULL),
            (2,99,0,'0003','0000125-0',999),(3,8,0,'0004','EXCLUDED',7);
    """)
    yield db
    db.close()


def test_active_scope_keeps_company_without_config_and_excludes_other_states(source):
    assert source.execute(queries()[0], ["A"]).fetchall() == [(1,), (2,)]
    assert [row[0] for row in source.execute(queries()[1], ["A"])] == [1, 2]
    assert [row[0] for row in source.execute(queries()[2], ["A"])] == [1, 2]
    assert [row[0] for row in source.execute(queries()[3], ["A"])] == [1, 1, 2]


def test_chart_uses_declared_owner_and_preserves_absent_catalog(source):
    rows = source.execute(queries()[1], ["A"]).fetchall()
    assert rows[0] == (1, 99, 8, 8, "Shared chart", "001.008 ", "A", "A", None)
    assert rows[1] == (2, 2, 8, None, None, None, None, None, None)


def test_bank_refs_keep_multiplicity_zeros_and_null_catalog_without_cash_inference(source):
    rows = source.execute(queries()[3], ["A"]).fetchall()
    assert rows == [
        (1, 8, 0, "0001", "0000123-0", 7, 7, 0, "Synthetic bank"),
        (1, 8, 1, "0002", "0000124-0", None, None, None, None),
        (2, 99, 0, "0003", "0000125-0", 999, None, None, None),
    ]
    # A bank reference with no cash key must stay visible to the reader's gap flag.
    assert source.execute(queries()[2], ["A"]).fetchall() == [(1, 8, "S", 0), (2, 8, "N", None)]


@pytest.mark.parametrize("query,insert", [
    (1, "INSERT INTO bethadba.ctcontas VALUES (99,8,'Duplicate','1','A','A',NULL)"),
    (3, "INSERT INTO bethadba.CTLISTA_BANCOS_BANCO_CENTRAL VALUES (7,1,'Duplicate')"),
])
def test_fanout_is_not_silently_aggregated_or_discarded(source, query, insert):
    before = source.execute(queries()[query], ["A"]).fetchall()
    source.execute(insert)
    after = source.execute(queries()[query], ["A"]).fetchall()
    assert len(after) == len(before) + 1  # Windows reader rejects the repeated composite key.


@pytest.mark.parametrize("query,count,insert", [
    (0, 501, "INSERT INTO bethadba.geempre VALUES (?, 'A')"),
    (1, 5001, "INSERT INTO bethadba.CTCONCILIACAO_CONTA VALUES (1,99,?)"),
    (2, 5001, "INSERT INTO bethadba.ctcontacaixa VALUES (1,?,'S',0)"),
    (3, 20001, "INSERT INTO bethadba.CTCONTACAIXA_CONTA_BANCARIA VALUES (1,8,?,'0001','0000',7)"),
])
def test_query_returns_limit_plus_one_so_reader_can_refuse_truncation(source, query, count, insert):
    source.executemany(insert, [(value,) for value in range(100, 100 + count)])
    assert len(source.execute(queries()[query], ["A"]).fetchall()) == count
