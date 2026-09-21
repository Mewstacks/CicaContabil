from __future__ import annotations

import re
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.forms import ReconciliationUploadForm
from apps.hub.models import (
    AccountingExport,
    BankStatementImport,
    BankTransaction,
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    MovementReconciliation,
    NormalizedMovement,
    ProductModule,
    ReconciliationMatch,
    ReconciliationRule,
    ReconciliationRun,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_service import (
    ReconciliationError,
    apply_rules,
    approve_journal_entry,
    auto_reconcile_unique_movement,
    confirm_reconciliation,
    create_export,
    create_journal_entry_from_movement,
    create_source_file,
    local_ocr_available,
    prepare_run_for_layout,
    process_run,
    render_dominio_csv,
    require_review_for_low_quality_extraction,
    save_layout,
    save_rule_from_movement,
    undo_reconciliation,
)
from apps.organizations.models import Membership, Organization

CSV = (
    b"Data;Historico;Valor;Documento\n"
    b"12/09/2026;Fornecedor;1.234,56;N-1\n"
    b"13/09/2026;Cliente;-50,00;R-2\n"
)

DEFAULT_MAPPING = {
    "date": "Data",
    "description": "Historico",
    "amount": "Valor",
    "document": "Documento",
}


def _map_and_process(source: ReconciliationSourceFile, run: ReconciliationRun) -> None:
    layout = save_layout(
        source=source,
        name="Layout de teste",
        configuration={"mapping": DEFAULT_MAPPING},
    )
    prepared = prepare_run_for_layout(source=source, layout=layout)
    assert [item.id for item in prepared] == [run.id]
    process_run(str(run.id))


@pytest.mark.django_db
def test_upload_form_marks_each_financial_account_with_its_company() -> None:
    organization = Organization.objects.create(name="Seleção", slug="selecao-upload")
    first = ClientCompany.objects.create(organization=organization, name="Primeira")
    second = ClientCompany.objects.create(organization=organization, name="Segunda")
    first_account = FinancialAccount.objects.create(
        organization=organization, company=first, name="Banco 1", account_reference="001"
    )
    second_account = FinancialAccount.objects.create(
        organization=organization, company=second, name="Banco 2", account_reference="002"
    )

    form = ReconciliationUploadForm(
        companies=ClientCompany.objects.filter(organization=organization)
    )
    rendered = form["financial_account"].as_widget()

    assert f'data-company-id="{first.id}"' in rendered
    assert f'data-company-id="{second.id}"' in rendered
    assert "Selecione a conta" in rendered
    assert first_account.name in rendered
    assert second_account.name in rendered


@pytest.mark.django_db
def test_csv_auto_maps_and_saved_layout_reuses_the_structure() -> None:
    organization = Organization.objects.create(name="Módulo", slug="modulo")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    source, run, created = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )

    assert created is True
    result = process_run(str(run.id))
    run.refresh_from_db()
    assert result["state"] == ReconciliationRun.State.REVIEW, (result, run.errors)
    assert run.stage == "mapping"

    layout = save_layout(
        source=source,
        name="Extrato padrao",
        configuration={"mapping": DEFAULT_MAPPING},
    )
    assert [item.id for item in prepare_run_for_layout(source=source, layout=layout)] == [run.id]
    assert process_run(str(run.id))["state"] == ReconciliationRun.State.REVIEW
    rows = list(NormalizedMovement.objects.filter(source_file=source).order_by("source_key"))
    assert [row.amount_cents for row in rows] == [123456, -5000]
    assert rows[0].source_reference["row"] == 2
    assert layout.version == 1
    with pytest.raises(ReconciliationError, match="não existe neste arquivo"):
        save_layout(
            source=source,
            name="Layout inválido",
            configuration={"mapping": {**DEFAULT_MAPPING, "document": "Coluna inventada"}},
        )
    with pytest.raises(ReconciliationError, match="mais de um campo"):
        save_layout(
            source=source,
            name="Layout duplicado",
            configuration={"mapping": {**DEFAULT_MAPPING, "document": "Historico"}},
        )
    updated_layout = save_layout(
        source=source,
        name="Extrato padrao",
        configuration=layout.configuration,
    )
    layout.refresh_from_db()
    assert layout.active is False
    assert updated_layout.version == 2

    next_source, next_run, next_created = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos-outubro.csv",
        content=(b"Data;Historico;Valor;Documento\n14/10/2026;Fornecedor novo;20,00;N-2\n"),
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )

    assert next_created is True
    assert next_run.layout_version_id == updated_layout.id
    assert next_run.checkpoint["layout_selected_automatically"] is True
    assert process_run(str(next_run.id))["state"] == ReconciliationRun.State.REVIEW
    assert NormalizedMovement.objects.filter(source_file=next_source).count() == 1

    _changed_source, changed_run, changed_created = create_source_file(
        organization=organization,
        company=company,
        filename="estrutura-diferente.csv",
        content=b"Data;Narrativa;Valor;Documento\n15/10/2026;Outro;10,00;N-3\n",
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    assert changed_created is True
    assert changed_run.layout_version is None


@pytest.mark.django_db
def test_upload_keeps_company_selection_visible() -> None:
    organization = Organization.objects.create(name="Envio", slug="envio")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")

    form = ReconciliationUploadForm(companies=ClientCompany.objects.filter(id=company.id))

    assert form.fields["company"].widget.input_type == "select"


@pytest.mark.django_db
def test_upload_view_creates_a_persisted_csv_run(
    django_capture_on_commit_callbacks: object,
) -> None:
    organization = Organization.objects.create(name="Envio web", slug="envio-web")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@envio.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    with (
        patch("apps.hub.tasks.process_reconciliation_run.delay") as dispatch,
        django_capture_on_commit_callbacks(execute=True),  # type: ignore[operator]
    ):
        response = client.post(
            reverse("hub:reconciliation-upload"),
            {
                "company": str(company.id),
                "origin": ReconciliationSourceFile.Origin.BANK_STATEMENT,
                "period_start": "2026-09-01",
                "period_end": "2026-09-30",
                "files": SimpleUploadedFile("extrato.csv", CSV, content_type="text/csv"),
            },
        )

    assert response.status_code == 302
    source = ReconciliationSourceFile.objects.get(organization=organization)
    run = ReconciliationRun.objects.get(source_file=source)
    assert source.company_id == company.id
    assert run.state == ReconciliationRun.State.WAITING
    dispatch.assert_called_once_with(str(run.id))
    assert AuditEvent.objects.filter(
        action="hub.reconciliation.source_uploaded", target_id=str(source.id)
    ).exists()


@pytest.mark.django_db
def test_upload_view_rejects_a_corrupted_xlsx_without_creating_a_source() -> None:
    organization = Organization.objects.create(name="XLSX inválido", slug="xlsx-invalido")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@xlsx.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    response = client.post(
        reverse("hub:reconciliation-upload"),
        {
            "company": str(company.id),
            "origin": ReconciliationSourceFile.Origin.BANK_STATEMENT,
            "period_start": "2026-09-01",
            "period_end": "2026-09-30",
            "files": SimpleUploadedFile(
                "corrompido.xlsx", b"PK\x03\x04 sem uma planilha", content_type="application/zip"
            ),
        },
        follow=True,
    )

    assert response.status_code == 200
    assert b"n\xc3\xa3o foi poss\xc3\xadvel abrir a planilha xlsx" in response.content.lower()
    assert not ReconciliationSourceFile.objects.filter(organization=organization).exists()


@pytest.mark.django_db
def test_corrupted_xlsx_is_rejected_before_persistence() -> None:
    organization = Organization.objects.create(name="Arquivo corrompido", slug="arquivo-corrompido")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")

    with pytest.raises(ReconciliationError, match="Não foi possível abrir a planilha XLSX"):
        create_source_file(
            organization=organization,
            company=company,
            filename="corrompido.xlsx",
            content=b"PK\x03\x04 sem uma planilha",
            origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
        )

    assert not ReconciliationSourceFile.objects.filter(organization=organization).exists()


@pytest.mark.django_db
def test_upload_validation_keeps_errors_visible_in_the_assistant() -> None:
    organization = Organization.objects.create(name="Erros de envio", slug="erros-envio")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@erros-envio.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    response = client.post(
        reverse("hub:reconciliation-upload"),
        {
            "company": str(company.id),
            "origin": ReconciliationSourceFile.Origin.BANK_STATEMENT,
            "period_start": "2026-10-01",
            "period_end": "2026-09-01",
        },
    )

    assert response.status_code == 400
    assert b"data-form-errors" in response.content
    assert b"fim do per" in response.content.lower()
    assert b"Selecione ao menos um arquivo" in response.content


@pytest.mark.django_db
def test_identical_source_is_idempotent_and_keeps_original() -> None:
    organization = Organization.objects.create(name="Idempotência", slug="idempotencia")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    first, run, created = create_source_file(
        organization=organization,
        company=company,
        filename="a.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    repeated, repeated_run, repeated_created = create_source_file(
        organization=organization,
        company=company,
        filename="renomeado.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )

    assert created is True
    assert repeated_created is False
    assert repeated.id == first.id
    assert repeated_run.id == run.id
    assert first.content.name


@pytest.mark.django_db
@override_settings(RECONCILIATION_DOMINIO_EXPORT_HOMOLOGATED=True)
def test_export_is_immutable_and_rejects_unbalanced_entry() -> None:
    organization = Organization.objects.create(name="Exportação", slug="exportacao")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    LedgerAccount.objects.create(organization=organization, company=company, code="1", name="Banco")
    LedgerAccount.objects.create(
        organization=organization, company=company, code="2", name="Despesa"
    )
    entry = JournalEntry.objects.create(
        organization=organization,
        company=company,
        occurred_on=date(2026, 9, 12),
        history="Pagamento",
        purpose="record",
        state=JournalEntry.State.APPROVED,
    )
    JournalLine.objects.create(
        organization=organization,
        entry=entry,
        account_code="1",
        side=JournalLine.Side.DEBIT,
        amount_cents=1250,
    )
    JournalLine.objects.create(
        organization=organization,
        entry=entry,
        account_code="2",
        side=JournalLine.Side.CREDIT,
        amount_cents=1250,
    )

    exported = create_export(
        organization=organization, company=company, start=date(2026, 9, 1), end=date(2026, 9, 30)
    )

    assert exported.content_hash
    assert exported.content.read().startswith(b"\xef\xbb\xbfData;")
    entry.refresh_from_db()
    assert entry.state == JournalEntry.State.EXPORTED
    reexported = create_export(
        organization=organization,
        company=company,
        start=date(2026, 9, 1),
        end=date(2026, 9, 30),
        reexport_of=exported,
        reexport_reason="Reenvio para conferência",
    )
    assert reexported.reexport_of_id == exported.id
    assert reexported.content_hash == exported.content_hash


@pytest.mark.django_db
def test_reconciliation_allocation_needs_independent_evidence_and_preserves_capacity() -> None:
    organization = Organization.objects.create(name="Conciliação", slug="conciliacao")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(source, run)
    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    LedgerAccount.objects.bulk_create(
        [
            LedgerAccount(organization=organization, company=company, code="1", name="Banco"),
            LedgerAccount(organization=organization, company=company, code="2", name="Despesa"),
        ]
    )
    entry = JournalEntry.objects.create(
        organization=organization,
        company=company,
        occurred_on=date(2026, 9, 12),
        history="Obrigação existente",
        purpose="settlement",
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                organization=organization,
                entry=entry,
                account_code="1",
                side=JournalLine.Side.DEBIT,
                amount_cents=60000,
            ),
            JournalLine(
                organization=organization,
                entry=entry,
                account_code="2",
                side=JournalLine.Side.CREDIT,
                amount_cents=60000,
            ),
        ]
    )

    reconciliation = confirm_reconciliation(
        movement=movement,
        entry=entry,
        amount_cents=60000,
        evidence={"document": "N-1"},
    )

    second_entry = JournalEntry.objects.create(
        organization=organization,
        company=company,
        occurred_on=date(2026, 9, 12),
        history="Obrigação complementar",
        purpose="settlement",
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                organization=organization,
                entry=second_entry,
                account_code="1",
                side=JournalLine.Side.DEBIT,
                amount_cents=63456,
            ),
            JournalLine(
                organization=organization,
                entry=second_entry,
                account_code="2",
                side=JournalLine.Side.CREDIT,
                amount_cents=63456,
            ),
        ]
    )
    second_reconciliation = confirm_reconciliation(
        movement=movement,
        entry=second_entry,
        amount_cents=63456,
        evidence={"document": "N-2"},
    )

    assert reconciliation.amount_cents + second_reconciliation.amount_cents == 123456
    third_entry = JournalEntry.objects.create(
        organization=organization,
        company=company,
        occurred_on=date(2026, 9, 12),
        history="Obrigação adicional",
        purpose="settlement",
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                organization=organization,
                entry=third_entry,
                account_code="1",
                side=JournalLine.Side.DEBIT,
                amount_cents=1,
            ),
            JournalLine(
                organization=organization,
                entry=third_entry,
                account_code="2",
                side=JournalLine.Side.CREDIT,
                amount_cents=1,
            ),
        ]
    )
    with pytest.raises(ReconciliationError, match="excede"):
        confirm_reconciliation(
            movement=movement,
            entry=third_entry,
            amount_cents=1,
            evidence={"document": "N-1"},
        )
    undo_reconciliation(reconciliation=second_reconciliation)
    second_reconciliation.refresh_from_db()
    assert second_reconciliation.state == "undone"
    assert (
        confirm_reconciliation(
            movement=movement,
            entry=third_entry,
            amount_cents=1,
            evidence={"document": "N-3"},
        ).amount_cents
        == 1
    )


