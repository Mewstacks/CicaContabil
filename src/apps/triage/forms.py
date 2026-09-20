from __future__ import annotations

import re
import uuid
from datetime import date
from pathlib import PureWindowsPath

from django import forms

from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.triage.models import DestinationProfile, DocumentType, Mailbox


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


class OfficeOAuthAppForm(forms.Form):
    client_id = forms.CharField(label="ID do aplicativo (Client ID)", max_length=255)
    client_secret = forms.CharField(
        label="Valor do segredo (Client Secret)",
        max_length=512,
        strip=False,
        widget=forms.PasswordInput(render_value=False, attrs={"autocomplete": "new-password"}),
    )
    tenant_id = forms.CharField(
        label="ID do diretório Microsoft (Tenant ID)", max_length=64, required=False
    )

    def __init__(self, *args: object, provider: str, **kwargs: object) -> None:
        kwargs.setdefault("prefix", provider)
        super().__init__(*args, **kwargs)
        self.provider = provider
        self.fields["client_id"].widget.attrs.update({"autocomplete": "off", "spellcheck": "false"})
        self.fields["tenant_id"].widget.attrs.update({"autocomplete": "off", "spellcheck": "false"})
        if provider == "ms365_graph":
            self.fields["tenant_id"].required = True
        elif provider == "gmail_api":
            del self.fields["tenant_id"]
        else:
            raise ValueError("Provedor OAuth invalido.")

    def clean_client_id(self) -> str:
        value = str(self.cleaned_data["client_id"]).strip()
        if not value or any(c.isspace() for c in value):
            raise forms.ValidationError("Copie o ID do aplicativo sem espaços.")
        return value

    def clean_client_secret(self) -> str:
        value = str(self.cleaned_data["client_secret"])
        if not value.strip() or any(c in value for c in "\r\n\x00"):
            raise forms.ValidationError("Copie o valor do segredo, não o ID do segredo.")
        return value

    def clean_tenant_id(self) -> str:
        value = str(self.cleaned_data["tenant_id"]).strip()
        try:
            return str(uuid.UUID(value))
        except ValueError as exc:
            raise forms.ValidationError("Copie o ID do diretório em formato UUID.") from exc


class MailboxOperationForm(forms.Form):
    folder = forms.CharField(label="Pasta ou etiqueta", max_length=160)
    since = forms.DateField(
        label="Ler mensagens recebidas a partir de",
        widget=forms.DateInput(attrs={"type": "date", "autocomplete": "off"}),
    )
    sender_filter = forms.CharField(
        label="Remetente contém (opcional)", required=False, max_length=255
    )
    subject_filter = forms.CharField(
        label="Assunto contém (opcional)", required=False, max_length=255
    )
    active = forms.BooleanField(
        label="Ativar leitura automática desta caixa", required=False
    )

    def __init__(self, *args: object, mailbox: Mailbox, **kwargs: object) -> None:
        kwargs.setdefault("prefix", f"mailbox-{mailbox.id}")
        super().__init__(*args, **kwargs)
        self.mailbox = mailbox
        if not self.is_bound:
            self.initial.update(
                {
                    "folder": mailbox.folder,
                    "since": mailbox.since.date() if mailbox.since else date.today(),
                    "sender_filter": mailbox.sender_filter,
                    "subject_filter": mailbox.subject_filter,
                    "active": mailbox.active,
                }
            )
        for name in ("folder", "sender_filter", "subject_filter"):
            self.fields[name].widget.attrs.update(
                {"autocomplete": "off", "spellcheck": "false"}
            )

    def clean_folder(self) -> str:
        value = str(self.cleaned_data["folder"]).strip()
        if not value or any(char in value for char in "\r\n\x00"):
            raise forms.ValidationError("Informe uma pasta ou etiqueta válida.")
        return value

    def clean_since(self) -> date:
        value = self.cleaned_data["since"]
        if value > date.today():
            raise forms.ValidationError("A data inicial não pode estar no futuro.")
        return value

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        if cleaned.get("active") and (
            self.mailbox.status != Mailbox.Status.ACTIVE or not self.mailbox.credential
        ):
            self.add_error("active", "Reconecte a caixa antes de ativar a leitura.")
        return cleaned


class DestinationProfileForm(forms.Form):
    mode = forms.ChoiceField(
        label="Destino dos arquivos aprovados", choices=DestinationProfile.Mode.choices
    )
    windows_root = forms.CharField(
        label="Pasta raiz no Windows",
        required=False,
        max_length=500,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "spellcheck": "false",
                "placeholder": r"Ex.: D:\Clientes\Documentos",
            }
        ),
    )
    folder_template = forms.CharField(
        label="Formato das pastas Windows",
        required=False,
        initial="{company_name} [Domínio {dominio_code}]",
        max_length=200,
        help_text=(
            "Use {company_name}, {dominio_code}, {document_type} e {period}. "
            "Separe subpastas com \\."
        ),
        widget=forms.TextInput(
            attrs={
                "autocomplete": "off",
                "spellcheck": "false",
                "placeholder": r"{company_name} [{dominio_code}]\{document_type}\{period}",
            }
        ),
    )

    def __init__(
        self, *args: object, profile: DestinationProfile | None, **kwargs: object
    ) -> None:
        super().__init__(*args, **kwargs)
        if profile is not None and not self.is_bound:
            self.initial.update(
                {
                    "mode": profile.mode,
                    "windows_root": profile.windows_root,
                    "folder_template": profile.folder_template,
                }
            )

    def clean_windows_root(self) -> str:
        value = str(self.cleaned_data.get("windows_root", "")).strip()
        if any(char in value for char in "\r\n\x00"):
            raise forms.ValidationError("A pasta raiz contém caracteres inválidos.")
        return value

    def clean(self) -> dict[str, object]:
        cleaned = super().clean()
        root = str(cleaned.get("windows_root") or "")
        template = str(
            cleaned.get("folder_template") or "{company_name} [Domínio {dominio_code}]"
        ).strip()
        if cleaned.get("mode") == DestinationProfile.Mode.WINDOWS:
            path = PureWindowsPath(root)
            if (
                not root
                or not path.is_absolute()
                or root.startswith("\\\\")
                or ".." in path.parts
            ):
                self.add_error(
                    "windows_root",
                    (
                        r"Informe uma pasta local absoluta, por exemplo D:\Clientes\Documentos. "
                        "Unidade de rede será liberada após homologação."
                    ),
                )
        else:
            cleaned["windows_root"] = ""
        cleaned["folder_template"] = template
        if cleaned.get("mode") == DestinationProfile.Mode.WINDOWS:
            allowed = {"company_name", "dominio_code", "document_type", "period"}
            fields = set(re.findall(r"{([^{}]+)}", template))
            literal = re.sub(r"{[^{}]+}", "", template)
            if (
                not template
                or fields - allowed
                or "{" in literal
                or any(char in literal for char in ':*?"<>|')
            ):
                self.add_error(
                    "folder_template",
                    "Use somente as variáveis informadas, sem chaves soltas.",
                )
            elif (
                not ({"company_name", "dominio_code"} & fields)
                or ".." in PureWindowsPath(template).parts
                or PureWindowsPath(template).is_absolute()
            ):
                self.add_error(
                    "folder_template",
                    "Inclua empresa ou código Domínio e use apenas subpastas relativas.",
                )
        return cleaned
