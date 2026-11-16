"""Automatic counts use complete fixed-query reads, never user-supplied totals."""

from copy import deepcopy
from datetime import date
from uuid import uuid4

import pytest

from apps.hub.ledger_requests import (
    ledger_request_context,
    request_ledger,
    save_ledger_mapping,
)
from apps.hub.models import (
    AccountingEntry,
    IndependentLedgerRecord,
    JournalEntry,
    JournalLine,
    ProductModule,
    ReconciliationLedgerMapping,
    ReconciliationSourceFile,
)
from apps.intelligence.models import NativeLedgerCollection
from apps.intelligence.native_ledger_contract import (
    AUTOMATIC_VERSION,
    COUNT_FIELDS,
    canonical_hash,
    is_automatic_scope,
    normalize_snapshot,
    snapshot_version,
    validate_scope,
    validate_snapshot,
)
from apps.platform.models import TenantContract
from test_native_ledger import complete, pilot_scope, post, snapshot
from test_native_ledger import setup_native as native_fixture
from test_native_titles import encode


def automatic_source(identifier=None):
    scope = {key: value for key, value in pilot_scope().items() if key not in COUNT_FIELDS}
    scope["capture_id"] = str(identifier or uuid4())
    data = snapshot(scope)
    data["version"] = AUTOMATIC_VERSION
    return scope, data


def test_automatic_counts_are_derived_without_changing_fixed_mapping_or_source():
    scope, data = automatic_source()
    original = deepcopy(data)
    assert is_automatic_scope(validate_scope(scope))
    assert snapshot_version(scope) == AUTOMATIC_VERSION
    assert not COUNT_FIELDS.intersection(scope)
    assert validate_snapshot(encode(data), scope) == original
    candidate = normalize_snapshot(data, scope)
    assert candidate.source_rows == 177 and candidate.journals == 163
    assert candidate.bank_effects == 163
    assert data == original and not COUNT_FIELDS.intersection(scope)


@pytest.mark.parametrize(
    "value", [None, True, 7, "", "not-a-uuid", "1" * 32, "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"]
)
def test_capture_identity_requires_canonical_uuid(value):
    scope, _ = automatic_source()
    scope["capture_id"] = value
    with pytest.raises(ValueError):
        validate_scope(scope)


@pytest.mark.parametrize("field", sorted(COUNT_FIELDS))
def test_automatic_scope_rejects_guessed_or_claimed_totals(field):
    scope, _ = automatic_source()
    scope[field] = 0
    with pytest.raises(ValueError):
        validate_scope(scope)


@pytest.mark.parametrize(
    "change",
    [
        "record_missing",
        "lot_missing",
        "lot_count",
        "foreign_company",
        "foreign_chart",
        "foreign_branch",
        "outside_month",
        "duplicate",
        "claimed_counts",
        "legacy_envelope",
        "other_capture",
    ],
)
def test_automatic_snapshot_still_requires_complete_scoped_rows(change):
    scope, data = automatic_source()
    if change == "record_missing":
        data["records"].pop()
    elif change == "lot_missing":
        data["lots"].pop()
    elif change == "lot_count":
        data["lots"][0]["row_count"] += 1
    elif change == "foreign_company":
        data["records"][0]["company_code"] = 999
    elif change == "foreign_chart":
        data["records"][0]["chart_company_code"] = 999
    elif change == "foreign_branch":
        data["records"][0]["branch_code"] = 999
    elif change == "outside_month":
        data["records"][0]["occurred_on"] = "2026-10-01"
    elif change == "duplicate":
        data["records"][-1] = deepcopy(data["records"][0])
    elif change == "claimed_counts":
        data["expected_source_rows"] = 177
    elif change == "legacy_envelope":
        data["version"] = "dominio-ledger-snapshot-v1"
    else:
        scope["capture_id"] = str(uuid4())
    with pytest.raises(ValueError):
        validate_snapshot(encode(data), scope)


def test_explicit_empty_month_is_not_fabricated_into_financial_records():
    scope, data = automatic_source()
    data.update(records=[], lots=[], accounts=[])
    validate_snapshot(encode(data), scope)
    candidate = normalize_snapshot(data, scope)
    assert candidate.parties == () and candidate.source_rows == candidate.bank_effects == 0


