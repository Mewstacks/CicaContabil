"""Explicit correction form for an existing manual financial account."""

from __future__ import annotations

from typing import Any

from django import forms

from apps.hub.models import FinancialAccount, LedgerAccount
from apps.hub.setup_review import ACCOUNT_FIELDS, IDENTITY_FIELDS, account_revision


class FinancialAccountEditForm(forms.Form):
    name = forms.CharField(max_length=160, label="Nome da conta")
    bank_code = forms.CharField(max_length=20, required=False, label="Código do banco")
    account_reference = forms.CharField(max_length=160, required=False, label="Agência e conta")
    ledger_code = forms.CharField(max_length=64, required=False, label="Conta contábil vinculada")
    active = forms.BooleanField(required=False, label="Conta ativa para novos usos")
    reason = forms.CharField(
        max_length=1000, label="Motivo da correção",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    expected_revision = forms.RegexField(r"\A[0-9a-f]{64}\Z", widget=forms.HiddenInput)

    def __init__(self, *args: Any, account: FinancialAccount,
                 identity_locked: bool = False, **kwargs: Any) -> None:
        initial = {field: getattr(account, field) for field in ACCOUNT_FIELDS}
        initial["expected_revision"] = account_revision(account)
        kwargs["initial"] = initial
        super().__init__(*args, **kwargs)
        for name in ("name", *IDENTITY_FIELDS):
            self.fields[name].widget.attrs["autocomplete"] = "off"
        if identity_locked:
            for name in IDENTITY_FIELDS:
                self.fields[name].widget.attrs["readonly"] = True
        else:
            choices = list(LedgerAccount.objects.filter(
                organization_id=account.organization_id, company_id=account.company_id,
                active=True, accepts_entries=True,
            ).order_by("code").values_list("code", "name"))
            options = [(code, f"{code} — {name}") for code, name in choices]
            if account.ledger_code and account.ledger_code not in {code for code, _ in options}:
                options.append((account.ledger_code, f"{account.ledger_code} — vínculo atual"))
            self.fields["ledger_code"].widget = forms.Select(
                choices=[("", "Selecione a conta contábil"), *options],
            )
        self.fields["reason"].help_text = "Descreva o que foi conferido e por que o cadastro mudou."

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        for field in ("name", *IDENTITY_FIELDS):
            if any(ord(char) < 32 or ord(char) == 127 for char in cleaned.get(field, "")):
                self.add_error(field, "Use uma identificação sem quebras de linha ou controles.")
        return cleaned
