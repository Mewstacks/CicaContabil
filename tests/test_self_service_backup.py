from __future__ import annotations

import hashlib
import hmac
import json
import time
from datetime import timedelta

import pytest
from django.core.files.base import ContentFile
from django.test import Client, override_settings
from django.utils import timezone

from apps.hub.models import (
    AccumulatorCatalogEntry,
    AccumulatorHistoryEntry,
    AccumulatorObservation,
    ClientCompany,
    DataSource,
    ImportBatch,
)
from apps.intelligence.models import EdgeAgent
from apps.organizations.models import Organization
from apps.platform.models import TenantContract, TenantLifecycle
from apps.platform.tasks import advance_tenant_lifecycles

pytestmark = pytest.mark.django_db


def _signed_headers(agent: EdgeAgent, body: bytes) -> dict[str, str]:
    timestamp = str(int(time.time()))
    signature = hmac.new(
        agent.shared_secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return {
        "X-Hub-Agent-ID": str(agent.id),
        "X-Hub-Agent-Timestamp": timestamp,
        "X-Hub-Agent-Signature": signature,
    }


def _post(client: Client, agent: EdgeAgent, path: str, payload: dict[str, object]):
    body = json.dumps(payload, separators=(",", ":")).encode()
    return client.generic(
        "POST", path, body, content_type="application/json", headers=_signed_headers(agent, body)
    )


@override_settings(EDGE_AGENT_MTLS_REQUIRED=False)
def test_agent_claims_downloads_and_completes_a_web_backup(tmp_path) -> None:
    organization = Organization.objects.create(name="CICA Teste", slug="cica-teste")
    source = DataSource.objects.create(
        organization=organization,
        kind=DataSource.Kind.DOMINIO_WEB_BACKUP,
        label="Domínio Web",
        status=DataSource.Status.PROCESSING,
    )
    agent = EdgeAgent.objects.create(
        organization=organization,
        label="Servidor",
        fingerprint="fingerprint",
        shared_secret="secret-for-tests",
    )
    content = b"PK\x03\x04fake-dom-backup"
    batch = ImportBatch.objects.create(
        organization=organization,
        data_source=source,
        kind=ImportBatch.Kind.DOMINIO_BACKUP,
        status=ImportBatch.Status.QUEUED,
        original_filename="escritorio.dom",
        content_hash=hashlib.sha256(content).hexdigest(),
        backup_key="onvio-key",
        source_snapshot_at=timezone.now(),
        mapping={"bridge_required": True},
    )
    client = Client()
    with override_settings(MEDIA_ROOT=tmp_path):
        batch.source_file.save("escritorio.dom", ContentFile(content), save=True)
        claim = _post(client, agent, "/api/agent/v2/backups/next", {})
        job = claim.json()["job"]
        assert claim.status_code == 200
        assert job["id"] == str(batch.id)
        assert job["backup_key"] == "onvio-key"

        download = _post(client, agent, f"/api/agent/v2/backups/{batch.id}/download", {})
        assert b"".join(download.streaming_content) == content

        page = _post(
            client,
            agent,
            "/api/agent/v2/sync/companies",
            {
                "batch_id": str(batch.id),
                "rows": [
                    {
                        "external_key": "1",
                        "name": "Empresa do backup",
                        "cnpj": "12.345.678/0001-90",
                        "active": True,
                    }
                ],
            },
        )
        accumulator_page = _post(
            client,
            agent,
            "/api/agent/v2/sync/accumulator_catalog",
            {
                "batch_id": str(batch.id),
                "rows": [
                    {
                        "company_key": "1",
                        "accumulator_code": "SERV-001",
                        "name": "Servicos prestados",
                        "active": True,
                        "source_identifier": "42",
                    }
                ],
            },
        )
        observation_page = _post(
            client,
            agent,
            "/api/agent/v2/sync/accumulator_observations",
            {
                "batch_id": str(batch.id),
                "rows": [
                    {
                        "company_key": "1",
                        "accumulator_code": "SERV-001",
                        "service_code": "1401",
                        "counterparty_ref": "9f86d081884c7d659a2feaa0",
                        "direction": "provided",
                        "frequency": 7,
                        "last_used_at": "2026-09-23T20:00:00-03:00",
                    }
                ],
            },
        )
        completed = _post(
            client, agent, "/api/agent/v2/sync/complete", {"batch_id": str(batch.id)}
        )

    batch.refresh_from_db()
    source.refresh_from_db()
    assert page.json() == {"created": 1, "updated": 0, "ignored": 0}
    assert accumulator_page.json() == {"created": 1, "updated": 0, "ignored": 0}
    assert observation_page.json() == {"created": 1, "updated": 0, "ignored": 0}
    assert completed.json() == {"status": "completed"}
    assert batch.status == ImportBatch.Status.COMPLETED
    assert batch.backup_key == ""
    assert not batch.source_file
    assert source.status == DataSource.Status.READY
    assert source.capabilities == [
        "accumulator_catalog",
        "accumulator_observations",
        "companies",
    ]
    assert ClientCompany.objects.filter(
        organization=organization, data_source=source, external_key="1"
    ).exists()
    assert AccumulatorCatalogEntry.objects.filter(
        organization=organization,
        company__external_key="1",
        accumulator_code="SERV-001",
        source_batch=batch,
    ).exists()
    assert AccumulatorHistoryEntry.objects.filter(
        organization=organization,
        company__external_key="1",
        accumulator_code="SERV-001",
        source=AccumulatorHistoryEntry.Source.BACKUP,
    ).exists()
    assert AccumulatorObservation.objects.filter(
        organization=organization,
        company__external_key="1",
        accumulator_code="SERV-001",
        service_code="1401",
        counterparty_ref="9f86d081884c7d659a2feaa0",
        direction=AccumulatorObservation.Direction.PROVIDED,
        frequency=7,
    ).exists()


@override_settings(EDGE_AGENT_MTLS_REQUIRED=False)
def test_backup_rejects_observation_outside_the_company_catalog() -> None:
    organization = Organization.objects.create(name="CICA Teste", slug="cica-teste-invalid")
    source = DataSource.objects.create(
        organization=organization,
        kind=DataSource.Kind.DOMINIO_WEB_BACKUP,
        label="Domínio Web",
        status=DataSource.Status.PROCESSING,
    )
    agent = EdgeAgent.objects.create(
        organization=organization,
        label="Servidor",
        fingerprint="fingerprint-invalid",
        shared_secret="secret-for-tests",
    )
    batch = ImportBatch.objects.create(
        organization=organization,
        data_source=source,
        kind=ImportBatch.Kind.DOMINIO_BACKUP,
        status=ImportBatch.Status.PROCESSING,
        content_hash="a" * 64,
        source_snapshot_at=timezone.now(),
        mapping={"claimed_by": str(agent.id)},
    )
    ClientCompany.objects.create(
        organization=organization,
        data_source=source,
        external_key="1",
        dominio_code="1",
        name="Empresa do backup",
    )

    response = _post(
        Client(),
        agent,
        "/api/agent/v2/sync/accumulator_observations",
        {
            "batch_id": str(batch.id),
            "rows": [
                {
                    "company_key": "1",
                    "accumulator_code": "FORA-DO-CATALOGO",
                    "service_code": "1401",
                    "frequency": 1,
                    "last_used_at": "2026-09-23T20:00:00-03:00",
                }
            ],
        },
    )

    assert response.status_code == 200
    assert response.json() == {"created": 0, "updated": 0, "ignored": 1}
    batch.refresh_from_db()
    assert batch.ignored_count == 1
    assert batch.errors[0]["message"] == "Acumulador não pertence ao catálogo da empresa."
    assert not AccumulatorObservation.objects.filter(organization=organization).exists()


def test_trial_moves_to_read_only_grace_without_automatic_suspension() -> None:
    organization = Organization.objects.create(name="Ciclo", slug="ciclo")
    contract = TenantContract.objects.create(
        organization=organization,
        status=TenantContract.Status.TRIAL,
        trial_ends_on=timezone.localdate() - timedelta(days=1),
    )
    lifecycle = TenantLifecycle.objects.create(
        organization=organization, state=TenantLifecycle.State.ACTIVE
    )

    assert advance_tenant_lifecycles() == 1
    contract.refresh_from_db()
    lifecycle.refresh_from_db()
    assert contract.status == TenantContract.Status.GRACE
    assert lifecycle.state == TenantLifecycle.State.GRACE

    contract.grace_ends_on = timezone.localdate() - timedelta(days=1)
    contract.save(update_fields=["grace_ends_on"])
    assert advance_tenant_lifecycles() == 0
    contract.refresh_from_db()
    lifecycle.refresh_from_db()
    assert contract.status == TenantContract.Status.GRACE
    assert lifecycle.state == TenantLifecycle.State.GRACE
