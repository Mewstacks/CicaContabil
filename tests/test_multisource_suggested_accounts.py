"""Contas sugeridas e Seu Nº da francesinha (D-420). Plano e dados fictícios."""

from __future__ import annotations

import json
from datetime import date

import pytest
from tests.test_multisource_matching import D1, RECEIVABLES, cash, collection, item, sheet

from apps.hub.multisource.common import MultisourceError
from apps.hub.multisource.matching import AUTOMATIC, BankLine, simulate
from apps.hub.multisource.report import render_lines_csv
from apps.hub.multisource.suggested_accounts import (
    Chart,
    read_chart_jsonl,
    suggest_accounts,
    summary_lines,
)


def row(code, classification, name, kind="A", status="A", chart=900):
    return {
        "chart_company_code": chart,
        "account_code": code,
        "account_name_raw": name,
        "classification_raw": classification,
        "account_type_raw": kind,
        "account_status_raw": status,
        "inactive_on_raw": None,
    }


ROWS = [
    row(1, "1101001001", "CAIXA"),
    row(9, "1102001001001", "COBRANÇA"),
    row(10, "1102001", "CLIENTES", kind="S"),
    row(11, "1102001001", "CLIENTES", kind="S"),
    row(500, "11020010011", "CLIENTE ALFA LTDA - 9"),
    row(501, "11020010012", "CLIENTE BETA SA - 2"),
    row(502, "11020010013", "CLIENTE INATIVO", status="I"),
    row(4, "2101001001001", "PAGAMENTO DE FORNECEDORES"),
    row(20, "2101001001", "FORNECEDORES", kind="S"),
    row(132, "4201024001", "JUROS ATIVOS"),
    row(227, "4201023005", "DESPESAS BANCÁRIAS"),
    row(385, "1103002001", "EMPRÉSTIMO A SÓCIA FICTICIA"),
    row(386, "1103002002", "EMPRÉSTIMO AO SÓCIO FICTICIO"),
    row(99, "1101001001", "CAIXA", chart=901),
]


def chart():
    return Chart([r for r in ROWS if r["chart_company_code"] == 900])


def test_chart_reads_jsonl_by_chart_company_and_finds_names():
    content = "\n".join(json.dumps(r) for r in ROWS).encode()
    plan = read_chart_jsonl(content, 900)
    assert len(plan) == 9  # analíticas ativas da empresa 900 (sintéticas e inativa fora)
    assert [a.code for a in plan.named("COBRANCA")] == [9]
    assert [a.code for a in plan.named("EMPRESTIMO A SOCIA*")] == [385]
    assert [a.code for a in plan.party("receivable", "CLIENTE ALFA LTDA - 9")] == [500]
    assert plan.party("payable", "CLIENTE ALFA LTDA - 9") == ()  # fora do grupo Fornecedores
    with pytest.raises(MultisourceError, match="902 ausente"):
        read_chart_jsonl(content, 902)


def test_collection_parts_get_bank_and_settlement_accounts():
    bank = [BankLine(1, D1, 140000 + 1120 + 445667, "LIQ.COBRANCA SIMPLES COB000003")]
    result = simulate(
        bank,
        collection=collection(
            item("CLIENTE ALFA LTDA", 140000, interest=1120),
            item("CLIENTE BETA SA", 445667, our="26/000002-2"),
        ),
        receivables=RECEIVABLES,
    )
    suggestions = suggest_accounts(result, chart())
    texts = [suggestions.text(p) for p in result.lines[0].parts]
    assert texts[0] == "banco: 9 COBRANÇA; baixa: 500 CLIENTE ALFA LTDA - 9"
    assert texts[1] == "banco: 9 COBRANÇA; baixa: 132 JUROS ATIVOS (Q-53)"
    assert texts[2] == "banco: 9 COBRANÇA; baixa: 501 CLIENTE BETA SA - 2"
    assert (suggestions.covered, suggestions.parts, suggestions.missing_party) == (3, 3, 0)
    assert "contas_sugeridas_a_confirmar" in render_lines_csv(result, suggestions)
    summary = "\n".join(summary_lines(suggestions, chart_size=9))
    assert (
        "Partes com conta sugerida: 3 de 3." in summary and "| banco: 9 COBRANÇA | 3 |" in summary
    )


def test_cashbook_natures_follow_september_practice():
    bank = [
        BankLine(1, D1, -910, "TARIFA SERV.COBR.TITULOS"),
        BankLine(2, D1, -1000000, "PAGAMENTO PIX 12345678900 SOCIO"),
        BankLine(3, date(2026, 10, 2), -5000, "PAGAMENTO PIX 22222222000122 LOJA"),
    ]
    cashbook = sheet(
        cash(1, D1, "TARIFA COBRANÇA", -910),
        cash(2, D1, "DISTRIBUIÇÃO DE LUCROS", -1000000),
        cash(3, date(2026, 10, 2), "COMPRA DIVERSA", -5000),
    )
    result = simulate(bank, cashbook=cashbook)
    suggestions = suggest_accounts(result, chart())
    tariff, profit, other = (suggestions.text(line.parts[0]) for line in result.lines)
    assert tariff == "banco: 227 DESPESAS BANCÁRIAS"
    assert "386 EMPRÉSTIMO AO SÓCIO FICTICIO + 385 EMPRÉSTIMO A SÓCIA FICTICIA" in profit
    assert "meio a meio" in profit
    assert other == "banco: 4 PAGAMENTO DE FORNECEDORES"  # PIX pago com CPF/CNPJ, sem regra própria


def test_star_your_number_points_to_the_invoice_without_cashbook():
    """Q-52: `*1NNNNNNPP` traz a NF; sem caixa, ela escolhe o título entre os de mesmo valor."""
    collected = item("CLIENTE BETA SA", 445667)
    star = type(collected)(**{**collected.__dict__, "your_number": "*100020002"})
    assert star.invoice_from_your_number == "200"
    other = type(collected)(**{**collected.__dict__, "your_number": "XX00002255"})
    assert other.invoice_from_your_number == ""
    bank = [BankLine(1, D1, 445667, "LIQ.COBRANCA SIMPLES COB000003")]
    result = simulate(bank, collection=collection(star), receivables=RECEIVABLES)
    assert result.lines[0].status == AUTOMATIC
    assert "NF 200" in result.lines[0].parts[0].label
