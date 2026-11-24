"""AC-11.3: leitura sem executar conteúdo; OCR em fila própria, atrás de flag e orçamento."""

from __future__ import annotations

import io
from typing import Any
from unittest.mock import patch

from django.test import override_settings
from openpyxl import Workbook
from reportlab.pdfgen import canvas

from apps.triage import ocr
from apps.triage.extraction import extract_item
from apps.triage.models import TriageItem, TriageOcrUsage, TriagePolicy
from apps.triage.readers import needs_ocr, read_text
from apps.triage.tasks import ocr_triage_item
from apps.triage.transitions import TriageStatus
from triage_v2_support import PNG, TriageV2Case, alnum_cnpj


def blank_pdf(pages: int = 1) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    for _ in range(pages):
        pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def text_pdf(text: str) -> bytes:
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer)
    pdf.drawString(72, 720, text)
    pdf.save()
    return buffer.getvalue()


class ReaderTests(TriageV2Case):
    def test_html_is_reduced_to_visible_text_without_scripts_or_styles(self) -> None:
        html = (
            b"<html><head><style>x{}</style></head><body><script>alert(1)</script>"
            b"<p>Ola <b>CNPJ 1</b></p></body></html>"
        )
        text = read_text(html, ".html")
        self.assertIn("Ola CNPJ 1", text)
        self.assertNotIn("alert", text)

    def test_txt_csv_ofx_decode_utf8_and_latin1(self) -> None:
        self.assertIn("Conciliação", read_text("Conciliação".encode(), ".txt"))
        self.assertIn("Conciliação", read_text("Conciliação".encode("latin-1"), ".csv"))
        self.assertIn("BANKID", read_text(b"<OFX><BANKID>001</BANKID></OFX>", ".ofx"))

    def test_xlsx_cells_are_read_but_formulas_are_not_evaluated(self) -> None:
        book = Workbook()
        sheet = book.active
        sheet.append(["Empresa", "Competência 09/2026"])
        sheet.append(["=1+1", "=HYPERLINK(\"http://x\",\"y\")"])
        buffer = io.BytesIO()
        book.save(buffer)
        text = read_text(buffer.getvalue(), ".xlsx")
        self.assertIn("Competência 09/2026", text)
        self.assertNotIn("http://x", text)

    def test_xls_and_images_have_no_readable_text_here(self) -> None:
        self.assertEqual(read_text(b"xx", ".xls"), "")
        self.assertEqual(read_text(PNG, ".png"), "")

    def test_text_below_the_threshold_asks_for_ocr(self) -> None:
        self.assertTrue(needs_ocr(".pdf", "x" * 79))
        self.assertFalse(needs_ocr(".pdf", "x" * 80))
        self.assertTrue(needs_ocr(".png", ""))
        self.assertFalse(needs_ocr(".csv", ""))

    def test_pdf_with_a_text_layer_never_goes_to_ocr(self) -> None:
        body = "Extrato bancario competencia 09/2026 conta corrente saldo anterior " * 2
        item = self.released(filename="e.pdf", payload=text_pdf(body))
        extract_item(item_id=item.pk)
        item.refresh_from_db()
        self.assertEqual(item.ocr_state, "")
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)


class FakeEngine:
    def __init__(self, text: str = "", fail: bool = False) -> None:
        self.text = text
        self.fail = fail
        self.calls = 0

    def read(self, image_png: bytes) -> str:
        self.calls += 1
        if self.fail:
            raise ocr.OcrFailed("boom")
        return self.text


class OcrCase(TriageV2Case):
    def enable(self, **policy: Any) -> None:
        TriagePolicy.objects.update_or_create(
            organization=self.office, defaults={"ocr_enabled": True, **policy}
        )

    def scanned(self, name: str = "scan.pdf", pages: int = 1) -> TriageItem:
        return self.released(filename=name, payload=blank_pdf(pages) + name.encode())

    def run_extract(self, item: TriageItem, engine: FakeEngine | None) -> TriageItem:
        with (
            override_settings(TRIAGE_OCR_ENABLED=True),
            patch("apps.triage.ocr.get_engine", return_value=engine),
            patch.object(ocr_triage_item, "apply_async") as queued,
            self.captureOnCommitCallbacks(execute=True),
        ):
            extract_item(item_id=item.pk)
        self.queued = queued
        return TriageItem.objects.get(pk=item.pk)


