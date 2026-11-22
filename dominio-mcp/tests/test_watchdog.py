from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from dominio_mcp.watchdog import CancelUnconfirmed, CursorGuard, QueryTimeout, run_guarded
from fake_odbc import Block, FakeCursor, FakeDriver


def new_cursor(driver: FakeDriver | None = None) -> tuple[FakeDriver, FakeCursor]:
    driver = driver or FakeDriver()
    return driver, driver.connect("DSN=x").cursor()


def blocking_work(cursor: FakeCursor) -> Any:
    def work() -> str:
        cursor.execute("SELECT lento")
        return "nunca"

    return work


def test_fast_work_returns_value_and_closes_cursor_without_cancel() -> None:
    _, cursor = new_cursor()
    errors: list[BaseException] = []
    guard = CursorGuard(cursor, errors.append)
    assert run_guarded(guard, lambda: 42, timeout=1.0, confirm=1.0) == 42
    assert cursor.closed is True
    assert errors == []


def test_work_exception_propagates_unchanged_and_cursor_is_closed() -> None:
    _, cursor = new_cursor()
    guard = CursorGuard(cursor)

    def work() -> None:
        raise ValueError("falha do trabalho")

    with pytest.raises(ValueError, match="falha do trabalho"):
        run_guarded(guard, work, timeout=1.0, confirm=1.0)
    assert cursor.closed is True


def test_timeout_cancels_the_cursor_and_is_confirmed() -> None:
    driver, cursor = new_cursor()
    driver.server.script.append(Block())
    guard = CursorGuard(cursor)
    started = time.monotonic()
    with pytest.raises(QueryTimeout):
        run_guarded(guard, blocking_work(cursor), timeout=0.1, confirm=2.0)
    assert 0.09 <= time.monotonic() - started < 1.5
    assert cursor.closed is True


def test_late_cancel_never_touches_a_closed_cursor_or_the_next_one() -> None:
    driver = FakeDriver()
    _, cursor_a = new_cursor(driver)
    errors: list[BaseException] = []
    guard_a = CursorGuard(cursor_a, errors.append)
    guard_a.finish()
    assert cursor_a.closed is True

    _, cursor_b = new_cursor(driver)
    driver.server.script.append(Block())
    outcome: list[str] = []

    def run_b() -> None:
        try:
            cursor_b.execute("SELECT lento")
        except Exception:
            outcome.append("cancelado")

    thread = threading.Thread(target=run_b, daemon=True)
    thread.start()
    time.sleep(0.05)
    guard_a.cancel()  # cancelamento de A chega atrasado
    time.sleep(0.1)
    assert outcome == [], "o cancelamento de A atingiu a consulta B"
    assert not cursor_b._cancel.is_set()
    assert errors == []
    cursor_b.cancel()
    thread.join(2)
    assert outcome == ["cancelado"]


def test_cancel_that_blocks_ends_as_unconfirmed_and_does_not_hang_the_caller() -> None:
    driver, cursor = new_cursor()
    driver.server.cancel_mode = "blocks"
    driver.server.script.append(Block(ignore_cancel=True))
    guard = CursorGuard(cursor)
    started = time.monotonic()
    with pytest.raises(CancelUnconfirmed):
        run_guarded(guard, blocking_work(cursor), timeout=0.1, confirm=0.2)
    assert 0.29 <= time.monotonic() - started < 1.5
    driver.server.release()


def test_cancel_failure_is_swallowed_audited_and_leaves_it_unconfirmed() -> None:
    driver, cursor = new_cursor()
    driver.server.cancel_mode = "fails"
    driver.server.script.append(Block())
    errors: list[BaseException] = []
    guard = CursorGuard(cursor, errors.append)
    with pytest.raises(CancelUnconfirmed):
        run_guarded(guard, blocking_work(cursor), timeout=0.1, confirm=0.2)
    assert len(errors) == 1
    cursor._cancel.set()


def test_late_success_after_cancel_is_returned() -> None:
    _, cursor = new_cursor()
    guard = CursorGuard(cursor)

    def work() -> str:
        time.sleep(0.2)
        return "terminou"

    assert run_guarded(guard, work, timeout=0.1, confirm=2.0) == "terminou"


def test_predicate_decides_which_errors_count_as_the_cancellation() -> None:
    class Cancelled(Exception):
        pass

    _, cursor = new_cursor()
    guard = CursorGuard(cursor)

    def work_cancelled() -> None:
        time.sleep(0.2)
        raise Cancelled

    with pytest.raises(QueryTimeout):
        run_guarded(
            guard,
            work_cancelled,
            timeout=0.1,
            confirm=2.0,
            is_cancel_error=lambda e: type(e) is Cancelled,
        )

    _, cursor2 = new_cursor()
    guard2 = CursorGuard(cursor2)

    def work_other() -> None:
        time.sleep(0.2)
        raise ValueError("outro erro")

    with pytest.raises(ValueError, match="outro erro"):
        run_guarded(
            guard2,
            work_other,
            timeout=0.1,
            confirm=2.0,
            is_cancel_error=lambda e: type(e) is Cancelled,
        )


def test_guard_close_error_does_not_break_finish() -> None:
    class BadCursor:
        def cancel(self) -> None:
            return None

        def close(self) -> None:
            raise RuntimeError("falha ao fechar")

    guard = CursorGuard(BadCursor())
    guard.finish()
    guard.finish()
