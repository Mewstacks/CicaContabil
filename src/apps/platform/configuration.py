import base64
import hashlib
import re
from datetime import date
from decimal import Decimal
from pathlib import Path

from cryptography.hazmat.primitives.serialization import pkcs12
from django import forms
from django.conf import settings as django_settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from apps.accounts import mfa
from apps.audit.services import record_event
from apps.common.cnpj import lookup_company, normalize_cnpj
from apps.common.database_email import smtp_backend_for_configuration
from apps.platform.forms import PlanCatalogForm
from apps.platform.models import (
    BillingCloseDeferral,
    Plan,
    PlatformAccess,
    PlatformConfiguration,
    TenantContract,
)
from apps.platform.operations import scheduled_operation_overview
from apps.platform.policies import platform_required
from apps.platform.views import context


class ConfigurationForm(forms.ModelForm):
    provider_cnpj = forms.CharField(
        max_length=18,
        label="CNPJ da fornecedora",
        widget=forms.TextInput(
            attrs={"autocomplete": "off", "inputmode": "numeric", "spellcheck": "false"}
        ),
    )

    class Meta:
        model = PlatformConfiguration
        fields = (
            "provider_cnpj",
            "support_email",
            "support_phone",
            "privacy_email",
            "support_hours",
            "legal_address",
        )
        labels = {
            "provider_cnpj": "CNPJ da fornecedora",
            "support_email": "E-mail público da Mewstack",
            "support_phone": "Telefone público",
            "privacy_email": "Canal de privacidade",
            "support_hours": "Dias e horário de atendimento",
            "legal_address": "Endereço comercial da Mewstack",
        }
        widgets = {
            "support_email": forms.EmailInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
            "support_phone": forms.TextInput(attrs={"autocomplete": "off", "inputmode": "tel"}),
            "privacy_email": forms.EmailInput(attrs={"autocomplete": "off", "spellcheck": "false"}),
            "support_hours": forms.Textarea(attrs={"autocomplete": "off", "rows": 3}),
            "legal_address": forms.Textarea(attrs={"autocomplete": "street-address", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.is_bound and self.instance._state.adding:
            self.fields["provider_cnpj"].initial = "68340160000113"
        elif not self.is_bound and len(self.instance.provider_cnpj) == 14:
            value = self.instance.provider_cnpj
            self.initial["provider_cnpj"] = (
                f"{value[:2]}.{value[2:5]}.{value[5:8]}/{value[8:12]}-{value[12:]}"
            )

    def clean_provider_cnpj(self) -> str:
        return normalize_cnpj(self.cleaned_data["provider_cnpj"])


class IntegraCertificateForm(forms.Form):
    certificate = forms.FileField(
        label="Certificado A1 da Mewstack (.pfx ou .p12)",
        help_text="Máximo de 2 MB. O arquivo será cifrado e não poderá ser baixado.",
    )
    password = forms.CharField(
        label="Senha do certificado",
        required=False,
        strip=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "new-password", "spellcheck": "false"},
        ),
    )

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        upload = cleaned.get("certificate")
        if upload is None:
            return cleaned
        if upload.size > 2 * 1024 * 1024:
            self.add_error("certificate", "O certificado deve ter no máximo 2 MB.")
            return cleaned
        suffix = Path(upload.name).suffix.lower()
        if suffix not in {".pfx", ".p12"}:
            self.add_error("certificate", "Envie um certificado PKCS#12 .pfx ou .p12.")
            return cleaned
        blob = upload.read()
        password = str(cleaned.get("password") or "")
        try:
            key, certificate, _chain = pkcs12.load_key_and_certificates(
                blob, password.encode() or None
            )
        except ValueError:
            self.add_error("password", "Não foi possível abrir o certificado com esta senha.")
            return cleaned
        if key is None or certificate is None:
            self.add_error("certificate", "O arquivo não contém certificado e chave privada.")
            return cleaned
        cleaned["certificate_bytes"] = blob
        cleaned["parsed_certificate"] = certificate
        return cleaned

    def save(self, configuration: PlatformConfiguration) -> PlatformConfiguration:
        upload = self.cleaned_data["certificate"]
        blob = self.cleaned_data["certificate_bytes"]
        certificate = self.cleaned_data["parsed_certificate"]
        configuration.integra_certificate_blob = base64.b64encode(blob).decode("ascii")
        configuration.integra_certificate_password = str(self.cleaned_data.get("password") or "")
        configuration.integra_certificate_name = Path(upload.name).name[:180]
        configuration.integra_certificate_fingerprint = hashlib.sha256(blob).hexdigest()
        configuration.integra_certificate_subject = certificate.subject.rfc4514_string()[:240]
        configuration.integra_certificate_valid_until = certificate.not_valid_after_utc
        configuration.save()
        return configuration


class IntegraCredentialsForm(forms.ModelForm):
    """Write-only central Serpro credentials, protected by the platform MFA gate."""

    consumer_key = forms.CharField(
        label="Consumer key",
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "new-password", "spellcheck": "false"},
        ),
    )
    consumer_secret = forms.CharField(
        label="Consumer secret",
        required=False,
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "new-password", "spellcheck": "false"},
        ),
    )
    integra_contratante_cnpj = forms.CharField(
        max_length=18,
        label="CNPJ contratante",
        widget=forms.TextInput(
            attrs={"autocomplete": "off", "inputmode": "numeric", "spellcheck": "false"}
        ),
    )
    integra_autor_pedido_cnpj = forms.CharField(
        max_length=18,
        required=False,
        label="CNPJ autor do pedido (fallback)",
        help_text="Deixe vazio para usar o CNPJ do escritório responsável pela consulta.",
        widget=forms.TextInput(
            attrs={"autocomplete": "off", "inputmode": "numeric", "spellcheck": "false"}
        ),
    )
    confirm_production = forms.BooleanField(
        required=False,
        label="Confirmo que as credenciais pertencem ao ambiente de produção.",
        help_text="A alteração só grava a configuração; ela não realiza consultas ao Serpro.",
    )
    field_order = (
        "integra_environment",
        "integra_contratante_cnpj",
        "integra_autor_pedido_cnpj",
        "consumer_key",
        "consumer_secret",
        "confirm_production",
    )

    class Meta:
        model = PlatformConfiguration
        fields = ("integra_contratante_cnpj", "integra_autor_pedido_cnpj", "integra_environment")
        labels = {
            "integra_contratante_cnpj": "CNPJ contratante",
            "integra_autor_pedido_cnpj": "CNPJ autor do pedido",
            "integra_environment": "Ambiente",
        }
        widgets = {
            "integra_environment": forms.Select(
                choices=(("trial", "Homologação"), ("production", "Produção"))
            ),
        }

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if field.help_text:
                field.widget.attrs["aria-describedby"] = f"id_{name}_helptext"

    def clean_integra_contratante_cnpj(self) -> str:
        value = normalize_cnpj(self.cleaned_data["integra_contratante_cnpj"])
        if not value:
            raise forms.ValidationError("Informe o CNPJ contratante da Mewstack.")
        return value

    def clean_integra_autor_pedido_cnpj(self) -> str:
        value = str(self.cleaned_data.get("integra_autor_pedido_cnpj") or "")
        return normalize_cnpj(value) if value else ""

    def clean_integra_environment(self) -> str:
        value = str(self.cleaned_data["integra_environment"])
        if value not in {"trial", "production"}:
            raise forms.ValidationError("Selecione homologação ou produção.")
        return value

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        key = str(cleaned.get("consumer_key") or "")
        secret = str(cleaned.get("consumer_secret") or "")
        if not key and not self.instance.integra_consumer_key:
            self.add_error("consumer_key", "Informe a consumer key para concluir a configuração.")
            self.fields["consumer_key"].widget.attrs["aria-describedby"] = (
                "id_consumer_key_error"
            )
        if not secret and not self.instance.integra_consumer_secret:
            self.add_error(
                "consumer_secret", "Informe a consumer secret para concluir a configuração."
            )
            self.fields["consumer_secret"].widget.attrs["aria-describedby"] = (
                "id_consumer_secret_error"
            )
        if (
            cleaned.get("integra_environment") == "production"
            and not cleaned.get("confirm_production")
        ):
            self.add_error(
                "confirm_production",
                "Confirme a mudança para produção antes de salvar.",
            )
            self.fields["confirm_production"].widget.attrs["aria-describedby"] = (
                "id_confirm_production_helptext id_confirm_production_error"
            )
        return cleaned

    def save(self, commit: bool = True) -> PlatformConfiguration:
        configuration = super().save(commit=False)
        key = str(self.cleaned_data.get("consumer_key") or "")
        secret = str(self.cleaned_data.get("consumer_secret") or "")
        if key:
            configuration.integra_consumer_key = key
        if secret:
            configuration.integra_consumer_secret = secret
        if commit:
            configuration.save()
        return configuration


