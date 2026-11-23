"""Prova de instalacao do `.mcpb` fora do checkout (M11, D-332).

Faz o que o Claude Desktop faz, sem o Claude Desktop: descompacta o pacote numa pasta nova do
sistema, cria um venv **vazio** (so a biblioteca padrao) e executa `server/main.py` com o `env`
do manifesto. Um cliente MCP real (SDK) fala com ele por stdio e confere:

- o interpretador limpo enxerga `dominio_mcp`, `mcp` e `pyodbc` so por `server/lib`, nunca pelo
  checkout;
- o servidor inicia sem banco, sem pack e sem DSN alcancavel, e lista as 10 ferramentas (sem L3);
- os dados do pacote (`importlib.resources`) carregam: recurso `dominio://glossario` e as
  consultas verificadas respondem; sem pack, `mapa_do_banco` falha com erro estruturado;
- o manifesto empacotado e o do repositorio.

Nao prova: o Claude Desktop instalando o pacote num perfil Windows limpo (teste manual, plano M11),
nem o ODBC contra o banco (isso e `doctor` e os testes vivos).

Uso (da pasta `dominio-mcp`):  uv run python scripts/prove_mcpb.py [caminho do .mcpb]
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

import anyio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

ROOT = Path(__file__).resolve().parents[1]
EXPECTED_TOOLS = (
    "mapa_do_banco",
    "buscar_esquema",
    "descrever_tabela",
    "caminho_entre_tabelas",
    "valores_do_campo",
    "empresas",
    "empresa_perfil",
    "movimento_fiscal",
    "conferir_numeracao",
    "consulta_estruturada",
)


def fail(message: str) -> None:
    sys.exit(f"PROVA FALHOU: {message}")


def venv_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def env_from_manifest(manifest: dict[str, object], bundle: Path, home: Path) -> dict[str, str]:
    server = manifest["server"]
    assert isinstance(server, dict)
    raw_env = server["mcp_config"]["env"]  # type: ignore[index]
    env: dict[str, str] = {}
    for key, value in raw_env.items():
        text = str(value).replace("${__dirname}", str(bundle))
        env[key] = text.replace("${user_config.dsn}", "contabil")
    env["DOMINIO_MCP_HOME"] = str(home)  # pasta de dados do teste: nunca a do escritorio
    env["SystemRoot"] = "C:\\Windows" if sys.platform == "win32" else ""
    return {k: v for k, v in env.items() if v}


def probe(python: Path, env: dict[str, str], cwd: Path, bundle: Path) -> None:
    lib = (bundle / "server" / "lib").as_posix()  # o mesmo que server/main.py faz
    code = (
        f"import site; site.addsitedir({lib!r});"
        "import sys, json, pyodbc, mcp, pydantic, yaml, dominio_mcp;"
        "print(json.dumps({'checkout_no_path': not any('HubContador' in p for p in sys.path),"
        "'dominio': dominio_mcp.__file__, 'pyodbc': pyodbc.version}))"
    )
    done = subprocess.run(  # noqa: S603
        [str(python), "-c", code], env=env, cwd=cwd, capture_output=True, text=True, check=False
    )
    if done.returncode != 0:
        fail(f"o interpretador limpo nao importou as dependencias:\n{done.stderr[-1500:]}")
    info = json.loads(done.stdout)
    if not info["checkout_no_path"] or "server" not in info["dominio"]:
        fail(f"o pacote usou codigo de fora de server/lib: {info}")
    print(f"importacoes ok: pyodbc {info['pyodbc']} | dominio_mcp em {info['dominio']}")


async def talk(python: Path, main_py: Path, env: dict[str, str], cwd: Path) -> None:
    params = StdioServerParameters(command=str(python), args=[str(main_py)], env=env, cwd=cwd)
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        tools = [t.name for t in (await session.list_tools()).tools]
        if tuple(tools) != EXPECTED_TOOLS:
            fail(f"ferramentas inesperadas: {tools}")
        if any("sql" in name for name in tools):
            fail("L3 apareceu no pacote")
        glossary = await session.read_resource("dominio://glossario")  # type: ignore[arg-type]
        text = glossary.contents[0].text  # type: ignore[union-attr]
        if "sinonimos" not in json.loads(text):
            fail("o glossario empacotado nao carregou")
        result = await session.call_tool("mapa_do_banco", {})
        body = json.loads(result.content[0].text)  # type: ignore[union-attr]
        if not result.is_error or body["erro"]["codigo"] != "pack_ausente":
            fail(f"sem pack, mapa_do_banco devia falhar com pack_ausente: {body}")
        off = await session.call_tool("empresas", {})
        off_body = json.loads(off.content[0].text)  # type: ignore[union-attr]
        if not off.is_error:
            fail(f"empresas sem pack devia falhar: {off_body}")
        print(f"servidor ok: {len(tools)} ferramentas, glossario carregado, erros estruturados")


def main() -> int:
    artifact = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else next(iter(sorted((ROOT / "dist").glob("dominio-mcp-*.mcpb"))), None)
    )  # type: ignore[assignment]
    if artifact is None or not Path(artifact).is_file():
        fail("rode `uv run python scripts/build_mcpb.py` antes")
    artifact = Path(artifact).resolve()
    with tempfile.TemporaryDirectory(prefix="mcpb-prova-") as scratch_name:
        scratch = Path(scratch_name).resolve()
        if ROOT in scratch.parents:
            fail("a pasta da prova esta dentro do checkout")
        bundle = scratch / "extensao"
        with zipfile.ZipFile(artifact) as archive:
            archive.extractall(bundle)
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        repo_manifest = json.loads((ROOT / "mcpb" / "manifest.json").read_text(encoding="utf-8"))
        if manifest != repo_manifest:
            fail("o manifesto empacotado difere do mcpb/manifest.json")
        venv = scratch / "venv-vazio"
        subprocess.run(  # noqa: S603
            [sys.executable, "-m", "venv", str(venv)], check=True, capture_output=True
        )
        python = venv_python(venv)
        listed = subprocess.run(  # noqa: S603
            [str(python), "-m", "pip", "list", "--format", "json"],
            capture_output=True, text=True, check=False,
        )  # fmt: skip
        extra = {p["name"].lower() for p in json.loads(listed.stdout or "[]")} - {
            "pip",
            "setuptools",
        }
        if extra:
            fail(f"o venv da prova nao esta vazio: {sorted(extra)}")
        home = scratch / "dados"
        home.mkdir()
        env = env_from_manifest(manifest, bundle, home)
        probe(python, env, scratch, bundle)
        anyio.run(talk, python, bundle / "server" / "main.py", env, scratch)
    print(f"PROVA OK: {artifact.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
