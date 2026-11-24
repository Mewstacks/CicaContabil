from __future__ import annotations

import json
from pathlib import Path

from dominio_mcp.catalog import Catalog, Column, ForeignKey, Table, build_catalog
from dominio_mcp.joins import find_path
from dominio_mcp.overlay import overlay_from_files
from dominio_mcp.pack import Pack, build_pack
from dominio_mcp.policy import load_policy
from dominio_mcp.readable import ReadableReport

POLICY = load_policy()
OVERLAY = overlay_from_files({})
FIXTURE = Path(__file__).parent / "fixtures" / "mini_catalog.json"


def make(tmp_path: Path, catalog: Catalog, **kw: object) -> Pack:
    build_pack(tmp_path / "p.sqlite3", catalog=catalog, policy=POLICY, overlay=OVERLAY, **kw)  # type: ignore[arg-type]
    return Pack(tmp_path / "p.sqlite3")


def tbl(name: str) -> Table:
    cols = (
        Column("id", 1, "integer", 4, 0, False, None),
        Column("x", 2, "integer", 4, 0, True, None),
    )
    return Table(name, "BASE", 10, None, cols, ("id",), (), None)


def fk(child: str, parent: str, cols: tuple[str, ...] = ("id",)) -> ForeignKey:
    return ForeignKey(child, cols, parent, cols)


def catalog(names: list[str], fks: list[ForeignKey]) -> Catalog:
    return Catalog("bethadba", {n: tbl(n) for n in names}, tuple(fks))


def path_names(steps: list | None) -> list[tuple[str, str, str]] | None:  # type: ignore[type-arg]
    return None if steps is None else [(s.from_table, s.to_table, s.direction) for s in steps]


def test_child_to_parent_chain_with_composite_keys(tmp_path: Path) -> None:
    pack = make(tmp_path, build_catalog(json.loads(FIXTURE.read_text(encoding="utf-8"))))
    steps = find_path(pack, "EFMVSPRO", "geempre")
    assert path_names(steps) == [("efmvspro", "efsaidas", "up"), ("efsaidas", "geempre", "up")]
    assert steps is not None
    assert steps[0].from_columns == ("codi_emp", "codi_sai", "seg_sai")
    assert steps[0].to_columns == ("codi_emp", "codi_sai", "seg_sai")
    assert steps[1].from_columns == ("codi_emp",)


def test_parent_to_child_goes_down(tmp_path: Path) -> None:
    pack = make(tmp_path, build_catalog(json.loads(FIXTURE.read_text(encoding="utf-8"))))
    assert path_names(find_path(pack, "geempre", "efsaidas")) == [("geempre", "efsaidas", "down")]
    assert path_names(find_path(pack, "geempre", "efmvspro")) == [
        ("geempre", "efsaidas", "down"),
        ("efsaidas", "efmvspro", "down"),
    ]


def test_same_table_is_an_empty_path_and_unknown_tables_have_none(tmp_path: Path) -> None:
    pack = make(tmp_path, catalog(["a", "b"], [fk("b", "a")]))
    assert find_path(pack, "a", "a") == []
    assert find_path(pack, "a", "nao_existe") is None
    assert find_path(pack, "nao_existe", "a") is None


def test_siblings_through_a_shared_parent_are_never_joined(tmp_path: Path) -> None:
    pack = make(
        tmp_path,
        catalog(
            ["geempre", "efsaidas", "efentradas"],
            [fk("efsaidas", "geempre"), fk("efentradas", "geempre")],
        ),
    )
    assert find_path(pack, "efsaidas", "efentradas") is None


def test_star_join_through_the_fact_table_is_allowed(tmp_path: Path) -> None:
    pack = make(
        tmp_path,
        catalog(["p", "q", "fato"], [fk("fato", "p"), fk("fato", "q")]),
    )
    assert path_names(find_path(pack, "p", "q")) == [("p", "fato", "down"), ("fato", "q", "up")]


def test_shortest_path_wins_and_ties_are_deterministic(tmp_path: Path) -> None:
    cat = catalog(
        ["a", "b", "c", "d"],
        [fk("a", "b"), fk("b", "d"), fk("a", "c"), fk("c", "d")],
    )
    pack = make(tmp_path, cat)
    first = path_names(find_path(pack, "a", "d"))
    assert first == [("a", "b", "up"), ("b", "d", "up")]
    assert first == path_names(find_path(pack, "a", "d"))


def test_hop_limit_is_four(tmp_path: Path) -> None:
    names = [f"t{i}" for i in range(7)]
    chain = [fk(names[i], names[i + 1]) for i in range(6)]
    pack = make(tmp_path, catalog(names, chain))
    assert len(find_path(pack, "t0", "t4") or []) == 4
    assert find_path(pack, "t0", "t5") is None
    assert len(find_path(pack, "t0", "t5", max_hops=5) or []) == 5


def test_unreadable_bridge_tables_are_skipped(tmp_path: Path) -> None:
    cat = catalog(["a", "ponte", "b"], [fk("a", "ponte"), fk("ponte", "b")])
    report = ReadableReport(frozenset({"a", "b"}), {"ponte": "sem_permissao"}, True)
    pack = make(tmp_path, cat, readable=report)
    assert find_path(pack, "a", "b") is None
    (tmp_path / "x").mkdir()
    open_pack = make(tmp_path / "x", cat)
    assert path_names(find_path(open_pack, "a", "b")) == [
        ("a", "ponte", "up"),
        ("ponte", "b", "up"),
    ]


def test_no_foreign_keys_means_no_path(tmp_path: Path) -> None:
    pack = make(tmp_path, catalog(["a", "b"], []))
    assert find_path(pack, "a", "b") is None
