"""Ponto de entrada do pacote .mcpb: o mesmo `dominio-mcp serve` (stdio, perfil remote).

O Claude Desktop executa este arquivo com `PYTHONPATH=<pacote>/server/lib`, onde estao as
dependencias e o proprio `dominio_mcp`. `PYTHONPATH` nao le arquivos `.pth`, e o `pywin32` (exigido
pelo SDK `mcp` no Windows) so enxerga `pywintypes` por um deles: `site.addsitedir` resolve.
O perfil e sempre `remote` (D-326): L3 nao existe aqui.
"""

import site
import sys
from pathlib import Path

site.addsitedir(str(Path(__file__).resolve().parent / "lib"))

from dominio_mcp.cli import main

if __name__ == "__main__":
    sys.exit(main(["serve"]))
