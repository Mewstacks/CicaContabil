from datetime import date

import pytest

from apps.hub.cash_projection import CashMovement, CashView, project_cash


def test_projection_separates_gross_receipt_retention_and_payment() -> None:
    projection = project_cash(
        view=CashView.PROJECTION,
        opening_balance_cents=10_000,
        movements=[
            CashMovement(
                occurred_on=date(2026, 10, 2),
                description="Recebimento parcelado",
                gross_receipt_cents=20_000,
                retention_cents=3_000,
            ),
            CashMovement(
                occurred_on=date(2026, 10, 3), description="Folha", payment_cents=18_000
            ),
        ],
    )

    assert [item.closing_balance_cents for item in projection.positions] == [27_000, 9_000]
    assert projection.lowest_balance_cents == 9_000
    assert projection.estimated_working_capital_cents == 0


def test_projection_refuses_double_deduction_of_retention_and_provision() -> None:
    movement = CashMovement(
        occurred_on=date(2026, 10, 2),
        description="Recebimento com split payment",
        gross_receipt_cents=20_000,
        retention_cents=3_000,
        provision_cents=3_000,
        retention_already_provisioned=True,
    )

    with pytest.raises(ValueError, match="não pode ser deduzida novamente"):
        project_cash(view=CashView.SIMULATION, opening_balance_cents=0, movements=[movement])
