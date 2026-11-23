"""Repasse pelo agente (Fase 2, peca 3, A6 do rascunho): so L0 a L2, nunca L3, nunca SQL."""

from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp import cli
from dominio_mcp.config import Profile
from dominio_mcp.relay import (
    MAX_JOB_BYTES,
    MAX_RESULT_BYTES,
    RELAY_CONTRACT,
    Job,
    RelayRefused,
    parse_job,
    run_job,
)
from dominio_mcp.server import TOOL_NAMES
from fake_odbc import Rows
from test_server_contract import CHEAP, make_deps

JOB_ID = "job_0123456789abcdef"


def job(tool: str = "mapa_do_banco", args: dict[str, Any] | None = None, **extra: Any) -> bytes:
    body = {"contrato": RELAY_CONTRACT, "id": JOB_ID, "ferramenta": tool, "argumentos": args or {}}
    return json.dumps({**body, **extra}).encode("utf-8")


def test_a_valid_job_runs_the_tool_and_returns_the_envelope(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)
    out = run_job(deps, job("mapa_do_banco"))
    assert out["contrato"] == RELAY_CONTRACT and out["id"] == JOB_ID and out["ok"] is True
    assert out["resultado"]["banco"].startswith("Dominio")


def test_l2_goes_through_plan_and_the_policy_like_any_other_channel(tmp_path: Path) -> None:
    deps, driver = make_deps(tmp_path)
    driver.server.script += [Rows(["plan"], [(CHEAP,)]), Rows(["codi_emp"], [(1,), (2,)])]
    query = {"tabela": "geempre", "colunas": ["codi_emp"], "limite": 5}
    out = run_job(deps, job("consulta_estruturada", {"consulta": query}))
    assert out["ok"] is True and out["resultado"]["linhas"] == [[1], [2]]
    blocked = {"tabela": "geempre", "colunas": ["ende_emp"]}
    refused = run_job(deps, job("consulta_estruturada", {"consulta": blocked}))
    assert refused["ok"] is False and refused["erro"]["codigo"] == "coluna_bloqueada"


@pytest.mark.parametrize(
    "tool", ["sql_somente_leitura", "SQL", "executar_sql", "", "empresas;DROP"]
)
def test_there_is_no_way_to_name_l3_or_any_unknown_tool(tmp_path: Path, tool: str) -> None:
    deps, driver = make_deps(tmp_path)
    out = run_job(deps, job(tool, {"sql": "SELECT 1"}))
    assert out["ok"] is False and out["erro"]["codigo"] == "trabalho_invalido"
    assert driver.server.log == []


def test_l3_stays_closed_even_with_local_profile_and_raw_sql_in_the_settings(
    tmp_path: Path,
) -> None:
    deps, driver = make_deps(tmp_path, profile=Profile.LOCAL, raw_sql=True)
    assert deps.settings.raw_sql_enabled is True
    out = run_job(deps, job("sql_somente_leitura", {"sql": "SELECT codi_emp FROM geempre"}))
    assert out["ok"] is False and out["erro"]["codigo"] == "trabalho_invalido"
    assert driver.server.log == []
    assert "sql_somente_leitura" not in TOOL_NAMES


@pytest.mark.parametrize(
    "field", ["sql", "consulta_sql", "query", "comando", "perfil", "perfil_local"]
)
def test_the_job_has_no_field_that_could_carry_sql_or_a_profile(tmp_path: Path, field: str) -> None:
    deps, driver = make_deps(tmp_path)
    out = run_job(deps, job("empresas", {}, **{field: "SELECT 1"}))
    assert out["ok"] is False and out["erro"]["codigo"] == "trabalho_invalido"
    assert driver.server.log == []


@pytest.mark.parametrize(
    ("raw", "code"),
    [
        (b"nao e json", "json_invalido"),
        (b"[]", "trabalho_invalido"),
        (b"\xff\xfe", "json_invalido"),
        (
            json.dumps({"contrato": 2, "id": JOB_ID, "ferramenta": "empresas"}).encode(),
            "contrato_desconhecido",
        ),
        (json.dumps({"id": JOB_ID, "ferramenta": "empresas"}).encode(), "contrato_desconhecido"),
        (
            json.dumps({"contrato": 1, "id": "curto", "ferramenta": "empresas"}).encode(),
            "trabalho_invalido",
        ),
        (
            json.dumps({"contrato": 1, "id": "a b c d e f g h", "ferramenta": "empresas"}).encode(),
            "trabalho_invalido",
        ),
        (
            json.dumps(
                {"contrato": 1, "id": JOB_ID, "ferramenta": "empresas", "argumentos": []}
            ).encode(),
            "trabalho_invalido",
        ),
        pytest.param(b"x" * (MAX_JOB_BYTES + 1), "trabalho_grande_demais", id="grande"),
    ],
)
def test_malformed_jobs_are_refused_before_any_call(tmp_path: Path, raw: bytes, code: str) -> None:
    deps, driver = make_deps(tmp_path)
    out = run_job(deps, raw)
    assert out["ok"] is False and out["erro"]["codigo"] == code
    assert driver.server.log == []


def test_deeply_nested_arguments_are_refused() -> None:
    nested: Any = {}
    cursor = nested
    for _ in range(20):
        cursor["a"] = {}
        cursor = cursor["a"]
    with pytest.raises(RelayRefused) as refused:
        parse_job(job("consulta_estruturada", {"consulta": nested}))
    assert refused.value.code == "argumentos_fundos_demais"


def test_a_refusal_never_raises_and_keeps_the_job_id_when_it_had_one(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)
    out = run_job(deps, job("descrever_tabela", {"tabela": "nao_existe"}))
    assert out["id"] == JOB_ID and out["ok"] is False
    assert out["erro"]["codigo"] == "tabela_desconhecida"
    bad = run_job(deps, b"{}")
    assert bad["id"] is None and bad["ok"] is False


def test_the_envelope_is_bounded(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)
    out = run_job(deps, job("descrever_tabela", {"tabela": "efsaidas"}))
    assert len(json.dumps(out, ensure_ascii=False).encode("utf-8")) <= MAX_RESULT_BYTES


def test_the_job_model_is_frozen_and_strict() -> None:
    parsed = parse_job(job("empresas", {"limite": 3}))
    assert isinstance(parsed, Job) and parsed.argumentos == {"limite": 3}
    with pytest.raises(Exception, match=r"frozen|immutable"):
        parsed.ferramenta = "mapa_do_banco"  # type: ignore[misc]


def test_cli_relay_job_reads_stdin_and_writes_one_json_line(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DOMINIO_MCP_HOME", str(tmp_path))
    monkeypatch.setattr("sys.stdin", type("S", (), {"buffer": io.BytesIO(b"nao e json")})())
    assert cli.main(["relay-job"]) == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 1
    out = json.loads(lines[0])
    assert out["ok"] is False and out["erro"]["codigo"] == "json_invalido"


def test_cli_relay_job_refuses_an_oversized_stdin_without_reading_it_all(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    monkeypatch.setenv("DOMINIO_MCP_HOME", str(tmp_path))
    stream = io.BytesIO(b"x" * (MAX_JOB_BYTES * 4))
    monkeypatch.setattr("sys.stdin", type("S", (), {"buffer": stream})())
    assert cli.main(["relay-job"]) == 0
    assert json.loads(capsys.readouterr().out)["erro"]["codigo"] == "trabalho_grande_demais"
    assert stream.tell() == MAX_JOB_BYTES + 1
