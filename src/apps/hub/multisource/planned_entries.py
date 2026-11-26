"""Prévia dos lançamentos de baixa que o multifontes geraria — D-421, PC-33.

O lançamento do banco continua com o uso direto (D-393). Aqui ficam só as baixas que a CONTAD
fazia no Domínio: conta de passagem (COBRANÇA ou PAGAMENTO DE FORNECEDORES) contra a conta do
cliente ou do fornecedor, e os juros recebidos. É prévia: nada é gravado e não há arquivo `.txt`
(D-421 item 5).
"""

from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date

from apps.hub.multisource.common import money
from apps.hub.multisource.matching import AUTOMATIC, SimulationResult
from apps.hub.multisource.title_position import PAYABLE, RECEIVABLE, TitlePosition

READY = "pronto quando as contas forem confirmadas"
NO_ACCOUNT = "sem conta sugerida"
AMBIGUOUS = "mais de uma conta com o mesmo nome no plano — escolher"
ALREADY = "o Domínio já registra baixa deste título — não lançar"


@dataclass(frozen=True)
class PlannedEntry:
    occurred_on: date
    history: str
    debit: str
    credit: str
    amount_cents: int
    origin: str
    situation: str


def _accounts(suggestions: object, part: object, role: str) -> list[str]:
    if suggestions is None:
        return []
    for suggestion in suggestions.for_part(part):  # type: ignore[attr-defined]
        if suggestion.role == role and suggestion.accounts:
            return [str(a) for a in suggestion.accounts]
    return []


Key = tuple[str, str, str, date]


def _reference_balances(
    references: dict[str, TitlePosition | None],
) -> tuple[set[str], dict[Key, int]]:
    """Tipos com posição do Domínio do mês e o saldo de cada parcela nela.

    O relatório do Domínio não detalha título quitado (Q-59): parcela ausente da posição do mês, ou
    com saldo menor que o de abertura, já teve baixa no Domínio."""
    kinds: set[str] = set()
    balances: dict[Key, int] = {}
    for position in references.values():
        if position is None:
            continue
        kinds.add(position.kind)
        for item in position.installments:
            balances[(item.kind, item.party_code, item.document, item.due_on)] = item.balance_cents
    return kinds, balances


def plan_settlements(
    result: SimulationResult,
    suggestions: object = None,
    references: dict[str, TitlePosition | None] | None = None,
) -> list[PlannedEntry]:
    kinds, balances = _reference_balances(references or {})
    settled_sources: set[str] = set()
    entries: list[PlannedEntry] = []
    for line in result.lines:
        if line.status != AUTOMATIC:
            continue  # sinalizado ou só identificado nunca gera baixa (D-421 item 2)
        bank = line.bank
        origin = f"{bank.account} {bank.occurred_on:%d/%m/%Y} {money(bank.amount_cents)}"
        for part in line.parts:
            if part.kind not in ("receivable", "payable", "interest"):
                continue
            item = result.installments.get(part.installment_key) if part.installment_key else None
            if part.kind == "interest":
                history = f"Juros/multa recebidos — {part.source}"
            elif item is not None:
                history = (
                    f"Baixa NF {item.document} parc. {item.ordinal}/{item.count} — "
                    f"{item.party_name} — {part.source}"
                )
            else:
                continue
            passage = _accounts(suggestions, part, "banco")
            other = _accounts(suggestions, part, "baixa")
            debit, credit = (other, passage) if part.kind == PAYABLE else (passage, other)
            situation = READY if debit and credit else NO_ACCOUNT
            if len(debit) > 1 or len(credit) > 1:
                situation = AMBIGUOUS
            if item is not None and part.kind in (RECEIVABLE, PAYABLE) and item.kind in kinds:
                key = (item.kind, item.party_code, item.document, item.due_on)
                if balances.get(key, 0) < item.balance_cents:
                    situation = ALREADY
                    settled_sources.add(part.source)
            if part.kind == "interest" and part.source in settled_sources:
                situation = ALREADY  # juros acompanham a baixa do título da mesma cobrança
            entries.append(
                PlannedEntry(
                    bank.occurred_on,
                    history,
                    " | ".join(debit),
                    " | ".join(credit),
                    part.amount_cents,
                    origin,
                    situation,
                )
            )
    return entries


def render_planned_csv(entries: list[PlannedEntry]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(
        ["data", "historico", "debito", "credito", "valor", "movimento_do_banco", "situacao"]
    )
    for entry in entries:
        writer.writerow(
            [
                entry.occurred_on.strftime("%d/%m/%Y"),
                entry.history,
                entry.debit or "a definir",
                entry.credit or "a definir",
                money(entry.amount_cents),
                entry.origin,
                entry.situation,
            ]
        )
    return out.getvalue()


def planned_summary(entries: list[PlannedEntry]) -> list[str]:
    def total(rows: list[PlannedEntry]) -> str:
        return money(sum(e.amount_cents for e in rows))

    ready = [e for e in entries if e.situation == READY]
    already = [e for e in entries if e.situation == ALREADY]
    missing = [e for e in entries if e.situation == NO_ACCOUNT]
    ambiguous = [e for e in entries if e.situation == AMBIGUOUS]
    return [
        "",
        "## Lançamentos de baixa previstos (D-421, prévia)",
        "",
        "O lançamento do banco segue o uso direto; estes são só as baixas que a CONTAD fazia no "
        "Domínio. Nada foi lançado e não há arquivo para importar.",
        "",
        f"- Prontos quando as contas forem confirmadas: {len(ready)} · {total(ready)}",
        f"- O Domínio já registra a baixa (não lançar): {len(already)} · {total(already)}",
        f"- Sem conta sugerida: {len(missing)} · {total(missing)}",
        f"- Mais de uma conta com o mesmo nome (escolher): {len(ambiguous)} · {total(ambiguous)}",
    ]
