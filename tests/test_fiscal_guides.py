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
from apps.hub.models import ClientCompany, FiscalGuide, OfficeProfile, ProductModule
from apps.hub.services import issue_fiscal_guide, sync_fiscal_guides
from apps.hub.tasks import dispatch_fiscal_guide
from apps.integra.errors import IntegraServiceError
from apps.intelligence.models import IntelligenceConnector
from apps.organizations.models import Membership, Organization
from apps.platform.models import (
    Plan,
    TenantContract,
    TokenActionWeight,
    TokenModuleRate,
    TokenPriceBook,
    TokenUsageEvent,
)


def _token_terms(
    *, organization: Organization, contract: TenantContract, accepted_by: User
) -> None:
    book = TokenPriceBook.objects.create(
        contract=contract,
        version=1,
        token_price_cents=5,
        monthly_overage_cap_cents=10_000,
    )
    rate = TokenModuleRate.objects.create(
        book=book,
        module_code="integra",
        monthly_base_cents=10_000,
        included_tokens=1_000,
    )
    TokenActionWeight.objects.create(module_rate=rate, action_code="dctfweb.guia", tokens=9)
    book.status = TokenPriceBook.Status.ACTIVE
    book.effective_from = date(2026, 9, 1)
    book.activated_at = timezone.now()
    book.accepted_by = accepted_by
    book.accepted_at = timezone.now()
    book.save()


def _guide(*, suffix: str = "") -> FiscalGuide:
    organization = Organization.objects.create(name=f"Guias {suffix}", slug=f"guias{suffix}")
    OfficeProfile.objects.create(organization=organization, cnpj="11.222.333/0001-81")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa Guias", cnpj_masked="12.345.678/0001-95"
    )
    plan = Plan.objects.create(code=f"guias{suffix}", name="Guias")
    contract = TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    accepter = User.objects.create_user(
        f"guide-token{suffix or '-base'}@example.test", "safe-password-123"
    )
    Membership.objects.create(organization=organization, user=accepter, role=Membership.Role.OWNER)
    _token_terms(organization=organization, contract=contract, accepted_by=accepter)
    return FiscalGuide.objects.create(
        organization=organization,
        company=company,
        kind=FiscalGuide.Kind.DCTFWEB,
        reference="dctf-2026-09",
        competence="09/2026",
        due_on=date(2026, 9, 20),
        amount_cents=12_345,
        integra_service_key="dctfweb.guia",
    )


pytestmark = pytest.mark.django_db


def test_demo_guide_records_only_a_simulated_result() -> None:
    guide = _guide(suffix="-demo")
    guide.organization.is_demo = True
    guide.organization.save(update_fields=["is_demo"])
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        issue_fiscal_guide(guide=guide)
    with patch("apps.hub.tasks.IntegraClient") as client:
        dispatch_fiscal_guide.run(str(guide.id))
    client.assert_not_called()
    guide.refresh_from_db()
    assert guide.status == FiscalGuide.Status.ISSUED
    assert guide.provider_request_id.startswith("DEMO-")
    assert '"simulated": true' in guide.provider_payload
    assert not TokenUsageEvent.objects.filter(idempotency_key=f"fiscal-guide:{guide.id}:1").exists()


def test_issue_guide_reserves_one_central_call_and_queues_the_worker() -> None:
    guide = _guide()
    with (
        patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: callback()),
        patch("apps.hub.tasks.dispatch_fiscal_guide.delay") as mock_delay,
    ):
        issue_fiscal_guide(guide=guide)

    guide.refresh_from_db()
    assert guide.status == FiscalGuide.Status.QUEUED
    assert TokenUsageEvent.objects.filter(idempotency_key=f"fiscal-guide:{guide.id}:1").exists()
    mock_delay.assert_called_once_with(str(guide.id))


def test_dominio_snapshot_creates_and_updates_only_pending_obligations() -> None:
    guide = _guide()
    guide.company.dominio_code = "001"
    guide.company.save(update_fields=["dominio_code"])

    first = sync_fiscal_guides(
        organization=guide.organization,
        rows=[
            {
                "company_code": "001",
                "reference": "dominio-42",
                "kind": "dctfweb",
                "competence": "09/2026",
                "due_on": "2026-09-20",
                "amount_cents": 12_345,
            }
        ],
    )
    synced = FiscalGuide.objects.get(organization=guide.organization, reference="dominio-42")
    second = sync_fiscal_guides(
        organization=guide.organization,
        rows=[
            {
                "company_code": "001",
                "reference": "dominio-42",
                "kind": "dctfweb",
                "competence": "09/2026",
                "due_on": "2026-09-25",
                "amount_cents": 13_000,
            }
        ],
    )

    synced.refresh_from_db()
    assert first.created == 1
    assert second.updated == 1
    assert synced.status == FiscalGuide.Status.DISCOVERED
    assert synced.amount_cents == 13_000


