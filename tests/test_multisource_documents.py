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
    _mod11_collection,
    amount_in_words,
    extract_document,
    parse_boleto_line,
    parse_collection_line,
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


# D-414 — guias, linha tolerante, valor por extenso e soma conferida.


def collection_line(
    *, value_id="6", cents=18692, segment="4", free="01231234567890123456789012345"
):
    """Linha de guia/conta de consumo sintética (48 dígitos) com dígitos corretos."""
    check = _mod10 if value_id in "67" else _mod11_collection
    body = f"8{segment}{value_id}" + f"{cents:011d}" + free[:29]
    general = check(body)
    barcode = body[:3] + str(general) + body[3:]
    blocks = [barcode[i : i + 11] for i in range(0, 44, 11)]
    return " ".join(f"{block}-{check(block)}" for block in blocks)


@pytest.mark.parametrize("value_id", ["6", "8"])
def test_collection_line_gives_amount_and_rejects_misread_digit(value_id):
    line = collection_line(value_id=value_id)
    parsed = parse_collection_line(f"Conta de consumo\n{line}\n")
    assert parsed is not None and (parsed.kind, parsed.amount_cents) == ("guia", 18692)
    digits = list(line)
    digits[20] = str((int(digits[20]) + 1) % 10)
    assert parse_collection_line("".join(digits)) is None
    # Quantidade de referência (7 e 9) não é valor em reais.
    reference = parse_collection_line(collection_line(value_id="7"))
    assert reference is not None and reference.amount_cents == 0


def test_collection_document_is_a_payment_matched_with_the_bank():
    text = (
        "Fatura de serviços\nVencimento 15/10/2026\nCNPJ 33.333.333/0001-33\n"
        f"Total a pagar R$ 186,92\n{collection_line()}"
    )
    document = extract_document(text, source="s.pdf", page=1, confidence=70)
    assert (document.kind, document.amount_cents, document.due_on) == (
        "guia",
        18692,
        date(2026, 10, 15),
    )
    assert document.is_payment and not document.uncertain
    bank = [BankLine(1, date(2026, 10, 15), -18692, "PAGAMENTO CONVENIO TELEFONIA")]
    result = simulate(bank, documents=[document])
    assert result.documents[0].line is result.lines[0]
    assert "s.pdf;1;guia;186,92;15/10/2026" in render_documents_csv(result)


def test_utility_bill_with_total_to_pay_is_a_payment():
    bill = extract_document(
        "Período de uso\nVencimento 15/10/2026\nTotala pagar\nR$186,92\nPlano R$186,16",
        source="s.pdf",
        page=1,
        confidence=95,
    )
    assert (bill.kind, bill.amount_cents, bill.is_payment) == ("fatura", 18692, True)


def test_boleto_line_with_misread_separators_still_validates():
    line = boleto_line(bank="001", cents=94243)
    glued = line.replace(" ", "", 1).replace(
        ".", ":", 2
    )  # campo 1 colado ao 2; ponto lido como ":"
    tail_glued = line[: line.rfind(" ")] + line[line.rfind(" ") + 1 :]  # DV colado ao fator
    for text in (glued, tail_glued, f"|{line}|"):
        parsed = parse_boleto_line(text)
        assert parsed is not None and parsed.amount_cents == 94243, text


def test_amount_in_words_tolerates_ocr_misspelling():
    assert amount_in_words("A quantia de SEISSENTOS E CINQUENTA REAIS referente") == 65000
    assert amount_in_words("(mil trezentos e oitenta e oito reais e dezoito centavos)") == 138818
    assert amount_in_words("dois milhões e duzentos mil reais") == 220000000
    assert amount_in_words("cinquenta centavos") == 50
    assert amount_in_words("SEM VALORES EXPRESSOS EM REAIS") is None
    assert amount_in_words("Recibo de aluguel 650,00") is None


def test_amount_in_words_confirms_or_questions_the_figure():
    confirmed = extract_document(
        "Recibo de aluguel\nLíquido 650,00\nA quantia de SEISSENTOS E CINQUENTA REAIS",
        source="s.pdf",
        page=1,
        confidence=80,
    )
    assert confirmed.amount_cents == 65000 and not confirmed.uncertain and not confirmed.note
    divergent = extract_document(
        "Recibo\nLíquido 650,00\na quantia de seiscentos e sessenta reais",
        source="s.pdf",
        page=1,
        confidence=95,
    )
    assert divergent.amount_cents == 65000  # vale o algarismo
    assert divergent.note == "valor por extenso diferente (660,00); confirmar"
    alone = extract_document(
        "Recibo\na quantia de seiscentos reais", source="s.pdf", page=1, confidence=95
    )
    assert alone.amount_cents is None  # o extenso sozinho não cria valor
    figure_and_words = extract_document(
        "Recibo\nRecebi R$ 600,00 (seiscentos reais)", source="s.pdf", page=1, confidence=95
    )
    assert figure_and_words.amount_cents == 60000 and figure_and_words.corroborated


def test_sum_of_two_values_on_the_page_confirms_the_amount():
    text = "RECIBO DE RESSARCIMENTO\nR$1.388,08\nR$ 158,89\n1.229,19\n1.388,08 p"
    receipt = extract_document(text, source="s.pdf", page=1, confidence=80)
    assert receipt.amount_cents == 138808 and receipt.corroborated and not receipt.uncertain
    caixa = CashbookSheet("CAIXA", 0, (cash(1, date(2026, 10, 20), "PAGTO AGUA/LUZ", -138818),), ())
    result = simulate([], cash_accounts=[caixa], documents=[receipt])
    assert "confirmado na página" in result.documents[0].note
    shares = "RECIBO DE DISTRIBUIÇÃO\nSócio A R$ 5.000,00\nSócio B R$ 5.000,00\nTOTAL R$ 10.000,00"
    assert not extract_document(shares, source="s.pdf", page=1, confidence=80).uncertain
