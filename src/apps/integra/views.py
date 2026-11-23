"""Serpro screens of the office: identity and cost, and the fiscal radar (T10.6).

Behind `INTEGRA_SCREENS_ENABLED` (off by default: the routes answer 404). Cost is for owners and
administrators; the radar is for whoever may use the Central Integra Contador module.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from django.conf import settings
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.http import Http404, HttpRequest, HttpResponse
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.hub.models import ProductModule
from apps.hub.nfse_procuracao import current_office_certificate
from apps.hub.views import collaborator_can_use_module, office_required, refuse, workspace_context
from apps.integra.identity import identity_enabled
from apps.integra.models import IntegraCall, OfficeSerproIdentity
from apps.integra.radar import EVENT_LABELS, EVENTOS, radar_enabled, summary_for
from apps.organizations.models import Membership, Organization

COST_MONTHS = 6
EXPIRING_DAYS = 30
COST_ROLES = {Membership.Role.OWNER, Membership.Role.ADMIN}


def screens_enabled() -> bool:
    return bool(getattr(settings, "INTEGRA_SCREENS_ENABLED", False))


def _reais(cents: int) -> str:
    whole, fraction = divmod(int(cents), 100)
    return f"R$ {whole:,}".replace(",", ".") + f",{fraction:02d}"


def _termo_state(office: Organization, identity: OfficeSerproIdentity | None) -> dict[str, str]:
    if not identity_enabled():
        return {"label": "Desligado", "tone": "is-muted"}
    mode = identity.mode if identity else OfficeSerproIdentity.Mode.DEFAULT
    if mode == OfficeSerproIdentity.Mode.DEFAULT:
        return {"label": "Padrão", "tone": "is-muted"}
    if mode == OfficeSerproIdentity.Mode.OWN_CONTRACT:
        return {"label": "Contrato próprio", "tone": "is-active"}
    now = timezone.now()
    certificate = current_office_certificate(office.pk, now=now)
    if certificate is None:
        return {"label": "e-CNPJ ausente", "tone": "is-danger"}
    days = (certificate.valid_until - now).days
    if days <= EXPIRING_DAYS:
        plural = "s" if days != 1 else ""
        return {"label": f"e-CNPJ vence em {days} dia{plural}", "tone": "is-warning"}
    return {"label": "Termo pronto", "tone": "is-active"}


def _cost_rows(office: Organization, monthly_cap: int) -> list[dict[str, Any]]:
    since = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    since = since - timedelta(days=31 * (COST_MONTHS - 1))
    since = since.replace(day=1)
    grouped = (
        IntegraCall.objects.filter(organization=office, created_at__gte=since)
        .annotate(month=TruncMonth("created_at"))
        .values("month")
        .annotate(cost=Sum("cost_cents"), calls=Count("pk"))
        .order_by("-month")
    )
    rows = []
    for item in grouped:
        cost = int(item["cost"] or 0)
        rows.append(
            {
                "month": item["month"],
                "calls": item["calls"],
                "cost": _reais(cost),
                "share": min(100, round(cost * 100 / monthly_cap)) if monthly_cap else 0,
            }
        )
    return rows


@office_required
@require_http_methods(["GET"])
def serpro_status(request: HttpRequest) -> HttpResponse:
    if not screens_enabled():
        raise Http404
    context = workspace_context(request)
    if not collaborator_can_use_module(context, ProductModule.Code.INTEGRA):
        return refuse(request, "Seu acesso não inclui a Central Integra Contador.")
    office = context["office"]
    assert isinstance(office, Organization)
    membership = context["membership"]
    can_see_cost = isinstance(membership, Membership) and membership.role in COST_ROLES
    identity = OfficeSerproIdentity.objects.filter(organization=office).first()
    monthly_cap = identity.monthly_cap_cents if identity else 5000
    return render(
        request,
        "integra/serpro_status.html",
        {
            **context,
            "page_title": "Serpro",
            "mode_label": identity.get_mode_display() if identity else "Padrão",
            "termo": _termo_state(office, identity),
            "can_see_cost": can_see_cost,
            "cost_rows": _cost_rows(office, monthly_cap) if can_see_cost else [],
            "monthly_cap": _reais(monthly_cap),
            "radar_on": radar_enabled(),
        },
    )


@office_required
@require_http_methods(["GET"])
def serpro_radar(request: HttpRequest) -> HttpResponse:
    if not screens_enabled():
        raise Http404
    context = workspace_context(request)
    if not collaborator_can_use_module(context, ProductModule.Code.INTEGRA):
        return refuse(request, "Seu acesso não inclui a Central Integra Contador.")
    office = context["office"]
    assert isinstance(office, Organization)
    summary = summary_for(office)
    rows = [
        {
            "company": row.company,
            "cells": [(EVENT_LABELS[code], row.events.get(code)) for code in EVENTOS],
        }
        for row in summary
    ]
    denied = sum(
        1 for row in summary if any(signal.sem_procuracao for signal in row.events.values())
    )
    return render(
        request,
        "integra/serpro_radar.html",
        {
            **context,
            "page_title": "Radar fiscal",
            "rows": rows,
            "events": [(code, EVENT_LABELS[code]) for code in EVENTOS],
            "denied": denied,
            "radar_on": radar_enabled(),
        },
    )
