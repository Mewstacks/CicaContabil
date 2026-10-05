from __future__ import annotations

import base64
import json
from datetime import date
from types import SimpleNamespace
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
    DctfWebDocument,
    FiscalGuide,
    OfficeProfile,
    ProductModule,
)
from apps.hub.services import (
    DctfWebDocumentTransitionError,
    prepare_dctfweb_guide_from_documents,
    request_dctfweb_document,
)
from apps.hub.tasks import dispatch_dctfweb_document
from apps.integra.errors import IntegraTransportError
from apps.intelligence.models import IntelligenceConnector
from apps.organizations.models import Membership, Organization
from apps.platform.models import (
    Plan,
    TenantContract,
    TokenActionWeight,
    TokenModuleRate,
    TokenPriceBook,
    TokenUsageEvent,
    UsageEvent,
)

pytestmark = pytest.mark.django_db


def _case() -> tuple[Organization, ClientCompany]:
    organization = Organization.objects.create(name="DCTF documentos", slug="dctf-documentos")
    OfficeProfile.objects.create(organization=organization, cnpj="11.222.333/0001-81")
    company = ClientCompany.objects.create(
        organization=organization,
        name="Empresa DCTF",
        cnpj_masked="12.345.678/0001-95",
        dominio_code="323",
    )
    ProductModule.objects.create(
        organization=organization,
        code=ProductModule.Code.GUIDES,
        enabled=True,
    )
    plan = Plan.objects.create(code="dctf-docs", name="DCTF documentos")
    contract = TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    accepter = User.objects.create_user("token-accept@example.test", "safe-password-123")
    Membership.objects.create(organization=organization, user=accepter, role=Membership.Role.OWNER)
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
    TokenActionWeight.objects.create(
        module_rate=rate, action_code="dctfweb.declaracao_completa", tokens=8
    )
    TokenActionWeight.objects.create(module_rate=rate, action_code="dctfweb.recibo", tokens=5)
    book.status = TokenPriceBook.Status.ACTIVE
    book.effective_from = date(2026, 9, 1)
    book.activated_at = timezone.now()
    book.accepted_by = accepter
    book.accepted_at = timezone.now()
    book.save()
    return organization, company


def test_document_request_reserves_the_specific_service_and_is_idempotent() -> None:
    organization, company = _case()
    with (
        patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: callback()),
        patch("apps.hub.tasks.dispatch_dctfweb_document.delay") as delay,
    ):
        document = request_dctfweb_document(
            organization=organization,
            company=company,
            actor=Membership.objects.get(organization=organization).user,
            competence="09/2026",
            kind=DctfWebDocument.Kind.RECEIPT,
        )

    document.refresh_from_db()
    assert document.status == DctfWebDocument.Status.QUEUED
    assert document.service_key == "dctfweb.recibo"
    assert document.token_usage_event is not None
    assert document.token_usage_event.action_code == "dctfweb.recibo"
    assert document.token_usage_event.tokens == 5
    delay.assert_called_once_with(str(document.id))


def test_document_request_without_current_actor_is_refused_before_reservation() -> None:
    organization, company = _case()
    with patch("apps.hub.services.reserve_tokens") as reserve:
        with pytest.raises(DctfWebDocumentTransitionError, match="solicitante"):
            request_dctfweb_document(
                organization=organization,
                company=company,
                competence="09/2026",
                kind=DctfWebDocument.Kind.RECEIPT,
            )
        reserve.assert_not_called()
    assert not DctfWebDocument.objects.exists()


