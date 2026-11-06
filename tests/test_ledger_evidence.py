from __future__ import annotations

import hashlib
import json
import stat
from io import BytesIO, StringIO

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError
from reportlab.pdfgen.canvas import Canvas
from scripts.compare_bank_ledger import main

from apps.hub.ledger_evidence import (
    LedgerEvidenceError,
    compare_ledger_files,
    read_dominio_ledger_pdf,
)

COMPANY = "EMPRESA SINTETICA LTDA"
WIDTH, HEIGHT = 595.273, 841.886


def money(cents, *, balance=False):
    integer, fraction = divmod(abs(cents), 100)
    value = f"{integer:,}".replace(",", ".") + f",{fraction:02}"
    return value + (("D" if cents > 0 else "C") if balance and cents else "")


def ledger_pdf(
    *,
    pages=None,
    opening=100,
    total=True,
    wrong_total=False,
    company=COMPANY,
    page_numbers=None,
    changed_company=False,
    period="01/09/2026 - 30/09/2026",
    overlapping=False,
    swap_columns=False,
):
    pages = pages or [[{"debit": 10000}, {"credit": 2000}]]
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(WIDTH, HEIGHT))
    previous, index, debit_total, credit_total = opening, 0, 0, 0
    for page_index, rows in enumerate(pages):
        canvas.setFont("Helvetica", 7)
        page_no = page_numbers[page_index] if page_numbers else page_index + 1
        label = "OUTRA EMPRESA LTDA" if changed_company and page_index else company
        for x, top, text in [
            (0, 10, f"Empresa: {label}"),
            (465, 10, f"Folha: {page_no:04}"),
            (0, 22, "C.N.P.J.: 00.000.000/0001-00"),
            (0, 32, f"Período: {period}"),
            (264, 50, "RAZÃO"),
            (0, 70, "Data"),
            (46, 70, "Número Histórico"),
            (315, 70, "Cta.C.Part."),
            (381, 70, "Crédito" if swap_columns else "Débito"),
            (438, 70, "Débito" if swap_columns else "Crédito"),
            (495, 70, "Saldo-Exercício"),
            (0, 80, "Conta: 8 - 1.1.01 BANCO SINTETICO"),
        ]:
            canvas.drawString(x, HEIGHT - top, text)
        if page_index == 0:
            canvas.drawString(79, HEIGHT - 90, "SALDO ANTERIOR")
            canvas.drawRightString(554, HEIGHT - 90, money(opening, balance=True))
        for row_index, row in enumerate(rows):
            index += 1
            y = HEIGHT - 110 - row_index * 20
            debit, credit = row.get("debit", 0), row.get("credit", 0)
            previous += debit - credit
            debit_total += debit
            credit_total += credit
            if overlapping:
                # A separate history layer 0.9 pt above the numeric baseline.
                canvas.drawString(0, y + 0.9, "RECEBIMENTO PIX 00000000000000 " * 12)
            canvas.drawString(0, y, row.get("date", "01/09/2026"))
            canvas.drawRightString(75, y, row.get("entry", str(100000 + index)))
            canvas.drawString(79, y - 9, "Historico sintetico")
            if row.get("counterpart", "9") is not None:
                canvas.drawRightString(355, y, row.get("counterpart", "9"))
            if debit or row.get("print_zero"):
                canvas.drawRightString(406, y, money(debit))
            if credit:
                canvas.drawRightString(466, y, money(credit))
            canvas.drawRightString(554, y, money(row.get("balance", previous), balance=True))
        if page_index == len(pages) - 1 and total:
            y = HEIGHT - 150 - len(rows) * 20
            canvas.drawString(257, y, "Total da conta:")
            canvas.drawRightString(406, y, money(debit_total + int(wrong_total)))
            canvas.drawRightString(466, y, money(credit_total))
        canvas.showPage()
    canvas.save()
    return stream.getvalue()


