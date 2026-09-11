from __future__ import annotations

import json
from time import perf_counter
from typing import Any

from django.conf import settings
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.http import require_POST

from apps.audit.services import record_event
from apps.common.ratelimit import rate_limited
from apps.hub.controlplane import authorization_is_fresh
from apps.hub.views import active_membership
from apps.intelligence.mcp import PROTOCOL_VERSION, TOOLS, McpToolError, call_tool


def _response(payload: dict[str, object], status: int = 200) -> JsonResponse:
    response = JsonResponse(payload, status=status)
    response["Cache-Control"] = "no-store"
    return response


def _error(request_id: object, code: int, message: str, status: int = 200) -> JsonResponse:
    return _response(
        {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}, status
    )


@require_POST
def mcp_endpoint(request: HttpRequest) -> HttpResponse:
    """MCP JSON-RPC transport for the Hub-internal gateway only."""
    if not request.user.is_authenticated:
        return _error(None, -32001, "Autenticação necessária.", 401)
    if rate_limited(
        f"mcp:{request.user.pk}", limit=settings.MCP_RATE_LIMIT_PER_MINUTE, window_seconds=60
    ):
        return _error(None, -32005, "Muitas requisições. Tente novamente em instantes.", 429)
    if len(request.body) > 65_536:
        return _error(None, -32600, "Requisição MCP excede 64 KB.", 413)
    try:
        payload: Any = json.loads(request.body)
    except (TypeError, UnicodeDecodeError, json.JSONDecodeError):
        return _error(None, -32700, "JSON inválido.", 400)
    if not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0":
        return _error(
            payload.get("id") if isinstance(payload, dict) else None,
            -32600,
            "Requisição JSON-RPC inválida.",
        )
    request_id = payload.get("id")
    method = payload.get("method")
    params = payload.get("params", {})
    if not isinstance(method, str) or not isinstance(params, dict):
        return _error(request_id, -32600, "Método ou parâmetros inválidos.")
    membership = active_membership(request)
    if membership is None:
        return _error(request_id, -32001, "Escritório não selecionado.", 403)
    organization = membership.organization
    if not authorization_is_fresh(organization):
        return _error(
            request_id, -32001, "PermissÃ£o expirada; aguarde a renovaÃ§Ã£o pelo CRMew.", 403
        )
    if method == "initialize":
        return _response(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "protocolVersion": PROTOCOL_VERSION,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "hub-dominio-mcp", "version": "0.1.0"},
                },
            }
        )
    if method == "tools/list":
        return _response({"jsonrpc": "2.0", "id": request_id, "result": {"tools": TOOLS}})
    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments", {})
        if not isinstance(name, str) or not isinstance(arguments, dict):
            return _error(request_id, -32602, "Ferramenta ou argumentos inválidos.")
        started_at = perf_counter()
        try:
            structured = call_tool(
                name=name,
                arguments=arguments,
                organization=organization,
                membership=membership,
                actor=request.user,
                request=request,
            )
        except McpToolError as exc:
            record_event(
                action="intelligence.mcp.tool_called",
                actor=request.user,
                organization=organization,
                request=request,
                success=False,
                metadata={
                    "tool": name,
                    "purpose": "internal_mcp_business_query",
                    "failure_class": "tool_validation",
                    "latency_ms": round((perf_counter() - started_at) * 1_000),
                },
            )
            return _error(request_id, -32602, str(exc))
        return _response(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {"type": "text", "text": "Consulta concluída com fontes compactas."}
                    ],
                    "structuredContent": structured,
                },
            }
        )
    return _error(request_id, -32601, "Método MCP não implementado.")
