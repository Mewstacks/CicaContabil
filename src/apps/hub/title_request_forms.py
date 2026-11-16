"""Company-scoped collection inputs; a bank account is never inferred."""

from __future__ import annotations

import re
from datetime import date
from typing import Any, cast

from django import forms
from django.db.models import QuerySet

from apps.hub.models import ClientCompany


class TitleMonthField(forms.CharField):
    def __init__(self, **kwargs: Any) -> None:
        kwargs.setdefault("max_length", 7)
        kwargs.setdefault(
            "widget",
            forms.DateInput(
                format="%Y-%m", attrs={"type": "month", "min": "0001-01", "max": "9998-12"}
            ),
        )
        super().__init__(**kwargs)

    def clean(self, value: Any) -> date:
        value = super().clean(value)
        if not isinstance(value, str) or not re.fullmatch(r"[0-9]{4}-[0-9]{2}", value):
            raise forms.ValidationError("Informe a competência no formato AAAA-MM.")
        try:
            month = date.fromisoformat(value + "-01")
        except ValueError:
            raise forms.ValidationError("Escolha uma competência válida.") from None
        if month.year > 9998:
            raise forms.ValidationError("Escolha uma competência entre 0001-01 e 9998-12.")
        return month


class TitleRequestForm(forms.Form):
    companies = forms.ModelMultipleChoiceField(
        queryset=ClientCompany.objects.none(),
        label="Empresas",
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Selecione ao menos uma empresa."},
    )
    start_month = TitleMonthField(label="Competência inicial")
    end_month = TitleMonthField(label="Competência final")
    request_key = forms.UUIDField(widget=forms.HiddenInput)
    expected_revision = forms.CharField(widget=forms.HiddenInput, max_length=64, required=False)

    def __init__(self, *args: Any, companies: QuerySet[ClientCompany], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        field = cast("forms.ModelMultipleChoiceField[ClientCompany]", self.fields["companies"])
        field.queryset = companies.order_by("name", "pk")
        setattr(  # noqa: B010
            field,
            "label_from_instance",
            lambda item: f"{item.name} · Domínio {item.dominio_code or 'não vinculado'}",
        )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if hasattr(self.data, "getlist"):
            selected = self.data.getlist("companies")
            if len(selected) != len(set(selected)):
                self.add_error("companies", "Selecione cada empresa uma única vez.")
            if any(
                len(self.data.getlist(name)) > 1
                for name in (*[name for name in self.fields if name != "companies"], "action")
            ):
                self.add_error(None, "Informe cada campo uma única vez.")
        start, end = cleaned.get("start_month"), cleaned.get("end_month")
        companies = cleaned.get("companies")
        if start and end:
            if end < start:
                self.add_error(
                    "end_month", "A competência final deve ser igual ou posterior à inicial."
                )
            elif companies is not None:
                months = (end.year - start.year) * 12 + end.month - start.month + 1
                if months * len(companies) > 2000:
                    self.add_error(
                        None,
                        "O lote ultrapassa 2.000 buscas. Reduza as empresas ou o intervalo "
                        "e faça outro lote depois.",
                    )
        return cleaned
