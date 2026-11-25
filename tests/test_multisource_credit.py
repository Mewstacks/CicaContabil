"""Empréstimo e fatura do cartão na simulação multifontes (D-418). Textos fictícios."""

from __future__ import annotations

from datetime import date

import pytest

from apps.hub.multisource.common import MultisourceError
from apps.hub.multisource.credit import parse_card_text, parse_loan_text
from apps.hub.multisource.matching import AUTOMATIC, IDENTIFIED, BankLine, simulate
from apps.hub.multisource.report import render_summary

LOAN = """Cooperativa: 9999 Conta Corrente: 00001-0
Consulta de Empréstimos
Parcelas do Título
Nro do Título: X000111
Data de Liberação: 16/07/2026
Parcela Vencimento Pagamento
001 LIQUIDADO 13/08/2026 13/08/2026 1.000,00
002 LIQUIDADO 13/09/2026 14/09/2026 1.010,00
003 LIQUIDADO 13/10/2026 13/10/2026 990,00
004 NORMAL 13/11/2026 900,00
005 NORMAL 13/12/2026 900,00
"""
CARD = [
    """Empresa Ficticia
Visa Empresas final 9999 Melhor dia de compra 10
Total fatura de outubro R$ 150,00
Vencimento 23/out
Total desta Fatura 150,00""",
    """Empresa Ficticia Vencimento 23/10/2026
Visa Empresas final 9999 Total fatura de outubro R$ 150,00
24/set 22:56 Cidade Loja Ficticia R$ 100,00
02/out 10:00 Cidade Servico Ficticio R$ 50,00
23/set 23:34 Pagamento 000000001 -R$ 80,00
Total cartão (final 9999) R$ 150,00""",
]


def test_loan_schedule_and_card_invoice_are_read():
    loan = parse_loan_text([LOAN])
    assert (loan.contract, loan.released_on, loan.count) == ("X000111", date(2026, 7, 16), 5)
    third = loan.installments[2]
    assert (third.status, third.paid_on, third.amount_cents) == (
        "LIQUIDADO",
        date(2026, 10, 13),
        99000,
    )
    assert loan.installments[3].paid_on is None
    assert loan.open_after(date(2026, 10, 31)) == 180000
    card = parse_card_text(CARD)
    assert (card.card, card.due_on, card.total_cents) == ("9999", date(2026, 10, 23), 15000)
    assert [(t.occurred_on, t.amount_cents) for t in card.transactions] == [
        (date(2026, 9, 24), 10000),
        (date(2026, 10, 2), 5000),
        (date(2026, 9, 23), -8000),
    ]
    assert card.warnings == ()
    with pytest.raises(MultisourceError, match="parcelas de empréstimo"):
        parse_loan_text(["Extrato qualquer"])
    with pytest.raises(MultisourceError, match="fatura de cartão"):
        parse_card_text(["Extrato qualquer"])


def test_payments_are_identified_never_automatic():
    bank = [
        BankLine(1, date(2026, 10, 13), -99000, "LIQUIDACAO DE PARCELA"),
        BankLine(2, date(2026, 10, 23), -15000, "DEB.CTA.FATURA"),
        BankLine(3, date(2026, 10, 30), -100, "TARIFA"),
    ]
    result = simulate(bank, loans=[parse_loan_text([LOAN])], cards=[parse_card_text(CARD)])
    loan_line, card_line, other = result.lines
    assert loan_line.status == IDENTIFIED and loan_line.status != AUTOMATIC
    assert loan_line.parts[0].kind == "loan"
    assert "parcela 003/005" in loan_line.parts[0].label and "Q-55" in loan_line.parts[0].label
    assert card_line.status == IDENTIFIED and card_line.parts[0].kind == "card"
    assert "final 9999" in card_line.parts[0].label and "2 despesa(s)" in card_line.parts[0].label
    assert other.parts == []
    summary = render_summary(result, title="Teste")
    assert "## Empréstimo e cartão (D-418)" in summary
    assert "parcelas a vencer depois de 30/10/2026: 1.800,00" in summary
    assert "02/10/2026 Cidade Servico Ficticio: 50,00" in summary
    assert "Parcelas de empréstimo — juros e principal a separar (Q-55): 1 · 990,00" in summary


def test_missing_or_ambiguous_debits_are_reported_not_guessed():
    day = date(2026, 10, 13)
    twice = [
        BankLine(1, day, -99000, "LIQUIDACAO DE PARCELA"),
        BankLine(2, day, -99000, "LIQUIDACAO DE PARCELA"),
    ]
    result = simulate(twice, loans=[parse_loan_text([LOAN])], cards=[parse_card_text(CARD)])
    assert all(line.parts == [] for line in result.lines)
    assert any("mais de um débito" in w for w in result.warnings)
    assert [item.number for _loan, item in result.loan_unmatched] == [3]
    assert result.cards_unmatched  # sem débito de 150,00 perto do vencimento
    summary = render_summary(result, title="Teste")
    assert "Parcela 003 de X000111 paga em 13/10/2026 (990,00) sem débito no extrato." in summary
    assert "150,00 (sem débito no extrato)" in summary
