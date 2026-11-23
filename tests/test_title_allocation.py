import hashlib
import json
import stat
from copy import deepcopy
from dataclasses import FrozenInstanceError
from datetime import date, datetime

import pytest
from scripts.preview_title_allocations import main

from apps.hub.title_allocation import preview_title_allocations
from apps.hub.title_contract import CONTRACT, TitleContractError


def sources():
    titles = {
        "contract": CONTRACT,
        "company_key": "synthetic-company",
        "account_reference": "synthetic-bank",
        "as_of": "2026-09-30",
        "settlements_complete": True,
        "titles": [
            {
                "key": "title-1",
                "kind": "payable",
                "installments": [
                    {
                        "key": "01",
                        "due_on": "2026-10-01",
                        "principal_cents": 10000,
                        "outstanding_cents": 4000,
                        "settlements": [
                            {
                                "key": "payment-1",
                                "posted_on": "2026-09-12",
                                "principal_cents": 6000,
                                "interest_cents": 150,
                                "penalty_cents": 50,
                                "fees_cents": 25,
                                "discount_cents": 100,
                                "cash_cents": 6125,
                                "direction": "outflow",
                                "reverses": None,
                            }
                        ],
                    }
                ],
            }
        ],
    }
    bank = {
        "contract": "bank-cash-normalized-v1",
        "company_key": "synthetic-company",
        "account_reference": "synthetic-bank",
        "period_start": "2026-09-01",
        "period_end": "2026-09-30",
        "movements": [
            {
                "key": "bank-1",
                "occurred_on": "2026-09-12",
                "cash_cents": 6125,
                "direction": "outflow",
            }
        ],
    }
    allocations = [
        {
            "movement_key": "bank-1",
            "title_key": "title-1",
            "installment_key": "01",
            "settlement_key": "payment-1",
            "cash_cents": 6125,
        }
    ]
    return titles, bank, allocations


def preview(titles, bank, allocations, **overrides):
    scope = {
        "company_key": "synthetic-company",
        "account_reference": "synthetic-bank",
        "period_start": date(2026, 9, 1),
        "period_end": date(2026, 9, 30),
    }
    return preview_title_allocations(titles, bank, allocations, **(scope | overrides))


def test_effective_cash_capacity_preserves_components_and_always_requires_review():
    titles, bank, allocations = sources()
    before = deepcopy((titles, bank, allocations))
    result = preview(titles, bank, allocations)
    assert result.requires_review is True
    assert result.movements[0].remaining_cents == result.settlements[0].remaining_cents == 0
    payment = result.settlements[0].settlement
    assert (payment.principal_cents, payment.cash_cents) == (6000, 6125)
    assert (payment.interest_cents, payment.penalty_cents) == (150, 50)
    assert (payment.fees_cents, payment.discount_cents) == (25, 100)
    assert (titles, bank, allocations) == before
    with pytest.raises(FrozenInstanceError):
        result.requires_review = False


def test_no_match_is_created_from_equal_amount_date_or_due_date():
    titles, bank, _ = sources()
    result = preview(titles, bank, [])
    assert not result.allocations
    assert result.movements[0].remaining_cents == result.settlements[0].remaining_cents == 6125
    titles["titles"][0]["installments"][0].update(settlements=[], outstanding_cents=10000)
    result = preview(titles, bank, [])
    assert not result.settlements
    assert result.movements[0].remaining_cents == 6125


def test_grouped_payment_uses_separate_title_capacities_even_when_local_keys_repeat():
    titles, bank, allocations = sources()
    second = deepcopy(titles["titles"][0])
    second["key"] = "title-2"
    titles["titles"].append(second)
    bank["movements"][0]["cash_cents"] *= 2
    allocations.append({**allocations[0], "title_key": "title-2"})
    result = preview(titles, bank, allocations)
    assert len(result.settlements) == 2
    assert all(item.remaining_cents == 0 for item in result.settlements)
    assert result.movements[0].remaining_cents == 0


def test_partial_allocation_and_split_bank_payments_keep_capacity_in_both_directions():
    titles, bank, allocations = sources()
    allocations[0]["cash_cents"] = 3000
    partial = preview(titles, bank, allocations)
    assert partial.movements[0].remaining_cents == 3125
    assert partial.settlements[0].remaining_cents == 3125
    bank["movements"][0]["cash_cents"] = 3000
    bank["movements"].append({**bank["movements"][0], "key": "bank-2", "cash_cents": 3125})
    allocations.append({**allocations[0], "movement_key": "bank-2", "cash_cents": 3125})
    result = preview(titles, bank, allocations)
    assert all(item.remaining_cents == 0 for item in result.movements)
    assert result.settlements[0].remaining_cents == 0


