"""Platform admin in a support session sees the whole office, as an owner would."""

from __future__ import annotations

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import OperationalActivity
from apps.organizations.models import Membership, Organization
from apps.platform.models import PlatformAccess, SupportSession
from closing_support import make_activity, make_company, make_office
from conftest import complete_mfa

JUSTIFICATION = "Suporte do dono da plataforma"


def _platform_client(role: str, email: str) -> tuple[Client, User]:
    user = User.objects.create_user(email, "senha-longa-de-teste-2026")
    PlatformAccess.objects.create(user=user, role=role)
    client = Client()
    client.force_login(user)
    complete_mfa(client)
    return client, user


def _office_with_activity() -> tuple[Organization, OperationalActivity]:
    office = make_office("suporte-total")
    company = make_company(office)
    return office, make_activity(office, company)


def _open(client: Client, office: Organization) -> None:
    response = client.post(
        reverse("platform:start-support", args=[office.id]), {"justification": JUSTIFICATION}
    )
    assert response.status_code == 302


@pytest.mark.django_db
def test_admin_support_session_sees_full_office_without_membership() -> None:
    office, activity = _office_with_activity()
    client, admin = _platform_client(PlatformAccess.Role.ADMIN, "admin@example.test")
    _open(client, office)

    urls = [
        reverse("hub:activities"),
        reverse("hub:activity-detail", args=[activity.id]),
        reverse("hub:companies"),
        reverse("hub:certificates"),
        reverse("hub:settings"),
    ]
    for url in urls:
        assert client.get(url).status_code == 200, url
    assert not Membership.objects.filter(user=admin).exists()


@pytest.mark.django_db
def test_admin_support_session_lasts_eight_hours_and_is_audited() -> None:
    office, _ = _office_with_activity()
    client, admin = _platform_client(PlatformAccess.Role.ADMIN, "admin2@example.test")
    _open(client, office)

    session = SupportSession.objects.get(support_user=admin)
    remaining = session.expires_at - timezone.now()
    assert 7 * 3600 < remaining.total_seconds() <= 8 * 3600
    assert session.access_mode == SupportSession.AccessMode.FULL
    assert AuditEvent.objects.filter(action="platform.support.opened", actor=admin).exists()


@pytest.mark.django_db
def test_admin_support_session_does_not_leak_other_office() -> None:
    office, _ = _office_with_activity()
    other = make_office("outro-escritorio")
    foreign = make_activity(other, make_company(other, "Outra", "98.765.432/0001-98"))
    client, _admin = _platform_client(PlatformAccess.Role.ADMIN, "admin3@example.test")
    _open(client, office)

    assert client.get(reverse("hub:activity-detail", args=[foreign.id])).status_code == 404


@pytest.mark.django_db
def test_support_role_keeps_limited_behaviour() -> None:
    office, _ = _office_with_activity()
    client, _user = _platform_client(PlatformAccess.Role.SUPPORT, "sup@example.test")
    _open(client, office)

    assert client.get(reverse("hub:activities")).status_code == 404
    session = SupportSession.objects.get(organization=office)
    assert (session.expires_at - timezone.now()).total_seconds() <= 30 * 60


@pytest.mark.django_db
def test_user_without_membership_is_still_refused() -> None:
    office, activity = _office_with_activity()
    user = User.objects.create_user("plain@example.test", "senha-longa-de-teste-2026")
    client = Client()
    client.force_login(user)
    complete_mfa(client)

    assert client.get(reverse("hub:activities")).status_code in {403, 404}
    assert client.get(reverse("hub:activity-detail", args=[activity.id])).status_code in {
        403,
        404,
    }
    assert not SupportSession.objects.filter(organization=office).exists()


@pytest.mark.django_db
def test_admin_support_session_can_operate_and_mutation_is_audited() -> None:
    office, activity = _office_with_activity()
    client, admin = _platform_client(PlatformAccess.Role.ADMIN, "admin4@example.test")
    _open(client, office)

    response = client.post(
        reverse("hub:activity-block", args=[activity.id]), {"reason": "Falta o extrato do mês"}
    )

    assert response.status_code == 302
    activity.refresh_from_db()
    assert activity.work_status == OperationalActivity.WorkStatus.BLOCKED
    assert AuditEvent.objects.filter(action="hub.activity.blocked", actor=admin).exists()
    assert not Membership.objects.filter(user=admin).exists()


@pytest.mark.django_db
def test_expired_admin_session_loses_access() -> None:
    office, _ = _office_with_activity()
    client, admin = _platform_client(PlatformAccess.Role.ADMIN, "admin5@example.test")
    _open(client, office)
    SupportSession.objects.filter(support_user=admin).update(
        expires_at=timezone.now() - timezone.timedelta(minutes=1)
    )

    assert client.get(reverse("hub:activities")).status_code == 403
