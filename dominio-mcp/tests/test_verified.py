from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.config import Limits, Settings, load_settings
from dominio_mcp.executor import QueryEngine
from dominio_mcp.odbc import build_session
from dominio_mcp.overlay import load_overlay, overlay_from_files
from dominio_mcp.pack import Pack, pack_store_for
from dominio_mcp.policy import PolicyClass
from dominio_mcp.query_spec import QueryRefused
from dominio_mcp.verified import (
    ToolDisabled,
    VerifiedError,
    VerifiedRunner,
    assemble,
    load_shipped_tools,
    parse_tool,
    render_literal,
    tool_status,
)
from fake_odbc import Rows
from packs import build_demo_pack
from qhelp import POLICY

PLANS = Path(__file__).parent / "fixtures" / "plans"
CHEAP = (PLANS / "full_scan.txt").read_text(encoding="utf-8")

TOOL = """
version: 1
name: empresas_teste
titulo: Empresas de teste
descricao: Lista empresas
aviso: Diagnostico.
parametros:
  - {nome: situacao, tipo: choice, valores: [A, I]}
  - {nome: codi_emp, tipo: int}
  - {nome: limite, tipo: int, padrao: 2, minimo: 1, maximo: 10}
dependencias:
  geempre: {codi_emp: normal, nome_emp: normal, cgce_emp: documento}
sql: >-
  SELECT TOP {top} g.codi_emp AS codi_emp, g.nome_emp AS nome, g.cgce_emp AS cnpj
  FROM bethadba.geempre g WHERE 1 = 1
  {?situacao: AND g.nome_emp = ?situacao} {?codi_emp: AND g.codi_emp = ?codi_emp}
  ORDER BY g.codi_emp
saidas:
  - {nome: codi_emp, tipo: int, classe: normal}
  - {nome: nome, tipo: text, classe: normal, legenda: {tabela: geempre, coluna: cgce_emp}}
  - {nome: cnpj, tipo: text, classe: documento}
"""


class Guard:
    def __init__(self, pack: Pack) -> None:
        self.pack = pack

    def precheck(self) -> Pack:
        return self.pack

    def check(self, execute: Any) -> Pack:
        return self.pack


def runner(
    tmp_path: Path, tool_text: str = TOOL, **settings: Any
) -> tuple[VerifiedRunner, Any, Pack]:
    from fake_odbc import FakeDriver

    pack = build_demo_pack(tmp_path)
    cfg = Settings(dsn="contabil", home=tmp_path, limits=Limits(), **settings)
    driver = FakeDriver()
    session = build_session(cfg, driver=driver, lock_wait_seconds=0.3)
    engine = QueryEngine(settings=cfg, policy=POLICY, guard=Guard(pack), session=session)
    tool = parse_tool(tool_text)
    return VerifiedRunner(engine, {tool.name: tool}, overlay_from_files({})), driver, pack


def test_shipped_tools_parse_with_their_contract() -> None:
    tools = load_shipped_tools()
    assert set(tools) == {"empresas", "empresa_perfil", "movimento_fiscal", "conferir_numeracao"}
    assert tools["conferir_numeracao"].variant_param == "documento"
    assert set(tools["conferir_numeracao"].variants) == {"saidas", "servicos"}
    assert tools["movimento_fiscal"].janela == ("inicio", "fim")
    for tool in tools.values():
        assert tool.aviso and tool.sql_hash and tool.saidas
        for variant in tool.variants.values():
            sql, names = assemble(variant.sql, {p.nome: 1 for p in tool.params}, 11)
            assert sql.count("?") == len(names) and "{" not in sql and ";" not in sql
            assert sql.lstrip().upper().startswith("SELECT")
            assert all(n in {p.nome for p in tool.params} for n in names)


def test_template_language_binds_names_in_order_and_drops_unused_blocks() -> None:
    sql = "SELECT TOP {top} x WHERE a = ?a {?b: AND b = ?b} {?c: AND c = ?c} AND d = ?a"
    text, names = assemble(sql, {"a": 1, "b": 2}, 51)
    assert text == "SELECT TOP 51 x WHERE a = ?  AND b = ?  AND d = ?"
    assert names == ["a", "b", "a"]
    text2, names2 = assemble(sql, {"a": 1}, 6)
    assert names2 == ["a", "a"] and "AND b" not in text2


