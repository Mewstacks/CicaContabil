from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db

PASSWORD = "safe-password-123456"
EVIL = "https://phishing.example/entrar"


@pytest.fixture
def member() -> User:
    user = User.objects.create_user(email="member@example.test", password=PASSWORD)
    office = Organization.objects.create(name="Escritório", slug="escritorio")
    Membership.objects.create(user=user, organization=office, role=Membership.Role.OWNER)
    return user


def test_login_refuses_to_redirect_to_another_host(member: User) -> None:
    response = Client().post(
        reverse("hub:login"),
        {"username": member.email, "password": PASSWORD, "next": EVIL},
    )

    assert response.status_code == 302
    assert response.headers["Location"] != EVIL


def test_login_still_honours_a_local_next(member: User) -> None:
    response = Client().post(
        reverse("hub:login"),
        {"username": member.email, "password": PASSWORD, "next": "/app/empresas/"},
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "/app/empresas/"


def test_switching_office_refuses_to_redirect_to_another_host(member: User) -> None:
    membership = Membership.objects.get(user=member)
    client = Client()
    client.force_login(member)

    response = client.post(
        reverse("hub:switch-office"),
        {"organization_id": str(membership.organization_id), "next": EVIL},
    )

    assert response.status_code == 302
    assert response.headers["Location"] != EVIL
