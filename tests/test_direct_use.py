"""D-393: an office in direct use sees and uses the data without human review steps."""

from __future__ import annotations

import csv
import io
import json
from datetime import date

import pytest
from django.core.management import call_command
from django.urls import reverse
from tests.test_depara_ledger import BASE, _load, setup  # noqa: F401  (fixture reuse)

from apps.audit.models import AuditEvent
from apps.hub.accounting_import import export_allowed, export_homologated
from apps.hub.auto_confirm import auto_confirm_exact
from apps.hub.depara_ledger import ledger_rules
from apps.hub.direct_use import POSTED_ACTION, direct_use_enabled
from apps.hub.ledger_import import LEDGER_COLUMNS
from apps.hub.models import (
    AccountingExport,
    JournalEntry,
    NormalizedMovement,
    ReconciliationRule,
)
from apps.hub.reconciliation_service import (
    ReconciliationError,
    create_export,
    create_source_file,
    get_accounting_export_adapter,
    process_run,
)
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db
VERSION = get_accounting_export_adapter("dominio").version


@pytest.fixture
def enabled(setup, settings):  # noqa: F811
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(setup["org"].pk)]
    return setup


def _october(setup, bank_rows, ledger_rows):  # noqa: F811
    """bank_rows: (text, cents); ledger_rows: (text, cents, contra). Same day, Razão arrives."""
    org, company, account = setup["org"], setup["company"], setup["account"]
    ofx = (
        "OFXHEADER:100\n<OFX><BANKID>748<ACCTID>123<BANKTRANLIST>"
        + "".join(
            f"<STMTTRN><DTPOSTED>20261015<TRNAMT>{cents / 100:.2f}"
            f"<FITID>out-{i}<MEMO>{text}</STMTTRN>"
            for i, (text, cents) in enumerate(bank_rows)
        )
        + "</BANKTRANLIST></OFX>"
    )
    source, run, _ = create_source_file(
        organization=org, company=company, financial_account=account,
        filename="extrato-out.ofx", content=ofx.encode(), origin="bank_statement",
    )
    process_run(str(run.pk))
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(LEDGER_COLUMNS)
    for i, (text, cents, contra) in enumerate(ledger_rows):
        common = [f"out-entry-{i}", "bank", "2026-10-15", f"Razão {text}"]
        amount = abs(cents)
        side, other, direction = (
            ("debit", "credit", "inflow") if cents > 0 else ("credit", "debit", "outflow")
        )
        writer.writerow([*common, "1.1", side, amount, direction, ""])
        writer.writerow([common[0], "other", *common[2:], contra, other, amount, "", ""])
    _ledger, run, _ = create_source_file(
        organization=org, company=company, financial_account=account,
        filename="razao-out.csv", content=output.getvalue().encode(), origin="accounting",
    )
    process_run(str(run.pk))
    auto_confirm_exact(source=source, month=date(2026, 10, 1), actor=setup["user"])
    return source


OCTOBER_BANK = [
    ("LIQUIDACAO BOLETO 777", -4321),  # rule matches, absent from the Razão -> posted
    ("LIQUIDACAO BOLETO 778", -4322),  # booked in the Razão -> confirmed, never posted
    ("LIQUIDACAO BOLETO 780", -555),  # two equal bank lines, one Razão record -> ambiguous
    ("LIQUIDACAO BOLETO 781", -555),
    ("DEPOSITO QUALQUER", 9000),  # no rule -> stays for the office, not posted
]
OCTOBER_LEDGER = [("LIQUIDACAO BOLETO 778", -4322, "4.1"), ("BOLETO", -555, "4.1")]


def test_disabled_office_keeps_drafts_and_posts_nothing(setup, django_capture_on_commit_callbacks):  # noqa: F811
    with django_capture_on_commit_callbacks(execute=True):
        _load(setup, BASE)
        _october(setup, OCTOBER_BANK, OCTOBER_LEDGER)
    assert not direct_use_enabled(setup["org"])
    assert {rule.state for rule, _ in ledger_rules(setup["account"])} == {"draft"}
    assert not JournalEntry.objects.filter(organization=setup["org"], purpose="record").exists()