def test_literal_rendering_is_typed_and_quote_safe() -> None:
    import datetime

    out = render_literal(
        "WHERE a = ? AND b = ? AND c = ?",
        ["codi", "texto", "dia"],
        {"codi": "int", "texto": "text", "dia": "date"},
        {"codi": 5, "texto": "O'Brien", "dia": datetime.date(2026, 1, 2)},
    )
    assert out == "WHERE a = 5 AND b = 'O''Brien' AND c = '2026-01-02'"
    with pytest.raises(VerifiedError):
        render_literal("a = ?", [], {}, {})


@pytest.mark.parametrize(
    "broken",
    ["nome: x\n", "- lista\n", "{", TOOL.replace("tipo: choice", "tipo: coisa", 1)],
)
def test_malformed_tool_files_are_errors(broken: str) -> None:
    with pytest.raises(VerifiedError):
        parse_tool(broken)


def test_run_binds_parameters_estimates_cost_and_shapes(tmp_path: Path) -> None:
    runr, driver, _ = runner(tmp_path)
    driver.server.script += [
        Rows(["plan"], [(CHEAP,)]),
        Rows(
            ["codi_emp", "nome", "cnpj"],
            [(1, "ACME ", "11222333000181"), (2, "BETA", "52998224725"), (3, "X", None)],
        ),
    ]
    out = runr.run("empresas_teste", {"codi_emp": 1})
    assert out["colunas"] == ["codi_emp", "nome", "cnpj"]
    assert out["linhas"][1][2] == "529.***.***-25"
    assert out["truncado"] is True and out["consulta"].startswith("empresas_teste v1 (")
    assert out["aviso"] == "Diagnostico." and "legendas" not in out
    _plan_sql, plan_params = next(
        (s, p) for s, p in driver.server.log if s.startswith("SELECT PLAN")
    )
    assert "g.codi_emp = 1" in plan_params[0] and "?" not in plan_params[0]
    data = next((s, p) for s, p in driver.server.log if s.startswith("SELECT TOP"))
    assert data[0].startswith("SELECT TOP 3 ") and data[1] == (1,)


def test_parameter_validation(tmp_path: Path) -> None:
    runr, *_ = runner(tmp_path)
    cases = [
        ({"situacao": "Z"}, "parametro_invalido"),
        ({"codi_emp": "abc"}, "parametro_invalido"),
        ({"limite": 0}, "parametro_invalido"),
        ({"limite": 11}, "parametro_invalido"),
        ({"coisa": 1}, "parametro_desconhecido"),
    ]
    for args, code in cases:
        with pytest.raises(QueryRefused) as exc:
            runr.run("empresas_teste", args)
        assert exc.value.code == code
    with pytest.raises(QueryRefused) as exc2:
        runr.run("nao_existe", {})
    assert exc2.value.code == "ferramenta_desconhecida"


WINDOW_TOOL = TOOL.replace(
    "  - {nome: limite, tipo: int, padrao: 2, minimo: 1, maximo: 10}",
    "  - {nome: inicio, tipo: date}\n  - {nome: fim, tipo: date}\n"
    "  - {nome: limite, tipo: int, padrao: 2, minimo: 1, maximo: 10}",
).replace("saidas:\n", "janela: {inicio: inicio, fim: fim}\nsaidas:\n", 1)


def test_date_window_is_required_closed_and_at_most_13_months(tmp_path: Path) -> None:
    runr, *_ = runner(tmp_path, WINDOW_TOOL)
    cases = [
        ({}, "janela_invalida"),
        ({"inicio": "2025-01-01"}, "janela_invalida"),
        ({"inicio": "2025-02-01", "fim": "2025-01-01"}, "janela_invalida"),
        ({"inicio": "2024-01-01", "fim": "2025-12-31"}, "janela_de_datas_longa"),
        ({"inicio": "2025-13-01", "fim": "2025-12-31"}, "parametro_invalido"),
    ]
    for args, code in cases:
        with pytest.raises(QueryRefused) as exc:
            runr.run("empresas_teste", args)
        assert exc.value.code == code


