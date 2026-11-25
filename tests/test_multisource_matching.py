"""Motor de casamento multifontes em simulação (D-409). Dados sintéticos."""

from __future__ import annotations

from datetime import date
from io import BytesIO, StringIO
from pathlib import Path

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from openpyxl import Workbook
from reportlab.pdfgen.canvas import Canvas

from apps.hub.multisource.client_cashbook import CashbookLine, CashbookSheet, extract_refs
from apps.hub.multisource.francesinha import CollectionItem, CollectionReport
from apps.hub.multisource.matching import (
    AUTOMATIC,
    FLAGGED,
    IDENTIFIED,
    BankLine,
    simulate,
    subset_with_sum,
)
from apps.hub.multisource.report import render_lines_csv, render_position_csv, render_summary
from apps.hub.multisource.title_position import (
    PAYABLE,
    RECEIVABLE,
    PositionInstallment,
    TitlePosition,
)

D1, D2 = date(2026, 10, 1), date(2026, 10, 2)


def inst(kind, code, name, document, due, balance, ordinal=1, count=1, amount=None):
    return PositionInstallment(
        kind=kind,
        party_code=code,
        party_name=name,
        document=document,
        ordinal=ordinal,
        count=count,
        issued_on=None,
        moved_on=None,
        due_on=due,
        amount_cents=amount or balance,
        paid_cents=0,
        interest_cents=0,
        penalty_cents=0,
        other_cents=0,
        discount_cents=0,
        returned_cents=0,
        balance_cents=balance,
        status="Aberta",
        row=0,
    )


def position(kind, *items):
    total = sum(i.balance_cents for i in items)
    return TitlePosition(
        kind, "EMPRESA FICTICIA", "11222333000181", None, tuple(items), total, 0, total, ()
    )


def item(payer, nominal, *, interest=0, credited=D1, our="26/000001-1"):
    return CollectionItem(
        your_number="X",
        our_number=our,
        payer=payer,
        moved_on=credited,
        credited_on=credited,
        nominal_cents=nominal,
        abatement_cents=0,
        discount_cents=0,
        interest_cents=interest,
        penalty_cents=0,
        amount_cents=nominal + interest,
        kind="Crédito",
        description="",
        page=1,
        line=1,
    )


def collection(*items):
    return CollectionReport(
        D1,
        date(2026, 10, 31),
        "1",
        "Crédito",
        tuple(items),
        len(items),
        sum(i.amount_cents for i in items),
        sum(i.interest_cents for i in items),
        0,
        0,
        0,
    )


def cash(row, day, history, amount):
    return CashbookLine(
        "BANCO", row, day, history, max(amount, 0), max(-amount, 0), None, extract_refs(history)
    )


def sheet(*lines):
    return CashbookSheet("BANCO", 0, tuple(lines), ())


RECEIVABLES = position(
    RECEIVABLE,
    inst(RECEIVABLE, "1", "CLIENTE ALFA LTDA - 9", "100", date(2026, 9, 14), 140000),
    inst(RECEIVABLE, "2", "CLIENTE BETA SA", "200", date(2026, 9, 16), 445667, 1, 3),
    inst(RECEIVABLE, "2", "CLIENTE BETA SA", "200", date(2026, 10, 1), 445667, 2, 3),
    inst(RECEIVABLE, "2", "CLIENTE BETA SA", "200", date(2026, 10, 16), 445666, 3, 3),
)
PAYABLES = position(
    PAYABLE,
    inst(PAYABLE, "10", "TRANSPORTES DELTA LTDA", "70001", date(2026, 10, 1), 9325),
    inst(PAYABLE, "10", "TRANSPORTES DELTA LTDA", "70002", date(2026, 10, 1), 4000),
    inst(PAYABLE, "11", "SOFTWARE EPSILON TECNOLOGIA LTDA", "5956", date(2026, 10, 1), 60000),
    inst(PAYABLE, "12", "FRETE ZETA LTDA", "1", date(2026, 10, 1), 10000),
    inst(PAYABLE, "12", "FRETE ZETA LTDA", "2", date(2026, 10, 2), 10000),
)


