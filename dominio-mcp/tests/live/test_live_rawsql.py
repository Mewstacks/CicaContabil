# ruff: noqa: S608, F811
"""Teste vivo de L3 no banco real: o SQL vira L2 e segue o mesmo caminho, so leitura e agregado.

Reaproveita o pack temporario e o motor de `test_live_query` (aceite restrito a quatro colunas).
Rode com:  $env:DOMINIO_MCP_LIVE = '1'; uv run --directory dominio-mcp pytest -q -m live tests/live
"""

from __future__ import annotations

import dataclasses
from collections.abc import Iterator

import pytest
from test_live_query import engine as base_engine  # noqa: F401  (fixture do modulo vizinho)

from dominio_mcp.config import Profile
from dominio_mcp.executor import QueryEngine
from dominio_mcp.query_spec import QueryRefused
from dominio_mcp.tools_rawsql import run_raw_sql

pytestmark = pytest.mark.live


@pytest.fixture
def engine(base_engine: QueryEngine) -> Iterator[QueryEngine]:
    """O mesmo motor, com o perfil do processo `local` e `raw_sql` ligado (so durante o teste)."""
    original = base_engine.settings
    base_engine._settings = dataclasses.replace(original, profile=Profile.LOCAL, raw_sql=True)
    try:
        yield base_engine
    finally:
        base_engine._settings = original


def test_sql_count_runs_on_the_real_database(engine: QueryEngine) -> None:
    out = run_raw_sql(engine, Profile.LOCAL, "SELECT COUNT(*) AS n FROM geempre")
    assert out["colunas"] == ["n"] and isinstance(out["linhas"][0][0], int)
    assert out["consistencia"] == "leitura_nao_confirmada"


def test_sql_over_a_big_table_needs_company_and_window_like_l2(engine: QueryEngine) -> None:
    with pytest.raises(QueryRefused) as refused:
        run_raw_sql(engine, Profile.LOCAL, "SELECT COUNT(*) AS n FROM efsaidas")
    assert refused.value.code == "sem_filtro_de_empresa"
    code = engine.run({"tabela": "geempre", "colunas": ["codi_emp"], "limite": 1})["linhas"][0][0]
    out = run_raw_sql(
        engine,
        Profile.LOCAL,
        f"SELECT COUNT(*) AS notas, SUM(vcon_sai) AS total FROM efsaidas WHERE codi_emp = {code} "
        "AND dsai_sai BETWEEN '2025-01-01' AND '2025-12-31'",
    )
    assert out["colunas"] == ["notas", "total"] and out["custo_estimado"] < 10


def test_sql_cannot_reach_blocked_columns_or_write(engine: QueryEngine) -> None:
    with pytest.raises(QueryRefused) as blocked:
        run_raw_sql(engine, Profile.LOCAL, "SELECT nome_emp FROM geempre")
    assert blocked.value.code == "coluna_bloqueada"
    with pytest.raises(QueryRefused) as write:
        run_raw_sql(engine, Profile.LOCAL, "DELETE FROM geempre")
    assert write.value.code == "sql_recusado"