def test_request_uuid_changes_revision_but_not_ledger_mapping_or_record_identity():
    first, data = automatic_source()
    second = {**first, "capture_id": str(uuid4())}
    assert canonical_hash(first) != canonical_hash(second)
    first_candidate = normalize_snapshot(data, first)
    data["scope_revision"] = canonical_hash(second)
    validate_snapshot(encode(data), second)
    assert normalize_snapshot(data, second) == first_candidate


native_source = native_fixture
AUTOMATIC_CAPABILITY = {
    "version": "1.0.8",
    "portfolio_scope": True,
    "automatic_counts": True,
}


@pytest.fixture
def automatic_request(native_source, user, membership):
    agent, account, legacy, _ = native_source
    ProductModule.objects.create(
        organization=account.organization, code="reconciliation", enabled=True
    )
    TenantContract.objects.create(
        organization=account.organization, status="active", selected_modules=["reconciliation"]
    )
    account.bank_code = "001"
    account.save(update_fields=["bank_code"])
    legacy.state = NativeLedgerCollection.State.FAILED
    legacy.save(update_fields=["state"])
    context = ledger_request_context(account=account, actor=user)
    save_ledger_mapping(
        account=account,
        actor=user,
        expected_revision=context["mapping_revision"],
        chart_company_code=212,
        branch_code=212,
        bank_inflow_side="debit",
        evidence_reference="Fonte sintética revisada",
        confirmed=True,
    )
    job = fresh_request(account, user)
    _, data = automatic_source(job.pk)
    return agent, account, job, data


def fresh_request(account, user):
    context = ledger_request_context(account=account, actor=user)
    job, created = request_ledger(
        account=account,
        actor=user,
        month=date(2026, 9, 1),
        request_key=uuid4(),
        expected_mapping_revision=context["mapping_revision"],
    )
    assert created
    return job


def select_lots(data, keys):
    data = deepcopy(data)
    data["lots"] = [lot for lot in data["lots"] if lot["lot_code"] in keys]
    data["records"] = [row for row in data["records"] if row["lot_code"] in keys]
    used = {
        row[field]
        for row in data["records"]
        for field in ("debit_account_code", "credit_account_code")
    }
    data["accounts"] = [account for account in data["accounts"] if account["account_code"] in used]
    return data


def for_request(data, job):
    return {**deepcopy(data), "scope_revision": job.scope_revision}


def test_old_agents_never_receive_automatic_requests_and_delivery_is_recorded(automatic_request):
    agent, _, job, _ = automatic_request
    for capability in ({"version": "1.0.8"}, {"version": "1.0.8", "portfolio_scope": True}):
        response = post(agent, "agent-v2-ledger-next", capability)
        assert response.status_code == 200 and response.json()["job"] is None
        job.refresh_from_db()
        assert job.claimed_at is None
    response = post(agent, "agent-v2-ledger-next", AUTOMATIC_CAPABILITY)
    assert response.status_code == 200
    delivered = response.json()["job"]
    assert delivered["id"] == str(job.pk) and delivered["version"] == AUTOMATIC_VERSION
    assert delivered["scope"]["capture_id"] == str(job.pk)
    assert not COUNT_FIELDS.intersection(delivered["scope"])
    job.refresh_from_db()
    claimed = job.claimed_at
    assert claimed is not None
    agent.refresh_from_db()
    assert agent.ledger_capabilities == AUTOMATIC_CAPABILITY
    assert agent.ledger_capabilities_observed_at is not None
    assert post(agent, "agent-v2-ledger-next", AUTOMATIC_CAPABILITY).status_code == 200
    job.refresh_from_db()
    assert job.claimed_at == claimed


def test_counts_are_observed_and_same_receipt_replays_without_duplicate_facts(automatic_request):
    agent, account, job, data = automatic_request
    data = select_lots(data, {1, 8})
    response = complete(agent, job, data)
    assert response.status_code == 200, response.content
    assert response.json() == {
        "state": "imported",
        "result": {
            "created": 2,
            "ignored": 0,
            "journals": 2,
            "parties": 5,
            "source_rows": 4,
            "bank_effects": 2,
        },
    }
    assert complete(agent, job, data).json() == response.json()
    assert IndependentLedgerRecord.objects.filter(financial_account=account).count() == 2
    assert ReconciliationSourceFile.objects.count() == 1
    assert set(
        IndependentLedgerRecord.objects.values_list("source_reference__contract", flat=True)
    ) == {AUTOMATIC_VERSION}


