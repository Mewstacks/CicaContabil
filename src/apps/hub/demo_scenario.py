"""Repeatable, synthetic operational reference data for the demonstration office."""

from __future__ import annotations

from datetime import date, datetime, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.fiscal_calendar.reference import national_non_business_days
from apps.fiscal_calendar.services import add_months, day_in_month
from apps.hub.models import (
    ActivityTemplate,
    ActivityTemplateAssignment,
    ClientCompany,
    CompanyAccessGrant,
    FiscalGuide,
    OperationalActivity,
    OperationalActivityEvent,
    OperationalEvidence,
)
from apps.hub.module_catalog import OFFERED_MODULE_CODES
from apps.organizations.models import Membership, Organization


def persona_email(office: Organization, index: int = 0) -> str:
    return f"cica-demo-{office.pk}-{index}@example.test"


# No automatic tasks or external integrations are invoked by this fixture.
SCENARIOS = (
    ("fechamento-contabil", "Conferir fechamento contábil", "accounting"),
    ("conciliacao", "Conferir divergências do extrato bancário", "accounting"),
    ("fechamento-fiscal", "Conferir apuração e fechamento fiscal", "fiscal"),
    ("classificacao", "Revisar classificação dos serviços tomados", "fiscal"),
    ("fechamento-folha", "Conferir folha e encargos da competência", "payroll"),
    ("documentos", "Conferir documentos recebidos do cliente", "general"),
)


@transaction.atomic
def populate_operations(office: Organization, *, today: date | None = None) -> dict[str, int]:
    """Keep the synthetic window current; evidence and events stay append-only."""
    office = Organization.objects.select_for_update().get(pk=office.pk)
    if not office.is_demo or not office.is_active:
        raise ValidationError("Somente um escritório de demonstração ativo pode ser populado.")
    companies = list(
        ClientCompany.objects.filter(organization=office, active=True).order_by("dominio_code")
    )
    if not companies:
        raise ValidationError("Prepare as empresas fictícias com seed_demo primeiro.")
    today = today or timezone.localdate()
    now = timezone.now()
    current = today.replace(day=1)
    people = []
    for index, name in enumerate(
        ("Ana Martins · demo", "Bruno Costa · demo", "Camila Rocha · demo")
    ):
        person = User.objects.filter(email=persona_email(office, index)).first()
        if person is None:
            person = User.objects.create_user(email=persona_email(office, index), full_name=name)
        elif (
            person.has_usable_password()
            or person.organization_memberships.exclude(organization=office).exists()
        ):
            raise ValidationError("A identidade fictícia conflita com uma conta existente.")
        member, _ = Membership.objects.get_or_create(
            organization=office, user=person, defaults={"role": Membership.Role.OPERATOR}
        )
        for company in companies:
            CompanyAccessGrant.objects.get_or_create(
                organization=office,
                membership=member,
                company=company,
                defaults={"modules": list(OFFERED_MODULE_CODES), "capabilities": ["read", "write"]},
            )
        people.append(person)

    created_count = 0
    # Rolling window (D-277): the accountant works on the month that just closed. Competência
    # M-1 holds the open scenario and M-2 the finished history; every date falls after its
    # competência. Older or future rows of a previous layout leave the open queues.
    open_month = add_months(current, -1)
    history_month = add_months(current, -2)
    for scenario_index, (code, title, area) in enumerate(SCENARIOS):
        closes = code.startswith("fechamento-")
        template, _ = ActivityTemplate.objects.get_or_create(
            organization=office,
            code=f"DEMO-{code}",
            version=1,
            defaults={
                "title": title,
                "area": area,
                "requires_processing_closed": closes,
                "description": (
                    "Modelo fictício para explorar a rotina. "
                    "Prazos ilustrativos, sem calendário fiscal oficial."
                ),
                "internal_due_day": 10 + scenario_index,
                "due_month_offset": 1,
                "evidence_requirement": ActivityTemplate.EvidenceRequirement.HUMAN,
            },
        )
        if template.due_month_offset != 1:
            template.due_month_offset = 1
            template.save(update_fields=["due_month_offset", "updated_at"])
        for company_index, company in enumerate(companies):
            person = people[scenario_index % len(people)]
            # Each area has examples of pending, complete, blocked and unavailable work.
            state_index = (company_index + scenario_index) % 7
            assignee = None if state_index == 6 else person
            ActivityTemplateAssignment.objects.get_or_create(
                organization=office,
                template=template,
                company=company,
                defaults={"assigned_to": assignee},
            )
            rows = {
                row.competence: row
                for row in OperationalActivity.objects.filter(
                    organization=office, company=company, code=template.code, template_version=1
                )
            }
            open_status = _scenario_status(state_index, closes)
            moved = rows.get(open_month)
            if (
                history_month not in rows
                and moved is not None
                and moved.work_status == OperationalActivity.WorkStatus.COMPLETED
                and open_status != OperationalActivity.WorkStatus.COMPLETED
            ):
                # An earlier layout finished this month already; it becomes the history row.
                moved.competence = history_month
                moved.save(update_fields=["competence", "updated_at"])
                rows[history_month] = rows.pop(open_month)
            for month in (history_month, open_month):
                historic = month == history_month
                status = OperationalActivity.WorkStatus.COMPLETED if historic else open_status
                if historic:
                    due = day_in_month(add_months(month, 1), 10 + scenario_index)
                else:
                    offset = (-3, 0, 2, 5, -1, 12, 7)[state_index]
                    due = max(today + timedelta(days=offset), current)
                created = _apply_scenario(
                    office=office,
                    company=company,
                    template=template,
                    month=month,
                    activity=rows.pop(month, None),
                    status=status,
                    due=due,
                    assignee=assignee,
                    person=person,
                    closes=closes,
                    freshness_unavailable=not historic and state_index == 3,
                    reference=f"DEMO-{company.dominio_code}-{month:%Y%m}-{scenario_index + 1}",
                    now=now,
                )
                created_count += int(created)
            for stale in rows.values():
                if stale.work_status in _OPEN_STATES:
                    stale.work_status = OperationalActivity.WorkStatus.WAIVED
                    stale.waived_reason = "Cenário fictício fora da competência em conferência."
                    stale.blocked_reason = ""
                    stale.internal_due_on = None
                    stale.legal_due_on = None
                    stale.save(
                        update_fields=[
                            "work_status",
                            "waived_reason",
                            "blocked_reason",
                            "internal_due_on",
                            "legal_due_on",
                            "updated_at",
                        ]
                    )
    return {
        "created": created_count,
        "activities": OperationalActivity.objects.filter(organization=office).count(),
        "templates": ActivityTemplate.objects.filter(organization=office).count(),
        "people": len(people),
    }


