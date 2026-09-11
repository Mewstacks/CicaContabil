from __future__ import annotations

from django.http import HttpRequest
from django.utils.http import url_has_allowed_host_and_scheme


def safe_next(request: HttpRequest, candidate: str | None, *, fallback: str) -> str:
    """Return a caller-supplied redirect target only when it stays on this host.

    An unvalidated ``next`` is an open redirect: after a successful sign-in the
    browser would follow an attacker-chosen domain while the user still believes
    they are inside the product.
    """

    if candidate and url_has_allowed_host_and_scheme(
        url=candidate,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return candidate
    return fallback