class OcrGateTests(OcrCase):
    def test_everything_off_by_default_item_goes_to_review_without_ocr(self) -> None:
        item = self.scanned()
        extract_item(item_id=item.pk)
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(item.ocr_state, "skipped")
        self.assertTrue(item.events.filter(note__contains="OCR desligado na plataforma").exists())
        self.assertFalse(TriageOcrUsage.objects.exists())

    def test_platform_flag_alone_is_not_enough(self) -> None:
        item = self.run_extract(self.scanned(), FakeEngine("x"))
        self.assertEqual(item.ocr_state, "skipped")
        self.assertTrue(item.events.filter(note__contains="neste escritório").exists())

    def test_no_engine_configured_skips_with_a_reason(self) -> None:
        self.enable()
        item = self.run_extract(self.scanned(), None)
        self.assertEqual(item.ocr_state, "skipped")
        self.assertEqual(item.status, TriageStatus.AWAITING_REVIEW)
        self.assertTrue(item.events.filter(note__contains="indisponível").exists())

    def test_allowed_item_waits_on_the_dedicated_queue(self) -> None:
        self.enable()
        item = self.run_extract(self.scanned(), FakeEngine("x"))
        self.assertEqual(item.ocr_state, "queued")
        self.assertEqual(item.status, TriageStatus.AWAITING_EXTRACTION)
        self.queued.assert_called_once()
        self.assertEqual(self.queued.call_args.kwargs["queue"], "triage_ocr")

    def test_a_queued_item_is_not_extracted_again_until_the_ocr_answers(self) -> None:
        self.enable()
        item = self.run_extract(self.scanned(), FakeEngine("x"))
        again = extract_item(item_id=item.pk)
        self.assertEqual(again.status, TriageStatus.AWAITING_EXTRACTION)
        self.assertEqual(again.ocr_state, "queued")

    def test_budget_exhausted_skips(self) -> None:
        self.enable(ocr_monthly_pages=1)
        first = self.scanned("a.pdf")
        TriageOcrUsage.objects.create(organization=self.office, triage_item=first, pages=1)
        item = self.run_extract(self.scanned("b.pdf"), FakeEngine("x"))
        self.assertEqual(item.ocr_state, "skipped")
        self.assertTrue(item.events.filter(note__contains="Orçamento").exists())

    def test_page_count_is_what_the_budget_sees(self) -> None:
        self.enable(ocr_monthly_pages=2)
        item = self.run_extract(self.scanned("c.pdf", pages=3), FakeEngine("x"))
        self.assertEqual(item.ocr_state, "skipped")

    def test_another_offices_usage_never_spends_this_budget(self) -> None:
        other = self.make_office("e11-ocr-other")
        self.enable(ocr_monthly_pages=1)
        stray = self.released(
            filename="z.pdf", payload=blank_pdf() + b"z", mailbox=self.make_mailbox(other)
        )
        TriageOcrUsage.objects.create(organization=other, triage_item=stray, pages=999)
        item = self.run_extract(self.scanned("d.pdf"), FakeEngine("x"))
        self.assertEqual(item.ocr_state, "queued")

    def test_policy_of_another_office_does_not_enable_this_one(self) -> None:
        other = self.make_office("e11-ocr-other2")
        TriagePolicy.objects.create(organization=other, ocr_enabled=True)
        item = self.run_extract(self.scanned(), FakeEngine("x"))
        self.assertEqual(item.ocr_state, "skipped")


