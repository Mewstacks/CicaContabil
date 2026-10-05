from __future__ import annotations

import base64
import json
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.mfa import SESSION_KEY
from apps.accounts.models import User
from apps.hub.models import (
    ClientCompany,
    FiscalGuide,
    FiscalGuideAttemptEvent,
    OfficeProfile,
    ProductModule,
)
from apps.hub.services import FiscalGuideTransitionError, issue_fiscal_guide, sync_fiscal_guides
from apps.hub.tasks import dispatch_fiscal_guide
from apps.integra.errors import IntegraServiceError, IntegraTransportError
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
    ProductModule.objects.create(
        organization=organization,
        code=ProductModule.Code.GUIDES,
        enabled=True,
    )
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


def test_attempt_history_preserves_legacy_result_and_separates_next_response():
    guide = _guide()
    actor = Membership.objects.get(organization=guide.organization).user
    guide.status = FiscalGuide.Status.FAILED
    guide.issue_attempt = 1
    guide.issue_requested_by = actor
    guide.issue_requested_at = timezone.now()
    guide.provider_request_id = "previous-request"
    guide.provider_payload = '{"previous":"private-result"}'
    guide.error_code = "service"
    guide.save()
    with patch("apps.hub.services.transaction.on_commit"):
        issue_fiscal_guide(guide=guide, actor=actor)
    guide.refresh_from_db()
    previous = guide.attempt_events.get(attempt=1)
    assert previous.status == FiscalGuide.Status.FAILED
    assert previous.request_snapshot["snapshot_source"] == "current_record"
    assert previous.provider_request_id == "previous-request"
    assert previous.provider_payload == '{"previous":"private-result"}'
    assert previous.requested_by_reference == str(actor.pk)
    assert previous.consumption_reference == f"fiscal-guide:{guide.pk}:1"
    assert guide.provider_request_id == guide.provider_payload == ""
    assert guide.issued_at is None
    assert guide.attempt_events.get(attempt=2).provider_payload == ""
    with patch("apps.hub.tasks.IntegraClient") as provider:
        provider.return_value.call.return_value = {
            "status": 200,
            "requestId": "new-request",
            "dados": json.dumps({
                "PDFByteArrayBase64": base64.b64encode(b"%PDF-1.7\nDARF").decode(),
            }),
        }
        dispatch_fiscal_guide.run(str(guide.pk))
        dispatch_fiscal_guide.run(str(guide.pk))
        provider.return_value.call.assert_called_once()
    assert list(guide.attempt_events.filter(attempt=2).values_list("status", flat=True)) == [
        FiscalGuide.Status.QUEUED, FiscalGuide.Status.ISSUING, FiscalGuide.Status.ISSUED,
    ]
    issued = guide.attempt_events.get(attempt=2, status=FiscalGuide.Status.ISSUED)
    assert issued.provider_request_id == "new-request"
    assert issued.request_snapshot["amount_cents"] == 12_345
    assert issued.request_snapshot["snapshot_source"] == "queued_request"
    usage = TokenUsageEvent.objects.get(idempotency_key=issued.consumption_reference)
    assert usage.status == TokenUsageEvent.Status.SETTLED
    previous.refresh_from_db()
    assert previous.provider_request_id == "previous-request"
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT provider_payload FROM hub_fiscalguideattemptevent WHERE id = %s",
            [FiscalGuideAttemptEvent._meta.pk.get_db_prep_value(previous.pk, connection)],
        )
        assert "private-result" not in cursor.fetchone()[0]


def test_attempt_evidence_is_immutable_and_cannot_cross_organizations():
    from apps.hub.guide_history import record_guide_attempt

    guide = _guide()
    guide.issue_attempt = 1
    guide.status = FiscalGuide.Status.UNKNOWN
    guide.save()
    record_guide_attempt(guide)
    record_guide_attempt(guide)
    evidence = guide.attempt_events.get()
    for operation in (
        evidence.save,
        evidence.delete,
        lambda: guide.attempt_events.update(provider_request_id="replace"),
        lambda: guide.attempt_events.all().delete(),
    ):
        with pytest.raises(ValidationError):
            operation()
    other = Organization.objects.create(name="Other", slug="other")
    with pytest.raises(ValidationError, match="organization"):
        FiscalGuideAttemptEvent.objects.create(
            organization=other, guide=guide, attempt=2, status=FiscalGuide.Status.QUEUED,
        )
    assert guide.attempt_events.count() == 1


