"""Fixtures built from the official Integra Contador documentation; no call to the Serpro.

Each file in tests/fixtures/integra/serpro/ is named `<idSistema>.<idServico>.<variant>.json` and
holds the answer of one official example: its `source` page, the `servico`, the `notes` of every
correction made to the example (the official pages have missing commas and placeholder PDFs),
the `status`, the `mensagens` and `dados` already decoded. `official_payload` returns the answer
as the client does: `dados` is the escaped JSON string of the gateway.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "integra" / "serpro"
MINIMAL_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF\n"
MINIMAL_PDF_B64 = base64.b64encode(MINIMAL_PDF).decode()


def fixture_names(servico: str | None = None) -> list[str]:
    """Names (without .json) of the fixtures, optionally only those of `SISTEMA.SERVICO`."""

    prefix = f"{servico}." if servico else ""
    return sorted(
        path.name[: -len(".json")]
        for path in FIXTURE_DIR.glob("*.json")
        if path.name.startswith(prefix)
    )


def official_fixture(name: str) -> dict[str, Any]:
    text = (FIXTURE_DIR / f"{name}.json").read_text(encoding="utf-8")
    fixture: dict[str, Any] = json.loads(text)
    return fixture


def official_payload(name: str, *, status: int | None = None) -> dict[str, Any]:
    """The gateway answer of a fixture: status, mensagens and the escaped `dados` string."""

    fixture = official_fixture(name)
    dados = fixture["dados"]
    return {
        "status": fixture["status"] if status is None else status,
        "mensagens": fixture["mensagens"],
        "dados": dados if isinstance(dados, str) else json.dumps(dados, ensure_ascii=False),
    }


def official_dados(name: str) -> Any:
    """The decoded `dados` of a fixture (to alter it in a test and re-encode it)."""

    return official_fixture(name)["dados"]


def payload_with(dados: Any, *, status: int = 200) -> dict[str, Any]:
    """A gateway answer around the given decoded `dados`."""

    return {"status": status, "mensagens": [], "dados": json.dumps(dados, ensure_ascii=False)}
