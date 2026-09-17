import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, cast

from django import forms
from django.db.models import QuerySet

from apps.common.cnpj import normalize_cnpj
from apps.hub.models import (
    AccountingPeriod,
    ClientCompany,
    ClientJourney,
    CostCenter,
    DataSource,
    FinancialAccount,
    ImportBatch,
    JourneyStep,
    LedgerAccount,
    PortalRequest,
    ReconciliationRule,
    ReconciliationSourceFile,
)
from apps.hub.module_catalog import MODULES
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantUsagePolicy


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    widget = MultipleFileInput

    def clean(self, data: Any, initial: Any = None) -> list[Any]:
        values = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(value, initial) for value in values]


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

    def clean_cnpj_masked(self) -> str:
        value = str(self.cleaned_data.get("cnpj_masked") or "").strip()
        if not value:
            return ""
        cnpj = normalize_cnpj(value)
        return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


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


class FinancialAccountSelect(forms.Select):
    """Expose account ownership to the progressive client-side filter.

    The server remains the authorization boundary. The attribute only prevents an
    operator from selecting a visibly incompatible account after changing company.
    """

    def create_option(self, name: str, value: Any, label: str, selected: bool, index: int,
                      subindex: int | None = None, attrs: dict[str, Any] | None = None) -> dict[str, Any]:
        option = super().create_option(name, value, label, selected, index, subindex, attrs)
        instance = getattr(value, "instance", None)
        if isinstance(instance, FinancialAccount):
            option["attrs"]["data-company-id"] = str(instance.company_id)
        return option


