"""Offline candidate normalization: complete source lots, no ERP access or persistence.

Source structure alone does not approve grouping or accounting semantics. The caller
must supply an explicit reviewed scope/mapping and complete per-lot row counts.
This module never enables a dataset, imports journals or approves exports.
"""

from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any

FIELDS = frozenset(
    {
        "company_code",
        "chart_company_code",
        "lot_code",
        "row_code",
        "branch_code",
        "occurred_on",
        "debit_account_code",
        "credit_account_code",
        "amount",
        "history",
        "document",
    }
)
MAX_SOURCE_ROWS = 50_000
MAX_CENTS = 99_999_999_999_999  # Observed source NUMERIC(14,2), without rounding.


class JournalNormalizationError(ValueError):
    """Safe static errors: never echo source values or exception driver messages."""


@dataclass(frozen=True)
class JournalScope:
    company_code: int
    chart_company_code: int
    bank_account_code: int
    branch_codes: frozenset[int]
    account_codes: frozenset[int]
    absent_account_code: int
    bank_inflow_side: str
    period_start: date
    period_end_exclusive: date
    expected_lot_rows: tuple[tuple[int, int], ...]
    expected_bank_effects: int


@dataclass(frozen=True)
class LedgerParty:
    entry_key: str
    line_key: str
    date: str
    history: str
    account_code: str
    side: str
    amount_cents: int
    cash_direction: str
    document: str


@dataclass(frozen=True)
class NormalizedJournalCandidate:
    parties: tuple[LedgerParty, ...]
    source_rows: int
    journals: int
    bank_effects: int
    requires_source_review: bool = True
    financial_collection_enabled: bool = False

    def contract_rows(self) -> tuple[dict[str, Any], ...]:
        return tuple(asdict(party) for party in self.parties)


def _code(value: Any, *, minimum: int = 0) -> int:
    if type(value) is not int or not minimum <= value <= 2147483647:
        raise JournalNormalizationError("Identificador de origem incompatível.")
    return value


def _text(value: Any, *, limit: int, required: bool) -> str:
    if not isinstance(value, str) or len(value) > limit or (required and not value.strip()):
        raise JournalNormalizationError("Texto de partida incompatível com o contrato atual.")
    if value != value.strip() or any(unicodedata.category(c).startswith("C") for c in value):
        raise JournalNormalizationError("Texto não pode ser alterado ou truncado para normalizar.")
    return value


def _cents(value: Any) -> int:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,12}(?:\.[0-9]{1,2})?", value):
        raise JournalNormalizationError(
            "Valor de origem exige decimal positivo com até duas casas."
        )
    integer, _, fraction = value.partition(".")
    cents = int(integer) * 100 + int(fraction.ljust(2, "0") or "0")
    if not 0 < cents <= MAX_CENTS:
        raise JournalNormalizationError(
            "Valor de origem fora do limite; não aplicar módulo ou arredondar."
        )
    return cents


