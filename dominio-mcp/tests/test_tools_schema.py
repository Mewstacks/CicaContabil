from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.catalog import Catalog, build_catalog
from dominio_mcp.overlay import Overlay, load_overlay, overlay_from_files
from dominio_mcp.pack import Pack, build_pack
from dominio_mcp.policy import load_policy
from dominio_mcp.tools_schema import MAP_BYTES, MAX_BYTES, SchemaTools, ToolError, size_of
from packs import build_demo_pack, col, table

FIXTURES = Path(__file__).parent / "fixtures"

LEGENDS = """
version: 1
legends:
  geempre.nome_emp:
    confianca: confirmada
    valores: {1: Um, 2: Dois}
warnings:
  - pattern: '^situ_'
    aviso: "Aviso de teste: coluna situ_ nao confiavel."
"""
CORE = """
version: 1
tables:
  - {name: geempre, titulo: Empresas, aliases: [empresa, empresas]}
  - {name: efsaidas, titulo: Notas de saida, aliases: [nota de saida]}
"""
MODULES = """
version: 1
modules:
  ef: {nome: Escrita fiscal, descricao: x, confianca: inferida}
  ge: {nome: Cadastros gerais, descricao: y, confianca: inferida}
"""


def overlay() -> Overlay:
    return overlay_from_files(
        {"legends.yaml": LEGENDS, "core_tables.yaml": CORE, "modules.yaml": MODULES}
    )


def tools(pack: Pack, *, stale: str | None = None, ov: Overlay | None = None) -> SchemaTools:
    return SchemaTools(lambda: pack, lambda: stale, ov or overlay())


@pytest.fixture
def pack(tmp_path: Path) -> Pack:
    return build_demo_pack(tmp_path)


def flat(body: dict[str, Any]) -> str:
    return json.dumps(body, ensure_ascii=False)


def test_map_is_small_and_points_to_the_next_tools(pack: Pack) -> None:
    body = tools(pack).mapa_do_banco()
    assert size_of(body) <= MAP_BYTES
    assert body["pack"]["versao"] == pack.meta.short and "desatualizado" not in body["pack"]
    assert {m["prefixo"] for m in body["modulos"]} == {"ef", "ge"}
    assert body["centrais"][0]["tabela"] == "efsaidas"
    assert any("buscar_esquema" in line for line in body["como_usar"])
    assert "gecertificadosdigitais" not in flat(body)


def test_map_reports_a_stale_pack(pack: Pack) -> None:
    body = tools(pack, stale="a estrutura do banco mudou").mapa_do_banco()
    assert body["pack"]["desatualizado"] == "a estrutura do banco mudou"


def test_search_returns_compact_cards_with_source_and_confidence(pack: Pack) -> None:
    body = tools(pack).buscar_esquema("notas de saida")
    first = body["resultados"][0]
    assert first["tabela"] == "efsaidas" and first["titulo"] == "Notas de saida"
    assert first["fonte"] == "overlay" and first["confianca"] == "media"
    assert first["consultavel"] is True and first["modulo"] == "ef"
    assert body["proximo_passo"].startswith("descrever_tabela")
    assert all(len(flat(card)) < 600 for card in body["resultados"])
    assert len(tools(pack).buscar_esquema("empresas", limite=50)["resultados"]) <= 8


def test_search_refuses_empty_queries_and_hides_credential_tables(pack: Pack) -> None:
    with pytest.raises(ToolError) as exc:
        tools(pack).buscar_esquema("   ")
    assert exc.value.code == "consulta_vazia"
    out = tools(pack).buscar_esquema("certificados digitais gecertificadosdigitais")
    assert "gecertificadosdigitais" not in flat(out)
    nothing = tools(pack).buscar_esquema("zzzzqqqq")
    assert nothing["resultados"] == [] and "nenhuma tabela" in nothing["proximo_passo"]


def test_unqueryable_objects_are_findable_but_flagged(pack: Pack) -> None:
    body = tools(pack).buscar_esquema("vw totais visao")
    view = next((c for c in body["resultados"] if c["tabela"] == "vw_totais"), None)
    assert view is not None and view["consultavel"] is False
    assert view["motivo_bloqueio"] == "view_nao_aprovada" and view["tipo"] == "VIEW"


