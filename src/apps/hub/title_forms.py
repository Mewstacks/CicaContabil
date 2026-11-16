"""Human-readable title allocation forms; internal contracts never require JSON editing."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Any, cast

from django import forms
from django.forms import BaseFormSet, formset_factory

from apps.hub.title_contract import MAX_CENTS

MAX_ALLOCATION_ROWS = 20


class BRLCentsField(forms.Field):
    def __init__(self, *, allow_zero: bool = False, **kwargs: Any) -> None:
        self.allow_zero = allow_zero
        kwargs.setdefault(
            "widget",
            forms.TextInput(
                attrs={
                    "inputmode": "decimal",
                    "autocomplete": "off",
                    "placeholder": "0,00",
                    "maxlength": 30,
                }
            ),
        )
        super().__init__(**kwargs)

    def to_python(self, value: Any) -> int | None:
        if value in self.empty_values:
            return None
        text = str(value).strip()
        if not text:
            return None
        if len(text) > 30:
            raise forms.ValidationError("Use até 30 caracteres para informar o valor.")
        if not re.fullmatch(
            r"(?:0|[1-9][0-9]*|[1-9][0-9]{0,2}(?:\.[0-9]{3})+)(?:,[0-9]{1,2})?", text
        ):
            raise forms.ValidationError("Use reais, como 1.234,56, sem sinal ou símbolo de moeda.")
        try:
            cents = Decimal(text.replace(".", "").replace(",", ".")) * 100
        except InvalidOperation:
            raise forms.ValidationError("Informe um valor válido em reais.") from None
        if (
            not (0 if self.allow_zero else 1) <= cents <= MAX_CENTS
            or cents != cents.to_integral_value()
        ):
            raise forms.ValidationError(
                "Informe um valor dentro do limite permitido, sem sinal negativo."
            )
        return int(cents)


class TitlePeriodForm(forms.Form):
    start = forms.DateField(
        label="De",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )
    end = forms.DateField(
        label="Até",
        input_formats=["%Y-%m-%d"],
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
    )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if cleaned.get("start") and cleaned.get("end") and cleaned["start"] > cleaned["end"]:
            raise forms.ValidationError("A data inicial deve ser anterior ou igual à final.")
        for key in ("start", "end"):
            if (
                self.is_bound
                and key in cleaned
                and str(self.data.get(key, "")) != cleaned[key].isoformat()
            ):
                self.add_error(key, "Informe a data no formato AAAA-MM-DD.")
        return cleaned


class TitleAllocationForm(forms.Form):
    settlement = forms.ChoiceField(label="Baixa revisada", choices=())
    movement_key = forms.ChoiceField(label="Movimento do extrato", choices=())
    cash_cents = BRLCentsField(label="Valor a vincular (R$)")

    def __init__(
        self,
        *args: Any,
        movements: list[dict[str, Any]],
        settlements: list[dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.settlement_rows = {str(row["key"]): row for row in settlements}
        cast(forms.ChoiceField, self.fields["settlement"]).choices = [
            ("", "Selecione a baixa…"),
            *(
                (str(row["key"]), f"{row['label']} · disponível {row['remaining_display']}")
                for row in settlements
                if row["remaining_cents"] > 0 and row["available"]
            ),
        ]
        cast(forms.ChoiceField, self.fields["movement_key"]).choices = [
            ("", "Selecione o movimento…"),
            *(
                (str(row["key"]), str(row["label"]))
                for row in movements
                if row["remaining_cents"] > 0 and row["available"]
            ),
        ]

    def allocation_request(self) -> dict[str, Any]:
        row = self.settlement_rows[self.cleaned_data["settlement"]]
        return {
            "movement_key": self.cleaned_data["movement_key"],
            "title_key": row["title_key"],
            "installment_key": row["installment_key"],
            "settlement_key": row["settlement_key"],
            "cash_cents": self.cleaned_data["cash_cents"],
        }


class TitleAllocationFormSet(BaseFormSet):  # type: ignore[type-arg]
    def clean(self) -> None:
        if any(self.errors):
            return
        selected = [form for form in self.forms if form.cleaned_data]
        if not selected:
            raise forms.ValidationError("Selecione ao menos uma baixa e um movimento bancário.")
        pairs = [(f.cleaned_data["settlement"], f.cleaned_data["movement_key"]) for f in selected]
        if len(set(pairs)) != len(pairs):
            raise forms.ValidationError(
                "A mesma baixa e o mesmo movimento aparecem mais de uma vez."
            )


AllocationFormSet = formset_factory(
    TitleAllocationForm,
    formset=TitleAllocationFormSet,
    extra=1,
    max_num=MAX_ALLOCATION_ROWS,
    absolute_max=MAX_ALLOCATION_ROWS,
    validate_max=True,
)


class TitleConfirmForm(forms.Form):
    token = forms.CharField(widget=forms.HiddenInput, max_length=32000)
    evidence_reference = forms.CharField(
        label="Evidência da relação",
        max_length=240,
        widget=forms.Textarea(
            attrs={"rows": 2, "placeholder": "Documento ou conferência que comprova estes vínculos"}
        ),
    )
    reviewed = forms.BooleanField(
        label="Conferi as baixas, os movimentos e os valores desta prévia."
    )
    accept_date_differences = forms.BooleanField(
        label="Conferi e aceito as diferenças de data indicadas.",
        required=False,
    )

    def __init__(self, *args: Any, date_differences: bool = False, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["accept_date_differences"].required = date_differences
        if not date_differences:
            self.fields["accept_date_differences"].widget = forms.HiddenInput()


class TitleUndoForm(forms.Form):
    reason = forms.CharField(
        label="Motivo para desfazer",
        max_length=240,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