def normalize_journal_snapshot(
    records: list[dict[str, Any]], scope: JournalScope
) -> NormalizedJournalCandidate:
    """All-or-nothing candidate for the unchanged nine-column ledger-csv-v1 contract.

    A unilateral source row becomes one explicit party of its source lot. No
    counterpart is fabricated; completeness and balance are checked per lot.
    Multiple bank effects and differing party texts remain unsupported rather than
    being silently split, merged, truncated or replaced by invented descriptions.
    """
    for value in (scope.company_code, scope.chart_company_code, scope.bank_account_code):
        _code(value, minimum=1)
    _code(scope.absent_account_code)
    if (
        not isinstance(scope.branch_codes, frozenset)
        or not scope.branch_codes
        or not isinstance(scope.account_codes, frozenset)
        or not 1 <= len(scope.account_codes) <= 100_000
        or scope.absent_account_code in scope.account_codes
        or scope.bank_account_code not in scope.account_codes
        or scope.bank_inflow_side not in {"debit", "credit"}
    ):
        raise JournalNormalizationError(
            "Mapa explícito de contas, filiais e direção é obrigatório."
        )
    for value in scope.branch_codes | scope.account_codes:
        _code(value)
    if (
        type(scope.period_start) is not date
        or type(scope.period_end_exclusive) is not date
        or scope.period_start >= scope.period_end_exclusive
        or type(scope.expected_lot_rows) is not tuple
        or not 1 <= len(scope.expected_lot_rows) <= MAX_SOURCE_ROWS
    ):
        raise JournalNormalizationError("Período ou cobertura do snapshot incompatível.")
    expected: dict[int, int] = {}
    for item in scope.expected_lot_rows:
        if type(item) is not tuple or len(item) != 2:
            raise JournalNormalizationError("Contagem de lote incompatível.")
        lot, count = item
        _code(lot)
        _code(count, minimum=1)
        if lot in expected:
            raise JournalNormalizationError("Contagem de lote repetida.")
        expected[lot] = count
    if (
        not isinstance(records, list)
        or not 1 <= len(records) <= MAX_SOURCE_ROWS
        or sum(expected.values()) != len(records)
        or _code(scope.expected_bank_effects, minimum=1) != len(expected)
    ):
        raise JournalNormalizationError("Snapshot incompleto ou cobertura bancária incompatível.")

    grouped: dict[int, list[tuple[int, int, LedgerParty]]] = defaultdict(list)
    rows_by_lot: dict[int, int] = defaultdict(int)
    branches_by_lot: dict[int, set[int]] = defaultdict(set)
    seen: set[int] = set()
    for row in records:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise JournalNormalizationError("Campos de origem incompatíveis.")
        if (
            type(row["company_code"]) is not int
            or row["company_code"] != scope.company_code
            or type(row["chart_company_code"]) is not int
            or row["chart_company_code"] != scope.chart_company_code
        ):
            raise JournalNormalizationError("Empresa ou plano fora do escopo explícito.")
        lot, row_id, branch = (_code(row[k]) for k in ("lot_code", "row_code", "branch_code"))
        if lot not in expected or branch not in scope.branch_codes or row_id in seen:
            raise JournalNormalizationError(
                "Lote/filial fora da cobertura ou linha de origem duplicada."
            )
        seen.add(row_id)
        rows_by_lot[lot] += 1
        branches_by_lot[lot].add(branch)
        try:
            day_text = row["occurred_on"]
            if not isinstance(day_text, str) or not re.fullmatch(
                r"[0-9]{4}-[0-9]{2}-[0-9]{2}", day_text
            ):
                raise ValueError
            occurred_on = date.fromisoformat(day_text)
        except ValueError:
            raise JournalNormalizationError("Data de origem incompatível.") from None
        if not scope.period_start <= occurred_on < scope.period_end_exclusive:
            raise JournalNormalizationError(
                "Partida fora do período; não cortar um lote incompleto."
            )
        history = _text(row["history"], limit=500, required=True)
        document = _text(row["document"], limit=160, required=False)
        amount = _cents(row["amount"])
        accounts = {side: _code(row[f"{side}_account_code"]) for side in ("debit", "credit")}
        if all(code == scope.absent_account_code for code in accounts.values()):
            raise JournalNormalizationError("Registro sem partida explícita.")
        for side, account in accounts.items():
            if account == scope.absent_account_code:
                continue
            if account not in scope.account_codes:
                raise JournalNormalizationError("Partida ausente do plano explícito.")
            direction = (
                ("inflow" if side == scope.bank_inflow_side else "outflow")
                if account == scope.bank_account_code
                else ""
            )
            party = LedgerParty(
                entry_key=f"dominio:{scope.company_code}:lote:{lot}",
                line_key=f"dominio:{scope.company_code}:registro:{row_id}:{side}",
                date=day_text,
                history=history,
                account_code=str(account),
                side=side,
                amount_cents=amount,
                cash_direction=direction,
                document=document,
            )
            grouped[lot].append((row_id, 0 if side == "debit" else 1, party))
    if rows_by_lot != expected:
        raise JournalNormalizationError("Cobertura das linhas de cada lote diverge da fonte.")
    parties: list[LedgerParty] = []
    bank_effects = 0
    for lot, values in sorted(grouped.items()):
        group = [item[2] for item in sorted(values, key=lambda item: (item[0], item[1]))]
        if (
            len(branches_by_lot[lot]) != 1
            or len({(p.date, p.history, p.document) for p in group}) != 1
        ):
            raise JournalNormalizationError(
                "Lote com dados por partida incompatíveis com ledger-csv-v1."
            )
        debit = sum(p.amount_cents for p in group if p.side == "debit")
        credit = sum(p.amount_cents for p in group if p.side == "credit")
        if len(group) < 2 or debit != credit or debit > 9223372036854775807:
            raise JournalNormalizationError("Lote incompleto, desequilibrado ou fora do limite.")
        effects = sum(bool(p.cash_direction) for p in group)
        if effects != 1:
            raise JournalNormalizationError(
                "Contrato atual exige um efeito bancário por lote, sem repartir."
            )
        bank_effects += effects
        parties.extend(group)
    if bank_effects != scope.expected_bank_effects or len(parties) > 100_000:
        raise JournalNormalizationError("Cobertura final das partidas incompatível.")
    return NormalizedJournalCandidate(tuple(parties), len(records), len(grouped), bank_effects)
