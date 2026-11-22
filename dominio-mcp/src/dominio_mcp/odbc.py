"""Execucao no ODBC do Dominio (SAP SQL Anywhere 17), somente leitura.

Receita medida no banco real (evidencia 01 e 02):

- conexao `DSN=<nome>` sem `CharSet`, pooling desligado, `autocommit`, `readonly` (dica: a
  eficacia do modo somente leitura do ODBC nao foi verificada, nao e defesa);
- `SQL_CHAR` entregue como UTF-16 (`ctype=SQL_WCHAR`): o acento chega certo por ponto de codigo;
- `SET TEMPORARY OPTION isolation_level = 0` (leitura sem confirmacao; todo resultado leva
  `consistencia` e `lido_em` na moldagem);
- `SQL_ATTR_QUERY_TIMEOUT` e recusado (HYC00): o limite vem do vigia (`watchdog.py`).

Erros do driver viram `DbError` com so tipo, SQLSTATE e codigo nativo: o texto do driver pode
repetir fragmento de SQL ou valor de linha e nunca e propagado (nem como causa encadeada).
"""

from __future__ import annotations

import hashlib
import importlib
import re
import threading
import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Protocol

from dominio_mcp.budget import ExecutionGovernor, Ticket
from dominio_mcp.config import Settings
from dominio_mcp.quarantine import TerminationStatus
from dominio_mcp.values import Cell, normalize_row, normalize_value
from dominio_mcp.watchdog import CancelUnconfirmed, CursorGuard, QueryTimeout, run_guarded

FETCH_BATCH = 500
_NATIVE_RE = re.compile(r"\((-?\d+)\)(?:\s*\(SQL\w+\))?\s*$")
_SQLSTATE_RE = re.compile(r"[0-9A-Z]{5}")


class OdbcUnavailable(Exception):
    """O driver Python (pyodbc) ou o driver ODBC do SQL Anywhere nao esta instalado."""


class DbErrorKind(StrEnum):
    CANCELLED = "cancelada"
    LOST = "conexao_perdida"
    DENIED = "sem_permissao"
    NOT_FOUND = "nao_encontrado"
    SYNTAX = "sintaxe"
    OTHER = "outro"


class DbError(Exception):
    def __init__(self, kind: DbErrorKind, sqlstate: str, native_code: int | None) -> None:
        super().__init__(f"erro do banco: {kind.value} (sqlstate {sqlstate}, codigo {native_code})")
        self.kind = kind
        self.sqlstate = sqlstate
        self.native_code = native_code


@dataclass(frozen=True, slots=True)
class RawResult:
    columns: tuple[str, ...]
    rows: list[list[Cell]]
    truncated: bool
    elapsed_ms: float
    read_at: datetime


def load_driver() -> Any:
    module: Any = None
    try:
        module = importlib.import_module("pyodbc")
    except ImportError:
        module = None
    if module is None:
        raise OdbcUnavailable(
            "pyodbc nao esta instalado (rode `uv sync` em dominio-mcp) ou o driver ODBC do "
            "SQL Anywhere 17 nao esta presente neste computador"
        )
    return module


def _classify(sqlstate: str, native: int | None) -> DbErrorKind:
    if native == -299 or sqlstate == "HY008":
        return DbErrorKind.CANCELLED
    if native in (-85, -101, -308) or sqlstate.startswith("08"):
        return DbErrorKind.LOST
    if native == -121:
        return DbErrorKind.DENIED
    if native in (-141, -143) or sqlstate in ("42S02", "42S22"):
        return DbErrorKind.NOT_FOUND
    if native == -131 or sqlstate == "37000":
        return DbErrorKind.SYNTAX
    return DbErrorKind.OTHER


def map_error(exc: BaseException) -> DbError:
    args = exc.args
    first = args[0] if args else None
    sqlstate = first if isinstance(first, str) and _SQLSTATE_RE.fullmatch(first) else "?"
    message = args[1] if len(args) > 1 and isinstance(args[1], str) else ""
    found = _NATIVE_RE.search(message)
    native = int(found.group(1)) if found else None
    return DbError(_classify(sqlstate, native), sqlstate, native)


@dataclass(slots=True)
class OdbcConnection:
    raw: Any
    number: int | None

    def close(self) -> None:
        try:
            self.raw.close()
        except Exception:  # fechar conexao quebrada nao pode mascarar o erro original
            return


