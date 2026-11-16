"""Explicit human bank mapping, separate from immutable imported candidate facts."""

from __future__ import annotations

from typing import Any

from django import forms

from apps.hub.models import ReconciliationAccountCandidate


class _CandidateReviewForm(forms.Form):
    expected_source_hash = forms.RegexField(r"\A[0-9a-f]{64}\Z", widget=forms.HiddenInput)
    expected_state = forms.ChoiceField(choices=[("pending", "Pendente")], widget=forms.HiddenInput)

    def __init__(
        self, *args: Any, candidate: ReconciliationAccountCandidate, **kwargs: Any
    ) -> None:
        initial = dict(kwargs.pop("initial", {}) or {})
        initial.update(expected_source_hash=candidate.source_file_sha256, expected_state="pending")
        super().__init__(*args, initial=initial, **kwargs)


class AccountCandidateLinkForm(_CandidateReviewForm):
    name = forms.CharField(
        max_length=160,
        label="Nome da conta conforme o plano conferido",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    bank_code = forms.CharField(
        max_length=20,
        label="Código do banco",
        help_text="Copie o código da identificação bancária conferida.",
        widget=forms.TextInput(attrs={"autocomplete": "off", "inputmode": "numeric"}),
    )
    account_reference = forms.CharField(
        max_length=160,
        label="Referência bancária: agência e conta",
        help_text="Use a referência identificada no extrato da própria empresa, preservando zeros.",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    bank_inflow_side = forms.ChoiceField(
        label="Uma entrada no banco corresponde a qual lado desta conta no Razão?",
        choices=[("", "Selecione após conferir"), ("debit", "Débito"), ("credit", "Crédito")],
    )
    evidence_reference = forms.CharField(
        max_length=1000,
        label="Referência da evidência conferida",
        help_text="Identifique o extrato e o plano consultados; não informe senhas ou credenciais.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    bank_association_confirmed = forms.BooleanField(
        label="Conferi que esta conta bancária pertence à empresa e corresponde à conta do Razão.",
    )
    chart_owner_confirmed = forms.BooleanField(
        label="Conferi o vínculo da empresa com o plano de contas indicado.",
    )
    account_active_and_postable = forms.BooleanField(
        label="Conferi que a conta contábil está ativa e aceita lançamentos analíticos.",
    )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        for field in ("name", "bank_code", "account_reference"):
            value = cleaned.get(field, "")
            if any(ord(char) < 32 or ord(char) == 127 for char in value):
                self.add_error(field, "Use uma identificação sem quebras de linha ou controles.")
        return cleaned


class AccountCandidateDismissForm(_CandidateReviewForm):
    reason = forms.CharField(
        max_length=1000,
        label="Motivo para não utilizar esta candidata",
        help_text="Registre o resultado da sua conferência. A origem será preservada.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
