from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.dte_payload import list_page
from apps.hub.models import (
    ClientCompany,
    DteMessage,
    DteMessageObservation,
    DteMessageState,
    DteRun,
    DteRunItem,
    OfficeProfile,
)
from apps.hub.services import (
    DTE_ACTION_CODE,
    DteRunTransitionError,
    approve_dte_run,
    cancel_dte_run,
    prepare_dte_next_page,
)
from apps.hub.tasks import _save_messages, dispatch_dte_run
from apps.integra.errors import IntegraConfigurationError
from apps.organizations.models import Membership, Organization
from apps.platform.billing import reserve_usage
from apps.platform.models import (
    Plan,
    PlanServiceRate,
    TenantContract,
    TenantUsagePolicy,
    TokenActionWeight,
    TokenModuleRate,
    TokenPriceBook,
    TokenUsageEvent,
    UsageEvent,
)

pytestmark = pytest.mark.django_db


def test_dte_approval_uses_accepted_token_book_and_links_each_company() -> None:
    organization = Organization.objects.create(name="DTE tokens", slug="dte-tokens")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa", cnpj_masked="12.345.678/0001-95"
    )
    plan = Plan.objects.create(code="dte-token-plan", name="DTE tokens")
    contract = TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    owner = User.objects.create_user("dte-token-owner@example.test", "test-password")
    Membership.objects.create(organization=organization, user=owner, role=Membership.Role.OWNER)
    book = TokenPriceBook.objects.create(
        contract=contract, version=1,
        token_price_cents=5, monthly_overage_cap_cents=500,
        effective_from=timezone.localdate().replace(day=1), accepted_by=owner,
        accepted_at=timezone.now(), activated_at=timezone.now(),
    )
    rate = TokenModuleRate.objects.create(
        book=book, module_code="integra", monthly_base_cents=1000, included_tokens=100
    )
    TokenActionWeight.objects.create(
        module_rate=rate, action_code=DTE_ACTION_CODE, tokens=4
    )
    TokenPriceBook.objects.filter(id=book.id).update(status=TokenPriceBook.Status.ACTIVE)
    run = DteRun.objects.create(organization=organization, total_companies=1)
    item = DteRunItem.objects.create(organization=organization, run=run, company=company)

    with patch("apps.hub.services.transaction.on_commit"):
        approve_dte_run(run=run, actor=owner)

    item.refresh_from_db()
    event = TokenUsageEvent.objects.get(id=item.token_usage_event_id)
    assert event.tokens == 4
    assert event.action_code == DTE_ACTION_CODE
    assert item.usage_event_id is None


def test_demo_dte_run_completes_locally_without_serpro() -> None:
    organization = Organization.objects.create(
        name="Demonstração fictícia", slug="dte-demo-central", is_demo=True
    )
    company = ClientCompany.objects.create(organization=organization, name="Empresa fictícia")
    DteMessage.objects.create(
        organization=organization,
        company=company,
        source_isn="demo-1",
        subject="Aviso fictício",
        sender="Origem simulada",
        sent_at=timezone.now(),
    )
    run = DteRun.objects.create(
        organization=organization, status=DteRun.Status.QUEUED, total_companies=1
    )
    item = DteRunItem.objects.create(organization=organization, run=run, company=company)
    with patch("apps.hub.tasks.IntegraClient") as client:
        dispatch_dte_run.run(str(run.id))
    client.assert_not_called()
    run.refresh_from_db()
    item.refresh_from_db()
    assert run.status == DteRun.Status.COMPLETED
    assert run.messages_found == 1
    assert item.service_response_id.startswith("DEMO-")


def test_demo_dte_approval_needs_no_commercial_contract_or_usage_event() -> None:
    organization = Organization.objects.create(
        name="DTE demo", slug="dte-demo-approval", is_demo=True
    )
    company = ClientCompany.objects.create(
        organization=organization,
        name="Empresa fictícia",
        cnpj_masked="12.345.678/0001-95",
    )
    run = DteRun.objects.create(
        organization=organization, status=DteRun.Status.AWAITING_APPROVAL, total_companies=1
    )
    DteRunItem.objects.create(organization=organization, run=run, company=company)
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        approve_dte_run(run=run, actor=None)
    run.refresh_from_db()
    assert run.status == DteRun.Status.QUEUED
    assert not UsageEvent.objects.filter(organization=organization).exists()
    with patch("apps.hub.tasks.IntegraClient") as client:
        dispatch_dte_run.run(str(run.id))
    client.assert_not_called()
    run.refresh_from_db()
    assert run.status == DteRun.Status.COMPLETED


