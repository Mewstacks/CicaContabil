"""Triagem: manual upload (one or many files) into the normal quarantine pipeline."""

from __future__ import annotations

from typing import Any, cast

from django import forms
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from apps.accounts.models import User
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import _can_manage_collaborators, _module_page_context, office_required, refuse
from apps.organizations.models import Organization
from apps.triage.intake_policy import policy_for
from apps.triage.models import DocumentType
from apps.triage.upload import receive_upload

MAX_FILES_PER_UPLOAD = 20


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("widget", MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data: Any, initial: Any = None) -> Any:
        single = super().clean
        if isinstance(data, list | tuple):
            return [single(item, initial) for item in data]
        return [single(data, initial)]


class UploadForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=ClientCompany.objects.none(), required=False, label="Empresa"
    )
    document_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.none(), required=False, label="Tipo"
    )
    documents = MultipleFileField(label="Arquivos")

    def __init__(
        self, *args: Any, organization: Organization, companies: Any, require_company: bool,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        company_field = cast("forms.ModelChoiceField[ClientCompany]", self.fields["company"])
        company_field.queryset = companies.filter(organization=organization, active=True).order_by(
            "name"
        )
        company_field.empty_label = "Identificar sozinha"
        company_field.required = require_company
        if require_company:
            company_field.empty_label = "Escolha"
        type_field = cast("forms.ModelChoiceField[DocumentType]", self.fields["document_type"])
        type_field.queryset = DocumentType.objects.filter(
            organization=organization, active=True
        ).order_by("label")
        type_field.empty_label = "Identificar sozinho"

    def clean_documents(self) -> list[Any]:
        files = self.cleaned_data["documents"]
        if len(files) > MAX_FILES_PER_UPLOAD:
            raise forms.ValidationError(f"No máximo {MAX_FILES_PER_UPLOAD} arquivos por envio.")
        return list(files)


@office_required
@require_http_methods(["GET", "POST"])
def triage_upload(request: HttpRequest) -> HttpResponse:
    context, blocked = _module_page_context(request, definition(ProductModule.Code.TRIAGE))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    if request.method == "POST":
        if office.is_demo:
            return refuse(request, "A demonstração não recebe arquivos.", kind="unavailable")
        if not context["support_can_mutate"]:
            return refuse(request, "Este perfil não pode enviar arquivos.")
    # Items without a company are visible to administrators only: others must pick one.
    require_company = not _can_manage_collaborators(context)
    form = UploadForm(
        request.POST or None,
        request.FILES or None,
        organization=office,
        companies=context["companies"],
        require_company=require_company,
    )
    status = 200
    if request.method == "POST":
        if form.is_valid():
            received = 0
            for upload in form.cleaned_data["documents"]:
                try:
                    receive_upload(
                        organization=office,
                        actor=cast(User, request.user),
                        upload=upload,
                        company=form.cleaned_data["company"],
                        document_type=form.cleaned_data["document_type"],
                        request=request,
                    )
                    received += 1
                except ValidationError as exc:
                    messages.error(request, " ".join(exc.messages))
            if received:
                messages.success(
                    request, f"{received} arquivo{'s' if received != 1 else ''} recebido"
                    f"{'s' if received != 1 else ''}."
                )
                return redirect("hub:triage")
            status = 400
        else:
            status = 400
    context.update(
        {
            "page_title": "Enviar arquivo",
            "form": form,
            "accepted": sorted(policy_for(office).suffixes),
            "max_files": MAX_FILES_PER_UPLOAD,
        }
    )
    return render(request, "hub/triage_upload.html", context, status=status)
