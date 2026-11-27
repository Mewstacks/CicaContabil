"""Telas do FAP: lotes, itens, PDF protegido e travas do escritório."""

from __future__ import annotations

from datetime import date
from typing import Any, cast
from uuid import UUID

from django.contrib import messages
from django.db.models import Q
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_POST

from apps.accounts.models import User
from apps.hub.models import ProductModule
from apps.hub.views import office_required
from apps.rpa import ui
from apps.rpa.registry import RpaError

from . import services
from .models import FapBatch, FapItem

CODE = ProductModule.Code.FAP


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
            "page_title": "FAP",
            "cfg": services.settings_for(org),
            "choices": ui.companies(context).filter(active=True).order_by("name")[:500],
            "batches": _batches(context, request).order_by("-created_at")[:30],
            "default_year": date.today().year + 1,
        }
    )
    return render(request, "fap/index.html", context)


@office_required
@require_POST
def batch_new(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_write(request, context):
        return denied
    allowed = {str(c.pk): c for c in ui.companies(context).filter(active=True)}
    chosen = [allowed[v] for v in request.POST.getlist("empresas") if v in allowed]
    try:
        batch = services.create_batch(
            organization=ui.office(context),
            user=cast(User, request.user),
            year=int(request.POST.get("vigencia", "0") or 0),
            companies=chosen,
        )
    except (services.FapError, RpaError) as exc:
        messages.error(request, getattr(exc, "message", str(exc)))
        return redirect("fap:index")
    return redirect("fap:batch", batch_id=batch.pk)


def _batches(context: dict[str, Any], request: HttpRequest) -> Any:
    """Lotes que a pessoa criou ou que têm empresa da sua carteira."""

    mine = FapItem.objects.filter(ui.scope(context), organization=ui.office(context))
    return FapBatch.objects.filter(
        Q(created_by=request.user) | Q(pk__in=mine.values("batch_id")),
        organization=ui.office(context),
    )


def _batch(context: dict[str, Any], request: HttpRequest, batch_id: UUID) -> FapBatch:
    return cast(FapBatch, get_object_or_404(_batches(context, request), pk=batch_id))


@office_required
@require_GET
def batch(request: HttpRequest, batch_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    item = _batch(context, request, batch_id)
    context.update(
        {
            "page_title": f"FAP {item.year}",
            "batch": item,
            "items": item.items.filter(ui.scope(context)).order_by("name"),
        }
    )
    return render(request, "fap/batch.html", context)


@office_required
@require_POST
def batch_action(request: HttpRequest, batch_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_write(request, context):
        return denied
    item = _batch(context, request, batch_id)
    try:
        if request.POST.get("acao") == "pausar":
            services.pause(item, user=cast(User, request.user))
        elif request.POST.get("acao") == "retomar":
            services.resume(item, user=cast(User, request.user))
    except (services.FapError, RpaError) as exc:
        messages.error(request, getattr(exc, "message", str(exc)))
    return redirect("fap:batch", batch_id=item.pk)


@office_required
@require_POST
def item_reprocess(request: HttpRequest, item_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_write(request, context):
        return denied
    item = get_object_or_404(
        FapItem.objects.filter(ui.scope(context)), pk=item_id, organization=ui.office(context)
    )
    try:
        services.reprocess(
            item, user=cast(User, request.user), reason=request.POST.get("motivo", "")
        )
    except (services.FapError, RpaError) as exc:
        messages.error(request, getattr(exc, "message", str(exc)))
    return redirect("fap:batch", batch_id=item.batch_id)


@office_required
@require_GET
def item_file(request: HttpRequest, item_id: UUID) -> HttpResponseBase:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    item = get_object_or_404(
        FapItem.objects.filter(ui.scope(context)), pk=item_id, organization=ui.office(context)
    )
    if item.pdf is None:
        raise Http404
    response = FileResponse(
        item.pdf.file.open("rb"),
        as_attachment=True,
        filename=f"FAP-{item.year}-{item.cnpj or item.code}.pdf",
        content_type="application/pdf",
    )
    response["Cache-Control"] = "private, no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["X-CICA-Content-SHA256"] = item.sha256
    return response


@office_required
@require_POST
def config(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_admin(request, context):
        return denied
    cfg = services.settings_for(ui.office(context))
    cfg.enabled = request.POST.get("liberado") == "sim"
    cfg.portal_validated = request.POST.get("portal_validado") == "sim"
    try:
        limit = int(request.POST.get("teto", cfg.batch_limit))
    except ValueError:
        limit = cfg.batch_limit
    cfg.batch_limit = min(max(limit, 0), 500)
    cfg.save()
    messages.success(request, "Guardado.")
    return redirect("fap:index")
