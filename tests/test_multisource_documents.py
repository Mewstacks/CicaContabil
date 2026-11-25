"""Documentos escaneados na simulação multifontes (D-412). Documentos sintéticos."""

from __future__ import annotations

from datetime import date
from io import BytesIO

import pytest
from reportlab.pdfgen.canvas import Canvas

from apps.hub.multisource.client_cashbook import CashbookLine, CashbookSheet, extract_refs
from apps.hub.multisource.matching import AUTOMATIC, FLAGGED, IDENTIFIED, BankLine, simulate
from apps.hub.multisource.report import render_documents_csv, render_summary
from apps.hub.multisource.scanned_documents import (
    _mod10,
    _mod11_barcode,
    extract_document,
    parse_boleto_line,
    read_scanned_pdf,
)
from apps.hub.multisource.title_position import PAYABLE, PositionInstallment, TitlePosition
from apps.hub.reconciliation_service import local_ocr_available

OWN = "11222333000181"


def boleto_line(*, bank="999", factor=1614, cents=18300, free="1234567890123456789012345"):
    """Linha digitável sintética com dígitos verificadores corretos."""
    head = bank + "9"
    tail = f"{factor:04d}{cents:010d}"
    general = _mod11_barcode(head + tail + free)
    f1 = head + free[:5]
    f2 = free[5:15]
    f3 = free[15:25]
    f1, f2, f3 = f1 + str(_mod10(f1)), f2 + str(_mod10(f2)), f3 + str(_mod10(f3))
    return f"{f1[:5]}.{f1[5:]} {f2[:5]}.{f2[5:]} {f3[:5]}.{f3[5:]} {general} {tail}"


def test_boleto_line_gives_amount_and_due_date_and_rejects_misread_digit():
    line = boleto_line()
    parsed = parse_boleto_line(f"Recibo do Pagador\n{line}\n")
    assert parsed is not None
    assert (parsed.amount_cents, parsed.due_on, parsed.bank) == (18300, date(2026, 10, 29), "999")
    misread = line[:-1] + str((int(line[-1]) + 1) % 10)
    assert parse_boleto_line(misread) is None
    odd_factor = parse_boleto_line(boleto_line(factor=9785))
    assert odd_factor is not None and odd_factor.due_on is None  # vencimento virá do texto


def test_extracts_boleto_fields_ignoring_own_tax_id():
    text = (
        "Banco Ficticio 999-9 Recibo do Pagador\n"
        "Beneficiário FORNECEDOR ALFA LTDA\n"
        "CNPJ 22.222.222/0001-22 Nº do Documento 0051845/01\n"
        "Pagador EMPRESA FICTICIA LTDA CNPJ: 11.222.333/0001-81\n"
        f"{boleto_line(cents=18300)}\n"
    )
    document = extract_document(text, source="scan.pdf", page=1, confidence=80, own_tax_id=OWN)
    assert document.kind == "boleto" and document.amount_cents == 18300
    assert document.tax_ids == ("22222222000122",)
    assert document.number == "0051845/01"
    assert document.issuer.startswith("FORNECEDOR ALFA")
    assert not document.uncertain  # a linha digitável validada dispensa a confiança do OCR


def test_receipt_without_boleto_uses_text_and_low_confidence_is_uncertain():
    text = "Recibo de aluguel\nAluguel 650,00\nSoma 650,00\nLíquido 650,00\nRecebi(emos) de EMPRESA"
    document = extract_document(text, source="scan.pdf", page=2, confidence=95)
    assert (document.kind, document.amount_cents, document.uncertain) == ("recibo", 65000, False)
    shaky = extract_document("Recibo\nLíquido 650,00", source="scan.pdf", page=2, confidence=60)
    assert shaky.uncertain
    # O mesmo valor repetido na página confirma a leitura mesmo com OCR fraco.
    assert not extract_document(text, source="scan.pdf", page=2, confidence=60).uncertain


def cash(row, day, history, amount):
    return CashbookLine(
        "CAIXA", row, day, history, max(amount, 0), max(-amount, 0), None, extract_refs(history)
    )


def payable(document, cents):
    return PositionInstallment(
        kind=PAYABLE,
        party_code="10",
        party_name="FORNECEDOR ALFA LTDA",
        document=document,
        ordinal=1,
        count=1,
        issued_on=None,
        moved_on=None,
        due_on=date(2026, 10, 29),
        amount_cents=cents,
        paid_cents=0,
        interest_cents=0,
        penalty_cents=0,
        other_cents=0,
        discount_cents=0,
        returned_cents=0,
        balance_cents=cents,
        status="Aberta",
        row=1,
    )


