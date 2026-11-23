from __future__ import annotations

import csv
import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.http import QueryDict
from django.test.utils import CaptureQueriesContext

from apps.audit.models import AuditEvent
from apps.hub.forms import ReconciliationUploadForm
from apps.hub.ledger_import import (
    LEDGER_COLUMNS,
    import_ledger_source,
    ledger_csv_template,
    preview_ledger_uploads,
)
from apps.hub.models import (
    AccountingEntry,
    ClientCompany,
    FinancialAccount,
    IndependentLedgerRecord,
    JournalEntry,
    JournalLine,
    LedgerAccount,
    ReconciliationRun,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_service import ReconciliationError, create_source_file
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db


def content(*, key="synthetic-1", counterpart="9", amount=10000):
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(LEDGER_COLUMNS)
    writer.writerow(
        [key, "bank", "2026-09-12", "Synthetic source", "8", "debit", amount, "inflow", "SYNTHETIC"]
    )
    writer.writerow(
        [
            key,
            "other",
            "2026-09-12",
            "Synthetic source",
            counterpart,
            "credit",
            amount,
            "",
            "SYNTHETIC",
        ]
    )
    return output.getvalue().encode()


def upload(data=None, name="synthetic.csv"):
    return SimpleUploadedFile(name, content() if data is None else data)


@pytest.fixture
def account(organization, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    company = ClientCompany.objects.create(
        organization=organization, name="Synthetic company", dominio_code="21"
    )
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Synthetic bank",
        bank_code="001",
        account_reference="001:123",
        ledger_code="8",
    )
    for code in ("8", "9"):
        LedgerAccount.objects.create(
            organization=organization, company=company, code=code, name=f"Synthetic {code}"
        )
    return account


def preview(account, uploads):
    return preview_ledger_uploads(
        organization=account.organization,
        company=account.company,
        financial_account=account,
        uploads=uploads,
    )


def form(account, uploads, **changes):
    data = {
        "company": str(account.company_id),
        "financial_account": str(account.pk),
        "origin": "accounting",
        "purpose": "independent_ledger",
    }
    data.update(changes)
    return ReconciliationUploadForm(
        data,
        {"files": uploads},
        companies=ClientCompany.objects.filter(organization=account.organization),
    )


def snapshot():
    return {
        model.__name__: list(model.objects.order_by("pk").values())
        for model in (
            ReconciliationSourceFile,
            ReconciliationRun,
            FinancialAccount,
            LedgerAccount,
            IndependentLedgerRecord,
            JournalEntry,
            JournalLine,
            AccountingEntry,
            AuditEvent,
        )
    }


def test_complete_batch_preview_is_select_only_and_preserves_stream(account, tmp_path):
    files = [upload(), upload(content(key="synthetic-2"))]
    files[0].seek(3)
    before = snapshot()
    with CaptureQueriesContext(connection) as queries:
        report = preview(account, files)
    assert [item["new"] for item in report] == [1, 1]
    assert files[0].tell() == 3 and files[1].tell() == 0
    assert snapshot() == before and not list(tmp_path.rglob("*"))
    assert all(query["sql"].lstrip().upper().startswith("SELECT") for query in queries)
    assert all("FOR UPDATE" not in query["sql"].upper() for query in queries)


@pytest.mark.parametrize("bad", ["pdf", "xlsx", "generic", "binary", "blank", "oversize_field"])
def test_valid_and_invalid_batch_is_rejected_without_writes(account, tmp_path, bad):
    invalid = {
        "pdf": (b"%PDF-synthetic", "synthetic.pdf"),
        "xlsx": (b"PK-synthetic", "synthetic.xlsx"),
        "generic": (b"Data;Valor\n12/09/2026;100,00\n", "generic.csv"),
        "binary": (b"\x00", "binary.csv"),
        "blank": (b"", "empty.csv"),
        "oversize_field": (content().replace(b"Synthetic source", b"x" * 140000), "long.csv"),
    }[bad]
    files = [upload(), upload(*invalid)]
    before = snapshot()
    bound = form(account, files)
    assert not bound.is_valid() and "files" in bound.errors
    assert snapshot() == before and not list(tmp_path.rglob("*"))
    assert files[0].tell() == files[1].tell() == 0


def test_form_previews_every_file_before_a_caller_can_store_any(account):
    bound = form(account, [upload(), upload(content(key="second", counterpart="MISSING"))])
    before = snapshot()
    assert not bound.is_valid()
    assert "MISSING" in str(bound.errors) and "Plano de contas" in str(bound.errors)
    assert snapshot() == before and bound.independent_ledger_preview == []


@pytest.mark.parametrize("condition", ["missing", "inactive", "not_postable"])
def test_plan_errors_are_shared_by_preview_and_import(account, condition):
    counterpart = LedgerAccount.objects.get(company=account.company, code="9")
    if condition == "missing":
        counterpart.delete()
    else:
        setattr(counterpart, "active" if condition == "inactive" else "accepts_entries", False)
        counterpart.save()
    with pytest.raises(ReconciliationError, match="9"):
        preview(account, [upload()])
    source, _, _ = create_source_file(
        organization=account.organization,
        company=account.company,
        financial_account=account,
        origin="accounting",
        filename="synthetic.csv",
        content=content(),
    )
    with pytest.raises(ReconciliationError, match="9"):
        import_ledger_source(source)
    assert not IndependentLedgerRecord.objects.exists() and not JournalEntry.objects.exists()


def test_missing_codes_are_bounded(account):
    data = content()
    for index in range(30):
        data += content(key=f"synthetic-{index + 2}", counterpart=f"MISSING-{index:02}").split(
            b"\n", 1
        )[1]
    with pytest.raises(ReconciliationError) as exc:
        preview(account, [upload(data)])
    assert "MISSING-00" in str(exc.value) and "MISSING-19" in str(exc.value)
    assert "MISSING-20" not in str(exc.value) and "mais 10" in str(exc.value)


@pytest.mark.parametrize(
    "field", ["bank_code", "name", "ledger_code", "account_reference", "active"]
)
def test_new_independent_intake_requires_complete_active_account(account, field):
    setattr(account, field, False if field == "active" else "")
    account.save()
    before = snapshot()
    assert not form(account, [upload()]).is_valid()
    assert snapshot() == before


@pytest.mark.parametrize(
    "change",
    [
        "company",
        "financial_account",
        "origin",
        "purpose",
        "wrong_company",
        "malformed_account_scope",
    ],
)
def test_scope_and_purpose_fail_closed(account, change):
    other_org = Organization.objects.create(name="Other", slug="other-intake")
    other_company = ClientCompany.objects.create(organization=other_org, name="Other company")
    other_account = FinancialAccount.objects.create(
        organization=other_org, company=other_company, name="Other bank", account_reference="other"
    )
    changes = {"company": "not-a-uuid"} if change == "company" else {}
    if change == "financial_account":
        changes["financial_account"] = str(other_account.pk)
    elif change == "wrong_company":
        changes["company"] = str(other_company.pk)
    elif change == "origin":
        changes["origin"] = "bank_statement"
    elif change == "purpose":
        changes["purpose"] = "unknown"
    elif change == "malformed_account_scope":
        FinancialAccount.objects.filter(pk=account.pk).update(organization=other_org)
    before = snapshot()
    assert not form(account, [upload()], **changes).is_valid()
    assert snapshot() == before


def test_duplicate_purpose_cannot_downgrade_validation(account):
    data = QueryDict(mutable=True)
    data.update(
        company=str(account.company_id), financial_account=str(account.pk), origin="accounting"
    )
    data.setlist("purpose", ["independent_ledger", "general"])
    bound = ReconciliationUploadForm(
        data,
        {"files": [upload(b"generic")]},
        companies=ClientCompany.objects.filter(pk=account.company_id),
    )
    assert not bound.is_valid() and "__all__" in bound.errors


def test_model_is_explicitly_fictitious_and_cannot_be_imported(account):
    model = ledger_csv_template()
    assert next(csv.reader(io.StringIO(model.decode()), delimiter=";")) == list(LEDGER_COLUMNS)
    assert "FICTÍCIO" in model.decode() and b"CONTRAPARTIDA" in model
    before = snapshot()
    with pytest.raises(ReconciliationError, match="fictícias"):
        preview(account, [upload(model)])
    assert snapshot() == before


def test_conflicting_keys_within_batch_are_rejected(account):
    before = snapshot()
    with pytest.raises(ReconciliationError, match="lote repete"):
        preview(account, [upload(), upload(content(amount=20000))])
    assert snapshot() == before
    report = preview(account, [upload(), upload()])
    assert report[0]["new"] == 1 and report[1]["ignored"] == 1


def test_existing_source_origin_cannot_be_relabelled(account):
    create_source_file(
        organization=account.organization,
        company=account.company,
        financial_account=account,
        origin="document",
        filename="synthetic.csv",
        content=content(),
    )
    before = snapshot()
    with pytest.raises(ReconciliationError, match="outra origem"):
        preview(account, [upload()])
    assert snapshot() == before


def test_valid_intake_and_import_replay_preserve_existing_contract(account):
    bound = form(account, [upload()])
    assert bound.is_valid(), bound.errors
    source, _, _ = create_source_file(
        organization=account.organization,
        company=account.company,
        financial_account=account,
        origin="accounting",
        filename="synthetic.csv",
        content=content(),
    )
    assert import_ledger_source(source) == {"created": 1, "ignored": 0, "processed": 1}
    assert preview(account, [upload()])[0]["ignored"] == 1
    assert import_ledger_source(source) == {"created": 0, "ignored": 1, "processed": 1}
    assert IndependentLedgerRecord.objects.count() == 1
    assert JournalEntry.objects.get().purpose == "source_ledger"


@pytest.mark.parametrize("purpose", ["general", ""])
def test_generic_legacy_import_is_preserved_without_independent_claim(account, purpose):
    bound = form(account, [upload(b"Data;Valor\n12/09/2026;100,00\n")], purpose=purpose)
    before = snapshot()
    assert bound.is_valid(), bound.errors
    assert bound.cleaned_data["purpose"] == "general"
    assert bound.independent_ledger_preview == [] and snapshot() == before
