"""Synthetic read journeys preserve scope, evidence and globally shared capacity."""

from copy import deepcopy
from datetime import date
from unittest.mock import Mock

import pytest
from django.core.exceptions import PermissionDenied

from apps.audit.models import AuditEvent
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    NormalizedMovement,
    ReconciliationSourceFile,
    ReconciliationTitleAllocation,
    ReconciliationTitleDecision,
    ReconciliationTitleSnapshot,
)
from apps.hub.title_contract import TitleContractError
from apps.hub.title_persistence import title_plan_review, undo_title_allocation
from apps.hub.title_read_model import build_title_workspace, load_latest_title_snapshot
from apps.platform.models import TenantContract
from test_title_persistence import END, START, bank, confirmed, imported, prepared, request
from test_title_persistence import context as context_fixture

context = context_fixture
pytestmark = pytest.mark.django_db


def workspace(context, **options):
    account, actor, _ = context
    return build_title_workspace(account=account, actor=actor, start=START, end=END, **options)


def counts():
    return {
        model.__name__: model.objects.count()
        for model in (
            AuditEvent, FinancialAccount, NormalizedMovement, ReconciliationSourceFile,
            ReconciliationTitleSnapshot, ReconciliationTitleAllocation,
            ReconciliationTitleDecision,
        )
    }


def test_catalog_read_has_no_writes_and_does_not_turn_due_date_into_payment(context):
    account, _, payload = context
    payload["settlements_complete"] = False
    payload["titles"][0]["installments"][0]["outstanding_cents"] = None
    imported(context)
    bank(account)
    before = counts()
    result = workspace(context)
    assert not result["blocking"] and result["warnings"]
    assert result["installment_rows"][0]["due_on"] == date(2026, 10, 1)
    assert result["installment_rows"][0]["outstanding_cents"] is None
    assert result["installment_rows"][0]["outstanding_display"] == "Não informado"
    assert result["settlement_rows"][0]["posted_on"] == date(2026, 9, 12)
    assert result["settlement_rows"][0]["cash_display"] == "R$ 61,25"
    assert result["settlement_rows"][0]["interest_display"] == "R$ 1,50"
    assert counts() == before


def test_empty_catalog_is_explicit_without_creating_snapshot(context):
    result = workspace(context)
    assert result["snapshot"] is None and result["warnings"]
    assert not result["movement_rows"] and not result["settlement_rows"]
    assert not ReconciliationTitleSnapshot.objects.exists()


@pytest.mark.parametrize("role", ["operator", "auditor"])
def test_live_company_and_module_grants_are_intersected(context, membership, role):
    account, _, _ = context
    imported(context)
    other_company = ClientCompany.objects.create(
        organization=account.organization, name="Outra empresa fictícia",
    )
    membership.role = role
    membership.save()
    permitted = CompanyAccessGrant.objects.create(
        organization=account.organization, membership=membership,
        company=account.company, modules=["reconciliation"],
    )
    CompanyAccessGrant.objects.create(
        organization=account.organization, membership=membership,
        company=other_company, modules=["payroll"],
    )
    result = workspace(context)
    assert result["can_manage"] is (role == "operator")
    permitted.modules = ["payroll"]
    permitted.save()
    with pytest.raises(PermissionDenied):
        workspace(context)


@pytest.mark.parametrize("field", ["membership", "user", "company", "contract", "billing"])
def test_live_revocation_is_checked_before_source_reads(context, membership, field, monkeypatch):
    account, actor, _ = context
    imported(context)
    loader = Mock()
    monkeypatch.setattr("apps.hub.title_read_model._load", loader)
    if field == "membership":
        membership.is_active = False
        membership.save()
    elif field == "user":
        actor.is_active = False
        actor.save()
    elif field == "company":
        account.company.active = False
        account.company.save()
    elif field == "billing":
        membership.role = "billing"
        membership.save()
    else:
        TenantContract.objects.filter(organization=account.organization).update(status="suspended")
    with pytest.raises((PermissionDenied, ValueError)):
        workspace(context)
    loader.assert_not_called()


def test_inactive_account_can_read_prior_evidence_without_management(context):
    account, _, _ = context
    imported(context)
    FinancialAccount.objects.filter(pk=account.pk).update(active=False)
    result = workspace(context)
    assert result["snapshot"] and not result["can_manage"]
    assert any("inativa" in warning for warning in result["warnings"])


def test_global_capacity_and_preview_include_prior_allocations(context):
    account, actor, payload = context
    other = deepcopy(payload["titles"][0])
    other["key"] = "T-2"
    payload["titles"].append(other)
    snapshot = imported(context)
    first, duplicate = bank(account, key="ofx:SHARED"), bank(account, key="ofx:SHARED")
    confirmed(snapshot, [request(first, cents=2000)], actor)
    confirmed(snapshot, [request(duplicate, cents=1000, title="T-2")], actor)
    result = workspace(context)
    assert len(result["movement_rows"]) == 1
    assert result["movement_rows"][0]["allocated_cents"] == 3000
    assert result["movement_rows"][0]["remaining_cents"] == 3125
    events = {row["title_key"]: row for row in result["settlement_rows"]}
    assert events["T-1"]["allocated_cents"] == 2000
    assert events["T-1"]["remaining_cents"] == 4125
    assert events["T-2"]["remaining_cents"] == 5125
    plan = prepared(snapshot, [request(first, cents=500)], actor)
    assert plan.preview.movements[0].allocated_cents == 3500
    assert plan.preview.movements[0].remaining_cents == 2625
    settlements = {row.reference.title_key: row for row in plan.preview.settlements}
    assert settlements["T-1"].allocated_cents == 2500
    assert settlements["T-1"].remaining_cents == 3625
    assert settlements["T-2"].allocated_cents == 1000
    assert title_plan_review(plan)["movements"][0]["remaining_cents"] == 2625


