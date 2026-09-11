from typing import Any, cast

from django import forms
from django.db.models import QuerySet

from apps.hub.models import ClientCompany, Connector, OperationalTask
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


class ConnectorConfigForm(forms.Form):
    """Small, guided connector setup; secrets are encrypted before persistence."""

    kind = forms.ChoiceField(
        choices=(
            (Connector.Kind.INTEGRA, "Integra Contador"),
            (Connector.Kind.ONVIO, "Onvio API"),
        ),
        initial=Connector.Kind.INTEGRA,
        label="Tipo de conexão",
        widget=forms.Select(attrs={"autocomplete": "off"}),
    )
    label = forms.CharField(
        max_length=120,
        label="Nome da conexão",
        widget=forms.TextInput(
            attrs={"autocomplete": "organization", "placeholder": "Ex.: Domínio do escritório"}
        ),
    )
    endpoint = forms.URLField(
        required=False,
        label="Endereço do serviço",
        help_text="Preencha apenas quando o conector usar um serviço HTTP.",
        widget=forms.URLInput(attrs={"autocomplete": "url", "placeholder": "https://…"}),
    )
    database_alias = forms.CharField(
        required=False,
        max_length=120,
        label="Nome do banco ou DSN",
        widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
    )
    secret = forms.CharField(
        required=False,
        max_length=500,
        label="Chave ou senha (opcional)",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
        help_text="Fica cifrada nesta instalação e nunca aparece nos logs.",
    )

    def clean_kind(self) -> str:
        kind = str(self.cleaned_data["kind"])
        if kind not in Connector.Kind.values:
            raise forms.ValidationError("Conector inválido.")
        return kind


class DtePreparationForm(forms.Form):
    companies = forms.ModelMultipleChoiceField(
        queryset=ClientCompany.objects.none(),
        label="Empresas para consultar",
        widget=forms.CheckboxSelectMultiple,
        error_messages={
            "required": "Selecione ao menos uma empresa para preparar a consulta.",
            "invalid_choice": "A empresa selecionada n\u00e3o est\u00e1 no seu escopo.",
        },
    )

    def __init__(
        self,
        *args: Any,
        companies: QuerySet[ClientCompany] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        company_field = cast(
            "forms.ModelMultipleChoiceField[ClientCompany]", self.fields["companies"]
        )
        company_field.queryset = (
            companies if companies is not None else ClientCompany.objects.none()
        )


class OperationalTaskForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = OperationalTask
        fields = ("company", "title", "details", "due_on", "priority")
        widgets = {
            "company": forms.Select(attrs={"autocomplete": "off"}),
            "title": forms.TextInput(
                attrs={"autocomplete": "off", "placeholder": "Ex.: Confirmar guia do Simples"}
            ),
            "details": forms.Textarea(
                attrs={"rows": 3, "autocomplete": "off", "placeholder": "Contexto opcional"}
            ),
            "due_on": forms.DateInput(attrs={"type": "date", "autocomplete": "off"}),
            "priority": forms.Select(attrs={"autocomplete": "off"}),
        }
        labels = {
            "company": "Empresa",
            "title": "Pendência",
            "details": "Detalhes",
            "due_on": "Prazo",
            "priority": "Prioridade",
        }

    def __init__(
        self,
        *args: Any,
        companies: QuerySet[ClientCompany] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        company_field = cast("forms.ModelChoiceField[ClientCompany]", self.fields["company"])
        company_field.queryset = (
            companies if companies is not None else ClientCompany.objects.none()
        )