def test_history_failure_rolls_back_request_and_reservation():
    guide = _guide()
    with (
        patch(
            "apps.hub.guide_history.record_guide_attempt",
            side_effect=[None, RuntimeError("storage")],
        ),
        patch("apps.hub.services.transaction.on_commit") as enqueue,
        pytest.raises(RuntimeError, match="storage"),
    ):
        issue_fiscal_guide(
            guide=guide, actor=Membership.objects.get(organization=guide.organization).user,
        )
    enqueue.assert_not_called()
    guide.refresh_from_db()
    assert guide.status == FiscalGuide.Status.READY
    assert guide.issue_attempt == 0
    assert not TokenUsageEvent.objects.exists()


def test_guide_requires_identified_authorized_requester_before_reserving():
    guide = _guide()
    with patch("apps.hub.services.reserve_tokens") as reserve:
        with pytest.raises(FiscalGuideTransitionError, match="solicitante"):
            issue_fiscal_guide(guide=guide)
        reserve.assert_not_called()
    guide.refresh_from_db()
    assert guide.status == FiscalGuide.Status.READY
    assert guide.issue_attempt == 0


@pytest.mark.parametrize("revoke_module", [True, False])
def test_guide_worker_refuses_revocation_before_provider_and_releases_reservation(revoke_module):
    guide = _guide()
    member = Membership.objects.get(organization=guide.organization)
    with patch("apps.hub.services.transaction.on_commit"):
        issue_fiscal_guide(guide=guide, actor=member.user)
    if revoke_module:
        ProductModule.objects.filter(organization=guide.organization).update(enabled=False)
    else:
        Membership.objects.filter(pk=member.pk).update(role=Membership.Role.AUDITOR)
    with patch("apps.hub.tasks.IntegraClient") as provider:
        dispatch_fiscal_guide.run(str(guide.pk))
        dispatch_fiscal_guide.run(str(guide.pk))
        provider.assert_not_called()
    guide.refresh_from_db()
    assert guide.status == FiscalGuide.Status.FAILED
    assert guide.error_code == "authorization_revoked"
    usage = TokenUsageEvent.objects.get(idempotency_key=f"fiscal-guide:{guide.pk}:1")
    assert usage.status == TokenUsageEvent.Status.RELEASED


def test_demo_guide_records_only_a_simulated_result() -> None:
    guide = _guide(suffix="-demo")
    guide.organization.is_demo = True
    guide.organization.save(update_fields=["is_demo"])
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        issue_fiscal_guide(
            guide=guide, actor=Membership.objects.get(organization=guide.organization).user
        )
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
        issue_fiscal_guide(
            guide=guide, actor=Membership.objects.get(organization=guide.organization).user
        )

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
        issue_fiscal_guide(
            guide=guide, actor=Membership.objects.get(organization=guide.organization).user
        )
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
def test_guide_worker_preserves_uncertainty_without_a_valid_pdf(mock_client: MagicMock) -> None:
    guide = _guide(suffix="-missing-pdf")
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        issue_fiscal_guide(
            guide=guide, actor=Membership.objects.get(organization=guide.organization).user
        )
    mock_client.return_value.call.return_value = {
        "status": 200,
        "requestId": "guide-without-document",
        "dados": "{}",
    }

    dispatch_fiscal_guide.run(str(guide.id))

    guide.refresh_from_db()
    usage = TokenUsageEvent.objects.get(idempotency_key=f"fiscal-guide:{guide.id}:1")
    assert guide.status == FiscalGuide.Status.UNKNOWN
    assert guide.error_code == "uncertain_result"
    assert guide.provider_request_id == "guide-without-document"
    assert json.loads(guide.provider_payload)["dados"] == "{}"
    uncertain = guide.attempt_events.get(attempt=1, status=FiscalGuide.Status.UNKNOWN)
    assert uncertain.provider_request_id == guide.provider_request_id
    assert uncertain.provider_payload == guide.provider_payload
    assert usage.status == TokenUsageEvent.Status.RESERVED
    dispatch_fiscal_guide.run(str(guide.id))
    mock_client.return_value.call.assert_called_once()
    with pytest.raises(FiscalGuideTransitionError):
        issue_fiscal_guide(
            guide=guide,
            actor=Membership.objects.get(organization=guide.organization).user,
        )


