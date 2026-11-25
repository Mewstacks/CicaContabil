"""Monta o pacote do servico do Windows: roda `uv build --wheel` e zipa wheel + scripts.

Saida: `dist/dominio-mcp-servico-<versao>.zip` com `instalar-servico.ps1`,
`desinstalar-servico.ps1` e a roda, tudo na raiz do zip (o instalador procura a roda ao lado).
"""

from __future__ import annotations

import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = (2020, 1, 1, 0, 0, 0)  # zip reproduzivel


def build() -> Path:
    subprocess.run(  # noqa: S603 - comando fixo
        ["uv", "build", "--wheel", "--out-dir", str(ROOT / "dist")],  # noqa: S607
        cwd=ROOT,
        check=True,
    )
    wheels = sorted((ROOT / "dist").glob("dominio_mcp-*.whl"))
    if not wheels:
        raise SystemExit("nenhuma roda em dist/")
    wheel = wheels[-1]
    version = wheel.name.split("-")[1]
    target = ROOT / "dist" / f"dominio-mcp-servico-{version}.zip"
    members = [
        wheel,
        ROOT / "instalador" / "instalar-servico.ps1",
        ROOT / "instalador" / "desinstalar-servico.ps1",
    ]
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as archive:
        for member in members:
            info = zipfile.ZipInfo(member.name, date_time=FIXED_TIME)
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, member.read_bytes())
    return target


if __name__ == "__main__":
    print(build(), file=sys.stderr)
