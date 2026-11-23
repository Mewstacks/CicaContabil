"""Gateway MCP externo (D-333): OAuth 2.1 do DOT mais o endpoint, com recusa por degrau."""

from __future__ import annotations

import json
from datetime import timedelta
from typing import Any
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from oauth2_provider.models import (
    get_access_token_model,
    get_application_model,
    get_refresh_token_model,
)

from apps.mcpgateway.models import McpConsent
from apps.organizations.models import Membership, Organization
from mcp_gateway_support import (
    CALLBACK,
    ISSUER,
    ORIGIN,
    RESOURCE,
    SCOPE,
    authorize_params,
    browser,
    configure,
    consent,
    exchange,
    full_flow,
    hidden_fields,
    make_user,
    pkce,
    refresh,
    register,
    rpc,
)

pytestmark = pytest.mark.django_db(databases=["default", "knowledge"])

ENDPOINT = "apps.mcpgateway.endpoint"


@pytest.fixture
def gateway(settings: Any) -> None:
    configure(settings)


@pytest.fixture
def office_a(db: object) -> Organization:
    return Organization.objects.create(name="Escritorio A", slug="escritorio-a")


@pytest.fixture
def office_b(db: object) -> Organization:
    return Organization.objects.create(name="Escritorio B", slug="escritorio-b")


@pytest.fixture(autouse=True)
def fresh_permission() -> Any:
    from django.core.cache import cache

    cache.clear()  # os tetos por minuto e por hora contam no cache do processo
    with (
        patch(f"{ENDPOINT}.authorization_is_fresh", return_value=True),
        patch(f"{ENDPOINT}.membership_has_capability", return_value=True),
    ):
        yield


# --- desligado: nada existe ---------------------------------------------------------------


@pytest.mark.parametrize(
    "path",
    [
        "/mcp",
        "/oauth/token/",
        "/oauth/authorize/",
        "/oauth/register/",
        "/oauth/revoke_token/",
        "/.well-known/oauth-authorization-server",
        "/.well-known/oauth-authorization-server/oauth",
        "/.well-known/oauth-protected-resource/mcp",
    ],
)
def test_with_the_flag_off_every_route_is_404(path: str, settings: Any) -> None:
    settings.MCP_GATEWAY_ENABLED = False
    client = Client()
    assert client.get(path).status_code == 404
    assert client.post(path, "{}", content_type="application/json").status_code == 404


def test_without_a_public_url_the_gateway_stays_off(settings: Any) -> None:
    settings.MCP_GATEWAY_ENABLED = True
    settings.MCP_GATEWAY_PUBLIC_URL = ""
    assert Client().post("/mcp", "{}", content_type="application/json").status_code == 404


# --- metadados ----------------------------------------------------------------------------


def test_authorization_server_metadata_pins_the_secure_profile(gateway: None) -> None:
    for path in (
        "/.well-known/oauth-authorization-server",
        "/.well-known/oauth-authorization-server/oauth",
    ):
        meta = Client().get(path).json()
        assert meta["issuer"] == ISSUER
        assert meta["code_challenge_methods_supported"] == ["S256"]
        assert meta["response_types_supported"] == ["code"]
        assert meta["grant_types_supported"] == ["authorization_code", "refresh_token"]
        assert meta["token_endpoint_auth_methods_supported"] == ["none"]
        assert meta["client_id_metadata_document_supported"] is True
        assert meta["authorization_response_iss_parameter_supported"] is True
        assert meta["authorization_endpoint"] == f"{ORIGIN}/oauth/authorize/"
        assert meta["token_endpoint"] == f"{ORIGIN}/oauth/token/"
        assert meta["registration_endpoint"] == f"{ORIGIN}/oauth/register/"
        assert meta["scopes_supported"] == [SCOPE]
        assert "introspection_endpoint" not in meta


def test_protected_resource_metadata_names_the_fixed_resource_and_issuer(
    gateway: None, settings: Any
) -> None:
    settings.ALLOWED_HOSTS = ["*"]
    url = "/.well-known/oauth-protected-resource/mcp"
    meta = Client().get(url, HTTP_HOST="atacante.example").json()
    assert meta["resource"] == RESOURCE
    assert meta["authorization_servers"] == [ISSUER]
    assert meta["bearer_methods_supported"] == ["header"]
    assert Client().get("/.well-known/oauth-protected-resource").status_code == 404


