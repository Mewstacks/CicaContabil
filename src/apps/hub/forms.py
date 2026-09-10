from typing import Any, cast

from django import forms
from django.db.models import QuerySet

from apps.hub.models import ClientCompany
from apps.organizations.models import Organization


class CompanyForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = ClientCompany
        fields = ("name", "cnpj_masked", "dominio_code")
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "organization"}),
            "cnpj_masked": forms.TextInput(
                attrs={
                    "autocomplete": "off",
                    "inputmode": "numeric",
                    "placeholder": "00.000.000/0000-00…",
                }
            ),
            "dominio_code": forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
        }
        labels = {
            "name": "Razão social ou nome fantasia",
            "cnpj_masked": "CNPJ",
            "dominio_code": "Código no Domínio",
        }


class CertificateUploadForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=ClientCompany.objects.none(),
        label="Empresa",
        widget=forms.Select(attrs={"autocomplete": "off"}),
    )
    label = forms.CharField(
        max_length=120,
        label="Identificação",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    pfx_file = forms.FileField(label="Arquivo A1/PFX")
    password = forms.CharField(
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "off"}),
        label="Senha do certificado",
    )

    def __init__(
        self,
        *args: Any,
        organization: Organization | None = None,
        companies: QuerySet[ClientCompany] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        queryset = ClientCompany.objects.none()
        if companies is not None:
            queryset = companies
        elif organization is not None:
            queryset = ClientCompany.objects.filter(organization=organization, active=True)
        company_field = cast("forms.ModelChoiceField[ClientCompany]", self.fields["company"])
        company_field.queryset = queryset


class ActivationForm(forms.Form):
    password = forms.CharField(
        min_length=12,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "minlength": 12}),
        label="Criar senha",
    )
    password_confirm = forms.CharField(
        min_length=12,
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password", "minlength": 12}),
        label="Confirmar senha",
    )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        if cleaned.get("password") != cleaned.get("password_confirm"):
            self.add_error("password_confirm", "As senhas não conferem.")
        return cleaned
