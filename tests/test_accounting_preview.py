from __future__ import annotations

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier, Event

import pytest
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, transaction
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.accounting_preview import create_preview, open_preview_content, preview_is_current
from apps.hub.models import (
    AccountingExport,
    AccountingExportPreview,
    AccountingPeriod,
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    JournalEntry,
    LedgerAccount,
    MovementReconciliation,
    NormalizedMovement,
    ProductModule,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_service import (
    ReconciliationError,
    approve_journal_entry,
    create_journal_entry_from_movement,
    create_source_file,
)
from apps.organizations.models import Membership, Organization

START, END = date(2026, 9, 1), date(2026, 9, 30)


@pytest.fixture
def case(db, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    settings.RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED = False
    organization = Organization.objects.create(name="Escritório sintético", slug="preview-office")
    company = ClientCompany.objects.create(organization=organization, name="Empresa sintética")
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Banco sintético",
        account_reference="synthetic-bank-account",
        ledger_code="1",
    )
    for code in ("1", "2"):
        LedgerAccount.objects.create(
            organization=organization, company=company, code=code, name=code
        )
    actor = User.objects.create_user("preview@example.test", "local-synthetic-password")
    membership = Membership.objects.create(
        organization=organization,
        user=actor,
        role=Membership.Role.OWNER,
    )
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="synthetic.csv",
        content=b"Data;Historico;Valor\n12/09/2026;Recebimento;100,00\n",
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
        financial_account=account,
    )
    movement = NormalizedMovement.objects.create(
        organization=organization,
        company=company,
        source_file=source,
        run=run,
        source_key="synthetic-movement",
        occurred_on=date(2026, 9, 12),
        amount_cents=10000,
        description="Recebimento sintético",
        debit_account_code="1",
        credit_account_code="2",
        review_state="ready",
    )
    entry = create_journal_entry_from_movement(movement=movement, actor=actor)
    entry = approve_journal_entry(entry=entry, actor=actor)
    settings.RECONCILIATION_DOMINIO_PREVIEW_ORGANIZATION_IDS = [str(organization.pk)]
    client = Client()
    client.force_login(actor)
    session = client.session
    session["hub_organization_id"] = str(organization.pk)
    session.save()
    return dict(
        organization=organization,
        company=company,
        account=account,
        actor=actor,
        membership=membership,
        movement=movement,
        entry=entry,
        client=client,
        source=source,
    )


def generate(case):
    return create_preview(
        organization=case["organization"],
        account=case["account"],
        start=START,
        end=END,
        actor=case["actor"],
    )


def selection(case):
    return dict(
        financial_account=str(case["account"].pk),
        period_start=START.isoformat(),
        period_end=END.isoformat(),
    )


def test_immutable_photo_without_export_or_journal_transition(case, settings):
    before = JournalEntry.objects.values().get(pk=case["entry"].pk)
    preview, created = generate(case)
    assert created and preview_is_current(preview)
    assert JournalEntry.objects.values().get(pk=case["entry"].pk) == before
    assert AccountingExport.objects.count() == 0
    assert settings.RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED is False
    assert preview.source_snapshot["homologated"] is False
    assert preview.source_snapshot["entries"][0]["id"] == str(case["entry"].pk)
    with open_preview_content(preview) as stream:
        content = stream.read()
    assert b"100.00" in content
    assert hashlib.sha256(content).hexdigest() == preview.content_hash
    with pytest.raises(ValidationError):
        preview.save()
    with pytest.raises(ValidationError):
        AccountingExportPreview.objects.filter(pk=preview.pk).update(content_hash="0" * 64)
    with pytest.raises(ValidationError):
        preview.delete()


def test_retry_reuses_original_bytes_and_one_creation(case):
    first, _ = generate(case)
    second, created = generate(case)
    assert first.pk == second.pk and not created
    assert AccountingExportPreview.objects.count() == 1
    assert AuditEvent.objects.filter(action="hub.reconciliation.preview_created").count() == 1


