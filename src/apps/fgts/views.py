"""Telas do FGTS Digital: apuração, lotes, emissão e itens incertos."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast
from uuid import UUID

from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_GET, require_http_methods, require_POST

from apps.accounts.models import User
from apps.hub.models import ProductModule
from apps.hub.views import office_required
from apps.rpa import ui
from apps.rpa.registry import RpaError

from . import services
from .models import FgtsItem

CODE = ProductModule.Code.FGTS


def _gate(request: HttpRequest) -> tuple[dict[str, Any], HttpResponse | None]:
    context, blocked = ui.gate(request, CODE)
    return cast("dict[str, Any]", context), blocked


def _group_visible(group: dict[str, Any], visible: set[str]) -> bool:
    """Grupo com várias empresas só é de quem enxerga TODAS elas (e ao menos uma existe)."""

    codes = {str(c) for c in group.get("codes", [])}
    return bool(codes) and codes <= {str(v) for v in visible}


def _competence(request: HttpRequest) -> tuple[int, int]:
    today = date.today()
    try:
        year, month = (int(p) for p in request.GET.get("mes", "").split("-"))
        if 1 <= month <= 12 and 2000 <= year <= 2100:
            return year, month
    except ValueError:
        pass
    year, month = (today.year, today.month - 1) if today.month > 1 else (today.year - 1, 12)
    return year, month


@office_required
@require_GET
def index(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    org = ui.office(context)
    year, month = _competence(request)
    source = services.latest_source(org, year, month)
    live = set(
        FgtsItem.objects.filter(
            organization=org, year=year, month=month, state__in=FgtsItem.BLOCKING
        ).values_list("root", flat=True)
    )
    visible = set(ui.companies(context).values_list("dominio_code", flat=True))
    wide = bool(context.get("can_admin"))
    groups = [
        g
        for g in (source.groups if source else [])
        if g["root"] not in live and (wide or _group_visible(g, visible))
    ]
    allowed, why = services.emission_allowed(org)
    context.update(
        {
            "page_title": "FGTS Digital",
            "year": year,
            "month": month,
            "month_value": f"{year}-{month:02d}",
            "source": source,
            "groups": groups,
            "items": FgtsItem.objects.filter(
                ui.scope(context), organization=org, year=year, month=month
            )
            .select_related("batch")
            .order_by("root"),
            "emission_allowed": allowed,
            "emission_blocked_reason": why,
            "cfg": services.settings_for(org),
        }
    )
    return render(request, "fgts/index.html", context)


@office_required
@require_POST
def source(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_write(request, context):
        return denied
    year, month = _competence_from(request.POST.get("mes", ""))
    try:
        services.request_source(ui.office(context), year, month)
        messages.success(request, "Consulta pedida ao agente.")
    except (services.FgtsError, RpaError) as exc:
        messages.error(request, getattr(exc, "message", str(exc)))
    return redirect(f"/app/fgts/?mes={year}-{month:02d}")


def _competence_from(value: str) -> tuple[int, int]:
    try:
        year, month = (int(p) for p in value.split("-"))
    except ValueError:
        return 0, 0
    return year, month


@office_required
@require_POST
def batch_new(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_write(request, context):
        return denied
    year, month = _competence_from(request.POST.get("mes", ""))
    try:
        deadline = datetime.strptime(request.POST.get("limite", ""), "%d/%m/%Y").date()
        roots = request.POST.getlist("raizes")
        src = services.latest_source(ui.office(context), year, month)
        visible = set(ui.companies(context).values_list("dominio_code", flat=True))
        allowed = {
            g["root"]
            for g in (src.groups if src else [])
            if context.get("can_admin") or _group_visible(g, visible)
        }
        if set(roots) - allowed:
            raise services.FgtsError("Há grupo fora da sua carteira.")
        services.create_batch(
            organization=ui.office(context),
            user=cast(User, request.user),
            year=year,
            month=month,
            deadline=deadline,
            roots=roots,
        )
    except ValueError:
        messages.error(request, "Informe a data limite como DD/MM/AAAA.")
    except (services.FgtsError, RpaError) as exc:
        messages.error(request, getattr(exc, "message", str(exc)))
    return redirect(f"/app/fgts/?mes={year}-{month:02d}")


@office_required
@require_POST
def item_action(request: HttpRequest, item_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_write(request, context):
        return denied
    item = get_object_or_404(
        FgtsItem.objects.filter(ui.scope(context)), pk=item_id, organization=ui.office(context)
    )
    user = cast(User, request.user)
    action = request.POST.get("acao", "")
    try:
        if action == "emitir":
            services.request_emission(item, user=user)
        elif action == "resolver":
            upload = request.FILES.get("pdf")
            services.resolve_uncertain(
                item,
                user=user,
                issued=request.POST.get("emitida") == "sim",
                note=request.POST.get("conferido", ""),
                pdf=upload.read(services.MAX_PDF + 1) if upload else None,
            )
        elif action == "revisar":
            services.mark_reviewed(item, user=user)
        else:
            messages.error(request, "Ação desconhecida.")
    except (services.FgtsError, RpaError) as exc:
        messages.error(request, getattr(exc, "message", str(exc)))
    return redirect(f"/app/fgts/?mes={item.year}-{item.month:02d}")


@office_required
@require_http_methods(["POST"])
def config(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_admin(request, context):
        return denied
    cfg = services.settings_for(ui.office(context))
    cfg.source_validated = request.POST.get("fonte_validada") == "sim"
    cfg.emission_enabled = request.POST.get("emissao") == "sim"
    cfg.save()
    messages.success(request, "Guardado.")
    return redirect("fgts:index")