def test_dte_page_pointer_accepts_new_24_digit_format_and_keeps_rows_without_pointer() -> None:
    payload = {"dados": {"conteudo": [{
        "indicadorUltimaPagina": "N", "ponteiroProximaPagina": "1" * 24,
        "listaMensagens": [{"isn": "123"}],
    }]}}
    assert list_page(payload) == ([{"isn": "123"}], True, "1" * 24)
    payload["dados"]["conteudo"][0]["ponteiroProximaPagina"] = "invalid"
    assert list_page(payload) == ([{"isn": "123"}], True, "")


@patch("apps.hub.tasks.IntegraClient")
def test_dte_worker_settles_usage_and_deduplicates_returned_messages(
    mock_client: MagicMock,
) -> None:
    organization = Organization.objects.create(name="DTE Central", slug="dte-central")
    OfficeProfile.objects.create(organization=organization, cnpj="11.222.333/0001-81")
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
    OfficeProfile.objects.create(organization=organization, cnpj="11.222.333/0001-81")
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
    assert item.next_page_pointer == "20260912093015"
    assert item.messages_found == 1
    assert message.subject == "Processo 2026"
    assert message.sent_at is not None and message.sent_at.year == 2026
    assert timezone.localtime(message.sent_at).hour == 10
    assert message.source_science_at is not None
    mock_client.return_value.call.assert_called_once_with(
        "caixapostal.mensagens",
        contribuinte="12345678000195",
        autor_pedido="11222333000181",
        dados={"statusLeitura": "0", "indicadorPagina": "0"},
    )


@patch("apps.hub.tasks.IntegraClient")
def test_next_dte_page_requires_new_usage_and_uses_saved_pointer(mock_client: MagicMock) -> None:
    organization = Organization.objects.create(name="Caixa em páginas", slug="caixa-em-paginas")
    OfficeProfile.objects.create(organization=organization, cnpj="11.222.333/0001-81")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa", cnpj_masked="12.345.678/0001-95"
    )
    plan = Plan.objects.create(code="caixa-em-paginas", name="Caixa")
    PlanServiceRate.objects.create(plan=plan, action_code=DTE_ACTION_CODE, included_units=10)
    TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    first = DteRun.objects.create(organization=organization, status=DteRun.Status.COMPLETED)
    source = DteRunItem.objects.create(
        organization=organization, run=first, company=company,
        status=DteRunItem.Status.COMPLETED, more_available=True,
        next_page_pointer="20260912093015",
    )
    second = prepare_dte_next_page(source_item=source)
    item = second.items.get()
    assert second.status == DteRun.Status.AWAITING_APPROVAL
    assert item.requested_page_pointer == "20260912093015"
    with pytest.raises(ValueError, match="já foi preparada"):
        prepare_dte_next_page(source_item=source)
    reserve_usage(
        organization=organization,
        action_code=DTE_ACTION_CODE,
        idempotency_key=f"dte-run-item:{item.id}:caixapostal",
    )
    second.status = DteRun.Status.QUEUED
    second.save(update_fields=["status"])
    mock_client.return_value.call.return_value = {
        "status": 200,
        "dados": {"conteudo": [{"indicadorUltimaPagina": "S", "listaMensagens": []}]},
    }
    dispatch_dte_run.run(str(second.id))
    item.refresh_from_db()
    assert item.status == DteRunItem.Status.COMPLETED
    assert item.more_available is False
    mock_client.return_value.call.assert_called_once_with(
        "caixapostal.mensagens",
        contribuinte="12345678000195",
        autor_pedido="11222333000181",
        dados={
            "statusLeitura": "0", "indicadorPagina": "1",
            "ponteiroPagina": "20260912093015",
        },
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
