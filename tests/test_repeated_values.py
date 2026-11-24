"""D-400: repeated-value groups of equal size are conferred automatically in direct use."""

from __future__ import annotations

import io
import json
from datetime import date
from types import SimpleNamespace

import pytest
from django.core.management import call_command
from tests.test_depara_ledger import BASE, _load, setup  # noqa: F401
from tests.test_direct_use import _october, enabled  # noqa: F401

from apps.hub import reconciliation_workbench
from apps.hub.auto_confirm import REPEATED_NOTE, auto_confirm_exact
from apps.hub.models import MovementReconciliation, NormalizedMovement
from apps.hub.reconciliation_service import undo_reconciliation

pytestmark = pytest.mark.django_db

BANK = [
    ("PIX ALESSANDRA", -91200),
    ("PIX LUANA", -91200),
    ("PIX SHPP", -20000),
    ("PIX SHPP", -20000),
    ("TARIFA", -555),
    ("TARIFA", -555),
]
# Two 912,00, two 200,00 in the Razão; only one 5,55: that group stays alone.
LEDGER = [
    ("PIX LUANA", -91200, "4.1"),
    ("PIX ALESSANDRA", -91200, "4.1"),
    ("PIX SHPP", -20000, "4.1"),
    ("PIX SHPP", -20000, "4.1"),
    ("TARIFA", -555, "4.1"),
]


def _confirmed(source):
    return {
        item.movement_id: item
        for item in MovementReconciliation.objects.filter(
            movement__source_file=source, state=MovementReconciliation.State.CONFIRMED
        ).select_related("movement", "entry")
    }


def _load_october(case, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        _load(case, BASE)
        return _october(case, BANK, LEDGER)


def test_equal_groups_are_conferred_and_unequal_groups_stay(
    enabled,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    source = _load_october(enabled, django_capture_on_commit_callbacks)
    confirmed = _confirmed(source)
    amounts = sorted(abs(item.movement.amount_cents) for item in confirmed.values())
    assert amounts == [20000, 20000, 91200, 91200]
    assert all(item.evidence["note"] == REPEATED_NOTE for item in confirmed.values())
    assert all(item.evidence["automatic"] for item in confirmed.values())
    # Each Razão record is used once.
    assert len({item.entry_id for item in confirmed.values()}) == 4
    tariffs = NormalizedMovement.objects.filter(source_file=source, amount_cents=-555)
    assert not any(movement.pk in confirmed for movement in tariffs)


def test_other_offices_keep_repeated_values_unconferred(
    setup,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    source = _load_october(setup, django_capture_on_commit_callbacks)
    assert _confirmed(source) == {}


def test_a_group_someone_undid_is_never_redone(
    enabled,  # noqa: F811
    django_capture_on_commit_callbacks,
):
    source = _load_october(enabled, django_capture_on_commit_callbacks)
    item = next(
        item for item in _confirmed(source).values() if abs(item.movement.amount_cents) == 91200
    )
    undo_reconciliation(reconciliation=item, actor=enabled["user"])
    auto_confirm_exact(source=source, month=date(2026, 10, 1), actor=enabled["user"])
    amounts = sorted(abs(i.movement.amount_cents) for i in _confirmed(source).values())
    assert amounts == [20000, 20000, 91200]  # the other 912,00 kept; the undone one stays out


def test_same_history_is_paired_first(monkeypatch):
    monkeypatch.setattr(reconciliation_workbench, "compatible_record", lambda m, r: True)

    def movement(key, text):
        return SimpleNamespace(source_key=key, pk=key, original_description=text, description="")

    def record(entry_id, text):
        return SimpleNamespace(
            entry_id=entry_id,
            entry=SimpleNamespace(occurred_on=date(2026, 9, 4), history=text),
        )

    bank = [movement("a", "PIX Alessandra"), movement("b", "PIX LUANA")]
    razao = [record("1", "pix  luana"), record("2", "PIX ALESSANDRA")]
    pairs = reconciliation_workbench._repeated_group_pairs(bank, razao, set())
    assert {(m.pk, r.entry_id) for m, r in pairs} == {("a", "2"), ("b", "1")}
    assert reconciliation_workbench._repeated_group_pairs(bank, razao[:1], set()) == []
    assert reconciliation_workbench._repeated_group_pairs(bank, razao, {"1"}) == []


def test_command_previews_then_applies(
    enabled,  # noqa: F811
    django_capture_on_commit_callbacks,
    settings,
):
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = []  # data loaded before D-400 existed
    source = _load_october(enabled, django_capture_on_commit_callbacks)
    assert _confirmed(source) == {}
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(enabled["org"].pk)]
    out = io.StringIO()
    call_command("conferir_repetidos", organization=enabled["org"].pk, stdout=out)
    preview = json.loads(out.getvalue())
    assert preview["apply"] is False and len(preview["pairs"]) == 4
    assert _confirmed(source) == {}
    out = io.StringIO()
    with django_capture_on_commit_callbacks(execute=True):
        call_command("conferir_repetidos", organization=enabled["org"].pk, apply=True, stdout=out)
    assert json.loads(out.getvalue()) == {"apply": True, "confirmed": 4}
    assert len(_confirmed(source)) == 4
    out = io.StringIO()
    call_command("conferir_repetidos", organization=enabled["org"].pk, apply=True, stdout=out)
    assert json.loads(out.getvalue())["confirmed"] == 0  # idempotent
