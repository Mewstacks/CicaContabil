from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
from django.test import TestCase
from django.urls import reverse

from apps.accounts.mfa import SESSION_KEY
from apps.accounts.models import User
from apps.hub.models import ClientCompany, FiscalGuide, ProductModule
from apps.hub.services import issue_fiscal_guide, sync_fiscal_guides
from apps.hub.tasks import dispatch_fiscal_guide
from apps.integra.errors import IntegraServiceError
from apps.organizations.models import Membership, Organization
from apps.platform.models import Plan, PlanServiceRate, TenantContract, UsageEvent


def _guide(*, suffix: str = "") -> FiscalGuide:
    organization = Organization.objects.create(name=f"Guias {suffix}", slug=f"guias{suffix}")
    company = ClientCompany.objects.create(
        organization=organization, name="Empresa Guias", cnpj_masked="12.345.678/0001-95"
    )
    plan = Plan.objects.create(code=f"guias{suffix}", name="Guias")
    PlanServiceRate.objects.create(
        plan=plan,
        action_code="dctfweb.guia",
        included_units=5,
        overage_unit_price_cents=150,
    )
    TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
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


def test_issue_guide_reserves_one_central_call_and_queues_the_worker() -> None:
    guide = _guide()
    with (
        patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: callback()),
        patch("apps.hub.tasks.dispatch_fiscal_guide.delay") as mock_delay,
    ):
        issue_fiscal_guide(guide=guide)

    guide.refresh_from_db()
    assert guide.status == FiscalGuide.Status.QUEUED
    assert UsageEvent.objects.filter(idempotency_key=f"fiscal-guide:{guide.id}:1").exists()
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
        "dados": {"documento": "emitido"},
    }

    dispatch_fiscal_guide.run(str(guide.id))

    guide.refresh_from_db()
    usage = UsageEvent.objects.get(idempotency_key=f"fiscal-guide:{guide.id}:1")
    assert guide.status == FiscalGuide.Status.ISSUED
    assert guide.provider_request_id == "guide-42"
    assert usage.status == UsageEvent.Status.SETTLED


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
    usage = UsageEvent.objects.get(idempotency_key=f"fiscal-guide:{guide.id}:1")
    assert guide.error_code == "authorization"
    assert usage.status == UsageEvent.Status.RELEASED


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
        PlanServiceRate.objects.create(
            plan=plan,
            action_code="dctfweb.guia",
            included_units=5,
            overage_unit_price_cents=150,
        )
        TenantContract.objects.create(
            organization=self.organization,
            plan=plan,
            status=TenantContract.Status.ACTIVE,
        )
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
