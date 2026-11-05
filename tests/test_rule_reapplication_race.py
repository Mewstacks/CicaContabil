from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread

import pytest
from django.db import close_old_connections, connection, transaction
from django.db.models.query import QuerySet
from django.test import override_settings

from apps.hub.models import (
    ClientCompany,
    JournalEntry,
    NormalizedMovement,
    ReconciliationRule,
    ReconciliationRun,
)
from apps.hub.reconciliation_service import apply_rules, create_source_file, process_run


@pytest.mark.django_db
@pytest.mark.parametrize("review_state", ["ignored", "pending"])
@pytest.mark.parametrize("classification", ["none", "rule"])
@pytest.mark.parametrize("operation", ["apply", "reapply"])
def test_human_editor_protects_ignore_or_restore_without_manual_classification(
    organization, user, tmp_path, review_state, classification, operation
):
    with override_settings(MEDIA_ROOT=tmp_path):
        company = ClientCompany.objects.create(organization=organization, name="Synthetic")
        source, run, _ = create_source_file(
            organization=organization,
            company=company,
            filename="review.ofx",
            origin="bank_statement",
            content=(
                b"OFXHEADER:100\n<OFX><BANKID>001<ACCTID>123<BANKTRANLIST><STMTTRN>"
                b"<DTPOSTED>20260912<TRNAMT>-10.00<FITID>synthetic<NAME>Synthetic fee"
                b"</STMTTRN></BANKTRANLIST></OFX>"
            ),
        )
        assert process_run(str(run.pk))["created"] == 1
        movement = NormalizedMovement.objects.get(source_file=source)
        # Individual and bulk ignore/restore historically set the editor without
        # changing the classification marker. A stale object must reload that fact.
        NormalizedMovement.objects.filter(pk=movement.pk).update(
            edited_by=user,
            review_state=review_state,
            classification_source=classification,
            accounting_history="Human review retained",
        )
        ReconciliationRule.objects.create(
            organization=organization,
            company=company,
            name="Synthetic conflicting rule",
            state="active",
            actions={"accounting_history": "Rule must not replace human choice"},
        )
        if operation == "apply":
            apply_rules(movement)
        else:
            repeated = ReconciliationRun.objects.create(
                organization=organization,
                source_file=source,
                continued_from=run,
                checkpoint={"mode": "rules"},
            )
            result = process_run(str(repeated.pk))
            assert result["updated"] == 0 and result["protected"] == 1
        movement.refresh_from_db()
        assert movement.review_state == review_state
        assert movement.classification_source == classification
        assert movement.accounting_history == "Human review retained"
        assert movement.edited_by_id == user.pk
        assert movement.revision == 1


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("decision", ["manual", "journal", "ignored", "restored"])
def test_postgresql_reapplication_rechecks_human_decision_after_wait(
    organization, user, tmp_path, monkeypatch, decision
):
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    with override_settings(MEDIA_ROOT=tmp_path):
        company = ClientCompany.objects.create(organization=organization, name="Synthetic")
        source, run, _ = create_source_file(
            organization=organization,
            company=company,
            filename="race.ofx",
            origin="bank_statement",
            content=(
                b"OFXHEADER:100\n<OFX><BANKID>001<ACCTID>123<BANKTRANLIST><STMTTRN>"
                b"<DTPOSTED>20260912<TRNAMT>-10.00<FITID>synthetic<NAME>Synthetic fee"
                b"</STMTTRN></BANKTRANLIST></OFX>"
            ),
        )
        assert process_run(str(run.pk))["created"] == 1
        movement = NormalizedMovement.objects.get(source_file=source)
        movement.debit_account_code = "human-code"
        movement.save()
        repeated = ReconciliationRun.objects.create(
            organization=organization,
            source_file=source,
            continued_from=run,
            checkpoint={"mode": "rules"},
        )
        selected, committed = Event(), Event()
        get = QuerySet.get

        def wait_before_company_lock(query, *args, **kwargs):
            if (
                query.model is ClientCompany
                and query.query.select_for_update
                and current_thread().name.startswith("rules-worker")
            ):
                selected.set()
                assert committed.wait(10), "Human transaction did not finish"
            return get(query, *args, **kwargs)

        monkeypatch.setattr(QuerySet, "get", wait_before_company_lock)

        def worker():
            close_old_connections()
            try:
                return process_run(str(repeated.pk))
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=1, thread_name_prefix="rules-worker") as pool:
            future = pool.submit(worker)
            try:
                assert selected.wait(10), "Worker never reached company lock"
                with transaction.atomic():
                    ClientCompany.objects.select_for_update().get(pk=company.pk)
                    if decision == "manual":
                        NormalizedMovement.objects.filter(pk=movement.pk).update(
                            classification_source="manual", debit_account_code="human-final"
                        )
                    elif decision in {"ignored", "restored"}:
                        NormalizedMovement.objects.filter(pk=movement.pk).update(
                            edited_by=user,
                            review_state="ignored" if decision == "ignored" else "pending",
                        )
                    else:
                        JournalEntry.objects.create(
                            organization=organization,
                            company=company,
                            movement=movement,
                            occurred_on=movement.occurred_on,
                            history="Reviewed draft",
                            purpose="record",
                            source_movement_revision=movement.revision,
                        )
            finally:
                committed.set()
            result = future.result(timeout=15)
        movement.refresh_from_db()
        assert movement.debit_account_code == (
            "human-final" if decision == "manual" else "human-code"
        )
        assert result["updated"] == 0 and result["protected"] == 1
        if decision in {"ignored", "restored"}:
            assert movement.edited_by_id == user.pk
            assert movement.review_state == ("ignored" if decision == "ignored" else "pending")
