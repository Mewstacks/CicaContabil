"""Keep guide attempts separate without changing authorization or pricing rules."""

from collections.abc import Iterable

from django.db import transaction

from apps.hub.models import FiscalGuide, FiscalGuideAttemptEvent


def record_guide_attempt(guide: FiscalGuide) -> None:
    """Copy only an observed state, including the available state of legacy attempts."""
    if not guide.issue_attempt:
        return
    queued = FiscalGuideAttemptEvent.objects.filter(
        organization_id=guide.organization_id,
        guide=guide,
        attempt=guide.issue_attempt,
        status=FiscalGuide.Status.QUEUED,
    ).first()
    request_snapshot = (
        queued.request_snapshot
        if queued
        else {
            "snapshot_source": (
                "queued_request" if guide.status == FiscalGuide.Status.QUEUED else "current_record"
            ),
            "company_id": str(guide.company_id),
            "reference": guide.reference,
            "kind": guide.kind,
            "competence": guide.competence,
            "due_on": guide.due_on.isoformat(),
            "amount_cents": guide.amount_cents,
            "service_key": guide.integra_service_key,
            "simulated": guide.organization.is_demo,
        }
    )
    FiscalGuideAttemptEvent.objects.get_or_create(
        organization_id=guide.organization_id,
        guide=guide,
        attempt=guide.issue_attempt,
        status=guide.status,
        defaults={
            "request_snapshot": request_snapshot,
            "requested_by_reference": str(guide.issue_requested_by_id or ""),
            "requested_at": guide.issue_requested_at,
            "issued_at": guide.issued_at,
            "consumption_reference": f"fiscal-guide:{guide.pk}:{guide.issue_attempt}",
            "provider_request_id": guide.provider_request_id,
            "provider_payload": guide.provider_payload,
            "error_code": guide.error_code,
            "error_message": guide.error_message,
        },
    )


@transaction.atomic
def save_guide_attempt(guide: FiscalGuide, *, update_fields: Iterable[str]) -> None:
    """Persist state and its evidence together, never as a best-effort UI projection."""
    guide.save(update_fields=update_fields)
    record_guide_attempt(guide)