_OPEN_STATES = {
    OperationalActivity.WorkStatus.PENDING,
    OperationalActivity.WorkStatus.IN_PROGRESS,
    OperationalActivity.WorkStatus.BLOCKED,
}


def _scenario_status(state_index: int, closes: bool) -> str:
    if state_index == 4:
        return OperationalActivity.WorkStatus.COMPLETED
    if state_index == 5 and not closes:
        return OperationalActivity.WorkStatus.WAIVED
    if state_index == 2:
        return OperationalActivity.WorkStatus.BLOCKED
    if state_index in (1, 3):
        return OperationalActivity.WorkStatus.IN_PROGRESS
    return OperationalActivity.WorkStatus.PENDING


def _apply_scenario(
    *,
    office: Organization,
    company: ClientCompany,
    template: ActivityTemplate,
    month: date,
    activity: OperationalActivity | None,
    status: str,
    due: date,
    assignee: User | None,
    person: User,
    closes: bool,
    freshness_unavailable: bool,
    reference: str,
    now: datetime,
) -> bool:
    """Create or re-state one scenario row; evidence and events are only ever appended."""

    done = status == OperationalActivity.WorkStatus.COMPLETED
    values = {
        "template": template,
        "title": template.title,
        "area": template.area,
        "assigned_to": assignee,
        "internal_due_on": due,
        "legal_due_on": None,
        "work_status": status,
        "requires_processing_closed": closes,
        "evidence_requirement": ActivityTemplate.EvidenceRequirement.HUMAN,
        "processing_status": "closed" if done and closes else "open" if closes else "not_verified",
        "freshness": "unavailable" if freshness_unavailable else "current",
        "blocked_reason": (
            "Aguardando o extrato complementar do cliente. Cenário fictício."
            if status == OperationalActivity.WorkStatus.BLOCKED
            else ""
        ),
        "waived_reason": (
            "Documento não exigido neste cenário fictício."
            if status == OperationalActivity.WorkStatus.WAIVED
            else ""
        ),
        "completed_at": now - timedelta(days=2) if done else None,
        "completed_by": person if done else None,
    }
    created = activity is None
    if activity is None:
        activity = OperationalActivity(
            organization=office,
            company=company,
            code=template.code,
            competence=month,
            template_version=1,
            **values,
        )
        activity.full_clean()
        activity.save()
        OperationalActivityEvent.objects.create(
            organization=office,
            activity=activity,
            event_type="Cenário de demonstração",
            summary=(
                "Atividade fictícia criada a partir do modelo, "
                "com prazo ilustrativo e responsável da equipe demo."
            ),
            occurred_at=now - timedelta(days=4),
        )
    else:
        previous_status = activity.work_status
        if previous_status == status and done:
            # A finished row keeps who finished it and when; only the window moves.
            values["completed_at"] = activity.completed_at
            values["completed_by"] = activity.completed_by
        changed = [field for field, value in values.items() if getattr(activity, field) != value]
        for field in changed:
            setattr(activity, field, values[field])
        if changed:
            activity.save(update_fields=[*changed, "updated_at"])
        if previous_status == status:
            return False
    OperationalActivityEvent.objects.create(
        organization=office,
        activity=activity,
        event_type=activity.get_work_status_display(),
        summary=values["blocked_reason"]
        or (
            "Conferência simulada concluída; nenhuma fonte externa foi consultada."
            if done
            else "Andamento fictício registrado para explorar a rotina."
        ),
        occurred_at=now - timedelta(days=2 if done else 1),
    )
    if (done or status == OperationalActivity.WorkStatus.IN_PROGRESS) and not (
        OperationalEvidence.objects.filter(activity=activity, reference=reference).exists()
    ):
        OperationalEvidence.objects.create(
            organization=office,
            activity=activity,
            kind="human",
            reference=reference,
            summary=(
                "Evidência fictícia: saldos, documentos e totais conferidos."
                if done
                else "Evidência fictícia: divergências aguardando revisão."
            ),
            recorded_by=person,
            observed_at=now - timedelta(days=2 if done else 1),
        )
    return created


