"""Explicit review of retained suggestions; no generation or approval defaults."""

from __future__ import annotations

from typing import Any

from django import forms


class DeparaReviewForm(forms.Form):
    expected_token = forms.CharField(widget=forms.HiddenInput, max_length=1024)
    confirmed = forms.BooleanField(
        label="Conferi as contas, a direção e o histórico das sugestões selecionadas.",
    )


class DeparaChoiceForm(forms.Form):
    selected = forms.BooleanField(required=False, label="Preparar rascunho desta sugestão")
    debit = forms.ChoiceField(required=False, label="Conta de débito")
    credit = forms.ChoiceField(required=False, label="Conta de crédito")
    history = forms.CharField(
        required=False, label="Histórico contábil conferido", max_length=500,
        widget=forms.Textarea(attrs={"rows": 3}),
    )

    def __init__(
        self, *args: Any, accounts: list[Any], suggestion: dict[str, str],
        bank_code: str, **kwargs: Any,
    ) -> None:
        initial = {"debit": suggestion["debit"], "credit": suggestion["credit"]}
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        choices = [("", "Selecione a conta conferida")]
        choices.extend((row.code, f"{row.code} · {row.name}") for row in accounts)
        self.fields["debit"].choices = choices  # type: ignore[attr-defined]
        self.fields["credit"].choices = choices  # type: ignore[attr-defined]
        self.bank_code = bank_code

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if not cleaned.get("selected"):
            return cleaned
        for field in ("debit", "credit", "history"):
            if not cleaned.get(field):
                self.add_error(field, "Informe este dado para a sugestão selecionada.")
        if cleaned.get("debit") and cleaned.get("credit"):
            if cleaned["debit"] == cleaned["credit"]:
                self.add_error("credit", "Débito e crédito precisam ser contas diferentes.")
            elif self.bank_code not in {cleaned["debit"], cleaned["credit"]}:
                self.add_error(None, "Um dos lados precisa ser a conta bancária desta revisão.")
        return cleaned
