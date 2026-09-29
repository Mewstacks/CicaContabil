"""Bounded internal client for the local JavaScript report renderer."""

from __future__ import annotations

import hashlib
import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from django.conf import settings


class ReportingServiceUnavailable(RuntimeError):
    """The explicitly configured internal renderer did not produce a safe result."""


EXPECTED_CONTENT_TYPES = {
    "pdf": "application/pdf",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def configured_renderer_url() -> str | None:
    value = str(getattr(settings, "CICA_REPORTING_URL", "") or "").strip().rstrip("/")
    return value or None


def render_snapshot(*, snapshot: dict[str, Any], export_format: str) -> bytes:
    """Render through the explicitly configured internal JavaScript service only."""

    url = configured_renderer_url()
    if url is None:
        raise ReportingServiceUnavailable(
            "O serviÃ§o interno de relatÃ³rios nÃ£o estÃ¡ configurado."
        )
    shared_secret = str(getattr(settings, "CICA_REPORTING_SHARED_SECRET", "") or "").strip()
    if not shared_secret:
        raise ReportingServiceUnavailable(
            "A autenticação do serviço interno de relatórios não está configurada."
        )
    parsed = urlsplit(url)
    if (
        parsed.scheme not in {"http", "https"}
        or not parsed.netloc
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ReportingServiceUnavailable("A URL do serviço interno de relatórios é inválida.")
    content_type = EXPECTED_CONTENT_TYPES.get(export_format)
    if content_type is None:
        raise ValueError("Formato de relatório inválido.")
    body = json.dumps(
        {"format": export_format, "snapshot": snapshot},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    request = Request(  # noqa: S310 - scheme and credentials are validated above
        f"{url}/v1/render",
        data=body,
        headers={
            "Content-Type": "application/json",
            "Accept": content_type,
            "X-CICA-Reporting-Secret": shared_secret,
        },
        method="POST",
    )
    timeout = float(getattr(settings, "CICA_REPORTING_TIMEOUT_SECONDS", 30))
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310 - configured internal URL
            result = response.read()
            received_type = response.headers.get_content_type()
            received_hash = response.headers.get("X-CICA-Report-Hash", "")
    except (HTTPError, URLError, TimeoutError, OSError) as error:
        raise ReportingServiceUnavailable(
            "O serviço interno de relatórios não respondeu."
        ) from error
    if received_type != content_type or not result:
        raise ReportingServiceUnavailable("O serviço interno devolveu um relatório inválido.")
    expected_hash = hashlib.sha256(result).hexdigest()
    if received_hash != expected_hash:
        raise ReportingServiceUnavailable("O hash do relatório interno não confere.")
    return bytes(result)
