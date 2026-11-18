import hashlib
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from threading import Barrier
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection
from django.test import Client
from django.urls import reverse
from tests.accounting_import_fixtures import homologate_synthetic

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.accounting_import import (
    ImportReceiptConflict,
    ImportReceiptError,
    export_homologated,
    import_receipt_context,
    record_import_receipt,
    verify_import_receipt,
)
from apps.hub.models import (
    AccountingExport,
    AccountingExportHomologation,
    AccountingImportReceipt,
    ClientCompany,
    CompanyAccessGrant,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    ProductModule,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_service import ReconciliationError, create_export
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db
START, END = date(2026, 9, 1), date(2026, 9, 30)


@pytest.fixture
def case(organization, tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    settings.RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED = False
    company = ClientCompany.objects.create(organization=organization, name="Synthetic importer")
    actor = User.objects.create_user("receipt@example.test", "synthetic-password")
    member = Membership.objects.create(organization=organization, user=actor, role="owner")
    approval, _ = homologate_synthetic(organization)
    for code in ("1", "2"):
        LedgerAccount.objects.create(
            organization=organization, company=company, code=code, name=code
        )
    for n in range(2):
        entry = JournalEntry.objects.create(
            organization=organization,
            company=company,
            occurred_on=START,
            history=f"Synthetic {n}",
            purpose="record",
            state="approved",
        )
        for code, side in (("1", "debit"), ("2", "credit")):
            JournalLine.objects.create(
                organization=organization,
                entry=entry,
                account_code=code,
                side=side,
                amount_cents=12345 + n,
            )
    export = create_export(
        organization=organization,
        company=company,
        start=START,
        end=END,
        actor=actor,
    )
    return dict(
        organization=organization,
        company=company,
        actor=actor,
        membership=member,
        approval=approval,
        export=export,
    )


def params(case, statuses=("accepted", "accepted")):
    return dict(
        export=case["export"],
        actor=case["actor"],
        request_key=uuid4(),
        content_hash=case["export"].content_hash,
        items=[
            dict(
                entry_id=identifier,
                status=status,
                erp_reference=f"SYNTHETIC-{index}" if status == "accepted" else "",
                evidence_reference=f"SYNTHETIC row {index}",
            )
            for index, (identifier, status) in enumerate(
                zip(
                    case["export"].entry_ids,
                    statuses,
                    strict=True,
                )
            )
        ],
        evidence_reference="SYNTHETIC private importer report",
        importer_version="SYNTHETIC-NONPRODUCTION",
        review_confirmed=True,
    )


def test_office_target_version_and_latest_revocation_control_gate(case, settings):
    org, version = case["organization"], case["export"].adapter_version
    assert export_homologated(org, "dominio", version)
    other = Organization.objects.create(name="Other", slug="other-import-office")
    settings.RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED = True
    assert not export_homologated(other, "dominio", version)
    assert not export_homologated(org, "siescon", version)
    assert not export_homologated(org, "dominio", "different-version")
    homologate_synthetic(org, approved=False)
    assert not export_homologated(org, "dominio", version)
    with pytest.raises(ReconciliationError, match="homologação"):
        create_export(
            organization=org,
            company=case["company"],
            start=START,
            end=END,
            reexport_of=case["export"],
            reexport_reason="Synthetic copy",
        )


def test_technical_homologation_is_immutable_replayable_and_not_attributed_to_customer(case):
    row = case["approval"]
    assert row.created_by_id is None
    assert row.evidence["authorship"] == "technical_record_of_external_decision"
    again, created = homologate_synthetic(case["organization"], request_key=row.request_key)
    assert again.pk == row.pk and not created
    with pytest.raises(ImportReceiptConflict):
        homologate_synthetic(case["organization"], request_key=row.request_key, approved=False)
    with pytest.raises(ValidationError):
        row.save()
    with pytest.raises(ValidationError):
        AccountingExportHomologation.objects.filter(pk=row.pk).update(approved=False)


@pytest.mark.parametrize(
    "statuses,outcome",
    [
        (("accepted", "rejected"), "partial"),
        (("rejected", "rejected"), "rejected"),
        (("accepted", "uncertain"), "uncertain"),
        (("uncertain", "uncertain"), "uncertain"),
    ],
)
def test_incomplete_import_is_visible_but_does_not_confirm(case, statuses, outcome):
    receipt, created = record_import_receipt(**params(case, statuses))
    assert created and receipt.outcome == outcome
    case["export"].refresh_from_db()
    assert case["export"].state == "ready" and case["export"].confirmed_at is None
    context = import_receipt_context(export=case["export"], actor=case["actor"])
    assert context["outcome"] == outcome and len(context["items"]) == 2
    assert context["expected_previous_id"] == str(receipt.pk)


def test_complete_receipt_replays_without_duplicate_audit_or_confirmation(case):
    args = params(case)
    receipt, created = record_import_receipt(**args)
    again, repeated = record_import_receipt(**args)
    assert created and not repeated and again.pk == receipt.pk
    export = AccountingExport.objects.get(pk=case["export"].pk)
    assert export.state == "confirmed" and export.confirmed_by == case["actor"]
    assert (
        AuditEvent.objects.filter(action="hub.reconciliation.import_receipt_recorded").count() == 1
    )
    with pytest.raises(ValidationError):
        receipt.delete()
    with pytest.raises(ValidationError):
        receipt.save()
    with pytest.raises(ValidationError):
        AccountingImportReceipt.objects.filter(pk=receipt.pk).update(outcome="rejected")


def test_historical_receipt_verification_checks_its_own_fingerprint(case):
    first, _ = record_import_receipt(**params(case, ("uncertain", "uncertain")))
    next_args = params(case)
    next_args["expected_previous_id"] = str(first.pk)
    record_import_receipt(**next_args)
    verify_import_receipt(receipt=first, export=case["export"])
    first.items[0]["evidence_reference"] = "Altered after the receipt"
    with pytest.raises(ImportReceiptError, match="integridade"):
        verify_import_receipt(receipt=first, export=case["export"])


def test_new_observation_preserves_accepted_items_and_requires_current_receipt(case):
    args = params(case, ("accepted", "uncertain"))
    first, _ = record_import_receipt(**args)
    finished = params(case)
    with pytest.raises(ImportReceiptConflict, match="mais recente"):
        record_import_receipt(**finished)
    finished["expected_previous_id"] = first.pk
    altered = deepcopy(finished)
    altered["items"][0]["erp_reference"] = "different"
    with pytest.raises(ImportReceiptConflict, match="já aceitos"):
        record_import_receipt(**altered)
    second, _ = record_import_receipt(**finished)
    assert second.previous_id == first.pk and second.outcome == "accepted"
    assert AccountingImportReceipt.objects.count() == 2


@pytest.mark.parametrize(
    "change",
    [
        "hash",
        "missing_item",
        "duplicate",
        "foreign",
        "no_evidence",
        "no_erp_reference",
        "not_confirmed",
        "invalid_status",
        "tamper",
        "missing_file",
        "source_ledger",
    ],
)
def test_invalid_or_unverifiable_receipt_cannot_confirm_or_create_audit(case, change):
    args = params(case)
    if change == "hash":
        args["content_hash"] = "0" * 64
    elif change == "missing_item":
        args["items"].pop()
    elif change == "duplicate":
        args["items"][1] = args["items"][0]
    elif change == "foreign":
        args["items"][0]["entry_id"] = str(uuid4())
    elif change == "no_evidence":
        args["evidence_reference"] = ""
    elif change == "no_erp_reference":
        args["items"][0]["erp_reference"] = ""
    elif change == "not_confirmed":
        args["review_confirmed"] = False
    elif change == "invalid_status":
        args["items"][0]["status"] = "done"
    elif change == "tamper":
        with case["export"].content.open("wb") as stream:
            stream.write(b"corrupt")
    elif change == "missing_file":
        case["export"].content.delete(save=False)
    else:
        JournalEntry.objects.filter(pk=case["export"].entry_ids[0]).update(purpose="source_ledger")
    with pytest.raises(ImportReceiptError):
        record_import_receipt(**args)
    assert AccountingImportReceipt.objects.count() == 0
    assert not AuditEvent.objects.filter(
        action="hub.reconciliation.import_receipt_recorded"
    ).exists()
    case["export"].refresh_from_db()
    assert case["export"].state == "ready"


@pytest.mark.parametrize("change", ["membership", "user", "module", "company", "auditor"])
def test_receipt_rechecks_authorization(case, change):
    if change == "membership":
        Membership.objects.filter(pk=case["membership"].pk).update(is_active=False)
    elif change == "user":
        User.objects.filter(pk=case["actor"].pk).update(is_active=False)
    elif change == "module":
        ProductModule.objects.filter(organization=case["organization"]).update(enabled=False)
    elif change == "auditor":
        Membership.objects.filter(pk=case["membership"].pk).update(role="auditor")
    else:
        Membership.objects.filter(pk=case["membership"].pk).update(role="operator")
        CompanyAccessGrant.objects.filter(membership=case["membership"]).delete()
    with pytest.raises((PermissionDenied, ImportReceiptError)):
        record_import_receipt(**params(case))
    assert not AccountingImportReceipt.objects.exists()


def test_copy_uses_original_receipt_chain_instead_of_confirming_the_import_twice(case):
    copy = create_export(
        organization=case["organization"],
        company=case["company"],
        start=START,
        end=END,
        reexport_of=case["export"],
        reexport_reason="Copy",
    )
    args = params(case)
    args["export"] = copy
    row, _ = record_import_receipt(**args)
    assert row.export_id == case["export"].pk and row.submitted_export_id == copy.pk
    assert import_receipt_context(export=copy, actor=case["actor"])["outcome"] == "accepted"
    with pytest.raises(ImportReceiptConflict):
        record_import_receipt(**params(case))


def test_legacy_checkbox_cannot_replace_item_evidence_even_with_global_switch(case, settings):
    settings.RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED = True
    client = Client()
    client.force_login(case["actor"])
    session = client.session
    session["hub_organization_id"] = str(case["organization"].pk)
    session.save()
    response = client.post(
        reverse("hub:reconciliation-export-confirm", args=[case["export"].pk]),
        {"content_hash": case["export"].content_hash, "confirm_import": "yes"},
    )
    assert response.status_code == 302
    case["export"].refresh_from_db()
    assert case["export"].state == "ready" and not AccountingImportReceipt.objects.exists()


@pytest.mark.parametrize("change", ["valid", "other_company", "wrong_origin", "corrupt"])
def test_receipt_document_is_private_scoped_and_verified(case, change):
    content = b"SYNTHETIC ERP IMPORT REPORT / NO REAL TRANSACTION"
    company = case["company"]
    if change == "other_company":
        company = ClientCompany.objects.create(organization=case["organization"], name="Other")
    source = ReconciliationSourceFile.objects.create(
        organization=case["organization"],
        company=company,
        kind="pdf",
        origin="bank_statement" if change == "wrong_origin" else "document",
        original_filename="synthetic.pdf",
        content_type="application/pdf",
        content_hash=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
        content=SimpleUploadedFile("synthetic.pdf", content),
        uploaded_by=case["actor"],
    )
    if change == "corrupt":
        with source.content.open("wb") as stream:
            stream.write(b"different")
    args = params(case)
    args["evidence_source"] = source
    if change != "valid":
        with pytest.raises(ImportReceiptError):
            record_import_receipt(**args)
        assert not AccountingImportReceipt.objects.exists()
    else:
        receipt, _ = record_import_receipt(**args)
        assert receipt.evidence["kind"] == "document"
        assert receipt.evidence["source_id"] == str(source.pk)
        assert receipt.evidence["sha256"] == source.content_hash


def test_unreviewed_pages_can_remain_uncertain_and_note_hash_is_computed(case):
    args = params(case, ("accepted", "uncertain"))
    args["items"][1]["evidence_reference"] = ""
    receipt, _ = record_import_receipt(**args)
    assert receipt.outcome == "uncertain"
    assert receipt.evidence["kind"] == "attestation"
    assert (
        receipt.evidence["sha256"]
        == hashlib.sha256(
            args["evidence_reference"].encode("utf-8"),
        ).hexdigest()
    )


def test_audit_failure_rolls_back_receipt_and_confirmation(case, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr("apps.hub.accounting_import.record_event", fail)
    with pytest.raises(RuntimeError, match="synthetic"):
        record_import_receipt(**params(case))
    assert not AccountingImportReceipt.objects.exists()
    case["export"].refresh_from_db()
    assert case["export"].state == "ready" and case["export"].confirmed_by_id is None


def test_importer_version_and_revocation_are_rechecked_before_receipt(case):
    args = params(case)
    args["importer_version"] = "unverified importer"
    with pytest.raises(ImportReceiptError, match="versão do importador"):
        record_import_receipt(**args)
    homologate_synthetic(case["organization"], approved=False)
    with pytest.raises(ImportReceiptError, match="não está homologado"):
        record_import_receipt(**params(case))
    assert not AccountingImportReceipt.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_same_receipt_records_one_result(case):
    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks")
    barrier = Barrier(2)
    args = params(case)

    def run(_):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return record_import_receipt(**args)[1]
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(run, range(2))) == [False, True]
    assert AccountingImportReceipt.objects.count() == 1
