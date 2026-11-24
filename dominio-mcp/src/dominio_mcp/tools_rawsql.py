"""Ferramenta `sql_somente_leitura` (L3): so no perfil `local` com `raw_sql` ligado (D-326, D-330).

A decisao e tomada em dois lugares independentes, nenhum deles so "esconde" a ferramenta:
registro (`server.build_server` so a registra quando `Settings.raw_sql_enabled`) e despacho
(`run_raw_sql` recusa de novo). Um cliente que chame o nome sem a ferramenta estar listada tambem
nao chega aqui: o servidor MCP nao tem o nome. Depois disso o SQL vira consulta estruturada
(`rawsql.translate`) e segue o mesmo caminho de L2, com a mesma politica de dados.
"""

from __future__ import annotations

from typing import Any

from dominio_mcp.config import Profile, Settings
from dominio_mcp.executor import QueryEngine
from dominio_mcp.rawsql import check_joins, translate
from dominio_mcp.verified import ToolDisabled

TOOL_NAME = "sql_somente_leitura"


def raw_sql_available(settings: Settings, profile: Profile) -> bool:
    """Perfil pedido pela CLI e o do processo precisam ser `local`, e `raw_sql` ligado."""
    return profile is Profile.LOCAL and settings.profile is Profile.LOCAL and settings.raw_sql


def run_raw_sql(engine: QueryEngine, profile: Profile, sql: str) -> dict[str, Any]:
    if not raw_sql_available(engine.settings, profile):
        raise ToolDisabled(
            TOOL_NAME,
            "so existe no perfil local com raw_sql ligado; use `consulta_estruturada`",
        )
    raw = translate(sql)
    return engine.run(raw.spec, tool=TOOL_NAME, verify=lambda vq: check_joins(raw, vq))
