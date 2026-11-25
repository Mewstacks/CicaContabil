"""Motor de casamento multifontes em modo simulação (D-409, PC-33).

Ordem determinística, sempre com motivo gravado:

1. Cobrança do extrato ("LIQ.COBRANCA") decomposta pelos títulos da francesinha com a mesma data
   de lançamento em c/c; a soma precisa ser exata.

2. Demais movimentos casados com as linhas do caixa do cliente da mesma data: valor igual (1:1) e,
   depois, soma exata de várias linhas (1:N, ex.: folha).

3. Recebimentos baixam o valor nominal da parcela aberta; juros e multa ficam "a classificar"
   (Q-53). Com vários candidatos de valor exato, baixa o de vencimento mais antigo (R-05); valor
   diferente vira sinalização (tolerância zero, Q-58).

4. Pagamentos baixam um título por documento citado no caixa (R-08); sem documento, o título
   aberto de valor exato do fornecedor (R-09); mais de um candidato vira sinalização.

5. O que sobra é natureza informada pelo caixa (sem título) ou sinalização. Nada é gravado: o
   resultado é uma simulação com a posição de títulos recalculada.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import date
from difflib import SequenceMatcher

from apps.hub.multisource.client_cashbook import CashbookLine, CashbookSheet, DocumentRef
from apps.hub.multisource.common import money, names_match
from apps.hub.multisource.francesinha import CollectionItem, CollectionReport
from apps.hub.multisource.investment import InvestmentMovement, InvestmentStatement
from apps.hub.multisource.title_position import (
    PAYABLE,
    RECEIVABLE,
    PositionInstallment,
    TitlePosition,
)

MAX_SUBSET_NODES = 200_000
NATURE_SIMILARITY = 0.8

# Situações de cada movimento do extrato.
AUTOMATIC = "baixa_automatica"  # todo o valor explicado por baixa de títulos (+ juros)
IDENTIFIED = (
    "identificado_sem_titulo"  # natureza ou documento informados pelo caixa; conta pelo DE-PARA
)
FLAGGED = "sinalizado"

STATUS_LABELS = {
    AUTOMATIC: "Automático (títulos ou aplicação)",
    IDENTIFIED: "Identificado pelo caixa (sem baixa de título)",
    FLAGGED: "Sinalizado para a contadora",
}


@dataclass(frozen=True)
class BankLine:
    index: int
    occurred_on: date
    amount_cents: int
    description: str
    document: str = ""
    account: str = "extrato"

    @property
    def is_collection(self) -> bool:
        return self.description.upper().startswith("LIQ.COBRANCA")

    @property
    def counterparty(self) -> str:
        """Nome após o CPF/CNPJ no histórico do extrato ("... 22222222000122 SOFTWARE ALFA TEC")."""
        match = re.search(r"\b\d{11,14}\b\s+(.+)$", self.description)
        return match[1].strip() if match else ""

    @property
    def tax_id(self) -> str:
        match = re.search(r"\b(\d{14}|\d{11})\b", self.description)
        return match[1] if match else ""


@dataclass(frozen=True)
class Part:
    kind: str  # receivable | payable | interest | document | nature
    amount_cents: int
    label: str
    installment_key: tuple[str, str, str, int] | None = None
    source: str = ""


@dataclass
class LineResult:
    bank: BankLine
    status: str = FLAGGED
    parts: list[Part] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    cashbook_rows: list[int] = field(default_factory=list)
    collection_items: list[CollectionItem] = field(default_factory=list)


@dataclass(frozen=True)
class PositionDifference:
    kind: str
    outcome: str
    label: str
    simulated_cents: int
    reference_cents: int


@dataclass
class SimulationResult:
    lines: list[LineResult]
    unmatched_cashbook: list[CashbookLine]
    unmatched_collection: list[CollectionItem]
    closing: dict[tuple[str, str, str, int], int]
    installments: dict[tuple[str, str, str, int], PositionInstallment]
    differences: list[PositionDifference]
    warnings: list[str]
    investment: InvestmentStatement | None = None
    investment_unmatched: list[InvestmentMovement] = field(default_factory=list)

    def count(self, status: str) -> int:
        return sum(1 for line in self.lines if line.status == status)

    @property
    def automatic_share(self) -> float:
        return self.count(AUTOMATIC) / len(self.lines) if self.lines else 0.0

    @property
    def identified_share(self) -> float:
        done = self.count(AUTOMATIC) + self.count(IDENTIFIED)
        return done / len(self.lines) if self.lines else 0.0


def subset_with_sum(values: Sequence[int], target: int) -> tuple[list[int] | None, bool]:
    """Índices cuja soma é `target` (sinais iguais). Devolve (solução, ambígua?).

    Busca em profundidade com poda; ambígua quando existe outra combinação de índices com a mesma
    soma
    e valores diferentes. Limitada a MAX_SUBSET_NODES para não travar com listas grandes.
    """
    order = sorted(range(len(values)), key=lambda i: -abs(values[i]))
    solutions: list[list[int]] = []
    nodes = 0

    def search(position: int, remaining: int, chosen: list[int]) -> None:
        nonlocal nodes
        nodes += 1
        if nodes > MAX_SUBSET_NODES or len(solutions) > 1:
            return
        if remaining == 0 and chosen:
            solutions.append(sorted(chosen))
            return
        for p in range(position, len(order)):
            value = values[order[p]]
            if (target > 0 and 0 < value <= remaining) or (target < 0 and remaining <= value < 0):
                chosen.append(order[p])
                search(p + 1, remaining - value, chosen)
                chosen.pop()
                if len(solutions) > 1:
                    return

    search(0, target, [])
    if not solutions:
        return None, nodes > MAX_SUBSET_NODES
    if len(solutions) == 1:
        return solutions[0], False
    same_values = sorted(values[i] for i in solutions[0]) == sorted(values[i] for i in solutions[1])
    return solutions[0], not same_values


class OpenTitles:
    """Saldos em aberto durante a simulação (começam pela posição de abertura)."""

    def __init__(self, positions: Iterable[TitlePosition | None]):
        self.items: dict[tuple[str, str, str, int], PositionInstallment] = {}
        self.balance: dict[tuple[str, str, str, int], int] = {}
        for position in positions:
            if position is None:
                continue
            for item in position.installments:
                self.items[item.key] = item
                self.balance[item.key] = item.balance_cents

    def open(self, kind: str) -> list[PositionInstallment]:
        return [i for k, i in self.items.items() if k[0] == kind and self.balance[k] > 0]

    def candidates(
        self, kind: str, refs: Sequence[DocumentRef], name: str
    ) -> list[PositionInstallment]:
        numbers = {r.number for r in refs}
        found = [i for i in self.open(kind) if not numbers or i.document.lstrip("0") in numbers]
        if name:
            named = [i for i in found if names_match(name, i.party_name)]
            if named or not numbers:
                found = named
        return sorted(found, key=lambda i: (i.due_on, i.party_code, i.document, i.ordinal))

    def settle(self, item: PositionInstallment, cents: int) -> None:
        self.balance[item.key] -= cents


OUTSIDE = "fora_da_posicao"


def _settle_receipt(
    titles: OpenTitles, kind: str, nominal: int, refs: Sequence[DocumentRef], name: str, source: str
) -> tuple[list[Part], str | None]:
    """Baixa recebimento/pagamento contra títulos abertos. Devolve (partes, motivo da sinalização).

    O motivo `OUTSIDE` indica que nenhum documento citado está na posição de abertura (ex.: nota
    emitida
    e paga no próprio mês): quem chama decide como registrar.
    """
    label_kind = "receber" if kind == RECEIVABLE else "pagar"
    documents = list(dict.fromkeys(r.number for r in refs if r.kind in ("nf", "cte", "doc")))
    if len(documents) > 1:
        chosen = []
        missing = []
        for number in documents:
            options = titles.candidates(kind, [DocumentRef("nf", number)], name)
            if options:
                chosen.append(options[0])
            else:
                missing.append(number)
        if not chosen:
            return [], OUTSIDE
        if missing:
            found = sum(titles.balance[i.key] for i in chosen)
            return [], (
                f"{len(missing)} de {len(documents)} documentos citados não estão em aberto na "
                f"posição a {label_kind} (os {len(chosen)} encontrados somam {money(found)}; "
                f"valor {money(nominal)})"
            )
        total = sum(titles.balance[i.key] for i in chosen)
        if total != nominal:
            return [], (
                f"soma dos {len(chosen)} documentos citados ({money(total)}) difere do valor "
                f"({money(nominal)})"
            )
        parts = []
        for item in chosen:
            cents = titles.balance[item.key]
            titles.settle(item, cents)
            parts.append(Part(kind, cents, item.label, item.key, source))
        return parts, None
    candidates = titles.candidates(kind, [DocumentRef("nf", d) for d in documents], name)
    if not candidates and documents:
        return [], OUTSIDE
    if not candidates:
        where = f"nome {name!r}"
        return [], f"nenhum título a {label_kind} em aberto para {where} na posição de abertura"
    exact = [i for i in candidates if titles.balance[i.key] == nominal]
    if not exact:
        listed = "; ".join(
            f"{i.label} saldo {money(titles.balance[i.key])}" for i in candidates[:4]
        )
        return [], f"valor {money(nominal)} não confere com os títulos em aberto ({listed})"
    parties = {i.party_code for i in exact}
    if len(parties) > 1:
        return [], "valor confere com títulos de mais de um cliente/fornecedor; escolha manual"
    if kind == PAYABLE and len(exact) > 1 and not documents:
        return [], f"{len(exact)} títulos a pagar com o mesmo valor; escolha manual (R-09)"
    item = exact[0]  # R-05: vencimento mais antigo
    titles.settle(item, nominal)
    note = f" (mais antigo entre {len(exact)})" if len(exact) > 1 else ""
    return [Part(kind, nominal, item.label + note, item.key, source)], None


def simulate(
    bank_lines: Sequence[BankLine],
    *,
    collection: CollectionReport | None = None,
    receivables: TitlePosition | None = None,
    payables: TitlePosition | None = None,
    cashbook: CashbookSheet | None = None,
    reference_receivables: TitlePosition | None = None,
    reference_payables: TitlePosition | None = None,
    cash_accounts: Sequence[CashbookSheet] = (),
    investment: InvestmentStatement | None = None,
) -> SimulationResult:
    """Simula o mês. `cash_accounts` são abas do caixa sem extrato (ex.: dinheiro em espécie):
    cada linha da aba é o próprio movimento e baixa títulos com a mesma carteira do extrato."""
    titles = OpenTitles([receivables, payables])
    main = _run_account(bank_lines, collection, cashbook, titles)
    results = list(main.results)
    investment_unmatched = _apply_investment(main.results, investment) if investment else []
    _flag_unusual_nature(main.results, cashbook)
    for sheet in cash_accounts:
        own = [
            BankLine(c.row, c.occurred_on, c.amount_cents, c.history, account=sheet.name)
            for c in sheet.lines
        ]
        results.extend(_run_account(own, None, sheet, titles).results)
    warnings: list[str] = []
    differences = _compare(titles, [reference_receivables, reference_payables])
    for source in (
        collection,
        receivables,
        payables,
        cashbook,
        *cash_accounts,
        reference_receivables,
        reference_payables,
    ):
        warnings.extend(getattr(source, "warnings", ()) or ())
    return SimulationResult(
        results,
        main.unmatched_cash,
        main.unmatched_items,
        dict(titles.balance),
        dict(titles.items),
        differences,
        warnings,
        investment,
        investment_unmatched,
    )


def _apply_investment(
    results: list[LineResult], investment: InvestmentStatement
) -> list[InvestmentMovement]:
    """Casa aplicações e resgates do extrato bancário com o extrato da aplicação (D-411).

    No mesmo dia, as linhas do banco que somam exatamente a aplicação (saída) ou o resgate (entrada)
    viram transferência entre banco e aplicação. Devolve os movimentos da aplicação sem par
    no banco.
    """
    unmatched = []
    for movement in investment.movements:
        if movement.kind not in ("application", "redemption"):
            continue
        sign = -1 if movement.kind == "application" else 1
        pool = [
            r
            for r in results
            if r.bank.occurred_on == movement.occurred_on
            and not r.bank.is_collection
            and "APLIC" in r.bank.description.upper()
            and r.bank.amount_cents * sign > 0
            and not any(p.kind == "investment" for p in r.parts)
        ]
        chosen, ambiguous = subset_with_sum(
            [r.bank.amount_cents for r in pool], sign * movement.amount_cents
        )
        if not chosen or ambiguous:
            unmatched.append(movement)
            continue
        label = (
            "Aplicação financeira (transferência do banco)"
            if movement.kind == "application"
            else "Resgate da aplicação (transferência para o banco)"
        )
        for index in chosen:
            line = pool[index]
            line.parts = [
                Part("investment", abs(line.bank.amount_cents), label, source="aplicação")
            ]
            line.reasons = []
            line.status = AUTOMATIC
    return unmatched


def _nature_key(label: str) -> str:
    text = re.sub(r"\(parte\)|\bN[FO]\b|\d+[\d/.,]*", " ", label.upper())
    return " ".join(text.split())


def _flag_unusual_nature(results: list[LineResult], cashbook: CashbookSheet | None) -> None:
    """R-12: mesmo CPF/CNPJ com natureza habitual no mês e um movimento com outra natureza."""
    if cashbook is None:
        return
    by_tax_id: dict[str, list[LineResult]] = defaultdict(list)
    for line in results:
        natures = [p for p in line.parts if p.kind == "nature"]
        if line.status == IDENTIFIED and line.bank.tax_id and len(natures) == 1:
            by_tax_id[line.bank.tax_id].append(line)
    for lines in by_tax_id.values():
        keys = [_nature_key(line.parts[0].label) for line in lines]
        habitual, count = Counter(keys).most_common(1)[0]
        if count < 2:
            continue
        for line, key in zip(lines, keys, strict=True):
            # Grafias diferentes da mesma natureza ("ADIANTAMENTOCLIENTE X") não contam.
            if SequenceMatcher(None, key, habitual).ratio() < NATURE_SIMILARITY:
                line.status = FLAGGED
                line.reasons.append(
                    f"natureza diferente do habitual para este CPF/CNPJ "
                    f"(habitual: {habitual}; agora: {key})"
                )


@dataclass(frozen=True)
class _AccountRun:
    results: list[LineResult]
    unmatched_items: list[CollectionItem]
    unmatched_cash: list[CashbookLine]


def _run_account(
    bank_lines: Sequence[BankLine],
    collection: CollectionReport | None,
    cashbook: CashbookSheet | None,
    titles: OpenTitles,
) -> _AccountRun:
    """Processa uma conta: decompõe cobranças, liga ao caixa e classifica cada movimento."""
    results = [LineResult(line) for line in bank_lines]
    cash_by_day: dict[date, list[CashbookLine]] = defaultdict(list)
    for cash in cashbook.lines if cashbook else ():
        cash_by_day[cash.occurred_on].append(cash)
    used_cash: set[int] = set()
    items_by_day: dict[date, list[CollectionItem]] = defaultdict(list)
    for item in collection.items if collection else ():
        if item.credited_on:
            items_by_day[item.credited_on].append(item)
    used_items: set[int] = set()

    by_day: dict[date, list[LineResult]] = defaultdict(list)
    for result in results:
        by_day[result.bank.occurred_on].append(result)

    for day in sorted(by_day):
        day_results = by_day[day]
        _decompose_collections(
            day_results, items_by_day.get(day, []), used_items, collection is not None
        )
        _link_cashbook(day_results, cash_by_day.get(day, []), used_cash, cashbook is not None)
        for result in day_results:
            _classify(result, titles, cash_by_day.get(day, []), cashbook is not None)

    unmatched_cash = [c for c in (cashbook.lines if cashbook else ()) if id(c) not in used_cash]
    unmatched_items = [
        i for i in (collection.items if collection else ()) if id(i) not in used_items
    ]
    return _AccountRun(results, unmatched_items, unmatched_cash)


def _decompose_collections(
    day_results: list[LineResult], items: list[CollectionItem], used: set[int], available: bool
) -> None:
    lines = [r for r in day_results if r.bank.is_collection and r.bank.amount_cents > 0]
    if not lines:
        return
    if not available:
        for result in lines:
            result.reasons.append("cobrança sem francesinha do período para decompor")
        return
    pool = [i for i in items if id(i) not in used]
    for result in lines:
        values = [i.amount_cents for i in pool]
        chosen, ambiguous = subset_with_sum(values, result.bank.amount_cents)
        if chosen is None:
            total = sum(values)
            result.reasons.append(
                f"cobrança de {money(result.bank.amount_cents)} não fecha com os títulos da "
                f"francesinha lançados no dia (soma disponível {money(total)})"
            )
            continue
        if ambiguous:
            result.reasons.append("mais de uma combinação de títulos da francesinha fecha o valor")
            continue
        picked = [pool[i] for i in chosen]
        result.collection_items.extend(picked)
        for item in picked:
            used.add(id(item))
        pool = [i for i in pool if id(i) not in used]


def _link_cashbook(
    day_results: list[LineResult], cash: list[CashbookLine], used: set[int], available: bool
) -> None:
    if not available:
        return
    # Cobrança: cada título da francesinha casa com uma linha "FRANC" do caixa (mesmo valor).
    for result in day_results:
        for item in result.collection_items:
            match = next(
                (c for c in cash if id(c) not in used and c.inflow_cents == item.amount_cents),
                None,
            )
            if match:
                used.add(id(match))
                result.cashbook_rows.append(match.row)
    others = [r for r in day_results if not r.bank.is_collection]
    # 1:1 por valor; empate decidido pelo nome mais parecido e, depois, pela ordem.
    for result in others:
        same = [c for c in cash if id(c) not in used and c.amount_cents == result.bank.amount_cents]
        if not same:
            continue
        named = [c for c in same if _names_overlap(result.bank, c)]
        match = (named or same)[0]
        used.add(id(match))
        result.cashbook_rows.append(match.row)
    # 1:N por soma exata (ex.: débito de folha = várias linhas de salário).
    for result in others:
        if result.cashbook_rows:
            continue
        pool = [c for c in cash if id(c) not in used]
        chosen, ambiguous = subset_with_sum(
            [c.amount_cents for c in pool], result.bank.amount_cents
        )
        if chosen and not ambiguous and len(chosen) > 1:
            for index in chosen:
                used.add(id(pool[index]))
                result.cashbook_rows.append(pool[index].row)
    # N:1: vários movimentos do extrato somam uma linha do caixa (ex.: resgates parciais).
    for cash_line in [c for c in cash if id(c) not in used]:
        pending = [r for r in others if not r.cashbook_rows]
        chosen, ambiguous = subset_with_sum(
            [r.bank.amount_cents for r in pending], cash_line.amount_cents
        )
        if chosen and not ambiguous and len(chosen) > 1:
            used.add(id(cash_line))
            for index in chosen:
                pending[index].cashbook_rows.append(cash_line.row)


def _names_overlap(bank: BankLine, cash: CashbookLine) -> bool:
    name = bank.counterparty or bank.description
    return bool(name) and names_match(
        name, re.sub(r"^(PAGTO|PGTO|PAGO|RECEB)\s+", "", cash.history)
    )


def _classify(
    result: LineResult, titles: OpenTitles, cash_day: list[CashbookLine], has_cashbook: bool = True
) -> None:
    rows = {c.row: c for c in cash_day}
    linked = [rows[r] for r in result.cashbook_rows if r in rows]
    bank = result.bank
    if bank.is_collection:
        if not result.collection_items:
            return  # motivo já registrado na decomposição
        problems = 0
        for item in result.collection_items:
            cash = next((c for c in linked if c.inflow_cents == item.amount_cents), None)
            refs = [r for r in (cash.refs if cash else ()) if r.kind == "nf"]
            parts, reason = _settle_receipt(
                titles,
                RECEIVABLE,
                item.nominal_cents,
                refs,
                item.payer,
                f"francesinha {item.our_number}",
            )
            if reason == OUTSIDE:
                hint = _same_party_hint(titles, RECEIVABLE, item.nominal_cents, item.payer, refs)
                if hint:
                    problems += 1
                    result.reasons.append(f"{item.payer} {money(item.amount_cents)}: {hint}")
                else:
                    source = f"francesinha {item.our_number}"
                    result.parts.append(_outside_part(refs, item.amount_cents, source))
                continue
            if reason:
                problems += 1
                result.reasons.append(f"{item.payer} {money(item.amount_cents)}: {reason}")
                continue
            result.parts.extend(parts)
            if item.extra_cents:
                result.parts.append(
                    Part(
                        "interest",
                        item.extra_cents,
                        f"Juros/multa recebidos de {item.payer} (conta a definir, Q-53)",
                        source=f"francesinha {item.our_number}",
                    )
                )
        result.status = FLAGGED if problems else _status(result.parts)
        return
    kind = RECEIVABLE if bank.amount_cents > 0 else PAYABLE
    if not linked:
        # Sem o caixa, o nome após o CPF/CNPJ do extrato ainda acha título de valor exato (R-09).
        if bank.counterparty:
            parts, reason = _settle_receipt(
                titles,
                kind,
                abs(bank.amount_cents),
                [],
                bank.counterparty,
                f"extrato linha {bank.index}",
            )
            if not reason:
                result.parts.extend(parts)
                result.status = AUTOMATIC
                return
            if reason != OUTSIDE and not reason.startswith("nenhum título"):
                result.reasons.append(f"{bank.counterparty}: {reason}")
                return
        result.reasons.append(
            "movimento sem linha correspondente no caixa do cliente"
            if has_cashbook
            else "sem caixa do cliente e sem título de valor exato para identificar o movimento"
        )
        return
    if len(linked) == 1:
        cash = linked[0]
        refs = [r for r in cash.refs if r.kind in ("nf", "cte", "doc")]
        name = bank.counterparty
        if refs or name:
            parts, reason = _settle_receipt(
                titles, kind, abs(bank.amount_cents), refs, name, f"caixa linha {cash.row}"
            )
            if reason == OUTSIDE:
                hint = _same_party_hint(titles, kind, abs(bank.amount_cents), name, refs)
                if hint:
                    result.reasons.append(f"{cash.history}: {hint}")
                    return
                result.parts.append(
                    _outside_part(refs, abs(bank.amount_cents), f"caixa linha {cash.row}")
                )
                result.status = IDENTIFIED
                return
            if not reason:
                result.parts.extend(parts)
                result.status = AUTOMATIC
                return
            if refs or not reason.startswith("nenhum título"):
                # Documento citado que não fecha, ou fornecedor/cliente com título aberto de outro
                # valor (pagamento parcial?): não vira natureza, a contadora decide (R-13).
                result.reasons.append(f"{cash.history}: {reason}")
                return
        label = (
            cash.history
            if abs(cash.amount_cents) == abs(bank.amount_cents)
            else f"{cash.history} (parte)"
        )
        result.parts.append(
            Part("nature", abs(bank.amount_cents), label, source=f"caixa linha {cash.row}")
        )
        result.status = IDENTIFIED
        return
    # Várias linhas do caixa somam o movimento (folha, guias): cada uma é uma natureza.
    if sum(abs(c.amount_cents) for c in linked) != abs(bank.amount_cents):
        cash = linked[0]  # N:1 — o movimento é parte de uma linha do caixa
        result.parts.append(
            Part(
                "nature",
                abs(bank.amount_cents),
                f"{cash.history} (parte)",
                source=f"caixa linha {cash.row}",
            )
        )
        result.status = IDENTIFIED
        return
    for cash in linked:
        result.parts.append(
            Part("nature", abs(cash.amount_cents), cash.history, source=f"caixa linha {cash.row}")
        )
    result.status = IDENTIFIED


def _same_party_hint(
    titles: OpenTitles, kind: str, cents: int, name: str, refs: Sequence[DocumentRef]
) -> str | None:
    """Documento citado não está em aberto, mas o mesmo cliente/fornecedor tem título do mesmo
    valor (ex.: número digitado com um dígito a menos): sugere, sem baixar."""
    if not name:
        return None
    same = [i for i in titles.candidates(kind, [], name) if titles.balance[i.key] == cents]
    if not same:
        return None
    cited = ", ".join(str(r) for r in refs)
    return (
        f"{cited} citado no caixa não está em aberto; há título do mesmo nome e valor "
        f"({same[0].label}) — confirmar se é o mesmo documento"
    )


def _outside_part(refs: Sequence[DocumentRef], cents: int, source: str) -> Part:
    cited = ", ".join(str(r) for r in refs)
    return Part(
        "document", cents, f"{cited} citado no caixa, fora da posição de abertura", source=source
    )


def _status(parts: Sequence[Part]) -> str:
    if parts and all(p.kind in ("receivable", "payable", "interest", "investment") for p in parts):
        return AUTOMATIC
    return IDENTIFIED


def _compare(
    titles: OpenTitles, references: Sequence[TitlePosition | None]
) -> list[PositionDifference]:
    differences: list[PositionDifference] = []
    for reference in references:
        if reference is None:
            continue
        kind = reference.kind
        ref_index: dict[tuple[str, str, date, int], list[PositionInstallment]] = defaultdict(list)
        for item in reference.installments:
            ref_index[(item.party_code, item.document, item.due_on, item.amount_cents)].append(item)
        seen: set[int] = set()
        for key, item in titles.items.items():
            if key[0] != kind:
                continue
            simulated = titles.balance[key]
            match = next(
                (
                    r
                    for r in ref_index.get(
                        (item.party_code, item.document, item.due_on, item.amount_cents), []
                    )
                    if id(r) not in seen
                ),
                None,
            )
            reference_cents = match.balance_cents if match else 0
            if match:
                seen.add(id(match))
            if simulated == reference_cents:
                continue
            if simulated == 0:
                outcome = "baixado na simulação, aberto na referência"
            elif match is None or reference_cents == 0:
                outcome = "aberto na simulação, baixado na referência"
            else:
                outcome = "saldo diferente"
            differences.append(
                PositionDifference(kind, outcome, item.label, simulated, reference_cents)
            )
        for item in reference.installments:
            if id(item) not in seen and item.balance_cents:
                differences.append(
                    PositionDifference(
                        kind,
                        "título novo na referência (fora da abertura)",
                        item.label,
                        0,
                        item.balance_cents,
                    )
                )
    return differences
