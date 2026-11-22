"""ODBC falso para testes: imita so o que o pacote usa do pyodbc.

Cada `execute` de consulta consome um comportamento do roteiro do servidor (`FakeServer.script`):

- `Rows(colunas, linhas)`: devolve linhas;
- `Fail(sqlstate, mensagem)`: levanta erro do driver;
- `Block(ignore_cancel=False)`: trava ate `cancel()` (e levanta -299) ou, se `ignore_cancel`,
  ate o teste chamar `server.release()`.

Comandos de sessao (`SET TEMPORARY OPTION`, `CONNECTION_PROPERTY('Number')`) e a consulta de
`sa_conn_info()` sao tratados a parte e nao consomem o roteiro.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field
from typing import Any

SQL_CHAR = 1
SQL_WCHAR = -8
SAFETY_SECONDS = 10.0


class Error(Exception):
    """Equivale a pyodbc.Error: args = (sqlstate, mensagem)."""


class ProgrammingError(Error):
    pass


class OperationalError(Error):
    pass


@dataclass
class Rows:
    columns: list[str]
    rows: list[tuple[Any, ...]]


@dataclass
class Fail:
    sqlstate: str
    message: str


@dataclass
class Block:
    ignore_cancel: bool = False


CANCELLED = Fail(
    "HY001", "[HY001] [SAP][ODBC Driver][SQL Anywhere]Statement interrupted by user (-299)"
)


@dataclass
class FakeServer:
    script: list[Any] = field(default_factory=list)
    live_numbers: set[int] = field(default_factory=set)
    next_number: int = 100
    connect_failures: int = 0
    cancel_mode: str = "ok"  # ok | blocks | fails
    sa_conn_info_error: bool = False
    log: list[tuple[str, tuple[Any, ...]]] = field(default_factory=list)
    cursors: list[FakeCursor] = field(default_factory=list)
    connections: list[FakeConnection] = field(default_factory=list)
    _release: threading.Event = field(default_factory=threading.Event)

    def release(self) -> None:
        self._release.set()

    def new_number(self) -> int:
        number = self.next_number
        self.next_number += 1
        self.live_numbers.add(number)
        return number


class FakeCursor:
    def __init__(self, conn: FakeConnection) -> None:
        self.conn = conn
        self.server = conn.server
        self.closed = False
        self.description: list[tuple[Any, ...]] | None = None
        self._rows: list[tuple[Any, ...]] = []
        self._pos = 0
        self._cancel = threading.Event()
        self.fetch_sizes: list[int] = []
        self.executed: list[tuple[str, tuple[Any, ...]]] = []
        self.server.cursors.append(self)

    def _check_open(self) -> None:
        if self.closed:
            raise ProgrammingError("HY000", "Attempt to use a closed cursor.")

    def _set_result(self, columns: list[str], rows: list[tuple[Any, ...]]) -> None:
        self.description = [(c, str, None, None, None, None, True) for c in columns]
        self._rows = list(rows)
        self._pos = 0

    def execute(self, sql: str, *params: Any) -> FakeCursor:
        self._check_open()
        self.server.log.append((sql, params))
        self.executed.append((sql, params))
        text = sql.strip().lower()
        if text.startswith("set temporary option"):
            self.description = None
            return self
        if "connection_property('number')" in text:
            self._set_result(["number"], [(self.conn.number,)])
            return self
        if "sa_conn_info" in text:
            if self.server.sa_conn_info_error:
                raise Error("42000", "[42000] sa_conn_info negado (-121)")
            target = params[0] if params else None
            alive = 1 if target in self.server.live_numbers else 0
            self._set_result(["n"], [(alive,)])
            return self
        if not self.server.script:
            raise AssertionError(f"roteiro vazio para: {sql[:80]}")
        step = self.server.script.pop(0)
        if isinstance(step, Fail):
            raise Error(step.sqlstate, step.message)
        if isinstance(step, Block):
            if step.ignore_cancel:
                self.server._release.wait(SAFETY_SECONDS)
                raise Error(*_pair(CANCELLED))
            if self._cancel.wait(SAFETY_SECONDS):
                raise Error(*_pair(CANCELLED))
            raise AssertionError("Block sem cancel() no prazo de seguranca")
        if isinstance(step, Rows):
            self._set_result(step.columns, step.rows)
            return self
        raise AssertionError(f"passo desconhecido: {step!r}")

    def fetchmany(self, size: int) -> list[tuple[Any, ...]]:
        self._check_open()
        self.fetch_sizes.append(size)
        chunk = self._rows[self._pos : self._pos + size]
        self._pos += len(chunk)
        return chunk

    def fetchone(self) -> tuple[Any, ...] | None:
        self._check_open()
        if self._pos >= len(self._rows):
            return None
        row = self._rows[self._pos]
        self._pos += 1
        return row

    def fetchall(self) -> list[tuple[Any, ...]]:
        self._check_open()
        chunk = self._rows[self._pos :]
        self._pos = len(self._rows)
        return chunk

    def cancel(self) -> None:
        if self.closed:
            raise ProgrammingError("HY000", "Attempt to use a closed cursor.")
        mode = self.server.cancel_mode
        if mode == "fails":
            raise Error("HY000", "cancel falhou")
        if mode == "blocks":
            self.server._release.wait(SAFETY_SECONDS)
            return
        self._cancel.set()

    def close(self) -> None:
        self.closed = True


class FakeConnection:
    def __init__(self, server: FakeServer, connection_string: str, kwargs: dict[str, Any]) -> None:
        self.server = server
        self.connection_string = connection_string
        self.kwargs = kwargs
        self.number = server.new_number()
        self.closed = False
        self.decodings: list[tuple[int, dict[str, Any]]] = []
        self.encodings: list[dict[str, Any]] = []
        server.connections.append(self)

    def cursor(self) -> FakeCursor:
        if self.closed:
            raise ProgrammingError("HY000", "Attempt to use a closed connection.")
        return FakeCursor(self)

    def setdecoding(self, sqltype: int, **kwargs: Any) -> None:
        self.decodings.append((sqltype, kwargs))

    def setencoding(self, **kwargs: Any) -> None:
        self.encodings.append(kwargs)

    def close(self) -> None:
        self.closed = True
        self.server.live_numbers.discard(self.number)


def _pair(fail: Fail) -> tuple[str, str]:
    return (fail.sqlstate, fail.message)


class FakeDriver:
    """Imita o modulo pyodbc (so os atributos usados)."""

    SQL_CHAR = SQL_CHAR
    SQL_WCHAR = SQL_WCHAR
    Error = Error
    ProgrammingError = ProgrammingError
    OperationalError = OperationalError

    def __init__(self, server: FakeServer | None = None) -> None:
        self.server = server or FakeServer()
        self.pooling: bool | None = None

    def connect(self, connection_string: str, **kwargs: Any) -> FakeConnection:
        if self.server.connect_failures > 0:
            self.server.connect_failures -= 1
            raise OperationalError("08001", "[08001] nao conectou (-100)")
        return FakeConnection(self.server, connection_string, kwargs)
