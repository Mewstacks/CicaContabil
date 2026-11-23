"""Triagem: the office's document type catalogue (list, create, edit, deactivate, seed).

Every query is scoped by the office of the session; a company is only reachable inside the
set the collaborator may use (``context["companies"]``). Only owner and admin write, as for
the other triage settings. ``hub/views.py`` is already huge: this module is wired in by
``hub/urls.py``.
"""

from __future__ import annotations

from typing import cast
from uuid import UUID

from django.contrib import messages
from django.db import transaction
from django.db.models import F, QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import _can_manage_collaborators, _module_page_context, office_required, refuse
from apps.organizations.models import Organization
from apps.triage.catalog import apply_default_catalog
from apps.triage.catalog_forms import CompanyExceptionForm, DocumentTypeForm
from apps.triage.models import ChecklistExpectation, DocumentType

_TEMPLATE = "hub/triage_catalog.html"


def _context(request: HttpRequest) -> tuple[dict[str, object], HttpResponse | None]:
    return _module_page_context(request, definition(ProductModule.Code.TRIAGE))


def _writer_refusal(request: HttpRequest, context: dict[str, object]) -> HttpResponse | None:
    office = cast(Organization, context["office"])
    if office.is_demo:
        return refuse(
            request, "A demonstração não altera o catálogo.", kind="unavailable"
        )
    if not _can_manage_collaborators(context):
        return refuse(request, "Somente o administrador altera o catálogo.")
    return None


def _render(
    request: HttpRequest,
    context: dict[str, object],
    *,
    form: DocumentTypeForm | None = None,
    editing: DocumentType | None = None,
    exception_form: CompanyExceptionForm | None = None,
    status: int = 200,
) -> HttpResponse:
    office = cast(Organization, context["office"])
    companies = cast("QuerySet[ClientCompany]", context["companies"])
    can_manage = _can_manage_collaborators(context) and not office.is_demo
    types = list(DocumentType.objects.filter(organization=office).order_by("-active", "label"))
    creating = form is not None and editing is None
    exceptions: list[ChecklistExpectation] = []
    if editing is not None:
        exceptions = list(
            ChecklistExpectation.objects.filter(
                organization=office, document_type=editing, company__in=companies
            )
            .select_related("company")
            .order_by("company__name")
        )
    if can_manage and (creating or editing is not None) and form is None:
        form = DocumentTypeForm(organization=office, instance=editing)
    context.update(
        {
            "page_title": "Catálogo",
            "types": types,
            "type_rows": [
                {
                    "type": row,
                    "shown_keywords": [str(word) for word in (row.keywords or [])][:4],
                    "more_keywords": max(0, len(row.keywords or []) - 4),
                    "regimes": [
                        dict(ClientCompany.TaxRegime.choices).get(code, code)
                        for code in (row.expected_regimes or [])
                    ],
                }
                for row in types
            ],
            "can_manage_catalog": can_manage,
            "form": form,
            "editing": editing,
            "creating": creating,
            "editor_open": bool(form is not None),
            "exceptions": exceptions,
            "exception_form": exception_form
            or (
                CompanyExceptionForm(companies=companies)
                if editing is not None and can_manage
                else None
            ),
        }
    )
    return render(request, _TEMPLATE, context, status=status)


@office_required
@require_http_methods(["GET"])
def triage_catalog(request: HttpRequest) -> HttpResponse:
    context, blocked = _context(request)
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    editing: DocumentType | None = None
    form: DocumentTypeForm | None = None
    type_id: UUID | None
    can_manage = _can_manage_collaborators(context) and not office.is_demo
    wanted = request.GET.get("editar", "")
    if wanted:
        try:
            type_id = UUID(wanted)
        except ValueError:
            type_id = None
        editing = get_object_or_404(DocumentType, organization=office, pk=type_id)
        if can_manage:
            form = DocumentTypeForm(organization=office, instance=editing)
    elif request.GET.get("novo") and can_manage:
        form = DocumentTypeForm(organization=office)
    return _render(request, context, form=form, editing=editing)


