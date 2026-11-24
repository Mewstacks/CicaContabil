from __future__ import annotations

import json
from pathlib import Path

from dominio_mcp.quarantine import Quarantine, TerminationStatus


def make(tmp_path: Path, clock: list[float] | None = None) -> Quarantine:
    now = clock if clock is not None else [1000.0]
    return Quarantine(tmp_path / "state" / "dsn.quarantine.json", clock=lambda: now[0])


def test_inactive_by_default(tmp_path: Path) -> None:
    q = make(tmp_path)
    assert q.is_active() is False
    assert q.state() is None
    assert q.try_release(lambda n: TerminationStatus.TERMINATED) is True


def test_enter_persists_state_atomically(tmp_path: Path) -> None:
    q = make(tmp_path)
    q.enter(4242, "cancelamento nao confirmado")
    assert q.is_active() is True
    state = q.state()
    assert state is not None
    assert state.connection_number == 4242
    assert state.reason == "cancelamento nao confirmado"
    assert state.pid > 0
    raw = json.loads((tmp_path / "state" / "dsn.quarantine.json").read_text(encoding="utf-8"))
    assert raw["connection_number"] == 4242
    assert not list((tmp_path / "state").glob("*.tmp"))


def test_second_enter_keeps_the_first_state(tmp_path: Path) -> None:
    q = make(tmp_path)
    q.enter(1, "primeira")
    q.enter(2, "segunda")
    state = q.state()
    assert state is not None
    assert (state.connection_number, state.reason) == (1, "primeira")


def test_state_survives_a_new_instance_like_a_process_restart(tmp_path: Path) -> None:
    make(tmp_path).enter(7, "queda")
    assert make(tmp_path).is_active() is True


def test_release_only_on_confirmed_termination(tmp_path: Path) -> None:
    q = make(tmp_path)
    q.enter(55, "x")
    assert q.try_release(lambda n: TerminationStatus.RUNNING) is False
    assert q.try_release(lambda n: TerminationStatus.UNKNOWN) is False
    assert q.is_active() is True
    seen: list[int] = []

    def probe(number: int) -> TerminationStatus:
        seen.append(number)
        return TerminationStatus.TERMINATED

    assert q.try_release(probe) is True
    assert seen == [55]
    assert q.is_active() is False


def test_probe_that_raises_counts_as_unknown(tmp_path: Path) -> None:
    q = make(tmp_path)
    q.enter(9, "x")

    def boom(number: int) -> TerminationStatus:
        raise RuntimeError("sem conexao")

    assert q.try_release(boom) is False
    assert q.is_active() is True


def test_unknown_connection_number_never_auto_releases(tmp_path: Path) -> None:
    q = make(tmp_path)
    q.enter(None, "numero desconhecido")
    called: list[int] = []

    def probe(number: int) -> TerminationStatus:
        called.append(number)
        return TerminationStatus.TERMINATED

    assert q.try_release(probe) is False
    assert called == []
    assert q.reset() is True
    assert q.is_active() is False


def test_time_alone_never_releases(tmp_path: Path) -> None:
    clock = [1000.0]
    q = make(tmp_path, clock)
    q.enter(3, "x")
    clock[0] += 10 * 24 * 3600
    assert q.is_active() is True
    assert q.try_release(lambda n: TerminationStatus.UNKNOWN) is False


def test_corrupt_state_file_fails_closed(tmp_path: Path) -> None:
    q = make(tmp_path)
    path = tmp_path / "state" / "dsn.quarantine.json"
    path.parent.mkdir(parents=True)
    path.write_text("{isto nao e json", encoding="utf-8")
    assert q.is_active() is True
    state = q.state()
    assert state is not None
    assert state.connection_number is None
    assert q.try_release(lambda n: TerminationStatus.TERMINATED) is False
    assert q.reset() is True
    assert q.is_active() is False


def test_reset_reports_whether_something_was_released(tmp_path: Path) -> None:
    q = make(tmp_path)
    assert q.reset() is False
    q.enter(1, "x")
    assert q.reset() is True
    assert q.reset() is False
