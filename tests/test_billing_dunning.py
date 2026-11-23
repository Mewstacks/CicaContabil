"""Acesso conforme o pagamento (E3, D-79): carência, somente leitura, reativação e eventos
repetidos, atrasados ou fora de ordem do Asaas."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

import pytest
from django.test import Client
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.platform import dunning
from apps.platform.models import (
    Invoice,
    PaymentAttempt,
    PaymentWebhookDelivery,
    TenantContract,
    TenantLifecycle,
)
from apps.platform.tasks import enforce_payment_policy
from billing_support import contract, invoice, office, owner

pytestmark = pytest.mark.django_db

TODAY = date(2026, 11, 20)
TOKEN = "t" * 32


@pytest.fixture(autouse=True)
def frozen_today(monkeypatch: pytest.MonkeyPatch) -> None:
    """A data do dia é parte do que se testa (carência de 7 dias): congelada em 20/11/2026."""

    monkeypatch.setattr("django.utils.timezone.localdate", lambda *args, **kwargs: TODAY)


def automatic(slug: str = "dunning"):
    organization = office(slug=slug)
    owner(organization, f"dono.{slug}@example.test")
    return organization, contract(organization)


def lifecycle(organization: Any) -> TenantLifecycle:
    return TenantLifecycle.objects.get(organization=organization)


def due(days_ago: int, *, status: str = Invoice.Status.OPEN) -> dict[str, Any]:
    return {"due_on": TODAY - timedelta(days=days_ago), "status": status}


# ---------------------------------------------------------------- desired_access


@pytest.mark.parametrize(
    ("days_ago", "status", "expected"),
    [
        (-5, Invoice.Status.OPEN, ("full", "")),  # ainda não venceu
        (0, Invoice.Status.OPEN, ("full", "")),
        (7, Invoice.Status.OVERDUE, ("full", "")),  # 7 dias de carência inteiros
        (8, Invoice.Status.OVERDUE, ("read_only", "overdue")),
        (8, Invoice.Status.OPEN, ("read_only", "overdue")),  # o evento do provedor não chegou
        (30, Invoice.Status.PAID, ("full", "")),
        (30, Invoice.Status.VOID, ("full", "")),
        (1, Invoice.Status.DISPUTED, ("read_only", "dispute")),
    ],
)
def test_the_carencia_is_seven_full_days_after_the_due_date(
    days_ago: int, status: str, expected: tuple[str, str]
) -> None:
    organization, record = automatic()
    invoice(record, **due(days_ago, status=status))

    assert dunning.desired_access(organization, today=TODAY) == expected


def test_a_dispute_outweighs_a_plain_delay() -> None:
    organization, record = automatic()
    invoice(record, period_start=date(2026, 8, 1), **due(40, status=Invoice.Status.OVERDUE))
    invoice(record, period_start=date(2026, 9, 1), **due(2, status=Invoice.Status.DISPUTED))

    assert dunning.desired_access(organization, today=TODAY) == ("read_only", "dispute")


def test_no_invoice_means_full_access() -> None:
    organization, _ = automatic()

    assert dunning.desired_access(organization, today=TODAY) == ("full", "")


# ---------------------------------------------------------------- sync_access


def test_an_overdue_office_goes_read_only_once_and_comes_back_when_paid() -> None:
    organization, record = automatic()
    late = invoice(record, **due(9, status=Invoice.Status.OVERDUE))

    assert dunning.sync_access(organization, today=TODAY) == dunning.READ_ONLY
    record.refresh_from_db()
    assert record.status == TenantContract.Status.GRACE and record.grace_ends_on == TODAY
    assert lifecycle(organization).state == TenantLifecycle.State.GRACE
    assert "atraso há mais de 7 dias" in lifecycle(organization).reason
    assert dunning.sync_access(organization, today=TODAY) is None  # reaplicar não muda nada
    assert AuditEvent.objects.filter(action="platform.billing.access_read_only").count() == 1

    Invoice.objects.filter(pk=late.pk).update(status=Invoice.Status.PAID)

    assert dunning.sync_access(organization, today=TODAY) == dunning.FULL
    record.refresh_from_db()
    assert record.status == TenantContract.Status.ACTIVE and record.grace_ends_on is None
    assert lifecycle(organization).state == TenantLifecycle.State.ACTIVE
    assert AuditEvent.objects.filter(action="platform.billing.access_restored").count() == 1


def test_a_manual_contract_is_never_touched() -> None:
    organization = office(slug="manual-dunning")
    record = contract(organization, mode=TenantContract.BillingMode.MANUAL)
    invoice(record, **due(60, status=Invoice.Status.OVERDUE))

    assert dunning.sync_access(organization, today=TODAY) is None
    assert dunning.enforce_all(today=TODAY) == {"read_only": 0, "restored": 0, "unchanged": 0}
    record.refresh_from_db()
    assert record.status == TenantContract.Status.ACTIVE
    assert lifecycle(organization).state == TenantLifecycle.State.ACTIVE


@pytest.mark.parametrize(
    "state",
    [
        TenantLifecycle.State.SUSPENDED,
        TenantLifecycle.State.ARCHIVED,
        TenantLifecycle.State.PROVISIONING,
        TenantLifecycle.State.ACTIVATION_PENDING,
    ],
)
def test_a_suspended_archived_or_unactivated_office_is_left_alone(state: str) -> None:
    organization, record = automatic()
    invoice(record, **due(60, status=Invoice.Status.OVERDUE))
    TenantLifecycle.objects.filter(organization=organization).update(state=state)

    assert dunning.sync_access(organization, today=TODAY) is None
    assert lifecycle(organization).state == state


def test_an_office_without_a_lifecycle_row_is_left_alone() -> None:
    organization = office(slug="sem-ciclo")
    record = contract(organization, lifecycle=None)
    invoice(record, **due(60, status=Invoice.Status.OVERDUE))

    assert dunning.sync_access(organization, today=TODAY) is None


def test_the_daily_sweep_counts_what_it_changed(settings: Any) -> None:
    late_org, late_contract = automatic("atrasado")
    invoice(late_contract, **due(10, status=Invoice.Status.OVERDUE))
    ok_org, ok_contract = automatic("em-dia")
    invoice(ok_contract, **due(-3))
    back_org, back_contract = automatic("voltando")
    TenantContract.objects.filter(pk=back_contract.pk).update(status=TenantContract.Status.GRACE)
    TenantLifecycle.objects.filter(organization=back_org).update(state=TenantLifecycle.State.GRACE)
    invoice(back_contract, **due(1, status=Invoice.Status.PAID))

    assert dunning.enforce_all(today=TODAY) == {"read_only": 1, "restored": 1, "unchanged": 1}
    assert lifecycle(late_org).state == TenantLifecycle.State.GRACE
    assert lifecycle(ok_org).state == TenantLifecycle.State.ACTIVE
    assert lifecycle(back_org).state == TenantLifecycle.State.ACTIVE


def test_the_scheduled_task_does_nothing_while_collection_is_off(settings: Any) -> None:
    _, record = automatic()
    invoice(record, **due(40, status=Invoice.Status.OVERDUE))

    assert enforce_payment_policy() == {"skipped": 1}
    settings.BILLING_COLLECTION_ENABLED = True
    settings.ASAAS_API_KEY = "chave"
    assert set(enforce_payment_policy()) == {"read_only", "restored", "unchanged"}


# ---------------------------------------------------------------- webhook


def event(
    event_id: str,
    name: str,
    payment_id: str = "pay_1",
    *,
    at: str | None = None,
    method: str = "PIX",
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "id": event_id,
        "event": name,
        "payment": {"id": payment_id, "billingType": method},
    }
    if at is not None:
        payload["dateCreated"] = at
    return payload


def deliver(settings: Any, payload: dict[str, Any]) -> dict[str, Any]:
    settings.ASAAS_WEBHOOK_TOKEN = TOKEN
    response = Client().post(
        "/platform/webhooks/asaas/",
        payload,
        content_type="application/json",
        headers={"asaas-access-token": TOKEN},
    )
    assert response.status_code == 200
    return dict(response.json())


def charged(
    slug: str = "webhook", method: str = PaymentAttempt.Method.PIX.value, **invoice_fields: Any
):
    organization, record = automatic(slug)
    open_invoice = invoice(record, **invoice_fields)
    attempt = PaymentAttempt.objects.create(
        invoice=open_invoice,
        provider=PaymentAttempt.Provider.ASAAS,
        method=method,
        idempotency_key=f"asaas:{open_invoice.pk}:{method}:1",
        external_id="pay_1",
    )
    return organization, record, open_invoice, attempt


def test_a_confirmed_card_payment_reactivates_without_waiting_for_the_money(settings: Any) -> None:
    organization, record, open_invoice, _ = charged(
        method=PaymentAttempt.Method.CARD.value, **due(9, status=Invoice.Status.OVERDUE)
    )
    dunning.sync_access(organization)
    assert lifecycle(organization).state == TenantLifecycle.State.GRACE

    deliver(settings, event("e1", "PAYMENT_CONFIRMED", method="CREDIT_CARD"))

    open_invoice.refresh_from_db()
    assert open_invoice.status == Invoice.Status.PAID
    assert lifecycle(organization).state == TenantLifecycle.State.ACTIVE
    record.refresh_from_db()
    assert record.status == TenantContract.Status.ACTIVE


def test_an_overdue_event_then_payment_closes_the_loop_with_no_manual_step(settings: Any) -> None:
    organization, _, open_invoice, _ = charged(**due(9))

    deliver(settings, event("e1", "PAYMENT_OVERDUE", at="2026-11-19 03:00:00"))
    open_invoice.refresh_from_db()
    assert open_invoice.status == Invoice.Status.OVERDUE
    assert lifecycle(organization).state == TenantLifecycle.State.GRACE  # já passou dos 7 dias

    deliver(settings, event("e2", "PAYMENT_RECEIVED", at="2026-11-20 10:00:00"))

    assert lifecycle(organization).state == TenantLifecycle.State.ACTIVE
    assert Invoice.objects.get(pk=open_invoice.pk).status == Invoice.Status.PAID


def test_an_older_event_arriving_late_never_undoes_a_newer_one(settings: Any) -> None:
    organization, _, open_invoice, attempt = charged(**due(1))
    deliver(settings, event("e1", "PAYMENT_RECEIVED", at="2026-11-18 09:00:00"))
    deliver(settings, event("e2", "PAYMENT_REFUNDED", at="2026-11-20 09:00:00"))
    assert lifecycle(organization).state == TenantLifecycle.State.GRACE
    assert Invoice.objects.get(pk=open_invoice.pk).status == Invoice.Status.DISPUTED

    late = deliver(settings, event("e3", "PAYMENT_CONFIRMED", at="2026-11-18 08:00:00"))

    assert late["status"] == "ignored" and late["error_code"] == "stale_event"
    assert Invoice.objects.get(pk=open_invoice.pk).status == Invoice.Status.DISPUTED
    assert lifecycle(organization).state == TenantLifecycle.State.GRACE
    attempt.refresh_from_db()
    assert attempt.status == PaymentAttempt.Status.CANCELLED


def test_refund_arriving_before_the_payment_it_refunds_still_ends_read_only(settings: Any) -> None:
    organization, _, open_invoice, _ = charged(**due(1))

    deliver(settings, event("e2", "PAYMENT_REFUNDED", at="2026-11-20 09:00:00"))
    stale = deliver(settings, event("e1", "PAYMENT_RECEIVED", at="2026-11-18 09:00:00"))

    assert stale["error_code"] == "stale_event"
    assert Invoice.objects.get(pk=open_invoice.pk).status == Invoice.Status.DISPUTED
    assert lifecycle(organization).state == TenantLifecycle.State.GRACE


def test_a_repeated_event_is_applied_once(settings: Any) -> None:
    _, _, _, _ = charged(**due(9, status=Invoice.Status.OVERDUE))

    first = deliver(settings, event("e1", "PAYMENT_RECEIVED"))
    second = deliver(settings, event("e1", "PAYMENT_RECEIVED"))

    assert first["status"] == "processed" and second["status"] == "duplicate"
    assert PaymentWebhookDelivery.objects.filter(event_id="e1").count() == 1
    assert AuditEvent.objects.filter(action="platform.billing.access_restored").count() == 0


def test_informational_events_do_not_move_the_event_clock(settings: Any) -> None:
    _, _, _, attempt = charged(**due(1))

    deliver(settings, event("e1", "PAYMENT_CREATED", at="2026-11-25 00:00:00"))
    deliver(settings, event("e2", "PAYMENT_RECEIVED", at="2026-11-20 09:00:00"))

    attempt.refresh_from_db()
    assert attempt.status == PaymentAttempt.Status.PAID
    assert attempt.last_event_at is not None and attempt.last_event_at.day == 20


def test_an_event_without_a_provider_timestamp_is_ordered_by_arrival(settings: Any) -> None:
    _, _, open_invoice, attempt = charged(**due(1))

    deliver(settings, event("e1", "PAYMENT_RECEIVED"))
    deliver(settings, event("e2", "PAYMENT_REFUNDED"))

    assert Invoice.objects.get(pk=open_invoice.pk).status == Invoice.Status.DISPUTED
    attempt.refresh_from_db()
    assert attempt.last_event_at is not None and attempt.last_event_at <= timezone.now()


def test_a_webhook_for_a_manual_contract_changes_the_invoice_but_not_access(settings: Any) -> None:
    organization = office(slug="manual-webhook")
    record = contract(organization, mode=TenantContract.BillingMode.MANUAL)
    open_invoice = invoice(record, **due(60, status=Invoice.Status.OVERDUE))
    PaymentAttempt.objects.create(
        invoice=open_invoice,
        provider=PaymentAttempt.Provider.ASAAS,
        method=PaymentAttempt.Method.PIX,
        idempotency_key="asaas:manual:1",
        external_id="pay_manual",
    )

    deliver(settings, event("e1", "PAYMENT_REFUNDED", "pay_manual"))

    assert Invoice.objects.get(pk=open_invoice.pk).status == Invoice.Status.DISPUTED
    assert lifecycle(organization).state == TenantLifecycle.State.ACTIVE
    record.refresh_from_db()
    assert record.status == TenantContract.Status.ACTIVE
