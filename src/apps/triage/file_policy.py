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


class UnsupportedAttachment(ValueError):
    pass


_MAX_BYTES = 25 * 1024 * 1024
_MAX_XLSX_UNCOMPRESSED = 100 * 1024 * 1024
_MAX_XLSX_PARTS = 500
_MIME = {
    ".pdf": "application/pdf",
    ".xml": "application/xml",
    ".csv": "text/csv",
    ".ofx": "application/x-ofx",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def validate_supported_attachment(stream: BinaryIO, *, filename: str) -> str:
    """Return detected type or reject mismatch, active XLSX parts and oversized ZIPs."""
    suffix = PurePath(filename.replace("\\", "/")).suffix.casefold()
    if suffix not in _MIME:
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
