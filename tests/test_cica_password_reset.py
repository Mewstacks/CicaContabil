import pytest
from django.core import mail
from django.test import Client
from django.urls import reverse

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
