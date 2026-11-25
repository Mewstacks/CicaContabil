"""Fila do conector MCP: gateway -> agente do escritorio -> resultado (Fase 2, peca 3)."""

from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import timedelta
from typing import Any
from unittest.mock import patch

import pytest
from asgiref.sync import sync_to_async
from django.test import Client
from django.utils import timezone

from apps.intelligence.agents import issue_enrollment, redeem_enrollment
from apps.intelligence.models import EdgeAgent
from apps.mcpgateway import jobs
from apps.mcpgateway.models import McpJob, McpSetting
from apps.organizations.models import Organization
from mcp_gateway_support import browser, configure, full_flow, make_user, rpc

pytestmark = pytest.mark.django_db(databases=["default", "knowledge"])

CLAIM = "/api/agent/mcp/claim"
RESULT = "/api/agent/mcp/result"


@pytest.fixture
def gateway(settings: Any) -> None:
    configure(settings)


def make_agent(org: Organization, label: str = "Servidor") -> tuple[EdgeAgent, str]:
    creds = redeem_enrollment(
        code=issue_enrollment(organization=org).code, label=label, fingerprint="fp-1234"
    )
    return EdgeAgent.objects.get(id=creds.agent_id), creds.shared_secret


def signed(client: Client, path: str, agent: EdgeAgent, secret: str, body: dict[str, Any]) -> Any:
    raw = json.dumps(body).encode()
    ts = str(int(timezone.now().timestamp()))
    sig = hmac.new(secret.encode(), ts.encode() + b"." + raw, hashlib.sha256).hexdigest()
    return client.post(
        path,
        raw,
        content_type="application/json",
        headers={
            "X-Hub-Agent-ID": str(agent.id),
            "X-Hub-Agent-Timestamp": ts,
            "X-Hub-Agent-Signature": sig,
        },
    )


def enable(org: Organization) -> None:
    McpSetting.objects.update_or_create(organization=org, defaults={"enabled": True})


def seen(agent: EdgeAgent) -> None:
    EdgeAgent.objects.filter(pk=agent.pk).update(last_seen_at=timezone.now())


def make_job(org: Organization, tool: str = "mapa_do_banco", **args: Any) -> McpJob:
    return McpJob.objects.create(organization=org, tool=tool, arguments=args)


def envelope(job: McpJob, **fields: Any) -> dict[str, Any]:
    return {"contrato": 1, "id": job.id.hex, "ok": True, "resultado": {"quantidade": 0}, **fields}