def test_required_parameters(tmp_path: Path) -> None:
    text = TOOL.replace(
        "{nome: codi_emp, tipo: int}", "{nome: codi_emp, tipo: int, obrigatorio: true}"
    )
    runr, *_ = runner(tmp_path, text)
    with pytest.raises(QueryRefused) as exc:
        runr.run("empresas_teste", {})
    assert exc.value.code == "parametro_ausente"


def test_value_that_cannot_be_encoded_is_refused(tmp_path: Path) -> None:
    text = TOOL.replace("tipo: choice, valores: [A, I]", "tipo: text")
    runr, *_ = runner(tmp_path, text)
    with pytest.raises(QueryRefused) as exc:
        runr.run("empresas_teste", {"situacao": "a\\b"})
    assert exc.value.code in {"valor_nao_codificavel", "parametro_invalido"}


def test_tool_is_disabled_with_a_reason_when_the_schema_drifts(tmp_path: Path) -> None:
    pack = build_demo_pack(tmp_path)
    tool = parse_tool(TOOL)
    assert tool_status(tool, pack, frozenset()) is None
    missing_table = parse_tool(TOOL.replace("geempre: {codi_emp", "tabela_que_sumiu: {codi_emp"))
    assert "nao existe mais" in (tool_status(missing_table, pack, frozenset()) or "")
    missing_col = parse_tool(TOOL.replace("nome_emp: normal", "coluna_que_sumiu: normal"))
    assert "coluna" in (tool_status(missing_col, pack, frozenset()) or "")
    stricter = parse_tool(TOOL.replace("cgce_emp: documento", "cgce_emp: normal"))
    assert "mais restrita" in (tool_status(stricter, pack, frozenset()) or "")
    secret = parse_tool(
        TOOL.replace("geempre: {codi_emp: normal", "gecertificadosdigitais: {codi_emp: normal")
    )
    assert "bloqueada" in (tool_status(secret, pack, frozenset()) or "")
    personal = parse_tool(TOOL.replace("nome_emp: normal", "ende_emp: pessoal"))
    assert tool_status(personal, pack, frozenset()) is not None
    assert tool_status(personal, pack, frozenset({"endereco"})) is None


def test_unaccepted_columns_are_accepted_by_a_curated_tool(tmp_path: Path) -> None:
    pack = build_demo_pack(tmp_path, accept_all=False)
    assert pack.column("geempre", "nome_emp").klass is PolicyClass.NAO_CLASSIFICADA  # type: ignore[union-attr]
    assert tool_status(parse_tool(TOOL), pack, frozenset()) is None


def test_disabled_tool_refuses_to_run_without_touching_the_database(tmp_path: Path) -> None:
    text = TOOL.replace("geempre: {codi_emp", "tabela_que_sumiu: {codi_emp")
    runr, driver, _ = runner(tmp_path, text)
    with pytest.raises(ToolDisabled) as exc:
        runr.run("empresas_teste", {})
    assert "nao existe mais" in exc.value.reason and driver.server.log == []
    assert "nao existe mais" in (runr.status("empresas_teste") or "")


def test_legends_come_from_the_pack_comment_and_from_the_overlay(tmp_path: Path) -> None:
    text = TOOL.replace(
        "legenda: {tabela: geempre, coluna: cgce_emp}", "legenda: {overlay: geempre.codi_emp}"
    )
    overlay = overlay_from_files(
        {
            "legends.yaml": (
                "legends:\n  geempre.codi_emp:\n    confianca: inferida\n"
                "    valores: {1: Um, 2: Dois}\n"
            )
        }
    )
    runr, driver, _pack = runner(tmp_path, text)
    runr._legends = overlay.data("legends.yaml")["legends"]
    driver.server.script += [Rows(["plan"], [(CHEAP,)]), Rows(["a", "b", "c"], [(1, "x", None)])]
    out = runr.run("empresas_teste", {})
    assert out["legendas"] == {"nome": "1=Um; 2=Dois (inferida)"}


def test_shipped_tools_against_the_real_pack_if_present() -> None:
    pack = pack_store_for(load_settings()).open_current()
    if pack is None:
        pytest.skip("sem pack real")
    states = {
        name: tool_status(tool, pack, frozenset()) for name, tool in load_shipped_tools().items()
    }
    assert states == dict.fromkeys(states), states
    assert load_overlay().data("legends.yaml")["legends"]["efparametro_vigencia.rfed_par"][
        "valores"
    ][5]
