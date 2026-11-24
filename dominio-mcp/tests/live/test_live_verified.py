"""Teste vivo das consultas verificadas (L1) no banco real: so leitura, sem imprimir valor.

Valida que o SQL de cada ferramenta roda no SQL Anywhere 17, devolve o formato prometido e que o
`movimento_fiscal` bate com uma consulta L2 independente (T5.4). A conferencia contra um relatorio
oficial do Dominio continua pendente (contadora).

Rode com:  $env:DOMINIO_MCP_LIVE = '1'; uv run --directory dominio-mcp pytest -q -m live tests/live
"""

from __future__ import annotations

import os
from collections.abc import Iterator
from datetime import date
from decimal import Decimal
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
from dominio_mcp.verified import VerifiedRunner, assemble, load_shipped_tools

pytestmark = pytest.mark.live

DSN = os.environ.get("DOMINIO_MCP_DSN", "contabil")
ACCEPTED = frozenset(
    {
        ("efsaidas", "codi_emp"),
        ("efsaidas", "dsai_sai"),
        ("efsaidas", "vcon_sai"),
        ("efsaidas", "cancelada_sai"),
    }
)
WINDOW = ("2025-06-01", "2025-06-30")


class Rig:
    def __init__(self, home: Path) -> None:
        settings = Settings(dsn=DSN, home=home)
        self.session: Session = build_session(settings, lock_wait_seconds=30.0)
        policy, overlay = load_policy(), load_overlay()
        with self.session.slot() as slot:
            catalog = build_catalog(extract_raw(slot.execute))
            result = slot.execute(
                'SELECT "codi_emp", COUNT(*) AS n FROM "bethadba"."efsaidas" '
                'GROUP BY "codi_emp" ORDER BY n DESC',
                max_rows=3,
                timeout=60,
            )
        self.company = int(result.rows[0][0])  # type: ignore[arg-type]
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
        self.engine = QueryEngine(
            settings=settings, policy=policy, guard=guard, session=self.session
        )
        self.verified = VerifiedRunner(self.engine, load_shipped_tools(), overlay)


@pytest.fixture(scope="module")
def rig(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Rig]:
    instance = Rig(tmp_path_factory.mktemp("live_l1"))
    try:
        yield instance
    finally:
        instance.session.close()


def test_every_shipped_tool_is_enabled_against_the_real_pack(rig: Rig) -> None:
    assert {n: rig.verified.status(n) for n in rig.verified.tools} == dict.fromkeys(
        rig.verified.tools
    )


def test_empresas_lists_the_portfolio_with_legends(rig: Rig) -> None:
    out = rig.verified.run("empresas", {"limite": 3})
    assert out["colunas"] == [
        "codi_emp",
        "razao_emp",
        "cnpj",
        "situacao",
        "regime_codigo",
        "regime_vigencia",
    ]
    assert 1 <= out["quantidade"] <= 3
    assert "situacao" in out["legendas"] and "regime_codigo" in out["legendas"]
    one = rig.verified.run("empresas", {"codi_emp": rig.company})
    assert one["quantidade"] == 1 and one["linhas"][0][0] == rig.company
    assert out["consistencia"] == "leitura_nao_confirmada" and out["custo_estimado"] < 10


def test_empresa_perfil_is_a_single_row_of_counts(rig: Rig) -> None:
    out = rig.verified.run("empresa_perfil", {"codi_emp": rig.company})
    assert out["quantidade"] == 1 and len(out["colunas"]) == 14
    row = dict(zip(out["colunas"], out["linhas"][0], strict=True))
    for key in (
        "saidas_linhas_12m",
        "entradas_linhas_12m",
        "servicos_linhas_12m",
        "lancamentos_12m",
    ):
        assert isinstance(row[key], int) and row[key] >= 0


