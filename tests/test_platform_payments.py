from __future__ import annotations

from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.platform.models import (
    Invoice,
    PaymentAttempt,
    PaymentWebhookDelivery,
    Plan,
    PlatformAccess,
    TenantContract,
)
from apps.platform.payments import ManualBillingError, set_manual_invoice_status
from conftest import complete_mfa

pytestmark = pytest.mark.django_db


def _invoice() -> Invoice:
    organization = Organization.objects.create(name="Financeiro", slug="financeiro")
    plan = Plan.objects.create(code="financeiro", name="Financeiro")
    contract = TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    return Invoice.objects.create(
        organization=organization,
        contract=contract,
        period_start=date(2026, 8, 1),
        period_end=date(2026, 8, 31),
        due_on=date(2026, 9, 10),
    )


def test_manual_billing_records_an_external_collection_without_a_provider() -> None:
    invoice = _invoice()
    contract_status = invoice.contract.status

    updated = set_manual_invoice_status(invoice=invoice, status=Invoice.Status.PAID)

    assert updated.status == Invoice.Status.PAID
    assert updated.payment_attempts.count() == 0
    invoice.contract.refresh_from_db()
    assert invoice.contract.status == contract_status


def test_manual_billing_rejects_unknown_status() -> None:
    with pytest.raises(ManualBillingError):
        set_manual_invoice_status(invoice=_invoice(), status="provider-settled")


def test_platform_admin_can_record_a_manual_invoice_status() -> None:
    invoice = _invoice()
    user = User.objects.create_user(email="admin@example.test", password="safe-password-123")
    PlatformAccess.objects.create(user=user, role=PlatformAccess.Role.ADMIN)
    client = Client()
    client.force_login(user)
    complete_mfa(client)

    response = client.post(
        reverse("platform:tenant-detail", args=[invoice.organization_id]),
        {"action": "invoice-status", "invoice_id": invoice.id, "status": Invoice.Status.PAID},
    )

    assert response.status_code == 302
    invoice.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID


def _asaas_event(
    *, event_id: str, event: str, payment_id: str, method: str = "PIX"
) -> dict[str, object]:
    return {
        "id": event_id,
        "event": event,
        "payment": {"id": payment_id, "billingType": method},
    }


def test_asaas_webhook_is_hidden_until_the_platform_configures_its_token() -> None:
    response = Client().post("/platform/webhooks/asaas/", data={}, content_type="application/json")
    assert response.status_code == 404


def test_asaas_webhook_authenticates_and_processes_each_payment_event_once(settings) -> None:
    settings.ASAAS_WEBHOOK_TOKEN = "a" * 32
    invoice = _invoice()
    attempt = PaymentAttempt.objects.create(
        invoice=invoice,
        provider=PaymentAttempt.Provider.ASAAS,
        method=PaymentAttempt.Method.PIX,
        idempotency_key="asaas-payment-1",
        external_id="pay_123",
    )
    client = Client()
    payload = _asaas_event(
        event_id="evt_123", event="PAYMENT_RECEIVED", payment_id=attempt.external_id
    )

    unauthorized = client.post(
        "/platform/webhooks/asaas/", payload, content_type="application/json"
    )
    response = client.post(
        "/platform/webhooks/asaas/",
        payload,
        content_type="application/json",
        headers={"asaas-access-token": settings.ASAAS_WEBHOOK_TOKEN},
    )
    duplicate = client.post(
        "/platform/webhooks/asaas/",
        payload,
        content_type="application/json",
        headers={"asaas-access-token": settings.ASAAS_WEBHOOK_TOKEN},
    )

    assert unauthorized.status_code == 401
    assert response.status_code == 200
    assert response.json()["status"] == "processed"
    assert duplicate.status_code == 200
    assert duplicate.json()["status"] == "duplicate"
    invoice.refresh_from_db()
    attempt.refresh_from_db()
    assert invoice.status == Invoice.Status.PAID
    assert attempt.status == PaymentAttempt.Status.PAID
    assert PaymentWebhookDelivery.objects.filter(event_id="evt_123").count() == 1


def test_asaas_webhook_keeps_manual_invoices_outside_provider_events(settings) -> None:
    settings.ASAAS_WEBHOOK_TOKEN = "b" * 32
    invoice = _invoice()
    client = Client()

    response = client.post(
        "/platform/webhooks/asaas/",
        _asaas_event(event_id="evt_unknown", event="PAYMENT_RECEIVED", payment_id="pay_unknown"),
        content_type="application/json",
        headers={"asaas-access-token": settings.ASAAS_WEBHOOK_TOKEN},
    )

    invoice.refresh_from_db()
    delivery = PaymentWebhookDelivery.objects.get(event_id="evt_unknown")
    assert response.status_code == 200
    assert response.json()["status"] == "ignored"
    assert delivery.error_code == "payment_not_found"
    assert invoice.status == Invoice.Status.OPEN


def test_asaas_webhook_does_not_downgrade_a_paid_invoice_to_overdue(settings) -> None:
    settings.ASAAS_WEBHOOK_TOKEN = "c" * 32
    invoice = _invoice()
    attempt = PaymentAttempt.objects.create(
        invoice=invoice,
        provider=PaymentAttempt.Provider.ASAAS,
        method=PaymentAttempt.Method.BOLETO,
        idempotency_key="asaas-payment-2",
        external_id="pay_456",
    )
    invoice.status = Invoice.Status.PAID
    invoice.save(update_fields=["status", "updated_at"])

    response = Client().post(
        "/platform/webhooks/asaas/",
        _asaas_event(
            event_id="evt_overdue",
            event="PAYMENT_OVERDUE",
            payment_id=attempt.external_id,
            method="BOLETO",
        ),
        content_type="application/json",
        headers={"asaas-access-token": settings.ASAAS_WEBHOOK_TOKEN},
    )

    invoice.refresh_from_db()
    assert response.status_code == 200
    assert invoice.status == Invoice.Status.PAID
