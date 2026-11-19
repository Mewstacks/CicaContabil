"""D-388: unique exact bank/Razão pairs are confirmed by the system."""

from __future__ import annotations

from datetime import date
from types import SimpleNamespace

import pytest
from tests.test_reconciliation_workbench import make_case

from apps.audit.models import AuditEvent
from apps.hub.auto_confirm import auto_confirm_exact, auto_confirm_for_job
from apps.hub.models import MovementReconciliation

pytestmark = pytest.mark.django_db


def test_exact_pairs_are_confirmed_automatically_and_marked(organization):
    case = make_case(organization, count=3)
    assert (
        auto_confirm_exact(source=case["source"], month=date(2026, 9, 1), actor=case["user"]) == 3
    )
    allocations = list(MovementReconciliation.objects.all())
    assert len(allocations) == 3
    assert all(a.state == "confirmed" and a.evidence.get("automatic") is True for a in allocations)
    assert all("D-388" in a.evidence["note"] for a in allocations)
    event = AuditEvent.objects.get(action="hub.reconciliation.exact_matches_confirmed")
    assert event.metadata["automatic"] is True and event.metadata["count"] == 3
    assert (
        auto_confirm_exact(source=case["source"], month=date(2026, 9, 1), actor=case["user"]) == 0
    )


def test_ambiguous_pairs_stay_for_review(organization):
    case = make_case(organization, amounts=[10000, 10000, 20000])
    assert (
        auto_confirm_exact(source=case["source"], month=date(2026, 9, 1), actor=case["user"]) == 1
    )
    assert MovementReconciliation.objects.get().amount_cents == 20000


def test_other_month_confirms_nothing(organization):
    case = make_case(organization, count=2)
    assert (
        auto_confirm_exact(source=case["source"], month=date(2026, 10, 1), actor=case["user"]) == 0
    )
    assert not MovementReconciliation.objects.exists()


def test_job_arrival_confirms_its_statement(organization):
    case = make_case(organization, count=2)
    job = SimpleNamespace(
        scope={"period_start": "2026-09-01"},
        bank_source_id=case["source"].pk,
        bank_source=case["source"],
        financial_account_id=case["source"].financial_account_id,
        requested_by=case["user"],
    )
    assert auto_confirm_for_job(job) == 2
    assert MovementReconciliation.objects.filter(state="confirmed").count() == 2
