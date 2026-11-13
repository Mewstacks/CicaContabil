"""Synthetic expanded collections: shared chart, month, access revocation and replay."""

import io
import json
from copy import deepcopy

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.hub.models import IndependentLedgerRecord, JournalEntry, ProductModule
from apps.intelligence.models import NativeLedgerCollection
from apps.intelligence.native_ledger_contract import (
    canonical_hash,
    normalize_snapshot,
    validate_scope,
    validate_snapshot,
)
from apps.organizations.models import Membership
from apps.platform.models import TenantContract
from test_native_ledger import complete, post
from test_native_ledger import setup_native as native_fixture

native_source = native_fixture
pytestmark = pytest.mark.django_db


@pytest.fixture
def expanded(native_source, user, membership, tmp_path):
    agent, account, legacy, data = native_source
    ProductModule.objects.create(
        organization=account.organization, code="reconciliation", enabled=True
    )
    TenantContract.objects.create(
        organization=account.organization, status="active", selected_modules=["reconciliation"]
    )
    account.company.dominio_code = "314"
    account.company.save()
    account.ledger_code = "21"
    account.save()
    scope = dict(
        legacy.scope,
        company_code=314,
        chart_company_code=77,
        branch_code=314,
        bank_account_code=21,
        period_start="2026-10-01",
        period_end_exclusive="2026-11-01",
    )
    for row in data["records"]:
        row.update(
            company_code=314, chart_company_code=77, branch_code=314, occurred_on="2026-10-03"
        )
        if row["debit_account_code"] == 8:
            row["debit_account_code"] = 21
    for row in data["accounts"]:
        row["company_code"] = 77
        if row["account_code"] == 8:
            row["account_code"] = 21
    data["scope_revision"] = canonical_hash(scope)
    path = tmp_path / "scope.json"
    path.write_text(json.dumps(scope))
    options = dict(
        organization=str(account.organization_id),
        agent=str(agent.pk),
        account=str(account.pk),
        actor=str(user.pk),
        scope_file=str(path),
        evidence="Synthetic reviewed chart/bank/month mapping",
    )
    return agent, account, data, scope, options


def test_expanded_preflight_never_queues_and_old_agent_never_receives_expanded_job(expanded):
    agent, _, _, _, options = expanded
    before = NativeLedgerCollection.objects.count()
    call_command("queue_portfolio_ledger", **options, stdout=io.StringIO())
    assert NativeLedgerCollection.objects.count() == before
    call_command(
        "queue_portfolio_ledger", **options, allow_financial_capture=True, stdout=io.StringIO()
    )
    # The stale legacy job belongs to an account whose company changed, and is refused.
    NativeLedgerCollection.objects.filter(requested_by__isnull=True).delete()
    assert post(agent, "agent-v2-ledger-next", {"version": "1.0.8"}).json()["job"] is None
    response = post(agent, "agent-v2-ledger-next", {"version": "1.0.8", "portfolio_scope": True})
    assert response.json()["job"]["scope"]["chart_company_code"] == 77


def test_another_company_shared_chart_month_and_bank_import_and_replay(expanded):
    agent, _, data, _, options = expanded
    call_command(
        "queue_portfolio_ledger", **options, allow_financial_capture=True, stdout=io.StringIO()
    )
    job = NativeLedgerCollection.objects.get(requested_by__isnull=False)
    result = complete(agent, job, data)
    assert result.status_code == 200, result.content
    assert result.json()["state"] == "imported"
    assert complete(agent, job, data).json() == result.json()
    assert JournalEntry.objects.count() == 163
    assert all(
        r.external_key.startswith("dominio:314:lote:")
        for r in IndependentLedgerRecord.objects.all()
    )
    assert all(r.source_reference["row_codes"] for r in IndependentLedgerRecord.objects.all())
    call_command(
        "queue_portfolio_ledger", **options, allow_financial_capture=True, stdout=io.StringIO()
    )
    assert NativeLedgerCollection.objects.filter(requested_by__isnull=False).count() == 1


def test_revocation_after_queue_blocks_both_delivery_and_receipt(expanded):
    agent, account, data, _, options = expanded
    call_command(
        "queue_portfolio_ledger", **options, allow_financial_capture=True, stdout=io.StringIO()
    )
    job = NativeLedgerCollection.objects.get(requested_by__isnull=False)
    Membership.objects.filter(organization_id=account.organization_id).update(is_active=False)
    assert complete(agent, job, data).status_code == 409
    assert not JournalEntry.objects.exists()
    with pytest.raises(CommandError):
        call_command("queue_portfolio_ledger", **options, allow_financial_capture=True)


def test_catalogue_must_belong_to_explicit_shared_chart(expanded):
    _, _, data, scope, _ = expanded
    validate_snapshot(json.dumps(data).encode(), scope)
    data["accounts"][0]["company_code"] = 314
    with pytest.raises(ValueError):
        validate_snapshot(json.dumps(data).encode(), scope)


@pytest.mark.parametrize(
    "field,value",
    [
        ("company_code", True),
        ("bank_account_code", -1),
        ("expected_lots", 50_001),
        ("expected_bank_effects", 162),
        ("period_start", "2026-08-01"),
        ("period_end_exclusive", "2026-12-01"),
        ("bank_inflow_side", "unknown"),
        ("bank_inflow_side", []),
    ],
)
def test_expanded_scope_still_refuses_unbounded_or_unproven_shapes(expanded, field, value):
    with pytest.raises(ValueError):
        validate_scope(dict(expanded[3], **{field: value}))


def test_explicit_zero_coverage_retains_empty_source_without_inventing_facts(expanded):
    scope = dict(expanded[3], expected_source_rows=0, expected_lots=0, expected_bank_effects=0)
    data = deepcopy(expanded[2])
    data.update(records=[], lots=[], accounts=[], scope_revision=canonical_hash(scope))
    validate_snapshot(json.dumps(data).encode(), scope)
    assert normalize_snapshot(data, scope).bank_effects == 0