class ReconciliationUploadForm(forms.Form):
    company = forms.ModelChoiceField(
        queryset=ClientCompany.objects.none(),
        label="Empresa",
        empty_label="Selecione a empresa",
    )
    financial_account = forms.ModelChoiceField(
        queryset=FinancialAccount.objects.none(),
        required=False,
        label="Conta financeira",
        empty_label="Selecione a conta",
        help_text="Obrigatória para extrato bancário quando a empresa tiver contas ativas.",
        widget=FinancialAccountSelect(attrs={"data-financial-account-select": ""}),
    )
    origin = forms.ChoiceField(label="Origem", choices=ReconciliationSourceFile.Origin.choices)
    period_start = forms.DateField(
        label="Início do período", widget=forms.DateInput(attrs={"type": "date", "autocomplete": "off"})
    )
    period_end = forms.DateField(
        label="Fim do período", widget=forms.DateInput(attrs={"type": "date", "autocomplete": "off"})
    )
    physical_batch = forms.CharField(
        label="Identificação do lote físico", max_length=120, required=False,
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
        help_text="Opcional; use para localizar a caixa ou malote original.",
    )
    files = MultipleFileField(
        label="Arquivos", widget=MultipleFileInput(attrs={"accept": ".ofx,.qfx,.csv,.xlsx,.pdf", "multiple": True})
    )

    def __init__(self, *args: Any, companies: QuerySet[ClientCompany], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        company = cast(forms.ModelChoiceField, self.fields["company"])
        company.queryset = companies
        company_id = self.data.get("company") if self.is_bound else None
        accounts = FinancialAccount.objects.filter(
            company__in=companies,
            active=True,
        ).select_related("company")
        if company_id:
            accounts = accounts.filter(company_id=company_id)
        financial_account_field = cast(
            forms.ModelChoiceField, self.fields["financial_account"]
        )
        financial_account_field.queryset = accounts.order_by("company__name", "name")
        financial_account_field.label_from_instance = lambda account: (
            f"{account.company.name} — {account.name} ({account.account_reference})"
        )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        start = cleaned.get("period_start")
        end = cleaned.get("period_end")
        if start and end and end < start:
            self.add_error("period_end", "O fim do período deve ser igual ou posterior ao início.")
        company = cleaned.get("company")
        financial_account = cleaned.get("financial_account")
        if (
            isinstance(company, ClientCompany)
            and isinstance(financial_account, FinancialAccount)
            and financial_account.company_id != company.id
        ):
            self.add_error("financial_account", "Escolha uma conta financeira da empresa selecionada.")
        if (
            cleaned.get("origin") == ReconciliationSourceFile.Origin.BANK_STATEMENT
            and isinstance(company, ClientCompany)
            and FinancialAccount.objects.filter(company=company, active=True).exists()
            and financial_account is None
        ):
            self.add_error("financial_account", "Escolha a conta financeira do extrato.")
        return cleaned


class ReconciliationMovementForm(forms.Form):
    occurred_on = forms.DateField(label="Data", required=False, widget=forms.DateInput(attrs={"type": "date", "autocomplete": "off"}))
    description = forms.CharField(label="Descrição", max_length=1000, required=False, widget=forms.TextInput(attrs={"autocomplete": "off"}))
    document_number = forms.CharField(label="Documento", max_length=160, required=False, widget=forms.TextInput(attrs={"autocomplete": "off"}))
    counterparty = forms.CharField(label="Contraparte", max_length=255, required=False, widget=forms.TextInput(attrs={"autocomplete": "off"}))
    debit_account_code = forms.CharField(label="Conta de débito", max_length=64, required=False, widget=forms.TextInput(attrs={"autocomplete": "off"}))
    credit_account_code = forms.CharField(label="Conta de crédito", max_length=64, required=False, widget=forms.TextInput(attrs={"autocomplete": "off"}))
    cost_center_code = forms.CharField(label="Centro de custo", max_length=64, required=False, widget=forms.TextInput(attrs={"autocomplete": "off"}))
    accounting_history = forms.CharField(label="Histórico contábil", max_length=500, required=False, widget=forms.TextInput(attrs={"autocomplete": "off"}))
    expected_revision = forms.IntegerField(widget=forms.HiddenInput)


class _ReconciliationCompanyScopedForm(forms.ModelForm):  # type: ignore[type-arg]
    """Keeps every accounting setup command inside the current office."""

    def __init__(self, *args: Any, companies: QuerySet[ClientCompany], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        company = cast(forms.ModelChoiceField, self.fields["company"])
        company.queryset = companies
        # The configuration page owns one explicit company switcher. Keeping this
        # field in the submitted form, but not as a second visible selector, avoids
        # accidentally saving a setup record for a different company.
        company.widget = forms.HiddenInput()


class FinancialAccountForm(_ReconciliationCompanyScopedForm):
    class Meta:
        model = FinancialAccount
        fields = ("company", "name", "bank_code", "account_reference", "ledger_code", "active")
        labels = {
            "company": "Empresa",
            "name": "Nome da conta financeira",
            "bank_code": "Código do banco",
            "account_reference": "Agência e conta",
            "ledger_code": "Conta contábil vinculada",
            "active": "Conta ativa",
        }
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "off"}),
            "bank_code": forms.TextInput(attrs={"autocomplete": "off", "inputmode": "numeric"}),
            "account_reference": forms.TextInput(attrs={"autocomplete": "off"}),
            "ledger_code": forms.TextInput(attrs={"autocomplete": "off"}),
        }

    def __init__(self, *args: Any, companies: QuerySet[ClientCompany], **kwargs: Any) -> None:
        super().__init__(*args, companies=companies, **kwargs)
        selected_company_id = (
            self.data.get("company") if self.is_bound else self.initial.get("company")
        )
        if isinstance(selected_company_id, ClientCompany):
            selected_company_id = selected_company_id.id
        accounts = LedgerAccount.objects.filter(
            company_id=selected_company_id,
            company__in=companies,
            active=True,
            accepts_entries=True,
        ).order_by("code") if selected_company_id else LedgerAccount.objects.none()
        self.fields["ledger_code"].widget = forms.Select(
            choices=[("", "Sem vínculo contábil por enquanto")]
            + [(account.code, f"{account.code} — {account.name}") for account in accounts]
        )
        self.fields["ledger_code"].help_text = (
            "Escolha somente uma conta ativa que aceite lançamentos desta empresa."
        )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        company = cleaned.get("company")
        ledger_code = str(cleaned.get("ledger_code") or "").strip()
        if isinstance(company, ClientCompany) and ledger_code and not LedgerAccount.objects.filter(
            company=company,
            code=ledger_code,
            active=True,
            accepts_entries=True,
        ).exists():
            self.add_error(
                "ledger_code",
                "Cadastre uma conta contábil ativa que aceite lançamentos antes de vinculá-la.",
            )
        return cleaned


class LedgerAccountForm(_ReconciliationCompanyScopedForm):
    class Meta:
        model = LedgerAccount
        fields = ("company", "code", "name", "nature", "active", "accepts_entries")
        labels = {
            "company": "Empresa",
            "code": "Código",
            "name": "Nome da conta",
            "nature": "Natureza",
            "active": "Conta ativa",
            "accepts_entries": "Aceita lançamentos",
        }
        widgets = {
            "code": forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
            "name": forms.TextInput(attrs={"autocomplete": "off"}),
            "nature": forms.TextInput(
                attrs={"autocomplete": "off", "placeholder": "Ex.: ativo, despesa…"}
            ),
        }


