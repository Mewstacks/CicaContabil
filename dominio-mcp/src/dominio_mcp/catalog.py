"""Catalogo do banco do Dominio, lido das visoes `SYS.*` do SQL Anywhere (T2.1).

O banco se autodocumenta: nomes, tipos, comentarios de tabela e coluna, chaves primarias e
estrangeiras, indices e definicao de view. `extract_raw` le tudo com consultas fixas (so SELECT em
`SYS.*`, sem dado de negocio) e `build_catalog` monta o modelo em memoria.

Tres hashes alimentam a versao composta do pack (`pack.py`):

- `structure_hash`: objetos, colunas, tipos, larguras, PK, FK e indices (contagem de linhas nao
  entra: e volatil);
- `views_hash`: definicao de cada view;
- `comments_hash`: comentarios de tabela e de coluna.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol

from dominio_mcp.odbc import RawResult

DEFAULT_OWNER = "bethadba"
KINDS = frozenset({"BASE", "VIEW", "MAT VIEW"})
MAX_CATALOG_ROWS = 500_000
CATALOG_TIMEOUT_SECONDS = 120.0

CATALOG_QUERIES: dict[str, str] = {
    "tables": (
        "SELECT t.table_id, u.user_name AS owner, t.table_name, t.table_type_str AS kind, "
        "t.count AS approx_rows, t.object_id "
        "FROM SYS.SYSTAB t JOIN SYS.SYSUSER u ON u.user_id = t.creator"
    ),
    "columns": (
        "SELECT c.table_id, c.column_id, c.column_name, d.domain_name AS type, c.width, c.scale, "
        'c.nulls, c."default" AS dflt, c.object_id '
        "FROM SYS.SYSTABCOL c JOIN SYS.SYSDOMAIN d ON d.domain_id = c.domain_id"
    ),
    "remarks": "SELECT object_id, remarks FROM SYS.SYSREMARK",
    "indexes": (
        "SELECT i.table_id, i.index_id, i.index_name, i.index_category AS category, "
        'i."unique" AS uniq FROM SYS.SYSIDX i'
    ),
    "index_columns": (
        'SELECT table_id, index_id, sequence, column_id, "order" AS ord, primary_column_id '
        "FROM SYS.SYSIDXCOL"
    ),
    "foreign_keys": (
        "SELECT foreign_table_id, foreign_index_id, primary_table_id, primary_index_id "
        "FROM SYS.SYSFKEY"
    ),
    "views": "SELECT view_object_id, view_def FROM SYS.SYSVIEW",
}

RawCatalog = dict[str, list[dict[str, Any]]]


class CatalogError(Exception):
    pass


class Runner(Protocol):
    def __call__(
        self, sql: str, params: tuple[Any, ...] = (), *, max_rows: int, timeout: float | None = None
    ) -> RawResult: ...


@dataclass(frozen=True, slots=True)
class Column:
    name: str
    position: int
    type: str
    width: int | None
    scale: int | None
    nullable: bool
    comment: str | None


@dataclass(frozen=True, slots=True)
class Index:
    name: str
    columns: tuple[str, ...]
    unique: int
    category: int

    @property
    def primary(self) -> bool:
        return self.category == 1


@dataclass(frozen=True, slots=True)
class ForeignKey:
    child_table: str
    child_columns: tuple[str, ...]
    parent_table: str
    parent_columns: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Table:
    name: str
    kind: str
    approx_rows: int | None
    comment: str | None
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...]
    indexes: tuple[Index, ...]
    view_definition: str | None

    @property
    def key(self) -> str:
        return self.name.lower()


def _digest(payload: Any) -> str:
    text = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True, slots=True)
class Catalog:
    owner: str
    tables: dict[str, Table]
    foreign_keys: tuple[ForeignKey, ...]

    def structure_hash(self) -> str:
        tables = [
            [
                t.name,
                t.kind,
                [[c.name, c.type, c.width, c.scale, c.nullable] for c in t.columns],
                list(t.primary_key),
                sorted([i.name, list(i.columns), i.unique, i.category] for i in t.indexes),
            ]
            for t in sorted(self.tables.values(), key=lambda x: x.key)
        ]
        fks = sorted(
            [f.child_table, list(f.child_columns), f.parent_table, list(f.parent_columns)]
            for f in self.foreign_keys
        )
        return _digest({"tables": tables, "foreign_keys": fks})

    def views_hash(self) -> str:
        views = sorted(
            [t.key, hashlib.sha256(t.view_definition.encode("utf-8")).hexdigest()]
            for t in self.tables.values()
            if t.view_definition is not None
        )
        return _digest(views)

    def comments_hash(self) -> str:
        items: list[list[Any]] = []
        for t in self.tables.values():
            items.append([t.key, "", t.comment])
            items.extend([t.key, c.name, c.comment] for c in t.columns if c.comment)
        return _digest(sorted(items, key=lambda x: (x[0], x[1])))


def extract_raw(run: Runner, *, timeout: float = CATALOG_TIMEOUT_SECONDS) -> RawCatalog:
    """Le o catalogo inteiro com as consultas fixas; recusa leitura truncada."""
    raw: RawCatalog = {}
    for name, sql in CATALOG_QUERIES.items():
        result = run(sql, (), max_rows=MAX_CATALOG_ROWS, timeout=timeout)
        if result.truncated:
            raise CatalogError(f"leitura truncada do catalogo ({name}): aumente o limite")
        raw[name] = [dict(zip(result.columns, row, strict=True)) for row in result.rows]
    return raw


def _section(raw: Mapping[str, list[dict[str, Any]]], name: str) -> list[dict[str, Any]]:
    if name not in raw:
        raise CatalogError(f"secao ausente no catalogo: {name}")
    return raw[name]


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def build_catalog(
    raw: Mapping[str, list[dict[str, Any]]], *, owner: str = DEFAULT_OWNER
) -> Catalog:
    try:
        return _build(raw, owner)
    except KeyError as exc:
        raise CatalogError(f"campo ausente no catalogo: {exc.args[0]}") from None


def _build(raw: Mapping[str, list[dict[str, Any]]], owner: str) -> Catalog:
    wanted = owner.lower()
    tables_raw = {
        int(t["table_id"]): t
        for t in _section(raw, "tables")
        if str(t["owner"]).lower() == wanted and str(t["kind"]) in KINDS
    }
    remarks = {int(r["object_id"]): _clean(r["remarks"]) for r in _section(raw, "remarks")}

    columns_by_table: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for c in _section(raw, "columns"):
        if int(c["table_id"]) in tables_raw:
            columns_by_table[int(c["table_id"])].append(c)
    column_name: dict[tuple[int, int], str] = {}
    for tid, cols in columns_by_table.items():
        cols.sort(key=lambda c: int(c["column_id"]))
        for c in cols:
            column_name[(tid, int(c["column_id"]))] = str(c["column_name"])

    index_columns: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    for ic in _section(raw, "index_columns"):
        key = (int(ic["table_id"]), int(ic["index_id"]))
        if key[0] in tables_raw:
            index_columns[key].append(ic)
    for items in index_columns.values():
        items.sort(key=lambda x: int(x["sequence"]))

    indexes_by_table: dict[int, list[Index]] = defaultdict(list)
    primary_key: dict[int, tuple[str, ...]] = {}
    for i in _section(raw, "indexes"):
        tid, iid = int(i["table_id"]), int(i["index_id"])
        if tid not in tables_raw:
            continue
        names = tuple(
            column_name[(tid, int(ic["column_id"]))]
            for ic in index_columns[(tid, iid)]
            if (tid, int(ic["column_id"])) in column_name
        )
        index = Index(str(i["index_name"]), names, int(i["uniq"] or 0), int(i["category"]))
        indexes_by_table[tid].append(index)
        if index.primary:
            primary_key[tid] = names

    views = {int(v["view_object_id"]): str(v["view_def"]) for v in _section(raw, "views")}

    tables: dict[str, Table] = {}
    for tid, t in tables_raw.items():
        columns = tuple(
            Column(
                name=str(c["column_name"]),
                position=int(c["column_id"]),
                type=str(c["type"]),
                width=None if c["width"] is None else int(c["width"]),
                scale=None if c["scale"] is None else int(c["scale"]),
                nullable=str(c["nulls"]).upper() == "Y",
                comment=remarks.get(int(c["object_id"])),
            )
            for c in columns_by_table[tid]
        )
        table = Table(
            name=str(t["table_name"]),
            kind=str(t["kind"]),
            approx_rows=None if t["approx_rows"] is None else int(t["approx_rows"]),
            comment=remarks.get(int(t["object_id"])),
            columns=columns,
            primary_key=primary_key.get(tid, ()),
            indexes=tuple(sorted(indexes_by_table[tid], key=lambda x: x.name)),
            view_definition=views.get(int(t["object_id"])),
        )
        tables[table.key] = table

    foreign_keys: list[ForeignKey] = []
    for f in _section(raw, "foreign_keys"):
        child, parent = int(f["foreign_table_id"]), int(f["primary_table_id"])
        if child not in tables_raw or parent not in tables_raw:
            continue
        pairs = index_columns[(child, int(f["foreign_index_id"]))]
        child_cols = [column_name.get((child, int(ic["column_id"]))) for ic in pairs]
        parent_cols = [
            None
            if ic["primary_column_id"] is None
            else column_name.get((parent, int(ic["primary_column_id"])))
            for ic in pairs
        ]
        if not pairs or None in child_cols or None in parent_cols:
            continue
        foreign_keys.append(
            ForeignKey(
                child_table=str(tables_raw[child]["table_name"]),
                child_columns=tuple(str(c) for c in child_cols),
                parent_table=str(tables_raw[parent]["table_name"]),
                parent_columns=tuple(str(c) for c in parent_cols),
            )
        )
    return Catalog(owner=owner, tables=tables, foreign_keys=tuple(foreign_keys))
