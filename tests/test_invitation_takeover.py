from __future__ import annotations

from datetime import timedelta

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Membership, Organization
from apps.platform.models import Invitation, Plan, TenantContract, TenantLifecycle

pytestmark = pytest.mark.django_db

VICTIM_PASSWORD = "victim-password-that-must-survive-1"
ATTACKER_PASSWORD = "attacker-chosen-password-9182"


def _invite(organization: Organization, email: str) -> str:
    token, digest = Invitation.issue_token()
    Invitation.objects.create(
        organization=organization,
        email=email,
        full_name="Alvo",
        role=Membership.Role.OWNER,
        token_digest=digest,
        expires_at=timezone.now() + timedelta(days=1),
    )
    return token


def test_activation_never_resets_the_password_of_an_existing_account() -> None:
    """An invitation to an e-mail that already has an account must not set its password.

    Anyone able to issue an invitation could otherwise take over any account -
    including an owner of another tenant - by typing its e-mail address.
    """

    victim = User.objects.create_user(email="victim@example.test", password=VICTIM_PASSWORD)
    attacker_office = Organization.objects.create(name="Outro", slug="outro-escritorio")
    token = _invite(attacker_office, victim.email)

    response = Client().post(
        reverse("hub:activate", args=[token]),
        {"password": ATTACKER_PASSWORD, "password_confirm": ATTACKER_PASSWORD},
    )

    victim.refresh_from_db()
    assert response.status_code == 200
    assert victim.check_password(VICTIM_PASSWORD)
    assert not victim.check_password(ATTACKER_PASSWORD)
    assert not Membership.objects.filter(user=victim, organization=attacker_office).exists()


def test_a_signed_out_visitor_is_asked_to_sign_in_instead_of_setting_a_password() -> None:
    User.objects.create_user(email="known@example.test", password=VICTIM_PASSWORD)
    office = Organization.objects.create(name="Escritório", slug="escritorio")
    token = _invite(office, "known@example.test")

    response = Client().get(reverse("hub:activate", args=[token]))

    assert response.status_code == 200
    assert b"Entre para aceitar" in response.content


def test_another_signed_in_user_cannot_accept_someone_elses_invitation() -> None:
    User.objects.create_user(email="invited@example.test", password=VICTIM_PASSWORD)
    intruder = User.objects.create_user(email="intruder@example.test", password=ATTACKER_PASSWORD)
    office = Organization.objects.create(name="Escritório", slug="escritorio")
    token = _invite(office, "invited@example.test")
    client = Client()
    client.force_login(intruder)

    response = client.post(reverse("hub:activate", args=[token]))

    assert response.status_code == 403
    assert not Membership.objects.filter(user=intruder, organization=office).exists()


def test_the_invited_user_accepts_after_signing_in() -> None:
    invited = User.objects.create_user(email="invited@example.test", password=VICTIM_PASSWORD)
    office = Organization.objects.create(name="Escritório", slug="escritorio")
    token = _invite(office, invited.email)
    client = Client()
    client.force_login(invited)

    response = client.post(reverse("hub:activate", args=[token]))

    invited.refresh_from_db()
    assert response.status_code == 302
    assert invited.check_password(VICTIM_PASSWORD)
    assert Membership.objects.filter(
        user=invited, organization=office, role=Membership.Role.OWNER, is_active=True
    ).exists()


def test_a_brand_new_invited_account_still_sets_its_password() -> None:
    office = Organization.objects.create(name="Escritório", slug="escritorio")
    token = _invite(office, "newcomer@example.test")

    response = Client().post(
        reverse("hub:activate", args=[token]),
        {"password": ATTACKER_PASSWORD, "password_confirm": ATTACKER_PASSWORD},
    )

    assert response.status_code == 302
    created = User.objects.get(email="newcomer@example.test")
    assert created.check_password(ATTACKER_PASSWORD)
    assert Membership.objects.filter(user=created, organization=office).exists()


def test_platform_invitation_does_not_activate_an_office_without_a_contract() -> None:
    office = Organization.objects.create(name="Escritório", slug="escritorio")
    TenantLifecycle.objects.create(
        organization=office, state=TenantLifecycle.State.ACTIVATION_PENDING
    )
    token = _invite(office, "newcomer@example.test")

    response = Client().post(
        reverse("hub:activate", args=[token]),
        {"password": ATTACKER_PASSWORD, "password_confirm": ATTACKER_PASSWORD},
    )

    assert response.status_code == 302
    assert TenantLifecycle.objects.get(organization=office).state == (
        TenantLifecycle.State.ACTIVATION_PENDING
    )
    pending = Client()
    pending.force_login(User.objects.get(email="newcomer@example.test"))
    response = pending.get(reverse("hub:dashboard"))
    assert response.status_code == 403
    assert "Seu acesso ainda está sendo preparado." in response.content.decode()


def test_platform_invitation_can_activate_an_office_with_a_trial_or_active_contract() -> None:
    office = Organization.objects.create(name="Escritório", slug="escritorio")
    TenantLifecycle.objects.create(
        organization=office, state=TenantLifecycle.State.ACTIVATION_PENDING
    )
    plan = Plan.objects.create(code="invitation-trial", name="Teste")
    TenantContract.objects.create(
        organization=office, plan=plan, status=TenantContract.Status.TRIAL
    )
    token = _invite(office, "newcomer@example.test")

    response = Client().post(
        reverse("hub:activate", args=[token]),
        {"password": ATTACKER_PASSWORD, "password_confirm": ATTACKER_PASSWORD},
    )

    assert response.status_code == 302
    assert TenantLifecycle.objects.get(organization=office).state == TenantLifecycle.State.ACTIVE


def test_archived_office_cannot_be_opened_by_a_member() -> None:
    office = Organization.objects.create(name="Arquivado", slug="arquivado")
    user = User.objects.create_user(email="member@example.test", password=VICTIM_PASSWORD)
    Membership.objects.create(organization=office, user=user, role=Membership.Role.OWNER)
    TenantLifecycle.objects.create(organization=office, state=TenantLifecycle.State.ARCHIVED)
    client = Client()
    client.force_login(user)

    response = client.get(reverse("hub:dashboard"))

    assert response.status_code == 403
    assert "Este escritório foi encerrado" in response.content.decode()
