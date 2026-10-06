"""Deterministic rules for the CICA operational activity centre."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.fiscal_calendar.models import TaxDeadlineRule
from apps.fiscal_calendar.services import (
    BusinessCalendar,
    CalendarIncomplete,
    add_months,
    approved_rule,
    day_in_month,
    internal_before,
    rule_due_date,
)
from apps.hub.controlplane import company_queryset_for_membership
from apps.hub.models import (
    ActivityTemplate,
    ActivityTemplateAssignment,
    CompanyAreaResponsible,
    DataSource,
    OperationalActivity,
    OperationalActivityEvent,
    OperationalEvidence,
    OperationalSourceObservation,
)
from apps.organizations.models import Membership

SOURCE_CAPABILITY_ACTIVITY_PROCESSING = "activity_processing_status"
SOURCE_CAPABILITY_ACTIVITY_OBLIGATION = "activity_obligation_status"


@dataclass(frozen=True)
class ClosingAssessment:
    """Deterministic aggregate for a company, area and competence without hiding its cause."""

    status: str
    total_activities: int
    completed_activities: int
    pending_activities: int
    blocked_activities: int
    unavailable_sources: int
    missing_requirements: tuple[tuple[str, tuple[str, ...]], ...] = ()


def completion_requirements(activity: OperationalActivity) -> tuple[str, ...]:
    """Revalidate the proof instead of trusting a persisted completed flag."""
    if activity.source_reform_alert_id:
        from apps.hub.reform_activities import reform_version

        alert = activity.source_reform_alert
        assert alert is not None
        received = activity.events.filter(event_type="reform_received").first()
        if activity.reform_version != reform_version(alert):
            return ("Atualize a atividade com a versão atual da publicação do Radar.",)
        if received is None or not activity.evidence_items.filter(
            organization_id=activity.organization_id, kind="human",
            recorded_by__isnull=False, observed_at__gte=received.occurred_at,
            created_at__gte=received.occurred_at,
        ).exists():
            return ("Registre análise humana após a última atualização da publicação.",)
    if activity.source_dte_message_id:
        from apps.hub.models import DteMessageAccess

        access = DteMessageAccess.objects.filter(
            organization_id=activity.organization_id,
            message_id=activity.source_dte_message_id,
        ).first()
        if access and access.status in {"reading", "unknown"}:
            return ("Confirme o resultado da abertura DTE antes de concluir a análise.",)
        if access and access.status == "opened":
            if not access.opened_at or not access.provider_payload:
                return ("Confirme o comprovante e o teor da abertura DTE.",)
            if not activity.evidence_items.filter(
                organization_id=activity.organization_id,
                kind="human",
                recorded_by__isnull=False,
                observed_at__gte=access.opened_at,
                created_at__gte=access.opened_at,
            ).exists():
                return ("Registre análise humana após a abertura do teor DTE.",)
    if activity.source_payroll_snapshot_id:
        received = activity.events.filter(event_type="payroll_received").first()
        if (
            received is None
            or not activity.evidence_items.filter(
                organization_id=activity.organization_id,
                kind="human",
                recorded_by__isnull=False,
                observed_at__gte=received.occurred_at,
                created_at__gte=received.occurred_at,
            ).exists()
        ):
            return (
                "Confira os dados da folha e registre confirmação humana "
                "após o último recebimento.",
            )
    if activity.source_reconciliation_file_id:
        from apps.hub.reconciliation_activities import reconciliation_file_pending

        source = activity.source_reconciliation_file
        assert source is not None
        pending, reason = reconciliation_file_pending(source)
        if pending:
            return (reason,)
    review = activity.source_nfse_review
    if review is not None and review.status != "resolved":
        return ("Conclua a revisão no módulo NFS-e antes de encerrar esta atividade.",)
    triage_item = activity.source_triage_item
    if triage_item is not None and not (
        triage_item.status == "arquivado"
        and triage_item.archived_at
        and triage_item.destination_path
        and triage_item.content_hash
        and triage_item.destination_hash == triage_item.content_hash
    ):
        return ("Confirme o arquivamento no módulo Triagem antes de encerrar esta atividade.",)
    kinds = {
        evidence.kind
        for evidence in activity.evidence_items.all()
        if evidence.organization_id == activity.organization_id
    }
    if activity.work_status == OperationalActivity.WorkStatus.WAIVED:
        if (
            activity.waived_reason.strip()
            and activity.completed_by_id
            and activity.completed_at
            and kinds
        ):
            return ()
        return ("A dispensa exige motivo, responsável, data e evidência.",)

    missing: list[str] = []
    if activity.evidence_requirement == "source" and "source" not in kinds:
        missing.append("Esta atividade exige evidência da fonte integrada.")
    elif activity.evidence_requirement == "human" and "human" not in kinds:
        missing.append("Esta atividade exige confirmação humana registrada.")
    elif activity.evidence_requirement == "source_or_human" and not kinds.intersection(
        {"source", "human"}
    ):
        missing.append("Registre uma evidência da fonte ou confirmação humana antes de concluir.")
    if activity.freshness in {
        OperationalActivity.Freshness.UNAVAILABLE,
        OperationalActivity.Freshness.STALE,
    } or (
        activity.evidence_requirement == "source"
        and activity.freshness != OperationalActivity.Freshness.CURRENT
    ):
        missing.append("Atualize a fonte antes de comprovar a conclusão.")
    if (
        activity.requires_processing_closed
        and activity.processing_status != OperationalActivity.ProcessingStatus.CLOSED
    ):
        missing.append("O processamento aplicável ainda não está confirmado como fechado.")
    if (
        activity.requires_accepted_obligation
        and activity.obligation_status != OperationalActivity.ObligationStatus.ACCEPTED
    ):
        missing.append("A obrigação aplicável ainda não está aceita.")
    return tuple(missing)


def assess_closing(activities: list[OperationalActivity]) -> ClosingAssessment:
    """Summarize activity states; an unavailable source never means no pending work."""

    total = len(activities)
    requirements = [(activity, completion_requirements(activity)) for activity in activities]
    completed = sum(
        activity.work_status
        in {OperationalActivity.WorkStatus.COMPLETED, OperationalActivity.WorkStatus.WAIVED}
        and not missing
        for activity, missing in requirements
    )
    blocked = sum(
        activity.work_status == OperationalActivity.WorkStatus.BLOCKED for activity in activities
    )
    unavailable = sum(
        activity.work_status != OperationalActivity.WorkStatus.WAIVED
        and activity.freshness
        in {OperationalActivity.Freshness.UNAVAILABLE, OperationalActivity.Freshness.STALE}
        for activity in activities
    )
    pending = total - completed
    if not total:
        status = "not_started"
    elif blocked:
        status = "blocked"
    elif any(
        activity.work_status != OperationalActivity.WorkStatus.WAIVED
        and (
            activity.processing_status == OperationalActivity.ProcessingStatus.REOPENED
            or activity.obligation_status == OperationalActivity.ObligationStatus.REJECTED
        )
        for activity in activities
    ):
        status = "reopened"
    elif unavailable:
        status = "unverifiable"
    elif not pending:
        status = "completed"
    else:
        status = "open"
    return ClosingAssessment(
        status=status,
        total_activities=total,
        completed_activities=completed,
        pending_activities=pending,
        blocked_activities=blocked,
        unavailable_sources=unavailable,
        missing_requirements=tuple(
            (str(activity.pk), missing) for activity, missing in requirements if missing
        ),
    )


def can_operate_activity(
    *, membership: Membership | None, activity: OperationalActivity, actor: User | None = None
) -> bool:
    """Use the live membership and portfolio before authorizing an activity write."""

    if membership is None:
        return False
    current = (
        Membership.objects.select_related("organization", "user")
        .filter(
            pk=membership.pk,
            organization_id=activity.organization_id,
            is_active=True,
            user__is_active=True,
        )
        .first()
    )
    if current is None or (actor is not None and current.user_id != actor.pk):
        return False
    if current.role in {Membership.Role.AUDITOR, Membership.Role.BILLING}:
        return False
    return company_queryset_for_membership(current).filter(pk=activity.company_id).exists()


def activity_is_overdue(activity: OperationalActivity, *, today: date | None = None) -> bool:
    reference = today or timezone.localdate()
    due_on = activity.internal_due_on or activity.legal_due_on
    return bool(
        due_on
        and due_on < reference
        and activity.work_status
        not in {OperationalActivity.WorkStatus.COMPLETED, OperationalActivity.WorkStatus.WAIVED}
    )


@transaction.atomic
def assign_activity(
    *,
    activity: OperationalActivity,
    membership: Membership,
    actor: User,
    assignee_id: str,
    expected_assignee_id: str,
    reason: str,
    request: object,
) -> OperationalActivity:
    current_membership = (
        Membership.objects.filter(
            pk=membership.pk,
            user_id=actor.pk,
            organization_id=activity.organization_id,
            is_active=True,
            user__is_active=True,
        )
        .only("role")
        .first()
    )
    if (
        current_membership is None
        or current_membership.role not in {Membership.Role.OWNER, Membership.Role.ADMIN}
        or not can_operate_activity(membership=membership, activity=activity, actor=actor)
    ):
        raise PermissionDenied("Somente a administracao pode atribuir atividades da carteira.")
    locked = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if locked.work_status in {
        OperationalActivity.WorkStatus.COMPLETED,
        OperationalActivity.WorkStatus.WAIVED,
    }:
        raise ValidationError("Atividade encerrada preserva seu responsável histórico.")
    previous = str(locked.assigned_to_id or "")
    if previous != expected_assignee_id:
        raise ValidationError("O responsável mudou. Recarregue a atividade antes de redistribuir.")
    reason = reason.strip()
    if not reason or len(reason) > 500:
        raise ValidationError("Informe um motivo com até 500 caracteres.")
    assignee = None
    if assignee_id:
        candidate = (
            Membership.objects.select_related("user", "organization")
            .filter(
                organization_id=locked.organization_id,
                user_id=assignee_id,
                is_active=True,
                user__is_active=True,
            )
            .first()
        )
        if candidate is None or not can_operate_activity(membership=candidate, activity=locked):
            raise ValidationError(
                "O responsável precisa ter perfil operacional e acesso ativo à empresa."
            )
        assignee = candidate.user
    if previous == str(assignee.pk if assignee else ""):
        return locked
    # The history is read by people: it names them. Identifiers stay in the audit metadata.
    previous_name = locked.assigned_to.display_name if locked.assigned_to else "sem responsável"
    locked.assigned_to = assignee
    locked.save(update_fields=["assigned_to", "updated_at"])
    _event(
        activity=locked,
        event_type="assigned",
        actor=actor,
        summary=(
            f"Responsável: {previous_name} → "
            f"{assignee.display_name if assignee else 'sem responsável'}. Motivo: {reason}"
        )[:500],
    )
    record_event(
        action="hub.activity.assigned",
        actor=actor,
        organization=locked.organization,
        target=locked,
        request=request,
        metadata={"previous_assignee": previous, "assignee": assignee_id, "reason": reason},
    )
    return locked


DEFAULT_INTERNAL_LEAD_BUSINESS_DAYS = 2


@dataclass(frozen=True)
class DueDates:
    legal: date | None
    internal: date | None
    rule: TaxDeadlineRule | None
    notes: tuple[tuple[str, str], ...] = ()


def compute_due_dates(
    *,
    template: ActivityTemplate,
    assignment: ActivityTemplateAssignment | None,
    competence: date,
    calendar: BusinessCalendar | None = None,
) -> DueDates:
    """Legal and internal deadlines of ``competence`` under the template (D-277).

    The legal date comes only from an approved rule (or a day the office typed for templates
    without rule). The internal date is the office's own day, or business days before the legal
    date, and is pulled back when it would fall after the legal one.
    """

    calendar = calendar or BusinessCalendar()
    competence = competence.replace(day=1)
    due_month = add_months(competence, template.due_month_offset or 0)
    notes: list[tuple[str, str]] = []
    rule = approved_rule(template.legal_rule_code, competence)
    legal: date | None = None
    if template.legal_rule_code:
        if rule is None:
            notes.append(
                (
                    "legal_due_unavailable",
                    "Prazo legal ausente: a regra da agenda tributária não tem versão aprovada "
                    "para esta competência.",
                )
            )
        else:
            try:
                legal = rule_due_date(rule, competence, calendar)
            except CalendarIncomplete as error:
                rule = None
                notes.append(
                    (
                        "legal_due_unavailable",
                        f"Prazo legal ausente: calendário de {error.args[0]} ainda não aprovado.",
                    )
                )
    else:
        legal_day = (assignment.legal_due_day if assignment else None) or template.legal_due_day
        legal = day_in_month(due_month, legal_day) if legal_day else None
    lead = (
        template.internal_lead_business_days
        if template.internal_lead_business_days is not None
        else DEFAULT_INTERNAL_LEAD_BUSINESS_DAYS
    )
    internal_day = (
        assignment.internal_due_day if assignment else None
    ) or template.internal_due_day
    internal = day_in_month(due_month, internal_day) if internal_day else None
    if internal is None and legal is not None and rule is not None:
        internal = internal_before(legal, lead, calendar)
    elif internal is not None and legal is not None and internal > legal:
        internal = internal_before(legal, lead, calendar)
        notes.append(
            (
                "internal_due_adjusted",
                f"Prazo interno antecipado para {internal:%d/%m/%Y}: ficaria depois do legal.",
            )
        )
    return DueDates(legal=legal, internal=internal, rule=rule, notes=tuple(notes))


def competence_ready_until(today: date, template: ActivityTemplate) -> date:
    """Latest competência whose work can start: M opens on the first day of M + offset."""

    return add_months(today.replace(day=1), -(template.due_month_offset or 0))


def _area_responsible(assignment: ActivityTemplateAssignment, area: str) -> User | None:
    """The company's default owner for ``area`` when that person can still operate it."""

    row = (
        CompanyAreaResponsible.objects.filter(
            company_id=assignment.company_id, area=area, user__isnull=False
        )
        .select_related("user")
        .first()
    )
    if row is None or row.user is None:
        return None
    membership = Membership.objects.filter(
        organization_id=assignment.organization_id,
        user_id=row.user_id,
        is_active=True,
        user__is_active=True,
    ).first()
    if (
        membership is None
        or membership.role in {Membership.Role.AUDITOR, Membership.Role.BILLING}
        or not company_queryset_for_membership(membership)
        .filter(pk=assignment.company_id)
        .exists()
    ):
        return None
    return row.user


