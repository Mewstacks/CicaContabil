"""D-391: DE-PARA suggestions learned from the contra accounts booked in the Razão."""

from __future__ import annotations

import csv
import io
from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.auto_confirm import auto_confirm_exact
from apps.hub.depara_ledger import (
    SUGGESTED_ACTION,
    create_drafts,
    evaluate,
    ledger_rules,
    propose,
)
from apps.hub.ledger_import import LEDGER_COLUMNS
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    LedgerAccount,
    NormalizedMovement,
    ProductModule,
    ReconciliationRule,
)
from apps.hub.reconciliation_service import create_source_file, process_run
from apps.organizations.models import Membership
from apps.platform.models import TenantContract

pytestmark = pytest.mark.django_db
CODES = ("1.1", "3.1", "4.1", "5.1", "5.2", "6.1")


@pytest.fixture
def setup(organization, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    user = User.objects.create_user("owner@depara.test", "safe-test-password-123")
    Membership.objects.create(organization=organization, user=user, role="owner")
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"]
    )
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa", dominio_code="T1"
    )
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Banco",
        account_reference="748:123",
        ledger_code="1.1",
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.pk)
    session.save()
    return {
        "org": organization,
        "user": user,
        "company": company,
        "account": account,
        "client": client,
    }


def _load(setup, rows, *, month="09", tag="a"):
    """rows: (description, signed cents, contra code). Bank OFX + Razão CSV, then confirm."""
    org, company, account = setup["org"], setup["company"], setup["account"]
    ofx = (
        "OFXHEADER:100\n<OFX><BANKID>748<ACCTID>123<BANKTRANLIST>"
        + "".join(
            f"<STMTTRN><DTPOSTED>2026{month}12<TRNAMT>{cents / 100:.2f}"
            f"<FITID>{tag}-{i}<MEMO>{text}</STMTTRN>"
            for i, (text, cents, _contra) in enumerate(rows)
        )
        + "</BANKTRANLIST></OFX>"
    )
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
    for i, (text, cents, contra) in enumerate(rows):
        common = [f"{tag}-entry-{i}", "bank", f"2026-{month}-12", f"Razão {text}"]
        amount = abs(cents)
        if cents > 0:
            writer.writerow([*common, "1.1", "debit", amount, "inflow", ""])
            writer.writerow([common[0], "other", *common[2:], contra, "credit", amount, "", ""])
        else:
            writer.writerow([*common, "1.1", "credit", amount, "outflow", ""])
            writer.writerow([common[0], "other", *common[2:], contra, "debit", amount, "", ""])
    catalogue = [
        LedgerAccount.objects.get_or_create(
            organization=org, company=company, code=code, defaults={"name": f"Conta {code}"}
        )[0]
        for code in CODES
    ]
    assert catalogue
    _ledger, run, _ = create_source_file(
        organization=org,
        company=company,
        financial_account=account,
        filename=f"razao-{tag}.csv",
        content=output.getvalue().encode(),
        origin="accounting",
    )
    process_run(str(run.pk))
    confirmed = auto_confirm_exact(
        source=source, month=date(2026, int(month), 1), actor=setup["user"]
    )
    assert confirmed == len(rows)
    return source


BASE = [
    *[(f"LIQUIDACAO BOLETO {900 + i}", -(1000 + i), "4.1") for i in range(5)],
    ("Recebimento Pix José 11", 2000, "3.1"),
    ("Recebimento Pix José 22", 2001, "3.1"),
    ("TARIFA BANCARIA", -300, "5.1"),
    ("TARIFA BANCARIA", -301, "5.2"),
]


