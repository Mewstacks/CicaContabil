from __future__ import annotations

from urllib.parse import urlencode

from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
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


def detail_redirect(request: HttpRequest, view: str, **kwargs: object) -> HttpResponseRedirect:
    """Retain the originating list after a detail action; the template validates it."""
    target = reverse(view, kwargs=kwargs)
    candidate = request.POST.get("return_to") or request.GET.get("return_to")
    if candidate:
        target += "?" + urlencode({"return_to": candidate})
    return redirect(target)