def _assignment_responsible_has_access(assignment: ActivityTemplateAssignment) -> bool:
    """Check the live portfolio instead of trusting an old default assignee."""

    if assignment.assigned_to_id is None:
        return True
    membership = Membership.objects.filter(
        organization_id=assignment.organization_id,
        user_id=assignment.assigned_to_id,
        is_active=True,
        user__is_active=True,
    ).first()
    return bool(
        membership
        and membership.role not in {Membership.Role.AUDITOR, Membership.Role.BILLING}
        and company_queryset_for_membership(membership)
        .filter(pk=assignment.company_id)
        .exists()
    )


@transaction.atomic
def generate_monthly_activities(
    *,
    assignments: list[ActivityTemplateAssignment],
    competence: date,
    actor: User | None,
    request: object | None,
) -> tuple[list[OperationalActivity], int]:
    """Materialize only active, explicitly assigned monthly templates once per competence."""

    created: list[OperationalActivity] = []
    ignored = 0
    competence = competence.replace(day=1)
    calendar = BusinessCalendar()
    for assignment in assignments:
        template = assignment.template
        if (
            assignment.organization_id != assignment.company.organization_id
            or assignment.organization_id != template.organization_id
        ):
            raise ValidationError(
                "Modelo, atribuicao e empresa precisam pertencer ao mesmo escritorio."
            )
        if not assignment.active or not template.active or template.frequency != "monthly":
            ignored += 1
            continue
        assignee_is_available = _assignment_responsible_has_access(assignment)
        assignee = assignment.assigned_to if assignee_is_available else None
        if assignment.assigned_to_id is None:
            # D-277: without an owner in the assignment, the client's area owner takes it.
            assignee = _area_responsible(assignment, template.area)
        due = compute_due_dates(
            template=template, assignment=assignment, competence=competence, calendar=calendar
        )
        activity, was_created = OperationalActivity.objects.get_or_create(
            organization=assignment.organization,
            company=assignment.company,
            code=template.code,
            competence=competence,
            template_version=template.version,
            defaults={
                "template": template,
                "title": template.title,
                "area": template.area,
                "legal_due_on": due.legal,
                "internal_due_on": due.internal,
                "legal_due_rule": due.rule,
                "assigned_to": assignee,
                "requires_processing_closed": template.requires_processing_closed,
                "requires_accepted_obligation": template.requires_accepted_obligation,
                "evidence_requirement": template.evidence_requirement,
            },
        )
        if not was_created:
            ignored += 1
            continue
        if assignment.assigned_to_id is not None and assignee is None:
            _event(
                activity=activity,
                event_type="assignment_unavailable",
                summary=(
                    "Gerada sem responsavel: a atribuicao anterior "
                    "nao tem acesso ativo a empresa."
                ),
                actor=actor,
            )
        _event(
            activity=activity,
            event_type="generated",
            summary=f"Gerada pelo modelo {template.code} v{template.version}.",
            actor=actor,
        )
        for event_type, summary in due.notes:
            _event(activity=activity, event_type=event_type, summary=summary, actor=actor)
        record_event(
            action="hub.activity.generated",
            actor=actor,
            organization=activity.organization,
            target=activity,
            request=request,
            metadata={
                "template_id": str(template.id),
                "template_version": template.version,
                "competence": competence.isoformat(),
            },
        )
        created.append(activity)
    return created, ignored