def test_guide_transport_timeout_preserves_reservation_and_blocks_retry():
    guide = _guide()
    actor = Membership.objects.get(organization=guide.organization).user
    with patch("apps.hub.services.transaction.on_commit"):
        issue_fiscal_guide(guide=guide, actor=actor)
    with patch("apps.hub.tasks.IntegraClient") as provider:
        provider.return_value.call.side_effect = IntegraTransportError("timeout")
        dispatch_fiscal_guide.run(str(guide.pk))
        dispatch_fiscal_guide.run(str(guide.pk))
        provider.return_value.call.assert_called_once()
    guide.refresh_from_db()
    assert guide.status == FiscalGuide.Status.UNKNOWN
    assert guide.issued_at is None
    assert TokenUsageEvent.objects.get().status == TokenUsageEvent.Status.RESERVED
    with pytest.raises(FiscalGuideTransitionError):
        issue_fiscal_guide(guide=guide, actor=actor)
    assert TokenUsageEvent.objects.count() == 1
    from apps.hub.services import (
        DctfWebDocumentTransitionError,
        prepare_dctfweb_guide_from_documents,
    )

    with pytest.raises(DctfWebDocumentTransitionError, match="resultado"):
        prepare_dctfweb_guide_from_documents(
            organization=guide.organization,
            company=guide.company,
            competence=guide.competence,
            due_on=guide.due_on,
            amount_cents=guide.amount_cents,
            source_reference="outra-apuracao",
            actor=actor,
        )
    alternative = FiscalGuide.objects.create(
        organization=guide.organization,
        company=guide.company,
        kind=guide.kind,
        reference="outra-referencia",
        competence=guide.competence,
        due_on=guide.due_on,
        integra_service_key=guide.integra_service_key,
    )
    with pytest.raises(FiscalGuideTransitionError, match="emissão anterior"):
        issue_fiscal_guide(guide=alternative, actor=actor)
    assert TokenUsageEvent.objects.count() == 1


def test_legacy_integration_failure_is_quarantined_without_altering_consumption():
    from importlib import import_module
    from types import SimpleNamespace

    from django.apps import apps
    from django.db import connection

    guide = _guide()
    guide.status = "failed"
    guide.error_code = "integration"
    guide.provider_request_id = "old-request"
    guide.save()
    migration = import_module("apps.hub.migrations.0063_alter_fiscalguide_status")
    migration.quarantine_legacy_results(apps, SimpleNamespace(connection=connection))
    guide.refresh_from_db()
    assert guide.status == "unknown"
    assert guide.error_code == "integration"
    assert guide.provider_request_id == "old-request"
    assert not TokenUsageEvent.objects.exists()


def test_guide_worker_fails_safely_without_a_reservation_or_valid_cnpj() -> None:
    missing_usage = _guide(suffix="-missing")
    missing_usage.status = FiscalGuide.Status.QUEUED
    missing_usage.save(update_fields=["status"])
    dispatch_fiscal_guide.run(str(missing_usage.id))
    missing_usage.refresh_from_db()
    assert missing_usage.error_code == "usage_missing"

    invalid_cnpj = _guide(suffix="-invalid")
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        issue_fiscal_guide(
            guide=invalid_cnpj,
            actor=Membership.objects.get(organization=invalid_cnpj.organization).user,
        )
    invalid_cnpj.company.cnpj_masked = "invalido"
    invalid_cnpj.company.save(update_fields=["cnpj_masked"])
    dispatch_fiscal_guide.run(str(invalid_cnpj.id))
    invalid_cnpj.refresh_from_db()
    assert invalid_cnpj.error_code == "invalid_cnpj"


@patch("apps.hub.tasks.IntegraClient")
def test_guide_worker_releases_usage_after_serpro_refusal(mock_client: MagicMock) -> None:
    guide = _guide()
    with patch("apps.hub.services.transaction.on_commit", side_effect=lambda callback: None):
        issue_fiscal_guide(
            guide=guide, actor=Membership.objects.get(organization=guide.organization).user
        )
    mock_client.return_value.call.side_effect = IntegraServiceError(
        "Procuração ausente", status=403, code="authorization"
    )

    dispatch_fiscal_guide.run(str(guide.id))

    guide.refresh_from_db()
    usage = TokenUsageEvent.objects.get(idempotency_key=f"fiscal-guide:{guide.id}:1")
    assert guide.error_code == "authorization"
    assert usage.status == TokenUsageEvent.Status.RELEASED


