"""Ensaio de carga (A11, T4.9): so roda com a janela autorizada pelo dono.

Criterios em `reports/carga.md` (escritos antes do ensaio). Exige DOMINIO_MCP_LIVE=1 **e**
DOMINIO_MCP_LOAD_WINDOW=1. Leitura somente de agregados; o pack e temporario, com aceite de poucas
colunas, e nao mexe no pack do escritorio.
"""

from __future__ import annotations

import os
import statistics
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.admission import estimate_plan
from dominio_mcp.catalog import build_catalog, extract_raw
from dominio_mcp.compiler import compile_query
from dominio_mcp.config import Settings
from dominio_mcp.executor import QueryEngine, parse_spec
from dominio_mcp.freshness import FreshnessGuard, make_rehasher
from dominio_mcp.odbc import Session, build_session, load_driver, open_connection
from dominio_mcp.overlay import load_overlay
from dominio_mcp.pack import build_pack, pack_store_for
from dominio_mcp.policy import load_policy
from dominio_mcp.query_spec import validate_query

pytestmark = pytest.mark.live

DSN = os.environ.get("DOMINIO_MCP_DSN", "contabil")
ACCEPTED = frozenset(
    {
        ("geempre", "codi_emp"),
        ("efsaidas", "codi_emp"),
        ("efsaidas", "dsai_sai"),
        ("efsaidas", "vcon_sai"),
        ("efsaidas", "codi_sai"),
    }
)
PROBE_SQL = 'SELECT TOP 1 "codi_emp" FROM "bethadba"."geempre" WHERE "codi_emp" = ?'
BASELINE_SAMPLES = 50
DURING_SAMPLES = 30
FACTOR = 2.0
LIMIT_MS = 250.0


@pytest.fixture(scope="module", autouse=True)
def window_is_authorized() -> None:
    if os.environ.get("DOMINIO_MCP_LOAD_WINDOW") != "1":
        pytest.skip("ensaio de carga: defina DOMINIO_MCP_LOAD_WINDOW=1 so com a janela autorizada")


class Rig:
    def __init__(self, home: Path) -> None:
        self.settings = Settings(dsn=DSN, home=home)
        self.session: Session = build_session(self.settings, lock_wait_seconds=60.0)
        self.policy, self.overlay = load_policy(), load_overlay()
        with self.session.slot() as slot:
            self.catalog = build_catalog(extract_raw(slot.execute))
        store = pack_store_for(self.settings)
        built = store.new_build_path()
        meta = build_pack(
            built,
            catalog=self.catalog,
            policy=self.policy,
            overlay=self.overlay,
            accepted=ACCEPTED,
            dsn=DSN,
        )
        store.publish(built, meta)
        self.guard = FreshnessGuard(
            store,
            policy_sha=self.policy.sha,
            overlay_sha=self.overlay.sha,
            rehash=make_rehasher("bethadba"),
        )
        self.engine = QueryEngine(
            settings=self.settings, policy=self.policy, guard=self.guard, session=self.session
        )

    def company_codes(self) -> list[int]:
        """Menor, mediana e maior empresa por numero de notas de saida (so codigos, sem nome)."""
        with self.session.slot() as slot:
            result = slot.execute(
                'SELECT "codi_emp", COUNT(*) AS n FROM "bethadba"."efsaidas" '
                'GROUP BY "codi_emp" ORDER BY n',
                max_rows=5000,
                timeout=60,
            )
        codes = [int(r[0]) for r in result.rows if isinstance(r[0], int | float)]
        return [codes[0], codes[len(codes) // 2], codes[-1]]


@pytest.fixture(scope="module")
def rig(tmp_path_factory: pytest.TempPathFactory) -> Iterator[Rig]:
    instance = Rig(tmp_path_factory.mktemp("load"))
    try:
        yield instance
    finally:
        instance.session.close()


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[max(0, round(0.95 * len(ordered)) - 1)]


def probe_loop(code: int, stop: threading.Event, out: list[float], limit: int) -> None:
    driver = load_driver()
    conn = open_connection(driver, DSN)
    try:
        cursor = conn.raw.cursor()
        while not stop.is_set() and len(out) < limit:
            started = time.perf_counter()
            cursor.execute(PROBE_SQL, code)
            cursor.fetchall()
            out.append((time.perf_counter() - started) * 1000)
            time.sleep(0.02)
    finally:
        conn.close()


def spec(code: int, start: str, end: str) -> dict[str, Any]:
    return {
        "tabela": "efsaidas",
        "agregacoes": [
            {"funcao": "count", "coluna": "*", "alias": "n"},
            {"funcao": "sum", "coluna": "vcon_sai", "alias": "total"},
        ],
        "filtros": [
            {"coluna": "codi_emp", "op": "=", "valor": code},
            {"coluna": "dsai_sai", "op": "between", "valor": [start, end]},
        ],
    }


def test_estimate_versus_real_and_interference(rig: Rig) -> None:
    small, medium, large = rig.company_codes()
    windows = [
        ("2025-01-01", "2025-01-31"),
        ("2025-01-01", "2025-03-31"),
        ("2025-01-01", "2025-12-31"),
        ("2024-12-01", "2025-12-31"),
    ]
    rows: list[tuple[str, float, float]] = []
    for code, label in ((small, "pequena"), (medium, "media"), (large, "grande")):
        for start, end in windows:
            parsed = parse_spec(spec(code, start, end))
            pack = rig.guard.pack()
            compiled = compile_query(
                validate_query(parsed, pack, rig.settings, rig.policy), pack.meta.owner
            )
            with rig.session.slot() as slot:
                estimate = estimate_plan(slot.execute, compiled.literal_sql)
            started = time.perf_counter()
            rig.engine.run(spec(code, start, end))
            real_ms = (time.perf_counter() - started) * 1000
            rows.append((f"{label} {start}..{end}", estimate.cost, real_ms))
    print("\n| consulta | custo estimado | tempo real (ms) |\n|---|---|---|")
    for label, cost, real in rows:
        print(f"| {label} | {cost:.4g} | {real:.0f} |")
    assert len(rows) >= 10
    assert max(real for _, _, real in rows) < 30_000, "C6: consulta admitida passou de 30 s"

    heavy = max(rows, key=lambda r: r[1])
    heavy_code = large
    baseline: list[float] = []
    stop = threading.Event()
    probe_loop(heavy_code, stop, baseline, BASELINE_SAMPLES)
    during: list[float] = []
    worker = threading.Thread(
        target=probe_loop, args=(heavy_code, stop, during, DURING_SAMPLES), daemon=True
    )
    worker.start()
    deadline = time.monotonic() + 120
    while len(during) < DURING_SAMPLES and time.monotonic() < deadline:
        rig.engine.run(spec(heavy_code, "2024-12-01", "2025-12-31"))
    stop.set()
    worker.join(10)
    base95, during95 = p95(baseline), p95(during)
    print(
        f"\nbase p50={statistics.median(baseline):.1f} ms p95={base95:.1f} ms | "
        f"durante p95={during95:.1f} ms (amostras: {len(baseline)} e {len(during)}) | "
        f"consulta mais cara estimada: {heavy[0]} custo {heavy[1]:.4g}"
    )
    assert len(baseline) >= BASELINE_SAMPLES and len(during) >= DURING_SAMPLES
    assert during95 <= max(FACTOR * base95, 1.0) and during95 <= LIMIT_MS, "C1: interferencia"
