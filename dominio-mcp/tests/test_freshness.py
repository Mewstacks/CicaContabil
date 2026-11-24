from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.catalog import build_catalog
from dominio_mcp.freshness import (
    PROBE_KEYS,
    PROBE_SQL,
    FreshnessGuard,
    Hashes,
    PackMissing,
    PackStale,
    make_rehasher,
    read_probe,
)
from dominio_mcp.odbc import DbError, DbErrorKind, RawResult
from dominio_mcp.overlay import OverlayError, approved_views, load_overlay, overlay_from_files
from dominio_mcp.pack import PackMeta, PackStore, build_pack
from dominio_mcp.policy import load_policy

FIXTURE = Path(__file__).parent / "fixtures" / "mini_catalog.json"
POLICY = load_policy()
OVERLAY = overlay_from_files({"glossary.yaml": "a: 1\n"})


def raw() -> dict[str, list[dict[str, Any]]]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def publish(store: PackStore, data: dict[str, list[dict[str, Any]]] | None = None) -> PackMeta:
    built = store.new_build_path()
    meta = build_pack(
        built,
        catalog=build_catalog(data or raw()),
        policy=POLICY,
        overlay=OVERLAY,
        dsn="contabil",
    )
    store.publish(built, meta)
    return meta


class Clock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class StubDb:
    """Executor falso: devolve a sonda e conta chamadas; `rehash` devolve hashes configuraveis."""

    def __init__(self, meta: PackMeta) -> None:
        self.probe = [10, 100, 5, 20, 90, 3, 500]
        self.hashes = Hashes(meta.structure_hash, meta.views_hash, meta.comments_hash)
        self.probe_calls = 0
        self.rehash_calls = 0
        self.fail: Exception | None = None

    def execute(
        self, sql: str, params: tuple[Any, ...] = (), *, max_rows: int, timeout: float | None = None
    ) -> RawResult:
        if self.fail is not None:
            raise self.fail
        assert sql == PROBE_SQL
        self.probe_calls += 1
        return RawResult((), [list(self.probe)], False, 1.0, datetime.now(UTC))

    def rehash(self, execute: Any) -> Hashes:
        if self.fail is not None:
            raise self.fail
        self.rehash_calls += 1
        return self.hashes


def make_guard(
    tmp_path: Path, **kw: Any
) -> tuple[FreshnessGuard, PackStore, PackMeta, StubDb, Clock]:
    store = PackStore(tmp_path / "packs")
    meta = publish(store)
    db, clock = StubDb(meta), Clock()
    guard = FreshnessGuard(
        store,
        policy_sha=kw.get("policy_sha", POLICY.sha),
        overlay_sha=kw.get("overlay_sha", OVERLAY.sha),
        rehash=db.rehash,
        clock=clock,
    )
    return guard, store, meta, db, clock


def test_missing_pack_is_reported(tmp_path: Path) -> None:
    store = PackStore(tmp_path / "packs")
    guard = FreshnessGuard(
        store, policy_sha="p", overlay_sha="o", rehash=lambda e: Hashes("", "", "")
    )
    with pytest.raises(PackMissing, match="build-pack"):
        guard.pack()


def test_startup_rehash_then_cheap_probe_then_hourly_rehash(tmp_path: Path) -> None:
    guard, _, meta, db, clock = make_guard(tmp_path)
    pack = guard.check(db.execute)
    assert pack.meta.version == meta.version
    assert (db.rehash_calls, db.probe_calls) == (1, 1)  # re-hash ao iniciar + base da sonda

    guard.check(db.execute)
    assert (db.rehash_calls, db.probe_calls) == (1, 1)  # dentro de 60 s nao toca o banco

    clock.now += 61
    guard.check(db.execute)
    assert (db.rehash_calls, db.probe_calls) == (1, 2)  # so a sonda barata

    clock.now += 3600
    guard.check(db.execute)
    assert (db.rehash_calls, db.probe_calls) == (2, 3)  # re-hash completo de 1 em 1 hora


def test_probe_mismatch_marks_the_pack_stale_until_a_new_pack_is_published(tmp_path: Path) -> None:
    guard, store, _, db, clock = make_guard(tmp_path)
    guard.check(db.execute)
    db.probe[1] += 1  # uma coluna nova
    clock.now += 61
    with pytest.raises(PackStale, match="contagens"):
        guard.check(db.execute)
    calls = (db.rehash_calls, db.probe_calls)
    clock.now += 61
    with pytest.raises(PackStale):
        guard.check(db.execute)
    assert (db.rehash_calls, db.probe_calls) == calls, "pegajoso: nem consulta o banco de novo"
    assert guard.stale_reason is not None

    changed = raw()
    changed["remarks"][3]["remarks"] = "Comentario novo"
    meta2 = publish(store, changed)
    db.hashes = Hashes(meta2.structure_hash, meta2.views_hash, meta2.comments_hash)
    assert guard.check(db.execute).meta.version == meta2.version
    assert guard.stale_reason is None


