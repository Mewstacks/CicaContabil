import pytest

from apps.hub.dre import DreMapping, calculate_dre


def test_dre_requires_explicit_mapping_and_keeps_source_balance_sign() -> None:
    result = calculate_dre(
        balances_cents={"3.01": -120_000, "4.01": 35_000, "9.99": 2_000},
        mappings=[
            DreMapping(account_code="3.01", group="Receita líquida", sign=-1),
            DreMapping(account_code="4.01", group="Despesas", sign=-1),
        ],
    )

    assert result.groups_cents == {"Receita líquida": 120_000, "Despesas": -35_000}
    assert result.result_cents == 85_000
    assert result.unmapped_account_codes == ("9.99",)
    assert not result.complete


def test_dre_refuses_invalid_mapping_sign() -> None:
    with pytest.raises(ValueError, match="sinal"):
        DreMapping(account_code="3.01", group="Receita", sign=0)
