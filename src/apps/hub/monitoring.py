from __future__ import annotations

import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.conf import settings

SENSITIVE_TERMS = {"cnpj", "cpf", "xml", "certificate", "password", "secret", "token", "payload"}


def _clean_tags(values: dict[str, object]) -> dict[str, object]:
    return {
        key: value
        for key, value in values.items()
        if not any(term in key.casefold() for term in SENSITIVE_TERMS)
    }


def send_mewpulse_event(
    *, component: str, event: str, tenant_ref: str = "", release: str = ""
) -> bool:
    """Best effort only. Absence or failure of CRMew must never block fiscal work."""
    endpoint = getattr(settings, "MEWPULSE_INGEST_URL", "")
    token = getattr(settings, "MEWPULSE_INGEST_TOKEN", "")
    if not endpoint or not token:
        return False
    body = json.dumps(
        {
            "events": [
                {
                    "event": event,
                    "tags": _clean_tags(
                        {"component": component, "tenant_ref": tenant_ref, "release": release}
                    ),
                }
            ]
        }
    ).encode()
    request = Request(  # noqa: S310 - endpoint is deployment-owned configuration
        endpoint,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=2):  # noqa: S310 - endpoint is deployment-owned configuration
            return True
    except (URLError, TimeoutError):
        return False


def send_mewguard_posture(*, component: str, release: str, dependency_count: int) -> bool:
    """Publish configuration/dependency/runtime posture without client or fiscal payloads."""
    endpoint = getattr(settings, "MEWGUARD_POSTURE_URL", "")
    token = getattr(settings, "MEWPULSE_INGEST_TOKEN", "")
    if not endpoint or not token:
        return False
    body = json.dumps(
        {
            "component": component,
            "release": release,
            "dependencies": {"count": dependency_count},
            "configuration": {"probe_enabled": False},
            "runtime": {"python": "managed"},
        }
    ).encode()
    request = Request(  # noqa: S310 - endpoint is deployment-owned configuration
        endpoint,
        data=body,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=2):  # noqa: S310 - endpoint is deployment-owned configuration
            return True
    except (URLError, TimeoutError):
        return False
