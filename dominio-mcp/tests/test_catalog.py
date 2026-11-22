from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.catalog import (
    CATALOG_QUERIES,
    Catalog,
    CatalogError,
    build_catalog,
    extract_raw,
)
from dominio_mcp.odbc import RawResult

FIXTURE = Path(__file__).parent / "fixtures" / "mini_catalog.json"


def raw() -> dict[str, list[dict[str, Any]]]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def catalog(data: dict[str, list[dict[str, Any]]] | None = None) -> Catalog:
    return build_catalog(data if data is not None else raw())


def test_only_base_tables_and_views_of_the_owner_are_kept() -> None:
    cat = catalog()
    assert set(cat.tables) == {"geempre", "efsaidas", "efmvspro", "vw_saidas"}
    assert cat.tables["efmvspro"].name == "EFMVSPRO"
    assert cat.tables["vw_saidas"].kind == "VIEW"
    assert build_catalog(raw(), owner="dbo").tables.keys() == {"sp_dummy"}


def test_columns_are_ordered_typed_and_commented() -> None:
    table = catalog().tables["efsaidas"]
    assert [c.name for c in table.columns] == [
        "codi_emp",
        "codi_sai",
        "dsai_sai",
        "vcon_sai",
        "seg_sai",
    ]
    vcon = table.columns[3]
    assert (vcon.type, vcon.width, vcon.scale, vcon.nullable) == ("numeric", 15, 2, True)
    assert vcon.comment == "Valor contabil"
    assert table.columns[0].nullable is False
    assert table.columns[0].comment is None
    assert table.comment == "Notas fiscais de saida"
    assert table.approx_rows == 386290


def test_primary_key_follows_index_sequence() -> None:
    cat = catalog()
    assert cat.tables["geempre"].primary_key == ("codi_emp",)
    assert cat.tables["efsaidas"].primary_key == ("codi_emp", "codi_sai", "seg_sai")


def test_indexes_keep_declared_column_order() -> None:
    idx = {i.name: i for i in catalog().tables["efsaidas"].indexes}
    assert idx["IDX_DATA_SAI"].columns == ("codi_emp", "dsai_sai")
    assert idx["IDX_DATA_SAI"].primary is False
    assert idx["efsaidas"].primary is True


def test_foreign_keys_map_child_columns_to_parent_columns() -> None:
    fks = {(f.child_table, f.parent_table): f for f in catalog().foreign_keys}
    simple = fks[("efsaidas", "geempre")]
    assert simple.child_columns == ("codi_emp",)
    assert simple.parent_columns == ("codi_emp",)
    composite = fks[("EFMVSPRO", "efsaidas")]
    assert composite.child_columns == ("codi_emp", "codi_sai", "seg_sai")
    assert composite.parent_columns == ("codi_emp", "codi_sai", "seg_sai")
    assert len(fks) == 2, "FK de objeto fora do dono precisa ser descartada"


def test_view_definition_is_attached_to_the_view_only() -> None:
    cat = catalog()
    assert cat.tables["vw_saidas"].view_definition is not None
    assert "GROUP BY" in cat.tables["vw_saidas"].view_definition
    assert cat.tables["efsaidas"].view_definition is None


def test_missing_key_in_raw_data_is_a_catalog_error() -> None:
    data = raw()
    del data["columns"][0]["column_name"]
    with pytest.raises(CatalogError):
        catalog(data)
    data2 = raw()
    del data2["foreign_keys"]
    with pytest.raises(CatalogError):
        catalog(data2)


def test_hashes_are_stable_and_ignore_volatile_row_counts() -> None:
    a = catalog()
    data = raw()
    data["tables"][1]["approx_rows"] = 999
    b = catalog(data)
    assert (a.structure_hash(), a.views_hash(), a.comments_hash()) == (
        b.structure_hash(),
        b.views_hash(),
        b.comments_hash(),
    )


def mutate(change: Any) -> Catalog:
    data = copy.deepcopy(raw())
    change(data)
    return catalog(data)


def test_structure_hash_changes_with_type_width_fk_index_and_new_column() -> None:
    base = catalog().structure_hash()
    assert mutate(lambda d: d["columns"][8].update(type="varchar")).structure_hash() != base
    assert mutate(lambda d: d["columns"][8].update(width=18)).structure_hash() != base
    assert mutate(lambda d: d["foreign_keys"].pop(0)).structure_hash() != base
    assert mutate(lambda d: d["indexes"].pop(1)).structure_hash() != base
    assert (
        mutate(
            lambda d: d["columns"].append(
                {
                    "table_id": 10,
                    "column_id": 6,
                    "column_name": "nova",
                    "type": "integer",
                    "width": 4,
                    "scale": 0,
                    "nulls": "Y",
                    "dflt": None,
                    "object_id": 2999,
                }
            )
        ).structure_hash()
        != base
    )


def test_views_hash_changes_only_with_the_view_definition() -> None:
    base = catalog()
    changed = mutate(lambda d: d["views"][0].update(view_def="SELECT 1 AS codi_emp"))
    assert changed.views_hash() != base.views_hash()
    assert changed.structure_hash() == base.structure_hash()


def test_comments_hash_changes_only_with_comments() -> None:
    base = catalog()
    changed = mutate(lambda d: d["remarks"][3].update(remarks="Outro texto"))
    assert changed.comments_hash() != base.comments_hash()
    assert changed.structure_hash() == base.structure_hash()


class FakeRunner:
    """Devolve o dado do fixture conforme a consulta pedida."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], int, float | None]] = []
        self._by_sql = {sql: name for name, sql in CATALOG_QUERIES.items()}
        self._data = raw()

    def __call__(
        self, sql: str, params: tuple[Any, ...] = (), *, max_rows: int, timeout: float | None = None
    ) -> RawResult:
        self.calls.append((sql, params, max_rows, timeout))
        rows = self._data[self._by_sql[sql]]
        columns = tuple(rows[0].keys())
        return RawResult(
            columns=columns,
            rows=[list(r.values()) for r in rows],
            truncated=False,
            elapsed_ms=1.0,
            read_at=datetime.now(UTC),
        )


def test_extract_raw_runs_every_catalog_query_and_rebuilds_the_same_catalog() -> None:
    runner = FakeRunner()
    extracted = extract_raw(runner)
    assert set(extracted) == set(CATALOG_QUERIES)
    assert build_catalog(extracted).structure_hash() == catalog().structure_hash()
    assert len(runner.calls) == len(CATALOG_QUERIES)
    assert all(call[2] >= 100_000 for call in runner.calls), "catalogo e lido por inteiro"
    assert all(call[3] is not None and call[3] >= 60 for call in runner.calls)


def test_extract_raw_refuses_a_truncated_read() -> None:
    class Truncating(FakeRunner):
        def __call__(self, sql: str, params: tuple[Any, ...] = (), **kw: Any) -> RawResult:
            result = super().__call__(sql, params, **kw)
            return RawResult(
                columns=result.columns,
                rows=result.rows,
                truncated=True,
                elapsed_ms=1.0,
                read_at=result.read_at,
            )

    with pytest.raises(CatalogError, match="truncad"):
        extract_raw(Truncating())


def test_catalog_queries_are_plain_selects_on_system_views() -> None:
    for sql in CATALOG_QUERIES.values():
        text = sql.strip().lower()
        assert text.startswith("select ")
        assert ";" not in text
        assert "sys." in text
        for word in ("insert ", "update ", "delete ", "drop ", "alter ", "create ", "call "):
            assert word not in text
