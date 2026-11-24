"""A7a completo: marcadores plantados nao aparecem em NENHUMA saida (ferramenta, erro, recurso,
prompt e auditoria). Catalogo sintetico em `fixtures/synthetic_catalog.json`; o ODBC falso devolve
os valores plantados SE a consulta chegar a executar, entao o teste tambem prova que as recusas
acontecem antes do banco.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import anyio
from mcp.client import Client

from dominio_mcp.audit import JsonlAuditor
from dominio_mcp.catalog import build_catalog
from dominio_mcp.config import Limits, Settings
from dominio_mcp.executor import QueryEngine
from dominio_mcp.odbc import build_session
from dominio_mcp.overlay import load_overlay
from dominio_mcp.pack import Pack, build_pack
from dominio_mcp.server import Deps, build_server
from dominio_mcp.tools_schema import SchemaTools
from dominio_mcp.verified import VerifiedRunner, load_shipped_tools
from fake_odbc import Fail, FakeDriver, Rows
from qhelp import POLICY

FIXTURE = Path(__file__).parent / "fixtures" / "synthetic_catalog.json"
PLAN = (Path(__file__).parent / "fixtures" / "plans" / "full_scan.txt").read_text(encoding="utf-8")
PLANTED = (
    "MARKER_SEGREDO_AUDADOS_9F3A",
    "MARKER_COMENTARIO_SECRETO_55AA",
    "MARKER_COMENTARIO_TABELA_SECRETA_77CC",
    "MARKER_SEGREDO_NO_ERRO",
    "52998224725",
    "529.982.247-25",
    "fulano@exemplo.com",
    "91234-5678",
)


class Guard:
    stale_reason = None

    def __init__(self, pack: Pack) -> None:
        self._pack = pack

    def pack(self) -> Pack:
        return self._pack

    precheck = pack

    def check(self, execute: Any) -> Pack:
        return self._pack


def make(tmp_path: Path) -> tuple[Deps, FakeDriver]:
    catalog = build_catalog(json.loads(FIXTURE.read_text(encoding="utf-8")))
    new_column = ("efnovas", "coluna_nova")
    accepted = frozenset(
        (k, c.name.lower()) for k, t in catalog.tables.items() for c in t.columns
    ) - {new_column}
    overlay = load_overlay()
    build_pack(
        tmp_path / "s.sqlite3",
        catalog=catalog,
        policy=POLICY,
        overlay=overlay,
        accepted=accepted,
        dsn="contabil",
    )
    pack = Pack(tmp_path / "s.sqlite3")
    settings = Settings(dsn="contabil", home=tmp_path, limits=Limits())
    auditor = JsonlAuditor(tmp_path / "audit")
    driver = FakeDriver()
    session = build_session(settings, driver=driver, auditor=auditor, lock_wait_seconds=0.3)
    guard = Guard(pack)
    engine = QueryEngine(
        settings=settings,
        policy=POLICY,
        guard=guard,  # type: ignore[arg-type]
        session=session,
        auditor=auditor,
    )
    deps = Deps(
        settings=settings,
        policy=POLICY,
        overlay=overlay,
        guard=guard,  # type: ignore[arg-type]
        session=session,
        auditor=auditor,
        engine=engine,
        schema=SchemaTools(guard.pack, lambda: None, overlay),
        verified=VerifiedRunner(engine, load_shipped_tools(), overlay),
    )
    return deps, driver


def l2(table: str, *columns: str, **extra: Any) -> dict[str, Any]:
    return {"consulta": {"tabela": table, "colunas": list(columns), **extra}}


def test_planted_markers_never_leave_any_output(tmp_path: Path) -> None:
    deps, driver = make(tmp_path)
    # valores plantados que o banco devolveria se a consulta chegasse a executar
    driver.server.script += [
        Rows(["plan"], [(PLAN,)]),
        Rows(["valor"], [("MARKER_SEGREDO_AUDADOS_9F3A",)]),
    ]
    outputs: list[str] = []

    async def go() -> None:
        async with Client(build_server(deps)) as client:
            refused = [
                l2("audados", "valor"),
                l2("geempre", "senha_modulo_web"),
                l2("efnovas", "coluna_nova"),
                l2("vw_dados", "conteudo"),
                l2("gecertificadosdigitais", "conteudo"),
                l2("gecertificadosdigitais", "nome"),
            ]
            for args in refused:
                result = await client.call_tool("consulta_estruturada", args)
                assert result.is_error, args
                outputs.append(result.content[0].text)  # type: ignore[union-attr]
            assert len(driver.server.script) == 2, "recusa tem de vir antes do banco"

            driver.server.script.clear()
            driver.server.script += [
                Rows(["plan"], [(PLAN,)]),
                Rows(
                    ["codi_emp", "observacao"],
                    [
                        (1, "ligar CPF 529.982.247-25 ou fulano@exemplo.com"),
                        (2, "fone (11) 91234-5678 / 52998224725"),
                    ],
                ),
            ]
            ok = await client.call_tool(
                "consulta_estruturada", l2("efobservacoes", "codi_emp", "observacao")
            )
            assert not ok.is_error
            outputs.append(ok.content[0].text)  # type: ignore[union-attr]
            assert "[cpf]" in ok.content[0].text and "[email]" in ok.content[0].text  # type: ignore[union-attr]

            driver.server.script += [
                Rows(["plan"], [(PLAN,)]),
                Fail("42S02", "[42S02] erro com MARKER_SEGREDO_NO_ERRO dentro (-141)"),
            ]
            broken = await client.call_tool("consulta_estruturada", l2("geempre", "codi_emp"))
            assert broken.is_error
            outputs.append(broken.content[0].text)  # type: ignore[union-attr]

            for name in (
                "geempre",
                "audados",
                "gecertificadosdigitais",
                "efobservacoes",
                "vw_dados",
                "efnovas",
            ):
                result = await client.call_tool("descrever_tabela", {"tabela": name})
                outputs.append(result.content[0].text)  # type: ignore[union-attr]
            for query in ("senha", "certificado", "auditoria", "observacao", "conteudo valor"):
                result = await client.call_tool("buscar_esquema", {"consulta": query})
                outputs.append(result.content[0].text)  # type: ignore[union-attr]
            for tool, args in (
                ("mapa_do_banco", {}),
                ("caminho_entre_tabelas", {"origem": "geempre", "destino": "audados"}),
                ("valores_do_campo", {"tabela": "geempre", "coluna": "senha_modulo_web"}),
                ("empresas", {}),
            ):
                result = await client.call_tool(tool, args)
                outputs.append(result.content[0].text)  # type: ignore[union-attr]
            mapa = await client.read_resource("dominio://mapa")
            glossario = await client.read_resource("dominio://glossario")
            outputs.append(mapa.contents[0].text)  # type: ignore[union-attr]
            outputs.append(glossario.contents[0].text)  # type: ignore[union-attr]
            prompt = await client.get_prompt("explorar_assunto", {"assunto": "senha"})
            outputs.append(prompt.messages[0].content.text)  # type: ignore[union-attr,attr-defined]

    anyio.run(go)
    outputs.append((tmp_path / "audit" / "audit.jsonl").read_text(encoding="utf-8"))
    everything = "\n".join(outputs)
    for planted in PLANTED:
        assert planted not in everything, planted
    assert "marker" not in everything.lower()