def open_connection(driver: Any, dsn: str, *, login_timeout: int = 15) -> OdbcConnection:
    """Abre e prepara uma conexao. `dsn` e so o nome do DSN de sistema (validado na config)."""
    driver.pooling = False
    mapped: DbError | None = None
    raw: Any = None
    number: int | None = None
    try:
        raw = driver.connect(f"DSN={dsn}", autocommit=True, readonly=True, timeout=login_timeout)
        raw.setdecoding(driver.SQL_CHAR, encoding="utf-16le", ctype=driver.SQL_WCHAR)
        raw.setdecoding(driver.SQL_WCHAR, encoding="utf-16le")
        cursor = raw.cursor()
        try:
            cursor.execute("SET TEMPORARY OPTION isolation_level = 0")
            cursor.execute("SELECT CONNECTION_PROPERTY('Number')")
            row = cursor.fetchone()
        finally:
            cursor.close()
        if row and row[0] is not None:
            try:
                number = int(row[0])
            except (TypeError, ValueError):
                number = None
    except driver.Error as exc:
        mapped = map_error(exc)
        if raw is not None:
            OdbcConnection(raw, None).close()
    if mapped is not None:
        raise mapped
    return OdbcConnection(raw, number)


def run_statement(
    driver: Any,
    cursor: Any,
    sql: str,
    params: tuple[Any, ...] = (),
    *,
    max_rows: int,
    batch: int = FETCH_BATCH,
) -> RawResult:
    """Executa um SELECT no cursor dado (um cursor por execucao; quem cria fecha).

    Le no maximo `max_rows + 1` linhas: a ultima e a linha-sonda que diz se houve truncamento.
    """
    started = time.perf_counter()
    mapped: DbError | None = None
    columns: tuple[str, ...] = ()
    rows: list[list[Cell]] = []
    truncated = False
    try:
        cursor.execute(sql, *params)
        description = cursor.description
        if description:
            columns = tuple(str(normalize_value(d[0])) for d in description)
            want = max_rows + 1
            fetched: list[Any] = []
            while len(fetched) < want:
                chunk = cursor.fetchmany(min(batch, want - len(fetched)))
                if not chunk:
                    break
                fetched.extend(chunk)
            truncated = len(fetched) > max_rows
            rows = [normalize_row(r) for r in fetched[:max_rows]]
    except driver.Error as exc:
        mapped = map_error(exc)
    if mapped is not None:
        raise mapped
    return RawResult(
        columns=columns,
        rows=rows,
        truncated=truncated,
        elapsed_ms=(time.perf_counter() - started) * 1000,
        read_at=datetime.now(UTC),
    )


class Auditor(Protocol):
    """Destino dos eventos de execucao (`audit.py`); nunca recebe SQL, parametro nem linha."""

    def event(self, name: str, **fields: Any) -> None: ...


class ExecutionUncertain(Exception):
    """O cancelamento nao foi confirmado: o servico entrou em quarentena (D-322)."""


def _sql_hash(sql: str) -> str:
    return hashlib.sha256(sql.encode("utf-8")).hexdigest()[:12]


def _is_cancelled(exc: BaseException) -> bool:
    return isinstance(exc, DbError) and exc.kind is DbErrorKind.CANCELLED


def probe_termination(driver: Any, dsn: str, number: int) -> TerminationStatus:
    """A conexao `number` ainda aparece em `sa_conn_info()`? (conexao nova; o Externo enxerga)."""
    try:
        conn = open_connection(driver, dsn, login_timeout=5)
    except DbError:
        return TerminationStatus.UNKNOWN
    row: Any = None
    failed = False
    try:
        cursor = conn.raw.cursor()
        try:
            cursor.execute("SELECT COUNT(*) FROM sa_conn_info() WHERE Number = ?", number)
            row = cursor.fetchone()
        finally:
            cursor.close()
    except driver.Error:
        failed = True
    finally:
        conn.close()
    if failed or not row or row[0] is None:
        return TerminationStatus.UNKNOWN
    return TerminationStatus.TERMINATED if int(row[0]) == 0 else TerminationStatus.RUNNING


