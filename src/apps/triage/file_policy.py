"""Bounded format checks for email attachments before leaving quarantine.

These checks establish a supported document format, not that content is harmless.
The independent antimalware result must also be clean for the exact content hash.
"""

from __future__ import annotations

import io
import zipfile
from pathlib import PurePath
from typing import BinaryIO

from defusedxml import ElementTree  # type: ignore[import-untyped]  # Package has no type stubs.
from PIL import Image, UnidentifiedImageError

from apps.triage.archives import ArchiveRejected, inspect_zip


class UnsupportedAttachment(ValueError):
    pass


_MAX_BYTES = 25 * 1024 * 1024
_MAX_XLSX_UNCOMPRESSED = 100 * 1024 * 1024
_MAX_XLSX_PARTS = 500
_MAX_IMAGE_PIXELS = 80_000_000
_BASE = frozenset({".pdf", ".xml", ".csv", ".ofx", ".xlsx"})
_MIME = {
    ".pdf": "application/pdf",
    ".xml": "application/xml",
    ".csv": "text/csv",
    ".ofx": "application/x-ofx",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
    ".html": "text/html",
    ".htm": "text/html",
    ".txt": "text/plain",
    ".xls": "application/vnd.ms-excel",
    ".zip": "application/zip",
}


def validate_supported_attachment(
    stream: BinaryIO, *, filename: str, allowed: frozenset[str] | None = None
) -> str:
    """Return detected type or reject mismatch, active XLSX parts and oversized ZIPs.

    ``allowed`` is the office's accepted suffix set (base formats when omitted).
    """
    suffix = PurePath(filename.replace("\\", "/")).suffix.casefold()
    if suffix not in _MIME or suffix not in (allowed if allowed is not None else _BASE):
        raise UnsupportedAttachment("Tipo de arquivo fora dos formatos aceitos.")
    stream.seek(0)
    data = stream.read(_MAX_BYTES + 1)
    if not data or len(data) > _MAX_BYTES:
        raise UnsupportedAttachment("Arquivo vazio ou maior que 25 MB.")
    if suffix == ".pdf":
        if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
            raise UnsupportedAttachment("PDF sem estrutura inicial e final válida.")
    elif suffix == ".xml":
        try:
            ElementTree.fromstring(data)
        except (ElementTree.ParseError, ValueError) as exc:
            raise UnsupportedAttachment("XML inválido ou com conteúdo externo.") from exc
    elif suffix == ".ofx":
        header = data[:1024].lstrip(b"\xef\xbb\xbf\r\n\t ").upper()
        if not (header.startswith(b"OFXHEADER:") or header.startswith(b"<?XML")
                or header.startswith(b"<OFX")):
            raise UnsupportedAttachment("OFX sem cabeçalho reconhecível.")
        if b"\x00" in data:
            raise UnsupportedAttachment("OFX contém dados binários inesperados.")
    elif suffix == ".csv":
        if b"\x00" in data or (b"\n" not in data and b"\r" not in data):
            raise UnsupportedAttachment("CSV sem linhas de texto válidas.")
    elif suffix in {".html", ".htm", ".txt"}:
        if b"\x00" in data:
            raise UnsupportedAttachment("Arquivo de texto contém dados binários.")
    elif suffix == ".xls":
        _check_xls(data)
    elif suffix in {".jpg", ".jpeg", ".png", ".webp"}:
        _check_image(data, suffix)
    elif suffix == ".zip":
        try:
            inspect_zip(data, allowed_suffixes=allowed if allowed is not None else _BASE)
        except ArchiveRejected as exc:
            raise UnsupportedAttachment(str(exc)[:200]) from exc
    else:
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as package:
                parts = package.infolist()
                names = {part.filename for part in parts}
                if len(parts) > _MAX_XLSX_PARTS or sum(
                    part.file_size for part in parts
                ) > _MAX_XLSX_UNCOMPRESSED:
                    raise UnsupportedAttachment("Planilha excede o limite de partes ou expansão.")
                if not {"[Content_Types].xml", "xl/workbook.xml"} <= names:
                    raise UnsupportedAttachment("Pacote XLSX sem pasta de trabalho válida.")
                if any(
                    part.filename.startswith("/")
                    or ".." in part.filename.split("/")
                    or part.filename.casefold().startswith((
                        "xl/externallinks/", "xl/embeddings/"
                    ))
                    or "vbaproject" in part.filename.casefold()
                    for part in parts
                ):
                    raise UnsupportedAttachment("Planilha contém partes externas ou executáveis.")
                if package.testzip() is not None:
                    raise UnsupportedAttachment("Planilha XLSX tem partes corrompidas.")
        except (zipfile.BadZipFile, OSError, RuntimeError) as exc:
            raise UnsupportedAttachment("Pacote XLSX inválido.") from exc
    return _MIME[suffix]


def _check_image(data: bytes, suffix: str) -> None:
    expected = {".jpg": "JPEG", ".jpeg": "JPEG", ".png": "PNG", ".webp": "WEBP"}[suffix]
    try:
        with Image.open(io.BytesIO(data)) as image:
            width, height = image.size
            if width * height > _MAX_IMAGE_PIXELS:
                raise UnsupportedAttachment("Imagem grande demais.")
            image.verify()
            if image.format != expected:
                raise UnsupportedAttachment("A extensão não corresponde ao conteúdo da imagem.")
    except UnsupportedAttachment:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError, SyntaxError) as exc:
        raise UnsupportedAttachment("Imagem inválida ou grande demais.") from exc


_OLE_MAGIC = bytes.fromhex("D0CF11E0A1B11AE1")
# OLE directory names are UTF-16LE. The sheet is never opened by the product; these checks
# keep macro and embedded-object carriers out, as the XLSX check does.
_XLS_ACTIVE = tuple(
    name.encode("utf-16-le")
    for name in ("_VBA_PROJECT", "VBA", "Macros", "ObjectPool", "Ole10Native")
)
_XLS_BOOK = tuple(name.encode("utf-16-le") for name in ("Workbook", "Book"))


def _check_xls(data: bytes) -> None:
    if not data.startswith(_OLE_MAGIC):
        raise UnsupportedAttachment("Arquivo .xls não é uma planilha do Excel válida.")
    if any(marker in data for marker in _XLS_ACTIVE):
        raise UnsupportedAttachment("Planilha .xls contém macro ou objeto embutido.")
    if not any(marker in data for marker in _XLS_BOOK):
        raise UnsupportedAttachment("Arquivo .xls sem pasta de trabalho do Excel.")
