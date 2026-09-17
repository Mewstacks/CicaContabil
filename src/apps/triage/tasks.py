"""Opt-in periodic email intake, one leased worker per authorized mailbox."""

from __future__ import annotations

import uuid
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils import timezone

from apps.triage.gmail_poll import GmailMailboxError, poll_gmail_mailbox
from apps.triage.graph_poll import GraphMailboxError, poll_graph_mailbox
from apps.triage.imap import MailboxIMAPError
from apps.triage.imap_poll import poll_imap_mailbox
from apps.triage.models import Mailbox
from apps.triage.oauth import MailboxOAuthError
from apps.triage.poll_state import mark_failure


def _eligible():  # type: ignore[no-untyped-def]
    return Mailbox.objects.filter(
        active=True,
        status=Mailbox.Status.ACTIVE,
        since__isnull=False,
        organization__is_active=True,
        organization__is_demo=False,
    )


@shared_task(name="triage.dispatch_active_mailboxes")  # type: ignore[untyped-decorator]
def dispatch_active_mailboxes() -> int:
    """Queue only explicitly activated boxes; installation defaults to no provider calls."""
    if not settings.TRIAGE_EMAIL_POLL_ENABLED:
        return 0
    now = timezone.now()
    ids = (
        _eligible()
        .filter(Q(poll_lease_until__isnull=True) | Q(poll_lease_until__lt=now))
        .filter(Q(poll_retry_after__isnull=True) | Q(poll_retry_after__lte=now))
        .order_by("last_polled_at", "pk")
        .values_list("pk", flat=True)[:1_000]
    )
    queued = 0
    for mailbox_id in ids:
        poll_activated_mailbox.delay(str(mailbox_id))
        queued += 1
    return queued


@shared_task(name="triage.poll_activated_mailbox")  # type: ignore[untyped-decorator]
def poll_activated_mailbox(mailbox_id: str) -> dict[str, object]:
    """Use a recoverable DB lease; provider checkpoints belong to the reader."""
    if not settings.TRIAGE_EMAIL_POLL_ENABLED:
        return {"state": "disabled"}
    try:
        parsed_id = uuid.UUID(mailbox_id)
    except (ValueError, AttributeError):
        return {"state": "invalid_id"}
    now = timezone.now()
    token = uuid.uuid4()
    lease_seconds = max(600, int(settings.CELERY_TASK_TIME_LIMIT) + 60)
    acquired = (
        _eligible()
        .filter(pk=parsed_id)
        .filter(Q(poll_lease_until__isnull=True) | Q(poll_lease_until__lt=now))
        .filter(Q(poll_retry_after__isnull=True) | Q(poll_retry_after__lte=now))
        .update(poll_lease_until=now + timedelta(seconds=lease_seconds), poll_lease_token=token)
    )
    if not acquired:
        return {"state": "inactive_or_busy"}
    try:
        mailbox = Mailbox.objects.select_related("organization", "oauth_app").get(pk=parsed_id)
        if (
            not mailbox.active
            or mailbox.status != Mailbox.Status.ACTIVE
            or mailbox.since is None
            or not mailbox.organization.is_active
            or mailbox.organization.is_demo
        ):
            return {"state": "inactive_or_busy"}
        if mailbox.provider == Mailbox.Provider.IMAP:
            result = poll_imap_mailbox(mailbox=mailbox, max_messages=10)
            count = result.attachments_created
        elif mailbox.provider == Mailbox.Provider.MS365_GRAPH:
            result = poll_graph_mailbox(mailbox=mailbox, max_pages=3)
            count = result.attachments_created
        elif mailbox.provider == Mailbox.Provider.GMAIL_API:
            result = poll_gmail_mailbox(mailbox=mailbox, max_pages=3)
            count = result.attachments_created
        else:
            mailbox.status = Mailbox.Status.ERROR
            mailbox.last_error = "Provedor de caixa indisponível."
            mailbox.save(update_fields=["status", "last_error", "updated_at"])
            return {"state": "unsupported"}
        return {"state": "completed", "attachments_created": count}
    except (
        GmailMailboxError,
        GraphMailboxError,
        MailboxIMAPError,
        MailboxOAuthError,
    ):
        # Reader has recorded the actionable error and whether it is retryable.
        return {"state": "poll_failed"}
    except ValidationError:
        mark_failure(
            mailbox,
            "O anexo não passou pela validação de entrada. Revise esta caixa.",
            transient=False,
        )
        return {"state": "poll_failed"}
    except Exception:  # Worker boundary must not log provider data/credentials.
        # Readers record known operational errors; unexpected errors get a safe message.
        Mailbox.objects.filter(pk=parsed_id, status=Mailbox.Status.ACTIVE).update(
            status=Mailbox.Status.ERROR,
            last_error="Falha inesperada na leitura. Solicite suporte para esta caixa.",
        )
        return {"state": "error"}
    finally:
        Mailbox.objects.filter(pk=parsed_id, poll_lease_token=token).update(
            poll_lease_until=None, poll_lease_token=None
        )
