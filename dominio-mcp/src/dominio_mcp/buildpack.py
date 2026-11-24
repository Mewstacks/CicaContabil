"""Comando de construcao do pack: `python -m dominio_mcp.buildpack [--aceitar]` (T2.9).

Le o catalogo vivo numa unica admissao (uma conta no orcamento de frequencia), confere a
legibilidade de cada objeto, classifica as colunas pela politica e publica o pack por troca
atomica. A saida so tem numeros: nunca comentario, nome de coluna bloqueada nem valor de linha.

`--aceitar` aprova o catalogo atual como base: toda coluna que nenhuma regra classificou passa a
`normal`. Sem ele, coluna nova (ou o catalogo inteiro, na primeira construcao) fica bloqueada como
`nao_classificada`. Coluna sensivel (segredo, documento, pessoal, texto livre) nunca e liberada
por aceite.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import Any, Protocol

from dominio_mcp.budget import Busy, Quarantined, RateLimited
from dominio_mcp.catalog import (
    DEFAULT_OWNER,
    CatalogError,
    Runner,
    build_catalog,
    extract_raw,
)
from dominio_mcp.config import ConfigError, Settings, load_settings
from dominio_mcp.odbc import (
    DbError,
    ExecutionUncertain,
    OdbcUnavailable,
    RawResult,
    build_session,
)
from dominio_mcp.overlay import Overlay, OverlayError, approved_views, load_overlay
from dominio_mcp.pack import (
    PackError,
    PackStore,
    build_pack,
    classify_for_pack,
    pack_store_for,
)
from dominio_mcp.policy import Policy, PolicyError, load_policy
from dominio_mcp.readable import ReadableProbeError, probe_readable
from dominio_mcp.watchdog import QueryTimeout

SERVER_INFO_SQL = "SELECT PROPERTY('ProductVersion'), DB_PROPERTY('Name')"


class BuildSlot(Protocol):
    def execute(
        self, sql: str, params: tuple[Any, ...] = (), *, max_rows: int, timeout: float | None = None
    ) -> RawResult: ...


class BuildSession(Protocol):
    def slot(self) -> AbstractContextManager[BuildSlot]: ...

    def execute_batch(
        self, statements: Sequence[str], *, timeout_each: float = 10.0
    ) -> list[RawResult | DbError | QueryTimeout]: ...


@dataclass(frozen=True, slots=True)
class BuildReport:
    version: str
    path: str
    size_bytes: int
    server: str
    tables: int
    columns: int
    foreign_keys: int
    classes: dict[str, int]
    unclassified: int
    unreadable: int
    accepted_total: int
    accepted_added: int
    seconds: dict[str, float]

    def render(self) -> str:
        classes = ", ".join(f"{k} {v}" for k, v in sorted(self.classes.items()))
        lines = [
            f"pack {self.version[:12]} publicado ({self.size_bytes / 1_048_576:.1f} MB)",
            f"versao: {self.version}",
            f"servidor: {self.server or 'desconhecido'}",
            f"tabelas: {self.tables} | colunas: {self.columns} | chaves estrangeiras: "
            f"{self.foreign_keys}",
            f"colunas por classe: {classes}",
            f"colunas aceitas: {self.accepted_total} (novas neste pack: {self.accepted_added})",
            f"objetos ilegiveis para este usuario: {self.unreadable}",
        ]
        if self.unclassified:
            lines.append(
                f"{self.unclassified} colunas sem classificacao ficaram BLOQUEADAS; rode com "
                "--aceitar para aprovar o catalogo atual"
            )
        s = self.seconds
        lines.append(
            f"tempo: leitura {s['extract']:.1f} s, legibilidade {s['probe']:.1f} s, "
            f"geracao {s['build']:.1f} s, total {s['total']:.1f} s"
        )
        return "\n".join(lines)


def _server_info(execute: Runner) -> str:
    try:
        row = execute(SERVER_INFO_SQL, (), max_rows=2, timeout=10.0).rows
    except DbError:
        return ""
    if len(row) == 1 and len(row[0]) == 2:
        return f"{row[0][0]} / {row[0][1]}"
    return ""


def run_build(
    settings: Settings,
    session: BuildSession,
    *,
    accept: bool = False,
    policy: Policy | None = None,
    overlay: Overlay | None = None,
    store: PackStore | None = None,
) -> BuildReport:
    started = time.perf_counter()
    policy = policy or load_policy()
    overlay = overlay or load_overlay()
    store = store or pack_store_for(settings)
    approved = approved_views(overlay)

    previous: frozenset[tuple[str, str]] = frozenset()
    try:
        old = store.open_current()
    except PackError:
        old = None  # pack de outro formato: reconstroi do zero, sem herdar aceite
    if old is not None:
        previous = old.accepted()
        old.close()

    with session.slot() as slot:
        raw = extract_raw(slot.execute)
        server = _server_info(slot.execute)
    t_extract = time.perf_counter()
    catalog = build_catalog(raw, owner=DEFAULT_OWNER)

    readable = probe_readable(session.execute_batch, catalog)
    t_probe = time.perf_counter()

    existing = {(k, c.name.lower()) for k, t in catalog.tables.items() for c in t.columns}
    accepted = {key for key in previous if key in existing}
    classes = classify_for_pack(catalog, policy, accepted, approved)
    unclassified_keys = {k for k, cp in classes.items() if cp.rule == "sem_regra"}
    added = 0
    if accept:
        added = len(unclassified_keys - accepted)
        accepted |= unclassified_keys
        classes = classify_for_pack(catalog, policy, accepted, approved)

    built = store.new_build_path()
    meta = build_pack(
        built,
        catalog=catalog,
        policy=policy,
        overlay=overlay,
        accepted=frozenset(accepted),
        approved_views=approved,
        readable=readable,
        dsn=settings.dsn,
        server_info=server,
    )
    size = built.stat().st_size
    final = store.publish(built, meta)
    done = time.perf_counter()

    class_counts: dict[str, int] = {}
    for cp in classes.values():
        class_counts[cp.klass.value] = class_counts.get(cp.klass.value, 0) + 1
    return BuildReport(
        version=meta.version,
        path=str(final),
        size_bytes=size,
        server=server,
        tables=meta.counts["tables"],
        columns=meta.counts["columns"],
        foreign_keys=meta.counts["foreign_keys"],
        classes=class_counts,
        unclassified=sum(1 for cp in classes.values() if cp.rule == "sem_regra"),
        unreadable=len(readable.unreadable),
        accepted_total=len(accepted),
        accepted_added=added,
        seconds={
            "extract": t_extract - started,
            "probe": t_probe - t_extract,
            "build": done - t_probe,
            "total": done - started,
        },
    )


_EXPECTED = (
    ConfigError,
    PolicyError,
    OverlayError,
    CatalogError,
    ReadableProbeError,
    DbError,
    OdbcUnavailable,
    ExecutionUncertain,
    QueryTimeout,
    Busy,
    Quarantined,
    RateLimited,
    PackError,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="dominio-mcp build-pack", description=__doc__)
    parser.add_argument(
        "--aceitar",
        action="store_true",
        help="aprova o catalogo atual como base (colunas sem regra passam a normal)",
    )
    args = parser.parse_args(argv)
    try:
        settings = load_settings()
        session = build_session(settings)
        try:
            report = run_build(settings, session, accept=args.aceitar)
        finally:
            close = getattr(session, "close", None)
            if close is not None:
                close()
    except _EXPECTED as exc:
        print(f"erro: {exc}", file=sys.stderr)
        return 1
    print(report.render())
    return 0


if __name__ == "__main__":
    sys.exit(main())
