"""Reviewed portfolio batches are atomic, scoped and inert until explicitly applied."""

import json
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import StringIO
from threading import Barrier
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.exceptions import ObjectDoesNotExist
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import close_old_connections, connection
from django.test.utils import CaptureQueriesContext

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    JournalEntry,
    ProductModule,
    ReconciliationSourceFile,
)
from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
from apps.intelligence.native_ledger_contract import MAX_BYTES, pilot_scope
from apps.intelligence.portfolio_ledger import (
    MAX_ITEMS,
    VERSION,
    PortfolioBatchError,
    prepare_portfolio_ledger_batch,
)
from apps.organizations.models import Membership, Organization
from apps.platform.models import TenantContract

pytestmark = pytest.mark.django_db


@pytest.fixture
def batch(organization, user, membership):
    ProductModule.objects.create(
        organization=organization, code="reconciliation", enabled=True
    )
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"]
    )
    agent = EdgeAgent.objects.create(
        organization=organization,
        label="Agente sintético",
        fingerprint="batch-synthetic",
        shared_secret="batch-test-secret",
        is_official=True,
    )
    companies = [
        ClientCompany.objects.create(
            organization=organization, name=f"Sintética {code}", dominio_code=str(code)
        )
        for code in (314, 315)
    ]
    accounts = [
        FinancialAccount.objects.create(
            organization=organization,
            company=company,
            name="Banco sintético",
            ledger_code=str(bank),
            account_reference=f"synthetic:{company.dominio_code}:{bank}",
        )
        for company, bank in ((companies[0], 8), (companies[0], 21), (companies[1], 8))
    ]
    items = []
    for account, month in ((accounts[0], 9), (accounts[1], 9), (accounts[2], 9), (accounts[0], 10)):
        scope = dict(
            pilot_scope(),
            company_code=int(account.company.dominio_code),
            chart_company_code=77,
            branch_code=int(account.company.dominio_code),
            bank_account_code=int(account.ledger_code),
            period_start=f"2026-{month:02}-01",
            period_end_exclusive=f"2026-{month + 1:02}-01",
            expected_source_rows=1,
            expected_lots=1,
            expected_bank_effects=1,
        )
        items.append({
            "financial_account_id": str(account.pk),
            "scope": scope,
            "evidence_reference": "Referência privada sintética revisada",
        })
    return {
        "organization_id": str(organization.pk),
        "agent_id": str(agent.pk),
        "actor_id": str(user.pk),
        "manifest": {
            "version": VERSION,
            "organization_id": str(organization.pk),
            "agent_id": str(agent.pk),
            "items": items,
        },
    }


def database_state():
    return {
        "jobs": list(NativeLedgerCollection.objects.order_by("pk").values()),
        "audit": list(AuditEvent.objects.order_by("pk").values()),
        "accounts": list(FinancialAccount.objects.order_by("pk").values()),
        "sources": list(ReconciliationSourceFile.objects.order_by("pk").values()),
        "journals": list(JournalEntry.objects.order_by("pk").values()),
    }


def test_preflight_has_no_writes_including_audit_and_apply_coexists_then_replays(batch):
    before = database_state()
    with CaptureQueriesContext(connection) as queries:
        preview = prepare_portfolio_ledger_batch(**batch)
    assert not any(
        query["sql"].lstrip().upper().startswith(("INSERT", "UPDATE", "DELETE"))
        for query in queries.captured_queries
    )
    assert database_state() == before
    assert preview["dry_run"] and preview["valid"] and preview["created"] == 0
    assert preview["counts"] == {"ready": 4}
    assert not preview["automatic_recurrence_enabled"] and preview["requires_source_review"]
    applied = prepare_portfolio_ledger_batch(**batch, enqueue=True)
    assert not applied["dry_run"] and applied["created"] == 4
    assert applied["counts"] == {"queued": 4}
    assert NativeLedgerCollection.objects.count() == 4
    assert set(NativeLedgerCollection.objects.values_list("scope__company_code", flat=True)) == {
        314, 315,
    }
    assert set(NativeLedgerCollection.objects.values_list("scope__period_start", flat=True)) == {
        "2026-09-01", "2026-10-01",
    }
    assert set(NativeLedgerCollection.objects.values_list("financial_account_id", flat=True)) == {
        account.pk for account in FinancialAccount.objects.all()
    }
    events = AuditEvent.objects.filter(action="intelligence.portfolio_ledger_requested")
    assert events.count() == 4
    assert all(event.metadata["batch_revision"] == preview["manifest_revision"] for event in events)
    assert all(str(event.actor_id) == batch["actor_id"] for event in events)
    assert not JournalEntry.objects.exists() and not ReconciliationSourceFile.objects.exists()
    after = database_state()
    assert prepare_portfolio_ledger_batch(**batch)["counts"] == {"queued": 4}
    replay = prepare_portfolio_ledger_batch(**batch, enqueue=True)
    assert replay["created"] == 0 and replay["counts"] == {"queued": 4}
    assert database_state() == after


