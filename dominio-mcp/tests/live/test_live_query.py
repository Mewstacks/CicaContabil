"""Teste vivo de L2 no banco real: so leitura, so agregado e sem imprimir valor de negocio.

O pack deste teste e gerado numa pasta temporaria a partir do catalogo real, com o aceite
restrito a quatro colunas (`geempre.codi_emp`, `efsaidas.codi_emp`, `efsaidas.dsai_sai`,
`efsaidas.vcon_sai`). Nao mexe no pack nem no aceite do escritorio.

Rode com:  $env:DOMINIO_MCP_LIVE = '1'; uv run --directory dominio-mcp pytest -q -m live tests/live
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from pathlib import Path

import pytest

from dominio_mcp.catalog import build_catalog, extract_raw
from dominio_mcp.config import Settings
from dominio_mcp.executor import QueryEngine
from dominio_mcp.freshness import FreshnessGuard, make_rehasher
from dominio_mcp.odbc import Session, build_session
from dominio_mcp.overlay import load_overlay
from dominio_mcp.pack import build_pack, pack_store_for
from dominio_mcp.policy import load_policy
from dominio_mcp.query_spec import QueryRefused

pytestmark = pytest.mark.live

DSN = os.environ.get("DOMINIO_MCP_DSN", "contabil")
ACCEPTED = frozenset(
    {
        ("geempre", "codi_emp"),
        ("efsaidas", "codi_emp"),
        ("efsaidas", "dsai_sai"),
        ("efsaidas", "vcon_sai"),
    }
)


@pytest.fixture(scope="module")
def engine(tmp_path_factory: pytest.TempPathFactory) -> Iterator[QueryEngine]:
    home: Path = tmp_path_factory.mktemp("live")
    settings = Settings(dsn=DSN, home=home)
    session: Session = build_session(settings, lock_wait_seconds=10.0)
    policy, overlay = load_policy(), load_overlay()
    with session.slot() as slot:
        catalog = build_catalog(extract_raw(slot.execute))
    store = pack_store_for(settings)
    built = store.new_build_path()
    meta = build_pack(
        built, catalog=catalog, policy=policy, overlay=overlay, accepted=ACCEPTED, dsn=DSN
    )
    store.publish(built, meta)
    guard = FreshnessGuard(
        store,
        policy_sha=policy.sha,
        overlay_sha=overlay.sha,
        rehash=make_rehasher("bethadba"),
    )
    try:
        yield QueryEngine(settings=settings, policy=policy, guard=guard, session=session)
    finally:
        session.close()


def test_count_of_companies_is_a_plain_integer_with_the_consistency_label(
    engine: QueryEngine,
) -> None:
    out = engine.run(
        {"tabela": "geempre", "agregacoes": [{"funcao": "count", "coluna": "*", "alias": "n"}]}
    )
    assert out["colunas"] == ["n"] and out["quantidade"] == 1
    assert isinstance(out["linhas"][0][0], int) and out["linhas"][0][0] >= 1
    assert out["consistencia"] == "leitura_nao_confirmada"
    assert out["tabelas"] == ["geempre"] and out["pack"]
    assert 0 <= out["custo_estimado"] < 10


def test_aggregate_over_a_big_table_with_company_and_window(engine: QueryEngine) -> None:
    company = engine.run({"tabela": "geempre", "colunas": ["codi_emp"], "limite": 1})
    code = company["linhas"][0][0]
    out = engine.run(
        {
            "tabela": "efsaidas",
            "agregacoes": [
                {"funcao": "count", "coluna": "*", "alias": "notas"},
                {"funcao": "sum", "coluna": "vcon_sai", "alias": "total"},
            ],
            "filtros": [
                {"coluna": "codi_emp", "op": "=", "valor": code},
                {"coluna": "dsai_sai", "op": "between", "valor": ["2025-01-01", "2025-12-31"]},
            ],
        }
    )
    assert out["colunas"] == ["notas", "total"] and out["quantidade"] == 1
    notas, total = out["linhas"][0]
    assert isinstance(notas, int) and notas >= 0
    assert total is None or isinstance(total, int | float)
    assert out["custo_estimado"] < 10


def test_scope_and_policy_refuse_before_reaching_the_database(engine: QueryEngine) -> None:
    with pytest.raises(QueryRefused) as scope:
        engine.run(
            {"tabela": "efsaidas", "agregacoes": [{"funcao": "count", "coluna": "*", "alias": "n"}]}
        )
    assert scope.value.code == "sem_filtro_de_empresa"
    with pytest.raises(QueryRefused) as blocked:
        engine.run({"tabela": "geempre", "colunas": ["nome_emp"]})
    assert blocked.value.code == "coluna_bloqueada"
    assert blocked.value.details["motivo"] == "nao_classificada"
