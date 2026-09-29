from __future__ import annotations

import base64
import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.mfa import SESSION_KEY
from apps.accounts.models import User
from apps.hub.models import (
    ClientCompany,
    CompanyAccessGrant,
    OfficeProfile,
    ParcelamentoOperation,
    ProductModule,
)
from apps.hub.services import request_parcelamento_operation
from apps.hub.tasks import dispatch_parcelamento_operation
from apps.integra.errors import IntegraTransportError
from apps.organizations.models import Membership, Organization
from apps.platform.models import (
    Plan,
    TenantContract,
    TokenActionWeight,
    TokenModuleRate,
    TokenPriceBook,
    TokenUsageEvent,
)

pytestmark = pytest.mark.django_db


def _case() -> tuple[Organization, ClientCompany, User]:
    organization = Organization.objects.create(name="PARCSN", slug="parcsn-test")
    ProductModule.objects.get_or_create(
        organization=organization,
        code=ProductModule.Code.INTEGRA,
        enabled=True,
    )
    OfficeProfile.objects.create(organization=organization, cnpj="11.222.333/0001-81")
    company = ClientCompany.objects.create(
        organization=organization,
        name="Empresa PARCSN",
        cnpj_masked="12.345.678/0001-95",
        dominio_code="323",
    )
    owner = User.objects.create_user("parcsn-owner@example.test", "safe-password-123")
    membership = Membership.objects.create(
        organization=organization, user=owner, role=Membership.Role.OWNER
    )
    CompanyAccessGrant.objects.create(
        organization=organization,
        membership=membership,
        company=company,
        modules=[ProductModule.Code.INTEGRA],
        capabilities=["*"],
    )
    plan = Plan.objects.create(code="parcsn", name="PARCSN")
    contract = TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    book = TokenPriceBook.objects.create(
        contract=contract,
        version=1,
        token_price_cents=5,
        monthly_overage_cap_cents=5_000,
    )
    rate = TokenModuleRate.objects.create(
        book=book,
        module_code="integra",
        monthly_base_cents=10_000,
        included_tokens=100,
    )
    for action, tokens in {
        "parcelamento.parcsn.pedidos": 3,
        "parcelamento.parcsn.detalhe": 4,
        "parcelamento.parcsn.parcelas": 5,
        "parcelamento.parcsn.das": 7,
    }.items():
        TokenActionWeight.objects.create(module_rate=rate, action_code=action, tokens=tokens)
    book.status = TokenPriceBook.Status.ACTIVE
    book.effective_from = date(2026, 9, 1)
    book.activated_at = timezone.now()
    book.accepted_by = owner
    book.accepted_at = timezone.now()
    book.save()
    return organization, company, owner


def test_request_reserves_exact_parcsn_action() -> None:
    organization, company, _owner = _case()
    with (
        patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: callback()),
        patch("apps.hub.tasks.dispatch_parcelamento_operation.delay") as delay,
    ):
        operation = request_parcelamento_operation(
            organization=organization,
            company=company,
            actor=_owner,
            kind=ParcelamentoOperation.Kind.DETAIL,
            agreement_number=42,
        )

    operation.refresh_from_db()
    assert operation.service_key == "parcelamento.parcsn.detalhe"
    assert operation.token_usage_event.tokens == 4
    delay.assert_called_once_with(str(operation.id))


def test_parcsn_requires_identified_requester_before_reserving():
    from apps.hub.services import ParcelamentoTransitionError

    organization, company, _owner = _case()
    with patch("apps.hub.services.reserve_tokens") as reserve:
        with pytest.raises(ParcelamentoTransitionError, match="solicitante"):
            request_parcelamento_operation(
                organization=organization,
                company=company,
                kind=ParcelamentoOperation.Kind.ORDERS,
            )
        reserve.assert_not_called()
    assert not ParcelamentoOperation.objects.exists()


@pytest.mark.parametrize("revoke_module", [True, False])
def test_parcsn_worker_refuses_revocation_before_provider_and_releases_reservation(revoke_module):
    organization, company, owner = _case()
    with patch("apps.hub.services.transaction.on_commit"):
        operation = request_parcelamento_operation(
            organization=organization,
            company=company,
            actor=owner,
            kind=ParcelamentoOperation.Kind.ORDERS,
        )
    if revoke_module:
        ProductModule.objects.filter(organization=organization).update(enabled=False)
    else:
        Membership.objects.filter(organization=organization).update(is_active=False)
    with patch("apps.hub.tasks.IntegraClient") as provider:
        dispatch_parcelamento_operation.run(str(operation.pk))
        dispatch_parcelamento_operation.run(str(operation.pk))
        provider.assert_not_called()
    operation.refresh_from_db()
    assert operation.status == ParcelamentoOperation.Status.FAILED
    assert operation.error_code == "authorization_revoked"
    usage = TokenUsageEvent.objects.get(pk=operation.token_usage_event_id)
    assert usage.status == TokenUsageEvent.Status.RELEASED