def test_describe_table_orders_keys_first_and_marks_classes(pack: Pack) -> None:
    body = tools(pack).descrever_tabela("EFSAIDAS")
    names = [c["nome"] for c in body["colunas"]["itens"]]
    assert names[:3] == ["codi_emp", "codi_sai", "seg_sai"]
    assert body["chave_primaria"] == ["codi_emp", "codi_sai", "seg_sai"]
    assert body["referencia"] == [{"para": "geempre", "colunas": ["codi_emp->codi_emp"]}]
    assert body["referenciada_por"][0]["de"] == "efmvspro"
    assert body["indices"][0]["nome"] == "IDX_DATA_SAI"
    by_name = {c["nome"]: c for c in body["colunas"]["itens"]}
    assert by_name["codi_emp"]["chave"] == "pk" and "classe" not in by_name["vcon_sai"]
    assert by_name["obs_sai"]["classe"] == "texto_livre"
    assert by_name["cgce_cli"]["classe"] == "documento"
    assert by_name["situ_sai"]["aviso"].startswith("Aviso de teste")
    assert by_name["situ_sai"]["legenda"] == "1=Normal; 2=Cancelada"
    assert by_name["situ_sai"]["legenda_confianca"] == "media"
    assert body["fonte"] == "overlay" and body["titulo"] == "Notas de saida"


def test_overlay_legend_beats_the_database_comment(pack: Pack) -> None:
    body = tools(pack).descrever_tabela("geempre")
    nome = next(c for c in body["colunas"]["itens"] if c["nome"] == "nome_emp")
    assert nome["legenda"] == "1=Um; 2=Dois" and nome["legenda_confianca"] == "confirmada"


def test_personal_columns_are_flagged_blocked_with_the_reason(pack: Pack) -> None:
    body = tools(pack).descrever_tabela("foempregados")
    by_name = {c["nome"]: c for c in body["colunas"]["itens"]}
    assert by_name["salario"]["classe"] == "pessoal:folha"
    assert by_name["nome"]["classe"] == "pessoal:nome"


def test_credential_tables_and_unknown_tables(pack: Pack) -> None:
    assert tools(pack).descrever_tabela("gecertificadosdigitais") == {
        "tabela": "gecertificadosdigitais",
        "bloqueada": True,
        "motivo": "politica de dados",
    }
    with pytest.raises(ToolError) as exc:
        tools(pack).descrever_tabela("nao_existe")
    assert exc.value.code == "tabela_desconhecida"
    unapproved = tools(pack).descrever_tabela("vw_totais")
    assert (
        unapproved["consultavel"] is False and unapproved["motivo_bloqueio"] == "view_nao_aprovada"
    )


def test_secret_columns_appear_blocked_without_comment_or_type(tmp_path: Path) -> None:
    data = json.loads((FIXTURES / "synthetic_catalog.json").read_text(encoding="utf-8"))
    build_pack(
        tmp_path / "s.sqlite3",
        catalog=build_catalog(data),
        policy=load_policy(),
        overlay=overlay_from_files({}),
    )
    synthetic = Pack(tmp_path / "s.sqlite3")
    body = tools(synthetic, ov=overlay_from_files({})).descrever_tabela("geempre")
    secret = next(c for c in body["colunas"]["itens"] if c["nome"] == "senha_modulo_web")
    assert secret == {"nome": "senha_modulo_web", "classe": "segredo", "bloqueada": True}


