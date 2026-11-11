from __future__ import annotations

from copy import deepcopy
from dataclasses import replace
from datetime import date

import pytest

from apps.hub.dominio_journal_normalization import (
    JournalNormalizationError,
    JournalScope,
    normalize_journal_snapshot,
)


def sample():
    scope = JournalScope(
        company_code=212,
        chart_company_code=212,
        bank_account_code=8,
        branch_codes=frozenset({0}),
        account_codes=frozenset({8, 20, 30}),
        absent_account_code=0,
        bank_inflow_side="debit",
        period_start=date(2026, 9, 1),
        period_end_exclusive=date(2026, 10, 1),
        expected_lot_rows=((10, 3),),
        expected_bank_effects=1,
    )
    shared = {
        "company_code": 212,
        "chart_company_code": 212,
        "lot_code": 10,
        "branch_code": 0,
        "occurred_on": "2026-09-03",
        "history": "Histórico sintético",
        "document": "123",
    }
    rows = [
        {
            **shared,
            "row_code": 1,
            "debit_account_code": 8,
            "credit_account_code": 0,
            "amount": "100.00",
        },
        {
            **shared,
            "row_code": 2,
            "debit_account_code": 0,
            "credit_account_code": 20,
            "amount": "60.00",
        },
        {
            **shared,
            "row_code": 3,
            "debit_account_code": 0,
            "credit_account_code": 30,
            "amount": "40.00",
        },
    ]
    return rows, scope


def test_unilateral_rows_preserve_all_parties_of_the_source_lot():
    rows, scope = sample()
    before = deepcopy(rows)
    result = normalize_journal_snapshot(rows, scope)
    assert (result.source_rows, result.journals, result.bank_effects) == (3, 1, 1)
    assert [(p.account_code, p.side, p.amount_cents, p.cash_direction) for p in result.parties] == [
        ("8", "debit", 10000, "inflow"),
        ("20", "credit", 6000, ""),
        ("30", "credit", 4000, ""),
    ]
    assert len({p.entry_key for p in result.parties}) == 1
    assert len({p.line_key for p in result.parties}) == 3
    assert result.requires_source_review and not result.financial_collection_enabled
    assert rows == before
    assert normalize_journal_snapshot(list(reversed(rows)), scope) == result
    assert list(result.contract_rows()[0]) == [
        "entry_key",
        "line_key",
        "date",
        "history",
        "account_code",
        "side",
        "amount_cents",
        "cash_direction",
        "document",
    ]


def test_bilateral_record_becomes_two_explicit_parties_not_two_source_records():
    rows, scope = sample()
    rows = [{**rows[0], "credit_account_code": 20, "amount": "0.01"}]
    result = normalize_journal_snapshot(rows, replace(scope, expected_lot_rows=((10, 1),)))
    assert result.source_rows == 1
    assert len(result.parties) == 2
    assert all(p.amount_cents == 1 for p in result.parties)


def test_bank_direction_is_explicit_in_context_not_inferred_from_amount():
    rows, scope = sample()
    result = normalize_journal_snapshot(rows, replace(scope, bank_inflow_side="credit"))
    assert result.parties[0].cash_direction == "outflow"


@pytest.mark.parametrize(
    "amount",
    [
        "0",
        "-1.00",
        "1.001",
        "1e2",
        "NaN",
        "1,00",
        " 1.00",
        "\u0661.\u0660\u0660",
        100.0,
        "1000000000000.00",
        None,
    ],
)
def test_never_rounds_or_takes_absolute_value_of_source_amount(amount):
    rows, scope = sample()
    rows[0]["amount"] = amount
    with pytest.raises(JournalNormalizationError):
        normalize_journal_snapshot(rows, scope)