def test_empty_month_imports_no_financial_facts(automatic_request):
    agent, _, job, data = automatic_request
    response = complete(agent, job, select_lots(data, set()))
    assert response.status_code == 200 and response.json()["state"] == "imported"
    assert response.json()["result"] == {
        "created": 0,
        "ignored": 0,
        "journals": 0,
        "parties": 0,
        "source_rows": 0,
        "bank_effects": 0,
    }
    assert not IndependentLedgerRecord.objects.exists()
    assert not JournalEntry.objects.exists() and not AccountingEntry.objects.exists()
    assert ReconciliationSourceFile.objects.count() == 1


def test_refresh_reuses_unchanged_facts_and_adds_only_new_lots(automatic_request, user):
    agent, account, job, data = automatic_request
    original = select_lots(data, {1, 8})
    assert complete(agent, job, original).json()["state"] == "imported"
    identities = list(
        IndependentLedgerRecord.objects.order_by("external_key").values_list(
            "pk", "fingerprint", "source_file_id", "entry_id", "accounting_entry_id"
        )
    )
    refresh = fresh_request(account, user)
    response = complete(agent, refresh, for_request(original, refresh))
    assert response.json()["result"]["created"] == 0
    assert response.json()["result"]["ignored"] == 2
    assert (
        list(
            IndependentLedgerRecord.objects.order_by("external_key").values_list(
                "pk", "fingerprint", "source_file_id", "entry_id", "accounting_entry_id"
            )
        )
        == identities
    )
    extension = fresh_request(account, user)
    response = complete(agent, extension, for_request(select_lots(data, {1, 8, 9}), extension))
    assert response.json()["state"] == "imported"
    assert response.json()["result"]["created"] == 1
    assert response.json()["result"]["ignored"] == 2
    assert IndependentLedgerRecord.objects.count() == 3
    assert ReconciliationSourceFile.objects.count() == 3


@pytest.mark.parametrize("change", ["changed", "removed", "empty"])
def test_refresh_never_replaces_or_drops_prior_facts(automatic_request, user, change):
    agent, account, job, data = automatic_request
    original = select_lots(data, {1, 8})
    assert complete(agent, job, original).json()["state"] == "imported"
    before = list(IndependentLedgerRecord.objects.order_by("id").values())
    before_lines = list(JournalLine.objects.order_by("id").values())
    refresh = fresh_request(account, user)
    changed = for_request(select_lots(data, {1, 8, 9}), refresh)
    if change == "changed":
        changed["records"][0]["history"] = "Fonte sintética alterada"
    else:
        changed = select_lots(changed, {8, 9} if change == "removed" else set())
    response = complete(agent, refresh, changed)
    assert response.status_code == 200 and response.json()["state"] == "review"
    refresh.refresh_from_db()
    assert refresh.error_code == (
        "ledger_content_conflict" if change == "changed" else "ledger_records_removed"
    )
    assert list(IndependentLedgerRecord.objects.order_by("id").values()) == before
    assert list(JournalLine.objects.order_by("id").values()) == before_lines
    assert ReconciliationSourceFile.objects.count() == 2
    assert complete(agent, refresh, changed).json() == response.json()


@pytest.mark.parametrize("change", ["capture", "mapping", "role", "module", "user"])
def test_revoked_or_changed_authority_blocks_delivery_and_receipt(
    automatic_request, membership, user, change
):
    agent, account, job, data = automatic_request
    if change == "capture":
        job.scope["capture_id"] = str(uuid4())
        job.scope_revision = canonical_hash(job.scope)
        job.save(update_fields=["scope", "scope_revision"])
        data["scope_revision"] = job.scope_revision
    elif change == "mapping":
        ReconciliationLedgerMapping.objects.filter(financial_account=account).update(
            evidence_reference="Alterada"
        )
    elif change == "role":
        membership.role = "auditor"
        membership.save(update_fields=["role"])
    elif change == "module":
        ProductModule.objects.filter(
            organization=account.organization, code="reconciliation"
        ).update(enabled=False)
    else:
        user.is_active = False
        user.save(update_fields=["is_active"])
    assert post(agent, "agent-v2-ledger-next", AUTOMATIC_CAPABILITY).status_code == 409
    assert complete(agent, job, data).status_code == 409
    assert not ReconciliationSourceFile.objects.exists()
    assert not IndependentLedgerRecord.objects.exists()


