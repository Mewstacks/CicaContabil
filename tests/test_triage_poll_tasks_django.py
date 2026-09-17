from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.organizations.models import Organization
from apps.triage.models import Mailbox
from apps.triage.tasks import dispatch_active_mailboxes, poll_activated_mailbox


class ScheduledMailboxIntakeTests(TestCase):
    def setUp(self) -> None:
        self.office = Organization.objects.create(name="Scheduled Office", slug="scheduled-office")
        self.mailbox = Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.GMAIL_API,
            address="inbox@scheduled.example.test",
            status=Mailbox.Status.ACTIVE,
            active=True,
            since=timezone.now() - timedelta(days=1),
        )

    def test_disabled_schedule_does_not_queue_or_call_provider(self) -> None:
        with (
            override_settings(TRIAGE_EMAIL_POLL_ENABLED=False),
            patch("apps.triage.tasks.poll_gmail_mailbox") as provider,
            patch("apps.triage.tasks.poll_activated_mailbox.delay") as queue,
        ):
            self.assertEqual(dispatch_active_mailboxes(), 0)
            self.assertEqual(poll_activated_mailbox(str(self.mailbox.pk)), {"state": "disabled"})
            queue.assert_not_called()
            provider.assert_not_called()

    @override_settings(TRIAGE_EMAIL_POLL_ENABLED=True)
    def test_only_active_dated_office_boxes_are_dispatched(self) -> None:
        other = Mailbox.objects.create(
            organization=self.office,
            provider=Mailbox.Provider.IMAP,
            address="other@scheduled.example.test",
            status=Mailbox.Status.ACTIVE,
            active=True,
            since=None,
        )
        with patch("apps.triage.tasks.poll_activated_mailbox.delay") as queue:
            self.assertEqual(dispatch_active_mailboxes(), 1)
            queue.assert_called_once_with(str(self.mailbox.pk))
            other.since = timezone.now()
            other.save(update_fields=["since"])
            self.office.is_active = False
            self.office.save(update_fields=["is_active"])
            self.assertEqual(dispatch_active_mailboxes(), 0)

    @override_settings(TRIAGE_EMAIL_POLL_ENABLED=True)
    def test_db_lease_blocks_overlap_and_releases_after_success(self) -> None:
        calls = 0

        def simulated(*, mailbox, max_pages):
            nonlocal calls
            calls += 1
            mailbox.refresh_from_db()
            self.assertIsNotNone(mailbox.poll_lease_token)
            self.assertEqual(poll_activated_mailbox(str(mailbox.pk)), {"state": "inactive_or_busy"})
            return type("Result", (), {"attachments_created": 2})()

        with patch("apps.triage.tasks.poll_gmail_mailbox", side_effect=simulated):
            self.assertEqual(
                poll_activated_mailbox(str(self.mailbox.pk)),
                {"state": "completed", "attachments_created": 2},
            )
        self.mailbox.refresh_from_db()
        self.assertEqual(calls, 1)
        self.assertIsNone(self.mailbox.poll_lease_token)
        self.assertIsNone(self.mailbox.poll_lease_until)

    @override_settings(TRIAGE_EMAIL_POLL_ENABLED=True)
    def test_unexpected_error_is_sanitized_and_lease_recovers(self) -> None:
        with patch("apps.triage.tasks.poll_gmail_mailbox", side_effect=RuntimeError("secret")):
            self.assertEqual(poll_activated_mailbox(str(self.mailbox.pk)), {"state": "error"})
        self.mailbox.refresh_from_db()
        self.assertEqual(self.mailbox.status, Mailbox.Status.ERROR)
        self.assertNotIn("secret", self.mailbox.last_error)
        self.assertIsNone(self.mailbox.poll_lease_token)
        self.assertIsNone(self.mailbox.poll_lease_until)