def test_rules_activate_without_review_and_only_missing_movements_are_posted(
    enabled, django_capture_on_commit_callbacks
):
    with django_capture_on_commit_callbacks(execute=True):
        _load(enabled, BASE)
    rules = ledger_rules(enabled["account"])
    assert {rule.state for rule, _ in rules} == {"active"}
    assert all(rule.actions["require_review"] is False for rule, _ in rules)
    # September is fully in the Razão: nothing to post.
    assert not JournalEntry.objects.filter(organization=enabled["org"], purpose="record").exists()

    with django_capture_on_commit_callbacks(execute=True):
        _october(enabled, OCTOBER_BANK, OCTOBER_LEDGER)
    entries = list(
        JournalEntry.objects.filter(organization=enabled["org"], purpose="record").select_related(
            "movement"
        )
    )
    assert [entry.movement.description for entry in entries] == ["LIQUIDACAO BOLETO 777"]
    assert entries[0].state == JournalEntry.State.APPROVED
    assert {(line.side, line.account_code) for line in entries[0].lines.all()} == {
        ("debit", "4.1"),
        ("credit", "1.1"),
    }
    assert AuditEvent.objects.filter(action=POSTED_ACTION, metadata__decision="D-393").count() == 1
    deposit = NormalizedMovement.objects.get(description="DEPOSITO QUALQUER")
    assert deposit.journal_entries.count() == 0


