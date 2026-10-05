from django import forms
from django.contrib.auth.forms import AuthenticationForm


class IdentifierAuthenticationForm(AuthenticationForm):
    """The underlying `username` field carries an e-mail or unique full name."""

    error_messages = {
        "invalid_login": (
            "Não foi possível entrar com os dados informados. "
            "Confira o e-mail ou nome cadastrado e a senha."
        ),
        "inactive": "Esta conta está inativa. Peça ajuda ao administrador do escritório.",
    }

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
