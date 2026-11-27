"""Formulários do Envio ao cliente."""

from __future__ import annotations

from datetime import date
from typing import Any

from django import forms
from django.db.models import QuerySet

from apps.delivery.models import MAX_ATTACHMENT_BYTES, DeliveryAccount
from apps.delivery.services import parse_recipients
from apps.delivery.transports import smtp_host_error
from apps.hub.models import ClientCompany


class MonthField(forms.Field):
    widget = forms.DateInput(attrs={"type": "month"}, format="%Y-%m")

    def to_python(self, value: Any) -> date | None:
        text = str(value or "").strip()
        if not text:
            return None
        try:
            year, month = text.split("-")
            return date(int(year), int(month), 1)
        except (ValueError, TypeError) as exc:
            raise forms.ValidationError("Informe mês e ano.") from exc


class ComposeForm(forms.Form):
    company = forms.ModelChoiceField(queryset=ClientCompany.objects.none(), label="Empresa")
    recipients = forms.CharField(label="Para", max_length=1000)
    subject = forms.CharField(label="Assunto", max_length=200)
    body = forms.CharField(label="Mensagem", widget=forms.Textarea(attrs={"rows": 8}))
    competence = MonthField(label="Competência", required=False)

    def __init__(self, *args: Any, companies: QuerySet[ClientCompany], **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = companies.filter(active=True).order_by("name")  # type: ignore[attr-defined]
        self.files_data: list[tuple[str, bytes]] = []

    def clean_recipients(self) -> list[str]:
        return parse_recipients(self.cleaned_data["recipients"])

    def read_files(self, uploads: list[Any]) -> None:
        total = 0
        collected: list[tuple[str, bytes]] = []
        for upload in uploads:
            total += upload.size
            if total > MAX_ATTACHMENT_BYTES:
                self.add_error(None, "Os anexos passam de 30 MB.")
                return
            collected.append((upload.name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1], upload.read()))
        self.files_data = collected


class AccountForm(forms.ModelForm):  # type: ignore[type-arg]
    smtp_password = forms.CharField(
        label="Senha", required=False, widget=forms.PasswordInput(render_value=False)
    )
    graph_client_secret = forms.CharField(
        label="Segredo", required=False, widget=forms.PasswordInput(render_value=False)
    )

    class Meta:
        model = DeliveryAccount
        fields = (
            "provider",
            "from_name",
            "from_address",
            "smtp_host",
            "smtp_port",
            "smtp_security",
            "smtp_username",
            "graph_tenant_id",
            "graph_client_id",
            "active",
        )
        labels = {
            "provider": "Provedor",
            "from_name": "Nome",
            "from_address": "Remetente",
            "smtp_host": "Servidor",
            "smtp_port": "Porta",
            "smtp_security": "Segurança",
            "smtp_username": "Usuário",
            "graph_tenant_id": "Diretório",
            "graph_client_id": "Aplicativo",
            "active": "Ativa",
        }

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.has_password = bool(self.instance.pk and self.instance.smtp_password)
        self.has_secret = bool(self.instance.pk and self.instance.graph_client_secret)

    def clean(self) -> dict[str, Any]:
        data = super().clean() or {}
        # Campo em branco mantém o segredo já guardado: ele nunca volta à tela. Mudou o
        # destino da credencial (servidor, porta, login, diretório ou aplicativo)? Quem
        # edita redigita o segredo, senão a senha guardada seguiria para outro servidor.
        smtp_moved = bool(
            {"smtp_host", "smtp_port", "smtp_security", "smtp_username", "from_address", "provider"}
            & set(self.changed_data)
        )
        graph_moved = bool(
            {"graph_tenant_id", "graph_client_id", "from_address", "provider"}
            & set(self.changed_data)
        )
        if not data.get("smtp_password") and self.instance.pk and not smtp_moved:
            data["smtp_password"] = self.instance.smtp_password
        if not data.get("graph_client_secret") and self.instance.pk and not graph_moved:
            data["graph_client_secret"] = self.instance.graph_client_secret
        provider = data.get("provider")
        if provider == DeliveryAccount.Provider.SMTP:
            refusal = smtp_host_error(data.get("smtp_host", ""), data.get("smtp_port") or 0)
            if refusal:
                self.add_error("smtp_host", refusal)
            if not data.get("smtp_password") and data.get("smtp_username"):
                self.add_error("smtp_password", "Informe a senha.")
        elif provider == DeliveryAccount.Provider.GRAPH and not data.get("graph_client_secret"):
            self.add_error("graph_client_secret", "Informe o segredo.")
        return data

    def save(self, commit: bool = True) -> DeliveryAccount:
        account = super().save(commit=False)
        account.smtp_password = self.cleaned_data.get("smtp_password", "")
        account.graph_client_secret = self.cleaned_data.get("graph_client_secret", "")
        if commit:
            account.save()
        return account  # type: ignore[no-any-return]
