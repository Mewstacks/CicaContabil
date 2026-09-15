from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.hub.models import (
    ClientCompany,
    DteMessage,
    DteMessageObservation,
    DteMessageState,
    DteRun,
    DteRunItem,
)
from apps.hub.services import (
    DTE_ACTION_CODE,
    DteRunTransitionError,
    approve_dte_run,
    cancel_dte_run,
)
from apps.hub.tasks import _save_messages, dispatch_dte_run
from apps.integra.errors import IntegraConfigurationError
from apps.organizations.models import Organization
from apps.platform.billing import reserve_usage
from apps.platform.models import (
    Plan,
    PlanServiceRate,
    TenantContract,
    TenantUsagePolicy,
    UsageEvent,
)

pytestmark = pytest.mark.django_db


@patch("apps.hub.tasks.IntegraClient")
def test_dte_worker_settles_usage_and_deduplicates_returned_messages(
    mock_client: MagicMock,
) -> None:
    organization = Organization.objects.create(name="DTE Central", slug="dte-central")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa DTE", cnpj_masked="12.345.678/0001-95"
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


@patch("apps.hub.tasks.IntegraClient")
def test_dte_worker_uses_official_nested_rows_dates_and_more_pages(mock_client: MagicMock) -> None:
    organization = Organization.objects.create(name="Caixa oficial", slug="caixa-oficial")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa", cnpj_masked="12.345.678/0001-95"
    )
    plan = Plan.objects.create(code="caixa-oficial", name="Caixa")
    PlanServiceRate.objects.create(plan=plan, action_code=DTE_ACTION_CODE, included_units=10)
    TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    run = DteRun.objects.create(
        organization=organization, status=DteRun.Status.QUEUED, total_companies=1
    )
    item = DteRunItem.objects.create(organization=organization, run=run, company=company)
    reserve_usage(
        organization=organization,
        action_code=DTE_ACTION_CODE,
        idempotency_key=f"dte-run-item:{item.id}:caixapostal",
    )
    mock_client.return_value.call.return_value = {
        "status": 200,
        "dados": json.dumps(
            {
                "codigo": "00",
                "conteudo": [{
                    "indicadorUltimaPagina": "N",
                    "ponteiroProximaPagina": "20260912093015",
                    "listaMensagens": [
                        {
                            "isn": "0000082838",
                            "assuntoModelo": "Processo ++VARIAVEL++",
                            "valorParametroAssunto": "2026",
                            "dataEnvio": "20260912",
                            "horaEnvio": "103015",
                            "dataLeitura": "",
                            "dataCiencia": "20260915",
                        }
                    ],
                }],
            }
        ),
    }

    dispatch_dte_run.run(str(run.id))

    item.refresh_from_db()
    message = DteMessage.objects.get(organization=organization, source_isn="0000082838")
    assert item.status == DteRunItem.Status.COMPLETED
    assert item.more_available is True
    assert item.messages_found == 1
    assert message.subject == "Processo 2026"
    assert message.sent_at is not None and message.sent_at.year == 2026
    assert timezone.localtime(message.sent_at).hour == 10
    assert message.source_science_at is not None
    mock_client.return_value.call.assert_called_once_with(
        "caixapostal.mensagens",
        contribuinte="12345678000195",
        dados={"statusLeitura": "0", "indicadorPagina": "0"},
    )


def test_repeated_list_refreshes_provider_read_and_science_state() -> None:
    organization = Organization.objects.create(name="Refresh DTE", slug="refresh-dte")
    company = ClientCompany.objects.create(organization=organization, name="Empresa")
    run = DteRun.objects.create(organization=organization)
    item = DteRunItem.objects.create(organization=organization, run=run, company=company)

    def response(*, read: str, science: str) -> dict[str, object]:
        return {"dados": json.dumps({"codigo": "00", "conteudo": [{
            "indicadorUltimaPagina": "S",
            "listaMensagens": [{
                "isn": "0000082838", "assuntoModelo": "Aviso fiscal",
                "dataEnvio": "20260912", "horaEnvio": "103015",
                "dataLeitura": read, "dataCiencia": science,
            }],
        }]})}

    _save_messages(item=item, payload=response(read="", science=""))
    message = DteMessage.objects.get(organization=organization, source_isn="0000082838")
    first_seen = message.first_seen_at
    assert message.read_at is None

    second_run = DteRun.objects.create(organization=organization)
    second_item = DteRunItem.objects.create(
        organization=organization, run=second_run, company=company
    )
    _save_messages(item=second_item, payload=response(read="20260915", science="20260915"))
    message.refresh_from_db()
    state = DteMessageState.objects.get(message=message)
    assert message.first_seen_at == first_seen
    assert message.read_at is None
    assert state.read_at is not None
    assert state.science_at is not None
    assert DteMessageObservation.objects.filter(message=message).count() == 2
    assert DteMessage.objects.filter(organization=organization).count() == 1


def test_approval_reserves_central_usage_and_cancellation_keeps_the_request_local() -> None:
    organization = Organization.objects.create(name="Aprovação DTE", slug="approval-dte")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa", cnpj_masked="12.345.678/0001-95"
    )
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


def test_batch_overage_requires_exact_amount_even_when_policy_allows_it() -> None:
    organization = Organization.objects.create(name="Excedente DTE", slug="excedente-dte")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa", cnpj_masked="12.345.678/0001-95"
    )
    plan = Plan.objects.create(code="excedente", name="Excedente")
    PlanServiceRate.objects.create(
        plan=plan, action_code=DTE_ACTION_CODE,
        included_units=0, overage_unit_price_cents=75,
    )
    TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    TenantUsagePolicy.objects.create(
        organization=organization, action_code=DTE_ACTION_CODE,
        overage_mode=TenantUsagePolicy.OverageMode.ALLOW,
        monthly_overage_cap_cents=75,
    )
    run = DteRun.objects.create(
        organization=organization, status=DteRun.Status.AWAITING_APPROVAL,
        total_companies=1,
    )
    DteRunItem.objects.create(organization=organization, run=run, company=company)

    with pytest.raises(DteRunTransitionError, match="valor exato"):
        approve_dte_run(run=run)
    with pytest.raises(DteRunTransitionError, match="valor exato"):
        approve_dte_run(run=run, approved_overage=True, approved_overage_total_cents=74)
    assert not UsageEvent.objects.filter(organization=organization).exists()

    with (
        patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: callback()),
        patch("apps.hub.tasks.dispatch_dte_run.delay") as mock_delay,
    ):
        approve_dte_run(
            run=run, approved_overage=True, approved_overage_total_cents=75
        )
    assert UsageEvent.objects.get(organization=organization).status == UsageEvent.Status.RESERVED
    mock_delay.assert_called_once_with(str(run.id))


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