class Session:
    """Uma conexao reutilizavel e execucao um-cursor-por-consulta sob governo de carga."""

    def __init__(
        self,
        settings: Settings,
        governor: ExecutionGovernor,
        *,
        driver: Any,
        auditor: Auditor | None = None,
        confirm_seconds: float | None = None,
    ) -> None:
        self._settings = settings
        self.governor = governor
        self._driver = driver
        self._auditor = auditor
        self._confirm = (
            float(settings.limits.cancel_confirm_seconds)
            if confirm_seconds is None
            else confirm_seconds
        )
        self._conn: OdbcConnection | None = None

    @property
    def connected(self) -> bool:
        return self._conn is not None

    def _audit(self, name: str, **fields: Any) -> None:
        if self._auditor is None:
            return
        try:
            self._auditor.event(name, **fields)
        except Exception:  # auditoria que falha nao pode derrubar a consulta
            return

    def _on_cancel_error(self, exc: BaseException) -> None:
        sqlstate = map_error(exc).sqlstate if isinstance(exc, self._driver.Error) else "?"
        self._audit("cancelamento_falhou", tipo=type(exc).__name__, sqlstate=sqlstate)

    def _connection(self) -> OdbcConnection:
        if self._conn is None:
            self._conn = open_connection(self._driver, self._settings.dsn)
        return self._conn

    def _discard(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            conn.close()

    def close(self) -> None:
        self._discard()

    def execute(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
        *,
        max_rows: int,
        timeout: float | None = None,
    ) -> RawResult:
        with self.slot() as slot:
            return slot.execute(sql, params, max_rows=max_rows, timeout=timeout)

    @contextmanager
    def slot(self) -> Iterator[Slot]:
        """Uma admissao do governador: varias consultas sob a mesma trava e a mesma conta."""
        with self.governor.admit() as ticket:
            yield Slot(self, ticket)

    def default_timeout(self) -> float:
        return float(self._settings.limits.query_timeout_seconds)

    def execute_batch(
        self, statements: Sequence[str], *, timeout_each: float = 10.0
    ) -> list[RawResult | DbError | QueryTimeout]:
        """Varias consultas numa unica admissao (uma conta no orcamento de frequencia).

        Erro de uma consulta (negado, nao encontrado, passou do limite) vira resultado e o lote
        segue; conexao perdida ou termino incerto interrompem o lote.
        """
        outcomes: list[RawResult | DbError | QueryTimeout] = []
        with self.governor.admit() as ticket:
            for sql in statements:
                try:
                    outcomes.append(self._run_one(ticket, sql, (), 1, timeout_each))
                except QueryTimeout as timeout:
                    outcomes.append(timeout)
                except DbError as err:
                    if err.kind is DbErrorKind.LOST:
                        raise
                    outcomes.append(err)
        return outcomes

    def _run_one(
        self, ticket: Ticket, sql: str, params: tuple[Any, ...], max_rows: int, limit: float
    ) -> RawResult:
        conn = self._connection()
        mapped: DbError | None = None
        cursor: Any = None
        try:
            cursor = conn.raw.cursor()
        except self._driver.Error as exc:
            mapped = map_error(exc)
        if mapped is not None:
            self._discard()
            raise mapped
        guard = CursorGuard(cursor, self._on_cancel_error)

        def work() -> RawResult:
            return run_statement(self._driver, cursor, sql, params, max_rows=max_rows)

        try:
            return run_guarded(
                guard,
                work,
                timeout=limit,
                confirm=self._confirm,
                is_cancel_error=_is_cancelled,
            )
        except QueryTimeout:
            self._audit("consulta_cancelada", limite_s=limit, sql_hash=_sql_hash(sql))
            raise
        except CancelUnconfirmed as unconfirmed:
            self._conn = None  # descartada sem fechar: o driver ainda pode estar ocupado
            ticket.quarantine(conn.number, "cancelamento nao confirmado")
            self._audit(
                "execucao_incerta", conexao=conn.number, limite_s=limit, sql_hash=_sql_hash(sql)
            )
            reaper = threading.Thread(
                target=_close_when_done,
                args=(conn, unconfirmed.done),
                name="dominio-mcp-limpeza",
                daemon=True,
            )
            reaper.start()
            raise ExecutionUncertain(
                "a consulta nao foi encerrada com confirmacao; o servico ficou em "
                "quarentena ate o termino ser confirmado ou `dominio-mcp reset`"
            ) from None
        except DbError as err:
            if err.kind is DbErrorKind.LOST:
                self._discard()
            raise


class Slot:
    """Executa dentro de uma admissao ja obtida (`Session.slot()`); mesma conta de frequencia."""

    def __init__(self, session: Session, ticket: Ticket) -> None:
        self._session = session
        self._ticket = ticket

    def execute(
        self,
        sql: str,
        params: tuple[Any, ...] = (),
        *,
        max_rows: int,
        timeout: float | None = None,
    ) -> RawResult:
        limit = self._session.default_timeout() if timeout is None else float(timeout)
        return self._session._run_one(self._ticket, sql, params, max_rows, limit)


def _close_when_done(conn: OdbcConnection, done: threading.Event) -> None:
    done.wait()
    conn.close()


def build_session(
    settings: Settings,
    *,
    driver: Any | None = None,
    auditor: Auditor | None = None,
    clock: Callable[[], float] = time.time,
    confirm_seconds: float | None = None,
    lock_wait_seconds: float = 5.0,
) -> Session:
    drv = driver if driver is not None else load_driver()
    governor = ExecutionGovernor(
        settings.home / "state",
        settings.dsn,
        per_minute=settings.limits.executions_per_minute,
        prober=lambda number: probe_termination(drv, settings.dsn, number),
        wait_seconds=lock_wait_seconds,
        clock=clock,
    )
    return Session(settings, governor, driver=drv, auditor=auditor, confirm_seconds=confirm_seconds)