@pytest.mark.parametrize("invalid", ["account_missing", "scope_mismatch", "evidence_missing"])
def test_invalid_item_blocks_whole_batch_without_partial_inserts(batch, invalid):
    item = batch["manifest"]["items"][-1]
    if invalid == "account_missing":
        item["financial_account_id"] = str(uuid4())
    elif invalid == "scope_mismatch":
        item["scope"]["company_code"] = 999
    else:
        item["evidence_reference"] = "   "
    before = database_state()
    preview = prepare_portfolio_ledger_batch(**batch)
    assert not preview["valid"] and preview["counts"] == {"ready": 3, "invalid": 1}
    with pytest.raises(PortfolioBatchError) as raised:
        prepare_portfolio_ledger_batch(**batch, enqueue=True)
    assert raised.value.report["created"] == 0
    assert database_state() == before


@pytest.mark.parametrize("state", ["imported", "review", "failed"])
def test_existing_terminal_state_actor_and_evidence_are_preserved(batch, state):
    report = prepare_portfolio_ledger_batch(**batch, enqueue=True)
    job = NativeLedgerCollection.objects.get(pk=report["items"][0]["job_id"])
    job.state = state
    job.error_code = "retained-synthetic-code"
    job.result = {"created": 0, "source_rows": 1}
    job.save(update_fields=["state", "error_code", "result"])
    batch["manifest"]["items"][0]["evidence_reference"] = "Outro texto não substitui a revisão"
    before = database_state()
    replay = prepare_portfolio_ledger_batch(**batch, enqueue=True)
    assert replay["items"][0]["state"] == state and replay["created"] == 0
    assert database_state() == before


def test_duplicate_account_month_and_existing_conflicting_revision_require_review(batch):
    batch["manifest"]["items"].append(deepcopy(batch["manifest"]["items"][0]))
    before = database_state()
    preview = prepare_portfolio_ledger_batch(**batch)
    assert preview["items"][-1]["issues"] == ["duplicate_account_month"]
    with pytest.raises(PortfolioBatchError):
        prepare_portfolio_ledger_batch(**batch, enqueue=True)
    assert database_state() == before
    batch["manifest"]["items"].pop()
    prepare_portfolio_ledger_batch(**batch, enqueue=True)
    batch["manifest"]["items"][0]["scope"]["bank_inflow_side"] = "credit"
    before = database_state()
    preview = prepare_portfolio_ledger_batch(**batch)
    assert preview["items"][0]["issues"] == ["existing_scope_conflict"]
    with pytest.raises(PortfolioBatchError):
        prepare_portfolio_ledger_batch(**batch, enqueue=True)
    assert database_state() == before


def test_previously_authorized_job_cannot_be_adopted_by_a_different_actor(batch):
    prepare_portfolio_ledger_batch(**batch, enqueue=True)
    replacement = User.objects.create_user("replacement@batch.test", "synthetic-password")
    Membership.objects.create(
        organization_id=batch["organization_id"], user=replacement, role="owner"
    )
    Membership.objects.filter(user_id=batch["actor_id"]).update(is_active=False)
    batch["actor_id"] = str(replacement.pk)
    before = database_state()
    preview = prepare_portfolio_ledger_batch(**batch)
    assert not preview["valid"]
    assert all(item["issues"] == ["existing_job_requires_review"] for item in preview["items"])
    with pytest.raises(PortfolioBatchError):
        prepare_portfolio_ledger_batch(**batch, enqueue=True)
    assert database_state() == before