def test_propose_learns_only_unanimous_repeated_patterns(setup):
    _load(setup, BASE)
    result = propose(setup["account"])
    by_label = {s.label: s for s in result["suggestions"]}
    assert set(by_label) == {"LIQUIDACAO BOLETO", "RECEBIMENTO PIX JOSE"}
    boleto, pix = by_label["LIQUIDACAO BOLETO"], by_label["RECEBIMENTO PIX JOSE"]
    assert (boleto.level, boleto.debit, boleto.credit, boleto.support) == (
        "inicio",
        "4.1",
        "1.1",
        5,
    )
    assert (pix.level, pix.debit, pix.credit, pix.support) == ("palavras", "1.1", "3.1", 2)
    assert result["rejected"].get("divergente", 0) >= 1  # TARIFA BANCARIA → 5.1 and 5.2
    assert result["covered"] == 7 and result["examples"] == 9


def test_pattern_that_would_hit_another_contra_account_is_refused(setup):
    _load(setup, [*BASE, ("LIQUIDACAO BOLETO ESPECIAL 7", -999, "6.1")])
    labels = {s.label for s in propose(setup["account"])["suggestions"]}
    assert "LIQUIDACAO BOLETO" not in labels
    assert propose(setup["account"])["rejected"].get("casaria_outra_conta", 0) >= 1


def test_drafts_review_activation_and_classification_of_a_new_statement(setup):
    _load(setup, BASE)
    created = create_drafts(setup["account"])
    assert created["created"] == 2 and create_drafts(setup["account"])["existing"] == 2
    rules = ledger_rules(setup["account"])
    assert {rule.state for rule, _ in rules} == {"draft"}
    rule, evidence = next((r, e) for r, e in rules if e["label"] == "LIQUIDACAO BOLETO")
    assert rule.actions["require_review"] is True and evidence["support"] == 5
    assert AuditEvent.objects.get(action=SUGGESTED_ACTION, target_id=str(rule.pk)).actor is None

    url = reverse("hub:reconciliation-depara-ledger", args=[setup["account"].pk])
    page = setup["client"].get(url).content.decode()
    assert "Histórico começa com “LIQUIDACAO BOLETO”" in page and "Conta 4.1" in page
    assert "A revisar" in page
    response = setup["client"].post(
        url, {"rule_id": str(rule.pk), "expected_state": "draft"}, follow=True
    )
    assert "Regra ativada." in response.content.decode()
    rule.refresh_from_db()
    assert rule.state == "active"

    ofx = (
        "OFXHEADER:100\n<OFX><BANKID>748<ACCTID>123<BANKTRANLIST>"
        "<STMTTRN><DTPOSTED>20261005<TRNAMT>-55.00<FITID>novo-1<MEMO>LIQUIDACAO BOLETO 777"
        "</STMTTRN></BANKTRANLIST></OFX>"
    )
    source, run, _ = create_source_file(
        organization=setup["org"],
        company=setup["company"],
        financial_account=setup["account"],
        filename="outubro.ofx",
        content=ofx.encode(),
        origin="bank_statement",
    )
    process_run(str(run.pk))
    movement = NormalizedMovement.objects.get(source_file=source)
    assert movement.classification_source == "rule"
    assert (movement.debit_account_code, movement.credit_account_code) == ("4.1", "1.1")
    assert movement.review_state == "pending"


def test_discard_disables_the_draft(setup):
    _load(setup, BASE)
    create_drafts(setup["account"])
    rule, _ = ledger_rules(setup["account"])[0]
    url = reverse("hub:reconciliation-depara-ledger", args=[setup["account"].pk])
    response = setup["client"].post(
        url, {"rule_id": str(rule.pk), "action": "discard"}, follow=True
    )
    assert "Sugestão descartada." in response.content.decode()
    rule.refresh_from_db()
    assert rule.state == ReconciliationRule.State.DISABLED


def test_evaluate_measures_out_of_sample_month(setup):
    _load(setup, BASE)
    create_drafts(setup["account"])
    _load(
        setup,
        [
            ("LIQUIDACAO BOLETO 501", -5001, "4.1"),
            ("LIQUIDACAO BOLETO 502", -5002, "4.1"),
            ("Recebimento Pix José 33", 6000, "3.1"),
            ("DEPOSITO 1", 7000, "3.1"),
        ],
        month="10",
        tag="b",
    )
    report = evaluate(setup["account"], month="2026-10")
    assert (report["correct"], report["wrong"], report["uncovered"]) == (3, 0, 1)
    assert report["precision_percent"] == 100
    same_month = evaluate(setup["account"], month="2026-09")
    assert same_month["correct"] == 0 and same_month["uncovered"] == 9


