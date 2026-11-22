"""Quarentena compartilhada por DSN (D-322).

Quando o cancelamento de uma consulta nao e confirmado, nao se sabe se ela ainda roda no servidor.
Enquanto o termino for incerto, nenhum processo admite nova execucao: o estado fica num arquivo ao
lado da trava, sobrevive a queda do processo e so sai por:

- termino confirmado (a conexao descartada some de `sa_conn_info()`, lida por conexao nova);
- `dominio-mcp reset`, explicito.

Passar do tempo nunca libera. Arquivo ilegivel conta como quarentena (falha fechada).
"""

from __future__ import annotations

import json
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path


class TerminationStatus(StrEnum):
    TERMINATED = "terminou"
    RUNNING = "em_execucao"
    UNKNOWN = "desconhecido"


@dataclass(frozen=True, slots=True)
class QuarantineState:
    since: str
    connection_number: int | None
    reason: str
    pid: int


_UNREADABLE = QuarantineState(since="?", connection_number=None, reason="estado ilegivel", pid=0)

# Quarentena que nao conseguiu ser gravada em disco (disco cheio, permissao): vale neste processo,
# senao a falha de gravacao liberaria a proxima execucao com a anterior ainda rodando no servidor.
_HELD: dict[str, QuarantineState] = {}
_HELD_LOCK = threading.Lock()


class Quarantine:
    def __init__(self, path: Path, *, clock: Callable[[], float] = time.time) -> None:
        self._path = path
        self._clock = clock

    def _held(self) -> QuarantineState | None:
        with _HELD_LOCK:
            return _HELD.get(str(self._path))

    def state(self) -> QuarantineState | None:
        try:
            text = self._path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return self._held()
        except OSError:
            return _UNREADABLE
        try:
            data = json.loads(text)
            number = data["connection_number"]
            if number is not None and (isinstance(number, bool) or not isinstance(number, int)):
                return _UNREADABLE
            return QuarantineState(
                since=str(data["since"]),
                connection_number=number,
                reason=str(data["reason"]),
                pid=int(data["pid"]),
            )
        except (ValueError, KeyError, TypeError):
            return _UNREADABLE

    def is_active(self) -> bool:
        return self.state() is not None

    def held_state(self) -> QuarantineState | None:
        """A quarentena que so existe em memoria (a gravacao em disco falhou), se houver."""
        return self._held()

    def enter(self, connection_number: int | None, reason: str) -> bool:
        """Entra em quarentena. `True` se ficou gravada em disco (vale para todo processo);
        `False` se so da para segurar em memoria, e o governador precisa manter a trava."""
        if self.state() is not None:
            return True
        payload = {
            "since": datetime.fromtimestamp(self._clock(), UTC).isoformat(timespec="seconds"),
            "connection_number": connection_number,
            "reason": reason[:200],
            "pid": os.getpid(),
        }
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._path.with_name(f"{self._path.name}.{os.getpid()}.tmp")
            tmp.write_text(json.dumps(payload), encoding="utf-8")
            os.replace(tmp, self._path)
        except OSError:
            with _HELD_LOCK:
                _HELD[str(self._path)] = QuarantineState(
                    since=str(payload["since"]),
                    connection_number=connection_number,
                    reason=str(payload["reason"]),
                    pid=os.getpid(),
                )
            return False
        return True

    def try_release(self, probe: Callable[[int], TerminationStatus]) -> bool:
        """Libera so com termino confirmado; sem numero de conexao so `reset` libera."""
        state = self.state()
        if state is None:
            return True
        if state.connection_number is None:
            return False
        try:
            status = probe(state.connection_number)
        except Exception:  # sonda que falha = nao sei = continua em quarentena
            status = TerminationStatus.UNKNOWN
        if status is TerminationStatus.TERMINATED:
            self.reset()
            return True
        return False

    def reset(self) -> bool:
        with _HELD_LOCK:
            held = _HELD.pop(str(self._path), None) is not None
        try:
            self._path.unlink()
        except FileNotFoundError:
            return held
        return True
