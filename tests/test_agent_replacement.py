"""D-324: staged host replacement, atomic cutover and unchanged financial scope."""

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
from django.db import IntegrityError, close_old_connections, connection, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.hub.models import ClientCompany, DominioBankEntry, FinancialAccount
from apps.intelligence.agent_scope import build_portfolio_scope, build_sync_scope
from apps.intelligence.agents import (
    activate_official_replacement,
    issue_enrollment,
    redeem_enrollment,
    revoke_agent,
)
from apps.intelligence.models import AgentCompanyScan, AgentEnrollment, EdgeAgent
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture(params=["pilot", "portfolio"])
def previous(organization, settings, request):
    settings.EDGE_AGENT_MTLS_REQUIRED = False
    company = ClientCompany.objects.create(
        organization=organization, name="Synthetic", dominio_code="1"
    )
    account = FinancialAccount.objects.create(
        organization=organization, company=company, name="Synthetic", account_reference="001:123"
    )
    scope = (
        build_sync_scope(
            account=account, start=date(2026, 9, 1), end=date(2026, 9, 30), statement_ids=["10"]
        )
        if request.param == "pilot"
        else build_portfolio_scope(
            organization=organization,
            start=date(2026, 9, 1),
            end=date(2026, 9, 30),
            company_status_map={"A": True},
        )
    )
    return EdgeAgent.objects.create(
        organization=organization,
        label="Old PC",
        fingerprint="old-host",
        shared_secret="old-host-test-secret",
        sync_scope=scope,
    )


def prepare(previous):
    return issue_enrollment(
        organization=previous.organization, sync_scope=previous.sync_scope, replaces_agent=previous
    )


def redeem(code, **changes):
    return redeem_enrollment(
        **{
            "code": code.code,
            "label": "New Server",
            "fingerprint": "new-host",
            "allow_scoped": True,
            "allow_portfolio": True,
            "allow_replacement": True,
            **changes,
        }
    )


def stage(previous):
    credentials = redeem(prepare(previous))
    return EdgeAgent.objects.get(pk=credentials.agent_id)


