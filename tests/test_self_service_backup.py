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

from apps.hub.models import ClientCompany, DataSource, ImportBatch
from apps.intelligence.models import EdgeAgent
from apps.organizations.models import Organization
from apps.platform.models import TenantContract, TenantLifecycle
from apps.platform.pricing import quote_subscription
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


def test_pricing_applies_all_ranges_without_a_company_ceiling() -> None:
    two = quote_subscription(module_codes=["nfse", "guides"], company_count=20)
    three = quote_subscription(module_codes=["nfse", "guides", "reform"], company_count=50)
    full = quote_subscription(
        module_codes=[
            "nfse",
            "guides",
            "integra",
            "reconciliation",
            "reform",
            "journey",
            "ai",
        ],
        company_count=2_000,
    )

    assert two.discount_percent == 10
    assert two.monthly_cents == 24_120
    assert three.discount_percent == 15
    assert three.company_multiplier.as_tuple().exponent == -2
    assert full.discount_percent == 25
    assert full.company_multiplier.as_tuple().digits == (1, 8, 2)
    assert full.monthly_cents == 128_720


@override_settings(EDGE_AGENT_MTLS_REQUIRED=False)
def test_agent_claims_downloads_and_completes_a_web_backup(tmp_path) -> None:
    organization = Organization.objects.create(name="Regaro Teste", slug="regaro-teste")
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
        completed = _post(
            client, agent, "/api/agent/v2/sync/complete", {"batch_id": str(batch.id)}
        )

    batch.refresh_from_db()
    source.refresh_from_db()
    assert page.json() == {"created": 1, "updated": 0, "ignored": 0}
    assert completed.json() == {"status": "completed"}
    assert batch.status == ImportBatch.Status.COMPLETED
    assert batch.backup_key == ""
    assert not batch.source_file
    assert source.status == DataSource.Status.READY
    assert source.capabilities == ["companies"]
    assert ClientCompany.objects.filter(
        organization=organization, data_source=source, external_key="1"
    ).exists()


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
