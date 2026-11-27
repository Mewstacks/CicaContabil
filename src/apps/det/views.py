"""Telas do DET: escolher empresas, acompanhar a consulta e baixar a planilha."""

from __future__ import annotations

from typing import Any, cast
from uuid import UUID

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.hub.models import ProductModule
from apps.hub.views import office_required
from apps.rpa import ui
from apps.rpa.models import RpaJob
from apps.rpa.registry import RpaError

from . import services
from .models import DetQuery

CODE = ProductModule.Code.DET


def _gate(request: HttpRequest) -> tuple[dict[str, Any], HttpResponse | None]:
    context, blocked = ui.gate(request, CODE)
    return cast("dict[str, Any]", context), blocked


@office_required
@require_GET
def index(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    org = ui.office(context)
    context.update(
        {
            "page_title": "DET",
            "choices": ui.companies(context)
            .filter(active=True)
            .exclude(cnpj_masked="")
            .order_by("name")[:2000],
            "queries": DetQuery.objects.filter(organization=org).order_by("-created_at")[:30],
        }
    )
    return render(request, "det/index.html", context)


@office_required
@require_POST
def query_new(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_write(request, context):
        return denied
    allowed = {str(c.pk): c for c in ui.companies(context).filter(active=True)}
    chosen = [allowed[v] for v in request.POST.getlist("empresas") if v in allowed]
    try:
        query = services.create_query(
            organization=ui.office(context), user=cast(User, request.user), companies=chosen
        )
    except services.DetError as exc:
        messages.error(request, str(exc))
        return redirect("det:index")
    except RpaError as exc:
        messages.error(request, exc.message)
        return redirect("det:index")
    return redirect("det:query", query_id=query.pk)


def _load(context: dict[str, Any], query_id: UUID) -> DetQuery:
    return get_object_or_404(DetQuery, pk=query_id, organization=ui.office(context))


@office_required
@require_GET
def query(request: HttpRequest, query_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    item = _load(context, query_id)
    waiting = [
        c.job
        for c in item.chunks.select_related("job")
        if c.job is not None and c.job.state == RpaJob.State.LEASED and c.job.phase == "atencao"
    ]
    context.update(
        {
            "page_title": "DET · Consulta",
            "query": item,
            "results": item.results.order_by("company_code"),
            "waiting_for_person": bool(waiting),
            "done_count": item.results.count(),
            "total": len(item.companies),
        }
    )
    return render(request, "det/query.html", context)


@office_required
@require_GET
def sheet(request: HttpRequest, query_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    item = _load(context, query_id)
    response = HttpResponse(
        services.workbook(item),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = (
        f'attachment; filename="det-{item.created_at:%Y%m%d-%H%M}.xlsx"'
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response
