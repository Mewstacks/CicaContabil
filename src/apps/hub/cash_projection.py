"""Deterministic cash projection primitives for reform scenarios and realized cash."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import StrEnum


class CashView(StrEnum):
    SIMULATION = "simulation"
    PROJECTION = "projection"
    REALIZED = "realized"


@dataclass(frozen=True)
class CashMovement:
    occurred_on: date
    description: str
    gross_receipt_cents: int = 0
    payment_cents: int = 0
    retention_cents: int = 0
    provision_cents: int = 0
    retention_already_provisioned: bool = False

    def net_change_cents(self) -> int:
        if min(
            self.gross_receipt_cents,
            self.payment_cents,
            self.retention_cents,
            self.provision_cents,
        ) < 0:
            raise ValueError("Movimentos de caixa devem usar valores não negativos.")
        if self.retention_already_provisioned and self.retention_cents and self.provision_cents:
            raise ValueError("A retenção já provisionada não pode ser deduzida novamente.")
        withheld = self.retention_cents or self.provision_cents
        return self.gross_receipt_cents - withheld - self.payment_cents


@dataclass(frozen=True)
class CashPosition:
    occurred_on: date
    net_change_cents: int
    closing_balance_cents: int


@dataclass(frozen=True)
class CashProjection:
    view: CashView
    opening_balance_cents: int
    positions: tuple[CashPosition, ...]

    @property
    def lowest_balance_cents(self) -> int:
        balances = (position.closing_balance_cents for position in self.positions)
        return min(balances, default=self.opening_balance_cents)

    @property
    def estimated_working_capital_cents(self) -> int:
        return max(0, -self.lowest_balance_cents)


def project_cash(
    *, view: CashView, opening_balance_cents: int, movements: list[CashMovement]
) -> CashProjection:
    """Build a dated, explainable projection from explicit facts or user assumptions."""

    if opening_balance_cents < 0 and view == CashView.SIMULATION:
        # A negative simulation opening balance is still valid, but requires no special handling.
        pass
    balance = opening_balance_cents
    positions: list[CashPosition] = []
    for movement in sorted(movements, key=lambda row: row.occurred_on):
        change = movement.net_change_cents()
        balance += change
        positions.append(
            CashPosition(
                occurred_on=movement.occurred_on,
                net_change_cents=change,
                closing_balance_cents=balance,
            )
        )
    return CashProjection(
        view=view,
        opening_balance_cents=opening_balance_cents,
        positions=tuple(positions),
    )
