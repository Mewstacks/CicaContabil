"""Vigia de consulta: limite por `cursor.cancel()`, preso ao cursor da propria execucao.

O ODBC do Dominio recusa o atributo de timeout (`HYC00`), mas `cancel()` chamado de outra thread
interrompe a consulta (`-299`) e a conexao segue utilizavel (evidencia 01). O vigia garante que:

- cada execucao tem o seu cursor e o seu vigia; um cancelamento atrasado de A nunca alcanca B
  (o cursor so e fechado, e o cancelamento so e feito, sob o mesmo trinco: `cancel()` em cursor
  fechado nem chega ao driver);
- a excecao de `cancel()` e engolida e entregue a `on_cancel_error` (auditoria);
- `cancel()` que trava nao prende quem chamou: se a execucao nao terminar em `confirm`
  segundos depois do cancelamento, `CancelUnconfirmed` e levantada e a execucao e dada como
  incerta (o chamador descarta a conexao e entra em quarentena);
- 30 s e um alvo, nao uma garantia absoluta.

A consulta roda numa thread daemon; quem chamou espera por `done` com prazo.
"""

from __future__ import annotations

import threading
from collections.abc import Callable
from typing import Any, cast


class QueryTimeout(Exception):
    """A consulta passou do limite, foi cancelada e o cancelamento foi confirmado."""


class CancelUnconfirmed(Exception):
    """O cancelamento nao foi confirmado a tempo: nao se sabe se a consulta ainda roda.

    `done` sinaliza quando a thread da consulta terminar de fato; quem descartou a conexao pode
    esperar por ele para fecha-la sem tocar num driver ainda ocupado.
    """

    def __init__(self, done: threading.Event) -> None:
        super().__init__("cancelamento nao confirmado dentro do prazo")
        self.done = done


class CursorGuard:
    def __init__(
        self, cursor: Any, on_cancel_error: Callable[[BaseException], None] | None = None
    ) -> None:
        self._cursor = cursor
        self._on_error = on_cancel_error
        self._lock = threading.Lock()
        self._finished = False

    def _report(self, exc: BaseException) -> None:
        if self._on_error is None:
            return
        try:
            self._on_error(exc)
        except Exception:  # auditoria que falha nao pode derrubar o vigia
            return

    def cancel(self) -> None:
        with self._lock:
            if self._finished:
                return
            try:
                self._cursor.cancel()
            except Exception as exc:  # a excecao do cancel() e engolida e auditada
                self._report(exc)

    def finish(self) -> None:
        with self._lock:
            if self._finished:
                return
            self._finished = True
            try:
                self._cursor.close()
            except Exception:  # fechar cursor quebrado nao pode mascarar o resultado
                return


def run_guarded[T](
    guard: CursorGuard,
    work: Callable[[], T],
    *,
    timeout: float,
    confirm: float,
    is_cancel_error: Callable[[BaseException], bool] | None = None,
) -> T:
    outcome: dict[str, Any] = {}
    done = threading.Event()

    def worker() -> None:
        try:
            outcome["value"] = work()
        except BaseException as exc:
            outcome["error"] = exc
        finally:
            guard.finish()
            done.set()

    threading.Thread(target=worker, name="dominio-mcp-consulta", daemon=True).start()
    if done.wait(timeout):
        return cast(T, _result(outcome))

    threading.Thread(target=guard.cancel, name="dominio-mcp-cancelamento", daemon=True).start()
    if not done.wait(confirm):
        raise CancelUnconfirmed(done)
    error = outcome.get("error")
    if error is not None and (is_cancel_error is None or is_cancel_error(error)):
        raise QueryTimeout("consulta cancelada por passar do limite de tempo")
    return cast(T, _result(outcome))


def _result(outcome: dict[str, Any]) -> Any:
    if "error" in outcome:
        raise outcome["error"]
    return outcome["value"]
