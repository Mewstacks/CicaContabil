"""Endpoint MCP externo (Streamable HTTP, so POST/JSON) do gateway (D-333).

Ordem de cada chamada, e cada degrau tem teste de recusa:

1. gateway ligado e `Origin` (se vier) na lista; so POST;
2. token Bearer valido no DOT (hash no banco, expiracao, escopo) e **audiencia exata**: token sem
   `resource` ou de outro recurso nunca passa, ao contrario do padrao do DOT;
3. escritorio vindo do vinculo (pessoa, cliente) gravado no consentimento, com o vinculo do
   escritorio ainda ativo e a permissao do controle central fresca;
4. teto por pessoa e por escritorio;
5. so as ferramentas de leitura; o conjunto e filtrado pela capacidade do perfil.

O token nao carrega nada alem do que o DOT guarda; o escritorio nunca vem do corpo da chamada.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from oauth2_provider.oauth2_backends import get_oauthlib_core

from apps.common.ratelimit import rate_limited
from apps.hub.controlplane import authorization_is_fresh, membership_has_capability
from apps.intelligence.mcp import TOOLS, McpToolError, call_tool
from apps.mcpgateway import conf
from apps.mcpgateway.models import McpConsent
from apps.organizations.models import Membership

SUPPORTED_PROTOCOLS = ("2025-11-25", "2025-06-18", "2025-03-26")
MAX_BODY = 64 * 1024
MAX_RESULT_BYTES = 32 * 1024
EXTERNAL_TOOLS = frozenset(
    {
        "search_data_catalog",
        "retrieve_knowledge",
        "get_company_context",
        "get_risk_snapshot",
        "list_obligations",
        "explain_classification",
    }
)


@dataclass(frozen=True)
class Caller:
    user: Any
    membership: Membership
    token_id: int


def _json(payload: dict[str, Any], status: int = 200) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response


def _rpc_error(request_id: object, code: int, message: str, status: int = 200) -> JsonResponse:
    return _json(
        {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}, status
    )


def _challenge(error: str | None = None, status: int = 401) -> HttpResponse:
    parts = ['Bearer realm="mcp"', f'resource_metadata="{conf.metadata_url()}"']
    if error:
        parts.append(f'error="{error}"')
    if error == "insufficient_scope":
        parts.append(f'scope="{conf.required_scope()}"')
    response = _json({"error": error or "unauthorized"}, status)
    response["WWW-Authenticate"] = ", ".join(parts)
    return response


def _origin_allowed(request: HttpRequest) -> bool:
    origin = request.headers.get("Origin")
    return origin is None or origin in settings.MCP_GATEWAY_ALLOWED_ORIGINS


def authenticate(request: HttpRequest) -> Caller | HttpResponse:
    header = request.headers.get("Authorization", "")
    if not header.lower().startswith("bearer ") or "access_token" in request.GET:
        return _challenge()
    valid, oauth_request = get_oauthlib_core().verify_request(
        request, scopes=[conf.required_scope()]
    )
    token = getattr(oauth_request, "access_token", None)
    if not valid or token is None:
        return _challenge("invalid_token")
    if not token.resource or not token.allows_audience(conf.resource_url()):
        return _challenge("invalid_token")
    if token.user is None or not token.user.is_active:
        return _challenge("invalid_token")
    consent = (
        McpConsent.objects.select_related("organization")
        .filter(user=token.user, application=token.application)
        .first()
    )
    if consent is None:
        return _challenge("invalid_token")
    membership = (
        Membership.objects.select_related("organization")
        .filter(
            user=token.user,
            organization=consent.organization,
            is_active=True,
            organization__is_active=True,
        )
        .first()
    )
    if membership is None or not authorization_is_fresh(membership.organization):
        return _json({"error": "access_denied"}, 403)
    return Caller(user=token.user, membership=membership, token_id=token.pk)


def _tools_for(membership: Membership) -> list[dict[str, object]]:
    if not membership_has_capability(membership=membership, capability="read"):
        return []
    return [tool for tool in TOOLS if tool["name"] in EXTERNAL_TOOLS]


def _call(
    request: HttpRequest, caller: Caller, request_id: object, params: dict[str, Any]
) -> JsonResponse:
    name = params.get("name")
    arguments = params.get("arguments", {})
    if not isinstance(name, str) or not isinstance(arguments, dict):
        return _rpc_error(request_id, -32602, "Ferramenta ou argumentos inválidos.")
    # a mesma lista que `tools/list` mostra: lista e chamada nao podem divergir
    if name not in {tool["name"] for tool in _tools_for(caller.membership)}:
        return _rpc_error(request_id, -32602, "Ferramenta não disponível neste conector.")
    try:
        structured = call_tool(
            name=name,
            arguments=arguments,
            organization=caller.membership.organization,
            membership=caller.membership,
            actor=caller.user,
            request=request,
        )
    except McpToolError as exc:
        return _json(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {"content": [{"type": "text", "text": str(exc)}], "isError": True},
            }
        )
    text = json.dumps(structured, ensure_ascii=False, separators=(",", ":"), default=str)
    if len(text.encode("utf-8")) > MAX_RESULT_BYTES:
        return _rpc_error(request_id, -32603, "Resultado grande demais; refine a consulta.")
    return _json(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "content": [{"type": "text", "text": text}],
                "structuredContent": structured,
            },
        }
    )


def _initialize(request_id: object, params: dict[str, Any]) -> JsonResponse:
    asked = params.get("protocolVersion")
    version = asked if asked in SUPPORTED_PROTOCOLS else SUPPORTED_PROTOCOLS[0]
    return _json(
        {
            "jsonrpc": "2.0",
            "id": request_id,
            "result": {
                "protocolVersion": version,
                "capabilities": {"tools": {"listChanged": False}},
                "serverInfo": {"name": "cica-mcp", "version": "0.1.0"},
            },
        }
    )


@csrf_exempt
def mcp_endpoint(request: HttpRequest) -> HttpResponse:
    if not conf.enabled():
        return HttpResponse(status=404)
    if not _origin_allowed(request):
        return _json({"error": "origin_not_allowed"}, 403)
    if request.method != "POST":
        response = _json({"error": "method_not_allowed"}, 405)
        response["Allow"] = "POST"
        return response
    if request.content_type != "application/json":
        return _rpc_error(None, -32600, "Use application/json.", 415)
    caller = authenticate(request)
    if isinstance(caller, HttpResponse):
        return caller
    if rate_limited(
        f"mcpx:u:{caller.user.pk}",
        limit=settings.MCP_GATEWAY_RATE_LIMIT_PER_MINUTE,
        window_seconds=60,
    ) or rate_limited(
        f"mcpx:o:{caller.membership.organization_id}",
        limit=settings.MCP_GATEWAY_ORG_RATE_LIMIT_PER_MINUTE,
        window_seconds=60,
    ):
        response = _rpc_error(None, -32005, "Muitas requisições.", 429)
        response["Retry-After"] = "60"
        return response
    if len(request.body) > MAX_BODY:
        return _rpc_error(None, -32600, "Requisição excede 64 KB.", 413)
    try:
        payload: Any = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _rpc_error(None, -32700, "JSON inválido.", 400)
    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        return _rpc_error(None, -32600, "Requisição JSON-RPC inválida.", 400)
    method, params = payload.get("method"), payload.get("params", {})
    if not isinstance(method, str) or not isinstance(params, dict):
        return _rpc_error(payload.get("id"), -32600, "Método ou parâmetros inválidos.")
    if "id" not in payload:  # notificacao: sem resposta
        return HttpResponse(status=202)
    request_id = payload["id"]
    if method == "initialize":
        return _initialize(request_id, params)
    if method == "ping":
        return _json({"jsonrpc": "2.0", "id": request_id, "result": {}})
    if method == "tools/list":
        return _json(
            {"jsonrpc": "2.0", "id": request_id, "result": {"tools": _tools_for(caller.membership)}}
        )
    if method == "tools/call":
        return _call(request, caller, request_id, params)
    return _rpc_error(request_id, -32601, "Método MCP não implementado.")
