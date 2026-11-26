"""Comparação da simulação multifontes com o Razão da conta bancária (D-410, PC-33).

O Razão é o que a contadora já lançou à mão. Para cada movimento do extrato, procura no Razão os
lançamentos da conta bancária no mesmo dia (ou até 5 dias de distância, como na D-397) cuja soma
seja o valor do movimento e compara o desdobramento com o da simulação. Também reúne as contas de
contrapartida usadas pela contadora para cada tipo de parte, como evidência para Q-50/Q-53. Nada
vira regra ou conta automaticamente.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from apps.hub.multisource.common import MultisourceError
from apps.hub.multisource.matching import LineResult, SimulationResult, subset_with_sum

WINDOW_DAYS = 5

SAME_SPLIT = "mesmo desdobramento"
OTHER_SPLIT = "mesmo valor, desdobramento diferente"
MISSING = "não encontrado no Razão"
ONLY_LEDGER = "só no Razão"


@dataclass(frozen=True)
class LedgerMovement:
    """Efeito de um lançamento na conta bancária: + entrada, - saída."""

    occurred_on: date
    amount_cents: int
    counterparts: tuple[str, ...]
    history: str
    reference: str


@dataclass
class ComparisonLine:
    line: LineResult
    outcome: str
    movements: list[LedgerMovement] = field(default_factory=list)
    shifted_days: int = 0


@dataclass
class LedgerComparison:
    lines: list[ComparisonLine]
    only_ledger: list[LedgerMovement]
    accounts: dict[str, Counter[str]]

    def count(self, outcome: str) -> int:
        return sum(1 for item in self.lines if item.outcome == outcome)


def movements_from_pdf(evidence: object) -> list[LedgerMovement]:
    """Linhas do Razão do Domínio em PDF (`ledger_evidence.read_dominio_ledger_pdf`)."""
    result = []
    for line in getattr(evidence, "lines", ()):
        counterpart = line.counterparty_code or ""
        result.append(
            LedgerMovement(
                line.occurred_on,
                line.amount_cents,  # débito na conta bancária (ativo) é entrada
                (counterpart,) if counterpart else (),
                "",
                f"Razão nº {line.printed_entry_number}",
            )
        )
    return result


def movements_from_ledger_csv(content: bytes) -> list[LedgerMovement]:
    """Lançamentos no contrato `ledger-csv-v1`; a partida bancária tem `cash_direction`."""
    from apps.hub.ledger_import import _content_rows
    from apps.hub.reconciliation_service import ReconciliationError

    try:
        grouped = _content_rows(content)
    except ReconciliationError as exc:
        raise MultisourceError(str(exc)) from exc
    result = []
    for key, rows in grouped.items():
        bank = [r for r in rows if r["cash_direction"] in ("inflow", "outflow")]
        if len(bank) != 1:
            raise MultisourceError(
                f"Razão: o lançamento {key} precisa de uma única partida bancária."
            )
        sign = 1 if bank[0]["cash_direction"] == "inflow" else -1
        others = tuple(sorted({r["account_code"] for r in rows if r is not bank[0]}))
        result.append(
            LedgerMovement(
                date.fromisoformat(bank[0]["date"]),
                sign * int(bank[0]["amount_cents"]),
                others,
                bank[0]["history"],
                f"Razão {key}",
            )
        )
    return result


def _expected_splits(line: LineResult) -> list[list[int]]:
    """Desdobramentos aceitos como iguais: por título (nominal + juros juntos) ou por parte."""
    sign = 1 if line.bank.amount_cents > 0 else -1
    options = []
    if line.collection_items:
        options.append(sorted(sign * i.amount_cents for i in line.collection_items))
    if line.parts:
        options.append(sorted(sign * p.amount_cents for p in line.parts))
    if len(line.parts) <= 1 and len(line.collection_items) <= 1:
        options.append([line.bank.amount_cents])
    return options


def compare_with_ledger(
    result: SimulationResult, movements: Sequence[LedgerMovement], *, account: str = "extrato"
) -> LedgerComparison:
    pool = sorted(movements, key=lambda m: (m.occurred_on, m.reference))
    used: set[int] = set()
    lines = [r for r in result.lines if r.bank.account == account]
    comparisons: list[ComparisonLine] = []
    pending: list[LineResult] = []
    # 1ª passada: mesmo dia; 2ª passada: até WINDOW_DAYS de distância.
    for line in lines:
        found = _find(line, pool, used, 0)
        if found is None:
            pending.append(line)
        else:
            comparisons.append(found)
    for line in pending:
        found = _find(line, pool, used, WINDOW_DAYS)
        comparisons.append(found or ComparisonLine(line, MISSING))
    comparisons.sort(key=lambda c: c.line.bank.index)
    only = [m for i, m in enumerate(pool) if i not in used]
    return LedgerComparison(comparisons, only, _accounts(comparisons))


def _find(
    line: LineResult, pool: list[LedgerMovement], used: set[int], window: int
) -> ComparisonLine | None:
    day = line.bank.occurred_on
    candidates = [
        i
        for i, m in enumerate(pool)
        if i not in used
        and abs((m.occurred_on - day).days) <= window
        and (m.amount_cents > 0) == (line.bank.amount_cents > 0)
    ]
    if window:
        candidates = [i for i in candidates if pool[i].occurred_on != day]
    # Preferir um único lançamento de valor igual; senão, a soma de vários do mesmo dia.
    single = [i for i in candidates if pool[i].amount_cents == line.bank.amount_cents]
    if single:
        chosen = [min(single, key=lambda i: abs((pool[i].occurred_on - day).days))]
    else:
        same_day: dict[date, list[int]] = defaultdict(list)
        for i in candidates:
            same_day[pool[i].occurred_on].append(i)
        chosen = []
        for _day, indexes in sorted(same_day.items(), key=lambda kv: abs((kv[0] - day).days)):
            subset, ambiguous = subset_with_sum(
                [pool[i].amount_cents for i in indexes], line.bank.amount_cents
            )
            if subset and not ambiguous:
                chosen = [indexes[k] for k in subset]
                break
        if not chosen:
            return None
    used.update(chosen)
    picked = [pool[i] for i in chosen]
    split = sorted(m.amount_cents for m in picked)
    outcome = SAME_SPLIT if split in _expected_splits(line) else OTHER_SPLIT
    shift = max(abs((m.occurred_on - day).days) for m in picked)
    return ComparisonLine(line, outcome, picked, shift)


def _part_group(kind: str, label: str) -> str:
    if kind == "nature":
        text = re.sub(r"\(parte\)|\d+[\d/.,]*", "", label.upper())
        return "natureza: " + " ".join(text.split())[:60]
    return {
        "receivable": "recebimento de cliente (baixa de título)",
        "payable": "pagamento de fornecedor (baixa de título)",
        "interest": "juros/multa recebidos",
        "document": "nota citada no caixa, fora da posição",
    }.get(kind, kind)


def _accounts(comparisons: list[ComparisonLine]) -> dict[str, Counter[str]]:
    """Contas de contrapartida usadas no Razão por tipo de parte, só quando o casamento é 1:1."""
    accounts: dict[str, Counter[str]] = defaultdict(Counter)
    for item in comparisons:
        if not item.movements:
            continue
        parts = item.line.parts
        movements = item.movements
        if len(parts) == len(movements):
            pairs = zip(
                sorted(parts, key=lambda p: p.amount_cents),
                sorted(movements, key=lambda m: abs(m.amount_cents)),
                strict=True,
            )
            for part, movement in pairs:
                if part.amount_cents == abs(movement.amount_cents):
                    for code in movement.counterparts or ("(sem contrapartida única)",):
                        accounts[_part_group(part.kind, part.label)][code] += 1
        elif len(movements) == 1 and parts:
            kinds = {p.kind for p in parts}
            if len(kinds) == 1:
                group = _part_group(parts[0].kind, parts[0].label)
                for code in movements[0].counterparts or ("(sem contrapartida única)",):
                    accounts[group][code] += 1
    return dict(accounts)