class TestAgentClaim:
    def test_gateway_off_is_404(self) -> None:
        assert Client().post(CLAIM, "{}", content_type="application/json").status_code == 404

    def test_unsigned_or_wrong_signature_is_401(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        agent, _ = make_agent(org)
        assert Client().post(CLAIM, "{}", content_type="application/json").status_code == 401
        assert signed(Client(), CLAIM, agent, "outro-segredo", {}).status_code == 401

    def test_returns_only_own_org_job_with_relay_contract(self, gateway: None) -> None:
        mine = Organization.objects.create(name="A", slug="a")
        other = Organization.objects.create(name="B", slug="b")
        agent, secret = make_agent(mine)
        make_job(other, "empresas")
        job = make_job(mine, "empresa_perfil", codi_emp=560)
        body = signed(Client(), CLAIM, agent, secret, {}).json()
        assert body["job"] == {
            "contrato": 1,
            "id": job.id.hex,
            "ferramenta": "empresa_perfil",
            "argumentos": {"codi_emp": 560},
        }
        job.refresh_from_db()
        assert job.status == McpJob.Status.CLAIMED and job.agent_id == agent.id
        assert signed(Client(), CLAIM, agent, secret, {}).json() == {"job": None}

    def test_claim_marks_agent_seen(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        agent, secret = make_agent(org)
        signed(Client(), CLAIM, agent, secret, {})
        agent.refresh_from_db()
        assert agent.last_seen_at is not None

    def test_revoked_agent_is_refused(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        agent, secret = make_agent(org)
        EdgeAgent.objects.filter(pk=agent.pk).update(status=EdgeAgent.Status.REVOKED)
        assert signed(Client(), CLAIM, agent, secret, {}).status_code == 401

    def test_stale_pending_job_expires_instead_of_running_late(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        agent, secret = make_agent(org)
        job = make_job(org)
        McpJob.objects.filter(pk=job.pk).update(created_at=timezone.now() - timedelta(minutes=5))
        assert signed(Client(), CLAIM, agent, secret, {}).json() == {"job": None}
        job.refresh_from_db()
        assert job.status == McpJob.Status.EXPIRED

    def test_long_poll_wait_is_capped(self, gateway: None, settings: Any) -> None:
        settings.MCP_AGENT_LONG_POLL_SECONDS = 0
        org = Organization.objects.create(name="A", slug="a")
        agent, secret = make_agent(org)
        started = time.monotonic()
        assert signed(Client(), CLAIM, agent, secret, {"wait": 9999}).json() == {"job": None}
        assert time.monotonic() - started < 2

    def test_two_claims_never_share_a_job(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        first, s1 = make_agent(org, "um")
        second, s2 = make_agent(org, "dois")
        make_job(org)
        got = [
            signed(Client(), CLAIM, first, s1, {}).json()["job"],
            signed(Client(), CLAIM, second, s2, {}).json()["job"],
        ]
        assert sum(1 for g in got if g) == 1


class TestAgentResult:
    def claimed(self, org: Organization) -> tuple[McpJob, EdgeAgent, str]:
        agent, secret = make_agent(org)
        job = make_job(org)
        signed(Client(), CLAIM, agent, secret, {})
        job.refresh_from_db()
        return job, agent, secret

    def test_success_is_stored_once(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        job, agent, secret = self.claimed(org)
        ok = signed(Client(), RESULT, agent, secret, {"id": str(job.id), "envelope": envelope(job)})
        assert ok.status_code == 200
        job.refresh_from_db()
        assert job.status == McpJob.Status.DONE and job.result == {"quantidade": 0}
        again = signed(
            Client(), RESULT, agent, secret, {"id": str(job.id), "envelope": envelope(job)}
        )
        assert again.status_code == 409

    def test_refusal_envelope_marks_failed_with_code(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        job, agent, secret = self.claimed(org)
        env = {
            "contrato": 1,
            "id": job.id.hex,
            "ok": False,
            "erro": {"codigo": "ocupado", "mensagem": "uma consulta por vez"},
        }
        signed(Client(), RESULT, agent, secret, {"id": str(job.id), "envelope": env})
        job.refresh_from_db()
        assert job.status == McpJob.Status.FAILED and job.error_code == "ocupado"

    def test_other_agent_cannot_deliver(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        other_org = Organization.objects.create(name="B", slug="b")
        job, _agent, _ = self.claimed(org)
        thief, thief_secret = make_agent(other_org)
        reply = signed(
            Client(), RESULT, thief, thief_secret, {"id": str(job.id), "envelope": envelope(job)}
        )
        assert reply.status_code == 409
        job.refresh_from_db()
        assert job.status == McpJob.Status.CLAIMED

    @pytest.mark.parametrize(
        "mutate",
        [
            lambda e: {**e, "id": "0" * 32},
            lambda e: {**e, "contrato": 2},
            lambda e: {**e, "ok": "sim"},
            lambda e: {k: v for k, v in e.items() if k != "resultado"},
            lambda e: {**e, "resultado": ["lista"]},
            lambda e: {**e, "resultado": {"x": "a" * 30000}},
        ],
    )
    def test_bad_envelope_is_refused(self, gateway: None, mutate: Any) -> None:
        org = Organization.objects.create(name="A", slug="a")
        job, agent, secret = self.claimed(org)
        reply = signed(
            Client(), RESULT, agent, secret, {"id": str(job.id), "envelope": mutate(envelope(job))}
        )
        assert reply.status_code == 409
        job.refresh_from_db()
        assert job.status == McpJob.Status.CLAIMED


class TestGatewayTools:
    def login(self, org: Organization) -> tuple[Client, str]:
        user = make_user("dono@x.test", org)
        _cid, token, _r = full_flow(browser(user), org)
        return Client(), token

    def names(self, client: Client, token: str) -> set[str]:
        tools = rpc(client, token, "tools/list").json()["result"]["tools"]
        return {t["name"] for t in tools}

    def test_hidden_until_switch_on_and_agent_paired(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        client, token = self.login(org)
        assert "analise_da_carteira" not in self.names(client, token)
        enable(org)
        assert "analise_da_carteira" not in self.names(client, token)
        make_agent(org)
        listed = self.names(client, token)
        assert len(listed & jobs.dominio_tool_names()) == 11
        assert "sql_somente_leitura" not in listed

    def test_switch_off_hides_again(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        client, token = self.login(org)
        enable(org)
        make_agent(org)
        McpSetting.objects.filter(organization=org).update(enabled=False)
        assert not self.names(client, token) & jobs.dominio_tool_names()

    def test_call_without_switch_is_refused(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        client, token = self.login(org)
        reply = rpc(client, token, "tools/call", {"name": "mapa_do_banco", "arguments": {}})
        assert reply.json()["error"]["code"] == -32602
        assert McpJob.objects.count() == 0

    def test_call_offline_agent_says_so_and_queues_nothing(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        client, token = self.login(org)
        enable(org)
        make_agent(org)  # nunca puxou: offline
        reply = rpc(client, token, "tools/call", {"name": "mapa_do_banco", "arguments": {}})
        result = reply.json()["result"]
        assert result["isError"] and "não está conectado" in result["content"][0]["text"]
        assert McpJob.objects.count() == 0

    def test_call_roundtrip_returns_agent_result(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        client, token = self.login(org)
        enable(org)
        agent, _secret = make_agent(org)
        seen(agent)
        real_await = jobs.await_result

        async def agent_answers(job: McpJob, **kwargs: Any) -> McpJob:
            # o agente trabalha direto na fila: chamar o cliente HTTP daqui travaria a thread
            def work() -> None:
                claimed = jobs.try_claim(agent)
                assert claimed is not None
                payload = jobs.relay_payload(claimed)
                assert payload["ferramenta"] == "empresa_perfil"
                assert payload["argumentos"] == {"codi_emp": 560}
                env = {
                    "contrato": 1,
                    "id": payload["id"],
                    "ok": True,
                    "resultado": {"quantidade": 1, "linhas": [[560]]},
                }
                jobs.finish(agent=agent, job_id=payload["id"], envelope=env)

            await sync_to_async(work)()
            return await real_await(job, **kwargs)

        with patch.object(jobs, "await_result", agent_answers):
            reply = rpc(
                client,
                token,
                "tools/call",
                {"name": "empresa_perfil", "arguments": {"codi_emp": 560}},
            )
        result = reply.json()["result"]
        assert result["isError"] is False
        assert result["structuredContent"] == {"quantidade": 1, "linhas": [[560]]}
        assert McpJob.objects.get().requested_by.email == "dono@x.test"

    def test_agent_refusal_is_an_error_result(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        client, token = self.login(org)
        enable(org)
        agent, _secret = make_agent(org)
        seen(agent)
        real_await = jobs.await_result

        async def agent_refuses(job: McpJob, **kwargs: Any) -> McpJob:
            def work() -> None:
                claimed = jobs.try_claim(agent)
                assert claimed is not None
                env = {
                    "contrato": 1,
                    "id": claimed.id.hex,
                    "ok": False,
                    "erro": {"codigo": "ocupado", "mensagem": "uma consulta por vez"},
                }
                jobs.finish(agent=agent, job_id=str(claimed.id), envelope=env)

            await sync_to_async(work)()
            return await real_await(job, **kwargs)

        with patch.object(jobs, "await_result", agent_refuses):
            reply = rpc(client, token, "tools/call", {"name": "mapa_do_banco", "arguments": {}})
        result = reply.json()["result"]
        assert result["isError"] is True
        assert result["structuredContent"]["erro"]["codigo"] == "ocupado"

    def test_timeout_expires_the_job(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        client, token = self.login(org)
        enable(org)
        agent, _ = make_agent(org)
        seen(agent)
        real_await = jobs.await_result

        async def impatient(job: McpJob, **kwargs: Any) -> McpJob:
            return await real_await(job, timeout=0.01)

        with patch.object(jobs, "await_result", impatient):
            reply = rpc(client, token, "tools/call", {"name": "mapa_do_banco", "arguments": {}})
        result = reply.json()["result"]
        assert result["isError"] and "não respondeu" in result["content"][0]["text"]
        assert McpJob.objects.get().status == McpJob.Status.EXPIRED

    def test_open_jobs_are_capped_per_org(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        client, token = self.login(org)
        enable(org)
        agent, _ = make_agent(org)
        seen(agent)
        for _ in range(jobs.MAX_OPEN_JOBS):
            make_job(org)
        reply = rpc(client, token, "tools/call", {"name": "mapa_do_banco", "arguments": {}})
        assert "demais" in reply.json()["result"]["content"][0]["text"]
        assert McpJob.objects.count() == jobs.MAX_OPEN_JOBS

    def test_oversized_or_deep_arguments_never_queue(self, gateway: None) -> None:
        org = Organization.objects.create(name="A", slug="a")
        client, token = self.login(org)
        enable(org)
        agent, _ = make_agent(org)
        seen(agent)
        deep: Any = "x"
        for _ in range(12):
            deep = {"a": deep}
        for arguments in ({"consulta": "x" * 20000}, deep):
            reply = rpc(client, token, "tools/call", {"name": "empresas", "arguments": arguments})
            assert reply.json()["result"]["isError"]
        assert McpJob.objects.count() == 0

    def test_other_orgs_agent_is_not_enough(self, gateway: None) -> None:
        mine = Organization.objects.create(name="A", slug="a")
        other = Organization.objects.create(name="B", slug="b")
        client, token = self.login(mine)
        enable(mine)
        agent, _ = make_agent(other)
        seen(agent)
        assert not self.names(client, token) & jobs.dominio_tool_names()