@pytest.mark.django_db
def test_reconciliation_detail_offers_a_partial_candidate_with_its_real_limit() -> None:
    organization = Organization.objects.create(name="Parcial", slug="parcial-ui")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@parcial.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(source, run)
    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    partial_entry = JournalEntry.objects.create(
        organization=organization,
        company=company,
        occurred_on=movement.occurred_on,
        history="Pagamento Fornecedor N-1",
        purpose="settlement",
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                organization=organization,
                entry=partial_entry,
                account_code="1",
                side="debit",
                amount_cents=60_000,
            ),
            JournalLine(
                organization=organization,
                entry=partial_entry,
                account_code="2",
                side="credit",
                amount_cents=60_000,
            ),
        ]
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    response = client.get(reverse("hub:reconciliation-movement", args=[movement.id]))

    content = response.content.decode()
    assert response.status_code == 200
    assert f'value="{partial_entry.id}"' in content
    allocation_limit = re.search(r'data-allocation-limit="([^"]+)"', content)
    maximum = re.search(r' id="amount-brl"[^>]* max="([^"]+)"', content)
    assert allocation_limit, content
    assert maximum, content
    assert allocation_limit.group(1) == "600.00"
    assert maximum.group(1) == "600.00"


@pytest.mark.django_db
def test_reconciliation_detail_pages_all_matching_candidates_without_a_silent_cutoff() -> None:
    organization = Organization.objects.create(name="Candidatos", slug="candidatos-ui")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@candidatos.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(source, run)
    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    entries = [
        JournalEntry.objects.create(
            organization=organization,
            company=company,
            occurred_on=movement.occurred_on,
            history=f"Fornecedor N-1 candidato {index:02d}",
            purpose="settlement",
        )
        for index in range(51)
    ]
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                organization=organization,
                entry=entry,
                account_code="1",
                side=JournalLine.Side.DEBIT,
                amount_cents=123_456,
            )
            for entry in entries
        ]
        + [
            JournalLine(
                organization=organization,
                entry=entry,
                account_code="2",
                side=JournalLine.Side.CREDIT,
                amount_cents=123_456,
            )
            for entry in entries
        ]
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()
    url = reverse("hub:reconciliation-movement", args=[movement.id])

    pages = [client.get(url, {"candidate_page": page}) for page in range(1, 4)]

    assert all(page.status_code == 200 for page in pages)
    assert pages[0].context["reconciliation_candidate_total"] == 51
    assert pages[0].context["reconciliation_candidate_page"].number == 1
    assert pages[2].context["reconciliation_candidate_page"].number == 3
    assert [len(page.context["reconciliation_candidates"]) for page in pages] == [25, 25, 1]
    presented_ids = {
        suggestion["entry"].id
        for page in pages
        for suggestion in page.context["reconciliation_candidates"]
    }
    assert presented_ids == {entry.id for entry in entries}
    assert "Página 1 de 3 · 51 lançamentos avaliados" in pages[0].content.decode()
    assert "candidate_page=2" in pages[0].content.decode()
    assert "candidate_page=3" in pages[1].content.decode()


