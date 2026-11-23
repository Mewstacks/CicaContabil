"""Synthetic monthly self-service requests never infer mappings or financial counts."""

from datetime import date, timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.hub.ledger_requests import (
    LedgerRequestConflict,
    LedgerRequestError,
    ledger_job_context,
    ledger_request_context,
    request_ledger,
    retry_ledger_request,
    save_ledger_mapping,
    validate_job_mapping,
)
from apps.hub.models import (
    CompanyAccessGrant,
    FinancialAccount,
    ProductModule,
    ReconciliationLedgerMapping,
    ReconciliationSourceFile,
)
from apps.intelligence.models import NativeLedgerCollection
from apps.platform.models import TenantContract
from test_native_ledger import complete
from test_native_ledger import setup_native as native_fixture

native = native_fixture
pytestmark = pytest.mark.django_db


@pytest.fixture
def context(native, user, membership):
    agent, account, legacy, data = native
    account.bank_code = "001"
    account.save()
    ProductModule.objects.create(
        organization=account.organization, code="reconciliation", enabled=True
    )
    TenantContract.objects.create(
        organization=account.organization, status="active", selected_modules=["reconciliation"]
    )
    return agent, account, user, legacy, data


def read(context):
    _, account, actor, _, _ = context
    return ledger_request_context(account=account, actor=actor)


def save(context, **options):
    _, account, actor, _, _ = context
    values = dict(
        expected_revision=read(context)["mapping_revision"],
        chart_company_code=212,
        branch_code=212,
        bank_inflow_side="debit",
        evidence_reference="Fonte sintética",
        confirmed=True,
    )
    values.update(options)
    return save_ledger_mapping(account=account, actor=actor, **values)


def queue(context, **options):
    _, account, actor, _, _ = context
    values = dict(
        month=date(2026, 10, 1),
        request_key=uuid4(),
        expected_mapping_revision=read(context)["mapping_revision"],
    )
    values.update(options)
    return request_ledger(account=account, actor=actor, **values)


def counts():
    return tuple(
        model.objects.count()
        for model in (
            AuditEvent,
            NativeLedgerCollection,
            ReconciliationLedgerMapping,
            ReconciliationSourceFile,
        )
    )


def test_unreviewed_account_requires_mapping_get_is_readonly_and_never_infers_branch(context):
    before = counts()
    result = read(context)
    assert result["needs_mapping"] and not result["readiness"]
    assert result["mapping_fields"] == {
        "company_code": 212,
        "bank_account_code": 8,
        "absent_account_code": 0,
    }
    assert counts() == before
    with pytest.raises(LedgerRequestError, match="Confira o vínculo"):
        queue(context)
    assert counts() == before


def test_reviewed_monthly_request_nonce_replay_and_explicit_refresh_preserve_jobs(context):
    save(context)
    key = uuid4()
    first, created = queue(context, request_key=key)
    assert created and first.scope["capture_id"] == str(first.pk)
    assert not any(key.startswith("expected_") for key in first.scope)
    assert first.scope["period_start"] == "2026-10-01"
    assert first.scope["period_end_exclusive"] == "2026-11-01"
    before = counts()
    repeated, created = queue(context, request_key=key)
    assert repeated.pk == first.pk and not created and counts() == before
    fresh, created = queue(context)
    assert created and fresh.pk != first.pk and fresh.scope_revision != first.scope_revision
    assert validate_job_mapping(first) and validate_job_mapping(fresh)
    assert first.requested_by_id == context[2].pk


@pytest.mark.parametrize("month", [date(2026, 8, 1), date(2026, 9, 2), "2026-09", None])
def test_invalid_month_does_not_broaden_period_or_create_job(context, month):
    save(context)
    before = counts()
    with pytest.raises(LedgerRequestError):
        queue(context, month=month)
    assert counts() == before


@pytest.mark.parametrize(
    "change",
    [
        {"confirmed": False},
        {"confirmed": "true"},
        {"evidence_reference": ""},
        {"branch_code": "01"},
        {"chart_company_code": True},
        {"bank_inflow_side": ""},
    ],
)
def test_mapping_needs_literal_codes_human_evidence_and_explicit_check(context, change):
    before = counts()
    with pytest.raises(ValueError):
        save(context, **change)
    assert counts() == before


def test_changed_revision_blocks_old_page_and_pending_job_without_changing_history(context):
    original = save(context)
    old_revision = read(context)["mapping_revision"]
    job, _ = queue(context)
    changed = save(context, branch_code=99, evidence_reference="Filial conferida novamente")
    assert changed.pk == original.pk and len(changed.review_history) == 1
    assert changed.review_history[0]["scope"]["branch_code"] == 212
    assert not validate_job_mapping(job)
    result = ledger_job_context(job=job, actor=context[2])
    assert result["status"] == "review" and result["can_retry"]
    job.refresh_from_db()
    assert job.state == "queued" and job.scope["branch_code"] == 212
    before = counts()
    with pytest.raises(LedgerRequestConflict):
        queue(context, expected_mapping_revision=old_revision)
    with pytest.raises(LedgerRequestConflict):
        save(context, expected_revision=old_revision)
    assert counts() == before