def test_receivables_and_reversal_have_explicit_gross_cash_flows_without_netting():
    titles, bank, allocations = sources()
    title = titles["titles"][0]
    title["kind"] = "receivable"
    part = title["installments"][0]
    payment = part["settlements"][0]
    payment["direction"] = "inflow"
    part["settlements"].append(
        {
            **payment,
            "key": "reversal",
            "posted_on": "2026-09-13",
            "reverses": "payment-1",
            "direction": "outflow",
        }
    )
    part["outstanding_cents"] = 10000
    bank["movements"][0]["direction"] = "inflow"
    bank["movements"].append(
        {
            **bank["movements"][0],
            "key": "bank-2",
            "occurred_on": "2026-09-13",
            "direction": "outflow",
        }
    )
    allocations.append({**allocations[0], "movement_key": "bank-2", "settlement_key": "reversal"})
    result = preview(titles, bank, allocations)
    assert len(result.settlements) == 2
    assert sum(item.allocated_cents for item in result.settlements) == 12250
    assert {item.settlement.direction for item in result.settlements} == {"inflow", "outflow"}
    assert all(item.remaining_cents == 0 for item in result.settlements)


def test_date_difference_and_incomplete_source_stay_explicit():
    titles, bank, allocations = sources()
    titles["settlements_complete"] = False
    bank["movements"][0]["occurred_on"] = "2026-09-14"
    result = preview(titles, bank, allocations)
    assert result.allocations[0].date_difference is True
    assert result.source_settlements_complete is False
    assert result.requires_review is True


@pytest.mark.parametrize("source", ["titles", "bank"])
@pytest.mark.parametrize("field", ["company_key", "account_reference", "contract"])
def test_scope_mismatch_is_rejected_for_each_source(source, field):
    titles, bank, allocations = sources()
    (titles if source == "titles" else bank)[field] = "another-scope"
    with pytest.raises(TitleContractError):
        preview(titles, bank, allocations)


@pytest.mark.parametrize(
    "change",
    [
        "bank_period",
        "bank_date",
        "bank_direction",
        "duplicate_bank",
        "missing_bank_field",
        "extra_bank_field",
        "unknown_bank",
        "unknown_title",
        "unknown_part",
        "unknown_payment",
        "duplicate_pair",
        "wrong_direction",
        "out_of_period_payment",
        "bank_overallocated",
        "payment_overallocated",
    ],
)
def test_invalid_plan_is_rejected_whole_without_mutation(change):
    titles, bank, allocations = sources()
    if change == "bank_period":
        bank["period_start"] = "2026-08-01"
    elif change == "bank_date":
        bank["movements"][0]["occurred_on"] = "2026-08-31"
    elif change == "bank_direction":
        bank["movements"][0]["direction"] = ["outflow"]
    elif change == "duplicate_bank":
        bank["movements"].append(deepcopy(bank["movements"][0]))
    elif change == "missing_bank_field":
        del bank["account_reference"]
    elif change == "extra_bank_field":
        bank["guessed_bank_account"] = "not-allowed"
    elif change.startswith("unknown_"):
        field = {
            "unknown_bank": "movement_key",
            "unknown_title": "title_key",
            "unknown_part": "installment_key",
            "unknown_payment": "settlement_key",
        }[change]
        allocations[0][field] = "missing"
    elif change == "duplicate_pair":
        allocations.append(deepcopy(allocations[0]))
    elif change == "wrong_direction":
        bank["movements"][0]["direction"] = "inflow"
    elif change == "out_of_period_payment":
        titles["titles"][0]["installments"][0]["settlements"][0]["posted_on"] = "2026-08-31"
    elif change == "bank_overallocated":
        second = deepcopy(titles["titles"][0])
        second["key"] = "title-2"
        titles["titles"].append(second)
        allocations.append({**allocations[0], "title_key": "title-2"})
    else:
        bank["movements"].append({**bank["movements"][0], "key": "bank-2"})
        allocations.append({**allocations[0], "movement_key": "bank-2"})
    before = deepcopy((titles, bank, allocations))
    with pytest.raises(TitleContractError):
        preview(titles, bank, allocations)
    assert (titles, bank, allocations) == before


@pytest.mark.parametrize("value", [True, False, 0, -1, 1.5, "6125", None, 2**63])
@pytest.mark.parametrize("target", ["movement", "allocation"])
def test_cash_values_are_strict_positive_integer_cents(value, target):
    titles, bank, allocations = sources()
    (bank["movements"][0] if target == "movement" else allocations[0])["cash_cents"] = value
    with pytest.raises(TitleContractError):
        preview(titles, bank, allocations)


