"""Posição de títulos por NF e parcela em planilha (R-07, D-417, PC-33).

Simulação (D-409): a planilha mostra o que a CICA baixaria no mês a partir da posição de abertura;
nada é lançado. Valores ficam como números e datas como datas, para a contadora filtrar e somar.
"""

from __future__ import annotations

import io
from collections import defaultdict
from datetime import date

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.worksheet import Worksheet

from apps.hub.multisource.common import money
from apps.hub.multisource.matching import SimulationResult
from apps.hub.multisource.title_position import PAYABLE, RECEIVABLE

MONEY_FORMAT = "#,##0.00"
DATE_FORMAT = "DD/MM/YYYY"
HEADER_FILL = PatternFill("solid", fgColor="DDE7E2")
SHEETS = ((RECEIVABLE, "A receber", "Cliente"), (PAYABLE, "A pagar", "Fornecedor"))
COLUMNS = (
    ("Código", 10),
    ("{party}", 38),
    ("NF", 12),
    ("Parcela", 9),
    ("Emissão", 12),
    ("Vencimento", 12),
    ("Valor da parcela", 16),
    ("Saldo na abertura", 17),
    ("Baixado no mês", 16),
    ("Saldo final", 15),
    ("Situação", 14),
    ("Baixas no mês", 44),
    ("Posição do Domínio do mês", 34),
)
MONEY_COLUMNS = (7, 8, 9, 10)
DATE_COLUMNS = (5, 6)


def _situation(opening: int, closing: int) -> str:
    if closing == 0:
        return "Baixado"
    if closing < opening:
        return "Baixa parcial"
    return "Em aberto"


def _settlements(result: SimulationResult) -> dict[tuple[str, str, str, int], list[str]]:
    """Data, conta e valor de cada baixa simulada, por parcela."""
    found: dict[tuple[str, str, str, int], list[str]] = defaultdict(list)
    for line in result.lines:
        for part in line.parts:
            if part.installment_key is None:
                continue
            found[part.installment_key].append(
                f"{line.bank.occurred_on:%d/%m/%Y} {line.bank.account} {money(part.amount_cents)}"
            )
    return found


def _header(sheet: Worksheet, party: str) -> None:
    for index, (title, width) in enumerate(COLUMNS, start=1):
        cell = sheet.cell(row=1, column=index, value=title.format(party=party))
        cell.font = Font(bold=True)
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(vertical="center", wrap_text=True)
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "C2"


def _money(value: int) -> float:
    return round(value / 100, 2)


def render_position_xlsx(result: SimulationResult, *, period: date | None = None) -> bytes:
    book = Workbook()
    summary = book.active
    summary.title = "Resumo"
    settlements = _settlements(result)
    reference = {d.label: d.outcome for d in result.differences}
    totals: list[tuple[str, int, int, int, int]] = []
    for kind, title, party in SHEETS:
        keys = sorted(
            (k for k in result.installments if k[0] == kind),
            key=lambda k: (
                result.installments[k].party_name,
                result.installments[k].document,
                result.installments[k].ordinal,
            ),
        )
        if not keys:
            continue
        sheet = book.create_sheet(title)
        _header(sheet, party)
        opening_total = closing_total = settled_count = 0
        for row, key in enumerate(keys, start=2):
            item = result.installments[key]
            closing = result.closing[key]
            opening_total += item.balance_cents
            closing_total += closing
            settled_count += closing < item.balance_cents
            values = (
                item.party_code,
                item.party_name,
                item.document,
                f"{item.ordinal}/{item.count}",
                item.issued_on,
                item.due_on,
                _money(item.amount_cents),
                _money(item.balance_cents),
                _money(item.balance_cents - closing),
                _money(closing),
                _situation(item.balance_cents, closing),
                "; ".join(settlements.get(key, ())),
                reference.get(item.label, ""),
            )
            for column, value in enumerate(values, start=1):
                cell = sheet.cell(row=row, column=column, value=value)
                if column in MONEY_COLUMNS:
                    cell.number_format = MONEY_FORMAT
                elif column in DATE_COLUMNS:
                    cell.number_format = DATE_FORMAT
        total_row = len(keys) + 2
        sheet.cell(row=total_row, column=2, value="Total").font = Font(bold=True)
        for column in MONEY_COLUMNS:
            letter = get_column_letter(column)
            cell = sheet.cell(
                row=total_row, column=column, value=f"=SUM({letter}2:{letter}{total_row - 1})"
            )
            cell.number_format = MONEY_FORMAT
            cell.font = Font(bold=True)
        sheet.auto_filter.ref = f"A1:{get_column_letter(len(COLUMNS))}{total_row - 1}"
        totals.append((title, len(keys), settled_count, opening_total, closing_total))

    month = f" — {period:%m/%Y}" if period else ""
    summary["A1"] = f"Posição de títulos por NF{month}"
    summary["A1"].font = Font(bold=True, size=13)
    summary["A2"] = (
        "Simulação: mostra o que a CICA baixaria no mês a partir da posição do mês anterior. "
        "Nada foi lançado no Domínio."
    )
    summary["A2"].alignment = Alignment(wrap_text=True)
    summary.merge_cells("A2:F2")
    summary.row_dimensions[2].height = 32
    headers = (
        "Tipo",
        "Parcelas",
        "Com baixa no mês",
        "Saldo na abertura",
        "Baixado",
        "Saldo final",
    )
    for column, title in enumerate(headers, start=1):
        cell = summary.cell(row=4, column=column, value=title)
        cell.font = Font(bold=True)
        cell.fill = HEADER_FILL
        summary.column_dimensions[get_column_letter(column)].width = 18
    for row, (title, count, settled, opening, closing) in enumerate(totals, start=5):
        values = (
            title,
            count,
            settled,
            _money(opening),
            _money(opening - closing),
            _money(closing),
        )
        for column, value in enumerate(values, start=1):
            cell = summary.cell(row=row, column=column, value=value)
            if column >= 4:
                cell.number_format = MONEY_FORMAT
    if not totals:
        summary["A5"] = "Sem posição de títulos enviada."
    buffer = io.BytesIO()
    book.save(buffer)
    return buffer.getvalue()