def bank_pdf(*, amounts=(10000, -2000), holder=COMPANY, opening=100):
    stream = BytesIO()
    canvas = Canvas(stream, pagesize=(612, 792))
    canvas.setFont("Helvetica", 9)
    for y, text in [
        (775, f"Associado: {holder}"),
        (760, "Cooperativa: 9999"),
        (745, "Conta: 00001-0"),
        (725, "Extrato (Período de 01/09/2026 a 30/09/2026)"),
    ]:
        canvas.drawString(40, y, text)
    for x, text in [
        (40, "Data"),
        (120, "Descrição"),
        (350, "Documento"),
        (450, "Valor (R$)"),
        (520, "Saldo (R$)"),
    ]:
        canvas.drawString(x, 700, text)
    canvas.drawString(120, 680, "SALDO ANTERIOR")
    canvas.drawRightString(590, 680, money(opening))
    previous = opening
    for i, amount in enumerate(amounts):
        y = 660 - i * 20
        previous += amount
        canvas.drawString(40, y, "01/09/2026")
        canvas.drawString(120, y, "Movimento sintetico")
        canvas.drawString(350, y, f"DOC-{i}")
        canvas.drawRightString(500, y, ("-" if amount < 0 else "") + money(amount))
        canvas.drawRightString(590, y, ("-" if previous < 0 else "") + money(previous))
    canvas.save()
    return stream.getvalue()


def ofx(amounts=(10000, -2000)):
    rows = "".join(
        f"<STMTTRN><DTPOSTED>20260901<TRNAMT>{amount / 100:.2f}"
        f"<FITID>synthetic-{i}<MEMO>Teste</STMTTRN>"
        for i, amount in enumerate(amounts)
    )
    return (
        f"OFXHEADER:100\n<OFX><BANKID>748<ACCTID>000010<BANKTRANLIST>{rows}</BANKTRANLIST></OFX>"
    ).encode()


def compare(**kwargs):
    return compare_ledger_files(
        ofx=kwargs.pop("ofx", ofx()),
        bank_pdf=kwargs.pop("bank_pdf", bank_pdf()),
        ledger_pdf=kwargs.pop("ledger_pdf", ledger_pdf()),
        company_name=COMPANY,
        ledger_code="8",
        **kwargs,
    )


def test_reads_bank_side_with_explicit_columns_and_preserves_missing_counterpart():
    report = read_dominio_ledger_pdf(
        ledger_pdf(
            pages=[[{"debit": 10000}], [{"credit": 2000, "counterpart": None}]],
        )
    )
    assert report.company_name == COMPANY and report.ledger_code == "8"
    assert report.opening_cents == 100 and report.closing_cents == 8100
    assert [r.amount_cents for r in report.lines] == [10000, -2000]
    assert report.lines[1].counterparty_code is None
    assert [r.reference["page"] for r in report.lines] == [1, 2]


def test_overlapping_history_layers_do_not_corrupt_dates_ids_or_balances():
    report = read_dominio_ledger_pdf(ledger_pdf(overlapping=True))
    assert [r.printed_entry_number for r in report.lines] == ["100001", "100002"]
    assert report.closing_cents == 8100


def test_credit_balances_keep_their_printed_sign():
    report = read_dominio_ledger_pdf(ledger_pdf(opening=-10100))
    assert report.opening_cents == -10100 and report.closing_cents == -2100


@pytest.mark.parametrize("limit", ["MAX_PAGES", "MAX_ROWS", "MAX_SOURCE_BYTES"])
def test_rejects_report_above_resource_limits(monkeypatch, limit):
    content = ledger_pdf(pages=[[{"debit": 1}], [{"debit": 1}]])
    monkeypatch.setattr(f"apps.hub.ledger_evidence.{limit}", 1)
    with pytest.raises(LedgerEvidenceError):
        read_dominio_ledger_pdf(content)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"total": False},
        {"wrong_total": True},
        {"swap_columns": True},
        {"pages": [[{"debit": 10000, "balance": 100}]]},
        {"pages": [[{"debit": 1, "entry": "100001"}, {"debit": 1, "entry": "100001"}]]},
        {"pages": [[{"debit": 1, "date": "31/09/2026"}]]},
        {"pages": [[{"debit": 1, "date": "01/10/2026"}]]},
        {"pages": [[{"debit": 1, "date": "bad-date"}]]},
        {"pages": [[{"debit": 1, "date": "02/09/2026"}, {"debit": 1}]]},
        {"pages": [[{"debit": 1, "credit": 1}]]},
        {"pages": [[{"print_zero": True}]]},
        {"pages": [[{"debit": 1, "entry": ""}]]},
        {"pages": [[{"debit": 1}], [{"debit": 1}]], "page_numbers": [1, 3]},
        {"pages": [[{"debit": 1}], [{"debit": 1}]], "changed_company": True},
        {"pages": [[{"debit": 1}]], "page_numbers": [2]},
        {"period": "30/09/2026 - 01/09/2026"},
    ],
)
def test_rejects_inconsistent_or_incomplete_reports(kwargs):
    with pytest.raises(LedgerEvidenceError):
        read_dominio_ledger_pdf(ledger_pdf(**kwargs))


