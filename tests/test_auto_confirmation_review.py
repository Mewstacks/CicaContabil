"""D-390: the owner reviews the D-388 automatic confirmations; D-73 precision is measured."""

from __future__ import annotations

import io
import json
from datetime import date

import pytest
from django.core.management import call_command
from django.urls import reverse
from tests.test_reconciliation_workbench import make_case

from apps.audit.models import AuditEvent
from apps.hub.auto_confirm import auto_confirm_exact
from apps.hub.auto_confirmation_review import (
    DECLARATION,
    REVIEW_ACTION,
    acceptance_report,
    review_summary,
)
from apps.hub.models import MovementReconciliation
from apps.hub.reconciliation_service import undo_reconciliation

pytestmark = pytest.mark.django_db


@pytest.fixture
def case(organization, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    return make_case(organization)


def _auto(case) -> int:
    return auto_confirm_exact(source=case["source"], month=date(2026, 9, 1), actor=case["user"])


def _post(case, **data):
    url = reverse("hub:reconciliation-source-auto-review", args=[case["source"].pk])
    payload = {"declaration": DECLARATION, "expected_total": "3", **data}
    return case["client"].post(url, payload, follow=True)


def _reviews(case):
    return AuditEvent.objects.filter(action=REVIEW_ACTION, target_id=str(case["source"].pk))


def test_owner_registers_review_with_kept_and_undone(case):
    assert _auto(case) == 3
    undo_reconciliation(
        reconciliation=MovementReconciliation.objects.filter(evidence__automatic=True).first(),
        actor=case["user"],
    )
    page = case["client"].get(reverse("hub:reconciliation-source-review", args=[case["source"].pk]))
    html = page.content.decode()
    assert "3 confirmações automáticas" in html and "Sem revisão da proprietária" in html
    assert DECLARATION in html and "Registrar revisão" in html

    response = _post(case)
    assert "Revisão registrada: 2 mantidas e 1 desfeita." in response.content.decode()
    event = _reviews(case).get()
    assert event.actor_id == case["user"].pk
    assert (event.metadata["reviewed"], event.metadata["kept"], event.metadata["undone"]) == (
        3,
        2,
        1,
    )
    assert {item["state"] for item in event.metadata["items"]} == {"confirmed", "undone"}
    assert event.metadata["release_accepted"] is False

    again = _post(case)
    assert "Revisão já registrada com o mesmo resultado" in again.content.decode()
    assert _reviews(case).count() == 1
    summary = review_summary(case["source"])
    assert summary["review_is_current"] is True
    assert "Registrar revisão" not in again.content.decode()
    assert "Revisão registrada" in again.content.decode()


def test_change_after_review_marks_it_outdated_and_new_review_supersedes(case):
    _auto(case)
    _post(case)
    undo_reconciliation(
        reconciliation=MovementReconciliation.objects.filter(evidence__automatic=True).first(),
        actor=case["user"],
    )
    page = case["client"].get(reverse("hub:reconciliation-source-review", args=[case["source"].pk]))
    assert "Revisão desatualizada" in page.content.decode()
    _post(case)
    assert _reviews(case).count() == 2
    report = acceptance_report(case["source"].organization_id)
    assert (report["statements_reviewed"], report["reviewed"], report["kept"]) == (1, 3, 2)
    assert report["precision_percent"] == 66.6667
    assert report["missing_to_minimum"] == 197
    assert report["threshold_passed"] is False and report["release_accepted"] is False


@pytest.mark.parametrize(
    "data, message",
    [
        ({"declaration": ""}, "Marque a declaração"),
        ({"expected_total": "2"}, "As confirmações mudaram"),
    ],
)
def test_review_requires_declaration_and_current_counts(case, data, message):
    _auto(case)
    response = _post(case, **data)
    assert message in response.content.decode()
    assert not _reviews(case).exists()


def test_without_automatic_confirmations_there_is_nothing_to_review(case):
    page = case["client"].get(reverse("hub:reconciliation-source-review", args=[case["source"].pk]))
    assert "confirmações automáticas" not in page.content.decode()
    response = _post(case, expected_total="0")
    assert "não tem confirmações automáticas" in response.content.decode()
    assert not _reviews(case).exists()


def test_only_the_owner_registers(organization, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    case = make_case(organization, role="admin")
    _auto(case)
    page = case["client"].get(reverse("hub:reconciliation-source-review", args=[case["source"].pk]))
    html = page.content.decode()
    assert "3 confirmações automáticas" in html and "Registrar revisão" not in html
    response = case["client"].post(
        reverse("hub:reconciliation-source-auto-review", args=[case["source"].pk]),
        {"declaration": DECLARATION, "expected_total": "3"},
    )
    assert response.status_code == 403
    assert not _reviews(case).exists()


def _synthetic_review(organization, target_id: str, reviewed: int, kept: int) -> None:
    AuditEvent.objects.create(
        action=REVIEW_ACTION,
        organization=organization,
        target_type="hub.reconciliationsourcefile",
        target_id=target_id,
        metadata={"reviewed": reviewed, "kept": kept, "undone": reviewed - kept},
    )


@pytest.mark.parametrize("kept, passed", [(190, True), (189, False)])
def test_threshold_is_exact_integer_arithmetic(organization, kept, passed):
    _synthetic_review(organization, "a", 120, 120)
    _synthetic_review(organization, "b", 80, kept - 120)
    report = acceptance_report(organization.pk)
    assert report["reviewed"] == 200 and report["kept"] == kept
    assert report["threshold_passed"] is passed


def test_command_prints_read_only_report(case):
    _auto(case)
    _post(case)
    before = AuditEvent.objects.count()
    output = io.StringIO()
    call_command(
        "auto_confirmation_acceptance",
        organization=str(case["source"].organization_id),
        stdout=output,
    )
    report = json.loads(output.getvalue())
    assert report["reviewed"] == 3 and report["kept"] == 3 and report["precision_percent"] == 100
    assert AuditEvent.objects.count() == before
