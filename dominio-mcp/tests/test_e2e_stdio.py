"""e2e por stdio de verdade: processo filho, framing JSON-RPC e cliente do SDK (T6.3)."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

HERE = Path(__file__).parent


async def session_run(params: StdioServerParameters, steps: Any) -> Any:
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        return await steps(session)


def test_fake_backend_server_answers_over_real_stdio(tmp_path: Path) -> None:
    params = StdioServerParameters(
        command=sys.executable, args=[str(HERE / "e2e_server.py"), str(tmp_path)]
    )

    async def steps(session: ClientSession) -> dict[str, Any]:
        tools = await session.list_tools()
        mapa = await session.call_tool("mapa_do_banco", {})
        consulta = await session.call_tool(
            "consulta_estruturada",
            {"consulta": {"tabela": "geempre", "colunas": ["codi_emp", "nome_emp"], "limite": 5}},
        )
        bloqueada = await session.call_tool(
            "consulta_estruturada", {"consulta": {"tabela": "geempre", "colunas": ["ende_emp"]}}
        )
        return {
            "tools": [t.name for t in tools.tools],
            "mapa": json.loads(mapa.content[0].text),  # type: ignore[union-attr]
            "consulta": json.loads(consulta.content[0].text),  # type: ignore[union-attr]
            "bloqueada_erro": bloqueada.is_error,
            "bloqueada": json.loads(bloqueada.content[0].text),  # type: ignore[union-attr]
        }

    out = anyio.run(lambda: session_run(params, steps))
    assert len(out["tools"]) == 10 and out["tools"][0] == "mapa_do_banco"
    assert out["mapa"]["banco"].startswith("Dominio")
    assert out["consulta"]["linhas"] == [[1, "ACME"], [2, "BETA"]]
    assert out["bloqueada_erro"] is True
    assert out["bloqueada"]["erro"]["codigo"] == "coluna_bloqueada"
    events = (tmp_path / "audit" / "audit.jsonl").read_text(encoding="utf-8")
    assert "consulta_estruturada" in events and "ACME" not in events


def test_big_result_is_truncated_over_stdio_and_a_new_process_reconnects(tmp_path: Path) -> None:
    def server(folder: Path) -> StdioServerParameters:
        return StdioServerParameters(
            command=sys.executable, args=[str(HERE / "e2e_server.py"), str(folder)]
        )

    spec = {"tabela": "geempre", "colunas": ["codi_emp", "nome_emp"]}

    async def steps(session: ClientSession) -> dict[str, Any]:
        await session.call_tool("consulta_estruturada", {"consulta": {**spec, "limite": 5}})
        big = await session.call_tool("consulta_estruturada", {"consulta": {**spec, "limite": 120}})
        text = big.content[0].text  # type: ignore[union-attr]
        return {"erro": big.is_error, "bytes": len(text.encode("utf-8")), "corpo": json.loads(text)}

    async def count_tools(session: ClientSession) -> int:
        return len((await session.list_tools()).tools)

    out = anyio.run(lambda: session_run(server(tmp_path / "primeira"), steps))
    assert out["erro"] is False and out["bytes"] <= 12 * 1024
    assert out["corpo"]["truncado"] is True and out["corpo"]["proximo_passo"]
    assert len(out["corpo"]["linhas"]) < 120
    # reconexao: o processo anterior terminou com a sessao; um novo processo atende do zero
    assert anyio.run(lambda: session_run(server(tmp_path / "segunda"), count_tools)) == 10


def test_real_cli_serves_without_pack_or_database(tmp_path: Path) -> None:
    env = {**os.environ, "DOMINIO_MCP_HOME": str(tmp_path), "DOMINIO_MCP_CONFIG": ""}
    env.pop("DOMINIO_MCP_CONFIG")
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "dominio_mcp", "serve"], env=env
    )

    async def steps(session: ClientSession) -> dict[str, Any]:
        tools = await session.list_tools()
        mapa = await session.call_tool("mapa_do_banco", {})
        return {
            "n": len(tools.tools),
            "erro": mapa.is_error,
            "corpo": json.loads(mapa.content[0].text),  # type: ignore[union-attr]
        }

    out = anyio.run(lambda: session_run(params, steps))
    assert out["n"] == 10 and out["erro"] is True
    assert out["corpo"]["erro"]["codigo"] == "pack_ausente"
