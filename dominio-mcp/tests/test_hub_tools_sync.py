"""O arquivo de ferramentas do Hub tem de ser igual ao que o servidor anuncia."""

from __future__ import annotations

import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "export_tools.py"


def test_hub_tools_file_matches_server() -> None:
    spec = importlib.util.spec_from_file_location("export_tools", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    assert module.TARGET.read_text(encoding="utf-8") == module.render(), (
        "rode: python scripts/export_tools.py"
    )
