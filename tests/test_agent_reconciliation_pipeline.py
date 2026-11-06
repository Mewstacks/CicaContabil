"""Exercise the native agent's HTTP intake through reconciliation (synthetic only)."""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import date

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import (
    AccountingEntry,
    ClientCompany,
    DominioBankEntry,
    FinancialAccount,
    IndependentLedgerRecord,
    JournalEntry,
    LedgerAccount,
    MovementReconciliation,
    ReconciliationMatch,
)
from apps.hub.reconciliation import confirm_reconciliation_match, import_ofx
from apps.hub.reconciliation_report import build_source_report, render_conference_csv
from apps.hub.reconciliation_service import create_source_file, process_run
from apps.intelligence.agent_scope import build_sync_scope
from apps.intelligence.agents import issue_enrollment, redeem_enrollment, revoke_agent
from apps.intelligence.models import EdgeAgent
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


@pytest.fixture
def agent(organization):
    company = ClientCompany.objects.create(
        organization=organization, name="Teste", dominio_code="001"
    )
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Banco sintético",
        account_reference="001:123",
        ledger_code="1.1",
    )
    scope = build_sync_scope(
        account=account, start=date(2026, 9, 1), end=date(2026, 9, 30), statement_ids=["1"]
    )
    enrollment = issue_enrollment(organization=organization, sync_scope=scope)
    return redeem_enrollment(
        code=enrollment.code, label="Windows sintético", fingerprint="test", allow_scoped=True
    )


def post_page(agent, rows, *, secret=None):
    body = json.dumps({"rows": rows, "scope_revision": agent.sync_scope["revision"]}).encode()
    timestamp = str(int(timezone.now().timestamp()))
    signature = hmac.new(
        (secret or agent.shared_secret).encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return Client().post(
        reverse("agent-v2-dominio-bank-entries"),
        data=body,
        content_type="application/json",
        headers={
            "X-Hub-Agent-Protocol": "scoped-v1",
            "X-Hub-Agent-ID": agent.agent_id,
            "X-Hub-Agent-Timestamp": timestamp,
            "X-Hub-Agent-Signature": signature,
        },
        secure=True,
    )


def bank_row(index=0, *, code="001"):
    return {
        "source_id": f"{code}|1|{index}",
        "company_code": code,
        "occurred_on": "2026-09-12",
        "description": "Extrato sintético, não Razão",
        "amount": "100.00",
        "direction": "C",
        "is_linked": False,
        "account_reference": "001:123",
    }


def test_native_pages_retry_and_link_updates_remain_scoped_bank_mirrors(agent, organization):
    company = ClientCompany.objects.get(organization=organization, dominio_code="001")
    outsider = Organization.objects.create(name="Outro escritório", slug="outside-agent-test")
    ClientCompany.objects.create(organization=outsider, name="Outra", dominio_code="001")
    first_page = [bank_row(i) for i in range(500)]
    assert post_page(agent, first_page).json() == {"created": 500, "updated": 0, "ignored": 0}
    assert post_page(agent, [bank_row(500)]).json()["created"] == 1
    assert post_page(agent, first_page).json() == {"created": 0, "updated": 0, "ignored": 0}
    assert post_page(agent, [{**bank_row(), "is_linked": True}]).json()["updated"] == 1
    assert DominioBankEntry.objects.filter(company=company).count() == 501
    assert AccountingEntry.objects.filter(company=company).count() == 501
    assert not DominioBankEntry.objects.filter(organization=outsider).exists()
    assert not AccountingEntry.objects.filter(organization=outsider).exists()
    assert DominioBankEntry.objects.get(source_id="001|1|0").is_linked
    assert not IndependentLedgerRecord.objects.exists()
    assert not JournalEntry.objects.exists()


@pytest.mark.parametrize("rows", [[bank_row()] * 501, ["invalid"], {}, None])
def test_invalid_native_bank_page_is_rejected_before_persistence(agent, rows):
    assert post_page(agent, rows).status_code == 400
    assert not DominioBankEntry.objects.exists()
    assert not AccountingEntry.objects.exists()


def test_bad_signature_revocation_and_missing_mtls_block_bank_intake(agent):
    assert post_page(agent, [bank_row()], secret="wrong-test-secret").status_code == 401
    with override_settings(EDGE_AGENT_MTLS_REQUIRED=True):
        assert post_page(agent, [bank_row()]).status_code == 401
    revoke_agent(agent=EdgeAgent.objects.get(pk=agent.agent_id))
    assert post_page(agent, [bank_row()]).status_code == 401
    assert not DominioBankEntry.objects.exists()
    assert not AccountingEntry.objects.exists()


def test_received_bank_mirror_needs_independent_ledger_before_shared_confirmation(
    agent, organization, tmp_path
):
    company = ClientCompany.objects.get(organization=organization, dominio_code="001")
    account = FinancialAccount.objects.get(company=company, account_reference="001:123")
    for code in ["1.1", "2.1"]:
        LedgerAccount.objects.create(
            organization=organization, company=company, code=code, name=code
        )
    assert post_page(agent, [bank_row()]).status_code == 200
    bank_bytes = (
        b"OFXHEADER:100\n<OFX><BANKID>001<ACCTID>123<BANKTRANLIST>"
        b"<STMTTRN><DTPOSTED>20260912<TRNAMT>100.00<FITID>bank-1"
        b"<MEMO>Credito sintetico</STMTTRN></BANKTRANLIST></OFX>"
    )
    ledger_bytes = (
        b"entry_key;line_key;date;history;account_code;side;amount_cents;"
        b"cash_direction;document\n"
        b"journal-1;bank;2026-09-12;Razao sintetico;1.1;debit;10000;inflow;DOC-1\n"
        b"journal-1;other;2026-09-12;Razao sintetico;2.1;credit;10000;;DOC-1\n"
    )
    common = dict(organization=organization, company=company, financial_account=account)
    with override_settings(MEDIA_ROOT=tmp_path):
        source, run, _ = create_source_file(
            **common, filename="bank.ofx", content=bank_bytes, origin="bank_statement"
        )
        import_ofx(**common, filename="bank.ofx", content=bank_bytes)
        assert process_run(str(run.pk))["created"] == 1
        match = ReconciliationMatch.objects.get()
        assert match.status == "unmatched"
        with pytest.raises(ValueError, match=r"não comprova.*Razão"):
            confirm_reconciliation_match(
                match=match, accounting_entry=AccountingEntry.objects.get()
            )
        before = build_source_report(source)
        assert before["ledger_count"] == 0 and before["bank_unmatched_count"] == 1
        assert not MovementReconciliation.objects.exists()
        _, ledger_run, _ = create_source_file(
            **common, filename="ledger.csv", content=ledger_bytes, origin="accounting"
        )
        result = process_run(str(ledger_run.pk))
        assert result["created"] == 1
        record = IndependentLedgerRecord.objects.get()
        confirm_reconciliation_match(match=match, accounting_entry=record.accounting_entry)
        # A repeated agent page must not erase the human decision or create another allocation.
        assert post_page(agent, [bank_row()]).json()["created"] == 0
        match.refresh_from_db()
        assert match.status == "matched" and match.is_manual
        assert MovementReconciliation.objects.filter(state="confirmed").count() == 1
        report = build_source_report(source)
        assert report["bank_unmatched_count"] == report["ledger_unmatched_count"] == 0
        assert report["period_difference_cents"] == 0
        assert not report["coverage_confirmed"] and not report["homologated"]
        assert "não informado" in render_conference_csv(report).decode("utf-8-sig")
