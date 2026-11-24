"""Identidade fixa do gateway MCP externo (D-333): URL do recurso, do emissor e escopo.

`resource` (RFC 8707) e `iss` (RFC 9207) saem da configuracao, nunca do cabecalho `Host` da
requisicao: um cabecalho forjado nao muda para quem o token vale.
"""

from __future__ import annotations

from django.conf import settings

MCP_PATH = "/mcp"
OAUTH_PREFIX = "/oauth"


def enabled() -> bool:
    return bool(settings.MCP_GATEWAY_ENABLED and settings.MCP_GATEWAY_PUBLIC_URL)


def origin() -> str:
    return str(settings.MCP_GATEWAY_PUBLIC_URL).rstrip("/")


def resource_url() -> str:
    return f"{origin()}{MCP_PATH}"


def issuer_url() -> str:
    return f"{origin()}{OAUTH_PREFIX}"


def metadata_url() -> str:
    """Onde o recurso publica os metadados (RFC 9728, forma com caminho)."""
    return f"{origin()}/.well-known/oauth-protected-resource{MCP_PATH}"


def required_scope() -> str:
    return str(settings.MCP_GATEWAY_SCOPE)


def resource_matches(request_uri: str, audiences: list[str]) -> bool:
    """Validador de audiencia do DOT: so vale o recurso exato, comparado como texto.

    O padrao do DOT casa por prefixo; aqui qualquer diferenca (barra final, consulta, fragmento,
    caixa do host) e recusa. Um token sem `resource` nunca chega a este ponto: o endpoint
    recusa antes.
    """
    target = resource_url()
    return bool(audiences) and all(audience == target for audience in audiences)
