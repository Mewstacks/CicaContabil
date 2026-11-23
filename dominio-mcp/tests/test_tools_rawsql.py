"""Ferramenta L3 no servidor (M9, A5, A10): registro, despacho, politica e auditoria."""

# ruff: noqa: S608
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
from mcp.client import Client

from dominio_mcp.config import Profile
from dominio_mcp.server import build_server
from dominio_mcp.tools_rawsql import TOOL_NAME, raw_sql_available, run_raw_sql
from dominio_mcp.verified import ToolDisabled
from fake_odbc import Rows
from test_server_contract import CHEAP, body, call, make_deps, run


def names_of(deps: Any, profile: Profile) -> list[str]:
    async def go() -> list[str]:
        async with Client(build_server(deps, profile)) as client:
            return [t.name for t in (await client.list_tools()).tools]

    return run(go)


@pytest.mark.parametrize(
    ("settings_profile", "raw_sql", "cli_profile", "listed"),
    [
        (Profile.REMOTE, True, Profile.REMOTE, False),
        (
            Profile.REMOTE,
            True,
            Profile.LOCAL,
            False,
        ),  # o processo e remote: o perfil da CLI nao basta
        (Profile.LOCAL, False, Profile.LOCAL, False),
        (Profile.LOCAL, True, Profile.REMOTE, False),
        (Profile.LOCAL, True, Profile.LOCAL, True),
    ],
)
def test_the_tool_exists_only_for_local_profile_with_the_flag(
    tmp_path: Path, settings_profile: Profile, raw_sql: bool, cli_profile: Profile, listed: bool
) -> None:
    deps, _ = make_deps(tmp_path, profile=settings_profile, raw_sql=raw_sql)
    assert (TOOL_NAME in names_of(deps, cli_profile)) is listed
    assert raw_sql_available(deps.settings, cli_profile) is listed


def test_dispatch_refuses_again_even_if_someone_reaches_the_function(tmp_path: Path) -> None:
    deps, driver = make_deps(tmp_path, profile=Profile.LOCAL, raw_sql=True)
    with pytest.raises(ToolDisabled):
        run_raw_sql(deps.engine, Profile.REMOTE, "SELECT codi_emp FROM geempre")
    remote, _ = make_deps(tmp_path / "r", profile=Profile.REMOTE, raw_sql=True)
    with pytest.raises(ToolDisabled):
        run_raw_sql(remote.engine, Profile.LOCAL, "SELECT codi_emp FROM geempre")
    assert driver.server.log == []  # nada chegou ao banco


def test_the_tool_is_annotated_read_only(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path, profile=Profile.LOCAL, raw_sql=True)

    async def go() -> Any:
        async with Client(build_server(deps, Profile.LOCAL)) as client:
            return next(t for t in (await client.list_tools()).tools if t.name == TOOL_NAME)

    tool = run(go)
    ann = tool.annotations
    assert (ann.read_only_hint, ann.destructive_hint, ann.open_world_hint) == (True, False, False)
    assert tool.input_schema["required"] == ["sql"]


def test_a_legitimate_select_runs_through_plan_and_comes_back_shaped(tmp_path: Path) -> None:
    deps, driver = make_deps(tmp_path, profile=Profile.LOCAL, raw_sql=True)
    driver.server.script += [
        Rows(["plan"], [(CHEAP,)]),
        Rows(["codi_emp", "nome_emp"], [(1, "ACME"), (2, "BETA")]),
    ]
    result = run(
        lambda: call(
            deps,
            TOOL_NAME,
            {"sql": "SELECT TOP 5 codi_emp, nome_emp FROM geempre WHERE codi_emp >= 1"},
            Profile.LOCAL,
        )
    )
    out = body(result)
    assert not result.is_error and out["linhas"] == [[1, "ACME"], [2, "BETA"]]
    assert out["consistencia"] == "leitura_nao_confirmada" and out["tabelas"] == ["geempre"]
    executed = [sql for sql, _params in driver.server.log if "geempre" in sql]
    assert executed
    session_setup = "SET TEMPORARY OPTION isolation_level = 0"
    assert all(
        sql == session_setup or sql.lstrip().upper().startswith("SELECT")
        for sql, _ in driver.server.log
    )


@pytest.mark.parametrize(
    ("sql", "code"),
    [
        ("DROP TABLE geempre", "sql_recusado"),
        ("SELECT codi_emp FROM geempre; DELETE FROM geempre", "sql_recusado"),
        ("SELECT * FROM geempre", "sql_recusado"),
        ("SELECT ende_emp FROM geempre", "coluna_bloqueada"),
        ("SELECT nome FROM gecertificadosdigitais", "tabela_bloqueada"),
        ("SELECT g.codi_emp FROM geempre g JOIN efsaidas s ON g.codi_emp = s.codi_sai",
         "juncao_diferente_da_fk"),
    ],
)  # fmt: skip
def test_refusals_come_back_as_structured_errors_and_never_reach_the_database(
    tmp_path: Path, sql: str, code: str
) -> None:
    deps, driver = make_deps(tmp_path, profile=Profile.LOCAL, raw_sql=True)
    result = run(lambda: call(deps, TOOL_NAME, {"sql": sql}, Profile.LOCAL))
    assert result.is_error and body(result)["erro"]["codigo"] == code
    assert driver.server.log == []


def test_audit_records_the_tool_and_a_hash_never_the_sql_text(tmp_path: Path) -> None:
    deps, driver = make_deps(tmp_path, profile=Profile.LOCAL, raw_sql=True)
    driver.server.script += [Rows(["plan"], [(CHEAP,)]), Rows(["codi_emp"], [(1,)])]
    secret_filter = "SEGREDINHO-DO-FILTRO"
    sql = f"SELECT codi_emp FROM geempre WHERE nome_emp = '{secret_filter}'"
    run(lambda: call(deps, TOOL_NAME, {"sql": sql}, Profile.LOCAL))
    text = (tmp_path / "audit" / "audit.jsonl").read_text(encoding="utf-8")
    events = [json.loads(line) for line in text.splitlines()]
    assert any(e.get("tool") == TOOL_NAME for e in events)
    assert secret_filter not in text and "DROP" not in text
