from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Membership, Organization
from apps.platform.models import Invitation, PlatformAccess, SupportSession


@pytest.mark.django_db
def test_superuser_gets_platform_console_without_tenant_membership() -> None:
    user = User.objects.create_superuser(
        email="platform@example.test", password="safe-password-123"
    )
    client = Client()
    client.force_login(user)

    response = client.get(reverse("platform:dashboard"))

    assert response.status_code == 200
    assert not Membership.objects.filter(user=user).exists()


@pytest.mark.django_db
def test_office_user_cannot_open_platform_console() -> None:
    user = User.objects.create_user(email="office@example.test", password="safe-password-123")
    office = Organization.objects.create(name="Escritório", slug="escritorio")
    Membership.objects.create(user=user, organization=office, role=Membership.Role.OWNER)
    client = Client()
    client.force_login(user)

    assert client.get(reverse("platform:dashboard")).status_code == 403


@pytest.mark.django_db
def test_support_session_grants_temporary_operational_access_without_membership() -> None:
    support = User.objects.create_user(email="support@example.test", password="safe-password-123")
    PlatformAccess.objects.create(user=support, role=PlatformAccess.Role.SUPPORT)
    office = Organization.objects.create(name="Escritório", slug="escritorio")
    client = Client()
    client.force_login(support)

    response = client.post(
        reverse("platform:start-support", args=[office.id]),
        {"justification": "Investigar fila travada"},
    )

    assert response.status_code == 302
    assert SupportSession.objects.filter(organization=office, support_user=support).exists()
    assert not Membership.objects.filter(user=support, organization=office).exists()


@pytest.mark.django_db
def test_internal_activation_creates_office_membership_once() -> None:
    office = Organization.objects.create(name="Escritório", slug="escritorio")
    token, digest = Invitation.issue_token()
    Invitation.objects.create(
        organization=office,
        email="owner@example.test",
        full_name="Owner",
        role=Membership.Role.OWNER,
        token_digest=digest,
        expires_at=timezone.now() + timedelta(days=1),
    )
    client = Client()

    response = client.post(
        reverse("hub:activate", args=[token]),
        {"password": "safe-password-123", "password_confirm": "safe-password-123"},
    )

    assert response.status_code == 302
    assert Membership.objects.filter(
        organization=office, user__email="owner@example.test", role=Membership.Role.OWNER
    ).exists()
