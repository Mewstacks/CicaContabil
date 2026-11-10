"""Explicit scope changes preserve credentials/data and serialize with ingestion."""

from __future__ import annotations

import hashlib
import hmac
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from io import StringIO
from threading import Event
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections, connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.hub.models import ClientCompany, DominioBankEntry, FinancialAccount
from apps.intelligence.agent_scope import PORTFOLIO_VERSION, build_sync_scope
from apps.intelligence.agents import issue_enrollment, revoke_agent
from apps.intelligence.models import AgentCompanyScan, EdgeAgent
from apps.intelligence.portfolio_configuration import (
    ACTION,
    INVENTORY_LIMIT,
    configure_portfolio,
    reviewed_inventory,
)
from apps.organizations.models import Membership

pytestmark = pytest.mark.django_db


def raw(value):
    return json.dumps(value, sort_keys=True).encode()


@pytest.fixture
def prepared(organization, user):
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    company = ClientCompany.objects.create(
        organization=organization, name="Preserved synthetic company", dominio_code="1"
    )
    account = FinancialAccount.objects.create(
        organization=organization, company=company, name="Synthetic", account_reference="001:123"
    )
    scope = build_sync_scope(
        account=account, start=date(2026, 9, 1), end=date(2026, 9, 30), statement_ids=["10"]
    )
    agent = EdgeAgent.objects.create(
        organization=organization,
        label="Synthetic official",
        fingerprint="synthetic-host",
        shared_secret="synthetic-secret-preserved",
        sync_scope=scope,
        is_official=True,
        last_seen_at=timezone.now(),
    )
    inventory = {
        "version": "contad-schema-inventory-v1",
        "observed_at_utc": timezone.now().isoformat(),
        "financial_period_start": "2026-09-01",
        "objects": [
            {
                "schema": "bethadba",
                "name": "GEEMPRE",
                "kind": "TABLE",
                "columns": [
                    {"name": name, "type": "varchar", "ordinal": i + 1}
                    for i, name in enumerate(["CODI_EMP", "NOME_EMP", "CGCE_EMP", "STAT_EMP"])
                ],
            }
        ],
        "object_count": 1,
        "column_count": 4,
        "company_count": 503,
        "company_status_counts": [
            {"source_status": "A", "count": 501},
            {"source_status": "I", "count": 2},
        ],
        "status_mapping_approved": False,
        "keys_relations_and_financial_semantics_verified": False,
    }
    review = {
        "version": "contad-company-status-review-v1",
        "organization_id": str(organization.pk),
        "agent_id": str(agent.pk),
        "reviewer_id": str(user.pk),
        "review_reference": "synthetic-review-1",
        "agent_version": "1.0.5",
        "inventory_sha256": hashlib.sha256(raw(inventory)).hexdigest(),
        "company_status_map": {"A": True, "I": False},  # Synthetic; no ERP semantics inferred.
    }
    return agent, inventory, review


def configure(prepared, *, apply=False, **changes):
    agent, inventory, review = prepared
    return configure_portfolio(
        **{
            "organization": agent.organization,
            "agent_id": agent.pk,
            "expected_revision": agent.sync_scope["revision"],
            "inventory_raw": raw(inventory),
            "review_raw": raw(review),
            "period_end": date(2026, 10, 31),
            "apply": apply,
            **changes,
        }
    )


def test_preview_is_read_only_does_not_read_secret_and_explains_financial_pause(prepared):
    agent, _, _ = prepared
    old = agent.sync_scope
    audits = AuditEvent.objects.count()
    with CaptureQueriesContext(connection) as queries:
        result = configure(prepared)
    assert not result["applied"] and not result["financial_collection_enabled"]
    assert result["datasets"] == ["companies"] and result["observed_company_count"] == 503
    assert all("shared_secret" not in q["sql"] for q in queries)
    agent.refresh_from_db()
    assert agent.sync_scope == old and AuditEvent.objects.count() == audits


def test_apply_and_replay_preserve_identity_history_and_audit_once(prepared):
    agent, _, review = prepared
    old_scope = agent.sync_scope
    expected = configure(prepared)
    changed = configure(prepared, apply=True)
    assert changed["scope_revision"] == expected["scope_revision"]
    agent.refresh_from_db()
    assert agent.sync_scope["version"] == PORTFOLIO_VERSION
    assert agent.sync_scope["company_status_map"] == {"A": True, "I": False}
    assert agent.shared_secret == "synthetic-secret-preserved"
    assert agent.is_official and agent.status == "active"
    assert ClientCompany.objects.get().name == "Preserved synthetic company"
    assert FinancialAccount.objects.count() == 1 and not DominioBankEntry.objects.exists()
    assert not AgentCompanyScan.objects.exists()
    event = AuditEvent.objects.get(action=ACTION)
    assert event.actor_id == review["reviewer_id"] or str(event.actor_id) == review["reviewer_id"]
    assert event.metadata["previous_scope"] == old_scope
    # Retry uses the original expected revision, including an uncertain CLI result.
    retried = configure(prepared, apply=True, expected_revision=old_scope["revision"])
    assert retried["replayed"] and not retried["applied"]
    assert AuditEvent.objects.filter(action=ACTION).count() == 1


