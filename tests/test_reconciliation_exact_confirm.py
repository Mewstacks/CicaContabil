from __future__ import annotations

import pytest
from django.urls import reverse
from tests.test_reconciliation_workbench import make_case

from apps.audit.models import AuditEvent
from apps.hub.models import AccountingExport, MovementReconciliation
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


def _urls(case):
    source = case["source"]
    return (
        reverse("hub:reconciliation-source-review", args=[source.pk]),
        reverse("hub:reconciliation-source-confirm-exact", args=[source.pk]),
    )


def test_operator_confirms_only_unique_exact_pairs_and_can_undo_each(organization):
    case = make_case(organization, count=4)
    review, confirm = _urls(case)
    client = case["client"]
    page = client.get(review)
    assert page.context["conference_exact_count"] == 4
    assert page.context["conference_period_label"] == "12/09/2026 a 12/09/2026"
    html = page.content.decode()
    assert "Confirmar 4 coincidências" in html and "12/09/2026 a 12/09/2026" in html
    assert not MovementReconciliation.objects.exists()
    response = client.post(confirm, {"expected_count": "4"})
    assert response.status_code == 302 and response["Location"].startswith(review)
    allocations = list(MovementReconciliation.objects.all())
    assert len(allocations) == 4
    assert all(a.state == "confirmed" and a.confirmed_by == case["user"] for a in allocations)
    assert all(a.evidence["batch"] is True for a in allocations)
    assert {a.amount_cents for a in allocations} == {10000, 10001, 10002, 10003}
    batch_events = AuditEvent.objects.filter(action="hub.reconciliation.exact_matches_confirmed")
    assert batch_events.count() == 1
    assert (
        AuditEvent.objects.filter(action="hub.reconciliation.reconciliation_confirmed").count() == 4
    )
    assert not AccountingExport.objects.exists()
    after = client.get(review)
    assert after.context["conference_confirmed_count"] == 4
    assert after.context["conference_exact_count"] == 0
    assert "coincidência" not in after.content.decode().split("Conferir os movimentos")[0]
    movement = allocations[0].movement
    undone = client.post(
        reverse("hub:reconciliation-movement", args=[movement.pk]),
        {"action": "undo_reconciliation", "reconciliation_id": str(allocations[0].pk)},
    )
    assert undone.status_code == 302
    assert client.get(review).context["conference_confirmed_count"] == 3


def test_ambiguous_amounts_stay_for_individual_review(organization):
    # Two movements and two ledger records share date, direction and amount.
    case = make_case(organization, amounts=[10000, 10000, 20000])
    review, confirm = _urls(case)
    count = case["client"].get(review).context["conference_exact_count"]
    assert count == 1
    case["client"].post(confirm, {"expected_count": str(count)})
    allocation = MovementReconciliation.objects.get()
    assert allocation.amount_cents == 20000


def test_stale_count_is_refused_without_partial_writes(organization):
    case = make_case(organization, count=3)
    _, confirm = _urls(case)
    response = case["client"].post(confirm, {"expected_count": "2"}, follow=True)
    assert response.status_code == 200
    assert "A conferência mudou" in response.content.decode()
    assert not MovementReconciliation.objects.exists()
    batch_events = AuditEvent.objects.filter(action="hub.reconciliation.exact_matches_confirmed")
    assert not batch_events.exists()


def test_auditor_and_other_tenant_cannot_confirm(organization):
    case = make_case(organization, role="auditor")
    review, confirm = _urls(case)
    page = case["client"].get(review)
    assert "Confirmar 3 coincidências" not in page.content.decode()
    response = case["client"].post(confirm, {"expected_count": "3"})
    assert response.status_code in {302, 403}
    assert not MovementReconciliation.objects.exists()
    outsider = Organization.objects.create(name="Outro escritório", slug="exact-outsider")
    other = make_case(outsider)
    owner = make_case(Organization.objects.create(name="Escritório dono", slug="exact-owner"))
    foreign = reverse("hub:reconciliation-source-confirm-exact", args=[other["source"].pk])
    assert owner["client"].post(foreign, {"expected_count": "3"}).status_code == 404
    assert not MovementReconciliation.objects.exists()


def test_get_is_not_allowed(organization):
    case = make_case(organization)
    _, confirm = _urls(case)
    assert case["client"].get(confirm).status_code == 405
