"""Synthetic central fixtures, loaded only by the isolated QA server."""

import json
from datetime import timedelta

from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.mfa import SESSION_KEY
from apps.accounts.models import User
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    DataSource,
    FiscalGuide,
    OperationalActivity,
    ProductModule,
)
from apps.hub.module_activities import sync_fiscal_guide_activity
from apps.organizations.models import Membership, Organization


def seed_central(root):
    office, _ = Organization.objects.get_or_create(
        slug="qa-central", defaults={"name": "Central QA"}
    )
    companies = [
        ClientCompany.objects.get_or_create(
            organization=office,
            dominio_code=f"CENTRAL-{n}",
            defaults={"name": f"Empresa sintética {n} para conferência da carteira"},
        )[0]
        for n in (1, 2)
    ]
    ProductModule.objects.get_or_create(
        organization=office, code="guides", defaults={"enabled": True}
    )
    people = {}
    cookies = {}
    for role in ("owner", "operator", "auditor"):
        user, _ = User.objects.get_or_create(
            email=f"central-{role}@example.test",
            defaults={"full_name": f"Pessoa QA {role}"},
        )
        member, _ = Membership.objects.get_or_create(
            organization=office,
            user=user,
            defaults={"role": role},
        )
        CompanyAccessGrant.objects.get_or_create(
            organization=office,
            membership=member,
            company=companies[0],
            defaults={"modules": ["guides"], "capabilities": ["*"]},
        )
        people[role] = user
        client = Client()
        client.force_login(user)
        session = client.session
        session["hub_organization_id"] = str(office.pk)
        session[SESSION_KEY] = True
        session.save()
        cookies[role] = client.cookies["sessionid"].value
    today = timezone.localdate()
    activities = {}
    for code, title, delta, assigned, company in (
        ("overdue", "QA tarefa atrasada", -2, people["operator"], companies[0]),
        ("today", "QA tarefa de hoje", 0, people["operator"], companies[0]),
        ("future", "QA tarefa futura", 5, people["operator"], companies[0]),
        ("needs-evidence", "QA tarefa sem evidencia", 1, people["operator"], companies[0]),
        ("complete-v2", "QA tarefa para concluir", 1, people["operator"], companies[0]),
        ("shared", "QA tarefa compartilhada", 0, None, companies[0]),
        ("someone-else", "QA tarefa de outra pessoa", 0, people["owner"], companies[0]),
        ("restricted", "QA tarefa fora da carteira", 0, people["owner"], companies[1]),
    ):
        activity, _ = OperationalActivity.objects.get_or_create(
            organization=office,
            company=company,
            code=f"qa-{code}",
            defaults={
                "title": title,
                "area": "fiscal",
                "assigned_to": assigned,
                "competence": today.replace(day=1),
                "evidence_requirement": "human",
                "internal_due_on": today + timedelta(days=delta),
                "freshness": "current",
            },
        )
        if code in {"needs-evidence", "complete-v2"}:
            activity.work_status = OperationalActivity.WorkStatus.PENDING
            activity.completed_at = None
            activity.completed_by = None
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
        activities[code] = reverse("hub:activity-detail", args=[activity.pk])
    OperationalActivity.objects.update_or_create(
        organization=office,
        company=companies[0],
        code="qa-company-legal",
        defaults={
            "title": "QA ficha prazo legal",
            "area": "fiscal",
            "legal_due_on": today - timedelta(days=1),
            "internal_due_on": None,
        },
    )
    OperationalActivity.objects.update_or_create(
        organization=office,
        company=companies[0],
        code="qa-company-internal",
        defaults={
            "title": "QA ficha prazo interno",
            "area": "fiscal",
            "legal_due_on": today - timedelta(days=4),
            "internal_due_on": today + timedelta(days=4),
        },
    )
    OperationalActivity.objects.get_or_create(
        organization=office,
        company=companies[0],
        code="qa-close",
        defaults={
            "title": "QA fechamento fiscal aguardando fonte",
            "area": "fiscal",
            "competence": today.replace(day=1),
            "requires_processing_closed": True,
            "requires_accepted_obligation": True,
            "freshness": "unavailable",
            "internal_due_on": today,
            "evidence_requirement": "source",
        },
    )
    guide, _ = FiscalGuide.objects.get_or_create(
        organization=office,
        company=companies[0],
        reference="qa-guide-available",
        defaults={
            "kind": FiscalGuide.Kind.DAS,
            "status": FiscalGuide.Status.ISSUED,
            "competence": today.strftime("%m/%Y"),
            "due_on": today,
            "integra_service_key": "pgdasd.das",
            "issue_attempt": 1,
            "issue_requested_by": people["operator"],
            "issued_at": timezone.now(),
        },
    )
    guide_activity = sync_fiscal_guide_activity(guide.pk)
    if guide_activity is not None:
        activities["guide"] = reverse("hub:activity-detail", args=[guide_activity.pk])
    disabled_source, _ = DataSource.objects.get_or_create(
        organization=office,
        kind=DataSource.Kind.DOMINIO_LOCAL_AGENT,
        defaults={
            "label": "Fonte QA desativada",
            "status": DataSource.Status.DISABLED,
            "capabilities": ["companies"],
        },
    )
    if disabled_source.status != DataSource.Status.DISABLED:
        disabled_source.status = DataSource.Status.DISABLED
        disabled_source.save(update_fields=["status", "updated_at"])
    (root / "central-session.json").write_text(
        json.dumps(
            {
                "cookies": cookies,
                "activities": activities,
                "disabled_source_id": str(disabled_source.pk),
                "company_detail": reverse("hub:company-detail", args=[companies[0].pk]),
            }
        ),
        encoding="utf-8",
    )
