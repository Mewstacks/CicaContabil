"""Explicit source interpretation shares capacity across bank accounts of one company."""

from copy import deepcopy
from datetime import date
from uuid import uuid4

import pytest
from django.db import connection

from apps.hub.models import FinancialAccount, ReconciliationTitleAllocation
from apps.hub.title_contract import TitleContractError
from apps.hub.title_persistence import (
    _load,
    confirm_title_allocations,
    prepare_title_allocations,
    undo_title_allocation,
)
from apps.intelligence.models import CompanyTitleCollection, NativeTitleSettlementProvenance
from apps.intelligence.native_title_contract import AUTOMATIC_VERSION, canonical_hash, contract_hash
from apps.intelligence.native_title_translation import import_reviewed_native_titles
from test_native_title_translation import review_data
from test_native_titles import complete
from test_native_titles import fiscal as fiscal_fixture
from test_title_persistence import bank

fiscal = fiscal_fixture
pytestmark = pytest.mark.django_db
START, END = date(2026, 9, 1), date(2026, 9, 30)


@pytest.fixture
def shared(fiscal):
    agent, first, actor, legacy, data, _ = fiscal
    scope = {
        key: value
        for key, value in legacy.scope.items()
        if key not in {"comparison_bank_account_code", "expected_counts"}
    }
    scope["capture_id"] = str(uuid4())
    data.update(version=AUTOMATIC_VERSION, scope_revision=canonical_hash(scope))
    job = CompanyTitleCollection.objects.create(
        pk=scope["capture_id"],
        organization=first.organization,
        company=first.company,
        agent=agent,
        requested_by=actor,
        evidence_reference="Captura sintética",
        request_key=uuid4(),
        batch_key=uuid4(),
        scope=scope,
        scope_revision=canonical_hash(scope),
        contract_hash=contract_hash(),
    )
    assert complete(agent, job, data).status_code == 200
    job.refresh_from_db()
    second = FinancialAccount.objects.create(
        organization=first.organization,
        company=first.company,
        name="Outra conta",
        account_reference="SYN-OTHER",
        ledger_code="9",
    )
    review = review_data(scope, data)
    snapshots = [
        import_reviewed_native_titles(
            organization_id=first.organization_id,
            capture_id=job.pk,
            actor=actor,
            review=review,
            financial_account=account,
        )[0]
        for account in (first, second)
    ]
    return actor, job, review, [first, second], snapshots


def proposal(shared, index, cents=3000):
    actor, _, _, accounts, snapshots = shared
    snapshot, account = snapshots[index], accounts[index]
    payload, _ = _load(snapshot, account)
    title = payload["titles"][0]
    part = title["installments"][0]
    event = part["settlements"][0]
    movement = bank(account, cents=-4000)
    return dict(
        snapshot=snapshot,
        actor=actor,
        period_start=START,
        period_end=END,
        requests=[
            dict(
                movement_key=str(movement.pk),
                title_key=title["key"],
                installment_key=part["key"],
                settlement_key=event["key"],
                cash_cents=cents,
            )
        ],
    )


def confirm(options, plan=None):
    plan = plan or prepare_title_allocations(**options)
    return confirm_title_allocations(
        **options,
        request_id=uuid4(),
        preview_fingerprint=plan.fingerprint,
        evidence_reference="Conferência sintética multiconta",
    )[0]


def test_same_payment_shares_company_capacity_and_undo_releases_it(shared):
    assert NativeTitleSettlementProvenance.objects.count() == 4
    first, second = proposal(shared, 0), proposal(shared, 1)
    before = prepare_title_allocations(**second)
    batch = confirm(first)
    with pytest.raises(TitleContractError, match="Capacidade"):
        confirm(second, before)
    second["requests"][0]["cash_cents"] = 1000
    confirm(second)
    assert sum(ReconciliationTitleAllocation.objects.values_list("cash_cents", flat=True)) == 4000
    undo_title_allocation(
        allocation=batch.allocations.get(), actor=shared[0], reason="Desfazer vínculo sintético"
    )
    second["requests"][0]["cash_cents"] = 3000
    confirm(second)


def test_different_payment_in_same_installment_can_use_another_account(shared):
    first, second = proposal(shared, 0, 4000), proposal(shared, 1, 3000)
    payload, _ = _load(shared[4][1], shared[3][1])
    event = payload["titles"][0]["installments"][0]["settlements"][1]
    second["requests"][0]["settlement_key"] = event["key"]
    confirm(first)
    confirm(second)
    assert ReconciliationTitleAllocation.objects.count() == 2


def test_changed_interpretation_in_another_account_requires_undo(shared):
    actor, job, review, accounts, _ = shared
    confirm(proposal(shared, 0))
    changed = deepcopy(review)
    changed["decisions"][0]["settlements"][0]["normalized"].update(
        principal_cents=3500, cash_cents=3500
    )
    with pytest.raises(TitleContractError, match="interpretação"):
        import_reviewed_native_titles(
            organization_id=accounts[1].organization_id,
            capture_id=job.pk,
            actor=actor,
            review=changed,
            financial_account=accounts[1],
        )


