"""Agente do computador do escritorio: assinatura, pareamento, laco e o relay de verdade."""

from __future__ import annotations

import hashlib
import hmac
import json
import sys
import threading
from pathlib import Path
from typing import Any

import pytest

from dominio_mcp import agent as agent_mod
from dominio_mcp.agent import (
    CLAIM_PATH,
    RESULT_PATH,
    Agent,
    AgentConfig,
    AgentError,
    enroll,
    load_config,
    save_config,
    sign,
)
from dominio_mcp.relay import run_job
from test_server_contract import make_deps

CONFIG = AgentConfig("https://cica.test", "agente-1", "segredo-do-agente")
JOB = {
    "contrato": 1,
    "id": "0123456789abcdef0123456789abcdef",
    "ferramenta": "mapa_do_banco",
    "argumentos": {},
}


class FakeHub:
    """Hub de mentira que confere a assinatura como o de verdade (`verify_agent_signature`)."""

    def __init__(self, jobs: list[dict[str, Any]] | None = None) -> None:
        self.jobs = list(jobs or [])
        self.results: list[dict[str, Any]] = []
        self.calls: list[str] = []

    def __call__(
        self, url: str, body: bytes, headers: dict[str, str], config: AgentConfig | None
    ) -> dict[str, Any]:
        self.calls.append(url)
        path = url.removeprefix("https://cica.test")
        expected = hmac.new(
            CONFIG.shared_secret.encode(),
            headers["X-Hub-Agent-Timestamp"].encode() + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        assert headers["X-Hub-Agent-ID"] == "agente-1"
        assert hmac.compare_digest(expected, headers["X-Hub-Agent-Signature"])
        payload = json.loads(body)
        if path == CLAIM_PATH:
            return {"job": self.jobs.pop(0) if self.jobs else None}
        assert path == RESULT_PATH
        self.results.append(payload)
        return {"ok": True}


def test_signature_is_hmac_of_timestamp_dot_body() -> None:
    expected = hmac.new(b"k", b"123.{}", hashlib.sha256).hexdigest()
    assert sign("k", "123", b"{}") == expected


def test_step_without_work_returns_false_and_posts_no_result() -> None:
    hub = FakeHub()
    agent = Agent(CONFIG, lambda raw: pytest.fail("nao havia trabalho"), transport=hub)
    assert agent.step(wait=0) is False
    assert hub.calls == ["https://cica.test" + CLAIM_PATH]


def test_step_runs_the_job_and_delivers_the_envelope() -> None:
    hub = FakeHub([JOB])
    seen: list[bytes] = []

    def runner(raw: bytes) -> dict[str, Any]:
        seen.append(raw)
        return {"contrato": 1, "id": JOB["id"], "ok": True, "resultado": {"banco": "x"}}

    assert Agent(CONFIG, runner, transport=hub).step(wait=0) is True
    assert json.loads(seen[0]) == JOB
    assert hub.results == [
        {
            "id": JOB["id"],
            "envelope": {"contrato": 1, "id": JOB["id"], "ok": True, "resultado": {"banco": "x"}},
        }
    ]


def test_a_job_with_sql_or_unknown_tool_is_refused_by_the_relay_not_run(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)
    hub = FakeHub(
        [
            {**JOB, "ferramenta": "sql_somente_leitura", "argumentos": {"sql": "DELETE"}},
            {**JOB, "id": "ffffffffffffffffffffffffffffffff", "sql": "DROP TABLE x"},
        ]
    )
    agent = Agent(CONFIG, lambda raw: run_job(deps, raw), transport=hub)
    assert agent.step(wait=0) and agent.step(wait=0)
    assert [r["envelope"]["ok"] for r in hub.results] == [False, False]
    assert {r["envelope"]["erro"]["codigo"] for r in hub.results} == {"trabalho_invalido"}


def test_real_relay_answers_a_real_tool_through_the_agent(tmp_path: Path) -> None:
    deps, _ = make_deps(tmp_path)
    hub = FakeHub([JOB])
    assert Agent(CONFIG, lambda raw: run_job(deps, raw), transport=hub).step(wait=0)
    envelope = hub.results[0]["envelope"]
    assert envelope["ok"] is True and envelope["id"] == JOB["id"]
    assert envelope["resultado"]["banco"].startswith("Dominio")


def test_run_survives_hub_errors_and_stops_on_event() -> None:
    stop = threading.Event()
    attempts: list[int] = []

    def flaky(url: str, body: bytes, headers: dict[str, str], config: Any) -> dict[str, Any]:
        attempts.append(1)
        if len(attempts) == 1:
            raise AgentError("sem conexao com o Hub")
        if len(attempts) == 2:
            raise ValueError("bug inesperado")
        stop.set()
        return {"job": None}

    agent = Agent(CONFIG, lambda raw: {}, transport=flaky)
    original = agent_mod.BACKOFF_START
    agent_mod.BACKOFF_START = 0.0
    try:
        agent.run(stop)
    finally:
        agent_mod.BACKOFF_START = original
    assert len(attempts) == 3


@pytest.mark.parametrize(
    "hub", ["http://cica.test", "ftp://cica.test", "cica.test", "https://u:p@cica.test"]
)
def test_hub_must_be_https(hub: str) -> None:
    with pytest.raises(AgentError):
        enroll(hub_url=hub, code="c", label="x", transport=FakeHub())


def test_http_is_allowed_only_on_loopback() -> None:
    seen: list[str] = []

    def hub(url: str, body: bytes, headers: dict[str, str], config: Any) -> dict[str, Any]:
        seen.append(url)
        return {"agent_id": "a", "shared_secret": "s"}

    config = enroll(hub_url="http://127.0.0.1:8000", code="c", label="x", transport=hub)
    assert seen == ["http://127.0.0.1:8000/api/v1/intelligence/agent/enroll/"]
    assert config.agent_id == "a"


def test_enroll_sends_code_label_fingerprint_and_never_a_secret() -> None:
    sent: list[dict[str, Any]] = []

    def hub(url: str, body: bytes, headers: dict[str, str], config: Any) -> dict[str, Any]:
        sent.append(json.loads(body))
        return {"agent_id": "agente-9", "shared_secret": "novo-segredo"}

    config = enroll(hub_url="https://cica.test/", code=" ABC ", label="Servidor", transport=hub)
    assert sent[0]["code"] == "ABC" and sent[0]["label"] == "Servidor"
    assert len(sent[0]["fingerprint"]) == 32 and "secret" not in json.dumps(sent[0])
    assert (config.hub_url, config.agent_id) == ("https://cica.test", "agente-9")


@pytest.mark.parametrize("reply", [{}, {"agent_id": "a"}, {"agent_id": "", "shared_secret": "s"}])
def test_enroll_without_identity_fails(reply: dict[str, Any]) -> None:
    with pytest.raises(AgentError):
        enroll(hub_url="https://cica.test", code="c", label="x", transport=lambda *a: reply)


def test_config_roundtrip_keeps_secret_out_of_the_file_on_windows(tmp_path: Path) -> None:
    path = save_config(tmp_path, CONFIG)
    assert load_config(tmp_path) == CONFIG
    if sys.platform == "win32":
        assert "segredo-do-agente" not in path.read_text(encoding="utf-8")


def test_missing_or_corrupt_config_is_a_clear_error(tmp_path: Path) -> None:
    with pytest.raises(AgentError, match="nao pareado"):
        load_config(tmp_path)
    (tmp_path / "agent.json").write_text("{nao e json", encoding="utf-8")
    with pytest.raises(AgentError, match="ilegivel"):
        load_config(tmp_path)