def test_identity_changed_after_review_blocks_collection_and_allows_explicit_rereview(context):
    save(context)
    account = context[1]
    FinancialAccount.objects.filter(pk=account.pk).update(account_reference="corrigida")
    result = read(context)
    assert not result["readiness"] and result["needs_mapping"] and result["errors"]
    save(context)
    assert read(context)["readiness"]


def test_nonnumeric_ledger_code_gives_actionable_error_without_conversion(context):
    FinancialAccount.objects.filter(pk=context[1].pk).update(ledger_code="1.1.01")
    result = read(context)
    assert not result["readiness"] and "conta contábil" in result["errors"][0]
    with pytest.raises(LedgerRequestError, match="numérico"):
        save(context)


def test_mapping_and_request_roll_back_when_audit_fails(context, monkeypatch):
    fail = Mock(side_effect=RuntimeError("synthetic audit failure"))
    with monkeypatch.context() as patch:
        patch.setattr("apps.hub.ledger_requests.record_event", fail)
        with pytest.raises(RuntimeError):
            save(context)
    assert not ReconciliationLedgerMapping.objects.exists()
    save(context)
    before = counts()
    monkeypatch.setattr("apps.hub.ledger_requests.record_event", fail)
    with pytest.raises(RuntimeError):
        queue(context)
    assert counts() == before


def test_idempotency_key_cannot_be_reused_for_another_month_or_bank_source(context):
    save(context)
    key = uuid4()
    queue(context, request_key=key)
    with pytest.raises(LedgerRequestConflict):
        queue(context, request_key=key, month=date(2026, 11, 1))


@pytest.mark.parametrize("role", ["auditor", "operator"])
def test_read_and_write_apply_live_company_and_module_scope(context, membership, role):
    save(context)
    membership.role = role
    membership.save()
    grant = CompanyAccessGrant.objects.create(
        organization=context[1].organization,
        membership=membership,
        company=context[1].company,
        modules=["reconciliation"],
    )
    assert read(context)["readiness"]
    if role == "auditor":
        with pytest.raises(PermissionDenied):
            queue(context)
        with pytest.raises(PermissionDenied):
            save(context)
    else:
        queue(context)
    grant.modules = ["payroll"]
    grant.save()
    with pytest.raises(PermissionDenied):
        read(context)
    with pytest.raises(PermissionDenied):
        queue(context)


@pytest.mark.parametrize("changed", ["membership", "actor", "company", "contract"])
def test_revocation_rechecked_under_write_locks(context, membership, changed):
    save(context)
    revision = read(context)["mapping_revision"]
    if changed == "membership":
        membership.is_active = False
        membership.save()
    elif changed == "actor":
        context[2].is_active = False
        context[2].save()
    elif changed == "company":
        context[1].company.active = False
        context[1].company.save()
    else:
        TenantContract.objects.update(status="suspended")
    with pytest.raises((PermissionDenied, ValueError)):
        request_ledger(
            account=context[1],
            actor=context[2],
            month=date(2026, 10, 1),
            request_key=uuid4(),
            expected_mapping_revision=revision,
        )


def test_previous_imported_scope_is_reused_with_original_provenance_and_no_fake_reviewer(context):
    agent, _, actor, legacy, data = context
    FinancialAccount.objects.filter(pk=context[1].pk).update(bank_code="")
    assert complete(agent, legacy, data).status_code == 200
    before = counts()
    result = read(context)
    assert result["readiness"] and not result["needs_mapping"]
    assert result["mapping_source"] == "Vínculo da fonte já importada"
    assert not ReconciliationLedgerMapping.objects.exists() and counts() == before
    fresh, _ = queue(context)
    assert fresh.requested_by_id == actor.pk and validate_job_mapping(fresh)
    legacy.refresh_from_db()
    assert legacy.requested_by_id is None and legacy.evidence_reference == ""
    # Newly imported refreshes must not redefine their own review or change the revision.
    assert result["mapping_revision"] == read(context)["mapping_revision"]


def test_damaged_retained_source_is_not_usable_mapping(context):
    agent, _, _, legacy, data = context
    complete(agent, legacy, data)
    legacy.refresh_from_db()
    assert legacy.source_file
    path = legacy.source_file.content.path
    with open(path, "ab") as stream:
        stream.write(b"damaged")
    result = read(context)
    assert not result["readiness"] and result["needs_mapping"]