def test_metadata_ignores_a_forged_host_header(gateway: None, settings: Any) -> None:
    settings.ALLOWED_HOSTS = ["*"]
    meta = (
        Client().get("/.well-known/oauth-authorization-server", HTTP_HOST="atacante.example").json()
    )
    assert "atacante" not in json.dumps(meta)


def test_unused_dot_endpoints_are_not_mounted(gateway: None) -> None:
    client = Client()
    for path in (
        "/oauth/introspect/",
        "/oauth/device-authorization/",
        "/oauth/applications/",
        "/oauth/userinfo/",
        "/oauth/.well-known/openid-configuration",
    ):
        assert client.get(path).status_code == 404, path


# --- cadastro -----------------------------------------------------------------------------


def post_register(body: dict[str, Any]) -> Any:
    return Client().post("/oauth/register/", json.dumps(body), content_type="application/json")


@pytest.mark.parametrize(
    "body",
    [
        {"redirect_uris": ["https://atacante.example/cb"]},
        {"redirect_uris": [CALLBACK, "https://atacante.example/cb"]},
        {"redirect_uris": ["https://claude.ai/api/mcp/auth_callback/../x"]},
        {"redirect_uris": ["https://claude.ai/api/mcp/auth_callback#x"]},
        {"redirect_uris": ["https://claude.ai.atacante.example/api/mcp/auth_callback"]},
        {"redirect_uris": ["http://claude.ai/api/mcp/auth_callback"]},
        {"redirect_uris": ["https://chatgpt.com@atacante.example/connector/oauth/x"]},
        {"redirect_uris": ["https://chatgpt.com.atacante.example/connector/oauth/x"]},
        {"redirect_uris": []},
        {"redirect_uris": "https://claude.ai/api/mcp/auth_callback"},
        {},
        {"redirect_uris": [CALLBACK], "grant_types": ["implicit"]},
        {"redirect_uris": [CALLBACK], "grant_types": ["client_credentials"]},
        {"redirect_uris": [CALLBACK], "grant_types": ["authorization_code", "password"]},
        {"redirect_uris": [CALLBACK], "token_endpoint_auth_method": "client_secret_basic"},
        {"redirect_uris": [CALLBACK], "token_endpoint_auth_method": "client_secret_post"},
    ],
)
def test_registration_refuses_anything_outside_the_profile(
    gateway: None, body: dict[str, Any]
) -> None:
    before = get_application_model().objects.count()
    response = post_register(body)
    assert response.status_code in {400, 401, 403}
    assert get_application_model().objects.count() == before


@pytest.mark.parametrize(
    "redirect",
    [
        CALLBACK,
        "https://claude.com/api/mcp/auth_callback",
        "https://chatgpt.com/connector_platform_oauth_redirect",
        "https://chatgpt.com/connector/oauth/abc123",
        "http://127.0.0.1/callback",
        "http://localhost/callback",
        "http://[::1]/callback",
    ],
)
def test_registration_accepts_the_known_connectors(gateway: None, redirect: str) -> None:
    assert post_register({"redirect_uris": [redirect]}).status_code == 201


def test_registered_clients_are_public_pkce_clients_without_skip_authorization(
    gateway: None,
) -> None:
    client_id = register(Client(), skip_authorization=True)
    app = get_application_model().objects.get(client_id=client_id)
    assert app.client_type == "public"
    assert app.skip_authorization is False
    assert app.authorization_grant_type == "authorization-code"


def test_registration_is_rate_limited_per_address(gateway: None, settings: Any) -> None:
    settings.MCP_GATEWAY_REGISTRATION_PER_HOUR = 2
    codes = [post_register({"redirect_uris": [CALLBACK]}).status_code for _ in range(4)]
    assert codes[:2] == [201, 201]
    assert all(code in {401, 403} for code in codes[2:])


# --- autorizacao --------------------------------------------------------------------------


