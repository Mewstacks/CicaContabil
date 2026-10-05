import pytest
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from apps.hub.forms import ActivationForm
from apps.platform.forms import SignupPasswordForm

EIGHT_CHARACTER_PASSWORD = "V7!qZ2#p"
SEVEN_CHARACTER_PASSWORD = "V7!qZ#p"


def test_global_password_policy_accepts_eight_characters():
    validate_password(EIGHT_CHARACTER_PASSWORD)


def test_global_password_policy_rejects_seven_characters():
    with pytest.raises(ValidationError, match="8 caracteres"):
        validate_password(SEVEN_CHARACTER_PASSWORD)


@pytest.mark.parametrize("form_class", [ActivationForm, SignupPasswordForm])
def test_account_creation_forms_accept_eight_characters(form_class):
    data = {"password": EIGHT_CHARACTER_PASSWORD}
    if form_class is ActivationForm:
        data["password_confirm"] = EIGHT_CHARACTER_PASSWORD

    form = form_class(data=data)

    assert form.is_valid(), form.errors
    assert form.fields["password"].min_length == 8
    assert form.fields["password"].widget.attrs["minlength"] == "8"


@pytest.mark.parametrize("form_class", [ActivationForm, SignupPasswordForm])
def test_account_creation_forms_reject_seven_characters(form_class):
    data = {"password": SEVEN_CHARACTER_PASSWORD}
    if form_class is ActivationForm:
        data["password_confirm"] = SEVEN_CHARACTER_PASSWORD

    form = form_class(data=data)

    assert not form.is_valid()
    assert "8 caracteres" in str(form.errors["password"])