def test_status_uses_real_claim_and_capabilities_and_reading_never_creates_audit(context, settings):
    save(context)
    agent, _, actor, _, _ = context
    settings.EDGE_AGENT_INSTALLER_URL = "https://example.test/published-installer.msi"
    job, _ = queue(context)
    before = counts()
    result = ledger_job_context(job=job, actor=actor)
    assert result["status"] == "queued"
    assert result["agent_state"]["code"] == "unknown"
    assert "installer_url" not in result["agent_state"]
    agent.ledger_capabilities = {"automatic_counts": False, "version": "1.0.8"}
    agent.ledger_capabilities_observed_at = timezone.now()
    agent.save()
    result = ledger_job_context(job=job, actor=actor)
    assert result["agent_state"]["code"] == "outdated"
    assert result["agent_state"]["installer_url"] == settings.EDGE_AGENT_INSTALLER_URL
    agent.ledger_capabilities = {"automatic_counts": True, "version": "1.0.11"}
    agent.ledger_capabilities_observed_at = timezone.now()
    agent.last_seen_at = timezone.now() - timedelta(minutes=6)
    agent.save()
    assert ledger_job_context(job=job, actor=actor)["agent_state"]["code"] == "offline"
    agent.last_seen_at = timezone.now()
    agent.save()
    job.claimed_at = timezone.now()
    job.save()
    result = ledger_job_context(job=job, actor=actor)
    assert result["status"] == "delivered" and result["agent_state"]["code"] == "online"
    assert counts() == before


def test_retry_creates_new_capture_and_preserves_terminal_original(context):
    save(context)
    job, _ = queue(context)
    job.state = "review"
    job.error_code = "ledger_records_removed"
    job.save()
    result = ledger_job_context(job=job, actor=context[2])
    assert "não aparecem" in result["detail"]
    fresh, created = retry_ledger_request(
        job=job,
        actor=context[2],
        request_key=uuid4(),
        expected_mapping_revision=read(context)["mapping_revision"],
    )
    assert created and fresh.pk != job.pk
    job.refresh_from_db()
    assert job.state == "review" and job.error_code == "ledger_records_removed"


def test_mapping_tampering_invalidates_jobs_and_does_not_leak_private_fields_to_audit(context):
    mapping = save(context)
    job, _ = queue(context)
    mapping.scope = dict(mapping.scope, branch_code=99)
    mapping.save()
    assert not validate_job_mapping(job)
    for metadata in AuditEvent.objects.values_list("metadata", flat=True):
        assert "Fonte sintética" not in str(metadata)
        assert "synthetic-only" not in str(metadata)


def make_bank_source(account, *, digest="a" * 64):
    return ReconciliationSourceFile.objects.create(
        organization=account.organization,
        company=account.company,
        financial_account=account,
        origin="bank_statement",
        kind="ofx",
        original_filename="sintetico.ofx",
        content_hash=digest,
        size_bytes=1,
        content="private/synthetic.ofx",
    )


def test_bank_source_is_explicit_scoped_and_conference_preserves_month(context):
    save(context)
    source = make_bank_source(context[1])
    job, _ = queue(context, bank_source=source)
    assert job.bank_source_id == source.pk
    result = ledger_job_context(job=job, actor=context[2])
    assert str(source.pk) in result["source_url"]
    assert "start=2026-10-01" in result["source_url"] and "end=2026-10-31" in result["source_url"]
    other = FinancialAccount.objects.create(
        organization=context[1].organization,
        company=context[1].company,
        name="Outra sintética",
        account_reference="Outra",
        ledger_code="9",
    )
    wrong = make_bank_source(other, digest="b" * 64)
    with pytest.raises(LedgerRequestError, match="extrato desta empresa e conta"):
        queue(context, bank_source=wrong)
    NativeLedgerCollection.objects.filter(pk=job.pk).update(bank_source=wrong)
    assert not validate_job_mapping(job)
    with pytest.raises(LedgerRequestError):
        ledger_job_context(job=job, actor=context[2])


def test_foreign_accounting_source_cannot_be_exposed_by_status(context):
    save(context)
    job, _ = queue(context)
    other = FinancialAccount.objects.create(
        organization=context[1].organization,
        company=context[1].company,
        name="Outra sintética",
        account_reference="Outra",
        ledger_code="9",
    )
    source = make_bank_source(other)
    source.origin = "accounting"
    source.kind = "json"
    source.save()
    job.source_file = source
    job.content_hash = source.content_hash
    job.state = "review"
    job.save()
    with pytest.raises(LedgerRequestError, match="vínculo com a conta"):
        ledger_job_context(job=job, actor=context[2])


