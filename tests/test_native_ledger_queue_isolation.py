"""One account's queue failure must not block another authorized company."""

from copy import deepcopy
from datetime import timedelta

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    IndependentLedgerRecord,
    JournalEntry,
    ProductModule,
    ReconciliationSourceFile,
)
from apps.intelligence.models import NativeLedgerCollection
from apps.intelligence.native_ledger_contract import VERSION, canonical_hash, pilot_scope
from apps.organizations.models import Membership
from apps.platform.models import TenantContract
from test_native_ledger import complete, post
from test_native_ledger import setup_native as native_fixture

native_source = native_fixture
pytestmark = pytest.mark.django_db


@pytest.fixture
def portfolio(native_source, user, membership):
    agent, pilot_account, legacy, legacy_data = native_source
    ProductModule.objects.create(
        organization=agent.organization, code="reconciliation", enabled=True
    )
    TenantContract.objects.create(
        organization=agent.organization, status="active", selected_modules=["reconciliation"]
    )

    def add_job(company_code, bank_code, *, actor=user, month="2026-10"):
        company, _ = ClientCompany.objects.get_or_create(
            organization=agent.organization,
            dominio_code=str(company_code),
            defaults={"name": f"Empresa sintética {company_code}"},
        )
        account = FinancialAccount.objects.create(
            organization=agent.organization,
            company=company,
            name=f"Banco sintético {bank_code}",
            account_reference=f"synthetic:{company_code}:{bank_code}",
            ledger_code=str(bank_code),
        )
        scope = dict(
            pilot_scope(),
            company_code=company_code,
            chart_company_code=company_code,
            branch_code=company_code,
            bank_account_code=bank_code,
            period_start=f"{month}-01",
            period_end_exclusive=f"2026-{int(month[-2:]) + 1:02}-01",
            expected_source_rows=1,
            expected_lots=1,
            expected_bank_effects=1,
        )
        job = NativeLedgerCollection.objects.create(
            organization=agent.organization,
            agent=agent,
            financial_account=account,
            scope=scope,
            scope_revision=canonical_hash(scope),
            contract_hash=legacy.contract_hash,
            requested_by=actor,
            evidence_reference="Vínculo sintético revisado para o teste de fila",
        )
        data = {
            "version": VERSION,
            "scope_revision": job.scope_revision,
            "lots": [{"lot_code": 1, "row_count": 1, "type_raw": "C"}],
            "records": [{
                "company_code": company_code,
                "chart_company_code": company_code,
                "branch_code": company_code,
                "lot_code": 1,
                "row_code": 1,
                "occurred_on": f"{month}-03",
                "debit_account_code": bank_code,
                "credit_account_code": 30,
                "amount": "100.00",
                "history": "Recebimento sintético",
                "document": None,
                "history_code_raw": None,
            }],
            "accounts": [
                dict(
                    company_code=company_code,
                    account_code=code,
                    name_raw="Conta sintética",
                    classification_raw="1",
                    type_raw="A",
                    status_raw="A",
                    inactive_date_raw=None,
                )
                for code in (bank_code, 30)
            ],
        }
        return job, data

    return agent, pilot_account, legacy, legacy_data, add_job


def poll(agent, *, expanded=True):
    payload = {"version": "1.0.8"}
    if expanded:
        payload["portfolio_scope"] = True
    return post(agent, "agent-v2-ledger-next", payload)


def fail(agent, job, code):
    return post(
        agent,
        "agent-v2-ledger-failure",
        {"scope_revision": job.scope_revision, "contract_hash": job.contract_hash, "code": code},
        job=job,
    )


