"""Transferências entre contas da própria empresa na simulação multifontes (D-415).

Dados fictícios."""

from __future__ import annotations

from datetime import date

from apps.hub.multisource.client_cashbook import CashbookLine, CashbookSheet, extract_refs
from apps.hub.multisource.matching import AUTOMATIC, IDENTIFIED, STATUS_LABELS, BankLine, simulate
from apps.hub.multisource.report import render_summary

OWN = "11222333000181"
D7 = date(2026, 10, 7)
D16 = date(2026, 10, 16)
D29 = date(2026, 10, 29)


def cash(sheet, row, day, history, amount):
    return CashbookLine(
        sheet, row, day, history, max(amount, 0), max(-amount, 0), None, extract_refs(history)
    )


def tab(name, *lines):
    return CashbookSheet(name, 0, tuple(lines), ())


def run(bank, main_lines, *accounts, own_tax_id=OWN):
    return simulate(
        bank,
        cashbook=tab("BANCO", *main_lines),
        cash_accounts=list(accounts),
        own_tax_id=own_tax_id,
    )


def test_bank_to_cash_and_bank_to_other_bank_are_paired():
    bank = [
        BankLine(1, D7, -500000, f"DEBITO TED/IB {OWN} EMPRESA FICTICIA"),
        BankLine(2, D16, -3000000, "SAQUE DIN AG CHEQUE"),
        BankLine(3, D29, -3000000, "SAQUE DIN AG CHEQUE"),
    ]
    main = [
        cash("BANCO", 1, D7, "TRANS OUTRO BANCO", -500000),
        cash("BANCO", 2, D16, "DISTRIBUIÇÃO DE LUCROS", -3000000),
        cash("BANCO", 3, D29, "TRANSFERENCIA PARA CAIXA", -3000000),
    ]
    caixa = tab("CAIXA", cash("CAIXA", 9, D29, "RECEBIDO DE BANCO", 3000000))
    other = tab("OUTRO", cash("OUTRO", 4, D7, "RECEBIMENTO BANCO", 500000))
    result = run(bank, main, caixa, other)

    pairs = {(p.source_name, p.target_name, p.incoming.bank.amount_cents) for p in result.transfers}
    assert pairs == {("BANCO", "OUTRO", 500000), ("BANCO", "CAIXA", 3000000)}
    by_index = {(r.bank.account, r.bank.index): r for r in result.lines}
    for key in (("extrato", 1), ("extrato", 3), ("CAIXA", 9), ("OUTRO", 4)):
        assert by_index[key].status == AUTOMATIC and by_index[key].parts[0].kind == "transfer"
    # O saque de 16/10 é distribuição de lucros: o caixa só recebe 13 dias depois, sem par.
    assert by_index[("extrato", 2)].status == IDENTIFIED
    summary = render_summary(result, title="Teste")
    assert "## Transferências entre contas da empresa (D-415)" in summary
    assert "07/10/2026 BANCO → 07/10/2026 OUTRO: 5.000,00" in summary
    assert "Transferências entre contas da empresa — contas a definir (Q-57): 4" in summary
    assert STATUS_LABELS[AUTOMATIC] == "Automático (títulos, aplicação ou transferência)"


def test_same_value_without_transfer_evidence_is_not_paired():
    bank = [BankLine(1, D29, -3000000, "PAGAMENTO PIX 12345678900 FORNECEDOR")]
    main = [cash("BANCO", 1, D29, "PAGTO FORNECEDOR", -3000000)]
    caixa = tab("CAIXA", cash("CAIXA", 9, D29, "RECEB CLIENTE NF 123", 3000000))
    result = run(bank, main, caixa)
    assert result.transfers == []
    assert all(p.kind != "transfer" for r in result.lines for p in r.parts)


def test_two_possible_pairs_are_left_as_a_warning():
    bank = [BankLine(1, D29, -100000, "SAQUE DIN AG CHEQUE")]
    main = [cash("BANCO", 1, D29, "TRANSFERENCIA PARA CAIXA", -100000)]
    caixa = tab(
        "CAIXA",
        cash("CAIXA", 9, D29, "RECEBIDO DE BANCO", 100000),
        cash("CAIXA", 10, date(2026, 10, 30), "RECEBIDO DE BANCO", 100000),
    )
    result = run(bank, main, caixa)
    assert result.transfers == []
    assert any("mais de um par possível" in w for w in result.warnings)
    assert result.lines[0].status != AUTOMATIC


def test_without_cash_accounts_nothing_is_paired():
    bank = [
        BankLine(1, D7, -500000, f"DEBITO TED/IB {OWN} EMPRESA FICTICIA"),
        BankLine(2, D7, 500000, f"CREDITO TED {OWN} EMPRESA FICTICIA"),
    ]
    result = simulate(bank, own_tax_id=OWN)
    assert result.transfers == []
