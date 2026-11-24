from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp.audit import MAX_ITEMS, MAX_TEXT, JsonlAuditor


def lines(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_event_is_one_json_line_with_time_and_allowed_fields(tmp_path: Path) -> None:
    auditor = JsonlAuditor(tmp_path / "audit", clock=lambda: 1_763_735_400.0)
    auditor.event(
        "consulta",
        tool="consulta_estruturada",
        args="abc123",
        tabelas=["efsaidas", "geempre"],
        resultado="ok",
        linhas=12,
        truncado=False,
        latencia_ms=48,
        custo=0.4653,
        pack="deadbeef0000",
    )
    (record,) = lines(auditor.path)
    assert record["evento"] == "consulta" and record["ts"].startswith("2025-11-21T")
    assert record["tabelas"] == ["efsaidas", "geempre"] and record["linhas"] == 12
    assert record["truncado"] is False and record["custo"] == 0.4653
    assert "descartados" not in record


def test_unknown_fields_are_dropped_and_only_their_names_are_recorded(tmp_path: Path) -> None:
    auditor = JsonlAuditor(tmp_path)
    auditor.event(
        "consulta",
        resultado="ok",
        linha=["11.222.333/0001-81", "ACME"],
        valores={"cnpj": "11222333000181"},
        filtro="x' OR 1=1",
    )
    (record,) = lines(auditor.path)
    assert record["descartados"] == ["filtro", "linha", "valores"]
    text = json.dumps(record)
    assert "11222333" not in text and "ACME" not in text and "OR 1=1" not in text


def test_long_text_is_cut_and_nested_values_are_removed(tmp_path: Path) -> None:
    auditor = JsonlAuditor(tmp_path)
    auditor.event(
        "x",
        resultado="y" * 500,
        tabelas=[f"t{i}" for i in range(100)],
        tipo={"a": 1},
        custo=float("nan"),
    )
    (record,) = lines(auditor.path)
    assert len(record["resultado"]) == MAX_TEXT and record["resultado"].endswith("…")
    assert len(record["tabelas"]) == MAX_ITEMS
    assert record["tipo"] == "<removido>" and record["custo"] is None


def test_rotation_keeps_a_bounded_number_of_files(tmp_path: Path) -> None:
    auditor = JsonlAuditor(tmp_path, max_bytes=400, keep=3)
    for i in range(60):
        auditor.event("e", resultado=f"ok-{i}", tool="t")
    names = sorted(p.name for p in tmp_path.glob("audit*.jsonl"))
    assert names == ["audit.1.jsonl", "audit.2.jsonl", "audit.3.jsonl", "audit.jsonl"]
    assert all(p.stat().st_size <= 600 for p in tmp_path.glob("audit*.jsonl"))
    assert lines(auditor.path)[-1]["resultado"] == "ok-59"


def test_concurrent_writers_never_interleave_lines(tmp_path: Path) -> None:
    auditor = JsonlAuditor(tmp_path, max_bytes=10_000_000)

    def work(n: int) -> None:
        for i in range(20):
            auditor.event("e", tool=f"t{n}", resultado=f"r{i}")

    threads = [threading.Thread(target=work, args=(n,)) for n in range(25)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(lines(auditor.path)) == 500


def test_write_failure_never_raises_and_warns_once(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    blocker = tmp_path / "ocupado"
    blocker.write_text("arquivo no lugar da pasta", encoding="utf-8")
    auditor = JsonlAuditor(blocker / "audit")
    auditor.event("e", tool="t")
    auditor.event("e", tool="t")
    err = capsys.readouterr().err
    assert err.count("nao consegui gravar a auditoria") == 1
