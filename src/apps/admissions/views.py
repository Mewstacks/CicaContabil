"""Telas das Admissões: ficha, revisão campo a campo, execução e retenção."""

from __future__ import annotations

import re
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
from apps.rpa.registry import RpaError

from . import services
from .models import Admission

CODE = ProductModule.Code.ADMISSIONS
SCALARS = [
    k
    for k in (*services.REQUIRED, *services.REQUIRED_REAL_COMPANY, "rg", "pis", "email", "phone")
    if k != "salary_cents"
]


def _gate(request: HttpRequest) -> tuple[dict[str, Any], HttpResponse | None]:
    context, blocked = ui.gate(request, CODE)
    return cast("dict[str, Any]", context), blocked


def _money_to_cents(text: str) -> int | str:
    cleaned = text.strip().replace(".", "").replace(",", ".")
    try:
        return round(float(cleaned) * 100) if cleaned else ""
    except ValueError:
        return -1


def _lines(text: str, size: int) -> list[list[str]]:
    rows = []
    for line in text.splitlines():
        parts = [p.strip() for p in line.split(";")]
        if any(parts):
            rows.append((parts + [""] * size)[:size])
    return rows


def _collect(post: Any) -> dict[str, Any]:
    data: dict[str, Any] = {k: post.get(k, "").strip() for k in SCALARS}
    data["salary_cents"] = _money_to_cents(post.get("salary", ""))
    data["has_children"] = "SIM" if post.get("has_children") == "SIM" else "NAO"
    data["transport_voucher"] = "SIM" if post.get("transport_voucher") == "SIM" else "NAO"
    data["dependents"] = [
        {"cpf": c, "birth_date": b, "name": n} for c, b, n in _lines(post.get("dependents", ""), 3)
    ]
    data["transports"] = [
        {"line": line, "unit": unit, "start": start}
        for line, unit, start in _lines(post.get("transports", ""), 3)
    ]
    return data


@office_required
@require_GET
def index(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    org = ui.office(context)
    context.update(
        {
            "page_title": "Admissões",
            "cfg": services.settings_for(org),
            "choices": ui.companies(context).filter(active=True).order_by("name")[:500],
            "items": Admission.objects.filter(ui.scope(context), organization=org)
            .select_related("company")
            .order_by("-created_at")[:30],
        }
    )
    return render(request, "admissions/index.html", context)


@office_required
@require_POST
def new(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_write(request, context):
        return denied
    company = get_object_or_404(
        ui.companies(context).filter(active=True), pk=request.POST.get("empresa")
    )
    upload = request.FILES.get("ficha")
    try:
        admission = services.create(
            organization=ui.office(context),
            user=cast(User, request.user),
            company=company,
            upload=upload.read(services.MAX_UPLOAD + 1) if upload else None,
            original_name=upload.name if upload and upload.name else "",
        )
    except services.AdmissionError as exc:
        messages.error(request, str(exc))
        return redirect("admissions:index")
    return redirect("admissions:detail", admission_id=admission.pk)


def _load(context: dict[str, Any], admission_id: UUID) -> Admission:
    return get_object_or_404(
        Admission.objects.select_related("company").filter(ui.scope(context)),
        pk=admission_id,
        organization=ui.office(context),
    )


@office_required
@require_GET
def detail(request: HttpRequest, admission_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    item = _load(context, admission_id)
    data = item.data
    allowed, why = services.execution_allowed(item)
    context.update(
        {
            "page_title": f"Admissão · {item.company.name}",
            "item": item,
            "fields": [
                (k, services.LABELS[k], data.get(k, "")) for k in SCALARS if k in services.LABELS
            ],
            "salary": f"{data['salary_cents'] / 100:.2f}".replace(".", ",")
            if isinstance(data.get("salary_cents"), int) and data["salary_cents"] > 0
            else "",
            "dependents_text": "\n".join(
                f"{d.get('cpf', '')};{d.get('birth_date', '')};{d.get('name', '')}"
                for d in data.get("dependents", [])
            ),
            "transports_text": "\n".join(
                f"{t.get('line', '')};{t.get('unit', '')};{t.get('start', '')}"
                for t in data.get("transports", [])
            ),
            "has_children": data.get("has_children") == "SIM",
            "transport_voucher": data.get("transport_voucher") == "SIM",
            "can_execute": allowed,
            "execute_blocked_reason": why,
            "is_example": services.is_example(item),
        }
    )
    return render(request, "admissions/detail.html", context)


@office_required
@require_POST
def action(request: HttpRequest, admission_id: UUID) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_write(request, context):
        return denied
    item = _load(context, admission_id)
    user = cast(User, request.user)
    what = request.POST.get("acao", "")
    try:
        if what == "salvar":
            pending = services.save_review(item, user=user, data=_collect(request.POST))
            if pending:
                messages.warning(request, "Falta: " + ", ".join(pending))
        elif what == "executar":
            services.execute(item, user=user, example_confirmed=request.POST.get("teste") == "sim")
        elif what == "cancelar":
            services.cancel(item, user=user)
        elif what == "resolver":
            services.resolve_uncertain(
                item,
                user=user,
                registered=request.POST.get("cadastrado") == "sim",
                domain_code=re.sub(r"\D", "", request.POST.get("codigo", "")),
                note=request.POST.get("conferido", ""),
            )
    except (services.AdmissionError, RpaError) as exc:
        messages.error(request, getattr(exc, "message", str(exc)))
    return redirect("admissions:detail", admission_id=item.pk)


@office_required
@require_POST
def config(request: HttpRequest) -> HttpResponse:
    context, blocked = _gate(request)
    if blocked:
        return blocked
    if denied := ui.need_admin(request, context):
        return denied
    cfg = services.settings_for(ui.office(context))
    codes = [c.strip() for c in request.POST.get("autorizadas", "").replace("\n", ",").split(",")]
    cfg.allowed_codes = sorted({c for c in codes if c and c != "*"})[:500]
    cfg.execution_enabled = request.POST.get("execucao") == "sim"
    cfg.example_code = request.POST.get("exemplo", "").strip()[:64]
    cfg.save()
    messages.success(request, "Guardado.")
    return redirect("admissions:index")
