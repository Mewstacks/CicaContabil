from __future__ import annotations

import copy
import json
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp import buildpack
from dominio_mcp.buildpack import BuildReport, run_build
from dominio_mcp.catalog import CATALOG_QUERIES
from dominio_mcp.config import Settings
from dominio_mcp.odbc import DbError, DbErrorKind, RawResult
from dominio_mcp.pack import Pack, pack_store_for
from dominio_mcp.policy import PolicyClass
from dominio_mcp.readable import ReadableProbeError
from dominio_mcp.watchdog import QueryTimeout

FIXTURES = Path(__file__).parent / "fixtures"
BY_SQL = {sql: name for name, sql in CATALOG_QUERIES.items()}
EMPTY_COLUMNS = {
    "foreign_keys": [
        "foreign_table_id",
        "foreign_index_id",
        "primary_table_id",
        "primary_index_id",
    ],
}


def raw(name: str = "mini_catalog.json") -> dict[str, list[dict[str, Any]]]:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def result(columns: Sequence[str], rows: list[list[Any]]) -> RawResult:
    return RawResult(tuple(columns), rows, False, 1.0, datetime.now(UTC))


class StubSlot:
    def __init__(self, session: StubSession) -> None:
        self.session = session

    def execute(
        self, sql: str, params: tuple[Any, ...] = (), *, max_rows: int, timeout: float | None = None
    ) -> RawResult:
        if sql in BY_SQL:
            name = BY_SQL[sql]
            rows = self.session.data[name]
            if not rows:
                return result(EMPTY_COLUMNS[name], [])
            return result(list(rows[0]), [list(r.values()) for r in rows])
        if "PROPERTY('ProductVersion')" in sql:
            return result(["v", "n"], [["17.0.11.7312", "contabil"]])
        raise AssertionError(f"consulta inesperada: {sql[:60]}")


class StubSession:
    def __init__(
        self,
        data: dict[str, list[dict[str, Any]]],
        unreadable: set[str] = frozenset(),  # type: ignore[assignment]
        control_denied: bool = True,
    ) -> None:
        self.data = data
        self.unreadable = unreadable
        self.control_denied = control_denied
        self.slots = 0

    @contextmanager
    def slot(self) -> Iterator[StubSlot]:
        self.slots += 1
        yield StubSlot(self)

    def execute_batch(
        self, statements: Sequence[str], *, timeout_each: float = 10.0
    ) -> list[RawResult | DbError | QueryTimeout]:
        out: list[RawResult | DbError | QueryTimeout] = []
        for sql in statements:
            if "SYSUSERPERM" in sql:
                denied = DbError(DbErrorKind.DENIED, "42000", -121)
                out.append(denied if self.control_denied else result([], []))
                continue
            name = sql.split('"."', 1)[1].split('"', 1)[0]
            out.append(
                DbError(DbErrorKind.DENIED, "42000", -121)
                if name in self.unreadable
                else result([], [])
            )
        return out


def settings(tmp_path: Path) -> Settings:
    return Settings(dsn="contabil", home=tmp_path)


def open_pack(tmp_path: Path) -> Pack:
    pack = pack_store_for(settings(tmp_path)).open_current()
    assert pack is not None
    return pack


def test_first_build_without_acceptance_leaves_ordinary_columns_blocked(tmp_path: Path) -> None:
    session = StubSession(raw())
    report = run_build(settings(tmp_path), session)  # type: ignore[arg-type]
    assert isinstance(report, BuildReport)
    assert report.tables == 4 and report.foreign_keys == 2
    assert report.unclassified > 0 and report.accepted_added == 0 and report.accepted_total == 0
    assert report.server == "17.0.11.7312 / contabil"
    pack = open_pack(tmp_path)
    assert pack.meta.version == report.version
    col = pack.column("efsaidas", "vcon_sai")
    assert col is not None and col.klass is PolicyClass.NAO_CLASSIFICADA
    assert session.slots == 1


