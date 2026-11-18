"""The release 100 contingency can use immutable D-373 proofs without editing them."""

import hashlib
import zlib
from copy import deepcopy
from datetime import date
from importlib import import_module
from uuid import uuid4

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.urls import NoReverseMatch, reverse

from apps.audit.models import AuditEvent
from apps.hub.account_discovery_contract import digest
from apps.hub.account_discovery_review import discovery_source_identity
from apps.hub.ledger_requests import (
    LedgerRequestError,
    _stored_revision,
    discovery_mapping_month_allowed,
    ledger_request_context,
    request_ledger,
    validate_job_mapping,
)
from apps.hub.models import (
    ClientCompany,
    ReconciliationAccountDiscovery,
    ReconciliationCompanyDiscovery,
    ReconciliationDiscoveredChartAccount,
    ReconciliationDiscoverySourceBlock,
)
from apps.intelligence.models import NativeLedgerCollection
from apps.intelligence.native_ledger_contract import canonical_hash
from apps.organizations.models import Organization
from test_ledger_requests import context as context_fixture
from test_ledger_requests import native as native_fixture
from test_ledger_requests import save

context = context_fixture
native = native_fixture
pytestmark = pytest.mark.django_db


@pytest.fixture
def discovered(context):
    """Persist the same monthly proof shape that 02c13b0's confirmed account emits."""
    _, account, actor, _, _ = context
    mapping = save(context)
    batch = ReconciliationAccountDiscovery.objects.create(
        organization=account.organization,
        source_file_sha256="1" * 64,
        source_size_bytes=500,
        source_observed_at=mapping.reviewed_at,
        script_sha256="2" * 64,
        portfolio_file_sha256="3" * 64,
        company_codes_sha256="4" * 64,
        company_count=1,
        chart_account_count=1,
        source_metadata={"synthetic": True},
        source_data={"synthetic": True},
        provenance={"source_data_sha256": canonical_hash({"synthetic": True})},
        request_reference="Synthetic D-373 contingency fixture",
    )
    row = dict(
        chart_company_code=212,
        account_code=8,
        account_name_raw="Synthetic account",
        classification_raw="1.1.1",
        account_type_raw="A",
        account_status_raw="A",
        inactive_on_raw=None,
    )
    chart = ReconciliationDiscoveredChartAccount.objects.create(
        organization=account.organization,
        discovery=batch,
        chart_company_code=212,
        account_code=8,
        row=row,
        row_sha256=digest(row),
    )
    facts = {
        "company": {"company_code": 212},
        "observed_chart_usage": [{
            "company_code": 212, "chart_company_code": 212, "branch_code": 212,
            "year": 2026, "month": 9, "entry_count": 163,
        }],
    }
    coverage = ReconciliationCompanyDiscovery.objects.create(
        organization=account.organization,
        discovery=batch,
        company=account.company,
        source_company_code=212,
        coverage_state="catalogued",
        facts=facts,
        gaps=[],
        facts_sha256=digest({"facts": facts, "gaps": [], "state": "catalogued"}),
    )
    confirmation = {
        "month": "2026-09",
        "source_identity": discovery_source_identity(coverage, chart),
        "actor_id": str(actor.pk),
        "confirmed_at": mapping.reviewed_at.isoformat(),
    }
    mapping.provenance = {
        "kind": "discovered_account_review",
        "confirmations": [confirmation],
        "source_fields": ["name"],
        "confirmed_fields": ["bank_association_confirmed"],
        "period_scope": {"version": 1, "allowed_months": ["2026-09"], "branches": [212]},
    }
    mapping.revision = _stored_revision(mapping)
    mapping.save()
    return context, mapping, batch, coverage, chart


def queue(context, month=date(2026, 9, 1)):
    _, account, actor, _, _ = context
    return request_ledger(
        account=account,
        actor=actor,
        month=month,
        request_key=uuid4(),
        expected_mapping_revision=ledger_request_context(
            account=account, actor=actor
        )["mapping_revision"],
    )


