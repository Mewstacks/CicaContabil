from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

import pytest

from apps.triage.file_policy import UnsupportedAttachment, validate_supported_attachment


def _xlsx(*, extra: str = "") -> bytes:
    output = BytesIO()
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("xl/workbook.xml", "<workbook/>")
        if extra:
            package.writestr(extra, "payload")
    return output.getvalue()


@pytest.mark.parametrize(
    ("filename", "payload", "detected"),
    [
        ("doc.pdf", b"%PDF-1.4\n%%EOF", "application/pdf"),
        ("doc.xml", b"<root><a/></root>", "application/xml"),
        ("doc.csv", b"a,b\n1,2\n", "text/csv"),
        ("doc.ofx", b"OFXHEADER:100\n<OFX>", "application/x-ofx"),
        (
            "doc.xlsx", _xlsx(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        ),
    ],
)
def test_supported_formats(filename: str, payload: bytes, detected: str) -> None:
    assert validate_supported_attachment(BytesIO(payload), filename=filename) == detected


@pytest.mark.parametrize(
    ("filename", "payload"),
    [
        ("doc.pdf", b"not a pdf"),
        ("doc.xml", b"<!DOCTYPE foo [<!ENTITY x SYSTEM 'file:///etc/passwd'>]><foo>&x;</foo>"),
        ("doc.csv", b"a,b\x00\n"),
        ("doc.ofx", b"random binary"),
        ("doc.xlsx", _xlsx(extra="xl/vbaProject.bin")),
        ("doc.xlsx", _xlsx(extra="xl/externalLinks/externalLink1.xml")),
        ("doc.exe", b"MZ"),
    ],
)
def test_mismatch_and_active_parts_are_rejected(filename: str, payload: bytes) -> None:
    with pytest.raises(UnsupportedAttachment):
        validate_supported_attachment(BytesIO(payload), filename=filename)