def test_collection_is_split_by_credit_date_with_interest_and_oldest_installment():
    bank = [BankLine(1, D1, 140000 + 1120 + 445667, "LIQ.COBRANCA SIMPLES COB000003")]
    result = simulate(
        bank,
        collection=collection(
            item("CLIENTE ALFA LTDA", 140000, interest=1120),
            item("CLIENTE BETA SA", 445667, our="26/000002-2"),
        ),
        receivables=RECEIVABLES,
    )
    line = result.lines[0]
    assert line.status == AUTOMATIC
    assert [(p.kind, p.amount_cents) for p in line.parts] == [
        ("receivable", 140000),
        ("interest", 1120),
        ("receivable", 445667),
    ]
    # R-05: duas parcelas de 4.456,67 — baixa a de vencimento mais antigo.
    assert "parcela 1/3" in line.parts[2].label and "mais antigo entre 2" in line.parts[2].label
    assert result.closing[("receivable", "2", "200", 1)] == 0
    assert result.closing[("receivable", "2", "200", 2)] == 445667


def test_collection_that_does_not_close_is_flagged_without_settling():
    bank = [BankLine(1, D1, 999999, "LIQ.COBRANCA SIMPLES COB000003")]
    result = simulate(
        bank, collection=collection(item("CLIENTE ALFA LTDA", 140000)), receivables=RECEIVABLES
    )
    assert result.lines[0].status == FLAGGED
    assert "não fecha" in result.lines[0].reasons[0]
    assert result.unmatched_collection and not result.lines[0].parts


def test_value_mismatch_is_flagged_zero_tolerance():
    bank = [BankLine(1, D1, 139999, "LIQ.COBRANCA SIMPLES COB000003")]
    result = simulate(
        bank, collection=collection(item("CLIENTE ALFA LTDA", 139999)), receivables=RECEIVABLES
    )
    assert result.lines[0].status == FLAGGED
    assert "não confere" in result.lines[0].reasons[0]
    assert result.closing[("receivable", "1", "100", 1)] == 140000


def test_payment_settles_one_title_per_document_cited_in_cashbook():
    bank = [BankLine(1, D1, -13325, "LIQUIDACAO BOLETO 11111111000111 TRANSP DELTA")]
    cashbook = sheet(cash(5, D1, "PAGTO DELTA (CTE 70001, 70002)", -13325))
    result = simulate(bank, payables=PAYABLES, cashbook=cashbook)
    line = result.lines[0]
    assert line.status == AUTOMATIC and line.cashbook_rows == [5]
    assert [(p.amount_cents, p.label.split(" ·")[0]) for p in line.parts] == [
        (9325, "NF 70001"),
        (4000, "NF 70002"),
    ]


def test_payment_without_document_uses_exact_open_title_and_flags_duplicates():
    bank = [
        BankLine(1, D1, -60000, "LIQUIDACAO BOLETO 22222222000122 SOFTWARE EPSILON TEC"),
        BankLine(2, D1, -10000, "LIQUIDACAO BOLETO 33333333000133 FRETE ZETA"),
    ]
    result = simulate(bank, payables=PAYABLES)  # sem caixa: nome após o CNPJ
    assert result.lines[0].status == AUTOMATIC
    assert result.lines[1].status == FLAGGED and "mesmo valor" in result.lines[1].reasons[0]


def test_payroll_debit_is_split_into_cashbook_lines():
    bank = [BankLine(1, D1, -30000, "DEB. FOLHA PAGTO")]
    cashbook = sheet(
        cash(1, D1, "SALARIO PESSOA A", -10000), cash(2, D1, "SALARIO PESSOA B", -20000)
    )
    result = simulate(bank, cashbook=cashbook)
    assert result.lines[0].status == IDENTIFIED
    assert [p.label for p in result.lines[0].parts] == ["SALARIO PESSOA A", "SALARIO PESSOA B"]


def test_several_bank_lines_can_add_up_to_one_cashbook_line():
    bank = [
        BankLine(1, D1, 60226, "RESG.APLIC.FIN.AVISO PREV"),
        BankLine(2, D1, 375109, "RESG.APLIC.FIN.AVISO PREV"),
    ]
    result = simulate(bank, cashbook=sheet(cash(9, D1, "RESG APLIC FINANCEIRA", 435335)))
    assert [r.status for r in result.lines] == [IDENTIFIED, IDENTIFIED]
    assert result.lines[0].parts[0].label == "RESG APLIC FINANCEIRA (parte)"
    assert result.unmatched_cashbook == []


