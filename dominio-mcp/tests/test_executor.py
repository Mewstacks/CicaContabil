from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.config import Limits, Settings
from dominio_mcp.executor import QueryEngine, args_hash, parse_spec
from dominio_mcp.freshness import PackStale
from dominio_mcp.odbc import DbError, Session, build_session
from dominio_mcp.pack import Pack
from dominio_mcp.query_spec import QueryRefused
from dominio_mcp.watchdog import QueryTimeout
from fake_odbc import Block, Fail, FakeDriver, Rows
from packs import build_demo_pack
from qhelp import POLICY

PLANS = Path(__file__).parent / "fixtures" / "plans"
CHEAP = (PLANS / "full_scan.txt").read_text(encoding="utf-8")
PATHOLOGICAL = (PLANS / "pathological_selfjoin.txt").read_text(encoding="utf-8")


class StubGuard:
    def __init__(self, pack: Pack, stale: str | None = None) -> None:
        self.pack = pack
        self.stale = stale
        self.checks = 0

    def precheck(self) -> Pack:
        if self.stale:
            raise PackStale(self.stale)
        return self.pack

    def check(self, execute: Any) -> Pack:
        self.checks += 1
        return self.pack


class Recorder:
    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, Any]]] = []

    def event(self, name: str, **fields: Any) -> None:
        self.events.append((name, fields))


def make(
    tmp_path: Path, **limits: int
) -> tuple[QueryEngine, FakeDriver, StubGuard, Recorder, Session]:
    pack = build_demo_pack(tmp_path)
    settings = Settings(dsn="contabil", home=tmp_path, limits=Limits(**limits))
    driver = FakeDriver()
    session = build_session(settings, driver=driver, confirm_seconds=0.3, lock_wait_seconds=0.3)
    guard, recorder = StubGuard(pack), Recorder()
    engine = QueryEngine(
        settings=settings, policy=POLICY, guard=guard, session=session, auditor=recorder
    )
    return engine, driver, guard, recorder, session


SPEC = {"tabela": "geempre", "colunas": ["codi_emp", "nome_emp"], "limite": 2}


def test_happy_path_estimates_then_runs_with_bound_parameters(tmp_path: Path) -> None:
    engine, driver, guard, rec, _ = make(tmp_path)
    driver.server.script += [
        Rows(["plan"], [(CHEAP,)]),
        Rows(["codi_emp", "nome_emp"], [(1, "ACME  "), (2, "BETA"), (3, "GAMA")]),
    ]
    spec = {**SPEC, "filtros": [{"coluna": "nome_emp", "op": "prefix", "valor": "A'; --"}]}
    out = engine.run(spec)
    assert out["linhas"] == [[1, "ACME"], [2, "BETA"]] and out["truncado"] is True
    assert out["custo_estimado"] == pytest.approx(1.0, rel=0.01) and out["pack"]
    assert guard.checks == 1
    plan_sql, plan_params = next(
        (s, p) for s, p in driver.server.log if s.startswith("SELECT PLAN")
    )
    assert plan_sql == "SELECT PLAN(?)" and "A''; --%" in plan_params[0]
    data = next((s, p) for s, p in driver.server.log if s.startswith("SELECT TOP"))
    assert "LIKE ? ESCAPE '!'" in data[0] and data[1] == ("A'; --%",)
    assert "A'; --" not in data[0]
    name, fields = rec.events[-1]
    assert name == "consulta" and fields["tool"] == "consulta_estruturada"
    assert fields["resultado"] == "ok"
    assert fields["linhas"] == 2 and fields["tabelas"] == ["geempre"]
    assert len(fields["args"]) == 16 and "A'" not in str(fields)


