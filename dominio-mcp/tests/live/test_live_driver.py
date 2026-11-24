"""Teste vivo do driver no banco real (somente leitura, so catalogo; sem dado de negocio).

Rode com:  $env:DOMINIO_MCP_LIVE = '1'; uv run --directory dominio-mcp pytest -q -m live tests/live
"""

from __future__ import annotations

import os
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from dominio_mcp.config import Settings
from dominio_mcp.odbc import Session, build_session, load_driver, open_connection, probe_termination
from dominio_mcp.quarantine import TerminationStatus
from dominio_mcp.watchdog import QueryTimeout

pytestmark = pytest.mark.live

DSN = os.environ.get("DOMINIO_MCP_DSN", "contabil")
REMARK_SQL = (
    "SELECT r.remarks FROM SYS.SYSTAB t JOIN SYS.SYSTABCOL c ON c.table_id = t.table_id "
    "JOIN SYS.SYSREMARK r ON r.object_id = c.object_id "
    "WHERE t.table_name = 'geempre' AND c.column_name = 'tins_emp'"
)


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    sess = build_session(Settings(dsn=DSN, home=tmp_path), lock_wait_seconds=5.0)
    try:
        yield sess
    finally:
        sess.close()


def test_connection_recipe_and_isolation_level() -> None:
    driver = load_driver()
    conn = open_connection(driver, DSN)
    try:
        assert conn.number is not None and conn.number > 0
        cursor = conn.raw.cursor()
        try:
            cursor.execute("SELECT CONNECTION_PROPERTY('isolation_level')")
            assert int(cursor.fetchone()[0]) == 0
        finally:
            cursor.close()
    finally:
        conn.close()


def test_accents_arrive_correct_by_code_point(session: Session) -> None:
    result = session.execute(REMARK_SQL, max_rows=3)
    assert len(result.rows) == 1
    text = result.rows[0][0]
    assert isinstance(text, str)
    index = text.index("inscri") + len("inscri")
    assert [ord(c) for c in text[index : index + 2]] == [0x00E7, 0x00E3]
    assert chr(0xFFFD) not in text


def test_fetchmany_with_truncation_probe(session: Session) -> None:
    result = session.execute("SELECT TOP 7 table_id FROM SYS.SYSTAB ORDER BY table_id", max_rows=5)
    assert len(result.rows) == 5
    assert result.truncated is True
    full = session.execute("SELECT TOP 3 table_id FROM SYS.SYSTAB ORDER BY table_id", max_rows=5)
    assert len(full.rows) == 3
    assert full.truncated is False


def test_slow_query_is_cancelled_within_limit_and_connection_is_reusable(session: Session) -> None:
    started = time.monotonic()
    with pytest.raises(QueryTimeout):
        session.execute("WAITFOR DELAY '00:00:10'", max_rows=1, timeout=2.0)
    assert time.monotonic() - started <= 4.0
    assert session.connected is True
    again = session.execute("SELECT 1", max_rows=1)
    assert again.rows == [[1]]


def test_late_cancel_on_a_closed_cursor_is_harmless() -> None:
    driver = load_driver()
    conn = open_connection(driver, DSN)
    try:
        old = conn.raw.cursor()
        old.execute("SELECT 1")
        old.fetchall()
        old.close()
        with pytest.raises(driver.ProgrammingError):
            old.cancel()
        fresh = conn.raw.cursor()
        try:
            fresh.execute("SELECT 2")
            assert fresh.fetchone()[0] == 2
        finally:
            fresh.close()
    finally:
        conn.close()


def test_sa_conn_info_confirms_termination_of_a_closed_connection() -> None:
    driver = load_driver()
    conn = open_connection(driver, DSN)
    assert conn.number is not None
    number = conn.number
    assert probe_termination(driver, DSN, number) is TerminationStatus.RUNNING
    conn.close()
    deadline = time.monotonic() + 10
    status = probe_termination(driver, DSN, number)
    while status is not TerminationStatus.TERMINATED and time.monotonic() < deadline:
        time.sleep(0.25)
        status = probe_termination(driver, DSN, number)
    assert status is TerminationStatus.TERMINATED
