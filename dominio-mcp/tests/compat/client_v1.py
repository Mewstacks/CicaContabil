"""Cliente do SDK `mcp` 1.30 contra o servidor REAL do pacote (backend falso) por stdio (A12).

O ambiente do pacote tem o SDK 2.3.0; este script roda num ambiente separado, com o SDK 1.30, e
sobe o servidor com o Python do pacote. Fora do pytest de proposito (nome sem `test_`):

    uv run --directory <pacote> python -c "import sys; print(sys.executable)"
    uv run --no-project --with mcp==1.30.0 python tests/compat/client_v1.py \\
        <Python do pacote> <pasta vazia>

A primeira linha mostra o Python do pacote; a segunda roda o cliente 1.30. Cobre os itens da
matriz `reports/clientes.md`: inicializacao, descoberta, execucao, erro, resposta truncada e
reconexao (segunda sessao com novo processo). "Confirmacao" depende da interface de cada cliente
e nao existe num cliente de SDK.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from pydantic import AnyUrl

SERVER = Path(__file__).resolve().parents[1] / "e2e_server.py"
CAP = 12 * 1024
EXPECTED_TOOLS = 10
failures: list[str] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    print(f"{'OK    ' if ok else 'FALHOU'} {label}{(' | ' + detail) if detail else ''}")
    if not ok:
        failures.append(label)


def text_of(result: Any) -> str:
    return str(result.content[0].text)


async def session_for(python: str, home: Path, steps: Any) -> Any:
    params = StdioServerParameters(command=python, args=[str(SERVER), str(home)])
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        init = await session.initialize()
        return await steps(session, init)


async def first_session(session: ClientSession, init: Any) -> None:
    check(
        "inicializacao",
        init.serverInfo.name == "dominio-mcp",
        f"protocolo {init.protocolVersion}, servidor {init.serverInfo.name} "
        f"{init.serverInfo.version}",
    )
    instructions = init.instructions or ""
    check(
        "instructions: primeiros 512 caracteres dizem 'SOMENTE LEITURA'",
        "SOMENTE LEITURA" in instructions[:512],
        f"{len(instructions)} caracteres",
    )

    tools = (await session.list_tools()).tools
    check(
        "descoberta: 10 ferramentas", len(tools) == EXPECTED_TOOLS, ", ".join(t.name for t in tools)
    )
    hints_ok = all(
        t.annotations is not None
        and t.annotations.readOnlyHint is True
        and t.annotations.destructiveHint is False
        and t.annotations.openWorldHint is False
        for t in tools
    )
    check("descoberta: toda ferramenta declara somente leitura", hints_ok)
    check(
        "descoberta: toda ferramenta tem descricao",
        all((t.description or "").strip() for t in tools),
    )

    resources = {str(r.uri) for r in (await session.list_resources()).resources}
    check(
        "descoberta: recursos",
        {"dominio://mapa", "dominio://glossario"} <= resources,
        str(sorted(resources)),
    )
    prompts = {p.name for p in (await session.list_prompts()).prompts}
    check(
        "descoberta: roteiros",
        {"conferir_empresa", "explorar_assunto"} <= prompts,
        str(sorted(prompts)),
    )
    mapa_resource = await session.read_resource(AnyUrl("dominio://mapa"))
    check(
        "recurso dominio://mapa le",
        json.loads(mapa_resource.contents[0].text).get("banco") is not None,
    )  # type: ignore[union-attr]
    roteiro = await session.get_prompt("explorar_assunto", {"assunto": "notas fiscais"})
    check("roteiro explorar_assunto le", "buscar_esquema" in roteiro.messages[0].content.text)  # type: ignore[union-attr]

    mapa = await session.call_tool("mapa_do_banco", {})
    check("execucao: mapa_do_banco", not mapa.isError and "banco" in json.loads(text_of(mapa)))

    ok = await session.call_tool(
        "consulta_estruturada",
        {"consulta": {"tabela": "geempre", "colunas": ["codi_emp", "nome_emp"], "limite": 5}},
    )
    body = json.loads(text_of(ok))
    check(
        "execucao: consulta_estruturada devolve linhas e rastros",
        not ok.isError
        and body["linhas"] == [[1, "ACME"], [2, "BETA"]]
        and {"lido_em", "consistencia", "tabelas", "pack"} <= set(body),
    )

    blocked = await session.call_tool(
        "consulta_estruturada", {"consulta": {"tabela": "geempre", "colunas": ["ende_emp"]}}
    )
    err = json.loads(text_of(blocked))
    check(
        "erro: coluna bloqueada vem como isError com codigo estavel",
        bool(blocked.isError) and err["erro"]["codigo"] == "coluna_bloqueada",
    )

    big = await session.call_tool(
        "consulta_estruturada",
        {"consulta": {"tabela": "geempre", "colunas": ["codi_emp", "nome_emp"], "limite": 120}},
    )
    raw = text_of(big)
    big_body = json.loads(raw)
    check(
        "resposta truncada: teto de 12 KB, `truncado` e `proximo_passo`",
        not big.isError
        and len(raw.encode("utf-8")) <= CAP
        and big_body["truncado"] is True
        and bool(big_body.get("proximo_passo")),
        f"{len(raw.encode('utf-8'))} bytes, {len(big_body['linhas'])} linhas",
    )


async def second_session(session: ClientSession, init: Any) -> None:
    tools = (await session.list_tools()).tools
    check(
        "reconexao: nova sessao com novo processo inicializa e lista", len(tools) == EXPECTED_TOOLS
    )


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    python, home = sys.argv[1], Path(sys.argv[2])
    import importlib.metadata

    print(f"cliente: mcp {importlib.metadata.version('mcp')} | servidor: {python}")
    asyncio.run(session_for(python, home / "a", first_session))
    asyncio.run(session_for(python, home / "b", second_session))
    print(f"\n{'TUDO OK' if not failures else 'FALHAS: ' + '; '.join(failures)}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