@pytest.mark.django_db
def test_exact_unique_documentary_match_is_auto_confirmed_and_ambiguity_is_not() -> None:
    organization = Organization.objects.create(name="Automática", slug="automatica")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(source, run)
    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    movement.review_state = NormalizedMovement.ReviewState.READY
    movement.save(update_fields=["review_state", "updated_at"])

    def approved_entry(history: str, occurred_on: date) -> JournalEntry:
        entry = JournalEntry.objects.create(
            organization=organization,
            company=company,
            occurred_on=occurred_on,
            history=history,
            purpose="settlement",
            state=JournalEntry.State.APPROVED,
        )
        JournalLine.objects.bulk_create(
            [
                JournalLine(
                    organization=organization,
                    entry=entry,
                    account_code="1",
                    side="debit",
                    amount_cents=123456,
                ),
                JournalLine(
                    organization=organization,
                    entry=entry,
                    account_code="2",
                    side="credit",
                    amount_cents=123456,
                ),
            ]
        )
        return entry

    entry = approved_entry("Liquidação documento N-1", movement.occurred_on)
    matched = auto_reconcile_unique_movement(movement)

    assert matched is not None
    assert matched.entry_id == entry.id
    assert matched.evidence["method"] == "deterministic_exact_1to1"
    assert AuditEvent.objects.filter(
        organization=organization,
        action="hub.reconciliation.auto_confirmed",
        target_id=str(matched.id),
    ).exists()

    second_source, second_run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="ambigua.csv",
        content=CSV.replace(b"12/09/2026", b"14/09/2026"),
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(second_source, second_run)
    ambiguous_movement = NormalizedMovement.objects.get(
        source_file=second_source, source_key="row:2"
    )
    ambiguous_movement.review_state = NormalizedMovement.ReviewState.READY
    ambiguous_movement.save(update_fields=["review_state", "updated_at"])
    approved_entry("Liquidação documento N-1 alternativa", ambiguous_movement.occurred_on)
    approved_entry("Liquidação documento N-1 duplicada", ambiguous_movement.occurred_on)

    assert auto_reconcile_unique_movement(ambiguous_movement) is None
    assert not ambiguous_movement.reconciliations.filter(state="confirmed").exists()


@pytest.mark.django_db
def test_duplicate_records_in_one_batch_stay_pending_for_manual_reconciliation() -> None:
    organization = Organization.objects.create(name="Lote ambÃ­guo", slug="lote-ambiguo")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ReconciliationRule.objects.create(
        organization=organization,
        company=company,
        name="Classifica fornecedor",
        state=ReconciliationRule.State.ACTIVE,
        all_conditions=[{"field": "description", "operator": "equals", "value": "Fornecedor"}],
        actions={
            "debit_account_code": "1",
            "credit_account_code": "2",
            "accounting_history": "Fornecedor",
        },
    )
    entry = JournalEntry.objects.create(
        organization=organization,
        company=company,
        occurred_on=date(2026, 9, 12),
        history="LiquidaÃ§Ã£o documento N-1",
        purpose="settlement",
        state=JournalEntry.State.APPROVED,
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                organization=organization,
                entry=entry,
                account_code="1",
                side="debit",
                amount_cents=123456,
            ),
            JournalLine(
                organization=organization,
                entry=entry,
                account_code="2",
                side="credit",
                amount_cents=123456,
            ),
        ]
    )
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="duplicados.csv",
        content=(
            b"Data;Historico;Valor;Documento\n"
            b"12/09/2026;Fornecedor;1.234,56;N-1\n"
            b"12/09/2026;Fornecedor;1.234,56;N-1\n"
        ),
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )

    _map_and_process(source, run)

    movements = NormalizedMovement.objects.filter(source_file=source)
    assert movements.count() == 2
    assert not movements.filter(reconciliations__state="confirmed").exists()
    assert MovementReconciliation.objects.filter(entry=entry).count() == 0


@pytest.mark.django_db
def test_classified_movement_creates_a_balanced_draft_entry() -> None:
    organization = Organization.objects.create(name="Lançamentos", slug="lancamentos")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(source, run)
    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    movement.debit_account_code = "1"
    movement.credit_account_code = "2"
    movement.accounting_history = "Lançamento testado"
    movement.save()
    LedgerAccount.objects.bulk_create(
        [
            LedgerAccount(organization=organization, company=company, code="1", name="Banco"),
            LedgerAccount(organization=organization, company=company, code="2", name="Despesa"),
        ]
    )

    entry = create_journal_entry_from_movement(movement=movement)

    assert entry.state == JournalEntry.State.DRAFT
    assert entry.source_movement_revision == movement.revision
    assert sum(line.amount_cents for line in entry.lines.filter(side="debit")) == sum(
        line.amount_cents for line in entry.lines.filter(side="credit")
    )
    assert approve_journal_entry(entry=entry).state == JournalEntry.State.APPROVED


@pytest.mark.django_db
def test_changed_source_revision_invalidates_journal_approval() -> None:
    organization = Organization.objects.create(name="Revisão", slug="revisao")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(source, run)
    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    movement.debit_account_code = "1"
    movement.credit_account_code = "2"
    movement.accounting_history = "Pagamento"
    movement.save()
    LedgerAccount.objects.bulk_create(
        [
            LedgerAccount(organization=organization, company=company, code="1", name="Banco"),
            LedgerAccount(organization=organization, company=company, code="2", name="Despesa"),
        ]
    )
    entry = create_journal_entry_from_movement(movement=movement)
    movement.revision += 1
    movement.save(update_fields=["revision", "updated_at"])

    with pytest.raises(ReconciliationError, match="origem mudou"):
        approve_journal_entry(entry=entry)

    entry.refresh_from_db()
    assert entry.state == JournalEntry.State.INVALID


@pytest.mark.django_db
def test_dominio_export_is_blocked_until_homologated() -> None:
    organization = Organization.objects.create(name="Bloqueio Domínio", slug="bloqueio-dominio")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")

    with pytest.raises(ReconciliationError, match="bloqueada"):
        create_export(
            organization=organization,
            company=company,
            start=date(2026, 9, 1),
            end=date(2026, 9, 30),
        )


@pytest.mark.django_db
def test_siescon_export_is_explicitly_blocked_without_a_reviewed_adapter() -> None:
    organization = Organization.objects.create(name="Siescon", slug="siescon")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")

    with pytest.raises(ReconciliationError, match="Siescon está bloqueada"):
        create_export(
            organization=organization,
            company=company,
            start=date(2026, 9, 1),
            end=date(2026, 9, 30),
            target="siescon",
        )


@pytest.mark.django_db
def test_dominio_export_rejects_unhomologated_compound_pairing() -> None:
    organization = Organization.objects.create(name="Domínio", slug="dominio")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    LedgerAccount.objects.bulk_create(
        [
            LedgerAccount(organization=organization, company=company, code="1", name="Banco"),
            LedgerAccount(organization=organization, company=company, code="2", name="Despesa"),
            LedgerAccount(organization=organization, company=company, code="3", name="Taxa"),
        ]
    )
    entry = JournalEntry.objects.create(
        organization=organization,
        company=company,
        occurred_on=date(2026, 9, 12),
        history="Pagamento composto",
        purpose="record",
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                organization=organization,
                entry=entry,
                account_code="1",
                side="debit",
                amount_cents=1000,
            ),
            JournalLine(
                organization=organization,
                entry=entry,
                account_code="2",
                side="credit",
                amount_cents=800,
            ),
            JournalLine(
                organization=organization,
                entry=entry,
                account_code="3",
                side="credit",
                amount_cents=200,
            ),
        ]
    )

    with pytest.raises(ReconciliationError, match="quantidades diferentes"):
        render_dominio_csv([entry])