def test_document_outside_opening_position_is_identified_not_settled():
    bank = [BankLine(1, D1, -225400, "PAGAMENTO PIX 44444444000144 FORNECEDOR NOVO")]
    result = simulate(
        bank, payables=PAYABLES, cashbook=sheet(cash(3, D1, "PAGTO FORNECEDOR NF 70862", -225400))
    )
    line = result.lines[0]
    assert line.status == IDENTIFIED and line.parts[0].kind == "document"
    assert "fora da posição de abertura" in line.parts[0].label


def test_receipt_citing_many_notes_with_partial_match_is_flagged():
    receivables = position(RECEIVABLE, inst(RECEIVABLE, "3", "CONSUMIDOR A", "543", D1, 3000))
    bank = [BankLine(1, D1, 5000, "RECEBIMENTO PIX 55555555000155 MARKETPLACE")]
    result = simulate(
        bank,
        receivables=receivables,
        cashbook=sheet(cash(4, D1, "RECEB MARKETPLACE NF 543,573", 5000)),
    )
    assert result.lines[0].status == FLAGGED
    assert "1 de 2 documentos citados" in result.lines[0].reasons[0]


def test_nature_line_and_unmatched_cashbook_and_bank_lines():
    bank = [
        BankLine(1, D1, -1000000, "PAGAMENTO PIX 12345678900 SOCIO"),
        BankLine(2, D2, -500, "TARIFA X"),
    ]
    cashbook = sheet(
        cash(1, D1, "DISTRIBUIÇÃO DE LUCROS", -1000000),
        cash(2, D2, "ALUGUEL PAGO EM DINHEIRO", -65000),
    )
    result = simulate(bank, cashbook=cashbook)
    assert result.lines[0].status == IDENTIFIED and result.lines[0].parts[0].kind == "nature"
    assert result.lines[1].status == FLAGGED and "sem linha" in result.lines[1].reasons[0]
    assert [c.row for c in result.unmatched_cashbook] == [2]


def test_reference_position_comparison_outcomes():
    bank = [BankLine(1, D1, 140000, "LIQ.COBRANCA SIMPLES COB000003")]
    reference = position(
        RECEIVABLE,
        inst(
            RECEIVABLE, "1", "CLIENTE ALFA LTDA - 9", "100", date(2026, 9, 14), 140000
        ),  # ainda aberto
        inst(RECEIVABLE, "2", "CLIENTE BETA SA", "200", date(2026, 10, 1), 445667, 1, 2),
        inst(RECEIVABLE, "2", "CLIENTE BETA SA", "200", date(2026, 10, 16), 445666, 2, 2),
        inst(RECEIVABLE, "9", "CLIENTE NOVO", "300", date(2026, 11, 1), 1000),
    )
    result = simulate(
        bank,
        collection=collection(item("CLIENTE ALFA LTDA", 140000)),
        receivables=RECEIVABLES,
        reference_receivables=reference,
    )
    outcomes = sorted(d.outcome for d in result.differences)
    assert outcomes == [
        "aberto na simulação, baixado na referência",
        "baixado na simulação, aberto na referência",
        "título novo na referência (fora da abertura)",
    ]


def test_subset_with_sum_detects_ambiguity():
    assert subset_with_sum([100, 200, 300], 300)[1] is True
    assert subset_with_sum([100, 100, 50], 200) == ([0, 1], False)
    assert subset_with_sum([100, 200], 50) == (None, False)


def test_reports_render_without_touching_database():
    bank = [BankLine(1, D1, 141120, "LIQ.COBRANCA SIMPLES COB000003")]
    result = simulate(
        bank,
        collection=collection(item("CLIENTE ALFA LTDA", 140000, interest=1120)),
        receivables=RECEIVABLES,
    )
    summary = render_summary(result, title="Teste")
    assert (
        "Simulação (D-409)" in summary
        and "| Automático (títulos ou aplicação) | 1 | 1.411,20 |" in summary
    )
    assert "01/10/2026;1.411,20" in render_lines_csv(result)
    assert (
        "NF 100 · parcela 1/1 · CLIENTE ALFA LTDA - 9;14/09/2026;1.400,00;1.400,00;0,00"
        in render_position_csv(result)
    )


