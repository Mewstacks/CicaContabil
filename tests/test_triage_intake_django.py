"""AC-11.2: ingestão robusta. Logo ignorado, anexo ruim vira Rejeitado e a caixa segue."""

from __future__ import annotations

import json
from datetime import timedelta
from email.message import EmailMessage
from typing import Any
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.triage.imap_poll import poll_imap_mailbox
from apps.triage.ingest import receive_email_attachment, record_rejected_attachment
from apps.triage.intake_policy import decide_attachment
from apps.triage.models import Mailbox, TriageItem, TriagePolicy, TriageSafetyScan
from apps.triage.security import ScanVerdict, scan_quarantined_item
from apps.triage.transitions import TriageStatus
from triage_v2_support import PDF, PNG, FakeIMAP, TriageV2Case


class DecisionTests(TriageV2Case):
    def decide(self, name: str, size: int = 1000, **kw: Any) -> Any:
        return decide_attachment(organization=self.office, filename=name, size=size, **kw)

    def test_base_formats_are_accepted(self) -> None:
        for name in ("a.pdf", "a.CSV", "a.xml", "a.ofx", "a.xlsx"):
            self.assertEqual(self.decide(name).action, "accept", name)

    def test_logo_and_signature_images_are_ignored_not_rejected(self) -> None:
        for name in ("image001.png", "Outlook-abc123.jpg", "winmail.dat", "invite.ics", "c.vcf"):
            self.assertEqual(self.decide(name).action, "ignore", name)
        inline = self.decide("foto.png", 5000, inline=True, content_type="image/png")
        self.assertEqual(inline.action, "ignore")
        cid = self.decide("foto.png", 5000, content_id=True, content_type="image/png")
        self.assertEqual(cid.action, "ignore")

    def test_inline_pdf_is_still_a_document(self) -> None:
        got = self.decide("extrato.pdf", inline=True, content_type="application/pdf")
        self.assertEqual(got.action, "accept")

    def test_big_inline_image_is_a_document_photo(self) -> None:
        got = self.decide("foto.png", 500_000, content_id=True, content_type="image/png")
        self.assertNotEqual(got.action, "ignore")

    def test_unsupported_format_is_rejected_with_a_reason(self) -> None:
        decision = self.decide("setup.exe")
        self.assertEqual(decision.action, "reject")
        self.assertIn(".exe", decision.reason)
        self.assertEqual(self.decide("semextensao").action, "reject")

    def test_too_big_is_rejected_with_a_reason(self) -> None:
        decision = self.decide("big.pdf", 26 * 1024 * 1024)
        self.assertEqual(decision.action, "reject")
        self.assertIn("25 MB", decision.reason)

    def test_empty_attachment_is_ignored(self) -> None:
        self.assertEqual(self.decide("vazio.pdf", 0).action, "ignore")

    def test_extended_formats_and_archives_follow_the_office_policy(self) -> None:
        for name in ("foto.jpg", "pagina.html", "nota.txt", "antiga.xls", "pacote.zip"):
            self.assertEqual(self.decide(name).action, "reject", name)
        TriagePolicy.objects.create(organization=self.office, extended_formats=True)
        for name in ("foto.jpg", "pagina.html", "nota.txt", "antiga.xls"):
            self.assertEqual(self.decide(name).action, "accept", name)
        self.assertEqual(self.decide("pacote.zip").action, "reject")
        TriagePolicy.objects.filter(organization=self.office).update(open_archives=True)
        self.assertEqual(self.decide("pacote.zip").action, "accept")

    def test_policy_of_one_office_never_applies_to_another(self) -> None:
        other = self.make_office("e11-intake-other")
        TriagePolicy.objects.create(organization=other, extended_formats=True, open_archives=True)
        self.assertEqual(self.decide("foto.jpg").action, "reject")
        self.assertEqual(self.decide("pacote.zip").action, "reject")


