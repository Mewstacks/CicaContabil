"""Opt-in periodic email intake, one leased worker per authorized mailbox."""

from __future__ import annotations

import uuid
from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import F, Q, QuerySet
from django.utils import timezone

from apps.triage.gmail_poll import GmailMailboxError, poll_gmail_mailbox
from apps.triage.graph_poll import GraphMailboxError, poll_graph_mailbox
from apps.triage.imap import MailboxIMAPError
from apps.triage.imap_poll import poll_imap_mailbox
from apps.triage.models import Mailbox
from apps.triage.oauth import MailboxOAuthError
from apps.triage.poll_state import mark_failure


def _eligible() -> QuerySet[Mailbox]:
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


def _scanner_configured() -> bool:
    return bool(settings.TRIAGE_CLAMD_SOCKET or settings.TRIAGE_CLAMD_PORT)


# Automatic runs per item (the first dispatch included). Past it only Reprocessar resumes.
MAX_PIPELINE_ATTEMPTS = 3


@shared_task(name="triage.process_item")  # type: ignore[untyped-decorator]
def process_triage_item(item_id: str) -> str:
    """Scan a quarantined item, then extract suggestions. Each step is idempotent."""
    from apps.triage.extraction import extract_item
    from apps.triage.models import TriageItem
    from apps.triage.security import scan_quarantined_item
    from apps.triage.services import retry_failed_extraction
    from apps.triage.transitions import TriageStatus

    item = TriageItem.objects.filter(pk=item_id).first()
    if item is None:
        return "missing"
    runnable = {TriageStatus.QUARANTINED, TriageStatus.AWAITING_EXTRACTION, TriageStatus.FAILED}
    if item.status not in runnable:
        return str(item.status)
    TriageItem.objects.filter(pk=item.pk).update(pipeline_attempts=F("pipeline_attempts") + 1)
    if item.status == TriageStatus.FAILED:
        item = retry_failed_extraction(item=item)
    if item.status == TriageStatus.QUARANTINED:
        try:
            scan_quarantined_item(item=item)
        except ValidationError:
            return "scan_refused"
        item.refresh_from_db(fields=["status"])
    if item.status == TriageStatus.AWAITING_EXTRACTION:
        item = extract_item(item_id=item.pk)
    return str(item.status)


@shared_task(name="triage.recover_pipeline")  # type: ignore[untyped-decorator]
def recover_triage_pipeline() -> int:
    """Resume items a crashed worker or an absent scanner left behind."""
    from apps.triage.models import TriageItem
    from apps.triage.transitions import TriageStatus

    # Extraction runs in one transaction, so a crash never leaves an item in em_extracao.
    stale = timezone.now() - timedelta(minutes=10)
    waiting = Q(status=TriageStatus.AWAITING_EXTRACTION)
    if _scanner_configured():
        # Without a configured engine a retry only repeats the same failure event.
        waiting |= Q(status=TriageStatus.QUARANTINED, safety_scan__isnull=True) | Q(
            status=TriageStatus.QUARANTINED,
            safety_scan__verdict="error",
            safety_scan__scanned_at__lt=stale,
        )
    else:
        waiting |= Q(status=TriageStatus.QUARANTINED, safety_scan__isnull=True)
    # A failed extraction gets another automatic chance once it has rested, up to the cap.
    waiting |= Q(status=TriageStatus.FAILED, updated_at__lt=stale)
    ids = list(
        TriageItem.objects.filter(
            waiting,
            organization__is_demo=False,
            pipeline_attempts__lt=MAX_PIPELINE_ATTEMPTS,
        )
        .order_by("created_at")
        .values_list("pk", flat=True)[:200]
    )
    for item_id in ids:
        process_triage_item.delay(str(item_id))
    return len(ids)


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
            count = poll_imap_mailbox(mailbox=mailbox, max_messages=10).attachments_created
        elif mailbox.provider == Mailbox.Provider.MS365_GRAPH:
            count = poll_graph_mailbox(mailbox=mailbox, max_pages=3).attachments_created
        elif mailbox.provider == Mailbox.Provider.GMAIL_API:
            count = poll_gmail_mailbox(mailbox=mailbox, max_pages=3).attachments_created
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


@shared_task(name="triage.ocr_item")  # type: ignore[untyped-decorator]
def ocr_triage_item(item_id: str) -> str:
    """OCR one file on the dedicated queue, then resume extraction. Idempotent."""
    from apps.triage import ocr
    from apps.triage.extraction import _blob_bytes, extract_item
    from apps.triage.models import TriageEvent, TriageItem, TriageOcrUsage
    from apps.triage.readers import suffix_of
    from apps.triage.transitions import TriageStatus

    item = TriageItem.objects.select_related("blob", "organization").filter(pk=item_id).first()
    if (
        item is None
        or item.status != TriageStatus.AWAITING_EXTRACTION
        or item.ocr_state != "queued"
    ):
        return "skipped"
    reservation = TriageOcrUsage.objects.filter(
        organization=item.organization, triage_item=item
    ).first()
    approved = reservation.pages if reservation is not None else 0
    state, text, pages, note = "failed", "", 0, "OCR falhou; seguindo sem ele"
    engine = ocr.get_engine()
    # Switches may have changed while queued; the budget was reserved when it was queued.
    still_allowed = not ocr.ocr_blocker(item.organization, 0)
    if engine is not None and approved and still_allowed and not item.organization.is_demo:
        try:
            text, pages = ocr.run_ocr(
                _blob_bytes(item), suffix_of(item.original_name), engine, approved
            )
            state, note = "done", f"OCR concluído: {pages} página{'s' if pages != 1 else ''}"
        except Exception:  # an OCR failure must never strand the file
            text, pages = "", 0
    TriageItem.objects.filter(pk=item.pk, ocr_state="queued").update(
        ocr_state=state, ocr_text=text
    )
    if reservation is not None:
        if pages:
            TriageOcrUsage.objects.filter(pk=reservation.pk).update(pages=pages)
        else:
            reservation.delete()  # nothing was read: give the pages back
    TriageEvent.objects.create(
        organization=item.organization,
        triage_item=item,
        from_status=item.status,
        to_status=item.status,
        note=note,
    )
    return str(extract_item(item_id=item.pk).status)