@pytest.mark.parametrize("content", [b"", b"not-a-pdf"])
def test_rejects_invalid_pdf(content):
    with pytest.raises(LedgerEvidenceError):
        read_dominio_ledger_pdf(content)


def test_comparison_is_evidence_and_never_confirmation_or_complete_journal():
    result = compare()
    assert result["same_date_amount_multiset"] and result["same_opening_and_closing"]
    assert result["equal_date_amount_count"] == result["unique_candidate_count"] == 2
    assert result["bank_pair"]["same_date_amount_multiset"]
    assert result["confirmed_allocations"] == 0
    assert not result["complete_journal_entries"]
    assert not result["homologated"] and not result["account_relation_verified"]
    assert not result["transmitted"] and not result["erp_written"]


def test_repeated_amounts_stay_in_an_ambiguous_group_without_pairing_by_order():
    amounts = (10000, 10000, -2000)
    result = compare(
        ofx=ofx(amounts),
        bank_pdf=bank_pdf(amounts=amounts),
        ledger_pdf=ledger_pdf(
            pages=[[{"debit": 10000}, {"debit": 10000}, {"credit": 2000}]],
        ),
    )
    assert result["equal_date_amount_count"] == 3
    assert result["unique_candidate_count"] == 1
    assert result["ambiguous_group_count"] == 1
    group = next(g for g in result["groups"] if g["state"] == "ambiguous_candidates")
    assert len(group["bank_rows"]) == len(group["ledger_rows"]) == 2
    assert result["confirmed_allocations"] == 0


def test_preserves_multiplicity_and_shows_bank_only_and_ledger_only():
    result = compare(ledger_pdf=ledger_pdf(pages=[[{"debit": 9000}, {"credit": 2000}]]))
    assert result["bank_only_count"] == result["ledger_only_count"] == 1
    assert not result["same_date_amount_multiset"]
    assert not result["same_opening_and_closing"]


def test_bank_pair_discrepancy_remains_visible_even_when_pdf_matches_ledger():
    result = compare(ofx=ofx((10000, -2000, 10000)))
    assert result["same_date_amount_multiset"]
    assert result["bank_pair"]["ofx_only_count"] == 1
    assert not result["bank_pair"]["same_date_amount_multiset"]


@pytest.mark.parametrize("change", ["ledger-company", "bank-holder", "ledger-account", "period"])
def test_refuses_cross_scope_files(change):
    kwargs = {}
    if change == "ledger-company":
        kwargs["ledger_pdf"] = ledger_pdf(company="OUTRA EMPRESA")
    elif change == "bank-holder":
        kwargs["bank_pdf"] = bank_pdf(holder="OUTRA EMPRESA")
    elif change == "ledger-account":
        with pytest.raises(LedgerEvidenceError, match="recorte"):
            compare_ledger_files(
                ofx=ofx(),
                bank_pdf=bank_pdf(),
                ledger_pdf=ledger_pdf(),
                company_name=COMPANY,
                ledger_code="9",
            )
        return
    else:
        kwargs["ledger_pdf"] = ledger_pdf(period="01/09/2026 - 29/09/2026")
    with pytest.raises(LedgerEvidenceError):
        compare(**kwargs)


def cli_sources(tmp_path):
    args, paths = [], []
    for name, content in [("ofx", ofx()), ("bank-pdf", bank_pdf()), ("ledger-pdf", ledger_pdf())]:
        path = tmp_path / name
        path.write_bytes(content)
        args.extend((f"--{name}", str(path)))
        paths.append(path)
    output = tmp_path / "evidence.json"
    args.extend(("--company-name", COMPANY, "--ledger-code", "8", "--output", str(output)))
    return args, paths, output


