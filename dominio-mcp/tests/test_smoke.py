from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

import dominio_mcp


def test_package_exposes_version() -> None:
    assert dominio_mcp.__version__.count(".") == 2


def test_import_does_not_pull_odbc_driver() -> None:
    """O pacote precisa importar sem o driver ODBC (CI e maquinas sem unixODBC)."""
    code = textwrap.dedent(
        """
        import sys
        import dominio_mcp
        sys.exit(1 if "pyodbc" in sys.modules else 0)
        """
    )
    result = subprocess.run([sys.executable, "-c", code], check=False)  # noqa: S603
    assert result.returncode == 0


@pytest.mark.live
def test_live_marker_is_skipped_by_default() -> None:
    assert os.environ.get("DOMINIO_MCP_LIVE") == "1"


def test_tests_dir_layout() -> None:
    here = Path(__file__).parent
    assert (here / "conftest.py").is_file()