def _event(
    *, activity: OperationalActivity, event_type: str, summary: str, actor: User | None
) -> None:
    OperationalActivityEvent.objects.create(
        organization=activity.organization,
        activity=activity,
        event_type=event_type,
        summary=summary,
        actor=actor,
    )


RESCHEDULE_ROLES = frozenset(
    {Membership.Role.OWNER, Membership.Role.ADMIN, Membership.Role.MANAGER}
)


def can_reschedule_activity(
    *, membership: Membership | None, activity: OperationalActivity
) -> bool:
    """D-277: owner, administration and management move internal deadlines."""

    return bool(
        membership is not None
        and membership.role in RESCHEDULE_ROLES
        and can_operate_activity(membership=membership, activity=activity)
    )


@transaction.atomic
def reschedule_activity(
    *,
    activity: OperationalActivity,
    membership: Membership | None,
    actor: User,
    internal_due_on: date,
    expected_internal_due_on: str,
    reason: str,
    request: object,
) -> OperationalActivity:
    """Move the internal deadline with a reason; the legal deadline is never edited here."""

    if not can_reschedule_activity(membership=membership, activity=activity):
        raise PermissionDenied("Somente proprietário, administração ou gestão muda prazos.")
    locked = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if locked.work_status in {
        OperationalActivity.WorkStatus.COMPLETED,
        OperationalActivity.WorkStatus.WAIVED,
    }:
        raise ValidationError("Atividade encerrada mantém o prazo registrado.")
    previous = locked.internal_due_on
    if (previous.isoformat() if previous else "") != expected_internal_due_on:
        raise ValidationError("O prazo mudou. Recarregue a atividade antes de alterar.")
    reason = reason.strip()
    if not reason or len(reason) > 500:
        raise ValidationError("Informe um motivo com até 500 caracteres.")
    if locked.legal_due_on and internal_due_on > locked.legal_due_on:
        raise ValidationError(
            f"O prazo interno não pode passar do prazo legal ({locked.legal_due_on:%d/%m/%Y})."
        )
    if internal_due_on == previous:
        return locked
    locked.internal_due_on = internal_due_on
    locked.save(update_fields=["internal_due_on", "updated_at"])
    _event(
        activity=locked,
        event_type="due_changed",
        actor=actor,
        summary=(
            f"Prazo interno: {previous:%d/%m/%Y} → {internal_due_on:%d/%m/%Y}. Motivo: {reason}"
            if previous
            else f"Prazo interno definido para {internal_due_on:%d/%m/%Y}. Motivo: {reason}"
        )[:500],
    )
    record_event(
        action="hub.activity.rescheduled",
        actor=actor,
        organization=locked.organization,
        target=locked,
        request=request,
        metadata={
            "previous": previous.isoformat() if previous else "",
            "internal_due_on": internal_due_on.isoformat(),
            "reason": reason[:240],
        },
    )
    return locked


