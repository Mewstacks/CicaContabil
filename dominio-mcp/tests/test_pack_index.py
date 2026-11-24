from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dominio_mcp.catalog import Catalog, Column, ForeignKey, Table, build_catalog
from dominio_mcp.overlay import overlay_from_files
from dominio_mcp.pack import Pack, build_pack
from dominio_mcp.policy import load_policy
from dominio_mcp.readable import ReadableReport
from dominio_mcp.textnorm import index_text

FIXTURES = Path(__file__).parent / "fixtures"
POLICY = load_policy()
OVERLAY = overlay_from_files({})


def make_pack(tmp_path: Path, catalog: Catalog, **kw: Any) -> Pack:
    build_pack(tmp_path / "p.sqlite3", catalog=catalog, policy=POLICY, overlay=OVERLAY, **kw)
    return Pack(tmp_path / "p.sqlite3")


def mini() -> Catalog:
    return build_catalog(json.loads((FIXTURES / "mini_catalog.json").read_text(encoding="utf-8")))


def keys(rows: list[tuple[Any, ...]]) -> list[str]:
    return [r[0] for r in rows]


def test_fts_finds_tables_by_comment_and_by_column_text(tmp_path: Path) -> None:
    pack = make_pack(tmp_path, mini())
    by_comment = keys(
        pack.query("SELECT table_key FROM fts_tables WHERE fts_tables MATCH 'saida' ORDER BY rank")
    )
    assert "efsaidas" in by_comment and "efmvspro" in by_comment
    by_column = keys(
        pack.query("SELECT table_key FROM fts_tables WHERE fts_tables MATCH 'contabil'")
    )
    assert by_column == ["efsaidas"]


def test_fts_ignores_accents_both_ways(tmp_path: Path) -> None:
    table = Table(
        name="ctlancto",
        kind="BASE",
        approx_rows=10,
        comment="Lançamentos contábeis",
        columns=(Column("codi_emp", 1, "integer", 4, 0, False, None),),
        primary_key=("codi_emp",),
        indexes=(),
        view_definition=None,
    )
    pack = make_pack(tmp_path, Catalog("bethadba", {"ctlancto": table}, ()))
    for term in ("lancamentos", "contabeis", "lançamentos"):
        hits = keys(
            pack.query(
                "SELECT table_key FROM fts_tables WHERE fts_tables MATCH ?", (index_text(term),)
            )
        )
        assert hits == ["ctlancto"], term


def test_trigram_matches_pieces_of_table_and_column_names(tmp_path: Path) -> None:
    pack = make_pack(tmp_path, mini())
    tables = keys(pack.query("SELECT table_key FROM tri_tables WHERE tri_tables MATCH 'efsaid'"))
    assert tables == ["efsaidas"]
    cols = pack.query(
        "SELECT table_key, column_key FROM tri_columns WHERE tri_columns MATCH 'vcon'"
    )
    assert cols == [("efsaidas", "vcon_sai")]
    upper = keys(pack.query("SELECT table_key FROM tri_tables WHERE tri_tables MATCH 'MVSPRO'"))
    assert upper == ["efmvspro"]


def test_credential_tables_and_secret_columns_are_not_searchable(tmp_path: Path) -> None:
    data = json.loads((FIXTURES / "synthetic_catalog.json").read_text(encoding="utf-8"))
    pack = make_pack(tmp_path, build_catalog(data))
    for table in ("fts_tables", "tri_tables", "features"):
        assert pack.query(f"SELECT 1 FROM {table} WHERE table_key = 'gecertificadosdigitais'") == []  # noqa: S608
    assert pack.query("SELECT 1 FROM tri_columns WHERE column_key = 'senha_modulo_web'") == []
    hits = pack.query("SELECT table_key FROM fts_tables WHERE fts_tables MATCH 'senha'")
    assert hits == []


def test_features_carry_the_structural_prior(tmp_path: Path) -> None:
    pack = make_pack(tmp_path, mini())
    rows = {
        r[0]: r
        for r in pack.query(
            "SELECT table_key, fk_in, fk_out, rows, ncols, name_len, parts, module, kind "
            "FROM features"
        )
    }
    assert rows["geempre"][1:3] == (1, 0)
    assert rows["efsaidas"][1:3] == (1, 1)
    assert rows["efmvspro"][1:3] == (0, 1)
    assert rows["efsaidas"][3:5] == (386290, 5)
    assert rows["efmvspro"][5:7] == (8, 1)
    assert rows["geempre"][7:] == ("ge", "BASE")
    assert rows["vw_saidas"][8] == "VIEW"


def test_hub_table_counts_every_foreign_key_that_points_to_it(tmp_path: Path) -> None:
    id_col = (Column("id", 1, "integer", 4, 0, False, None),)
    parent = Table("pai", "BASE", 5, None, id_col, ("id",), (), None)
    child_cols = (Column("pai_id", 1, "integer", 4, 0, False, None),)
    children = {
        f"filho{i}": Table(f"filho{i}", "BASE", 1, None, child_cols, (), (), None) for i in range(3)
    }
    fks = tuple(ForeignKey(f"filho{i}", ("pai_id",), "pai", ("id",)) for i in range(3))
    pack = make_pack(tmp_path, Catalog("bethadba", {"pai": parent, **children}, fks))
    rows = dict(pack.query("SELECT table_key, fk_in FROM features"))
    assert rows["pai"] == 3
    assert rows["filho0"] == 0


def test_unreadable_tables_stay_searchable(tmp_path: Path) -> None:
    report = ReadableReport(frozenset({"geempre"}), {"efsaidas": "sem_permissao"}, True)
    pack = make_pack(tmp_path, mini(), readable=report)
    hits = keys(
        pack.query(
            "SELECT table_key FROM fts_tables WHERE fts_tables MATCH ?",
            (index_text("notas fiscais"),),
        )
    )
    assert hits == ["efsaidas"]
    row = pack.table("efsaidas")
    assert row is not None and row.queryable is False


def test_name_tokens_drop_the_module_prefix_and_keep_the_stemmed_parts() -> None:
    from dominio_mcp.pack_index import count_children, name_tokens

    assert name_tokens("efsaidas") == "saida efsaida"
    assert name_tokens("EFMVSPRO_APURACAO_ESTOQUE") == "mvspro apuracao estoque efmvspro"
    assert name_tokens("ct") == "ct"
    names = {"efmvspro", "efmvspro_apuracao", "efmvspro_apuracao_estoque", "efsaidas", "solto_x"}
    kids = count_children(names)
    assert kids == {"efmvspro": 1, "efmvspro_apuracao": 1}


def test_business_word_matches_a_table_through_its_name_without_prefix(tmp_path: Path) -> None:
    pack = make_pack(tmp_path, mini())
    hits = keys(pack.query("SELECT table_key FROM fts_tables WHERE fts_tables MATCH 'saida'"))
    assert "efsaidas" in hits


def test_child_tables_are_counted_in_features(tmp_path: Path) -> None:
    id_col = (Column("id", 1, "integer", 4, 0, False, None),)

    def tbl(name: str) -> Table:
        return Table(name, "BASE", 1, None, id_col, ("id",), (), None)

    catalog = Catalog("bethadba", {n: tbl(n) for n in ("efsaidas", "efsaidas_itens", "outra")}, ())
    pack = make_pack(tmp_path, catalog)
    kids = dict(pack.query("SELECT table_key, kids FROM features"))
    assert kids == {"efsaidas": 1, "efsaidas_itens": 0, "outra": 0}
