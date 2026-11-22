"""Controle de carga no servidor do Dominio (D-327): trava, fila de 1, frequencia e quarentena.

`ExecutionGovernor.admit()` e o unico caminho para executar no banco:

1. fila de 1 por processo: uma execucao em andamento, no maximo uma esperando, a terceira recebe
   `Busy` na hora;
2. trava entre processos por DSN (bloqueio do sistema operacional no arquivo de estado: dois
   clientes stdio, ou um stdio e o tunel, nunca executam juntos; a trava some se o processo cai);
3. quarentena compartilhada: se o termino de uma execucao anterior e incerto, ninguem executa
   (`Quarantined`) ate o termino ser confirmado pelo `prober` ou o dono rodar `reset`;
4. orcamento de frequencia compartilhado por arquivo (`RateLimited`).

O orcamento numerico de custo por consulta e outro mecanismo (`admission.py`, via `PLAN`).
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from pathlib import Path

from dominio_mcp.quarantine import Quarantine, QuarantineState, TerminationStatus

_POLL_SECONDS = 0.02
_WINDOW_SECONDS = 60.0

if sys.platform == "win32":
    import msvcrt

    def _try_lock(fd: int) -> bool:
        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        except OSError:
            return False
        return True

    def _unlock(fd: int) -> None:
        os.lseek(fd, 0, os.SEEK_SET)
        msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)

else:
    import fcntl

    def _try_lock(fd: int) -> bool:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            return False
        return True

    def _unlock(fd: int) -> None:
        fcntl.flock(fd, fcntl.LOCK_UN)


class Busy(Exception):
    """Ha outra consulta em andamento (neste ou em outro processo)."""


class Quarantined(Exception):
    def __init__(self, state: QuarantineState) -> None:
        super().__init__(
            f"servico em quarentena desde {state.since}: {state.reason}. Nenhuma consulta e "
            "feita ate o termino da anterior ser confirmado; depois de conferir no servidor, "
            "rode `dominio-mcp reset`"
        )
        self.state = state


class RateLimited(Exception):
    def __init__(self, retry_after: float, per_minute: int) -> None:
        super().__init__(
            f"limite de {per_minute} consultas por minuto no banco; tente em {retry_after:.0f} s"
        )
        self.retry_after = retry_after


class ProcessLock:
    """Trava exclusiva do sistema operacional num arquivo; liberada se o processo morrer."""

    def __init__(self, path: Path) -> None:
        self._path = path
        self._fd: int | None = None

    def acquire(self, timeout: float) -> bool:
        if self._fd is not None:
            raise RuntimeError("trava ja adquirida por este objeto")
        self._path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_BINARY", 0)
        fd = os.open(self._path, flags)
        deadline = time.monotonic() + max(timeout, 0.0)
        while True:
            if _try_lock(fd):
                self._fd = fd
                return True
            if time.monotonic() >= deadline:
                os.close(fd)
                return False
            time.sleep(_POLL_SECONDS)

    def release(self) -> None:
        fd, self._fd = self._fd, None
        if fd is None:
            return
        try:
            _unlock(fd)
        except OSError:
            pass
        finally:
            os.close(fd)


class RateBudget:
    """Janela deslizante de 60 s guardada em arquivo; chamar com a trava de processo em maos."""

    def __init__(
        self, path: Path, per_minute: int, *, clock: Callable[[], float] = time.time
    ) -> None:
        self._path = path
        self._per_minute = per_minute
        self._clock = clock

    def _load(self, now: float) -> list[float] | None:
        """Instantes ainda na janela; `None` se o arquivo esta ilegivel (falha fechada)."""
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except (OSError, ValueError):
            return None
        if not isinstance(data, list) or any(
            isinstance(t, bool) or not isinstance(t, int | float) for t in data
        ):
            return None
        # Instante no futuro (relogio que voltou) conta como agora: continua ocupando a janela.
        return sorted(min(float(t), now) for t in data if now - _WINDOW_SECONDS < t)

    def _write(self, stamps: list[float]) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._path.with_name(f"{self._path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(stamps), encoding="utf-8")
        os.replace(tmp, self._path)

    def check_and_record(self) -> None:
        now = self._clock()
        stamps = self._load(now)
        if stamps is None:
            # Arquivo corrompido: nao se sabe quantas execucoes houve. Fecha uma janela inteira e
            # regrava um arquivo valido, para a liberacao acontecer sozinha em 60 s.
            self._write([now] * self._per_minute)
            raise RateLimited(_WINDOW_SECONDS, self._per_minute)
        if len(stamps) >= self._per_minute:
            raise RateLimited(max(stamps[0] + _WINDOW_SECONDS - now, 0.0), self._per_minute)
        stamps.append(now)
        self._write(stamps)


class Ticket:
    """Entregue a quem foi admitido: marca execucao de termino incerto."""

    def __init__(self, quarantine: Quarantine) -> None:
        self._quarantine = quarantine
        self.keeps_lock = False

    def quarantine(self, connection_number: int | None, reason: str) -> None:
        if not self._quarantine.enter(connection_number, reason):
            # Nao deu para gravar a quarentena: so a trava de processo segura os outros processos.
            self.keeps_lock = True


# Trava de processo que ficou presa de proposito (quarentena nao gravada): sai quando o termino e
# confirmado, no `reset` do mesmo processo ou quando o processo morre (o sistema libera a trava).
_RETAINED: dict[str, ProcessLock] = {}


def release_retained_locks() -> None:
    for lock in list(_RETAINED.values()):
        lock.release()
    _RETAINED.clear()


def state_slug(dsn: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]", "_", dsn)


def quarantine_for(
    state_dir: Path, dsn: str, *, clock: Callable[[], float] = time.time
) -> Quarantine:
    """A quarentena compartilhada do DSN (a mesma que o governador usa; `reset` da CLI)."""
    return Quarantine(state_dir / f"{state_slug(dsn)}.quarantine.json", clock=clock)


class ExecutionGovernor:
    def __init__(
        self,
        state_dir: Path,
        dsn: str,
        *,
        per_minute: int,
        prober: Callable[[int], TerminationStatus],
        wait_seconds: float = 5.0,
        max_waiting: int = 1,
        clock: Callable[[], float] = time.time,
    ) -> None:
        slug = state_slug(dsn)
        self._lock_path = state_dir / f"{slug}.lock"
        self.quarantine = quarantine_for(state_dir, dsn, clock=clock)
        self._rate = RateBudget(state_dir / f"{slug}.rate.json", per_minute, clock=clock)
        self._prober = prober
        self._wait = wait_seconds
        self._max_waiting = max_waiting
        self._mutex = threading.Lock()
        self._waiting = 0

    def reset(self) -> bool:
        freed = self.quarantine.reset()
        self._free_retained()
        return freed

    def _free_retained(self) -> None:
        lock = _RETAINED.pop(str(self._lock_path), None)
        if lock is not None:
            lock.release()

    def _acquire(self) -> ProcessLock:
        lock = ProcessLock(self._lock_path)
        if lock.acquire(0.0):
            return lock
        with self._mutex:
            if self._waiting >= self._max_waiting:
                raise Busy("ha uma consulta em andamento e outra ja esta esperando")
            self._waiting += 1
        try:
            got = lock.acquire(self._wait)
        finally:
            with self._mutex:
                self._waiting -= 1
        if not got:
            raise Busy("outra consulta esta em andamento (neste ou em outro processo)")
        return lock

    @contextmanager
    def admit(self) -> Iterator[Ticket]:
        held = self.quarantine.held_state()
        if held is not None:
            # quarentena so em memoria: este processo segura a trava; sai com o termino confirmado
            if not self.quarantine.try_release(self._prober):
                raise Quarantined(held)
            self._free_retained()
        lock = self._acquire()
        ticket = Ticket(self.quarantine)
        try:
            if self.quarantine.is_active() and not self.quarantine.try_release(self._prober):
                state = self.quarantine.state()
                assert state is not None
                raise Quarantined(state)
            self._rate.check_and_record()
            yield ticket
        finally:
            if ticket.keeps_lock:
                _RETAINED[str(self._lock_path)] = lock
            else:
                lock.release()