@override_settings(TRIAGE_OCR_ENABLED=True)
class OcrRunTests(OcrCase):
    def test_ocr_text_finds_the_company_and_the_item_reaches_review(self) -> None:
        self.enable()
        read = "CNPJ 12.345.678/0001-95 competencia 09/2026"
        item = self.run_extract(self.scanned(), FakeEngine(read))
        with (
            override_settings(TRIAGE_OCR_ENABLED=True),
            patch("apps.triage.ocr.get_engine", return_value=FakeEngine(read)),
        ):
            status = ocr_triage_item(str(item.pk))
        item.refresh_from_db()
        self.assertEqual(status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(item.ocr_state, "done")
        self.assertEqual(item.company, self.company)
        self.assertEqual(item.period_label, "2026-09")
        self.assertEqual(TriageOcrUsage.objects.get().pages, 1)
        self.assertEqual(TriageOcrUsage.objects.get().organization_id, self.office.id)

    def test_alphanumeric_cnpj_in_ocr_text_is_recognised(self) -> None:
        from apps.hub.models import ClientCompany
        from triage_v2_support import mask_cnpj

        letters = alnum_cnpj("12ABC34501DE")
        company = ClientCompany.objects.create(
            organization=self.office, name="Letra", cnpj_masked=mask_cnpj(letters), dominio_code="9"
        )
        self.enable()
        item = self.run_extract(self.scanned("l.pdf"), FakeEngine("x"))
        with patch("apps.triage.ocr.get_engine", return_value=FakeEngine(f"CNPJ {letters}")):
            ocr_triage_item(str(item.pk))
        item.refresh_from_db()
        self.assertEqual(item.company, company)

    def test_engine_failure_never_strands_the_item(self) -> None:
        self.enable()
        item = self.run_extract(self.scanned(), FakeEngine("x"))
        with patch("apps.triage.ocr.get_engine", return_value=FakeEngine(fail=True)):
            status = ocr_triage_item(str(item.pk))
        item.refresh_from_db()
        self.assertEqual(status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(item.ocr_state, "failed")
        self.assertFalse(TriageOcrUsage.objects.exists())

    def test_task_is_idempotent_and_ignores_items_not_queued(self) -> None:
        self.enable()
        item = self.run_extract(self.scanned(), FakeEngine("x"))
        with patch("apps.triage.ocr.get_engine", return_value=FakeEngine("texto")):
            ocr_triage_item(str(item.pk))
            self.assertEqual(ocr_triage_item(str(item.pk)), "skipped")
        self.assertEqual(TriageOcrUsage.objects.count(), 1)

    def test_image_goes_through_ocr_when_allowed(self) -> None:
        self.enable()
        TriagePolicy.objects.filter(organization=self.office).update(extended_formats=True)
        item = self.released(filename="foto.png", payload=PNG)
        item = self.run_extract(item, FakeEngine("x"))
        self.assertEqual(item.ocr_state, "queued")
        with patch("apps.triage.ocr.get_engine", return_value=FakeEngine("texto lido")):
            ocr_triage_item(str(item.pk))
        item.refresh_from_db()
        self.assertEqual(item.ocr_text, "texto lido")

    def test_ocr_text_is_bounded(self) -> None:
        self.enable()
        item = self.run_extract(self.scanned(), FakeEngine("x"))
        with patch("apps.triage.ocr.get_engine", return_value=FakeEngine("a" * 200_000)):
            ocr_triage_item(str(item.pk))
        item.refresh_from_db()
        self.assertLessEqual(len(item.ocr_text), ocr.MAX_OCR_TEXT)

    def test_huge_pages_are_rendered_at_a_bounded_scale(self) -> None:
        self.assertEqual(ocr.scale_for(595, 842), 1.5)
        scale = ocr.scale_for(200_000, 200_000)
        self.assertLessEqual(200_000 * 200_000 * scale * scale, ocr.MAX_RENDER_PIXELS * 1.01)

    def test_stale_queue_entry_stops_blocking_the_item(self) -> None:
        from datetime import timedelta

        from django.utils import timezone

        self.enable()
        item = self.run_extract(self.scanned(), FakeEngine("x"))
        TriageItem.objects.filter(pk=item.pk).update(
            updated_at=timezone.now() - timedelta(hours=2)
        )
        again = extract_item(item_id=item.pk)
        self.assertEqual(again.status, TriageStatus.AWAITING_REVIEW)
        self.assertEqual(again.ocr_state, "failed")


class OcrReservationTests(OcrCase):
    def test_pages_are_reserved_when_queued_so_two_items_cannot_overspend(self) -> None:
        self.enable(ocr_monthly_pages=1)
        first = self.run_extract(self.scanned("r1.pdf"), FakeEngine("x"))
        second = self.run_extract(self.scanned("r2.pdf"), FakeEngine("x"))
        self.assertEqual(first.ocr_state, "queued")
        self.assertEqual(second.ocr_state, "skipped")
        self.assertEqual(TriageOcrUsage.objects.get().pages, 1)

    def test_failure_gives_the_reserved_pages_back(self) -> None:
        self.enable(ocr_monthly_pages=1)
        item = self.run_extract(self.scanned("r3.pdf"), FakeEngine("x"))
        with (
            override_settings(TRIAGE_OCR_ENABLED=True),
            patch("apps.triage.ocr.get_engine", return_value=FakeEngine(fail=True)),
        ):
            ocr_triage_item(str(item.pk))
        self.assertFalse(TriageOcrUsage.objects.exists())

    def test_task_never_reads_more_pages_than_were_reserved(self) -> None:
        self.enable()
        item = self.run_extract(self.scanned("r4.pdf", pages=3), FakeEngine("x"))
        TriageOcrUsage.objects.filter(triage_item=item).update(pages=1)
        engine = FakeEngine("texto")
        with (
            override_settings(TRIAGE_OCR_ENABLED=True),
            patch("apps.triage.ocr.get_engine", return_value=engine),
        ):
            ocr_triage_item(str(item.pk))
        self.assertEqual(engine.calls, 1)

    def test_switches_turned_off_while_queued_stop_the_run(self) -> None:
        self.enable()
        item = self.run_extract(self.scanned("r5.pdf"), FakeEngine("x"))
        TriagePolicy.objects.filter(organization=self.office).update(ocr_enabled=False)
        engine = FakeEngine("texto")
        with (
            override_settings(TRIAGE_OCR_ENABLED=True),
            patch("apps.triage.ocr.get_engine", return_value=engine),
        ):
            ocr_triage_item(str(item.pk))
        self.assertEqual(engine.calls, 0)
        self.assertFalse(TriageOcrUsage.objects.exists())


class XlsxBoundTests(TriageV2Case):
    def test_expansion_bomb_is_not_parsed(self) -> None:
        import zipfile

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as package:
            package.writestr("[Content_Types].xml", "<a/>")
            package.writestr("xl/sharedStrings.xml", "0" * (8 * 1024 * 1024))
        with patch("openpyxl.load_workbook", side_effect=AssertionError("parsed")):
            self.assertEqual(read_text(buffer.getvalue(), ".xlsx"), "")

    def test_wide_rows_and_long_cells_are_capped(self) -> None:
        book = Workbook()
        sheet = book.active
        sheet.append(["x" * 5000] + ["c"] * 80)
        buffer = io.BytesIO()
        book.save(buffer)
        text = read_text(buffer.getvalue(), ".xlsx")
        self.assertLess(len(text), 1200)
