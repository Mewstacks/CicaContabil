"""Baixa no checklist do escritório (``OperationalActivity``) a partir de uma conferência.

A atividade é a do mesmo escritório, empresa, código e competência do documento; nunca
outra. O documento lido vira evidência (``source`` na baixa automática, ``human`` quando uma
pessoa decide). As regras de conclusão da atividade continuam valendo: se o item exige outra
prova, ele recebe a evidência e fica aberto, em vez de ser fechado por cima da regra.
"""

from __future__ import annotations

from django.utils import timezone

from apps.closing.models import ClosingConference
from apps.hub.models import OperationalActivity, OperationalActivityEvent, OperationalEvidence
from apps.hub.operations import completion_requirements

AUTOMATIC_ACTOR_LABEL = "Leitura automática do Fechamento"


def find_activity(conference: ClosingConference) -> OperationalActivity | None:
    document = conference.document
    layout = conference.layout
    if (
        layout is None
        or not layout.activity_code
        or document.company_id is None
        or document.competence is None
    ):
        return None
    return (
        OperationalActivity.objects.select_for_update()
        .filter(
            organization_id=document.organization_id,
            company_id=document.company_id,
            code=layout.activity_code,
            competence=document.competence,
        )
        .order_by("-template_version", "-created_at")
        .first()
    )


def _event(activity: OperationalActivity, kind: str, summary: str, actor: object | None) -> None:
    OperationalActivityEvent.objects.create(
        organization_id=activity.organization_id,
        activity=activity,
        event_type=kind,
        summary=summary[:500],
        actor=actor,  # type: ignore[misc]
    )


def _summary(conference: ClosingConference) -> str:
    document = conference.document
    base = f"{document.original_name}: {conference.get_outcome_display().lower()}"
    if conference.reference_amount is not None and conference.declared_amount is not None:
        base += (
            f" (documento R$ {conference.declared_amount:.2f}, "
            f"referência R$ {conference.reference_amount:.2f})"
        )
    return base


def clear(
    conference: ClosingConference, *, actor: object | None = None, human: bool = False
) -> str:
    """Grava a evidência e, se as regras do item permitem, conclui. Devolve o estado."""
    Checklist = ClosingConference.Checklist
    activity = find_activity(conference)
    if activity is None:
        _store(conference, None, Checklist.NO_ITEM)
        return Checklist.NO_ITEM
    if activity.work_status in {
        OperationalActivity.WorkStatus.COMPLETED,
        OperationalActivity.WorkStatus.WAIVED,
    }:
        _store(conference, activity, Checklist.DONE)
        return Checklist.DONE
    now = timezone.now()
    reference = f"closing:{conference.document_id}:{conference.document.content_hash[:16]}"
    if human:
        reason = conference.resolution_reason
        OperationalEvidence.objects.get_or_create(  # type: ignore[misc]
            organization_id=activity.organization_id,
            activity=activity,
            kind=OperationalActivity.EvidenceKind.HUMAN,
            reference=f"{reference}:human",
            defaults={
                "observed_at": now,
                "summary": f"{_summary(conference)}. Decisão humana: {reason}"[:500],
                "recorded_by": actor,
            },
        )
    else:
        # Documento lido e conferido pelo sistema: é fonte, não confirmação humana.
        kind = (
            OperationalActivity.EvidenceKind.SOURCE
            if activity.evidence_requirement != "human"
            else OperationalActivity.EvidenceKind.DOCUMENT
        )
        OperationalEvidence.objects.get_or_create(
            organization_id=activity.organization_id,
            activity=activity,
            kind=kind,
            reference=reference,
            defaults={"observed_at": now, "summary": _summary(conference)[:500]},
        )
        if activity.freshness != OperationalActivity.Freshness.CURRENT:
            activity.freshness = OperationalActivity.Freshness.CURRENT
            activity.save(update_fields=["freshness", "updated_at"])
    activity.refresh_from_db()
    missing = completion_requirements(activity)
    if missing:
        _event(
            activity, "closing_evidence", f"Evidência do Fechamento: {_summary(conference)}", actor
        )
        _store(conference, activity, Checklist.OPEN)
        return Checklist.OPEN
    activity.work_status = OperationalActivity.WorkStatus.COMPLETED
    activity.completed_at = now
    activity.completed_by = actor if human else None  # type: ignore[assignment]
    activity.blocked_reason = ""
    activity.save(
        update_fields=[
            "work_status",
            "completed_at",
            "completed_by",
            "blocked_reason",
            "updated_at",
        ]
    )
    who = "Baixa confirmada por pessoa" if human else AUTOMATIC_ACTOR_LABEL
    _event(activity, "closing_cleared", f"{who}: {_summary(conference)}", actor if human else None)
    _store(conference, activity, Checklist.DONE)
    return Checklist.DONE


def block(conference: ClosingConference, reason: str) -> str:
    """Impede o item: a divergência espera uma pessoa e não pode parecer pendência comum."""
    Checklist = ClosingConference.Checklist
    activity = find_activity(conference)
    if activity is None:
        _store(conference, None, Checklist.NO_ITEM)
        return Checklist.NO_ITEM
    if activity.work_status in {
        OperationalActivity.WorkStatus.COMPLETED,
        OperationalActivity.WorkStatus.WAIVED,
    }:
        _store(conference, activity, Checklist.DONE)
        return Checklist.DONE
    activity.work_status = OperationalActivity.WorkStatus.BLOCKED
    activity.blocked_reason = reason[:500]
    activity.save(update_fields=["work_status", "blocked_reason", "updated_at"])
    _event(activity, "closing_blocked", reason, None)
    _store(conference, activity, Checklist.BLOCKED)
    return Checklist.BLOCKED


def _store(conference: ClosingConference, activity: OperationalActivity | None, state: str) -> None:
    conference.activity = activity
    conference.checklist = state
    conference.save(update_fields=["activity", "checklist", "updated_at"])
