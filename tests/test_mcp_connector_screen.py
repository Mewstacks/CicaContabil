"""Tela do conector MCP: quem configura, o que muda e o que nunca vaza entre escritorios."""

from __future__ import annotations

from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from apps.intelligence.models import EdgeAgent
from apps.mcpgateway.models import McpConsent, McpSetting
from apps.organizations.models import Membership, Organization
from mcp_gateway_support import browser, configure, full_flow, make_user, rpc
from test_mcp_connector_queue import make_agent

pytestmark = pytest.mark.django_db(databases=["default", "knowledge"])

URL = "/app/conector-mcp/"


@pytest.fixture
def gateway(settings: Any) -> None:
    configure(settings)


def owner(org: Organization, email: str = "dono@x.test") -> Client:
    return browser(make_user(email, org))


def test_anonymous_goes_to_login() -> None:
    response = Client().get(URL)
    assert response.status_code == 302 and response["Location"].startswith("/entrar/")


def test_plain_member_is_refused(gateway: None) -> None:
    org = Organization.objects.create(name="A", slug="a")
    user = make_user("membro@x.test", org)
    Membership.objects.filter(user=user).update(role=Membership.Role.AUDITOR)
    assert browser(user).get(URL).status_code == 403


def test_page_renders_with_gateway_off() -> None:
    org = Organization.objects.create(name="A", slug="a")
    response = owner(org).get(URL)
    assert response.status_code == 200
    assert "Indisponível" in response.content.decode()
    assert "Ligar" not in response.content.decode().split("Computador")[0]


def test_toggle_on_and_off(gateway: None) -> None:
    org = Organization.objects.create(name="A", slug="a")
    web = owner(org)
    web.post(URL, {"action": "ligar"})
    assert McpSetting.objects.get(organization=org).enabled is True
    web.post(URL, {"action": "desligar"})
    assert McpSetting.objects.get(organization=org).enabled is False


def test_pairing_code_shows_once_and_pairs_a_computer(gateway: None) -> None:
    org = Organization.objects.create(name="A", slug="a")
    web = owner(org)
    web.post(URL, {"action": "parear"})
    first = web.get(URL).content.decode()
    assert "instalar-servico.ps1 -Hub https://cica.test -Codigo " in first
    assert "instalar-servico.ps1" not in web.get(URL).content.decode()


def test_revoke_agent_only_in_own_office(gateway: None) -> None:
    mine = Organization.objects.create(name="A", slug="a")
    other = Organization.objects.create(name="B", slug="b")
    web = owner(mine)
    own, _ = make_agent(mine)
    foreign, _ = make_agent(other)
    web.post(URL, {"action": "revogar-agente", "id": str(foreign.id)})
    foreign.refresh_from_db()
    assert foreign.status == EdgeAgent.Status.ACTIVE
    web.post(URL, {"action": "revogar-agente", "id": str(own.id)})
    own.refresh_from_db()
    assert own.status == EdgeAgent.Status.REVOKED
    assert web.post(URL, {"action": "revogar-agente", "id": "lixo"}).status_code == 302


def test_revoke_client_kills_the_token_and_ignores_other_offices(gateway: None) -> None:
    mine = Organization.objects.create(name="A", slug="a")
    other = Organization.objects.create(name="B", slug="b")
    admin = make_user("dono@x.test", mine)
    web = browser(admin)
    _cid, token, _refresh = full_flow(browser(admin), mine)
    outsider = make_user("fora@x.test", other)
    full_flow(browser(outsider), other)
    foreign = McpConsent.objects.get(user=outsider)
    web.post(URL, {"action": "revogar-cliente", "id": foreign.pk})
    assert McpConsent.objects.filter(pk=foreign.pk).exists()
    own = McpConsent.objects.get(user=admin)
    assert rpc(Client(), token, "tools/list").status_code == 200
    web.post(URL, {"action": "revogar-cliente", "id": own.pk})
    assert not McpConsent.objects.filter(pk=own.pk).exists()
    assert rpc(Client(), token, "tools/list").status_code == 401


def test_page_lists_only_own_office_data(gateway: None) -> None:
    mine = Organization.objects.create(name="A", slug="a")
    other = Organization.objects.create(name="B", slug="b")
    agent, _ = make_agent(mine, "Servidor-A")
    make_agent(other, "Servidor-B")
    EdgeAgent.objects.filter(pk=agent.pk).update(last_seen_at=timezone.now())
    html = owner(mine).get(URL).content.decode()
    assert "Servidor-A" in html and "Online" in html
    assert "Servidor-B" not in html