class TrialConfigurationForm(forms.ModelForm):
    class Meta:
        model = PlatformConfiguration
        fields = ("trial_ai_included_requests",)
        labels = {"trial_ai_included_requests": "Perguntas do Copiloto no teste"}
        widgets = {
            "trial_ai_included_requests": forms.NumberInput(
                attrs={"min": "1", "inputmode": "numeric", "autocomplete": "off"}
            )
        }

    def clean_trial_ai_included_requests(self) -> int:
        allowance = int(self.cleaned_data["trial_ai_included_requests"])
        if allowance < 1:
            raise forms.ValidationError("Informe ao menos 1 pergunta para liberar novos testes.")
        return allowance


class CopilotAvailabilityForm(forms.ModelForm):
    """Developer-only release gate for the prepared Copilot runtime."""

    class Meta:
        model = PlatformConfiguration
        fields = ("copilot_available_for_offices", "trial_ai_included_requests")
        labels = {
            "copilot_available_for_offices": "Disponibilizar o Copiloto para escritórios",
            "trial_ai_included_requests": "Perguntas incluídas no teste",
        }
        widgets = {
            "trial_ai_included_requests": forms.NumberInput(
                attrs={"min": "0", "inputmode": "numeric", "autocomplete": "off"}
            )
        }

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        if (
            cleaned.get("copilot_available_for_offices")
            and int(cleaned.get("trial_ai_included_requests") or 0) < 1
        ):
            self.add_error(
                "trial_ai_included_requests",
                "Defina ao menos uma pergunta antes de disponibilizar o Copiloto.",
            )
        local_ready = bool(self.instance.local_llm_endpoint and self.instance.local_llm_model)
        cloud_ready = bool(
            self.instance.cloud_fallback_enabled
            and self.instance.cloud_fallback_model
            and (django_settings.CICA_CLAUDE_API_KEY or self.instance.cloud_fallback_api_key)
            and self.instance.cloud_fallback_max_request_cents > 0
            and self.instance.cloud_fallback_daily_limit_cents > 0
            and self.instance.cloud_fallback_monthly_limit_cents > 0
        )
        if cleaned.get("copilot_available_for_offices") and not (local_ready or cloud_ready):
            self.add_error(
                None,
                "Configure Claude com chave e limites ou o runtime local antes de "
                "disponibilizar o Copiloto.",
            )
        return cleaned


