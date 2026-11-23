"""D-397: AI demotion, titles and new-account trigger (review of 23/11/2026, all companies)."""

from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from tests.test_depara_ai_auto import GOOD, _run, ai_on  # noqa: F401
from tests.test_depara_ledger import setup  # noqa: F401
from tests.test_title_auto import _rows

import apps.hub.depara_ai_auto as ai
from apps.audit.services import record_event
from apps.hub.direct_use import run_for_account
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    JournalEntry,
    NormalizedMovement,
    ReconciliationRule,
)
from apps.hub.reconciliation_service import create_source_file, process_run
from apps.hub.title_auto import ACTION, _decision
from apps.hub.title_requests import _direct_use_detail

pytestmark = pytest.mark.django_db


def test_ai_rules_go_back_to_draft_when_the_new_measurement_fails(
    ai_on, monkeypatch, django_capture_on_commit_callbacks  # noqa: F811
):
    _run(ai_on, monkeypatch, GOOD, django_capture_on_commit_callbacks)
    [rule] = ReconciliationRule.objects.filter(name__startswith=ai.RULE_PREFIX)
    deposit = NormalizedMovement.objects.get(description="DEPOSITO QUALQUER")
    entry = deposit.journal_entries.get()
    assert rule.state == "active" and entry.state == JournalEntry.State.APPROVED
    # A new pattern arrives and the new blind measurement is below 90%.
    ofx = (
        "OFXHEADER:100\n<OFX><BANKID>748<ACCTID>123<BANKTRANLIST><STMTTRN><DTPOSTED>20261020"
        "<TRNAMT>-15.00<FITID>new-1<MEMO>SAQUE CAIXA ELETRONICO</STMTTRN></BANKTRANLIST></OFX>"
    )
    _source, run, _ = create_source_file(
        organization=ai_on["org"], company=ai_on["company"], financial_account=ai_on["account"],
        filename="extrato-novo.ofx", content=ofx.encode(), origin="bank_statement",
    )
    process_run(str(run.pk))
    failing = {"measured": 12, "correct": 6, "precision": 50}
    monkeypatch.setattr(ai, "measure", lambda *a, **k: failing)
    run_for_account(ai_on["account"])
    rule.refresh_from_db()
    entry.refresh_from_db()
    assert rule.state == "draft" and rule.actions["require_review"] is True
    assert entry.state == JournalEntry.State.INVALID


def test_negative_net_value_never_falls_back_to_gross():
    spec, payments = _rows("entradas", [("2026-09-10", 1, 1, "10.00")])
    for net in ("-100.00", "10.001", "abc"):
        part = {"vlor_entp": net, "vbru_entp": "100.00"}
        assert _decision("entradas", spec, part, "r", payments, "2026-09-30") is None
    zero = {"vlor_entp": "0.00", "vbru_entp": "100.00"}  # D-394: gross only if net is zero/empty
    assert _decision("entradas", spec, zero, "r", payments, "2026-09-30")["principal_field"] == (
        "vbru_entp"
    )


def test_capture_message_says_what_really_happened(organization, settings):
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(organization.pk)]
    company = ClientCompany.objects.create(organization=organization, name="Sem conta")
    job = SimpleNamespace(pk=uuid4())
    assert "importe o extrato OFX" in _direct_use_detail(job, company)
    FinancialAccount.objects.create(
        organization=organization, company=company, name="Banco", account_reference="1:2"
    )
    assert "em andamento" in _direct_use_detail(job, company)
    record_event(
        action=ACTION, actor=None, organization=organization, target=company,
        metadata={"capture_id": str(job.pk)},
    )
    assert "interpretados automaticamente" in _direct_use_detail(job, company)


def test_new_bank_account_by_any_path_triggers_title_reading(
    organization, settings, monkeypatch, django_capture_on_commit_callbacks
):
    import apps.hub.title_auto as title_auto

    calls = []
    monkeypatch.setattr(title_auto, "schedule_company", lambda pk: calls.append(pk))
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    FinancialAccount.objects.create(
        organization=organization, company=company, name="Fora", account_reference="1:1"
    )
    assert calls == []  # office outside direct use
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(organization.pk)]
    account = FinancialAccount.objects.create(
        organization=organization, company=company, name="Dentro", account_reference="1:3"
    )
    assert calls == [company.pk]
    account.name = "Renomeada"
    account.save()
    assert calls == [company.pk]  # only creation triggers
