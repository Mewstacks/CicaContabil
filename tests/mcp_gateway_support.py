"""Apoio dos testes do gateway MCP externo: configuracao ligada e o fluxo OAuth completo."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, urlsplit

from django.test import Client

from apps.accounts.models import User
from apps.organizations.models import Membership, Organization

ORIGIN = "https://cica.test"
RESOURCE = f"{ORIGIN}/mcp"
ISSUER = f"{ORIGIN}/oauth"
CALLBACK = "https://claude.ai/api/mcp/auth_callback"
SCOPE = "mcp:read"
PASSWORD = "correct-horse-battery-staple"


def configure(settings: Any) -> None:
    settings.MCP_GATEWAY_ENABLED = True
    settings.MCP_GATEWAY_PUBLIC_URL = ORIGIN
    settings.OAUTH2_PROVIDER = {
        **settings.OAUTH2_PROVIDER,
        "OIDC_ISS_ENDPOINT": ISSUER,
        "OAUTH2_PROTECTED_RESOURCE_IDENTIFIER": RESOURCE,
        "OAUTH2_PROTECTED_RESOURCE_AUTHORIZATION_SERVERS": [ISSUER],
    }


def make_user(email: str, *orgs: Organization) -> User:
    user = User.objects.create_user(email=email, password=PASSWORD, full_name=email)
    for org in orgs:
        Membership.objects.create(organization=org, user=user, role=Membership.Role.OWNER)
    return user


def browser(user: User) -> Client:
    from conftest import complete_mfa

    client = Client()
    client.force_login(user)
    complete_mfa(client)
    return client


def pkce() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(48)
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return verifier, base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def register(client: Client, **overrides: Any) -> str:
    body = {
        "client_name": "Claude",
        "redirect_uris": [CALLBACK],
        "grant_types": ["authorization_code", "refresh_token"],
        "token_endpoint_auth_method": "none",
        **overrides,
    }
    response = client.post("/oauth/register/", json.dumps(body), content_type="application/json")
    assert response.status_code == 201, response.content
    return str(response.json()["client_id"])


@dataclass
class Grant:
    client_id: str
    verifier: str
    code: str
    redirect_uri: str = CALLBACK


def authorize_params(client_id: str, challenge: str, **overrides: Any) -> dict[str, str]:
    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": CALLBACK,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "scope": SCOPE,
        "resource": RESOURCE,
        "state": "estado-123",
    }
    params.update({k: v for k, v in overrides.items() if v is not None})
    return {k: v for k, v in params.items() if v != ""}


def hidden_fields(response: Any) -> dict[str, str]:
    form = response.context["form"]
    return {
        name: str(form.initial.get(name) or "")
        for name in (
            "redirect_uri",
            "scope",
            "client_id",
            "state",
            "response_type",
            "code_challenge",
            "code_challenge_method",
            "resource",
        )
    }


def consent(
    web: Client, client_id: str, organization: Organization | None, **overrides: Any
) -> Grant | Any:
    verifier, challenge = pkce()
    params = authorize_params(client_id, challenge, **overrides)
    page = web.get("/oauth/authorize/", params)
    if page.status_code != 200:
        return page
    data = hidden_fields(page)
    data["allow"] = "true"
    if organization is not None:
        data["organization"] = str(organization.id)
    result = web.post("/oauth/authorize/", data)
    if result.status_code != 302:
        return result
    query = parse_qs(urlsplit(result["Location"]).query)
    assert query["state"] == ["estado-123"]
    assert query["iss"] == [ISSUER]
    return Grant(client_id=client_id, verifier=verifier, code=query["code"][0])


def exchange(client: Client, grant: Grant, **overrides: Any) -> Any:
    data = {
        "grant_type": "authorization_code",
        "client_id": grant.client_id,
        "code": grant.code,
        "redirect_uri": grant.redirect_uri,
        "code_verifier": grant.verifier,
        "resource": RESOURCE,
    }
    data.update(overrides)
    return client.post("/oauth/token/", {k: v for k, v in data.items() if v is not None})


def refresh(client: Client, client_id: str, refresh_token: str) -> Any:
    return client.post(
        "/oauth/token/",
        {"grant_type": "refresh_token", "client_id": client_id, "refresh_token": refresh_token},
    )


def rpc(
    client: Client,
    token: str | None,
    method: str,
    params: dict[str, Any] | None = None,
    *,
    request_id: int | None = 1,
    **extra: Any,
) -> Any:
    body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
    if request_id is not None:
        body["id"] = request_id
    if params is not None:
        body["params"] = params
    headers = {"HTTP_AUTHORIZATION": f"Bearer {token}"} if token else {}
    return client.post(
        "/mcp", json.dumps(body), content_type="application/json", **headers, **extra
    )


def full_flow(web: Client, organization: Organization | None) -> tuple[str, str, str]:
    """Cadastro, consentimento e troca; devolve (client_id, access_token, refresh_token)."""
    anonymous = Client()
    client_id = register(anonymous)
    grant = consent(web, client_id, organization)
    assert isinstance(grant, Grant), getattr(grant, "content", grant)
    response = exchange(anonymous, grant)
    assert response.status_code == 200, response.content
    payload = response.json()
    return client_id, payload["access_token"], payload["refresh_token"]
