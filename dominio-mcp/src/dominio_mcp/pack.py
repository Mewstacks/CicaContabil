"""Pack de conhecimento do banco, por escritorio (D-318, T2.6).

SQLite gerado do catalogo vivo + politica + overlay: tabelas, colunas (com classe de dados e
legenda), chaves, indices, quais colunas o dono aceitou e as estruturas de busca (`pack_index.py`).
Fica em `%LOCALAPPDATA%\\dominio-mcp\\packs`, fora do git, e nao e redistribuido.

- **Versao composta**: hash da estrutura, das definicoes de view, dos comentarios, da politica, do
  overlay, das colunas aceitas e da legibilidade. Mudou qualquer um, a versao muda.
- **Troca atomica**: cada versao vive num arquivo proprio (`pack-<versao>.sqlite3`); o ponteiro
  `current.json` e trocado por `os.replace`. Nunca se substitui um arquivo aberto (no Windows o
  SQLite nao deixa).
- Comentario de coluna de segredo e de tabela de credencial **nao e guardado**.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sqlite3
import threading
import time
from collections.abc import Iterable, Mapping, Set
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dominio_mcp.catalog import Catalog, Table
from dominio_mcp.config import Settings
from dominio_mcp.enums import is_unused, parse_legend
from dominio_mcp.overlay import Overlay
from dominio_mcp.pack_index import create_search_structures
from dominio_mcp.policy import ColumnPolicy, Policy, PolicyClass
from dominio_mcp.readable import ReadableReport

# Sobe quando a classificacao de colunas muda de comportamento no codigo (nao so no YAML da
# politica), senao um pack antigo seguiria "fresco" com classes antigas. 4: D-328 e D-329.
PACK_FORMAT = 4
_STALE_BUILD_SECONDS = 3600

SCHEMA = """
CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
CREATE TABLE tables (
  key TEXT PRIMARY KEY, name TEXT NOT NULL, kind TEXT NOT NULL, approx_rows INTEGER,
  comment TEXT, module TEXT NOT NULL, readable INTEGER, blocked_reason TEXT,
  queryable INTEGER NOT NULL, obsolete INTEGER NOT NULL, pk TEXT NOT NULL, view_sha TEXT
);
CREATE TABLE columns (
  table_key TEXT NOT NULL, key TEXT NOT NULL, name TEXT NOT NULL, position INTEGER NOT NULL,
  type TEXT NOT NULL, width INTEGER, scale INTEGER, nullable INTEGER NOT NULL, comment TEXT,
  klass TEXT NOT NULL, category TEXT, rule TEXT NOT NULL, blocked_reason TEXT, legend TEXT,
  unused INTEGER NOT NULL, in_pk INTEGER NOT NULL, in_fk INTEGER NOT NULL,
  PRIMARY KEY (table_key, key)
);
CREATE TABLE idx (
  table_key TEXT NOT NULL, name TEXT NOT NULL, columns TEXT NOT NULL,
  uniq INTEGER NOT NULL, category INTEGER NOT NULL
);
CREATE TABLE fks (
  child TEXT NOT NULL, child_cols TEXT NOT NULL, parent TEXT NOT NULL, parent_cols TEXT NOT NULL
);
CREATE TABLE accepted (
  table_key TEXT NOT NULL, column_key TEXT NOT NULL, PRIMARY KEY (table_key, column_key)
);
"""


class PackError(Exception):
    pass


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def acceptance_hash(accepted: Iterable[tuple[str, str]]) -> str:
    return sha256_text(json.dumps(sorted(accepted), separators=(",", ":")))


def readable_hash(report: ReadableReport | None) -> str:
    if report is None:
        return ""
    return sha256_text(json.dumps(sorted(report.unreadable.items()), separators=(",", ":")))


def compute_version(
    *,
    structure_hash: str,
    views_hash: str,
    comments_hash: str,
    policy_sha: str,
    overlay_sha: str,
    acceptance_sha: str,
    readable_sha: str = "",
) -> str:
    parts = [
        f"formato-{PACK_FORMAT}",
        structure_hash,
        views_hash,
        comments_hash,
        policy_sha,
        overlay_sha,
        acceptance_sha,
        readable_sha,
    ]
    return sha256_text("|".join(parts))


@dataclass(frozen=True, slots=True)
class PackMeta:
    version: str
    owner: str
    dsn: str
    built_at: str
    structure_hash: str
    views_hash: str
    comments_hash: str
    policy_sha: str
    overlay_sha: str
    acceptance_sha: str
    counts: dict[str, int]
    server: str = ""

    @property
    def short(self) -> str:
        return self.version[:12]


@dataclass(frozen=True, slots=True)
class TableRow:
    key: str
    name: str
    kind: str
    approx_rows: int | None
    comment: str | None
    module: str
    readable: bool | None
    blocked_reason: str | None
    queryable: bool
    obsolete: bool
    pk: tuple[str, ...]
    view_sha: str | None


@dataclass(frozen=True, slots=True)
class ColumnRow:
    table_key: str
    key: str
    name: str
    position: int
    type: str
    width: int | None
    scale: int | None
    nullable: bool
    comment: str | None
    klass: PolicyClass
    category: str | None
    rule: str
    blocked_reason: str | None
    legend: str | None
    unused: bool
    in_pk: bool
    in_fk: bool


@dataclass(frozen=True, slots=True)
class FkRow:
    child: str
    child_cols: tuple[str, ...]
    parent: str
    parent_cols: tuple[str, ...]


def table_blocked_reason(
    table: Table,
    policy: Policy,
    readable: ReadableReport | None,
    approved_views: Mapping[str, str],
) -> str | None:
    if table.key in policy.denied_tables:
        return "tabela_de_credencial"
    if readable is not None and table.key in readable.unreadable:
        return f"ilegivel:{readable.unreadable[table.key]}"
    if table.kind != "BASE" and not _view_is_approved(table, approved_views):
        return "view_nao_aprovada"
    return None


def view_sha(table: Table) -> str | None:
    return None if table.view_definition is None else sha256_text(table.view_definition)


def _view_is_approved(table: Table, approved_views: Mapping[str, str]) -> bool:
    return view_sha(table) is not None and approved_views.get(table.key) == view_sha(table)


def classify_for_pack(
    catalog: Catalog,
    policy: Policy,
    accepted: Set[tuple[str, str]],
    approved_views: Mapping[str, str],
) -> dict[tuple[str, str], ColumnPolicy]:
    return policy.classify_catalog(
        catalog,
        lambda t, c: (t, c) in accepted,
        lambda table: _view_is_approved(table, approved_views),
    )


def build_pack(
    target: Path,
    *,
    catalog: Catalog,
    policy: Policy,
    overlay: Overlay,
    accepted: Set[tuple[str, str]] = frozenset(),
    approved_views: Mapping[str, str] | None = None,
    readable: ReadableReport | None = None,
    dsn: str = "",
    built_at: datetime | None = None,
    server_info: str = "",
) -> PackMeta:
    """Escreve o pack SQLite em `target` (arquivo novo, ainda sem ponteiro) e devolve a meta."""
    approved = dict(approved_views or {})
    stamp = (built_at or datetime.now(UTC)).isoformat(timespec="seconds")
    classes = classify_for_pack(catalog, policy, accepted, approved)
    version = compute_version(
        structure_hash=catalog.structure_hash(),
        views_hash=catalog.views_hash(),
        comments_hash=catalog.comments_hash(),
        policy_sha=policy.sha,
        overlay_sha=overlay.sha,
        acceptance_sha=acceptance_hash(accepted),
        readable_sha=readable_hash(readable),
    )
    if target.exists():
        target.unlink()
    target.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(target)
    try:
        conn.executescript(SCHEMA)
        fk_child_cols: dict[str, set[str]] = {}
        for fk in catalog.foreign_keys:
            fk_child_cols.setdefault(fk.child_table.lower(), set()).update(
                c.lower() for c in fk.child_columns
            )
        table_rows: list[tuple[Any, ...]] = []
        column_rows: list[tuple[Any, ...]] = []
        index_rows: list[tuple[Any, ...]] = []
        for tkey, table in sorted(catalog.tables.items()):
            reason = table_blocked_reason(table, policy, readable, approved)
            hidden = reason == "tabela_de_credencial"
            readable_flag = None if readable is None else int(tkey in readable.readable)
            table_rows.append(
                (
                    tkey,
                    table.name,
                    table.kind,
                    table.approx_rows,
                    None if hidden else table.comment,
                    tkey[:2],
                    readable_flag,
                    reason,
                    int(reason is None),
                    int(is_unused(table.comment)),
                    json.dumps(list(table.primary_key)),
                    view_sha(table),
                )
            )
            pk = {c.lower() for c in table.primary_key}
            for column in table.columns:
                ckey = column.name.lower()
                cp = classes[(tkey, ckey)]
                secret = cp.klass is PolicyClass.SEGREDO
                comment = None if secret else column.comment
                legend = None if secret else parse_legend(column.comment)
                column_rows.append(
                    (
                        tkey,
                        ckey,
                        column.name,
                        column.position,
                        column.type,
                        column.width,
                        column.scale,
                        int(column.nullable),
                        comment,
                        cp.klass.value,
                        cp.category,
                        cp.rule,
                        cp.blocked_reason,
                        None if legend is None else json.dumps(legend.render()),
                        int(is_unused(comment)),
                        int(ckey in pk),
                        int(ckey in fk_child_cols.get(tkey, ())),
                    )
                )
            index_rows.extend(
                (tkey, i.name, json.dumps(list(i.columns)), i.unique, i.category)
                for i in table.indexes
            )
        conn.executemany("INSERT INTO tables VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", table_rows)
        conn.executemany(
            "INSERT INTO columns VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", column_rows
        )
        conn.executemany("INSERT INTO idx VALUES (?,?,?,?,?)", index_rows)
        conn.executemany(
            "INSERT INTO fks VALUES (?,?,?,?)",
            [
                (
                    f.child_table.lower(),
                    json.dumps([c.lower() for c in f.child_columns]),
                    f.parent_table.lower(),
                    json.dumps([c.lower() for c in f.parent_columns]),
                )
                for f in catalog.foreign_keys
            ],
        )
        conn.executemany("INSERT INTO accepted VALUES (?,?)", sorted(accepted))
        create_search_structures(conn)
        class_counts: dict[str, int] = {}
        for cp in classes.values():
            class_counts[cp.klass.value] = class_counts.get(cp.klass.value, 0) + 1
        counts = {
            "tables": len(table_rows),
            "columns": len(column_rows),
            "foreign_keys": len(catalog.foreign_keys),
            **{f"columns_{k}": v for k, v in sorted(class_counts.items())},
        }
        meta = PackMeta(
            version=version,
            owner=catalog.owner,
            dsn=dsn,
            built_at=stamp,
            structure_hash=catalog.structure_hash(),
            views_hash=catalog.views_hash(),
            comments_hash=catalog.comments_hash(),
            policy_sha=policy.sha,
            overlay_sha=overlay.sha,
            acceptance_sha=acceptance_hash(accepted),
            counts=counts,
            server=server_info,
        )
        conn.executemany(
            "INSERT INTO meta VALUES (?,?)",
            [
                ("format", str(PACK_FORMAT)),
                ("version", meta.version),
                ("owner", meta.owner),
                ("dsn", meta.dsn),
                ("built_at", meta.built_at),
                ("structure_hash", meta.structure_hash),
                ("views_hash", meta.views_hash),
                ("comments_hash", meta.comments_hash),
                ("policy_sha", meta.policy_sha),
                ("overlay_sha", meta.overlay_sha),
                ("acceptance_sha", meta.acceptance_sha),
                ("counts", json.dumps(counts)),
                ("server", meta.server),
            ],
        )
        conn.execute(f"PRAGMA user_version = {PACK_FORMAT}")
        conn.commit()
    finally:
        conn.close()
    return meta


class Pack:
    """Leitura somente leitura de um pack; seguro entre threads (trinco proprio)."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()
        try:
            self._conn = sqlite3.connect(
                f"{path.resolve().as_uri()}?mode=ro", uri=True, check_same_thread=False
            )
            version = self._conn.execute("PRAGMA user_version").fetchone()[0]
        except sqlite3.Error as exc:
            raise PackError("pack ilegivel") from exc
        if version != PACK_FORMAT:
            self._conn.close()
            raise PackError(f"formato de pack {version} nao suportado (esperado {PACK_FORMAT})")
        self.meta = self._load_meta()

    def _load_meta(self) -> PackMeta:
        values = dict(self.query("SELECT key, value FROM meta"))
        try:
            return PackMeta(
                version=values["version"],
                owner=values["owner"],
                dsn=values["dsn"],
                built_at=values["built_at"],
                structure_hash=values["structure_hash"],
                views_hash=values["views_hash"],
                comments_hash=values["comments_hash"],
                policy_sha=values["policy_sha"],
                overlay_sha=values["overlay_sha"],
                acceptance_sha=values["acceptance_sha"],
                counts=json.loads(values["counts"]),
                server=values.get("server", ""),
            )
        except KeyError as exc:
            raise PackError("pack sem metadados completos") from exc

    def query(self, sql: str, params: tuple[Any, ...] = ()) -> list[tuple[Any, ...]]:
        with self._lock:
            return list(self._conn.execute(sql, params))

    def close(self) -> None:
        self._conn.close()

    def table(self, key: str) -> TableRow | None:
        rows = self.query("SELECT * FROM tables WHERE key = ?", (key.lower(),))
        return _table_row(rows[0]) if rows else None

    def tables(self) -> list[TableRow]:
        return [_table_row(r) for r in self.query("SELECT * FROM tables ORDER BY key")]

    def columns(self, table_key: str) -> list[ColumnRow]:
        rows = self.query(
            "SELECT * FROM columns WHERE table_key = ? ORDER BY position", (table_key.lower(),)
        )
        return [_column_row(r) for r in rows]

    def column(self, table_key: str, column_key: str) -> ColumnRow | None:
        rows = self.query(
            "SELECT * FROM columns WHERE table_key = ? AND key = ?",
            (table_key.lower(), column_key.lower()),
        )
        return _column_row(rows[0]) if rows else None

    def foreign_keys(self) -> list[FkRow]:
        return [
            FkRow(c, tuple(json.loads(cc)), p, tuple(json.loads(pc)))
            for c, cc, p, pc in self.query("SELECT child, child_cols, parent, parent_cols FROM fks")
        ]

    def indexes(self, table_key: str) -> list[tuple[str, tuple[str, ...], int, int]]:
        rows = self.query(
            "SELECT name, columns, uniq, category FROM idx WHERE table_key = ? ORDER BY name",
            (table_key.lower(),),
        )
        return [(n, tuple(json.loads(c)), u, k) for n, c, u, k in rows]

    def accepted(self) -> frozenset[tuple[str, str]]:
        return frozenset(
            (t, c) for t, c in self.query("SELECT table_key, column_key FROM accepted")
        )


