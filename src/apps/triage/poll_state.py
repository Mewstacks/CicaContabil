"""Durable mailbox retry state shared by the three read-only transports."""

from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from apps.triage.models import Mailbox


def retry_hint_seconds(header: str | None) -> int:
    """Honor bounded integer Retry-After hints without trusting provider payloads."""
    if not header or not header.isascii() or not header.isdigit() or len(header) > 7:
        return 0
    return min(int(header), 86_400)


def mark_failure(
    mailbox: Mailbox, message: str, *, transient: bool, retry_seconds: int = 0
) -> None:
    mailbox.last_error = message[:500]
    if transient:
        mailbox.poll_failure_count = min(mailbox.poll_failure_count + 1, 15)
        delay = min(300 * 2 ** (mailbox.poll_failure_count - 1), 21_600)
        mailbox.poll_retry_after = timezone.now() + timedelta(
            seconds=max(delay, min(retry_seconds, 86_400))
        )
        mailbox.status = Mailbox.Status.ACTIVE
    else:
        mailbox.status = Mailbox.Status.ERROR
        mailbox.poll_retry_after = None
        mailbox.poll_failure_count = 0
    mailbox.save(
        update_fields=[
            "last_error",
            "status",
            "poll_retry_after",
            "poll_failure_count",
            "updated_at",
        ]
    )


def mark_success(mailbox: Mailbox) -> None:
    mailbox.last_error = ""
    mailbox.poll_retry_after = None
    mailbox.poll_failure_count = 0
    mailbox.last_polled_at = timezone.now()
    mailbox.save(
        update_fields=[
            "last_error",
            "poll_retry_after",
            "poll_failure_count",
            "last_polled_at",
            "updated_at",
        ]
    )
