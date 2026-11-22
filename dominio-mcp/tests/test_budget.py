from __future__ import annotations

import json
import subprocess
import sys
import textwrap
import threading
import time
from pathlib import Path

import pytest

from dominio_mcp.budget import (
    Busy,
    ExecutionGovernor,
    ProcessLock,
    Quarantined,
    RateBudget,
    RateLimited,
)
from dominio_mcp.quarantine import TerminationStatus


def never_probe(number: int) -> TerminationStatus:
    raise AssertionError("o probe nao devia ser chamado")


def governor(
    tmp_path: Path,
    *,
    per_minute: int = 100,
    wait: float = 0.3,
    prober=lambda n: TerminationStatus.UNKNOWN,  # type: ignore[no-untyped-def]
    clock=time.time,  # type: ignore[no-untyped-def]
) -> ExecutionGovernor:
    return ExecutionGovernor(
        tmp_path / "state",
        "contabil",
        per_minute=per_minute,
        prober=prober,
        wait_seconds=wait,
        clock=clock,
    )


# --- ProcessLock -----------------------------------------------------------------------------


def test_lock_excludes_a_second_holder_until_released(tmp_path: Path) -> None:
    path = tmp_path / "x.lock"
    a, b = ProcessLock(path), ProcessLock(path)
    assert a.acquire(0.1) is True
    assert b.acquire(0.1) is False
    a.release()
    assert b.acquire(0.1) is True
    b.release()


def test_release_without_acquire_is_harmless(tmp_path: Path) -> None:
    ProcessLock(tmp_path / "x.lock").release()


HOLDER = textwrap.dedent(
    """
    import sys, time, pathlib
    from dominio_mcp.budget import ProcessLock
    lock = ProcessLock(pathlib.Path(sys.argv[1]))
    assert lock.acquire(2.0)
    pathlib.Path(sys.argv[2]).write_text("preso")
    time.sleep(float(sys.argv[3]))
    lock.release()
    """
)


def wait_for(path: Path, seconds: float = 10.0) -> None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        if path.exists():
            return
        time.sleep(0.02)
    raise AssertionError(f"{path} nao apareceu")


def test_two_real_processes_never_hold_the_lock_together(tmp_path: Path) -> None:
    lock_path, marker = tmp_path / "x.lock", tmp_path / "preso.txt"
    proc = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", HOLDER, str(lock_path), str(marker), "1.5"]
    )
    try:
        wait_for(marker)
        mine = ProcessLock(lock_path)
        assert mine.acquire(0.2) is False, "dois processos seguraram a trava juntos"
        proc.wait(timeout=10)
        assert mine.acquire(1.0) is True
        mine.release()
    finally:
        proc.kill()


def test_lock_is_released_when_the_holder_process_dies(tmp_path: Path) -> None:
    lock_path, marker = tmp_path / "x.lock", tmp_path / "preso.txt"
    proc = subprocess.Popen(  # noqa: S603
        [sys.executable, "-c", HOLDER, str(lock_path), str(marker), "30"]
    )
    try:
        wait_for(marker)
        proc.kill()
        proc.wait(timeout=10)
        mine = ProcessLock(lock_path)
        assert mine.acquire(2.0) is True
        mine.release()
    finally:
        proc.kill()


# --- RateBudget ------------------------------------------------------------------------------


def test_rate_budget_blocks_the_call_after_the_limit_and_recovers(tmp_path: Path) -> None:
    clock = [1000.0]
    budget = RateBudget(tmp_path / "rate.json", per_minute=2, clock=lambda: clock[0])
    budget.check_and_record()
    clock[0] += 10
    budget.check_and_record()
    with pytest.raises(RateLimited) as exc:
        budget.check_and_record()
    assert 49.0 <= exc.value.retry_after <= 50.5
    clock[0] += 51
    budget.check_and_record()


def test_rate_budget_is_shared_through_the_file(tmp_path: Path) -> None:
    path = tmp_path / "rate.json"
    RateBudget(path, per_minute=1, clock=lambda: 1000.0).check_and_record()
    with pytest.raises(RateLimited):
        RateBudget(path, per_minute=1, clock=lambda: 1001.0).check_and_record()


def test_rate_budget_corrupt_file_fails_closed_for_one_window(tmp_path: Path) -> None:
    # Revisao do Codex (achado 14): arquivo corrompido nao pode zerar o orcamento; fecha uma janela
    # e regrava um arquivo valido (o teste de recuperacao esta em test_review_r1.py).
    path = tmp_path / "rate.json"
    path.write_text("lixo", encoding="utf-8")
    with pytest.raises(RateLimited):
        RateBudget(path, per_minute=1, clock=lambda: 1000.0).check_and_record()
    assert json.loads(path.read_text(encoding="utf-8")) == [1000.0]


