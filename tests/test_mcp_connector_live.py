"""Cadeia inteira com o Dominio real: /mcp -> fila do Hub -> agente (processo) -> ODBC.

So roda com `DOMINIO_MCP_LIVE_CLI` apontando para o `dominio-mcp.exe` instalado e
`DOMINIO_MCP_LIVE_HOME` para uma pasta com `packs/` ja gerado. O agente e um processo de verdade,
fala HTTP com o servidor de teste do Django e le o banco real, somente leitura.
"""

from __future__ import annotations

import os
import subprocess
from typing import Any

import pytest
from django.test import Client

from apps.intelligence.agents import issue_enrollment
from apps.mcpgateway.models import McpJob, McpSetting
from apps.organizations.models import Organization
from mcp_gateway_support import browser, configure, full_flow, make_user, rpc

CLI = os.environ.get("DOMINIO_MCP_LIVE_CLI", "")
HOME = os.environ.get("DOMINIO_MCP_LIVE_HOME", "")

pytestmark = [
    pytest.mark.skipif(not (CLI and HOME), reason="defina DOMINIO_MCP_LIVE_CLI e _HOME"),
    pytest.mark.django_db(transaction=True, databases=["default", "knowledge"]),
]


def test_assistant_question_reaches_the_real_dominio(live_server: Any, settings: Any) -> None:
    configure(settings)
    org = Organization.objects.create(name="Escritorio", slug="escritorio")
    web = browser(make_user("dono@x.test", org))
    _cid, token, _refresh = full_flow(web, org)
    McpSetting.objects.create(organization=org, enabled=True)
    code = issue_enrollment(organization=org).code
    env = {**os.environ, "DOMINIO_MCP_HOME": HOME}
    enrolled = subprocess.run(  # noqa: S603
        [CLI, "agent-enroll", "--hub", live_server.url, "--codigo", code, "--nome", "pc-teste"],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert enrolled.returncode == 0, enrolled.stderr
    agent = subprocess.Popen([CLI, "agent-run"], env=env, stderr=subprocess.PIPE, text=True)  # noqa: S603
    try:
        client = Client()
        listed = rpc(client, token, "tools/list").json()["result"]["tools"]
        assert "analise_da_carteira" in {t["name"] for t in listed}
        # o primeiro ciclo de claim marca o agente online; espera ate 20 s
        import time

        deadline = time.monotonic() + 20
        reply: Any = None
        while time.monotonic() < deadline:
            reply = rpc(
                client,
                token,
                "tools/call",
                {
                    "name": "analise_da_carteira",
                    "arguments": {"analise": "cadastro", "so_pendencias": 1, "limite": 3},
                },
            ).json()
            if not reply["result"]["isError"]:
                break
            time.sleep(1)
        result = reply["result"]
        assert result["isError"] is False, result
        assert "colunas" in result["structuredContent"]
        job = McpJob.objects.filter(status=McpJob.Status.DONE).latest("created_at")
        assert job.tool == "analise_da_carteira"
    finally:
        agent.terminate()
        agent.wait(timeout=20)
