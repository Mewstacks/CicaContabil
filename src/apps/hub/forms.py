from decimal import ROUND_HALF_UP, Decimal
from typing import Any, cast

from django import forms
from django.db.models import QuerySet

from apps.common.cnpj import normalize_cnpj
from apps.hub.models import (
    ClientCompany,
    ClientJourney,
    DataSource,
    ImportBatch,
    JourneyStep,
    PortalRequest,
)
from apps.hub.module_catalog import MODULES
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantUsagePolicy


class CompanyForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = ClientCompany
        fields = ("name", "cnpj_masked", "dominio_code")
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "organization"}),
            "cnpj_masked": forms.TextInput(
                attrs={
                    "autocomplete": "off",
                    "inputmode": "text",
                    "placeholder": "00.000.000/0000-00…",
                }
            ),
            "dominio_code": forms.TextInput(
                attrs={"autocomplete": "off", "spellcheck": "false", "placeholder": "Ex.: 0101"}
            ),
        }
        labels = {
            "name": "Razão social ou nome fantasia",
            "cnpj_masked": "CNPJ",
            "dominio_code": "Código no Domínio",
        }

    def __init__(
        self,
        *args: Any,
        organization: Organization | None = None,
        require_dominio_code: bool = False,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.organization = organization
        if require_dominio_code:
            self.fields["dominio_code"].required = True
            self.fields["dominio_code"].error_messages["required"] = (
                "Este escritório exige o código do Domínio."
            )

    def clean_dominio_code(self) -> str:
        code = str(self.cleaned_data.get("dominio_code") or "").strip()
        if not code or self.organization is None:
            return code
        duplicate = ClientCompany.objects.filter(
            organization=self.organization, dominio_code=code
        ).exclude(pk=self.instance.pk)
        if duplicate.exists():
            raise forms.ValidationError("Outra empresa já usa este código.")
        return code


class JourneyForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = ClientJourney
        fields = ("company", "title", "due_on")
        widgets = {
            "company": forms.Select(attrs={"autocomplete": "organization"}),
            "title": forms.TextInput(
                attrs={"autocomplete": "off", "placeholder": "Ex.: Onboarding fiscal"}
            ),
            "due_on": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "company": "Empresa",
            "title": "Nome da jornada",
            "due_on": "Prazo inicial",
        }


class JourneyStepForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = JourneyStep
        fields = ("title", "description", "due_on")
        widgets = {
            "title": forms.TextInput(
                attrs={"autocomplete": "off", "placeholder": "Ex.: Conferir procurações"}
            ),
            "description": forms.Textarea(attrs={"rows": 3, "autocomplete": "off"}),
            "due_on": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "title": "Etapa",
            "description": "Orientação para o time",
            "due_on": "Prazo",
        }


class PortalRequestForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = PortalRequest
        fields = ("title", "details", "due_on")
        widgets = {
            "title": forms.TextInput(
                attrs={"autocomplete": "off", "placeholder": "Ex.: Enviar extrato de março"}
            ),
            "details": forms.Textarea(attrs={"rows": 3, "autocomplete": "off"}),
            "due_on": forms.DateInput(attrs={"type": "date"}),
        }
        labels = {
            "title": "Solicitação",
            "details": "Orienta\u00e7\u00e3o interna",
            "due_on": "Prazo",
        }


class CollaboratorInvitationForm(forms.Form):
    """A workspace owner scopes a teammate before the invitation is sent."""

    full_name = forms.CharField(
        label="Nome",
        max_length=150,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    email = forms.EmailField(
        label="E-mail de trabalho",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "spellcheck": "false"}),
    )
    role = forms.ChoiceField(
        label="Perfil",
        choices=(
            (Membership.Role.MANAGER, "Gestor"),
            (Membership.Role.OPERATOR, "Operador"),
            (Membership.Role.AUDITOR, "Auditor"),
            (Membership.Role.BILLING, "Financeiro"),
        ),
    )
    modules = forms.MultipleChoiceField(
        label="M\u00f3dulos permitidos",
        choices=(),
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Selecione ao menos um m\u00f3dulo."},
    )
    companies = forms.MultipleChoiceField(
        label="Empresas permitidas",
        choices=(),
        widget=forms.CheckboxSelectMultiple,
        error_messages={"required": "Selecione ao menos uma empresa."},
    )

    def __init__(
        self,
        *args: Any,
        companies: QuerySet[ClientCompany] | None = None,
        module_codes: set[str] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        available = module_codes if module_codes is not None else set(MODULES)
        self.fields["modules"].choices = [
            (code, MODULES[code].label) for code in MODULES if code in available
        ]
        self.fields["companies"].choices = [
            (str(company.id), company.name)
            for company in (companies or ClientCompany.objects.none())
        ]

    def clean_modules(self) -> list[str]:
        values = list(self.cleaned_data["modules"])
        allowed = {str(code) for code, _label in self.fields["modules"].choices}
        if not set(values).issubset(allowed):
            raise forms.ValidationError(
                "Selecione apenas m\u00f3dulos dispon\u00edveis neste escrit\u00f3rio."
            )
        return values

    def clean_companies(self) -> list[str]:
        values = list(self.cleaned_data["companies"])
        allowed = {str(company_id) for company_id, _label in self.fields["companies"].choices}
        if not set(values).issubset(allowed):
            raise forms.ValidationError("Selecione apenas empresas do seu escrit\u00f3rio.")
        return values


class CollaboratorAccessForm(CollaboratorInvitationForm):
    """The same explicit scope controls used after a teammate has joined."""

    can_acknowledge_dte = forms.BooleanField(
        required=False,
        label="Pode abrir mensagens DTE e registrar ciência",
    )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields.pop("full_name")
        self.fields.pop("email")


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
        help_text="Use pelo menos 12 caracteres. Você pode colar uma senha do seu gerenciador.",
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
        candidates = list(companies) if companies is not None else []
        eligible_ids = []
        for company in candidates:
            try:
                normalize_cnpj(company.cnpj_masked)
            except forms.ValidationError:
                continue
            eligible_ids.append(company.id)
        self.scope_count = len(candidates)
        self.ineligible_count = self.scope_count - len(eligible_ids)
        company_field.queryset = (
            companies.filter(id__in=eligible_ids)
            if companies is not None
            else ClientCompany.objects.none()
        )
        company_field.label_from_instance = lambda company: (
            company.name
            + (f" · Domínio {company.dominio_code}" if company.dominio_code else "")
            + (f" · {company.cnpj_masked}" if company.cnpj_masked else " · CNPJ ausente")
        )


class OfxImportForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=ClientCompany.objects.none(),
        label="Empresa",
        empty_label="Selecionar empresa",
    )
    ofx_file = forms.FileField(
        label="Arquivo OFX",
        widget=forms.ClearableFileInput(attrs={"accept": ".ofx,.qfx", "class": "sr-only"}),
    )

    def __init__(self, *args: Any, companies: QuerySet[ClientCompany], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        company_field = cast("forms.ModelChoiceField[ClientCompany]", self.fields["company"])
        company_field.queryset = companies


class UsagePolicyForm(forms.Form):
    overage_mode = forms.ChoiceField(
        label="Quando a franquia acabar",
        choices=TenantUsagePolicy.OverageMode.choices,
    )
    warning_percent = forms.IntegerField(
        label="Avisar ao atingir (%)",
        min_value=1,
        max_value=100,
        widget=forms.NumberInput(attrs={"inputmode": "numeric"}),
    )
    monthly_overage_cap_brl = forms.DecimalField(
        label="Teto de excedente no mês (R$)",
        min_value=Decimal("0"),
        max_digits=10,
        decimal_places=2,
        required=False,
        help_text="Deixe em branco para usar apenas a regra do contrato.",
        widget=forms.NumberInput(attrs={"inputmode": "decimal", "step": "0.01"}),
    )

    def cap_cents(self) -> int:
        amount = self.cleaned_data["monthly_overage_cap_brl"]
        if amount is None:
            return 0
        return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


class DataSourceForm(forms.Form):
    kind = forms.ChoiceField(
        label="Como seus dados chegam ao CICA?",
        choices=(
            (DataSource.Kind.DOMINIO_LOCAL_AGENT, "Domínio Local — sincronização automática"),
            (DataSource.Kind.DOMINIO_WEB_BACKUP, "Domínio Web — envio manual de backup"),
            (DataSource.Kind.OTHER_MANUAL, "Outro sistema — arquivos e cadastro manual"),
        ),
        widget=forms.Select(attrs={"autocomplete": "off"}),
    )


class UnifiedImportForm(forms.Form):
    kind = forms.ChoiceField(
        label="Tipo de informação",
        choices=ImportBatch.Kind.choices,
        widget=forms.Select(attrs={"autocomplete": "off"}),
    )
    upload = forms.FileField(
        label="Arquivo",
        widget=forms.ClearableFileInput(attrs={"accept": ".csv,.xlsx,.xml,.ofx,.qfx,.dom,.zip"}),
    )
    company = forms.ModelChoiceField(
        queryset=ClientCompany.objects.none(), required=False, label="Empresa do arquivo"
    )
    source_snapshot_at = forms.DateTimeField(
        required=False,
        label="Data e hora do backup",
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "autocomplete": "off"}),
    )
    backup_key = forms.CharField(
        required=False,
        max_length=255,
        label="Chave do arquivo do Onvio",
        help_text="Use a chave exibida ao lado do backup no Onvio.",
        widget=forms.PasswordInput(attrs={"autocomplete": "off"}),
    )

    def __init__(
        self,
        *args: Any,
        companies: QuerySet[ClientCompany],
        source_kind: str = "",
        **kwargs: Any,
    ) -> None:
        super().__init__(*args, **kwargs)
        cast(forms.ModelChoiceField, self.fields["company"]).queryset = companies
        if source_kind != DataSource.Kind.DOMINIO_WEB_BACKUP:
            self.fields["kind"].choices = [
                choice
                for choice in ImportBatch.Kind.choices
                if choice[0] != ImportBatch.Kind.DOMINIO_BACKUP
            ]

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        upload = cleaned.get("upload")
        kind = cleaned.get("kind")
        if upload is None or not kind:
            return cleaned
        suffix = str(upload.name).rsplit(".", 1)[-1].casefold() if "." in upload.name else ""
        allowed = {
            ImportBatch.Kind.COMPANIES: {"csv", "xlsx"},
            ImportBatch.Kind.OBLIGATIONS: {"csv", "xlsx"},
            ImportBatch.Kind.ACCOUNTING: {"csv", "xlsx"},
            ImportBatch.Kind.FISCAL_XML: {"xml"},
            ImportBatch.Kind.BANK_OFX: {"ofx", "qfx"},
            ImportBatch.Kind.DOMINIO_BACKUP: {"dom", "zip"},
        }
        if suffix not in allowed.get(kind, set()):
            self.add_error("upload", "O formato do arquivo não corresponde ao tipo escolhido.")
        if kind in {ImportBatch.Kind.FISCAL_XML, ImportBatch.Kind.BANK_OFX} and not cleaned.get(
            "company"
        ):
            self.add_error("company", "Selecione a empresa deste arquivo.")
        if kind == ImportBatch.Kind.DOMINIO_BACKUP:
            if not cleaned.get("source_snapshot_at"):
                self.add_error("source_snapshot_at", "Informe a data e hora do backup.")
            if not cleaned.get("backup_key"):
                self.add_error("backup_key", "Informe a chave exibida no Onvio.")
        return cleaned
