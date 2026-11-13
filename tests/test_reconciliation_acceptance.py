import hashlib
from datetime import timedelta

import pytest
from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    LedgerAccount,
    NormalizedMovement,
    ProductModule,
    ReconciliationRun,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_acceptance import (
    acceptance_report,
    acceptance_review_packet,
    prepare_acceptance_sample,
    review_acceptance_sample,
)
from apps.organizations.models import Membership
from apps.platform.models import TenantContract

pytestmark = pytest.mark.django_db


@pytest.fixture
def acceptance(organization, user, membership, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"]
    )
    company = ClientCompany.objects.create(organization=organization, name="Synthetic acceptance")
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        account_reference="synthetic",
        ledger_code="1",
        name="Bank",
    )
    for code in ("1", "2", "3"):
        LedgerAccount.objects.create(
            organization=organization, company=company, code=code, name=code
        )
    content = b"Synthetic immutable source only; no real financial data."
    source = ReconciliationSourceFile.objects.create(
        organization=organization,
        company=company,
        financial_account=account,
        kind="ofx",
        origin="bank_statement",
        original_filename="synthetic.ofx",
        content_hash=hashlib.sha256(content).hexdigest(),
        content=ContentFile(content, name="synthetic.ofx"),
        size_bytes=len(content),
    )
    run = ReconciliationRun.objects.create(organization=organization, source_file=source)
    NormalizedMovement.objects.bulk_create(
        [
            NormalizedMovement(
                organization=organization,
                company=company,
                financial_account=account,
                source_file=source,
                run=run,
                source_key=f"fitid-{i}",
                direction="outflow",
                amount_cents=100,
                debit_account_code="2",
                credit_account_code="1",
                classification_source="rule",
            )
            for i in range(200)
        ]
    )
    ids = [str(k) for k in NormalizedMovement.objects.values_list("pk", flat=True)]
    return account, user, run, ids


def reviewed(acceptance, correct=190, ids=None):
    account, actor, _, all_ids = acceptance
    sample = prepare_acceptance_sample(
        account=account, actor=actor, movement_ids=ids or all_ids, release="synthetic-release"
    )
    expected = [
        {
            "fact_key": fact["fact_key"],
            "debit": "2" if i < correct else "3",
            "credit": "1",
            "cost_center": "",
        }
        for i, fact in enumerate(sample.metadata["facts"])
    ]
    review = review_acceptance_sample(
        account=account,
        actor=actor,
        sample_id=str(sample.pk),
        expected=expected,
        evidence_reference="Synthetic owner review only",
    )
    return sample, review, expected


@pytest.mark.parametrize("correct,passed", [(190, True), (189, False), (200, True), (0, False)])
def test_accuracy_uses_frozen_predictions_and_exact_95_percent_boundary(
    acceptance, correct, passed
):
    account, actor, _, _ = acceptance
    reviewed(acceptance, correct=correct)
    report = acceptance_report(account=account, actor=actor, release="synthetic-release")
    assert report["reviewed_distinct_facts"] == 200
    assert report["automatic_correct"] == correct
    assert report["classification_threshold_passed"] is passed
    assert report["precision_percent"] == correct / 2
    assert report["release_accepted"] is False and report["performance_threshold_passed"] is False
    # Later human corrections must not rewrite the model's measured prediction.
    NormalizedMovement.objects.update(
        debit_account_code="3", classification_source="manual", confidence=100
    )
    assert (
        acceptance_report(account=account, actor=actor, release="synthetic-release")[
            "automatic_correct"
        ]
        == correct
    )


def test_163_facts_and_repeated_sample_never_become_200(acceptance):
    account, actor, _, ids = acceptance
    sample, _, _ = reviewed(acceptance, correct=163, ids=ids[:163])
    repeated = prepare_acceptance_sample(
        account=account,
        actor=actor,
        movement_ids=list(reversed(ids[:163])),
        release="synthetic-release",
    )
    assert repeated.pk == sample.pk
    report = acceptance_report(account=account, actor=actor, release="synthetic-release")
    assert report["missing_to_200"] == 37 and report["automatic_reviewed"] == 163
    assert report["classification_threshold_passed"] is False


def test_overlap_across_samples_is_counted_once(acceptance):
    account, actor, _, ids = acceptance
    reviewed(acceptance, correct=200, ids=ids[:150])
    reviewed(acceptance, correct=200, ids=ids[100:])
    report = acceptance_report(account=account, actor=actor, release="synthetic-release")
    assert report["reviewed_distinct_facts"] == 200 and report["conflicting_facts"] == 0


def test_unreviewed_and_manual_classifications_do_not_prove_automatic_precision(acceptance):
    account, actor, _, ids = acceptance
    NormalizedMovement.objects.update(classification_source="manual", confidence=100)
    prepare_acceptance_sample(account=account, actor=actor, movement_ids=ids, release="unreviewed")
    assert (
        acceptance_report(account=account, actor=actor, release="unreviewed")[
            "reviewed_distinct_facts"
        ]
        == 0
    )
    reviewed(acceptance, correct=200)
    report = acceptance_report(account=account, actor=actor, release="synthetic-release")
    assert report["automatic_reviewed"] == 0 and report["precision_percent"] is None


def test_only_owner_can_attest_and_review_is_immutable(acceptance):
    account, actor, _, _ = acceptance
    sample, prior, expected = reviewed(acceptance)
    args = dict(
        account=account,
        actor=actor,
        sample_id=str(sample.pk),
        expected=expected,
        evidence_reference="Synthetic owner review only",
    )
    assert review_acceptance_sample(**args).pk == prior.pk
    expected[0]["debit"] = "3"
    with pytest.raises(ValueError):
        review_acceptance_sample(**args)
    Membership.objects.filter(user=actor).update(role="operator")
    with pytest.raises(PermissionDenied):
        review_acceptance_sample(**args)
    assert AuditEvent.objects.filter(action="hub.reconciliation.acceptance_review").count() == 1


def test_performance_uses_complete_run_timestamps_and_five_minute_company_total(acceptance):
    account, actor, run, _ = acceptance
    start = timezone.now()
    run.started_at, run.completed_at, run.state = start, start + timedelta(seconds=300), "completed"
    run.processed_count = 200
    run.save()
    report = acceptance_report(
        account=account, actor=actor, release="synthetic-release", run_ids=[str(run.pk)]
    )
    assert (
        report["company_processing_seconds"] == 300
        and report["performance_threshold_passed"] is True
    )
    run.completed_at += timedelta(seconds=1)
    run.save()
    assert (
        acceptance_report(
            account=account, actor=actor, release="synthetic-release", run_ids=[str(run.pk)]
        )["performance_threshold_passed"]
        is False
    )
    run.started_at = None
    run.save()
    with pytest.raises(ValueError):
        acceptance_report(
            account=account, actor=actor, release="synthetic-release", run_ids=[str(run.pk)]
        )


def test_owner_worksheet_preserves_source_context_and_hides_the_prediction(acceptance):
    account, actor, _, ids = acceptance
    sample = prepare_acceptance_sample(
        account=account, actor=actor, movement_ids=ids[:2], release="synthetic-release"
    )
    packet = acceptance_review_packet(account=account, actor=actor, sample_id=str(sample.pk))
    assert len(packet["facts"]) == 2 and packet["facts"][0]["cash_cents"] == 100
    assert all(row["debit"] == "" and row["credit"] == "" for row in packet["expected"])
    assert "prediction" not in str(packet)