def test_planted_markers_never_leave_any_l0_tool(tmp_path: Path) -> None:
    data = json.loads((FIXTURES / "synthetic_catalog.json").read_text(encoding="utf-8"))
    build_pack(
        tmp_path / "s.sqlite3",
        catalog=build_catalog(data),
        policy=load_policy(),
        overlay=overlay_from_files({}),
    )
    synthetic = Pack(tmp_path / "s.sqlite3")
    t = tools(synthetic, ov=overlay_from_files({}))
    outputs = [flat(t.mapa_do_banco())]
    for name in (
        "geempre",
        "audados",
        "gecertificadosdigitais",
        "efobservacoes",
        "vw_dados",
        "efnovas",
    ):
        outputs.append(flat(t.descrever_tabela(name)))
    for query in ("senha", "certificado", "comentario secreto", "observacao livre", "auditoria"):
        outputs.append(flat(t.buscar_esquema(query)))
    for column in ("senha_modulo_web", "nome_emp"):
        try:
            outputs.append(flat(t.valores_do_campo("geempre", column)))
        except ToolError as exc:
            outputs.append(exc.message)
    assert "marker" not in "".join(outputs).lower()


def test_table_with_657_columns_still_fits_in_12_kb_and_pages(tmp_path: Path) -> None:
    wide = table(
        "EFPARAMETRO_VIGENCIA",
        [col(f"coluna_numero_{i:03d}", "varchar", 60, "x" * 150) for i in range(657)],
        ("coluna_numero_000",),
        1301,
    )
    catalog = Catalog("bethadba", {wide.key: wide}, ())
    build_pack(
        tmp_path / "w.sqlite3",
        catalog=catalog,
        policy=load_policy(),
        overlay=overlay_from_files({}),
        accepted=frozenset((wide.key, c.name.lower()) for c in wide.columns),
    )
    pack = Pack(tmp_path / "w.sqlite3")
    t = tools(pack, ov=overlay_from_files({}))
    first = t.descrever_tabela("efparametro_vigencia")
    assert size_of(first) <= MAX_BYTES
    assert first["colunas"]["total"] == 657 and len(first["colunas"]["itens"]) >= 1
    assert "pagina=2" in first["proximo_passo"]
    seen = {c["nome"] for c in first["colunas"]["itens"]}
    page = 2
    while page <= 17:
        body = t.descrever_tabela("efparametro_vigencia", pagina=page)
        assert size_of(body) <= MAX_BYTES
        seen |= {c["nome"] for c in body["colunas"]["itens"]}
        page += 1
    assert len(seen) >= 600
    assert t.descrever_tabela("efparametro_vigencia", pagina=999)["colunas"]["itens"] == []


def test_join_path_and_its_absence(pack: Pack) -> None:
    ok = tools(pack).caminho_entre_tabelas("efmvspro", "geempre")
    assert ok["saltos"] == 2
    assert [(s["de"], s["para"], s["relacao"]) for s in ok["caminho"]] == [
        ("efmvspro", "efsaidas", "muitos_para_um"),
        ("efsaidas", "geempre", "muitos_para_um"),
    ]
    assert ok["caminho"][0]["colunas"][0] == "codi_emp = codi_emp"
    none = tools(pack).caminho_entre_tabelas("efsaidas", "efclientes")
    assert none["caminho"] is None and "multiplica linhas" in none["motivo"]
    with pytest.raises(ToolError):
        tools(pack).caminho_entre_tabelas("efsaidas", "nao_existe")


def test_field_values_come_from_legends_and_never_from_the_database(pack: Pack) -> None:
    with_legend = tools(pack).valores_do_campo("efsaidas", "situ_sai")
    assert with_legend["legenda"] == "1=Normal; 2=Cancelada" and with_legend["fonte"] == (
        "comentario_do_banco"
    )
    assert "aviso" in with_legend
    from_overlay = tools(pack).valores_do_campo("geempre", "nome_emp")
    assert from_overlay["fonte"] == "overlay" and from_overlay["confianca"] == "confirmada"
    no_legend = tools(pack).valores_do_campo("efsaidas", "vcon_sai")
    assert no_legend["legenda"] is None if "legenda" in no_legend else True
    assert "consulta_estruturada" in no_legend["proximo_passo"]
    with pytest.raises(ToolError):
        tools(pack).valores_do_campo("efsaidas", "coluna_que_nao_existe")


def test_shipped_overlay_loads_into_the_tools(pack: Pack) -> None:
    t = tools(pack, ov=load_overlay())
    assert t.mapa_do_banco()["pack"]["versao"] == pack.meta.short
    assert t.buscar_esquema("empresas")["resultados"][0]["tabela"] == "geempre"
