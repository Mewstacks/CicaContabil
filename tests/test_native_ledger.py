"""Synthetic native snapshot through authenticated intake, storage and atomic drafts."""

from __future__ import annotations

import base64
import hashlib
import hmac
import io
import json
from copy import deepcopy
from datetime import date

import pytest
from django.core.management import call_command
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.hub.models import (
    AccountingEntry,
    ClientCompany,
    FinancialAccount,
    IndependentLedgerRecord,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    ReconciliationSourceFile,
)
from apps.intelligence.agent_scope import build_portfolio_scope
from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
from apps.intelligence.native_ledger_contract import (
    VERSION,
    canonical_hash,
    contract_hash,
    validate_scope,
    validate_snapshot,
)

pytestmark = pytest.mark.django_db


def pilot_scope():
    return validate_scope(
        {
            "company_code": 212,
            "chart_company_code": 212,
            "branch_code": 212,
            "bank_account_code": 8,
            "absent_account_code": 0,
            "bank_inflow_side": "debit",
            "period_start": "2026-09-01",
            "period_end_exclusive": "2026-10-01",
            "expected_source_rows": 177,
            "expected_lots": 163,
            "expected_bank_effects": 163,
        }
    )


def snapshot(scope):
    records, lots = [], []
    for lot in range(1, 164):
        shared = dict(
            company_code=212,
            chart_company_code=212,
            lot_code=lot,
            branch_code=212,
            occurred_on="2026-09-03",
            history=None,
            document=None,
            history_code_raw=None,
        )
        sides = (
            [(8, 0, "100.00"), (0, 20, "60.00"), (0, 30, "40.00")]
            if lot <= 7
            else [(8, 20, "100.00")]
        )
        lots.append(dict(lot_code=lot, row_count=len(sides), type_raw="C"))
        for debit, credit, amount in sides:
            records.append(
                dict(
                    shared,
                    row_code=len(records) + 1,
                    debit_account_code=debit,
                    credit_account_code=credit,
                    amount=amount,
                )
            )
    records[0]["history"] = "  Banco\n" + "á" * 990
    records[1]["history"] = "Outra partida"
    records[1]["document"] = 12
    return dict(
        version=VERSION,
        scope_revision=canonical_hash(scope),
        lots=lots,
        records=records,
        accounts=[
            dict(
                company_code=212,
                account_code=code,
                name_raw="Conta bruta",
                classification_raw="1",
                type_raw="A",
                status_raw="I",
                inactive_date_raw=None,
            )
            for code in (8, 20, 30)
        ],
    )


@pytest.fixture
def setup_native(organization, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.EDGE_AGENT_MTLS_REQUIRED = False
    company = ClientCompany.objects.create(
        organization=organization, name="Sintética", dominio_code="212"
    )
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Banco teste",
        account_reference="synthetic-only",
        ledger_code="8",
    )
    agent = EdgeAgent.objects.create(
        organization=organization,
        label="Sintético",
        fingerprint="test",
        shared_secret="synthetic-secret",
        is_official=True,
        sync_scope=build_portfolio_scope(
            organization=organization,
            start=date(2026, 9, 1),
            end=date(2026, 9, 30),
            company_status_map={"A": True},
            active_only=True,
        ),
    )
    output = io.StringIO()
    call_command(
        "queue_contad_native_ledger",
        organization=str(organization.pk),
        agent=str(agent.pk),
        account=str(account.pk),
        stdout=output,
    )
    job = NativeLedgerCollection.objects.get()
    return agent, account, job, snapshot(job.scope)


def post(agent, route, payload, *, job=None, protocol="scoped-v4", secure=True, secret=None):
    body = json.dumps(payload).encode()
    timestamp = str(int(timezone.now().timestamp()))
    signature = hmac.new(
        (secret or agent.shared_secret).encode(), timestamp.encode() + b"." + body, hashlib.sha256
    ).hexdigest()
    return Client().post(
        reverse(route, kwargs={"job_id": job.pk} if job else None),
        data=body,
        content_type="application/json",
        secure=secure,
        headers={
            "X-Hub-Agent-ID": str(agent.pk),
            "X-Hub-Agent-Timestamp": timestamp,
            "X-Hub-Agent-Signature": signature,
            "X-Hub-Agent-Protocol": protocol,
        },
    )


