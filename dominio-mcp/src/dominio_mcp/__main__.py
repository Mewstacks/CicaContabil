"""`python -m dominio_mcp` equivale a `dominio-mcp`."""

from __future__ import annotations

import sys

from dominio_mcp.cli import main

if __name__ == "__main__":
    sys.exit(main())