# --- ExecutionGovernor -----------------------------------------------------------------------


def test_admit_holds_the_lock_and_releases_even_on_error(tmp_path: Path) -> None:
    gov = governor(tmp_path)
    with pytest.raises(ValueError, match="falha"), gov.admit():
        other = ProcessLock(tmp_path / "state" / "contabil.lock")
        assert other.acquire(0.05) is False
        raise ValueError("falha")
    with gov.admit():
        pass


def test_queue_of_one_second_waiter_enters_third_is_rejected(tmp_path: Path) -> None:
    gov = governor(tmp_path, wait=3.0)
    inside, may_leave = threading.Event(), threading.Event()
    order: list[str] = []

    def first() -> None:
        with gov.admit():
            order.append("primeiro")
            inside.set()
            may_leave.wait(5)

    def second() -> None:
        with gov.admit():
            order.append("segundo")

    t1 = threading.Thread(target=first)
    t1.start()
    assert inside.wait(5)
    t2 = threading.Thread(target=second)
    t2.start()
    time.sleep(0.2)
    with pytest.raises(Busy), gov.admit():
        pass
    may_leave.set()
    t1.join(5)
    t2.join(5)
    assert order == ["primeiro", "segundo"]


def test_busy_when_another_holder_keeps_the_lock_past_the_wait(tmp_path: Path) -> None:
    gov = governor(tmp_path, wait=0.2)
    holder = ProcessLock(tmp_path / "state" / "contabil.lock")
    (tmp_path / "state").mkdir(parents=True, exist_ok=True)
    assert holder.acquire(0.5)
    try:
        started = time.monotonic()
        with pytest.raises(Busy), gov.admit():
            pass
        assert 0.19 <= time.monotonic() - started < 1.5
    finally:
        holder.release()


def test_quarantine_blocks_everyone_and_frees_the_lock(tmp_path: Path) -> None:
    gov = governor(tmp_path, prober=lambda n: TerminationStatus.RUNNING)
    with gov.admit() as ticket:
        ticket.quarantine(321, "cancelamento nao confirmado")
    other = governor(tmp_path, prober=lambda n: TerminationStatus.RUNNING)  # "segundo processo"
    for g in (gov, other):
        with pytest.raises(Quarantined), g.admit():
            pytest.fail("nenhum processo pode executar em quarentena")
    # a trava nao ficou presa pela recusa
    assert ProcessLock(tmp_path / "state" / "contabil.lock").acquire(0.2) is True


def test_quarantine_is_lifted_only_by_confirmed_termination(tmp_path: Path) -> None:
    status = [TerminationStatus.RUNNING]
    seen: list[int] = []

    def prober(number: int) -> TerminationStatus:
        seen.append(number)
        return status[0]

    gov = governor(tmp_path, prober=prober)
    with gov.admit() as ticket:
        ticket.quarantine(77, "x")
    with pytest.raises(Quarantined), gov.admit():
        pass
    status[0] = TerminationStatus.TERMINATED
    with gov.admit():
        pass
    assert seen == [77, 77]
    with gov.admit():  # ja liberada: nao sonda de novo
        pass
    assert seen == [77, 77]


def test_reset_lifts_the_quarantine_without_a_probe(tmp_path: Path) -> None:
    gov = governor(tmp_path, prober=never_probe)
    with gov.admit() as ticket:
        ticket.quarantine(None, "numero desconhecido")
    with pytest.raises(Quarantined), gov.admit():
        pass
    assert gov.reset() is True
    with gov.admit():
        pass


def test_rate_limit_rejects_and_frees_the_lock(tmp_path: Path) -> None:
    gov = governor(tmp_path, per_minute=2, clock=lambda: 1000.0)
    for _ in range(2):
        with gov.admit():
            pass
    with pytest.raises(RateLimited), gov.admit():
        pass
    assert ProcessLock(tmp_path / "state" / "contabil.lock").acquire(0.2) is True


def test_dsn_names_become_safe_file_names(tmp_path: Path) -> None:
    gov = ExecutionGovernor(
        tmp_path / "state",
        "meu dsn/../x",
        per_minute=5,
        prober=lambda n: TerminationStatus.UNKNOWN,
    )
    with gov.admit():
        pass
    names = {p.name for p in (tmp_path / "state").iterdir()}
    assert all(
        "/" not in n and ".." not in n.replace(".lock", "").replace(".json", "") for n in names
    )
