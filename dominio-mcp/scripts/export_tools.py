"""Exporta as definicoes das 11 ferramentas para o Hub (`dominio_tools.json`).

O gateway do Hub anuncia estas ferramentas sem importar o `dominio_mcp`. Um teste do
`dominio-mcp` confere que o arquivo do Hub e igual ao que o servidor anuncia hoje.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import anyio
from mcp.client import Client

from dominio_mcp.config import Limits, Profile, Settings
from dominio_mcp.server import build_server

TARGET = Path(__file__).resolve().parents[2] / "src" / "apps" / "mcpgateway" / "dominio_tools.json"


def live_tools() -> list[dict[str, Any]]:
    # registrar ferramentas nao toca o banco: so a chamada usa `schema` e `verified`
    from dominio_mcp.verified import load_shipped_tools

    settings = Settings(dsn="x", home=Path("."), limits=Limits(), profile=Profile.REMOTE)
    deps = SimpleNamespace(
        settings=settings, schema=None, verified=SimpleNamespace(tools=load_shipped_tools())
    )

    async def run() -> list[dict[str, Any]]:
        async with Client(build_server(deps, Profile.REMOTE)) as client:  # type: ignore[arg-type]
            listed = await client.list_tools()
        return [
            {
                "name": t.name,
                "description": t.description or "",
                "inputSchema": t.input_schema,
                "annotations": {"readOnlyHint": True, "destructiveHint": False},
            }
            for t in sorted(listed.tools, key=lambda t: t.name)
        ]

    return anyio.run(run)


def render() -> str:
    return json.dumps(live_tools(), ensure_ascii=False, indent=1, sort_keys=True) + "\n"


if __name__ == "__main__":
    TARGET.write_text(render(), encoding="utf-8", newline="\n")
    print(f"{TARGET} ({len(live_tools())} ferramentas)", file=sys.stderr)
