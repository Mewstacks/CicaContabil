"""Formatos extras (imagem, texto, xls) validados sem executar nada."""

from __future__ import annotations

import io

import pytest

from apps.triage.file_policy import UnsupportedAttachment, validate_supported_attachment
from triage_v2_support import PNG

ALL = frozenset({".png", ".jpg", ".txt", ".html", ".xls", ".pdf"})
OLE = bytes.fromhex("D0CF11E0A1B11AE1")


def check(name: str, data: bytes, allowed: frozenset[str] = ALL) -> str:
    return validate_supported_attachment(io.BytesIO(data), filename=name, allowed=allowed)


def test_valid_png_txt_html_and_xls_are_accepted() -> None:
    assert check("a.png", PNG) == "image/png"
    assert check("a.txt", b"texto simples") == "text/plain"
    assert check("a.html", b"<p>oi</p>") == "text/html"
    assert check("a.xls", OLE + "Workbook".encode("utf-16-le")) == "application/vnd.ms-excel"


@pytest.mark.parametrize(
    ("name", "data"),
    [
        ("a.png", b"not an image"),
        ("a.jpg", PNG),  # extension does not match the content
        ("a.txt", b"abc" + bytes([0]) + b"def"),
        ("a.html", bytes([0]) + b"<p>"),
        ("a.xls", b"nao e ole"),
        ("a.xls", OLE + "Workbook".encode("utf-16-le") + "_VBA_PROJECT".encode("utf-16-le")),
        ("a.xls", OLE + "Macros".encode("utf-16-le") + "Workbook".encode("utf-16-le")),
        ("a.xls", OLE + b"sem planilha"),
    ],
)
def test_bad_content_is_refused(name: str, data: bytes) -> None:
    with pytest.raises(UnsupportedAttachment):
        check(name, data)


def test_suffix_outside_the_office_set_is_refused() -> None:
    with pytest.raises(UnsupportedAttachment):
        check("a.png", PNG, allowed=frozenset({".pdf"}))