@pytest.mark.parametrize("mode", ["empty", "slug", "name", "demo", "inactive"])
def test_requires_explicit_active_non_demo_office_uuid(case, settings, mode):
    if mode in {"empty", "slug", "name"}:
        settings.RECONCILIATION_DOMINIO_PREVIEW_ORGANIZATION_IDS = {
            "empty": [],
            "slug": [case["organization"].slug],
            "name": [case["organization"].name],
        }[mode]
    else:
        setattr(case["organization"], "is_demo" if mode == "demo" else "is_active", mode == "demo")
    with pytest.raises(ReconciliationError, match="indisponível"):
        generate(case)
    assert AccountingExportPreview.objects.count() == 0


@pytest.mark.parametrize(
    "change",
    [
        "source",
        "exported",
        "draft",
        "unbalanced",
        "account_inactive",
        "period_locked",
        "wrong_bank_ledger",
        "movement_revision",
        "ignored",
        "ledger_match",
        "export_history",
    ],
)
def test_rejects_unsafe_or_already_written_facts(case, change):
    entry = case["entry"]
    if change in {"source", "exported", "draft"}:
        if change == "source":
            entry.purpose = "source_ledger"
        else:
            entry.state = change
        entry.save()
    elif change == "unbalanced":
        entry.lines.filter(side="debit").update(amount_cents=10001)
    elif change == "account_inactive":
        LedgerAccount.objects.filter(company=case["company"], code="2").update(active=False)
    elif change == "period_locked":
        AccountingPeriod.objects.create(
            organization=case["organization"],
            company=case["company"],
            starts_on=START,
            ends_on=END,
            locked_at=timezone.now(),
        )
    elif change == "wrong_bank_ledger":
        case["account"].ledger_code = "other-account"
        case["account"].save()
    elif change in {"movement_revision", "ignored"}:
        movement = case["movement"]
        if change == "ignored":
            movement.review_state = "ignored"
        else:
            movement.revision += 1
        movement.save()
    elif change == "ledger_match":
        MovementReconciliation.objects.create(
            organization=case["organization"],
            movement=case["movement"],
            entry=entry,
            amount_cents=1,
            state="confirmed",
        )
    else:
        AccountingExport.objects.create(
            organization=case["organization"],
            company=case["company"],
            period_start=START,
            period_end=END,
            state="ready",
            entry_ids=[str(entry.pk)],
        )
    with pytest.raises(ReconciliationError):
        generate(case)
    assert AccountingExportPreview.objects.count() == 0


@pytest.mark.parametrize("change", ["history", "movement", "line", "new_approval", "export"])
def test_changed_facts_make_the_preserved_photo_obsolete(case, change):
    preview, _ = generate(case)
    snapshot, digest = preview.source_snapshot, preview.content_hash
    entry = case["entry"]
    if change == "history":
        entry.history = "Histórico corrigido"
        entry.save()
    elif change == "movement":
        case["movement"].review_state = "ignored"
        case["movement"].save()
    elif change == "line":
        entry.lines.update(history="Partida corrigida")
    elif change == "new_approval":
        movement = NormalizedMovement.objects.create(
            organization=case["organization"],
            company=case["company"],
            source_file=case["source"],
            source_key="second",
            run=case["movement"].run,
            occurred_on=date(2026, 9, 13),
            amount_cents=500,
            description="Outro recebimento",
            debit_account_code="1",
            credit_account_code="2",
            review_state="ready",
        )
        approve_journal_entry(
            entry=create_journal_entry_from_movement(movement=movement), actor=case["actor"]
        )
    else:
        AccountingExport.objects.create(
            organization=case["organization"],
            company=case["company"],
            period_start=START,
            period_end=END,
            state="ready",
            entry_ids=[str(entry.pk)],
        )
    assert not preview_is_current(preview)
    preview.refresh_from_db()
    assert preview.source_snapshot == snapshot and preview.content_hash == digest
    with open_preview_content(preview) as stream:
        assert hashlib.sha256(stream.read()).hexdigest() == digest


def test_new_generation_retains_both_photos(case):
    first, _ = generate(case)
    case["entry"].history = "Correção humana revisada"
    case["entry"].save()
    second, created = generate(case)
    assert created and first.pk != second.pk
    assert not preview_is_current(first) and preview_is_current(second)
    assert AccountingExportPreview.objects.count() == 2