@pytest.mark.parametrize(
    "revocation",
    [
        "user",
        "membership",
        "company",
        "module",
        "missing_actor",
        "grant",
        "role",
    ],
)
def test_queued_document_revalidates_access_and_releases_only_unexecuted_usage(revocation):
    organization, company = _case()
    member = Membership.objects.get(organization=organization)
    actor = member.user
    if revocation == "grant":
        member.role = Membership.Role.OPERATOR
        member.save()
        CompanyAccessGrant.objects.create(
            organization=organization,
            company=company,
            membership=member,
            modules=[ProductModule.Code.GUIDES],
            capabilities=["*"],
        )
    with patch("apps.hub.services.transaction.on_commit"):
        document = request_dctfweb_document(
            organization=organization,
            company=company,
            actor=actor,
            competence="09/2026",
            kind=DctfWebDocument.Kind.RECEIPT,
        )
    if revocation == "user":
        User.objects.filter(pk=actor.pk).update(is_active=False)
    elif revocation == "membership":
        Membership.objects.filter(pk=member.pk).update(is_active=False)
    elif revocation == "company":
        ClientCompany.objects.filter(pk=company.pk).update(active=False)
    elif revocation == "module":
        ProductModule.objects.filter(organization=organization).update(enabled=False)
    elif revocation == "missing_actor":
        DctfWebDocument.objects.filter(pk=document.pk).update(requested_by=None)
    elif revocation == "grant":
        CompanyAccessGrant.objects.filter(membership=member).update(is_active=False)
    else:
        Membership.objects.filter(pk=member.pk).update(role=Membership.Role.AUDITOR)
    with patch("apps.hub.tasks.IntegraClient") as provider:
        dispatch_dctfweb_document.run(str(document.pk))
        dispatch_dctfweb_document.run(str(document.pk))
        provider.assert_not_called()
    document.refresh_from_db()
    assert document.status == DctfWebDocument.Status.FAILED
    assert document.error_code == "authorization_revoked"
    assert document.completed_at is not None
    assert (
        TokenUsageEvent.objects.get(pk=document.token_usage_event_id).status
        == TokenUsageEvent.Status.RELEASED
    )


@patch("apps.hub.tasks.IntegraClient")
def test_document_worker_persists_a_valid_pdf_without_a_second_call(
    client: MagicMock,
) -> None:
    organization, company = _case()
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        document = request_dctfweb_document(
            organization=organization,
            company=company,
            actor=Membership.objects.get(organization=organization).user,
            competence="09/2026",
            kind=DctfWebDocument.Kind.DECLARATION,
        )
    client.return_value.call.return_value = {
        "status": 200,
        "idRequisicao": "decl-42",
        "dados": json.dumps(
            {"PDFByteArrayBase64": base64.b64encode(b"%PDF-1.7\ndeclaration").decode()}
        ),
    }

    dispatch_dctfweb_document.run(str(document.id))

    document.refresh_from_db()
    usage = TokenUsageEvent.objects.get(id=document.token_usage_event_id)
    assert document.status == DctfWebDocument.Status.AVAILABLE
    assert usage.status == TokenUsageEvent.Status.SETTLED
    client.return_value.call.assert_called_once_with(
        "dctfweb.declaracao_completa",
        contribuinte="12345678000195",
        autor_pedido="11222333000181",
        dados={"categoria": "GERAL_MENSAL", "anoPA": "2026", "mesPA": "09"},
    )


@patch("apps.hub.tasks.IntegraClient")
def test_transport_uncertainty_is_not_retried_or_released(client: MagicMock) -> None:
    organization, company = _case()
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        document = request_dctfweb_document(
            organization=organization,
            company=company,
            actor=Membership.objects.get(organization=organization).user,
            competence="09/2026",
            kind=DctfWebDocument.Kind.RECEIPT,
        )
    client.return_value.call.side_effect = IntegraTransportError("tempo esgotado")

    dispatch_dctfweb_document.run(str(document.id))
    dispatch_dctfweb_document.run(str(document.id))

    document.refresh_from_db()
    usage = TokenUsageEvent.objects.get(id=document.token_usage_event_id)
    assert document.status == DctfWebDocument.Status.UNKNOWN
    assert usage.status == TokenUsageEvent.Status.RESERVED
    assert client.return_value.call.call_count == 1


def test_guide_requires_both_persisted_official_documents() -> None:
    organization, company = _case()
    DctfWebDocument.objects.create(
        organization=organization,
        company=company,
        kind=DctfWebDocument.Kind.DECLARATION,
        status=DctfWebDocument.Status.AVAILABLE,
        competence="09/2026",
        service_key="dctfweb.declaracao_completa",
    )

    with pytest.raises(DctfWebDocumentTransitionError, match="declaração completa e o recibo"):
        prepare_dctfweb_guide_from_documents(
            organization=organization,
            company=company,
            competence="09/2026",
            due_on=date(2026, 10, 20),
            amount_cents=123_456,
            source_reference="fovguiainss:proof",
        )

    assert not FiscalGuide.objects.filter(organization=organization).exists()


class DctfWebDocumentViewTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.organization, self.company = _case()
        self.user = User.objects.create_user("dctf-owner@example.test", "safe-password-123")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        session[SESSION_KEY] = True
        session.save()

    def test_quote_screen_separates_declaration_and_receipt(self) -> None:
        response = self.client.get(
            reverse("hub:dctfweb-consult"),
            {"company": self.company.id, "competence": "09/2026"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Declaração completa")
        self.assertContains(response, "Recibo de transmissão")
        self.assertContains(response, "Franquia restante")

    def test_missing_or_malformed_company_returns_to_the_portfolio(self) -> None:
        for value in ("", "invalid"):
            for method in (self.client.get, self.client.post):
                response = method(reverse("hub:dctfweb-consult"), {"company": value})
                self.assertRedirects(response, reverse("hub:guides"))

    def test_confirmation_queues_exactly_one_consultation(self) -> None:
        with (
            patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None),
            patch("apps.hub.tasks.dispatch_dctfweb_document.delay"),
        ):
            response = self.client.post(
                reverse("hub:dctfweb-consult"),
                {
                    "company": self.company.id,
                    "competence": "09/2026",
                    "kind": DctfWebDocument.Kind.RECEIPT,
                    "approved_overage_cents": "0",
                },
            )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(
            DctfWebDocument.objects.filter(
                organization=self.organization,
                company=self.company,
                kind=DctfWebDocument.Kind.RECEIPT,
            ).count(),
            1,
        )

    def test_bulk_preview_quotes_all_selected_consultations(self) -> None:
        response = self.client.post(
            reverse("hub:dctfweb-bulk-consult"),
            {
                "kind": DctfWebDocument.Kind.RECEIPT,
                "targets": [
                    f"{self.company.id}|08/2026",
                    f"{self.company.id}|09/2026",
                ],
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "2</strong><small>Máximo de 30")
        self.assertContains(response, "10 tokens")
        self.assertFalse(DctfWebDocument.objects.exists())

    def test_bulk_confirmation_reserves_every_item_before_queueing(self) -> None:
        with patch("apps.hub.services.transaction.on_commit"):
            response = self.client.post(
                reverse("hub:dctfweb-bulk-consult"),
                {
                    "step": "confirm",
                    "kind": DctfWebDocument.Kind.RECEIPT,
                    "approved_overage_cents": "0",
                    "targets": [
                        f"{self.company.id}|08/2026",
                        f"{self.company.id}|09/2026",
                    ],
                },
            )

        self.assertRedirects(response, reverse("hub:guides"))
        self.assertEqual(DctfWebDocument.objects.count(), 2)
        self.assertEqual(TokenUsageEvent.objects.count(), 2)
        self.assertEqual(
            sum(TokenUsageEvent.objects.values_list("tokens", flat=True)),
            10,
        )

    def test_bulk_preview_preserves_machine_cost_and_normalizes_ids(self) -> None:
        with patch(
            "apps.hub.views.quote_tokens",
            return_value=SimpleNamespace(
                total_tokens=5, tokens_per_operation=5, additional_overage_cents=1234
            ),
        ):
            response = self.client.post(
                reverse("hub:dctfweb-bulk-consult"),
                {
                    "kind": "receipt",
                    "targets": [
                        f"{str(self.company.id).upper()}|09/2026",
                        f"{self.company.id}|09/2026",
                    ],
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="approved_overage_cents" value="1234"')
        self.assertContains(response, "1</strong><small>Máximo de 30")
        self.assertFalse(DctfWebDocument.objects.exists())

    def test_invalid_bulk_scope_never_partially_queues(self) -> None:
        for targets in (
            [],
            [f"{self.company.id}|09/0000"],
            [f"{self.company.id}|09/2026", "invalid|09/2026"],
            [f"{self.company.id}|09/2026"] * 31,
        ):
            with (
                self.subTest(targets=targets),
                patch("apps.hub.views.request_dctfweb_document") as service,
            ):
                response = self.client.post(
                    reverse("hub:dctfweb-bulk-consult"),
                    {"kind": "receipt", "step": "confirm", "targets": targets},
                )
                self.assertEqual(response.status_code, 302)
                service.assert_not_called()
        self.assertFalse(TokenUsageEvent.objects.exists())

    def test_invalid_document_kind_is_rejected_without_usage(self) -> None:
        response = self.client.post(
            reverse("hub:dctfweb-consult"),
            {
                "company": self.company.id,
                "competence": "09/2026",
                "kind": "qualquer-servico",
                "approved_overage_cents": "0",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Escolha declaração completa ou recibo")
        self.assertFalse(DctfWebDocument.objects.exists())
        self.assertFalse(UsageEvent.objects.exists())
        self.assertFalse(TokenUsageEvent.objects.exists())

    def test_saved_pdf_download_does_not_call_provider(self) -> None:
        document = DctfWebDocument.objects.create(
            organization=self.organization,
            company=self.company,
            kind=DctfWebDocument.Kind.RECEIPT,
            status=DctfWebDocument.Status.AVAILABLE,
            competence="09/2026",
            service_key="dctfweb.recibo",
            provider_payload=json.dumps(
                {
                    "dados": json.dumps(
                        {"PDFByteArrayBase64": base64.b64encode(b"%PDF-1.7\nreceipt").decode()}
                    )
                }
            ),
        )
        with patch("apps.hub.views.IntegraClient", create=True) as provider:
            response = self.client.get(reverse("hub:dctfweb-document-pdf", args=[document.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"%PDF-1.7\nreceipt")
        provider.assert_not_called()

    def test_refresh_only_reads_state_and_unknown_never_offers_retry(self) -> None:
        document = DctfWebDocument.objects.create(
            organization=self.organization,
            company=self.company,
            kind="receipt",
            competence="09/2026",
            service_key="dctfweb.recibo",
            status="queued",
            error_code="uncertain_result",
            error_message="<script>provider-secret()</script>",
        )
        with patch("apps.hub.views.request_dctfweb_document") as request_service:
            for state in ("queued", "fetching", "unknown"):
                document.status = state
                document.save(update_fields=["status"])
                response = self.client.get(
                    reverse("hub:dctfweb-consult"),
                    {"company": self.company.pk, "competence": "09/2026"},
                )
                self.assertEqual(response.status_code, 200)
                if state == "unknown":
                    self.assertContains(response, "Não repita a consulta")
                    self.assertContains(response, str(document.pk))
                    self.assertNotContains(response, 'name="kind" value="receipt"')
                    self.assertContains(response, "uncertain_result")
                    self.assertNotContains(response, "provider-secret")
                else:
                    self.assertContains(response, "Atualizar situação")
                    self.assertContains(response, "Atualizar não cria outra consulta")
                document.refresh_from_db()
                self.assertEqual(document.status, state)
            request_service.assert_not_called()
        self.assertFalse(TokenUsageEvent.objects.exists())

    @patch("apps.hub.views.ReadOnlyDominoOdbc")
    def test_documents_promote_reloaded_dominio_calculation_to_ready_guide(
        self, adapter: MagicMock
    ) -> None:
        IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="healthy",
            odbc_dsn="contabil",
        )
        for kind, service in {
            DctfWebDocument.Kind.DECLARATION: "dctfweb.declaracao_completa",
            DctfWebDocument.Kind.RECEIPT: "dctfweb.recibo",
        }.items():
            DctfWebDocument.objects.create(
                organization=self.organization,
                company=self.company,
                kind=kind,
                status=DctfWebDocument.Status.AVAILABLE,
                competence="09/2026",
                service_key=service,
            )
        adapter.return_value.execute.return_value = [
            {
                "source_id": "calc-1",
                "company_code": "323",
                "competence": date(2026, 9, 1),
                "due_on": date(2026, 10, 20),
                "amount": "1000.00",
            },
            {
                "source_id": "calc-2",
                "company_code": "323",
                "competence": date(2026, 9, 1),
                "due_on": date(2026, 10, 25),
                "amount": "234.56",
            },
        ]

        response = self.client.post(
            reverse("hub:dctfweb-consult"),
            {
                "company": self.company.id,
                "competence": "09/2026",
                "action": "prepare_guide",
            },
        )

        guide = FiscalGuide.objects.get(
            organization=self.organization,
            company=self.company,
            competence="09/2026",
        )
        self.assertRedirects(response, reverse("hub:guide-detail", args=[guide.id]))
        self.assertEqual(guide.status, FiscalGuide.Status.READY)
        self.assertEqual(guide.amount_cents, 123_456)
        self.assertEqual(guide.due_on, date(2026, 10, 20))
        self.assertTrue(guide.external_key.startswith("fovguiainss:"))