def test_documents_link_payments_settle_titles_and_list_unpaid_ones():
    day = date(2026, 10, 29)
    boleto = extract_document(
        f"Recibo do Pagador\nNº do Documento 0051845/01\n{boleto_line(cents=18300)}",
        source="scan-a.pdf",
        page=1,
        confidence=80,
    )
    rent = extract_document(
        "Recibo de aluguel\nLíquido 650,00", source="scan-b.pdf", page=1, confidence=96
    )
    unpaid = extract_document("Recibo\nLíquido 99,00", source="scan-b.pdf", page=2, confidence=96)
    shaky = extract_document("Recibo\nLíquido 77,00", source="scan-b.pdf", page=3, confidence=40)
    bank = [BankLine(1, day, -18300, "LIQUIDACAO BOLETO 22222222000122 PAGADORIA XPTO")]
    caixa = CashbookSheet("CAIXA", 0, (cash(5, date(2026, 10, 5), "PAGTO ALUGUEL", -65000),), ())
    payables = TitlePosition(
        PAYABLE, "X", OWN, None, (payable("51845", 18300),), 18300, 0, 18300, ()
    )
    result = simulate(
        bank,
        payables=payables,
        cash_accounts=[caixa],
        documents=[boleto, rent, unpaid, shaky],
    )
    # R-10: sem caixa para o banco, o número do boleto baixou o título.
    assert result.lines[0].status == AUTOMATIC and "NF 51845" in result.lines[0].parts[0].label
    matched = {
        m.document.page: (m.line.bank.account if m.line else None, m.settled)
        for m in result.documents
        if m.document.source == "scan-b.pdf"
    }
    assert matched == {1: ("CAIXA", False), 2: (None, False), 3: (None, False)}
    summary = render_summary(result, title="Teste")
    assert "Títulos baixados pelo documento, sem linha no caixa (R-10): 1" in summary
    assert "RECIBO (scan-b.pdf p. 2): 99,00" in summary
    assert "Leitura incerta (confiança do OCR abaixo de 90, sem linha digitável): 1" in summary
    assert "scan-a.pdf;1;boleto;183,00;29/10/2026" in render_documents_csv(result)


def test_unmatched_bank_payment_stays_flagged_when_document_does_not_close():
    day = date(2026, 10, 29)
    boleto = extract_document(boleto_line(cents=18300), source="s.pdf", page=1, confidence=80)
    bank = [BankLine(1, day, -18300, "LIQUIDACAO BOLETO 22222222000122 OUTRO")]
    result = simulate(bank, documents=[boleto])
    # Sem título na posição, o documento identifica o pagamento (R-10), sem baixa.
    assert result.lines[0].status == IDENTIFIED and result.documents[0].line is result.lines[0]
    assert result.lines[0].parts[0].label.endswith("(documento escaneado)")
    payables = TitlePosition(PAYABLE, "X", OWN, None, (payable("999", 18299),), 18299, 0, 18299, ())
    same_supplier = [BankLine(1, day, -18300, "LIQUIDACAO BOLETO 22222222000122 FORNECEDOR ALFA")]
    wrong_value = simulate(same_supplier, payables=payables, documents=[boleto])
    assert wrong_value.lines[0].status == FLAGGED  # há título do fornecedor, mas o valor não fecha


@pytest.mark.skipif(not local_ocr_available(), reason="Tesseract com português não instalado")
def test_ocr_reads_a_rendered_receipt_page():
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(595, 842))
    canvas.setFont("Helvetica", 18)
    for y, text in ((760, "RECIBO DE ALUGUEL"), (720, "Aluguel 650,00"), (690, "Liquido 650,00")):
        canvas.drawString(60, y, text)
    canvas.showPage()
    canvas.save()
    documents = read_scanned_pdf(stream.getvalue(), source="sintetico.pdf")
    assert [(d.kind, d.amount_cents) for d in documents] == [("recibo", 65000)]


def test_low_confidence_boleto_line_needs_the_amount_in_the_text():
    line = boleto_line(cents=69930000)
    weak = extract_document(f"Recibo do Pagador\n{line}", source="s.pdf", page=1, confidence=54)
    assert weak.boleto is None and weak.amount_cents is None
    confirmed = extract_document(
        f"Recibo do Pagador\nValor do Documento 699.300,00\n{line}",
        source="s.pdf",
        page=1,
        confidence=54,
    )
    assert confirmed.boleto is not None and confirmed.amount_cents == 69930000


def test_transport_document_with_payer_receipt_is_not_a_payment_receipt():
    text = "DACTE\nCT-e 1425491\nRECIBO DO SACADO\nValor Total 2.106,72"
    document = extract_document(text, source="s.pdf", page=1, confidence=90)
    assert document.kind == "cte" and not document.is_payment


def test_card_invoice_takes_the_invoice_total_not_the_credit_limit():
    text = (
        "Limite total de crédito R$ 10.000,00\nVencimento 23/10/2026\n"
        "Total fatura de outubro R$ 210,42"
    )
    document = extract_document(text, source="s.pdf", page=1, confidence=92)
    assert (document.kind, document.amount_cents, document.due_on) == (
        "fatura",
        21042,
        date(2026, 10, 23),
    )


def test_profit_distribution_receipt_uses_total_not_partner_percentages():
    text = (
        "DEMONSTRATIVO E RECIBO DE DISTRIBUIÇÃO DE LUCROS\n"
        "Sócio A 50,00% R$ 5.000,00\nSócio B 50,00% R$ 5.000,00\nTOTAL 100% R$ 10.000,00"
    )
    document = extract_document(text, source="s.pdf", page=1, confidence=95)
    assert (document.kind, document.amount_cents) == ("recibo", 1000000)


def test_weak_ocr_amount_one_digit_off_links_with_a_note():
    receipt = extract_document("Recibo\nLíquido 1.388,08", source="s.pdf", page=1, confidence=80)
    receipt = type(receipt)(**{**receipt.__dict__, "corroborated": True})
    caixa = CashbookSheet("CAIXA", 0, (cash(1, date(2026, 10, 20), "PAGTO AGUA/LUZ", -138818),), ())
    result = simulate([], cash_accounts=[caixa], documents=[receipt])
    match = result.documents[0]
    assert match.line is not None and "um dígito" in match.note and not match.settled