def test_nonce_replay_after_role_revocation_cannot_disclose_job(context, membership):
    save(context)
    key = uuid4()
    queue(context, request_key=key)
    revision = read(context)["mapping_revision"]
    membership.is_active = False
    membership.save()
    with pytest.raises(PermissionDenied):
        request_ledger(
            account=context[1],
            actor=context[2],
            month=date(2026, 10, 1),
            request_key=key,
            expected_mapping_revision=revision,
        )


def test_empty_import_has_distinct_status_and_not_amount_based_success(context):
    save(context)
    job, _ = queue(context)
    job.state = "imported"
    job.result = {"created": 0, "ignored": 0, "source_rows": 0, "bank_effects": 0}
    job.save()
    result = ledger_job_context(job=job, actor=context[2])
    assert result["status"] == "empty" and "Sem lançamentos" in result["label"]
    assert not result["can_retry"]


@pytest.mark.django_db(transaction=True)
def test_concurrent_nonce_creates_exactly_one_job_and_one_audit(context):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("PostgreSQL row locks required")
    save(context)
    key = uuid4()
    revision = read(context)["mapping_revision"]
    barrier = Barrier(2)

    def worker():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            result, created = request_ledger(
                account=context[1],
                actor=context[2],
                month=date(2026, 10, 1),
                request_key=key,
                expected_mapping_revision=revision,
            )
            return result.pk, created
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: worker(), range(2)))
    assert len({identifier for identifier, _ in results}) == 1
    assert sorted(created for _, created in results) == [False, True]
    assert NativeLedgerCollection.objects.filter(request_key=key).count() == 1
    assert AuditEvent.objects.filter(action="hub.reconciliation.ledger_requested").count() == 1


def test_new_human_mapping_requires_bank_code_but_no_inferred_chart_account(context):
    from apps.hub.models import LedgerAccount

    FinancialAccount.objects.filter(pk=context[1].pk).update(bank_code="")
    result = read(context)
    assert "código do banco" in " ".join(result["errors"])
    with pytest.raises(LedgerRequestError, match="código do banco"):
        save(context)
    assert not ReconciliationLedgerMapping.objects.exists()
    FinancialAccount.objects.filter(pk=context[1].pk).update(bank_code="001")
    save(context)
    assert not LedgerAccount.objects.exists()


def test_mapping_is_not_financial_usage_and_identity_edit_invalidates_it(context):
    from apps.hub.setup_review import account_usage_reasons

    # The legacy fixture's queued job is a real usage; remove only that synthetic job
    # to prove a configuration-only relation does not lock an otherwise unused account.
    context[3].delete()
    save(context)
    account = context[1]
    assert not account_usage_reasons(account)
    FinancialAccount.objects.filter(pk=account.pk).update(account_reference="corrigida")
    assert read(context)["needs_mapping"]
    save(context)
    queue(context)
    assert "intelligence.nativeledgercollection" in account_usage_reasons(account)


def test_pending_request_from_revoked_actor_is_actionable_for_current_authorized_user(context):
    from apps.accounts.models import User
    from apps.organizations.models import Membership

    save(context)
    job, _ = queue(context)
    viewer = User.objects.create_user("another.synthetic@example.test", "synthetic-password")
    Membership.objects.create(organization=context[1].organization, user=viewer, role="owner")
    context[2].is_active = False
    context[2].save()
    result = ledger_job_context(job=job, actor=viewer)
    assert result["status"] == "review" and result["can_retry"]
    assert "Acesso" in result["label"]
    fresh, _ = retry_ledger_request(
        job=job,
        actor=viewer,
        request_key=uuid4(),
        expected_mapping_revision=ledger_request_context(
            account=context[1],
            actor=viewer,
        )["mapping_revision"],
    )
    assert fresh.requested_by_id == viewer.pk
    job.refresh_from_db()
    assert job.requested_by_id == context[2].pk and job.state == "queued"


def test_pending_job_for_replaced_agent_never_claims_agent_is_connected(context):
    save(context)
    job, _ = queue(context)
    agent = context[0]
    agent.is_official = False
    agent.status = "revoked"
    agent.save()
    result = ledger_job_context(job=job, actor=context[2])
    assert result["status"] == "review" and result["can_retry"]
    assert result["agent_state"]["code"] == "missing"


def test_retained_source_size_metadata_must_match_private_bytes(context):
    agent, _, _, legacy, data = context
    assert complete(agent, legacy, data).status_code == 200
    legacy.refresh_from_db()
    assert legacy.source_file is not None
    ReconciliationSourceFile.objects.filter(pk=legacy.source_file_id).update(size_bytes=1)
    result = read(context)
    assert result["needs_mapping"] and not result["readiness"]
    assert not ReconciliationLedgerMapping.objects.exists()
