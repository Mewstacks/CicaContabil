"""What an attachment is, before a single byte is stored: document, noise or refusal.

Pure decisions over metadata (name, size, inline hints) plus the office's ``TriagePolicy``.
The pollers call it for every attachment so that a logo is dropped, a strange or huge file
becomes a visible *Rejeitado* with a reason, and the mailbox keeps going either way.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Literal

from apps.organizations.models import Organization
from apps.triage.models import TriagePolicy

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024
# A logo is KB; a photographed document pasted in the body is bigger.
INLINE_IMAGE_LIMIT = 100 * 1024

BASE_SUFFIXES = frozenset({".pdf", ".csv", ".xml", ".ofx", ".xlsx"})
EXTENDED_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".html", ".htm", ".txt", ".xls"})
ARCHIVE_SUFFIXES = frozenset({".zip"})

_SIGNATURE_IMAGE = re.compile(r"(?i)(image\d{3}|outlook-[a-z0-9_\-]+)\.(png|jpe?g|gif|bmp)")
_NOISE_NAMES = frozenset({"winmail.dat", "smime.p7s"})
_NOISE_SUFFIXES = (".ics", ".vcf", ".p7s")


@dataclass(frozen=True)
class IntakePolicy:
    extended_formats: bool = False
    open_archives: bool = False
    ocr_enabled: bool = False
    ocr_monthly_pages: int = 100

    @property
    def suffixes(self) -> frozenset[str]:
        found = set(BASE_SUFFIXES)
        if self.extended_formats:
            found |= EXTENDED_SUFFIXES
        if self.open_archives:
            found |= ARCHIVE_SUFFIXES
        return frozenset(found)


def policy_for(organization: Organization) -> IntakePolicy:
    """The office's switches; an office that never set any keeps today's behaviour."""

    row = TriagePolicy.objects.filter(organization=organization).first()
    if row is None:
        return IntakePolicy()
    return IntakePolicy(
        extended_formats=row.extended_formats,
        open_archives=row.open_archives,
        ocr_enabled=row.ocr_enabled,
        ocr_monthly_pages=row.ocr_monthly_pages,
    )


@dataclass(frozen=True)
class IntakeDecision:
    action: Literal["accept", "ignore", "reject"]
    reason: str = ""


def suffix_of(filename: str) -> str:
    return PurePosixPath(filename.replace("\\", "/")).suffix.casefold()


def decide_attachment(
    *,
    organization: Organization,
    filename: str,
    size: int,
    inline: bool = False,
    content_id: bool = False,
    content_type: str = "",
) -> IntakeDecision:
    name = PurePosixPath(filename.replace("\\", "/")).name
    lower = name.casefold()
    if not name or size <= 0:
        return IntakeDecision("ignore")
    if lower in _NOISE_NAMES or lower.endswith(_NOISE_SUFFIXES):
        return IntakeDecision("ignore")
    if _SIGNATURE_IMAGE.fullmatch(name):
        return IntakeDecision("ignore")
    is_image = content_type.casefold().startswith("image/")
    # Only small inline images are logos: an inline PDF is a document some clients mark so.
    if is_image and (inline or content_id) and size < INLINE_IMAGE_LIMIT:
        return IntakeDecision("ignore")
    suffix = suffix_of(name)
    if suffix not in policy_for(organization).suffixes:
        shown = suffix if suffix else "sem extensão"
        return IntakeDecision("reject", f"Formato {shown} não aceito neste escritório.")
    if size > MAX_ATTACHMENT_BYTES:
        return IntakeDecision("reject", "Anexo maior que 25 MB; não foi armazenado.")
    return IntakeDecision("accept")
