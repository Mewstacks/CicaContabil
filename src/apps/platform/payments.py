"""Internal billing ledger transitions.

The CICA does not collect from accounting offices. The Mewstack team charges
outside the product and records the resulting invoice state in its console.
"""

from __future__ import annotations

from django.db import transaction

from apps.platform.models import Invoice


class ManualBillingError(ValueError):
    """The requested internal ledger transition is invalid."""


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
