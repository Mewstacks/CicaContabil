"""Exercise the fixed aggregate SQL against adversarial source-shaped rows."""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture
def source():
    connection = sqlite3.connect(":memory:")
    connection.execute("ATTACH DATABASE ':memory:' AS bethadba")
    connection.create_function("YEAR", 1, lambda value: int(value[:4]))
    connection.create_function("MONTH", 1, lambda value: int(value[5:7]))
    statements = [
        "CREATE TABLE bethadba.geempre(codi_emp INTEGER, stat_emp TEXT)",
        "CREATE TABLE bethadba.ctparmto(codi_emp INTEGER,codi_pad INTEGER,"
        "comp_pad TEXT,I_PLANOCONTAS INTEGER)",
        "CREATE TABLE bethadba.ctcontacaixa(codi_emp INTEGER,codi_cta INTEGER,"
        "sele_cta TEXT,TIPO_CONTA_CAIXA INTEGER)",
        "CREATE TABLE bethadba.CTCONTACAIXA_CONTA_BANCARIA(CODI_EMP INTEGER,"
        "I_CONTA_CAIXA INTEGER,I_SEQUENCIAL_CONTA_BANCARIA INTEGER)",
        "CREATE TABLE bethadba.ctlancto(codi_emp INTEGER,CODI_EMP_PLANO INTEGER,"
        "fili_lan INTEGER,data_lan TEXT,cdeb_lan INTEGER,ccre_lan INTEGER,codi_lote INTEGER)",
    ]
    for statement in statements:
        connection.execute(statement)
    connection.executemany(
        "INSERT INTO bethadba.geempre VALUES (?,?)", [(1, "A"), (2, "A"), (3, "M"), (4, "I")]
    )
    connection.executemany(
        "INSERT INTO bethadba.ctparmto VALUES (?,?,?,?)", [(1, 9, "N", 1), (3, 3, "S", 2)]
    )
    connection.executemany(
        "INSERT INTO bethadba.ctcontacaixa VALUES (?,?,?,?)",
        [(1, 8, "S", 1), (2, 8, "N", 2), (3, 8, "S", 1)],
    )
    connection.executemany(
        "INSERT INTO bethadba.CTCONTACAIXA_CONTA_BANCARIA VALUES (?,?,?)",
        [(1, 8, 1), (1, 8, 2), (3, 8, 1)],
    )
    connection.executemany(
        "INSERT INTO bethadba.ctlancto VALUES (?,?,?,?,?,?,?)",
        [
            (1, 9, 1, "2026-09-01", 0, 8, 1),
            (1, 9, 1, "2026-09-30", 8, 0, None),
            (1, 1, 0, "2026-10-31", 8, 9, 3),
            (1, 1, 0, "2026-08-31", 8, 9, 4),
            (1, 1, 0, "2026-11-01", 8, 9, 5),
            (3, 3, 0, "2026-09-01", 8, 9, 1),
            (4, 4, 0, "2026-09-01", 8, 9, 1),
        ],
    )
    yield connection
    connection.close()


def queries():
    text = (
        Path(__file__).parents[1] / "agent-windows/inspect-contad-portfolio-profile.ps1"
    ).read_text(encoding="utf-8-sig")
    fixed = re.findall(r"-Query @'\n(.*?)\n'@", text, re.S)
    assert len(fixed) == 3
    result = []
    for statement in fixed:
        match = re.search(r"SELECT TOP (\d+) ", statement)
        assert match
        result.append(re.sub(r"SELECT TOP \d+ ", "SELECT ", statement) + f" LIMIT {match[1]}")
        assert not re.search(
            r"\b(?:VLOR_LAN|CHIS_LAN|NDOC_LAN|NOME_EMP|NOME_CTA|AGENCIA|IDENTIFICADOR_CONTA)\b",
            statement,
            re.I,
        )
    return result


def test_active_companies_include_absent_configuration_and_preserve_duplicate_signal(source):
    sql = queries()[0]
    assert source.execute(sql, ["A"]).fetchall() == [(1, 1, 9, "N", 1), (2, 0, None, None, None)]
    source.execute("INSERT INTO bethadba.ctparmto VALUES (1,7,'S',2)")
    rows = source.execute(sql, ["A"]).fetchall()
    assert rows[0][1] == 2  # The reader must refuse this, never accept MIN as a mapping.


def test_bank_reference_multiplicity_uses_both_company_and_cash_keys(source):
    assert source.execute(queries()[1], ["A"]).fetchall() == [(1, 8, "S", 1, 2), (2, 8, "N", 2, 0)]


def test_monthly_count_covers_own_and_other_plan_branches_with_exclusive_period(source):
    rows = source.execute(queries()[2], ["A", "2026-09-01", "2026-11-01"]).fetchall()
    assert rows == [(1, 1, 0, 2026, 10, 1, 0, 0, 0), (1, 9, 1, 2026, 9, 2, 1, 1, 1)]
    assert source.execute(queries()[2], ["A", "2026-09-01", "2026-10-01"]).fetchall() == [rows[1]]
