"""Leitores multifontes (D-409): posição Domínio, francesinha Sicredi e caixa do cliente.

Todos os dados são sintéticos; só o leiaute imita os arquivos reais.
"""

from __future__ import annotations

from datetime import date
from io import BytesIO

import pytest
from openpyxl import Workbook
from reportlab.pdfgen.canvas import Canvas

from apps.hub.multisource.client_cashbook import (
    DocumentRef,
    extract_refs,
    read_client_cashbook_xlsx,
)
from apps.hub.multisource.common import MultisourceError, cents_from_number, names_match
from apps.hub.multisource.francesinha import read_francesinha_pdf
from apps.hub.multisource.title_position import (
    PAYABLE,
    RECEIVABLE,
    parse_title_position_rows,
    read_title_position_xls,
)

# ---------------------------------------------------------------- posição de títulos (.xls)


def _row(width: int, **cells: object) -> list[object]:
    row: list[object] = [None] * width
    for index, value in cells.items():
        row[int(index[1:])] = value
    return row


def receivable_rows(
    *, saldo_total: float = 2300.0, parcela_total: float = 2500.0
) -> list[list[object]]:
    """Leiaute CR: colunas espalhadas como no Domínio (Documento c4, Vencimento c9, Saldo c21)."""
    w = 25
    return [
        _row(w, c0="Empresa:", c2="EMPRESA FICTICIA LTDA", c22="Página:", c24="1/1"),
        _row(w, c0="CNPJ:", c2="11222333000181", c22="Emissão:", c24="19/10/2026"),
        _row(w, c0="CONTAS A RECEBER POR CLIENTE"),
        _row(
            w,
            c4="Documento",
            c5="Emissão",
            c6="Saída",
            c9="Vencimento",
            c12="V. Parcela",
            c13="V. Recebido",
            c15="Juros",
            c17="Multa",
            c18="Outras",
            c19="Desconto",
            c20="Devolução",
            c21="Saldo",
            c24="Situação",
        ),
        _row(w, c0="Cliente:", c4="100 - CLIENTE ALFA LTDA - 9"),
        _row(
            w,
            c4=5001.0,
            c5=date(2026, 8, 1),
            c6=date(2026, 8, 1),
            c9=date(2026, 10, 15),
            c12=500.0,
            c13=0.0,
            c21=500.0,
            c24="Aberta",
        ),
        _row(
            w,
            c4=5001.0,
            c5=date(2026, 8, 1),
            c6=date(2026, 8, 1),
            c9=date(2026, 9, 15),
            c12=500.0,
            c13=0.0,
            c21=500.0,
            c24="Aberta",
        ),
        _row(w, c8="Sub Total:", c11=1000.0, c21=1000.0),
        _row(w, c0="Cliente:", c4="200 - CLIENTE BETA SA"),
        _row(
            w,
            c4=5002.0,
            c5=date(2026, 9, 1),
            c6=date(2026, 9, 1),
            c9=date(2026, 9, 30),
            c12=1500.0,
            c13=200.0,
            c21=1300.0,
            c24="Parcial",
        ),
        _row(w, c8="Sub Total:", c11=1500.0, c13=200.0, c21=1300.0),
        _row(w, c8="Total Geral:", c11=parcela_total, c13=200.0, c21=saldo_total, c23=9999.0),
    ]


def test_position_reads_receivables_with_ordinals_by_due_date():
    position = parse_title_position_rows(receivable_rows())
    assert position.kind == RECEIVABLE
    assert position.company_cnpj == "11222333000181"
    assert position.emitted_on == date(2026, 10, 19)
    alfa = [i for i in position.installments if i.document == "5001"]
    # A parcela de vencimento mais antigo é a 1ª, mesmo listada depois.
    assert [(i.ordinal, i.due_on.month) for i in sorted(alfa, key=lambda i: i.ordinal)] == [
        (1, 9),
        (2, 10),
    ]
    beta = next(i for i in position.installments if i.document == "5002")
    assert (beta.paid_cents, beta.balance_cents, beta.status) == (20000, 130000, "Parcial")
    assert position.balance_cents == 230000
    assert beta.label == "NF 5002 · parcela 1/1 · CLIENTE BETA SA"
    assert position.warnings == ()  # saldo e valor da parcela fecham; a coluna extra é ignorada


def test_position_warns_when_total_amount_differs_but_balance_closes():
    position = parse_title_position_rows(receivable_rows(parcela_total=2793.40))
    assert len(position.warnings) == 1 and "Q-59" in position.warnings[0]


def test_position_refuses_balance_that_does_not_close():
    with pytest.raises(MultisourceError, match="saldos das parcelas não fecha"):
        parse_title_position_rows(receivable_rows(saldo_total=2299.99))


def test_position_keeps_zero_balance_rows_out_of_matching():
    rows = receivable_rows()
    rows.insert(
        7, _row(25, c4=5003.0, c9=date(2026, 9, 1), c12=80.0, c13=80.0, c21=0.0, c24="Parcial")
    )
    position = parse_title_position_rows(rows)
    assert len(position.installments) == 4 and len(position.open_installments) == 3
    assert any("saldo zero" in w for w in position.warnings)