def test_dominio_snapshot_ignores_invalid_obligations() -> None:
    guide = _guide()
    guide.company.dominio_code = "001"
    guide.company.save(update_fields=["dominio_code"])

    result = sync_fiscal_guides(
        organization=guide.organization,
        rows=[
            {
                "company_code": "001",
                "reference": "bad",
                "kind": "dctfweb",
                "competence": "13/2026",
                "due_on": "2026-09-20",
                "amount_cents": 10,
            },
            {
                "company_code": "001",
                "reference": "bad-date",
                "kind": "dctfweb",
                "competence": "09/2026",
                "due_on": "wrong",
                "amount_cents": 10,
            },
        ],
    )

    assert result.ignored == 2
    assert not FiscalGuide.objects.filter(organization=guide.organization, reference="bad").exists()


@patch("apps.hub.tasks.IntegraClient")
def test_guide_worker_records_the_serpro_result(mock_client: MagicMock) -> None:
    guide = _guide()
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        issue_fiscal_guide(guide=guide)
    mock_client.return_value.call.return_value = {
        "status": 200,
        "requestId": "guide-42",
        "dados": json.dumps({"PDFByteArrayBase64": base64.b64encode(b"%PDF-1.7\nDARF").decode()}),
    }

    dispatch_fiscal_guide.run(str(guide.id))

    guide.refresh_from_db()
    usage = TokenUsageEvent.objects.get(idempotency_key=f"fiscal-guide:{guide.id}:1")
    assert guide.status == FiscalGuide.Status.ISSUED
    assert guide.provider_request_id == "guide-42"
    assert usage.status == TokenUsageEvent.Status.SETTLED
    mock_client.return_value.call.assert_called_once_with(
        "dctfweb.guia",
        contribuinte="12345678000195",
        autor_pedido="11222333000181",
        dados={"categoria": "GERAL_MENSAL", "anoPA": "2026", "mesPA": "09"},
    )


@patch("apps.hub.tasks.IntegraClient")
def test_guide_worker_rejects_http_success_without_a_valid_pdf(mock_client: MagicMock) -> None:
    guide = _guide(suffix="-missing-pdf")
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        issue_fiscal_guide(guide=guide)
    mock_client.return_value.call.return_value = {
        "status": 200,
        "requestId": "guide-without-document",
        "dados": "{}",
    }

    dispatch_fiscal_guide.run(str(guide.id))

    guide.refresh_from_db()
    usage = TokenUsageEvent.objects.get(idempotency_key=f"fiscal-guide:{guide.id}:1")
    assert guide.status == FiscalGuide.Status.FAILED
    assert guide.error_code == "integration"
    assert usage.status == TokenUsageEvent.Status.RELEASED


def test_guide_worker_fails_safely_without_a_reservation_or_valid_cnpj() -> None:
    missing_usage = _guide(suffix="-missing")
    missing_usage.status = FiscalGuide.Status.QUEUED
    missing_usage.save(update_fields=["status"])
    dispatch_fiscal_guide.run(str(missing_usage.id))
    missing_usage.refresh_from_db()
    assert missing_usage.error_code == "usage_missing"

    invalid_cnpj = _guide(suffix="-invalid")
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        issue_fiscal_guide(guide=invalid_cnpj)
    invalid_cnpj.company.cnpj_masked = "invalido"
    invalid_cnpj.company.save(update_fields=["cnpj_masked"])
    dispatch_fiscal_guide.run(str(invalid_cnpj.id))
    invalid_cnpj.refresh_from_db()
    assert invalid_cnpj.error_code == "invalid_cnpj"


@patch("apps.hub.tasks.IntegraClient")
def test_guide_worker_releases_usage_after_serpro_refusal(mock_client: MagicMock) -> None:
    guide = _guide()
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        issue_fiscal_guide(guide=guide)
    mock_client.return_value.call.side_effect = IntegraServiceError(
        "Procuração ausente", status=403, code="authorization"
    )

    dispatch_fiscal_guide.run(str(guide.id))

    guide.refresh_from_db()
    usage = TokenUsageEvent.objects.get(idempotency_key=f"fiscal-guide:{guide.id}:1")
    assert guide.error_code == "authorization"
    assert usage.status == TokenUsageEvent.Status.RELEASED


