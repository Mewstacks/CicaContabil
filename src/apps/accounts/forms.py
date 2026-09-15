from django import forms
from django.contrib.auth.forms import AuthenticationForm


class IdentifierAuthenticationForm(AuthenticationForm):
    """The underlying `username` field carries an e-mail or unique full name."""

    username = forms.CharField(
        label="E-mail ou nome cadastrado",
        widget=forms.TextInput(
            attrs={
                "autocomplete": "username",
                "autocapitalize": "none",
                "spellcheck": "false",
                "placeholder": "voce@escritorio.com…",
            }
        ),
    )
