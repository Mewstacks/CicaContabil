"""Comparação da simulação multifontes com o Razão lançado (D-410). Dados sintéticos."""

from __future__ import annotations

from datetime import date
from io import StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from openpyxl import Workbook
from tests.test_ledger_evidence import ledger_pdf

from apps.hub.ledger_evidence import read_dominio_ledger_pdf
from apps.hub.multisource.client_cashbook import CashbookLine, CashbookSheet, extract_refs
from apps.hub.multisource.common import MultisourceError
from apps.hub.multisource.ledger_comparison import (
    MISSING,
    OTHER_SPLIT,
    SAME_SPLIT,
    LedgerMovement,
    compare_with_ledger,
    movements_from_ledger_csv,
    movements_from_pdf,
)
from apps.hub.multisource.matching import BankLine, simulate
from apps.hub.multisource.report import render_ledger_csv, render_ledger_summary

D1, D2 = date(2026, 10, 1), date(2026, 10, 2)


def cash(row, day, history, amount):
    return CashbookLine(
        "BANCO", row, day, history, max(amount, 0), max(-amount, 0), None, extract_refs(history)
    )


def moved(day, cents, *accounts, ref="Razão 1"):
    return LedgerMovement(day, cents, tuple(accounts), "", ref)


def scenario():
    bank = [
        BankLine(1, D1, -30000, "DEB. FOLHA PAGTO"),
        BankLine(2, D1, -500, "TARIFA COBRANCA"),
        BankLine(3, D2, -10000, "PAGAMENTO PIX 12345678900 SOCIO"),
        BankLine(4, D2, -777, "TARIFA SEM LANCAMENTO"),
    ]
    sheet = CashbookSheet(
        "BANCO",
        0,
        (
            cash(1, D1, "SALARIO PESSOA A", -10000),
            cash(2, D1, "SALARIO PESSOA B", -20000),
            cash(3, D1, "TARIFA COBRANÇA", -500),
            cash(4, D2, "DISTRIBUIÇÃO DE LUCROS", -10000),
        ),
        (),
    )
    return simulate(bank, cashbook=sheet)


def test_compares_split_value_shift_and_missing():
    ledger = [
        moved(D1, -10000, "401", ref="Razão 10"),
        moved(D1, -20000, "401", ref="Razão 11"),  # folha lançada por pessoa = mesmo desdobramento
        moved(D1, -500, "520", ref="Razão 12"),
        moved(date(2026, 10, 5), -6000, "301", ref="Razão 13"),  # lucros em 2 lançamentos, 3 dias
        moved(date(2026, 10, 5), -4000, "301", ref="Razão 14"),
        moved(D2, -999, "999", ref="Razão 15"),  # só no Razão
    ]
    comparison = compare_with_ledger(scenario(), ledger)
    outcomes = [c.outcome for c in comparison.lines]
    assert outcomes == [SAME_SPLIT, SAME_SPLIT, OTHER_SPLIT, MISSING]
    assert comparison.lines[2].shifted_days == 3
    assert [m.reference for m in comparison.only_ledger] == ["Razão 15"]
    groups = comparison.accounts
    assert groups["natureza: SALARIO PESSOA A"]["401"] == 1
    assert groups["natureza: TARIFA COBRANÇA"]["520"] == 1


def test_single_ledger_entry_for_split_movement_counts_as_other_split():
    comparison = compare_with_ledger(scenario(), [moved(D1, -30000, "401")])
    assert comparison.lines[0].outcome == OTHER_SPLIT


def test_reports_render_sections_and_csv():
    comparison = compare_with_ledger(scenario(), [moved(D1, -500, "520")])
    summary = render_ledger_summary(comparison)
    assert "| mesmo desdobramento | 1 |" in summary and "| não encontrado no Razão | 3 |" in summary
    assert "| natureza: TARIFA COBRANÇA | 520 (1) |" in summary
    assert (
        "01/10/2026;-5,00;TARIFA COBRANCA;mesmo desdobramento;0;Razão 1 01/10 -5,00 contra 520"
        in (render_ledger_csv(comparison))
    )


LEDGER_CSV_HEADER = (
    "entry_key;line_key;date;history;account_code;side;amount_cents;cash_direction;document\n"
)


def test_ledger_csv_movements_use_the_bank_line_sign_and_counterparts():
    content = (
        LEDGER_CSV_HEADER
        + "L1;1;2026-10-01;Folha;8;credit;30000;outflow;\n"
        + "L1;2;2026-10-01;Folha;401;debit;30000;;\n"
        + "L2;1;2026-10-02;Recebimento;8;debit;1500;inflow;\n"
        + "L2;2;2026-10-02;Recebimento;120;credit;1400;;\n"
        + "L2;3;2026-10-02;Recebimento;610;credit;100;;\n"
    ).encode()
    movements = sorted(movements_from_ledger_csv(content), key=lambda m: m.reference)
    assert [(m.amount_cents, m.counterparts) for m in movements] == [
        (-30000, ("401",)),
        (1500, ("120", "610")),
    ]
    with pytest.raises(MultisourceError, match="nove colunas"):
        movements_from_ledger_csv(b"a;b\n1;2\n")


def test_ledger_pdf_movements_keep_bank_side_and_counterpart():
    evidence = read_dominio_ledger_pdf(
        ledger_pdf(pages=[[{"debit": 10000, "counterpart": "120"}, {"credit": 2000}]])
    )
    assert [(m.amount_cents, m.counterparts) for m in movements_from_pdf(evidence)] == [
        (10000, ("120",)),
        (-2000, ("9",)),
    ]


def test_command_writes_ledger_comparison(tmp_path: Path):
    from tests.test_multisource_matching import _statement_pdf

    statement = tmp_path / "extrato.pdf"
    statement.write_bytes(_statement_pdf())
    book = Workbook()
    ws = book.active
    ws.title = "SICREDI"
    ws.append(["DATA", "HISTÓRICO", "ENTRADA", "SAÍDA", "SALDO"])
    ws.append([D1, "SALARIO PESSOA A", None, 100])
    ws.append([D1, "SALARIO PESSOA B", None, 200])
    workbook = tmp_path / "caixa.xlsx"
    book.save(workbook)
    ledger = tmp_path / "razao.csv"
    ledger.write_bytes(
        (
            LEDGER_CSV_HEADER
            + "L1;1;2026-10-01;Folha;8;credit;30000;outflow;\n"
            + "L1;2;2026-10-01;Folha;401;debit;30000;;\n"
        ).encode()
    )
    out = tmp_path / "saida"
    call_command(
        "simular_multifontes",
        "--extrato",
        str(statement),
        "--caixa",
        str(workbook),
        "--razao-csv",
        str(ledger),
        "--saida",
        str(out),
        stdout=StringIO(),
    )
    assert (out / "comparacao-razao.csv").exists()
    summary = (out / "resumo.md").read_text(encoding="utf-8")
    assert "Comparação com o Razão lançado" in summary
    assert "| mesmo valor, desdobramento diferente | 1 |" in summary
