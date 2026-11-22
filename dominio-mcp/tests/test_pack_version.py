from __future__ import annotations

import copy
import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.catalog import Catalog, build_catalog
from dominio_mcp.overlay import Overlay, overlay_from_files
from dominio_mcp.pack import (
    Pack,
    PackError,
    PackMeta,
    PackStore,
    build_pack,
    sha256_text,
)
from dominio_mcp.policy import Policy, PolicyClass, load_policy
from dominio_mcp.readable import ReadableReport

FIXTURES = Path(__file__).parent / "fixtures"
POLICY = load_policy()
OVERLAY = overlay_from_files({"glossary.yaml": "faturamento: [vendas]\n"})


def raw(name: str = "mini_catalog.json") -> dict[str, list[dict[str, Any]]]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def build(
    tmp_path: Path,
    *,
    data: dict[str, list[dict[str, Any]]] | None = None,
    policy: Policy = POLICY,
    overlay: Overlay = OVERLAY,
    accepted: frozenset[tuple[str, str]] = frozenset(),
    approved: dict[str, str] | None = None,
    readable: ReadableReport | None = None,
    name: str = "p.sqlite3",
    built_at: datetime | None = None,
) -> PackMeta:
    catalog: Catalog = build_catalog(data if data is not None else raw())
    return build_pack(
        tmp_path / name,
        catalog=catalog,
        policy=policy,
        overlay=overlay,
        accepted=accepted,
        approved_views=approved,
        readable=readable,
        dsn="contabil",
        built_at=built_at,
    )


def test_same_inputs_same_version_regardless_of_build_time(tmp_path: Path) -> None:
    a = build(tmp_path, built_at=datetime(2026, 1, 1, tzinfo=UTC))
    b = build(tmp_path, name="q.sqlite3", built_at=datetime(2026, 6, 1, tzinfo=UTC))
    assert a.version == b.version
    assert a.built_at != b.built_at
    assert len(a.version) == 64 and a.short == a.version[:12]


def mutated(change: Any) -> dict[str, list[dict[str, Any]]]:
    data = copy.deepcopy(raw())
    change(data)
    return data


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d["views"][0].update(view_def="SELECT 1 AS codi_emp"),
        lambda d: d["foreign_keys"].pop(0),
        lambda d: d["remarks"][3].update(remarks="Outro texto"),
        lambda d: d["indexes"].pop(1),
        lambda d: d["columns"][8].update(type="varchar"),
        lambda d: d["columns"][8].update(width=18),
    ],
    ids=["view", "fk", "comentario", "indice", "tipo", "largura"],
)
def test_version_changes_with_view_fk_comment_index_type_width(tmp_path: Path, change: Any) -> None:
    base = build(tmp_path)
    assert build(tmp_path, data=mutated(change), name="q.sqlite3").version != base.version


def test_version_changes_with_policy_overlay_acceptance_and_readability(tmp_path: Path) -> None:
    base = build(tmp_path)
    other_policy = Policy.from_text("version: 1\ndenied_tables: [outra]\n")
    assert build(tmp_path, policy=other_policy, name="a.sqlite3").version != base.version
    other_overlay = overlay_from_files({"glossary.yaml": "faturamento: [venda]\n"})
    assert build(tmp_path, overlay=other_overlay, name="b.sqlite3").version != base.version
    accepted = frozenset({("geempre", "codi_emp")})
    assert build(tmp_path, accepted=accepted, name="c.sqlite3").version != base.version
    report = ReadableReport(frozenset({"geempre"}), {"efsaidas": "sem_permissao"}, True)
    assert build(tmp_path, readable=report, name="d.sqlite3").version != base.version


def test_pack_roundtrip_tables_columns_legends_and_classes(tmp_path: Path) -> None:
    accepted = frozenset(
        {("geempre", "codi_emp"), ("geempre", "nome_emp"), ("geempre", "tins_emp")}
    )
    meta = build(tmp_path, accepted=accepted)
    pack = Pack(tmp_path / "p.sqlite3")
    assert pack.meta == meta
    assert meta.counts["tables"] == 4 and meta.counts["foreign_keys"] == 2
    assert pack.accepted() == accepted
    geempre = pack.table("GEEMPRE")
    assert geempre is not None and geempre.module == "ge" and geempre.pk == ("codi_emp",)
    assert geempre.queryable is True and geempre.blocked_reason is None
    cols = {c.key: c for c in pack.columns("geempre")}
    assert cols["cgce_emp"].klass is PolicyClass.DOCUMENTO
    assert cols["nome_emp"].klass is PolicyClass.NORMAL
    assert cols["dina_emp"].klass is PolicyClass.NAO_CLASSIFICADA
    assert cols["tins_emp"].legend == "1=CNPJ; 2=CPF"
    assert cols["codi_emp"].in_pk is True
    efsaidas = {c.key: c for c in pack.columns("efsaidas")}
    assert efsaidas["codi_emp"].in_fk is True
    assert pack.indexes("efsaidas")[0][0] in {"IDX_DATA_SAI", "efsaidas", "fk_efsaidas_geempre"}
    assert {(f.child, f.parent) for f in pack.foreign_keys()} == {
        ("efsaidas", "geempre"),
        ("efmvspro", "efsaidas"),
    }
    assert pack.table("nao_existe") is None


