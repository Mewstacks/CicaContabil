"""Analises de carteira (DC-1): uma ferramenta, oito consultas verificadas, sem SQL do cliente."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from mcp.client import Client

from dominio_mcp.config import HARD_TOOL_PLAN_COST_BUDGET
from dominio_mcp.relay import ToolName, parse_job
from dominio_mcp.server import TOOL_NAMES, briefing_text, build_server
from dominio_mcp.verified import assemble, load_shipped_tools
from test_server_contract import make_deps, run

ANALYSES = (
    "notas_sem_contabilizacao",
    "faturamento_e_limite",
    "sem_movimento",
    "variacao_faturamento",
    "cadastro",
    "lancamentos_contabeis",
    "notas_canceladas",
    "numeracao",
)


def body(result: Any) -> dict[str, Any]:
    return json.loads(result.content[0].text)  # type: ignore[no-any-return]


class Spy:
    """Troca o executor das consultas verificadas e anota o que o servidor mandou."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def run(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, args))
        return {"linhas": [], "quantidade": 0, "truncado": False}


def test_the_portfolio_tool_is_registered_with_a_closed_list_of_analyses(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)

    async def go() -> list[Any]:
        async with Client(build_server(deps)) as client:
            return list((await client.list_tools()).tools)

    tools = {t.name: t for t in run(go)}
    assert "analise_da_carteira" in TOOL_NAMES and len(TOOL_NAMES) == 11
    schema = tools["analise_da_carteira"].input_schema
    assert schema["required"] == ["analise"]
    assert tuple(schema["properties"]["analise"]["enum"]) == ANALYSES
    assert "sql" not in json.dumps(schema).lower()
    for name in ANALYSES:
        assert name in tools["analise_da_carteira"].description


@pytest.mark.parametrize("analysis", ANALYSES)
def test_each_analysis_calls_its_own_verified_query_with_only_the_given_arguments(
    tmp_path: Path, analysis: str
) -> None:
    deps, driver = make_deps(tmp_path)
    spy = Spy()
    deps.verified = spy  # type: ignore[assignment]

    async def go() -> Any:
        async with Client(build_server(deps)) as client:
            return await client.call_tool(
                "analise_da_carteira",
                {"analise": analysis, "inicio": "2026-10-01", "fim": "2026-10-31", "limite": 7},
            )

    result = run(go)
    assert not result.is_error, result.content
    assert spy.calls == [
        (
            f"carteira_{analysis}",
            {"inicio": "2026-10-01", "fim": "2026-10-31", "limite": 7, "deslocamento": 0},
        )
    ]
    assert driver.server.log == []


def test_an_analysis_outside_the_list_is_refused_before_any_work(tmp_path: Path) -> None:
    deps, driver = make_deps(tmp_path)
    spy = Spy()
    deps.verified = spy  # type: ignore[assignment]

    async def go() -> Any:
        async with Client(build_server(deps)) as client:
            return await client.call_tool("analise_da_carteira", {"analise": "apagar_tudo"})

    assert run(go).is_error
    assert spy.calls == [] and driver.server.log == []


def test_every_portfolio_query_is_fixed_read_only_paged_and_budgeted() -> None:
    tools = load_shipped_tools()
    portfolio = {name: tool for name, tool in tools.items() if name.startswith("carteira_")}
    assert set(portfolio) == {f"carteira_{name}" for name in ANALYSES}
    for name, tool in portfolio.items():
        assert tool.aviso and tool.orcamento is not None, name
        cost, rows = tool.orcamento
        assert 1 <= cost <= HARD_TOOL_PLAN_COST_BUDGET and rows >= 1, name
        assert "deslocamento" in {p.nome for p in tool.params}, name
        assert {p.nome for p in tool.params} >= {"limite"}, name
        for variant in tool.variants.values():
            sql, names = assemble(variant.sql, {p.nome: 1 for p in tool.params}, 11, 1)
            upper = " ".join(sql.upper().split())
            assert upper.startswith("SELECT TOP 11 START AT 1 "), name
            assert ";" not in sql and "{" not in sql and sql.count("?") == len(names), name
            for forbidden in ("INSERT ", "UPDATE ", "DELETE ", "DROP ", "ALTER ", "CALL ", "EXEC"):
                assert forbidden not in upper, (name, forbidden)
        assert any(
            o.nome == "razao_emp" and o.classe.value == "texto_livre" for o in tool.saidas
        ), name


def test_the_relay_accepts_the_tool_and_still_has_no_sql_field() -> None:
    assert "analise_da_carteira" in ToolName.__args__  # type: ignore[attr-defined]
    job = parse_job(
        json.dumps(
            {
                "contrato": 1,
                "id": "job_0123456789abcdef",
                "ferramenta": "analise_da_carteira",
                "argumentos": {"analise": "cadastro", "so_pendencias": 1},
            }
        )
    )
    assert job.ferramenta == "analise_da_carteira"


def test_the_briefing_prompt_lists_the_analyses_and_the_caveat(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)

    async def go() -> str:
        async with Client(build_server(deps)) as client:
            prompts = {p.name for p in (await client.list_prompts()).prompts}
            assert "briefing_da_carteira" in prompts
            got = await client.get_prompt("briefing_da_carteira", {"mes": "2026-10"})
            return got.messages[0].content.text  # type: ignore[union-attr,no-any-return]

    text = run(go)
    for name in ("faturamento_e_limite", "notas_sem_contabilizacao", "sem_movimento", "cadastro"):
        assert name in text
    assert "2026-10" in text and "conferir" in text.lower()


def test_the_briefing_prompt_hands_over_dates_the_tools_accept() -> None:
    from dominio_mcp.query_spec import coerce

    for month, last in (
        ("2026-10", "2026-10-31"),
        ("2026-02", "2026-02-28"),
        ("2028-02", "2028-02-29"),
    ):
        text = briefing_text(month)
        assert f"{month}-01" in text and last in text
        for value in (f"{month}-01", last):
            coerce("date", value)


def test_the_briefing_prompt_refuses_a_malformed_month() -> None:
    for bad in ("2026-13", "outubro", "2026-1", "", "2026-10-01"):
        with pytest.raises(ValueError):
            briefing_text(bad)


def test_months_without_history_are_not_a_valid_variation_filter() -> None:
    tool = load_shipped_tools()["carteira_variacao_faturamento"]
    param = next(p for p in tool.params if p.nome == "meses_minimos")
    assert param.minimo == 1 and "inclui empresa nova" not in tool.descricao