def test_authorize_needs_a_signed_in_person(gateway: None) -> None:
    client_id = register(Client())
    response = Client().get("/oauth/authorize/", authorize_params(client_id, pkce()[1]))
    assert response.status_code == 302
    assert response["Location"].startswith(reverse("hub:login"))


@pytest.mark.parametrize(
    "resource",
    [None, "", "https://atacante.example/mcp", f"{RESOURCE}/", f"{RESOURCE}/x", ORIGIN, "mcp"],
)
def test_authorize_requires_the_exact_resource(
    gateway: None, office_a: Organization, resource: str | None
) -> None:
    web = browser(make_user("a@example.test", office_a))
    client_id = register(Client())
    params = authorize_params(client_id, pkce()[1])
    params.pop("resource")
    if resource:
        params["resource"] = resource
    response = web.get("/oauth/authorize/", params)
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_target"


def test_authorize_refuses_two_resources(gateway: None, office_a: Organization) -> None:
    web = browser(make_user("a@example.test", office_a))
    client_id = register(Client())
    params = authorize_params(client_id, pkce()[1])
    response = web.get(
        "/oauth/authorize/?"
        + "&".join(f"{k}={v}" for k, v in params.items())
        + "&resource=https://atacante.example/mcp"
    )
    assert response.status_code == 400


@pytest.mark.parametrize(
    "override",
    [
        {"code_challenge": ""},
        {"code_challenge_method": "plain"},
        {"code_challenge_method": ""},
        {"response_type": "token"},
        {"scope": "mcp:write"},
    ],
)
def test_authorize_refuses_weak_pkce_and_other_flows(
    gateway: None, office_a: Organization, override: dict[str, str]
) -> None:
    web = browser(make_user("a@example.test", office_a))
    client_id = register(Client())
    params = authorize_params(client_id, pkce()[1])
    params.update(override)
    params = {k: v for k, v in params.items() if v != ""}
    page = web.get("/oauth/authorize/", params)
    results = [page]
    if page.status_code == 200:
        data = hidden_fields(page)
        data.update({"allow": "true", "organization": str(office_a.id)})
        results.append(web.post("/oauth/authorize/", data))
    for response in results:
        if response.status_code == 302:
            assert "code=" not in response["Location"], response["Location"]
    assert not get_access_token_model().objects.filter(scope=SCOPE).exists()


