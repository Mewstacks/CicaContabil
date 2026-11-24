"""Run the engine again over pending items of one office (never over a person's work).

Used when the office raises its ``engine_version`` and when a learned link just became active.
An item a person already corrected or decided is left alone; for the rest only values the
engine itself had set (the evidence names them) are replaced.
"""

from __future__ import annotations

from uuid import UUID

from django.db import transaction

from apps.organizations.models import Organization
from apps.triage.extraction import suggest
from apps.triage.intake_policy import engine_version_for
from apps.triage.models import TriageEvent, TriageItem, TriagePolicy
from apps.triage.transitions import TriageStatus

RECLASSIFY_LIMIT = 500


def touched_by_a_person(item: TriageItem) -> bool:
    return (
        item.reviewed_by_id is not None
        or item.events.filter(actor__isnull=False, note__startswith="Corrigido").exists()
    )


def _engine_made(item: TriageItem, label: str, current: str) -> bool:
    return str((item.ai_fields.get(label) or {}).get("valor", "")) == current and bool(current)


def reclassify_item(item: TriageItem) -> bool:
    """Apply a fresh suggestion to one pending, untouched item. True when it changed."""

    with transaction.atomic():
        item = (
            TriageItem.objects.select_for_update(of=("self",))
            .select_related("blob", "organization", "company", "document_type")
            .get(pk=item.pk)
        )
        if item.status != TriageStatus.AWAITING_REVIEW or touched_by_a_person(item):
            return False
        before = (item.company_id, item.document_type_id, item.period_label)
        result = suggest(item)
        if item.company_id is None or _engine_made(
            item, "Empresa", item.company.name if item.company else ""
        ):
            item.company = result.company
        if item.document_type_id is None or _engine_made(
            item, "Tipo", item.document_type.label if item.document_type else ""
        ):
            item.document_type = result.document_type
        if not item.period_label or _engine_made(item, "Período", item.period_label):
            item.period_label = result.period_label
        if not item.counterparty_token:
            item.counterparty_token = result.counterparty_token
        changed = before != (item.company_id, item.document_type_id, item.period_label)
        if changed or not item.final_name:
            item.final_name = result.final_name or item.final_name
        item.ai_fields = result.evidence
        item.scores = result.scores
        item.engine_version = engine_version_for(item.organization)
        item.save()
        TriageEvent.objects.create(
            organization=item.organization,
            triage_item=item,
            from_status=item.status,
            to_status=item.status,
            note="Reclassificado pelo motor" + (" (mudou)" if changed else ""),
        )
    return changed


def reclassify_pending(
    organization: Organization, *, exclude: UUID | None = None, limit: int = RECLASSIFY_LIMIT
) -> int:
    """Reclassify this office's pending items; returns how many changed."""

    pending = TriageItem.objects.filter(
        organization=organization, status=TriageStatus.AWAITING_REVIEW, reviewed_by__isnull=True
    ).order_by("created_at")
    if exclude is not None:
        pending = pending.exclude(pk=exclude)
    changed = 0
    for item in pending[:limit]:
        changed += int(reclassify_item(item))
    return changed


def bump_engine_version(organization: Organization) -> int:
    """Raise the office's engine version and reclassify what is pending. Returns the version."""

    policy, _ = TriagePolicy.objects.get_or_create(organization=organization)
    policy.engine_version += 1
    policy.save(update_fields=["engine_version", "updated_at"])
    reclassify_pending(organization)
    return policy.engine_version
