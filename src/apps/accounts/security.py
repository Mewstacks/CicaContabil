from __future__ import annotations

from typing import Any

from django.conf import settings
from django.http import HttpRequest, JsonResponse


def axes_lockout_response(
    request: HttpRequest,
    response: object,
    credentials: dict[str, Any],
    *args: object,
    **kwargs: object,
) -> JsonResponse:
    retry_after = int(settings.AXES_COOLOFF_TIME.total_seconds())
    result = JsonResponse(
        {
            "error": {
                "status": 429,
                "code": "authentication_locked",
                "detail": "Too many authentication attempts. Try again later.",
            }
        },
        status=429,
    )
    result["Retry-After"] = str(retry_after)
    return result