def complete(agent, job, data, **kwargs):
    content = json.dumps(data, ensure_ascii=False).encode()
    payload = dict(
        scope_revision=job.scope_revision,
        contract_hash=job.contract_hash,
        content_sha256=hashlib.sha256(content).hexdigest(),
        content_base64=base64.b64encode(content).decode(),
    )
    return post(agent, "agent-v2-ledger-complete", payload, job=job, **kwargs)


def test_native_intake_preserves_text_parties_null_source_and_idempotency(setup_native):
    agent, account, job, data = setup_native
    queued = post(agent, "agent-v2-ledger-next", {"version": "1.0.8"})
    assert queued.status_code == 200 and queued.json()["job"]["id"] == str(job.id)
    first = complete(agent, job, data)
    assert first.status_code == 200, first.content
    assert first.json()["state"] == "imported"
    assert first.json()["result"] == dict(
        created=163, ignored=0, journals=163, parties=333, source_rows=177, bank_effects=163
    )
    assert complete(agent, job, data).json() == first.json()
    assert JournalEntry.objects.count() == 163 and JournalLine.objects.count() == 333
    assert IndependentLedgerRecord.objects.count() == 163 and AccountingEntry.objects.count() == 163
    assert not LedgerAccount.objects.exists()  # No inferred active/classification/type semantics.
    assert not JournalEntry.objects.exclude(state="draft", purpose="source_ledger").exists()
    entry = JournalEntry.objects.get(history=data["records"][0]["history"])
    assert set(entry.lines.values_list("history", flat=True)) == {
        data["records"][0]["history"],
        "Outra partida",
        "",
    }
    source = ReconciliationSourceFile.objects.get()
    assert (
        source.financial_account == account
        and source.origin == "accounting"
        and source.kind == "json"
    )
    with source.content.open("rb") as stream:
        assert json.load(stream) == data
    assert post(agent, "agent-v2-ledger-next", {"version": "1.0.8"}).json()["job"] is None


@pytest.mark.parametrize(
    "change",
    [
        "company",
        "chart",
        "branch",
        "date",
        "missing",
        "duplicate",
        "zero",
        "amount",
        "text",
        "extra",
        "lot_count",
    ],
)
def test_bad_or_cross_scope_snapshots_leave_no_source_or_partial_journals(setup_native, change):
    agent, _, job, data = setup_native
    if change == "company":
        data["records"][0]["company_code"] = 213
    if change == "chart":
        data["records"][0]["chart_company_code"] = 213
    if change == "branch":
        data["records"][0]["branch_code"] = 1
    if change == "date":
        data["records"][0]["occurred_on"] = "2026-08-31"
    if change == "missing":
        data["records"].pop()
    if change == "duplicate":
        data["records"][-1] = deepcopy(data["records"][0])
    if change == "zero":
        data["accounts"][0]["account_code"] = 0
    if change == "amount":
        data["records"][0]["amount"] = 100.0
    if change == "text":
        data["records"][0]["history"] = "á" * 1001
    if change == "extra":
        data["records"][0]["cpf"] = "unexpected"
    if change == "lot_count":
        data["lots"][0]["row_count"] += 1
    assert complete(agent, job, data).status_code == 400
    assert not ReconciliationSourceFile.objects.exists() and not JournalEntry.objects.exists()
    job.refresh_from_db()
    assert job.state == "queued"


@pytest.mark.parametrize(
    "mode", ["revoked", "nonofficial", "protocol", "http", "signature", "other_org"]
)
def test_official_identity_and_transport_boundaries(setup_native, organization, mode):
    agent, _account, job, data = setup_native
    kwargs = {}
    if mode == "revoked":
        agent.is_official = False
        agent.status = "revoked"
        agent.save()
    if mode == "nonofficial":
        agent.is_official = False
        agent.save()
    if mode == "protocol":
        kwargs["protocol"] = "scoped-v3"
    if mode == "http":
        kwargs["secure"] = False
    if mode == "signature":
        kwargs["secret"] = "wrong"
    if mode == "other_org":
        from apps.organizations.models import Organization

        outsider = Organization.objects.create(name="Outro", slug="other-native")
        job.organization = outsider
        job.save()
    assert complete(agent, job, data, **kwargs).status_code in {401, 404, 409}
    assert not JournalEntry.objects.exists() and not ReconciliationSourceFile.objects.exists()


