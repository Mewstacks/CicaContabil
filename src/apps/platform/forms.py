import json
import re
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, cast

from django import forms
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.common.cnpj import lookup_company, normalize_cnpj
from apps.integra.catalog import SERVICES
from apps.organizations.models import Membership
from apps.platform.models import (
    Lead,
    Plan,
    PlanServiceRate,
    TenantContract,
    TenantServiceRate,
    TenantUsagePolicy,
)

_CLAUDE_MODEL_RE = re.compile(r"claude-[a-z0-9._-]{1,72}")


class LeadForm(forms.ModelForm):  # type: ignore[type-arg]
    # The stored columns are encrypted text, so length and format are enforced here.
    contact_name = forms.CharField(
        max_length=150,
        label="Seu nome",
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    contact_email = forms.EmailField(
        max_length=254,
        label="E-mail de contato",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "spellcheck": "false"}),
    )
    cnpj = forms.CharField(
        max_length=18,
        label="CNPJ do escritório",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "autocapitalize": "characters",
                "spellcheck": "false",
                "placeholder": "00.000.000/0000-00…",
            }
        ),
    )

    class Meta:
        model = Lead
        fields = ("contact_name", "contact_email", "cnpj")

    def clean_cnpj(self) -> str:
        return normalize_cnpj(self.cleaned_data["cnpj"])

    def save(self, commit: bool = True) -> Lead:
        lead = super().save(commit=False)
        registry = lookup_company(self.cleaned_data["cnpj"])
        lead.office_name = registry.get("razao_social") or f"CNPJ {lead.cnpj}"
        lead.registry_data = json.dumps(registry, ensure_ascii=False)
        if commit:
            lead.save()
        return lead


class LegacyLeadForm(forms.ModelForm):  # type: ignore[type-arg]
    """Compatibility-only parser for old integrations posting to /proposta/."""

    office_name = forms.CharField(max_length=160)
    contact_name = forms.CharField(max_length=150)
    contact_email = forms.EmailField(max_length=254)
    message = forms.CharField(max_length=1000, required=False)

    class Meta:
        model = Lead
        fields = ("office_name", "contact_name", "contact_email", "company_count", "message")
        widgets = {
            "office_name": forms.TextInput(attrs={"autocomplete": "organization"}),
            "contact_name": forms.TextInput(attrs={"autocomplete": "name"}),
            "contact_email": forms.EmailInput(
                attrs={"autocomplete": "email", "spellcheck": "false"}
            ),
            "company_count": forms.NumberInput(attrs={"min": 1, "inputmode": "numeric"}),
            "message": forms.Textarea(attrs={"rows": 3}),
        }
        labels = {
            "office_name": "Nome do escritório",
            "contact_name": "Seu nome",
            "contact_email": "E-mail de contato",
            "company_count": "Quantidade de empresas",
            "message": "Como podemos ajudar?",
        }


class SelfServiceSignupForm(forms.Form):
    full_name = forms.CharField(
        max_length=150, label="Seu nome", widget=forms.TextInput(attrs={"autocomplete": "name"})
    )
    email = forms.EmailField(
        max_length=254,
        label="E-mail profissional",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "spellcheck": "false"}),
    )
    cnpj = forms.CharField(
        max_length=18,
        label="CNPJ do escritório",
        widget=forms.TextInput(attrs={"inputmode": "numeric", "autocomplete": "off"}),
    )
    accept_terms = forms.BooleanField(
        label="Li e aceito os Termos de Uso e a Política de Privacidade."
    )

    accept_marketing = forms.BooleanField(
        required=False,
        label="Quero receber novidades da CICA por e-mail.",
    )

    def clean_email(self) -> str:
        return str(self.cleaned_data["email"]).strip().casefold()

    def clean_cnpj(self) -> str:
        return normalize_cnpj(str(self.cleaned_data["cnpj"]))


class SignupPasswordForm(forms.Form):
    password = forms.CharField(
        min_length=12,
        label="Crie uma senha",
        help_text="Use pelo menos 12 caracteres. Colar do gerenciador de senhas é permitido.",
        widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}),
    )

    def clean_password(self) -> str:
        password = str(self.cleaned_data["password"])
        try:
            validate_password(password)
        except ValidationError as exc:
            raise forms.ValidationError(list(exc.messages)) from exc
        return password


