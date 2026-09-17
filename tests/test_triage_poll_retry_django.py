from __future__ import annotations

import json
import socket
from datetime import timedelta
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.organizations.models import Organization
from apps.triage.gmail_poll import GmailTemporaryError, poll_gmail_mailbox
from apps.triage.gmail_poll import _get_json as gmail_get_json
from apps.triage.graph_poll import GraphTemporaryError, poll_graph_mailbox
from apps.triage.graph_poll import _get_json as graph_get_json
from apps.triage.imap import MailboxIMAPTemporaryError
from apps.triage.imap_poll import poll_imap_mailbox
from apps.triage.models import Mailbox
from apps.triage.poll_state import mark_success
from apps.triage.tasks import dispatch_active_mailboxes, poll_activated_mailbox


class MailboxRetryTests(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Retry Office", slug="retry-office")
        self.cutoff = timezone.now() - timedelta(days=1)

    def _mailbox(self, provider: str, name: str) -> Mailbox:
        return Mailbox.objects.create(
            organization=self.office,
            provider=provider,
            address=name,
            status=Mailbox.Status.ACTIVE,
            active=True,
            since=self.cutoff,
        )

    def test_provider_429_hints_are_bounded_and_retryable(self) -> None:
        headers = {"Retry-After": "1200"}

        class FailingOpener:
            def open(self, request, timeout):
                raise HTTPError(request.full_url, 429, "quota", headers, None)

        with (
            patch("apps.triage.gmail_poll.build_opener", return_value=FailingOpener()),
            self.assertRaises(GmailTemporaryError) as gmail,
        ):
            gmail_get_json("https://gmail.googleapis.com/gmail/v1/users/me/profile", "fake", 100)
        with (
            patch("apps.triage.graph_poll.build_opener", return_value=FailingOpener()),
            self.assertRaises(GraphTemporaryError) as graph,
        ):
            graph_get_json("https://graph.microsoft.com/v1.0/me/messages/delta", "fake", 100)
        self.assertEqual(gmail.exception.retry_seconds, 1200)
        self.assertEqual(graph.exception.retry_seconds, 1200)
        self.assertNotIn("quota", str(gmail.exception))

    @override_settings(TRIAGE_EMAIL_POLL_ENABLED=True)
    def test_transient_graph_error_keeps_cursor_and_scheduler_skips_until_due(self) -> None:
        mailbox = self._mailbox(Mailbox.Provider.MS365_GRAPH, "graph@retry.example.test")
        with self.assertRaises(GraphTemporaryError):
            poll_graph_mailbox(
                mailbox=mailbox,
                get_json=lambda url, token, limit: (_ for _ in ()).throw(
                    GraphTemporaryError("temporary", retry_seconds=1200)
                ),
                refresh=lambda provider, credential, app: ("fake", credential),
            )
        mailbox.refresh_from_db()
        self.assertEqual(mailbox.status, Mailbox.Status.ACTIVE)
        self.assertEqual(mailbox.cursor, "")
        self.assertEqual(mailbox.poll_failure_count, 1)
        self.assertGreater(mailbox.poll_retry_after, timezone.now() + timedelta(minutes=19))
        with patch("apps.triage.tasks.poll_activated_mailbox.delay") as queue:
            self.assertEqual(dispatch_active_mailboxes(), 0)
            queue.assert_not_called()
        self.assertEqual(poll_activated_mailbox(str(mailbox.pk)), {"state": "inactive_or_busy"})
        mailbox.poll_retry_after = timezone.now() - timedelta(seconds=1)
        mailbox.save(update_fields=["poll_retry_after"])
        with patch("apps.triage.tasks.poll_activated_mailbox.delay") as queue:
            self.assertEqual(dispatch_active_mailboxes(), 1)
            queue.assert_called_once_with(str(mailbox.pk))
        mark_success(mailbox)
        mailbox.refresh_from_db()
        self.assertEqual(mailbox.poll_failure_count, 0)
        self.assertIsNone(mailbox.poll_retry_after)

    def test_gmail_transient_error_keeps_box_active(self) -> None:
        mailbox = self._mailbox(Mailbox.Provider.GMAIL_API, "gmail@retry.example.test")
        with self.assertRaises(GmailTemporaryError):
            poll_gmail_mailbox(
                mailbox=mailbox,
                get_json=lambda url, token, limit: (_ for _ in ()).throw(
                    GmailTemporaryError("temporary")
                ),
                refresh=lambda provider, credential, app: ("fake", credential),
            )
        mailbox.refresh_from_db()
        self.assertEqual(mailbox.status, Mailbox.Status.ACTIVE)
        self.assertEqual(mailbox.poll_failure_count, 1)
        self.assertIsNotNone(mailbox.poll_retry_after)

    def test_imap_socket_failure_retries_without_consuming_uid(self) -> None:
        mailbox = self._mailbox(Mailbox.Provider.IMAP, "imap@retry.example.test")
        mailbox.credential = json.dumps(
            {
                "version": 1,
                "provider": "imap",
                "host": "mail.example.test",
                "username": "box",
                "password": "fake",
            }
        )
        mailbox.save(update_fields=["credential"])

        class BrokenIMAP:
            def __init__(self, host: str, address: str) -> None:
                pass

            def login(self, username: str, password: str):
                raise OSError("connection dropped")

            def logout(self) -> None:
                pass

        with (
            patch("apps.triage.imap_poll.public_imap_address", return_value="8.8.8.8"),
            self.assertRaises(MailboxIMAPTemporaryError),
        ):
            poll_imap_mailbox(mailbox=mailbox, connection_factory=BrokenIMAP)
        mailbox.refresh_from_db()
        self.assertEqual(mailbox.status, Mailbox.Status.ACTIVE)
        self.assertEqual(mailbox.cursor, "")
        self.assertEqual(mailbox.poll_failure_count, 1)
        self.assertNotIn("connection dropped", mailbox.last_error)

    def test_imap_temporary_dns_failure_is_not_treated_as_bad_configuration(self) -> None:
        mailbox = self._mailbox(Mailbox.Provider.IMAP, "dns@retry.example.test")
        mailbox.credential = json.dumps(
            {
                "version": 1,
                "provider": "imap",
                "host": "mail.example.test",
                "username": "box",
                "password": "fake",
            }
        )
        mailbox.save(update_fields=["credential"])
        with (
            patch(
                "apps.triage.imap.socket.getaddrinfo",
                side_effect=socket.gaierror(socket.EAI_AGAIN, "temporary"),
            ),
            self.assertRaises(MailboxIMAPTemporaryError),
        ):
            poll_imap_mailbox(mailbox=mailbox)
        mailbox.refresh_from_db()
        self.assertEqual(mailbox.status, Mailbox.Status.ACTIVE)
        self.assertEqual(mailbox.poll_failure_count, 1)
