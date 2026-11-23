"""Forms of the office's document type catalogue (scoped by the office passed in)."""

from __future__ import annotations

import re
from typing import Any, cast

from django import forms
from django.utils.text import slugify

from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage.catalog import parse_keywords, validate_folder_template
from apps.triage.models import ChecklistExpectation, DocumentType

NAME_FIELDS = ("codigo", "periodo", "contraparte")


class DocumentTypeForm(forms.Form):
    label = forms.CharField(max_length=160, label="Nome")
    code = forms.CharField(max_length=64, required=False, label="Código")
    keywords = forms.CharField(
        required=False,
        label="Palavras-chave",
        widget=forms.Textarea(attrs={"rows": 3, "placeholder": "vírgula separa"}),
    )
    name_template = forms.CharField(
        max_length=200,
        label="Nome do arquivo",
        widget=forms.TextInput(attrs={"placeholder": "{codigo}_EXTRATO_{periodo}"}),
    )
    folder_template = forms.CharField(
        max_length=200,
        required=False,
        label="Pasta",
        widget=forms.TextInput(attrs={"placeholder": r"{company_name}\Extratos\{period}"}),
    )
    period_kind = forms.ChoiceField(choices=DocumentType.PeriodKind.choices, label="Período")
    counterparty_kind = forms.ChoiceField(
        choices=DocumentType.CounterpartyKind.choices, required=False, label="Contraparte"
    )
    expected_default = forms.BooleanField(required=False, label="Todas as empresas")
    expected_regimes = forms.MultipleChoiceField(
        choices=ClientCompany.TaxRegime.choices,
        required=False,
        label="Regimes",
        widget=forms.CheckboxSelectMultiple,
    )

    def __init__(
        self,
        *args: Any,
        organization: Organization,
        instance: DocumentType | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.organization = organization
        self.instance = instance
        if instance is not None and not self.is_bound:
            self.initial.update(
                {
                    "label": instance.label,
                    "code": instance.code,
                    "keywords": ", ".join(str(word) for word in instance.keywords or []),
                    "name_template": instance.name_template,
                    "folder_template": instance.folder_template,
                    "period_kind": instance.period_kind,
                    "counterparty_kind": instance.counterparty_kind,
                    "expected_default": instance.expected_default,
                    "expected_regimes": list(instance.expected_regimes or []),
                }
            )
        for name in ("label", "name_template", "folder_template", "code"):
            self.fields[name].widget.attrs.update({"autocomplete": "off", "spellcheck": "false"})

    def clean_label(self) -> str:
        label = " ".join(str(self.cleaned_data["label"]).split())
        if not label:
            raise forms.ValidationError("Informe o nome.")
        return label

    def clean_name_template(self) -> str:
        template = str(self.cleaned_data["name_template"]).strip()
        fields = set(re.findall(r"{([^{}]*)}", template))
        literal = re.sub(r"{[^{}]*}", "", template)
        if (
            not template
            or fields - set(NAME_FIELDS)
            or "{" in literal
            or "}" in literal
            or any(char in literal for char in '<>:"/\\|?*\x00')
        ):
            raise forms.ValidationError("Use {codigo}, {periodo} e {contraparte}.")
        return template

    def clean_folder_template(self) -> str:
        value = str(self.cleaned_data.get("folder_template") or "").strip()
        return validate_folder_template(value) if value else ""

    def clean_keywords(self) -> list[str]:
        return parse_keywords(str(self.cleaned_data.get("keywords") or ""))

    def clean_counterparty_kind(self) -> str:
        return str(self.cleaned_data.get("counterparty_kind") or DocumentType.CounterpartyKind.NONE)

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if self.instance is not None:
            cleaned["code"] = self.instance.code  # the code is the type's identity
            return cleaned
        code = slugify(str(cleaned.get("code") or "") or str(cleaned.get("label") or ""))[:64]
        if not code:
            self.add_error("code", "Informe um código.")
        elif DocumentType.objects.filter(organization=self.organization, code=code).exists():
            self.add_error("code", "Este código já existe.")
        cleaned["code"] = code
        return cleaned


class CompanyExceptionForm(forms.Form):
    company = forms.ModelChoiceField(queryset=ClientCompany.objects.none(), label="Empresa")
    requirement = forms.ChoiceField(
        choices=ChecklistExpectation.Requirement.choices, required=False, label="Regra"
    )
    action = forms.ChoiceField(choices=(("save", "Guardar"), ("remove", "Remover")))

    def __init__(self, *args: Any, companies: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        cast("forms.ModelChoiceField[ClientCompany]", self.fields["company"]).queryset = (
            companies.order_by("name")
        )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if cleaned.get("action") == "save" and not cleaned.get("requirement"):
            self.add_error("requirement", "Escolha a regra.")
        return cleaned
