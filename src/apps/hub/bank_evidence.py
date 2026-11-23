"""Read-only evidence for the supplied Sicredi textual layout; no accounting inference."""

from __future__ import annotations

import io
import re
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

import pdfplumber

MONEY = re.compile(r"^-?\d{1,3}(?:\.\d{3})*,\d{2}$")
DAY = re.compile(r"^\d{2}/\d{2}/\d{4}$")


@dataclass(frozen=True)
class StatementLine:
    occurred_on: date
    amount_cents: int
    balance_cents: int
    description: str
    document: str
    reference: dict[str, Any]


@dataclass(frozen=True)
class StatementEvidence:
    period_start: date
    period_end: date
    cooperative: str
    account: str
    opening_cents: int
    closing_cents: int
    lines: tuple[StatementLine, ...]


def _day(value: str) -> date:
    return datetime.strptime(value, "%d/%m/%Y").date()


def _money(value: str) -> int:
    return int(Decimal(value.replace(".", "").replace(",", ".")) * 100)


def read_sicredi_pdf(content: bytes) -> StatementEvidence | None:
    from apps.hub.reconciliation_service import MAX_PAGES, MAX_ROWS, ReconciliationError

    with pdfplumber.open(io.BytesIO(content)) as pdf:
        if len(pdf.pages) > MAX_PAGES:
            raise ReconciliationError("PDF excede 500 páginas.")
        first = pdf.pages[0].extract_text() or ""
        period = re.search(
            r"Extrato\s*\(Período de (\d{2}/\d{2}/\d{4}) a (\d{2}/\d{2}/\d{4})\)", first
        )
        cooperative = re.search(r"Cooperativa:\s*(\d+)", first)
        account = re.search(r"Conta:\s*([\d-]+)", first)
        opening = re.search(r"SALDO ANTERIOR\s+(-?[\d.]+,\d{2})", first)
        if not all([period, cooperative, account, opening]):
            return None
        assert period and cooperative and account and opening
        # This combination of metadata and table columns identifies the supported layout.
        words = pdf.pages[0].extract_words()
        doc_header = next((w for w in words if w["text"] == "Documento"), None)
        if doc_header is None or "Saldo (R$)" not in first or "Valor (R$)" not in first:
            return None
        start, end = _day(period[1]), _day(period[2])
        if start > end:
            raise ReconciliationError("Sicredi: período inválido; revise o extrato original.")
        previous = _money(opening[1])
        lines: list[StatementLine] = []
        finished = False
        for page_number, page in enumerate(pdf.pages, 1):
            words = page.extract_words()
            rows: list[list[dict[str, Any]]] = []
            for word in sorted(words, key=lambda w: (float(w["top"]), float(w["x0"]))):
                if not rows or abs(float(word["top"]) - float(rows[-1][0]["top"])) > 2:
                    rows.append([])
                rows[-1].append(word)
            for row_number, row in enumerate(rows, 1):
                row.sort(key=lambda w: float(w["x0"]))
                text = " ".join(w["text"] for w in row)
                if "Lançamentos Futuros" in text:
                    finished = True
                if finished or not DAY.fullmatch(row[0]["text"]):
                    continue
                if len(row) < 4 or not all(MONEY.fullmatch(w["text"]) for w in row[-2:]):
                    raise ReconciliationError(
                        "Sicredi: movimento sem valor/saldo; revise o PDF original."
                    )
                occurred = _day(row[0]["text"])
                amount, balance = _money(row[-2]["text"]), _money(row[-1]["text"])
                if not start <= occurred <= end or not amount or previous + amount != balance:
                    raise ReconciliationError(
                        "Sicredi: data ou sequência de saldos diverge; revise o PDF."
                    )
                if lines and occurred < lines[-1].occurred_on:
                    raise ReconciliationError("Sicredi: movimentos fora da ordem de data.")
                body = row[1:-2]
                description = " ".join(w["text"] for w in body if w["x0"] < doc_header["x0"] - 1)
                document = " ".join(w["text"] for w in body if w["x0"] >= doc_header["x0"] - 1)
                if not description:
                    raise ReconciliationError("Sicredi: movimento sem descrição; revise o PDF.")
                lines.append(
                    StatementLine(
                        occurred,
                        amount,
                        balance,
                        description,
                        document,
                        {
                            "page": page_number,
                            "line": row_number,
                            "layout": "sicredi-text-v1",
                            "reported_balance_cents": balance,
                            "reported_account": account[1],
                            "reported_cooperative": cooperative[1],
                            "bbox": {
                                "x0": min(w["x0"] for w in row),
                                "top": min(w["top"] for w in row),
                                "x1": max(w["x1"] for w in row),
                                "bottom": max(w["bottom"] for w in row),
                                "unit": "pdf_points",
                            },
                        },
                    )
                )
                if len(lines) > MAX_ROWS:
                    raise ReconciliationError("PDF excede 100.000 movimentos.")
                previous = balance
        if not lines:
            raise ReconciliationError(
                "Sicredi: nenhum movimento lido; revise o documento original."
            )
        return StatementEvidence(
            start, end, cooperative[1], account[1], _money(opening[1]), previous, tuple(lines)
        )


def compare_bank_files(*, ofx: bytes, pdf: bytes) -> dict[str, Any]:
    """Two bank representations are never independent ledger evidence."""
    from apps.hub.reconciliation import parse_ofx
    from apps.hub.reconciliation_service import ReconciliationError

    statement = parse_ofx(ofx)
    evidence = read_sicredi_pdf(pdf)
    if evidence is None:
        raise ReconciliationError("PDF fora do layout textual Sicredi suportado.")
    bank = Counter((r.occurred_on, r.amount_cents) for r in statement.transactions)
    paper = Counter((r.occurred_on, r.amount_cents) for r in evidence.lines)
    return {
        "read_only": True,
        "homologated": False,
        "independent_ledger": False,
        "account_relation": "requires_confirmation",
        "layout": "sicredi-text-v1",
        "period_start": evidence.period_start.isoformat(),
        "period_end": evidence.period_end.isoformat(),
        "pdf_count": len(evidence.lines),
        "ofx_count": len(statement.transactions),
        "pdf_only_count": sum((paper - bank).values()),
        "ofx_only_count": sum((bank - paper).values()),
        "same_date_amount_multiset": bank == paper,
        "opening_bank_cents": evidence.opening_cents,
        "closing_bank_cents": evidence.closing_cents,
        "running_balances_valid": True,
    }
