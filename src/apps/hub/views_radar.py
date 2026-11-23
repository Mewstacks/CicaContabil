"""Radar Simples/MEI (E14): receita de serviço por NFS-e contra o teto, por empresa."""

from __future__ import annotations

import csv
from datetime import date
from decimal import Decimal
from typing import cast

from django.conf import settings
from django.db.models import QuerySet
from django.http import Http404, HttpRequest, HttpResponse
from django.http.response import HttpResponseBase
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_GET

from apps.hub import simples_radar
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.views import collaborator_can_use_module, office_required, refuse, workspace_context
from apps.organizations.models import Organization

FILTERS = (("all", "Todas"), ("alert", "Com alerta"), ("mei", "MEI"), ("simples", "Simples"))
ALERT_BADGE = {None: "is-active", 80: "is-warning", 90: "is-warning", 100: "is-danger"}


def _money(value: Decimal) -> str:
    return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _csv(rows: list[simples_radar.RadarRow], today: date) -> HttpResponse:
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="radar-teto-{today:%Y-%m-%d}.csv"'
    response.write("﻿")
    writer = csv.writer(response, delimiter=";")
    writer.writerow(
        ["Empresa", "Regime", "Receita no ano", "Últimos 12 meses", "Teto", "% do teto", "Alerta"]
    )
    for row in rows:
        writer.writerow(
            [
                _cell(row.company_name),
                row.regime.upper(),
                _money(row.year_revenue),
                _money(row.trailing_12m),
                _money(row.limit),
                str(row.percent).replace(".", ","),
                f"{row.alert}%" if row.alert else "",
            ]
        )
    return response


def _cell(value: str) -> str:
    """Nome de empresa vai para planilha: fórmula não pode executar na abertura."""

    return f"'{value}" if value[:1] in {"=", "+", "-", "@", "\t", "\r"} else value


@office_required
@require_GET
def simples_radar_view(request: HttpRequest) -> HttpResponseBase:
    if not getattr(settings, "SIMPLES_RADAR_ENABLED", False):
        raise Http404
    context = workspace_context(request)
    if not collaborator_can_use_module(context, ProductModule.Code.NFSE):
        return refuse(request, "Seu acesso não inclui NFS-e Inteligente.")
    office = context["office"]
    assert isinstance(office, Organization)
    today = timezone.localdate()
    scope = cast("QuerySet[ClientCompany]", context["companies"])
    rows = simples_radar.portfolio(office, today, scope)
    tab = request.GET.get("filtro", "all")
    if tab not in {key for key, _label in FILTERS}:
        tab = "all"
    shown = [
        row for row in rows if tab == "all" or (tab == "alert" and row.alert) or row.regime == tab
    ]
    if request.GET.get("export") == "csv":
        return _csv(shown, today)
    counts = {
        "all": len(rows),
        "alert": sum(1 for row in rows if row.alert),
        "mei": sum(1 for row in rows if row.regime == "mei"),
        "simples": sum(1 for row in rows if row.regime == "simples"),
    }
    context.update(
        {
            "page_title": "Teto",
            "nfse_view": "radar",
            "rows": [(row, ALERT_BADGE[row.alert]) for row in shown],
            "tabs": [
                {"key": key, "label": label, "count": counts[key], "current": key == tab}
                for key, label in FILTERS
            ],
            "tab": tab,
            "today": today,
            "has_unconfirmed_limit": any(not row.limit_confirmed for row in rows),
        }
    )
    return render(request, "hub/simples_radar.html", context)
