from __future__ import annotations

from django.http import HttpRequest
from rest_framework.request import Request
from rest_framework.throttling import AnonRateThrottle, ScopedRateThrottle, UserRateThrottle

from apps.common.network import client_ip


class ClientIPIdentMixin:
    """Throttle per validated edge IP instead of the caller-supplied forwarded header.

    DRF's ``get_ident`` returns the raw ``X-Forwarded-For`` value whenever ``NUM_PROXIES``
    is unset, so any client can mint a fresh throttle bucket per request by varying the
    header. ``apps.common.network.client_ip`` only trusts ``REMOTE_ADDR`` and the
    edge-controlled ``Fly-Client-IP`` header, so buckets cannot be forged.
    """

    def get_ident(self, request: Request | HttpRequest) -> str:
        # An unparseable address collapses into a single shared bucket rather than an
        # unthrottled one, so a malformed peer address can never buy extra quota.
        return client_ip(getattr(request, "_request", request)) or ""


class IPAnonRateThrottle(ClientIPIdentMixin, AnonRateThrottle):
    pass


class IPUserRateThrottle(ClientIPIdentMixin, UserRateThrottle):
    pass


class IPScopedRateThrottle(ClientIPIdentMixin, ScopedRateThrottle):
    pass
