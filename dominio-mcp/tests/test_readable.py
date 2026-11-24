from __future__ import annotations

import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.catalog import build_catalog
from dominio_mcp.odbc import DbError, DbErrorKind, RawResult
from dominio_mcp.readable import ReadableProbeError, probe_readable
from dominio_mcp.watchdog import QueryTimeout

FIXTURE = Path(__file__).parent / "fixtures" / "mini_catalog.json"
CATALOG = build_catalog(json.loads(FIXTURE.read_text(encoding="utf-8")))


def ok() -> RawResult:
    return RawResult((), [], False, 1.0, datetime.now(UTC))


def denied() -> DbError:
    return DbError(DbErrorKind.DENIED, "42000", -121)


class StubBatch:
    def __init__(self, outcomes: dict[str, Any], control: Any = None) -> None:
        self.outcomes = outcomes
        self.control = control if control is not None else denied()
        self.statements: list[str] = []

    def __call__(
        self, statements: Sequence[str], *, timeout_each: float = 10.0
    ) -> list[RawResult | DbError | QueryTimeout]:
        self.statements = list(statements)
        out: list[RawResult | DbError | QueryTimeout] = []
        for sql in statements:
            if "SYSUSERPERM" in sql:
                out.append(self.control)
                continue
            name = sql.split('"."', 1)[1].split('"', 1)[0]
            out.append(self.outcomes.get(name, ok()))
        return out


def test_probe_classifies_unreadable_objects_by_reason() -> None:
    batch = StubBatch(
        {
            "efsaidas": denied(),
            "geempre": DbError(DbErrorKind.NOT_FOUND, "42S02", -141),
            "vw_saidas": QueryTimeout("lento"),
            "EFMVSPRO": DbError(DbErrorKind.OTHER, "23000", -196),
        }
    )
    report = probe_readable(batch, CATALOG)
    assert report.readable == frozenset()
    assert report.unreadable == {
        "efsaidas": "sem_permissao",
        "geempre": "nao_encontrado",
        "vw_saidas": "timeout",
        "efmvspro": "outro:outro",
    }
    assert report.control_denied is True


def test_readable_objects_and_exact_statements() -> None:
    batch = StubBatch({"efsaidas": denied()})
    report = probe_readable(batch, CATALOG)
    assert report.readable == frozenset({"geempre", "efmvspro", "vw_saidas"})
    assert report.unreadable == {"efsaidas": "sem_permissao"}
    assert batch.statements[0] == "SELECT * FROM SYS.SYSUSERPERM WHERE 1=0"
    assert 'SELECT * FROM "bethadba"."EFMVSPRO" WHERE 1=0' in batch.statements
    assert len(batch.statements) == 1 + len(CATALOG.tables)
    assert all(s.endswith("WHERE 1=0") for s in batch.statements)


def test_probe_refuses_to_trust_a_control_that_was_not_denied() -> None:
    with pytest.raises(ReadableProbeError, match="controle"):
        probe_readable(StubBatch({}, control=ok()), CATALOG)
    with pytest.raises(ReadableProbeError, match="controle"):
        probe_readable(StubBatch({}, control=DbError(DbErrorKind.OTHER, "23000", -196)), CATALOG)


def test_probe_refuses_a_short_answer() -> None:
    def short(statements: Sequence[str], *, timeout_each: float = 10.0) -> list[RawResult]:
        return [ok()]

    with pytest.raises(ReadableProbeError, match="resposta"):
        probe_readable(short, CATALOG)  # type: ignore[arg-type]
