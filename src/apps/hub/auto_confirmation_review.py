"""D-390: owner review of the D-388 automatic confirmations, measured for D-73."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db import transaction

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.hub.models import ClientCompany, MovementReconciliation, ReconciliationSourceFile
from apps.organizations.models import Membership

REVIEW_ACTION = "hub.reconciliation.auto_confirmation_review"
DECLARATION = "Conferi cada confirmação automática deste extrato e desfiz as incorretas."
MINIMUM_REVIEWED = 200
THRESHOLD_PERCENT = 95


def automatic_confirmations(source: ReconciliationSourceFile) -> list[MovementReconciliation]:
    """Kept (confirmed) and undone D-388 allocations of one bank statement."""
    return list(
        MovementReconciliation.objects.filter(
            organization_id=source.organization_id,
            movement__source_file=source,
            movement__company_id=source.company_id,
            evidence__automatic=True,
            state__in=[
                MovementReconciliation.State.CONFIRMED,
                MovementReconciliation.State.UNDONE,
            ],
        ).order_by("id")
    )


def _items(rows: list[MovementReconciliation]) -> list[dict[str, str]]:
    return [
        {
            "reconciliation_id": str(row.pk),
            "movement_id": str(row.movement_id),
            "entry_id": str(row.entry_id),
            "state": row.state,
        }
        for row in rows
    ]


def _fingerprint(source: ReconciliationSourceFile, items: list[dict[str, str]]) -> str:
    payload = {"source_id": str(source.pk), "source_sha256": source.content_hash, "items": items}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(encoded.encode()).hexdigest()


def latest_review(source: ReconciliationSourceFile) -> AuditEvent | None:
    return (
        AuditEvent.objects.filter(
            organization_id=source.organization_id,
            action=REVIEW_ACTION,
            target_type="hub.reconciliationsourcefile",
            target_id=str(source.pk),
        )
        .order_by("-occurred_at", "-id")
        .first()
    )


def review_summary(source: ReconciliationSourceFile) -> dict[str, Any]:
    rows = automatic_confirmations(source)
    kept = sum(row.state == MovementReconciliation.State.CONFIRMED for row in rows)
    review = latest_review(source)
    current = review is not None and review.metadata.get("fingerprint") == _fingerprint(
        source, _items(rows)
    )
    return {
        "total": len(rows),
        "kept": kept,
        "undone": len(rows) - kept,
        "review": review,
        "review_is_current": current,
    }


def is_owner(organization_id: Any, user: Any) -> bool:
    return Membership.objects.filter(
        organization_id=organization_id,
        user=user,
        is_active=True,
        user__is_active=True,
        role=Membership.Role.OWNER,
    ).exists()


@transaction.atomic
def record_owner_review(
    *,
    source: ReconciliationSourceFile,
    actor: Any,
    declaration: str,
    expected_total: int,
    request: Any = None,
) -> tuple[AuditEvent, bool]:
    """Freeze, per allocation, what the owner kept (correct) or undid (wrong)."""
    ClientCompany.objects.select_for_update().get(
        pk=source.company_id, organization_id=source.organization_id
    )
    if not is_owner(source.organization_id, actor):
        raise PermissionDenied("Somente a proprietária do escritório registra esta revisão.")
    if declaration != DECLARATION:
        raise ValueError("Marque a declaração de que conferiu todas as confirmações.")
    rows = automatic_confirmations(source)
    if not rows:
        raise ValueError("Este extrato não tem confirmações automáticas para revisar.")
    if len(rows) != expected_total:
        raise ValueError("As confirmações mudaram desde que a página foi aberta; revise de novo.")
    items = _items(rows)
    fingerprint = _fingerprint(source, items)
    prior = latest_review(source)
    if prior is not None and prior.metadata.get("fingerprint") == fingerprint:
        return prior, False
    kept = sum(item["state"] == MovementReconciliation.State.CONFIRMED for item in items)
    event = record_event(
        action=REVIEW_ACTION,
        actor=actor,
        organization=source.organization,
        target=source,
        request=request,
        metadata={
            "decision": "D-390",
            "source_id": str(source.pk),
            "source_sha256": source.content_hash,
            "company_id": str(source.company_id),
            "financial_account_id": str(source.financial_account_id),
            "declaration": DECLARATION,
            "items": items,
            "reviewed": len(items),
            "kept": kept,
            "undone": len(items) - kept,
            "fingerprint": fingerprint,
            "release_accepted": False,
        },
    )
    return event, True


def acceptance_report(organization_id: Any) -> dict[str, Any]:
    """Read-only D-73 measurement over the latest owner review of each statement."""
    latest: dict[str, AuditEvent] = {}
    for event in AuditEvent.objects.filter(
        organization_id=organization_id, action=REVIEW_ACTION
    ).order_by("occurred_at", "id"):
        latest[event.target_id] = event
    reviewed = sum(int(event.metadata["reviewed"]) for event in latest.values())
    kept = sum(int(event.metadata["kept"]) for event in latest.values())
    return {
        "decision": "D-390",
        "statements_reviewed": len(latest),
        "reviewed": reviewed,
        "kept": kept,
        "undone": reviewed - kept,
        "precision_percent": round(100 * kept / reviewed, 4) if reviewed else None,
        "missing_to_minimum": max(0, MINIMUM_REVIEWED - reviewed),
        "threshold_passed": reviewed >= MINIMUM_REVIEWED
        and kept * 100 >= reviewed * THRESHOLD_PERCENT,
        "reviews": [
            {
                "source_id": event.target_id,
                "company_id": event.metadata.get("company_id"),
                "reviewed": event.metadata["reviewed"],
                "kept": event.metadata["kept"],
                "reviewed_at": event.occurred_at.isoformat(),
                "reviewer_id": str(event.actor_id) if event.actor_id else None,
            }
            for event in latest.values()
        ],
        "release_accepted": False,
        "remaining_gates": [
            "classification_sample_or_waiver",
            "integrity_and_isolation",
            "destination_import",
            "owner_release_signoff",
        ],
    }