def test_account_and_office_scope_never_broaden_selection(case):
    other = Organization.objects.create(name="Outro escritório", slug="other-preview")
    with pytest.raises(ReconciliationError):
        create_preview(
            organization=other, account=case["account"], start=START, end=END, actor=case["actor"]
        )
    second = FinancialAccount.objects.create(
        organization=case["organization"],
        company=case["company"],
        name="Outra conta",
        ledger_code="1",
        account_reference="other",
    )
    with pytest.raises(ReconciliationError, match="Não há"):
        create_preview(
            organization=case["organization"],
            account=second,
            start=START,
            end=END,
            actor=case["actor"],
        )


def test_http_creation_download_and_audit_keep_global_export_disabled(case):
    client = case["client"]
    response = client.post(reverse("hub:reconciliation-preview"), selection(case))
    assert response.status_code == 302
    preview = AccountingExportPreview.objects.get()
    download = client.get(reverse("hub:reconciliation-preview-download", args=[preview.pk]))
    assert download.status_code == 200
    assert "previa-nao-homologada" in download["Content-Disposition"]
    assert download["Cache-Control"] == "private, no-store"
    assert hashlib.sha256(b"".join(download.streaming_content)).hexdigest() == preview.content_hash
    page = client.get(response.url)
    assert "Prévia não homologada" in page.content.decode()
    assert "Confirmar importação" not in page.content.decode()
    assert AccountingExport.objects.count() == 0
    assert AuditEvent.objects.filter(action="hub.reconciliation.preview_downloaded").exists()


@pytest.mark.parametrize(
    "bad_data",
    [{}, {"period_start": "bad"}, {"financial_account": "bad"}, {"period_end": "2026-08-01"}],
)
def test_invalid_form_preserves_input_and_creates_no_file(case, bad_data):
    values = selection(case) if bad_data else {}
    values.update(bad_data)
    response = case["client"].post(reverse("hub:reconciliation-preview"), values)
    assert response.status_code == 200 and response.context["preview_form"].errors
    assert AccountingExportPreview.objects.count() == 0


@pytest.mark.parametrize("missing", [False, True])
def test_corrupt_or_missing_file_refuses_download_and_retry_without_rewriting(case, missing):
    preview, _ = generate(case)
    if missing:
        preview.content.storage.delete(preview.content.name)
    else:
        with preview.content.storage.open(preview.content.name, "wb") as output:
            output.write(b"corrupt")
    with pytest.raises(ReconciliationError):
        generate(case)
    response = case["client"].get(reverse("hub:reconciliation-preview-download", args=[preview.pk]))
    assert response.status_code == 404
    assert AccountingExportPreview.objects.count() == 1
    assert AuditEvent.objects.filter(
        action="hub.reconciliation.preview_integrity_failed", target_id=str(preview.pk)
    ).count() == 1


def test_auditor_can_download_but_not_generate_and_ungranted_company_is_private(case):
    preview, _ = generate(case)
    member = case["membership"]
    member.role = Membership.Role.AUDITOR
    member.save()
    CompanyAccessGrant.objects.create(
        organization=case["organization"],
        membership=member,
        company=case["company"],
        modules=["reconciliation"],
        capabilities=["bank_statements", "accounting_entries"],
    )
    client = case["client"]
    assert client.get(reverse("hub:reconciliation-preview")).status_code == 200
    assert client.post(reverse("hub:reconciliation-preview"), selection(case)).status_code == 403
    response = client.get(reverse("hub:reconciliation-preview-download", args=[preview.pk]))
    assert response.status_code == 200
    assert b"100.00" in b"".join(response.streaming_content)
    CompanyAccessGrant.objects.all().delete()
    assert (
        client.get(reverse("hub:reconciliation-preview-download", args=[preview.pk])).status_code
        == 404
    )