@pytest.mark.parametrize(
    "overrides",
    [
        {"period_start": date(2026, 10, 1)},
        {"period_end": date(2026, 10, 1)},
        {"period_start": datetime(2026, 9, 1)},
        {"period_end": "2026-09-30"},
    ],
)
def test_invalid_or_uncovered_period_is_rejected(overrides):
    titles, bank, allocations = sources()
    with pytest.raises(TitleContractError, match="Período"):
        preview(titles, bank, allocations, **overrides)


def test_fingerprint_is_order_independent_and_changes_with_source_or_manual_selection():
    titles, bank, allocations = sources()
    second = deepcopy(titles["titles"][0])
    second["key"] = "title-2"
    titles["titles"].append(second)
    bank["movements"].append({**bank["movements"][0], "key": "bank-2"})
    allocations.append({**allocations[0], "movement_key": "bank-2", "title_key": "title-2"})
    first = preview(titles, bank, allocations)
    titles["titles"].reverse()
    bank["movements"].reverse()
    allocations.reverse()
    assert preview(titles, bank, allocations) == first
    allocations[0]["cash_cents"] -= 1
    assert preview(titles, bank, allocations).fingerprint != first.fingerprint
    allocations[0]["cash_cents"] += 1
    bank["movements"][0]["occurred_on"] = "2026-09-13"
    assert preview(titles, bank, allocations).fingerprint != first.fingerprint


def test_preview_is_bounded_across_movements_settlements_and_allocations(monkeypatch):
    titles, bank, allocations = sources()
    monkeypatch.setattr("apps.hub.title_allocation.MAX_ITEMS", 2)
    with pytest.raises(TitleContractError, match="limite global"):
        preview(titles, bank, allocations)


def cli_files(tmp_path):
    paths = []
    args = []
    for name, payload in zip(("titles", "bank", "allocations"), sources(), strict=True):
        path = tmp_path / f"{name}.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        paths.append(path)
        args.extend((f"--{name}", str(path)))
    output = tmp_path / "private-preview.json"
    args.extend(
        (
            "--company-key",
            "synthetic-company",
            "--account-reference",
            "synthetic-bank",
            "--start",
            "2026-09-01",
            "--end",
            "2026-09-30",
            "--output",
            str(output),
        )
    )
    return args, paths, output


def test_cli_produces_private_complete_report_with_original_source_hashes(tmp_path, capsys):
    args, paths, output = cli_files(tmp_path)
    before = [path.read_bytes() for path in paths]
    assert main(args) == 0
    report = json.loads(output.read_text())
    assert report["status"] == "requires_review"
    assert report["erp_written"] is report["persisted_allocations"] is False
    assert report["preview"]["requires_review"] is True
    assert report["preview"]["period_start"] == "2026-09-01"
    assert report["preview"]["settlements"][0]["settlement"]["interest_cents"] == 150
    assert report["source_sha256"] == {
        key: hashlib.sha256(content).hexdigest()
        for key, content in zip(("titles", "bank", "allocations"), before, strict=True)
    }
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert [path.read_bytes() for path in paths] == before
    assert "synthetic-company" not in capsys.readouterr().out
    assert not list(tmp_path.glob(".cica-preview-*"))


@pytest.mark.parametrize("symlink", [False, True])
def test_cli_never_overwrites_existing_destination_or_symlink(tmp_path, symlink):
    args, paths, output = cli_files(tmp_path)
    before = [path.read_bytes() for path in paths]
    if symlink:
        output.symlink_to(paths[0])
    else:
        output.write_text("preserve-me")
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert [path.read_bytes() for path in paths] == before
    assert output.is_symlink() if symlink else output.read_text() == "preserve-me"
    assert not list(tmp_path.glob(".cica-preview-*"))


@pytest.mark.parametrize("content", [b'{"company_key":"a","company_key":"b"}', b"\xff", b"[]oops"])
def test_cli_rejects_ambiguous_or_invalid_json_before_creating_output(tmp_path, content):
    args, paths, output = cli_files(tmp_path)
    paths[0].write_bytes(content)
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert not output.exists()
    assert not list(tmp_path.glob(".cica-preview-*"))


def test_cli_refuses_large_source_and_partial_publication(tmp_path, monkeypatch):
    args, _, output = cli_files(tmp_path)
    with monkeypatch.context() as patch:
        patch.setattr("scripts.preview_title_allocations.MAX_SOURCE_BYTES", 20)
        with pytest.raises(SystemExit):
            main(args)
    assert not output.exists()

    def failed_fsync(_):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr("scripts.preview_title_allocations.os.fsync", failed_fsync)
    with pytest.raises(SystemExit):
        main(args)
    assert not output.exists()
    assert not list(tmp_path.glob(".cica-preview-*"))
