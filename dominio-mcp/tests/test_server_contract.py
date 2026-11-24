"""Contrato do servidor MCP (A10): ferramentas, anotacoes, erros, perfil e auditoria."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

import anyio
from mcp.client import Client

from dominio_mcp.audit import JsonlAuditor
from dominio_mcp.config import Limits, Profile, Settings
from dominio_mcp.executor import QueryEngine
from dominio_mcp.odbc import build_session
from dominio_mcp.overlay import load_overlay
from dominio_mcp.pack import Pack
from dominio_mcp.server import (
    INSTRUCTIONS,
    TOOL_NAMES,
    Deps,
    build_server,
    compact,
    to_error,
)
from dominio_mcp.tools_schema import SchemaTools
from dominio_mcp.verified import VerifiedRunner, load_shipped_tools
from fake_odbc import Fail, FakeDriver, Rows
from packs import build_demo_pack
from qhelp import POLICY

PLANS = Path(__file__).parent / "fixtures" / "plans"
CHEAP = (PLANS / "full_scan.txt").read_text(encoding="utf-8")


class StubGuard:
    stale_reason: str | None = None

    def __init__(self, pack: Pack) -> None:
        self._pack = pack

    def pack(self) -> Pack:
        return self._pack

    def precheck(self) -> Pack:
        return self._pack

    def check(self, execute: Any) -> Pack:
        return self._pack


def make_deps(
    tmp_path: Path, *, profile: Profile = Profile.REMOTE, raw_sql: bool = False
) -> tuple[Deps, FakeDriver]:
    pack = build_demo_pack(tmp_path)
    settings = Settings(
        dsn="contabil", home=tmp_path, limits=Limits(), profile=profile, raw_sql=raw_sql
    )
    overlay = load_overlay()
    auditor = JsonlAuditor(tmp_path / "audit")
    driver = FakeDriver()
    session = build_session(settings, driver=driver, auditor=auditor, lock_wait_seconds=0.3)
    guard = StubGuard(pack)
    engine = QueryEngine(
        settings=settings,
        policy=POLICY,
        guard=guard,
        session=session,
        auditor=auditor,  # type: ignore[arg-type]
    )
    deps = Deps(
        settings=settings,
        policy=POLICY,
        overlay=overlay,
        guard=guard,  # type: ignore[arg-type]
        session=session,
        auditor=auditor,
        engine=engine,
        schema=SchemaTools(guard.pack, lambda: guard.stale_reason, overlay),
        verified=VerifiedRunner(engine, load_shipped_tools(), overlay),
    )
    return deps, driver


def run[T](coro_fn: Callable[[], Awaitable[T]]) -> T:
    return anyio.run(coro_fn)  # type: ignore[arg-type]


async def call(deps: Deps, name: str, args: dict[str, Any], profile: Profile = Profile.REMOTE):  # type: ignore[no-untyped-def]
    async with Client(build_server(deps, profile)) as client:
        return await client.call_tool(name, args)


def body(result: Any) -> dict[str, Any]:
    return json.loads(result.content[0].text)  # type: ignore[no-any-return]


def test_tools_are_the_documented_set_in_a_stable_order(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)

    async def go() -> tuple[list[str], list[str]]:
        async with Client(build_server(deps)) as client:
            first = [t.name for t in (await client.list_tools()).tools]
            second = [t.name for t in (await client.list_tools()).tools]
            return first, second

    first, second = run(go)
    assert tuple(first) == TOOL_NAMES and first == second and len(first) <= 16


def test_every_tool_is_annotated_read_only_and_described(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)

    async def go() -> list[Any]:
        async with Client(build_server(deps)) as client:
            return list((await client.list_tools()).tools)

    for tool in run(go):
        ann = tool.annotations
        assert ann is not None, tool.name
        assert (ann.read_only_hint, ann.destructive_hint, ann.open_world_hint) == (
            True,
            False,
            False,
        )
        assert tool.description and len(tool.description) > 20
        assert tool.input_schema["type"] == "object"
    schema = {t.name: t.input_schema for t in run(go)}
    assert "consulta" in schema["consulta_estruturada"]["properties"]
    assert set(schema["movimento_fiscal"]["required"]) == {"codi_emp", "inicio", "fim"}
    assert set(schema["conferir_numeracao"]["required"]) == {
        "codi_emp",
        "documento",
        "inicio",
        "fim",
    }


def test_instructions_are_self_contained_in_the_first_512_characters(tmp_path: Path) -> None:
    head = INSTRUCTIONS[:512]
    for needle in ("SOMENTE LEITURA", "mapa_do_banco", "consulta_estruturada", "Nunca invente"):
        assert needle in head
    assert len(INSTRUCTIONS) <= 700
    deps, _ = make_deps(tmp_path)

    async def go() -> str | None:
        async with Client(build_server(deps)) as client:
            return client.instructions

    assert run(go) == INSTRUCTIONS


def test_results_are_compact_json_text_within_the_caps(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)
    result = run(lambda: call(deps, "mapa_do_banco", {}))
    assert not result.is_error and len(result.content) == 1
    text = result.content[0].text
    assert "\n" not in text and text == compact(json.loads(text))
    assert len(text.encode("utf-8")) <= 3 * 1024
    search = run(lambda: call(deps, "buscar_esquema", {"consulta": "notas fiscais de saida"}))
    assert body(search)["resultados"][0]["tabela"] == "efsaidas"
    described = run(lambda: call(deps, "descrever_tabela", {"tabela": "efsaidas"}))
    assert len(described.content[0].text.encode("utf-8")) <= 12 * 1024


def test_errors_are_structured_with_stable_codes(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)
    unknown = run(lambda: call(deps, "descrever_tabela", {"tabela": "nao_existe"}))
    assert unknown.is_error and body(unknown)["erro"]["codigo"] == "tabela_desconhecida"
    blocked = run(
        lambda: call(
            deps,
            "consulta_estruturada",
            {"consulta": {"tabela": "geempre", "colunas": ["ende_emp"]}},
        )
    )
    err = body(blocked)["erro"]
    assert blocked.is_error and err["codigo"] == "coluna_bloqueada"
    assert err["detalhes"]["motivo"] == "pessoal_nao_liberado:endereco"
    disabled = run(lambda: call(deps, "empresas", {}))
    assert disabled.is_error and body(disabled)["erro"]["codigo"] == "ferramenta_desligada"


def test_a_successful_l2_query_goes_through_plan_and_returns_shaped_rows(tmp_path: Path) -> None:
    deps, driver = make_deps(tmp_path)
    driver.server.script += [
        Rows(["plan"], [(CHEAP,)]),
        Rows(["codi_emp", "nome_emp"], [(1, "ACME"), (2, "BETA")]),
    ]
    result = run(
        lambda: call(
            deps,
            "consulta_estruturada",
            {"consulta": {"tabela": "geempre", "colunas": ["codi_emp", "nome_emp"], "limite": 5}},
        )
    )
    out = body(result)
    assert not result.is_error and out["linhas"] == [[1, "ACME"], [2, "BETA"]]
    assert out["consistencia"] == "leitura_nao_confirmada" and out["tabelas"] == ["geempre"]


def test_unexpected_exceptions_become_a_generic_error_without_their_text(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)

    def boom() -> dict[str, Any]:
        raise RuntimeError("segredo-interno 11.222.333/0001-81")

    deps.schema.mapa_do_banco = boom  # type: ignore[method-assign]
    result = run(lambda: call(deps, "mapa_do_banco", {}))
    assert result.is_error and body(result)["erro"]["codigo"] == "erro_interno"
    assert "segredo-interno" not in result.content[0].text
    assert "11.222" not in result.content[0].text


def test_database_errors_never_carry_driver_text(tmp_path: Path) -> None:
    deps, driver = make_deps(tmp_path)
    driver.server.script += [
        Rows(["plan"], [(CHEAP,)]),
        Fail("42S02", "[42S02] Table 'SEGREDO_DO_DRIVER' not found (-141)"),
    ]
    result = run(
        lambda: call(
            deps,
            "consulta_estruturada",
            {"consulta": {"tabela": "geempre", "colunas": ["codi_emp"]}},
        )
    )
    assert result.is_error and body(result)["erro"]["codigo"] == "erro_do_banco"
    assert "SEGREDO_DO_DRIVER" not in result.content[0].text


def test_to_error_maps_every_known_exception_to_a_code() -> None:
    from dominio_mcp.budget import Busy, Quarantined, RateLimited
    from dominio_mcp.freshness import PackMissing, PackStale
    from dominio_mcp.odbc import DbError, DbErrorKind, ExecutionUncertain, OdbcUnavailable
    from dominio_mcp.quarantine import QuarantineState
    from dominio_mcp.watchdog import QueryTimeout

    cases: list[tuple[BaseException, str]] = [
        (PackMissing("x"), "pack_ausente"),
        (PackStale("motivo"), "pack_desatualizado"),
        (Busy("x"), "ocupado"),
        (Quarantined(QuarantineState("t", 1, "r", 1)), "quarentena"),
        (RateLimited(5.0, 20), "limite_de_frequencia"),
        (QueryTimeout("x"), "tempo_esgotado"),
        (ExecutionUncertain("x"), "execucao_incerta"),
        (OdbcUnavailable("x"), "odbc_indisponivel"),
        (DbError(DbErrorKind.DENIED, "42000", -121), "erro_do_banco"),
        (ValueError("x"), "erro_interno"),
    ]
    for exc, code in cases:
        assert to_error(exc)[0] == code


def test_resources_and_prompts_are_exposed(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)

    async def go() -> tuple[list[str], str, list[str], str]:
        async with Client(build_server(deps)) as client:
            uris = [str(r.uri) for r in (await client.list_resources()).resources]
            mapa = await client.read_resource("dominio://mapa")
            names = [p.name for p in (await client.list_prompts()).prompts]
            prompt = await client.get_prompt(
                "conferir_empresa", {"codi_emp": "560", "inicio": "2025-06-01", "fim": "2025-06-30"}
            )
            return uris, mapa.contents[0].text, names, prompt.messages[0].content.text  # type: ignore[union-attr,attr-defined]

    uris, mapa_text, names, prompt_text = run(go)
    assert uris == ["dominio://mapa", "dominio://glossario"]
    assert json.loads(mapa_text)["banco"].startswith("Dominio")
    assert names == ["conferir_empresa", "explorar_assunto"]
    assert "560" in prompt_text and "movimento_fiscal" in prompt_text


def test_remote_profile_never_registers_or_dispatches_raw_sql(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)
    assert deps.settings.raw_sql_enabled is False

    async def go(profile: Profile) -> list[str]:
        async with Client(build_server(deps, profile)) as client:
            return [t.name for t in (await client.list_tools()).tools]

    for profile in (Profile.REMOTE, Profile.LOCAL):
        names = run(lambda p=profile: go(p))
        assert not any("sql" in n for n in names)
    refused = run(lambda: call(deps, "sql_somente_leitura", {"sql": "SELECT 1"}))
    assert refused.is_error


def test_every_call_is_audited_without_arguments_or_rows(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)
    run(lambda: call(deps, "buscar_esquema", {"consulta": "notas fiscais de saida"}))
    run(lambda: call(deps, "descrever_tabela", {"tabela": "nao_existe"}))
    events = [
        json.loads(line)
        for line in (tmp_path / "audit" / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    tools = [(e["ferramenta"], e["resultado"]) for e in events if e["evento"] == "ferramenta"]
    assert tools == [
        ("buscar_esquema", "ok"),
        ("descrever_tabela", "erro:tabela_desconhecida"),
    ]
    text = json.dumps(events)
    assert "notas fiscais" not in text and "nao_existe" not in text
