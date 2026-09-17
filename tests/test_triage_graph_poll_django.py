from __future__ import annotations

import json
from datetime import timedelta
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.organizations.models import Organization
from apps.triage.graph_poll import GraphMailboxError, poll_graph_mailbox
from apps.triage.models import Mailbox, TriageItem
from apps.triage.transitions import TriageStatus


class GraphAttachmentDeltaTests(TestCase):
    def setUp(self) -> None:
        self.enterContext(override_settings(MEDIA_ROOT=self.enterContext(TemporaryDirectory())))
        self.office = Organization.objects.create(name="Graph Office", slug="graph-triage")
        self.cutoff = timezone.now() - timedelta(days=1)
        self.mailbox = Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.MS365_GRAPH,
            address="box@graph.example.test",
            folder="INBOX",
            status=Mailbox.Status.ACTIVE,
            active=True,
            since=self.cutoff,
            credential='{"version":1,"provider":"ms365_graph","refresh_token":"synthetic"}',
        )
        self.delta_path = "/v1.0/me/mailFolders/inbox/messages/delta"
        self.delta_link = f"https://graph.microsoft.com{self.delta_path}?$deltatoken=synthetic"
        self.next_link = f"https://graph.microsoft.com{self.delta_path}?$skiptoken=synthetic"
        self.payload = b"synthetic-attachment-bytes"
        self.message = {
            "id": "immutable-message-id",
            "receivedDateTime": timezone.now().isoformat(),
            "hasAttachments": False,  # inline-only files are omitted from this flag
            "subject": "Document",
            "from": {"emailAddress": {"address": "sender@example.test"}},
        }

    def _attachment_list(self) -> dict[str, object]:
        return {
            "value": [
                {
                    "@odata.type": "#microsoft.graph.fileAttachment",
                    "id": "attachment-id",
                    "name": "statement.pdf",
                    "size": len(self.payload),
                    "contentType": "application/pdf",
                    "isInline": True,
                }
            ]
        }

    def test_graph_polls_inline_attachment_and_commits_only_complete_pages(self) -> None:
        calls: list[str] = []

        def get_json(url: str, token: str, limit: int) -> dict[str, object]:
            calls.append(url)
            if urlsplit(url).path == self.delta_path:
                if "$skiptoken=" in url:
                    return {"value": [], "@odata.deltaLink": self.delta_link}
                return {"value": [self.message], "@odata.nextLink": self.next_link}
            return self._attachment_list()

        def get_bytes(url: str, token: str, limit: int) -> bytes:
            calls.append(url)
            return self.payload

        result = poll_graph_mailbox(
            mailbox=self.mailbox,
            get_json=get_json,
            get_bytes=get_bytes,
            refresh=lambda provider, credential, app: ("synthetic-access", credential),
        )
        self.mailbox.refresh_from_db()
        item = TriageItem.objects.get(organization=self.office)
        self.assertEqual(result.pages, 2)
        self.assertTrue(result.round_complete)
        self.assertEqual(result.attachments_created, 1)
        self.assertEqual(item.status, TriageStatus.QUARANTINED)
        self.assertEqual(item.sender, "sender@example.test")
        self.assertEqual(json.loads(self.mailbox.cursor)["url"], self.delta_link)
        self.assertTrue(any("/$value" in url for url in calls))

    def test_graph_skips_nonmatching_message_before_listing_attachments(self) -> None:
        self.mailbox.sender_filter = "documentos@cliente.test"
        self.mailbox.save(update_fields=["sender_filter"])
        calls: list[str] = []

        def get_json(url: str, token: str, limit: int) -> dict[str, object]:
            calls.append(url)
            if urlsplit(url).path == self.delta_path:
                return {"value": [self.message], "@odata.deltaLink": self.delta_link}
            self.fail("attachments must not be listed for a filtered message")

        result = poll_graph_mailbox(
            mailbox=self.mailbox,
            get_json=get_json,
            get_bytes=lambda url, token, limit: self.fail("file must not be downloaded"),
            refresh=lambda provider, credential, app: ("access", credential),
        )

        self.assertEqual(result.attachments_created, 0)
        self.assertFalse(TriageItem.objects.exists())
        self.assertFalse(any("/attachments" in url for url in calls))

    def test_invalid_provider_nextlink_preserves_cursor_and_replay_deduplicates(self) -> None:
        def malicious(url: str, token: str, limit: int) -> dict[str, object]:
            if urlsplit(url).path == self.delta_path:
                return {
                    "value": [self.message],
                    "@odata.nextLink": "https://attacker.example.test/steal",
                }
            return self._attachment_list()

        with self.assertRaises(GraphMailboxError):
            poll_graph_mailbox(
                mailbox=self.mailbox,
                get_json=malicious,
                get_bytes=lambda url, token, limit: self.payload,
                refresh=lambda provider, credential, app: ("access", credential),
            )
        self.mailbox.refresh_from_db()
        self.assertEqual(self.mailbox.cursor, "")
        self.assertEqual(self.mailbox.status, Mailbox.Status.ERROR)
        self.assertEqual(TriageItem.objects.count(), 1)

        self.mailbox.status = Mailbox.Status.ACTIVE
        self.mailbox.save(update_fields=["status"])
        downloads = 0

        def no_redownload(url: str, token: str, limit: int) -> bytes:
            nonlocal downloads
            downloads += 1
            return self.payload

        def safe(url: str, token: str, limit: int) -> dict[str, object]:
            if urlsplit(url).path == self.delta_path:
                return {"value": [self.message], "@odata.deltaLink": self.delta_link}
            return self._attachment_list()

        result = poll_graph_mailbox(
            mailbox=self.mailbox,
            get_json=safe,
            get_bytes=no_redownload,
            refresh=lambda provider, credential, app: ("access", credential),
        )
        self.assertEqual(downloads, 0)
        self.assertEqual(result.duplicates, 1)
        self.assertEqual(TriageItem.objects.count(), 1)

    def test_oversized_attachment_never_downloads_or_advances_delta(self) -> None:
        def oversized(url: str, token: str, limit: int) -> dict[str, object]:
            if urlsplit(url).path == self.delta_path:
                return {"value": [self.message], "@odata.deltaLink": self.delta_link}
            row = self._attachment_list()
            row["value"][0]["size"] = 25 * 1024 * 1024 + 1
            return row

        with self.assertRaises(GraphMailboxError):
            poll_graph_mailbox(
                mailbox=self.mailbox,
                get_json=oversized,
                get_bytes=lambda url, token, limit: self.fail("raw file must not be fetched"),
                refresh=lambda provider, credential, app: ("access", credential),
            )
        self.mailbox.refresh_from_db()
        self.assertEqual(self.mailbox.cursor, "")
        self.assertFalse(TriageItem.objects.exists())