@pytest.mark.parametrize(
    "case",
    [
        "wrong_company",
        "wrong_plan",
        "unknown_account",
        "unknown_branch",
        "outside_period",
        "duplicate_row",
        "missing_source_row",
        "wrong_lot_count",
        "missing_lot",
        "unbalanced",
        "no_side",
        "multiple_bank_effects",
        "different_history",
        "different_document",
        "different_date",
        "blank_history",
        "oversized_history",
        "history_padding",
        "history_control",
        "invalid_date",
        "unknown_field",
        "float_id",
        "boolean_id",
        "absent_side_is_real_account",
        "unknown_direction",
        "duplicate_lot_manifest",
        "mixed_branches",
        "whole_period_balance_only",
    ],
)
def test_refuses_incomplete_scopes_or_unsupported_journals(case):
    rows, scope = sample()
    if case == "wrong_company":
        rows[0]["company_code"] = 999
    elif case == "wrong_plan":
        rows[0]["chart_company_code"] = 999
    elif case == "unknown_account":
        rows[1]["credit_account_code"] = 999
    elif case == "unknown_branch":
        rows[0]["branch_code"] = 1
    elif case == "outside_period":
        rows[0]["occurred_on"] = "2026-10-01"
    elif case == "duplicate_row":
        rows[1]["row_code"] = rows[0]["row_code"]
    elif case == "missing_source_row":
        rows.pop()
    elif case == "wrong_lot_count":
        scope = replace(scope, expected_lot_rows=((10, 2), (11, 1)), expected_bank_effects=2)
    elif case == "missing_lot":
        rows[0]["lot_code"] = 99
    elif case == "unbalanced":
        rows[0]["amount"] = "99.99"
    elif case == "no_side":
        rows[0].update(debit_account_code=0, credit_account_code=0)
    elif case == "multiple_bank_effects":
        rows[1]["credit_account_code"] = 8
    elif case == "different_history":
        rows[1]["history"] = "Outro histórico preservado"
    elif case == "different_document":
        rows[1]["document"] = "456"
    elif case == "different_date":
        rows[1]["occurred_on"] = "2026-09-04"
    elif case == "blank_history":
        rows[0]["history"] = ""
    elif case == "oversized_history":
        rows[0]["history"] = "x" * 501
    elif case == "history_padding":
        rows[0]["history"] = " não remover espaço"
    elif case == "history_control":
        rows[0]["history"] = "não remover\x00controle"
    elif case == "invalid_date":
        rows[0]["occurred_on"] = "2026-09-31"
    elif case == "unknown_field":
        rows[0]["password"] = "synthetic-private-value"
    elif case == "float_id":
        rows[0]["row_code"] = 1.0
    elif case == "boolean_id":
        rows[0]["branch_code"] = False
    elif case == "absent_side_is_real_account":
        scope = replace(scope, account_codes=scope.account_codes | {0})
    elif case == "unknown_direction":
        scope = replace(scope, bank_inflow_side="unknown")
    elif case == "duplicate_lot_manifest":
        scope = replace(scope, expected_lot_rows=((10, 1), (10, 2)), expected_bank_effects=2)
    elif case == "mixed_branches":
        scope = replace(scope, branch_codes=frozenset({0, 1}))
        rows[1]["branch_code"] = 1
    elif case == "whole_period_balance_only":
        rows[1]["lot_code"] = rows[2]["lot_code"] = 11
        scope = replace(scope, expected_lot_rows=((10, 1), (11, 2)), expected_bank_effects=2)
    with pytest.raises(JournalNormalizationError) as error:
        normalize_journal_snapshot(rows, scope)
    assert "synthetic-private-value" not in str(error.value)


def test_balanced_prefix_cannot_hide_a_missing_zero_or_cancelling_source_record():
    rows, scope = sample()
    balanced_prefix = [{**rows[0], "credit_account_code": 20}]
    # The supplied row alone balances, but the manifest says three source rows.
    with pytest.raises(JournalNormalizationError, match="Snapshot incompleto"):
        normalize_journal_snapshot(balanced_prefix, scope)