class PlanCatalogForm(forms.ModelForm):  # type: ignore[type-arg]
    """Developer-managed commercial catalogue; contracts keep their own snapshots."""

    monthly_price_brl = forms.DecimalField(
        label="Mensalidade-base",
        min_value=0,
        decimal_places=2,
        max_digits=12,
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "inputmode": "decimal"}),
    )
    modules = forms.MultipleChoiceField(
        label="Módulos incluídos",
        required=False,
        choices=(
            ("nfse", "NFS-e Inteligente"),
            ("guides", "Guias e DCTFWeb"),
            ("integra", "Central Integra Contador"),
            ("reconciliation", "Conciliação OFX"),
            ("reform", "Radar da Reforma"),
            ("journey", "Jornadas"),
            ("ai", "Copiloto CICA"),
        ),
        widget=forms.CheckboxSelectMultiple,
    )
    ai_included_requests = forms.IntegerField(
        label="Perguntas incluídas por mês",
        min_value=0,
        initial=0,
        help_text="No teste, o limite bloqueia novas perguntas sem cobrança automática.",
        widget=forms.NumberInput(
            attrs={"min": "0", "inputmode": "numeric", "autocomplete": "off"}
        ),
    )
    ai_overage_price_brl = forms.DecimalField(
        label="Valor por pergunta excedente",
        min_value=0,
        decimal_places=2,
        max_digits=10,
        initial=0,
        help_text="Só poderá ser cobrado em contrato que autorize excedente.",
        widget=forms.NumberInput(
            attrs={"min": "0", "step": "0.01", "inputmode": "decimal", "autocomplete": "off"}
        ),
    )

    class Meta:
        model = Plan
        fields = ("code", "name", "version", "is_active", "modules")
        labels = {
            "code": "Código interno",
            "name": "Nome apresentado",
            "version": "Versão",
            "is_active": "Disponível para novas contratações",
        }
        widgets = {
            "code": forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
            "name": forms.TextInput(attrs={"autocomplete": "off"}),
            "version": forms.NumberInput(
                attrs={"min": "1", "inputmode": "numeric", "autocomplete": "off"}
            ),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["monthly_price_brl"].initial = Decimal(self.instance.monthly_price_cents) / 100
        self.fields["modules"].initial = self.instance.modules
        if self.instance.pk:
            rate = self.instance.service_rates.filter(action_code="ai.answer").first()
            if rate:
                self.fields["ai_included_requests"].initial = rate.included_units
                self.fields["ai_overage_price_brl"].initial = (
                    Decimal(rate.overage_unit_price_cents) / 100
                )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean()
        if "ai" in cleaned.get("modules", []) and not cleaned.get("ai_included_requests"):
            self.add_error(
                "ai_included_requests",
                "Informe ao menos uma pergunta quando o Copiloto estiver incluído.",
            )
        return cleaned

    def save(self, commit: bool = True) -> Plan:
        plan = super().save(commit=False)
        plan.monthly_price_cents = int(self.cleaned_data["monthly_price_brl"] * 100)
        plan.modules = list(self.cleaned_data["modules"])
        if commit:
            plan.save()
            self.save_m2m()
            if "ai" in plan.modules:
                PlanServiceRate.objects.update_or_create(
                    plan=plan,
                    action_code="ai.answer",
                    defaults={
                        "included_units": self.cleaned_data["ai_included_requests"],
                        "overage_unit_price_cents": int(
                            self.cleaned_data["ai_overage_price_brl"] * 100
                        ),
                    },
                )
            else:
                PlanServiceRate.objects.filter(plan=plan, action_code="ai.answer").delete()
        return cast(Plan, plan)


class TenantContractForm(forms.ModelForm):  # type: ignore[type-arg]
    monthly_price_brl = forms.DecimalField(
        label="Mensalidade",
        decimal_places=2,
        max_digits=12,
        min_value=0,
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "inputmode": "decimal"}),
    )

    class Meta:
        model = TenantContract
        fields = ("plan", "status", "reference", "starts_on", "ends_on", "grace_ends_on", "notes")
        widgets = {
            "starts_on": forms.DateInput(attrs={"type": "date"}),
            "ends_on": forms.DateInput(attrs={"type": "date"}),
            "grace_ends_on": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self._initial_plan_id = self.instance.plan_id
        self.fields["monthly_price_brl"].initial = self.instance.monthly_price_cents / 100

    def save(self, commit: bool = True) -> TenantContract:
        contract = super().save(commit=False)
        contract.monthly_price_cents = int(self.cleaned_data["monthly_price_brl"] * 100)
        contract.monthly_price_locked = True
        if contract.plan_id and contract.plan_id != self._initial_plan_id:
            contract.selected_modules = list(contract.plan.modules)
        if commit:
            contract.save()
            self.save_m2m()
        return cast(TenantContract, contract)


class TenantServiceRateForm(forms.Form):
    service = forms.ChoiceField(label="Serviço")
    included_units = forms.IntegerField(label="Franquia", min_value=0)
    overage_price_brl = forms.DecimalField(
        label="Excedente", min_value=0, decimal_places=2, max_digits=12
    )
    overage_cap_brl = forms.DecimalField(
        label="Teto mensal", min_value=0, decimal_places=2, max_digits=12
    )
    overage_mode = forms.ChoiceField(
        label="Ao atingir o limite", choices=TenantUsagePolicy.OverageMode.choices
    )

    def __init__(self, *args: Any, contract: TenantContract | None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.contract = contract
        cast(forms.ChoiceField, self.fields["service"]).choices = [
            (key, spec.label) for key, spec in SERVICES.items() if spec.billable
        ]

    def save(self) -> None:
        if self.contract is None:
            raise ValueError("Contrato ausente.")
        data = self.cleaned_data
        code = cast(str, data["service"])
        TenantServiceRate.objects.update_or_create(
            contract=self.contract,
            action_code=code,
            defaults={
                "included_units": data["included_units"],
                "overage_unit_price_cents": int(data["overage_price_brl"] * 100),
            },
        )
        TenantUsagePolicy.objects.update_or_create(
            organization=self.contract.organization,
            action_code=code,
            defaults={
                "overage_mode": data["overage_mode"],
                "monthly_overage_cap_cents": int(data["overage_cap_brl"] * 100),
            },
        )


class ClaudeFallbackForm(forms.Form):
    """Developer-only policy for the encrypted, last-resort cloud route."""

    enabled = forms.BooleanField(
        required=False,
        label="Permitir fallback externo após timeout técnico local",
    )
    allow_full_data = forms.BooleanField(
        required=False,
        label="Permitir contexto completo quando o fallback for usado",
    )
    allowed_roles = forms.MultipleChoiceField(
        label="Perfis autorizados",
        choices=(
            (Membership.Role.OWNER, "Proprietário"),
            (Membership.Role.ADMIN, "Administrador"),
            (Membership.Role.MANAGER, "Gestor"),
            (Membership.Role.OPERATOR, "Operador"),
            (Membership.Role.AUDITOR, "Auditor"),
            (Membership.Role.BILLING, "Financeiro"),
        ),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    api_key = forms.CharField(
        label="Chave do provedor",
        required=False,
        help_text="Fica cifrada e não será exibida novamente.",
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
    )
    clear_api_key = forms.BooleanField(required=False, label="Remover chave armazenada")
    model = forms.CharField(
        label="Modelo permitido",
        max_length=80,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
    )
    max_request_brl = forms.DecimalField(
        label="Teto por solicitação (R$)",
        min_value=Decimal("0"),
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "inputmode": "decimal"}),
    )
    daily_limit_brl = forms.DecimalField(
        label="Teto diário aprovado (R$)",
        min_value=Decimal("0"),
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "inputmode": "decimal"}),
    )
    monthly_limit_brl = forms.DecimalField(
        label="Teto mensal aprovado (R$)",
        min_value=Decimal("0"),
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={"min": "0", "step": "0.01", "inputmode": "decimal"}),
    )
    valid_until = forms.DateTimeField(
        label="Aprovação válida até",
        required=False,
        widget=forms.DateTimeInput(attrs={"type": "datetime-local", "autocomplete": "off"}),
    )

    def __init__(self, *args: Any, settings: Any, approval: Any, **kwargs: Any) -> None:
        self.settings = settings
        self.approval = approval
        super().__init__(*args, **kwargs)
        if self.is_bound:
            return
        self.initial.update(
            {
                "enabled": bool(settings and settings.claude_fallback_enabled),
                "allow_full_data": bool(settings and settings.claude_full_data_allowed),
                "allowed_roles": list(settings.claude_allowed_roles) if settings else [],
                "model": settings.claude_model if settings else "",
                "max_request_brl": (
                    Decimal(settings.claude_max_request_cents) / 100 if settings else None
                ),
                "daily_limit_brl": (
                    Decimal(approval.daily_limit_cents) / 100 if approval else None
                ),
                "monthly_limit_brl": (
                    Decimal(approval.monthly_limit_cents) / 100 if approval else None
                ),
                "valid_until": approval.valid_until if approval else None,
            }
        )

    @staticmethod
    def cents(value: Decimal | None) -> int:
        if value is None:
            return 0
        return int((value * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        enabled = bool(cleaned.get("enabled"))
        if not enabled:
            return cleaned
        if not cleaned.get("allowed_roles"):
            self.add_error("allowed_roles", "Selecione ao menos um perfil.")
        model = str(cleaned.get("model") or "")
        if not _CLAUDE_MODEL_RE.fullmatch(model):
            self.add_error("model", "Informe um modelo Claude permitido.")
        if not cleaned.get("api_key") and not (self.settings and self.settings.claude_api_key):
            self.add_error("api_key", "Informe a chave antes de habilitar o fallback.")
        if cleaned.get("clear_api_key"):
            self.add_error("clear_api_key", "Não remova a chave enquanto o fallback estiver ativo.")
        for field in ("max_request_brl", "daily_limit_brl", "monthly_limit_brl"):
            if self.cents(cleaned.get(field)) <= 0:
                self.add_error(field, "Informe um teto maior que zero.")
        valid_until = cleaned.get("valid_until")
        if valid_until is None:
            self.add_error("valid_until", "Defina quando essa aprovação expira.")
        elif valid_until <= timezone.now():
            self.add_error("valid_until", "Informe uma data futura.")
        return cleaned


class ClaudeFallbackCredentialForm(forms.Form):
    """Local provider secret, deliberately separate from a CRMew-owned policy."""

    api_key = forms.CharField(
        label="Nova chave do provedor",
        required=False,
        help_text="Fica cifrada e não será exibida novamente.",
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
    )
    clear_api_key = forms.BooleanField(
        required=False,
        label="Remover a chave armazenada",
        help_text="Isso bloqueia o fallback até que uma nova chave seja configurada.",
    )

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        api_key = str(cleaned.get("api_key") or "").strip()
        clear_api_key = bool(cleaned.get("clear_api_key"))
        if api_key and clear_api_key:
            self.add_error(
                "clear_api_key", "Escolha cadastrar uma chave ou removê-la, não os dois."
            )
        elif not api_key and not clear_api_key:
            self.add_error("api_key", "Informe uma nova chave ou selecione a remoção.")
        return cleaned


class AssistantRetentionForm(forms.Form):
    """Developer-controlled retention with an explicit safeguard for shortening it."""

    retention_days = forms.IntegerField(
        min_value=1,
        max_value=3650,
        label="Dias de retenção das conversas",
        help_text="A rotina diária remove apenas conversas elegíveis após esse prazo.",
        widget=forms.NumberInput(attrs={"min": "1", "max": "3650", "inputmode": "numeric"}),
    )
    confirm_shortening = forms.BooleanField(
        required=False,
        label="Confirmo que encurtar o prazo pode tornar conversas antigas elegíveis para remoção.",
    )

    def __init__(self, *args: Any, settings: Any, **kwargs: Any) -> None:
        self.settings = settings
        super().__init__(*args, **kwargs)
        if not self.is_bound:
            self.initial["retention_days"] = settings.retention_days if settings else 90

    def clean(self) -> dict[str, Any]:
        cleaned = super().clean() or {}
        current_days = self.settings.retention_days if self.settings else 90
        requested_days = cleaned.get("retention_days")
        if (
            isinstance(requested_days, int)
            and requested_days < current_days
            and not cleaned.get("confirm_shortening")
        ):
            self.add_error(
                "confirm_shortening",
                "Confirme a redução antes de salvar uma retenção menor.",
            )
        return cleaned


class InvitationForm(forms.Form):
    email = forms.EmailField(
        label="E-mail do proprietário",
        widget=forms.EmailInput(attrs={"autocomplete": "email", "spellcheck": "false"}),
    )
    full_name = forms.CharField(
        label="Nome",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={"autocomplete": "name"}),
    )
    role = forms.ChoiceField(label="Papel", choices=[(Membership.Role.OWNER, "Proprietário")])