@pytest.mark.django_db
def test_manual_correction_can_be_saved_as_a_company_rule() -> None:
    organization = Organization.objects.create(name="Regras", slug="regras")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(source, run)
    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    movement.debit_account_code = "1"
    movement.credit_account_code = "2"
    movement.accounting_history = "Fornecedor"
    movement.save()

    rule = save_rule_from_movement(movement=movement)

    assert rule.state == "active"
    assert rule.all_conditions[0]["value"] == "Fornecedor"

    next_source, next_run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos-segundo-lote.csv",
        content=(b"Data;Historico;Valor;Documento\n14/09/2026;Fornecedor;75,00;N-2\n"),
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    process_run(str(next_run.id))
    applied = NormalizedMovement.objects.get(source_file=next_source, source_key="row:2")

    assert applied.classification_source == NormalizedMovement.ClassificationSource.RULE
    assert applied.applied_rule_id == rule.id
    assert applied.debit_account_code == "1"
    assert applied.credit_account_code == "2"


@pytest.mark.django_db
def test_conflicting_rules_stay_in_review() -> None:
    organization = Organization.objects.create(name="Conflitos", slug="conflitos")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    condition = [
        {"field": "description", "operator": "equals", "value": "Fornecedor"},
        {"field": "direction", "operator": "equals", "value": "inflow"},
    ]
    ReconciliationRule.objects.bulk_create(
        [
            ReconciliationRule(
                organization=organization,
                company=company,
                name="Conta A",
                priority=10,
                state=ReconciliationRule.State.ACTIVE,
                all_conditions=condition,
                actions={"debit_account_code": "1", "credit_account_code": "2"},
            ),
            ReconciliationRule(
                organization=organization,
                company=company,
                name="Conta B",
                priority=20,
                state=ReconciliationRule.State.ACTIVE,
                all_conditions=condition,
                actions={"debit_account_code": "3", "credit_account_code": "2"},
            ),
        ]
    )
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="conflito.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )

    _map_and_process(source, run)
    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")

    assert movement.review_state == NormalizedMovement.ReviewState.CONFLICT
    assert movement.confidence_details["rule_conflicts"] == ["debit_account_code"]
    assert len(movement.confidence_details["rules"]) == 2


@pytest.mark.django_db
def test_rule_actions_keep_review_and_ignore_as_distinct_states() -> None:
    organization = Organization.objects.create(name="Ações", slug="acoes")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ReconciliationRule.objects.bulk_create(
        [
            ReconciliationRule(
                organization=organization,
                company=company,
                name="Revisar tarifa",
                state=ReconciliationRule.State.ACTIVE,
                all_conditions=[{"field": "description", "operator": "equals", "value": "Tarifa"}],
                actions={"review": True},
            ),
            ReconciliationRule(
                organization=organization,
                company=company,
                name="Ignorar saldo",
                state=ReconciliationRule.State.ACTIVE,
                all_conditions=[{"field": "description", "operator": "equals", "value": "Saldo"}],
                actions={"ignore": True},
            ),
        ]
    )
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="acoes.csv",
        content=(
            b"Data;Historico;Valor;Documento\n"
            b"12/09/2026;Tarifa;10,00;T-1\n"
            b"13/09/2026;Saldo;20,00;S-1\n"
        ),
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )

    _map_and_process(source, run)
    run.refresh_from_db()

    review = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    ignored = NormalizedMovement.objects.get(source_file=source, source_key="row:3")
    assert review.review_state == NormalizedMovement.ReviewState.PENDING
    assert ignored.review_state == NormalizedMovement.ReviewState.IGNORED
    assert ignored.classification_source == NormalizedMovement.ClassificationSource.RULE
    assert run.ignored_count == 1
    with pytest.raises(ReconciliationError, match="Desfaça o ignorar"):
        create_journal_entry_from_movement(movement=ignored)


@pytest.mark.django_db
def test_low_quality_ocr_stays_pending_even_when_a_rule_matches() -> None:
    organization = Organization.objects.create(name="OCR incerto", slug="ocr-incerto")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.DOCUMENT,
    )
    _map_and_process(source, run)
    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    movement.confidence = 62
    movement.confidence_details = {"method": "tesseract-local", "reading_quality": 62}
    movement.save(update_fields=["confidence", "confidence_details", "updated_at"])
    ReconciliationRule.objects.create(
        organization=organization,
        company=company,
        name="Classificação OCR",
        state=ReconciliationRule.State.ACTIVE,
        all_conditions=[{"field": "description", "operator": "contains", "value": "fornecedor"}],
        actions={"debit_account_code": "1", "credit_account_code": "2"},
    )

    apply_rules(movement)
    require_review_for_low_quality_extraction(movement)

    movement.refresh_from_db()
    assert movement.classification_source == NormalizedMovement.ClassificationSource.RULE
    assert movement.review_state == NormalizedMovement.ReviewState.PENDING
    assert movement.confidence_details["requires_review"] == "low_ocr_quality"


@pytest.mark.django_db
def test_rule_can_match_only_the_configured_financial_account() -> None:
    organization = Organization.objects.create(name="Conta regra", slug="conta-regra")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Banco principal",
        account_reference="001:123",
    )
    rule = ReconciliationRule.objects.create(
        organization=organization,
        company=company,
        name="Somente banco principal",
        state=ReconciliationRule.State.ACTIVE,
        all_conditions=[{"field": "financial_account", "operator": "equals", "value": "001:123"}],
        actions={"accounting_history": "Banco principal"},
    )
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        financial_account=account,
        filename="referencia.csv",
        content=b"Data;Historico;Valor;Documento\n12/09/2026;Movimento;1,00;R-1\n",
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(source, run)
    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    assert movement.financial_account_id == account.id
    assert movement.applied_rule_id == rule.id
    assert movement.accounting_history == "Banco principal"
    movement.debit_account_code = "1"
    movement.credit_account_code = "2"
    movement.save(update_fields=["debit_account_code", "credit_account_code", "updated_at"])
    learned_rule = save_rule_from_movement(movement=movement)
    assert learned_rule.all_conditions[0] == {
        "field": "financial_account",
        "operator": "equals",
        "value": "001:123",
    }


@pytest.mark.django_db
def test_rule_reapplication_preserves_manual_and_posting_decisions() -> None:
    organization = Organization.objects.create(name="Reaplicar regras", slug="reaplicar-regras")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    source, original_run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(source, original_run)
    supplier = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    manual = NormalizedMovement.objects.get(source_file=source, source_key="row:3")
    manual.classification_source = NormalizedMovement.ClassificationSource.MANUAL
    manual.debit_account_code = "manual-debit"
    manual.credit_account_code = "manual-credit"
    manual.accounting_history = "Decisão humana"
    manual.save()
    rule = ReconciliationRule.objects.create(
        organization=organization,
        company=company,
        name="Fornecedor automático",
        state=ReconciliationRule.State.ACTIVE,
        all_conditions=[{"field": "description", "operator": "contains", "value": "fornecedor"}],
        actions={
            "debit_account_code": "1",
            "credit_account_code": "2",
            "accounting_history": "Pagamento de fornecedor",
        },
    )
    reapplied = ReconciliationRun.objects.create(
        organization=organization,
        source_file=source,
        continued_from=original_run,
        checkpoint={"mode": "rules"},
    )

    result = process_run(str(reapplied.id))

    reapplied.refresh_from_db()
    supplier.refresh_from_db()
    manual.refresh_from_db()
    assert result["state"] == ReconciliationRun.State.COMPLETED_ALERTS
    assert reapplied.updated_count == 1
    assert supplier.applied_rule_id == rule.id
    assert supplier.review_state == NormalizedMovement.ReviewState.READY
    assert supplier.debit_account_code == "1"
    assert manual.classification_source == NormalizedMovement.ClassificationSource.MANUAL
    assert manual.accounting_history == "Decisão humana"

    LedgerAccount.objects.bulk_create(
        [
            LedgerAccount(organization=organization, company=company, code="1", name="Banco"),
            LedgerAccount(organization=organization, company=company, code="2", name="Despesa"),
        ]
    )
    create_journal_entry_from_movement(movement=supplier)
    protected_reapplication = ReconciliationRun.objects.create(
        organization=organization,
        source_file=source,
        continued_from=reapplied,
        checkpoint={"mode": "rules"},
    )

    protected_result = process_run(str(protected_reapplication.id))

    protected_reapplication.refresh_from_db()
    supplier.refresh_from_db()
    assert protected_result["state"] == ReconciliationRun.State.COMPLETED_ALERTS
    assert protected_reapplication.updated_count == 0
    assert protected_reapplication.error_count == 1
    assert supplier.applied_rule_id == rule.id


