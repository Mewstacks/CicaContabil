"""HTTP receipt review preserves scope, prior accepted results and page context."""

import json
from copy import deepcopy
from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from django.db import connection
from django.test import Client
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from tests.accounting_import_fixtures import homologate_synthetic
from tests.test_accounting_import import case as import_case

from apps.hub.models import (
    AccountingImportReceipt,
    CompanyAccessGrant,
    JournalEntry,
    JournalLine,
    ProductModule,
)
from apps.hub.reconciliation_service import create_export

case = import_case
pytestmark = pytest.mark.django_db


@pytest.fixture
def web(case):
    client = Client()
    client.force_login(case["actor"])
    session = client.session
    session["hub_organization_id"] = str(case["organization"].pk)
    session.save()
    return client


def url(case, page=1):
    return reverse("hub:reconciliation-import-receipt", args=[case["export"].pk]) + f"?page={page}"


def payload(response, status="uncertain"):
    initial = response.context["import_form"].initial
    values = {key: str(value) if value is not None else "" for key, value in initial.items()}
    values.update(evidence_reference="SYNTHETIC private ERP observation", review_confirmed="on")
    for index, row in enumerate(response.context["import_rows"]):
        if row["accepted"]:
            continue
        prefix = row["form"].prefix
        values[prefix + "-status"] = status
        values[prefix + "-erp_reference"] = f"SYNTHETIC-{index}" if status == "accepted" else ""
        values[prefix + "-evidence_reference"] = "SYNTHETIC result" if status != "uncertain" else ""
    return values


def test_get_is_private_readonly_and_starts_uncertain_without_checked_confirmation(case, web):
    before = AccountingImportReceipt.objects.count()
    response = web.get(url(case))
    assert response.status_code == 200
    assert response["Cache-Control"] == "no-store, private"
    assert AccountingImportReceipt.objects.count() == before
    assert response.context["import_counts"] == dict(accepted=0, rejected=0, uncertain=2, total=2)
    assert "checked" not in str(response.context["import_form"]["review_confirmed"])
    assert all(
        row["form"].initial["status"] == "uncertain" for row in response.context["import_rows"]
    )
    assert case["export"].content_hash in response.content.decode()
    assert "consulte o ERP antes de repetir" in response.content.decode()


def test_record_partial_and_idempotent_replay(case, web):
    initial = web.get(url(case))
    data = payload(initial, "accepted")
    prefix = initial.context["import_rows"][1]["form"].prefix
    data[prefix + "-status"] = "rejected"
    data[prefix + "-erp_reference"] = ""
    response = web.post(url(case), data)
    assert response.status_code == 302
    receipt = AccountingImportReceipt.objects.get()
    assert receipt.outcome == "partial" and receipt.evidence["kind"] == "attestation"
    case["export"].refresh_from_db()
    assert case["export"].state == "ready"
    assert web.post(url(case), data).status_code == 302
    assert AccountingImportReceipt.objects.count() == 1
    page = web.get(url(case))
    assert "Importação parcial" in page.content.decode()
    assert "sem documento anexado" in page.content.decode()
    assert page.context["import_rows"][0]["form"] is None


def test_complete_receipt_and_duplicate_post_are_confirmed_once(case, web):
    data = payload(web.get(url(case)), "accepted")
    assert web.post(url(case), data).status_code == 302
    assert web.post(url(case), data).status_code == 302
    assert AccountingImportReceipt.objects.count() == 1
    case["export"].refresh_from_db()
    assert case["export"].state == "confirmed"
    page = web.get(url(case))
    assert not page.context["import_can_record"]
    assert "Importação integral conferida" in page.content.decode()
    assert "import-receipt-form" not in page.content.decode()


@pytest.mark.parametrize("field", ["erp_reference", "evidence_reference"])
def test_accepted_result_requires_reference_and_evidence_inline(case, web, field):
    page = web.get(url(case))
    data = payload(page, "accepted")
    prefix = page.context["import_rows"][0]["form"].prefix
    data[prefix + "-" + field] = ""
    response = web.post(url(case), data)
    assert response.status_code == 400
    assert response.context["import_rows"][0]["form"].errors[field]
    assert response.context["import_form"].data["evidence_reference"] == data["evidence_reference"]
    assert not AccountingImportReceipt.objects.exists()