@pytest.mark.parametrize(
    ("field", "reason"),
    [("structure", "estrutura"), ("views", "view"), ("comments", "comentarios")],
)
def test_full_rehash_mismatch_names_what_changed(tmp_path: Path, field: str, reason: str) -> None:
    guard, _, meta, db, _ = make_guard(tmp_path)
    values = {
        "structure": meta.structure_hash,
        "views": meta.views_hash,
        "comments": meta.comments_hash,
    }
    values[field] = "x" * 64
    db.hashes = Hashes(**values)
    with pytest.raises(PackStale, match=reason):
        guard.check(db.execute)


def test_policy_or_overlay_change_is_stale_without_touching_the_database(tmp_path: Path) -> None:
    guard, _, _, db, _ = make_guard(tmp_path, policy_sha="outra")
    with pytest.raises(PackStale, match="politica"):
        guard.check(db.execute)
    guard2, _, _, db2, _ = make_guard(tmp_path / "b", overlay_sha="outro")
    with pytest.raises(PackStale, match="overlay"):
        guard2.check(db2.execute)
    assert (db.rehash_calls, db.probe_calls, db2.rehash_calls, db2.probe_calls) == (0, 0, 0, 0)


def test_database_failure_propagates_without_marking_stale(tmp_path: Path) -> None:
    guard, _, _, db, _ = make_guard(tmp_path)
    db.fail = DbError(DbErrorKind.LOST, "08S01", None)
    with pytest.raises(DbError):
        guard.check(db.execute)
    assert guard.stale_reason is None
    db.fail = None
    assert guard.check(db.execute).meta.owner == "bethadba"


def test_pack_switch_by_another_process_is_picked_up(tmp_path: Path) -> None:
    guard, store, meta, db, _ = make_guard(tmp_path)
    assert guard.check(db.execute).meta.version == meta.version
    changed = raw()
    changed["remarks"][3]["remarks"] = "Comentario de outro build"
    meta2 = publish(store, changed)
    assert guard.pack().meta.version == meta2.version
    db.hashes = Hashes(meta2.structure_hash, meta2.views_hash, meta2.comments_hash)
    before = db.rehash_calls
    guard.check(db.execute)
    assert db.rehash_calls == before + 1, "pack novo sempre passa por um re-hash completo"


def test_probe_sql_is_a_plain_select_on_catalog_views_without_modified_at() -> None:
    assert PROBE_SQL.startswith("SELECT ") and ";" not in PROBE_SQL
    assert "last_modified_at" not in PROBE_SQL
    for view in ("SYSTAB", "SYSTABCOL", "SYSFKEY", "SYSIDX", "SYSREMARK", "SYSVIEW"):
        assert f"SYS.{view}" in PROBE_SQL
    assert len(PROBE_KEYS) == 7


def test_read_probe_parses_text_numbers_and_rejects_odd_answers() -> None:
    def ok(sql: str, params: tuple[Any, ...] = (), **kw: Any) -> RawResult:
        return RawResult(
            (), [["5477", 63031, None, "12768", 61250, 256, "849538"]], False, 1, datetime.now(UTC)
        )

    assert read_probe(ok) == dict(
        zip(PROBE_KEYS, [5477, 63031, 0, 12768, 61250, 256, 849538], strict=True)
    )

    def short(sql: str, params: tuple[Any, ...] = (), **kw: Any) -> RawResult:
        return RawResult((), [[1, 2]], False, 1, datetime.now(UTC))

    with pytest.raises(PackStale):
        read_probe(short)

    def garbage(sql: str, params: tuple[Any, ...] = (), **kw: Any) -> RawResult:
        return RawResult((), [["a"] * 7], False, 1, datetime.now(UTC))

    with pytest.raises(PackStale):
        read_probe(garbage)


def test_make_rehasher_reads_the_whole_catalog_and_hashes_it() -> None:
    data = raw()
    from dominio_mcp.catalog import CATALOG_QUERIES

    by_sql = {sql: name for name, sql in CATALOG_QUERIES.items()}

    def executor(sql: str, params: tuple[Any, ...] = (), **kw: Any) -> RawResult:
        rows = data[by_sql[sql]]
        return RawResult(
            tuple(rows[0]), [list(r.values()) for r in rows], False, 1, datetime.now(UTC)
        )

    hashes = make_rehasher("bethadba")(executor)
    catalog = build_catalog(data)
    assert hashes == Hashes(catalog.structure_hash(), catalog.views_hash(), catalog.comments_hash())


def test_approved_views_parse_and_validate() -> None:
    sha = "ab" * 32
    ok = overlay_from_files(
        {"views_aprovadas.yaml": f"views:\n  - {{name: VW_Um, sha256: {sha}}}\n"}
    )
    assert approved_views(ok) == {"vw_um": sha}
    assert approved_views(overlay_from_files({})) == {}
    assert approved_views(load_overlay()) == {}
    for bad in (
        "views: x\n",
        "views:\n  - {name: v}\n",
        "views:\n  - {name: v, sha256: curto}\n",
        "views:\n  - {name: v, sha256: " + "zz" * 32 + "}\n",
    ):
        with pytest.raises(OverlayError):
            approved_views(overlay_from_files({"views_aprovadas.yaml": bad}))
