"""D-389: bank balances of the conference report from the OFX's own LEDGERBAL."""

from __future__ import annotations

from datetime import date

import pytest
from django.urls import reverse
from tests.test_reconciliation_workbench import make_case

from apps.hub.models import ClientCompany, FinancialAccount, ProductModule
from apps.hub.reconciliation import read_ofx_statement_balance
from apps.hub.reconciliation_report import build_source_report, report_presentation_context
from apps.hub.reconciliation_service import create_source_file, process_run

# Synthetic statement: 01/09 +100,00; 10/09 -30,00; 20/09 +5,50 → closing 1.075,50.
ROWS = (("20260901", "100.00"), ("20260910", "-30.00"), ("20260920", "5.50"))


def ofx(
    *,
    balance: str | None = "1075.50",
    as_of: str = "20260930",
    start: str | None = "20260901",
    end: str | None = "20260930",
    extra: str = "",
    account: str = "<BANKID>748<BRANCHID>0101<ACCTID>12345",
) -> bytes:
    window = (f"<DTSTART>{start}" if start else "") + (f"<DTEND>{end}" if end else "")
    rows = "".join(
        f"<STMTTRN><TRNTYPE>OTHER<DTPOSTED>{day}<TRNAMT>{amount}"
        f"<FITID>fit-{index}<MEMO>Movimento sintético {index}</STMTTRN>"
        for index, (day, amount) in enumerate(ROWS)
    )
    ledger = (
        f"<LEDGERBAL><BALAMT>{balance}<DTASOF>{as_of}</LEDGERBAL>" if balance is not None else ""
    )
    return (
        "OFXHEADER:100\n<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKACCTFROM>"
        f"{account}</BANKACCTFROM>"
        f"<BANKTRANLIST>{window}{rows}</BANKTRANLIST>{ledger}{extra}"
        "<AVAILBAL><BALAMT>999.99<DTASOF>20260930</AVAILBAL>"
        "</STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"
    ).encode()


def test_reads_ledger_balance_not_available_balance():
    parsed = read_ofx_statement_balance(ofx())
    assert parsed is not None
    assert parsed.balance_cents == 107550
    assert (parsed.as_of, parsed.period_start, parsed.period_end) == (
        date(2026, 9, 30),
        date(2026, 9, 1),
        date(2026, 9, 30),
    )


def test_balances_for_full_and_partial_periods():
    parsed = read_ofx_statement_balance(ofx())
    assert parsed is not None
    assert parsed.balances_for(date(2026, 9, 1), date(2026, 9, 30)) == (100000, 107550)
    # 05/09 a 15/09: opening after the 01/09 credit; closing before the 20/09 credit.
    assert parsed.balances_for(date(2026, 9, 5), date(2026, 9, 15)) == (110000, 107000)


def test_zero_and_negative_balances_are_real_values():
    assert read_ofx_statement_balance(ofx(balance="0.00")).balance_cents == 0
    assert read_ofx_statement_balance(ofx(balance="-12,34")).balance_cents == -1234


@pytest.mark.parametrize(
    "content",
    [
        ofx(balance=None),
        ofx(balance="abc"),
        ofx(start=None),
        ofx(end=None),
        ofx(as_of="20260915"),  # balance before the last movement of the file
        ofx(as_of="20261005"),  # balance after the declared end: unlisted movements possible
        ofx(start="20260905"),  # declared window does not hold all movements
        ofx(extra="<LEDGERBAL><BALAMT>1.00<DTASOF>20260930</LEDGERBAL>"),
        b"not an ofx",
    ],
)
def test_unproven_coverage_yields_no_balance(content):
    assert read_ofx_statement_balance(content) is None


def test_periods_outside_the_file_yield_no_balance():
    parsed = read_ofx_statement_balance(ofx(as_of="20260925"))
    assert parsed is not None
    assert parsed.balances_for(date(2026, 8, 31), date(2026, 9, 20)) is None
    assert parsed.balances_for(date(2026, 9, 1), date(2026, 9, 26)) is None
    assert parsed.balances_for(date(2026, 9, 1), date(2026, 9, 25)) == (100000, 107550)


def _source(organization, settings, tmp_path, content):
    settings.MEDIA_ROOT = tmp_path
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa sintética", dominio_code="TEST9"
    )
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Banco sintético",
        account_reference="748:0101:12345",
        ledger_code="1.1",
    )
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        financial_account=account,
        filename="extrato.ofx",
        content=content,
        origin="bank_statement",
    )
    assert process_run(str(run.pk))["created"] == len(ROWS)
    source.refresh_from_db()
    return source


@pytest.mark.django_db
def test_report_shows_bank_balances_from_ofx(organization, settings, tmp_path):
    source = _source(organization, settings, tmp_path, ofx())
    report = build_source_report(source)
    assert (report["opening_bank_cents"], report["closing_bank_cents"]) == (100000, 107550)
    assert any("saldo final informado no OFX" in warning for warning in report["warnings"])
    partial = build_source_report(source, start=date(2026, 9, 5), end=date(2026, 9, 15))
    assert (partial["opening_bank_cents"], partial["closing_bank_cents"]) == (110000, 107000)
    labels = {
        item["label"]: item["value"]
        for item in report_presentation_context(source, report)["report_balances"]
    }
    assert labels["Saldo inicial do banco"] == "R$ 1.000,00"
    assert labels["Saldo final do banco"] == "R$ 1.075,50"
    # The Razão side is unchanged: no opening informed, no calculated closing.
    assert labels["Saldo inicial do Razão"] == "Não informado"


@pytest.mark.django_db
def test_report_keeps_not_informed_without_ledger_balance(organization, settings, tmp_path):
    source = _source(organization, settings, tmp_path, ofx(balance=None))
    report = build_source_report(source)
    assert report["opening_bank_cents"] is None and report["closing_bank_cents"] is None
    assert not any("saldo final informado no OFX" in warning for warning in report["warnings"])


@pytest.mark.django_db
def test_print_report_page_shows_ofx_balances(organization, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    case = make_case(organization)
    source, run, _ = create_source_file(
        organization=organization,
        company=case["company"],
        financial_account=case["account"],
        filename="extrato-com-saldo.ofx",
        content=ofx(account="<BANKID>001<ACCTID>123"),
        origin="bank_statement",
    )
    assert process_run(str(run.pk))["created"] == len(ROWS)
    url = reverse("hub:reconciliation-source-report", args=[source.pk]) + "?format=print"
    page = case["client"].get(url)
    assert page.status_code == 200
    html = page.content.decode()
    assert "R$ 1.000,00" in html and "R$ 1.075,50" in html
    assert "saldo final informado no OFX" in html
