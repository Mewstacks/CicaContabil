"""Read-only evidence from the observed Domínio account-report PDF layout.

An account report proves its bank-side rows, not complete journal entries.
Nothing in this module persists, allocates, approves or exports accounting facts.
"""

from __future__ import annotations

import hashlib
import io
import json
import os
import re
import tempfile
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pdfplumber
from pdfminer.pdfexceptions import PDFException
from pdfplumber.utils.exceptions import PdfminerException

MAX_SOURCE_BYTES = 25 * 1024 * 1024
MAX_PAGES = 500
MAX_ROWS = 100_000
_DAY = re.compile(r"\d{2}/\d{2}/\d{4}")
_MONEY = re.compile(r"(?:\d{1,3}(?:\.\d{3})*|\d+),\d{2}")


class LedgerEvidenceError(ValueError):
    pass


def write_evidence_report(path: Path, report: dict[str, Any]) -> None:
    """Publish a complete private report without replacing any existing destination."""

    def serialize(value: Any) -> str:
        if type(value) is date:
            return value.isoformat()
        raise TypeError("Tipo não serializável na conferência.")

    content = (
        json.dumps(report, default=serialize, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8")
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=path.parent, prefix=".cica-evidence-", delete=False
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path, follow_symlinks=False)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


@dataclass(frozen=True)
class LedgerEvidenceLine:
    occurred_on: date
    printed_entry_number: str
    debit_cents: int
    credit_cents: int
    balance_cents: int
    counterparty_code: str | None
    reference: dict[str, Any]

    @property
    def amount_cents(self) -> int:
        return self.debit_cents - self.credit_cents


@dataclass(frozen=True)
class LedgerEvidence:
    company_name: str
    taxpayer_id: str
    ledger_code: str
    classification: str
    ledger_name: str
    period_start: date
    period_end: date
    opening_cents: int
    closing_cents: int
    lines: tuple[LedgerEvidenceLine, ...]


def _money(value: str) -> int:
    if not _MONEY.fullmatch(value):
        raise LedgerEvidenceError("Razão: valor fora do formato suportado.")
    integer, fraction = value.replace(".", "").split(",")
    result = int(integer) * 100 + int(fraction)
    if result > 9223372036854775807:
        raise LedgerEvidenceError("Razão: valor excede o limite suportado.")
    return result


def _balance(value: str) -> int:
    side = value[-1:] if value[-1:] in {"D", "C"} else ""
    result = _money(value[:-1] if side else value)
    if result and not side:
        raise LedgerEvidenceError("Razão: saldo não zero sem indicação D/C.")
    return -result if side == "C" else result


def _day(value: str) -> date:
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError as exc:
        raise LedgerEvidenceError("Razão: data inválida.") from exc


def _normalize_name(value: str) -> str:
    return " ".join(value.split()).casefold()


def _header(page: Any, number: int) -> tuple[str, ...]:
    # Coordinates belong to the inspected A4 portrait layout, in PDF points.
    if abs(page.width - 595.273) > 1 or abs(page.height - 841.886) > 1:
        raise LedgerEvidenceError("Razão: tamanho de página fora do layout suportado.")
    text = page.crop((0, 0, page.width, 82)).extract_text(x_tolerance=1) or ""
    company = re.search(r"^Empresa:\s*(.+?)\s+Folha:\s*(\d+)\s*$", text, re.M)
    taxpayer = re.search(r"^C\.N\.P\.J\.:\s*(\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2})$", text, re.M)
    period = re.search(r"^Período:\s*(\S+)\s+-\s+(\S+)\s*$", text, re.M)
    account = re.search(r"^Conta:\s*(\d+)\s+-\s+([\d.]+)\s+(.+)$", text, re.M)
    columns = (
        "RAZÃO",
        "Data",
        "Número",
        "Histórico",
        "Cta.C.Part.",
        "Débito",
        "Crédito",
        "Saldo-Exercício",
    )
    if not (company and taxpayer and period and account and all(c in text for c in columns)):
        raise LedgerEvidenceError("Razão: cabeçalho incompleto ou layout não suportado.")
    header_words = page.crop((0, 55, page.width, 72)).extract_words(x_tolerance=1)
    for label, left, right in [
        ("Débito", 365, 420),
        ("Crédito", 420, 490),
        ("Saldo-Exercício", 490, 560),
    ]:
        matches = [w for w in header_words if w["text"] == label]
        if len(matches) != 1 or not left <= matches[0]["x0"] < matches[0]["x1"] <= right:
            raise LedgerEvidenceError("Razão: posição dos cabeçalhos numéricos não suportada.")
    if int(company[2]) != number:
        raise LedgerEvidenceError("Razão: sequência de folhas incompleta ou repetida.")
    return (
        company[1].strip(),
        taxpayer[1],
        account[1],
        account[2],
        account[3].strip(),
        period[1],
        period[2],
    )


def _near(words: list[dict[str, Any]], top: float) -> list[dict[str, Any]]:
    return sorted((w for w in words if abs(w["top"] - top) < 0.25), key=lambda w: w["x0"])


def _read_report(pdf: Any) -> LedgerEvidence:
    if not 1 <= len(pdf.pages) <= MAX_PAGES:
        raise LedgerEvidenceError("Razão: quantidade de páginas fora do limite suportado.")
    identity: tuple[str, ...] | None = None
    opening: int | None = None
    totals: tuple[int, int] | None = None
    lines: list[LedgerEvidenceLine] = []
    entry_numbers: set[str] = set()
    previous: int | None = None
    for number, original in enumerate(pdf.pages, 1):
        # Do not deduplicate nearby glyphs: the report has overlapping text
        # layers, and numeric zeroes can otherwise disappear from a balance.
        page = original
        current = _header(page, number)
        if identity is None:
            identity = current
        elif current != identity:
            raise LedgerEvidenceError("Razão: empresa, conta ou período mudou entre páginas.")
        start, end = _day(current[5]), _day(current[6])
        if start > end:
            raise LedgerEvidenceError("Razão: período inválido.")
        # The observed PDF repeats history text behind rows, 0.9 pt above the
        # numeric baseline. A broad vertical tolerance interleaves those layers.
        words = [
            w for w in page.extract_words(x_tolerance=1, y_tolerance=0.15) if 82 < w["top"] < 810
        ]
        openings = [w for w in words if w["text"] == "ANTERIOR"]
        if openings:
            if number != 1 or len(openings) != 1:
                raise LedgerEvidenceError(
                    "Razão: saldo anterior repetido ou fora da primeira folha."
                )
            row = _near(words, openings[0]["top"])
            if not any(w["text"] == "SALDO" for w in row):
                raise LedgerEvidenceError("Razão: saldo anterior incompleto.")
            amounts = [w for w in row if w["x0"] >= 490]
            if len(amounts) != 1:
                raise LedgerEvidenceError("Razão: saldo anterior ausente ou ambíguo.")
            opening = previous = _balance(amounts[0]["text"])
        if opening is None:
            raise LedgerEvidenceError("Razão: saldo anterior não informado.")
        total_words = [w for w in words if w["text"] == "Total" and 240 < w["x0"] < 280]
        total_top = 810.0
        if total_words:
            if len(total_words) != 1 or totals is not None or number != len(pdf.pages):
                raise LedgerEvidenceError("Razão: total repetido ou fora da última folha.")
            total_top = float(total_words[0]["top"])
            row = _near(words, total_top)
            if "da conta:" not in " ".join(w["text"] for w in row):
                raise LedgerEvidenceError("Razão: total da conta incompleto.")
            amounts = [w for w in row if w["x0"] >= 365]
            if len(amounts) != 2 or not (amounts[0]["x1"] < 420 < amounts[1]["x1"] < 490):
                raise LedgerEvidenceError("Razão: colunas dos totais inválidas.")
            totals = (_money(amounts[0]["text"]), _money(amounts[1]["text"]))
        starts = [w for w in words if w["x0"] < 40 and _DAY.fullmatch(w["text"])]
        entries = [w for w in words if 40 <= w["x0"] < w["x1"] <= 78 and w["text"].isdigit()]
        if len(starts) != len(entries) or not starts:
            raise LedgerEvidenceError("Razão: data/número de lançamento ausente.")
        if any(not any(abs(w["top"] - d["top"]) < 0.25 for d in starts) for w in entries):
            raise LedgerEvidenceError("Razão: lançamento sem data na mesma linha.")
        for first in starts:
            top = float(first["top"])
            if top >= total_top or not _DAY.fullmatch(first["text"]):
                raise LedgerEvidenceError("Razão: linha fora da tabela ou data inválida.")
            row = _near(words, top)
            ids = [w["text"] for w in row if 40 <= w["x0"] < w["x1"] <= 78]
            if len(ids) != 1 or not ids[0].isdigit() or ids[0] in entry_numbers:
                raise LedgerEvidenceError("Razão: número de lançamento inválido ou repetido.")
            amounts = [w for w in row if w["x0"] >= 365]
            debit = [w for w in amounts if w["x1"] < 420]
            credit = [w for w in amounts if 420 <= w["x1"] < 490]
            balance = [w for w in amounts if w["x1"] >= 490]
            if len(debit) + len(credit) != 1 or len(balance) != 1:
                raise LedgerEvidenceError("Razão: colunas de débito/crédito/saldo incompletas.")
            occurred = _day(first["text"])
            if not start <= occurred <= end or (lines and occurred < lines[-1].occurred_on):
                raise LedgerEvidenceError("Razão: data fora do período ou da ordem.")
            d = _money(debit[0]["text"]) if debit else 0
            c = _money(credit[0]["text"]) if credit else 0
            b = _balance(balance[0]["text"])
            if not d + c or previous is None or previous + d - c != b:
                raise LedgerEvidenceError("Razão: sequência de saldos inconsistente.")
            counterparts = [w["text"] for w in row if 325 <= w["x0"] < 365]
            if len(counterparts) > 1 or (counterparts and not counterparts[0].isdigit()):
                raise LedgerEvidenceError("Razão: coluna de contrapartida ambígua.")
            lines.append(
                LedgerEvidenceLine(
                    occurred,
                    ids[0],
                    d,
                    c,
                    b,
                    counterparts[0] if counterparts else None,
                    {"page": number, "top_pdf_points": top, "layout": "dominio-account-pdf-v1"},
                )
            )
            entry_numbers.add(ids[0])
            previous = b
            if len(lines) > MAX_ROWS:
                raise LedgerEvidenceError("Razão: quantidade de linhas excede o limite.")
    if not lines or totals != (
        sum(r.debit_cents for r in lines),
        sum(r.credit_cents for r in lines),
    ):
        raise LedgerEvidenceError("Razão: totais ausentes ou divergentes das linhas.")
    assert identity is not None and opening is not None and previous is not None
    return LedgerEvidence(
        identity[0],
        identity[1],
        identity[2],
        identity[3],
        identity[4],
        _day(identity[5]),
        _day(identity[6]),
        opening,
        previous,
        tuple(lines),
    )


def read_dominio_ledger_pdf(content: bytes) -> LedgerEvidence:
    if not content or len(content) > MAX_SOURCE_BYTES:
        raise LedgerEvidenceError("Razão: arquivo vazio ou maior que 25 MiB.")
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            return _read_report(pdf)
    except (PDFException, PdfminerException, OSError) as exc:
        raise LedgerEvidenceError("Razão: PDF inválido ou indisponível para leitura.") from exc


def compare_ledger_files(
    *,
    ofx: bytes,
    bank_pdf: bytes,
    ledger_pdf: bytes,
    company_name: str,
    ledger_code: str,
) -> dict[str, Any]:
    """Compare the supplied test corpus, preserving ambiguity instead of allocating."""
    from apps.hub.bank_evidence import compare_bank_files, read_sicredi_pdf

    if any(
        not content or len(content) > MAX_SOURCE_BYTES for content in (ofx, bank_pdf, ledger_pdf)
    ):
        raise LedgerEvidenceError("Fonte vazia ou maior que 25 MiB.")
    ledger = read_dominio_ledger_pdf(ledger_pdf)
    if (
        _normalize_name(ledger.company_name) != _normalize_name(company_name)
        or ledger.ledger_code != ledger_code
    ):
        raise LedgerEvidenceError("Razão: empresa/conta difere do recorte solicitado.")
    try:
        pair = compare_bank_files(ofx=ofx, pdf=bank_pdf)
        bank = read_sicredi_pdf(bank_pdf)
        assert bank is not None
        with pdfplumber.open(io.BytesIO(bank_pdf)) as pdf:
            text = pdf.pages[0].extract_text() or ""
    except (PDFException, PdfminerException, OSError) as exc:
        raise LedgerEvidenceError("Extrato: PDF inválido ou indisponível para leitura.") from exc
    holder = re.search(r"^Associado:\s*(.+)$", text, re.M)
    if not holder or _normalize_name(holder[1]) != _normalize_name(company_name):
        raise LedgerEvidenceError("Extrato: titular difere do recorte solicitado.")
    if (bank.period_start, bank.period_end) != (ledger.period_start, ledger.period_end):
        raise LedgerEvidenceError("Banco e Razão têm períodos diferentes.")
    bank_groups: dict[tuple[date, int], list[dict[str, Any]]] = defaultdict(list)
    ledger_groups: dict[tuple[date, int], list[dict[str, Any]]] = defaultdict(list)
    for index, row in enumerate(bank.lines, 1):
        bank_groups[(row.occurred_on, row.amount_cents)].append({"index": index, **asdict(row)})
    for row_ledger in ledger.lines:
        ledger_groups[(row_ledger.occurred_on, row_ledger.amount_cents)].append(asdict(row_ledger))
    bank_counts = Counter({key: len(rows) for key, rows in bank_groups.items()})
    ledger_counts = Counter({key: len(rows) for key, rows in ledger_groups.items()})
    groups = []
    for key in sorted(bank_counts.keys() | ledger_counts.keys()):
        nb, nl = bank_counts[key], ledger_counts[key]
        state = (
            "bank_only"
            if not nl
            else "ledger_only"
            if not nb
            else "unique_candidate"
            if nb == nl == 1
            else "ambiguous_candidates"
        )
        groups.append(
            {
                "date": key[0],
                "signed_amount_cents": key[1],
                "state": state,
                "bank_rows": bank_groups[key],
                "ledger_rows": ledger_groups[key],
            }
        )
    return {
        "contract": "bank-ledger-evidence-report-v1",
        "read_only": True,
        "status": "requires_review",
        "homologated": False,
        "confirmed_allocations": 0,
        "complete_journal_entries": False,
        "erp_written": False,
        "transmitted": False,
        "account_relation_verified": False,
        "source_sha256": {
            "ofx": hashlib.sha256(ofx).hexdigest(),
            "bank_pdf": hashlib.sha256(bank_pdf).hexdigest(),
            "ledger_pdf": hashlib.sha256(ledger_pdf).hexdigest(),
        },
        "company_name": ledger.company_name,
        "ledger_code": ledger.ledger_code,
        "period_start": ledger.period_start,
        "period_end": ledger.period_end,
        "bank_pair": pair,
        "bank_count": len(bank.lines),
        "ledger_count": len(ledger.lines),
        "same_date_amount_multiset": bank_counts == ledger_counts,
        "equal_date_amount_count": sum((bank_counts & ledger_counts).values()),
        "bank_only_count": sum((bank_counts - ledger_counts).values()),
        "ledger_only_count": sum((ledger_counts - bank_counts).values()),
        "unique_candidate_count": sum(g["state"] == "unique_candidate" for g in groups),
        "ambiguous_group_count": sum(g["state"] == "ambiguous_candidates" for g in groups),
        "blank_counterparty_count": sum(r.counterparty_code is None for r in ledger.lines),
        "opening_bank_cents": bank.opening_cents,
        "closing_bank_cents": bank.closing_cents,
        "opening_ledger_cents": ledger.opening_cents,
        "closing_ledger_cents": ledger.closing_cents,
        "same_opening_and_closing": (bank.opening_cents, bank.closing_cents)
        == (ledger.opening_cents, ledger.closing_cents),
        "groups": groups,
    }