class LocalRuntimeForm(forms.ModelForm):
    """Developer-only local runtime setup; a blank token never clears the saved secret."""

    local_llm_api_key = forms.CharField(
        required=False,
        label="Token de acesso",
        help_text="Deixe em branco para manter o token já armazenado.",
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "new-password", "spellcheck": "false"},
        ),
    )

    class Meta:
        model = PlatformConfiguration
        fields = (
            "local_llm_endpoint",
            "local_llm_model",
            "local_llm_api_key",
            "local_multimodal_endpoint",
        )
        labels = {
            "local_llm_endpoint": "Endpoint local",
            "local_llm_model": "Modelo local",
            "local_multimodal_endpoint": "Endpoint de análise de documentos",
        }
        help_texts = {
            "local_llm_endpoint": (
                "URL interna compatível com OpenAI; a CICA acrescenta /v1/chat/completions."
            ),
            "local_llm_model": "Identificador enviado ao runtime local.",
            "local_multimodal_endpoint": (
                "URL privada do adaptador de PDF e imagem; a CICA acrescenta /v1/analyze-document."
            ),
        }
        widgets = {
            "local_llm_endpoint": forms.URLInput(
                attrs={"autocomplete": "off", "spellcheck": "false", "inputmode": "url"}
            ),
            "local_llm_model": forms.TextInput(
                attrs={"autocomplete": "off", "spellcheck": "false"}
            ),
            "local_multimodal_endpoint": forms.URLInput(
                attrs={"autocomplete": "off", "spellcheck": "false", "inputmode": "url"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_api_key = self.instance.local_llm_api_key if self.instance.pk else ""

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        endpoint = str(cleaned.get("local_llm_endpoint") or "").rstrip("/")
        model = str(cleaned.get("local_llm_model") or "").strip()
        multimodal_endpoint = str(cleaned.get("local_multimodal_endpoint") or "").rstrip("/")
        if bool(endpoint) != bool(model):
            self.add_error(
                "local_llm_endpoint" if not endpoint else "local_llm_model",
                "Informe endpoint e modelo juntos, ou deixe os dois em branco.",
            )
        cleaned["local_llm_endpoint"] = endpoint
        cleaned["local_llm_model"] = model
        cleaned["local_multimodal_endpoint"] = multimodal_endpoint
        return cleaned

    def save(self, commit: bool = True) -> PlatformConfiguration:
        configuration = super().save(commit=False)
        if not self.cleaned_data.get("local_llm_api_key"):
            configuration.local_llm_api_key = self._saved_api_key
        if commit:
            configuration.save()
        return configuration


_CLOUD_MODEL_RE = re.compile(r"claude-[a-z0-9._-]{1,72}")


class CloudFallbackForm(forms.ModelForm):
    """Mewstack-owned, encrypted last-resort cloud route."""

    cloud_fallback_api_key = forms.CharField(
        required=False,
        label="Chave do provedor",
        help_text="Deixe em branco para manter o segredo já armazenado.",
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "new-password", "spellcheck": "false"},
        ),
    )

    class Meta:
        model = PlatformConfiguration
        fields = (
            "cloud_fallback_enabled",
            "cloud_fallback_api_key",
            "cloud_fallback_model",
            "cloud_fallback_max_request_cents",
            "cloud_fallback_daily_limit_cents",
            "cloud_fallback_monthly_limit_cents",
        )
        labels = {
            "cloud_fallback_enabled": "Permitir Claude via API key",
            "cloud_fallback_model": "Modelo permitido",
            "cloud_fallback_max_request_cents": "Teto por solicitação (centavos)",
            "cloud_fallback_daily_limit_cents": "Teto diário da Mewstack (centavos)",
            "cloud_fallback_monthly_limit_cents": "Teto mensal da Mewstack (centavos)",
        }
        help_texts = {
            "cloud_fallback_enabled": (
                "Usado agora; quando o PC local estiver pronto, será reserva após falha técnica."
            ),
            "cloud_fallback_max_request_cents": "Reserva conservadora antes de chamar o provedor.",
        }
        widgets = {
            "cloud_fallback_model": forms.TextInput(
                attrs={"autocomplete": "off", "spellcheck": "false"}
            ),
            "cloud_fallback_max_request_cents": forms.NumberInput(
                attrs={"min": "0", "inputmode": "numeric", "autocomplete": "off"}
            ),
            "cloud_fallback_daily_limit_cents": forms.NumberInput(
                attrs={"min": "0", "inputmode": "numeric", "autocomplete": "off"}
            ),
            "cloud_fallback_monthly_limit_cents": forms.NumberInput(
                attrs={"min": "0", "inputmode": "numeric", "autocomplete": "off"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_api_key = self.instance.cloud_fallback_api_key if self.instance.pk else ""

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        if not cleaned.get("cloud_fallback_enabled"):
            return cleaned
        if not (
            cleaned.get("cloud_fallback_api_key")
            or self._saved_api_key
            or django_settings.CICA_CLAUDE_API_KEY
        ):
            self.add_error(
                "cloud_fallback_api_key",
                "Informe a chave no .env ou neste campo antes de habilitar Claude.",
            )
        model = str(cleaned.get("cloud_fallback_model") or "").strip()
        if not _CLOUD_MODEL_RE.fullmatch(model):
            self.add_error("cloud_fallback_model", "Informe um modelo permitido.")
        for field in (
            "cloud_fallback_max_request_cents",
            "cloud_fallback_daily_limit_cents",
            "cloud_fallback_monthly_limit_cents",
        ):
            if int(cleaned.get(field) or 0) <= 0:
                self.add_error(field, "Informe um teto maior que zero.")
        request_limit = int(cleaned.get("cloud_fallback_max_request_cents") or 0)
        daily_limit = int(cleaned.get("cloud_fallback_daily_limit_cents") or 0)
        monthly_limit = int(cleaned.get("cloud_fallback_monthly_limit_cents") or 0)
        if request_limit > daily_limit > 0:
            self.add_error(
                "cloud_fallback_daily_limit_cents", "O teto diário deve cobrir uma solicitação."
            )
        if daily_limit > monthly_limit > 0:
            self.add_error(
                "cloud_fallback_monthly_limit_cents", "O teto mensal deve cobrir o diário."
            )
        cleaned["cloud_fallback_model"] = model
        return cleaned

    def save(self, commit: bool = True) -> PlatformConfiguration:
        configuration = super().save(commit=False)
        if not self.cleaned_data.get("cloud_fallback_api_key"):
            configuration.cloud_fallback_api_key = self._saved_api_key
        if commit:
            configuration.save()
        return configuration


class TransactionalEmailForm(forms.ModelForm):
    """Write-only SMTP configuration owned by Mewstack developers."""

    transactional_email_password = forms.CharField(
        required=False,
        label="Senha ou token SMTP",
        help_text="Deixe em branco para manter o segredo já armazenado.",
        widget=forms.PasswordInput(
            render_value=False,
            attrs={"autocomplete": "new-password", "spellcheck": "false"},
        ),
    )

    class Meta:
        model = PlatformConfiguration
        fields = (
            "transactional_email_host",
            "transactional_email_port",
            "transactional_email_username",
            "transactional_email_password",
            "transactional_email_use_tls",
            "transactional_email_from",
        )
        labels = {
            "transactional_email_host": "Servidor SMTP",
            "transactional_email_port": "Porta",
            "transactional_email_username": "Usuário SMTP",
            "transactional_email_use_tls": "Usar TLS",
            "transactional_email_from": "Remetente padrão",
        }
        help_texts = {
            "transactional_email_host": "Nome do servidor, sem protocolo e sem caminho.",
            "transactional_email_from": (
                "Endereço exibido em confirmações, convites e recuperação de senha."
            ),
        }
        widgets = {
            "transactional_email_host": forms.TextInput(
                attrs={"autocomplete": "off", "spellcheck": "false"}
            ),
            "transactional_email_port": forms.NumberInput(
                attrs={"min": "1", "max": "65535", "inputmode": "numeric", "autocomplete": "off"}
            ),
            "transactional_email_username": forms.TextInput(
                attrs={"autocomplete": "off", "spellcheck": "false"}
            ),
            "transactional_email_from": forms.EmailInput(
                attrs={"autocomplete": "off", "spellcheck": "false"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_password = (
            self.instance.transactional_email_password if self.instance.pk else ""
        )

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        host = str(cleaned.get("transactional_email_host") or "").strip()
        username = str(cleaned.get("transactional_email_username") or "").strip()
        password = str(cleaned.get("transactional_email_password") or "")
        sender = str(cleaned.get("transactional_email_from") or "").strip()
        if host and ("://" in host or "/" in host):
            self.add_error("transactional_email_host", "Informe apenas o nome do servidor SMTP.")
        if host and not sender:
            self.add_error("transactional_email_from", "Informe o remetente padrão.")
        if sender and not host:
            self.add_error("transactional_email_host", "Informe o servidor SMTP.")
        if bool(username) != bool(password or self._saved_password):
            self.add_error(
                "transactional_email_password" if username else "transactional_email_username",
                (
                    "Usuário e senha SMTP devem ser informados juntos; deixe ambos vazios "
                    "para relay sem autenticação."
                ),
            )
        cleaned["transactional_email_host"] = host
        cleaned["transactional_email_username"] = username
        cleaned["transactional_email_from"] = sender
        return cleaned

    def save(self, commit: bool = True) -> PlatformConfiguration:
        configuration = super().save(commit=False)
        if not self.cleaned_data.get("transactional_email_password"):
            configuration.transactional_email_password = self._saved_password
        if commit:
            configuration.save()
        return configuration


def _registry_address(registry: dict[str, str]) -> str:
    complement = registry.get("complemento", "").strip()
    # Some public registry payloads repeat the complement verbatim (for
    # example, "FUNDOSFUNDOS"). Keep the value useful without publishing the
    # upstream duplication in CICA's legal pages.
    if len(complement) % 2 == 0:
        midpoint = len(complement) // 2
        if complement[:midpoint].casefold() == complement[midpoint:].casefold():
            complement = complement[:midpoint]
    street = " ".join(
        part
        for part in (
            registry.get("descricao_tipo_de_logradouro"),
            registry.get("logradouro"),
        )
        if part
    )
    address = ", ".join(
        part
        for part in (
            street,
            registry.get("numero"),
            complement,
            registry.get("bairro"),
        )
        if part
    )
    cep = registry.get("cep", "")
    if len(cep) == 8:
        cep = f"{cep[:5]}-{cep[5:]}"
    city = " / ".join(part for part in (registry.get("municipio"), registry.get("uf")) if part)
    return " · ".join(part for part in (address, city, f"CEP {cep}" if cep else "") if part)


@platform_required(PlatformAccess.Role.DEVELOPER)
@never_cache
@require_http_methods(["GET", "POST"])
@transaction.atomic
def configuration(request):
    if not mfa.session_is_verified(request):
        return redirect(
            "accounts:mfa-verify" if mfa.is_enrolled(request.user) else "accounts:mfa-setup"
        )
    action = request.POST.get("action", "provider")
    instance = PlatformConfiguration.objects.filter(key="default").first()
    form = ConfigurationForm(
        request.POST
        if request.method == "POST" and action in {"provider", "provider_sync"}
        else None,
        instance=instance,
    )
    trial_form = TrialConfigurationForm(
        request.POST if request.method == "POST" and action == "trial" else None,
        instance=instance,
    )
    copilot_form = CopilotAvailabilityForm(
        request.POST if request.method == "POST" and action == "copilot-availability" else None,
        instance=instance,
    )
    runtime_form = LocalRuntimeForm(
        request.POST if request.method == "POST" and action == "local-runtime" else None,
        instance=instance,
    )
    cloud_fallback_form = CloudFallbackForm(
        request.POST if request.method == "POST" and action == "cloud-fallback" else None,
        instance=instance,
    )
    email_form = TransactionalEmailForm(
        request.POST
        if request.method == "POST"
        and action in {"transactional-email", "transactional-email-test"}
        else None,
        instance=instance,
    )
    integra_certificate_form = IntegraCertificateForm(
        request.POST if request.method == "POST" and action == "integra-certificate" else None,
        request.FILES if request.method == "POST" and action == "integra-certificate" else None,
    )
    integra_credentials_form = IntegraCredentialsForm(
        request.POST if request.method == "POST" and action == "integra-credentials" else None,
        instance=instance,
    )
    plan_instance = Plan(is_active=False)
    selected_plan_id = (
        request.POST.get("plan_id") if request.method == "POST" else request.GET.get("plan")
    )
    if selected_plan_id:
        try:
            plans_query = Plan.objects
            if request.method == "POST" and action == "plan":
                plans_query = plans_query.select_for_update()
            plan_instance = plans_query.get(pk=selected_plan_id)
        except (ValidationError, Plan.DoesNotExist):
            return HttpResponse(status=404)
        # Entitlements still depend on the referenced plan. Never rewrite a
        # contracted version through the catalogue, including archived contracts.
        # A new code/version can be created without changing the old agreement.
        if plan_instance.tenantcontract_set.exists():
            return HttpResponse(status=409)
    plan_form = PlanCatalogForm(
        request.POST if request.method == "POST" and action == "plan" else None,
        instance=plan_instance,
    )
    if request.method == "POST" and action in {"provider", "provider_sync"} and form.is_valid():
        with transaction.atomic():
            config = form.save(commit=False)
            config.updated_by = request.user
            if action == "provider_sync":
                registry = lookup_company(config.provider_cnpj)
                if registry.get("status") != "found":
                    form.add_error(
                        "provider_cnpj",
                        "A consulta cadastral está indisponível. Tente novamente mais tarde.",
                    )
                    config = None
                else:
                    config.provider_legal_name = registry.get("razao_social", "")
                    config.provider_trade_name = registry.get("nome_fantasia", "")
                    config.provider_registration_status = registry.get(
                        "descricao_situacao_cadastral", ""
                    )
                    config.provider_primary_activity = registry.get("cnae_fiscal_descricao", "")
                    config.provider_registry_source = registry.get("source", "BrasilAPI")
                    config.provider_registry_checked_at = timezone.now()
                    try:
                        config.provider_opened_on = date.fromisoformat(
                            registry.get("data_inicio_atividade", "")
                        )
                    except ValueError:
                        config.provider_opened_on = None
                    config.legal_address = _registry_address(registry)
            if config is not None:
                config.save()
                record_event(
                    action=(
                        "platform.provider_registry.synced"
                        if action == "provider_sync"
                        else "platform.configuration.updated"
                    ),
                    actor=request.user,
                    target=config,
                    request=request,
                )
        if config is None:
            pass
        else:
            messages.success(
                request,
                "Cadastro público atualizado."
                if action == "provider_sync"
                else "Dados da Mewstack atualizados.",
            )
            return redirect("platform:configuration")
    if request.method == "POST" and action == "trial" and trial_form.is_valid():
        configuration = trial_form.save(commit=False)
        configuration.updated_by = request.user
        configuration.save()
        record_event(
            action="platform.trial_configuration.updated",
            actor=request.user,
            target=configuration,
            request=request,
            metadata={"trial_ai_included_requests": configuration.trial_ai_included_requests},
        )
        messages.success(request, "Franquia do Copiloto para novos testes atualizada.")
        return redirect("platform:configuration")
    if (
        request.method == "POST"
        and action == "integra-certificate"
        and integra_certificate_form.is_valid()
    ):
        configuration = instance or PlatformConfiguration(key="default")
        configuration.updated_by = request.user
        integra_certificate_form.save(configuration)
        record_event(
            action="platform.integra_certificate.updated",
            actor=request.user,
            target=configuration,
            request=request,
            metadata={
                "fingerprint_suffix": configuration.integra_certificate_fingerprint[-12:],
                "valid_until": (
                    configuration.integra_certificate_valid_until.isoformat()
                    if configuration.integra_certificate_valid_until
                    else ""
                ),
            },
        )
        messages.success(request, "Certificado A1 da Mewstack armazenado com segurança.")
        return redirect("platform:configuration")
    if (
        request.method == "POST"
        and action == "integra-credentials"
        and integra_credentials_form.is_valid()
    ):
        configuration = integra_credentials_form.save(commit=False)
        configuration.updated_by = request.user
        configuration.save()
        record_event(
            action="platform.integra_credentials.updated",
            actor=request.user,
            target=configuration,
            request=request,
            metadata={
                "consumer_key_configured": bool(configuration.integra_consumer_key),
                "consumer_secret_configured": bool(configuration.integra_consumer_secret),
                "contratante_configured": bool(configuration.integra_contratante_cnpj),
                "environment": configuration.integra_environment,
            },
        )
        messages.success(request, "Credenciais centrais do Integra Contador atualizadas.")
        return redirect("platform:configuration")
    if request.method == "POST" and action == "copilot-availability" and copilot_form.is_valid():
        configuration = copilot_form.save(commit=False)
        configuration.updated_by = request.user
        configuration.save()
        record_event(
            action="platform.copilot_availability.updated",
            actor=request.user,
            target=configuration,
            request=request,
            metadata={
                "available_for_offices": configuration.copilot_available_for_offices,
                "trial_ai_included_requests": configuration.trial_ai_included_requests,
            },
        )
        messages.success(request, "Disponibilidade do Copiloto atualizada.")
        return redirect("platform:configuration")
    if request.method == "POST" and action == "local-runtime" and runtime_form.is_valid():
        configuration = runtime_form.save(commit=False)
        configuration.updated_by = request.user
        configuration.save()
        record_event(
            action="platform.copilot_runtime.updated",
            actor=request.user,
            target=configuration,
            request=request,
            metadata={
                "endpoint_configured": bool(configuration.local_llm_endpoint),
                "model_configured": bool(configuration.local_llm_model),
                "token_configured": bool(configuration.local_llm_api_key),
            },
        )
        messages.success(request, "Runtime local do Copiloto atualizado.")
        return redirect("platform:configuration")
    if request.method == "POST" and action == "cloud-fallback" and cloud_fallback_form.is_valid():
        configuration = cloud_fallback_form.save(commit=False)
        configuration.updated_by = request.user
        configuration.save()
        record_event(
            action="platform.cloud_fallback.updated",
            actor=request.user,
            target=configuration,
            request=request,
            metadata={
                "enabled": configuration.cloud_fallback_enabled,
                "model": configuration.cloud_fallback_model,
                "api_key_configured": bool(configuration.cloud_fallback_api_key),
                "max_request_cents": configuration.cloud_fallback_max_request_cents,
                "daily_limit_cents": configuration.cloud_fallback_daily_limit_cents,
                "monthly_limit_cents": configuration.cloud_fallback_monthly_limit_cents,
            },
        )
        messages.success(request, "Fallback externo da Mewstack atualizado.")
        return redirect("platform:configuration")
    if (
        request.method == "POST"
        and action in {"transactional-email", "transactional-email-test"}
        and email_form.is_valid()
    ):
        configuration = email_form.save(commit=False)
        if action == "transactional-email-test":
            try:
                backend = smtp_backend_for_configuration(configuration)
                backend.open()
                backend.close()
            except Exception:
                email_form.add_error(
                    None,
                    (
                        "Não foi possível autenticar no SMTP. Confira servidor, porta, TLS e "
                        "credenciais."
                    ),
                )
            else:
                messages.success(request, "Conexão SMTP validada. Nenhum e-mail foi enviado.")
                return redirect("platform:configuration")
        else:
            configuration.updated_by = request.user
            configuration.save()
            record_event(
                action="platform.transactional_email.updated",
                actor=request.user,
                target=configuration,
                request=request,
                metadata={
                    "host_configured": bool(configuration.transactional_email_host),
                    "username_configured": bool(configuration.transactional_email_username),
                    "password_configured": bool(configuration.transactional_email_password),
                    "tls_enabled": configuration.transactional_email_use_tls,
                    "sender_configured": bool(configuration.transactional_email_from),
                },
            )
            messages.success(request, "Configuração de e-mail transacional atualizada.")
            return redirect("platform:configuration")
    if request.method == "POST" and action == "plan" and plan_form.is_valid():
        with transaction.atomic():
            plan = plan_form.save()
            record_event(
                action="platform.plan_catalog.updated",
                actor=request.user,
                target=plan,
                request=request,
                metadata={"code": plan.code, "version": plan.version, "active": plan.is_active},
            )
        messages.success(
            request,
            "Catálogo comercial salvo. Contratos existentes mantêm seus valores registrados.",
        )
        return redirect("platform:configuration")
    plans = list(Plan.objects.prefetch_related("service_rates").order_by("name", "version"))
    contracted_plan_ids = set(TenantContract.objects.values_list("plan_id", flat=True))
    for plan in plans:
        plan.is_contracted = plan.pk in contracted_plan_ids  # type: ignore[attr-defined]
        plan.ai_rate = next(  # type: ignore[attr-defined]
            (rate for rate in plan.service_rates.all() if rate.action_code == "ai.answer"), None
        )
        plan.monthly_price_brl = Decimal(plan.monthly_price_cents) / 100  # type: ignore[attr-defined]
    ctx = context(request)
    integra_required = (
        "INTEGRA_CONSUMER_KEY",
        "INTEGRA_CONSUMER_SECRET",
        "INTEGRA_CONTRATANTE_CNPJ",
    )
    credential_values = {
        "INTEGRA_CONSUMER_KEY": (instance.integra_consumer_key if instance else "")
        or getattr(django_settings, "INTEGRA_CONSUMER_KEY", ""),
        "INTEGRA_CONSUMER_SECRET": (instance.integra_consumer_secret if instance else "")
        or getattr(django_settings, "INTEGRA_CONSUMER_SECRET", ""),
        "INTEGRA_CONTRATANTE_CNPJ": (instance.integra_contratante_cnpj if instance else "")
        or getattr(django_settings, "INTEGRA_CONTRATANTE_CNPJ", ""),
    }
    integra_missing = [name for name in integra_required if not credential_values[name]]
    integra_credential_status = {
        "environment": (instance.integra_environment if instance else "")
        or getattr(django_settings, "INTEGRA_ENVIRONMENT", "trial"),
        "consumer_key": bool(credential_values["INTEGRA_CONSUMER_KEY"]),
        "consumer_secret": bool(credential_values["INTEGRA_CONSUMER_SECRET"]),
        "contratante": bool(credential_values["INTEGRA_CONTRATANTE_CNPJ"]),
    }
    certificate_path = str(getattr(django_settings, "INTEGRA_CERTIFICATE_PATH", "") or "")
    certificate_found = bool(
        (instance and instance.integra_certificate_blob)
        or (certificate_path and Path(certificate_path).is_file())
    )
    integra_ready = not integra_missing and certificate_found
    ctx.update(
        page_title="Configurações da CICA",
        form=form,
        trial_form=trial_form,
        copilot_form=copilot_form,
        runtime_form=runtime_form,
        cloud_fallback_form=cloud_fallback_form,
        email_form=email_form,
        integra_certificate_form=integra_certificate_form,
        integra_credentials_form=integra_credentials_form,
        operation_rows=scheduled_operation_overview(),
        billing_close_deferrals=list(
            BillingCloseDeferral.objects.filter(resolved_at__isnull=True)
            .select_related("organization")
            .order_by("period_start", "organization__name")[:30]
        ),
        copilot_available=bool(instance and instance.copilot_available_for_offices),
        plan_form=plan_form,
        editing_plan=bool(selected_plan_id),
        plans=plans,
        integra_missing=integra_missing,
        integra_ready=integra_ready,
        integra_credential_status=integra_credential_status,
        integra_certificate_found=certificate_found,
        integra_certificate=instance if instance and instance.integra_certificate_blob else None,
        integra_environment=(instance.integra_environment if instance else "")
        or getattr(django_settings, "INTEGRA_ENVIRONMENT", "trial"),
    )
    return render(request, "platform/configuration.html", ctx)
