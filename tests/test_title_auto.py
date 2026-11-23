"""D-394: automatic interpretation of captured titles (C01/C02) for direct-use offices."""

from __future__ import annotations

import io
import json
from datetime import date

import pytest
from django.core.management import call_command

from apps.audit.models import AuditEvent
from apps.hub.models import ReconciliationTitleSnapshot
from apps.hub.title_auto import ACTION, RULES, _decision, interpret_capture, interpret_company
from apps.hub.title_persistence import _load, latest_title_snapshot
from apps.hub.title_read_model import build_title_workspace
from apps.hub.title_robot import ROBOT_EMAIL, is_title_robot, title_robot
from apps.intelligence.native_title_comparison import (
    NativeTitleComparisonError,
    load_capture_for_routine,
)
from apps.intelligence.native_title_contract import manifest
from test_native_titles import complete
from test_native_titles import fiscal as fiscal_fixture

fiscal = fiscal_fixture
pytestmark = pytest.mark.django_db


def _rows(family, rows):
    spec = manifest()["families"][family]
    suffix = spec["payment_type_field"].split("_", 1)[1]
    return spec, {
        f"r{index}": {
            spec["payment_date_field"]: date_,
            spec["payment_number_field"]: number,
            spec["payment_type_field"]: kind,
            f"vpag_{suffix}": amount,
        }
        for index, (date_, number, kind, amount) in enumerate(rows)
    }


def test_c01_withholding_stays_out_of_cash():
    spec, payments = _rows(
        "entradas", [("2026-09-10", 1, 1, "759.22"), ("2026-09-10", 1, 9, "37.62")]
    )
    part = {"vlor_entp": "759.22", "vbru_entp": "808.97"}
    decision = _decision("entradas", spec, part, "ref", payments, "2026-09-30")
    assert decision["kind"] == "payable" and decision["principal_field"] == "vlor_entp"
    [event] = decision["settlements"]
    assert sorted(event["payment_references"]) == ["r0", "r1"]  # CRF kept in provenance
    normalized = event["normalized"]
    assert (normalized["cash_cents"], normalized["principal_cents"]) == (75922, 75922)
    assert normalized["direction"] == "outflow"


def test_c02_interest_is_already_inside_type_1():
    spec, payments = _rows("saidas", [("2026-09-10", 1, 1, "502.00"), ("2026-09-10", 1, 2, "2.00")])
    part = {"vlor_saip": "500.00", "vbru_saip": "500.00"}
    decision = _decision("saidas", spec, part, "ref", payments, "2026-09-30")
    normalized = decision["settlements"][0]["normalized"]
    assert decision["kind"] == "receivable"
    assert (
        normalized["cash_cents"],
        normalized["interest_cents"],
        normalized["principal_cents"],
        normalized["direction"],
    ) == (50200, 200, 50000, "inflow")


@pytest.mark.parametrize(
    "rows",
    [
        [("2026-09-10", 1, 1, "-2.00")],  # reversal not proven
        [("2026-09-10", 1, 5, "10.00")],  # type outside the official list
        [("2026-09-10", 1, 9, "10.00")],  # withholding without cash
        [("2026-09-10", 1, 1, "80.00"), ("2026-09-11", 2, 1, "30.00")],  # above principal
        [("2026-10-03", 1, 1, "10.00")],  # after the captured month
    ],
)
def test_unproven_cases_stay_uninterpreted(rows):
    spec, payments = _rows("entradas", rows)
    assert _decision("entradas", spec, {"vlor_entp": "100.00"}, "r", payments, "2026-09-30") is None


def test_services_have_no_automatic_reading():
    assert set(RULES) == {"entradas", "saidas"}


def test_capture_is_interpreted_once_by_the_robot(
    fiscal, settings, django_capture_on_commit_callbacks
):
    agent, account, user, job, data, _ = fiscal
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(account.organization_id)]
    with django_capture_on_commit_callbacks(execute=True):
        assert complete(agent, job, data).status_code == 200  # triggers the worker task
    snapshot = latest_title_snapshot(account)
    assert snapshot is not None
    assert is_title_robot(snapshot.reviewed_by)
    payload, _ = _load(snapshot, account)
    [title] = payload["titles"]
    assert title["kind"] == "payable"
    [part] = title["installments"]
    assert part["principal_cents"] == 10000
    assert sorted(s["cash_cents"] for s in part["settlements"]) == [3000, 4000]
    event = AuditEvent.objects.get(action=ACTION)
    assert event.metadata["skipped"] == 1  # the Saídas row with a negative amount
    assert event.metadata["decision"] == "D-394"
    again = interpret_capture(job.pk, account.organization_id)
    assert again["status"] == "ja_interpretado"
    assert ReconciliationTitleSnapshot.objects.count() == 1
    workspace = build_title_workspace(
        account=account, actor=user, start=date(2026, 9, 1), end=date(2026, 9, 30)
    )
    assert workspace["title_rows"] and not workspace["blocking"]


def test_offices_outside_direct_use_keep_human_review(fiscal, django_capture_on_commit_callbacks):
    agent, account, _, job, data, _ = fiscal
    with django_capture_on_commit_callbacks(execute=True):
        assert complete(agent, job, data).status_code == 200
    assert latest_title_snapshot(account) is None
    with pytest.raises(NativeTitleComparisonError):
        load_capture_for_routine(job.pk, account.organization_id)
    assert interpret_company(account.company) == []


def test_robot_cannot_log_in_and_is_not_a_member(fiscal):
    robot = title_robot()
    assert robot.email == ROBOT_EMAIL and not robot.is_active
    assert not robot.has_usable_password()
    from apps.organizations.models import Membership

    assert not Membership.objects.filter(user=robot).exists()


def test_command_lists_then_applies(fiscal, settings):
    agent, account, _, job, data, _ = fiscal
    assert complete(agent, job, data).status_code == 200
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(account.organization_id)]
    dry = io.StringIO()
    call_command("titulos_auto", organization=str(account.organization_id), stdout=dry)
    assert json.loads(dry.getvalue())["captures"] == 1
    assert latest_title_snapshot(account) is None
    out = io.StringIO()
    call_command("titulos_auto", organization=str(account.organization_id), apply=True, stdout=out)
    totals = json.loads(out.getvalue())
    assert totals["interpretado"] == 1 and totals.get("erro", 0) == 0
    assert latest_title_snapshot(account) is not None


def test_automatic_titles_show_note_and_installment(
    fiscal, settings, django_capture_on_commit_callbacks
):
    """D-396: the screen, report and CSV read the note/installment, not the hash."""
    from apps.hub.title_labels import enrich_title_labels

    agent, account, user, job, data, _ = fiscal
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(account.organization_id)]
    with django_capture_on_commit_callbacks(execute=True):
        assert complete(agent, job, data).status_code == 200
    workspace = build_title_workspace(
        account=account, actor=user, start=date(2026, 9, 1), end=date(2026, 9, 30)
    )
    enrich_title_labels(data=workspace, account=account, actor=user)
    [row] = workspace["installment_rows"]
    assert row["title_label"].startswith("Entradas · ")
    assert "0001/A" in row["title_label"]  # numero_titulo of the synthetic source
    assert row["installment_label"] == "1"
    assert all(s["settlement_label"].startswith("Baixa ") for s in workspace["settlement_rows"])