@transaction.atomic
def add_activity_note(
    *,
    activity: OperationalActivity,
    membership: Membership | None,
    actor: User,
    note: str,
    request: object,
) -> OperationalActivityEvent:
    """A short note for whoever picks the work up next; it never counts as evidence."""

    if not can_operate_activity(membership=membership, activity=activity, actor=actor):
        raise PermissionDenied("Você não possui acesso a esta atividade.")
    note = note.strip()
    if not note or len(note) > 500:
        raise ValidationError("Escreva uma observação com até 500 caracteres.")
    event = OperationalActivityEvent.objects.create(
        organization=activity.organization,
        activity=activity,
        event_type="note",
        summary=note,
        actor=actor,
    )
    record_event(
        action="hub.activity.note_added",
        actor=actor,
        organization=activity.organization,
        target=activity,
        request=request,
        metadata={"length": len(note)},
    )
    return event


@transaction.atomic
def claim_activity(
    *,
    activity: OperationalActivity,
    membership: Membership | None,
    actor: User,
    request: object,
) -> OperationalActivity:
    """Take unassigned work inside one's own portfolio (D-277)."""

    if not can_operate_activity(membership=membership, activity=activity, actor=actor):
        raise PermissionDenied("Você não possui acesso a esta atividade.")
    locked = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if locked.work_status in {
        OperationalActivity.WorkStatus.COMPLETED,
        OperationalActivity.WorkStatus.WAIVED,
    }:
        raise ValidationError("Atividade encerrada preserva seu responsável histórico.")
    if locked.assigned_to_id is not None:
        raise ValidationError("A atividade já tem responsável. Recarregue a página.")
    locked.assigned_to = actor
    locked.save(update_fields=["assigned_to", "updated_at"])
    _event(
        activity=locked,
        event_type="assigned",
        actor=actor,
        summary=f"Responsável: sem responsável → {actor.display_name}. Assumida pela pessoa.",
    )
    record_event(
        action="hub.activity.claimed",
        actor=actor,
        organization=locked.organization,
        target=locked,
        request=request,
    )
    return locked