def post(agent, route, payload=None):
    body = json.dumps(payload or {}).encode()
    timestamp = str(int(timezone.now().timestamp()))
    signature = hmac.new(
        agent.shared_secret.encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return Client().post(
        reverse(route),
        data=body,
        content_type="application/json",
        secure=True,
        headers={
            "X-Hub-Agent-ID": str(agent.pk),
            "X-Hub-Agent-Timestamp": timestamp,
            "X-Hub-Agent-Signature": signature,
            "X-Hub-Agent-Protocol": "scoped-v2",
        },
    )


def activate(previous, candidate, **changes):
    return activate_official_replacement(
        **{
            "organization": previous.organization,
            "previous_id": str(previous.pk),
            "candidate_id": str(candidate.pk),
            "scope_revision": previous.sync_scope["revision"],
            **changes,
        }
    )


def test_staging_preserves_old_agent_and_only_allows_heartbeat_configuration(previous):
    candidate = stage(previous)
    assert candidate.status == EdgeAgent.Status.PENDING_ACTIVATION
    assert candidate.sync_scope == previous.sync_scope and not candidate.is_official
    assert candidate.shared_secret != previous.shared_secret
    assert post(previous, "agent-v2-heartbeat").status_code == 200
    assert post(candidate, "agent-v2-heartbeat").status_code == 200
    response = post(candidate, "agent-v2-configuration-next")
    assert response.json()["collection_enabled"] is False
    assert response.json()["sync_scope"] == previous.sync_scope
    for route in (
        "agent-v2-dominio-companies",
        "agent-v2-dominio-bank-entries",
        "agent-v2-dominio-portfolio-companies",
        "agent-v2-backup-next",
        "agent-v2-file-next",
        "agent-v2-renew",
        "intelligence-agent-sync",
    ):
        assert post(candidate, route).status_code == 401
    assert not AgentCompanyScan.objects.exists()
    assert not DominioBankEntry.objects.exists()


def test_cutover_revokes_old_and_retry_keeps_one_official_audit(previous):
    candidate = stage(previous)
    assert post(candidate, "agent-v2-heartbeat").status_code == 200
    result = activate(previous, candidate)
    assert result.is_official and result.status == EdgeAgent.Status.ACTIVE
    previous.refresh_from_db()
    assert previous.status == EdgeAgent.Status.REVOKED and previous.revoked_at
    assert post(previous, "agent-v2-heartbeat").status_code == 401
    assert post(candidate, "agent-v2-configuration-next").json()["collection_enabled"] is True
    assert activate(previous, candidate).pk == candidate.pk
    event = AuditEvent.objects.get(action="intelligence.agent.official_replaced")
    assert event.metadata["previous_agent_id"] == str(previous.pk)
    assert previous.shared_secret not in json.dumps(event.metadata)
    assert EdgeAgent.objects.filter(is_official=True).count() == 1
    assert ClientCompany.objects.count() == 1


@pytest.mark.parametrize("age", [None, -301, 600])
def test_missing_stale_or_future_heartbeat_refuses_cutover(previous, age):
    candidate = stage(previous)
    if age is not None:
        EdgeAgent.objects.filter(pk=candidate.pk).update(
            last_seen_at=timezone.now() + timedelta(seconds=age)
        )
    with pytest.raises(ValueError, match="heartbeat"):
        activate(previous, candidate)
    previous.refresh_from_db()
    assert previous.status == EdgeAgent.Status.ACTIVE


def test_failed_audit_rolls_back_both_statuses_and_official_flag(previous):
    candidate = stage(previous)
    post(candidate, "agent-v2-heartbeat")
    with (
        patch("apps.intelligence.agents.record_event", side_effect=RuntimeError("audit failure")),
        pytest.raises(RuntimeError),
    ):
        activate(previous, candidate)
    previous.refresh_from_db()
    candidate.refresh_from_db()
    assert previous.status == EdgeAgent.Status.ACTIVE and previous.revoked_at is None
    assert candidate.status == EdgeAgent.Status.PENDING_ACTIVATION and not candidate.is_official


def test_client_without_staging_support_and_same_host_do_not_consume_code(previous):
    code = prepare(previous)
    for changes in ({"allow_replacement": False}, {"fingerprint": previous.fingerprint}):
        with pytest.raises(ValueError):
            redeem(code, **changes)
        assert AgentEnrollment.objects.get().used_at is None
        assert EdgeAgent.objects.count() == 1
    redeem(code)
    with pytest.raises(ValueError):
        redeem(code)


def test_v2_replacement_header_is_required_before_consumption(previous):
    code = prepare(previous)
    payload = {
        "code": code.code,
        "label": "Server",
        "fingerprint": "new-host",
        "authentication_mode": "hmac",
    }
    client = Client()
    headers = {"X-Hub-Agent-Protocol": "scoped-v2"}
    assert (
        client.post(
            reverse("agent-v2-enroll"),
            data=json.dumps(payload),
            content_type="application/json",
            headers=headers,
            secure=True,
        ).status_code
        == 403
    )
    assert AgentEnrollment.objects.get().used_at is None
    headers["X-Hub-Agent-Replacement"] = "staged-v1"
    assert (
        client.post(
            reverse("agent-v2-enroll"),
            data=json.dumps(payload),
            content_type="application/json",
            headers=headers,
            secure=True,
        ).status_code
        == 200
    )
    assert (
        EdgeAgent.objects.get(replaces_agent=previous).status == EdgeAgent.Status.PENDING_ACTIVATION
    )


def test_scope_changes_revocation_and_foreign_office_are_refused(previous):
    candidate = stage(previous)
    post(candidate, "agent-v2-heartbeat")
    with pytest.raises(ValueError):
        activate(previous, candidate, scope_revision="0" * 64)
    other = Organization.objects.create(name="Other", slug="other")
    with pytest.raises(ValueError):
        activate(previous, candidate, organization=other)
    with pytest.raises(ValueError):
        activate(previous, candidate, previous_id=str(uuid4()))
    EdgeAgent.objects.filter(pk=previous.pk).update(sync_scope={})
    with pytest.raises(ValueError, match="Manifesto"):
        activate(previous, candidate)
    revoke_agent(agent=candidate)
    assert post(candidate, "agent-v2-heartbeat").status_code == 401


def test_changed_scope_or_revoked_predecessor_invalidates_unconsumed_code(previous):
    code = prepare(previous)
    EdgeAgent.objects.filter(pk=previous.pk).update(sync_scope={})
    with pytest.raises(ValueError):
        redeem(code)
    assert AgentEnrollment.objects.get().used_at is None
    EdgeAgent.objects.filter(pk=previous.pk).update(sync_scope=previous.sync_scope)
    revoke_agent(agent=previous)
    with pytest.raises(ValueError):
        redeem(code)
    assert AgentEnrollment.objects.get().used_at is None


def test_duplicate_preparation_and_foreign_previous_cannot_issue_more_codes(previous):
    prepare(previous)
    with pytest.raises(ValueError, match="Já existe"):
        prepare(previous)
    other = Organization.objects.create(name="Other", slug="other")
    with pytest.raises(ValueError):
        issue_enrollment(
            organization=other, sync_scope=previous.sync_scope, replaces_agent=previous
        )
    assert AgentEnrollment.objects.count() == 1


def test_official_constraints_and_explicit_revocation(previous):
    previous.is_official = True
    previous.save(update_fields=["is_official"])
    with transaction.atomic(), pytest.raises(IntegrityError):
        EdgeAgent.objects.create(
            organization=previous.organization,
            label="Duplicate",
            fingerprint="dup",
            shared_secret="synthetic-secret",
            is_official=True,
        )
    with transaction.atomic(), pytest.raises(IntegrityError):
        EdgeAgent.objects.filter(pk=previous.pk).update(status=EdgeAgent.Status.REVOKED)
    revoke_agent(agent=previous)
    previous.refresh_from_db()
    assert not previous.is_official and previous.status == EdgeAgent.Status.REVOKED


def test_cutover_of_an_existing_official_and_conflicting_official(previous):
    candidate = stage(previous)
    post(candidate, "agent-v2-heartbeat")
    conflict = EdgeAgent.objects.create(
        organization=previous.organization,
        label="Other active agent",
        fingerprint="other",
        shared_secret="synthetic-other-secret",
        is_official=True,
    )
    with pytest.raises(ValueError, match="Outro agente"):
        activate(previous, candidate)
    revoke_agent(agent=conflict)
    previous.is_official = True
    previous.save(update_fields=["is_official"])
    assert activate(previous, candidate).is_official
    previous.refresh_from_db()
    assert not previous.is_official and previous.status == EdgeAgent.Status.REVOKED
    assert post(conflict, "agent-v2-heartbeat").status_code == 401


def test_commands_use_private_code_file_and_require_exact_cutover(previous, tmp_path):
    output = StringIO()
    destination = tmp_path / "replacement.json"
    options = {"organization": str(previous.organization_id), "previous": str(previous.pk)}
    call_command("prepare_agent_replacement", **options, output=str(destination), stdout=output)
    document = json.loads(destination.read_text())
    assert destination.stat().st_mode & 0o777 == 0o600
    assert document["code"] not in output.getvalue()
    assert previous.shared_secret not in destination.read_text()
    credentials = redeem_enrollment(
        code=document["code"],
        label="Server",
        fingerprint="new-host",
        allow_scoped=True,
        allow_portfolio=True,
        allow_replacement=True,
    )
    candidate = EdgeAgent.objects.get(pk=credentials.agent_id)
    post(candidate, "agent-v2-heartbeat")
    call_command(
        "activate_official_agent",
        **options,
        candidate=str(candidate.pk),
        scope_revision=previous.sync_scope["revision"],
        stdout=output,
    )
    candidate.refresh_from_db()
    assert candidate.is_official


def test_existing_delivery_is_not_overwritten_and_code_is_rolled_back(previous, tmp_path):
    destination = tmp_path / "exists.json"
    destination.write_text("preserve")
    with pytest.raises(CommandError):
        call_command(
            "prepare_agent_replacement",
            organization=str(previous.organization_id),
            previous=str(previous.pk),
            output=str(destination),
        )
    assert destination.read_text() == "preserve" and not AgentEnrollment.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_replacement_preparation_issues_only_one_code(previous):
    if connection.vendor != "postgresql":
        pytest.skip("Enrollment serialization requires PostgreSQL")

    def issue(_):
        close_old_connections()
        try:
            prepare(previous)
            return "issued"
        except ValueError:
            return "refused"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(issue, range(2)))
    assert sorted(results) == ["issued", "refused"]
    assert AgentEnrollment.objects.count() == 1
    assert EdgeAgent.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_activation_is_idempotent(previous):
    if connection.vendor != "postgresql":
        pytest.skip("Cutover serialization requires PostgreSQL")
    candidate = stage(previous)
    post(candidate, "agent-v2-heartbeat")

    def cutover(_):
        close_old_connections()
        try:
            return activate(previous, candidate).pk
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(cutover, range(2)))
    assert results == [candidate.pk, candidate.pk]
    assert AuditEvent.objects.filter(action="intelligence.agent.official_replaced").count() == 1


