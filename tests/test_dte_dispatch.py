from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.hub.models import ClientCompany, DteMessage, DteRun, DteRunItem
from apps.hub.services import DTE_ACTION_CODE, approve_dte_run, cancel_dte_run
from apps.hub.tasks import dispatch_dte_run
from apps.integra.errors import IntegraConfigurationError
from apps.organizations.models import Organization
from apps.platform.billing import reserve_usage
from apps.platform.models import Plan, PlanServiceRate, TenantContract, UsageEvent

pytestmark = pytest.mark.django_db


@patch("apps.hub.tasks.IntegraClient")
def test_dte_worker_settles_usage_and_deduplicates_returned_messages(
    mock_client: MagicMock,
) -> None:
    organization = Organization.objects.create(name="DTE Central", slug="dte-central")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa DTE", cnpj_masked="12.345.678/0001-90"
    )
    plan = Plan.objects.create(code="dte", name="DTE")
    PlanServiceRate.objects.create(
        plan=plan,
        action_code=DTE_ACTION_CODE,
        included_units=10,
        overage_unit_price_cents=100,
    )
    TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    run = DteRun.objects.create(
        organization=organization, status=DteRun.Status.QUEUED, total_companies=1
    )
    item = DteRunItem.objects.create(organization=organization, run=run, company=company)
    usage = reserve_usage(
        organization=organization,
        action_code=DTE_ACTION_CODE,
        idempotency_key=f"dte-run-item:{item.id}:caixapostal",
    )
    client = mock_client.return_value
    client.call.return_value = {
        "status": 200,
        "requestId": "serpro-42",
        "dados": {
            "mensagens": [
                {
                    "isn": "message-42",
                    "assunto": "Intimação",
                    "dataEnvio": "2026-09-12T10:00:00Z",
                }
            ]
        },
    }

    dispatch_dte_run.run(str(run.id))
    dispatch_dte_run.run(str(run.id))

    run.refresh_from_db()
    item.refresh_from_db()
    usage.refresh_from_db()
    assert run.status == DteRun.Status.COMPLETED
    assert item.status == DteRunItem.Status.COMPLETED
    assert item.messages_found == 1
    assert usage.status == UsageEvent.Status.SETTLED
    assert (
        DteMessage.objects.filter(organization=organization, source_isn="message-42").count() == 1
    )


def test_approval_reserves_central_usage_and_cancellation_keeps_the_request_local() -> None:
    organization = Organization.objects.create(name="Aprovação DTE", slug="approval-dte")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    plan = Plan.objects.create(code="approval", name="Aprovação")
    PlanServiceRate.objects.create(
        plan=plan,
        action_code=DTE_ACTION_CODE,
        included_units=2,
        overage_unit_price_cents=100,
    )
    TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    run = DteRun.objects.create(organization=organization, total_companies=1)
    item = DteRunItem.objects.create(organization=organization, run=run, company=company)

    with (
        patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: callback()),
        patch("apps.hub.tasks.dispatch_dte_run.delay") as mock_delay,
    ):
        confirmation = approve_dte_run(run=run)

    run.refresh_from_db()
    assert confirmation.connector is None
    assert run.status == DteRun.Status.QUEUED
    assert UsageEvent.objects.filter(idempotency_key=f"dte-run-item:{item.id}:caixapostal").exists()
    mock_delay.assert_called_once_with(str(run.id))

    cancelled = DteRun.objects.create(organization=organization, total_companies=1)
    DteRunItem.objects.create(organization=organization, run=cancelled, company=company)
    cancel_dte_run(run=cancelled)
    cancelled.refresh_from_db()
    assert cancelled.status == DteRun.Status.CANCELLED


@patch("apps.hub.tasks.IntegraClient", side_effect=IntegraConfigurationError())
def test_dte_worker_releases_a_reservation_when_central_credentials_are_unavailable(
    _mock_client: MagicMock,
) -> None:
    organization = Organization.objects.create(name="DTE sem chave", slug="dte-without-key")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    plan = Plan.objects.create(code="without-key", name="Sem chave")
    PlanServiceRate.objects.create(
        plan=plan,
        action_code=DTE_ACTION_CODE,
        included_units=2,
        overage_unit_price_cents=100,
    )
    TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    run = DteRun.objects.create(
        organization=organization, status=DteRun.Status.QUEUED, total_companies=1
    )
    item = DteRunItem.objects.create(organization=organization, run=run, company=company)
    usage = reserve_usage(
        organization=organization,
        action_code=DTE_ACTION_CODE,
        idempotency_key=f"dte-run-item:{item.id}:caixapostal",
    )

    dispatch_dte_run.run(str(run.id))

    item.refresh_from_db()
    usage.refresh_from_db()
    assert item.status == DteRunItem.Status.FAILED
    assert item.error_code == "configuration"
    assert usage.status == UsageEvent.Status.RELEASED