def test_movimento_fiscal_matches_an_independent_l2_aggregate(rig: Rig) -> None:
    l1 = rig.verified.run(
        "movimento_fiscal", {"codi_emp": rig.company, "inicio": WINDOW[0], "fim": WINDOW[1]}
    )
    assert l1["colunas"] == ["fonte", "competencia", "linhas", "documentos", "valor_contabil"]
    saidas = [r for r in l1["linhas"] if r[0] == "saidas"]
    assert all(r[1] == 202506 for r in saidas)
    l1_total = Decimal(str(saidas[0][4])) if saidas else Decimal(0)
    l1_lines = int(saidas[0][2]) if saidas else 0

    def l2(op: str) -> tuple[int, Decimal]:
        flt = {"coluna": "cancelada_sai", "op": op}
        if op != "is_null":
            flt["valor"] = "S"
        out = rig.engine.run(
            {
                "tabela": "efsaidas",
                "agregacoes": [
                    {"funcao": "count", "coluna": "*", "alias": "n"},
                    {"funcao": "sum", "coluna": "vcon_sai", "alias": "total"},
                ],
                "filtros": [
                    {"coluna": "codi_emp", "op": "=", "valor": rig.company},
                    {"coluna": "dsai_sai", "op": "between", "valor": list(WINDOW)},
                    flt,
                ],
            }
        )
        n, total = out["linhas"][0]
        return int(n), Decimal(str(total or 0))

    not_cancelled, nulls = l2("!="), l2("is_null")
    assert l1_lines == not_cancelled[0] + nulls[0]
    assert abs(l1_total - (not_cancelled[1] + nulls[1])) < Decimal("0.01")


def test_conferir_numeracao_runs_for_both_issued_documents(rig: Rig) -> None:
    for documento in ("saidas", "servicos"):
        out = rig.verified.run(
            "conferir_numeracao",
            {
                "codi_emp": rig.company,
                "documento": documento,
                "inicio": WINDOW[0],
                "fim": WINDOW[1],
            },
        )
        assert out["colunas"] == ["tipo", "especie", "serie", "de", "ate", "quantidade"]
        assert all(r[0] in ("lacuna", "duplicidade") for r in out["linhas"])


# Faixas de numeracao que se sobrepoem (revisao do Codex, achado 15). O SQL de L1 roda no servidor
# real, mas contra linhas sinteticas: a tabela `bethadba.efsaidas` vira uma tabela derivada de
# constantes (`dummy`), entao nenhum dado de negocio e lido.
SYNTHETIC_ISSUED = (
    "(SELECT 1 AS codi_emp, 1 AS codi_esp, 'A' AS seri_sai, 1 AS nume_sai, 100 AS atex_sai, "
    "1 AS segi_sai, CAST('2026-01-10' AS DATE) AS dsai_sai FROM dummy "
    "UNION ALL SELECT 1, 1, 'A', 50, 50, 1, CAST('2026-01-11' AS DATE) FROM dummy "
    "UNION ALL SELECT 1, 1, 'A', 101, 101, 1, CAST('2026-01-12' AS DATE) FROM dummy "
    "UNION ALL SELECT 1, 1, 'A', 150, 150, 1, CAST('2026-01-13' AS DATE) FROM dummy) AS efsaidas"
)
COVERED_BY = (
    "MAX(ultimo) OVER (PARTITION BY esp, serie ORDER BY nume ROWS BETWEEN UNBOUNDED PRECEDING "
    "AND CURRENT ROW) AS coberto"
)


def _numbering_rows(rig: Rig, sql_text: str) -> list[list[object]]:
    values = {"codi_emp": 1, "inicio": date(2026, 1, 1), "fim": date(2026, 3, 31)}
    sql, names = assemble(sql_text, values, 101)
    sql = sql.replace("bethadba.efsaidas", SYNTHETIC_ISSUED)
    result = rig.session.execute(sql, tuple(values[n] for n in names), max_rows=50, timeout=30)
    return [list(r) for r in result.rows]


def test_numbering_gaps_ignore_ranges_already_covered_by_an_earlier_one(rig: Rig) -> None:
    sql = " ".join(rig.verified.tools["conferir_numeracao"].variants["saidas"].sql.split())
    assert COVERED_BY in sql
    # 1 a 100, depois 50 (dentro), 101 e 150: so falta 102 a 149
    assert _numbering_rows(rig, sql) == [["lacuna", 1, "A", 102, 149, 48]]
    # o pareamento so com a faixa vizinha (antes da correcao) acusava tambem 51 a 100
    old = sql.replace(COVERED_BY, "ultimo").replace("a.coberto", "a.ultimo")
    assert ["lacuna", 1, "A", 51, 100, 50] in _numbering_rows(rig, old)
