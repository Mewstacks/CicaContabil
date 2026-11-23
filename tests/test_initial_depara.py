from dataclasses import replace

import pytest
from django.test import override_settings

from apps.hub.depara import DeparaExample, create_initial_depara_drafts
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    LedgerAccount,
    NormalizedMovement,
    ReconciliationRule,
)
from apps.hub.reconciliation_service import apply_rules, create_source_file, process_run
from apps.organizations.models import Membership

pytestmark = pytest.mark.django_db


@pytest.fixture
def setup(organization, user, tmp_path):
    with override_settings(MEDIA_ROOT=tmp_path):
        Membership.objects.create(organization=organization, user=user, role="owner")
        company = ClientCompany.objects.create(organization=organization, name="Synthetic")
        bank = FinancialAccount.objects.create(
            organization=organization,
            company=company,
            name="Synthetic",
            account_reference="001:123",
        )
        for code in ["1", "2", "3"]:
            LedgerAccount.objects.create(
                organization=organization, company=company, code=code, name=code
            )
        example = DeparaExample(
            reference="human-example-1",
            description="Synthetic fee",
            direction="outflow",
            account_reference=bank.account_reference,
            debit_account_code="2",
            credit_account_code="1",
            accounting_history="Reviewed synthetic fee",
        )
        yield company, user, example


def prepare(setup, examples=None):
    company, user, example = setup
    return create_initial_depara_drafts(
        company=company, examples=examples or [example], reviewed_by=user
    )


def test_drafts_require_review_and_retry_preserves_human_edited_disabled_rule(setup):
    result = prepare(setup)[0]
    assert result.status == "draft"
    rule = ReconciliationRule.objects.get(pk=result.rule_id)
    assert rule.state == "draft" and rule.actions["require_review"] is True
    rule.state = "disabled"
    rule.actions["credit_account_code"] = "3"
    rule.save()
    assert prepare(setup)[0].status == "preserved"
    rule.refresh_from_db()
    assert rule.state == "disabled" and rule.actions["credit_account_code"] == "3"
    assert ReconciliationRule.objects.count() == 1


def test_example_order_and_description_case_do_not_duplicate_drafts(setup):
    first = setup[2]
    second = replace(first, reference="human-example-2", description=first.description.upper())
    original = prepare(setup, [first, second])[0]
    repeated = prepare(setup, [second, first])[0]
    assert original.rule_id == repeated.rule_id
    assert repeated.status == "preserved"
    assert ReconciliationRule.objects.count() == 1


@pytest.mark.parametrize("kind", ["missing", "inactive", "synthetic", "bank", "other_company"])
def test_invalid_or_unusable_accounts_create_no_rule(setup, kind):
    company, _, example = setup
    if kind in {"inactive", "synthetic"}:
        LedgerAccount.objects.filter(company=company, code="2").update(
            **({"active": False} if kind == "inactive" else {"accepts_entries": False})
        )
    elif kind == "bank":
        FinancialAccount.objects.filter(company=company).update(active=False)
    elif kind == "other_company":
        other = ClientCompany.objects.create(organization=company.organization, name="Other")
        LedgerAccount.objects.filter(company=company, code="2").update(company=other)
    else:
        example = replace(example, debit_account_code="missing")
    assert prepare(setup, [example])[0].status == "invalid_accounts"
    assert not ReconciliationRule.objects.exists()


def test_contradictory_and_incomplete_examples_have_explicit_status(setup):
    example = setup[2]
    assert (
        prepare(
            setup, [example, replace(example, reference="human-example-2", debit_account_code="3")]
        )[0].status
        == "conflict"
    )
    assert prepare(setup, [replace(example, accounting_history="")])[0].status == "insufficient"
    assert not ReconciliationRule.objects.exists()


def test_broad_active_manual_rule_conflict_is_reported_without_replacing_it(setup):
    company, user, _ = setup
    human_rule = ReconciliationRule.objects.create(
        organization=company.organization,
        company=company,
        name="Human decision",
        state="active",
        all_conditions=[{"field": "description", "operator": "contains", "value": "fee"}],
        actions={"debit_account_code": "3"},
        created_by=user,
    )
    assert prepare(setup)[0].status == "conflict"
    human_rule.refresh_from_db()
    assert human_rule.actions == {"debit_account_code": "3"}
    assert ReconciliationRule.objects.count() == 1


def test_preparation_never_classifies_and_activated_draft_still_requires_review(setup):
    company, _, _ = setup
    bank = company.financial_accounts.get()
    source, run, _ = create_source_file(
        organization=company.organization,
        company=company,
        filename="synthetic.ofx",
        origin="bank_statement",
        financial_account=bank,
        content=(
            b"OFXHEADER:100\n<OFX><BANKID>001<ACCTID>123<BANKTRANLIST><STMTTRN>"
            b"<DTPOSTED>20260912<TRNAMT>-10.00<FITID>synthetic<NAME>Synthetic fee"
            b"</STMTTRN></BANKTRANLIST></OFX>"
        ),
    )
    assert process_run(str(run.pk))["created"] == 1
    movement = NormalizedMovement.objects.get(source_file=source)
    result = prepare(setup)[0]
    movement.refresh_from_db()
    assert movement.classification_source == "none"
    ReconciliationRule.objects.filter(pk=result.rule_id).update(state="active")
    apply_rules(movement)
    movement.refresh_from_db()
    assert movement.debit_account_code == "2" and movement.review_state == "pending"
    assert not movement.journal_entries.exists()


@pytest.mark.parametrize("role", ["auditor", "billing", "member", "inactive"])
def test_consultative_or_revoked_reviewer_cannot_prepare_drafts(setup, role):
    from django.core.exceptions import PermissionDenied

    company, user, _ = setup
    query = Membership.objects.filter(organization=company.organization, user=user)
    query.update(**({"is_active": False} if role == "inactive" else {"role": role}))
    with pytest.raises(PermissionDenied):
        prepare(setup)
    assert not ReconciliationRule.objects.exists()


def test_rule_application_reloads_and_preserves_a_newer_manual_decision(setup):
    company, _, _ = setup
    source, run, _ = create_source_file(
        organization=company.organization,
        company=company,
        filename="stale.ofx",
        origin="bank_statement",
        financial_account=company.financial_accounts.get(),
        content=(
            b"OFXHEADER:100\n<OFX><BANKID>001<ACCTID>123<BANKTRANLIST><STMTTRN>"
            b"<DTPOSTED>20260912<TRNAMT>-10.00<FITID>stale<NAME>Synthetic fee"
            b"</STMTTRN></BANKTRANLIST></OFX>"
        ),
    )
    assert process_run(str(run.pk))["created"] == 1
    stale = source.movements.get()
    result = prepare(setup)[0]
    ReconciliationRule.objects.filter(pk=result.rule_id).update(state="active")
    source.movements.update(classification_source="manual", debit_account_code="human-final")
    apply_rules(stale)
    assert stale.classification_source == "manual" and stale.debit_account_code == "human-final"
