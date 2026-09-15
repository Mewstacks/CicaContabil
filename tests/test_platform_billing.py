from __future__ import annotations

from datetime import date

import pytest

from apps.organizations.models import Organization
from apps.platform.billing import (
    BillingError,
    UsageApprovalRequired,
    UsageLimitReached,
    close_competence,
    reserve_usage,
    settle_usage,
)
from apps.platform.models import (
    Invoice,
    Plan,
    PlanServiceRate,
    TenantContract,
    TenantUsagePolicy,
    UsageEvent,
    UsageMeter,
)

pytestmark = pytest.mark.django_db


def _contract() -> tuple[Organization, Plan]:
    organization = Organization.objects.create(name="Escritório Cobrança", slug="cobranca")
    plan = Plan.objects.create(code="central", name="Central", monthly_price_cents=19_900)
    TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    PlanServiceRate.objects.create(
        plan=plan,
        action_code="caixapostal.mensagens",
        included_units=2,
        overage_unit_price_cents=175,
    )
    return organization, plan


def test_new_unlocked_contract_inherits_the_catalogue_price_once() -> None:
    organization = Organization.objects.create(name="Preço", slug="preco")
    plan = Plan.objects.create(code="inherit-price", name="Herda", monthly_price_cents=9_900)

    contract = TenantContract.objects.create(organization=organization, plan=plan)

    contract.refresh_from_db()
    assert contract.monthly_price_cents == 9_900
    assert contract.monthly_price_locked is True


def test_usage_is_reserved_then_only_billed_when_the_provider_settles() -> None:
    organization, _plan = _contract()
    TenantUsagePolicy.objects.create(
        organization=organization,
        action_code="caixapostal.mensagens",
        overage_mode=TenantUsagePolicy.OverageMode.ALLOW,
        monthly_overage_cap_cents=1_000,
    )

    first = reserve_usage(
        organization=organization, action_code="caixapostal.mensagens", idempotency_key="one"
    )
    same = reserve_usage(
        organization=organization, action_code="caixapostal.mensagens", idempotency_key="one"
    )
    assert first.id == same.id
    settle_usage(event=first, provider_http_status=200, billable=True)
    second = reserve_usage(
        organization=organization, action_code="caixapostal.mensagens", idempotency_key="two"
    )
    settle_usage(event=second, provider_http_status=200, billable=True)
    third = reserve_usage(
        organization=organization, action_code="caixapostal.mensagens", idempotency_key="three"
    )
    settle_usage(event=third, provider_http_status=200, billable=True)

    meter = UsageMeter.objects.get(organization=organization, action_code="caixapostal.mensagens")
    assert meter.reserved_units == 0
    assert meter.consumed_units == 3
    assert meter.overage_units == 1
    assert UsageEvent.objects.get(id=third.id).overage_cents == 175


def test_office_can_block_or_require_approval_for_an_overage() -> None:
    organization, plan = _contract()
    PlanServiceRate.objects.filter(plan=plan).update(included_units=0)
    TenantUsagePolicy.objects.create(
        organization=organization,
        action_code="caixapostal.mensagens",
        overage_mode=TenantUsagePolicy.OverageMode.BLOCK,
    )
    with pytest.raises(UsageLimitReached):
        reserve_usage(
            organization=organization,
            action_code="caixapostal.mensagens",
            idempotency_key="blocked",
        )

    TenantUsagePolicy.objects.filter(organization=organization).update(
        overage_mode=TenantUsagePolicy.OverageMode.REQUIRE_APPROVAL
    )
    with pytest.raises(UsageApprovalRequired):
        reserve_usage(
            organization=organization,
            action_code="caixapostal.mensagens",
            idempotency_key="approval",
        )
    approved = reserve_usage(
        organization=organization,
        action_code="caixapostal.mensagens",
        idempotency_key="approval-by-owner",
        approved_overage=True,
    )
    assert approved.status == UsageEvent.Status.RESERVED


def test_closing_a_competence_creates_one_combined_monthly_invoice() -> None:
    organization, plan = _contract()
    period_start = date(2026, 8, 1)
    UsageMeter.objects.create(
        organization=organization,
        action_code="caixapostal.mensagens",
        period_start=period_start,
        period_end=date(2026, 8, 31),
        included_units=2,
        overage_unit_price_cents=175,
        consumed_units=5,
        overage_units=3,
    )

    invoices = close_competence(period_start=period_start)
    repeat = close_competence(period_start=period_start)

    assert len(invoices) == len(repeat) == 1
    invoice = Invoice.objects.get(organization=organization, period_start=period_start)
    assert invoice.base_amount_cents == plan.monthly_price_cents
    assert invoice.overage_amount_cents == 525
    assert invoice.total_amount_cents == 20_425
    assert invoice.due_on == date(2026, 9, 10)
    assert invoice.lines.count() == 2


def test_contract_price_is_frozen_when_the_plan_changes() -> None:
    _organization, plan = _contract()
    plan.monthly_price_cents = 99_900
    plan.save(update_fields=["monthly_price_cents"])

    invoice = close_competence(period_start=date(2026, 8, 1))[0]

    assert invoice.base_amount_cents == 19_900


def test_usage_requires_a_contract_rate_and_releases_non_billable_calls() -> None:
    organization = Organization.objects.create(name="Sem contrato", slug="sem-contrato")
    with pytest.raises(BillingError):
        reserve_usage(
            organization=organization,
            action_code="caixapostal.mensagens",
            idempotency_key="no-contract",
        )
    plan = Plan.objects.create(code="sem-taxas", name="Sem taxas")
    TenantContract.objects.create(
        organization=organization, plan=plan, status=TenantContract.Status.ACTIVE
    )
    with pytest.raises(BillingError):
        reserve_usage(
            organization=organization,
            action_code="caixapostal.mensagens",
            idempotency_key="no-rate",
        )
    PlanServiceRate.objects.create(
        plan=plan,
        action_code="caixapostal.mensagens",
        included_units=1,
        overage_unit_price_cents=100,
    )
    event = reserve_usage(
        organization=organization,
        action_code="caixapostal.mensagens",
        idempotency_key="released",
    )
    released = settle_usage(event=event, provider_http_status=503, billable=False)
    assert released.status == UsageEvent.Status.RELEASED
    assert settle_usage(event=event, provider_http_status=503, billable=False).id == event.id
