"""Financial pilot boundaries are enforced before intake, including old clients."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import ClientCompany, DominioBankEntry, FinancialAccount
from apps.intelligence.agent_scope import build_sync_scope, validate_sync_scope
from apps.intelligence.agents import issue_enrollment, redeem_enrollment
from apps.intelligence.models import AgentEnrollment, EdgeAgent, IntelligenceConnector

pytestmark = pytest.mark.django_db


@pytest.fixture
def scoped(organization):
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa piloto", dominio_code="1"
    )
    account = FinancialAccount.objects.create(
        organization=organization, company=company, name="Conta piloto", account_reference="001:123"
    )
    scope = build_sync_scope(
        account=account, start=date(2026, 9, 1), end=date(2026, 9, 30), statement_ids=["10"]
    )
    enrollment = issue_enrollment(organization=organization, sync_scope=scope)
    credentials = redeem_enrollment(
        code=enrollment.code, label="Sintético", fingerprint="local", allow_scoped=True
    )
    return credentials, account


def post(credentials, route, payload, *, protocol="scoped-v1", extra_headers=None):
    body = json.dumps(payload).encode()
    timestamp = str(int(timezone.now().timestamp()))
    signature = hmac.new(
        credentials.shared_secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return Client().post(
        reverse(route),
        data=body,
        content_type="application/json",
        headers={
            "X-Hub-Agent-ID": credentials.agent_id,
            "X-Hub-Agent-Timestamp": timestamp,
            "X-Hub-Agent-Signature": signature,
            "X-Hub-Agent-Protocol": protocol,
            **(extra_headers or {}),
        },
        secure=True,
    )


def row(index=1):
    return {
        "source_id": f"1|10|{index}",
        "company_code": "1",
        "occurred_on": "2026-09-12",
        "description": "Sintético",
        "amount": "1.00",
        "direction": "C",
        "is_linked": False,
        "account_reference": "001:123",
    }


def test_unscoped_native_financial_client_is_refused_before_creating_connector(organization):
    enrollment = issue_enrollment(organization=organization)
    credentials = redeem_enrollment(code=enrollment.code, label="Antigo", fingerprint="local")
    assert post(credentials, "agent-v2-dominio-bank-entries", {"rows": []}).status_code == 403
    assert post(credentials, "agent-v2-dominio-companies", {"companies": []}).status_code == 403
    assert not IntelligenceConnector.objects.exists()


@pytest.mark.parametrize("count", [0, 1, 499, 500, 501])
def test_scoped_page_sizes_and_retry_are_atomic(scoped, count):
    credentials, _ = scoped
    payload = {
        "scope_revision": credentials.sync_scope["revision"],
        "rows": [row(i) for i in range(count)],
    }
    response = post(credentials, "agent-v2-dominio-bank-entries", payload)
    assert response.status_code == (400 if count > 500 else 200)
    assert DominioBankEntry.objects.count() == (0 if count > 500 else count)
    if count <= 500:
        assert post(credentials, "agent-v2-dominio-bank-entries", payload).json()["created"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("company_code", "2"),
        ("source_id", "1|11|1"),
        ("source_id", "2|10|1"),
        ("account_reference", "001:other"),
        ("occurred_on", "2026-10-01"),
        ("occurred_on", "2026-08-31"),
        ("occurred_on", "2026-09-99"),
    ],
)
def test_one_out_of_scope_row_rejects_the_entire_page(scoped, field, value):
    credentials, _ = scoped
    payload = {
        "scope_revision": credentials.sync_scope["revision"],
        "rows": [row(), {**row(2), field: value}],
    }
    assert post(credentials, "agent-v2-dominio-bank-entries", payload).status_code == 403
    assert not DominioBankEntry.objects.exists()
    assert not IntelligenceConnector.objects.exists()


def test_stale_manifest_old_protocol_other_modules_and_legacy_endpoint_are_refused(scoped):
    credentials, _ = scoped
    payload = {"scope_revision": credentials.sync_scope["revision"], "rows": [row()]}
    assert post(credentials, "agent-v2-heartbeat", {}, protocol="").status_code == 401
    assert (
        post(
            credentials, "agent-v2-dominio-bank-entries", {**payload, "scope_revision": "wrong"}
        ).status_code
        == 403
    )
    assert (
        post(
            credentials, "agent-v2-profitability-datasets", {"source_system": "dominio"}
        ).status_code
        == 401
    )
    assert post(credentials, "intelligence-agent-sync", {"companies": []}).status_code == 401
    config = post(credentials, "agent-v2-configuration-next", {}).json()
    assert config["windows_archive_root"] == ""
    assert config["sync_scope"] == credentials.sync_scope


def test_deactivating_account_revokes_financial_scope_without_mutating_history(scoped):
    credentials, account = scoped
    payload = {"scope_revision": credentials.sync_scope["revision"], "rows": [row()]}
    assert post(credentials, "agent-v2-dominio-bank-entries", payload).status_code == 200
    account.active = False
    account.save(update_fields=["active"])
    assert post(credentials, "agent-v2-heartbeat", {}).status_code == 401
    assert DominioBankEntry.objects.count() == 1


def test_manifest_cannot_cross_office_or_change_without_new_revision(scoped, organization):
    credentials, account = scoped
    with pytest.raises(ValueError, match="revisão"):
        validate_sync_scope({**credentials.sync_scope, "statement_ids": ["11"]}, organization)
    account.account_reference = "new"
    account.save(update_fields=["account_reference"])
    with pytest.raises(ValueError, match="conta"):
        validate_sync_scope(credentials.sync_scope, organization)
    assert EdgeAgent.objects.get(pk=credentials.agent_id).sync_scope == credentials.sync_scope


def test_scoped_code_is_not_consumed_by_legacy_bootstrap(scoped, organization):
    credentials, _ = scoped
    enrollment = issue_enrollment(organization=organization, sync_scope=credentials.sync_scope)
    with pytest.raises(ValueError, match="protocolo"):
        redeem_enrollment(code=enrollment.code, label="Antigo", fingerprint="legacy")
    assert AgentEnrollment.objects.filter(used_at__isnull=True).count() == 1