def test_refusals_before_the_database_never_touch_it(tmp_path: Path) -> None:
    engine, driver, guard, rec, session = make(tmp_path)
    cases = [
        ({"tabela": "nao_existe", "colunas": ["x"]}, "tabela_desconhecida"),
        ({"tabela": "efsaidas", "colunas": ["codi_sai"]}, "sem_filtro_de_empresa"),
        ({"tabela": "geempre", "colunas": ["ende_emp"]}, "coluna_bloqueada"),
        (
            {"tabela": "geempre", "colunas": ["codi_emp"], "sql": "SELECT 1"},
            "especificacao_invalida",
        ),
        (
            {
                "tabela": "efclientes",
                "colunas": ["codi_cli"],
                "filtros": [{"coluna": "nome_cli", "op": "=", "valor": "a\\b"}],
            },
            "valor_nao_codificavel",
        ),
    ]
    for spec, code in cases:
        with pytest.raises(QueryRefused) as exc:
            engine.run(spec)
        assert exc.value.code == code
    assert driver.server.log == [] and guard.checks == 0 and session.connected is False
    assert [f["resultado"] for _, f in rec.events] == [f"recusada:{c}" for _, c in cases]


def test_invalid_spec_message_lists_fields_without_echoing_values(tmp_path: Path) -> None:
    engine, *_ = make(tmp_path)
    with pytest.raises(QueryRefused) as exc:
        engine.run({"tabela": "geempre", "colunas": ["codi_emp"], "limite": "segredo-digitado"})
    assert "limite" in exc.value.message and "segredo-digitado" not in exc.value.message
    assert parse_spec({"tabela": "geempre", "colunas": ["a"]}).tabela == "geempre"


def test_pathological_plan_is_refused_and_the_query_never_runs(tmp_path: Path) -> None:
    engine, driver, _, rec, _ = make(tmp_path)
    driver.server.script += [
        Rows(["plan"], [(PATHOLOGICAL,)]),
        Rows(["codi_emp"], [(1,)]),
    ]
    with pytest.raises(QueryRefused) as exc:
        engine.run(SPEC)
    assert exc.value.code == "custo_estimado_alto"
    assert len(driver.server.script) == 1, "a consulta de verdade nao pode ter sido executada"
    assert rec.events[-1][1]["resultado"] == "recusada:custo_estimado_alto"


def test_stale_pack_stops_before_the_database(tmp_path: Path) -> None:
    engine, driver, guard, _, _ = make(tmp_path)
    guard.stale = "a politica de dados mudou"
    with pytest.raises(PackStale):
        engine.run(SPEC)
    assert driver.server.log == []


def test_one_admission_covers_freshness_plan_and_query(tmp_path: Path) -> None:
    engine, driver, _, _, _ = make(tmp_path, executions_per_minute=1)
    driver.server.script += [Rows(["plan"], [(CHEAP,)]), Rows(["codi_emp"], [(1,)])] * 2
    engine.run({"tabela": "geempre", "colunas": ["codi_emp"]})
    from dominio_mcp.budget import RateLimited

    with pytest.raises(RateLimited):
        engine.run({"tabela": "geempre", "colunas": ["codi_emp"]})


def test_database_errors_and_timeouts_propagate_without_driver_text(tmp_path: Path) -> None:
    engine, driver, _, rec, _ = make(tmp_path)
    driver.server.script += [
        Rows(["plan"], [(CHEAP,)]),
        Fail("42S02", "[42S02] Table 'SEGREDO' not found (-141)"),
    ]
    with pytest.raises(DbError) as exc:
        engine.run(SPEC)
    assert "SEGREDO" not in str(exc.value)
    assert rec.events[-1][1]["resultado"] == "erro:DbError"
    driver.server.script += [Rows(["plan"], [(CHEAP,)]), Block()]
    engine._session._settings = Settings(
        dsn="contabil", home=tmp_path, limits=Limits(query_timeout_seconds=1)
    )
    with pytest.raises(QueryTimeout):
        engine.run(SPEC)


def test_args_hash_ignores_key_order_but_follows_the_values() -> None:
    a = parse_spec({"tabela": "t", "colunas": ["a", "b"]})
    b = parse_spec({"colunas": ["a", "b"], "tabela": "t"})
    c = parse_spec({"tabela": "t", "colunas": ["a", "c"]})
    assert args_hash(a) == args_hash(b) != args_hash(c)
