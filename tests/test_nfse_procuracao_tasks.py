"""Fila de procuração (D-304): despacho, pausa, encadeamento e flag desligada."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.test import override_settings
from django.utils import timezone

from apps.hub.models import NfseSync, OfficeCertificate
from apps.hub.tasks_procuracao import (
    PAUSE_CACHE_KEY,
    chain_procuracao_certificate,
    dispatch_procuracao_syncs,
    poll_procuracao_sync,
)
from test_nfse_procuracao import make_company, make_office

ENABLED = {"NFSE_PROCURACAO_SYNC_ENABLED": True, "NFSE_ADN_ENVIRONMENT": "production"}


@pytest.fixture(autouse=True)
def clean_cache() -> None:
    cache.delete(PAUSE_CACHE_KEY)


def office_with_companies(slug: str, count: int) -> tuple[OfficeCertificate, list[NfseSync]]:
    office, certificate = make_office(slug)
    assert certificate is not None
    from test_nfse_procuracao import cnpj_from

    syncs = []
    for index in range(count):
        company = make_company(office, cnpj_from(f"{index + 10:02d}3456780001"))
        syncs.append(
            NfseSync.objects.create(
                organization=office,
                company=company,
                credential_mode=NfseSync.CredentialMode.PROCURACAO,
                office_certificate=certificate,
                enabled=True,
                status=NfseSync.Status.IDLE,
                next_run_at=timezone.now() - timedelta(minutes=1),
            )
        )
    return certificate, syncs


@pytest.mark.django_db
@pytest.mark.parametrize(
    "settings_override",
    [
        {"NFSE_PROCURACAO_SYNC_ENABLED": False, "NFSE_ADN_ENVIRONMENT": "production"},
        {"NFSE_PROCURACAO_SYNC_ENABLED": True, "NFSE_ADN_ENVIRONMENT": "trial"},
    ],
)
def test_the_lane_does_nothing_when_disabled_or_outside_production(
    settings_override: dict[str, object],
) -> None:
    _certificate, syncs = office_with_companies("lane-off", 2)

    with (
        override_settings(**settings_override),
        patch("apps.hub.tasks_procuracao.poll_procuracao_sync.delay") as queued,
        patch("apps.hub.tasks_procuracao.run_procuracao_sync") as run,
    ):
        assert dispatch_procuracao_syncs() == 0
        assert poll_procuracao_sync(str(syncs[0].pk)) == {"state": "disabled"}
        assert chain_procuracao_certificate("x") == 0

    queued.assert_not_called()
    run.assert_not_called()
    assert NfseSync.objects.filter(status=NfseSync.Status.IDLE).count() == 2


@pytest.mark.django_db
@override_settings(**ENABLED)
def test_dispatch_starts_one_company_per_certificate() -> None:
    first_certificate, first = office_with_companies("lane-a", 3)
    second_certificate, second = office_with_companies("lane-b", 2)

    with patch("apps.hub.tasks_procuracao.poll_procuracao_sync.delay") as queued:
        assert dispatch_procuracao_syncs() == 2
        assert dispatch_procuracao_syncs() == 0

    assert queued.call_count == 2
    assert NfseSync.objects.filter(status=NfseSync.Status.QUEUED).count() == 2
    for certificate, group in ((first_certificate, first), (second_certificate, second)):
        assert (
            NfseSync.objects.filter(
                office_certificate=certificate, status=NfseSync.Status.QUEUED
            ).count()
            == 1
        )
        assert len(group) >= 2


@pytest.mark.django_db
@override_settings(**ENABLED)
def test_dispatch_seeds_the_rows_of_new_companies() -> None:
    office, _certificate = make_office("lane-semente")
    make_company(office)

    with patch("apps.hub.tasks_procuracao.poll_procuracao_sync.delay") as queued:
        assert dispatch_procuracao_syncs() == 1

    assert NfseSync.objects.filter(organization=office).count() == 1
    queued.assert_called_once()


@pytest.mark.django_db
@override_settings(**ENABLED)
def test_a_paused_lane_dispatches_nothing() -> None:
    office_with_companies("lane-pausa", 2)
    cache.set(PAUSE_CACHE_KEY, True, 60)

    with patch("apps.hub.tasks_procuracao.poll_procuracao_sync.delay") as queued:
        assert dispatch_procuracao_syncs() == 0

    queued.assert_not_called()


@pytest.mark.django_db
@override_settings(**ENABLED)
def test_dispatch_recovers_rows_left_running_by_a_dead_worker() -> None:
    certificate, syncs = office_with_companies("lane-recupera", 1)
    NfseSync.objects.filter(pk=syncs[0].pk).update(
        status=NfseSync.Status.RUNNING,
        lease_token="00000000-0000-0000-0000-000000000001",
        lease_until=timezone.now() - timedelta(minutes=1),
    )
    OfficeCertificate.objects.filter(pk=certificate.pk).update(
        lease_token="00000000-0000-0000-0000-000000000001",
        lease_until=timezone.now() - timedelta(minutes=1),
    )

    with patch("apps.hub.tasks_procuracao.poll_procuracao_sync.delay") as queued:
        assert dispatch_procuracao_syncs() == 1

    queued.assert_called_once_with(str(syncs[0].pk))
    certificate.refresh_from_db()
    assert certificate.lease_token is None


@pytest.mark.django_db
@override_settings(**ENABLED)
def test_poll_chains_the_next_company_of_the_same_certificate() -> None:
    certificate, syncs = office_with_companies("lane-cadeia", 2)
    NfseSync.objects.filter(pk=syncs[0].pk).update(status=NfseSync.Status.QUEUED)

    with (
        patch(
            "apps.hub.tasks_procuracao.run_procuracao_sync",
            return_value={"state": "completed", "certificate_id": certificate.pk},
        ),
        patch("apps.hub.tasks_procuracao.chain_procuracao_certificate.apply_async") as chained,
    ):
        poll_procuracao_sync(str(syncs[0].pk))

    chained.assert_called_once_with(args=[str(certificate.pk)], countdown=1)


@pytest.mark.django_db
@override_settings(**ENABLED)
def test_a_429_pauses_the_lane_and_stops_the_chain() -> None:
    certificate, syncs = office_with_companies("lane-429", 2)

    with (
        patch(
            "apps.hub.tasks_procuracao.run_procuracao_sync",
            return_value={
                "state": "retry",
                "certificate_id": certificate.pk,
                "pause_seconds": 60,
            },
        ),
        patch("apps.hub.tasks_procuracao.chain_procuracao_certificate.apply_async") as chained,
    ):
        poll_procuracao_sync(str(syncs[0].pk))

    assert cache.get(PAUSE_CACHE_KEY) is True
    chained.assert_not_called()


@pytest.mark.django_db
@override_settings(**ENABLED)
def test_a_quarantined_certificate_stops_the_chain() -> None:
    certificate, syncs = office_with_companies("lane-495", 2)

    with (
        patch(
            "apps.hub.tasks_procuracao.run_procuracao_sync",
            return_value={"state": "retry", "certificate_id": certificate.pk, "quarantined": True},
        ),
        patch("apps.hub.tasks_procuracao.chain_procuracao_certificate.apply_async") as chained,
    ):
        poll_procuracao_sync(str(syncs[0].pk))

    chained.assert_not_called()


@pytest.mark.django_db
@override_settings(**ENABLED)
def test_chain_takes_the_next_due_company_and_nothing_while_one_is_in_flight() -> None:
    certificate, syncs = office_with_companies("lane-proxima", 2)

    with patch("apps.hub.tasks_procuracao.poll_procuracao_sync.delay") as queued:
        assert chain_procuracao_certificate(str(certificate.pk)) == 1
        assert chain_procuracao_certificate(str(certificate.pk)) == 0

    queued.assert_called_once()
    assert NfseSync.objects.filter(pk__in=[s.pk for s in syncs], status="queued").count() == 1