class RecordTests(TriageV2Case):
    def test_received_attachment_keeps_body_original_sender_and_origin(self) -> None:
        item = receive_email_attachment(
            mailbox=self.mailbox,
            message_id="m1",
            part_id="1",
            filename="a.pdf",
            payload=PDF,
            body_excerpt="Segue o extrato",
            original_sender="cliente@padaria.example",
            received_at=timezone.now(),
        ).item
        item.refresh_from_db()
        self.assertEqual(item.body_excerpt, "Segue o extrato")
        self.assertEqual(item.original_sender, "cliente@padaria.example")
        self.assertEqual(item.origin, TriageItem.Origin.EMAIL)

    def test_rejected_record_has_reason_no_blob_and_is_idempotent(self) -> None:
        args: dict[str, Any] = {
            "mailbox": self.mailbox,
            "message_id": "m2",
            "part_id": "9",
            "filename": "setup.exe",
            "size": 10,
            "reason": "Formato .exe não aceito.",
            "received_at": timezone.now(),
        }
        receipt = record_rejected_attachment(**args)
        item = receipt.item
        self.assertTrue(receipt.created)
        self.assertEqual(item.status, TriageStatus.REJECTED)
        self.assertEqual(item.rejection_reason, "Formato .exe não aceito.")
        self.assertFalse(hasattr(item, "blob"))
        self.assertEqual(item.byte_size, 10)
        again = record_rejected_attachment(**args)
        self.assertFalse(again.created)
        self.assertEqual(TriageItem.objects.count(), 1)

    def test_rejected_record_refuses_an_inactive_mailbox(self) -> None:
        self.mailbox.active = False
        self.mailbox.save()
        with self.assertRaises(ValidationError):
            record_rejected_attachment(
                mailbox=self.mailbox,
                message_id="m3",
                part_id="1",
                filename="x.exe",
                size=1,
                reason="x",
            )


class ScanFormatTests(TriageV2Case):
    def test_unsupported_content_is_rejected_with_the_reason_not_parked(self) -> None:
        item = receive_email_attachment(
            mailbox=self.mailbox,
            message_id="m4",
            part_id="1",
            filename="falso.pdf",
            payload=b"isto nao e pdf",
            received_at=timezone.now(),
        ).item

        class Clean:
            def scan(self, stream: object) -> ScanVerdict:
                return ScanVerdict("clean", "t")

        scan_quarantined_item(item=item, scanner=Clean())
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.REJECTED)
        self.assertIn("PDF", item.rejection_reason)
        self.assertEqual(
            item.safety_scan.format_verdict, TriageSafetyScan.FormatVerdict.INVALID
        )


def _message(
    *, sender: str = "ana@e11-office.test", body: str = "Segue", subject: str = "Docs"
) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["Subject"] = subject
    message.set_content(body)
    return message


def _attach(message: EmailMessage, payload: bytes, name: str) -> None:
    message.add_attachment(
        payload, maintype="application", subtype="octet-stream", filename=name
    )


