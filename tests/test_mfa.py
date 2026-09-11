from __future__ import annotations

import pytest
from django.core.cache import cache
from django.test import Client
from django.urls import reverse

from apps.accounts import mfa, totp
from apps.accounts.models import RecoveryCode, TotpDevice, User
from apps.hub.models import OfficeProfile
from apps.organizations.models import Membership, Organization
from apps.platform.models import PlatformAccess

pytestmark = pytest.mark.django_db

PASSWORD = "safe-password-123456"


@pytest.fixture(autouse=True)
def _clear_rate_limit() -> None:
    cache.clear()


def _operator() -> User:
    user = User.objects.create_user(email="operator@example.test", password=PASSWORD)
    PlatformAccess.objects.create(user=user, role=PlatformAccess.Role.SUPPORT)
    return user


def _enrol(user: User) -> TotpDevice:
    device = mfa.start_enrollment(user)
    mfa.confirm_enrollment(device, totp.code_for(device.secret, totp.counter_at()))
    device.refresh_from_db()
    return device


def test_a_platform_operator_cannot_reach_the_console_on_a_password_alone() -> None:
    """The console crosses every tenant, so mfa_required is enforced, not merely stored."""

    operator = _operator()
    client = Client()
    client.force_login(operator)

    response = client.get(reverse("platform:dashboard"))

    assert response.status_code == 302
    assert reverse("accounts:mfa-setup") in response.headers["Location"]


def test_an_enrolled_operator_is_sent_to_the_code_prompt() -> None:
    operator = _operator()
    _enrol(operator)
    client = Client()
    client.force_login(operator)

    response = client.get(reverse("platform:dashboard"))

    assert response.status_code == 302
    assert reverse("accounts:mfa-verify") in response.headers["Location"]


def test_a_valid_code_opens_the_session() -> None:
    operator = _operator()
    device = _enrol(operator)
    client = Client()
    client.force_login(operator)

    posted = client.post(
        reverse("accounts:mfa-verify"),
        {"code": totp.code_for(device.secret, totp.counter_at() + 1)},
    )

    assert posted.status_code == 302
    assert client.get(reverse("platform:dashboard")).status_code == 200


def test_a_code_cannot_be_replayed_within_its_own_window() -> None:
    operator = _operator()
    device = _enrol(operator)
    code = totp.code_for(device.secret, totp.counter_at() + 1)
    client = Client()
    client.force_login(operator)
    client.post(reverse("accounts:mfa-verify"), {"code": code})

    replay = Client()
    replay.force_login(operator)
    response = replay.post(reverse("accounts:mfa-verify"), {"code": code})

    assert response.status_code == 200
    assert not mfa.session_is_verified(replay.request().wsgi_request)


def test_a_recovery_code_works_once() -> None:
    operator = _operator()
    device = mfa.start_enrollment(operator)
    codes = mfa.confirm_enrollment(device, totp.code_for(device.secret, totp.counter_at()))
    assert codes is not None

    assert mfa.check_code(operator, codes[0])
    assert not mfa.check_code(operator, codes[0])
    assert RecoveryCode.objects.filter(user=operator, used_at__isnull=False).count() == 1


def test_an_office_can_require_a_second_factor_from_its_own_members() -> None:
    member = User.objects.create_user(email="member@example.test", password=PASSWORD)
    office = Organization.objects.create(name="Escritório", slug="escritorio")
    Membership.objects.create(user=member, organization=office, role=Membership.Role.OWNER)
    profile = OfficeProfile.objects.create(organization=office)
    client = Client()
    client.force_login(member)

    assert client.get(reverse("hub:dashboard")).status_code == 200

    profile.require_mfa = True
    profile.save(update_fields=["require_mfa"])

    assert client.get(reverse("hub:dashboard")).status_code == 302


def test_signing_out_stays_reachable_without_a_second_factor() -> None:
    operator = _operator()
    client = Client()
    client.force_login(operator)

    response = client.post(reverse("hub:logout"))

    assert response.status_code == 302
    assert reverse("accounts:mfa-setup") not in response.headers["Location"]


def test_guessing_the_code_runs_out_of_attempts() -> None:
    operator = _operator()
    _enrol(operator)
    client = Client()
    client.force_login(operator)

    responses = [client.post(reverse("accounts:mfa-verify"), {"code": "000000"}) for _ in range(12)]

    assert "Muitas tentativas" in responses[-1].content.decode()
