"""D-397: no double booking in direct use, across every company and bank account of the office."""

from __future__ import annotations

import csv
import io
from datetime import date

import pytest
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.auto_confirm import auto_confirm_exact
from apps.hub.direct_use import run_for_account, run_for_organization
from apps.hub.double_booking import SIMILAR_DAYS, WITHDRAWN_ACTION, statement_complement
from apps.hub.ledger_import import LEDGER_COLUMNS
from apps.hub.models import (
    AccountingExport,
    ClientCompany,
    FinancialAccount,
    JournalEntry,
    LedgerAccount,
    NormalizedMovement,
    ProductModule,
)
from apps.hub.reconciliation_service import (
    ReconciliationError,
    create_export,
    create_source_file,
    process_run,
)
from apps.organizations.models import Membership
from apps.platform.models import TenantContract

pytestmark = pytest.mark.django_db
CODES = {"8": "Banco", "4": "Fornecedores", "51": "Tarifas", "9": "Clientes"}


@pytest.fixture
def office(organization, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(organization.pk)]
    user = User.objects.create_user("owner@d397.test", "safe-test-password-123")
    Membership.objects.create(organization=organization, user=user, role="owner")
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"]
    )
    companies = {}
    for key, name, code, reference in (
        ("alfa", "Alfa Comércio", "212", "748:111"),
        ("beta", "Beta Serviços", "213", "001:222"),
    ):
        company = ClientCompany.objects.create(
            organization=organization, name=name, dominio_code=code
        )
        account = FinancialAccount.objects.create(
            organization=organization,
            company=company,
            name=f"Banco {name}",
            account_reference=reference,
            ledger_code="8",
        )
        for code_value, label in CODES.items():
            LedgerAccount.objects.create(
                organization=organization, company=company, code=code_value, name=label
            )
        companies[key] = {"company": company, "account": account}
    return {"org": organization, "user": user, **companies}


def _month(office, key, bank, ledger, *, month, tag):
    """bank: (text, cents, day); ledger: (text, cents, contra, day). Then the Razão 'arrives'."""
    org, company, account = office["org"], office[key]["company"], office[key]["account"]
    bank_id, acct_id = account.account_reference.split(":")
    ofx = (
        f"OFXHEADER:100\n<OFX><BANKID>{bank_id}<ACCTID>{acct_id}<BANKTRANLIST>"
        + "".join(
            f"<STMTTRN><DTPOSTED>2026{month:02d}{day:02d}<TRNAMT>{cents / 100:.2f}"
            f"<FITID>{tag}-{i}<MEMO>{text}</STMTTRN>"
            for i, (text, cents, day) in enumerate(bank)
        )
        + "</BANKTRANLIST></OFX>"
    )
    source = None
    if bank:
        source, run, _ = create_source_file(
            organization=org,
            company=company,
            financial_account=account,
            filename=f"extrato-{tag}.ofx",
            content=ofx.encode(),
            origin="bank_statement",
        )
        process_run(str(run.pk))
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(LEDGER_COLUMNS)
    for i, (text, cents, contra, day) in enumerate(ledger):
        row = [f"{tag}-e{i}", "bank", f"2026-{month:02d}-{day:02d}", f"{text}"]
        side, other, direction = (
            ("debit", "credit", "inflow") if cents > 0 else ("credit", "debit", "outflow")
        )
        writer.writerow([*row, "8", side, abs(cents), direction, ""])
        writer.writerow([row[0], "other", *row[2:], contra, other, abs(cents), "", ""])
    _l, run, _ = create_source_file(
        organization=org,
        company=company,
        financial_account=account,
        filename=f"razao-{tag}.csv",
        content=output.getvalue().encode(),
        origin="accounting",
    )
    process_run(str(run.pk))
    if source is not None:
        auto_confirm_exact(source=source, month=date(2026, month, 1), actor=office["user"])
    return source


def _history(office, capture):
    """September teaches the rules of both companies (D-391), confirmed one by one."""
    with capture(execute=True):
        _month(
            office,
            "alfa",
            [(f"LIQUIDACAO BOLETO {900 + i}", -(10_000 + i), 1 + i) for i in range(5)],
            [(f"BOLETO {900 + i}", -(10_000 + i), "4", 1 + i) for i in range(5)],
            month=9,
            tag="a9",
        )
        _month(
            office,
            "beta",
            [("TARIFA PACOTE", -(500 + i), 3 + i) for i in range(3)],
            [("TARIFA", -(500 + i), "51", 3 + i) for i in range(3)],
            month=9,
            tag="b9",
        )


def _entry(text):
    movement = NormalizedMovement.objects.get(description=text)
    return movement.journal_entries.exclude(state=JournalEntry.State.INVALID).first()