@pytest.mark.django_db
def test_ofx_account_mismatch_waits_for_review_without_creating_movements() -> None:
    organization = Organization.objects.create(name="OFX conta", slug="ofx-conta")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Conta selecionada",
        account_reference="001:999",
    )
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        financial_account=account,
        filename="outra-conta.ofx",
        content=(
            b"OFXHEADER:100\n<OFX><BANKMSGSRSV1><STMTRS><BANKACCTFROM>"
            b"<BANKID>001<ACCTID>123</BANKACCTFROM><BANKTRANLIST><STMTTRN>"
            b"<DTPOSTED>20260912<TRNAMT>1.00<FITID>fit-1<NAME>Teste</STMTTRN>"
            b"</BANKTRANLIST></STMTRS></BANKMSGSRSV1></OFX>"
        ),
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )

    result = process_run(str(run.id))
    run.refresh_from_db()

    assert result["state"] == "review"
    assert run.stage == "financial_account_review"
    assert run.errors[0]["code"] == "financial_account_mismatch"
    assert not NormalizedMovement.objects.filter(source_file=source).exists()


@pytest.mark.django_db
def test_reconciliation_overview_renders_ofx_source_reference() -> None:
    organization = Organization.objects.create(name="OFX tela", slug="ofx-tela")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@ofx-tela.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    _source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="extrato.ofx",
        content=(
            b"OFXHEADER:100\n<OFX><BANKMSGSRSV1><STMTTRS><BANKACCTFROM>"
            b"<BANKID>001<ACCTID>123</BANKACCTFROM><BANKTRANLIST><STMTTRN>"
            b"<DTPOSTED>20260912<TRNAMT>-1.00<FITID>fit-tela<NAME>Fornecedor OFX"
            b"</STMTTRN></BANKTRANLIST></STMTRS></BANKMSGSRSV1></OFX>"
        ),
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    process_run(str(run.id))
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    response = client.get(reverse("hub:reconciliation"))

    assert response.status_code == 200
    assert b"OFX fit-tela" in response.content
    assert b"Fornecedor OFX" in response.content


@pytest.mark.django_db
def test_reconciliation_overview_paginates_the_full_filtered_queue() -> None:
    organization = Organization.objects.create(name="Fila OFX", slug="fila-ofx")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@fila-ofx.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    statement = BankStatementImport.objects.create(
        organization=organization,
        company=company,
        original_filename="fila.ofx",
        content_hash="f" * 64,
        imported_by=user,
    )
    for index in range(101):
        transaction = BankTransaction.objects.create(
            organization=organization,
            statement=statement,
            external_id=f"queue-{index:03d}",
            occurred_on=date(2026, 1, 1) + timedelta(days=index),
            description=f"Fila paginada {index:03d}",
            amount_cents=-1_000,
        )
        ReconciliationMatch.objects.create(
            organization=organization,
            transaction=transaction,
            status=ReconciliationMatch.Status.UNMATCHED,
        )
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    first_page = client.get(reverse("hub:reconciliation"), {"q": "Fila paginada"})
    last_page = client.get(
        reverse("hub:reconciliation"),
        {
            "q": "Fila paginada",
            "processing_page": "2",
            "export_page": "2",
            "movement_page": "2",
            "page": "3",
        },
    )

    assert first_page.status_code == 200
    assert b"101 resultados na fila atual" in first_page.content
    assert b"P\xc3\xa1gina 1 de 3" in first_page.content
    assert b"Fila paginada 100" in first_page.content
    assert b"Fila paginada 000" not in first_page.content
    assert b"P\xc3\xa1gina 3 de 3" in last_page.content
    assert b"Fila paginada 000" in last_page.content
    assert (
        b"?q=Fila+paginada&amp;processing_page=2&amp;export_page=2&amp;movement_page=2"
        b"&amp;status=attention&amp;page=2"
        in last_page.content
    )


@pytest.mark.django_db
def test_reconciliation_keeps_processing_and_export_histories_independent() -> None:
    organization = Organization.objects.create(name="Históricos", slug="historicos-conciliacao")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@historicos.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    source, _run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="historico.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    for index in range(20):
        ReconciliationRun.objects.create(
            organization=organization,
            source_file=source,
            state=ReconciliationRun.State.COMPLETED,
            stage=f"completed-{index}",
        )
    for index in range(21):
        AccountingExport.objects.create(
            organization=organization,
            company=company,
            period_start=date(2026, 1, 1),
            period_end=date(2026, 1, 31),
            state=AccountingExport.State.READY,
            content_hash=f"{index:064x}",
        )
    for index in range(51):
        NormalizedMovement.objects.create(
            organization=organization,
            run=_run,
            source_file=source,
            company=company,
            source_key=f"navigation-{index}",
            occurred_on=date(2026, 1, 1),
            amount_cents=100,
            direction=NormalizedMovement.Direction.OUTFLOW,
            description=f"Movimento {index}",
        )
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    first_page = client.get(reverse("hub:reconciliation"), {"status": "all"})
    processing_page = client.get(
        reverse("hub:reconciliation"), {"status": "all", "processing_page": "2"}
    )
    export_page = client.get(
        reverse("hub:reconciliation"), {"status": "all", "export_page": "2"}
    )
    movement_page = client.get(
        reverse("hub:reconciliation"),
        {"status": "all", "processing_page": "2", "export_page": "2", "movement_page": "2"},
    )

    assert first_page.status_code == 200
    assert first_page.context["reconciliation_runs_total"] == 21
    assert first_page.context["accounting_exports_total"] == 21
    assert len(first_page.context["reconciliation_runs"]) == 20
    assert len(first_page.context["accounting_exports"]) == 20
    assert b"21 processamentos" in first_page.content
    assert b"21 exporta\xc3\xa7\xc3\xb5es" in first_page.content
    assert b"?status=all&amp;processing_page=2#processamentos" in first_page.content
    assert b"?status=all&amp;export_page=2#exportacoes" in first_page.content
    assert processing_page.context["reconciliation_runs_page"].number == 2
    assert processing_page.context["accounting_exports_page"].number == 1
    assert len(processing_page.context["reconciliation_runs"]) == 1
    assert export_page.context["reconciliation_runs_page"].number == 1
    assert export_page.context["accounting_exports_page"].number == 2
    assert len(export_page.context["accounting_exports"]) == 1
    assert movement_page.context["reconciliation_runs_page"].number == 2
    assert movement_page.context["accounting_exports_page"].number == 2
    assert movement_page.context["normalized_movement_page"].number == 2
    assert len(movement_page.context["normalized_movements"]) == 1
    assert (
        b"?status=all&amp;processing_page=2&amp;export_page=2&amp;movement_page=1#movimentos"
        in movement_page.content
    )


@pytest.mark.django_db
def test_reconciliation_audit_paginates_the_full_filtered_history() -> None:
    organization = Organization.objects.create(name="Auditoria paginada", slug="auditoria-paginada")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@auditoria-paginada.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    for index in range(201):
        AuditEvent.objects.create(
            organization=organization,
            actor=user,
            action="hub.reconciliation.audit_pagination",
            target_type="test.event",
            target_id=f"audit-{index:03d}",
        )
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    first_page = client.get(
        reverse("hub:reconciliation-audit"), {"action": "hub.reconciliation.audit_pagination"}
    )
    last_page = client.get(
        reverse("hub:reconciliation-audit"),
        {"action": "hub.reconciliation.audit_pagination", "page": "3"},
    )

    assert first_page.status_code == 200
    assert first_page.context["reconciliation_audit_total"] == 201
    assert first_page.context["reconciliation_audit_page"].number == 1
    assert len(first_page.context["reconciliation_audit_events"]) == 100
    assert last_page.context["reconciliation_audit_page"].number == 3
    assert [event.target_id for event in last_page.context["reconciliation_audit_events"]] == [
        "audit-000"
    ]
    assert b"201 eventos" in first_page.content
    assert "Página 3 de 3" in last_page.content.decode()
    assert (
        b"?action=hub.reconciliation.audit_pagination&amp;page=2" in last_page.content
    )


