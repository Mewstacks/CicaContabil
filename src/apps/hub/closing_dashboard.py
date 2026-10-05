"""Portfolio closure requirements, independently from a person's assigned work."""

from datetime import date

from django.core.paginator import Paginator
from django.db.models import Q, QuerySet

from apps.hub.models import ActivityTemplate, ClientCompany, OperationalActivity
from apps.hub.operations import assess_closing, completion_requirements


def closing_dashboard_context(
    *, companies: QuerySet[ClientCompany], month: str, page: str, today: date
) -> dict[str, object]:
    error = ""
    filter_valid = True
    try:
        competence = date.fromisoformat(f"{month}-01") if month else today.replace(day=1)
    except ValueError:
        competence = today.replace(day=1)
        filter_valid = False
        error = "Competência inválida. Selecione o mês e o ano para ver os fechamentos."
    company_page = Paginator(companies.order_by("name", "pk"), 10).get_page(page)
    company_list = list(company_page.object_list)
    activities = []
    if filter_valid:
        activities = list(
            OperationalActivity.objects.filter(
                company__in=company_list,
                competence=competence,
            )
            .filter(Q(requires_processing_closed=True) | Q(requires_accepted_obligation=True))
            .select_related("assigned_to")
            .prefetch_related("evidence_items")
            .order_by("title", "pk")
        )
    labels = {
        "not_started": "Sem requisitos cadastrados",
        "blocked": "Impedido",
        "reopened": "Reabertura ou rejeição",
        "unverifiable": "Fonte a atualizar",
        "completed": "Requisitos comprovados",
        "open": "Pendente",
    }
    next_steps = {
        "blocked": "Resolva o impedimento registrado para o fechamento avançar.",
        "reopened": "Revise a reabertura ou rejeição antes de concluir.",
        "unverifiable": "Atualize a fonte ou registre uma evidência autorizada.",
        "open": "Conclua os requisitos que ainda estão pendentes.",
        "completed": "Requisitos comprovados; nenhuma ação pendente.",
        "not_started": "Cadastre os requisitos esperados para esta área.",
    }
    rows = []
    for company in company_list if filter_valid else []:
        for area, area_label in ActivityTemplate.Area.choices:
            if area not in {"accounting", "fiscal", "payroll"}:
                continue
            relevant = [
                a
                for a in activities
                if a.company_id == company.pk
                and a.area == area
                and a.organization_id == company.organization_id
            ]
            assessment = assess_closing(relevant)
            items = [
                {
                    "activity": activity,
                    "missing": completion_requirements(activity),
                    "evidence_count": len(activity.evidence_items.all()),
                }
                for activity in relevant
            ]
            actionable_activities = [
                activity
                for activity in relevant
                if completion_requirements(activity)
                or activity.work_status
                not in {
                    OperationalActivity.WorkStatus.COMPLETED,
                    OperationalActivity.WorkStatus.WAIVED,
                }
            ]
            rows.append(
                {
                    "company": company,
                    "area_label": area_label,
                    "assessment": assessment,
                    "label": labels[assessment.status],
                    "items": items,
                    "next_step": next_steps[assessment.status],
                    "next_activity": (
                        (actionable_activities or relevant)[0]
                        if actionable_activities or relevant
                        else None
                    ),
                }
            )
    configured_rows = [row for row in rows if row["items"]]
    priority = {"blocked": 0, "reopened": 1, "unverifiable": 2, "open": 3, "completed": 4}
    configured_rows.sort(
        key=lambda row: (
            priority[row["assessment"].status],
            row["company"].name.casefold(),
            row["area_label"],
        )
    )
    attention_rows = [
        row for row in configured_rows if row["assessment"].status != "completed"
    ]
    completed_rows = [
        row for row in configured_rows if row["assessment"].status == "completed"
    ]
    unconfigured_rows = [row for row in rows if not row["items"]]
    return {
        "closing_rows": rows,
        "closing_configured_rows": configured_rows,
        "closing_attention_rows": attention_rows,
        "closing_completed_rows": completed_rows,
        "closing_unconfigured_rows": unconfigured_rows,
        "closing_status_counts": {
            "attention": len(attention_rows),
            "completed": len(completed_rows),
            "coverage_gaps": len(unconfigured_rows),
        },
        "closing_page": company_page,
        "closing_month": competence.strftime("%Y-%m") if filter_valid else "",
        "closing_competence": competence,
        "closing_error": error,
        "closing_filter_valid": filter_valid,
    }
