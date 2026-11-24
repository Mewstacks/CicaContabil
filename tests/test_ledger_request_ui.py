"""Synthetic customer requests keep bank uploads independent of the official agent."""

from datetime import date, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.hub.ledger_requests import ledger_request_context, save_ledger_mapping
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    FinancialAccount,
    ReconciliationLedgerMapping,
    ReconciliationSourceFile,
)
from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
from apps.organizations.models import Organization
from test_title_persistence import context as context_fixture

context = context_fixture
pytestmark = pytest.mark.django_db


@pytest.fixture
def case(context):
    account, actor, _ = context
    account.company.dominio_code = "212"
    account.company.save(update_fields=["dominio_code"])
    account.ledger_code = "8"
    account.bank_code = "001"
    account.save(update_fields=["ledger_code", "bank_code"])
    agent = EdgeAgent.objects.create(
        organization=account.organization,
        label="Conexão sintética",
        fingerprint="synthetic-ledger-ui",
        shared_secret="synthetic-only",
        status="active",
        is_official=True,
        last_seen_at=timezone.now(),
    )
    client = Client()
    client.force_login(actor)
    session = client.session
    session["hub_organization_id"] = str(account.organization_id)
    session.save()
    return {"account": account, "actor": actor, "agent": agent, "client": client}


def options(case, **extra):
    return {
        "company": str(case["account"].company_id),
        "account": str(case["account"].pk),
        "month": "2026-09",
        **extra,
    }


def endpoint():
    return reverse("hub:reconciliation-ledger-request")


def mapping(case):
    current = ledger_request_context(account=case["account"], actor=case["actor"])
    save_ledger_mapping(
        account=case["account"],
        actor=case["actor"],
        expected_revision=current["mapping_revision"],
        chart_company_code="212",
        branch_code="212",
        bank_inflow_side="debit",
        evidence_reference="Vínculo sintético revisado",
        confirmed=True,
    )


def command(case, **extra):
    response = case["client"].get(endpoint(), options(case))
    assert response.status_code == 200
    return options(
        case,
        action="request",
        request_key=str(uuid4()),
        expected_mapping_revision=response.context["ledger_mapping_revision"],
        **extra,
    )


def statement():
    return SimpleUploadedFile(
        "extrato-sintetico.csv", b"data;historico;valor\n2026-09-12;Teste;12,00\n"
    )


def test_read_only_selection_and_mapping_guidance(case):
    before = (
        AuditEvent.objects.count(),
        ReconciliationLedgerMapping.objects.count(),
        NativeLedgerCollection.objects.count(),
    )
    response = case["client"].get(endpoint(), options(case))
    assert response.status_code == 200 and "no-store" in response["Cache-Control"]
    assert response.context["ledger_mapping_form"]
    assert not response.context["ledger_can_request"]
    assert (
        AuditEvent.objects.count(),
        ReconciliationLedgerMapping.objects.count(),
        NativeLedgerCollection.objects.count(),
    ) == before
    assert "expected_count" not in response.content.decode()


def test_customer_saves_mapping_and_requests_month_without_extrato(case):
    page = case["client"].get(endpoint(), options(case))
    result = case["client"].post(
        endpoint(),
        options(
            case,
            action="mapping",
            **{
                "mapping-expected_revision": page.context["ledger_mapping_revision"],
                "mapping-chart_company_code": "212",
                "mapping-branch_code": "212",
                "mapping-bank_inflow_side": "debit",
                "mapping-evidence_reference": "Conferido sinteticamente",
                "mapping-confirmed": "on",
            },
        ),
    )
    assert result.status_code == 302
    payload = command(case)
    response = case["client"].post(endpoint(), payload)
    assert response.status_code == 302
    job = NativeLedgerCollection.objects.get()
    assert job.scope["period_start"] == "2026-09-01"
    assert job.scope["period_end_exclusive"] == "2026-10-01"
    assert job.requested_by_id == case["actor"].pk and job.bank_source_id is None
    assert case["client"].post(endpoint(), payload).status_code == 302
    assert NativeLedgerCollection.objects.count() == 1


def test_valid_upload_remains_accepted_when_collection_is_unavailable(case):
    payload = command(case, statement=statement())
    with patch("apps.hub.tasks.process_reconciliation_run.delay"):
        response = case["client"].post(endpoint(), payload)
    assert response.status_code == 409
    assert "Extrato recebido." in response.content.decode()
    assert ReconciliationSourceFile.objects.count() == 1
    assert not NativeLedgerCollection.objects.exists()
    selected = response.context["ledger_form"]["bank_source"].value()
    payload.pop("statement")
    payload["bank_source"] = selected
    assert case["client"].post(endpoint(), payload).status_code == 409
    assert ReconciliationSourceFile.objects.count() == 1