@pytest.mark.parametrize("revoked", ["membership", "contract", "account"])
def test_current_authorization_is_rechecked_at_apply(batch, revoked):
    assert prepare_portfolio_ledger_batch(**batch)["valid"]
    if revoked == "membership":
        Membership.objects.filter(user_id=batch["actor_id"]).update(is_active=False)
    elif revoked == "contract":
        TenantContract.objects.filter(organization_id=batch["organization_id"]).update(
            status="canceled"
        )
    else:
        FinancialAccount.objects.filter(
            pk=batch["manifest"]["items"][0]["financial_account_id"]
        ).update(active=False)
    before = database_state()
    with pytest.raises(PortfolioBatchError):
        prepare_portfolio_ledger_batch(**batch, enqueue=True)
    assert database_state() == before


def test_operator_requires_grants_for_each_company_and_auditor_cannot_apply(batch):
    membership = Membership.objects.get(user_id=batch["actor_id"])
    membership.role = "operator"
    membership.save(update_fields=["role"])
    account = FinancialAccount.objects.get(pk=batch["manifest"]["items"][0]["financial_account_id"])
    CompanyAccessGrant.objects.create(
        organization_id=batch["organization_id"], membership=membership, company=account.company,
        modules=["reconciliation"], capabilities=["bank_statements", "accounting_entries"],
    )
    before = database_state()
    preview = prepare_portfolio_ledger_batch(**batch)
    assert preview["counts"] == {"ready": 3, "invalid": 1}
    with pytest.raises(PortfolioBatchError):
        prepare_portfolio_ledger_batch(**batch, enqueue=True)
    assert database_state() == before
    membership.role = "auditor"
    membership.save(update_fields=["role"])
    assert prepare_portfolio_ledger_batch(**batch)["counts"] == {"invalid": 4}


def test_cross_organization_account_and_agent_are_refused_without_metadata_leak(batch):
    outsider = Organization.objects.create(name="Escritório privado", slug="batch-outsider")
    company = ClientCompany.objects.create(
        organization=outsider, name="Nome confidencial sintético", dominio_code="314"
    )
    account = FinancialAccount.objects.create(
        organization=outsider, company=company, name="Privado", ledger_code="8",
        account_reference="private-reference-marker",
    )
    manifest = deepcopy(batch["manifest"])
    manifest["items"][0]["financial_account_id"] = str(account.pk)
    before = database_state()
    preview = prepare_portfolio_ledger_batch(**{**batch, "manifest": manifest})
    assert preview["items"][0] == {
        "item": 1, "state": "invalid", "issues": ["access_account_scope_or_evidence_invalid"],
    }
    assert "private-reference-marker" not in json.dumps(preview)
    with pytest.raises(PortfolioBatchError):
        prepare_portfolio_ledger_batch(**{**batch, "manifest": manifest}, enqueue=True)
    other_agent = EdgeAgent.objects.create(
        organization=outsider, label="Outro agente", fingerprint="other-batch",
        shared_secret="other-synthetic-secret", is_official=True,
    )
    manifest["agent_id"] = str(other_agent.pk)
    with pytest.raises(ObjectDoesNotExist):
        prepare_portfolio_ledger_batch(
            **{**batch, "agent_id": str(other_agent.pk), "manifest": manifest}, enqueue=True
        )
    assert database_state() == before


def test_audit_failure_rolls_back_prior_jobs_and_events(batch):
    from apps.intelligence import portfolio_ledger

    record = portfolio_ledger.record_event
    count = 0

    def record_or_fail(**kwargs):
        nonlocal count
        count += 1
        if count == 2:
            raise RuntimeError("synthetic audit interruption")
        return record(**kwargs)

    before = database_state()
    with (
        patch.object(portfolio_ledger, "record_event", side_effect=record_or_fail),
        pytest.raises(RuntimeError, match="synthetic audit interruption"),
    ):
        prepare_portfolio_ledger_batch(**batch, enqueue=True)
    assert database_state() == before


