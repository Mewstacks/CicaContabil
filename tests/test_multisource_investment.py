"""Aplicação financeira e natureza divergente na simulação multifontes (D-411). Dados sintéticos."""

from __future__ import annotations

from datetime import date

import pytest

from apps.hub.multisource.client_cashbook import CashbookLine, CashbookSheet, extract_refs
from apps.hub.multisource.common import MultisourceError
from apps.hub.multisource.investment import parse_investment_text
from apps.hub.multisource.matching import AUTOMATIC, FLAGGED, IDENTIFIED, BankLine, simulate
from apps.hub.multisource.report import render_summary

HEADER = (
    "Associado: EMPRESA FICTICIA LTDA\n"
    "Cooperativa: 0101 Conta Corrente: 11111 Impresso em 2026-11-10\n"
    "Extrato de Aplicação - Depósito a Prazo - Simplificado -\n"
    "Produto: APLICACAO AUTOMATICA\n"
    "Data Histórico Valor (R$)\n"
)
PAGE_1 = HEADER + (
    "30/09/2026 Saldo Anterior 1.000,00\n"
    "01/10/2026 Aplicacoes 500,00\n"
    "05/10/2026 Resgates 400,00\n"
    "05/10/2026 Rendimentos 10,00\n"
)
PAGE_2 = (
    "05/10/2026 Rendimentos 10,00\n"  # repetida na virada de página
    "05/10/2026 Encargos de IRRF 2,00\n"
    "31/10/2026 Saldo Atual 1.108,00\n"
)


def test_reads_statement_drops_page_repeat_and_checks_balance_chain():
    statement = parse_investment_text([PAGE_1, PAGE_2])
    assert (statement.opening_cents, statement.closing_cents) == (100000, 110800)
    assert [m.kind for m in statement.movements] == [
        "application",
        "redemption",
        "income",
        "income_tax",
    ]
    assert statement.total("income") == 1000 and statement.total("income_tax") == 200
    assert statement.product == "APLICACAO AUTOMATICA" and statement.account == "11111"


def test_refuses_broken_chain_unknown_history_and_other_files():
    with pytest.raises(MultisourceError, match="cadeia de saldos"):
        parse_investment_text([PAGE_1, PAGE_2.replace("1.108,00", "1.108,01")])
    with pytest.raises(MultisourceError, match="histórico desconhecido"):
        parse_investment_text([PAGE_1 + "06/10/2026 Bonus 1,00\n", PAGE_2])
    with pytest.raises(MultisourceError, match="não é o Extrato"):
        parse_investment_text(["Outro relatório"])


def cash(row, day, history, amount):
    return CashbookLine(
        "BANCO", row, day, history, max(amount, 0), max(-amount, 0), None, extract_refs(history)
    )


def test_redemption_split_in_two_bank_lines_becomes_transfer_and_report_lists_income():
    statement = parse_investment_text([PAGE_1, PAGE_2])
    bank = [
        BankLine(1, date(2026, 10, 1), -50000, "APLICACAO FINANCEIRA"),
        BankLine(2, date(2026, 10, 5), 15000, "RESG.APLIC.FIN.AVISO PREV"),
        BankLine(3, date(2026, 10, 5), 25000, "RESG.APLIC.FIN.AVISO PREV"),
        BankLine(4, date(2026, 10, 5), 40000, "RECEBIMENTO PIX 12345678000199 OUTRO"),
    ]
    result = simulate(bank, investment=statement)
    assert [r.status for r in result.lines[:3]] == [AUTOMATIC] * 3
    assert result.lines[1].parts[0].kind == "investment"
    assert result.lines[3].status == FLAGGED  # sem "APLIC" no histórico, não vira resgate
    assert result.investment_unmatched == []
    summary = render_summary(result, title="Teste")
    assert "Rendimentos a lançar na conta da aplicação: 10,00; IRRF retido: 2,00" in summary


def test_investment_movement_without_bank_pair_is_reported():
    statement = parse_investment_text([PAGE_1, PAGE_2])
    result = simulate(
        [BankLine(1, date(2026, 10, 1), -50000, "APLICACAO FINANCEIRA")], investment=statement
    )
    assert [m.kind for m in result.investment_unmatched] == ["redemption"]
    assert "05/10/2026 resgate 400,00" in render_summary(result, title="Teste")


def test_unusual_nature_for_same_tax_id_is_flagged_but_spelling_variants_are_not():
    day = date(2026, 10, 1)
    payee = "PAGAMENTO PIX 55555555000155 MARKETPLACE"
    bank = [BankLine(i, day, -1000 * i, payee) for i in range(1, 5)]
    sheet = CashbookSheet(
        "BANCO",
        0,
        (
            cash(1, day, "PAGTO MARKETPLACE", -1000),
            cash(2, day, "PAGTO MARKETPLACE", -2000),
            cash(3, day, "PAGTO  MARKETPLACES", -3000),  # mesma natureza, grafia diferente
            cash(4, day, "COMPRA DE MERCADORIA", -4000),
        ),
        (),
    )
    result = simulate(bank, cashbook=sheet)
    assert [r.status for r in result.lines] == [IDENTIFIED, IDENTIFIED, IDENTIFIED, FLAGGED]
    assert "natureza diferente do habitual" in result.lines[3].reasons[0]
