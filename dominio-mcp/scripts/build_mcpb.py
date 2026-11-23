"""Monta o pacote `.mcpb` do dominio-mcp (M11, D-330).

Fluxo, sempre a partir do lock do projeto (nada de resolver versao nova):

1. `uv export --frozen --no-dev` -> pins de tudo o que o servidor precisa;
2. `uv build --wheel` -> o proprio `dominio_mcp`, com `data/` (overlay e consultas verificadas);
3. `uv pip install --target build/mcpb/server/lib` para **Windows x64, CPython 3.12**, so wheels
   binarios (`pyodbc`, `pydantic-core`... sao compilados: o pacote e preso a essa plataforma);
4. copia `mcpb/manifest.json` e `mcpb/server/main.py`;
5. `mcpb validate` e `mcpb pack` (CLI `@anthropic-ai/mcpb`, versao fixada abaixo).

Saida: `dist/dominio-mcp-<versao>.mcpb` e o SHA-256 dele. O pacote **so conta como entregue**
depois de `scripts/prove_mcpb.py` (instalacao em pasta limpa fora do checkout) e do teste manual
no Claude Desktop de um perfil Windows limpo (plano, M11).

Uso (a partir da pasta `dominio-mcp`):  uv run python scripts/build_mcpb.py
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path

MCPB_CLI = "@anthropic-ai/mcpb@2.1.2"
TARGET_PLATFORM = "x86_64-pc-windows-msvc"
TARGET_PYTHON = "3.12"
ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "build" / "mcpb"
WHEEL_DIR = ROOT / "build" / "wheel"
DIST = ROOT / "dist"


def run(*cmd: str, cwd: Path = ROOT) -> str:
    done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)  # noqa: S603
    if done.returncode != 0:
        sys.exit(f"falhou: {' '.join(cmd)}\n{done.stdout[-2000:]}\n{done.stderr[-2000:]}")
    return done.stdout


def project_version() -> str:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return str(data["project"]["version"])


def main() -> int:
    version = project_version()
    manifest = json.loads((ROOT / "mcpb" / "manifest.json").read_text(encoding="utf-8"))
    if manifest["version"] != version:
        sys.exit(f"mcpb/manifest.json esta em {manifest['version']} e o pacote em {version}")

    for folder in (STAGE, WHEEL_DIR):
        if folder.exists():
            shutil.rmtree(folder)
    lib = STAGE / "server" / "lib"
    lib.mkdir(parents=True)
    DIST.mkdir(exist_ok=True)

    requirements = WHEEL_DIR / "requirements.txt"
    WHEEL_DIR.mkdir(parents=True)
    exported = run(
        "uv", "export", "--frozen", "--no-dev", "--no-emit-project", "--no-hashes", "--quiet"
    )
    requirements.write_text(exported, encoding="utf-8")
    run("uv", "build", "--wheel", "--out-dir", str(WHEEL_DIR), "--quiet")
    wheels = sorted(WHEEL_DIR.glob("dominio_mcp-*.whl"))
    if len(wheels) != 1:
        sys.exit(f"esperava 1 wheel do dominio_mcp, achei {len(wheels)}")

    run(
        "uv", "pip", "install", "--quiet", "--target", str(lib),
        "--python-platform", TARGET_PLATFORM, "--python-version", TARGET_PYTHON,
        "--only-binary", ":all:", "--no-deps", "-r", str(requirements), str(wheels[0]),
    )  # fmt: skip
    for cache in lib.rglob("__pycache__"):
        shutil.rmtree(cache, ignore_errors=True)
    for stray in ("bin", "Scripts"):  # executaveis do `uv pip --target`: o pacote usa main.py
        shutil.rmtree(lib / stray, ignore_errors=True)

    shutil.copy2(ROOT / "mcpb" / "manifest.json", STAGE / "manifest.json")
    (STAGE / "server").mkdir(exist_ok=True)
    shutil.copy2(ROOT / "mcpb" / "server" / "main.py", STAGE / "server" / "main.py")

    output = DIST / f"dominio-mcp-{version}.mcpb"
    output.unlink(missing_ok=True)
    npx = shutil.which("npx") or "npx"
    run(npx, "-y", MCPB_CLI, "validate", str(STAGE / "manifest.json"))
    run(npx, "-y", MCPB_CLI, "pack", str(STAGE), str(output))
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    print(f"{output}  {output.stat().st_size / 1_048_576:.1f} MiB  sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
