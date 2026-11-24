"""Triagem: the delivery checklist (company x type x period) and the client request draft.

Read-only. Companies come from the collaborator's own scope (``context["companies"]``) and
are filtered by the office again, so no other office's company can appear. The draft is text
for a person to send; this module never sends anything.
"""

from __future__ import annotations

from typing import cast
from urllib.parse import quote, urlencode
from uuid import UUID

from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import _module_page_context, office_required
from apps.organizations.models import Organization
from apps.triage.checklist import (
    build_checklist,
    parse_period,
    period_label,
    request_draft,
    shift_period,
)

PAGE_SIZE = 25


def _current_period() -> str:
    return timezone.localdate().strftime("%Y-%m")


@office_required
@require_http_methods(["GET"])
def triage_checklist(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    period = parse_period(request.GET.get("periodo")) or _current_period()
    pending_only = request.GET.get("pendentes") == "1"
    query = request.GET.get("q", "").strip()[:100]
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    if query:
        companies = companies.filter(name__icontains=query)
    checklist = build_checklist(office, companies, period, timezone.localdate())
    has_types = _has_types(office)
    rows = (
        [row for row in checklist.rows if not pending_only or row.percent < 100]
        if has_types
        else []
    )
    page = Paginator(rows, PAGE_SIZE).get_page(request.GET.get("page"))
    base = {"pendentes": "1"} if pending_only else {}
    if query:
        base["q"] = query
    context.update(
        {
            "page_title": "Checklist",
            "checklist": checklist,
            "period": period,
            "period_label": period_label(period),
            "previous_url": "?" + urlencode({**base, "periodo": shift_period(period, -1)}),
            "next_url": "?" + urlencode({**base, "periodo": shift_period(period, 1)}),
            "page": page,
            "pending_only": pending_only,
            "query": query,
            "has_types": has_types,
            "querystring": urlencode({**base, "periodo": period}),
        }
    )
    return render(request, "hub/triage_checklist.html", context)


def _has_types(office: Organization) -> bool:
    from apps.triage.models import DocumentType

    return DocumentType.objects.filter(organization=office, active=True).exists()


@office_required
@require_http_methods(["GET"])
def triage_checklist_request(request: HttpRequest, company_id: UUID) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    period = parse_period(request.GET.get("periodo")) or _current_period()
    scoped = cast("QuerySet[ClientCompany]", context["companies"]).filter(
        organization=office, pk=company_id
    )
    checklist = build_checklist(office, scoped, period, timezone.localdate())
    if not checklist.rows:
        raise Http404
    row = checklist.rows[0]
    draft = request_draft(row, period)
    mailto = ""
    if draft.to and draft.body:
        mailto = f"mailto:{quote(draft.to, safe="@")}?" + urlencode(
            {"subject": draft.subject, "body": draft.body}, quote_via=quote
        )
    context.update(
        {
            "page_title": "Pedido ao cliente",
            "row": row,
            "draft": draft,
            "mailto": mailto,
            "period": period,
            "period_label": period_label(period),
            "back_url": reverse("hub:triage-checklist") + "?" + urlencode({"periodo": period}),
        }
    )
    return render(request, "hub/triage_checklist_request.html", context)
