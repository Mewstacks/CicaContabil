"""Formulários do Contraprova."""

from __future__ import annotations

from datetime import date
from typing import Any

from django import forms
from django.db.models import QuerySet
from django.utils import timezone

from apps.hub.models import ClientCompany

from .engine.rules import (
    DEFAULT_ICMS51_CFOPS,
    DEFAULT_NO_CREDIT_CFOPS,
    DEFAULT_SPED_SPED_FIELDS,
    DEFAULT_SPED_XML_FIELDS,
    OPERATIONS,
    SPED_SPED_FIELDS,
    SPED_XML_FIELDS,
    build_rules,
)
from .engine.tools import SPED_SPED, SPED_XML, TOOLS, choices

CFOP_HELP = "Separe por vírgula"


def previous_month(today: date | None = None) -> date:
    today = today or timezone.localdate()
    year, month = (today.year - 1, 12) if today.month == 1 else (today.year, today.month - 1)
    return date(year, month, 1)


class MonthField(forms.Field):
    """`<input type="month">`: AAAA-MM, devolvido como o primeiro dia do mês."""

    widget = forms.DateInput(attrs={"type": "month"}, format="%Y-%m")

    def to_python(self, value: Any) -> date | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            year, month = text.split("-")
            return date(int(year), int(month), 1)
        except (ValueError, TypeError) as exc:
            raise forms.ValidationError("Informe a competência no formato mês/ano.") from exc


class NewRunForm(forms.Form):
    tool = forms.ChoiceField(choices=choices(), widget=forms.RadioSelect, label="Ferramenta")
    company = forms.ModelChoiceField(queryset=ClientCompany.objects.none(), label="Empresa")
    competence = MonthField(label="Competência")
    tolerance_cents = forms.IntegerField(
        label="Tolerância", min_value=0, max_value=1000, initial=1, required=False
    )
    operation = forms.ChoiceField(
        choices=list(OPERATIONS.items()), initial="E", label="Operação", required=False
    )
    fields_xml = forms.MultipleChoiceField(
        choices=list(SPED_XML_FIELDS.items()),
        initial=list(DEFAULT_SPED_XML_FIELDS),
        widget=forms.CheckboxSelectMultiple,
        label="Campos",
        required=False,
    )
    fields_sped = forms.MultipleChoiceField(
        choices=[(code, label) for code, (label, _kind) in SPED_SPED_FIELDS.items()],
        initial=list(DEFAULT_SPED_SPED_FIELDS),
        widget=forms.CheckboxSelectMultiple,
        label="Campos",
        required=False,
    )
    no_credit_cfops = forms.CharField(
        initial=", ".join(sorted(DEFAULT_NO_CREDIT_CFOPS)),
        label="CFOP sem crédito",
        required=False,
        max_length=200,
    )
    icms51_cfops = forms.CharField(
        initial=", ".join(sorted(DEFAULT_ICMS51_CFOPS)),
        label="CFOP do ICMS 51",
        required=False,
        max_length=200,
    )
    include_analytic = forms.BooleanField(initial=True, label="Analítico", required=False)
    dominio_source = forms.ChoiceField(
        choices=[("arquivo", "Arquivo"), ("agente", "Agente")],
        initial="arquivo",
        label="Fonte do Domínio",
        required=False,
        widget=forms.RadioSelect,
    )

    def __init__(
        self,
        *args: Any,
        companies: QuerySet[ClientCompany],
        agent_enabled: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = companies.filter(active=True).order_by("name")  # type: ignore[attr-defined]
        self.fields["competence"].initial = previous_month()
        self.agent_enabled = agent_enabled
        if not agent_enabled:
            self.fields["dominio_source"].choices = [("arquivo", "Arquivo")]  # type: ignore[attr-defined]
        self.options: dict[str, Any] = {}

    @property
    def competence_text(self) -> str:
        """AAAA-MM para o `<input type="month">`, venha o valor da data inicial ou do POST."""

        value = self["competence"].value()
        if isinstance(value, date):
            return f"{value:%Y-%m}"
        return str(value or "")

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        tool = data.get("tool")
        if tool not in TOOLS:
            return data
        options: dict[str, Any] = {}
        if data.get("tolerance_cents") is not None:
            options["tolerance_cents"] = data["tolerance_cents"]
        if data.get("operation"):
            options["operation"] = data["operation"]
        if tool == SPED_XML:
            options["fields"] = data.get("fields_xml") or []
            options["no_credit_cfops"] = data.get("no_credit_cfops") or ""
        elif tool == SPED_SPED:
            options["fields"] = data.get("fields_sped") or []
            options["include_analytic"] = bool(data.get("include_analytic"))
        elif tool == "icms51":
            options["icms51_cfops"] = data.get("icms51_cfops") or ""
        options["dominio_source"] = data.get("dominio_source") or "arquivo"
        _rules, errors = build_rules(options, tool=tool)
        for message in errors:
            self.add_error(None, message)
        self.options = options
        return data