@pytest.mark.django_db
def test_ignore_rule_conflicts_with_another_matching_action() -> None:
    organization = Organization.objects.create(name="Ignorar conflito", slug="ignorar-conflito")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    condition = [{"field": "description", "operator": "equals", "value": "Saldo"}]
    ReconciliationRule.objects.bulk_create(
        [
            ReconciliationRule(
                organization=organization,
                company=company,
                name="Ignorar",
                state=ReconciliationRule.State.ACTIVE,
                all_conditions=condition,
                actions={"ignore": True},
            ),
            ReconciliationRule(
                organization=organization,
                company=company,
                name="Classificar",
                state=ReconciliationRule.State.ACTIVE,
                all_conditions=condition,
                actions={"accounting_history": "Saldo bancário"},
            ),
        ]
    )
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="saldo.csv",
        content=b"Data;Historico;Valor;Documento\n12/09/2026;Saldo;20,00;S-1\n",
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )

    _map_and_process(source, run)

    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    assert movement.review_state == NormalizedMovement.ReviewState.CONFLICT
    assert movement.confidence_details["rule_conflicts"] == ["ignore"]


@pytest.mark.django_db
def test_xlsx_and_text_pdf_preserve_source_evidence() -> None:
    from openpyxl import Workbook
    from reportlab.pdfgen.canvas import Canvas

    organization = Organization.objects.create(name="Evidências", slug="evidencias")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    workbook = Workbook()
    sheet = workbook.active
    sheet.append(["Data", "Historico", "Valor", "Documento"])
    sheet.append([date(2026, 9, 12), "Planilha", 15.25, "X-1"])
    xlsx_bytes = BytesIO()
    workbook.save(xlsx_bytes)
    xlsx_source, xlsx_run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="movimentos.xlsx",
        content=xlsx_bytes.getvalue(),
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(xlsx_source, xlsx_run)

    pdf_bytes = BytesIO()
    canvas = Canvas(pdf_bytes)
    canvas.drawString(72, 720, "12/09/2026 Pagamento fornecedor 15,25")
    canvas.save()
    pdf_source, pdf_run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="comprovante.pdf",
        content=pdf_bytes.getvalue(),
        origin=ReconciliationSourceFile.Origin.DOCUMENT,
    )
    process_run(str(pdf_run.id))

    assert (
        NormalizedMovement.objects.get(source_file=xlsx_source).source_reference["sheet"] == "Sheet"
    )
    pdf_movement = NormalizedMovement.objects.get(source_file=pdf_source)
    assert pdf_movement.source_reference["page"] == 1
    assert pdf_movement.source_reference["bbox"]["unit"] == "pdf_points"


@pytest.mark.django_db
def test_scanned_pdf_without_local_ocr_stays_in_review(monkeypatch: pytest.MonkeyPatch) -> None:
    from reportlab.pdfgen.canvas import Canvas

    monkeypatch.setattr("apps.hub.reconciliation_service.local_ocr_available", lambda: False)
    organization = Organization.objects.create(name="OCR", slug="ocr")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    pdf_bytes = BytesIO()
    canvas = Canvas(pdf_bytes)
    canvas.showPage()
    canvas.save()
    _source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="digitalizado.pdf",
        content=pdf_bytes.getvalue(),
        origin=ReconciliationSourceFile.Origin.DOCUMENT,
    )

    result = process_run(str(run.id))
    run.refresh_from_db()

    assert result["state"] == "review"
    assert run.stage == "ocr_review"
    assert run.errors[0]["code"] == "ocr_required"


@pytest.mark.django_db
def test_scanned_pdf_uses_local_portuguese_ocr_when_available() -> None:
    font_path = Path(r"C:\Windows\Fonts\arial.ttf")
    if not local_ocr_available() or not font_path.is_file():
        pytest.skip("OCR local em português não está disponível neste ambiente.")
    from PIL import Image, ImageDraw, ImageFont
    from reportlab.lib.utils import ImageReader
    from reportlab.pdfgen.canvas import Canvas

    organization = Organization.objects.create(name="OCR local", slug="ocr-local")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    image = Image.new("RGB", (1800, 360), "white")
    ImageDraw.Draw(image).text(
        (60, 130),
        "12/09/2026 Pagamento fornecedor 15,25",
        fill="black",
        font=ImageFont.truetype(str(font_path), 54),
    )
    image_bytes = BytesIO()
    image.save(image_bytes, format="PNG")
    pdf_bytes = BytesIO()
    canvas = Canvas(pdf_bytes, pagesize=(900, 180))
    canvas.drawImage(ImageReader(BytesIO(image_bytes.getvalue())), 0, 0, width=900, height=180)
    canvas.save()
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="digitalizado-com-texto.pdf",
        content=pdf_bytes.getvalue(),
        origin=ReconciliationSourceFile.Origin.DOCUMENT,
    )

    process_run(str(run.id))

    movement = NormalizedMovement.objects.get(source_file=source)
    assert movement.occurred_on == date(2026, 9, 12)
    assert movement.amount_cents == 1525
    assert movement.confidence_details["method"] == "tesseract-local"
    assert movement.source_reference["bbox"]["unit"] == "pixels@2x"


@pytest.mark.django_db
def test_expired_reconciliation_run_is_requeued(django_capture_on_commit_callbacks: object) -> None:
    from apps.hub.tasks import recover_reconciliation_runs

    organization = Organization.objects.create(name="Retomada", slug="retomada")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    _source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="aguardando.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    run.state = ReconciliationRun.State.PROCESSING
    run.stage = "extracting"
    run.lease_until = timezone.now() - timedelta(minutes=1)
    run.save(update_fields=["state", "stage", "lease_until", "updated_at"])

    with (
        patch("apps.hub.tasks.process_reconciliation_run.delay") as dispatch,
        django_capture_on_commit_callbacks(execute=True),  # type: ignore[operator]
    ):
        assert recover_reconciliation_runs() == 1

    run.refresh_from_db()
    assert run.state == ReconciliationRun.State.WAITING
    assert run.stage == "recovered"
    assert run.lease_until is None
    dispatch.assert_called_once_with(str(run.id))


@pytest.mark.django_db
def test_waiting_reconciliation_run_is_redispatched_from_the_database() -> None:
    from apps.hub.tasks import dispatch_waiting_reconciliation_runs

    organization = Organization.objects.create(name="Despacho", slug="despacho")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    _source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="aguardando.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )

    with patch("apps.hub.tasks.process_reconciliation_run.delay") as dispatch:
        assert dispatch_waiting_reconciliation_runs() == 1

    dispatch.assert_called_once_with(str(run.id))