def test_changed_content_after_commit_conflicts_without_overwrite(setup_native):
    agent, _, job, data = setup_native
    assert complete(agent, job, data).status_code == 200
    data["records"][0]["history"] = "Alterado"
    assert complete(agent, job, data).status_code == 409
    assert (
        JournalEntry.objects.count() == 163
        and not JournalEntry.objects.filter(history="Alterado").exists()
    )


def test_existing_source_journal_conflict_is_retained_privately_for_review(setup_native):
    agent, _account, job, data = setup_native
    assert complete(agent, job, data).status_code == 200
    # An operator reset must still protect the original journals.
    job.state = "queued"
    job.content_hash = ""
    job.save()
    data["records"][0]["history"] = "Changed source"
    result = complete(agent, job, data)
    assert result.status_code == 200 and result.json()["state"] == "review"
    assert JournalEntry.objects.count() == 163 and ReconciliationSourceFile.objects.count() == 2
    job.refresh_from_db()
    assert job.error_code == "ledger_content_conflict"
    assert post(agent, "agent-v2-ledger-next", {"version": "1.0.8"}).json()["review_required"]


def test_contract_hash_and_scope_fail_closed_and_duplicate_json_rejected(setup_native):
    _, _, job, _ = setup_native
    assert contract_hash() == job.contract_hash
    bad = dict(job.scope, company_code=True)
    with pytest.raises(ValueError):
        validate_scope(bad)
    with pytest.raises(ValueError):
        validate_snapshot(b'{"version":1,"version":2}', job.scope)
    assert NativeLedgerCollection.objects.count() == 1


def test_native_entries_can_be_suggested_without_becoming_confirmed(setup_native, org_client):
    from apps.hub.models import BankStatementImport, BankTransaction, ReconciliationMatch

    agent, account, job, data = setup_native
    bank = BankStatementImport.objects.create(
        organization=account.organization,
        company=account.company,
        account_reference=account.account_reference,
        content_hash="a" * 64,
    )
    item = BankTransaction.objects.create(
        organization=account.organization,
        statement=bank,
        external_id="one",
        occurred_on="2026-09-03",
        description="Synthetic",
        amount_cents=10000,
    )
    assert complete(agent, job, data).status_code == 200
    match = ReconciliationMatch.objects.get(transaction=item)
    assert match.status == "ambiguous" and not match.is_manual
    assert match.accounting_entry_id is None
    from apps.hub.models import ProductModule

    ProductModule.objects.create(
        organization=account.organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    session = org_client.session
    session["hub_organization_id"] = str(account.organization_id)
    session.save()
    response = org_client.get(reverse("hub:reconciliation"))
    assert response.status_code == 200
    visible = next(row for row in response.context["matches"] if row.pk == match.pk)
    assert visible.candidates and all(
        hasattr(row, "independent_source") for row in visible.candidates
    )


@pytest.mark.django_db(transaction=True)
def test_concurrent_retry_commits_one_source_and_one_set_of_journals(setup_native):
    from concurrent.futures import ThreadPoolExecutor

    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("Native intake serialization requires PostgreSQL row locks.")
    agent, _, job, data = setup_native

    def send():
        close_old_connections()
        try:
            return complete(agent, job, data).status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(lambda _: send(), range(2))) == [200, 200]
    assert ReconciliationSourceFile.objects.count() == 1
    assert JournalEntry.objects.count() == 163 and JournalLine.objects.count() == 333


def test_in_scope_unbalanced_snapshot_retained_for_review_without_partial_import(setup_native):
    agent, _, job, data = setup_native
    data["records"][0]["amount"] = "99.99"
    response = complete(agent, job, data)
    assert response.status_code == 200 and response.json()["state"] == "review"
    assert ReconciliationSourceFile.objects.count() == 1 and not JournalEntry.objects.exists()
    job.refresh_from_db()
    assert job.error_code == "ledger_import_review" and job.source_file_id
