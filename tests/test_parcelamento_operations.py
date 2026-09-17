from __future__ import annotations

import base64
import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.mfa import SESSION_KEY
from apps.accounts.models import User
from apps.hub.models import ClientCompany, OfficeProfile, ParcelamentoOperation, ProductModule
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
    OfficeProfile.objects.create(organization=organization, cnpj="11.222.333/0001-81")
    company = ClientCompany.objects.create(
        organization=organization,
        name="Empresa PARCSN",
        cnpj_masked="12.345.678/0001-95",
        dominio_code="323",
    )
    owner = User.objects.create_user("parcsn-owner@example.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=owner, role=Membership.Role.OWNER)
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
            kind=ParcelamentoOperation.Kind.DETAIL,
            agreement_number=42,
        )

    operation.refresh_from_db()
    assert operation.service_key == "parcelamento.parcsn.detalhe"
    assert operation.token_usage_event.tokens == 4
    delay.assert_called_once_with(str(operation.id))


@patch("apps.hub.tasks.IntegraClient")
def test_das_worker_stores_valid_pdf_and_sends_official_input(client: MagicMock) -> None:
    organization, company, _owner = _case()
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        operation = request_parcelamento_operation(
            organization=organization,
            company=company,
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
        ProductModule.objects.create(
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
        self.assertContains(response, "Selecionar todas as exibidas")
        self.assertContains(response, "Empresa, CNPJ ou código Domínio")
        self.assertContains(response, "3 token(s)")

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
