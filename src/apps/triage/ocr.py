"""OCR for scanned PDFs and images: local engine, own Celery queue, flag and monthly budget.

Nothing here runs unless ``TRIAGE_OCR_ENABLED`` is on (default off, it costs worker time),
the office switched ``TriagePolicy.ocr_enabled`` on, an engine is configured and the office
still has pages left this month. The only engine is a local Tesseract binary called with a
fixed argument list (no shell, no user-controlled argument). No external service is called.
"""

from __future__ import annotations

import io
import subprocess
import tempfile
from pathlib import Path
from typing import Protocol

from django.conf import settings
from django.db.models import Sum
from django.utils import timezone

from apps.organizations.models import Organization
from apps.triage.intake_policy import policy_for
from apps.triage.models import TriageOcrUsage

OCR_QUEUE = "triage_ocr"
MAX_OCR_TEXT = 64 * 1024
MAX_RENDER_PIXELS = 20_000_000
STALE_QUEUED_MINUTES = 30


class OcrEngine(Protocol):
    def read(self, image_png: bytes) -> str: ...


class OcrFailed(RuntimeError):
    pass


class TesseractEngine:
    def __init__(self, command: str, timeout: int) -> None:
        self.command = command
        self.timeout = timeout

    def read(self, image_png: bytes) -> str:
        with tempfile.TemporaryDirectory(prefix="cica-ocr-") as folder:
            source = Path(folder) / "page.png"
            source.write_bytes(image_png)
            try:
                result = subprocess.run(  # noqa: S603 - fixed argv, configured binary
                    [self.command, str(source), "stdout", "-l", "por"],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                    check=False,
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise OcrFailed("O OCR local não respondeu.") from exc
        if result.returncode:
            raise OcrFailed("O OCR local não conseguiu ler este arquivo.")
        return result.stdout


def get_engine() -> OcrEngine | None:
    command = str(getattr(settings, "TRIAGE_TESSERACT_CMD", "") or "").strip()
    if not command:
        return None
    return TesseractEngine(command, int(getattr(settings, "TRIAGE_OCR_TIMEOUT", 120)))


def max_pages() -> int:
    return max(1, int(getattr(settings, "TRIAGE_OCR_MAX_PAGES", 10)))


def pages_used_this_month(organization: Organization) -> int:
    start = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    total = TriageOcrUsage.objects.filter(
        organization=organization, created_at__gte=start
    ).aggregate(total=Sum("pages"))["total"]
    return int(total or 0)


def ocr_blocker(organization: Organization, pages: int) -> str:
    """Why OCR may not run now ("" when it may)."""

    if not getattr(settings, "TRIAGE_OCR_ENABLED", False):
        return "OCR desligado na plataforma."
    policy = policy_for(organization)
    if not policy.ocr_enabled:
        return "OCR desligado neste escritório."
    if get_engine() is None:
        return "Motor de OCR indisponível."
    if pages_used_this_month(organization) + pages > policy.ocr_monthly_pages:
        return "Orçamento mensal de OCR esgotado."
    return ""


def scale_for(width: float, height: float, base: float = 1.5) -> float:
    """A render scale that never exceeds ``MAX_RENDER_PIXELS`` (a huge page is a bomb)."""

    pixels = max(width * height, 1.0) * base * base
    if pixels <= MAX_RENDER_PIXELS:
        return base
    return float(base * (MAX_RENDER_PIXELS / pixels) ** 0.5)


def render_pdf_pages(data: bytes, limit: int) -> list[bytes]:
    import pypdfium2 as pdfium  # type: ignore[import-untyped]

    try:
        document = pdfium.PdfDocument(data)
    except Exception as exc:
        raise OcrFailed("Não foi possível abrir o PDF para OCR.") from exc
    pages: list[bytes] = []
    try:
        for index in range(min(len(document), limit)):
            page = document[index]
            width, height = page.get_size()
            bitmap = page.render(scale=scale_for(width, height))
            output = io.BytesIO()
            bitmap.to_pil().save(output, format="PNG")
            pages.append(output.getvalue())
    finally:
        document.close()
    return pages


def image_as_png(data: bytes) -> bytes:
    from PIL import Image

    with Image.open(io.BytesIO(data)) as image:
        width, height = image.size
        if width * height > 80_000_000:
            raise OcrFailed("Imagem grande demais para OCR.")
        output = io.BytesIO()
        image.convert("RGB").save(output, format="PNG")
    return output.getvalue()


def pdf_pages_for_ocr(data: bytes) -> int:
    """Pages OCR would read, counted by the same engine that renders them (0 = refuse)."""

    import pypdfium2 as pdfium

    try:
        document = pdfium.PdfDocument(data)
    except Exception:
        return 0
    try:
        return int(min(len(document), max_pages()))
    finally:
        document.close()


def run_ocr(data: bytes, suffix: str, engine: OcrEngine, limit: int) -> tuple[str, int]:
    """(text, pages read); never more pages than the ``limit`` the budget approved."""

    images = [image_as_png(data)] if suffix != ".pdf" else render_pdf_pages(data, limit)
    text = "\n\n".join(engine.read(image) for image in images)
    return text.replace("\x00", "")[:MAX_OCR_TEXT], len(images)
