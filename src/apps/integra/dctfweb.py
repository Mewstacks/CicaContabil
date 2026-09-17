"""Validated DCTFWeb request and document handling.

The Serpro contract identifies a monthly general declaration with category,
year and month. A successful HTTP response is not evidence of an issued DARF
unless its escaped ``dados`` object contains a valid PDF payload.
"""

from __future__ import annotations

import base64
import binascii
import json
import re
from typing import Any

from apps.integra.errors import IntegraTransportError

MAX_DCTFWEB_PDF_BYTES = 8_000_000
_COMPETENCE_RE = re.compile(r"^(0[1-9]|1[0-2])/(\d{4})$")


def monthly_request_data(competence: str, *, category: str = "GERAL_MENSAL") -> dict[str, str]:
    """Build the documented request for a monthly declaration."""

    match = _COMPETENCE_RE.fullmatch(competence.strip())
    if match is None:
        raise ValueError("Competência DCTFWeb inválida; use MM/AAAA.")
    month, year = match.groups()
    return {"categoria": category, "anoPA": year, "mesPA": month}


def response_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Decode Serpro's escaped response object without accepting other shapes."""

    raw = payload.get("dados")
    if isinstance(raw, dict):
        return raw
    if not isinstance(raw, str):
        raise IntegraTransportError("O Serpro não devolveu o objeto de resultado DCTFWeb.")
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise IntegraTransportError(
            "O resultado DCTFWeb devolvido pelo Serpro é ilegível."
        ) from exc
    if not isinstance(decoded, dict):
        raise IntegraTransportError("O Serpro devolveu um resultado DCTFWeb inesperado.")
    return decoded


def extract_pdf(payload: dict[str, Any]) -> bytes:
    """Return a bounded PDF only after validating base64 and its file signature."""

    encoded = response_data(payload).get("PDFByteArrayBase64")
    if not isinstance(encoded, str) or not encoded:
        raise IntegraTransportError("O Serpro respondeu sem o PDF esperado.")
    try:
        document = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise IntegraTransportError("O PDF devolvido pelo Serpro está corrompido.") from exc
    if not document.startswith(b"%PDF-"):
        raise IntegraTransportError("O documento devolvido pelo Serpro não é um PDF.")
    if len(document) > MAX_DCTFWEB_PDF_BYTES:
        raise IntegraTransportError("O PDF devolvido pelo Serpro excede o limite permitido.")
    return document