def test_disabled_feature_hides_entrypoint_and_refuses_direct_requests(case, settings):
    settings.RECONCILIATION_DOMINIO_PREVIEW_ORGANIZATION_IDS = []
    assert case["client"].get(reverse("hub:reconciliation-preview")).status_code == 404
    assert (
        case["client"].post(reverse("hub:reconciliation-preview"), selection(case)).status_code
        == 404
    )
    assert (
        b"/app/conciliacao/previas/"
        not in case["client"].get(reverse("hub:reconciliation")).content
    )


def test_csrf_protects_creation(case):
    client = Client(enforce_csrf_checks=True)
    client.force_login(case["actor"])
    session = client.session
    session["hub_organization_id"] = str(case["organization"].pk)
    session.save()
    assert client.post(reverse("hub:reconciliation-preview"), selection(case)).status_code == 403


def test_obsolete_preview_does_not_download_as_current(case):
    preview, _ = generate(case)
    case["movement"].review_state = "ignored"
    case["movement"].save()
    response = case["client"].get(reverse("hub:reconciliation-preview-download", args=[preview.pk]))
    assert response.status_code == 302
    page = case["client"].get(response.url)
    assert "Desatualizada" in page.content.decode()
    url = reverse("hub:reconciliation-preview-download", args=[preview.pk])
    assert url.encode() not in page.content


def test_other_office_cannot_read_or_select_the_authorized_office_account(case, settings):
    preview, _ = generate(case)
    other = Organization.objects.create(name="Outro escritório", slug="other-preview-office")
    Membership.objects.create(organization=other, user=case["actor"], role="owner")
    ProductModule.objects.create(organization=other, code="reconciliation", enabled=True)
    settings.RECONCILIATION_DOMINIO_PREVIEW_ORGANIZATION_IDS = [
        str(other.pk),
        str(case["organization"].pk),
    ]
    client = case["client"]
    session = client.session
    session["hub_organization_id"] = str(other.pk)
    session.save()
    assert (
        client.get(reverse("hub:reconciliation-preview-download", args=[preview.pk])).status_code
        == 404
    )
    response = client.post(reverse("hub:reconciliation-preview"), selection(case))
    assert response.status_code == 200 and response.context["preview_form"].errors
    assert AccountingExportPreview.objects.count() == 1


def test_persistence_failure_cleans_only_its_own_new_file(case, monkeypatch, tmp_path):
    before = set(tmp_path.rglob("*.csv"))

    def fail_audit(**kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr("apps.hub.accounting_preview.record_event", fail_audit)
    with pytest.raises(RuntimeError, match="synthetic audit"):
        generate(case)
    assert AccountingExportPreview.objects.count() == 0
    assert set(tmp_path.rglob("*.csv")) == before


@pytest.mark.django_db(transaction=True)
def test_concurrent_generation_reuses_one_photo(case):
    if connection.vendor != "postgresql":
        pytest.skip("A disputa de criação exige PostgreSQL com conexões independentes.")
    barrier = Barrier(2)

    def generate_thread():
        close_old_connections()
        try:
            barrier.wait(timeout=5)
            preview, created = generate(case)
            return preview.pk, created
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(generate_thread) for _ in range(2)]
        results = [future.result(timeout=15) for future in futures]
    assert results[0][0] == results[1][0]
    assert sorted(result[1] for result in results) == [False, True]
    assert AccountingExportPreview.objects.count() == 1


@pytest.mark.django_db(transaction=True)
def test_generation_revalidates_approval_after_waiting_for_company_lock(case):
    if connection.vendor != "postgresql":
        pytest.skip("Revalidação após trava exige PostgreSQL com conexões independentes.")
    attempted = Event()

    def generate_thread():
        close_old_connections()
        try:
            attempted.set()
            return generate(case)
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=1) as executor:
        with transaction.atomic():
            ClientCompany.objects.select_for_update().get(pk=case["company"].pk)
            future = executor.submit(generate_thread)
            assert attempted.wait(timeout=5)
            JournalEntry.objects.filter(pk=case["entry"].pk).update(state="invalid")
        with pytest.raises(ReconciliationError, match="Não há"):
            future.result(timeout=15)
    assert AccountingExportPreview.objects.count() == 0
