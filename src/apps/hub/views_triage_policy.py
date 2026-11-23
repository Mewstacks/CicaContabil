"""Triagem: the office's intake switches (extra formats, ZIP, OCR) and OCR page budget."""

from __future__ import annotations

from typing import cast

from django import forms
from django.contrib import messages
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import _can_manage_collaborators, _module_page_context, office_required, refuse
from apps.organizations.models import Organization
from apps.triage.models import TriagePolicy
from apps.triage.reclassify import bump_engine_version


class PolicyForm(forms.Form):
    extended_formats = forms.BooleanField(required=False, label="Imagem, HTML, TXT e XLS")
    open_archives = forms.BooleanField(required=False, label="Abrir ZIP")
    ocr_enabled = forms.BooleanField(required=False, label="OCR")
    ocr_monthly_pages = forms.IntegerField(
        min_value=0, max_value=100_000, required=False, label="Páginas de OCR por mês"
    )
    auto_approve = forms.BooleanField(required=False, label="Aprovar sozinho")
    auto_sample_every = forms.IntegerField(
        min_value=1, max_value=1000, required=False, label="Amostra para revisão (1 a cada)"
    )
    auto_warmup = forms.IntegerField(
        min_value=0, max_value=10_000, required=False, label="Revisões humanas antes"
    )


@office_required
@require_http_methods(["GET", "POST"])
def triage_policy(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    can_manage = _can_manage_collaborators(context) and not office.is_demo
    current = TriagePolicy.objects.filter(organization=office).first()
    initial = {
        "extended_formats": current.extended_formats if current else False,
        "open_archives": current.open_archives if current else False,
        "ocr_enabled": current.ocr_enabled if current else False,
        "ocr_monthly_pages": current.ocr_monthly_pages if current else 100,
        "auto_approve": current.auto_approve if current else False,
        "auto_sample_every": current.auto_sample_every if current else 20,
        "auto_warmup": current.auto_warmup if current else 30,
    }
    if request.method == "POST":
        if not can_manage:
            return refuse(request, "Somente o administrador altera a entrada.")
        if request.POST.get("action") == "reclassify":
            version = bump_engine_version(office)
            record_event(
                action="triage.engine.reclassified",
                actor=cast(User, request.user),
                organization=office,
                target=office,
                request=request,
                metadata={"engine_version": version},
            )
            messages.success(request, f"Reclassificado. Motor v{version}.")
            return redirect("hub:triage-policy")
        form = PolicyForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            pages = data["ocr_monthly_pages"]
            policy, _ = TriagePolicy.objects.update_or_create(
                organization=office,
                defaults={
                    "extended_formats": data["extended_formats"],
                    "open_archives": data["open_archives"],
                    "ocr_enabled": data["ocr_enabled"],
                    "ocr_monthly_pages": pages if pages is not None else 100,
                    "auto_approve": data["auto_approve"],
                    "auto_sample_every": data["auto_sample_every"] or 20,
                    "auto_warmup": (data["auto_warmup"] if data["auto_warmup"] is not None else 30),
                },
            )
            record_event(
                action="triage.policy.updated",
                actor=cast(User, request.user),
                organization=office,
                target=policy,
                request=request,
                metadata={
                    "extended_formats": policy.extended_formats,
                    "open_archives": policy.open_archives,
                    "ocr_enabled": policy.ocr_enabled,
                    "ocr_monthly_pages": policy.ocr_monthly_pages,
                    "auto_approve": policy.auto_approve,
                    "auto_sample_every": policy.auto_sample_every,
                    "auto_warmup": policy.auto_warmup,
                },
            )
            messages.success(request, "Entrada guardada.")
            return redirect("hub:triage-policy")
        status = 400
    else:
        form = PolicyForm(initial=initial)
        status = 200
    context.update(
        {
            "page_title": "Entrada",
            "form": form,
            "can_manage_policy": can_manage,
            "engine_version": current.engine_version if current else 1,
        }
    )
    return render(request, "hub/triage_policy.html", context, status=status)
