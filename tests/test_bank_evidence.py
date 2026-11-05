from __future__ import annotations

from io import BytesIO

import pytest
from reportlab.pdfgen.canvas import Canvas

from apps.hub.bank_evidence import compare_bank_files, read_sicredi_pdf
from apps.hub.reconciliation_service import ReconciliationError


def sicredi_pdf(*, wrong_balance=False, future=False):
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(612, 792))
    canvas.setFont("Helvetica", 9)
    canvas.drawString(40, 760, "Cooperativa: 9999")
    canvas.drawString(40, 745, "Conta: 00001-0")
    canvas.drawString(40, 725, "Extrato (Período de 01/09/2026 a 30/09/2026)")
    canvas.drawString(40, 700, "Data")
    canvas.drawString(120, 700, "Descrição")
    canvas.drawString(350, 700, "Documento")
    canvas.drawString(450, 700, "Valor (R$)")
    canvas.drawString(520, 700, "Saldo (R$)")
    canvas.drawString(120, 680, "SALDO ANTERIOR")
    canvas.drawRightString(590, 680, "1,00")
    rows = [
        ("01/09/2026", "Recebimento sintético", "DOC-1", "100,00", "101,00"),
        ("01/09/2026", "Pagamento sintético", "", "-20,00", "80,00" if wrong_balance else "81,00"),
    ]
    for i, (day, text, document, amount, balance) in enumerate(rows):
        y = 660 - i * 20
        for x, value in [(40, day), (120, text), (350, document)]:
            canvas.drawString(x, y, value)
        canvas.drawRightString(500, y, amount)
        canvas.drawRightString(590, y, balance)
    if future:
        canvas.drawString(40, 610, "Lançamentos Futuros (Próximos 30 dias)")
        canvas.drawString(40, 590, "01/10/2026")
        canvas.drawString(120, 590, "Previsão sem pagamento")
        canvas.drawRightString(500, 590, "-50,00")
        canvas.drawRightString(590, 590, "31,00")
    canvas.showPage()
    canvas.save()
    return stream.getvalue()


def test_sicredi_reads_transaction_amount_document_and_running_balance_separately():
    evidence = read_sicredi_pdf(sicredi_pdf(future=True))
    assert evidence is not None
    assert evidence.opening_cents == 100 and evidence.closing_cents == 8100
    assert [r.amount_cents for r in evidence.lines] == [10000, -2000]
    assert [r.document for r in evidence.lines] == ["DOC-1", ""]
    assert [r.description for r in evidence.lines] == [
        "Recebimento sintético",
        "Pagamento sintético",
    ]
    assert evidence.lines[1].reference["bbox"]["unit"] == "pdf_points"
    assert evidence.lines[1].reference["page"] == 1


def test_sicredi_refuses_inconsistent_running_balances_instead_of_silently_skipping_rows():
    with pytest.raises(ReconciliationError, match="sequência de saldos"):
        read_sicredi_pdf(sicredi_pdf(wrong_balance=True))


def test_bank_pair_preserves_multiplicity_and_never_claims_ledger_or_account_acceptance():
    ofx = (
        b"OFXHEADER:100\n<OFX><BANKID>748<ACCTID>9999<BANKTRANLIST>"
        b"<STMTTRN><DTPOSTED>20260901<TRNAMT>100<FITID>a<MEMO>Teste</STMTTRN>"
        b"<STMTTRN><DTPOSTED>20260901<TRNAMT>-20<FITID>b<MEMO>Teste</STMTTRN>"
        b"</BANKTRANLIST></OFX>"
    )
    result = compare_bank_files(ofx=ofx, pdf=sicredi_pdf())
    assert result["same_date_amount_multiset"]
    assert not result["independent_ledger"] and not result["homologated"]
    assert result["account_relation"] == "requires_confirmation"
    duplicate = ofx.replace(
        b"</BANKTRANLIST>",
        b"<STMTTRN><DTPOSTED>20260901<TRNAMT>100<FITID>c<MEMO>Teste</STMTTRN></BANKTRANLIST>",
    )
    result = compare_bank_files(ofx=duplicate, pdf=sicredi_pdf())
    assert not result["same_date_amount_multiset"]
    assert result["ofx_only_count"] == 1
