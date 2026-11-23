"""Avisos do radar Simples/MEI (E14): um aviso por empresa e nível, sem repetir, sem cliente."""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

import pytest

from apps.hub import simples_radar_alerts
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    ControlPlaneBinding,
    NfseDocument,
    NfseDocumentSide,
    Notification,
    ProductModule,
)
from apps.hub.tasks_radar import notify_simples_radar_task
from apps.organizations.models import Membership, Organization
from test_nfse_procuracao_views import World

pytestmark = pytest.mark.django_db
TODAY = date(2026, 11, 23)


def revenue(company: ClientCompany, amount: str, issued_on: date = date(2026, 3, 1)) -> None:
    digest = hashlib.sha256(f"{company.pk}{amount}{issued_on}".encode()).hexdigest()
    document = NfseDocument.objects.create(
        organization=company.organization,
        company=company,
        document_hash=digest,
        original_xml="<x/>",
        source_nsu=digest[:20],
    )
    NfseDocumentSide.objects.create(
        organization=company.organization,
        document=document,
        direction="provided",
        issued_on=issued_on,
        service_amount=Decimal(amount),
    )


@pytest.fixture
def world(db: object) -> World:
    built = World()
    built.padaria.tax_regime = "mei"
    built.padaria.save(update_fields=["tax_regime"])
    return built


def test_one_notice_per_administrator_company_and_level_and_it_escalates(world: World) -> None:
    revenue(world.padaria, "64800.00")  # 80%

    assert simples_radar_alerts.notify_simples_radar(today=TODAY) == 1  # só o dono administra
    assert simples_radar_alerts.notify_simples_radar(today=TODAY) == 0  # rodar de novo não repete

    revenue(world.padaria, "8100.00", date(2026, 4, 1))  # 90%
    assert simples_radar_alerts.notify_simples_radar(today=TODAY) == 1

    notices = Notification.objects.filter(organization=world.office)
    assert sorted(notice.title.split(": ")[0] for notice in notices) == [
        "Padaria Central a 80% do teto",
        "Padaria Central a 90% do teto",
    ]
    assert all(notice.recipient == world.owner for notice in notices)


def test_below_eighty_percent_and_other_regimes_stay_silent(world: World) -> None:
    revenue(world.padaria, "40000.00")
    revenue(world.oficina, "999999.00")  # sem regime

    assert simples_radar_alerts.notify_simples_radar(today=TODAY) == 0


def test_an_office_without_the_nfse_module_gets_nothing(world: World) -> None:
    revenue(world.padaria, "70000.00")
    ProductModule.objects.filter(organization=world.office).update(enabled=False)

    assert simples_radar_alerts.notify_simples_radar(today=TODAY) == 0


def test_demo_and_inactive_offices_are_skipped(world: World) -> None:
    revenue(world.padaria, "70000.00")
    Organization.objects.filter(pk=world.office.pk).update(is_demo=True)

    assert simples_radar_alerts.notify_simples_radar(today=TODAY) == 0


def test_the_task_does_nothing_while_the_flag_is_off(world: World, settings: object) -> None:
    revenue(world.padaria, "70000.00")
    settings.SIMPLES_RADAR_ENABLED = False  # type: ignore[attr-defined]
    assert notify_simples_radar_task() == 0
    assert not Notification.objects.exists()

    settings.SIMPLES_RADAR_ENABLED = True  # type: ignore[attr-defined]
    assert notify_simples_radar_task() >= 1
    assert Membership.objects.filter(organization=world.office).exists()


def test_with_a_control_plane_the_admin_without_a_grant_gets_no_notice(world: World) -> None:
    revenue(world.padaria, "70000.00")
    from datetime import timedelta
    from uuid import uuid4

    from django.utils import timezone

    ControlPlaneBinding.objects.create(
        organization=world.office,
        remote_installation_id=uuid4(),
        controller_url="https://crmew.example.test",
        device_private_key="x",
        controller_public_key="x",
        cache_expires_at=timezone.now() + timedelta(hours=1),
    )
    owner = Membership.objects.get(organization=world.office, user=world.owner)
    # Com plano de controle, nem o dono vê empresa sem concessão.
    assert simples_radar_alerts.notify_simples_radar(today=TODAY) == 0

    CompanyAccessGrant.objects.create(
        organization=world.office, membership=owner, company=world.padaria
    )
    assert simples_radar_alerts.notify_simples_radar(today=TODAY) == 1
    notice = Notification.objects.get()
    assert notice.company == world.padaria and notice.recipient == world.owner