@pytest.mark.django_db(transaction=True)
def test_cutover_waits_for_old_ingestion_and_rejects_it_afterwards(previous):
    if connection.vendor != "postgresql":
        pytest.skip("In-flight ingestion serialization requires PostgreSQL")
    portfolio = previous.sync_scope["version"] == "dominio-portfolio-v1"
    candidate = stage(previous)
    post(candidate, "agent-v2-heartbeat")
    entered, release, cutover_started = Event(), Event(), Event()
    from apps.intelligence import agent_v2
    from apps.intelligence import portfolio as portfolio_intake

    original = portfolio_intake.sync_companies if portfolio else agent_v2.sync_bank_entries

    def waiting_sync(**kwargs):
        entered.set()
        assert release.wait(10)
        return original(**kwargs)

    payload = {
        "scope_revision": previous.sync_scope["revision"],
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
    route = "agent-v2-dominio-bank-entries"
    target = "apps.intelligence.agent_v2.sync_bank_entries"
    if portfolio:
        route = "agent-v2-dominio-portfolio-companies"
        target = "apps.intelligence.portfolio.sync_companies"
        opened = post(
            previous,
            route,
            {
                "action": "open",
                "scope_revision": previous.sync_scope["revision"],
                "expected_count": 1,
            },
        ).json()
        payload = {
            "action": "page",
            "scope_revision": previous.sync_scope["revision"],
            "run_id": opened["run_id"],
            "after": "0",
            "complete": True,
            "source_count": 1,
            "rows": [{"codigo": "1", "nome": "Synthetic", "cnpj_masked": "", "status": "A"}],
        }

    def ingest():
        close_old_connections()
        try:
            return post(previous, route, payload).status_code
        finally:
            close_old_connections()

    def cutover():
        close_old_connections()
        try:
            cutover_started.set()
            return activate(previous, candidate).pk
        finally:
            close_old_connections()

    with (
        patch(target, side_effect=waiting_sync),
        ThreadPoolExecutor(max_workers=2) as executor,
    ):
        ingestion = executor.submit(ingest)
        assert entered.wait(10)
        replacement = executor.submit(cutover)
        assert cutover_started.wait(10)
        try:
            assert not replacement.done()
        finally:
            release.set()
        assert ingestion.result(timeout=10) == 200
        assert replacement.result(timeout=10) == candidate.pk
    assert post(previous, route, payload).status_code == 401
    if portfolio:
        scan = AgentCompanyScan.objects.get(pk=opened["run_id"])
        assert scan.agent_id == previous.pk and scan.completed_at is not None
        next_scan = post(
            candidate,
            route,
            {
                "action": "open",
                "scope_revision": candidate.sync_scope["revision"],
                "expected_count": 1,
            },
        ).json()
        assert next_scan["run_id"] != opened["run_id"] and next_scan["after"] == "0"
        payload["run_id"] = next_scan["run_id"]
        assert post(candidate, route, payload).status_code == 200
        assert ClientCompany.objects.count() == 1
        assert AgentCompanyScan.objects.filter(completed_at__isnull=False).count() == 2
    else:
        assert post(candidate, route, payload).json()["created"] == 0
        assert DominioBankEntry.objects.count() == 1
