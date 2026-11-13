from __future__ import annotations

import csv
import io

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.ledger_import import LEDGER_COLUMNS
from apps.hub.models import (
    AccountingExport,
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    LedgerAccount,
    MovementReconciliation,
    ProductModule,
    ReconciliationDecision,
)
from apps.hub.reconciliation_service import create_source_file, process_run
from apps.organizations.models import Membership, Organization

pytestmark = pytest.mark.django_db


def make_case(organization, *, count=3, label="Conferência sintética", role="owner"):
    user = User.objects.create_user(f"{organization.slug}@workbench.test", "safe-test-password-123")
    membership = Membership.objects.create(organization=organization, user=user, role=role)
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    company = ClientCompany.objects.create(
        organization=organization, name=label, dominio_code="TEST1"
    )
    if role == "auditor":
        CompanyAccessGrant.objects.create(
            organization=organization,
            company=company,
            membership=membership,
            modules=["reconciliation"],
            capabilities=["bank_statements", "accounting_entries"],
        )
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Banco de teste",
        account_reference="001:123",
        ledger_code="1.1",
    )
    bank = (
        "OFXHEADER:100\n<OFX><BANKID>001<ACCTID>123<BANKTRANLIST>"
        + "".join(
            f"<STMTTRN><DTPOSTED>20260912<TRNAMT>{(10000 + i) / 100:.2f}"
            f"<FITID>test-{i}<MEMO>Recebimento sintético {i}</STMTTRN>"
            for i in range(count)
        )
        + "</BANKTRANLIST></OFX>"
    ).encode()
    source, run, _ = create_source_file(
        organization=organization,
        company=company,
        financial_account=account,
        filename="extrato-teste.ofx",
        content=bank,
        origin="bank_statement",
    )
    result = process_run(str(run.pk))
    assert result["created"] == count
    output = io.StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(LEDGER_COLUMNS)
    for i in range(count):
        common = [f"entry-{i}", "bank", "2026-09-12", f"Razão independente sintético {i}"]
        writer.writerow([*common, "1.1", "debit", 10000 + i, "inflow", f"DOC-{i}"])
        writer.writerow(
            [common[0], "other", *common[2:], "2.1", "credit", 10000 + i, "", f"DOC-{i}"]
        )
    ledger, run, _ = create_source_file(
        organization=organization,
        company=company,
        financial_account=account,
        filename="razao-teste.csv",
        content=output.getvalue().encode(),
        origin="accounting",
    )
    # CSV ingestion validates its chart; the operational regression starts with
    # retained independent journals and no posting chart, as native collection can.
    catalogue = [
        LedgerAccount.objects.create(
            organization=organization, company=company, code=code, name=code
        )
        for code in ("1.1", "2.1")
    ]
    result = process_run(str(run.pk))
    run.refresh_from_db()
    assert result.get("created") == count, run.errors
    LedgerAccount.objects.filter(pk__in=[account.pk for account in catalogue]).delete()
    client = Client()
    client.force_login(user)
    session = client.session
    session["hub_organization_id"] = str(organization.pk)
    session.save()
    return dict(
        user=user, company=company, account=account, source=source, ledger=ledger, client=client
    )


def test_customer_can_compare_confirm_report_and_undo_without_chart_setup(organization):
    case = make_case(organization)
    assert not LedgerAccount.objects.filter(organization=organization).exists()
    client, source = case["client"], case["source"]
    url = reverse("hub:reconciliation-source-review", args=[source.pk])
    first = client.get(reverse("hub:reconciliation"))
    assert first.context["reconciliation_next_action"]["href"] == url
    assert "Abrir conferência" in first.content.decode()
    page = client.get(url)
    assert page.status_code == 200 and page["Cache-Control"] == "no-store, private"
    assert page.context["conference_confirmed_count"] == 0
    assert len(page.context["conference_rows"]) == 3
    assert (
        not MovementReconciliation.objects.exists() and not ReconciliationDecision.objects.exists()
    )
    row = page.context["conference_rows"][0]
    assert row["candidate_count"] == 1 and row["state"] == "pending"
    detail = client.get(row["detail_url"])
    assert "Voltar à conferência" in detail.content.decode()
    assert "Comparar com o registro existente" in detail.content.decode()
    assert 'id="movement-review-form"' not in detail.content.decode()
    assert "DOC-0" in detail.content.decode() and "Baixar razao-teste.csv" in detail.content.decode()
    chosen = detail.context["reconciliation_candidates"][0]["entry"]
    assert chosen.independent_source.external_key == "entry-0"
    response = client.post(
        row["detail_url"],
        {
            "action": "confirm_reconciliation",
            "entry_id": str(chosen.pk),
            "amount_brl": "100.00",
            "evidence_note": "Conferência sintética da fonte independente",
        },
    )
    assert response.status_code == 302
    allocation = MovementReconciliation.objects.get()
    assert allocation.confirmed_by == case["user"] and allocation.state == "confirmed"
    assert not AccountingExport.objects.exists()
    page = client.get(url)
    assert page.context["conference_confirmed_count"] == 1
    assert page.context["conference_page"].paginator.count == 2
    confirmed = client.get(url, {"state": "confirmed"})
    assert len(confirmed.context["conference_rows"]) == 1
    assert confirmed.context["conference_rows"][0]["state"] == "confirmed"
    report = client.get(reverse("hub:reconciliation-source-report", args=[source.pk]))
    assert report.status_code == 200 and "attachment" in report["Content-Disposition"]
    assert b"bank;" in report.content and b"ledger;" in report.content
    undone = client.post(
        row["detail_url"],
        {"action": "undo_reconciliation", "reconciliation_id": str(allocation.pk)},
    )
    assert undone.status_code == 302
    assert client.get(url).context["conference_confirmed_count"] == 0
    assert not LedgerAccount.objects.exists() and not AccountingExport.objects.exists()
    assert ReconciliationDecision.objects.count() == 2


