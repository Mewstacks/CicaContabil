"""Configuracao dos testes: testes vivos so rodam com DOMINIO_MCP_LIVE=1."""

from __future__ import annotations

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if os.environ.get("DOMINIO_MCP_LIVE") == "1":
        return
    skip_live = pytest.mark.skip(reason="teste vivo: defina DOMINIO_MCP_LIVE=1 para rodar")
    for item in items:
        if "live" in item.keywords:
            item.add_marker(skip_live)
