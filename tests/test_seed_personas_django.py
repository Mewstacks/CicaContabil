from __future__ import annotations

import hashlib

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import override_settings

from apps.accounts.models import User
from apps.hub.models import CompanyAccessGrant, OfficeProfile
from apps.hub.seeding import MFA_OFFICE_SLUG, OPERATOR_COMPANY_COUNT, RIVAL_SLUG, build_personas
from apps.organizations.models import Membership, Organization
from apps.platform.models import Invitation, PlatformAccess, TenantContract, TenantLifecycle

pytestmark = pytest.mark.django_db


def _seed() -> None:
    call_command("seed_demo", "--password", "seed-only-password-9f2c", verbosity=0)
    call_command("seed_personas", "--password", "seed-only-password-9f2c", verbosity=0)


@override_settings(DEBUG=True)
def test_every_persona_exists_with_its_own_authority() -> None:
    _seed()

    demo = Organization.objects.get(slug="escritorio-demo")
    roles = set(
        Membership.objects.filter(organization=demo).values_list("role", flat=True),
    )
    assert {
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
        Membership.Role.OPERATOR,
        Membership.Role.AUDITOR,
        Membership.Role.BILLING,
    } <= roles

    platform_roles = set(PlatformAccess.objects.values_list("role", flat=True))
    assert platform_roles == {
        PlatformAccess.Role.DEVELOPER,
        PlatformAccess.Role.SUPPORT,
        PlatformAccess.Role.COMMERCIAL,
    }


@override_settings(DEBUG=True)
def test_operator_sees_a_slice_of_the_office_not_all_of_it() -> None:
    _seed()

    demo = Organization.objects.get(slug="escritorio-demo")
    operator = Membership.objects.get(organization=demo, role=Membership.Role.OPERATOR)
    owner = Membership.objects.get(organization=demo, role=Membership.Role.OWNER)

    operator_scope = CompanyAccessGrant.objects.filter(membership=operator).count()
    owner_scope = CompanyAccessGrant.objects.filter(membership=owner).count()

    assert operator_scope == OPERATOR_COMPANY_COUNT
    assert operator_scope < owner_scope


@override_settings(DEBUG=True)
def test_the_second_factor_and_the_second_tenant_are_reachable() -> None:
    _seed()

    mfa_office = Organization.objects.get(slug=MFA_OFFICE_SLUG)
    assert OfficeProfile.objects.get(organization=mfa_office).require_mfa is True

    rival = Organization.objects.get(slug=RIVAL_SLUG)
    assert Membership.objects.filter(organization=rival).exists()
    assert not Membership.objects.filter(
        organization=rival, user__email="demo@hubcontador.local"
    ).exists()


@override_settings(DEBUG=True)
def test_the_commercial_model_and_the_suspended_state_are_no_longer_dead_code() -> None:
    _seed()

    demo = Organization.objects.get(slug="escritorio-demo")
    contract = TenantContract.objects.get(organization=demo)
    assert contract.status == TenantContract.Status.ACTIVE
    assert contract.plan is not None
    assert contract.plan.modules

    rival = Organization.objects.get(slug=RIVAL_SLUG)
    assert TenantLifecycle.objects.get(organization=rival).state == TenantLifecycle.State.SUSPENDED


@override_settings(DEBUG=True)
def test_the_returned_invitation_token_opens_the_stored_invitation() -> None:
    world = build_personas(password="seed-only-password-9f2c")

    assert world.invitation is not None
    digest = hashlib.sha256(world.invitation_token.encode()).hexdigest()
    assert Invitation.objects.get(token_digest=digest).pk == world.invitation.pk


@override_settings(DEBUG=True)
def test_seeding_twice_changes_nothing() -> None:
    _seed()
    users = User.objects.count()
    memberships = Membership.objects.count()

    call_command("seed_personas", "--password", "seed-only-password-9f2c", verbosity=0)

    assert User.objects.count() == users
    assert Membership.objects.count() == memberships


@override_settings(DEBUG=False, SEED_DEMO_ALLOWED=False)
def test_personas_refuse_to_appear_outside_debug() -> None:
    with pytest.raises(CommandError):
        call_command("seed_personas", verbosity=0)