@transaction.atomic
def complete_activity(
    *, activity: OperationalActivity, membership: Membership | None, actor: User, request: object
) -> OperationalActivity:
    """Complete only when its stated evidence/obligation requirements are satisfied."""

    if not can_operate_activity(membership=membership, activity=activity, actor=actor):
        raise PermissionDenied("Você não possui acesso a esta atividade.")
    locked = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    missing = completion_requirements(locked)
    if missing:
        raise ValidationError(list(missing))
    if locked.work_status in {
        OperationalActivity.WorkStatus.COMPLETED,
        OperationalActivity.WorkStatus.WAIVED,
    }:
        return locked
    locked.work_status = OperationalActivity.WorkStatus.COMPLETED
    locked.completed_at = timezone.now()
    locked.completed_by = actor
    locked.blocked_reason = ""
    locked.save(
        update_fields=[
            "work_status",
            "completed_at",
            "completed_by",
            "blocked_reason",
            "updated_at",
        ]
    )
    _event(activity=locked, event_type="completed", summary="Atividade concluída.", actor=actor)
    record_event(
        action="hub.activity.completed",
        actor=actor,
        organization=locked.organization,
        target=locked,
        request=request,
        metadata={
            "area": locked.area,
            "competence": locked.competence.isoformat() if locked.competence else "",
        },
    )
    return locked