def test_position_detects_payables_and_rejects_unknown_layout():
    rows = receivable_rows()
    rows[2] = _row(25, c0="CONTAS A PAGAR POR FORNECEDOR")
    rows[4] = _row(25, c0="Fornecedor:", c4="100 - FORNECEDOR ALFA LTDA")
    rows[8] = _row(25, c0="Fornecedor:", c4="200 - FORNECEDOR BETA")
    assert parse_title_position_rows(rows).kind == PAYABLE
    with pytest.raises(MultisourceError, match="não é a posição"):
        parse_title_position_rows([r for i, r in enumerate(receivable_rows()) if i != 2])
    with pytest.raises(MultisourceError, match="situação desconhecida"):
        bad = receivable_rows()
        bad[5][24] = "Quitada"
        parse_title_position_rows(bad)


def test_position_xls_reader_rejects_non_spreadsheet():
    with pytest.raises(MultisourceError, match=r"\.xls legível"):
        read_title_position_xls(b"not a spreadsheet")


# ---------------------------------------------------------------- francesinha (PDF)


def francesinha_pdf(*, credit_total: str = "1.611,20", count: int = 3) -> bytes:
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(1500, 600))
    canvas.setFont("Helvetica", 7)
    header = [
        "Relatório Financeiro Francesinha",
        "Conta Corrente: 99999",
        "Dados referentes ao período 01/10/2026 a 31/10/2026",
        "Tipo de movimento: Crédito",
        f"Quantidade de Títulos: {count}",
        f"Total de Créditos {count} R$ {credit_total}",
        "Total Abatimento 0 R$ 0,00",
        "Total Desconto 0 R$ 0,00",
        "Total Juros 1 R$ 11,20",
        "Total Multa 0 R$ 0,00",
    ]
    for i, text in enumerate(header):
        canvas.drawString(40, 580 - i * 10, text)
    columns = [
        ("Seu Nº", 40),
        ("Nosso Nº", 120),
        ("Pagador", 236),
        ("Data Mvto", 342),
        ("Data Lçto C/C", 419),
        ("Vlr Nominal", 500),
        ("Abat.", 560),
        ("Desconto", 610),
        ("Juros", 670),
        ("Multa", 720),
        ("Vlr Mvto", 770),
        ("Tipo Mvto", 830),
        ("Desc. Mvto", 1084),
        ("Carteira", 1175),
        ("Agência", 1230),
        ("C/C", 1280),
        ("%", 1350),
        ("Valor", 1420),
    ]
    y = 460
    for label, x in columns:
        canvas.drawString(x, y, label)

    def row(y: float, your: str, our: str, payer: str, desc: str, values: list[str]) -> None:
        canvas.drawString(40, y, your)
        canvas.drawString(120, y, our)
        if payer:
            canvas.drawString(200, y, payer)
        canvas.drawString(342, y, "30/09/2026")
        canvas.drawString(419, y, "01/10/2026")
        for x, value in zip((500, 560, 610, 670, 720, 770), values, strict=True):
            canvas.drawString(x, y, value)
        canvas.drawString(830, y, "Crédito")
        if desc:
            canvas.drawString(1080, y, desc)
        canvas.drawString(1175, y, "Simples")
        canvas.drawString(1230, y, "0101")
        canvas.drawString(1280, y, "11111-1")
        canvas.drawString(1350, y, "100,00%")
        canvas.drawString(1420, y, values[-1])

    zero = "0,00"
    canvas.drawString(1080, 432, "Liquidação")
    row(
        425,
        "*100000101",
        "26/000001-1",
        "CLIENTE ALFA LTDA",
        "",
        ["1.400,00", zero, zero, "11,20", zero, "1.411,20"],
    )
    canvas.drawString(1080, 418, "CARTORIAL")
    canvas.drawString(200, 402, "CLIENTE BETA DE NOME")
    row(
        395,
        "XX00000002",
        "26/000002-2",
        "",
        "Liquidação COMPE",
        ["150,00", zero, zero, zero, zero, "150,00"],
    )
    canvas.drawString(200, 388, "MUITO LONGO LTDA")
    row(
        365,
        "XX00000003",
        "26/000003-3",
        "CLIENTE GAMA",
        "Liquidação COMPE",
        ["50,00", zero, zero, zero, zero, "50,00"],
    )
    canvas.drawString(40, 330, "Impresso em 10/11/2026 10:12")
    canvas.drawString(
        40, 320, "* A transação acima foi realizada via internet conforme as condições."
    )
    canvas.showPage()
    canvas.save()
    return stream.getvalue()


def test_francesinha_reads_items_and_rejoins_wrapped_payer_and_description():
    report = read_francesinha_pdf(francesinha_pdf())
    assert (report.period_start, report.period_end, report.account) == (
        date(2026, 10, 1),
        date(2026, 10, 31),
        "99999",
    )
    assert [i.payer for i in report.items] == [
        "CLIENTE ALFA LTDA",
        "CLIENTE BETA DE NOME MUITO LONGO LTDA",
        "CLIENTE GAMA",
    ]
    first = report.items[0]
    assert first.description == "Liquidação CARTORIAL"
    assert (first.nominal_cents, first.interest_cents, first.amount_cents, first.extra_cents) == (
        140000,
        1120,
        141120,
        1120,
    )
    assert first.credited_on == date(2026, 10, 1)
    assert first.your_number == "*100000101"  # guardado como veio (Q-52)


