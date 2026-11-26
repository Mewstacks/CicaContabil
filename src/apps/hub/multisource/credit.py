"""Empréstimo e fatura do cartão do Sicredi em PDF texto — D-418, PC-33.

Só identificam o débito do extrato: o cronograma do empréstimo traz o valor total de cada parcela,
sem separar juros e principal (Q-55), e lançar a fatura pelo total ou por despesa está em aberto
(Q-56).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date

from apps.hub.multisource.common import (
    MAX_SOURCE_BYTES,
    MultisourceError,
    cents_from_text,
    parse_day,
)

LOAN_LAYOUT = "sicredi-emprestimo-parcelas-text-v1"
CARD_LAYOUT = "sicredi-fatura-cartao-text-v1"
MONEY = r"(\d{1,3}(?:\.\d{3})*,\d{2})"
DAY = r"\d{2}/\d{2}/\d{4}"
LOAN_LINE = re.compile(rf"^(\d{{3}})\s+([A-ZÀ-Ú ]+?)\s+({DAY})(?:\s+({DAY}))?\s+{MONEY}$")
CARD_LINE = re.compile(rf"^(\d{{2}})/([a-z]{{3}})\s+\d{{2}}:\d{{2}}\s+(.+?)\s+(-?)R\$\s*{MONEY}$")
MONTHS = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


@dataclass(frozen=True)
class LoanInstallment:
    number: int
    status: str
    due_on: date
    paid_on: date | None
    amount_cents: int


@dataclass(frozen=True)
class LoanSchedule:
    contract: str
    released_on: date | None
    installments: tuple[LoanInstallment, ...]

    @property
    def count(self) -> int:
        return max((i.number for i in self.installments), default=0)

    def open_after(self, day: date) -> int:
        """Soma das parcelas que vencem depois de `day` e não estão pagas até lá."""
        return sum(
            i.amount_cents
            for i in self.installments
            if i.due_on > day and (i.paid_on is None or i.paid_on > day)
        )


@dataclass(frozen=True)
class CardTransaction:
    occurred_on: date
    description: str
    amount_cents: int  # positivo para despesa, negativo para pagamento ou crédito


@dataclass(frozen=True)
class CardInvoice:
    card: str
    due_on: date
    total_cents: int
    transactions: tuple[CardTransaction, ...]
    warnings: tuple[str, ...] = ()

    @property
    def expenses(self) -> tuple[CardTransaction, ...]:
        return tuple(t for t in self.transactions if t.amount_cents > 0)


def _pdf_pages(content: bytes, label: str) -> list[str]:
    import pdfplumber

    if len(content) > MAX_SOURCE_BYTES:
        raise MultisourceError(f"{label}: arquivo maior que 25 MiB.")
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return [page.extract_text() or "" for page in pdf.pages[:50]]
    except Exception as exc:  # pdfplumber/pdfminer levantam tipos variados para PDF inválido
        raise MultisourceError(f"{label}: PDF ilegível.") from exc


def parse_loan_text(pages: list[str]) -> LoanSchedule:
    text = "\n".join(pages)
    contract = re.search(r"Nro do T[íi]tulo:\s*(\S+)", text)
    if "Parcelas do T" not in text or contract is None:
        raise MultisourceError("Arquivo não é a consulta de parcelas de empréstimo do Sicredi.")
    released = re.search(r"Data de Libera[çc][ãa]o:\s*(\d{2}/\d{2}/\d{4})", text)
    installments: dict[int, LoanInstallment] = {}
    for raw in text.splitlines():
        match = LOAN_LINE.match(raw.strip())
        if not match:
            continue
        number, status, due, paid, value = match.groups()
        due_on = parse_day(due)
        assert due_on
        installments[int(number)] = LoanInstallment(
            int(number), status.strip(), due_on, parse_day(paid), cents_from_text(value)
        )
    if not installments:
        raise MultisourceError("Empréstimo: nenhuma parcela encontrada.")
    return LoanSchedule(
        contract[1],
        parse_day(released[1]) if released else None,
        tuple(installments[n] for n in sorted(installments)),
    )


def read_loan_pdf(content: bytes) -> LoanSchedule:
    return parse_loan_text(_pdf_pages(content, "Empréstimo"))


def parse_card_text(pages: list[str]) -> CardInvoice:
    text = "\n".join(pages)
    card = re.search(r"final (\d{4})", text)
    due = re.search(r"Vencimento (\d{2}/\d{2}/\d{4})", text)
    total = re.search(r"Total desta Fatura\s+" + MONEY, text) or re.search(
        r"Total fatura de \w+ R\$\s*" + MONEY, text
    )
    if card is None or due is None or total is None:
        raise MultisourceError("Arquivo não é a fatura de cartão do Sicredi.")
    due_on = parse_day(due[1])
    assert due_on
    transactions: list[CardTransaction] = []
    seen: set[tuple[str, ...]] = set()
    for raw in text.splitlines():
        match = CARD_LINE.match(raw.strip())
        if not match or match.groups() in seen:
            continue
        seen.add(match.groups())
        day, month_text, description, negative, value = match.groups()
        if month_text not in MONTHS:
            continue
        month = MONTHS.index(month_text) + 1
        # A fatura não traz o ano: a transação é do mês do vencimento ou de antes dele.
        year = due_on.year - (1 if month > due_on.month else 0)
        try:
            occurred = date(year, month, int(day))
        except ValueError:
            continue
        cents = cents_from_text(value)
        transactions.append(
            CardTransaction(occurred, " ".join(description.split()), -cents if negative else cents)
        )
    total_cents = cents_from_text(total[1])
    expenses = sum(t.amount_cents for t in transactions if t.amount_cents > 0)
    warnings = ()
    if expenses != total_cents:
        warnings = (
            f"Fatura do cartão final {card[1]}: despesas listadas somam {expenses / 100:.2f}, "
            f"total da fatura {total_cents / 100:.2f} (encargos ou parcelas de outras faturas).",
        )
    return CardInvoice(card[1], due_on, total_cents, tuple(transactions), warnings)


def read_card_pdf(content: bytes) -> CardInvoice:
    return parse_card_text(_pdf_pages(content, "Fatura do cartão"))
