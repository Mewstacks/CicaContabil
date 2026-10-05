from datetime import timedelta

import pytest
from django.test import Client
from django.utils import timezone

from apps.accounts import mfa
from apps.hub.models import OfficeProfile
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantContract

pytestmark = pytest.mark.django_db


@pytest.fixture
def trial(user, organization):
    Membership.objects.create(user=user, organization=organization, role="owner")
    OfficeProfile.objects.create(
        organization=organization, require_mfa=False, trial_started_at=timezone.now()
    )
    return TenantContract.objects.create(
        organization=organization,
        status="trial",
        starts_on=timezone.localdate(),
        trial_ends_on=timezone.localdate() + timedelta(days=14),
    )


def test_current_trial_does_not_require_mfa(user, trial):
    assert not mfa.is_required(user)


def test_paid_office_does_not_force_customer_enrollment(user, trial):
    paid = Organization.objects.create(name="Paid", slug="paid-mfa")
    Membership.objects.create(user=user, organization=paid, role="operator")
    TenantContract.objects.create(organization=paid, status="active")
    assert not mfa.is_required(user)


@pytest.mark.parametrize("status", ["active", "grace", "suspended", "archived"])
def test_commercial_status_does_not_change_customer_mfa_policy(user, trial, status):
    trial.status = status
    trial.save()
    assert not mfa.is_required(user)
    client = Client()
    client.force_login(user)
    response = client.get("/app/")
    assert "/mfa/" not in response.get("Location", "")


def test_expired_trial_does_not_force_customer_enrollment(user, trial):
    OfficeProfile.objects.filter(organization=trial.organization).update(
        trial_started_at=timezone.now() - timedelta(days=14)
    )
    assert not mfa.is_required(user)


def test_missing_trial_expiry_does_not_force_customer_enrollment(user, trial):
    trial.trial_ends_on = None
    trial.save()
    assert not mfa.is_required(user)


def test_missing_trial_profile_does_not_force_customer_enrollment(user, trial):
    OfficeProfile.objects.filter(organization=trial.organization).delete()

    assert not mfa.is_required(user)


def test_inactive_membership_does_not_require_another_offices_mfa(user, trial):
    trial.status = "active"
    trial.save()
    Membership.objects.filter(user=user).update(is_active=False)
    assert not mfa.is_required(user)