@pytest.mark.parametrize(
    "change",
    [
        {"company_count": 502},
        {"company_count": True},
        {"object_count": 2},
        {"column_count": 5},
        {"objects": []},
        {"status_mapping_approved": True},
        {"keys_relations_and_financial_semantics_verified": True},
        {"financial_period_start": "2025-01-01"},
        {"observed_at_utc": "2026-01-01T00:00:00Z"},
        {"observed_at_utc": "2026-11-10"},
        {"company_status_counts": [{"source_status": "A", "count": -1}]},
    ],
)
def test_inventory_incomplete_stale_or_incompatible_never_changes_scope(prepared, change):
    agent, inventory, review = prepared
    inventory.update(change)
    review["inventory_sha256"] = hashlib.sha256(raw(inventory)).hexdigest()
    with pytest.raises(ValueError):
        configure(prepared, apply=True)
    agent.refresh_from_db()
    assert agent.sync_scope["version"] != PORTFOLIO_VERSION
    assert not AuditEvent.objects.filter(action=ACTION).exists()


@pytest.mark.parametrize(
    "change",
    [
        {"organization_id": str(uuid4())},
        {"agent_id": str(uuid4())},
        {"inventory_sha256": "0" * 64},
        {"company_status_map": {"A": True}},
        {"company_status_map": {"A": True, "I": "false"}},
        {"reviewer_id": str(uuid4())},
        {"agent_version": "1.0.3"},
        {"review_reference": ""},
        {"unexpected": True},
    ],
)
def test_review_requires_exact_binding_coverage_and_compatible_version(prepared, change):
    prepared[2].update(change)
    with pytest.raises(ValueError):
        configure(prepared, apply=True)
    assert not AuditEvent.objects.filter(action=ACTION).exists()


@pytest.mark.parametrize(
    "change",
    [
        {"status": "revoked", "is_official": False},
        {"status": "pending", "is_official": False},
        {"is_official": False},
        {"last_seen_at": None},
        {"last_seen_at": timezone.now() - timedelta(minutes=6)},
        {"last_seen_at": timezone.now() + timedelta(minutes=6)},
    ],
)
def test_only_recent_official_can_change(prepared, change):
    EdgeAgent.objects.filter(pk=prepared[0].pk).update(**change)
    with pytest.raises(ValueError):
        configure(prepared, apply=True)


def test_stale_revision_pending_replacement_and_inactive_reviewer_refused(prepared):
    agent, _, _ = prepared
    with pytest.raises(ValueError, match="Revisão anterior"):
        configure(prepared, apply=True, expected_revision="0" * 64)
    enrollment = issue_enrollment(
        organization=agent.organization, sync_scope=agent.sync_scope, replaces_agent=agent
    )
    with pytest.raises(ValueError, match="substituição pendente"):
        configure(prepared, apply=True)
    from apps.intelligence.models import AgentEnrollment

    AgentEnrollment.objects.filter(
        code_digest=hashlib.sha256(enrollment.code.encode()).hexdigest()
    ).update(expires_at=timezone.now() - timedelta(seconds=1))
    Membership.objects.filter(organization=agent.organization).update(is_active=False)
    with pytest.raises(ValueError, match="dono/administrador"):
        configure(prepared, apply=True)


def test_atomic_rollback_if_audit_fails(prepared):
    with (
        patch("apps.intelligence.portfolio_configuration.record_event", side_effect=RuntimeError),
        pytest.raises(RuntimeError),
    ):
        configure(prepared, apply=True)
    prepared[0].refresh_from_db()
    assert prepared[0].sync_scope["version"] != PORTFOLIO_VERSION


def test_duplicate_json_and_oversized_input_rejected(prepared):
    with pytest.raises(ValueError):
        reviewed_inventory(b'{"version":1,"version":2}', raw(prepared[2]))
    with pytest.raises(ValueError):
        reviewed_inventory(b" " * (INVENTORY_LIMIT + 1), raw(prepared[2]))


@pytest.mark.parametrize("case", ["column", "object", "future", "unknown_status"])
def test_schema_ambiguity_future_and_unknown_status_never_enable_collection(prepared, case):
    _, inventory, review = prepared
    if case == "column":
        inventory["objects"][0]["columns"].pop()
        inventory["column_count"] -= 1
    elif case == "object":
        inventory["objects"].append(inventory["objects"][0])
        inventory["object_count"] = 2
        inventory["column_count"] = 8
    elif case == "future":
        inventory["observed_at_utc"] = (timezone.now() + timedelta(hours=1)).isoformat()
    else:
        inventory["company_status_counts"][0]["source_status"] = "UNKNOWN"
    review["inventory_sha256"] = hashlib.sha256(raw(inventory)).hexdigest()
    with pytest.raises(ValueError):
        configure(prepared, apply=True)


