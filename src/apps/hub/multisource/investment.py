"""Extrato de aplicação (Depósito a Prazo) do Sicredi em PDF texto — D-411, PC-33.

Movimentos: Saldo Anterior, Aplicacoes, Resgates, Rendimentos, Encargos de IRRF/IOF e Saldo Atual.
O resgate é o valor que cai na conta corrente; rendimentos e encargos só movimentam a aplicação.
A cadeia conferida é: saldo anterior + aplicações - resgates + rendimentos - encargos = saldo atual.
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

LAYOUT = "sicredi-aplicacao-text-v1"
LINE = re.compile(r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+(-?\d{1,3}(?:\.\d{3})*,\d{2})$")
KINDS = {
    "aplicacoes": "application",
    "aplicacao": "application",
    "resgates": "redemption",
    "resgate": "redemption",
    "rendimentos": "income",
    "encargos de irrf": "income_tax",
    "encargos de iof": "iof",
}
SIGN = {"application": 1, "redemption": -1, "income": 1, "income_tax": -1, "iof": -1}


@dataclass(frozen=True)
class InvestmentMovement:
    occurred_on: date
    kind: str  # application | redemption | income | income_tax | iof
    amount_cents: int
    line: int


@dataclass(frozen=True)
class InvestmentStatement:
    product: str
    account: str
    opening_cents: int
    closing_cents: int
    movements: tuple[InvestmentMovement, ...]

    def total(self, kind: str) -> int:
        return sum(m.amount_cents for m in self.movements if m.kind == kind)


def _fold(text: str) -> str:
    text = text.strip().lower()
    for a, b in (("ç", "c"), ("õ", "o"), ("ã", "a"), ("á", "a"), ("é", "e")):
        text = text.replace(a, b)
    return text


def parse_investment_text(pages: list[str]) -> InvestmentStatement:
    first = pages[0] if pages else ""
    if "Extrato de Aplicação" not in first:
        raise MultisourceError("Arquivo não é o Extrato de Aplicação do Sicredi.")
    product = re.search(r"Produto:\s*(.+)", first)
    account = re.search(r"Conta Corrente:\s*(\d+)", first)
    opening = closing = None
    movements: list[InvestmentMovement] = []
    previous_last: tuple[str, ...] | None = None
    number = 0
    for page in pages:
        page_lines = [m.groups() for m in (LINE.match(t.strip()) for t in page.splitlines()) if m]
        # O PDF repete a última movimentação de uma página no topo da seguinte.
        if previous_last and page_lines and page_lines[0] == previous_last:
            page_lines = page_lines[1:]
        if page_lines:
            previous_last = page_lines[-1]
        for day_text, history, value in page_lines:
            number += 1
            label = _fold(history)
            if label == "saldo anterior":
                opening = cents_from_text(value)
                continue
            if label == "saldo atual":
                closing = cents_from_text(value)
                continue
            kind = KINDS.get(label)
            if kind is None:
                raise MultisourceError(f"Extrato de aplicação: histórico desconhecido {history!r}.")
            day = parse_day(day_text)
            assert day
            movements.append(InvestmentMovement(day, kind, cents_from_text(value), number))
    if opening is None or closing is None:
        raise MultisourceError("Extrato de aplicação: saldo anterior ou atual ausente.")
    running = opening + sum(SIGN[m.kind] * m.amount_cents for m in movements)
    if running != closing:
        raise MultisourceError(
            "Extrato de aplicação: a cadeia de saldos não fecha "
            f"({running / 100:.2f} calculado vs. {closing / 100:.2f} informado)."
        )
    return InvestmentStatement(
        product[1].strip() if product else "",
        account[1] if account else "",
        opening,
        closing,
        tuple(movements),
    )


def read_investment_pdf(content: bytes) -> InvestmentStatement:
    import pdfplumber

    if len(content) > MAX_SOURCE_BYTES:
        raise MultisourceError("Extrato de aplicação: arquivo maior que 25 MiB.")
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            pages = [page.extract_text() or "" for page in pdf.pages[:100]]
    except Exception as exc:  # pdfplumber/pdfminer levantam tipos variados para PDF inválido
        raise MultisourceError("Extrato de aplicação: PDF ilegível.") from exc
    return parse_investment_text(pages)