def test_no_confirmation_no_write(case, web):
    data = payload(web.get(url(case)), "accepted")
    data.pop("review_confirmed")
    response = web.post(url(case), data)
    assert (
        response.status_code == 400 and "review_confirmed" in response.context["import_form"].errors
    )
    assert not AccountingImportReceipt.objects.exists()


def test_stale_form_reports_conflict_and_preserves_submitted_text(case, web):
    initial = web.get(url(case))
    old = payload(initial)
    new = deepcopy(old)
    new["request_key"] = str(uuid4())
    assert web.post(url(case), new).status_code == 302
    response = web.post(url(case), old)
    assert response.status_code == 409
    assert "resultado mais recente" in response.content.decode()
    assert AccountingImportReceipt.objects.count() == 1
    assert response.context["import_form"].data["evidence_reference"] == old["evidence_reference"]


def test_accepted_prior_item_cannot_be_changed(case, web):
    page = web.get(url(case))
    data = payload(page)
    prefix = page.context["import_rows"][0]["form"].prefix
    data.update(
        {
            prefix + "-status": "accepted",
            prefix + "-erp_reference": "SYNTHETIC-1",
            prefix + "-evidence_reference": "SYNTHETIC accepted evidence",
        }
    )
    assert web.post(url(case), data).status_code == 302
    receipt = AccountingImportReceipt.objects.get()
    after = web.get(url(case))
    changed = payload(after)
    changed[prefix + "-status"] = "uncertain"
    assert web.post(url(case), changed).status_code == 409
    assert AccountingImportReceipt.objects.count() == 1
    receipt.refresh_from_db()
    assert receipt.items[0]["status"] == "accepted"


@pytest.mark.parametrize(
    "query", ["page=0", "page=999999", "page=bad", "page=1&page=2", "history_page=-1"]
)
def test_bad_page_never_broadens_or_writes(case, web, query):
    target = url(case).split("?")[0] + "?" + query
    response = web.get(target)
    assert response.status_code == 400 and not response.context["import_rows"]
    assert web.post(target, {}).status_code == 400
    assert not AccountingImportReceipt.objects.exists()


def test_auditor_read_only_and_no_cross_company_scope(case, web):
    member = case["membership"]
    data = payload(web.get(url(case)))
    member.role = "auditor"
    member.save(update_fields=["role"])
    grant = CompanyAccessGrant.objects.create(
        organization=case["organization"],
        membership=member,
        company=case["company"],
        modules=["reconciliation"],
        capabilities=["accounting_entries"],
    )
    response = web.get(url(case))
    assert response.status_code == 200 and not response.context["import_can_record"]
    assert web.post(url(case), data).status_code == 403
    member.role = "operator"
    member.save(update_fields=["role"])
    grant.modules = ["payroll"]
    grant.save(update_fields=["modules"])
    assert web.get(url(case)).status_code == 403


def test_revoked_membership_module_and_homologation_block_write(case, web):
    data = payload(web.get(url(case)))
    homologate_synthetic(case["organization"], approved=False)
    assert not web.get(url(case)).context["import_can_record"]
    assert web.post(url(case), data).status_code == 400
    ProductModule.objects.filter(organization=case["organization"]).update(enabled=False)
    assert web.get(url(case)).status_code == 403
    case["membership"].is_active = False
    case["membership"].save(update_fields=["is_active"])
    assert web.post(url(case), data).status_code == 403
    assert not AccountingImportReceipt.objects.exists()


def test_csrf_post_is_enforced(case, web):
    data = payload(web.get(url(case)))
    strict = Client(enforce_csrf_checks=True)
    strict.force_login(case["actor"])
    assert strict.post(url(case), data).status_code == 403
    assert not AccountingImportReceipt.objects.exists()