class GuidesViewTests(TestCase):
    def test_integra_counts_only_companies_with_the_integra_grant(self):
        from apps.hub.models import CompanyAccessGrant, DteMessage, DteRun, DteRunItem

        ProductModule.objects.create(
            organization=self.organization, code=ProductModule.Code.INTEGRA, enabled=True,
        )
        member = Membership.objects.get(organization=self.organization, user=self.user)
        member.role = Membership.Role.OPERATOR
        member.save(update_fields=["role"])
        other = ClientCompany.objects.create(organization=self.organization, name="Other scope")
        for company, module in (
            (self.company, ProductModule.Code.INTEGRA), (other, ProductModule.Code.NFSE),
        ):
            CompanyAccessGrant.objects.create(
                organization=self.organization, membership=member, company=company,
                modules=[module],
            )
            run = DteRun.objects.create(organization=self.organization, total_companies=1)
            DteRunItem.objects.create(organization=self.organization, run=run, company=company)
            DteMessage.objects.create(
                organization=self.organization, company=company, source_isn="message",
                subject="Private message",
            )
        with patch("apps.hub.tasks.IntegraClient") as provider:
            response = self.client.get(reverse("hub:integra"))
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.context["integra_company_count"], 1)
            self.assertEqual(response.context["integra_message_count"], 1)
            self.assertEqual(response.context["integra_pending_count"], 1)
            provider.assert_not_called()

    def test_module_grant_on_another_company_does_not_expose_guides_or_saved_pdfs(self):
        from apps.hub.models import CompanyAccessGrant

        allowed_company = ClientCompany.objects.create(
            organization=self.organization, name="Allowed company", cnpj_masked="11222333000181",
        )
        FiscalGuide.objects.create(
            organization=self.organization, company=allowed_company,
            reference="allowed-guide-reference", kind=FiscalGuide.Kind.DCTFWEB,
            competence="09/2026", due_on=date(2026, 9, 20), integra_service_key="dctfweb.guia",
        )
        member = Membership.objects.get(organization=self.organization, user=self.user)
        CompanyAccessGrant.objects.create(
            organization=self.organization, membership=member, company=allowed_company,
            modules=[ProductModule.Code.GUIDES],
        )
        CompanyAccessGrant.objects.create(
            organization=self.organization, membership=member, company=self.company,
            modules=[ProductModule.Code.NFSE],
        )
        self.guide.status = FiscalGuide.Status.ISSUED
        self.guide.provider_payload = json.dumps({"dados": json.dumps({
            "PDFByteArrayBase64": base64.b64encode(b"%PDF-1.7\nprivate-guide").decode(),
        })})
        self.guide.save()
        event = FiscalGuideAttemptEvent.objects.create(
            organization=self.organization, guide=self.guide, attempt=1,
            status=FiscalGuide.Status.ISSUED, provider_payload=self.guide.provider_payload,
        )
        for role in (Membership.Role.OPERATOR, Membership.Role.AUDITOR):
            with self.subTest(role=role):
                member.role = role
                member.save(update_fields=["role"])
                listing = self.client.get(reverse("hub:guides"), {"status": "all"})
                self.assertEqual(listing.status_code, 200)
                self.assertEqual(
                    {guide.company_id for guide in listing.context["guide_page"]},
                    {allowed_company.pk},
                )
                for url in (
                    reverse("hub:guide-detail", args=[self.guide.pk]),
                    reverse("hub:guide-pdf", args=[self.guide.pk]),
                    reverse("hub:guide-attempt-pdf", args=[self.guide.pk, event.pk]),
                ):
                    self.assertEqual(self.client.get(url).status_code, 404)

    def test_attempt_history_is_paginated_escaped_and_read_only(self):
        for attempt in range(1, 22):
            FiscalGuideAttemptEvent.objects.create(
                organization=self.organization, guide=self.guide, attempt=attempt,
                status=FiscalGuide.Status.UNKNOWN,
                requested_by_reference=str(self.user.pk),
                request_snapshot={"snapshot_source": "current_record"},
                provider_request_id=f"protocol-{attempt}",
                provider_payload='{"private":"never-render-this"}',
                error_message="<script>unsafe()</script>",
            )
        url = reverse("hub:guide-detail", args=[self.guide.pk])
        with patch("apps.hub.tasks.IntegraClient") as provider:
            response = self.client.get(url, {"next": "/app/guias/"})
            self.assertContains(response, "Tentativa 21")
            self.assertNotContains(response, "Tentativa 1 ")
            self.assertNotContains(response, "unsafe()")
            self.assertNotContains(response, "never-render-this")
            self.assertContains(response, self.user.email)
            self.assertContains(response, "history_page=2#historico")
            self.assertContains(response, "next=%2Fapp%2Fguias%2F")
            second = self.client.get(url, {"history_page": 2})
            self.assertContains(second, "Tentativa 1 ")
            self.assertEqual(len(second.context["guide_history_rows"]), 1)
            provider.assert_not_called()
        self.assertEqual(FiscalGuideAttemptEvent.objects.count(), 21)
        self.assertFalse(TokenUsageEvent.objects.exists())
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.issue_attempt, 0)

    def test_saved_attempt_pdf_and_history_require_current_company_access(self):
        from apps.hub.models import CompanyAccessGrant

        payload = {"dados": json.dumps({
            "PDFByteArrayBase64": base64.b64encode(b"%PDF-1.7\nold-guide").decode(),
        })}
        event = FiscalGuideAttemptEvent.objects.create(
            organization=self.organization, guide=self.guide, attempt=1,
            status=FiscalGuide.Status.ISSUED, provider_payload=json.dumps(payload),
        )
        url = reverse("hub:guide-attempt-pdf", args=[self.guide.pk, event.pk])
        with patch("apps.hub.tasks.IntegraClient") as provider:
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.content, b"%PDF-1.7\nold-guide")
            self.assertEqual(response["Cache-Control"], "private, no-store")
            provider.assert_not_called()
        self.assertFalse(TokenUsageEvent.objects.exists())
        other = _guide(suffix="-other-office")
        self.assertEqual(self.client.get(reverse(
            "hub:guide-attempt-pdf", args=[other.pk, event.pk],
        )).status_code, 404)
        self.assertEqual(self.client.get(reverse(
            "hub:guide-detail", args=[other.pk],
        )).status_code, 404)
        member = Membership.objects.get(organization=self.organization, user=self.user)
        member.role = Membership.Role.OPERATOR
        member.save(update_fields=["role"])
        grant = CompanyAccessGrant.objects.create(
            organization=self.organization, membership=member, company=self.company,
            modules=[ProductModule.Code.GUIDES],
        )
        self.assertEqual(self.client.get(url).status_code, 200)
        grant.is_active = False
        grant.save(update_fields=["is_active"])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.get(reverse(
            "hub:guide-detail", args=[self.guide.pk],
        )).status_code, 404)

    databases = {"default", "knowledge"}

    def test_uncertain_guide_is_pending_and_filterable_without_emission_action(self):
        self.guide.status = FiscalGuide.Status.UNKNOWN
        self.guide.save()
        pending = self.client.get(reverse("hub:guides"))
        self.assertContains(pending, self.company.name)
        self.assertContains(pending, "Resolver resultado")
        self.assertNotContains(pending, f'data-modal-open="issue-guide-{self.guide.pk}"')
        filtered = self.client.get(reverse("hub:guides"), {"status": "unknown"})
        self.assertContains(filtered, self.company.name)
        self.assertEqual(filtered.context["guide_status"], "unknown")
        detail = self.client.get(reverse("hub:guide-detail", args=[self.guide.pk]))
        self.assertContains(detail, "Não emita novamente")
        self.assertContains(detail, "Aguardar a conciliação")
        self.assertNotContains(detail, "Confirmar emissão")
        alternative = FiscalGuide.objects.create(
            organization=self.organization,
            company=self.company,
            kind=self.guide.kind,
            reference="referencia-alternativa",
            competence=self.guide.competence,
            due_on=self.guide.due_on,
            integra_service_key=self.guide.integra_service_key,
        )
        searched = self.client.get(reverse("hub:guides"), {"q": "referencia-alternativa"})
        self.assertContains(searched, "Há emissão anterior a confirmar")
        self.assertNotContains(searched, f'data-modal-open="issue-guide-{alternative.pk}"')

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
        self.assertContains(no_result, "Nenhuma guia corresponde aos filtros")
        self.assertNotContains(no_result, "Guias ainda sem fonte validada")

    def test_guides_screen_paginates_the_portfolio_without_hiding_records(self) -> None:
        for index in range(101):
            FiscalGuide.objects.create(
                organization=self.organization,
                company=self.company,
                kind=FiscalGuide.Kind.DCTFWEB,
                reference=f"page-guide-{index:03d}",
                competence="09/2026",
                due_on=date(2026, 1, 1) + timedelta(days=index),
                amount_cents=1_000,
                integra_service_key="dctfweb.guia",
            )

        first_page = self.client.get(reverse("hub:guides"), {"q": "page-guide"})
        second_page = self.client.get(reverse("hub:guides"), {"q": "page-guide", "page": "2"})

        self.assertContains(first_page, "101 resultados")
        self.assertContains(first_page, "Página 1 de 2")
        first_page_references = {
            guide.reference for guide in first_page.context["guide_page"]
        }
        self.assertIn("page-guide-000", first_page_references)
        self.assertNotIn("page-guide-100", first_page_references)
        self.assertContains(second_page, "Página 2 de 2")
        second_page_references = {
            guide.reference for guide in second_page.context["guide_page"]
        }
        self.assertIn("page-guide-100", second_page_references)
        self.assertContains(
            second_page,
            "?q=page-guide&amp;status=pending&amp;due=all&amp;page=1",
            html=False,
        )

    def test_odbc_cadastro_without_guide_source_does_not_claim_zero_debts(self) -> None:
        self.guide.delete()
        IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="healthy",
        )
        response = self.client.get(reverse("hub:guides"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Nenhuma apuração encontrada")
        self.assertContains(response, "Confira a competência e a última sincronização do Domínio.")

    @patch("apps.hub.views.ReadOnlyDominoOdbc")
    def test_odbc_failure_uses_safe_recovery_without_reflecting_connector_error(
        self, adapter
    ) -> None:
        self.company.dominio_code = "323"
        self.company.save(update_fields=["dominio_code"])
        IntelligenceConnector.objects.create(
            organization=self.organization,
            mode=IntelligenceConnector.Mode.DIRECT_ODBC,
            status="healthy",
            odbc_dsn="governed",
        )
        adapter.return_value.execute.side_effect = RuntimeError(
            "Driver failed at SECRET-SERVER\\DOMINIO"
        )

        response = self.client.get(reverse("hub:guides"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A origem não respondeu à leitura")
        self.assertNotContains(response, "SECRET-SERVER")

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
        self.assertContains(response, "1.335,00")
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
        self.guide.status = FiscalGuide.Status.READY
        self.guide.reference = "DEMO-GUIDE"
        self.guide.save(update_fields=["status", "reference"])
        self.assertEqual(
            self.client.get(reverse("hub:demo-guide-pdf", args=[self.guide.id])).status_code,
            404,
        )
        with patch("apps.hub.views.issue_fiscal_guide") as real_issue:
            issued = self.client.post(reverse("hub:issue-guide", args=[self.guide.id]))
        self.assertEqual(issued.status_code, 302)
        real_issue.assert_not_called()
        self.guide.refresh_from_db()
        self.assertEqual(self.guide.status, FiscalGuide.Status.READY)
        detail = self.client.get(reverse("hub:guide-detail", args=[self.guide.id]))
        pdf = self.client.get(reverse("hub:demo-guide-pdf", args=[self.guide.id]))
        self.assertContains(detail, "Baixar DARF fictício")
        self.assertEqual(pdf.status_code, 200)
        self.assertEqual(pdf["Content-Type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertEqual(pdf["Cache-Control"], "private, no-store")
        session = self.client.session
        session.pop("demo_progress", None)
        session.save()
        self.assertEqual(
            self.client.get(reverse("hub:demo-guide-pdf", args=[self.guide.id])).status_code,
            404,
        )
        self.organization.is_demo = False
        self.organization.save(update_fields=["is_demo"])
        self.assertEqual(
            self.client.get(reverse("hub:demo-guide-pdf", args=[self.guide.id])).status_code,
            404,
        )