@transaction.atomic
def block_activity(
    *,
    activity: OperationalActivity,
    membership: Membership | None,
    actor: User,
    request: object,
    reason: str,
) -> OperationalActivity:
    if not can_operate_activity(membership=membership, activity=activity, actor=actor):
        raise PermissionDenied("Você não possui acesso a esta atividade.")
    reason = reason.strip()
    if not reason:
        raise ValidationError("Informe o impedimento para preservar a trilha operacional.")
    locked = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if locked.work_status in {
        OperationalActivity.WorkStatus.COMPLETED,
        OperationalActivity.WorkStatus.WAIVED,
    }:
        raise ValidationError("Uma atividade encerrada não pode ser impedida.")
    locked.work_status = OperationalActivity.WorkStatus.BLOCKED
    locked.blocked_reason = reason
    locked.save(update_fields=["work_status", "blocked_reason", "updated_at"])
    _event(activity=locked, event_type="blocked", summary=reason, actor=actor)
    record_event(
        action="hub.activity.blocked",
        actor=actor,
        organization=locked.organization,
        target=locked,
        request=request,
        metadata={"area": locked.area},
    )
    return locked


@transaction.atomic
def add_human_evidence(
    *,
    activity: OperationalActivity,
    membership: Membership | None,
    actor: User,
    request: object,
    summary: str,
    reference: str = "",
) -> OperationalEvidence:
    if not can_operate_activity(membership=membership, activity=activity, actor=actor):
        raise PermissionDenied("Você não possui acesso a esta atividade.")
    summary = summary.strip()
    if not summary:
        raise ValidationError("Descreva a evidência confirmada.")
    evidence = OperationalEvidence.objects.create(
        organization=activity.organization,
        activity=activity,
        kind=OperationalActivity.EvidenceKind.HUMAN,
        reference=reference.strip(),
        summary=summary,
        recorded_by=actor,
    )
    _event(activity=activity, event_type="evidence_recorded", summary=summary, actor=actor)
    record_event(
        action="hub.activity.evidence_recorded",
        actor=actor,
        organization=activity.organization,
        target=evidence,
        request=request,
        metadata={"activity_id": str(activity.id), "kind": "human"},
    )
    return evidence


