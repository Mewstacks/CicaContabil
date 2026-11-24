"""Sonda de legibilidade: quais objetos do catalogo o usuario do DSN consegue ler (T2.5).

`SELECT * FROM <objeto> WHERE 1=0` nao le linha nenhuma, mas o servidor confere a permissao ao
preparar a consulta (medido: 4.964 objetos em 11,6 s, 18 negados). Antes de confiar, o **controle**
(`SYS.SYSUSERPERM`, sabidamente negado ao Externo) precisa ser negado: se passar, a sonda nao
distingue objeto negado e o resultado e descartado.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

from dominio_mcp.catalog import Catalog
from dominio_mcp.literals import qualified
from dominio_mcp.odbc import DbError, DbErrorKind, RawResult
from dominio_mcp.watchdog import QueryTimeout

CONTROL_SQL = "SELECT * FROM SYS.SYSUSERPERM WHERE 1=0"
_REASONS = {
    DbErrorKind.DENIED: "sem_permissao",
    DbErrorKind.NOT_FOUND: "nao_encontrado",
}


class ReadableProbeError(Exception):
    pass


class BatchRunner(Protocol):
    def __call__(
        self, statements: Sequence[str], *, timeout_each: float = 10.0
    ) -> list[RawResult | DbError | QueryTimeout]: ...


@dataclass(frozen=True, slots=True)
class ReadableReport:
    readable: frozenset[str]
    unreadable: dict[str, str]
    control_denied: bool


def probe_readable(
    run_batch: BatchRunner, catalog: Catalog, *, timeout_each: float = 10.0
) -> ReadableReport:
    tables = sorted(catalog.tables.values(), key=lambda t: t.key)
    # identificadores do catalogo passam por quote_ident (recusa aspas e controle), sem dado externo
    statements = [CONTROL_SQL] + [
        f"SELECT * FROM {qualified(catalog.owner, t.name)} WHERE 1=0"  # noqa: S608
        for t in tables
    ]
    outcomes = run_batch(statements, timeout_each=timeout_each)
    if len(outcomes) != len(statements):
        raise ReadableProbeError("resposta da sonda com tamanho diferente do pedido")
    control = outcomes[0]
    if not (isinstance(control, DbError) and control.kind is DbErrorKind.DENIED):
        raise ReadableProbeError(
            "o controle de objeto negado nao foi negado: a sonda nao distingue permissao"
        )
    readable: set[str] = set()
    unreadable: dict[str, str] = {}
    for table, outcome in zip(tables, outcomes[1:], strict=True):
        if isinstance(outcome, RawResult):
            readable.add(table.key)
        elif isinstance(outcome, QueryTimeout):
            unreadable[table.key] = "timeout"
        else:
            unreadable[table.key] = _REASONS.get(outcome.kind, f"outro:{outcome.kind.value}")
    return ReadableReport(frozenset(readable), unreadable, True)
