"""Opt-in auto-approval: only what the engine accepted, with the reason recorded.

Default is review everything. An office that switched ``TriagePolicy.auto_approve`` on still
sends to a person: the first ``auto_warmup`` documents (counted from human reviews), anything
the engine did not accept in full (company with threshold and margin, type, period, name,
counterparty when the type needs one), and a deterministic audit sample of one in
``auto_sample_every``. Auto-approval stops at *pronto para arquivar*; archiving stays a step.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from apps.triage.intake_policy import policy_for
from apps.triage.models import DocumentType, TriageItem
from apps.triage.transitions import TriageStatus


@dataclass(frozen=True)
class AutoVerdict:
    decision: str = ""  # "" (person decides) | "auto" | "sampled"
    reason: str = ""


def is_sampled(item_id: object, every: int) -> bool:
    """Deterministic one-in-``every`` sample keyed by the item id (1 = every item)."""

    if every <= 1:
        return True
    return int(hashlib.sha256(str(item_id).encode()).hexdigest()[:8], 16) % every == 0


def human_reviews(item: TriageItem) -> int:
    return (
        TriageItem.objects.filter(
            organization_id=item.organization_id,
            status=TriageStatus.ARCHIVED,
            reviewed_by__isnull=False,
        )
        .exclude(auto_decision="auto")
        .count()
    )


def evaluate(item: TriageItem, identification: object, scores: dict[str, object]) -> AutoVerdict:
    """The verdict for an item whose suggestion is already applied to its fields."""

    from apps.triage.identification import Identification

    policy = policy_for(item.organization)
    if not policy.auto_approve or not isinstance(identification, Identification):
        return AutoVerdict()
    company, document_type = item.company, item.document_type
    type_scores = scores.get("type")
    accepted_type = isinstance(type_scores, dict) and type_scores.get("status") == "accepted"
    if (
        identification.status != "accepted"
        or identification.company is None
        or company is None
        or company.pk != identification.company.pk
        or document_type is None
        or not accepted_type
        or not item.period_label
        or not item.final_name
        or item.duplicate_of_id is not None
        or (
            document_type.counterparty_kind != DocumentType.CounterpartyKind.NONE
            and not item.counterparty_token
        )
        or human_reviews(item) < policy.auto_warmup
    ):
        return AutoVerdict()
    why = (
        f"Empresa {company.name} ({'; '.join(s.text for s in identification.signals[:3])}; "
        f"{identification.score} pontos, margem {identification.margin}); "
        f"Tipo {document_type.label}; Período {item.period_label}"
    )
    if is_sampled(item.pk, policy.auto_sample_every):
        return AutoVerdict("sampled", why)
    return AutoVerdict("auto", why)