class ImapIntakeTests(TriageV2Case):
    def setUp(self) -> None:
        super().setUp()
        self.cutoff = timezone.now().replace(microsecond=0) - timedelta(days=1)
        self.stamp = timezone.now().replace(microsecond=0)
        self.mailbox.since = self.cutoff
        self.mailbox.credential = json.dumps(
            {
                "version": 1,
                "provider": "imap",
                "host": "mail.example.test",
                "username": "docs",
                "password": "x",
            }
        )
        self.mailbox.save()

    def poll(self, *raws: bytes) -> Any:
        fake = FakeIMAP(list(raws), self.stamp)
        with patch("apps.triage.imap_poll.public_imap_address", return_value="8.8.8.8"):
            result = poll_imap_mailbox(mailbox=self.mailbox, connection_factory=lambda *_: fake)
        self.mailbox.refresh_from_db()
        return result

    def test_logo_is_ignored_and_the_pdf_is_kept(self) -> None:
        message = _message()
        message.add_alternative("<p>oi</p><img src='cid:logo1'>", subtype="html")
        html_part = message.get_payload()[1]  # type: ignore[index]
        html_part.add_related(PNG, "image", "png", cid="<logo1>", filename="image001.png")
        _attach(message, PDF, "extrato.pdf")
        result = self.poll(message.as_bytes())
        names = list(TriageItem.objects.values_list("original_name", flat=True))
        self.assertEqual(names, ["extrato.pdf"])
        self.assertEqual(result.attachments_created, 1)

    def test_unsupported_attachment_is_rejected_and_the_mailbox_keeps_going(self) -> None:
        message = _message()
        _attach(message, b"MZ\x90", "setup.exe")
        _attach(message, PDF, "extrato.pdf")
        self.poll(message.as_bytes())
        self.assertEqual(self.mailbox.status, Mailbox.Status.ACTIVE)
        self.assertEqual(self.mailbox.last_error, "")
        rejected = TriageItem.objects.get(original_name="setup.exe")
        self.assertEqual(rejected.status, TriageStatus.REJECTED)
        self.assertIn(".exe", rejected.rejection_reason)
        self.assertTrue(TriageItem.objects.filter(original_name="extrato.pdf").exists())

    def test_oversized_attachment_is_rejected_and_the_cursor_advances(self) -> None:
        message = _message()
        _attach(message, PDF * 100, "big.pdf")
        with patch("apps.triage.intake_policy.MAX_ATTACHMENT_BYTES", 500):
            result = self.poll(message.as_bytes())
        self.assertEqual(self.mailbox.status, Mailbox.Status.ACTIVE)
        self.assertEqual(result.last_uid, 1)
        item = TriageItem.objects.get(original_name="big.pdf")
        self.assertEqual(item.status, TriageStatus.REJECTED)
        self.assertIn("25 MB", item.rejection_reason)
        self.assertFalse(hasattr(item, "blob"))

    def test_message_above_the_size_cap_is_rejected_not_a_mailbox_error(self) -> None:
        message = _message()
        _attach(message, PDF, "a.pdf")
        with patch("apps.triage.imap_poll.MAX_IMAP_MESSAGE_BYTES", 100):
            result = self.poll(message.as_bytes())
        self.assertEqual(self.mailbox.status, Mailbox.Status.ACTIVE)
        self.assertEqual(result.last_uid, 1)
        self.assertEqual(TriageItem.objects.filter(status=TriageStatus.REJECTED).count(), 1)

    def test_body_and_forwarded_original_sender_are_stored(self) -> None:
        body = (
            "Segue o extrato do cliente.\n\n"
            "De: Maria Padaria <maria@padaria.example>\nEnviado: segunda\nAssunto: extrato\n"
        )
        message = _message(body=body)
        _attach(message, PDF, "e.pdf")
        self.poll(message.as_bytes())
        item = TriageItem.objects.get()
        self.assertIn("Segue o extrato do cliente", item.body_excerpt)
        self.assertEqual(item.original_sender, "maria@padaria.example")
        self.assertEqual(item.origin, TriageItem.Origin.EMAIL)

    def test_original_sender_stays_empty_when_ambiguous_or_internal(self) -> None:
        for body in (
            "De: a@x.example, b@y.example\nAssunto: x\n",
            "De: colega <joao@e11-office.test>\nAssunto: x\n",
            "sem cabeçalho de encaminhamento",
        ):
            TriageItem.objects.all().delete()
            Mailbox.objects.filter(pk=self.mailbox.pk).update(cursor="")
            self.mailbox.refresh_from_db()
            message = _message(body=body)
            _attach(message, PDF + body.encode()[:5], "e.pdf")
            self.poll(message.as_bytes())
            self.assertEqual(TriageItem.objects.get().original_sender, "", body)

    def test_body_is_bounded_and_html_only_mail_is_reduced_to_text(self) -> None:
        message = EmailMessage()
        message["From"] = "ana@e11-office.test"
        message["Subject"] = "Html"
        html = "<html><script>alert(1)</script><p>Olá <b>mundo</b></p>" + "x" * 9000 + "</html>"
        message.set_content(html, subtype="html")
        _attach(message, PDF, "h.pdf")
        self.poll(message.as_bytes())
        excerpt = TriageItem.objects.get().body_excerpt
        self.assertLessEqual(len(excerpt), 6000)
        self.assertIn("Olá mundo", excerpt)
        self.assertNotIn("alert", excerpt)
        self.assertNotIn("<p>", excerpt)
