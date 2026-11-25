"""Posição de títulos por NF em planilha (D-417, R-07). Dados fictícios."""

from __future__ import annotations

from datetime import date
from io import BytesIO

from openpyxl import load_workbook
from tests.test_multisource_matching import (
    D1,
    PAYABLES,
    RECEIVABLES,
    collection,
    item,
)

from apps.hub.multisource.matching import BankLine, simulate
from apps.hub.multisource.position_workbook import render_position_xlsx


def simulated():
    bank = [BankLine(1, D1, 140000 + 1120 + 445667, "LIQ.COBRANCA SIMPLES COB000003")]
    return simulate(
        bank,
        collection=collection(
            item("CLIENTE ALFA LTDA", 140000, interest=1120),
            item("CLIENTE BETA SA", 445667, our="26/000002-2"),
        ),
        receivables=RECEIVABLES,
        payables=PAYABLES,
    )


def test_workbook_lists_each_installment_with_numbers_dates_and_settlements():
    book = load_workbook(BytesIO(render_position_xlsx(simulated(), period=date(2026, 10, 1))))
    assert book.sheetnames == ["Resumo", "A receber", "A pagar"]
    sheet = book["A receber"]
    header = [c.value for c in sheet[1]]
    assert header[:4] == ["Código", "Cliente", "NF", "Parcela"]
    rows = {(r[2], r[3]): r for r in sheet.iter_rows(min_row=2, values_only=True) if r[2]}
    alfa = rows[("100", "1/1")]
    assert alfa[1] == "CLIENTE ALFA LTDA - 9"
    assert (alfa[7], alfa[8], alfa[9], alfa[10]) == (1400.0, 1400.0, 0.0, "Baixado")
    assert alfa[11] == "01/10/2026 extrato 1.400,00"
    assert rows[("200", "2/3")][10] == "Em aberto"  # R-05: a mais antiga (1/3) foi baixada
    assert rows[("200", "1/3")][10] == "Baixado"
    assert sheet.cell(row=2, column=6).number_format == "DD/MM/YYYY"
    assert isinstance(sheet.cell(row=2, column=6).value, date)
    total = next(r for r in sheet.iter_rows(min_row=2) if r[1].value == "Total")
    assert str(total[9].value).startswith("=SUM(J2:")
    assert book["A pagar"]["B1"].value == "Fornecedor"
    summary = book["Resumo"]
    assert summary["A1"].value == "Posição de títulos por NF — 10/2026"
    assert "Nada foi lançado" in summary["A2"].value
    assert [c.value for c in summary[5]][:3] == ["A receber", 4, 2]


def test_workbook_without_position_says_so():
    book = load_workbook(BytesIO(render_position_xlsx(simulate([]))))
    assert book.sheetnames == ["Resumo"]
    assert book["Resumo"]["A5"].value == "Sem posição de títulos enviada."
