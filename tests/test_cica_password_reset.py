import pytest
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import Client
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from apps.accounts.models import User

pytestmark = pytest.mark.django_db


def test_password_reset_is_neutral_and_sends_a_link_for_active_account():
    User.objects.create_user(email="acesso@example.com", password="old-secret-password")
    client = Client()

    known = client.post("/recuperar-senha/", {"email": "acesso@example.com"})
    unknown = client.post("/recuperar-senha/", {"email": "ausente@example.com"})

    assert known.status_code == 302
    assert unknown.status_code == 302
    assert known.url == unknown.url == "/recuperar-senha/enviado/"
    assert len(mail.outbox) == 1
    assert "recuperar-senha/" in mail.outbox[0].body


def test_password_reset_confirmation_does_not_expose_the_token_in_a_referer_header():
    response = Client().get(reverse("hub:password-reset-confirm", args=["invalid", "invalid"]))

    assert response.status_code == 200
    assert response["Referrer-Policy"] == "no-referrer"


def test_sanitized_reset_page_keeps_same_origin_csrf_and_accepts_new_password():
    user = User.objects.create_user("reset@example.test", "previous-password-123")
    token = default_token_generator.make_token(user)
    client = Client(enforce_csrf_checks=True)
    response = client.get(
        reverse(
            "hub:password-reset-confirm", args=[urlsafe_base64_encode(force_bytes(user.pk)), token]
        )
    )
    assert response.status_code == 302
    assert token not in response.url
    assert response["Referrer-Policy"] == "no-referrer"
    sanitized_url = response.url
    page = client.get(sanitized_url)
    assert page["Referrer-Policy"] == "same-origin"
    result = client.post(
        sanitized_url,
        {
            "new_password1": "new-synthetic-password-123",
            "new_password2": "new-synthetic-password-123",
        },
        HTTP_X_CSRFTOKEN=client.cookies["csrftoken"].value,
        HTTP_ORIGIN="http://testserver",
    )
    assert result.status_code == 302
    assert result.url == reverse("hub:password-reset-complete")
    user.refresh_from_db()
    assert user.check_password("new-synthetic-password-123")