def test_confirmed_month_queues_and_executes_without_mutating_discovery(discovered):
    context, mapping, batch, coverage, chart = discovered
    before = [
        type(row).objects.filter(pk=row.pk).values().get() for row in (batch, coverage, chart)
    ]
    job, created = queue(context)
    assert created and validate_job_mapping(job)
    assert discovery_mapping_month_allowed(context[1], mapping, "2026-09", deep=True)
    for row, original in zip((batch, coverage, chart), before, strict=True):
        assert type(row).objects.filter(pk=row.pk).values().get() == original


def test_unconfirmed_month_rejected_on_request_and_job_execution(discovered):
    context, _, _, _, _ = discovered
    job, _ = queue(context)
    before = (NativeLedgerCollection.objects.count(), AuditEvent.objects.count())
    with pytest.raises(LedgerRequestError, match="competência"):
        queue(context, date(2026, 10, 1))
    assert (NativeLedgerCollection.objects.count(), AuditEvent.objects.count()) == before
    changed = dict(job.scope, period_start="2026-10-01", period_end_exclusive="2026-11-01")
    # A valid scope hash must not conceal the missing monthly mapping proof.
    NativeLedgerCollection.objects.filter(pk=job.pk).update(
        scope=changed, scope_revision=canonical_hash(changed)
    )
    job.refresh_from_db()
    assert not validate_job_mapping(job)


@pytest.mark.parametrize("target,field,value", [
    ("batch", "source_data", '{"corrupted":true}'),
    ("batch", "source_metadata", '{"corrupted":true}'),
    ("chart", "row_sha256", "0" * 64),
    ("chart", "row", '{"corrupted":true}'),
    ("coverage", "facts_sha256", "0" * 64),
    ("coverage", "facts", '{"corrupted":true}'),
])
def test_corruption_rejects_new_and_queued_jobs(discovered, target, field, value):
    context, _, batch, coverage, chart = discovered
    job, _ = queue(context)
    row = {"batch": batch, "coverage": coverage, "chart": chart}[target]
    # Deliberately simulate out-of-band corruption, bypassing immutable ORM guards.
    sql = {
        ("batch", "source_data"): (
            'UPDATE "hub_reconciliationaccountdiscovery" SET source_data = %s WHERE id = %s'
        ),
        ("batch", "source_metadata"): (
            'UPDATE "hub_reconciliationaccountdiscovery" SET source_metadata = %s WHERE id = %s'
        ),
        ("chart", "row_sha256"): (
            'UPDATE "hub_reconciliationdiscoveredchartaccount" SET row_sha256 = %s WHERE id = %s'
        ),
        ("chart", "row"): (
            'UPDATE "hub_reconciliationdiscoveredchartaccount" SET row = %s WHERE id = %s'
        ),
        ("coverage", "facts_sha256"): (
            'UPDATE "hub_reconciliationcompanydiscovery" SET facts_sha256 = %s WHERE id = %s'
        ),
        ("coverage", "facts"): (
            'UPDATE "hub_reconciliationcompanydiscovery" SET facts = %s WHERE id = %s'
        ),
    }[(target, field)]
    with connection.cursor() as cursor:
        cursor.execute(sql, [value, row.pk.hex])
    with pytest.raises(LedgerRequestError):
        queue(context)
    assert not validate_job_mapping(job)


@pytest.mark.parametrize("kind", ["organization", "company", "chart", "missing_proof"])
def test_identity_and_foreign_scope_rejected_even_with_updated_mapping_hash(discovered, kind):
    context, mapping, _, _, _ = discovered
    job, _ = queue(context)
    if kind == "organization":
        mapping.account_identity["organization_id"] = str(uuid4())
    elif kind == "company":
        identity = mapping.provenance["confirmations"][0]["source_identity"]
        identity["company_discovery_id"] = str(uuid4())
    elif kind == "chart":
        mapping.provenance["confirmations"][0]["source_identity"]["chart_account_id"] = str(uuid4())
    else:
        mapping.provenance["confirmations"] = []
    mapping.revision = _stored_revision(mapping)
    mapping.save()
    assert not discovery_mapping_month_allowed(context[1], mapping, "2026-09", deep=True)
    with pytest.raises(LedgerRequestError):
        queue(context)
    assert not validate_job_mapping(job)


