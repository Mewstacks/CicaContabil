"""Lacunas de recuperação da coleta por procuração (E1b, leitura de 23/11/2026).

1. Certificado recusado (401/403) não podia continuar sendo testado contra a carteira inteira.
2. e-CNPJ vencido parava a fila em silêncio: nenhum aviso depois do dia do vencimento.
3. Linha em erro não voltava sozinha nem quando o escritório enviava outro e-CNPJ.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.utils import timezone

from apps.hub import procuracao_alerts
from apps.hub.models import NfseSync, Notification, OfficeCertificate
from apps.hub.nfse_procuracao import (
    CERTIFICATE_PROBLEM_QUARANTINE_MINUTES,
    eligible_procuracao_syncs,
)
from apps.hub.office_certificate import store_office_certificate
from apps.hub.tasks_procuracao import notify_office_certificates
from pki_support import make_pfx
from test_nfse_procuracao import OFFICE_CNPJ, PASSWORD, due_sync, run_with
from test_nfse_procuracao_views import World
from test_procuracao_alerts import certificate

pytestmark = pytest.mark.django_db


# ------------------------------------------------------------ certificado recusado (401, 403)


@pytest.mark.parametrize("status", [401, 403])
def test_a_refused_e_cnpj_is_quarantined_so_the_chain_stops_testing_the_portfolio(
    status: int,
) -> None:
    sync, cert = due_sync(f"recusado-{status}")

    result, _ = run_with(sync, (status, b""))

    cert.refresh_from_db()
    assert result["quarantined"] is True
    assert cert.quarantined_until is not None
    assert cert.quarantined_until >= timezone.now() + timedelta(
        minutes=CERTIFICATE_PROBLEM_QUARANTINE_MINUTES - 1
    )
    assert not eligible_procuracao_syncs().exists()


# ------------------------------------------------------------ e-CNPJ vencido


def _lane_row(world: World, cert: OfficeCertificate | None, **extra: object) -> NfseSync:
    return NfseSync.objects.create(
        organization=world.office,
        company=world.padaria,
        credential_mode=NfseSync.CredentialMode.PROCURACAO,
        office_certificate=cert,
        enabled=True,
        **extra,
    )


def test_an_expired_e_cnpj_is_announced_once_and_the_lane_reports_it_blocked(settings) -> None:  # type: ignore[no-untyped-def]
    settings.NFSE_PROCURACAO_SYNC_ENABLED = True
    settings.NFSE_ADN_ENVIRONMENT = "production"
    world = World()
    cert = certificate(world, days=-3)
    _lane_row(world, cert, status=NfseSync.Status.IDLE, next_run_at=timezone.now())

    assert procuracao_alerts.notify_office_certificate_expired() == 1  # só o dono
    assert procuracao_alerts.notify_office_certificate_expired() == 0
    notice = Notification.objects.get(kind=Notification.Kind.CERTIFICATE_EXPIRING)
    assert notice.dedupe_key == f"office-cert-expired:{cert.pk}"
    assert "parada" in notice.title

    health = procuracao_alerts.lane_health()
    assert health["blocked"] == 1
    assert health["stalled"] is True


def test_a_newer_valid_e_cnpj_silences_the_expired_notice() -> None:
    world = World()
    certificate(world, days=-3)
    certificate(world, days=300, fingerprint_sha256="b" * 64)

    assert procuracao_alerts.notify_office_certificate_expired() == 0


def test_an_e_cnpj_expired_long_ago_or_revoked_stays_quiet() -> None:
    world = World()
    certificate(world, days=-90)
    certificate(world, days=-2, revoked_at=timezone.now(), fingerprint_sha256="r" * 64)

    assert procuracao_alerts.notify_office_certificate_expired() == 0


def test_a_row_waiting_for_the_first_e_cnpj_is_not_blocked(settings) -> None:  # type: ignore[no-untyped-def]
    settings.NFSE_PROCURACAO_SYNC_ENABLED = True
    settings.NFSE_ADN_ENVIRONMENT = "production"
    world = World()
    _lane_row(world, None, status=NfseSync.Status.IDLE, next_run_at=timezone.now())

    assert procuracao_alerts.lane_health()["blocked"] == 0


def test_the_daily_task_also_announces_the_expired_e_cnpj() -> None:
    world = World()
    certificate(world, days=-1)

    assert notify_office_certificates() == 1


# ------------------------------------------------------------ outro e-CNPJ reabre as linhas em erro


def _errored(world: World, cert: OfficeCertificate, company_name: str = "padaria") -> NfseSync:
    return _lane_row(
        world,
        cert,
        status=NfseSync.Status.ERROR,
        failure_count=4,
        last_error_code="certificate_problem",
        last_error_message="O ADN rejeitou o e-CNPJ do escritório (E2213).",
        last_error_at=timezone.now(),
        procuracao_status=NfseSync.ProcuracaoStatus.ERROR,
        next_run_at=None,
    )


def test_a_new_e_cnpj_gives_the_rows_that_stopped_on_an_error_another_chance() -> None:
    world = World()
    old = certificate(world, days=200)
    stuck = _errored(world, old)
    other_sync, _ = due_sync("outro-escritorio")
    NfseSync.objects.filter(pk=other_sync.pk).update(status=NfseSync.Status.ERROR)

    new = store_office_certificate(
        organization=world.office,
        pfx_bytes=make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ),
        password=PASSWORD,
    )

    stuck.refresh_from_db()
    assert stuck.office_certificate_id == new.pk
    assert stuck.status == NfseSync.Status.IDLE
    assert stuck.failure_count == 0
    assert stuck.last_error_code == "" and stuck.last_error_message == ""
    assert stuck.procuracao_status == NfseSync.ProcuracaoStatus.UNKNOWN
    assert stuck.next_run_at is not None and stuck.next_run_at <= timezone.now()
    # Outro escritório não é tocado.
    other_sync.refresh_from_db()
    assert other_sync.status == NfseSync.Status.ERROR


def test_a_new_e_cnpj_leaves_waiting_and_healthy_rows_alone() -> None:
    world = World()
    old = certificate(world, days=200)
    waiting = _lane_row(
        world,
        old,
        status=NfseSync.Status.IDLE,
        procuracao_status=NfseSync.ProcuracaoStatus.MISSING,
        failure_count=0,
        next_run_at=timezone.now() + timedelta(hours=5),
    )

    store_office_certificate(
        organization=world.office,
        pfx_bytes=make_pfx(password=PASSWORD, cnpj=OFFICE_CNPJ),
        password=PASSWORD,
    )

    waiting.refresh_from_db()
    assert waiting.procuracao_status == NfseSync.ProcuracaoStatus.MISSING
    assert waiting.next_run_at > timezone.now() + timedelta(hours=4)