def demo_guide_due_date(competence_month: date) -> date:
    """Day 20 of the following month, brought forward over non-business days.

    Same shape as the contribuições previdenciárias draft rule; the demonstration uses the
    reference holidays shipped with the code because it must not depend on an approval.
    """

    due = day_in_month(add_months(competence_month, 1), 20)
    holidays = {day for day, _name in national_non_business_days(due.year)}
    while due.weekday() >= 5 or due in holidays:
        due -= timedelta(days=1)
    return due


@transaction.atomic
def refresh_demo_guides(office: Organization, *, today: date | None = None) -> int:
    """DCTFWeb guides of the closed month; older demo guides leave the queue."""

    if not office.is_demo or not office.is_active:
        raise ValidationError("Somente um escritório de demonstração ativo pode ser populado.")
    today = today or timezone.localdate()
    month = add_months(today.replace(day=1), -1)
    competence = f"{month:%m/%Y}"
    companies = list(
        ClientCompany.objects.filter(organization=office, active=True).order_by("dominio_code")[:3]
    )
    references = []
    for index, company in enumerate(companies, start=1):
        reference = f"DEMO-DCTFWEB-{company.dominio_code}-{competence}"
        references.append(reference)
        FiscalGuide.objects.get_or_create(
            organization=office,
            company=company,
            reference=reference,
            defaults={
                "kind": FiscalGuide.Kind.DCTFWEB,
                "status": FiscalGuide.Status.READY,
                "competence": competence,
                "due_on": demo_guide_due_date(month),
                "amount_cents": 12_500 * index,
                "integra_service_key": "dctfweb.guia",
            },
        )
    return (
        FiscalGuide.objects.filter(
            organization=office,
            reference__startswith="DEMO-DCTFWEB-",
            status=FiscalGuide.Status.READY,
        )
        .exclude(reference__in=references)
        .update(status=FiscalGuide.Status.SKIPPED, updated_at=timezone.now())
    )
