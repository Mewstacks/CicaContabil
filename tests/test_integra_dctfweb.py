from __future__ import annotations

import base64
import json

import pytest

from apps.integra.dctfweb import extract_pdf, monthly_request_data
from apps.integra.errors import IntegraTransportError


def test_monthly_request_uses_the_documented_serpro_fields() -> None:
    assert monthly_request_data("09/2026") == {
        "categoria": "GERAL_MENSAL",
        "anoPA": "2026",
        "mesPA": "09",
    }


@pytest.mark.parametrize("value", ["2026-09", "13/2026", "9/2026", ""])
def test_monthly_request_rejects_ambiguous_competence(value: str) -> None:
    with pytest.raises(ValueError, match="MM/AAAA"):
        monthly_request_data(value)


def test_extract_pdf_accepts_the_escaped_serpro_result() -> None:
    document = b"%PDF-1.7\nexample"
    payload = {
        "dados": json.dumps({"PDFByteArrayBase64": base64.b64encode(document).decode()})
    }
    assert extract_pdf(payload) == document


@pytest.mark.parametrize(
    "dados",
    [
        "{}",
        json.dumps({"PDFByteArrayBase64": "not base64"}),
        json.dumps({"PDFByteArrayBase64": base64.b64encode(b"not a pdf").decode()}),
    ],
)
def test_extract_pdf_refuses_missing_corrupt_or_non_pdf_documents(dados: str) -> None:
    with pytest.raises(IntegraTransportError):
        extract_pdf({"dados": dados})