def test_split_component_groups_with_same_event_identity_cannot_duplicate_capacity(shared):
    actor, job, review, accounts, _ = shared
    confirm(proposal(shared, 0))
    changed = deepcopy(review)
    event = changed["decisions"][0]["settlements"][0]
    refs = event["payment_references"]
    assert len(refs) == 2
    event["payment_references"] = [refs[0]]
    event["normalized"]["key"] = canonical_hash([refs[0]])
    event["normalized"].update(principal_cents=2000, cash_cents=2000)
    other = deepcopy(event)
    other["payment_references"] = [refs[1]]
    other["normalized"]["key"] = canonical_hash([refs[1]])
    changed["decisions"][0]["settlements"].append(other)
    with pytest.raises(TitleContractError, match=r"[Aa]grupamento"):
        import_reviewed_native_titles(
            organization_id=accounts[1].organization_id,
            capture_id=job.pk,
            actor=actor,
            review=changed,
            financial_account=accounts[1],
        )


def test_tampered_provenance_or_raw_source_blocks_capacity(shared):
    _, job, _, _, snapshots = shared
    row = NativeTitleSettlementProvenance.objects.filter(snapshot=snapshots[0]).first()
    NativeTitleSettlementProvenance.objects.filter(pk=row.pk).update(fingerprint="0" * 64)
    with pytest.raises(TitleContractError, match="integridade"):
        prepare_title_allocations(**proposal(shared, 0))
    NativeTitleSettlementProvenance.objects.filter(pk=row.pk).update(fingerprint=row.fingerprint)
    job.source_file.content_hash = "0" * 64
    job.source_file.save()
    with pytest.raises(TitleContractError, match="fonte original"):
        prepare_title_allocations(**proposal(shared, 0))


@pytest.mark.django_db(transaction=True)
def test_postgresql_competing_accounts_share_native_capacity(shared):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connections

    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    options = [proposal(shared, index) for index in range(2)]
    plans = [prepare_title_allocations(**option) for option in options]
    barrier = Barrier(2)

    def run(index):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                confirm(options[index], plans[index])
                return "confirmed"
            except TitleContractError:
                return "blocked"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        result = list(pool.map(run, range(2)))
    assert sorted(result) == ["blocked", "confirmed"]
    assert list(ReconciliationTitleAllocation.objects.values_list("cash_cents", flat=True)) == [
        3000
    ]


def split_review(review):
    changed = deepcopy(review)
    event = changed["decisions"][0]["settlements"][0]
    refs = event["payment_references"]
    event["payment_references"] = [refs[0]]
    event["normalized"]["key"] = canonical_hash([refs[0]])
    event["normalized"].update(principal_cents=2000, cash_cents=2000)
    other = deepcopy(event)
    other["payment_references"] = [refs[1]]
    other["normalized"]["key"] = canonical_hash([refs[1]])
    changed["decisions"][0]["settlements"].append(other)
    return changed, event, other


def test_split_native_components_are_rejected_even_without_active_allocations(shared):
    actor, job, review, accounts, _ = shared
    changed, _, _ = split_review(review)
    with pytest.raises(TitleContractError, match="Agrupamento"):
        import_reviewed_native_titles(
            organization_id=accounts[0].organization_id,
            capture_id=job.pk,
            actor=actor,
            review=changed,
            financial_account=accounts[0],
        )
    assert not ReconciliationTitleAllocation.objects.exists()


def test_one_batch_rejects_preexisting_conflicting_groups_of_same_native_event(shared):
    from apps.hub.native_title_capacity import persist_native_provenance, proposed_provenance
    from apps.hub.title_persistence import import_title_snapshot
    from apps.intelligence.native_title_comparison import _load as load_native
    from apps.intelligence.native_title_translation import translate_reviewed_titles
    from test_native_titles import encode

    actor, job, review, accounts, snapshots = shared
    changed, event, other = split_review(review)
    _, evidence = load_native(job.pk, job.organization_id, actor)
    payload, provenance = translate_reviewed_titles(
        evidence=evidence,
        review=changed,
        company_key=str(accounts[0].company_id),
        account_reference=accounts[0].account_reference,
    )
    # Simulate a retained older normalization: ordinary publication now rejects this.
    snapshot, _ = import_title_snapshot(
        financial_account=accounts[0],
        content=encode(payload),
        actor=actor,
        evidence_reference="Fotografia antiga sintética",
    )
    proposed = proposed_provenance(
        account=accounts[0], job=job, payload=payload, provenance=provenance
    )
    persist_native_provenance(
        account=accounts[0],
        snapshot=snapshot,
        proposed=proposed,
        installments={(p["title_key"], p["installment_key"]) for p in provenance},
    )
    snapshots[0] = snapshot
    options = proposal(shared, 0, 2000)
    first = options["requests"][0]
    options["requests"] = [
        {**first, "settlement_key": event["normalized"]["key"]},
        {**first, "settlement_key": other["normalized"]["key"]},
    ]
    with pytest.raises(TitleContractError, match="Agrupamento"):
        confirm(options)
    assert not ReconciliationTitleAllocation.objects.exists()


def test_one_batch_accepts_distinct_native_events_of_the_same_installment(shared):
    options = proposal(shared, 0, 1000)
    payload, _ = _load(shared[4][0], shared[3][0])
    second = payload["titles"][0]["installments"][0]["settlements"][1]
    options["requests"].append({**options["requests"][0], "settlement_key": second["key"]})
    confirm(options)
    assert ReconciliationTitleAllocation.objects.count() == 2