class GuidesViewTests(TestCase):
    databases = {"default", "knowledge"}

    def setUp(self) -> None:
        self.user = User.objects.create_user("guide-owner@example.test", "safe-password-123")
        self.organization = Organization.objects.create(name="Tela Guias", slug="tela-guias")
        Membership.objects.create(
            organization=self.organization, user=self.user, role=Membership.Role.OWNER
        )
        self.company = ClientCompany.objects.create(
            organization=self.organization, name="Empresa da tela", cnpj_masked="12.345.678/0001-95"
        )
        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.GUIDES, enabled=True
        )
        plan = Plan.objects.create(code="tela-guias", name="Tela Guias")
        contract = TenantContract.objects.create(
            organization=self.organization,
            plan=plan,
            status=TenantContract.Status.ACTIVE,
        )
        _token_terms(organization=self.organization, contract=contract, accepted_by=self.user)
        self.guide = FiscalGuide.objects.create(
            organization=self.organization,
            company=self.company,
            kind=FiscalGuide.Kind.DCTFWEB,
            reference="screen-guide",
            competence="09/2026",
            due_on=date(2026, 9, 20),
            amount_cents=12_345,
            integra_service_key="dctfweb.guia",
        )
        self.client.force_login(self.user)
        session = self.client.session
        session["hub_organization_id"] = str(self.organization.id)
        # This office has an active commercial contract. The product rule is
        # MFA after trial/contracting, so view coverage must represent a
        # verified operator instead of silently bypassing the middleware.
        session[SESSION_KEY] = True
        session.save()

    def test_guides_screen_lists_the_domino_obligation_and_keeps_emission_contextual(self) -> None:
        response = self.client.get(reverse("hub:guides"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Guias e DCTFWeb")
        self.assertContains(response, self.company.name)
        self.assertContains(response, "Emitir")

    def test_guides_screen_searches_the_portfolio_and_filters_action_state(self) -> None:
        other_company = ClientCompany.objects.create(
            organization=self.organization,
            name="Empresa sem pendÃªncia",
            cnpj_masked="12.345.678/0001-95",
            dominio_code="0999",
        )
        FiscalGuide.objects.create(
            organization=self.organization,
            company=other_company,
            kind=FiscalGuide.Kind.DCTFWEB,
            status=FiscalGuide.Status.ISSUED,
            reference="issued-guide",
            competence="08/2026",
            due_on=date(2026, 9, 10),
            amount_cents=5000,
            integra_service_key="dctfweb.guia",
        )

        pending = self.client.get(reverse("hub:guides"))
        self.assertContains(pending, self.company.name)
        self.assertNotContains(pending, other_company.name)
        issued = self.client.get(reverse("hub:guides"), {"status": "issued", "q": "0999"})
        self.assertContains(issued, other_company.name)
        self.assertNotContains(issued, self.company.name)
        no_result = self.client.get(
            reverse("hub:guides"), {"status": "all", "q": "empresa inexistente"}
        )
        self.assertContains(no_result, "Nenhuma guia oficial corresponde aos filtros")
        self.assertNotContains(no_result, "Guias ainda sem fonte validada")

    def test_odbc_cadastro_without_guide_source_does_not_claim_zero_debts(self) -> None:
        self.guide.delete()
        IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="healthy",
        )
        response = self.client.get(reverse("hub:guides"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma apuração encontrada nos filtros")
        self.assertContains(response, "Confira a competência e a última sincronização do Domínio.")

    @patch("apps.hub.views.ReadOnlyDominoOdbc")
    def test_odbc_calculations_form_a_searchable_discovery_queue(self, adapter) -> None:
        self.guide.delete()
        self.company.dominio_code = "323"
        self.company.save(update_fields=["dominio_code"])
        IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="healthy",
            odbc_dsn="contabil",
        )
        adapter.return_value.execute.return_value = [
            {
                "source_id": "calc-1",
                "company_code": "323",
                "competence": date(2026, 8, 1),
                "due_on": date(2026, 9, 18),
                "amount": "1234.56",
                "guide_type_code": "1",
                "process_type_code": "11",
                "status_code": "1",
            },
            {
                "source_id": "calc-2",
                "company_code": "323",
                "competence": date(2026, 8, 1),
                "due_on": date(2026, 9, 25),
                "amount": "100.44",
                "guide_type_code": "1",
                "process_type_code": "52",
                "status_code": "1",
            },
        ]

        response = self.client.get(reverse("hub:guides"), {"q": "323"})

        self.assertContains(response, "Apurações do Domínio")
        self.assertContains(response, "08/2026")
        self.assertContains(response, "1335,00")
        self.assertContains(response, "2 componentes")
        self.assertContains(response, "até 25/09/2026")
        self.assertContains(response, f'value="{self.company.id}|08/2026"', count=1)
        self.assertContains(response, "Valores estimados. Confirme na DCTFWeb.")
        adapter.return_value.execute.assert_called_once_with("guide_calculations")

    @patch("apps.hub.views.ReadOnlyDominoOdbc")
    def test_calculation_pages_preserve_filters_and_reach_every_record(self, adapter) -> None:
        self.company.dominio_code = "323"
        self.company.save(update_fields=["dominio_code"])
        IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="healthy",
            odbc_dsn="synthetic",
        )
        adapter.return_value.execute.return_value = [
            {
                "source_id": f"calc-{index}",
                "company_code": "323",
                "competence": date(2020 + index // 12, 1 + index % 12, 1),
                "due_on": date(2026, 9, 20),
                "amount": "100.00",
            }
            for index in range(61)
        ]
        seen = set()
        for number, expected_size in ((1, 30), (2, 30), (3, 1)):
            response = self.client.get(
                reverse("hub:guides"),
                {"q": "323", "status": "all", "due": "all", "apuracao_pagina": number},
            )
            rows = response.context["dominio_calculations"]
            labels = {row["competence_label"] for row in rows}
            self.assertEqual(len(rows), expected_size)
            self.assertFalse(seen & labels)
            seen.update(labels)
            self.assertEqual(response.context["dominio_calculation_total"], 61)
            self.assertEqual(response.context["calculation_query"], "q=323&status=all&due=all")
            self.assertContains(response, "Selecionar esta página")
        self.assertEqual(len(seen), 61)
        invalid = self.client.get(reverse("hub:guides"), {"apuracao_pagina": "invalid"})
        self.assertEqual(invalid.context["calculation_page"].number, 1)

    def test_owner_queues_guide_from_the_contextual_confirmation(self) -> None:
        with (
            patch(
                "apps.hub.services.transaction.on_commit",
                side_effect=lambda callback: callback(),
            ),
            patch("apps.hub.tasks.dispatch_fiscal_guide.delay") as mock_delay,
        ):
            response = self.client.post(reverse("hub:issue-guide", args=[self.guide.id]))

        self.guide.refresh_from_db()
        self.assertRedirects(response, reverse("hub:guides"))
        self.assertEqual(self.guide.status, FiscalGuide.Status.QUEUED)
        mock_delay.assert_called_once_with(str(self.guide.id))

    def test_issued_guide_downloads_the_saved_pdf_without_calling_serpro(self) -> None:
        document = b"%PDF-1.7\nofficial-darf"
        self.guide.status = FiscalGuide.Status.ISSUED
        self.guide.provider_payload = json.dumps(
            {"dados": json.dumps({"PDFByteArrayBase64": base64.b64encode(document).decode()})}
        )
        self.guide.save(update_fields=["status", "provider_payload"])

        with patch("apps.hub.views.IntegraClient", create=True) as client:
            response = self.client.get(reverse("hub:guide-pdf", args=[self.guide.id]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, document)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        client.assert_not_called()

    def test_demo_guide_has_scoped_result_and_nonofficial_pdf(self) -> None:
        self.organization.is_demo = True
        self.organization.save(update_fields=["is_demo"])
        self.guide.status = FiscalGuide.Status.ISSUED
        self.guide.provider_request_id = "DEMO-GUIDE"
        self.guide.save(update_fields=["status", "provider_request_id"])
        detail = self.client.get(reverse("hub:guide-detail", args=[self.guide.id]))
        pdf = self.client.get(reverse("hub:demo-guide-pdf", args=[self.guide.id]))
        self.assertContains(detail, "Baixar PDF fictício sem validade")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertEqual(pdf["Cache-Control"], "private, no-store")
        self.organization.is_demo = False
        self.organization.save(update_fields=["is_demo"])
        self.assertEqual(
            self.client.get(reverse("hub:demo-guide-pdf", args=[self.guide.id])).status_code,
            404,
        )