def test_pagination_merges_prior_pages_and_replay_uses_submitted_previous(case, web):
    start = date(2026, 10, 1)
    for index in range(26):
        entry = JournalEntry.objects.create(
            organization=case["organization"],
            company=case["company"],
            occurred_on=start,
            history=f"SYNTHETIC paged {index}",
            purpose="record",
            state="approved",
        )
        for account, side in (("1", "debit"), ("2", "credit")):
            JournalLine.objects.create(
                organization=case["organization"],
                entry=entry,
                account_code=account,
                side=side,
                amount_cents=12345,
            )
    case["export"] = create_export(
        organization=case["organization"],
        company=case["company"],
        start=start,
        end=date(2026, 10, 31),
        actor=case["actor"],
    )
    with CaptureQueriesContext(connection) as queries:
        first = web.get(url(case))
    assert len(first.context["import_rows"]) == 25
    line_queries = [query["sql"] for query in queries if 'FROM "hub_journalline"' in query["sql"]]
    assert len(line_queries) == 1
    rows = first.context["import_rows"]
    assert all(row["amount_brl"] == Decimal("123.45") for row in rows)
    assert rows[0]["debits"] == [{"account": "1", "amount_brl": Decimal("123.45")}]
    assert rows[0]["credits"] == [{"account": "2", "amount_brl": Decimal("123.45")}]
    assert "Registro contábil vinculado ao arquivo exportado" in first.content.decode()
    second_id = case["export"].entry_ids[-1]
    assert second_id.replace("-", "") not in line_queries[0].replace("-", "")
    data = payload(first, "accepted")
    assert web.post(url(case), data).status_code == 302
    second = web.get(url(case, 2))
    assert len(second.context["import_rows"]) == 1
    assert second.context["import_counts"] == dict(accepted=25, rejected=0, uncertain=1, total=26)
    last_data = payload(second, "accepted")
    assert web.post(url(case, 2), last_data).status_code == 302
    assert web.post(url(case, 2), last_data).status_code == 302
    assert AccountingImportReceipt.objects.filter(export=case["export"]).count() == 2
    case["export"].refresh_from_db()
    assert case["export"].state == "confirmed"


def test_hash_and_request_key_tampering_are_refused(case, web):
    data = payload(web.get(url(case)))
    data["content_hash"] = "0" * 64
    assert web.post(url(case), data).status_code == 409
    data["request_key"] = "not-a-uuid"
    assert web.post(url(case), data).status_code == 400
    assert not AccountingImportReceipt.objects.exists()


def test_corrupted_historical_receipt_is_not_presented_as_evidence(case, web):
    first_data = payload(web.get(url(case)))
    first_data["evidence_reference"] = "SYNTHETIC corrupted historical evidence"
    assert web.post(url(case), first_data).status_code == 302
    first = AccountingImportReceipt.objects.get()
    assert web.post(url(case), payload(web.get(url(case)))).status_code == 302
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE hub_accountingimportreceipt SET fingerprint=%s WHERE id=%s",
            ["0" * 64, first.pk.hex if connection.vendor == "sqlite" else first.pk],
        )
    response = web.get(url(case))
    assert response.status_code == 409
    assert "revisão de integridade" in response.content.decode()
    assert "SYNTHETIC corrupted historical evidence" not in response.content.decode()
    assert not response.context["import_can_record"]


def test_corrupted_previous_receipt_outside_history_page_is_not_used(case, web):
    assert web.post(url(case), payload(web.get(url(case)))).status_code == 302
    first = AccountingImportReceipt.objects.get()
    stale_data = payload(web.get(url(case)))
    for _ in range(10):
        assert web.post(url(case), payload(web.get(url(case)))).status_code == 302
    changed = deepcopy(first.items)
    changed[0].update(
        status="accepted",
        erp_reference="TAMPERED ERP reference",
        evidence_reference="TAMPERED item evidence",
    )
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE hub_accountingimportreceipt SET items=%s WHERE id=%s",
            [json.dumps(changed), first.pk.hex if connection.vendor == "sqlite" else first.pk],
        )
    assert web.get(url(case)).status_code == 200
    response = web.post(url(case), stale_data)
    assert response.status_code == 409
    assert "O recibo anterior precisa de revisão de integridade" in response.content.decode()
    assert "TAMPERED" not in response.content.decode()
    assert all(row["item"]["status"] == "uncertain" for row in response.context["import_rows"])
    assert AccountingImportReceipt.objects.count() == 11
