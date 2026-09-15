from __future__ import annotations

from collections.abc import Callable
from urllib.parse import quote

from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.urls import resolve, reverse

from apps.accounts import mfa
from apps.accounts.models import User

# Reaching the second-factor screens must not itself require a verified second factor,
# and signing out has to stay available to somebody who cannot complete one.
EXEMPT_URL_NAMES = frozenset(
    {
        "accounts:mfa-setup",
        "accounts:mfa-verify",
        "accounts:mfa-qr",
        "accounts:mfa-recovery-codes",
        "hub:login",
        "hub:logout",
        "hub:home",
        "hub:legal",
        "hub:proposal",
        "hub:proposal-cnpj",
        "hub:signup",
        "hub:signup-verify",
    }
)
EXEMPT_PATH_PREFIXES = ("/api/v1/health/",)


class MfaEnforcementMiddleware:
    """Hold a session at the door until the account's required second factor is given.

    The check lives in middleware rather than in each decorator so a view added later
    cannot silently skip it.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        user = getattr(request, "user", None)
        if (
            isinstance(user, User)
            and user.is_authenticated
            and not mfa.session_is_verified(request)
            and not self._is_exempt(request)
            and mfa.is_required(user)
        ):
            target = "accounts:mfa-verify" if mfa.is_enrolled(user) else "accounts:mfa-setup"
            return redirect(f"{reverse(target)}?next={quote(request.get_full_path())}")
        return self.get_response(request)

    def _is_exempt(self, request: HttpRequest) -> bool:
        if request.path.startswith(EXEMPT_PATH_PREFIXES):
            return True
        try:
            match = resolve(request.path_info)
        except Exception:
            return False
        return bool(match.view_name in EXEMPT_URL_NAMES)
