"""Rotas do gateway MCP externo (D-333). Todas respondem 404 com o gateway desligado.

So entram as views do DOT que o gateway usa: metadados, autorizacao, token, revogacao e cadastro.
Introspeccao, fluxo de dispositivo, OIDC e telas de gerencia de aplicativo ficam de fora de
proposito. Os nomes seguem o namespace `oauth2_provider`, que o DOT usa para montar as URLs
anunciadas nos metadados.
"""

from __future__ import annotations

import functools
from collections.abc import Callable
from typing import Any

from django.http import HttpRequest, HttpResponse
from django.urls import include, path
from oauth2_provider import views as dot

from apps.mcpgateway import agent_api, conf, views
from apps.mcpgateway.authorize import McpAuthorizationView
from apps.mcpgateway.endpoint import mcp_endpoint


def gated(view: Callable[..., HttpResponse]) -> Callable[..., HttpResponse]:
    @functools.wraps(view)
    def wrapper(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
        if not conf.enabled():
            return HttpResponse(status=404)
        return view(request, *args, **kwargs)

    return wrapper


_oauth_patterns = [
    path(
        ".well-known/oauth-authorization-server",
        gated(dot.OAuthServerMetadataView.as_view()),
        name="oauth-server-metadata",
    ),
    path(
        ".well-known/oauth-authorization-server/oauth",
        gated(dot.OAuthServerMetadataView.as_view()),
        name="oauth-server-metadata-issuer-path",
    ),
    path(
        ".well-known/oauth-protected-resource/mcp",
        gated(dot.OAuthProtectedResourceMetadataView.as_view()),
        name="oauth-resource-metadata",
    ),
    path("oauth/authorize/", McpAuthorizationView.as_view(), name="authorize"),
    path("oauth/token/", gated(dot.TokenView.as_view()), name="token"),
    path("oauth/revoke_token/", gated(dot.RevokeTokenView.as_view()), name="revoke-token"),
    path(
        "oauth/register/",
        gated(dot.DynamicClientRegistrationView.as_view()),
        name="dcr-register",
    ),
    # O DOT monta `registration_client_uri` com este nome, mas a gerencia (RFC 7592) deixaria o
    # cliente trocar os redirecionamentos depois do cadastro e furar a lista fixa: a rota existe
    # so para o `reverse` e responde 404.
    path(
        "oauth/register/<str:client_id>/",
        lambda request, client_id: HttpResponse(status=404),
        name="dcr-register-management",
    ),
]

urlpatterns = [
    path("", include((_oauth_patterns, "oauth2_provider"), namespace="oauth2_provider")),
    path("mcp", mcp_endpoint, name="mcp"),
    path("app/conector-mcp/", views.connector, name="mcp-connector"),
    path("api/agent/mcp/claim", agent_api.claim, name="agent-mcp-claim"),
    path("api/agent/mcp/result", agent_api.result, name="agent-mcp-result"),
]