@pytest.mark.parametrize("invalid", ["account_inactive", "scope_changed", "actor_revoked"])
def test_invalid_first_job_does_not_block_other_accounts_or_companies(portfolio, invalid):
    agent, _, legacy, _, add_job = portfolio
    legacy.delete()
    actor = User.objects.create_user("revocable@queue.test", "synthetic-password")
    access = Membership.objects.create(
        organization=agent.organization, user=actor, role="owner"
    )
    first, first_data = add_job(314, 8, actor=actor)
    same_company, same_data = add_job(314, 21)
    other_company, other_data = add_job(315, 8)
    if invalid == "account_inactive":
        FinancialAccount.objects.filter(pk=first.financial_account_id).update(active=False)
    elif invalid == "scope_changed":
        scope = dict(first.scope, chart_company_code=77)
        NativeLedgerCollection.objects.filter(pk=first.pk).update(scope=scope)
    else:
        access.is_active = False
        access.save(update_fields=["is_active"])
    before = NativeLedgerCollection.objects.values().get(pk=first.pk)
    for expected, data in ((same_company, same_data), (other_company, other_data)):
        response = poll(agent)
        assert response.status_code == 200
        assert response.json()["job"]["id"] == str(expected.pk)
        assert response.json()["review_required"] is True
        assert complete(agent, expected, data).json()["state"] == "imported"
    assert complete(agent, first, first_data).status_code == 409
    assert poll(agent).status_code == 409
    assert NativeLedgerCollection.objects.values().get(pk=first.pk) == before
    assert JournalEntry.objects.count() == 2
    assert set(IndependentLedgerRecord.objects.values_list("financial_account_id", flat=True)) == {
        same_company.financial_account_id, other_company.financial_account_id,
    }
    assert not ReconciliationSourceFile.objects.filter(
        financial_account_id=first.financial_account_id
    ).exists()


@pytest.mark.parametrize("expanded", [False, True])
def test_all_invalid_still_returns_409_and_preserves_pending_job(portfolio, expanded):
    agent, account, legacy, _, _ = portfolio
    account.active = False
    account.save(update_fields=["active"])
    before = NativeLedgerCollection.objects.values().get(pk=legacy.pk)
    assert poll(agent, expanded=expanded).status_code == 409
    assert NativeLedgerCollection.objects.values().get(pk=legacy.pk) == before
    assert not ReconciliationSourceFile.objects.exists()
    assert not JournalEntry.objects.exists()


def test_legacy_capability_never_receives_expanded_scope_after_invalid_pilot(portfolio):
    agent, account, legacy, _, add_job = portfolio
    expanded, _ = add_job(314, 8)
    account.active = False
    account.save(update_fields=["active"])
    assert poll(agent, expanded=False).status_code == 409
    assert poll(agent).json()["job"]["id"] == str(expanded.pk)
    legacy.delete()
    assert poll(agent, expanded=False).json() == {"job": None, "review_required": False}


@pytest.mark.parametrize("code", ["source_changed", "source_unavailable"])
def test_transient_failure_rotates_accounts_and_retry_is_not_starved(portfolio, code):
    agent, _, legacy, _, add_job = portfolio
    legacy.delete()
    first, first_data = add_job(314, 8)
    second, second_data = add_job(314, 21)
    third, third_data = add_job(315, 8, month="2026-11")
    initial = timezone.now() - timedelta(minutes=3)
    for index, job in enumerate((first, second, third)):
        NativeLedgerCollection.objects.filter(pk=job.pk).update(
            updated_at=initial + timedelta(seconds=index)
        )
    assert poll(agent).json()["job"]["id"] == str(first.pk)
    assert fail(agent, first, code).json() == {"state": "queued"}
    assert poll(agent).json()["job"]["id"] == str(second.pk)
    assert fail(agent, second, code).json() == {"state": "queued"}
    assert poll(agent).json()["job"]["id"] == str(third.pk)
    assert complete(agent, third, third_data).json()["state"] == "imported"
    assert poll(agent).json()["job"]["id"] == str(first.pk)
    assert complete(agent, first, first_data).json()["state"] == "imported"
    assert poll(agent).json()["job"]["id"] == str(second.pk)
    assert complete(agent, second, second_data).json()["state"] == "imported"
    assert poll(agent).json() == {"job": None, "review_required": False}
    assert JournalEntry.objects.count() == 3


def test_legacy_job_rotates_after_transient_failure_only_for_expanded_agent(portfolio):
    agent, _, legacy, _, add_job = portfolio
    expanded, _ = add_job(314, 8)
    assert fail(agent, legacy, "source_unavailable").status_code == 200
    assert poll(agent, expanded=False).json()["job"]["id"] == str(legacy.pk)
    assert poll(agent).json()["job"]["id"] == str(expanded.pk)


def test_scope_tampering_is_refused_again_after_selection(portfolio):
    agent, _, legacy, _, add_job = portfolio
    legacy.delete()
    job, data = add_job(314, 8)
    assert poll(agent).json()["job"]["id"] == str(job.pk)
    changed = deepcopy(job.scope)
    changed["company_code"] = 999
    NativeLedgerCollection.objects.filter(pk=job.pk).update(scope=changed)
    assert complete(agent, job, data).status_code == 409
    assert not JournalEntry.objects.exists()