def test_upload_only_and_collection_share_exact_retained_source(case):
    mapping(case)
    payload = command(case, statement=statement())
    with patch("apps.hub.tasks.process_reconciliation_run.delay"):
        response = case["client"].post(endpoint(), {**payload, "action": "upload"})
    assert response.status_code == 302 and "bank_source=" in response.url
    assert not NativeLedgerCollection.objects.exists()
    source = ReconciliationSourceFile.objects.get()
    result = case["client"].post(endpoint(), command(case, bank_source=str(source.pk)))
    assert result.status_code == 302
    assert NativeLedgerCollection.objects.get().bank_source_id == source.pk


@pytest.mark.parametrize("month", ["", "2026-08", "2026-9", "2026-13", "invalid"])
def test_invalid_month_never_defaults_or_creates_job(case, month):
    response = case["client"].get(endpoint(), options(case, month=month))
    assert response.status_code == 400
    assert not NativeLedgerCollection.objects.exists()


def test_duplicate_fields_and_cross_company_source_are_rejected(case):
    payload = command(case)
    assert (
        case["client"].post(endpoint(), {**payload, "month": ["2026-09", "2026-10"]}).status_code
        == 400
    )
    other = ClientCompany.objects.create(
        organization=case["account"].organization, name="Outra sintética"
    )
    assert case["client"].post(endpoint(), {**payload, "company": str(other.pk)}).status_code == 400
    assert not NativeLedgerCollection.objects.exists()


def test_foreign_account_never_exposes_context(case):
    other = Organization.objects.create(name="Outra organização", slug="ledger-ui-foreign")
    company = ClientCompany.objects.create(organization=other, name="Fora da carteira")
    account = FinancialAccount.objects.create(
        organization=other, company=company, name="Conta estrangeira"
    )
    response = case["client"].get(endpoint(), options(case, account=str(account.pk)))
    assert response.status_code == 400
    assert "Conta estrangeira" not in response.content.decode()


def test_auditor_can_consult_but_cannot_request(case, membership):
    mapping(case)
    payload = command(case)
    membership.role = "auditor"
    membership.save(update_fields=["role"])
    CompanyAccessGrant.objects.create(
        organization=case["account"].organization,
        company=case["account"].company,
        membership=membership,
        modules=["reconciliation"],
    )
    response = case["client"].get(endpoint(), options(case))
    assert response.status_code == 200 and not response.context["ledger_can_write"]
    assert case["client"].post(endpoint(), payload).status_code == 403


def test_status_is_based_on_claim_and_keeps_month(case):
    mapping(case)
    assert case["client"].post(endpoint(), command(case)).status_code == 302
    job = NativeLedgerCollection.objects.get()
    url = reverse("hub:reconciliation-ledger-status", args=[job.pk])
    response = case["client"].get(url)
    assert response.status_code == 200 and response.json()["status"] == "queued"
    NativeLedgerCollection.objects.filter(pk=job.pk).update(claimed_at=timezone.now())
    response = case["client"].get(url)
    assert response.json()["status"] == "delivered"
    assert "no-store" in response["Cache-Control"]
    NativeLedgerCollection.objects.filter(pk=job.pk).update(state="review")
    response = case["client"].get(url)
    assert response.json()["can_retry"] and response.json()["retry_key"]
    assert response.json()["retry_url"].startswith("/app/conciliacao/razao/")
    assert len(response.json()["mapping_revision"]) == 64


def test_invalid_upload_does_not_queue_request(case):
    mapping(case)
    payload = command(case, statement=SimpleUploadedFile("executavel.exe", b"not accepted"))
    response = case["client"].post(endpoint(), payload)
    assert response.status_code == 400
    assert (
        not NativeLedgerCollection.objects.exists()
        and not ReconciliationSourceFile.objects.exists()
    )


def test_csrf_required_and_get_does_not_mutate(case):
    client = Client(enforce_csrf_checks=True)
    client.force_login(case["actor"])
    session = client.session
    session["hub_organization_id"] = str(case["account"].organization_id)
    session.save()
    assert client.post(endpoint(), options(case, action="upload")).status_code == 403
    response = client.get(endpoint(), options(case))
    assert response.status_code == 200
    assert response.context["ledger_start"] == date(2026, 9, 1)


