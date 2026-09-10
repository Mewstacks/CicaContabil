from django import forms

from apps.organizations.models import Membership
from apps.platform.models import Lead, TenantContract


class LeadForm(forms.ModelForm):  # type: ignore[type-arg]
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


class TenantContractForm(forms.ModelForm):  # type: ignore[type-arg]
    class Meta:
        model = TenantContract
        fields = ("plan", "status", "reference", "starts_on", "ends_on", "grace_ends_on", "notes")
        widgets = {
            "starts_on": forms.DateInput(attrs={"type": "date"}),
            "ends_on": forms.DateInput(attrs={"type": "date"}),
            "grace_ends_on": forms.DateInput(attrs={"type": "date"}),
        }


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