def test_similar_window_free_records_and_every_company(office, django_capture_on_commit_callbacks):
    _history(office, django_capture_on_commit_callbacks)
    with django_capture_on_commit_callbacks(execute=True):
        _month(
            office,
            "alfa",
            [
                ("LIQUIDACAO BOLETO 701", -5_000, 10),  # Razão 2 days later -> similar
                ("LIQUIDACAO BOLETO 702", -6_000, 10),  # Razão 10 days later -> posted
                ("LIQUIDACAO BOLETO 703", -7_000, 14),  # exact pair -> confirmed
                ("LIQUIDACAO BOLETO 704", -7_000, 16),  # that record is used -> posted
            ],
            [
                ("BOLETO", -5_000, "4", 10 + 2),
                ("BOLETO", -6_000, "4", 10 + SIMILAR_DAYS + 5),
                ("BOLETO", -7_000, "4", 14),
            ],
            month=10,
            tag="a10",
        )
        _month(
            office,
            "beta",
            [("TARIFA PACOTE", -900, 8)],
            [("OUTRA COISA", 1_234, "9", 20)],
            month=10,
            tag="b10",
        )
    assert _entry("LIQUIDACAO BOLETO 701") is None
    assert _entry("LIQUIDACAO BOLETO 702").state == JournalEntry.State.APPROVED
    confirmed = NormalizedMovement.objects.get(description="LIQUIDACAO BOLETO 703")
    assert confirmed.reconciliations.filter(state="confirmed").exists()
    assert _entry("LIQUIDACAO BOLETO 703") is None
    assert _entry("LIQUIDACAO BOLETO 704").state == JournalEntry.State.APPROVED
    # The other company of the office got its own rule and posting, independently.
    beta = NormalizedMovement.objects.get(
        description="TARIFA PACOTE", occurred_on=date(2026, 10, 8)
    )
    entry = beta.journal_entries.get()
    assert entry.state == JournalEntry.State.APPROVED
    assert {line.account_code for line in entry.lines.all()} == {"51", "8"}
    # D-397 item 3: the bank text goes with the rule history.
    assert "LIQUIDACAO BOLETO 704" in _entry("LIQUIDACAO BOLETO 704").history
    # Running the whole office again changes nothing.
    before = JournalEntry.objects.exclude(state=JournalEntry.State.INVALID).count()
    results = run_for_organization(office["org"])
    assert len(results) == 2 and not any("error" in r for r in results)
    assert JournalEntry.objects.exclude(state=JournalEntry.State.INVALID).count() == before


def test_export_waits_for_a_newer_razao_and_withdraws_what_it_covers(
    office, django_capture_on_commit_callbacks
):
    _history(office, django_capture_on_commit_callbacks)
    with django_capture_on_commit_callbacks(execute=True):
        _month(
            office,
            "alfa",
            [("LIQUIDACAO BOLETO 702", -6_000, 10), ("LIQUIDACAO BOLETO 704", -7_000, 16)],
            [("OUTRA", 3_000, "9", 25)],
            month=10,
            tag="a10",
        )
    alfa = office["alfa"]
    period = dict(start=date(2026, 10, 1), end=date(2026, 10, 31))
    with pytest.raises(ReconciliationError, match="aguardam o Razão atualizado"):
        create_export(organization=office["org"], company=alfa["company"], **period)
    # The office then booked 702 by hand one day later; the new Razão shows it.
    with django_capture_on_commit_callbacks(execute=True):
        _month(office, "alfa", [], [("PAGTO BOLETO 702", -6_000, "4", 11)], month=10, tag="a10b")
        run_for_account(alfa["account"])
    assert JournalEntry.objects.filter(
        movement__description="LIQUIDACAO BOLETO 702", state=JournalEntry.State.INVALID
    ).exists()
    assert (
        AuditEvent.objects.filter(
            action=WITHDRAWN_ACTION, metadata__reason="parecido_com_o_razao"
        ).count()
        == 1
    )
    export = create_export(organization=office["org"], company=alfa["company"], **period)
    assert export.state == AccountingExport.State.READY
    [exported] = JournalEntry.objects.filter(pk__in=export.entry_ids)
    assert exported.movement.description == "LIQUIDACAO BOLETO 704"
    content = export.content.open("rb").read().decode("cp1252")
    assert "LIQUIDACAO BOLETO 704" in content and "702" not in content
    # Nothing is exported twice, and the other company still waits for its own Razão.
    with pytest.raises(ReconciliationError):
        create_export(organization=office["org"], company=alfa["company"], **period)