def test_generic_review_cannot_bypass_month_proof(discovered):
    context, mapping, _, _, _ = discovered
    before = (deepcopy(mapping.provenance), AuditEvent.objects.count())
    with pytest.raises(LedgerRequestError, match="ficha da descoberta"):
        save(context)
    mapping.refresh_from_db()
    assert (mapping.provenance, AuditEvent.objects.count()) == before
    assert not discovery_mapping_month_allowed(context[1], mapping, "2026-10", deep=True)


def test_other_tenant_discovery_cannot_supply_monthly_proof(discovered):
    context, mapping, batch, coverage, chart = discovered
    other = Organization.objects.create(name="Other synthetic office", slug="other-proof")
    company = ClientCompany.objects.create(
        organization=other, name="Other synthetic company", dominio_code="212"
    )
    copies = []
    for row, overrides in (
        (batch, {}),
        (coverage, {"company": company}),
        (chart, {}),
    ):
        values = {
            field.name: getattr(row, field.name)
            for field in row._meta.concrete_fields
            if field.name not in {"id", "created_at", "updated_at", "organization", "discovery"}
        }
        values.update(organization=other, **overrides)
        if copies:
            values["discovery"] = copies[0]
        copies.append(type(row).objects.create(**values))
    _, other_coverage, other_chart = copies
    mapping.provenance["confirmations"][0]["source_identity"] = discovery_source_identity(
        other_coverage, other_chart
    )
    mapping.revision = _stored_revision(mapping)
    mapping.save()
    assert not discovery_mapping_month_allowed(context[1], mapping, "2026-09", deep=True)
    with pytest.raises(LedgerRequestError):
        queue(context)


@pytest.mark.parametrize("field", ["company_discovery_id", "chart_account_id", "discovery_id"])
def test_malformed_discovery_identity_fails_closed(discovered, field):
    context, mapping, _, _, _ = discovered
    mapping.provenance["confirmations"][0]["source_identity"][field] = "invalid-uuid"
    mapping.revision = _stored_revision(mapping)
    mapping.save()
    assert not discovery_mapping_month_allowed(context[1], mapping, "2026-09", deep=True)
    with pytest.raises(LedgerRequestError):
        queue(context)


def test_legacy_human_mapping_keeps_established_scope(context):
    mapping = save(context)
    assert discovery_mapping_month_allowed(context[1], mapping, "2026-10", deep=True)
    job, _ = queue(context, date(2026, 10, 1))
    assert validate_job_mapping(job)


def test_contingency_exposes_no_discovery_write_service_or_routes():
    module = import_module("apps.hub.account_discovery_review")
    assert not hasattr(module, "confirm_discovered_account")
    with pytest.raises(ModuleNotFoundError):
        import_module("apps.hub.account_discovery")
    for route in ("reconciliation_account_discovery", "reconciliation_discovered_account"):
        with pytest.raises(NoReverseMatch):
            reverse(f"hub:{route}")


def test_0088_models_remain_immutable(discovered):
    _, _, batch, coverage, chart = discovered
    for row in (batch, coverage, chart):
        with pytest.raises(ValidationError, match="Append-only"):
            type(row).objects.filter(pk=row.pk).delete()


def test_retained_source_block_validation_stays_bounded_and_immutable(discovered):
    _, _, batch, _, _ = discovered
    raw = b'{"synthetic":true}\n'
    block = ReconciliationDiscoverySourceBlock.objects.create(
        organization=batch.organization,
        discovery=batch,
        table_name="nature_rules",
        ordinal=0,
        row_count=1,
        raw_size_bytes=len(raw),
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        compressed_data=zlib.compress(raw),
    )
    with pytest.raises(ValidationError, match="Append-only"):
        ReconciliationDiscoverySourceBlock.objects.filter(pk=block.pk).update(row_count=2)
    original = ReconciliationDiscoverySourceBlock.objects.filter(pk=block.pk).values().get()
    block.compressed_data = zlib.compress(b"x" * (256 * 1024 + 1))
    block.raw_size_bytes = 256 * 1024 + 1
    with pytest.raises(ValidationError, match="Bloco"):
        block.full_clean()
    assert ReconciliationDiscoverySourceBlock.objects.filter(pk=block.pk).values().get() == original