def test_undone_history_remains_visible_without_consuming_capacity(context):
    account, actor, _ = context
    snapshot = imported(context)
    movement = bank(account)
    batch, _ = confirmed(snapshot, [request(movement, cents=4000)], actor)
    undo_title_allocation(
        allocation=batch.allocations.get(), actor=actor, reason="Revisão fictícia",
    )
    result = workspace(context)
    assert len(result["allocations"]) == 1 and len(result["decisions"]) == 2
    assert result["movement_rows"][0]["remaining_cents"] == 6125
    assert result["settlement_rows"][0]["allocated_cents"] == 0


@pytest.mark.parametrize("target", ["snapshot", "bank", "prior_bank", "event", "movement"])
def test_changed_sources_or_facts_block_new_choices_keep_scoped_history(context, target):
    account, actor, payload = context
    snapshot = imported(context)
    movement = bank(account)
    confirmed(snapshot, [request(movement, cents=1000)], actor)
    if target in {"snapshot", "bank", "prior_bank"}:
        source = snapshot.source_file if target == "snapshot" else movement.source_file
        with source.content.open("wb") as stream:
            stream.write(b"synthetic altered source")
    elif target == "event":
        changed = deepcopy(payload)
        changed["as_of"] = "2026-10-01"
        changed["titles"][0]["installments"][0]["settlements"][0]["posted_on"] = "2026-09-13"
        imported(context, changed)
    else:
        movement.original_description = "Alteração sintética"
        movement.save()
    result = workspace(context)
    assert result["blocking"] and result["errors"]
    assert not result["movement_rows"] and not result["settlement_rows"]
    assert len(result["allocations"]) == len(result["decisions"]) == 1
    if target == "prior_bank":
        # A separate selected movement must still verify the previously used source.
        with pytest.raises(TitleContractError, match="Hash"):
            prepared(snapshot, [request(bank(account), cents=500)], actor)


def test_overlapping_ofx_conflict_blocks_even_without_confirmations(context):
    account, _, _ = context
    imported(context)
    bank(account, key="ofx:DUP")
    bank(account, key="ofx:DUP", cents=-1000)
    result = workspace(context)
    assert result["blocking"] and "identidade" in result["errors"][0]


def test_current_snapshot_is_required_and_old_version_is_never_fallback(context):
    account, actor, payload = context
    first = imported(context)
    changed = deepcopy(payload)
    changed["as_of"] = "2026-10-01"
    newer = imported(context, changed)
    assert workspace(context)["snapshot"].pk == newer.pk
    result = workspace(context, snapshot_id=first.pk)
    assert result["blocking"] and not result["settlement_rows"]
    with pytest.raises(TitleContractError, match="fotografia mudou"):
        load_latest_title_snapshot(account=account, actor=actor, snapshot_id=first.pk)


def test_period_and_direction_only_select_matching_bank_and_settlement_rows(context):
    account, _, _ = context
    imported(context)
    selected = bank(account)
    bank(account, cents=1000)
    bank(account, day=date(2026, 10, 1))
    other = FinancialAccount.objects.create(
        organization=account.organization, company=account.company,
        name="Outro banco fictício", account_reference="OTHER",
    )
    bank(other)
    result = workspace(context, direction="outflow")
    assert [row["key"] for row in result["movement_rows"]] == [str(selected.pk)]
    assert len(result["settlement_rows"]) == 1
    assert not workspace(context, direction="inflow")["settlement_rows"]


@pytest.mark.parametrize("value", ["sideways", "", []])
def test_invalid_direction_fails_closed(context, value):
    with pytest.raises(TitleContractError):
        workspace(context, direction=value)


def test_period_after_snapshot_never_implies_missing_events(context):
    account, actor, _ = context
    imported(context)
    result = build_title_workspace(
        account=account, actor=actor, start=START, end=date(2026, 10, 1),
    )
    assert result["blocking"] and "posição" in result["errors"][0]
    assert not result["settlement_rows"]


def test_ignored_movements_are_visible_but_unavailable(context):
    account, _, _ = context
    imported(context)
    movement = bank(account)
    movement.review_state = "ignored"
    movement.save()
    row = workspace(context)["movement_rows"][0]
    assert not row["available"] and row["issues"]


def test_cross_scope_historical_relationship_never_reaches_template(context):
    account, actor, _ = context
    snapshot = imported(context)
    movement = bank(account)
    confirmed(snapshot, [request(movement, cents=1000)], actor)
    other = ClientCompany.objects.create(
        organization=account.organization, name="Empresa restrita fictícia",
    )
    NormalizedMovement.objects.filter(pk=movement.pk).update(company=other)
    with pytest.raises(TitleContractError, match="fora da empresa"):
        workspace(context)


def test_read_limit_requests_a_smaller_period_instead_of_silently_truncating(context, monkeypatch):
    account, _, _ = context
    imported(context)
    bank(account)
    bank(account)
    monkeypatch.setattr("apps.hub.title_read_model.MAX_MOVEMENTS", 1)
    result = workspace(context)
    assert result["blocking"] and not result["movement_rows"]
    assert "reduza o período" in result["errors"][0]
