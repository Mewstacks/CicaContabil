"""Repeatable, synthetic operational reference data for the demonstration office."""

from __future__ import annotations

from datetime import date, timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import (
    ActivityTemplate,
    ActivityTemplateAssignment,
    CompanyAccessGrant,
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
    """Add missing scenarios only; never reset progress or rewrite immutable evidence."""
    office = Organization.objects.select_for_update().get(pk=office.pk)
    if not office.is_demo or not office.is_active:
        raise ValidationError("Somente um escritório de demonstração ativo pode ser populado.")
    from apps.hub.models import ClientCompany

    companies = list(
        ClientCompany.objects.filter(organization=office, active=True).order_by("dominio_code")
    )
    if not companies:
        raise ValidationError("Prepare as empresas fictícias com seed_demo primeiro.")
    today = today or timezone.localdate()
    now = timezone.now()
    current = today.replace(day=1)
    previous = (current - timedelta(days=1)).replace(day=1)
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
                "evidence_requirement": ActivityTemplate.EvidenceRequirement.HUMAN,
            },
        )
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
            for month in (previous, current):
                historic = month == previous
                status = (
                    "completed"
                    if historic or state_index == 4
                    else "waived"
                    if state_index == 5 and not closes
                    else "blocked"
                    if state_index == 2
                    else "in_progress"
                    if state_index in (1, 3)
                    else "pending"
                )
                due = (
                    (current - timedelta(days=3))
                    if historic
                    else today + timedelta(days=(-3, 0, 2, 5, -1, 12, 7)[state_index])
                )
                done = status == "completed"
                blocked = (
                    "Aguardando o extrato complementar do cliente. Cenário fictício."
                    if status == "blocked"
                    else ""
                )
                activity, created = OperationalActivity.objects.get_or_create(
                    organization=office,
                    company=company,
                    code=template.code,
                    competence=month,
                    template_version=1,
                    defaults={
                        "template": template,
                        "title": title,
                        "area": area,
                        "assigned_to": assignee,
                        "internal_due_on": due,
                        "work_status": status,
                        "requires_processing_closed": closes,
                        "evidence_requirement": ActivityTemplate.EvidenceRequirement.HUMAN,
                        "processing_status": "closed"
                        if done and closes
                        else "open"
                        if closes
                        else "not_verified",
                        "freshness": "unavailable"
                        if not historic and state_index == 3
                        else "current",
                        "blocked_reason": blocked,
                        "waived_reason": "Documento não exigido neste cenário fictício."
                        if status == "waived"
                        else "",
                        "completed_at": now - timedelta(days=2) if done else None,
                        "completed_by": person if done else None,
                    },
                )
                if not created:
                    continue
                activity.full_clean()
                created_count += 1
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
                OperationalActivityEvent.objects.create(
                    organization=office,
                    activity=activity,
                    event_type=activity.get_work_status_display(),
                    summary=blocked
                    or (
                        "Conferência simulada concluída; nenhuma fonte externa foi consultada."
                        if done
                        else "Andamento fictício registrado para explorar a rotina."
                    ),
                    occurred_at=now - timedelta(days=2 if done else 1),
                )
                if done or status == "in_progress":
                    OperationalEvidence.objects.create(
                        organization=office,
                        activity=activity,
                        kind="human",
                        reference=f"DEMO-{company.dominio_code}-{month:%Y%m}-{scenario_index + 1}",
                        summary=(
                            "Evidência fictícia: saldos, documentos e totais conferidos."
                            if done
                            else "Evidência fictícia: divergências aguardando revisão."
                        ),
                        recorded_by=person,
                        observed_at=now - timedelta(days=2 if done else 1),
                    )
    return {
        "created": created_count,
        "activities": OperationalActivity.objects.filter(organization=office).count(),
        "templates": ActivityTemplate.objects.filter(organization=office).count(),
        "people": len(people),
    }
