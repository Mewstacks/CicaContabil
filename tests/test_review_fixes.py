"""D-396: fixes for the serious defects found by the 23/11/2026 CONTAD review."""

from __future__ import annotations

from datetime import date

import pytest
from tests.test_depara_ledger import BASE, _load, setup  # noqa: F401
from tests.test_direct_use import OCTOBER_BANK, OCTOBER_LEDGER, _october

from apps.hub.auto_confirm import auto_confirm_exact
from apps.hub.models import (
    JournalEntry,
    MovementReconciliation,
    NormalizedMovement,
    ReconciliationRule,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_service import ReconciliationError, undo_reconciliation

pytestmark = pytest.mark.django_db


def test_automatic_confirmation_never_redoes_an_undo(setup):  # noqa: F811
    source = _load(setup, BASE)
    allocation = MovementReconciliation.objects.filter(
        movement__description="TARIFA BANCARIA", state="confirmed"
    ).first()
    undo_reconciliation(reconciliation=allocation, actor=setup["user"])
    again = auto_confirm_exact(source=source, month=date(2026, 9, 1), actor=setup["user"])
    assert again == 0
    allocation.refresh_from_db()
    assert allocation.state == MovementReconciliation.State.UNDONE


def test_one_failing_pair_does_not_void_the_others(setup, monkeypatch):  # noqa: F811
    import apps.hub.reconciliation_service as service

    original = service.confirm_reconciliation

    def flaky(*, movement, **kwargs):
        if movement.description == "PAGAMENTO A":
            raise ReconciliationError("Lançamento já exportado")
        return original(movement=movement, **kwargs)

    _load(setup, BASE)  # creates the synthetic chart the Razão CSV needs
    monkeypatch.setattr(service, "confirm_reconciliation", flaky)
    _october(
        setup,
        [("PAGAMENTO A", -1111), ("PAGAMENTO B", -2222)],
        [("PAGAMENTO A", -1111, "4.1"), ("PAGAMENTO B", -2222, "4.1")],
    )
    states = dict(
        NormalizedMovement.objects.filter(description__startswith="PAGAMENTO").values_list(
            "description", "reconciliations__state"
        )
    )
    assert states == {"PAGAMENTO A": None, "PAGAMENTO B": "confirmed"}


def _direct(setup, settings):  # noqa: F811
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(setup["org"].pk)]


def test_retired_rule_withdraws_its_unexported_entries(
    setup,  # noqa: F811
    settings,
    django_capture_on_commit_callbacks,
):
    _direct(setup, settings)
    with django_capture_on_commit_callbacks(execute=True):
        _load(setup, BASE)
        _october(setup, OCTOBER_BANK, OCTOBER_LEDGER)
    entry = JournalEntry.objects.get(movement__description="LIQUIDACAO BOLETO 777")
    assert entry.state == JournalEntry.State.APPROVED
    rule = entry.movement.applied_rule
    # A later month books the same pattern elsewhere: the rule loses its evidence and retires.
    with django_capture_on_commit_callbacks(execute=True):
        _load(setup, [("LIQUIDACAO BOLETO 1", -8001, "6.1")], month="11", tag="r")
    rule.refresh_from_db()
    entry.refresh_from_db()
    movement = NormalizedMovement.objects.get(description="LIQUIDACAO BOLETO 777")
    assert rule.state == ReconciliationRule.State.DISABLED
    assert entry.state == JournalEntry.State.INVALID
    assert movement.classification_source == NormalizedMovement.ClassificationSource.NONE
    assert not movement.journal_entries.exclude(state=JournalEntry.State.INVALID).exists()


def test_exported_entries_of_a_retired_rule_are_preserved(
    setup,  # noqa: F811
    settings,
    django_capture_on_commit_callbacks,
):
    from apps.hub.direct_use import withdraw_rule_entries

    _direct(setup, settings)
    with django_capture_on_commit_callbacks(execute=True):
        _load(setup, BASE)
        _october(setup, OCTOBER_BANK, OCTOBER_LEDGER)
    entry = JournalEntry.objects.get(movement__description="LIQUIDACAO BOLETO 777")
    JournalEntry.objects.filter(pk=entry.pk).update(state=JournalEntry.State.EXPORTED)
    assert withdraw_rule_entries(entry.movement.applied_rule) == 0
    entry.refresh_from_db()
    assert entry.state == JournalEntry.State.EXPORTED


def test_sources_are_still_bank_statements(setup):  # noqa: F811
    _load(setup, BASE)
    assert ReconciliationSourceFile.objects.filter(origin="bank_statement").exists()
