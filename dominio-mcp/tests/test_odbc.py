from __future__ import annotations

import importlib
from datetime import date
from decimal import Decimal

import pytest

from dominio_mcp.odbc import (
    DbError,
    DbErrorKind,
    OdbcUnavailable,
    load_driver,
    map_error,
    open_connection,
    run_statement,
)
from fake_odbc import SQL_CHAR, SQL_WCHAR, Error, Fail, FakeDriver, Rows


def test_open_connection_applies_the_verified_recipe() -> None:
    driver = FakeDriver()
    conn = open_connection(driver, "contabil")
    server = driver.server
    fake = server.connections[0]
    assert driver.pooling is False
    assert fake.connection_string == "DSN=contabil"
    assert fake.kwargs == {"autocommit": True, "readonly": True, "timeout": 15}
    assert (SQL_CHAR, {"encoding": "utf-16le", "ctype": SQL_WCHAR}) in fake.decodings
    assert (SQL_WCHAR, {"encoding": "utf-16le"}) in fake.decodings
    assert any(sql == "SET TEMPORARY OPTION isolation_level = 0" for sql, _ in server.log)
    assert conn.number == fake.number
    assert all(c.closed for c in server.cursors), "cursores de inicializacao precisam fechar"


def test_open_connection_login_timeout_is_configurable() -> None:
    driver = FakeDriver()
    open_connection(driver, "contabil", login_timeout=5)
    assert driver.server.connections[0].kwargs["timeout"] == 5


def test_open_connection_failure_is_a_db_error_without_driver_text() -> None:
    driver = FakeDriver()
    driver.server.connect_failures = 1
    with pytest.raises(DbError) as exc:
        open_connection(driver, "contabil")
    assert exc.value.kind is DbErrorKind.LOST
    assert "nao conectou" not in str(exc.value)


def run(driver: FakeDriver, steps: list[object], sql: str = "SELECT 1", **kw: object):  # type: ignore[no-untyped-def]
    driver.server.script.extend(steps)
    conn = open_connection(driver, "contabil")
    cursor = conn.raw.cursor()
    return run_statement(driver, cursor, sql, **kw), cursor  # type: ignore[arg-type]


def test_run_statement_returns_normalized_rows_and_columns() -> None:
    driver = FakeDriver()
    rows = [(Decimal("10.50"), "ABC   ", date(2026, 1, 31)), (None, "X", date(2026, 2, 1))]
    result, _ = run(driver, [Rows(["v", "nome", "dt"], rows)], max_rows=10)
    assert result.columns == ("v", "nome", "dt")
    assert result.rows == [[10.5, "ABC", "2026-01-31"], [None, "X", "2026-02-01"]]
    assert result.truncated is False
    assert result.elapsed_ms >= 0
    assert result.read_at.tzinfo is not None


def test_truncation_uses_a_probe_row() -> None:
    driver = FakeDriver()
    result, _ = run(driver, [Rows(["n"], [(i,) for i in range(6)])], max_rows=5)
    assert len(result.rows) == 5
    assert result.truncated is True

    driver2 = FakeDriver()
    result2, _ = run(driver2, [Rows(["n"], [(i,) for i in range(5)])], max_rows=5)
    assert len(result2.rows) == 5
    assert result2.truncated is False


def test_fetch_is_batched_and_never_reads_past_the_probe_row() -> None:
    driver = FakeDriver()
    result, cursor = run(driver, [Rows(["n"], [(i,) for i in range(1200)])], max_rows=1000)
    assert len(result.rows) == 1000
    assert result.truncated is True
    assert max(cursor.fetch_sizes) <= 500  # type: ignore[attr-defined]
    assert sum(cursor.fetch_sizes) == 1001  # type: ignore[attr-defined]


def test_params_are_passed_positionally_and_sql_untouched() -> None:
    driver = FakeDriver()
    sql = 'SELECT "a" FROM "bethadba"."t" WHERE "x" = ? AND "y" = ?'
    _, cursor = run(driver, [Rows(["a"], [])], sql=sql, params=(560, "O'Brien"), max_rows=5)
    assert cursor.executed[-1] == (sql, (560, "O'Brien"))  # type: ignore[attr-defined]


def test_statement_without_result_set_returns_empty() -> None:
    driver = FakeDriver()
    result, _ = run(driver, [Rows([], [])], max_rows=5)
    assert result.columns == ()
    assert result.rows == []


@pytest.mark.parametrize(
    ("sqlstate", "message", "kind", "native"),
    [
        (
            "HY001",
            "[HY001] [SAP][ODBC Driver][SQL Anywhere]Statement interrupted by user (-299)",
            DbErrorKind.CANCELLED,
            -299,
        ),
        ("HY008", "Operation canceled", DbErrorKind.CANCELLED, None),
        ("42S02", "[42S02] Table 'SEGREDO_TABELA' not found (-141)", DbErrorKind.NOT_FOUND, -141),
        ("42S22", "[42S22] Column 'SEGREDO_COL' not found (-143)", DbErrorKind.NOT_FOUND, -143),
        (
            "42000",
            "[42000] Permission denied: you do not have permission to select (-121)",
            DbErrorKind.DENIED,
            -121,
        ),
        ("42000", "[42000] Syntax error near 'SEGREDO_SQL' (-131)", DbErrorKind.SYNTAX, -131),
        ("08S01", "Communication link failure", DbErrorKind.LOST, None),
        ("HY000", "[HY000] Connection was terminated (-308)", DbErrorKind.LOST, -308),
        ("HY000", "[HY000] Communication error (-85)", DbErrorKind.LOST, -85),
        (
            "23000",
            "[23000] Value 'SEGREDO_VALOR' violates something (-196)",
            DbErrorKind.OTHER,
            -196,
        ),
    ],
)
def test_error_mapping_never_echoes_driver_text(
    sqlstate: str, message: str, kind: DbErrorKind, native: int | None
) -> None:
    err = map_error(Error(sqlstate, message))
    assert err.kind is kind
    assert err.native_code == native
    assert err.sqlstate == sqlstate
    assert "SEGREDO" not in str(err)
    assert "SEGREDO" not in repr(err)


def test_error_mapping_handles_odd_exceptions() -> None:
    assert map_error(Error("so um argumento")).kind is DbErrorKind.OTHER
    assert map_error(Error()).sqlstate == "?"
    assert map_error(Error(42, None)).kind is DbErrorKind.OTHER  # type: ignore[arg-type]


def test_run_statement_maps_driver_errors() -> None:
    driver = FakeDriver()
    driver.server.script.append(Fail("42S02", "[42S02] Table 'SEGREDO' not found (-141)"))
    conn = open_connection(driver, "contabil")
    with pytest.raises(DbError) as exc:
        run_statement(driver, conn.raw.cursor(), "SELECT 1", max_rows=5)
    assert exc.value.kind is DbErrorKind.NOT_FOUND
    assert "SEGREDO" not in str(exc.value)


def test_load_driver_reports_a_clear_error_when_pyodbc_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def boom(name: str, package: str | None = None) -> object:
        raise ImportError("sem pyodbc")

    monkeypatch.setattr(importlib, "import_module", boom)
    with pytest.raises(OdbcUnavailable, match="pyodbc"):
        load_driver()
