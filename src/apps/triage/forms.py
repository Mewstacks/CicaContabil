from __future__ import annotations

import re

from django import forms

from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage.models import DocumentType


class ManualIntakeForm(forms.Form):
    company = forms.ModelChoiceField(queryset=ClientCompany.objects.none(), label="Empresa")
    document_type = forms.ModelChoiceField(
        queryset=DocumentType.objects.none(), required=False, label="Tipo de documento"
    )
    file = forms.FileField(label="Arquivo")

    def __init__(self, *args: object, organization: Organization, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["company"].queryset = ClientCompany.objects.filter(
            organization=organization, active=True
        ).order_by("name")
        self.fields["document_type"].queryset = DocumentType.objects.filter(
            organization=organization, active=True
        ).order_by("label")
        self.fields["company"].widget.attrs["autocomplete"] = "off"
        self.fields["document_type"].widget.attrs["autocomplete"] = "off"
        self.fields["file"].widget.attrs.update({"accept": ".pdf,.csv,.xml,.ofx,.xlsx"})


class TriageReviewForm(forms.Form):
    decision = forms.ChoiceField(
        choices=(("archive", "Arquivar na biblioteca"), ("reject", "Rejeitar")),
        widget=forms.RadioSelect,
        label="Decisão",
    )
    reason = forms.CharField(
        required=False,
        max_length=500,
        label="Motivo",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    confirm_rejection = forms.BooleanField(
        required=False,
        label="Confirmo que o arquivo deve ser rejeitado",
    )

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        if cleaned.get("decision") == "reject" and not str(cleaned.get("reason") or "").strip():
            self.add_error("reason", "Informe o motivo da rejeição.")
        if cleaned.get("decision") == "reject" and not cleaned.get("confirm_rejection"):
            self.add_error("confirm_rejection", "Confirme a rejeição para registrar a decisão.")
        return cleaned


class IMAPConnectionForm(forms.Form):
    address = forms.EmailField(label="E-mail da caixa", max_length=254)
    host = forms.CharField(label="Servidor IMAP", max_length=253)
    username = forms.CharField(
        label="Usuário IMAP (se diferente do e-mail)", required=False, max_length=254
    )
    password = forms.CharField(
        label="Senha específica de aplicativo ou credencial IMAP",
        max_length=256,
        strip=False,
        widget=forms.PasswordInput(render_value=False),
    )
    folder = forms.CharField(label="Pasta para testar", max_length=160, initial="INBOX")

    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.fields["address"].widget.attrs.update(
            {"autocomplete": "email", "spellcheck": "false", "placeholder": "caixa@escritorio.com…"}
        )
        self.fields["host"].widget.attrs.update(
            {"autocomplete": "off", "spellcheck": "false", "placeholder": "imap.provedor.com…"}
        )
        self.fields["username"].widget.attrs.update({"autocomplete": "off", "spellcheck": "false"})
        self.fields["password"].widget.attrs.update({"autocomplete": "new-password"})
        self.fields["folder"].widget.attrs.update({"autocomplete": "off", "spellcheck": "false"})

    def clean_host(self) -> str:
        host = str(self.cleaned_data["host"]).strip().casefold().rstrip(".")
        if (
            len(host) < 4
            or len(host) > 253
            or not re.fullmatch(r"[a-z0-9.-]+", host)
            or "." not in host
            or not host.rsplit(".", 1)[-1].isalpha()
            or host.endswith((".localhost", ".local", ".internal", ".test"))
            or any(
                not label or len(label) > 63 or label.startswith("-") or label.endswith("-")
                for label in host.split(".")
            )
        ):
            raise forms.ValidationError("Use o endereço público de IMAP fornecido pelo provedor.")
        return host

    def clean_folder(self) -> str:
        folder = str(self.cleaned_data["folder"]).strip()
        if not re.fullmatch(r"[A-Za-z0-9 ./_-]+", folder):
            raise forms.ValidationError("Use o nome simples da pasta IMAP, por exemplo INBOX.")
        return folder

    def clean_username(self) -> str:
        username = str(self.cleaned_data["username"]).strip()
        if any(char in username for char in "\r\n\x00"):
            raise forms.ValidationError("Usuário IMAP inválido.")
        return username

    def clean_password(self) -> str:
        password = str(self.cleaned_data["password"])
        if any(char in password for char in "\r\n\x00"):
            raise forms.ValidationError("Credencial IMAP inválida.")
        return password