def test_retry_checks_return_source_before_creating_new_job(case):
    mapping(case)
    assert case["client"].post(endpoint(), command(case)).status_code == 302
    job = NativeLedgerCollection.objects.get()
    NativeLedgerCollection.objects.filter(pk=job.pk).update(state="review")
    url = reverse("hub:reconciliation-ledger-retry", args=[job.pk])
    revision = ledger_request_context(account=case["account"], actor=case["actor"])[
        "mapping_revision"
    ]
    payload = {"request_key": str(uuid4()), "expected_mapping_revision": revision}
    response = case["client"].post(url + "?bank_source=" + str(uuid4()), payload)
    assert response.status_code == 404 and NativeLedgerCollection.objects.count() == 1
    response = case["client"].post(url, payload)
    assert response.status_code == 302 and NativeLedgerCollection.objects.count() == 2
    assert "month=2026-09" in response.url


def test_multiple_uploads_and_stale_mapping_do_not_hide_prior_file(case):
    mapping(case)
    payload = command(case, statement=[statement(), statement()])
    assert case["client"].post(endpoint(), payload).status_code == 400
    assert not ReconciliationSourceFile.objects.exists()
    payload = command(case, statement=statement())
    payload["expected_mapping_revision"] = "0" * 64
    with patch("apps.hub.tasks.process_reconciliation_run.delay"):
        response = case["client"].post(endpoint(), payload)
    assert response.status_code == 409 and "Extrato recebido." in response.content.decode()
    assert (
        ReconciliationSourceFile.objects.count() == 1
        and not NativeLedgerCollection.objects.exists()
    )


def test_selected_page_still_offers_other_authorized_company_accounts(case):
    other_company = ClientCompany.objects.create(
        organization=case["account"].organization,
        name="Outra empresa disponível",
    )
    other_account = FinancialAccount.objects.create(
        organization=case["account"].organization,
        company=other_company,
        name="Outra conta disponível",
        account_reference="001:456",
    )
    response = case["client"].get(endpoint(), options(case))
    assert response.status_code == 200
    assert other_account in response.context["ledger_form"].fields["account"].queryset
    wrong_pair = case["client"].get(endpoint(), options(case, account=str(other_account.pk)))
    assert wrong_pair.status_code == 400 and wrong_pair.context["ledger_form"].errors["account"]


def online(case):
    EdgeAgent.objects.filter(pk=case["agent"].pk).update(
        ledger_capabilities={"automatic_counts": True},
        ledger_capabilities_observed_at=timezone.now(),
        last_seen_at=timezone.now(),
    )


def test_running_search_shows_progress_and_blocks_duplicates(case):
    """D-403: while the Razão is being fetched the page says so and never queues another."""
    online(case)
    mapping(case)
    assert case["client"].post(endpoint(), command(case)).status_code == 302
    job = NativeLedgerCollection.objects.get()
    page = case["client"].get(endpoint(), options(case))
    html = page.content.decode()
    assert page.context["ledger_active_job"]["job"].pk == job.pk
    assert not page.context["ledger_can_request"]
    assert "Buscando o Razão de 09/2026 no Domínio" in html
    assert 'data-ledger-progress data-ledger-status-url="' in html
    assert "Já há uma busca do Razão em andamento" in html
    assert 'value="request" type="submit" data-busy-label="Solicitando…" disabled' in html
    response = case["client"].post(endpoint(), command(case))
    assert response.status_code == 302
    assert NativeLedgerCollection.objects.count() == 1
    NativeLedgerCollection.objects.filter(pk=job.pk).update(claimed_at=timezone.now())
    html = case["client"].get(endpoint(), options(case)).content.decode()
    assert "Solicitação entregue ao agente" in html


def test_progress_pauses_when_agent_is_offline(case):
    online(case)
    mapping(case)
    assert case["client"].post(endpoint(), command(case)).status_code == 302
    EdgeAgent.objects.filter(pk=case["agent"].pk).update(
        last_seen_at=timezone.now() - timedelta(hours=1)
    )
    html = case["client"].get(endpoint(), options(case)).content.decode()
    assert "Busca do Razão de 09/2026 parada" in html and "ledger-progress is-paused" in html
    assert "O pedido continua na fila" in html
    assert "Confira se o computador do Domínio está ligado" in html


@pytest.mark.parametrize("state", ["review", "failed", "imported"])
def test_finished_search_releases_the_button(case, state):
    mapping(case)
    assert case["client"].post(endpoint(), command(case)).status_code == 302
    NativeLedgerCollection.objects.update(state=state)
    page = case["client"].get(endpoint(), options(case))
    assert page.context["ledger_active_job"] is None
    assert "data-ledger-progress" not in page.content.decode()
    assert page.context["ledger_can_request"]
