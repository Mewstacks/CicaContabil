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
    try:
        competence = date.fromisoformat(f"{month}-01") if month else today.replace(day=1)
    except ValueError:
        competence = today.replace(day=1)
        error = "Competência inválida. Selecione o mês e o ano; exibindo o mês corrente."
    company_page = Paginator(companies.order_by("name", "pk"), 10).get_page(page)
    company_list = list(company_page.object_list)
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
    rows = []
    for company in company_list:
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
            rows.append(
                {
                    "company": company,
                    "area_label": area_label,
                    "assessment": assessment,
                    "label": labels[assessment.status],
                    "items": [
                        {
                            "activity": a,
                            "missing": completion_requirements(a),
                            "evidence_count": len(a.evidence_items.all()),
                        }
                        for a in relevant
                    ],
                }
            )
    return {
        "closing_rows": rows,
        "closing_configured_rows": [row for row in rows if row["items"]],
        "closing_unconfigured_rows": [row for row in rows if not row["items"]],
        "closing_page": company_page,
        "closing_month": competence.strftime("%Y-%m"),
        "closing_competence": competence,
        "closing_error": error,
    }