@transaction.atomic
def record_source_observation(
    *,
    activity: OperationalActivity,
    data_source: DataSource,
    actor: User | None,
    request: object | None,
    successful: bool,
    summary: str,
    external_reference: str = "",
    source_version: str = "",
    processing_status: str | None = None,
    obligation_status: str | None = None,
    observed_at: datetime | None = None,
) -> OperationalSourceObservation:
    """Apply a source result without treating a failed read as absence of a pending item."""

    if activity.organization_id != data_source.organization_id:
        raise ValidationError("A fonte e a atividade precisam pertencer ao mesmo escritório.")
    if processing_status and processing_status not in OperationalActivity.ProcessingStatus.values:
        raise ValidationError("Situação de processamento inválida.")
    if obligation_status and obligation_status not in OperationalActivity.ObligationStatus.values:
        raise ValidationError("Situação de obrigação inválida.")
    summary = summary.strip()
    if not summary:
        raise ValidationError("Descreva o resultado observado na fonte.")
    moment = observed_at or timezone.now()
    if timezone.is_naive(moment):
        raise ValidationError("A data observada precisa informar o fuso horário.")
    if (
        len(summary) > 500
        or len(external_reference.strip()) > 180
        or len(source_version.strip()) > 120
    ):
        raise ValidationError("A descrição ou referência da observação excede o limite permitido.")
    data_source = DataSource.objects.select_for_update().get(pk=data_source.pk)
    locked = OperationalActivity.objects.select_for_update().get(pk=activity.pk)
    if locked.organization_id != data_source.organization_id:
        raise ValidationError("A fonte e a atividade precisam pertencer ao mesmo escritório.")
    source_disabled = data_source.status == DataSource.Status.DISABLED
    declared_capabilities = set(data_source.capabilities)
    required_capabilities = {
        SOURCE_CAPABILITY_ACTIVITY_PROCESSING: processing_status,
        SOURCE_CAPABILITY_ACTIVITY_OBLIGATION: obligation_status,
    }
    missing_capabilities = [
        capability
        for capability, requested_value in required_capabilities.items()
        if requested_value and capability not in declared_capabilities
    ]
    if missing_capabilities:
        raise ValidationError(
            "A fonte nao declara capacidade comprovada para atualizar este estado operacional."
        )
    if (
        (processing_status or obligation_status)
        and source_disabled
    ):
        raise ValidationError("A fonte esta desativada e nao pode atualizar estado operacional.")
    history = locked.source_observations.all()
    payload = {
        "successful": successful,
        "external_reference": external_reference.strip(),
        "source_version": source_version.strip(),
        "processing_status": processing_status or "",
        "obligation_status": obligation_status or "",
        "summary": summary,
        "observed_at": moment,
    }
    repeated = history.filter(data_source=data_source, **payload).first()
    if repeated is not None:
        return repeated
    latest = history.order_by("-observed_at").first()
    update_freshness = (latest is None or moment > latest.observed_at) and not (
        successful and source_disabled
    )
    source_latest = data_source.operational_observations.order_by("-observed_at").first()
    update_source = not source_disabled and (
        (source_latest is None or moment > source_latest.observed_at)
        and (
            data_source.source_snapshot_at is None or moment >= data_source.source_snapshot_at
        )
    )
    applied: dict[str, object] = {}
    conflicts: list[str] = []
    if successful:
        for field, value in (
            ("processing_status", processing_status),
            ("obligation_status", obligation_status),
        ):
            if not value:
                continue
            prior = (
                history.filter(successful=True)
                .exclude(**{field: ""})
                .order_by("-observed_at")
                .first()
            )
            if prior is None or moment > prior.observed_at:
                applied[field] = value
            elif moment == prior.observed_at and value != getattr(prior, field):
                conflicts.append(field)
    observation = OperationalSourceObservation.objects.create(
        organization=locked.organization,
        data_source=data_source,
        activity=locked,
        successful=successful,
        external_reference=external_reference.strip(),
        source_version=source_version.strip(),
        processing_status=processing_status or "",
        obligation_status=obligation_status or "",
        summary=summary,
        observed_at=moment,
    )
    if successful and applied:
        OperationalEvidence.objects.create(
            organization=locked.organization,
            activity=locked,
            kind="source",
            reference=f"observation:{observation.pk}",
            summary=summary,
            observed_at=moment,
            recorded_by=actor,
        )
    if successful:
        conflicts = []
        for dimension in ("processing_status", "obligation_status"):
            dimension_history = history.filter(successful=True).exclude(**{dimension: ""})
            newest = dimension_history.order_by("-observed_at").first()
            if newest and (
                dimension_history.filter(observed_at=newest.observed_at)
                .order_by()
                .values_list(dimension, flat=True)
                .distinct()
                .count()
                > 1
            ):
                conflicts.append(dimension)

    if not successful:
        if update_freshness:
            locked.freshness = OperationalActivity.Freshness.UNAVAILABLE
            locked.save(update_fields=["freshness", "updated_at"])
        if update_source:
            data_source.status = DataSource.Status.ATTENTION
            data_source.last_error_message = summary[:240]
            data_source.save(update_fields=["status", "last_error_message", "updated_at"])
        _event(activity=locked, event_type="source_unavailable", summary=summary, actor=actor)
        event_action = "hub.activity.source_unavailable"
    else:
        update_fields: dict[str, object] = applied.copy()
        if update_freshness:
            update_fields["freshness"] = OperationalActivity.Freshness.CURRENT
        if conflicts:
            update_fields["freshness"] = OperationalActivity.Freshness.STALE
        reopening = locked.work_status == OperationalActivity.WorkStatus.COMPLETED and (
            applied.get("processing_status") == OperationalActivity.ProcessingStatus.REOPENED
            or applied.get("obligation_status") == OperationalActivity.ObligationStatus.REJECTED
        )
        if reopening:
            update_fields.update(
                {
                    "work_status": OperationalActivity.WorkStatus.PENDING,
                    "completed_at": None,
                    "completed_by": None,
                }
            )
        for field_name, field_value in update_fields.items():
            setattr(locked, field_name, field_value)
        if update_fields:
            locked.save(update_fields=[*update_fields.keys(), "updated_at"])
        if update_source:
            data_source.status = DataSource.Status.READY
            data_source.source_snapshot_at = observation.observed_at
            data_source.last_error_code = ""
            data_source.last_error_message = ""
            data_source.save(
                update_fields=[
                    "status",
                    "source_snapshot_at",
                    "last_error_code",
                    "last_error_message",
                    "updated_at",
                ]
            )
        event_type = "reopened_from_source" if reopening else "source_observed"
        event_summary = summary
        if conflicts:
            event_type = "source_conflict"
            event_summary = f"Retornos conflitantes; confira a fonte. {summary}"[:500]
        elif not applied and not update_freshness:
            event_type = "source_history_only"
            event_summary = f"Retorno histórico; estado atual preservado. {summary}"[:500]
        _event(activity=locked, event_type=event_type, summary=event_summary, actor=actor)
        event_action = "hub.activity.reopened" if reopening else "hub.activity.source_observed"
    record_event(
        action=event_action,
        actor=actor,
        organization=locked.organization,
        target=observation,
        request=request,
        metadata={
            "activity_id": str(locked.id),
            "data_source_id": str(data_source.id),
            "successful": successful,
            "processing_status": processing_status or "",
            "obligation_status": obligation_status or "",
            "applied_fields": list(applied),
            "freshness_applied": update_freshness or bool(successful and conflicts),
            "conflicting_fields": conflicts,
        },
    )
    return observation
