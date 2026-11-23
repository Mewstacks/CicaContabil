"""Only unresolved fields are editable when linking a discovered chart account."""

from __future__ import annotations

from typing import Any

from django import forms


class DiscoveryFiltersForm(forms.Form):
    month = forms.RegexField(
        r"\A[0-9]{4}-(?:0[1-9]|1[0-2])\Z",
        label="Competência",
        widget=forms.DateInput(attrs={"type": "month"}, format="%Y-%m"),
    )
    q = forms.CharField(required=False, max_length=100, label="Buscar")
    page = forms.IntegerField(required=False, min_value=1, max_value=999999)
    chart = forms.IntegerField(required=False, min_value=1, max_value=2147483647)

    def clean_month(self) -> str:
        value = str(self.cleaned_data["month"])
        if not 1900 <= int(value[:4]) <= 9998:
            raise forms.ValidationError("Informe uma competência entre 1900 e 9998.")
        return value


class DiscoveryLinkForm(forms.Form):
    expected_revision = forms.RegexField(r"\A[0-9a-f]{64}\Z", widget=forms.HiddenInput)

    def __init__(self, *args: Any, prepared: dict[str, Any], **kwargs: Any) -> None:
        kwargs["initial"] = {
            **(kwargs.get("initial") or {}),
            "expected_revision": prepared.get("revision", ""),
        }
        kwargs.setdefault("auto_id", "discovery-link-%s")
        super().__init__(*args, **kwargs)
        fields: dict[str, forms.Field] = {
            "bank_code": forms.CharField(
                max_length=20,
                label="Código do banco",
                help_text="Use o código mostrado no extrato desta conta.",
                widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
            ),
            "account_reference": forms.CharField(
                max_length=160,
                label="Agência e conta bancária",
                help_text=(
                    "Copie a identificação do extrato, preservando os zeros e dígitos. "
                    "Se for enviar OFX, prefira ler o arquivo acima: a importação exige "
                    "banco:agência:conta exatamente como no OFX."
                ),
                widget=forms.TextInput(attrs={"autocomplete": "off"}),
            ),
            "bank_inflow_side": forms.ChoiceField(
                label="Uma entrada no banco aparece em qual lado desta conta no Razão?",
                choices=[
                    ("", "Selecione após conferir"),
                    ("debit", "Débito"),
                    ("credit", "Crédito"),
                ],
                help_text="Confira pela perspectiva da conta contábil, não pelo rótulo do banco.",
            ),
            "branch_code": forms.IntegerField(
                label="Código da filial no Domínio",
                min_value=1,
                max_value=2147483647,
                help_text="Informe a filial correspondente ao Razão que será comparado.",
                widget=forms.NumberInput(attrs={"inputmode": "numeric"}),
            ),
            "chart_owner_confirmed": forms.BooleanField(
                label="Conferi que a empresa utiliza este plano de contas nesta competência.",
            ),
            "branch_scope_confirmed": forms.BooleanField(
                label="Conferi a filial e o alcance dos lançamentos desta conta na competência.",
            ),
            "bank_association_confirmed": forms.BooleanField(
                label="Esta conta contábil corresponde à conta bancária informada e à empresa.",
            ),
            "account_active_and_postable": forms.BooleanField(
                label="Conferi que a conta está ativa e aceita lançamentos analíticos.",
            ),
        }
        pending = prepared.get("pending_fields", [])
        if any(name not in fields for name in pending):
            raise ValueError("Campos de conferência indisponíveis.")
        for name, field in fields.items():
            if name in pending:
                self.fields[name] = field
        self.fields["evidence_reference"] = forms.CharField(
            required=False,
            max_length=1000,
            label="Observação da conferência (opcional)",
            help_text="Se necessário, identifique o extrato consultado. Não informe senhas.",
            widget=forms.Textarea(attrs={"rows": 2}),
        )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        for name, value in cleaned.items():
            if (
                isinstance(value, str)
                and name != "evidence_reference"
                and any(ord(char) < 32 or ord(char) == 127 for char in value)
            ):
                self.add_error(name, "Use uma identificação sem quebras de linha ou controles.")
        return cleaned


class OfxPrefillForm(forms.Form):
    """Upload read only to prefill bank identity; the file is never stored (D-377)."""

    statement = forms.FileField(
        label="Extrato OFX ou QFX desta conta",
        help_text=(
            "Preenche banco e conta como a importação exige. O arquivo não é gravado; "
            "você confere e confirma abaixo."
        ),
        widget=forms.ClearableFileInput(attrs={"accept": ".ofx,.qfx"}),
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("auto_id", "discovery-ofx-%s")
        super().__init__(*args, **kwargs)