@pytest.mark.django_db
def test_reconciliation_routes_do_not_cross_company_access_boundaries() -> None:
    organization = Organization.objects.create(name="Isolamento", slug="isolamento")
    allowed_company = ClientCompany.objects.create(organization=organization, name="Permitida")
    restricted_company = ClientCompany.objects.create(organization=organization, name="Restrita")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("operador@isolamento.test", "safe-password-123")
    membership = Membership.objects.create(
        organization=organization, user=user, role=Membership.Role.OPERATOR
    )
    CompanyAccessGrant.objects.create(
        organization=organization,
        membership=membership,
        company=allowed_company,
        modules=[ProductModule.Code.RECONCILIATION],
        capabilities=["*"],
    )
    source, run, _ = create_source_file(
        organization=organization,
        company=restricted_company,
        filename="restrita.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(source, run)
    movement = NormalizedMovement.objects.get(source_file=source, source_key="row:2")
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    assert client.get(reverse("hub:reconciliation")).status_code == 200
    assert client.get(reverse("hub:reconciliation-movement", args=[movement.id])).status_code == 404
    assert client.get(reverse("hub:reconciliation-run-status", args=[run.id])).status_code == 404
    assert (
        client.get(reverse("hub:reconciliation-source-download", args=[source.id])).status_code
        == 404
    )
    assert (
        client.get(reverse("hub:reconciliation-source-preview", args=[source.id])).status_code
        == 404
    )


@pytest.mark.django_db
def test_authorized_pdf_preview_is_private_and_audited() -> None:
    from reportlab.pdfgen.canvas import Canvas

    organization = Organization.objects.create(name="Prévia", slug="previa")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@previa.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    pdf_bytes = BytesIO()
    canvas = Canvas(pdf_bytes)
    canvas.drawString(72, 720, "12/09/2026 Pagamento 15,25")
    canvas.save()
    source, _run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="evidencia.pdf",
        content=pdf_bytes.getvalue(),
        origin=ReconciliationSourceFile.Origin.DOCUMENT,
    )
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    response = client.get(reverse("hub:reconciliation-source-preview", args=[source.id]))

    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert response["Cache-Control"] == "no-store, private"
    assert "inline" in response["Content-Disposition"]
    assert AuditEvent.objects.filter(
        action="hub.reconciliation.source_previewed", target_id=str(source.id)
    ).exists()


def test_reconciliation_recovery_is_scheduled() -> None:
    assert settings.CELERY_BEAT_SCHEDULE["recover-reconciliation-runs"]["task"] == (
        "hub.recover_reconciliation_runs"
    )
    assert settings.CELERY_BEAT_SCHEDULE["dispatch-waiting-reconciliation-runs"]["task"] == (
        "hub.dispatch_waiting_reconciliation_runs"
    )


def test_reconciliation_private_file_routes_are_registered() -> None:
    source_id = "00000000-0000-0000-0000-000000000001"
    assert reverse("hub:reconciliation-source-download", args=[source_id]).endswith(
        f"/app/conciliacao/arquivos/{source_id}/download/"
    )


@pytest.mark.django_db
def test_mapping_view_requeues_the_same_run(django_capture_on_commit_callbacks: object) -> None:
    organization = Organization.objects.create(name="Mapeamento", slug="mapeamento")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@mapeamento.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="extrato.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    process_run(str(run.id))
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()
    url = reverse("hub:reconciliation-mapping", args=[source.id])

    page = client.get(url)

    assert page.status_code == 200
    assert b"Salvar layout e processar" in page.content
    assert b'name="map_date"' in page.content
    assert b'name="map_description"' in page.content
    assert b"document.querySelector" not in page.content
    with (
        patch("apps.hub.tasks.process_reconciliation_run.delay") as dispatch,
        django_capture_on_commit_callbacks(execute=True),  # type: ignore[operator]
    ):
        response = client.post(
            url,
            {
                "name": "Extrato web",
                **{f"map_{field}": value for field, value in DEFAULT_MAPPING.items()},
            },
        )

    assert response.status_code == 302
    run.refresh_from_db()
    assert run.state == ReconciliationRun.State.WAITING
    assert run.layout_version is not None
    dispatch.assert_called_once_with(str(run.id))


