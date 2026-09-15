"""Internal billing ledger transitions.

The CICA does not collect from accounting offices. The Mewstack team charges
outside the product and records the resulting invoice state in its console.
"""

from __future__ import annotations

from dataclasses import dataclass

from django.db import transaction

from apps.platform.models import Invoice, PaymentAttempt, PaymentWebhookDelivery


class ManualBillingError(ValueError):
    """The requested internal ledger transition is invalid."""


class AsaasWebhookPayloadError(ValueError):
    """The authenticated notification does not contain a usable payment event."""


@dataclass(frozen=True)
class AsaasWebhookOutcome:
    duplicate: bool
    processing_status: str
    error_code: str = ""


_ASAAS_METHODS = {
    "PIX": PaymentAttempt.Method.PIX,
    "BOLETO": PaymentAttempt.Method.BOLETO,
    "CREDIT_CARD": PaymentAttempt.Method.CARD,
}
_ASAAS_PAID_EVENTS = frozenset({"PAYMENT_RECEIVED"})
_ASAAS_FAILED_EVENTS = frozenset({"PAYMENT_DELETED", "PAYMENT_CREDIT_CARD_CAPTURE_REFUSED"})
_ASAAS_DISPUTE_EVENTS = frozenset(
    {
        "PAYMENT_REFUNDED",
        "PAYMENT_PARTIALLY_REFUNDED",
        "PAYMENT_RECEIVED_IN_CASH_UNDONE",
        "PAYMENT_CHARGEBACK_REQUESTED",
        "PAYMENT_CHARGEBACK_DISPUTE",
        "PAYMENT_AWAITING_CHARGEBACK_REVERSAL",
    }
)


def _payload_string(payload: object, key: str, *, limit: int) -> str:
    if not isinstance(payload, dict) or not isinstance(payload.get(key), str):
        raise AsaasWebhookPayloadError("Evento Asaas sem identificador válido.")
    value = payload[key].strip()
    if not value or len(value) > limit:
        raise AsaasWebhookPayloadError("Evento Asaas com identificador inválido.")
    return value


def process_asaas_webhook(*, payload: object) -> AsaasWebhookOutcome:
    """Apply one authenticated Asaas event once, without changing contract access.

    The event id is the provider's idempotency boundary. Contract grace and suspension
    are deliberately not inferred here: those rules require the approved commercial policy.
    """

    event_id = _payload_string(payload, "id", limit=160)
    event_name = _payload_string(payload, "event", limit=80)
    payment = payload.get("payment") if isinstance(payload, dict) else None
    external_id = _payload_string(payment, "id", limit=160)
    billing_type = (
        str(payment.get("billingType") or "").strip() if isinstance(payment, dict) else ""
    )

    with transaction.atomic():
        delivery, created = PaymentWebhookDelivery.objects.get_or_create(
            provider=PaymentAttempt.Provider.ASAAS,
            event_id=event_id,
            defaults={"event_name": event_name, "external_id": external_id},
        )
        if not created:
            return AsaasWebhookOutcome(duplicate=True, processing_status=delivery.processing_status)

        attempt = (
            PaymentAttempt.objects.select_for_update()
            .select_related("invoice")
            .filter(provider=PaymentAttempt.Provider.ASAAS, external_id=external_id)
            .first()
        )
        if attempt is None:
            delivery.processing_status = PaymentWebhookDelivery.ProcessingStatus.IGNORED
            delivery.error_code = "payment_not_found"
            delivery.save(update_fields=["processing_status", "error_code", "updated_at"])
            return AsaasWebhookOutcome(False, delivery.processing_status, delivery.error_code)

        delivery.payment_attempt = attempt
        observed_method = _ASAAS_METHODS.get(billing_type)
        if observed_method is not None and observed_method != attempt.method:
            delivery.processing_status = PaymentWebhookDelivery.ProcessingStatus.FAILED
            delivery.error_code = "payment_method_mismatch"
            delivery.save(
                update_fields=["payment_attempt", "processing_status", "error_code", "updated_at"]
            )
            return AsaasWebhookOutcome(False, delivery.processing_status, delivery.error_code)

        invoice = attempt.invoice
        if event_name in _ASAAS_PAID_EVENTS:
            if invoice.status != Invoice.Status.VOID:
                attempt.status = PaymentAttempt.Status.PAID
                invoice.status = Invoice.Status.PAID
                attempt.save(update_fields=["status", "updated_at"])
                invoice.save(update_fields=["status", "updated_at"])
        elif event_name == "PAYMENT_OVERDUE":
            if invoice.status in {Invoice.Status.OPEN, Invoice.Status.OVERDUE}:
                invoice.status = Invoice.Status.OVERDUE
                invoice.save(update_fields=["status", "updated_at"])
        elif event_name in _ASAAS_FAILED_EVENTS:
            if attempt.status != PaymentAttempt.Status.PAID:
                attempt.status = PaymentAttempt.Status.FAILED
                attempt.save(update_fields=["status", "updated_at"])
        elif event_name in _ASAAS_DISPUTE_EVENTS:
            attempt.status = PaymentAttempt.Status.CANCELLED
            invoice.status = Invoice.Status.DISPUTED
            attempt.save(update_fields=["status", "updated_at"])
            invoice.save(update_fields=["status", "updated_at"])

        delivery.save(update_fields=["payment_attempt", "updated_at"])
        return AsaasWebhookOutcome(False, delivery.processing_status)


def set_manual_invoice_status(*, invoice: Invoice, status: str) -> Invoice:
    """Record an off-platform collection outcome without contacting a provider."""

    if status not in Invoice.Status.values:
        raise ManualBillingError("Selecione um status válido para a cobrança interna.")
    with transaction.atomic():
        locked = Invoice.objects.select_for_update().get(id=invoice.id)
        if locked.status == status:
            return locked
        locked.status = status
        locked.save(update_fields=["status", "updated_at"])
        return locked