@pytest.mark.parametrize("change", ["missing", "tampered", "cross_account"])
def test_success_replay_requires_intact_scoped_private_source(automatic_request, change):
    agent, account, job, data = automatic_request
    assert complete(agent, job, data).json()["state"] == "imported"
    job.refresh_from_db()
    source = job.source_file
    if change == "missing":
        source.content.delete(save=False)
    elif change == "tampered":
        with source.content.open("wb") as stream:
            stream.write(b"changed synthetic bytes")
    else:
        ReconciliationSourceFile.objects.filter(pk=source.pk).update(financial_account=None)
    assert complete(agent, job, data).status_code == 409
    assert IndependentLedgerRecord.objects.filter(financial_account=account).count() == 163


def test_import_audit_failure_rolls_back_facts_and_private_file(
    automatic_request, monkeypatch, settings
):
    from pathlib import Path

    from apps.hub import native_ledger_import

    agent, _, job, data = automatic_request
    before = {path for path in Path(settings.MEDIA_ROOT).rglob("*") if path.is_file()}

    def fail(**kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(native_ledger_import, "record_event", fail)
    with pytest.raises(RuntimeError, match="synthetic audit failure"):
        complete(agent, job, data)
    job.refresh_from_db()
    assert job.state == "queued" and job.source_file is None
    assert not ReconciliationSourceFile.objects.exists()
    assert not JournalEntry.objects.exists() and not JournalLine.objects.exists()
    assert not AccountingEntry.objects.exists() and not IndependentLedgerRecord.objects.exists()
    assert {path for path in Path(settings.MEDIA_ROOT).rglob("*") if path.is_file()} == before


@pytest.mark.parametrize("change", ["missing", "tampered", "wrong_hash"])
def test_refresh_requires_original_record_source_to_remain_intact(automatic_request, user, change):
    agent, account, job, data = automatic_request
    original = select_lots(data, {1, 8})
    assert complete(agent, job, original).json()["state"] == "imported"
    job.refresh_from_db()
    source = job.source_file
    if change == "missing":
        source.content.delete(save=False)
    elif change == "tampered":
        with source.content.open("wb") as stream:
            stream.write(b"synthetic modified source")
    else:
        record = IndependentLedgerRecord.objects.first()
        record.source_reference["content_hash"] = "0" * 64
        record.save(update_fields=["source_reference"])
    before = list(IndependentLedgerRecord.objects.order_by("id").values())
    refresh = fresh_request(account, user)
    response = complete(agent, refresh, for_request(select_lots(data, {1, 8, 9}), refresh))
    assert response.status_code == 200 and response.json()["state"] == "review"
    refresh.refresh_from_db()
    assert refresh.error_code == "ledger_content_conflict"
    assert list(IndependentLedgerRecord.objects.order_by("id").values()) == before
    assert ReconciliationSourceFile.objects.count() == 2


@pytest.mark.django_db(transaction=True)
def test_concurrent_automatic_receipt_is_idempotent(automatic_request):
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("Automatic receipt serialization requires PostgreSQL row locks.")
    agent, _, job, data = automatic_request
    data = select_lots(data, {1, 8})

    def send():
        close_old_connections()
        try:
            response = complete(agent, job, data)
            return response.status_code, response.json()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: send(), range(2)))
    assert results[0] == results[1]
    assert results[0][0] == 200 and results[0][1]["state"] == "imported"
    assert IndependentLedgerRecord.objects.count() == 2
    assert ReconciliationSourceFile.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_concurrent_refreshes_never_remove_facts(automatic_request, user):
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("Automatic refresh serialization requires PostgreSQL row locks.")
    agent, account, job, data = automatic_request
    assert complete(agent, job, select_lots(data, {1})).json()["state"] == "imported"
    unchanged = fresh_request(account, user)
    extension = fresh_request(account, user)
    inputs = [
        (unchanged, for_request(select_lots(data, {1}), unchanged)),
        (extension, for_request(select_lots(data, {1, 8}), extension)),
    ]

    def send(item):
        close_old_connections()
        try:
            request_job, request_data = item
            response = complete(agent, request_job, request_data)
            return response.status_code, response.json()["state"]
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(send, inputs))
    assert results[0] in [(200, "imported"), (200, "review")]
    assert results[1] == (200, "imported")
    assert IndependentLedgerRecord.objects.count() == 2
    assert ReconciliationSourceFile.objects.count() == 3
