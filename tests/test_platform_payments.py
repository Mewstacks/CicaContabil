from __future__ import annotations

from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.platform.models import Invoice, Plan, PlatformAccess, TenantContract
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


def test_asaas_webhook_is_not_a_public_route() -> None:
    assert Client().post("/platform/webhooks/asaas/", data={}).status_code == 404
