"""D-310: explicit HTTPS/HMAC pairing requires no private client CA."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date, timedelta
from unittest.mock import patch

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import ClientCompany, DominioBankEntry, FinancialAccount
from apps.intelligence.agent_scope import build_sync_scope
from apps.intelligence.agents import issue_enrollment, revoke_agent
from apps.intelligence.models import AgentEnrollment, EdgeAgent

pytestmark = pytest.mark.django_db


@pytest.fixture
def pilot(organization, settings):
    settings.EDGE_AGENT_MTLS_REQUIRED = False
    settings.EDGE_AGENT_CA_CERT_PATH = ""
    settings.EDGE_AGENT_CA_KEY_PATH = ""
    company = ClientCompany.objects.create(
        organization=organization, name="Synthetic HMAC", dominio_code="1"
    )
    account = FinancialAccount.objects.create(
        organization=organization, company=company, name="Synthetic", account_reference="001:123"
    )
    scope = build_sync_scope(
        account=account, start=date(2026, 9, 1), end=date(2026, 9, 30), statement_ids=["10"]
    )
    enrollment = issue_enrollment(organization=organization, sync_scope=scope)
    return enrollment, scope


def enroll(pilot, *, secure=True, **extra):
    return Client().post(
        reverse("agent-v2-enroll"),
        data=json.dumps(
            {
                "code": pilot[0].code,
                "label": "Synthetic Windows",
                "fingerprint": "synthetic",
                "authentication_mode": "hmac",
                **extra,
            }
        ),
        content_type="application/json",
        headers={"X-Hub-Agent-Protocol": "scoped-v1"},
        secure=secure,
    )


def signed(
    credentials,
    route="agent-v2-heartbeat",
    payload=None,
    *,
    secure=True,
    timestamp=None,
    signature=None,
):
    body = json.dumps(payload or {}).encode()
    stamp = timestamp or str(int(timezone.now().timestamp()))
    proof = (
        signature
        if signature is not None
        else hmac.new(
            credentials["shared_secret"].encode(), stamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
    )
    return Client().post(
        reverse(route),
        data=body,
        content_type="application/json",
        secure=secure,
        headers={
            "X-Hub-Agent-ID": credentials["agent_id"],
            "X-Hub-Agent-Timestamp": stamp,
            "X-Hub-Agent-Signature": proof,
            "X-Hub-Agent-Protocol": "scoped-v1",
        },
    )


def test_hmac_pairing_works_without_csr_certificate_or_ca_and_is_single_use(pilot):
    with patch("apps.intelligence.agent_v2._sign_csr", side_effect=AssertionError("CA unused")):
        response = enroll(pilot)
        assert response.status_code == 200
        credentials = response.json()
        assert credentials["authentication_mode"] == "hmac"
        assert credentials["sync_scope"] == pilot[1]
        assert "certificate" not in credentials and "certificate_chain" not in credentials
        assert response.headers["Cache-Control"] == "no-store"
        assert EdgeAgent.objects.get().mtls_certificate_sha256 == ""
        assert signed(credentials).status_code == 200
        assert enroll(pilot).status_code == 403
        assert EdgeAgent.objects.count() == 1


def test_http_pairing_never_consumes_the_code(pilot):
    assert enroll(pilot, secure=False).status_code == 400
    assert not EdgeAgent.objects.exists()
    assert AgentEnrollment.objects.get().used_at is None


@pytest.mark.parametrize("agent_id", ["", "not-a-uuid"])
def test_missing_or_malformed_agent_identity_is_rejected_without_server_error(pilot, agent_id):
    response = Client().post(
        reverse("agent-v2-heartbeat"),
        data="{}",
        content_type="application/json",
        secure=True,
        headers={"X-Hub-Agent-ID": agent_id},
    )
    assert response.status_code == 401


@pytest.mark.parametrize("mode", ["", "unknown", None, {}, 123])
def test_unknown_mode_never_consumes_the_code_or_opens_the_ca(pilot, mode):
    with patch("apps.intelligence.agent_v2._sign_csr", side_effect=AssertionError("CA unused")):
        assert enroll(pilot, authentication_mode=mode).status_code == 400
    assert not EdgeAgent.objects.exists()
    assert AgentEnrollment.objects.get().used_at is None


def test_explicit_mtls_deployment_refuses_hmac_without_consuming_code(pilot, settings):
    settings.EDGE_AGENT_MTLS_REQUIRED = True
    assert enroll(pilot).status_code == 403
    assert not EdgeAgent.objects.exists()
    assert AgentEnrollment.objects.get().used_at is None


def test_legacy_certificate_client_does_not_silently_fall_back_to_hmac(pilot):
    assert enroll(pilot, authentication_mode="mtls", csr="not-a-csr").status_code == 503
    assert not EdgeAgent.objects.exists()
    assert AgentEnrollment.objects.get().used_at is None


def test_expired_hmac_code_is_refused(pilot):
    AgentEnrollment.objects.update(expires_at=timezone.now() - timedelta(seconds=1))
    assert enroll(pilot).status_code == 403
    assert not EdgeAgent.objects.exists()


@pytest.mark.parametrize("seconds", [-301, 301])
def test_hmac_rejects_old_or_future_signatures(pilot, seconds):
    credentials = enroll(pilot).json()
    stamp = str(int((timezone.now() + timedelta(seconds=seconds)).timestamp()))
    assert signed(credentials, timestamp=stamp).status_code == 401


@pytest.mark.parametrize("proof", ["0" * 64, "ç" * 64, "", "not-a-signature"])
def test_hmac_rejects_bad_proofs_without_server_error(pilot, proof):
    credentials = enroll(pilot).json()
    assert signed(credentials, signature=proof).status_code == 401


def test_hmac_requires_https_and_revocation_still_takes_effect(pilot):
    credentials = enroll(pilot).json()
    assert signed(credentials, secure=False).status_code == 401
    assert signed(credentials).status_code == 200
    revoke_agent(agent=EdgeAgent.objects.get())
    assert signed(credentials).status_code == 401


def test_hmac_keeps_scope_validation_and_retry_and_never_renews_certificate(pilot):
    credentials = enroll(pilot).json()
    scope = credentials["sync_scope"]
    assert signed(credentials, "agent-v2-configuration-next").json()["sync_scope"] == scope
    row = {
        "source_id": "1|10|1",
        "company_code": "1",
        "occurred_on": "2026-09-12",
        "description": "Synthetic",
        "amount": "1.00",
        "direction": "C",
        "is_linked": False,
        "account_reference": "001:123",
    }
    payload = {"scope_revision": scope["revision"], "rows": [row]}
    route = "agent-v2-dominio-bank-entries"
    assert signed(credentials, route, payload).json()["created"] == 1
    assert signed(credentials, route, payload).json()["created"] == 0
    payload["rows"].append({**row, "source_id": "1|11|2"})
    assert signed(credentials, route, payload).status_code == 403
    assert DominioBankEntry.objects.count() == 1
    with patch("apps.intelligence.agent_v2._sign_csr", side_effect=AssertionError("CA unused")):
        assert signed(credentials, "agent-v2-renew", {"csr": "unused"}).status_code == 409
