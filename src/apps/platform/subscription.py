"""Assinatura (E3): do teste gratuito ao plano pago, só para quem fez o cadastro sozinho.

Só converte contrato de autoatendimento (`reference` = `self-service:*`) que ainda está em teste
ou terminou o teste. Contrato manual, aquele que a Mewstack opera hoje, nunca converte por clique:
`billing_mode` continua `manual` e a automação de cobrança e de acesso não o enxerga.

Depois de converter, vale D-79: competência fecha no dia 1, vencimento no dia 10, primeiro mês
proporcional (`billing.prorate_first_month`), 7 dias de carência após o atraso e somente leitura
depois. Mudança de plano depois da conversão fica com a Mewstack e vale no ciclo seguinte.

Nenhum plano nem preço nasce aqui: sem `Plan` ativo e com valor, a lista de planos fica vazia e
ninguém converte. Os valores são os que o responsável aprovar (D-307).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.organizations.models import Organization
from apps.platform.models import Entitlement, Plan, TenantContract, TenantLifecycle
from apps.platform.signup import TRIAL_PLAN_CODE


class SubscriptionError(ValueError):
    """The conversion is not allowed; the message is safe to show to the office."""


def selectable_plans() -> list[Plan]:
    return list(
        Plan.objects.filter(is_active=True, monthly_price_cents__gt=0)
        .exclude(code=TRIAL_PLAN_CODE)
        .order_by("monthly_price_cents", "code")
    )


def convertible_contract(organization: Organization) -> TenantContract | None:
    """The self-service contract that may still be converted, or `None`."""

    contract = (
        TenantContract.objects.filter(
            organization=organization,
            status__in=[TenantContract.Status.TRIAL, TenantContract.Status.GRACE],
            billing_mode=TenantContract.BillingMode.MANUAL,
            reference__startswith="self-service:",
        )
        .order_by("-created_at")
        .first()
    )
    return contract


def convert_to_plan(
    *,
    organization: Organization,
    plan: Plan,
    actor: Any = None,
    request: Any = None,
    today: date | None = None,
) -> TenantContract:
    if not plan.is_active or plan.monthly_price_cents <= 0 or plan.code == TRIAL_PLAN_CODE:
        raise SubscriptionError("Este plano não está disponível.")
    today = today or timezone.localdate()
    with transaction.atomic():
        contract = (
            TenantContract.objects.select_for_update()
            .filter(
                organization=organization,
                status__in=[TenantContract.Status.TRIAL, TenantContract.Status.GRACE],
                billing_mode=TenantContract.BillingMode.MANUAL,
                reference__startswith="self-service:",
            )
            .order_by("-created_at")
            .first()
        )
        if contract is None:
            raise SubscriptionError(
                "Este escritório não pode trocar de plano por aqui. Fale com a Mewstack."
            )
        lifecycle = (
            TenantLifecycle.objects.select_for_update().filter(organization=organization).first()
        )
        if lifecycle is None or lifecycle.state not in {
            TenantLifecycle.State.ACTIVE,
            TenantLifecycle.State.GRACE,
        }:
            raise SubscriptionError("O escritório não está em um estado que permita contratar.")
        modules = list(plan.modules) or list(contract.selected_modules)
        contract.plan = plan
        contract.monthly_price_cents = plan.monthly_price_cents
        contract.monthly_price_locked = True
        contract.billing_mode = TenantContract.BillingMode.AUTOMATIC
        contract.status = TenantContract.Status.ACTIVE
        contract.starts_on = today
        contract.grace_ends_on = None
        contract.selected_modules = modules
        contract.save(
            update_fields=[
                "plan",
                "monthly_price_cents",
                "monthly_price_locked",
                "billing_mode",
                "status",
                "starts_on",
                "grace_ends_on",
                "selected_modules",
                "updated_at",
            ]
        )
        # The trial entitlements end with the trial; a paid plan does not.
        Entitlement.objects.filter(organization=organization, code__in=modules).update(
            valid_until=None
        )
        lifecycle.state = TenantLifecycle.State.ACTIVE
        lifecycle.reason = "Plano contratado."
        lifecycle.save(update_fields=["state", "reason", "updated_at"])
    record_event(
        action="platform.billing.plan_converted",
        actor=actor,
        organization=organization,
        target=contract,
        request=request,
        metadata={"plan": plan.code, "starts_on": today.isoformat()},
    )
    return contract