def test_native_candidates_are_scoped_and_prioritized_before_pagination(organization):
    case = make_case(organization, count=35)
    movement = case["source"].movements.get(source_key="ofx:test-0")
    other = FinancialAccount.objects.create(
        organization=organization,
        company=case["company"],
        name="Outra conta",
        account_reference="001:999",
        ledger_code="8",
    )
    # Incompatible records must never fill the first page ahead of the exact one.
    case["ledger"].ledger_records.exclude(external_key="entry-0").update(financial_account=other)
    page = case["client"].get(reverse("hub:reconciliation-movement", args=[movement.pk]))
    entries = page.context["reconciliation_candidates"]
    assert len(entries) == 1 and entries[0]["entry"].independent_source.external_key == "entry-0"
    assert page.context["reconciliation_candidate_page"].paginator.count == 1


@pytest.mark.parametrize("target", ["source", "ledger"])
def test_source_review_is_company_and_tenant_scoped(organization, target):
    case = make_case(organization)
    outsider = Organization.objects.create(name="Outro escritório", slug="workbench-outsider")
    other = make_case(outsider)
    assert (
        case["client"]
        .get(reverse("hub:reconciliation-source-review", args=[other[target].pk]))
        .status_code
        == 404
    )
    if target == "ledger":
        assert (
            case["client"]
            .get(reverse("hub:reconciliation-source-review", args=[case[target].pk]))
            .status_code
            == 404
        )


def test_auditor_can_consult_but_cannot_confirm(organization):
    case = make_case(organization, role="auditor")
    url = reverse("hub:reconciliation-source-review", args=[case["source"].pk])
    page = case["client"].get(url)
    assert page.status_code == 200 and not page.context["can_review_conference"]
    assert "Comparar e revisar" not in page.content.decode()
    movement = case["source"].movements.first()
    entry = case["ledger"].ledger_records.first().entry
    response = case["client"].post(
        reverse("hub:reconciliation-movement", args=[movement.pk]),
        {
            "action": "confirm_reconciliation",
            "entry_id": str(entry.pk),
            "amount_brl": "100.00",
            "evidence_note": "Sem permissão",
        },
    )
    assert response.status_code == 403 and not MovementReconciliation.objects.exists()


def test_workbench_filter_pagination_and_back_link_preserve_context(organization):
    case = make_case(organization, count=55)
    url = reverse("hub:reconciliation-source-review", args=[case["source"].pk])
    page = case["client"].get(url, {"state": "all", "q": "Recebimento", "page": 2})
    assert len(page.context["conference_rows"]) == 5
    row = page.context["conference_rows"][0]
    detail = case["client"].get(row["detail_url"])
    back = detail.context["conference_return_url"]
    assert "state=all" in back and "q=Recebimento" in back and "page=2" in back
    empty = case["client"].get(url, {"q": "não existe"})
    assert not empty.context["conference_rows"]
    assert case["client"].get(url, {"state": "bad", "page": "bad"}).status_code == 200


@pytest.mark.parametrize(
    "return_to",
    [
        "https://example.com/",
        "//example.com/",
        "/app/conciliacao/arquivos/00000000-0000-0000-0000-000000000000/revisao/",
        "/app/conciliacao/\\bad",
    ],
)
def test_back_link_cannot_leave_the_same_source(organization, return_to):
    case = make_case(organization, count=1)
    movement = case["source"].movements.first()
    page = case["client"].get(
        reverse("hub:reconciliation-movement", args=[movement.pk]), {"return_to": return_to}
    )
    assert page.status_code == 200 and not page.context["conference_return_url"]


def test_workbench_keeps_conflict_priority_and_source_failure_guidance(organization):
    case = make_case(organization, count=1)
    movement = case["source"].movements.first()
    movement.review_state = "conflict"
    movement.save()
    page = case["client"].get(reverse("hub:reconciliation"))
    assert page.context["reconciliation_next_action"]["label"] == "Revisar conflitos"
    case["source"].content.delete(save=False)
    page = case["client"].get(reverse("hub:reconciliation-source-review", args=[case["source"].pk]))
    assert page.status_code == 302 and "processamentos" in page.url