def test_command_previews_without_writing_and_hides_bad_file_contents(prepared, tmp_path):
    agent, inventory, review = prepared
    inventory_file, review_file = tmp_path / "inventory.json", tmp_path / "review.json"
    inventory_file.write_bytes(raw(inventory))
    review_file.write_bytes(raw(review))
    out = StringIO()
    args = {
        "organization": str(agent.organization_id),
        "agent": str(agent.pk),
        "inventory": str(inventory_file),
        "review": str(review_file),
        "expected_scope_revision": agent.sync_scope["revision"],
        "period_end": "2026-10-31",
    }
    call_command("configure_agent_portfolio", **args, stdout=out)
    assert not json.loads(out.getvalue())["applied"]
    assert "synthetic-secret" not in out.getvalue()
    assert not AuditEvent.objects.filter(action=ACTION).exists()
    inventory_file.write_text('{"secret":"never-echo-this" invalid}')
    with pytest.raises(CommandError) as caught:
        call_command("configure_agent_portfolio", **args, apply=True)
    assert "never-echo-this" not in str(caught.value)


@pytest.mark.django_db(transaction=True)
def test_concurrent_apply_is_idempotent(prepared):
    if connection.vendor != "postgresql":
        pytest.skip("Real row locking requires PostgreSQL.")

    def apply():
        close_old_connections()
        try:
            return configure(prepared, apply=True)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: apply(), range(2)))
    assert sum(row["applied"] for row in results) == 1
    assert sum(row["replayed"] for row in results) == 1
    assert AuditEvent.objects.filter(action=ACTION).count() == 1


@pytest.mark.django_db(transaction=True)
def test_revocation_waits_for_configuration_and_wins_without_reactivation(prepared):
    if connection.vendor != "postgresql":
        pytest.skip("Real row locking requires PostgreSQL.")
    entered, release, revoke_started = Event(), Event(), Event()
    from apps.intelligence.portfolio_configuration import record_event as original

    def wait_for_audit(**kwargs):
        entered.set()
        assert release.wait(15)
        return original(**kwargs)

    def apply():
        close_old_connections()
        try:
            return configure(prepared, apply=True)
        finally:
            close_old_connections()

    def revoke():
        close_old_connections()
        try:
            revoke_started.set()
            revoke_agent(agent=prepared[0])
        finally:
            close_old_connections()

    with (
        patch("apps.intelligence.portfolio_configuration.record_event", side_effect=wait_for_audit),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        applying = executor.submit(apply)
        assert entered.wait(15)
        revoking = executor.submit(revoke)
        assert revoke_started.wait(15)
        try:
            assert not revoking.done()
        finally:
            release.set()
        assert applying.result(timeout=15)["applied"]
        revoking.result(timeout=15)
    prepared[0].refresh_from_db()
    assert prepared[0].status == "revoked" and not prepared[0].is_official


@pytest.mark.django_db(transaction=True)
def test_transition_waits_for_inflight_bank_page_then_refuses_old_scope(prepared, settings):
    if connection.vendor != "postgresql":
        pytest.skip("Real row locking requires PostgreSQL.")
    settings.EDGE_AGENT_MTLS_REQUIRED = False
    agent = prepared[0]
    payload = {
        "scope_revision": agent.sync_scope["revision"],
        "rows": [
            {
                "source_id": "1|10|1",
                "company_code": "1",
                "occurred_on": "2026-09-12",
                "description": "Synthetic",
                "amount": "1.00",
                "direction": "C",
                "is_linked": False,
                "account_reference": "001:123",
            }
        ],
    }

    def send_page():
        body = raw(payload)
        timestamp = str(int(timezone.now().timestamp()))
        signature = hmac.new(
            agent.shared_secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
        ).hexdigest()
        return (
            Client()
            .post(
                reverse("agent-v2-dominio-bank-entries"),
                data=body,
                content_type="application/json",
                secure=True,
                headers={
                    "X-Hub-Agent-ID": str(agent.pk),
                    "X-Hub-Agent-Protocol": "scoped-v1",
                    "X-Hub-Agent-Timestamp": timestamp,
                    "X-Hub-Agent-Signature": signature,
                },
            )
            .status_code
        )

    from apps.intelligence.agent_v2 import sync_bank_entries as original

    entered, release, change_started = Event(), Event(), Event()

    def waiting_ingestion(**kwargs):
        entered.set()
        assert release.wait(15)
        return original(**kwargs)

    def ingest():
        close_old_connections()
        try:
            return send_page()
        finally:
            close_old_connections()

    def change():
        close_old_connections()
        try:
            change_started.set()
            return configure(prepared, apply=True)
        finally:
            close_old_connections()

    with (
        patch("apps.intelligence.agent_v2.sync_bank_entries", side_effect=waiting_ingestion),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        ingestion = executor.submit(ingest)
        assert entered.wait(15)
        changing = executor.submit(change)
        assert change_started.wait(15)
        try:
            assert not changing.done()
        finally:
            release.set()
        assert ingestion.result(timeout=15) == 200
        assert changing.result(timeout=15)["applied"]
    assert DominioBankEntry.objects.count() == 1
    assert send_page() in (400, 401, 403)
    assert DominioBankEntry.objects.count() == 1
