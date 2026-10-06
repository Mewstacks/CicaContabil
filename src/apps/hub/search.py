"""Workspace search (D-277): companies, activities and NFS-e inside the person's portfolio.

The caller passes querysets already limited by office, portfolio and module; this module only
matches and shapes results. Queries are not logged.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from django.db.models import F, Q, QuerySet, Value
from django.db.models.functions import Coalesce, Replace
from django.urls import reverse

from apps.hub.models import ClientCompany, NfseDocument, OperationalActivity

RESULTS_PER_GROUP = 6
MIN_QUERY_LENGTH = 2


@dataclass(frozen=True)
class SearchResult:
    title: str
    detail: str
    url: str


@dataclass(frozen=True)
class SearchGroup:
    label: str
    results: list[SearchResult]


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value)


def search_workspace(
    *,
    query: str,
    companies: QuerySet[ClientCompany],
    activities: QuerySet[OperationalActivity],
    documents: QuerySet[NfseDocument] | None,
) -> list[SearchGroup]:
    query = query.strip()[:80]
    if len(query) < MIN_QUERY_LENGTH:
        return []
    digits = _digits(query)
    company_match = Q(name__icontains=query) | Q(dominio_code__iexact=query)
    company_rows = companies
    if len(digits) >= 3:
        company_rows = company_rows.annotate(
            cnpj_digits=Replace(
                Replace(Replace("cnpj_masked", Value("."), Value("")), Value("/"), Value("")),
                Value("-"),
                Value(""),
            )
        )
        company_match |= Q(cnpj_digits__contains=digits)
    groups: list[SearchGroup] = []
    found_companies = [
        SearchResult(
            title=company.name,
            detail=" · ".join(
                part
                for part in (
                    company.cnpj_masked,
                    f"Domínio {company.dominio_code}" if company.dominio_code else "",
                    company.get_tax_regime_display() if company.tax_regime else "",
                )
                if part
            ),
            url=reverse("hub:company-detail", args=[company.pk]),
        )
        for company in company_rows.filter(company_match).order_by("name")[:RESULTS_PER_GROUP]
    ]
    if found_companies:
        groups.append(SearchGroup("Empresas", found_companies))
    found_activities = [
        SearchResult(
            title=activity.title,
            detail=" · ".join(
                part
                for part in (
                    activity.company.name,
                    f"{activity.competence:%m/%Y}" if activity.competence else "",
                    activity.get_work_status_display(),
                )
                if part
            ),
            url=reverse("hub:activity-detail", args=[activity.pk]),
        )
        for activity in activities.filter(
            Q(title__icontains=query) | Q(company__name__icontains=query)
        )
        .exclude(
            work_status__in=[
                OperationalActivity.WorkStatus.COMPLETED,
                OperationalActivity.WorkStatus.WAIVED,
            ]
        )
        .select_related("company")
        .order_by(Coalesce("internal_due_on", "legal_due_on").asc(nulls_last=True), F("pk"))[
            :RESULTS_PER_GROUP
        ]
    ]
    if found_activities:
        groups.append(SearchGroup("Atividades", found_activities))
    if documents is not None and (digits or len(query) >= 3):
        found_documents = [
            SearchResult(
                title=f"NFS-e {document.normalized_data.get('number', '')}".strip(),
                detail=document.company.name,
                url=(
                    f"{reverse('hub:nfse-center')}?company={document.company_id}"
                    f"&q={document.normalized_data.get('number', '')}"
                ),
            )
            for document in documents.filter(normalized_data__number=query)
            .select_related("company")
            .order_by("-captured_at")[:RESULTS_PER_GROUP]
            if isinstance(document.normalized_data, dict)
        ]
        if found_documents:
            groups.append(SearchGroup("Notas", found_documents))
    return groups
