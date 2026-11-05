from copy import deepcopy

import pytest

from apps.hub.title_contract import CONTRACT, TitleContractError, validate_title_snapshot


def snapshot():
    return {
        "contract": CONTRACT,
        "company_key": "synthetic-company",
        "account_reference": "001:123",
        "as_of": "2026-09-30",
        "settlements_complete": True,
        "titles": [
            {
                "key": "title-1",
                "kind": "payable",
                "installments": [
                    {
                        "key": "01",
                        "due_on": "2026-09-01",
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


def validate(payload):
    return validate_title_snapshot(
        payload, company_key="synthetic-company", account_reference="001:123"
    )


def test_partial_payment_preserves_all_components_and_does_not_infer_due_date_payment():
    data = snapshot()
    result = validate(data)
    part = result.titles[0].installments[0]
    assert part.outstanding_cents == 4000
    assert part.settlements[0].cash_cents == 6125
    data["titles"][0]["installments"][0].update(settlements=[], outstanding_cents=10000)
    assert not validate(data).titles[0].installments[0].settlements


def test_unknown_balances_and_incomplete_coverage_stay_unknown():
    data = snapshot()
    data["settlements_complete"] = False
    data["titles"][0]["installments"][0].update(outstanding_cents=None, due_on=None)
    result = validate(data)
    assert result.settlements_complete is False
    assert result.titles[0].installments[0].outstanding_cents is None
    assert result.titles[0].installments[0].due_on is None


def test_full_reversal_is_linked_explicitly_and_restores_principal_capacity():
    data = snapshot()
    part = data["titles"][0]["installments"][0]
    original = part["settlements"][0]
    part["settlements"].insert(
        0,
        {
            **original,
            "key": "reversal-1",
            "reverses": original["key"],
            "posted_on": "2026-09-13",
            "direction": "inflow",
        },
    )
    part["outstanding_cents"] = 10000
    assert len(validate(data).titles[0].installments[0].settlements) == 2
    part["settlements"].append({**part["settlements"][0], "key": "second-reversal"})
    with pytest.raises(TitleContractError, match="Estorno"):
        validate(data)


@pytest.mark.parametrize("value", [True, False, -1, 1.5, "100", None, 2**63])
def test_amounts_are_explicit_integer_cents(value):
    data = snapshot()
    data["titles"][0]["installments"][0]["settlements"][0]["cash_cents"] = value
    with pytest.raises(TitleContractError):
        validate(data)


@pytest.mark.parametrize(
    "change",
    [
        "company",
        "account",
        "contract",
        "missing",
        "extra",
        "kind",
        "raw_date",
        "future",
        "amount",
        "direction",
        "duplicate_title",
        "duplicate_part",
        "duplicate_payment",
        "balance",
        "overpaid",
        "unlinked_reversal",
        "partial_reversal",
        "early_reversal",
    ],
)
def test_invalid_snapshot_is_rejected_whole_without_mutating_input(change):
    data = snapshot()
    title = data["titles"][0]
    part = title["installments"][0]
    payment = part["settlements"][0]
    if change in {"company", "account", "contract"}:
        data[{"company": "company_key", "account": "account_reference"}.get(change, change)] = (
            "other"
        )
    elif change == "missing":
        del payment["posted_on"]
    elif change == "extra":
        payment["raw_erp_type"] = "D"
    elif change == "kind":
        title["kind"] = ["payable"]
    elif change == "raw_date":
        payment["posted_on"] = "12/09/2026"
    elif change == "future":
        payment["posted_on"] = "2026-10-01"
    elif change == "amount":
        payment["cash_cents"] += 1
    elif change == "direction":
        payment["direction"] = "inflow"
    elif change == "duplicate_title":
        data["titles"].append(deepcopy(title))
    elif change == "duplicate_part":
        title["installments"].append(deepcopy(part))
    elif change == "duplicate_payment":
        part["settlements"].append(deepcopy(payment))
    elif change == "balance":
        part["outstanding_cents"] += 1
    elif change == "overpaid":
        payment.update(principal_cents=20000, cash_cents=20125)
    elif change == "unlinked_reversal":
        payment.update(reverses="missing", direction="inflow")
    else:
        reversal = {**payment, "key": "reversal", "reverses": payment["key"], "direction": "inflow"}
        if change == "partial_reversal":
            reversal.update(principal_cents=3000, cash_cents=3125)
        else:
            reversal["posted_on"] = "2026-09-11"
        part["settlements"].append(reversal)
    before = deepcopy(data)
    with pytest.raises(TitleContractError):
        validate(data)
    assert data == before


def test_fingerprint_ignores_physical_order_and_handles_200_synthetic_titles():
    data = snapshot()
    original = deepcopy(data["titles"][0])
    data["titles"] = [{**deepcopy(original), "key": f"title-{i}"} for i in range(200)]
    first = validate(data)
    data["titles"].reverse()
    assert len(first.titles) == 200
    assert validate(data).fingerprint == first.fingerprint
    data["titles"][0]["installments"][0]["due_on"] = "2026-09-02"
    assert validate(data).fingerprint != first.fingerprint
