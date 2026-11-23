"""Text out of a released file, without executing anything inside it.

PDF text layer (pypdf), spreadsheet cells as cached values (openpyxl ``data_only``, never a
formula result computed here, no macros since ``.xlsm`` is not a format), HTML reduced to its
visible text, plain text, CSV, OFX and XML decoded as text. Legacy ``.xls`` and images carry
no readable text here: images go through OCR when allowed, ``.xls`` is read by name only.
"""

from __future__ import annotations

import io
from pathlib import PurePosixPath

from apps.triage.mailtext import html_to_text

TEXT_LIMIT = 256 * 1024
PDF_PAGES = 3
XLSX_SHEETS = 10
XLSX_ROWS = 500
OCR_TEXT_THRESHOLD = 80  # characters of PDF text below which the page is a scan
IMAGE_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})
_PLAIN = frozenset({".xml", ".csv", ".ofx", ".txt"})


def suffix_of(name: str) -> str:
    return PurePosixPath(name.replace("\\", "/")).suffix.casefold()


def decode_text(data: bytes) -> str:
    head = data[:TEXT_LIMIT]
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            return head.decode(encoding)
        except UnicodeDecodeError:
            continue
    return ""


def pdf_text(data: bytes) -> str:
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data), strict=False)
        parts: list[str] = []
        for page in reader.pages[:PDF_PAGES]:
            parts.append(page.extract_text() or "")
            if sum(len(part) for part in parts) > TEXT_LIMIT:
                break
        return "".join(parts)[:TEXT_LIMIT]
    except Exception:  # a malformed but format-valid PDF still goes to review
        return ""


def pdf_page_count(data: bytes) -> int:
    try:
        from pypdf import PdfReader

        return len(PdfReader(io.BytesIO(data), strict=False).pages)
    except Exception:
        return 0


def xlsx_text(data: bytes) -> str:
    try:
        from openpyxl import load_workbook  # type: ignore[import-untyped]

        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception:
        return ""
    rows: list[str] = []
    try:
        for sheet in workbook.worksheets[:XLSX_SHEETS]:
            rows.append(f"PLANILHA: {sheet.title}")
            for row in sheet.iter_rows(max_row=XLSX_ROWS, values_only=True):
                rows.append(" | ".join(str(value) for value in row if value is not None))
            if sum(len(row) for row in rows) > TEXT_LIMIT:
                break
    except Exception:  # noqa: S110 - a truncated sheet only loses hints
        pass
    finally:
        workbook.close()
    return "\n".join(rows)[:TEXT_LIMIT]


def read_text(data: bytes, suffix: str) -> str:
    """Readable text of one file; "" when the format carries none here."""

    if suffix in _PLAIN:
        return decode_text(data).replace("\x00", "")
    if suffix in {".html", ".htm"}:
        return html_to_text(decode_text(data)).replace("\x00", "")[:TEXT_LIMIT]
    if suffix == ".pdf":
        return pdf_text(data).replace("\x00", "")
    if suffix == ".xlsx":
        return xlsx_text(data).replace("\x00", "")
    return ""


def needs_ocr(suffix: str, text: str) -> bool:
    if suffix in IMAGE_SUFFIXES:
        return True
    return suffix == ".pdf" and len(text.strip()) < OCR_TEXT_THRESHOLD