def _statement_pdf() -> bytes:
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(612, 792))
    canvas.setFont("Helvetica", 9)
    for y, text in (
        (760, "Cooperativa: 9999"),
        (745, "Conta: 00001-0"),
        (725, "Extrato (Período de 01/10/2026 a 31/10/2026)"),
    ):
        canvas.drawString(40, y, text)
    for x, text in (
        (40, "Data"),
        (120, "Descrição"),
        (350, "Documento"),
        (450, "Valor (R$)"),
        (520, "Saldo (R$)"),
    ):
        canvas.drawString(x, 700, text)
    canvas.drawString(120, 680, "SALDO ANTERIOR")
    canvas.drawRightString(590, 680, "0,00")
    canvas.drawString(40, 660, "01/10/2026")
    canvas.drawString(120, 660, "DEB. FOLHA PAGTO")
    canvas.drawRightString(500, 660, "-300,00")
    canvas.drawRightString(590, 660, "-300,00")
    canvas.showPage()
    canvas.save()
    return stream.getvalue()


def test_command_writes_private_reports(tmp_path: Path):
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
    out = tmp_path / "saida"
    stdout = StringIO()
    call_command(
        "simular_multifontes",
        "--extrato",
        str(statement),
        "--caixa",
        str(workbook),
        "--saida",
        str(out),
        stdout=stdout,
    )
    assert "1 movimentos" in stdout.getvalue()
    assert sorted(p.name for p in out.iterdir()) == [
        "diferencas-posicao.csv",
        "movimentos.csv",
        "posicao.csv",
        "resumo.md",
    ]
    assert oct((out / "resumo.md").stat().st_mode)[-3:] == "600"
    assert "Identificado pelo caixa" in (out / "movimentos.csv").read_text(encoding="utf-8")
    with pytest.raises(CommandError, match="não encontrado"):
        call_command(
            "simular_multifontes", "--extrato", str(tmp_path / "nao.pdf"), "--saida", str(out)
        )


def test_document_typo_suggests_same_party_title_without_settling():
    bank = [BankLine(1, D1, -60000, "LIQUIDACAO BOLETO 22222222000122 SOFTWARE EPSILON TEC")]
    cashbook = sheet(cash(1, D1, "PAGTO EPSILON NF 956", -60000))
    result = simulate(bank, payables=PAYABLES, cashbook=cashbook)
    line = result.lines[0]
    assert line.status == FLAGGED and "NF 5956" in line.reasons[0]
    assert result.closing[("payable", "11", "5956", 1)] == 60000


def test_partial_payment_of_open_title_is_flagged_not_nature():
    bank = [BankLine(1, D1, -20000, "LIQUIDACAO BOLETO 22222222000122 SOFTWARE EPSILON TEC")]
    result = simulate(bank, payables=PAYABLES, cashbook=sheet(cash(1, D1, "PAGTO EPSILON", -20000)))
    assert result.lines[0].status == FLAGGED
    assert "não confere" in result.lines[0].reasons[0]


def test_cash_account_without_statement_settles_with_shared_titles():
    bank = [BankLine(1, D1, 445667, "LIQ.COBRANCA SIMPLES COB000003")]
    cash_sheet = CashbookSheet(
        "CAIXA",
        0,
        (cash(7, D2, "RECEB BETA NF 200", 445667), cash(8, D2, "PAGTO ALUGUEL", -65000)),
        (),
    )
    result = simulate(
        bank,
        collection=collection(item("CLIENTE BETA SA", 445667)),
        receivables=RECEIVABLES,
        cash_accounts=[cash_sheet],
    )
    accounts = [(r.bank.account, r.status) for r in result.lines]
    assert accounts == [("extrato", AUTOMATIC), ("CAIXA", AUTOMATIC), ("CAIXA", IDENTIFIED)]
    # O extrato baixou a parcela 1; o caixa em dinheiro, a parcela 2 (mesma carteira).
    assert result.closing[("receivable", "2", "200", 1)] == 0
    assert result.closing[("receivable", "2", "200", 2)] == 0
