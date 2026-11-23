"""Operator diagnostics expose bounded coverage and no source identities/secrets."""

from __future__ import annotations

import io
import json
from datetime import timedelta

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection, transaction
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.intelligence.models import AgentCompanyScan, EdgeAgent
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db(transaction=True)


def report(organization, **kwargs):
    output = io.StringIO()
    call_command(
        "portfolio_sync_status", organization=str(organization.pk), stdout=output, **kwargs
    )
    return output.getvalue()


def test_pilot_without_scan_reports_stale_heartbeat_without_claiming_portfolio_coverage(
    organization,
):
    agent = EdgeAgent.objects.create(
        organization=organization,
        label="Do not print identity",
        shared_secret="never print secret",
        fingerprint="private-device",
        last_seen_at=timezone.now() - timedelta(hours=1),
        sync_scope={"version": "dominio-pilot-v1", "account_reference": "private-account"},
    )
    with CaptureQueriesContext(connection) as queries:
        text = report(organization)
    value = json.loads(text)
    assert value["read_only"] and value["coverage_kind"] == "keyset_scan_not_erp_snapshot"
    row = value["agents"][0]
    assert row["agent_id"] == str(agent.pk) and row["scope_version"] == "dominio-pilot-v1"
    assert row["heartbeat_age_seconds"] >= 3600 and row["scans"] == []
    assert row["total_scans"] == 0
    for secret in (
        "Do not print identity",
        "never print secret",
        "private-device",
        "private-account",
    ):
        assert secret not in text
    sql = "\n".join(query["sql"] for query in queries.captured_queries)
    for forbidden in (
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        '"shared_secret"',
        '"label"',
        '"fingerprint"',
    ):
        assert forbidden not in sql


def test_scan_history_is_bounded_and_reports_failures_and_completion(organization):
    agent = EdgeAgent.objects.create(
        organization=organization,
        label="Synthetic",
        shared_secret="secret",
        fingerprint="local",
        sync_scope={"version": "dominio-portfolio-v1"},
    )
    for revision in range(3):
        AgentCompanyScan.objects.create(
            organization=organization,
            agent=agent,
            scope_revision=str(revision) * 64,
            expected_count=1000,
            received_count=500,
            page_count=1,
            aborted_at=timezone.now(),
            last_error_at=timezone.now(),
            last_error_code="coverage_mismatch",
        )
    row = json.loads(report(organization, limit=2))["agents"][0]
    assert row["heartbeat_age_seconds"] is None
    assert row["total_scans"] == 3 and row["older_scans_omitted"] == 1
    assert len(row["scans"]) == 2
    assert all(
        scan["state"] == "aborted" and scan["last_error_code"] == "coverage_mismatch"
        for scan in row["scans"]
    )
    scan = AgentCompanyScan.objects.create(
        organization=organization,
        agent=agent,
        scope_revision="f" * 64,
        expected_count=0,
        completed_at=timezone.now(),
    )
    last = json.loads(report(organization, limit=1))["agents"][0]["scans"][0]
    assert last["id"] == str(scan.pk) and last["state"] == "completed"


def test_different_office_agent_is_never_returned_even_with_explicit_id(organization):
    other = Organization.objects.create(name="Other", slug="other")
    agent = EdgeAgent.objects.create(
        organization=other, label="Other", shared_secret="secret", fingerprint="other"
    )
    assert json.loads(report(organization))["agents"] == []
    with pytest.raises(CommandError, match="neste escritório"):
        report(organization, agent=str(agent.pk))


@pytest.mark.parametrize("limit", [0, 101, -1])
def test_invalid_limits_are_rejected_before_database_access(organization, limit):
    with CaptureQueriesContext(connection) as queries, pytest.raises(CommandError, match="--limit"):
        report(organization, limit=limit)
    assert not queries.captured_queries


def test_invalid_agent_id_and_unknown_office_are_rejected(organization):
    with pytest.raises(CommandError, match="inválido"):
        report(organization, agent="bad")
    with pytest.raises(CommandError, match="Escritório não encontrado"):
        call_command("portfolio_sync_status", organization="not-an-office")


def test_nested_transaction_is_refused_without_changing_the_callers_transaction(organization):
    with transaction.atomic():
        with pytest.raises(CommandError, match="fora de uma transação"):
            report(organization)
        organization.name = "Caller can still write"
        organization.save(update_fields=["name"])
    organization.refresh_from_db()
    assert organization.name == "Caller can still write"