def test_accepting_moves_unclassified_columns_to_normal_but_not_sensitive_ones(
    tmp_path: Path,
) -> None:
    session = StubSession(raw())
    report = run_build(settings(tmp_path), session, accept=True)  # type: ignore[arg-type]
    assert report.unclassified == 0 and report.accepted_added > 0
    pack = open_pack(tmp_path)
    col = pack.column("efsaidas", "vcon_sai")
    assert col is not None and col.klass is PolicyClass.NORMAL
    doc = pack.column("geempre", "cgce_emp")
    assert doc is not None and doc.klass is PolicyClass.DOCUMENTO
    assert report.version == pack.meta.version


def test_new_columns_stay_blocked_until_a_new_acceptance(tmp_path: Path) -> None:
    run_build(settings(tmp_path), StubSession(raw()), accept=True)  # type: ignore[arg-type]
    data = copy.deepcopy(raw())
    data["columns"].append(
        {
            "table_id": 11,
            "column_id": 6,
            "column_name": "coluna_nova",
            "type": "numeric",
            "width": 15,
            "scale": 2,
            "nulls": "Y",
            "dflt": None,
            "object_id": 2999,
        }
    )
    report = run_build(settings(tmp_path), StubSession(data))  # type: ignore[arg-type]
    assert report.unclassified == 1 and report.accepted_added == 0
    pack = open_pack(tmp_path)
    new = pack.column("efsaidas", "coluna_nova")
    old = pack.column("efsaidas", "vcon_sai")
    assert new is not None and new.klass is PolicyClass.NAO_CLASSIFICADA
    assert old is not None and old.klass is PolicyClass.NORMAL
    again = run_build(settings(tmp_path), StubSession(data), accept=True)  # type: ignore[arg-type]
    assert again.unclassified == 0 and again.accepted_added == 1


def test_acceptance_of_removed_columns_is_dropped(tmp_path: Path) -> None:
    run_build(settings(tmp_path), StubSession(raw()), accept=True)  # type: ignore[arg-type]
    data = copy.deepcopy(raw())
    data["columns"] = [c for c in data["columns"] if c["column_name"] != "vcon_sai"]
    report = run_build(settings(tmp_path), StubSession(data))  # type: ignore[arg-type]
    assert ("efsaidas", "vcon_sai") not in open_pack(tmp_path).accepted()
    assert report.accepted_total == len(open_pack(tmp_path).accepted())


def test_unreadable_objects_are_recorded(tmp_path: Path) -> None:
    session = StubSession(raw(), unreadable={"efsaidas"})
    report = run_build(settings(tmp_path), session)  # type: ignore[arg-type]
    assert report.unreadable == 1
    row = open_pack(tmp_path).table("efsaidas")
    assert row is not None and row.queryable is False


def test_a_probe_with_an_untrusted_control_publishes_nothing(tmp_path: Path) -> None:
    session = StubSession(raw(), control_denied=False)
    with pytest.raises(ReadableProbeError):
        run_build(settings(tmp_path), session)  # type: ignore[arg-type]
    assert pack_store_for(settings(tmp_path)).current_path() is None


def test_same_inputs_publish_the_same_version_twice(tmp_path: Path) -> None:
    a = run_build(settings(tmp_path), StubSession(raw()), accept=True)  # type: ignore[arg-type]
    b = run_build(settings(tmp_path), StubSession(raw()))  # type: ignore[arg-type]
    assert a.version == b.version


def test_report_text_carries_numbers_only_never_catalog_text(tmp_path: Path) -> None:
    session = StubSession(raw("synthetic_catalog.json"))
    report = run_build(settings(tmp_path), session, accept=True)  # type: ignore[arg-type]
    text = report.render()
    assert "marker" not in text.lower() and "senha" not in text.lower()
    assert report.version[:12] in text and "colunas" in text
    assert report.size_bytes > 0 and report.seconds["total"] >= 0


def test_main_runs_with_a_session_factory_and_reports(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DOMINIO_MCP_HOME", str(tmp_path))
    monkeypatch.setattr(buildpack, "build_session", lambda s: StubSession(raw()))
    assert buildpack.main(["--aceitar"]) == 0
    out = capsys.readouterr().out
    assert "versao" in out and "tabelas" in out
    assert pack_store_for(settings(tmp_path)).current_path() is not None
