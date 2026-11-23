"""Offline cash-capacity preview for explicit selections, without matching or writes."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from apps.hub.title_contract import (
    MAX_ITEMS,
    Settlement,
    TitleContractError,
    _cents,
    _day,
    _items,
    _key,
    _object,
    validate_title_snapshot,
)


@dataclass(frozen=True, order=True)
class SettlementReference:
    title_key: str
    installment_key: str
    settlement_key: str


@dataclass(frozen=True)
class BankCashMovement:
    key: str
    occurred_on: date
    cash_cents: int
    direction: str


@dataclass(frozen=True)
class MovementCapacity:
    movement: BankCashMovement
    allocated_cents: int
    remaining_cents: int


@dataclass(frozen=True)
class SettlementCapacity:
    reference: SettlementReference
    settlement: Settlement
    allocated_cents: int
    remaining_cents: int


@dataclass(frozen=True)
class ProposedAllocation:
    movement_key: str
    reference: SettlementReference
    cash_cents: int
    date_difference: bool


@dataclass(frozen=True)
class TitleAllocationPreview:
    company_key: str
    account_reference: str
    period_start: date
    period_end: date
    snapshot_fingerprint: str
    source_settlements_complete: bool
    movements: tuple[MovementCapacity, ...]
    settlements: tuple[SettlementCapacity, ...]
    allocations: tuple[ProposedAllocation, ...]
    fingerprint: str
    # This preview verifies arithmetic only. It cannot approve an association.
    requires_review: bool = True


def preview_title_allocations(
    snapshot_payload: Any,
    bank_payload: Any,
    requested_allocations: Any,
    *,
    company_key: str,
    account_reference: str,
    period_start: date,
    period_end: date,
) -> TitleAllocationPreview:
    """Validate a complete proposed plan before returning any capacity result.

    Every association is supplied explicitly. No due date, principal amount,
    description similarity or netted reversal creates a bank match. Original
    and reversal cash flows have separate capacities and opposite directions.
    This function has no database, ERP, provider, or UI side effects.
    """
    _key(company_key)
    _key(account_reference)
    snapshot = validate_title_snapshot(
        snapshot_payload, company_key=company_key, account_reference=account_reference
    )
    if (
        type(period_start) is not date
        or type(period_end) is not date
        or period_start > period_end
        or period_end > snapshot.as_of
    ):
        raise TitleContractError("Período inválido ou posterior à fotografia de títulos.")

    bank = _object(
        bank_payload,
        {"contract", "company_key", "account_reference", "period_start", "period_end", "movements"},
    )
    if (
        bank["contract"] != "bank-cash-normalized-v1"
        or _key(bank["company_key"]) != company_key
        or _key(bank["account_reference"]) != account_reference
        or _day(bank["period_start"]) != period_start
        or _day(bank["period_end"]) != period_end
    ):
        raise TitleContractError("Empresa, conta, período ou contrato bancário incompatíveis.")
    movements: dict[str, BankCashMovement] = {}
    for raw in _items(bank["movements"]):
        row = _object(raw, {"key", "occurred_on", "cash_cents", "direction"})
        key = _key(row["key"])
        occurred_on = _day(row["occurred_on"])
        direction = row["direction"]
        if (
            key in movements
            or not isinstance(direction, str)
            or direction not in {"inflow", "outflow"}
            or not period_start <= occurred_on <= period_end
        ):
            raise TitleContractError(
                "Movimento repetido, fora do período ou sem direção explícita."
            )
        movements[key] = BankCashMovement(
            key=key,
            occurred_on=occurred_on,
            cash_cents=_cents(row["cash_cents"], positive=True),
            direction=direction,
        )

    settlements = {
        SettlementReference(title.key, installment.key, settlement.key): settlement
        for title in snapshot.titles
        for installment in title.installments
        for settlement in installment.settlements
        if period_start <= settlement.posted_on <= period_end
    }
    proposed = _items(requested_allocations)
    if len(movements) + len(settlements) + len(proposed) > MAX_ITEMS:
        raise TitleContractError("Prévia de alocações excede o limite global.")
    movement_used = dict.fromkeys(movements, 0)
    settlement_used = dict.fromkeys(settlements, 0)
    seen: set[tuple[str, SettlementReference]] = set()
    allocations = []
    for raw in proposed:
        row = _object(
            raw,
            {"movement_key", "title_key", "installment_key", "settlement_key", "cash_cents"},
        )
        movement_key = _key(row["movement_key"])
        reference = SettlementReference(
            _key(row["title_key"]), _key(row["installment_key"]), _key(row["settlement_key"])
        )
        movement = movements.get(movement_key)
        settlement = settlements.get(reference)
        pair = movement_key, reference
        if movement is None or settlement is None or pair in seen:
            raise TitleContractError("Alocação repetida ou com movimento/baixa fora do recorte.")
        if movement.direction != settlement.direction:
            raise TitleContractError("Direção bancária diverge da baixa selecionada.")
        amount = _cents(row["cash_cents"], positive=True)
        movement_used[movement_key] += amount
        settlement_used[reference] += amount
        if (
            movement_used[movement_key] > movement.cash_cents
            or settlement_used[reference] > settlement.cash_cents
        ):
            raise TitleContractError(
                "Alocações excedem a capacidade de caixa do movimento ou baixa."
            )
        seen.add(pair)
        allocations.append(
            ProposedAllocation(
                movement_key=movement_key,
                reference=reference,
                cash_cents=amount,
                date_difference=movement.occurred_on != settlement.posted_on,
            )
        )
    allocations.sort(key=lambda item: (item.movement_key, item.reference))
    canonical = {
        "contract": "title-allocation-preview-v1",
        "company_key": company_key,
        "account_reference": account_reference,
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "snapshot_fingerprint": snapshot.fingerprint,
        "movements": [
            {
                "key": item.key,
                "occurred_on": item.occurred_on.isoformat(),
                "cash_cents": item.cash_cents,
                "direction": item.direction,
            }
            for item in sorted(movements.values(), key=lambda item: item.key)
        ],
        "allocations": [
            {
                "movement_key": item.movement_key,
                "title_key": item.reference.title_key,
                "installment_key": item.reference.installment_key,
                "settlement_key": item.reference.settlement_key,
                "cash_cents": item.cash_cents,
            }
            for item in allocations
        ],
    }
    fingerprint = hashlib.sha256(
        json.dumps(canonical, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()
    return TitleAllocationPreview(
        company_key=company_key,
        account_reference=account_reference,
        period_start=period_start,
        period_end=period_end,
        snapshot_fingerprint=snapshot.fingerprint,
        source_settlements_complete=snapshot.settlements_complete,
        movements=tuple(
            MovementCapacity(item, movement_used[key], item.cash_cents - movement_used[key])
            for key, item in sorted(movements.items())
        ),
        settlements=tuple(
            SettlementCapacity(
                ref, item, settlement_used[ref], item.cash_cents - settlement_used[ref]
            )
            for ref, item in sorted(settlements.items())
        ),
        allocations=tuple(allocations),
        fingerprint=fingerprint,
    )
