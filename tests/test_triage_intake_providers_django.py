"""AC-11.2 nos leitores Graph e Gmail: logo ignorado, corpo gravado, anexo estranho rejeitado."""

from __future__ import annotations

import base64
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlsplit

from django.utils import timezone

from apps.triage.gmail_poll import poll_gmail_mailbox
from apps.triage.graph_poll import poll_graph_mailbox
from apps.triage.models import Mailbox, TriageItem
from apps.triage.transitions import TriageStatus
from triage_v2_support import PDF, TriageV2Case


class GraphIntakeTests(TriageV2Case):
    def setUp(self) -> None:
        super().setUp()
        self.mailbox = Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.MS365_GRAPH,
            address="box@e11-office.test",
            folder="INBOX",
            status=Mailbox.Status.ACTIVE,
            active=True,
            since=timezone.now() - timedelta(days=1),
            credential='{"version":1,"provider":"ms365_graph","refresh_token":"synthetic"}',
        )
        self.delta_path = "/v1.0/me/mailFolders/inbox/messages/delta"
        self.delta_link = f"https://graph.microsoft.com{self.delta_path}?$deltatoken=x"

    def poll(self, rows: list[dict[str, Any]], *, body: str = "") -> Any:
        message = {
            "id": "msg-1",
            "receivedDateTime": timezone.now().isoformat(),
            "hasAttachments": True,
            "subject": "Docs",
            "bodyPreview": body,
            "from": {"emailAddress": {"address": "ana@e11-office.test"}},
        }

        def get_json(url: str, token: str, limit: int) -> dict[str, object]:
            if urlsplit(url).path == self.delta_path:
                return {"value": [message], "@odata.deltaLink": self.delta_link}
            return {"value": rows}

        return poll_graph_mailbox(
            mailbox=self.mailbox,
            get_json=get_json,
            get_bytes=lambda url, token, limit: PDF,
            refresh=lambda provider, credential, app: ("access", credential),
        )

    def row(self, name: str, **extra: Any) -> dict[str, Any]:
        base = {
            "@odata.type": "#microsoft.graph.fileAttachment",
            "id": f"id-{name}",
            "name": name,
            "size": len(PDF),
            "contentType": "application/pdf",
            "isInline": False,
        }
        base.update(extra)
        return base

    def test_signature_image_is_ignored_and_pdf_kept(self) -> None:
        logo = self.row("image001.png", contentType="image/png", isInline=True, size=2000)
        self.poll([logo, self.row("extrato.pdf")])
        self.assertEqual(
            list(TriageItem.objects.values_list("original_name", flat=True)), ["extrato.pdf"]
        )

    def test_attached_message_is_rejected_with_a_reason_and_polling_continues(self) -> None:
        item_attachment = {
            "@odata.type": "#microsoft.graph.itemAttachment",
            "id": "id-msg",
            "name": "Encaminhado",
            "size": 900,
        }
        result = self.poll([item_attachment, self.row("extrato.pdf")])
        self.assertTrue(result.round_complete)
        rejected = TriageItem.objects.get(original_name="Encaminhado")
        self.assertEqual(rejected.status, TriageStatus.REJECTED)
        self.assertTrue(rejected.rejection_reason)
        self.assertTrue(TriageItem.objects.filter(original_name="extrato.pdf").exists())
        self.mailbox.refresh_from_db()
        self.assertEqual(self.mailbox.status, Mailbox.Status.ACTIVE)

    def test_unsupported_format_is_rejected(self) -> None:
        self.poll([self.row("setup.exe", contentType="application/octet-stream")])
        item = TriageItem.objects.get()
        self.assertEqual(item.status, TriageStatus.REJECTED)
        self.assertIn(".exe", item.rejection_reason)

    def test_body_preview_and_forwarded_author_are_stored(self) -> None:
        self.poll(
            [self.row("extrato.pdf")],
            body="Segue\nDe: Maria <maria@padaria.example>\nEnviado: hoje",
        )
        item = TriageItem.objects.get()
        self.assertIn("Segue", item.body_excerpt)
        self.assertEqual(item.original_sender, "maria@padaria.example")


class GmailIntakeTests(TriageV2Case):
    def setUp(self) -> None:
        super().setUp()
        self.mailbox = Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.GMAIL_API,
            address="box@e11-office.test",
            folder="INBOX",
            status=Mailbox.Status.ACTIVE,
            active=True,
            since=timezone.now() - timedelta(days=1),
            credential='{"version":1,"provider":"gmail_api","refresh_token":"synthetic"}',
        )

    def message(self, parts: list[dict[str, Any]], body: str = "") -> dict[str, Any]:
        encoded = base64.urlsafe_b64encode(body.encode()).decode()
        return {
            "id": "gmail-one",
            "labelIds": ["INBOX"],
            "internalDate": str(int(timezone.now().timestamp() * 1_000)),
            "payload": {
                "headers": [
                    {"name": "From", "value": "ana@e11-office.test"},
                    {"name": "Subject", "value": "Docs"},
                ],
                "parts": [
                    {"partId": "0", "mimeType": "text/plain", "body": {"data": encoded}},
                    *parts,
                ],
            },
        }

    def poll(self, message: dict[str, Any]) -> None:
        def get_json(url: str, token: str, limit: int) -> dict[str, Any]:
            path = urlsplit(url).path
            query = parse_qs(urlsplit(url).query)
            if path.endswith("/profile"):
                return {"historyId": "100"}
            if path.endswith("/messages"):
                return {"messages": [{"id": "gmail-one"}]} if "pageToken" not in query else {}
            if path.endswith("/gmail-one"):
                return message
            if "/attachments/" in path:
                data = base64.urlsafe_b64encode(PDF).decode()
                return {"size": len(PDF), "data": data}
            raise AssertionError(url)

        poll_gmail_mailbox(
            mailbox=self.mailbox,
            get_json=get_json,
            refresh=lambda provider, credential, app: ("access", credential),
        )

    def part(self, name: str, mime: str, **extra: Any) -> dict[str, Any]:
        row = {
            "partId": f"p-{name}",
            "filename": name,
            "mimeType": mime,
            "body": {"size": len(PDF), "attachmentId": f"a-{name}"},
        }
        row.update(extra)
        return row

    def test_inline_logo_is_ignored_and_pdf_kept(self) -> None:
        logo = self.part(
            "logo.png",
            "image/png",
            headers=[{"name": "Content-ID", "value": "<l1>"}],
            body={"size": 2000, "attachmentId": "a-logo"},
        )
        self.poll(self.message([logo, self.part("extrato.pdf", "application/pdf")]))
        self.assertEqual(
            list(TriageItem.objects.values_list("original_name", flat=True)), ["extrato.pdf"]
        )

    def test_unsupported_part_is_rejected_and_body_is_stored(self) -> None:
        body = "Oi\nDe: Joao <joao@cliente.example>\nAssunto: x"
        self.poll(
            self.message(
                [self.part("setup.exe", "application/octet-stream"),
                 self.part("e.pdf", "application/pdf")],
                body=body,
            )
        )
        rejected = TriageItem.objects.get(original_name="setup.exe")
        self.assertEqual(rejected.status, TriageStatus.REJECTED)
        kept = TriageItem.objects.get(original_name="e.pdf")
        self.assertIn("Oi", kept.body_excerpt)
        self.assertEqual(kept.original_sender, "joao@cliente.example")
