"""HTTP em loopback (M10, A10): bind, Host, Origin, token, limites e o servico de verdade."""

from __future__ import annotations

import json
import socket
import threading
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import anyio
import httpx2
import pytest
import uvicorn
from mcp.client import Client
from mcp.client.streamable_http import streamable_http_client
from starlette.testclient import TestClient
from starlette.types import Receive, Scope, Send

from dominio_mcp import cli
from dominio_mcp.config import Profile
from dominio_mcp.http_app import (
    AUTH_FAILURES_PER_MINUTE,
    MAX_BODY_BYTES,
    FailureLimiter,
    HttpConfigError,
    LoopbackGate,
    build_http_app,
    check_bind,
    check_port,
    load_or_create_token,
    token_path,
)
from dominio_mcp.server import TOOL_NAMES, build_server
from test_server_contract import make_deps

TOKEN = "t" * 43
PORT = 8765
BASE = f"http://127.0.0.1:{PORT}"
AUTH = {"Authorization": f"Bearer {TOKEN}"}
ANY_ADDRESS = "0.0.0.0"  # noqa: S104  (o teste confere que e recusado)


async def echo_app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "lifespan":
        while True:
            message = await receive()
            if message["type"] == "lifespan.startup":
                await send({"type": "lifespan.startup.complete"})
            else:
                await send({"type": "lifespan.shutdown.complete"})
                return
    await send({"type": "http.response.start", "status": 200, "headers": []})
    await send({"type": "http.response.body", "body": b"passou"})


def gate(**kw: Any) -> LoopbackGate:
    return LoopbackGate(echo_app, token=TOKEN, port=PORT, **kw)


def client(app: Any = None) -> TestClient:
    return TestClient(app or gate(), base_url=BASE)


def test_only_literal_loopback_addresses_may_be_bound(tmp_path: Path) -> None:
    assert check_bind("127.0.0.1") == "127.0.0.1" and check_bind("::1") == "::1"
    for bad in (ANY_ADDRESS, "::", "localhost", "192.168.0.10", "10.0.0.1", "", "127.0.0.2", "x"):
        with pytest.raises(HttpConfigError):
            check_bind(bad)
    deps, _ = make_deps(tmp_path)
    with pytest.raises(HttpConfigError):
        build_http_app(build_server(deps), host=ANY_ADDRESS, port=PORT, token=TOKEN)


@pytest.mark.parametrize("port", [0, 80, 1023, 65536, -1, True])
def test_ports_outside_the_unprivileged_range_are_refused(port: int) -> None:
    with pytest.raises(HttpConfigError):
        check_port(port)


def test_the_token_is_created_once_never_overwritten_and_long(tmp_path: Path) -> None:
    path = token_path(tmp_path)
    first = load_or_create_token(path)
    assert len(first) >= 43 and first == load_or_create_token(path)
    assert path.read_text(encoding="ascii").strip() == first
    path.write_text("abc123xyz", encoding="ascii")
    with pytest.raises(HttpConfigError) as short:
        load_or_create_token(path)
    assert "abc123xyz" not in str(short.value)
    assert path.read_text(encoding="ascii").strip() == "abc123xyz"  # nao trocou sozinho


def test_a_short_token_cannot_arm_the_gate() -> None:
    with pytest.raises(HttpConfigError):
        LoopbackGate(echo_app, token="curto", port=PORT)


def test_a_valid_request_passes_through() -> None:
    with client() as c:
        assert c.post("/mcp", headers=AUTH, json={}).text == "passou"


@pytest.mark.parametrize(
    "host", ["evil.example", "127.0.0.1", "127.0.0.1:9999", "127.0.0.1.evil.example:8765", ""]
)
def test_a_wrong_host_is_refused_before_the_token_is_looked_at(host: str) -> None:
    with client() as c:
        reply = c.post("/mcp", headers={**AUTH, "Host": host}, json={})
    assert reply.status_code == 421 and "passou" not in reply.text


def test_a_browser_origin_is_refused_even_with_the_right_token() -> None:
    with client() as c:
        reply = c.post("/mcp", headers={**AUTH, "Origin": "https://evil.example"}, json={})
        assert reply.status_code == 403
        assert c.post("/mcp", headers={**AUTH, "Origin": "null"}, json={}).status_code == 403
    allowed = gate(allowed_origins=["https://app.example"])
    with client(allowed) as c:
        ok = c.post("/mcp", headers={**AUTH, "Origin": "https://app.example"}, json={})
        assert ok.status_code == 200


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer errado"},
        {"Authorization": f"Basic {TOKEN}"},
        {"Authorization": TOKEN},
        {"Authorization": "Bearer "},
        {"Authorization": f"Bearer {TOKEN}x"},
        {"Authorization": f"Bearer {TOKEN[:-1]}"},
        {"X-Api-Key": TOKEN},
    ],
)
def test_without_the_exact_bearer_token_nothing_passes(headers: dict[str, str]) -> None:
    with client() as c:
        reply = c.post("/mcp", headers=headers, json={})
    assert reply.status_code == 401 and reply.headers["www-authenticate"] == "Bearer"
    assert json.loads(reply.text) == {"erro": {"codigo": "nao_autorizado"}}