def _table_row(r: tuple[Any, ...]) -> TableRow:
    return TableRow(
        key=r[0],
        name=r[1],
        kind=r[2],
        approx_rows=r[3],
        comment=r[4],
        module=r[5],
        readable=None if r[6] is None else bool(r[6]),
        blocked_reason=r[7],
        queryable=bool(r[8]),
        obsolete=bool(r[9]),
        pk=tuple(json.loads(r[10])),
        view_sha=r[11],
    )


def _column_row(r: tuple[Any, ...]) -> ColumnRow:
    return ColumnRow(
        table_key=r[0],
        key=r[1],
        name=r[2],
        position=r[3],
        type=r[4],
        width=r[5],
        scale=r[6],
        nullable=bool(r[7]),
        comment=r[8],
        klass=PolicyClass(r[9]),
        category=r[10],
        rule=r[11],
        blocked_reason=r[12],
        legend=None if r[13] is None else str(json.loads(r[13])),
        unused=bool(r[14]),
        in_pk=bool(r[15]),
        in_fk=bool(r[16]),
    )


class PackStore:
    """Pasta de packs com ponteiro atomico para a versao corrente."""

    def __init__(self, directory: Path, *, keep: int = 2) -> None:
        self.directory = directory
        self._keep = keep

    @property
    def pointer(self) -> Path:
        return self.directory / "current.json"

    def current_path(self) -> Path | None:
        try:
            data = json.loads(self.pointer.read_text(encoding="utf-8"))
            path = self.directory / str(data["file"])
        except (OSError, ValueError, KeyError, TypeError):
            return None
        return path if path.is_file() else None

    def open_current(self) -> Pack | None:
        path = self.current_path()
        return None if path is None else Pack(path)

    def new_build_path(self) -> Path:
        self.directory.mkdir(parents=True, exist_ok=True)
        return self.directory / f"build-{os.getpid()}-{time.time_ns()}.sqlite3"

    def publish(self, built: Path, meta: PackMeta) -> Path:
        final = self.directory / f"pack-{meta.short}.sqlite3"
        if final.exists():
            built.unlink(missing_ok=True)  # mesma versao: conteudo igual, nao troca arquivo aberto
        else:
            os.replace(built, final)
        tmp = self.pointer.with_name(f"current.{os.getpid()}.tmp")
        tmp.write_text(json.dumps({"file": final.name, "version": meta.version}), encoding="utf-8")
        os.replace(tmp, self.pointer)
        self.cleanup()
        return final

    def cleanup(self) -> None:
        current = self.current_path()
        packs = sorted(self.directory.glob("pack-*.sqlite3"), key=lambda p: p.stat().st_mtime)
        for old in packs[: max(0, len(packs) - self._keep)]:
            if old != current:
                try:
                    old.unlink()
                except OSError:
                    continue  # aberto por outro processo (Windows): fica para a proxima limpeza
        for stale in self.directory.glob("build-*.sqlite3"):
            try:
                if time.time() - stale.stat().st_mtime > _STALE_BUILD_SECONDS:
                    stale.unlink()
            except OSError:
                continue


def pack_store_for(settings: Settings) -> PackStore:
    slug = re.sub(r"[^A-Za-z0-9_-]", "_", settings.dsn)
    return PackStore(settings.home / "packs" / slug)