@patch("apps.hub.tasks.IntegraClient")
def test_das_worker_stores_valid_pdf_and_sends_official_input(client: MagicMock) -> None:
    organization, company, _owner = _case()
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        operation = request_parcelamento_operation(
            organization=organization,
            company=company,
            actor=_owner,
            kind=ParcelamentoOperation.Kind.DAS,
            competence="202609",
        )
    pdf = b"%PDF-1.7\nDAS\n%%EOF"
    client.return_value.call.return_value = {
        "status": 200,
        "idRequisicao": "das-42",
        "dados": json.dumps({"docArrecadacaoPdfB64": base64.b64encode(pdf).decode()}),
    }

    dispatch_parcelamento_operation.run(str(operation.id))

    operation.refresh_from_db()
    usage = TokenUsageEvent.objects.get(id=operation.token_usage_event_id)
    assert operation.status == ParcelamentoOperation.Status.AVAILABLE
    assert usage.status == TokenUsageEvent.Status.SETTLED
    client.return_value.call.assert_called_once_with(
        "parcelamento.parcsn.das",
        contribuinte="12345678000195",
        autor_pedido="11222333000181",
        dados={"parcelaParaEmitir": 202609},
    )


@patch("apps.hub.tasks.IntegraClient")
def test_uncertain_transport_is_not_replayed_or_released(client: MagicMock) -> None:
    organization, company, _owner = _case()
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        operation = request_parcelamento_operation(
            organization=organization,
            company=company,
            actor=_owner,
            kind=ParcelamentoOperation.Kind.ORDERS,
        )
    client.return_value.call.side_effect = IntegraTransportError("tempo esgotado")

    dispatch_parcelamento_operation.run(str(operation.id))
    dispatch_parcelamento_operation.run(str(operation.id))

    operation.refresh_from_db()
    usage = TokenUsageEvent.objects.get(id=operation.token_usage_event_id)
    assert operation.status == ParcelamentoOperation.Status.UNKNOWN
    assert usage.status == TokenUsageEvent.Status.RESERVED
    assert client.return_value.call.call_count == 1


class ParcelamentoWorkspaceTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.organization, self.company, self.owner = _case()
        ProductModule.objects.get_or_create(
            organization=self.organization, code=ProductModule.Code.INTEGRA, enabled=True
        )
        self.client.force_login(self.owner)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session[SESSION_KEY] = True
        session.save()

    def test_workspace_has_search_select_all_and_real_quote(self) -> None:
        response = self.client.get(reverse("hub:parcelamentos"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Selecionar todas desta página")
        self.assertContains(response, "Empresa, CNPJ ou código Domínio")
        self.assertContains(response, "3 token(s)")

    def test_workspace_paginates_the_portfolio_without_hiding_companies(self) -> None:
        for index in range(101):
            ClientCompany.objects.create(
                organization=self.organization,
                name=f"Carteira de parcelamento {index:03d}",
                cnpj_masked=f"11.222.333/{index:04d}-81",
                dominio_code=f"P{index:03d}",
            )

        first_page = self.client.get(reverse("hub:parcelamentos"), {"search": "Carteira"})
        last_page = self.client.get(
            reverse("hub:parcelamentos"), {"search": "Carteira", "page": "4"}
        )

        self.assertContains(first_page, "101 encontradas")
        self.assertContains(first_page, "Página 1 de 4")
        self.assertContains(first_page, "Carteira de parcelamento 000")
        self.assertNotContains(first_page, "Carteira de parcelamento 100")
        self.assertContains(last_page, "Página 4 de 4")
        self.assertContains(last_page, "Carteira de parcelamento 100")
        self.assertContains(last_page, "?search=Carteira&amp;page=3", html=False)

    def test_workspace_paginates_a_company_operation_history(self) -> None:
        for index in range(21):
            ParcelamentoOperation.objects.create(
                organization=self.organization,
                company=self.company,
                kind=ParcelamentoOperation.Kind.ORDERS,
                status=ParcelamentoOperation.Status.UNKNOWN,
                service_key="parcelamento.parcsn.pedidos",
                provider_request_id=f"history-{index:03d}",
                requested_at=timezone.now() - timedelta(minutes=index),
            )

        first_page = self.client.get(
            reverse("hub:parcelamentos"), {"company": str(self.company.id)}
        )
        second_page = self.client.get(
            reverse("hub:parcelamentos"),
            {"company": str(self.company.id), "operation_page": "2"},
        )

        self.assertContains(first_page, "Página 1 de 2")
        self.assertContains(first_page, "history-000")
        self.assertNotContains(first_page, "history-020")
        self.assertContains(second_page, "Página 2 de 2")
        self.assertContains(second_page, "history-020")
        self.assertContains(
            second_page,
            f"?company={self.company.id}&amp;operation_page=1",
            html=False,
        )

    def test_bulk_confirmation_reserves_every_selected_company(self) -> None:
        second = ClientCompany.objects.create(
            organization=self.organization,
            name="Outra empresa",
            cnpj_masked="11.222.333/0001-81",
            dominio_code="324",
        )
        with patch("apps.hub.services.transaction.on_commit"):
            response = self.client.post(
                reverse("hub:parcelamentos"),
                {
                    "action": "consult_selected",
                    "selected_company": [str(self.company.id), str(second.id)],
                    "approved_overage_cents": "0",
                },
            )

        self.assertRedirects(response, reverse("hub:parcelamentos"))
        self.assertEqual(ParcelamentoOperation.objects.count(), 2)
        self.assertEqual(TokenUsageEvent.objects.count(), 2)

    def test_auditor_can_read_results_without_being_offered_billable_actions(self) -> None:
        Membership.objects.filter(organization=self.organization, user=self.owner).update(
            role=Membership.Role.AUDITOR
        )
        response = self.client.get(reverse("hub:parcelamentos"))
        self.assertContains(response, "Somente leitura")
        self.assertContains(response, "Abrir empresa")
        self.assertNotContains(response, 'id="parcelamento-submit"')
        self.assertNotContains(response, 'name="selected_company"')
        response = self.client.post(
            reverse("hub:parcelamentos"),
            {"action": "consult_selected", "selected_company": [str(self.company.id)]},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(ParcelamentoOperation.objects.exists())
        self.assertFalse(TokenUsageEvent.objects.exists())


def _stored(
    organization: Organization,
    company: ClientCompany,
    kind: str,
    dados: dict[str, object],
    **fields: object,
) -> ParcelamentoOperation:
    return ParcelamentoOperation.objects.create(
        organization=organization,
        company=company,
        kind=kind,
        status=fields.pop("status", ParcelamentoOperation.Status.AVAILABLE),
        service_key=f"parcelamento.parcsn.{kind}",
        provider_payload=json.dumps({"status": 200, "dados": json.dumps(dados)}),
        **fields,
    )


class ParcelamentoJourneyTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.organization, self.company, self.owner = _case()
        ProductModule.objects.get_or_create(
            organization=self.organization, code=ProductModule.Code.INTEGRA, enabled=True
        )
        self.client.force_login(self.owner)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session[SESSION_KEY] = True
        session.save()
        self.url = f"{reverse('hub:parcelamentos')}?company={self.company.id}"

    def test_company_panel_offers_a_direct_quoted_consultation(self) -> None:
        response = self.client.get(self.url)
        self.assertContains(response, "Consultar pedidos · 3 tokens")
        self.assertContains(response, "Nenhuma consulta executada")

    def test_single_company_bulk_consultation_opens_that_company(self) -> None:
        with patch("apps.hub.services.transaction.on_commit"):
            response = self.client.post(
                reverse("hub:parcelamentos"),
                {
                    "action": "consult_selected",
                    "selected_company": [str(self.company.id)],
                    "approved_overage_cents": "0",
                },
            )
        self.assertRedirects(response, f"{self.url}#company-heading", fetch_redirect_response=False)
        page = self.client.get(self.url)
        self.assertContains(page, "Consulta em andamento")
        self.assertContains(page, "data-auto-refresh")

    def test_detail_consolidation_payments_and_installment_timing_are_rendered(self) -> None:
        _stored(
            self.organization,
            self.company,
            ParcelamentoOperation.Kind.ORDERS,
            {
                "parcelamentos": [
                    {
                        "numero": 42,
                        "situacao": "Em parcelamento",
                        "dataDoPedido": 20250110,
                        "dataDaSituacao": 20250115,
                    }
                ]
            },
        )
        _stored(
            self.organization,
            self.company,
            ParcelamentoOperation.Kind.DETAIL,
            {
                "parcelamento": {
                    "numero": 42,
                    "situacao": "Em parcelamento",
                    "consolidacaoOriginal": {
                        "valorTotalConsolidado": 12000.5,
                        "quantidadeParcelas": 60,
                        "parcelaBasica": 200.01,
                    },
                    "demonstrativoPagamentos": [
                        {
                            "mesDaParcela": 202502,
                            "vencimentoDoDas": 20250228,
                            "dataDeArrecadacao": 20250227,
                            "valorPago": 201.4,
                        }
                    ],
                }
            },
            agreement_number=42,
        )
        now = timezone.localdate()
        current = int(now.strftime("%Y%m"))
        overdue = int((now.replace(day=1) - timedelta(days=1)).strftime("%Y%m"))
        _stored(
            self.organization,
            self.company,
            ParcelamentoOperation.Kind.INSTALLMENTS,
            {
                "listaParcelas": [
                    {"parcela": current, "valor": 210.0},
                    {"parcela": overdue, "valor": 205.0},
                ]
            },
        )

        response = self.client.get(self.url)

        self.assertContains(response, "Acordo 42")
        self.assertContains(response, "R$ 12.000,50")
        self.assertContains(response, "1 pagas de 60")
        self.assertContains(response, "02/2025")
        self.assertContains(response, "Em atraso")
        self.assertContains(response, "Mês atual")
        self.assertContains(response, "Emitir · 7 tokens")
        self.assertContains(response, "Consultar de novo · 3 tokens")

    def test_failed_das_can_be_issued_again(self) -> None:
        _stored(
            self.organization,
            self.company,
            ParcelamentoOperation.Kind.INSTALLMENTS,
            {"listaParcelas": [{"parcela": 202609, "valor": 210.0}]},
        )
        ParcelamentoOperation.objects.create(
            organization=self.organization,
            company=self.company,
            kind=ParcelamentoOperation.Kind.DAS,
            status=ParcelamentoOperation.Status.FAILED,
            service_key="parcelamento.parcsn.das",
            competence="202609",
            error_message="Serpro recusou a parcela.",
        )
        response = self.client.get(self.url)
        self.assertContains(response, "Emitir de novo · 7 tokens")
        self.assertContains(response, "Serpro recusou a parcela.")

    def test_uncertain_result_is_released_only_after_human_check(self) -> None:
        operation = ParcelamentoOperation.objects.create(
            organization=self.organization,
            company=self.company,
            kind=ParcelamentoOperation.Kind.ORDERS,
            status=ParcelamentoOperation.Status.UNKNOWN,
            service_key="parcelamento.parcsn.pedidos",
        )
        page = self.client.get(self.url)
        self.assertContains(page, "Conferido no e-CAC")
        self.assertNotContains(page, "Consultar pedidos · 3 tokens")

        response = self.client.post(
            reverse("hub:parcelamentos"),
            {
                "company": str(self.company.id),
                "operation": str(operation.id),
                "action": "release_uncertain",
            },
        )

        self.assertRedirects(response, f"{self.url}#company-heading", fetch_redirect_response=False)
        operation.refresh_from_db()
        self.assertEqual(operation.status, ParcelamentoOperation.Status.FAILED)
        self.assertEqual(operation.error_code, "manual_review")
        self.assertContains(self.client.get(self.url), "Consultar pedidos · 3 tokens")

    def test_auditor_cannot_release_an_uncertain_result(self) -> None:
        operation = ParcelamentoOperation.objects.create(
            organization=self.organization,
            company=self.company,
            kind=ParcelamentoOperation.Kind.ORDERS,
            status=ParcelamentoOperation.Status.UNKNOWN,
            service_key="parcelamento.parcsn.pedidos",
        )
        Membership.objects.filter(organization=self.organization, user=self.owner).update(
            role=Membership.Role.AUDITOR
        )
        response = self.client.post(
            reverse("hub:parcelamentos"),
            {
                "company": str(self.company.id),
                "operation": str(operation.id),
                "action": "release_uncertain",
            },
        )
        self.assertEqual(response.status_code, 403)
        operation.refresh_from_db()
        self.assertEqual(operation.status, ParcelamentoOperation.Status.UNKNOWN)
