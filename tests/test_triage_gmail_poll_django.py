from __future__ import annotations

import base64
import json
from datetime import timedelta
from tempfile import TemporaryDirectory
from urllib.parse import parse_qs, urlsplit

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.organizations.models import Organization
from apps.triage.gmail_poll import GmailHistoryExpired, GmailMailboxError, poll_gmail_mailbox
from apps.triage.models import Mailbox, TriageItem
from apps.triage.transitions import TriageStatus


class GmailAttachmentHistoryTests(TestCase):
    def setUp(self) -> None:
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.office = Organization.objects.create(name="Gmail Office", slug="gmail-poll-office")
        self.cutoff = timezone.now() - timedelta(days=1)
        self.mailbox = Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.GMAIL_API,
            address="box@gmail.example.test",
            folder="INBOX",
            status=Mailbox.Status.ACTIVE,
            active=True,
            since=self.cutoff,
            credential='{"version":1,"provider":"gmail_api","refresh_token":"synthetic"}',
        )
        self.raw = b"pdf-fixture-bytes"

    def _message(self, message_id: str = "gmail-one", *, size: int | None = None) -> dict:
        return {
            "id": message_id,
            "labelIds": ["INBOX"],
            "internalDate": str(int(timezone.now().timestamp() * 1_000)),
            "payload": {
                "headers": [
                    {"name": "From", "value": "from@example.test"},
                    {"name": "Subject", "value": "Arquivo"},
                ],
                "parts": [
                    {
                        "partId": "1",
                        "filename": "doc.pdf",
                        "mimeType": "application/pdf",
                        "body": {
                            "size": len(self.raw) if size is None else size,
                            "attachmentId": "attach-one",
                        },
                    }
                ],
            },
        }

    def _transport(self, *, fail_attachment: bool = False):
        calls: list[str] = []

        def get_json(url: str, token: str, limit: int) -> dict:
            calls.append(url)
            path = urlsplit(url).path
            query = parse_qs(urlsplit(url).query)
            if path.endswith("/profile"):
                return {"historyId": "100"}
            if path.endswith("/history"):
                return {
                    "history": [{"messagesAdded": [{"message": {"id": "gmail-two"}}]}],
                    "historyId": "102",
                }
            if path.endswith("/messages"):
                if "pageToken" in query:
                    return {"messages": []}
                return {"messages": [{"id": "gmail-one"}], "nextPageToken": "next-page"}
            if "/attachments/" in path:
                if fail_attachment:
                    raise GmailMailboxError("download synthetic failure")
                return {
                    "size": len(self.raw),
                    "data": base64.urlsafe_b64encode(self.raw).rstrip(b"=").decode(),
                }
            if path.endswith("/gmail-one"):
                return self._message()
            if path.endswith("/gmail-two"):
                return self._message("gmail-two")
            raise AssertionError(url)

        return get_json, calls

    def _poll(self, transport, pages: int = 3):
        return poll_gmail_mailbox(
            mailbox=self.mailbox,
            max_pages=pages,
            get_json=transport,
            refresh=lambda provider, credential, app: ("synthetic-access", credential),
        )

    def test_full_pages_then_history_receives_distinct_deliveries(self) -> None:
        transport, calls = self._transport()
        first = self._poll(transport)
        self.mailbox.refresh_from_db()
        self.assertEqual(first.pages, 2)
        self.assertEqual(first.attachments_created, 1)
        self.assertEqual(json.loads(self.mailbox.cursor)["mode"], "history")
        self.assertEqual(json.loads(self.mailbox.cursor)["history_id"], "100")
        second = self._poll(transport)
        self.assertEqual(second.attachments_created, 1)
        self.assertEqual(TriageItem.objects.count(), 2)
        self.assertEqual(
            set(TriageItem.objects.values_list("status", flat=True)), {TriageStatus.QUARANTINED}
        )
        self.assertTrue(any("startHistoryId=100" in call for call in calls))

    def test_gmail_skips_nonmatching_message_before_fetching_attachment_bytes(self) -> None:
        self.mailbox.subject_filter = "folha de pagamento"
        self.mailbox.save(update_fields=["subject_filter"])
        transport, calls = self._transport()

        result = self._poll(transport)

        self.assertEqual(result.attachments_created, 0)
        self.assertFalse(TriageItem.objects.exists())
        self.assertFalse(any("/attachments/" in call for call in calls))

    def test_failure_keeps_page_checkpoint_and_replay_deduplicates(self) -> None:
        first, calls = self._transport()
        fail = True

        def two_parts(url: str, token: str, limit: int) -> dict:
            if urlsplit(url).path.endswith("/gmail-one"):
                message = self._message()
                message["payload"]["parts"].append(
                    {
                        "partId": "2",
                        "filename": "second.pdf",
                        "mimeType": "application/pdf",
                        "body": {"size": len(self.raw), "attachmentId": "attach-two"},
                    }
                )
                return message
            if "/attachments/attach-two" in url and fail:
                raise GmailMailboxError("synthetic download failure")
            return first(url, token, limit)

        with self.assertRaises(GmailMailboxError):
            self._poll(two_parts)
        self.mailbox.refresh_from_db()
        self.assertEqual(json.loads(self.mailbox.cursor)["mode"], "full")
        self.assertEqual(json.loads(self.mailbox.cursor)["page_token"], "")
        self.assertEqual(TriageItem.objects.count(), 1)
        self.mailbox.status = Mailbox.Status.ACTIVE
        self.mailbox.save(update_fields=["status"])
        fail = False
        result = self._poll(two_parts)
        self.assertEqual(result.attachments_created, 1)
        self.assertEqual(result.duplicates, 1)
        self.assertEqual(TriageItem.objects.count(), 2)
        self.assertEqual(len([url for url in calls if "/attachments/attach-one" in url]), 1)

    def test_expired_history_resets_to_full_without_losing_items(self) -> None:
        self._poll(self._transport()[0])
        self.mailbox.refresh_from_db()

        def expired(url: str, token: str, limit: int) -> dict:
            if urlsplit(url).path.endswith("/history"):
                raise GmailHistoryExpired("expired")
            return {"historyId": "200"}

        result = self._poll(expired)
        self.mailbox.refresh_from_db()
        self.assertEqual(result.pages, 0)
        self.assertEqual(json.loads(self.mailbox.cursor)["mode"], "full")
        self.assertEqual(json.loads(self.mailbox.cursor)["history_id"], "200")
        self.assertEqual(TriageItem.objects.count(), 1)

    def test_oversized_attachment_preserves_cursor_without_fetching_bytes(self) -> None:
        calls: list[str] = []

        def oversized(url: str, token: str, limit: int) -> dict:
            calls.append(url)
            path = urlsplit(url).path
            if path.endswith("/profile"):
                return {"historyId": "100"}
            if path.endswith("/messages"):
                return {"messages": [{"id": "gmail-one"}]}
            if path.endswith("/gmail-one"):
                return self._message(size=25 * 1024 * 1024 + 1)
            raise AssertionError("oversized attachment fetched")

        with self.assertRaises(GmailMailboxError):
            self._poll(oversized)
        self.mailbox.refresh_from_db()
        self.assertEqual(json.loads(self.mailbox.cursor)["mode"], "full")
        self.assertFalse(TriageItem.objects.exists())
        self.assertFalse(any("/attachments/" in call for call in calls))