def test_authorize_never_redirects_to_an_unregistered_uri(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    client_id = register(Client())
    params = authorize_params(client_id, pkce()[1], redirect_uri="https://atacante.example/cb")
    response = web.get("/oauth/authorize/", params)
    assert response.status_code != 302


def test_the_consent_page_offers_only_the_persons_offices(
    gateway: None, office_a: Organization, office_b: Organization
) -> None:
    Organization.objects.create(name="Escritorio C", slug="escritorio-c")
    web = browser(make_user("a@example.test", office_a))
    page = web.get("/oauth/authorize/", authorize_params(register(Client()), pkce()[1]))
    assert page.status_code == 200
    ids = [value for value, _ in page.context["form"].fields["organization"].choices]
    assert ids == [str(office_a.id)]


def test_an_office_the_person_does_not_belong_to_is_rejected_at_consent(
    gateway: None, office_a: Organization, office_b: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    result = consent(web, register(Client()), office_b)
    assert not hasattr(result, "code")
    assert McpConsent.objects.count() == 0


def test_denying_consent_binds_nothing(gateway: None, office_a: Organization) -> None:
    web = browser(make_user("a@example.test", office_a))
    client_id = register(Client())
    _, challenge = pkce()
    page = web.get("/oauth/authorize/", authorize_params(client_id, challenge))
    data = hidden_fields(page)
    data["organization"] = str(office_a.id)
    result = web.post("/oauth/authorize/", data)
    assert result.status_code == 302
    query = parse_qs(urlsplit(result["Location"]).query)
    assert query["error"] == ["access_denied"] and "code" not in query
    assert McpConsent.objects.count() == 0


# --- token --------------------------------------------------------------------------------


def test_the_code_is_one_use_and_needs_the_right_verifier(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    anonymous = Client()
    client_id = register(anonymous)
    grant = consent(web, client_id, office_a)
    assert exchange(anonymous, grant, code_verifier="x" * 50).status_code == 400
    grant = consent(web, client_id, office_a)
    assert exchange(anonymous, grant).status_code == 200
    assert exchange(anonymous, grant).status_code == 400


def test_the_exchange_refuses_a_different_redirect_uri_and_a_foreign_resource(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    anonymous = Client()
    client_id = register(
        anonymous, redirect_uris=[CALLBACK, "https://claude.com/api/mcp/auth_callback"]
    )
    grant = consent(web, client_id, office_a)
    assert (
        exchange(
            anonymous, grant, redirect_uri="https://claude.com/api/mcp/auth_callback"
        ).status_code
        == 400
    )
    grant = consent(web, client_id, office_a)
    assert exchange(anonymous, grant, resource="https://atacante.example/mcp").status_code == 400


def test_the_token_is_stored_hashed_and_bound_to_the_resource(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    _, access, refresh_token = full_flow(web, office_a)
    row = get_access_token_model().objects.get(scope=SCOPE)
    assert row.token == "" and row.token_checksum != access
    assert access not in {r.token for r in get_access_token_model().objects.all()}
    assert row.resource == [RESOURCE]
    stored = get_refresh_token_model().objects.get()
    assert stored.token == "" and refresh_token not in stored.token_checksum


def test_the_registration_token_of_the_dcr_never_opens_the_endpoint(
    gateway: None, office_a: Organization
) -> None:
    full_flow(browser(make_user("a@example.test", office_a)), office_a)
    registration = get_access_token_model().objects.exclude(scope=SCOPE).get()
    assert registration.scope != SCOPE and registration.user is None
    assert registration.expires < timezone.now() + timedelta(hours=2)


def test_refresh_rotates_and_a_reused_refresh_token_kills_the_family(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    client_id, access, first = full_flow(web, office_a)
    anonymous = Client()
    second = refresh(anonymous, client_id, first)
    assert second.status_code == 200
    new = second.json()
    assert new["refresh_token"] != first and new["access_token"] != access
    assert refresh(anonymous, client_id, first).status_code == 400
    assert refresh(anonymous, client_id, new["refresh_token"]).status_code == 400


# --- endpoint -----------------------------------------------------------------------------


def test_missing_or_bad_tokens_get_the_bearer_challenge_with_the_metadata_url(
    gateway: None,
) -> None:
    for token in (None, "lixo", "x" * 80):
        response = rpc(Client(), token, "tools/list")
        assert response.status_code == 401
        challenge = response["WWW-Authenticate"]
        assert challenge.startswith("Bearer ")
        assert f'resource_metadata="{ORIGIN}/.well-known/oauth-protected-resource/mcp"' in challenge


def test_a_valid_token_runs_the_handshake_and_lists_only_read_tools(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    _, access, _ = full_flow(web, office_a)
    anonymous = Client()
    init = rpc(anonymous, access, "initialize", {"protocolVersion": "2025-11-25"}).json()
    assert init["result"]["protocolVersion"] == "2025-11-25"
    assert rpc(anonymous, access, "notifications/initialized", request_id=None).status_code == 202
    assert rpc(anonymous, access, "ping").json()["result"] == {}
    names = {t["name"] for t in rpc(anonymous, access, "tools/list").json()["result"]["tools"]}
    assert names == {
        "search_data_catalog",
        "retrieve_knowledge",
        "get_company_context",
        "get_risk_snapshot",
        "list_obligations",
        "explain_classification",
    }


@pytest.mark.parametrize("tool", ["create_classification_draft", "get_answer_evidence", "sql", "x"])
def test_write_and_internal_tools_are_not_callable_externally(
    gateway: None, office_a: Organization, tool: str
) -> None:
    web = browser(make_user("a@example.test", office_a))
    _, access, _ = full_flow(web, office_a)
    with patch(f"{ENDPOINT}.call_tool") as call:
        out = rpc(Client(), access, "tools/call", {"name": tool, "arguments": {}}).json()
    assert out["error"]["code"] == -32602
    call.assert_not_called()


def test_the_office_comes_from_the_consent_never_from_the_call(
    gateway: None, office_a: Organization, office_b: Organization
) -> None:
    person = make_user("a@example.test", office_a, office_b)
    web = browser(person)
    _, access, _ = full_flow(web, office_b)
    seen: dict[str, Any] = {}

    def fake(**kwargs: Any) -> dict[str, object]:
        seen.update(kwargs)
        return {"ok": True}

    with patch(f"{ENDPOINT}.call_tool", side_effect=fake):
        out = rpc(
            Client(),
            access,
            "tools/call",
            {
                "name": "search_data_catalog",
                "arguments": {"query": "x", "organization": str(office_a.id)},
            },
        ).json()
    assert out["result"]["structuredContent"] == {"ok": True}
    assert seen["organization"] == office_b
    assert seen["membership"].organization == office_b
    assert seen["actor"] == person


def test_unknown_arguments_are_refused_by_the_shared_tool_layer(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    _, access, _ = full_flow(web, office_a)
    out = rpc(
        Client(),
        access,
        "tools/call",
        {"name": "search_data_catalog", "arguments": {"query": "x", "organization": "1"}},
    ).json()
    assert out["result"]["isError"] is True


def test_a_token_without_resource_or_for_another_resource_is_refused(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    _, access, _ = full_flow(web, office_a)
    row = get_access_token_model().objects.get(scope=SCOPE)
    for resource in (
        [],
        ["https://atacante.example/mcp"],
        [RESOURCE, "https://atacante.example/mcp"],
        [f"{RESOURCE}/x"],
    ):
        row.resource = resource
        row.save(update_fields=["resource"])
        assert rpc(Client(), access, "tools/list").status_code == 401, resource


def test_an_expired_token_and_a_token_without_the_scope_are_refused(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    _, access, _ = full_flow(web, office_a)
    row = get_access_token_model().objects.get(scope=SCOPE)
    row.scope = "read"
    row.save(update_fields=["scope"])
    assert rpc(Client(), access, "tools/list").status_code == 401
    row.scope = SCOPE
    row.expires = timezone.now() - timedelta(seconds=1)
    row.save(update_fields=["scope", "expires"])
    assert rpc(Client(), access, "tools/list").status_code == 401


def test_revocation_takes_effect_on_the_next_call(gateway: None, office_a: Organization) -> None:
    web = browser(make_user("a@example.test", office_a))
    client_id, access, _ = full_flow(web, office_a)
    anonymous = Client()
    assert rpc(anonymous, access, "tools/list").status_code == 200
    revoked = anonymous.post("/oauth/revoke_token/", {"token": access, "client_id": client_id})
    assert revoked.status_code == 200
    assert rpc(anonymous, access, "tools/list").status_code == 401


def test_leaving_the_office_or_losing_the_authorization_blocks_the_token(
    gateway: None, office_a: Organization
) -> None:
    person = make_user("a@example.test", office_a)
    _, access, _ = full_flow(browser(person), office_a)
    with patch(f"{ENDPOINT}.authorization_is_fresh", return_value=False):
        assert rpc(Client(), access, "tools/list").status_code == 403
    Membership.objects.filter(user=person).update(is_active=False)
    assert rpc(Client(), access, "tools/list").status_code == 403
    Membership.objects.filter(user=person).update(is_active=True)
    Organization.objects.filter(pk=office_a.pk).update(is_active=False)
    assert rpc(Client(), access, "tools/list").status_code == 403


def test_no_read_capability_lists_no_tools(gateway: None, office_a: Organization) -> None:
    _, access, _ = full_flow(browser(make_user("a@example.test", office_a)), office_a)
    with patch(f"{ENDPOINT}.membership_has_capability", return_value=False):
        assert rpc(Client(), access, "tools/list").json()["result"]["tools"] == []


def test_choosing_another_office_for_the_same_client_revokes_the_old_tokens(
    gateway: None, office_a: Organization, office_b: Organization
) -> None:
    person = make_user("a@example.test", office_a, office_b)
    web = browser(person)
    anonymous = Client()
    client_id = register(anonymous)
    first = exchange(anonymous, consent(web, client_id, office_a)).json()
    assert rpc(anonymous, first["access_token"], "tools/list").status_code == 200
    second = exchange(anonymous, consent(web, client_id, office_b)).json()
    assert rpc(anonymous, first["access_token"], "tools/list").status_code == 401
    assert refresh(anonymous, client_id, first["refresh_token"]).status_code == 400
    assert rpc(anonymous, second["access_token"], "tools/list").status_code == 200
    assert McpConsent.objects.get().organization == office_b


def test_two_people_never_share_an_office_through_the_same_client(
    gateway: None, office_a: Organization, office_b: Organization
) -> None:
    pa, pb = make_user("a@example.test", office_a), make_user("b@example.test", office_b)
    anonymous = Client()
    client_id = register(anonymous)
    ta = exchange(anonymous, consent(browser(pa), client_id, office_a)).json()["access_token"]
    tb = exchange(anonymous, consent(browser(pb), client_id, office_b)).json()["access_token"]
    seen: list[Any] = []
    with patch(
        f"{ENDPOINT}.call_tool", side_effect=lambda **kw: seen.append(kw["organization"]) or {}
    ):
        for token in (ta, tb):
            rpc(
                anonymous,
                token,
                "tools/call",
                {"name": "search_data_catalog", "arguments": {"query": "x"}},
            )
    assert seen == [office_a, office_b]


def test_transport_rules(gateway: None, office_a: Organization, settings: Any) -> None:
    _, access, _ = full_flow(browser(make_user("a@example.test", office_a)), office_a)
    client = Client()
    assert client.get("/mcp", HTTP_AUTHORIZATION=f"Bearer {access}").status_code == 405
    assert client.delete("/mcp", HTTP_AUTHORIZATION=f"Bearer {access}").status_code == 405
    assert (
        rpc(client, access, "tools/list", HTTP_ORIGIN="https://atacante.example").status_code == 403
    )
    settings.MCP_GATEWAY_ALLOWED_ORIGINS = ["https://claude.ai"]
    assert rpc(client, access, "tools/list", HTTP_ORIGIN="https://claude.ai").status_code == 200
    query_token = client.post(
        f"/mcp?access_token={access}",
        json.dumps({"jsonrpc": "2.0", "id": 1, "method": "ping"}),
        content_type="application/json",
        HTTP_AUTHORIZATION=f"Bearer {access}",
    )
    assert query_token.status_code == 401
    batch = client.post(
        "/mcp", "[]", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {access}"
    )
    assert batch.status_code == 400
    broken = client.post(
        "/mcp", "{", content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {access}"
    )
    assert broken.status_code == 400
    huge = client.post(
        "/mcp", "x" * 70_000, content_type="application/json", HTTP_AUTHORIZATION=f"Bearer {access}"
    )
    assert huge.status_code == 413
    assert rpc(client, access, "resources/list").json()["error"]["code"] == -32601


def test_the_endpoint_is_rate_limited_per_person(
    gateway: None, office_a: Organization, settings: Any
) -> None:
    settings.MCP_GATEWAY_RATE_LIMIT_PER_MINUTE = 3
    _, access, _ = full_flow(browser(make_user("a@example.test", office_a)), office_a)
    codes = [rpc(Client(), access, "ping").status_code for _ in range(5)]
    assert codes[:3] == [200, 200, 200] and codes[3:] == [429, 429]


def test_oversized_results_are_refused_instead_of_streamed(
    gateway: None, office_a: Organization
) -> None:
    _, access, _ = full_flow(browser(make_user("a@example.test", office_a)), office_a)
    with patch(f"{ENDPOINT}.call_tool", return_value={"texto": "a" * 40_000}):
        out = rpc(
            Client(),
            access,
            "tools/call",
            {"name": "search_data_catalog", "arguments": {"query": "x"}},
        ).json()
    assert out["error"]["code"] == -32603


def test_the_session_cookie_never_authenticates_the_endpoint(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    assert rpc(web, None, "tools/list").status_code == 401


# --- CIMD ---------------------------------------------------------------------------------


def test_cimd_client_ids_outside_the_allowed_hosts_are_never_fetched(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    params = authorize_params("https://atacante.example/client.json", pkce()[1])
    with patch(
        "oauth2_provider.cimd.SafeMetadataFetcher.fetch", side_effect=AssertionError("fetch")
    ) as fetch:
        response = web.get("/oauth/authorize/", params)
    assert response.status_code != 302
    fetch.assert_not_called()


def test_the_application_model_is_the_stock_one() -> None:
    assert get_application_model().__name__ == "Application"


def test_consent_and_office_switch_leave_an_audit_trail_without_the_client_secret_material(
    gateway: None, office_a: Organization, office_b: Organization
) -> None:
    from apps.audit.models import AuditEvent

    person = make_user("a@example.test", office_a, office_b)
    web = browser(person)
    anonymous = Client()
    client_id = register(anonymous)
    consent(web, client_id, office_a)
    consent(web, client_id, office_b)
    events = list(
        AuditEvent.objects.filter(action__startswith="mcpgateway.").order_by("occurred_at")
    )
    assert [e.action for e in events] == [
        "mcpgateway.consent_granted",
        "mcpgateway.tokens_revoked",
        "mcpgateway.consent_granted",
    ]
    assert [e.organization_id for e in events] == [office_a.id, office_a.id, office_b.id]
    assert all(client_id not in json.dumps(e.metadata) for e in events)
    assert all(e.actor_id == person.id for e in events)


# --- achados da revisao independente (triagem) ----------------------------------------------


@pytest.mark.parametrize("separator", [" ", chr(9), chr(10), chr(0xA0), chr(0x2003)])
@pytest.mark.parametrize("head", ["http://localhost/a", "https://chatgpt.com/connector/oauth/x"])
def test_registration_refuses_two_uris_glued_by_whitespace(
    gateway: None, head: str, separator: str
) -> None:
    before = get_application_model().objects.count()
    response = post_register({"redirect_uris": [f"{head}{separator}https://atacante.example/cb"]})
    assert response.status_code in {400, 401, 403}
    assert get_application_model().objects.count() == before


def test_registration_without_an_auth_method_still_makes_a_public_client(gateway: None) -> None:
    response = post_register({"redirect_uris": [CALLBACK]})
    assert response.status_code == 201
    assert "client_secret" not in response.json()
    assert get_application_model().objects.get().client_type == "public"


@pytest.mark.parametrize(
    "grants", [["authorization_code", ["a"]], ["authorization_code", {"a": 1}], "x", 5]
)
def test_registration_with_odd_grant_types_is_refused_not_a_server_error(
    gateway: None, grants: Any
) -> None:
    response = post_register({"redirect_uris": [CALLBACK], "grant_types": grants})
    assert response.status_code in {400, 401, 403}


def _cimd_document(url: str, redirects: list[str]) -> tuple[dict[str, Any], int]:
    return {"client_id": url, "client_name": "Claude", "redirect_uris": redirects}, 300


CIMD_URL = "https://claude.ai/oauth/client-metadata.json"


def test_a_cimd_document_cannot_widen_the_redirect_list(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    document = _cimd_document(CIMD_URL, ["https://atacante.example/cb"])
    with patch("oauth2_provider.cimd.SafeMetadataFetcher.fetch", return_value=document):
        params = authorize_params(CIMD_URL, pkce()[1], redirect_uri="https://atacante.example/cb")
        response = web.get("/oauth/authorize/", params)
    assert response.status_code != 200
    assert "atacante" not in str(response.get("Location", ""))
    assert not get_application_model().objects.filter(client_id=CIMD_URL).exists()


def test_a_cimd_document_with_the_known_callback_works(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    document = _cimd_document(CIMD_URL, [CALLBACK])
    with patch("oauth2_provider.cimd.SafeMetadataFetcher.fetch", return_value=document):
        page = web.get("/oauth/authorize/", authorize_params(CIMD_URL, pkce()[1]))
    assert page.status_code == 200


def test_approval_prompt_auto_never_skips_the_consent_screen(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    client_id, _, _ = full_flow(web, office_a)
    params = authorize_params(client_id, pkce()[1], approval_prompt="auto")
    response = web.get("/oauth/authorize/", params)
    assert response.status_code == 200
    assert "code=" not in str(response.get("Location", ""))


def test_a_deactivated_person_loses_the_endpoint_and_the_refresh(
    gateway: None, office_a: Organization
) -> None:
    person = make_user("a@example.test", office_a)
    client_id, access, refresh_token = full_flow(browser(person), office_a)
    person.is_active = False
    person.save(update_fields=["is_active"])
    assert rpc(Client(), access, "tools/list").status_code in {401, 403}
    assert refresh(Client(), client_id, refresh_token).status_code == 400


def test_a_form_encoded_post_to_the_endpoint_is_refused_cleanly(
    gateway: None, office_a: Organization
) -> None:
    _, access, _ = full_flow(browser(make_user("a@example.test", office_a)), office_a)
    for content_type, body in (
        ("multipart/form-data; boundary=x", "--x--\r\n"),
        ("application/x-www-form-urlencoded", "a=b"),
        ("text/plain", "{}"),
    ):
        response = Client().post(
            "/mcp", body, content_type=content_type, HTTP_AUTHORIZATION=f"Bearer {access}"
        )
        assert response.status_code == 415, content_type


def test_a_failed_authorization_changes_nothing(
    gateway: None, office_a: Organization, office_b: Organization
) -> None:
    person = make_user("a@example.test", office_a, office_b)
    web = browser(person)
    anonymous = Client()
    client_id = register(anonymous)
    first = exchange(anonymous, consent(web, client_id, office_a)).json()
    page = web.get("/oauth/authorize/", authorize_params(client_id, pkce()[1]))
    data = hidden_fields(page)
    data.update(
        {"code_challenge_method": "plain", "allow": "true", "organization": str(office_b.id)}
    )
    web.post("/oauth/authorize/", data)
    assert McpConsent.objects.get().organization == office_a
    assert rpc(anonymous, first["access_token"], "tools/list").status_code == 200


def test_plain_pkce_is_refused_before_the_consent_screen(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    params = authorize_params(register(Client()), pkce()[1], code_challenge_method="plain")
    assert web.get("/oauth/authorize/", params).status_code != 200


def test_a_code_issued_before_an_office_change_dies_with_the_change(
    gateway: None, office_a: Organization, office_b: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a, office_b))
    anonymous = Client()
    client_id = register(anonymous)
    in_flight = consent(web, client_id, office_a)
    consent(web, client_id, office_b)
    assert exchange(anonymous, in_flight).status_code == 400


def test_the_consent_page_lets_the_form_post_redirect_to_the_client_origin(
    gateway: None, office_a: Organization
) -> None:
    web = browser(make_user("a@example.test", office_a))
    page = web.get("/oauth/authorize/", authorize_params(register(Client()), pkce()[1]))
    policy = page["Content-Security-Policy"]
    directive = next(d for d in policy.split(";") if d.strip().startswith("form-action"))
    assert "'self'" in directive and "https://claude.ai" in directive
    assert "atacante" not in directive


@pytest.mark.parametrize(
    "stored",
    [
        "https://cica.test/mcp?x=1",
        "https://cica.test/mcp#f",
        "https://CICA.test/mcp",
        "https://cica.test/mcp/",
    ],
)
def test_the_audience_check_is_plain_string_equality(gateway: None, stored: str) -> None:
    from apps.mcpgateway.conf import resource_matches

    assert resource_matches("", [stored]) is False
    assert resource_matches("", [RESOURCE]) is True


@pytest.mark.parametrize(
    "uri",
    [
        "https://chatgpt.com/connector/oauth/../admin",
        "https://chatgpt.com/connector/oauth/%2e%2e/admin",
        "https://chatgpt.com/connector/oauth/a/b",
        "https://chatgpt.com/connector/oauth/",
        "https://chatgpt.com/connector/oauth/a%2fb",
        "https://chatgpt.com/connector/oauth/a.b",
        "https://chatgpt.com:8443/connector/oauth/abc",
        "http://chatgpt.com/connector/oauth/abc",
    ],
)
def test_the_chatgpt_callback_is_one_safe_segment_on_the_exact_host(
    gateway: None, uri: str
) -> None:
    from apps.mcpgateway.registration import redirect_allowed

    assert redirect_allowed(uri) is False
    assert redirect_allowed("https://chatgpt.com/connector/oauth/Ab-9_x") is True