def test_francesinha_refuses_totals_that_do_not_match():
    with pytest.raises(MultisourceError, match="total de créditos"):
        read_francesinha_pdf(francesinha_pdf(credit_total="1.611,21"))
    with pytest.raises(MultisourceError, match="3 títulos lidos"):
        read_francesinha_pdf(francesinha_pdf(count=4))


def test_francesinha_rejects_other_pdf():
    stream = BytesIO()
    canvas = Canvas(stream)
    canvas.drawString(40, 700, "Outro relatório qualquer")
    canvas.showPage()
    canvas.save()
    with pytest.raises(MultisourceError, match="não é o Relatório"):
        read_francesinha_pdf(stream.getvalue())


# ---------------------------------------------------------------- caixa do cliente (.xlsx)


def cashbook_xlsx(*, broken_balance: bool = False) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "BANCO X"
    sheet.append(["BANCO", "BANCO X - CONTA 1", "maio"])  # mês do cabeçalho é ignorado
    sheet.append([])
    sheet.append(["DATA", "HISTÓRICO", "ENTRADA", "SAÍDA", "SALDO"])
    sheet.append([None, "SALDO ANTERIOR", None, None, 100])
    sheet.append([date(2026, 10, 1), "FRANC NF 5001/02", 500, None, 600])
    sheet.append([date(2026, 10, 1), "PAGTO TRANSP (CTE 70001, 70002)", None, 140, 460])
    sheet.append(
        [date(2026, 10, 2), "RECEB LOJA NF 11,12", 30, None, 999 if broken_balance else 490]
    )
    sheet.append([date(2026, 10, 2), "13, 14 SERIE 200 NF 15", None, None, 490])
    other = book.create_sheet("RESUMO")
    other.append(["sem cabeçalho de caixa"])
    stream = BytesIO()
    book.save(stream)
    return stream.getvalue()


def test_cashbook_reads_lines_continuations_and_refs():
    cashbook = read_client_cashbook_xlsx(cashbook_xlsx())
    assert [s.name for s in cashbook.sheets] == ["BANCO X"]
    sheet = cashbook.sheet("banco x")
    assert sheet.opening_cents == 10000 and sheet.warnings == ()
    assert [line.amount_cents for line in sheet.lines] == [50000, -14000, 3000]
    assert [str(r) for r in sheet.lines[0].refs] == ["NF 5001/02"]
    assert [str(r) for r in sheet.lines[1].refs] == ["CT-e 70001", "CT-e 70002"]
    # A linha sem valor continua o histórico anterior; "SERIE 200" não vira nota.
    assert [r.number for r in sheet.lines[2].refs] == ["11", "12", "13", "14", "15"]
    with pytest.raises(MultisourceError, match="aba 'CEF' não encontrada"):
        cashbook.sheet("CEF")


def test_cashbook_warns_when_spreadsheet_balance_differs():
    sheet = read_client_cashbook_xlsx(cashbook_xlsx(broken_balance=True)).sheet("BANCO X")
    assert any("saldo da planilha difere" in w for w in sheet.warnings)


@pytest.mark.parametrize(
    ("history", "expected"),
    [
        ("PAGTO XY (CTE 323599, 323808)", [("cte", "323599"), ("cte", "323808")]),
        ("PAGTO XY CTE 325914 E 326018", [("cte", "325914"), ("cte", "326018")]),
        ("FRANC NF29992/02", [("nf", "29992")]),
        ("PAGO FORNECEDOR nf 36240", [("nf", "36240")]),
        ("PATGO FORNECEDOR NOTA DE DEBITO 290", [("doc", "290")]),
        ("PAGTO PLANO SAUDE FATURA  166", [("doc", "166")]),
        ("DISTRIBUIÇÃO DE LUCROS", []),
        ("PAGTO NF 400 FORNECEDOR", [("nf", "400")]),
    ],
)
def test_extract_refs(history, expected):
    assert [(r.kind, r.number) for r in extract_refs(history)] == expected


def test_extract_refs_keeps_installment_suffix():
    assert extract_refs("FRANC NF 29740/03") == (DocumentRef("nf", "29740", "03"),)


def test_common_helpers():
    assert cents_from_number(1411.2) == 141120
    assert cents_from_number("1.411,20") == 141120
    assert names_match("SOFTWARE ALFA TEC", "SOFTWARE ALFA TECNOLOGIA DA INFORMACAO LTDA")
    assert names_match("XY LOGI", "XY LOGISTICA LTDA")
    assert names_match("METAIS ALFA LTDA", "METAIS ALFA LTDA - 1002")
    assert not names_match("METALURGICA ALFA", "METALURGICA BETA LTDA")
    assert not names_match("", "QUALQUER")
