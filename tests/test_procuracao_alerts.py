"""Alarmes da coleta por procuração (E5): e-CNPJ a vencer, procuração perdida e fila parada."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import pytest
from django.utils import timezone

from apps.hub import procuracao_alerts
from apps.hub.models import (
    NfseSync,
    Notification,
    OfficeCertificate,
    OfficeProfile,
)
from apps.hub.tasks_procuracao import (
    check_procuracao_lane,
    notify_lost_procuracoes,
    notify_office_certificates,
)
from apps.organizations.models import Membership, Organization
from test_nfse_procuracao import OFFICE_CNPJ
from test_nfse_procuracao_views import World, login

pytestmark = pytest.mark.django_db


def certificate(world: World, *, days: int, **extra: Any) -> OfficeCertificate:
    now = timezone.now()
    fields: dict[str, Any] = {
        "organization": world.office,
        "label": "e-CNPJ",
        "cnpj": OFFICE_CNPJ,
        "valid_from": now - timedelta(days=300),
        "valid_until": now + timedelta(days=days, hours=2),
        "fingerprint_sha256": f"{days:064d}",
    }
    fields.update(extra)
    return OfficeCertificate.objects.create(**fields)


def notices(kind: str = Notification.Kind.CERTIFICATE_EXPIRING) -> list[Notification]:
    return list(Notification.objects.filter(kind=kind))


# ---------------------------------------------------------------- e-CNPJ a vencer


@pytest.mark.parametrize(
    ("days", "threshold"),
    [(30, 30), (20, 30), (15, 15), (10, 15), (7, 7), (4, 7), (3, 3), (1, 1), (0, 1)],
)
def test_the_notice_escalates_through_the_thresholds(days: int, threshold: int) -> None:
    world = World()
    admin = world.member(Membership.Role.ADMIN, "admin@example.test")
    cert = certificate(world, days=days)

    created = procuracao_alerts.notify_office_certificate_expiring()

    assert created == 2  # dono e administrador; operador e auditor não recebem
    assert {notice.dedupe_key for notice in notices()} == {f"office-cert:{cert.pk}:{threshold}"}
    assert {notice.recipient for notice in notices()} == {world.owner, admin}


def test_a_certificate_far_from_expiry_or_already_revoked_stays_quiet() -> None:
    world = World()
    certificate(world, days=45)
    certificate(world, days=5, revoked_at=timezone.now(), fingerprint_sha256="r" * 64)

    assert procuracao_alerts.notify_office_certificate_expiring() == 0


def test_the_same_threshold_is_never_repeated_but_the_next_one_is_new() -> None:
    world = World()
    cert = certificate(world, days=12)
    assert procuracao_alerts.notify_office_certificate_expiring() == 1
    assert procuracao_alerts.notify_office_certificate_expiring() == 0

    OfficeCertificate.objects.filter(pk=cert.pk).update(
        valid_until=timezone.now() + timedelta(days=6, hours=2)
    )

    assert procuracao_alerts.notify_office_certificate_expiring() == 1
    assert {n.dedupe_key.rsplit(":", 1)[1] for n in notices()} == {"15", "7"}


def test_only_procuracao_offices_are_watched() -> None:
    world = World(mode=OfficeProfile.NfseCollectionMode.CERTIFICATE)
    certificate(world, days=5)

    assert procuracao_alerts.notify_office_certificate_expiring() == 0


def test_demo_and_inactive_offices_are_skipped() -> None:
    world = World()
    certificate(world, days=5)
    Organization.objects.filter(pk=world.office.pk).update(is_demo=True)
    assert procuracao_alerts.notify_office_certificate_expiring() == 0
    Organization.objects.filter(pk=world.office.pk).update(is_demo=False, is_active=False)
    assert procuracao_alerts.notify_office_certificate_expiring() == 0


def test_the_scheduled_task_runs_the_same_rule() -> None:
    world = World()
    certificate(world, days=2)

    assert notify_office_certificates() == 1


# ---------------------------------------------------------------- procuração perdida


def synced(world: World) -> NfseSync:
    login(world.owner, world.office).get("/app/nfse/procuracoes/")  # semeia as linhas
    return NfseSync.objects.get(company=world.padaria)


def lose(
    sync: NfseSync, *, had_ok: bool = True, checked_ago: timedelta = timedelta(hours=1)
) -> None:
    now = timezone.now()
    NfseSync.objects.filter(pk=sync.pk).update(
        procuracao_status=NfseSync.ProcuracaoStatus.MISSING,
        procuracao_ok_at=now - timedelta(days=10) if had_ok else None,
        procuracao_checked_at=now - checked_ago,
    )


def test_a_company_that_had_a_procuracao_and_lost_it_alerts_the_administrators_once() -> None:
    world = World()
    sync = synced(world)
    lose(sync)

    assert procuracao_alerts.notify_lost_procuracoes() == 1
    assert procuracao_alerts.notify_lost_procuracoes() == 0
    [notice] = notices(Notification.Kind.SOURCE_FAILED)
    assert notice.title == "Padaria Central · procuração deixou de valer"
    assert notice.company_id == world.padaria.pk and notice.recipient == world.owner


def test_a_company_that_never_had_a_procuracao_is_not_a_loss() -> None:
    world = World()
    lose(synced(world), had_ok=False)

    assert procuracao_alerts.notify_lost_procuracoes() == 0


def test_an_old_check_and_a_recovered_company_do_not_alert() -> None:
    world = World()
    sync = synced(world)
    lose(sync, checked_ago=timedelta(days=5))
    assert procuracao_alerts.notify_lost_procuracoes() == 0

    NfseSync.objects.filter(pk=sync.pk).update(
        procuracao_status=NfseSync.ProcuracaoStatus.OK, procuracao_checked_at=timezone.now()
    )

    assert procuracao_alerts.notify_lost_procuracoes() == 0


def test_a_second_loss_after_a_recovery_alerts_again() -> None:
    world = World()
    sync = synced(world)
    lose(sync)
    assert procuracao_alerts.notify_lost_procuracoes() == 1
    NfseSync.objects.filter(pk=sync.pk).update(
        procuracao_status=NfseSync.ProcuracaoStatus.OK,
        procuracao_ok_at=timezone.now() - timedelta(days=1),
    )
    NfseSync.objects.filter(pk=sync.pk).update(
        procuracao_status=NfseSync.ProcuracaoStatus.MISSING, procuracao_checked_at=timezone.now()
    )

    assert notify_lost_procuracoes() == 1  # outro ok_at, outra perda


# ---------------------------------------------------------------- saúde da fila


def lane_on(settings: Any) -> None:
    settings.NFSE_PROCURACAO_SYNC_ENABLED = True
    settings.NFSE_ADN_ENVIRONMENT = "production"


def test_a_lane_that_is_off_is_healthy_by_definition() -> None:
    assert procuracao_alerts.lane_health() == {
        "enabled": False,
        "stalled": False,
        "overdue": 0,
        "oldest_minutes": 0,
    }


def test_a_lane_that_is_keeping_up_is_not_stalled(settings: Any) -> None:
    lane_on(settings)
    world = World()
    certificate(world, days=200)
    synced(world)
    NfseSync.objects.update(next_run_at=timezone.now() + timedelta(minutes=30))

    health = procuracao_alerts.lane_health()

    assert health["enabled"] is True and health["stalled"] is False and health["overdue"] == 0


def test_rows_overdue_by_hours_make_the_lane_stalled_and_say_how_far_behind(
    settings: Any, caplog: pytest.LogCaptureFixture
) -> None:
    lane_on(settings)
    world = World()
    certificate(world, days=200)
    synced(world)
    now = timezone.now()
    NfseSync.objects.filter(company=world.padaria).update(next_run_at=now - timedelta(hours=9))
    NfseSync.objects.filter(company=world.oficina).update(next_run_at=now - timedelta(hours=7))
    NfseSync.objects.filter(company=world.mercado).update(next_run_at=now - timedelta(hours=2))
    NfseSync.objects.update(office_certificate=OfficeCertificate.objects.get())

    with caplog.at_level("WARNING"):
        health = procuracao_alerts.lane_health(now=now)

    assert health["stalled"] is True and health["overdue"] == 2
    assert 530 <= health["oldest_minutes"] <= 545  # ~9 h
    assert "procuracao.lane_stalled overdue=2" in caplog.text


def test_the_hourly_task_reports_the_same_numbers(settings: Any) -> None:
    lane_on(settings)

    assert check_procuracao_lane()["enabled"] is True
