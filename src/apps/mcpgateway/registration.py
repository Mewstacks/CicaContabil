"""Cadastro de cliente OAuth (DCR, RFC 7591) do gateway MCP externo (D-333).

O DOT deixa o cadastro aberto ou fechado; aqui ele fica aberto so para quem cumpre a regra:
redirecionamentos da lista fixa (comparacao exata; loopback sem porta), so `authorization_code`,
so cliente publico (`none`, sempre com PKCE) e teto por IP e por hora. O que passar daqui ainda
precisa do login do CICA e do consentimento de uma pessoa para virar token.
"""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlsplit

from django.conf import settings
from django.http import HttpRequest
from oauth2_provider.cimd import CIMDError, SafeMetadataFetcher

from apps.common.network import client_ip
from apps.common.ratelimit import rate_limited

ALLOWED_GRANTS = frozenset({"authorization_code", "refresh_token"})
MAX_BODY = 8 * 1024
MAX_REDIRECTS = 5
PUBLIC_CLIENT = "none"  # RFC 7591: sem segredo; a protecao vem do PKCE
_LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})
_UNSAFE = re.compile(r"[\s\x00-\x1f\x7f]")


def redirect_allowed(uri: str) -> bool:
    """Lista fixa por comparacao exata; loopback so em `http` e sem fragmento ou userinfo."""
    if not isinstance(uri, str) or len(uri) > 300:
        return False
    # O DOT guarda a lista unida por espaco e a separa de novo: um elemento com espaco (ou
    # qualquer separador Unicode) viraria dois redirecionamentos, o segundo sem conferencia.
    if _UNSAFE.search(uri) or not uri.isascii():
        return False
    if uri in settings.MCP_GATEWAY_REDIRECT_URIS:
        return True
    parts = urlsplit(uri)
    if parts.fragment or parts.username or parts.password or parts.query:
        return False
    if parts.scheme == "http" and parts.hostname in _LOOPBACK_HOSTS:
        return True
    return any(
        uri.startswith(prefix)
        for prefix in settings.MCP_GATEWAY_REDIRECT_PREFIXES
        if prefix.startswith("https://")
    )


def _metadata(request: HttpRequest) -> dict[str, Any] | None:
    if len(request.body) > MAX_BODY:
        return None
    try:
        data = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


class RegistrationPermission:
    """`DCR_REGISTRATION_PERMISSION_CLASSES`: recusa antes de o DOT gravar qualquer linha."""

    def has_permission(self, request: HttpRequest) -> bool:
        if request.method != "POST":
            return False
        if rate_limited(
            f"mcp-dcr:{client_ip(request) or 'unknown'}",
            limit=settings.MCP_GATEWAY_REGISTRATION_PER_HOUR,
            window_seconds=3600,
        ):
            return False
        data = _metadata(request)
        if data is None:
            return False
        redirects = data.get("redirect_uris")
        if (
            not isinstance(redirects, list)
            or not 1 <= len(redirects) <= MAX_REDIRECTS
            or not all(redirect_allowed(uri) for uri in redirects)
        ):
            return False
        grants = data.get("grant_types", ["authorization_code"])
        if (
            not isinstance(grants, list)
            or not all(isinstance(grant, str) for grant in grants)
            or "authorization_code" not in grants
            or not set(grants) <= ALLOWED_GRANTS
        ):
            return False
        method = data.get("token_endpoint_auth_method", PUBLIC_CLIENT)
        if "token_endpoint_auth_method" not in data:
            # RFC 7591 §2: o padrao seria `client_secret_basic`; aqui so existe cliente publico.
            data["token_endpoint_auth_method"] = PUBLIC_CLIENT
            request._body = json.dumps(data).encode("utf-8")
        return bool(method == PUBLIC_CLIENT)


class RedirectCheckedFetcher(SafeMetadataFetcher):
    """CIMD: o documento do cliente tambem nao pode ampliar a lista de redirecionamentos.

    O host do `client_id` ja e restrito, mas a lista de `redirect_uris` vem do documento e e
    relida a cada vencimento do cache; aqui cada uma passa pela mesma regra do cadastro.
    """

    def fetch(self, client_id: str) -> tuple[dict[str, Any], int]:
        metadata, max_age = super().fetch(client_id)
        redirects = metadata.get("redirect_uris")
        if (
            not isinstance(redirects, list)
            or not 1 <= len(redirects) <= MAX_REDIRECTS
            or not all(redirect_allowed(uri) for uri in redirects)
        ):
            raise CIMDError("redirect_uris fora da lista permitida")
        return metadata, max_age
