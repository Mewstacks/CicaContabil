from __future__ import annotations

import json
from datetime import timedelta
from email.message import EmailMessage
from io import BytesIO
from tempfile import TemporaryDirectory
from unittest.mock import patch

from django.core.exceptions import SuspiciousFileOperation, ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage.imap_poll import poll_imap_mailbox
from apps.triage.ingest import MAX_EMAIL_ATTACHMENT_BYTES, receive_email_attachment
from apps.triage.models import (
    DestinationProfile,
    DocumentType,
    Mailbox,
    TriageItem,
    TriageSafetyScan,
)
from apps.triage.security import (
    ClamdScanner,
    ScannerUnavailable,
    ScanVerdict,
    scan_quarantined_item,
)
from apps.triage.services import archive_internal, decide_item
from apps.triage.storage import PrivateTriageStorage
from apps.triage.transitions import TriageStatus


class EmailAttachmentQuarantineTests(TestCase):
    def setUp(self) -> None:
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.office = Organization.objects.create(name="Office One", slug="email-ingest-one")
        self.other = Organization.objects.create(name="Office Two", slug="email-ingest-two")
        self.mailbox = Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.IMAP,
            address="inbox@one.test",
            status=Mailbox.Status.ACTIVE,
            active=True,
        )
        self.other_mailbox = Mailbox.objects.create(
            organization=self.other,
            provider=Mailbox.Provider.IMAP,
            address="inbox@two.test",
            status=Mailbox.Status.ACTIVE,
            active=True,
        )

    def _receive(self, mailbox: Mailbox | None = None, **kwargs: object):
        values = {
            "mailbox": mailbox or self.mailbox,
            "message_id": "provider-message-1",
            "part_id": "part-1",
            "filename": r"C:\sender\folder\statement.pdf",
            "payload": b"unscanned-test-binary",
            "sender": "sender@example.test",
            "received_at": timezone.now() - timedelta(minutes=1),
            "declared_type": "application/pdf",
        }
        values.update(kwargs)
        return receive_email_attachment(**values)

    def test_received_email_attachment_stays_private_and_unreviewable(self) -> None:
        receipt = self._receive()
        item = receipt.item
        self.assertTrue(receipt.created)
        self.assertEqual(item.status, TriageStatus.QUARANTINED)
        self.assertIsNone(item.company)
        self.assertEqual(item.detected_type, "")
        self.assertEqual(item.original_name, "statement.pdf")
        self.assertEqual(item.blob.content.name.rsplit("/", 1)[-1], f"{item.id}.bin")
        self.assertEqual(item.events.count(), 1)
        with self.assertRaises(SuspiciousFileOperation):
            _ = item.blob.content.url
        with item.blob.content.open("rb") as file:
            self.assertEqual(file.read(), b"unscanned-test-binary")

    def test_replay_is_idempotent_but_separate_deliveries_keep_provenance(self) -> None:
        first = self._receive()
        replay = self._receive()
        duplicate = self._receive(message_id="provider-message-2")
        other_office = self._receive(self.other_mailbox)
        self.assertEqual(replay.duplicate_kind, "delivery")
        self.assertTrue(duplicate.created)
        self.assertEqual(first.item.id, replay.item.id)
        self.assertNotEqual(first.item.id, duplicate.item.id)
        self.assertEqual(first.item.content_hash, duplicate.item.content_hash)
        self.assertNotEqual(first.item.id, other_office.item.id)
        self.assertEqual(TriageItem.objects.filter(organization=self.office).count(), 2)
        self.assertEqual(TriageItem.objects.filter(organization=self.other).count(), 1)

    def test_paused_mailbox_and_oversized_attachment_do_not_store_binary(self) -> None:
        self.mailbox.active = False
        self.mailbox.save(update_fields=["active"])
        with self.assertRaises(ValidationError):
            self._receive()
        self.mailbox.active = True
        self.mailbox.save(update_fields=["active"])
        with self.assertRaises(ValidationError):
            self._receive(payload=b"x" * (MAX_EMAIL_ATTACHMENT_BYTES + 1))
        self.assertFalse(TriageItem.objects.exists())

    def test_imap_poll_uses_exact_cutoff_readonly_peek_and_checkpoint(self) -> None:
        cutoff = timezone.now().replace(microsecond=0)
        self.mailbox.since = cutoff
        self.mailbox.credential = json.dumps(
            {
                "version": 1,
                "provider": "imap",
                "host": "mail.example.test",
                "username": "inbox@one.test",
                "password": "synthetic-test-secret",
            }
        )
        self.mailbox.save(update_fields=["since", "credential"])
        message = EmailMessage()
        message["From"] = "sender@example.test"
        message["Subject"] = "Statement"
        message.set_content("Body")
        message.add_attachment(
            b"test-pdf-payload",
            maintype="application",
            subtype="pdf",
            filename="statement.pdf",
        )
        raw = message.as_bytes()

        class FakeIMAP:
            def __init__(self, host: str, address: str) -> None:
                self.calls: list[tuple[object, ...]] = []
                self.readonly = False

            def login(self, username: str, password: str):
                return "OK", [b"success"]

            def select(self, folder: str, readonly: bool = False):
                self.readonly = readonly
                return "OK", [b"2"]

            def response(self, code: str):
                return code, [b"900"]

            def uid(self, command: str, *args: object):
                self.calls.append((command, *args))
                if command == "search":
                    return "OK", [b"1 2"]
                uid = int(args[0])
                if args[1] == "(RFC822.SIZE INTERNALDATE)":
                    stamp = cutoff + timedelta(minutes=1 if uid == 2 else -1)
                    meta = (
                        f'1 (UID {uid} RFC822.SIZE {len(raw)} INTERNALDATE '
                        f'"{stamp.strftime("%d-%b-%Y %H:%M:%S %z")}")'
                    ).encode()
                    return "OK", [meta]
                if args[1] == "(BODY.PEEK[])":
                    return "OK", [(b"1 (BODY[] {size})", raw)]
                raise AssertionError(args)

            def logout(self) -> None:
                pass

        fake = FakeIMAP("", "")
        with patch("apps.triage.imap_poll.public_imap_address", return_value="8.8.8.8"):
            result = poll_imap_mailbox(mailbox=self.mailbox, connection_factory=lambda *_: fake)
        self.mailbox.refresh_from_db()
        self.assertTrue(fake.readonly)
        self.assertEqual(result.examined, 2)
        self.assertEqual(result.attachments_created, 1)
        self.assertEqual(result.last_uid, 2)
        self.assertEqual(TriageItem.objects.filter(organization=self.office).count(), 1)
        self.assertEqual(json.loads(self.mailbox.cursor)["uidvalidity"], 900)
        self.assertIn(("fetch", "2", "(BODY.PEEK[])"), fake.calls)

        replay = FakeIMAP("", "")
        with patch("apps.triage.imap_poll.public_imap_address", return_value="8.8.8.8"):
            second = poll_imap_mailbox(mailbox=self.mailbox, connection_factory=lambda *_: replay)
        self.assertEqual(second.examined, 0)
        self.assertFalse(any(call[0] == "fetch" for call in replay.calls))

    def test_antimalware_clean_result_does_not_release_unapproved_format(self) -> None:
        item = self._receive().item

        class CleanScanner:
            def scan(self, stream: object) -> ScanVerdict:
                self_payload = stream.read()
                assert self_payload == b"unscanned-test-binary"
                return ScanVerdict(TriageSafetyScan.Verdict.CLEAN, "test-scanner")

        scan = scan_quarantined_item(item=item, scanner=CleanScanner())
        item.refresh_from_db()
        self.assertEqual(scan.verdict, TriageSafetyScan.Verdict.CLEAN)
        self.assertEqual(scan.content_hash, item.content_hash)
        self.assertEqual(scan.format_verdict, TriageSafetyScan.FormatVerdict.INVALID)
        self.assertEqual(item.status, TriageStatus.QUARANTINED)
        self.assertEqual(item.events.count(), 2)

    def test_clean_supported_pdf_advances_to_extraction_queue(self) -> None:
        item = self._receive(
            message_id="valid-pdf", payload=b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
        ).item

        class CleanScanner:
            def scan(self, stream: object) -> ScanVerdict:
                return ScanVerdict(TriageSafetyScan.Verdict.CLEAN, "test-scanner")

        scan = scan_quarantined_item(item=item, scanner=CleanScanner())
        item.refresh_from_db()
        self.assertEqual(scan.format_verdict, TriageSafetyScan.FormatVerdict.VALID)
        self.assertEqual(item.status, TriageStatus.AWAITING_EXTRACTION)
        self.assertEqual(item.detected_type, "application/pdf")

    def test_approved_email_pdf_is_copied_and_verified_in_internal_library(self) -> None:
        item = self._receive(
            message_id="archive-pdf", payload=b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF\n"
        ).item

        class CleanScanner:
            def scan(self, stream: object) -> ScanVerdict:
                return ScanVerdict(TriageSafetyScan.Verdict.CLEAN, "test-scanner")

        scan_quarantined_item(item=item, scanner=CleanScanner())
        item.refresh_from_db()
        company = ClientCompany.objects.create(
            organization=self.office, name="Cliente", dominio_code="321"
        )
        document_type = DocumentType.objects.create(
            organization=self.office, code="documento", label="Documento",
            name_template="{codigo}_DOCUMENTO_{periodo}",
            period_kind=DocumentType.PeriodKind.COMPETENCIA,
        )
        DestinationProfile.objects.create(
            organization=self.office, mode=DestinationProfile.Mode.INTERNAL
        )
        reviewer = User.objects.create_user(email="reviewer@one.test", password="test-only")
        item.company = company
        item.document_type = document_type
        item.final_name = "321_DOCUMENTO_082026.pdf"
        item.transition_to(TriageStatus.EXTRACTING)
        item.transition_to(TriageStatus.AWAITING_REVIEW)
        item.save()
        decide_item(item=item, actor=reviewer, decision="archive", reason="")
        item.refresh_from_db()
        self.assertEqual(item.status, TriageStatus.READY_TO_ARCHIVE)
        self.assertEqual(item.destination_path, "")

        archived = archive_internal(item=item, actor=reviewer)
        self.assertEqual(archived.status, TriageStatus.ARCHIVED)
        self.assertNotEqual(archived.destination_path, archived.blob.content.name)
        self.assertTrue(archived.destination_path.startswith("private/triage/library/"))
        self.assertEqual(archived.destination_hash, archived.content_hash)
        self.assertTrue(PrivateTriageStorage().exists(archived.destination_path))
        self.assertEqual(archive_internal(item=archived, actor=reviewer).id, archived.id)
        with PrivateTriageStorage().open(archived.destination_path, "wb") as copy:
            copy.write(b"tampered")
        with self.assertRaises(ValidationError):
            archive_internal(item=archived, actor=reviewer)

    def test_antimalware_detection_rejects_and_unavailable_scanner_stays_quarantined(self) -> None:
        infected = self._receive().item
        pending = self._receive(message_id="provider-message-2").item

        class InfectedScanner:
            def scan(self, stream: object) -> ScanVerdict:
                return ScanVerdict(TriageSafetyScan.Verdict.INFECTED, "test-scanner")

        scan_quarantined_item(item=infected, scanner=InfectedScanner())
        infected.refresh_from_db()
        self.assertEqual(infected.status, TriageStatus.REJECTED)

        with override_settings(TRIAGE_CLAMD_SOCKET="", TRIAGE_CLAMD_PORT=0):
            error = scan_quarantined_item(item=pending)
        pending.refresh_from_db()
        self.assertEqual(error.verdict, TriageSafetyScan.Verdict.ERROR)
        self.assertEqual(pending.status, TriageStatus.QUARANTINED)

    def test_clamd_adapter_streams_bytes_and_requires_complete_clean_reply(self) -> None:
        class FakeSocket:
            def __init__(self, reply: bytes) -> None:
                self.reply = reply
                self.sent = bytearray()

            def __enter__(self):
                return self

            def __exit__(self, *args: object) -> None:
                pass

            def sendall(self, payload: bytes) -> None:
                self.sent.extend(payload)

            def recv(self, size: int) -> bytes:
                reply, self.reply = self.reply, b""
                return reply

        clean_socket = FakeSocket(b"stream: OK\0")
        scanner = ClamdScanner(loopback_port=3310)
        with patch.object(scanner, "_connect", return_value=clean_socket):
            verdict = scanner.scan(BytesIO(b"sample"))
        self.assertEqual(verdict.verdict, TriageSafetyScan.Verdict.CLEAN)
        self.assertTrue(clean_socket.sent.startswith(b"zINSTREAM\0"))
        self.assertTrue(clean_socket.sent.endswith(b"\x00\x00\x00\x00"))
        self.assertIn(b"sample", clean_socket.sent)

        partial_socket = FakeSocket(b"stream: OK")
        with (
            patch.object(scanner, "_connect", return_value=partial_socket),
            self.assertRaises(ScannerUnavailable),
        ):
            scanner.scan(BytesIO(b"sample"))