def test_running_again_never_duplicates(enabled, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        _load(enabled, BASE)
        _october(enabled, OCTOBER_BANK, OCTOBER_LEDGER)
    output = io.StringIO()
    call_command("uso_direto", organization=str(enabled["org"].pk), apply=True, stdout=output)
    totals = json.loads(output.getvalue())
    assert totals["posted"] == 0 and totals["errors"] == 0
    assert JournalEntry.objects.filter(organization=enabled["org"], purpose="record").count() == 1


def test_person_disabled_rule_is_never_reactivated(enabled, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        _load(enabled, BASE)
    rule, _ = ledger_rules(enabled["account"])[0]
    from apps.hub.depara_rule_activation import set_reconciliation_rule_state

    set_reconciliation_rule_state(rule=rule, actor=enabled["user"], expected_state="active")
    call_command(
        "uso_direto", organization=str(enabled["org"].pk), apply=True, stdout=io.StringIO()
    )
    rule.refresh_from_db()
    assert rule.state == ReconciliationRule.State.DISABLED


def test_export_is_allowed_only_for_the_listed_office(
    enabled, django_capture_on_commit_callbacks, monkeypatch
):
    import dataclasses

    import apps.hub.reconciliation_service as service

    # Synthetic chart codes ("4.1") are not Domínio reduced codes; the layout itself is
    # covered by test_dominio_lote19. Here only the gate and the entry bookkeeping matter.
    adapter = service.ACCOUNTING_EXPORT_ADAPTERS["dominio"]
    monkeypatch.setitem(
        service.ACCOUNTING_EXPORT_ADAPTERS,
        "dominio",
        dataclasses.replace(adapter, render=lambda entries: b"lote\r\n"),
    )
    with django_capture_on_commit_callbacks(execute=True):
        _load(enabled, BASE)
        _october(enabled, OCTOBER_BANK, OCTOBER_LEDGER)
    org = enabled["org"]
    enabled["company"].dominio_code = "212"
    enabled["company"].save(update_fields=["dominio_code"])
    assert not export_homologated(org, "dominio", VERSION)  # no fake homologation
    assert export_allowed(org, "dominio", VERSION)
    assert not export_allowed(org, "dominio", "outra-versao")
    assert not export_allowed(org, "siescon", VERSION)
    # D-408: the Razão already read is enough; no newer Razão is required (was D-397).
    export = create_export(
        organization=org,
        company=enabled["company"],
        start=date(2026, 10, 1),
        end=date(2026, 10, 31),
        actor=enabled["user"],
    )
    assert export.state == AccountingExport.State.READY
    assert len(export.entry_ids) == 1
    assert JournalEntry.objects.get(pk=export.entry_ids[0]).state == JournalEntry.State.EXPORTED
    # A demo or unlisted office never gets it.
    other = Organization.objects.create(name="Outro", slug="outro")
    assert not export_allowed(other, "dominio", VERSION)
    org.is_demo = True
    org.save(update_fields=["is_demo"])
    assert not direct_use_enabled(org)


def test_unlisted_office_export_stays_blocked(setup):  # noqa: F811
    with pytest.raises(ReconciliationError, match="bloqueada"):
        create_export(
            organization=setup["org"],
            company=setup["company"],
            start=date(2026, 10, 1),
            end=date(2026, 10, 31),
            actor=setup["user"],
        )


def test_export_panel_shows_the_form_in_direct_use(enabled):
    response = enabled["client"].get(reverse("hub:reconciliation"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Exportação Domínio bloqueada" not in content
    assert "Validar e gerar arquivo" in content


def _fresh_razao(office, rows=(("OUTRO LANCAMENTO", 777, "3.1"),), day="2026-10-28"):
    """A newer Razão of the account arrives (any content), as after the office books more."""
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(LEDGER_COLUMNS)
    for i, (text, cents, contra) in enumerate(rows):
        key = f"fresh-{day}-{i}"
        side, other, direction = (
            ("debit", "credit", "inflow") if cents > 0 else ("credit", "debit", "outflow")
        )
        writer.writerow([key, "bank", day, f"Razão {text}", "1.1", side, abs(cents), direction, ""])
        writer.writerow([key, "other", day, f"Razão {text}", contra, other, abs(cents), "", ""])
    _source, run, _ = create_source_file(
        organization=office["org"], company=office["company"],
        financial_account=office["account"], filename=f"razao-{day}.csv",
        content=output.getvalue().encode(), origin="accounting",
    )
    process_run(str(run.pk))


def _send_statement(client, company, value, content):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return client.post(
        reverse("hub:reconciliation-upload"),
        {
            "purpose": "general",
            "company": str(company.pk),
            "financial_account": value,
            "origin": "bank_statement",
            "files": [SimpleUploadedFile("extrato.ofx", content, "application/x-ofx")],
        },
    )


def test_company_without_bank_in_chart_imports_and_views_the_statement(
    enabled, django_capture_on_commit_callbacks
):
    from apps.hub.models import ClientCompany, FinancialAccount, ReconciliationSourceFile
    from test_discovery_ofx_prefill import synthetic_ofx

    company = ClientCompany.objects.create(
        organization=enabled["org"], name="Sem banco no plano", dominio_code="55"
    )
    html = enabled["client"].get(reverse("hub:reconciliation")).content.decode()
    assert f'value="extrato:{company.pk}"' in html
    assert "Conta do extrato, lida do OFX (sem Razão)" in html
    with django_capture_on_commit_callbacks(execute=True):
        response = _send_statement(
            enabled["client"], company, f"extrato:{company.pk}", synthetic_ofx(rows=3)
        )
    assert response.status_code == 302
    assert response["Location"].endswith("#processamentos")
    account = FinancialAccount.objects.get(company=company)
    assert account.account_reference == "748:0101:00012345-6"
    assert account.ledger_code == ""
    assert not hasattr(account, "ledger_mapping")
    source = ReconciliationSourceFile.objects.get(company=company)
    assert source.financial_account_id == account.pk
    assert source.movements.count() == 3
    review = enabled["client"].get(
        reverse("hub:reconciliation-source-review", args=[source.pk])
        + "?start=2026-09-01&end=2026-09-30"
    )
    assert review.status_code == 200
    portfolio = enabled["client"].get(
        reverse("hub:reconciliation-portfolio") + f"?month=2026-09&company={company.pk}"
    ).content.decode()
    assert "Abrir conferência" in portfolio
    # The same OFX again reuses the account instead of creating another.
    with django_capture_on_commit_callbacks(execute=True):
        _send_statement(enabled["client"], company, str(account.pk), synthetic_ofx(rows=4))
    assert FinancialAccount.objects.filter(company=company).count() == 1


def test_statement_only_option_is_absent_outside_direct_use(setup):  # noqa: F811
    from apps.hub.models import ClientCompany

    company = ClientCompany.objects.create(
        organization=setup["org"], name="Sem banco no plano", dominio_code="55"
    )
    html = setup["client"].get(reverse("hub:reconciliation")).content.decode()
    assert f'value="extrato:{company.pk}"' not in html
    response = _send_statement(
        setup["client"], company, f"extrato:{company.pk}", b"OFXHEADER:100"
    )
    assert response.status_code == 400
    assert not company.financial_accounts.exists()
