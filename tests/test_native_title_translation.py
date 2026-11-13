import hashlib
from copy import deepcopy
from datetime import date
from uuid import uuid4

import pytest

from apps.audit.models import AuditEvent
from apps.hub.models import JournalEntry, ReconciliationTitleSnapshot
from apps.hub.title_persistence import (
    confirm_title_allocations,
    prepare_title_allocations,
    undo_title_allocation,
)
from apps.intelligence.native_title_comparison import TitleSourceEvidence
from apps.intelligence.native_title_contract import canonical_hash, contract_hash, manifest
from apps.intelligence.native_title_translation import (
    import_reviewed_native_titles,
    row_reference,
    translate_reviewed_titles,
)
from test_native_titles import complete, encode, sample
from test_native_titles import fiscal as fiscal_fixture
from test_title_persistence import bank

fiscal_source = fiscal_fixture
pytestmark = pytest.mark.django_db


def review_data(scope, data):
    family = data["families"][0]
    part = family["installments"][0]
    rows = family["payments"]
    spec = manifest()["families"][family["name"]]
    settlements = []
    for number, cents in ((1, 4000), (2, 3000)):
        refs = [
            row_reference(family["name"], "payments", r)
            for r in rows
            if r[spec["payment_number_field"]] == number
        ]
        settlements.append(
            {
                "payment_references": refs,
                "normalized": {
                    "key": canonical_hash(sorted(refs)),
                    "posted_on": "2026-09-12",
                    "principal_cents": cents,
                    "interest_cents": 0,
                    "penalty_cents": 0,
                    "fees_cents": 0,
                    "discount_cents": 0,
                    "cash_cents": cents,
                    "direction": "outflow",
                    "reverses": None,
                },
            }
        )
    return {
        "source_sha256": hashlib.sha256(encode(data)).hexdigest(),
        "evidence_reference": "Synthetic explicit component semantic review",
        "decisions": [
            {
                "family": family["name"],
                "installment_reference": row_reference(family["name"], "installments", part),
                "kind": "payable",
                "principal_field": next(k for k in part if k.startswith("vlor_")),
                "settlements": settlements,
            }
        ],
    }


def translate(data=None, scope=None, review=None):
    if data is None:
        scope, data = sample()
    evidence = TitleSourceEvidence(
        encode(data), scope, hashlib.sha256(encode(data)).hexdigest(), contract_hash()
    )
    return translate_reviewed_titles(
        evidence=evidence,
        review=review or review_data(scope, data),
        company_key="synthetic-company",
        account_reference="synthetic-bank",
    )


def test_explicit_review_keeps_partial_payments_source_dates_unknown_balance_and_provenance():
    payload, provenance = translate()
    part = payload["titles"][0]["installments"][0]
    assert part["principal_cents"] == 10_000
    assert part["outstanding_cents"] is None and payload["settlements_complete"] is False
    assert [r["cash_cents"] for r in part["settlements"]] == [4000, 3000]
    assert sum(len(s["payment_references"]) for s in provenance[0]["settlements"]) == 3


@pytest.mark.parametrize(
    "change",
    ["hash", "omission", "duplicate", "date", "principal", "math", "unknown", "wrong_kind"],
)
def test_financial_decisions_cannot_drop_or_invent_source_facts(change):
    scope, data = sample()
    review = review_data(scope, data)
    decision = review["decisions"][0]
    if change == "hash":
        review["source_sha256"] = "0" * 64
    if change == "omission":
        decision["settlements"].pop()
    if change == "duplicate":
        decision["settlements"].append(deepcopy(decision["settlements"][0]))
    if change == "date":
        decision["settlements"][0]["normalized"]["posted_on"] = "2026-09-13"
    if change == "principal":
        decision["principal_field"] = "codi_emp"
    if change == "math":
        decision["settlements"][0]["normalized"]["cash_cents"] = 1
    if change == "unknown":
        decision["settlements"][0]["payment_references"] = ["unknown"]
    if change == "wrong_kind":
        decision["kind"] = "receivable"
    with pytest.raises(ValueError):
        translate(data, scope, review)


