from __future__ import annotations

import ipaddress

from django.conf import settings
from django.http import HttpRequest


def client_ip(request: HttpRequest) -> str | None:
    """Return a validated edge client IP without trusting generic forwarded headers."""

    fly_client_ip = request.headers.get("Fly-Client-IP") if settings.FLY_APP_NAME else None
    candidates = (fly_client_ip, request.META.get("REMOTE_ADDR"))
    for candidate in candidates:
        if not candidate:
            continue
        try:
            return str(ipaddress.ip_address(candidate))
        except ValueError:
            continue
    return None