def test_unreadable_and_unapproved_objects_are_described_but_not_queryable(tmp_path: Path) -> None:
    report = ReadableReport(
        frozenset({"geempre", "efmvspro", "vw_saidas"}), {"efsaidas": "sem_permissao"}, True
    )
    build(tmp_path, readable=report)
    pack = Pack(tmp_path / "p.sqlite3")
    efsaidas = pack.table("efsaidas")
    assert efsaidas is not None
    assert (efsaidas.readable, efsaidas.queryable) == (False, False)
    assert efsaidas.blocked_reason == "ilegivel:sem_permissao"
    view = pack.table("vw_saidas")
    assert view is not None and view.blocked_reason == "view_nao_aprovada"
    assert view.queryable is False


def test_view_becomes_queryable_only_with_the_exact_definition_hash(tmp_path: Path) -> None:
    definition = raw()["views"][0]["view_def"]
    build(tmp_path, approved={"vw_saidas": sha256_text(definition)})
    view = Pack(tmp_path / "p.sqlite3").table("vw_saidas")
    assert view is not None and view.queryable is True and view.view_sha == sha256_text(definition)
    build(tmp_path, approved={"vw_saidas": sha256_text(definition + " ")}, name="q.sqlite3")
    stale = Pack(tmp_path / "q.sqlite3").table("vw_saidas")
    assert stale is not None and stale.queryable is False


def test_comments_of_secret_columns_and_tables_are_never_stored(tmp_path: Path) -> None:
    build(tmp_path, data=raw("synthetic_catalog.json"))
    blob = (tmp_path / "p.sqlite3").read_bytes().lower()
    assert b"marker" not in blob
    pack = Pack(tmp_path / "p.sqlite3")
    secret = pack.column("geempre", "senha_modulo_web")
    assert secret is not None and secret.klass is PolicyClass.SEGREDO and secret.comment is None
    denied = pack.table("gecertificadosdigitais")
    assert denied is not None and denied.comment is None
    assert denied.blocked_reason == "tabela_de_credencial"


def test_store_publishes_atomically_and_switches_the_pointer(tmp_path: Path) -> None:
    store = PackStore(tmp_path / "packs", keep=2)
    assert store.current_path() is None and store.open_current() is None
    built = store.new_build_path()
    meta = build_pack(
        built, catalog=build_catalog(raw()), policy=POLICY, overlay=OVERLAY, dsn="contabil"
    )
    first = store.publish(built, meta)
    assert first.name == f"pack-{meta.short}.sqlite3" and not built.exists()
    opened = store.open_current()
    assert opened is not None and opened.meta.version == meta.version
    opened.close()

    changed = mutated(lambda d: d["remarks"][3].update(remarks="Outro"))
    built2 = store.new_build_path()
    meta2 = build_pack(
        built2, catalog=build_catalog(changed), policy=POLICY, overlay=OVERLAY, dsn="contabil"
    )
    second = store.publish(built2, meta2)
    current = store.open_current()
    assert current is not None and current.meta.version == meta2.version
    current.close()
    assert first.exists() and second.exists()


def test_store_republishing_the_same_version_keeps_the_open_file(tmp_path: Path) -> None:
    store = PackStore(tmp_path / "packs")
    for _ in range(2):
        built = store.new_build_path()
        meta = build_pack(
            built, catalog=build_catalog(raw()), policy=POLICY, overlay=OVERLAY, dsn="contabil"
        )
        store.publish(built, meta)
        assert not built.exists()
    assert len(list((tmp_path / "packs").glob("pack-*.sqlite3"))) == 1


def test_store_keeps_only_the_newest_packs(tmp_path: Path) -> None:
    store = PackStore(tmp_path / "packs", keep=2)
    versions = []
    for i in range(4):
        data = mutated(lambda d, i=i: d["remarks"][3].update(remarks=f"Texto {i}"))
        built = store.new_build_path()
        meta = build_pack(
            built, catalog=build_catalog(data), policy=POLICY, overlay=OVERLAY, dsn="contabil"
        )
        store.publish(built, meta)
        versions.append(meta.short)
    left = sorted(p.name for p in (tmp_path / "packs").glob("pack-*.sqlite3"))
    assert len(left) == 2
    assert f"pack-{versions[-1]}.sqlite3" in left


def test_corrupt_pointer_or_foreign_format_is_refused(tmp_path: Path) -> None:
    store = PackStore(tmp_path / "packs")
    (tmp_path / "packs").mkdir()
    store.pointer.write_text("nao json", encoding="utf-8")
    assert store.current_path() is None
    foreign = tmp_path / "foreign.sqlite3"
    conn = sqlite3.connect(foreign)
    conn.execute("PRAGMA user_version = 99")
    conn.execute("CREATE TABLE meta (key TEXT, value TEXT)")
    conn.commit()
    conn.close()
    with pytest.raises(PackError, match="formato"):
        Pack(foreign)
    with pytest.raises(PackError):
        Pack(tmp_path / "ausente.sqlite3")
