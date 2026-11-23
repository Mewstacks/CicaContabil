"""Acesso conforme o pagamento (E3, D-79): carência de 7 dias, somente leitura, reativação.

D-79, aprovado em 18/09/2026: após atraso confirmado há 7 dias de carência; depois, somente
leitura; pagamento confirmado reativa sozinho; estorno ou disputa volta a somente leitura.
Somente leitura mantém consulta, documentos arquivados, auditoria e exportação dos próprios dados
e bloqueia sincronização nova, IA, download em lote novo, Serpro e consumo (a barreira por
operação já existe: `office_required` recusa escrita em carência, `active_contract` recusa consumo).

O acesso é função do ESTADO das faturas, não da ordem dos eventos do provedor: o Asaas não
garante ordem de entrega (docs.asaas.com, lido em 20/11/2026). Reaplicar a regra a qualquer
momento dá o mesmo resultado, então evento repetido, atrasado ou fora de ordem não regride nada.

Só toca contrato com `billing_mode = automatic` cujo ciclo de vida está ativo ou em carência. Todo
contrato de hoje é manual, e suspenso/arquivado/em provisionamento nunca é mexido aqui.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from django.utils import timezone

from apps.audit.services import record_event
from apps.organizations.models import Organization
from apps.platform.models import Invoice, TenantContract, TenantLifecycle

GRACE_DAYS = 7
FULL = "full"
READ_ONLY = "read_only"
OVERDUE = "overdue"
DISPUTE = "dispute"
REASONS = {
    OVERDUE: "Pagamento em atraso há mais de 7 dias. Pague a fatura para voltar a operar.",
    DISPUTE: "Pagamento estornado ou contestado. Fale com o suporte para regularizar.",
}


def automatic_contract(organization: Organization) -> TenantContract | None:
    return (
        TenantContract.objects.filter(
            organization=organization,
            billing_mode=TenantContract.BillingMode.AUTOMATIC,
            status__in=[TenantContract.Status.ACTIVE, TenantContract.Status.GRACE],
        )
        .order_by("-created_at")
        .first()
    )


def desired_access(organization: Organization, *, today: date | None = None) -> tuple[str, str]:
    """(`full`|`read_only`, motivo). Disputa pesa mais que atraso."""

    today = today or timezone.localdate()
    invoices = Invoice.objects.filter(
        organization=organization,
        status__in=[Invoice.Status.OPEN, Invoice.Status.OVERDUE, Invoice.Status.DISPUTED],
    ).only("status", "due_on")
    reason = ""
    for invoice in invoices:
        if invoice.status == Invoice.Status.DISPUTED:
            return READ_ONLY, DISPUTE
        if invoice.due_on + timedelta(days=GRACE_DAYS) < today:
            reason = OVERDUE
    return (READ_ONLY, reason) if reason else (FULL, "")


def sync_access(
    organization: Organization, *, today: date | None = None, request: Any = None
) -> str | None:
    """Apply D-79 to one office. Returns the new mode when it changed, else `None`."""

    contract = automatic_contract(organization)
    if contract is None:
        return None
    lifecycle = TenantLifecycle.objects.filter(organization=organization).first()
    if lifecycle is None or lifecycle.state not in {
        TenantLifecycle.State.ACTIVE,
        TenantLifecycle.State.GRACE,
    }:
        return None
    mode, reason = desired_access(organization, today=today)
    today = today or timezone.localdate()
    if mode == READ_ONLY and contract.status == TenantContract.Status.ACTIVE:
        contract.status = TenantContract.Status.GRACE
        contract.grace_ends_on = today
        contract.save(update_fields=["status", "grace_ends_on", "updated_at"])
        lifecycle.state = TenantLifecycle.State.GRACE
        lifecycle.reason = REASONS[reason]
        lifecycle.save(update_fields=["state", "reason", "updated_at"])
        record_event(
            action="platform.billing.access_read_only",
            organization=organization,
            target=contract,
            request=request,
            metadata={"reason": reason},
        )
        return READ_ONLY
    if mode == FULL and contract.status == TenantContract.Status.GRACE:
        contract.status = TenantContract.Status.ACTIVE
        contract.grace_ends_on = None
        contract.save(update_fields=["status", "grace_ends_on", "updated_at"])
        lifecycle.state = TenantLifecycle.State.ACTIVE
        lifecycle.reason = "Pagamento confirmado."
        lifecycle.save(update_fields=["state", "reason", "updated_at"])
        record_event(
            action="platform.billing.access_restored",
            organization=organization,
            target=contract,
            request=request,
            metadata={"reason": "payment_confirmed"},
        )
        return FULL
    return None


def enforce_all(*, today: date | None = None) -> dict[str, int]:
    """Daily sweep: the 7-day carência ends on a date, with or without a provider event."""

    today = today or timezone.localdate()
    offices = Organization.objects.filter(
        contracts__billing_mode=TenantContract.BillingMode.AUTOMATIC,
        contracts__status__in=[TenantContract.Status.ACTIVE, TenantContract.Status.GRACE],
        is_active=True,
    ).distinct()
    outcome = {"read_only": 0, "restored": 0, "unchanged": 0}
    for organization in offices.iterator():
        changed = sync_access(organization, today=today)
        if changed == READ_ONLY:
            outcome["read_only"] += 1
        elif changed == FULL:
            outcome["restored"] += 1
        else:
            outcome["unchanged"] += 1
    return outcome
