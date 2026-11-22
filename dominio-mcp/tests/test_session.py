"""Execucao sob governo: A8 (cancelamento atrasado, quarentena, termino confirmado)."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.budget import Quarantined, RateLimited
from dominio_mcp.config import Limits, Settings
from dominio_mcp.odbc import (
    DbError,
    DbErrorKind,
    ExecutionUncertain,
    Session,
    build_session,
    probe_termination,
)
from dominio_mcp.quarantine import TerminationStatus
from dominio_mcp.watchdog import QueryTimeout
from fake_odbc import Block, Fail, FakeDriver, Rows


class Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def event(self, name: str, **fields: Any) -> None:
        self.events.append((name, fields))

    def names(self) -> list[str]:
        return [n for n, _ in self.events]


def make_session(
    tmp_path: Path,
    driver: FakeDriver | None = None,
    *,
    auditor: Recorder | None = None,
    confirm: float = 0.3,
    per_minute: int = 100,
    clock: Any = time.time,
) -> tuple[Session, FakeDriver]:
    driver = driver or FakeDriver()
    settings = Settings(
        dsn="contabil", home=tmp_path, limits=Limits(executions_per_minute=per_minute)
    )
    session = build_session(
        settings,
        driver=driver,
        auditor=auditor,
        clock=clock,
        confirm_seconds=confirm,
        lock_wait_seconds=0.3,
    )
    return session, driver


def wait_until(predicate: Any, seconds: float = 3.0) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("condicao nao atendida a tempo")


def query_cursors(driver: FakeDriver, text: str) -> list[Any]:
    return [c for c in driver.server.cursors if any(text in sql for sql, _ in c.executed)]


def test_reuses_the_connection_and_gives_each_execution_its_own_closed_cursor(
    tmp_path: Path,
) -> None:
    session, driver = make_session(tmp_path)
    driver.server.script += [Rows(["a"], [(1,)]), Rows(["a"], [(2,)])]
    r1 = session.execute("SELECT um", max_rows=5)
    r2 = session.execute("SELECT dois", max_rows=5)
    assert (r1.rows, r2.rows) == ([[1]], [[2]])
    assert len(driver.server.connections) == 1
    c1, c2 = query_cursors(driver, "SELECT um")[0], query_cursors(driver, "SELECT dois")[0]
    assert c1 is not c2
    assert all(c.closed for c in driver.server.cursors)
    session.close()
    assert driver.server.connections[0].closed is True
    session.close()


def test_timeout_is_cancelled_and_the_connection_stays_usable(tmp_path: Path) -> None:
    rec = Recorder()
    session, driver = make_session(tmp_path, auditor=rec)
    driver.server.script += [Block(), Rows(["a"], [(1,)])]
    with pytest.raises(QueryTimeout):
        session.execute("SELECT lento", max_rows=5, timeout=0.1)
    assert session.connected is True
    assert session.execute("SELECT 1", max_rows=5).rows == [[1]]
    assert len(driver.server.connections) == 1
    assert rec.names() == ["consulta_cancelada"]
    assert "lento" not in str(rec.events)


def test_unconfirmed_cancel_quarantines_for_every_process_until_termination_is_confirmed(
    tmp_path: Path,
) -> None:
    rec = Recorder()
    session, driver = make_session(tmp_path, auditor=rec, confirm=0.2)
    driver.server.cancel_mode = "blocks"
    driver.server.script += [Block(ignore_cancel=True)]
    with pytest.raises(ExecutionUncertain):
        session.execute("SELECT lento", max_rows=5, timeout=0.1)
    abandoned = driver.server.connections[0]
    assert abandoned.closed is False
    assert session.connected is False
    assert session.governor.quarantine.is_active()
    assert "execucao_incerta" in rec.names()

    # "segundo processo": outra sessao com o mesmo diretorio de estado
    other, _ = make_session(tmp_path, driver)
    for who in (session, other):
        with pytest.raises(Quarantined):
            who.execute("SELECT 1", max_rows=5)
    assert driver.server.script == [], "nenhuma consulta pode ser executada em quarentena"

    # o servidor encerra a consulta: a conexao descartada some de sa_conn_info()
    driver.server.release()
    wait_until(lambda: abandoned.closed)
    driver.server.script.append(Rows(["a"], [(9,)]))
    assert other.execute("SELECT 9", max_rows=5).rows == [[9]]
    assert not other.governor.quarantine.is_active()
    # o cancelamento atrasado da consulta A nao atingiu a B
    assert not query_cursors(driver, "SELECT 9")[0]._cancel.is_set()


def test_cancel_that_fails_is_audited_and_leaves_the_execution_uncertain(tmp_path: Path) -> None:
    rec = Recorder()
    session, driver = make_session(tmp_path, auditor=rec, confirm=0.2)
    driver.server.cancel_mode = "fails"
    driver.server.script += [Block()]
    with pytest.raises(ExecutionUncertain):
        session.execute("SELECT lento", max_rows=5, timeout=0.1)
    assert "cancelamento_falhou" in rec.names()
    assert session.governor.quarantine.is_active()
    query_cursors(driver, "SELECT lento")[0]._cancel.set()


def test_reset_is_the_other_way_out_of_quarantine(tmp_path: Path) -> None:
    session, driver = make_session(tmp_path, confirm=0.2)
    driver.server.cancel_mode = "blocks"
    driver.server.script += [Block(ignore_cancel=True)]
    with pytest.raises(ExecutionUncertain):
        session.execute("SELECT lento", max_rows=5, timeout=0.1)
    with pytest.raises(Quarantined):
        session.execute("SELECT 1", max_rows=5)
    assert session.governor.reset() is True
    driver.server.script.append(Rows(["a"], [(1,)]))
    assert session.execute("SELECT 1", max_rows=5).rows == [[1]]
    driver.server.release()


def test_lost_connection_is_discarded_and_reopened(tmp_path: Path) -> None:
    session, driver = make_session(tmp_path)
    driver.server.script += [Fail("08S01", "Communication link failure"), Rows(["a"], [(1,)])]
    with pytest.raises(DbError) as exc:
        session.execute("SELECT 1", max_rows=5)
    assert exc.value.kind is DbErrorKind.LOST
    assert session.connected is False
    assert driver.server.connections[0].closed is True
    assert session.execute("SELECT 1", max_rows=5).rows == [[1]]
    assert len(driver.server.connections) == 2


def test_ordinary_errors_keep_the_connection_and_hide_driver_text(tmp_path: Path) -> None:
    session, driver = make_session(tmp_path)
    driver.server.script += [
        Fail("42000", "[42000] Syntax error near 'SEGREDO' (-131)"),
        Rows(["a"], [(1,)]),
    ]
    with pytest.raises(DbError) as exc:
        session.execute("SELECT x", max_rows=5)
    assert exc.value.kind is DbErrorKind.SYNTAX
    assert "SEGREDO" not in str(exc.value)
    assert exc.value.__cause__ is None
    assert exc.value.__context__ is None
    assert session.connected is True
    assert session.execute("SELECT 1", max_rows=5).rows == [[1]]
    assert len(driver.server.connections) == 1
    assert all(c.closed for c in driver.server.cursors)


def test_quarantine_refusal_does_not_open_a_connection_or_run_anything(tmp_path: Path) -> None:
    session, driver = make_session(tmp_path)
    driver.server.live_numbers.add(5)
    session.governor.quarantine.enter(5, "teste")
    with pytest.raises(Quarantined):
        session.execute("SELECT 1", max_rows=5)
    assert session.connected is False
    assert driver.server.script == []
    assert not any("SELECT 1" in sql for sql, _ in driver.server.log)


def test_frequency_budget_is_enforced_per_minute(tmp_path: Path) -> None:
    session, driver = make_session(tmp_path, per_minute=1, clock=lambda: 1000.0)
    driver.server.script += [Rows(["a"], [(1,)]), Rows(["a"], [(2,)])]
    session.execute("SELECT 1", max_rows=5)
    with pytest.raises(RateLimited):
        session.execute("SELECT 2", max_rows=5)


# --- probe_termination -----------------------------------------------------------------------


def test_probe_termination_reads_sa_conn_info() -> None:
    driver = FakeDriver()
    driver.server.live_numbers.add(42)
    assert probe_termination(driver, "contabil", 42) is TerminationStatus.RUNNING
    assert probe_termination(driver, "contabil", 43) is TerminationStatus.TERMINATED
    assert all(c.closed for c in driver.server.connections), "a conexao da sonda precisa fechar"


def test_probe_termination_is_unknown_when_it_cannot_tell() -> None:
    driver = FakeDriver()
    driver.server.sa_conn_info_error = True
    assert probe_termination(driver, "contabil", 42) is TerminationStatus.UNKNOWN
    driver2 = FakeDriver()
    driver2.server.connect_failures = 1
    assert probe_termination(driver2, "contabil", 42) is TerminationStatus.UNKNOWN


# --- lote (varias consultas, uma admissao) ---------------------------------------------------


def test_batch_is_one_admission_and_errors_become_results(tmp_path: Path) -> None:
    session, driver = make_session(tmp_path, per_minute=1, clock=lambda: 1000.0)
    driver.server.script += [
        Rows([], []),
        Fail("42000", "[42000] Permission denied: SEGREDO (-121)"),
        Rows([], []),
    ]
    out = session.execute_batch(["a", "b", "c"])
    assert [type(o).__name__ for o in out] == ["RawResult", "DbError", "RawResult"]
    assert isinstance(out[1], DbError) and out[1].kind is DbErrorKind.DENIED
    with pytest.raises(RateLimited):
        session.execute("SELECT 1", max_rows=1)
    assert all(c.closed for c in driver.server.cursors)


def test_batch_item_that_times_out_does_not_stop_the_batch(tmp_path: Path) -> None:
    session, driver = make_session(tmp_path)
    driver.server.script += [Block(), Rows([], [])]
    out = session.execute_batch(["lenta", "ok"], timeout_each=0.1)
    assert isinstance(out[0], QueryTimeout)
    assert not isinstance(out[1], (QueryTimeout, DbError))
    assert session.connected is True


def test_batch_aborts_on_lost_connection(tmp_path: Path) -> None:
    session, driver = make_session(tmp_path)
    driver.server.script += [Fail("08S01", "Communication link failure"), Rows([], [])]
    with pytest.raises(DbError) as exc:
        session.execute_batch(["a", "b"])
    assert exc.value.kind is DbErrorKind.LOST
    assert session.connected is False
    assert len(driver.server.script) == 1, "a segunda consulta nao pode rodar"


def test_batch_aborts_and_quarantines_when_cancel_is_unconfirmed(tmp_path: Path) -> None:
    session, driver = make_session(tmp_path, confirm=0.2)
    driver.server.cancel_mode = "blocks"
    driver.server.script += [Block(ignore_cancel=True), Rows([], [])]
    with pytest.raises(ExecutionUncertain):
        session.execute_batch(["lenta", "b"], timeout_each=0.1)
    assert session.governor.quarantine.is_active()
    assert len(driver.server.script) == 1
    driver.server.release()


# --- slot: varias consultas, uma admissao ------------------------------------------------------


def test_slot_runs_several_queries_under_one_admission(tmp_path: Path) -> None:
    session, driver = make_session(tmp_path, per_minute=1, clock=lambda: 1000.0)
    driver.server.script += [Rows(["a"], [(1,)]), Rows(["a"], [(2,)])]
    with session.slot() as slot:
        assert slot.execute("SELECT 1", max_rows=5).rows == [[1]]
        assert slot.execute("SELECT 2", max_rows=5).rows == [[2]]
    with pytest.raises(RateLimited):
        session.execute("SELECT 3", max_rows=5)
    assert all(c.closed for c in driver.server.cursors)


def test_slot_holds_the_process_lock_for_its_whole_block(tmp_path: Path) -> None:
    from dominio_mcp.budget import ProcessLock

    session, _ = make_session(tmp_path)
    with session.slot():
        other = ProcessLock(tmp_path / "state" / "contabil.lock")
        assert other.acquire(0.05) is False
    other2 = ProcessLock(tmp_path / "state" / "contabil.lock")
    assert other2.acquire(0.2) is True
    other2.release()