class CostCenterForm(_ReconciliationCompanyScopedForm):
    class Meta:
        model = CostCenter
        fields = ("company", "code", "name", "active", "required")
        labels = {
            "company": "Empresa",
            "code": "Código",
            "name": "Nome do centro de custo",
            "active": "Centro ativo",
            "required": "Exigir em novos lançamentos",
        }
        widgets = {
            "code": forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
            "name": forms.TextInput(attrs={"autocomplete": "off"}),
        }


class AccountingPeriodForm(_ReconciliationCompanyScopedForm):
    class Meta:
        model = AccountingPeriod
        fields = ("company", "starts_on", "ends_on")
        labels = {"company": "Empresa", "starts_on": "Início", "ends_on": "Fim"}
        widgets = {
            "starts_on": forms.DateInput(attrs={"type": "date", "autocomplete": "off"}),
            "ends_on": forms.DateInput(attrs={"type": "date", "autocomplete": "off"}),
        }

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        if (
            cleaned.get("starts_on")
            and cleaned.get("ends_on")
            and cleaned["ends_on"] < cleaned["starts_on"]
        ):
            self.add_error("ends_on", "O fim do período deve ser igual ou posterior ao início.")
        return cleaned


class ReconciliationRuleForm(forms.Form):
    """A constrained, inspectable rule builder; it never accepts executable code."""

    CONDITION_FIELDS = (
        ("financial_account", "Conta financeira"),
        ("description", "Histórico"),
        ("counterparty", "Contraparte"),
        ("document", "Documento"),
        ("direction", "Natureza"),
        ("amount_cents", "Faixa de valor"),
    )
    OPERATORS = (
        ("equals", "É exatamente"),
        ("contains", "Contém"),
        ("regex", "Corresponde à expressão regular"),
        ("range", "Está na faixa de valor"),
    )
    CONDITION_GROUPS = (
        ("all", "Todas as condições devem coincidir"),
        ("any", "Basta uma das condições coincidir"),
    )

    company = forms.ModelChoiceField(queryset=ClientCompany.objects.none(), label="Empresa")
    name = forms.CharField(
        max_length=160,
        label="Nome da regra",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    priority = forms.IntegerField(
        min_value=1,
        max_value=9999,
        initial=100,
        label="Prioridade",
        help_text="Menor número é avaliado primeiro. Regras conflitantes continuam em revisão.",
        widget=forms.NumberInput(attrs={"min": 1, "max": 9999, "inputmode": "numeric"}),
    )
    state = forms.ChoiceField(
        choices=ReconciliationRule.State.choices,
        initial=ReconciliationRule.State.DRAFT,
        label="Situação",
    )
    condition_field = forms.ChoiceField(choices=CONDITION_FIELDS, label="Quando o campo")
    condition_operator = forms.ChoiceField(choices=OPERATORS, label="Operador")
    condition_value = forms.CharField(
        max_length=160,
        required=False,
        label="Valor da condição",
        help_text=(
            "Para conta financeira, use a referência cadastrada. Para natureza, use entrada "
            "ou saída. Para faixa, informe os limites abaixo."
        ),
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    condition_group = forms.ChoiceField(
        choices=CONDITION_GROUPS,
        initial="all",
        required=False,
        label="Como combinar a condição adicional",
        help_text="A segunda condição é opcional. Use “todas” para tornar a regra mais específica.",
    )
    additional_condition_field = forms.ChoiceField(
        choices=(("", "Nenhuma condição adicional"), *CONDITION_FIELDS[:-1]),
        required=False,
        label="E também considerar",
    )
    additional_condition_operator = forms.ChoiceField(
        choices=(("", "Selecione o operador"), *OPERATORS[:-1]),
        required=False,
        label="Operador adicional",
    )
    additional_condition_value = forms.CharField(
        max_length=160,
        required=False,
        label="Valor adicional",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    minimum_brl = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=14,
        decimal_places=2,
        label="Valor mínimo",
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "inputmode": "decimal"}),
    )
    maximum_brl = forms.DecimalField(
        required=False,
        min_value=0,
        max_digits=14,
        decimal_places=2,
        label="Valor máximo",
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "inputmode": "decimal"}),
    )
    debit_account_code = forms.CharField(
        max_length=64,
        required=False,
        label="Conta de débito",
        widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
    )
    credit_account_code = forms.CharField(
        max_length=64,
        required=False,
        label="Conta de crédito",
        widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
    )
    cost_center_code = forms.CharField(
        max_length=64,
        required=False,
        label="Centro de custo",
        widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
    )
    accounting_history = forms.CharField(
        max_length=500,
        required=False,
        label="Histórico contábil",
        widget=forms.TextInput(attrs={"autocomplete": "off"}),
    )
    require_review = forms.BooleanField(
        required=False,
        label="Enviar o resultado para revisão antes de lançar",
    )
    ignore = forms.BooleanField(required=False, label="Marcar os movimentos compatíveis como ignorados")

    def __init__(self, *args: Any, companies: QuerySet[ClientCompany], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        company = cast(forms.ModelChoiceField, self.fields["company"])
        company.queryset = companies
        company.widget = forms.HiddenInput()

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        operator = cleaned.get("condition_operator")
        field = cleaned.get("condition_field")
        value = str(cleaned.get("condition_value") or "").strip()
        minimum = cleaned.get("minimum_brl")
        maximum = cleaned.get("maximum_brl")
        if operator == "range":
            if field != "amount_cents":
                self.add_error("condition_field", "A faixa de valor só pode usar o campo Valor.")
            if minimum is None or maximum is None:
                self.add_error("minimum_brl", "Informe os dois limites da faixa.")
            elif maximum < minimum:
                self.add_error("maximum_brl", "O valor máximo deve ser igual ou maior que o mínimo.")
        elif not value:
            self.add_error("condition_value", "Informe o valor que a regra deve reconhecer.")
        elif operator == "regex":
            if len(value) > 160:
                self.add_error("condition_value", "A expressão pode ter no máximo 160 caracteres.")
            else:
                try:
                    re.compile(value)
                except re.error:
                    self.add_error("condition_value", "A expressão regular não é válida.")
        additional_field = str(cleaned.get("additional_condition_field") or "")
        additional_operator = str(cleaned.get("additional_condition_operator") or "")
        additional_value = str(cleaned.get("additional_condition_value") or "").strip()
        if additional_field or additional_operator or additional_value:
            if not additional_field:
                self.add_error("additional_condition_field", "Escolha o campo da condição adicional.")
            if not additional_operator:
                self.add_error("additional_condition_operator", "Escolha o operador adicional.")
            if not additional_value:
                self.add_error("additional_condition_value", "Informe o valor adicional.")
            elif additional_operator == "regex":
                try:
                    re.compile(additional_value)
                except re.error:
                    self.add_error("additional_condition_value", "A expressão regular adicional não é válida.")
        if not any(
            cleaned.get(key)
            for key in (
                "debit_account_code",
                "credit_account_code",
                "cost_center_code",
                "accounting_history",
                "require_review",
                "ignore",
            )
        ):
            self.add_error(None, "Defina ao menos uma ação para a regra.")
        company = cleaned.get("company")
        if isinstance(company, ClientCompany):
            for field_name in ("debit_account_code", "credit_account_code"):
                code = str(cleaned.get(field_name) or "")
                if code and not LedgerAccount.objects.filter(
                    company=company, code=code, active=True, accepts_entries=True
                ).exists():
                    self.add_error(field_name, "Cadastre uma conta contábil ativa que aceite lançamentos.")
            cost_center = str(cleaned.get("cost_center_code") or "")
            if cost_center and not CostCenter.objects.filter(
                company=company, code=cost_center, active=True
            ).exists():
                self.add_error("cost_center_code", "Cadastre um centro de custo ativo antes de usá-lo.")
        return cleaned

    def condition_groups(self) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
        if self.cleaned_data["condition_operator"] == "range":
            value: object = {
                "min": int(self.cleaned_data["minimum_brl"] * 100),
                "max": int(self.cleaned_data["maximum_brl"] * 100),
            }
        else:
            value = self.cleaned_data["condition_value"]
        primary = {
            "field": self.cleaned_data["condition_field"],
            "operator": self.cleaned_data["condition_operator"],
            "value": value,
        }
        additional_field = str(self.cleaned_data.get("additional_condition_field") or "")
        if not additional_field:
            return [primary], []
        additional = {
            "field": additional_field,
            "operator": self.cleaned_data["additional_condition_operator"],
            "value": self.cleaned_data["additional_condition_value"],
        }
        if self.cleaned_data.get("condition_group") == "any":
            return [], [primary, additional]
        return [primary, additional], []

    def actions(self) -> dict[str, object]:
        actions = {
            key: self.cleaned_data[key]
            for key in (
                "debit_account_code",
                "credit_account_code",
                "cost_center_code",
                "accounting_history",
                "ignore",
            )
            if self.cleaned_data.get(key)
        }
        if self.cleaned_data.get("require_review"):
            actions["review"] = True
        return actions