def command_options(batch, tmp_path):
    path = tmp_path / "batch.json"
    path.write_text(json.dumps(batch["manifest"]), encoding="utf-8")
    return {
        "organization": batch["organization_id"],
        "agent": batch["agent_id"],
        "actor": batch["actor_id"],
        "manifest_file": str(path),
    }, path


def test_cli_defaults_to_preflight_and_applies_only_explicitly(batch, tmp_path):
    options, _ = command_options(batch, tmp_path)
    before = database_state()
    output = StringIO()
    call_command("queue_portfolio_ledger_batch", **options, stdout=output)
    assert json.loads(output.getvalue())["counts"] == {"ready": 4}
    assert database_state() == before
    output = StringIO()
    call_command(
        "queue_portfolio_ledger_batch", **options, allow_financial_capture=True, stdout=output
    )
    assert json.loads(output.getvalue())["created"] == 4


@pytest.mark.parametrize("apply", [False, True])
def test_cli_reports_invalid_item_with_nonzero_failure_and_no_writes(batch, tmp_path, apply):
    batch["manifest"]["items"][-1]["evidence_reference"] = ""
    options, _ = command_options(batch, tmp_path)
    before = database_state()
    output = StringIO()
    with pytest.raises(CommandError):
        call_command(
            "queue_portfolio_ledger_batch", **options,
            allow_financial_capture=apply, stdout=output,
        )
    report = json.loads(output.getvalue())
    assert not report["valid"] and report["created"] == 0
    assert database_state() == before


@pytest.mark.parametrize("failure", ["missing", "malformed", "duplicate_json", "oversize"])
def test_cli_unreadable_or_ambiguous_json_is_safe(batch, tmp_path, failure):
    options, path = command_options(batch, tmp_path)
    if failure == "missing":
        path.unlink()
    elif failure == "malformed":
        path.write_bytes(b"\xffprivate-data-marker")
    elif failure == "duplicate_json":
        path.write_text('{"version":"private-data-marker","version":"duplicate"}')
    else:
        path.write_bytes(b" " * (MAX_BYTES + 1))
    before = database_state()
    output = StringIO()
    with pytest.raises(CommandError) as raised:
        call_command("queue_portfolio_ledger_batch", **options, stdout=output)
    assert "private-data-marker" not in str(raised.value) + output.getvalue()
    assert database_state() == before


@pytest.mark.parametrize("failure", ["wrong_org", "wrong_agent", "version", "empty", "too_many"])
def test_manifest_envelope_never_changes_or_expands_scope(batch, failure):
    manifest = batch["manifest"]
    if failure == "wrong_org":
        manifest["organization_id"] = str(uuid4())
    elif failure == "wrong_agent":
        manifest["agent_id"] = str(uuid4())
    elif failure == "version":
        manifest["version"] = "unrecognized"
    elif failure == "empty":
        manifest["items"] = []
    else:
        manifest["items"] = [manifest["items"][0]] * (MAX_ITEMS + 1)
    before = database_state()
    with pytest.raises(ValueError, match="Manifesto"):
        prepare_portfolio_ledger_batch(**batch, enqueue=True)
    assert database_state() == before


@pytest.mark.django_db(transaction=True)
def test_concurrent_batch_replay_creates_one_set_and_audit(batch):
    if connection.vendor != "postgresql":
        pytest.skip("Portfolio batch serialization requires PostgreSQL row locks.")
    ready = Barrier(2)

    def apply():
        close_old_connections()
        try:
            ready.wait(timeout=10)
            return prepare_portfolio_ledger_batch(**batch, enqueue=True)["created"]
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _: apply(), range(2)))
    assert sorted(results) == [0, 4]
    assert NativeLedgerCollection.objects.count() == 4
    assert AuditEvent.objects.filter(action="intelligence.portfolio_ledger_requested").count() == 4
