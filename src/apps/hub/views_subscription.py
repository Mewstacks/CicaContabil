"""Assinatura do escritório (E3): plano, limites, faturas e pagamento.

Visível a quem cuida do contrato (dono, administrador, financeiro). Contrato que a Mewstack opera
à mão (`billing_mode = manual`, o que existe hoje) só mostra o estado e as faturas; pagar por aqui
e escolher plano só existem para contrato de autoatendimento convertido (D-79, D-307).
"""

from __future__ import annotations

import uuid
from typing import Any
from urllib.parse import urlparse

from django.contrib import messages
from django.http import HttpRequest, HttpResponseRedirect
from django.http.response import HttpResponseBase
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.hub.views import office_required, refuse, workspace_context
from apps.organizations.models import Membership, Organization
from apps.platform import collection, dunning, subscription
from apps.platform import limits as plan_limits
from apps.platform.models import Invoice, PaymentAttempt, Plan, TenantContract, TenantLifecycle

BILLING_ROLES = {Membership.Role.OWNER, Membership.Role.ADMIN, Membership.Role.BILLING}
INVOICE_ROWS = 12
METHOD_LABELS = (
    (PaymentAttempt.Method.PIX.value, "Pix"),
    (PaymentAttempt.Method.BOLETO.value, "Boleto"),
    (PaymentAttempt.Method.CARD.value, "Cartão"),
)
CONTRACT_LABELS = {
    TenantContract.Status.TRIAL: "Teste",
    TenantContract.Status.ACTIVE: "Ativo",
    TenantContract.Status.GRACE: "Pagamento pendente",
    TenantContract.Status.SUSPENDED: "Suspenso",
}
STATUS_TONES = {
    Invoice.Status.OPEN: "is-muted",
    Invoice.Status.PAID: "is-active",
    Invoice.Status.OVERDUE: "is-danger",
    Invoice.Status.VOID: "is-muted",
    Invoice.Status.DISPUTED: "is-danger",
}


def _brl(cents: int) -> str:
    whole, fraction = divmod(abs(cents), 100)
    return f"R$ {whole:,}".replace(",", ".") + f",{fraction:02d}"


def safe_checkout_url(url: str) -> str:
    """Only the provider's own HTTPS pages: the URL comes from an API response."""

    parts = urlparse(url)
    host = (parts.hostname or "").lower()
    if parts.scheme == "https" and (host == "asaas.com" or host.endswith(".asaas.com")):
        return url
    return ""


def _contract(organization: Organization) -> TenantContract | None:
    return (
        TenantContract.objects.filter(organization=organization)
        .exclude(status__in=[TenantContract.Status.DRAFT, TenantContract.Status.ARCHIVED])
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )


@office_required
@require_http_methods(["GET", "POST"])
def subscription_page(request: HttpRequest) -> HttpResponseBase:
    context = workspace_context(request)
    office = context["office"]
    assert isinstance(office, Organization)
    membership = context["membership"]
    allowed = (
        isinstance(membership, Membership)
        and context["support_session"] is None
        and membership.role in BILLING_ROLES
    )
    if not allowed:
        return refuse(request, "A assinatura é restrita a dono, administrador e financeiro.")
    contract = _contract(office)
    automatic = (
        contract is not None and contract.billing_mode == TenantContract.BillingMode.AUTOMATIC
    )

    if request.method == "POST":
        action = request.POST.get("action", "")
        if action == "convert":
            plan = Plan.objects.filter(code=request.POST.get("plan", "")).first()
            try:
                if plan is None:
                    raise subscription.SubscriptionError("Este plano não está disponível.")
                subscription.convert_to_plan(
                    organization=office, plan=plan, actor=request.user, request=request
                )
            except subscription.SubscriptionError as exc:
                messages.error(request, str(exc))
            else:
                messages.success(request, f"Plano {plan.name} contratado.")
            return redirect("hub:subscription")
        if action == "pay":
            invoice = (
                Invoice.objects.filter(
                    organization=office, pk=request.POST.get("invoice", "")
                ).first()
                if _is_uuid(request.POST.get("invoice", ""))
                else None
            )
            try:
                if invoice is None:
                    raise collection.CollectionError("Fatura não encontrada.")
                attempt = collection.request_payment(
                    invoice=invoice,
                    method=request.POST.get("method", ""),
                    actor=request.user,
                    request=request,
                )
            except collection.CollectionError as exc:
                messages.error(request, str(exc))
                return redirect("hub:subscription")
            target = safe_checkout_url(attempt.checkout_url)
            if target:
                return HttpResponseRedirect(target)
            messages.warning(request, "Cobrança criada. O link de pagamento ainda não chegou.")
            return redirect("hub:subscription")
        return redirect("hub:subscription")

    lifecycle = TenantLifecycle.objects.filter(organization=office).first()
    read_only = bool(lifecycle is not None and lifecycle.state == TenantLifecycle.State.GRACE)
    invoices = list(
        Invoice.objects.filter(organization=office)
        .prefetch_related("payment_attempts")
        .order_by("-period_start")[:INVOICE_ROWS]
    )
    can_collect = automatic and collection.enabled()
    rows: list[dict[str, Any]] = []
    for invoice in invoices:
        open_invoice = invoice.status in {Invoice.Status.OPEN, Invoice.Status.OVERDUE}
        link = next(
            (
                safe_checkout_url(attempt.checkout_url)
                for attempt in invoice.payment_attempts.all()
                if attempt.status == PaymentAttempt.Status.PENDING and attempt.checkout_url
            ),
            "",
        )
        rows.append(
            {
                "invoice": invoice,
                "total": _brl(invoice.total_amount_cents),
                "tone": STATUS_TONES[Invoice.Status(invoice.status)],
                "can_pay": can_collect and open_invoice and invoice.total_amount_cents > 0,
                "checkout_url": link,
            }
        )
    context.update(
        {
            "page_title": "Assinatura",
            "contract": contract,
            "contract_label": CONTRACT_LABELS.get(TenantContract.Status(contract.status), "")
            if contract
            else "",
            "plan_name": contract.plan.name if contract and contract.plan else "",
            "price": _brl(contract.monthly_price_cents) if contract else "",
            "automatic": automatic,
            "read_only": read_only,
            "access_reason": lifecycle.reason if read_only and lifecycle else "",
            "carencia_days": dunning.GRACE_DAYS,
            "limit_states": plan_limits.states(office),
            "rows": rows,
            "methods": METHOD_LABELS,
            "plans": [
                {"plan": plan, "price": _brl(plan.monthly_price_cents)}
                for plan in subscription.selectable_plans()
            ]
            if subscription.convertible_contract(office) is not None
            else [],
            "trial_ends_on": contract.trial_ends_on if contract else None,
            "today": timezone.localdate(),
        }
    )
    return render(request, "hub/subscription.html", context)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True