@pytest.mark.django_db
def test_owner_configures_accounting_references_inside_reconciliation(
    django_capture_on_commit_callbacks: object,
) -> None:
    organization = Organization.objects.create(name="Configuração", slug="configuracao")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    ProductModule.objects.create(
        organization=organization, code=ProductModule.Code.RECONCILIATION, enabled=True
    )
    user = User.objects.create_user("owner@config.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.id)
    session.save()

    page = client.get(reverse("hub:reconciliation-configuration"))

    assert page.status_code == 200
    assert b"Contas financeiras" in page.content
    assert b"PRONTO PARA IMPORTAR" in page.content
    # Company selection lives in one explicit context switcher. Individual setup
    # forms keep their company identifier as a hidden, server-validated field.
    assert page.content.count(b'id="reconciliation-configuration-company"') == 1
    invalid_financial_account = client.post(
        reverse("hub:reconciliation-configuration"),
        {
            "action": "financial_account",
            "company": str(company.id),
            "name": "Conta com vinculo invalido",
            "bank_code": "001",
            "account_reference": "001:invalida",
            "ledger_code": "1.1.99",
            "active": "on",
        },
    )
    assert invalid_financial_account.status_code == 200
    assert b"Cadastre uma conta cont" in invalid_financial_account.content
    assert not FinancialAccount.objects.filter(
        organization=organization, company=company, account_reference="001:invalida"
    ).exists()
    LedgerAccount.objects.create(
        organization=organization, company=company, code="1.1.01", name="Banco"
    )
    LedgerAccount.objects.create(
        organization=organization, company=company, code="2", name="Contrapartida"
    )
    response = client.post(
        reverse("hub:reconciliation-configuration"),
        {
            "action": "financial_account",
            "company": str(company.id),
            "name": "Banco principal",
            "bank_code": "001",
            "account_reference": "001:123",
            "ledger_code": "1.1.01",
            "active": "on",
        },
    )

    assert response.status_code == 302
    financial_account = FinancialAccount.objects.get(
        organization=organization, company=company, account_reference="001:123"
    )
    upload_page = client.get(reverse("hub:reconciliation"))
    assert upload_page.status_code == 200
    assert b"Banco principal" in upload_page.content
    deactivate = client.post(
        reverse("hub:reconciliation-configuration"),
        {
            "action": "toggle_setup",
            "company": str(company.id),
            "setup_kind": "financial_account",
            "setup_id": str(financial_account.id),
        },
    )
    assert deactivate.status_code == 302
    financial_account.refresh_from_db()
    assert financial_account.active is False
    assert FinancialAccount.objects.filter(
        organization=organization,
        company=company,
        account_reference="001:123",
    ).exists()
    rule_response = client.post(
        reverse("hub:reconciliation-configuration"),
        {
            "action": "reconciliation_rule",
            "company": str(company.id),
            "name": "Banco principal",
            "priority": "10",
            "state": "active",
            "condition_field": "description",
            "condition_operator": "contains",
            "condition_value": "fornecedor",
            "debit_account_code": "1.1.01",
            "require_review": "on",
        },
    )

    assert rule_response.status_code == 302
    assert ReconciliationRule.objects.filter(
        organization=organization,
        company=company,
        name="Banco principal",
        all_conditions=[{"field": "description", "operator": "contains", "value": "fornecedor"}],
    ).exists()
    combined_rule_response = client.post(
        reverse("hub:reconciliation-configuration"),
        {
            "action": "reconciliation_rule",
            "company": str(company.id),
            "name": "Fornecedor ou documento",
            "priority": "20",
            "state": "draft",
            "condition_field": "description",
            "condition_operator": "contains",
            "condition_value": "fornecedor",
            "condition_group": "any",
            "additional_condition_field": "document",
            "additional_condition_operator": "contains",
            "additional_condition_value": "N-",
            "debit_account_code": "1.1.01",
        },
    )
    assert combined_rule_response.status_code == 302
    combined_rule = ReconciliationRule.objects.get(
        organization=organization, name="Fornecedor ou documento"
    )
    assert combined_rule.all_conditions == []
    assert combined_rule.any_conditions == [
        {"field": "description", "operator": "contains", "value": "fornecedor"},
        {"field": "document", "operator": "contains", "value": "N-"},
    ]
    rule = ReconciliationRule.objects.get(organization=organization, name="Banco principal")
    toggle_response = client.post(
        reverse("hub:reconciliation-configuration"),
        {"action": "toggle_rule", "company": str(company.id), "rule_id": str(rule.id)},
    )
    assert toggle_response.status_code == 302
    rule.refresh_from_db()
    assert rule.state == ReconciliationRule.State.DISABLED
    _source, run, _ = create_source_file(
        organization=organization,
        company=company,
        filename="filtro.csv",
        content=CSV,
        origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
    )
    _map_and_process(_source, run)
    with (
        patch("apps.hub.tasks.process_reconciliation_run.delay") as dispatch,
        django_capture_on_commit_callbacks(execute=True),  # type: ignore[operator]
    ):
        requested_reapplication = client.post(
            reverse("hub:reconciliation-run-action", args=[run.id]),
            {"action": "reapply_rules"},
        )
    assert requested_reapplication.status_code == 302
    reapplication = ReconciliationRun.objects.filter(continued_from=run).latest("created_at")
    assert reapplication.checkpoint == {"mode": "rules", "source_run_id": str(run.id)}
    dispatch.assert_called_once_with(str(reapplication.id))
    assert AuditEvent.objects.filter(
        action="hub.reconciliation.rules_reapplication_requested",
        target_id=str(reapplication.id),
    ).exists()
    movement = NormalizedMovement.objects.get(source_file=_source, source_key="row:2")
    review_page = client.get(reverse("hub:reconciliation"))
    assert review_page.status_code == 200
    assert b"Aplicar aos selecionados" in review_page.content
    bulk_ignore = client.post(
        reverse("hub:reconciliation-movement-bulk-action"),
        {
            "movement_ids": [str(movement.id)],
            "action": "ignore",
            "reason": "Saldo inicial já conferido",
        },
    )
    assert bulk_ignore.status_code == 302
    movement.refresh_from_db()
    assert movement.review_state == NormalizedMovement.ReviewState.IGNORED
    assert AuditEvent.objects.filter(
        action="hub.reconciliation.movements_ignored", target_id=str(movement.id)
    ).exists()
    bulk_restore = client.post(
        reverse("hub:reconciliation-movement-bulk-action"),
        {
            "movement_ids": [str(movement.id)],
            "action": "review",
            "reason": "Retomar conferência individual",
        },
    )
    assert bulk_restore.status_code == 302
    movement.refresh_from_db()
    assert movement.review_state == NormalizedMovement.ReviewState.PENDING
    invalid_manual_edit = client.post(
        reverse("hub:reconciliation-movement", args=[movement.id]),
        {
            "action": "save",
            "occurred_on": movement.occurred_on.isoformat(),
            "description": movement.description,
            "document_number": movement.document_number,
            "counterparty": movement.counterparty,
            "debit_account_code": "inexistente",
            "credit_account_code": "",
            "cost_center_code": "",
            "accounting_history": "",
            "expected_revision": str(movement.revision),
        },
    )
    assert invalid_manual_edit.status_code == 200
    assert b"Escolha uma conta ativa" in invalid_manual_edit.content
    movement.refresh_from_db()
    assert movement.debit_account_code == ""
    movement.debit_account_code = "1.1.01"
    movement.credit_account_code = "2"
    movement.accounting_history = "Pagamento conferido"
    movement.save()
    entry_invalidated_by_edit = create_journal_entry_from_movement(movement=movement)
    approve_journal_entry(entry=entry_invalidated_by_edit)
    valid_manual_edit = client.post(
        reverse("hub:reconciliation-movement", args=[movement.id]),
        {
            "action": "save",
            "occurred_on": movement.occurred_on.isoformat(),
            "description": movement.description,
            "document_number": movement.document_number,
            "counterparty": movement.counterparty,
            "debit_account_code": "1.1.01",
            "credit_account_code": "2",
            "cost_center_code": "",
            "accounting_history": "Pagamento revisado",
            "expected_revision": str(movement.revision),
        },
    )
    assert valid_manual_edit.status_code == 302
    entry_invalidated_by_edit.refresh_from_db()
    assert entry_invalidated_by_edit.state == JournalEntry.State.INVALID
    movement.refresh_from_db()
    entry_invalidated_by_ignore = create_journal_entry_from_movement(movement=movement)
    approve_journal_entry(entry=entry_invalidated_by_ignore)
    ignored_response = client.post(
        reverse("hub:reconciliation-movement", args=[movement.id]),
        {"action": "ignore_movement", "reason": "Saldo inicial já conferido"},
    )
    assert ignored_response.status_code == 302
    movement.refresh_from_db()
    assert movement.review_state == NormalizedMovement.ReviewState.IGNORED
    entry_invalidated_by_ignore.refresh_from_db()
    assert entry_invalidated_by_ignore.state == JournalEntry.State.INVALID
    restored_response = client.post(
        reverse("hub:reconciliation-movement", args=[movement.id]),
        {"action": "restore_movement"},
    )
    assert restored_response.status_code == 302
    movement.refresh_from_db()
    assert movement.review_state == NormalizedMovement.ReviewState.PENDING
    JournalEntry.objects.filter(id=entry_invalidated_by_ignore.id).update(
        state=JournalEntry.State.EXPORTED
    )
    blocked_exported_edit = client.post(
        reverse("hub:reconciliation-movement", args=[movement.id]),
        {
            "action": "save",
            "occurred_on": movement.occurred_on.isoformat(),
            "description": "Tentativa de alterar exportado",
            "document_number": movement.document_number,
            "counterparty": movement.counterparty,
            "debit_account_code": "1.1.01",
            "credit_account_code": "2",
            "cost_center_code": "",
            "accounting_history": "Tentativa de alterar exportado",
            "expected_revision": str(movement.revision),
        },
    )
    assert blocked_exported_edit.status_code == 200
    assert b"retifica" in blocked_exported_edit.content
    movement.refresh_from_db()
    assert movement.description == "Fornecedor"
    independent_entry = JournalEntry.objects.create(
        organization=organization,
        company=company,
        occurred_on=date(2026, 9, 12),
        history="Fornecedor N-1",
        purpose="settlement",
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                organization=organization,
                entry=independent_entry,
                account_code="1.1.01",
                side=JournalLine.Side.DEBIT,
                amount_cents=123456,
            ),
            JournalLine(
                organization=organization,
                entry=independent_entry,
                account_code="2",
                side=JournalLine.Side.CREDIT,
                amount_cents=123456,
            ),
        ]
    )
    detail = client.get(reverse("hub:reconciliation-movement", args=[movement.id]))
    assert detail.status_code == 200
    assert b"Localiza" in detail.content
    assert b"Uma sugest" in detail.content
    ambiguous_entry = JournalEntry.objects.create(
        organization=organization,
        company=company,
        occurred_on=date(2026, 9, 12),
        history="Fornecedor N-1",
        purpose="settlement",
    )
    JournalLine.objects.bulk_create(
        [
            JournalLine(
                organization=organization,
                entry=ambiguous_entry,
                account_code="1.1.01",
                side=JournalLine.Side.DEBIT,
                amount_cents=123456,
            ),
            JournalLine(
                organization=organization,
                entry=ambiguous_entry,
                account_code="2",
                side=JournalLine.Side.CREDIT,
                amount_cents=123456,
            ),
        ]
    )
    ambiguous = client.get(reverse("hub:reconciliation-movement", args=[movement.id]))
    assert "2 sugestões possíveis" in ambiguous.content.decode()
    confirmation = client.post(
        reverse("hub:reconciliation-movement", args=[movement.id]),
        {
            "action": "confirm_reconciliation",
            "entry_id": str(independent_entry.id),
            "amount_brl": "1234.56",
            "evidence_note": "Documento N-1",
        },
    )
    assert confirmation.status_code == 302
    filtered = client.get(
        reverse("hub:reconciliation"),
        {
            "movement_company": str(company.id),
            "movement_review": "pending",
            "movement_q": "Fornecedor",
        },
    )
    assert filtered.status_code == 200
    assert b"Fornecedor" in filtered.content
    assert AuditEvent.objects.filter(
        organization=organization, action="hub.reconciliation.financial_account.created"
    ).exists()
    assert AuditEvent.objects.filter(
        organization=organization,
        action="hub.reconciliation.financial_account.state_changed",
    ).exists()
    assert AuditEvent.objects.filter(
        organization=organization, action="hub.reconciliation.movement_ignored"
    ).exists()
    assert AuditEvent.objects.filter(
        organization=organization, action="hub.reconciliation.movement_restored"
    ).exists()
    assert AuditEvent.objects.filter(
        organization=organization,
        action="hub.reconciliation.reconciliation_confirmed",
    ).exists()
    audit = client.get(reverse("hub:reconciliation-audit"))
    assert audit.status_code == 200
    assert b"hub.reconciliation.financial_account.created" in audit.content
