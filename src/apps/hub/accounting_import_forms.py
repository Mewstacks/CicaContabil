"""Human-observed import results, one bounded page at a time."""

from __future__ import annotations

from typing import Any

from django import forms

RESULT_CHOICES = (
    ("uncertain", "Incerto — conferir no Domínio"),
    ("accepted", "Aceito — localizado e conferido"),
    ("rejected", "Rejeitado — retorno conferido"),
)


class ImportReceiptForm(forms.Form):
    request_key = forms.UUIDField(widget=forms.HiddenInput)
    content_hash = forms.RegexField(r"\A[0-9a-f]{64}\Z", widget=forms.HiddenInput)
    expected_previous_id = forms.UUIDField(required=False, widget=forms.HiddenInput)
    importer_version = forms.CharField(
        label="Versão do importador conferida",
        max_length=120,
        widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
    )
    evidence_reference = forms.CharField(
        label="Evidência do resultado desta conferência",
        max_length=1000,
        help_text="Identifique o retorno ou relatório consultado no Domínio. Não informe senhas.",
        widget=forms.Textarea(attrs={"rows": 2, "autocomplete": "off"}),
    )
    review_confirmed = forms.BooleanField(
        label="Conferi no Domínio os resultados que estou registrando nesta página.",
        error_messages={"required": "Confirme a conferência desta página antes de registrar."},
    )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        for name in ("importer_version", "evidence_reference"):
            value = cleaned.get(name, "")
            if any(ord(char) < 32 or ord(char) == 127 for char in value):
                self.add_error(name, "Use uma identificação sem quebras de linha ou controles.")
        return cleaned


class ImportReceiptItemForm(forms.Form):
    status = forms.ChoiceField(label="Resultado no Domínio", choices=RESULT_CHOICES)
    erp_reference = forms.CharField(
        label="Identificação do lançamento no Domínio",
        required=False,
        max_length=240,
        help_text="Obrigatória quando o lançamento foi aceito.",
        widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
    )
    evidence_reference = forms.CharField(
        label="Evidência deste lançamento",
        required=False,
        max_length=1000,
        help_text="Obrigatória para resultado aceito ou rejeitado.",
        widget=forms.Textarea(attrs={"rows": 2, "autocomplete": "off"}),
    )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        status = cleaned.get("status")
        if status == "accepted" and not cleaned.get("erp_reference"):
            self.add_error("erp_reference", "Informe a identificação encontrada no Domínio.")
        if status in {"accepted", "rejected"} and not cleaned.get("evidence_reference"):
            self.add_error(
                "evidence_reference", "Identifique a evidência consultada para este resultado."
            )
        for name in ("erp_reference", "evidence_reference"):
            if any(ord(char) < 32 or ord(char) == 127 for char in cleaned.get(name, "")):
                self.add_error(name, "Use uma identificação sem quebras de linha ou controles.")
        return cleaned