def test_the_token_in_the_query_string_is_ignored() -> None:
    with client() as c:
        assert c.post(f"/mcp?token={TOKEN}", json={}).status_code == 401


def test_other_paths_and_methods_never_reach_the_app() -> None:
    with client() as c:
        for path in ("/", "/sse", "/mcp/", "/messages/", "/.well-known/oauth-authorization-server"):
            assert c.post(path, headers=AUTH, json={}).status_code == 404
        for method in ("PUT", "PATCH", "OPTIONS", "HEAD", "TRACE"):
            assert c.request(method, "/mcp", headers=AUTH).status_code == 405


def test_guessing_is_capped_per_minute_and_the_cap_frees_itself() -> None:
    now = [0.0]
    limiter = FailureLimiter(AUTH_FAILURES_PER_MINUTE, clock=lambda: now[0])
    wrong = {"Authorization": "Bearer x"}
    with client(gate(limiter=limiter)) as c:
        codes = [
            c.post("/mcp", headers=wrong, json={}).status_code
            for _ in range(AUTH_FAILURES_PER_MINUTE + 3)
        ]
        assert codes[:AUTH_FAILURES_PER_MINUTE] == [401] * AUTH_FAILURES_PER_MINUTE
        assert codes[AUTH_FAILURES_PER_MINUTE:] == [429] * 3
        # durante o bloqueio nem o token certo passa: o teto vale para o palpite que acertar
        assert c.post("/mcp", headers=AUTH, json={}).status_code == 429
        now[0] = 61.0
        assert c.post("/mcp", headers=AUTH, json={}).status_code == 200


def test_the_real_app_rejects_oversized_bodies_and_wrong_content_type(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)
    server = build_server(deps, Profile.REMOTE)
    app = build_http_app(server, host="127.0.0.1", port=PORT, token=TOKEN)
    json_type = {**AUTH, "Content-Type": "application/json"}
    with client(app) as c:
        big = c.post("/mcp", headers=json_type, content=b"x" * (MAX_BODY_BYTES + 1))
        assert big.status_code == 413
        wrong = c.post("/mcp", headers={**AUTH, "Content-Type": "text/plain"}, content=b"{}")
        assert wrong.status_code == 400


def test_http_refuses_the_local_profile_on_the_command_line(
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = cli.main(["serve", "--http", "--profile", "local"])
    assert code == 1 and "remote" in capsys.readouterr().err


def test_http_refuses_a_non_loopback_host_on_the_command_line(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DOMINIO_MCP_HOME", str(tmp_path))
    code = cli.main(["serve", "--http", "--host", ANY_ADDRESS])
    assert code == 1 and "127.0.0.1" in capsys.readouterr().err


def test_http_token_command_prints_the_token_and_keeps_it(
    capsys: pytest.CaptureFixture[str], tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DOMINIO_MCP_HOME", str(tmp_path))
    assert cli.main(["http-token"]) == 0
    first = capsys.readouterr().out.strip()
    assert cli.main(["http-token"]) == 0
    assert capsys.readouterr().out.strip() == first and len(first) >= 43


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture
def live_server(tmp_path: Path) -> Iterator[int]:
    deps, _ = make_deps(tmp_path)
    port = free_port()
    server_app = build_server(deps, Profile.REMOTE)
    app = build_http_app(server_app, host="127.0.0.1", port=port, token=TOKEN)
    server = uvicorn.Server(
        uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning", access_log=False)
    )
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 15
    while not server.started and time.monotonic() < deadline:
        time.sleep(0.05)
    assert server.started
    try:
        yield port
    finally:
        server.should_exit = True
        thread.join(timeout=10)


def test_a_real_mcp_client_lists_and_calls_tools_over_http(live_server: int) -> None:
    url = f"http://127.0.0.1:{live_server}/mcp"

    async def go() -> tuple[list[str], dict[str, Any]]:
        http = httpx2.AsyncClient(headers=AUTH)
        async with http, Client(streamable_http_client(url, http_client=http)) as mcp:
            names = [t.name for t in (await mcp.list_tools()).tools]
            result = await mcp.call_tool("mapa_do_banco", {})
            return names, json.loads(result.content[0].text)  # type: ignore[union-attr]

    names, mapa = anyio.run(go)
    assert tuple(names) == TOOL_NAMES and "sql_somente_leitura" not in names
    assert mapa["banco"].startswith("Dominio")


def test_the_live_service_answers_401_without_the_token_and_refuses_foreign_headers(
    live_server: int,
) -> None:
    url = f"http://127.0.0.1:{live_server}/mcp"
    body = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
    base = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    assert httpx2.post(url, json=body, headers=base).status_code == 401
    foreign_host = {**base, **AUTH, "Host": "evil.example"}
    assert httpx2.post(url, json=body, headers=foreign_host).status_code == 421
    foreign_origin = {**base, **AUTH, "Origin": "https://evil.example"}
    assert httpx2.post(url, json=body, headers=foreign_origin).status_code == 403