@office_required
@require_http_methods(["POST"])
def triage_catalog_save(request: HttpRequest) -> HttpResponse:
    context, blocked = _context(request)
    if blocked:
        return blocked
    if refusal := _writer_refusal(request, context):
        return refusal
    office = cast(Organization, context["office"])
    editing: DocumentType | None = None
    type_id = request.POST.get("type_id", "")
    if type_id:
        try:
            parsed = UUID(type_id)
        except ValueError:
            parsed = None
        editing = get_object_or_404(DocumentType, organization=office, pk=parsed)
    form = DocumentTypeForm(request.POST, organization=office, instance=editing)
    if not form.is_valid():
        return _render(request, context, form=form, editing=editing, status=400)
    data = form.cleaned_data
    fields = {
        "label": data["label"],
        "keywords": data["keywords"],
        "name_template": data["name_template"],
        "folder_template": data["folder_template"],
        "period_kind": data["period_kind"],
        "counterparty_kind": data["counterparty_kind"],
        "expected_default": bool(data["expected_default"]),
        "expected_regimes": sorted(data["expected_regimes"]),
    }
    with transaction.atomic():
        if editing is None:
            document_type = DocumentType.objects.create(
                organization=office, code=data["code"], **fields
            )
            action = "triage.catalog.type_created"
        else:
            DocumentType.objects.filter(pk=editing.pk, organization=office).update(
                revision=F("revision") + 1, **fields
            )
            document_type = DocumentType.objects.get(pk=editing.pk, organization=office)
            action = "triage.catalog.type_updated"
    record_event(
        action=action,
        actor=cast(User, request.user),
        organization=office,
        target=document_type,
        request=request,
        metadata={"code": document_type.code, "keywords": len(document_type.keywords)},
    )
    messages.success(request, "Tipo guardado.")
    return redirect("hub:triage-catalog")


@office_required
@require_http_methods(["POST"])
def triage_catalog_toggle(request: HttpRequest, type_id: UUID) -> HttpResponse:
    context, blocked = _context(request)
    if blocked:
        return blocked
    if refusal := _writer_refusal(request, context):
        return refusal
    office = cast(Organization, context["office"])
    document_type = get_object_or_404(DocumentType, organization=office, pk=type_id)
    document_type.active = not document_type.active
    document_type.save(update_fields=["active", "updated_at"])
    record_event(
        action="triage.catalog.type_toggled",
        actor=cast(User, request.user),
        organization=office,
        target=document_type,
        request=request,
        metadata={"code": document_type.code, "active": document_type.active},
    )
    messages.success(request, "Tipo ativado." if document_type.active else "Tipo desativado.")
    return redirect("hub:triage-catalog")


@office_required
@require_http_methods(["POST"])
def triage_catalog_seed(request: HttpRequest) -> HttpResponse:
    context, blocked = _context(request)
    if blocked:
        return blocked
    if refusal := _writer_refusal(request, context):
        return refusal
    office = cast(Organization, context["office"])
    created = apply_default_catalog(office)
    record_event(
        action="triage.catalog.starter_set_loaded",
        actor=cast(User, request.user),
        organization=office,
        target=office,
        request=request,
        metadata={"created": created},
    )
    messages.success(
        request, f"{len(created)} tipos carregados." if created else "Nada novo para carregar."
    )
    return redirect("hub:triage-catalog")


@office_required
@require_http_methods(["POST"])
def triage_catalog_exception(request: HttpRequest, type_id: UUID) -> HttpResponse:
    context, blocked = _context(request)
    if blocked:
        return blocked
    if refusal := _writer_refusal(request, context):
        return refusal
    office = cast(Organization, context["office"])
    document_type = get_object_or_404(DocumentType, organization=office, pk=type_id)
    form = CompanyExceptionForm(request.POST, companies=context["companies"])
    if not form.is_valid():
        return _render(
            request,
            context,
            form=DocumentTypeForm(organization=office, instance=document_type),
            editing=document_type,
            exception_form=form,
            status=400,
        )
    company = form.cleaned_data["company"]
    if form.cleaned_data["action"] == "remove":
        ChecklistExpectation.objects.filter(
            organization=office, company=company, document_type=document_type
        ).delete()
        outcome = "removed"
    else:
        ChecklistExpectation.objects.update_or_create(
            organization=office,
            company=company,
            document_type=document_type,
            defaults={"requirement": form.cleaned_data["requirement"]},
        )
        outcome = form.cleaned_data["requirement"]
    record_event(
        action="triage.catalog.company_exception",
        actor=cast(User, request.user),
        organization=office,
        target=document_type,
        request=request,
        metadata={"company_id": str(company.pk), "outcome": outcome},
    )
    messages.success(request, "Exceção removida." if outcome == "removed" else "Exceção guardada.")
    return redirect(f"{reverse('hub:triage-catalog')}?editar={document_type.pk}")