def test_reversal_requires_explicit_link_and_matching_components():
    scope, data = sample()
    family = data["families"][0]
    spec = manifest()["families"][family["name"]]
    second = family["payments"][1]
    second[spec["payment_date_field"]] = "2026-09-13"
    second[next(k for k in second if k.startswith("vpag_"))] = "-40.00"
    # No fiscal accounting link for the changed component; update original fixture accordingly.
    family["accounting_links"] = [
        r for r in family["accounting_links"] if r[spec["payment_number_field"]] != 2
    ]
    family["control"]["accounting_links"] = len(family["accounting_links"])
    scope["expected_counts"][family["name"]]["accounting_links"] = len(family["accounting_links"])
    data["scope_revision"] = canonical_hash(scope)
    review = review_data(scope, data)
    events = review["decisions"][0]["settlements"]
    events[1]["normalized"].update(
        posted_on="2026-09-13",
        principal_cents=4000,
        cash_cents=4000,
        direction="inflow",
        reverses=events[0]["normalized"]["key"],
    )
    payload, _ = translate(data, scope, review)
    assert payload["titles"][0]["installments"][0]["settlements"][1]["reverses"]


def test_retained_capture_to_normalized_snapshot_is_private_idempotent_and_audited(fiscal_source):
    agent, account, actor, job, data, _ = fiscal_source
    assert complete(agent, job, data).status_code == 200
    review = review_data(job.scope, data)
    snapshot, created = import_reviewed_native_titles(
        organization_id=account.organization_id, capture_id=job.pk, actor=actor, review=review
    )
    assert created and snapshot.settlements_complete is False
    repeated, created = import_reviewed_native_titles(
        organization_id=account.organization_id, capture_id=job.pk, actor=actor, review=review
    )
    assert repeated.pk == snapshot.pk and not created
    assert ReconciliationTitleSnapshot.objects.count() == 1 and not JournalEntry.objects.exists()
    event = AuditEvent.objects.get(action="hub.reconciliation.native_titles_translated")
    assert event.metadata["source_sha256"] == review["source_sha256"]
    assert event.metadata["bank_linkage"] == "unproven"


def test_reviewed_raw_source_reaches_partial_bank_allocation_and_audited_undo(fiscal_source):
    agent, account, actor, job, data, _ = fiscal_source
    assert complete(agent, job, data).status_code == 200
    snapshot, _ = import_reviewed_native_titles(
        organization_id=account.organization_id,
        capture_id=job.pk,
        actor=actor,
        review=review_data(job.scope, data),
    )
    raw, _ = translate(data, job.scope)
    title = raw["titles"][0]
    part = title["installments"][0]
    settlement = part["settlements"][0]
    movement = bank(account, cents=-4000)
    requests = [
        {
            "movement_key": str(movement.pk),
            "title_key": title["key"],
            "installment_key": part["key"],
            "settlement_key": settlement["key"],
            "cash_cents": 2000,
        }
    ]
    scope = dict(
        snapshot=snapshot,
        requests=requests,
        actor=actor,
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
    )
    plan = prepare_title_allocations(**scope)
    batch, created = confirm_title_allocations(
        **scope,
        request_id=uuid4(),
        preview_fingerprint=plan.fingerprint,
        evidence_reference="Synthetic explicit bank evidence",
    )
    assert created
    allocation = batch.allocations.get()
    assert allocation.cash_cents == 2000 and allocation.state == "confirmed"
    # Shared capacity checks preserve the bank remainder; undo restores it.
    requests[0]["cash_cents"] = 2001
    with pytest.raises(ValueError):
        prepare_title_allocations(**scope)
    assert undo_title_allocation(
        allocation=allocation, actor=actor, reason="Synthetic reviewed undo"
    )
    requests[0]["cash_cents"] = 4000
    assert prepare_title_allocations(**scope).preview.allocations[0].cash_cents == 4000
    assert not JournalEntry.objects.exists()