def test_entries_approved_by_a_person_are_not_held(office, django_capture_on_commit_callbacks):
    from apps.hub.double_booking import check_export

    _history(office, django_capture_on_commit_callbacks)
    with django_capture_on_commit_callbacks(execute=True):
        _month(
            office,
            "alfa",
            [("LIQUIDACAO BOLETO 702", -6_000, 10)],
            [("X", 1, "9", 25)],
            month=10,
            tag="a10",
        )
    from apps.hub.reconciliation_service import (
        approve_journal_entry,
        create_journal_entry_from_movement,
    )

    automatic = _entry("LIQUIDACAO BOLETO 702")
    JournalEntry.objects.filter(pk=automatic.pk).update(state=JournalEntry.State.INVALID)
    manual = create_journal_entry_from_movement(movement=automatic.movement, actor=office["user"])
    manual = approve_journal_entry(entry=manual, actor=office["user"])
    assert manual.state == JournalEntry.State.APPROVED
    check = check_export(
        organization=office["org"],
        company=office["alfa"]["company"],
        start=date(2026, 10, 1),
        end=date(2026, 10, 31),
        withdraw=False,
    )
    assert not check.held_ids


def test_offices_outside_direct_use_are_unchanged(office, settings):
    from apps.hub.double_booking import check_export

    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = []
    check = check_export(
        organization=office["org"],
        company=office["alfa"]["company"],
        start=date(2026, 10, 1),
        end=date(2026, 10, 31),
        withdraw=True,
    )
    assert not check.held and not check.withdrawn


def test_statement_complement():
    assert statement_complement("LIQUIDACAO BOLETO", "LIQUIDACAO BOLETO 777") == (
        "LIQUIDACAO BOLETO · LIQUIDACAO BOLETO 777"
    )
    assert statement_complement("Tarifa", "tarifa") == "Tarifa"
    assert statement_complement("", "PIX JOSE") == "PIX JOSE"
    assert len(statement_complement("A" * 400, "B" * 400)) == 500


def test_ofx_windows_1252_keeps_accents():
    from apps.hub.reconciliation import parse_ofx

    content = (
        "OFXHEADER:100\nCHARSET:1252\n<OFX><BANKID>748<ACCTID>1<BANKTRANLIST><STMTTRN>"
        "<DTPOSTED>20261001<TRNAMT>-1.00<FITID>a<MEMO>MANUTENÇÃO CONTA</STMTTRN>"
        "</BANKTRANLIST></OFX>"
    ).encode("cp1252")
    [row] = parse_ofx(content).transactions
    assert row.description == "MANUTENÇÃO CONTA"
    utf8 = content.decode("cp1252").encode("utf-8")
    assert parse_ofx(utf8).transactions[0].description == "MANUTENÇÃO CONTA"


def test_ofx_of_another_company_is_refused(office):
    from apps.hub.account_auto_link import (
        AutoLinkError,
        link_statement_only,
        refuse_foreign_account,
    )

    third = ClientCompany.objects.create(organization=office["org"], name="Gama", dominio_code="55")
    with pytest.raises(AutoLinkError, match="Alfa Comércio"):
        refuse_foreign_account(office["org"], third, "748:111")
    refuse_foreign_account(office["org"], office["alfa"]["company"], "748:111")  # its own
    ofx = (
        b"OFXHEADER:100\n<OFX><BANKMSGSRSV1><STMTTRNRS><STMTRS><BANKACCTFROM><BANKID>748"
        b"<ACCTID>111<ACCTTYPE>CHECKING</BANKACCTFROM><BANKTRANLIST>"
        b"<STMTTRN><DTPOSTED>20261001<TRNAMT>-1.00<FITID>z<MEMO>X</STMTTRN>"
        b"</BANKTRANLIST></STMTRS></STMTTRNRS></BANKMSGSRSV1></OFX>"
    )
    with pytest.raises(AutoLinkError, match="Alfa Comércio"):
        link_statement_only(office=office["org"], company=third, content=ofx, actor=office["user"])
    assert not FinancialAccount.objects.filter(company=third).exists()


def test_statement_only_option_skips_companies_already_linked_to_the_razao(office):
    from apps.hub.account_auto_link import statement_only_options

    third = ClientCompany.objects.create(organization=office["org"], name="Gama", dominio_code="55")
    options = statement_only_options(ClientCompany.objects.filter(organization=office["org"]), [])
    assert [o["company_id"] for o in options] == [str(third.pk)]


def test_automation_runs_once_per_account_at_a_time(office, monkeypatch):
    from celery.exceptions import Retry
    from django.core.cache import cache

    import apps.hub.depara_ledger as depara_ledger
    from apps.hub.tasks import refresh_account_automation

    calls = []
    monkeypatch.setattr(depara_ledger, "refresh_now", lambda pk: calls.append(pk))
    account_id = str(office["alfa"]["account"].pk)
    cache.add(f"hub:account-automation:{account_id}", "1", timeout=60)
    with pytest.raises(Retry):
        refresh_account_automation.apply(args=[account_id], throw=True)
    assert calls == []
    cache.delete(f"hub:account-automation:{account_id}")
    refresh_account_automation.apply(args=[account_id], throw=True)
    assert calls == [account_id]


def test_commands_refuse_an_office_that_is_not_a_uuid():
    for command in ("uso_direto", "titulos_auto"):
        with pytest.raises(CommandError):
            call_command(command, "--organization", "CONTAD")