def test_review_page_requires_manager_permission(organization, settings, tmp_path, setup):
    _load(setup, BASE)
    create_drafts(setup["account"])
    viewer = User.objects.create_user("auditor@depara.test", "safe-test-password-123")
    Membership.objects.create(organization=organization, user=viewer, role="auditor")
    client = Client()
    client.force_login(viewer)
    session = client.session
    session["hub_organization_id"] = str(organization.pk)
    session.save()
    rule, _ = ledger_rules(setup["account"])[0]
    url = reverse("hub:reconciliation-depara-ledger", args=[setup["account"].pk])
    response = client.post(url, {"rule_id": str(rule.pk), "expected_state": "draft"})
    assert response.status_code in {403, 404}
    rule.refresh_from_db()
    assert rule.state == "draft"


def test_confirmations_create_suggestions_automatically(setup, django_capture_on_commit_callbacks):
    with django_capture_on_commit_callbacks(execute=True):
        _load(setup, BASE)
    labels = {evidence["label"] for _rule, evidence in ledger_rules(setup["account"])}
    assert labels == {"LIQUIDACAO BOLETO", "RECEBIMENTO PIX JOSE"}
    assert {rule.state for rule, _ in ledger_rules(setup["account"])} == {"draft"}


def test_draft_without_current_evidence_is_retired_but_active_rules_stay(
    setup, django_capture_on_commit_callbacks
):
    _load(setup, BASE)
    create_drafts(setup["account"])
    rules = dict((e["label"], r) for r, e in ledger_rules(setup["account"]))
    pix = rules["RECEBIMENTO PIX JOSE"]
    pix.state = "active"
    pix.save(update_fields=["state"])
    with django_capture_on_commit_callbacks(execute=True):
        _load(
            setup,
            [
                ("LIQUIDACAO BOLETO 1", -8001, "6.1"),
                ("Recebimento Pix José 9", 8002, "5.1"),
            ],
            month="10",
            tag="c",
        )
    boleto = rules["LIQUIDACAO BOLETO"]
    boleto.refresh_from_db()
    pix.refresh_from_db()
    assert boleto.state == ReconciliationRule.State.DISABLED
    assert pix.state == "active"  # a person activated it; the routine never changes it
    assert AuditEvent.objects.filter(
        target_id=str(boleto.pk), metadata__reason="sem_evidencia_atual"
    ).exists()


def test_refresh_failure_never_breaks_the_confirmation(
    setup, django_capture_on_commit_callbacks, monkeypatch
):
    import apps.hub.depara_ledger as module

    def boom(account):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(module, "create_drafts", boom)
    with django_capture_on_commit_callbacks(execute=True):
        source = _load(setup, BASE)
    assert NormalizedMovement.objects.filter(
        source_file=source, reconciliations__state="confirmed"
    ).count() == len(BASE)
    assert not ledger_rules(setup["account"])


def test_create_all_covers_every_active_account(setup):
    import io as _io
    import json as _json

    from django.core.management import call_command

    _load(setup, BASE)
    other_company = ClientCompany.objects.create(
        organization=setup["org"], name="Outra", dominio_code="T2"
    )
    FinancialAccount.objects.create(
        organization=setup["org"],
        company=other_company,
        name="Outro banco",
        account_reference="001:999",
        ledger_code="1.1",
    )
    output = _io.StringIO()
    call_command("depara_razao", "create-all", organization=str(setup["org"].pk), stdout=output)
    totals = _json.loads(output.getvalue())
    assert totals == {"accounts": 2, "created": 2, "retired": 0, "failed": 0}
