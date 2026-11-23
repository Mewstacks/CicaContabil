"""Cloudflare Turnstile no cadastro de escritório novo (E2): barra robô sem pedir imagem.

Fonte: developers.cloudflare.com/turnstile (server-side-validation, client-side-rendering e
reference/content-security-policy), lidas em 2026-11-20.

- O navegador carrega `https://challenges.cloudflare.com/turnstile/v0/api.js` (exatamente essa URL;
  proxiar ou guardar em cache quebra o widget) e posta o token no campo `cf-turnstile-response`.
- O servidor confirma o token em `POST https://challenges.cloudflare.com/turnstile/v0/siteverify`
  com `secret` e `response`. Token: até 2048 caracteres, vale 300 s, uso único.
- CSP: `script-src` e `frame-src` com `https://challenges.cloudflare.com`.

Desligado enquanto `TURNSTILE_SITE_KEY` ou `TURNSTILE_SECRET_KEY` estiver vazio: o cadastro fica
como era. Ligado, falha **fechada**: sem token válido, ou com a Cloudflare fora do ar, ninguém se
cadastra (o limite por IP continua valendo de qualquer forma). O IP do visitante não é enviado
(`remoteip` é opcional): minimização de dados, LGPD.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from typing import Any, cast
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from django.conf import settings
from django.http import HttpResponse
from django.utils.csp import CSP

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"
API_SCRIPT_URL = "https://challenges.cloudflare.com/turnstile/v0/api.js"
ORIGIN = "https://challenges.cloudflare.com"
FIELD = "cf-turnstile-response"
MAX_TOKEN_LENGTH = 2048
TIMEOUT_SECONDS = 5

OK = "ok"
FAILED = "failed"
UNAVAILABLE = "unavailable"

Post = Callable[[str, dict[str, str], float], dict[str, Any]]


def enabled() -> bool:
    return bool(settings.TURNSTILE_SITE_KEY and settings.TURNSTILE_SECRET_KEY)


def site_key() -> str:
    return str(settings.TURNSTILE_SITE_KEY) if enabled() else ""


def _post(url: str, data: dict[str, str], timeout: float) -> dict[str, Any]:
    request = Request(  # noqa: S310 - fixed HTTPS origin
        url,
        data=urlencode(data).encode(),
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "User-Agent": "CICA/1.0",
        },
        method="POST",
    )
    with urlopen(request, timeout=timeout) as response:  # noqa: S310 - fixed HTTPS origin
        payload = json.loads(response.read(65_536))
    if not isinstance(payload, dict):
        raise ValueError("unexpected siteverify payload")
    return payload


def verify(token: str, *, hostname: str = "", post: Post | None = None) -> str:
    """`ok`, `failed` (token ruim, vencido, repetido ou de outro site) ou `unavailable`."""

    if not token or len(token) > MAX_TOKEN_LENGTH:
        return FAILED
    send = post or _post
    try:
        result = send(
            SITEVERIFY_URL,
            {"secret": str(settings.TURNSTILE_SECRET_KEY), "response": token},
            TIMEOUT_SECONDS,
        )
    except (URLError, TimeoutError, OSError, ValueError):
        logger.warning("turnstile.siteverify_unavailable")
        return UNAVAILABLE
    if result.get("success") is not True:
        codes = result.get("error-codes")
        logger.info("turnstile.rejected codes=%s", codes if isinstance(codes, list) else [])
        if isinstance(codes, list) and "internal-error" in codes:
            return UNAVAILABLE
        return FAILED
    if (
        settings.TURNSTILE_CHECK_HOSTNAME
        and hostname
        and str(result.get("hostname", "")).lower() != hostname.lower()
    ):
        logger.warning("turnstile.hostname_mismatch")
        return FAILED
    return OK


def allow_in_csp(response: HttpResponse) -> HttpResponse:
    """Abre `script-src` e `frame-src` para a Cloudflare só na página que mostra o widget."""

    current = cast("dict[str, list[str]]", settings.SECURE_CSP)
    config = {key: list(value) for key, value in current.items()}
    config["script-src"] = [*config.get("script-src", [CSP.SELF]), ORIGIN]
    config["frame-src"] = [*config.get("frame-src", []), ORIGIN]
    response._csp_config = config  # type: ignore[attr-defined]
    return response