def test_cli_publishes_private_atomic_report_and_preserves_sources(tmp_path, capsys):
    args, paths, output = cli_sources(tmp_path)
    before = [p.read_bytes() for p in paths]
    assert main(args) == 0
    report = json.loads(output.read_text())
    assert report["source_sha256"] == {
        kind: hashlib.sha256(content).hexdigest()
        for kind, content in zip(("ofx", "bank_pdf", "ledger_pdf"), before, strict=True)
    }
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert [p.read_bytes() for p in paths] == before
    assert COMPANY not in capsys.readouterr().out
    assert report["groups"][0]["date"] == "2026-09-01"


@pytest.mark.parametrize("symlink", [False, True])
def test_cli_never_replaces_existing_output_or_symlink(tmp_path, symlink):
    args, paths, output = cli_sources(tmp_path)
    if symlink:
        output.symlink_to(paths[0])
    else:
        output.write_text("preserve")
    with pytest.raises(SystemExit) as error:
        main(args)
    assert error.value.code == 2
    assert output.is_symlink() if symlink else output.read_text() == "preserve"
    assert not list(tmp_path.glob(".cica-evidence-*"))


def test_cli_rejects_large_source_without_partial_output(tmp_path, monkeypatch):
    args, _, output = cli_sources(tmp_path)
    monkeypatch.setattr("scripts.compare_bank_ledger.MAX_SOURCE_BYTES", 20)
    with pytest.raises(SystemExit):
        main(args)
    assert not output.exists()


def test_cli_reports_invalid_bank_pdf_without_writing_partial_output(tmp_path, capsys):
    args, paths, output = cli_sources(tmp_path)
    paths[1].write_bytes(b"invalid-bank-pdf")
    with pytest.raises(SystemExit):
        main(args)
    assert not output.exists()
    assert "Extrato: PDF inválido" in capsys.readouterr().err


def test_cli_cleans_temporary_file_on_failed_publication(tmp_path, monkeypatch):
    args, _, output = cli_sources(tmp_path)

    def fail(_):
        raise OSError("synthetic disk failure")

    monkeypatch.setattr("apps.hub.ledger_evidence.os.fsync", fail)
    with pytest.raises(SystemExit):
        main(args)
    assert not output.exists()
    assert not list(tmp_path.glob(".cica-evidence-*"))


def test_cli_performs_no_database_connection_or_outbound_network(tmp_path, monkeypatch):
    args, _, output = cli_sources(tmp_path)

    def deny(*_args, **_kwargs):
        pytest.fail("Offline comparison attempted an external connection")

    monkeypatch.setattr("socket.socket.connect", deny)
    monkeypatch.setattr("socket.socket.connect_ex", deny)
    monkeypatch.setattr("django.db.backends.base.base.BaseDatabaseWrapper.connect", deny)
    assert main(args) == 0
    assert output.exists()


def test_deployed_command_preserves_offline_private_report_contract(tmp_path, monkeypatch):
    args, paths, output = cli_sources(tmp_path)
    original = [p.read_bytes() for p in paths]
    stdout = StringIO()

    def deny(*_args, **_kwargs):
        pytest.fail("Administrative comparison attempted an external connection")

    monkeypatch.setattr("socket.socket.connect", deny)
    monkeypatch.setattr("django.db.backends.base.base.BaseDatabaseWrapper.connect", deny)
    call_command("compare_bank_ledger", *args, stdout=stdout)
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    assert json.loads(output.read_text())["equal_date_amount_count"] == 2
    assert [p.read_bytes() for p in paths] == original
    assert COMPANY not in stdout.getvalue()
    with pytest.raises(CommandError):
        call_command("compare_bank_ledger", *args, stdout=stdout)
    assert not list(tmp_path.glob(".cica-evidence-*"))


def test_deployed_command_rejects_invalid_input_without_partial_report(tmp_path):
    args, paths, output = cli_sources(tmp_path)
    paths[2].write_bytes(b"broken-pdf")
    with pytest.raises(CommandError, match="PDF inválido"):
        call_command("compare_bank_ledger", *args)
    assert not output.exists()
