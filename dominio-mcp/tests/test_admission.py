from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.admission import PLAN_SQL, PlanEstimate, admit, estimate_plan, parse_plan
from dominio_mcp.odbc import RawResult
from dominio_mcp.query_spec import QueryRefused

PLANS = Path(__file__).parent / "fixtures" / "plans"
OK_HEAD = "( Plan [ Estimated cost: 1, Estimated rows: 1"


def plan(name: str) -> str:
    return (PLANS / name).read_text(encoding="utf-8")


def raw(*rows: list[Any]) -> RawResult:
    return RawResult(("plan",), list(rows), False, 1.0, datetime.now(UTC))


@pytest.mark.parametrize(
    ("file", "cost", "rows"),
    [
        ("lookup.txt", 1e-05, 1.0),
        ("indexed_aggregate.txt", 9.4314e-06, 2.0),
        ("full_scan.txt", 1.003, 1.0),
        ("pathological_selfjoin.txt", 2.3505e06, 1.0),
    ],
)
def test_recorded_real_plans_are_parsed(file: str, cost: float, rows: float) -> None:
    estimate = parse_plan(plan(file))
    assert estimate.cost == pytest.approx(cost)
    assert estimate.rows == pytest.approx(rows)


def test_real_plan_costs_order_the_way_the_budget_assumes() -> None:
    cheap = parse_plan(plan("indexed_aggregate.txt")).cost
    scan = parse_plan(plan("full_scan.txt")).cost
    patho = parse_plan(plan("pathological_selfjoin.txt")).cost
    assert cheap < scan < 10 < patho


def test_budget_admits_normal_queries_and_refuses_the_pathological_one() -> None:
    for name in ("lookup.txt", "indexed_aggregate.txt", "full_scan.txt"):
        admit(parse_plan(plan(name)), cost_budget=10, rows_budget=1_000_000)
    with pytest.raises(QueryRefused) as exc:
        admit(parse_plan(plan("pathological_selfjoin.txt")), cost_budget=10, rows_budget=1_000_000)
    assert exc.value.code == "custo_estimado_alto"
    assert "codi_emp" in exc.value.message and exc.value.details["limite"] == 10


def test_row_estimate_has_its_own_limit() -> None:
    with pytest.raises(QueryRefused) as exc:
        admit(PlanEstimate(cost=1.0, rows=5e6), cost_budget=10, rows_budget=1_000_000)
    assert exc.value.code == "linhas_estimadas_demais"


@pytest.mark.parametrize(
    "text",
    [
        None,
        "",
        5,
        "nao e um plano",
        "( Plan [ Estimated rows: 1, Estimated cost: 1 ] )",
        "( Plan [ Estimated cost: abc, Estimated rows: 1",
        "( Plan [ Estimated cost: nan, Estimated rows: 1",
        "( Plan [ Estimated cost: inf, Estimated rows: 1",
        "( Plan [ Estimated cost: -1, Estimated rows: 1",
        OK_HEAD + " ]" + "x" * 20_000,
        "SELECT 1; " + OK_HEAD,
    ],
)
def test_odd_plan_answers_are_refused(text: object) -> None:
    with pytest.raises(QueryRefused) as exc:
        parse_plan(text)
    assert exc.value.code == "plano_invalido"


def test_estimate_binds_the_inner_sql_as_a_parameter_never_inline() -> None:
    calls: list[tuple[str, tuple[Any, ...], int, float | None]] = []

    def execute(
        sql: str, params: tuple[Any, ...] = (), *, max_rows: int, timeout: float | None = None
    ) -> RawResult:
        calls.append((sql, params, max_rows, timeout))
        return raw([plan("full_scan.txt")])

    inner = "SELECT 'a''b' FROM t; -- x"
    estimate = estimate_plan(execute, inner)
    assert estimate.cost == pytest.approx(1.003)
    assert calls == [(PLAN_SQL, (inner,), 2, 10.0)]
    assert PLAN_SQL == "SELECT PLAN(?)" and inner not in PLAN_SQL


def test_estimate_refuses_malformed_result_shapes() -> None:
    def two_rows(sql: str, params: tuple[Any, ...] = (), **kw: Any) -> RawResult:
        return raw(["a"], ["b"])

    def no_rows(sql: str, params: tuple[Any, ...] = (), **kw: Any) -> RawResult:
        return raw()

    def two_cols(sql: str, params: tuple[Any, ...] = (), **kw: Any) -> RawResult:
        return raw(["a", "b"])

    for executor in (two_rows, no_rows, two_cols):
        with pytest.raises(QueryRefused):
            estimate_plan(executor, "SELECT 1")
