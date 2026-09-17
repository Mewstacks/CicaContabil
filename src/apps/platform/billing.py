"""Central, auditable metering for CICA's shared Integra contract."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.organizations.models import Organization
from apps.platform.models import (
    BillingCloseDeferral,
    Invoice,
    InvoiceLine,
    PlanServiceRate,
    TenantContract,
    TenantServiceRate,
    TenantUsagePolicy,
    TokenMeter,
    TokenModuleRate,
    TokenPriceBook,
    TokenUsageEvent,
    UsageEvent,
    UsageMeter,
)


class BillingError(ValueError):
    """The central contract does not allow the requested API use."""


class UsageLimitReached(BillingError):
    """The office chose to stop at its included allowance or spending cap."""


class UsageApprovalRequired(BillingError):
    """An owner must approve this projected overage before dispatching it."""


@dataclass(frozen=True)
class UsageProjection:
    included_remaining: int
    projected_overage_units: int
    projected_overage_cents: int


@dataclass(frozen=True)
class UsageQuote:
    included_remaining: int
    additional_overage_units: int
    additional_overage_cents: int
    overage_unit_price_cents: int


def month_bounds(value: date) -> tuple[date, date]:
    start = value.replace(day=1)
    next_month = (start + timedelta(days=32)).replace(day=1)
    return start, next_month - timedelta(days=1)


def active_contract(organization: Organization) -> TenantContract:
    contract = (
        TenantContract.objects.filter(
            organization=organization,
            status__in=[
                TenantContract.Status.TRIAL,
                TenantContract.Status.ACTIVE,
            ],
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )
    if contract is None or contract.plan is None:
        raise BillingError("Este escritório não tem um contrato vigente para consumir o serviço.")
    return contract


def snapshot_contract_pricing(contract: TenantContract, *, initialize_price: bool = False) -> None:
    """Freeze the reusable plan's commercial terms in one office contract."""

    if contract.plan is None:
        return
    # A console-approved R$ 0,00 is a real price. Only an unlocked new
    # contract may inherit the plan default; metering and invoice retries never
    # reprice an agreement.
    if initialize_price and not contract.monthly_price_locked:
        contract.monthly_price_cents = contract.plan.monthly_price_cents
        contract.monthly_price_locked = True
        contract.save(
            update_fields=["monthly_price_cents", "monthly_price_locked", "updated_at"]
        )
    for rate in PlanServiceRate.objects.filter(plan=contract.plan):
        TenantServiceRate.objects.get_or_create(
            contract=contract,
            action_code=rate.action_code,
            defaults={
                "included_units": rate.included_units,
                "overage_unit_price_cents": rate.overage_unit_price_cents,
            },
        )


def _rate(contract: TenantContract, action_code: str) -> TenantServiceRate:
    snapshot_contract_pricing(contract)
    rate = TenantServiceRate.objects.filter(contract=contract, action_code=action_code).first()
    if rate is not None:
        return rate
    assert contract.plan is not None
    raise BillingError("Este serviço Integra não está incluído no contrato do escritório.")


def _meter(
    *, organization: Organization, action_code: str, on_date: date
) -> tuple[UsageMeter, TenantServiceRate]:
    contract = active_contract(organization)
    rate = _rate(contract, action_code)
    start, end = month_bounds(on_date)
    try:
        # A savepoint leaves the outer reservation transaction usable when two
        # workers create the same monthly meter concurrently.
        with transaction.atomic():
            meter, _ = UsageMeter.objects.get_or_create(
                organization=organization,
                action_code=action_code,
                period_start=start,
                defaults={
                    "period_end": end,
                    "included_units": rate.included_units,
                    "overage_unit_price_cents": rate.overage_unit_price_cents,
                },
            )
    except IntegrityError:
        meter = UsageMeter.objects.get(
            organization=organization, action_code=action_code, period_start=start
        )
    return meter, rate


def usage_projection(meter: UsageMeter, *, units: int = 1) -> UsageProjection:
    projected = meter.consumed_units + meter.reserved_units + units
    overage = max(0, projected - meter.included_units)
    return UsageProjection(
        included_remaining=max(
            0,
            meter.included_units - meter.consumed_units - meter.reserved_units,
        ),
        projected_overage_units=overage,
        projected_overage_cents=overage * meter.overage_unit_price_cents,
    )


def quote_usage(*, organization: Organization, action_code: str, units: int = 1) -> UsageQuote:
    """Quote this request; reservation still checks the live meter atomically."""

    if units < 1:
        raise BillingError("Uma consulta precisa incluir ao menos uma unidade.")
    with transaction.atomic():
        Organization.objects.select_for_update().get(id=organization.id)
        start, _end = month_bounds(timezone.localdate())
        if Invoice.objects.filter(organization=organization, period_start=start).exists():
            raise BillingError("A competência já foi faturada; não prepare outro consumo.")
        meter, _rate_record = _meter(
            organization=organization, action_code=action_code, on_date=timezone.localdate()
        )
        meter = UsageMeter.objects.select_for_update().get(id=meter.id)
        before = usage_projection(meter, units=0)
        after = usage_projection(meter, units=units)
        return UsageQuote(
            included_remaining=before.included_remaining,
            additional_overage_units=(
                after.projected_overage_units - before.projected_overage_units
            ),
            additional_overage_cents=(
                after.projected_overage_cents - before.projected_overage_cents
            ),
            overage_unit_price_cents=meter.overage_unit_price_cents,
        )


def reserve_usage(
    *,
    organization: Organization,
    action_code: str,
    idempotency_key: str,
    units: int = 1,
    approved_overage: bool = False,
    approved_overage_cents: int | None = None,
    require_explicit_overage: bool = False,
) -> UsageEvent:
    """Reserve a billable central call before it leaves the application."""

    if units < 1:
        raise BillingError("Uma chamada precisa consumir ao menos uma unidade.")
    if getattr(settings, "TOKEN_BILLING_ENABLED", False) and TokenPriceBook.objects.filter(
        contract__organization=organization,
        status=TokenPriceBook.Status.ACTIVE,
        effective_from__lte=timezone.localdate(),
    ).exists():
        raise BillingError(
            "Esta competência usa tokens. Migre a operação antes de enviar uma chamada externa."
        )
    with transaction.atomic():
        Organization.objects.select_for_update().get(id=organization.id)
        existing = UsageEvent.objects.filter(idempotency_key=idempotency_key).first()
        if existing is not None:
            if existing.organization_id != organization.id or existing.action_code != action_code:
                raise BillingError("A chave de idempotência já pertence a outro consumo.")
            return existing
        start, _end = month_bounds(timezone.localdate())
        if Invoice.objects.filter(organization=organization, period_start=start).exists():
            raise BillingError("A competência já foi faturada; não reserve outro consumo.")
        meter, _rate_record = _meter(
            organization=organization, action_code=action_code, on_date=timezone.localdate()
        )
        meter = UsageMeter.objects.select_for_update().get(id=meter.id)
        projection = usage_projection(meter, units=units)
        policy = TenantUsagePolicy.objects.filter(
            organization=organization, action_code=action_code
        ).first()
        crosses_allowance = projection.projected_overage_units > meter.overage_units
        additional_overage_cents = (
            projection.projected_overage_cents
            - usage_projection(meter, units=0).projected_overage_cents
        )
        if crosses_allowance and require_explicit_overage and (
            not approved_overage
            or approved_overage_cents is None
            or approved_overage_cents < additional_overage_cents
        ):
            raise UsageApprovalRequired(
                "O excedente mudou ou ainda não foi autorizado com o valor exato. "
                "Revise a consulta antes de enviar."
            )
        if policy is not None:
            if (
                policy.monthly_overage_cap_cents
                and projection.projected_overage_cents > policy.monthly_overage_cap_cents
            ):
                raise UsageLimitReached("O teto mensal de excedente deste escritório foi atingido.")
            if crosses_allowance and policy.overage_mode == TenantUsagePolicy.OverageMode.BLOCK:
                raise UsageLimitReached(
                    "A franquia deste serviço foi atingida para esta competência."
                )
            if (
                crosses_allowance
                and policy.overage_mode == TenantUsagePolicy.OverageMode.REQUIRE_APPROVAL
                and not approved_overage
            ):
                raise UsageApprovalRequired(
                    "O excedente precisa da aprovação de um owner ou administrador."
                )
        elif crosses_allowance:
            raise UsageLimitReached("A franquia deste serviço foi atingida para esta competência.")
        event = UsageEvent.objects.create(
            meter=meter,
            organization=organization,
            action_code=action_code,
            idempotency_key=idempotency_key,
            units=units,
        )
        meter.reserved_units += units
        meter.save(update_fields=["reserved_units", "updated_at"])
        return event


def settle_usage(
    *, event: UsageEvent, provider_http_status: int, provider_request_id: str = "", billable: bool
) -> UsageEvent:
    """Settle a reservation only after knowing whether Serpro billed the request."""

    with transaction.atomic():
        Organization.objects.select_for_update().get(id=event.organization_id)
        event = UsageEvent.objects.select_for_update().select_related("meter").get(id=event.id)
        if event.status != UsageEvent.Status.RESERVED:
            return event
        meter = UsageMeter.objects.select_for_update().get(id=event.meter_id)
        meter.reserved_units -= event.units
        if billable:
            previous_overage = meter.overage_units
            meter.consumed_units += event.units
            meter.overage_units = max(0, meter.consumed_units - meter.included_units)
            new_overage = meter.overage_units - previous_overage
            event.overage_cents = new_overage * meter.overage_unit_price_cents
            event.status = UsageEvent.Status.SETTLED
        else:
            event.status = UsageEvent.Status.RELEASED
        meter.save(
            update_fields=["reserved_units", "consumed_units", "overage_units", "updated_at"]
        )
        event.provider_http_status = provider_http_status
        event.provider_request_id = provider_request_id[:160]
        event.save(
            update_fields=[
                "status",
                "overage_cents",
                "provider_http_status",
                "provider_request_id",
                "updated_at",
            ]
        )
        return event


def close_competence(
    *, period_start: date, deferred_organization_ids: list[str] | None = None
) -> list[Invoice]:
    """Generate exactly one immutable-open invoice per active office and month."""

    start, end = month_bounds(period_start)
    if start >= timezone.localdate().replace(day=1):
        raise BillingError("A competência ainda não terminou; aguarde o mês completo.")
    invoices: list[Invoice] = []
    contracts = (
        TenantContract.objects.filter(
            status__in=[TenantContract.Status.ACTIVE, TenantContract.Status.GRACE]
        )
        .select_related("organization", "plan")
        .order_by("organization_id", "-created_at")
    )
    seen_organizations: set[object] = set()
    for contract in contracts:
        if contract.organization_id in seen_organizations or contract.plan is None:
            continue
        seen_organizations.add(contract.organization_id)
        with transaction.atomic():
            Organization.objects.select_for_update().get(id=contract.organization_id)
            if (
                UsageEvent.objects.filter(
                    organization=contract.organization,
                    meter__period_start=start,
                    status=UsageEvent.Status.RESERVED,
                ).exists()
                or TokenUsageEvent.objects.filter(
                    organization=contract.organization,
                    meter__period_start=start,
                    status=TokenUsageEvent.Status.RESERVED,
                ).exists()
                or UsageMeter.objects.filter(
                    organization=contract.organization, period_start=start,
                    reserved_units__gt=0,
                ).exists()
                or TokenMeter.objects.filter(
                    organization=contract.organization, period_start=start,
                    reserved_tokens__gt=0,
                ).exists()
            ):
                if deferred_organization_ids is not None:
                    BillingCloseDeferral.objects.update_or_create(
                        organization=contract.organization,
                        period_start=start,
                        defaults={
                            "reason": "reserved_usage",
                            "last_seen_at": timezone.now(),
                            "resolved_at": None,
                        },
                    )
                    deferred_organization_ids.append(str(contract.organization_id))
                    continue
                raise BillingError(
                    "Há operações reservadas nesta competência. "
                    "Conclua ou libere todas antes de gerar a fatura."
                )
            snapshot_contract_pricing(contract)
            token_book = None
            if getattr(settings, "TOKEN_BILLING_ENABLED", False):
                token_book = TokenPriceBook.objects.filter(
                    contract=contract,
                    status__in=[
                        TokenPriceBook.Status.ACTIVE, TokenPriceBook.Status.RETIRED
                    ],
                    effective_from__lte=start,
                ).order_by("-effective_from", "-version").first()
            if token_book is None and TokenMeter.objects.filter(
                organization=contract.organization, period_start=start
            ).exists():
                raise BillingError(
                    "Há consumo por tokens nesta competência sem tabela ativa. "
                    "Reconcilie antes de fechar a fatura."
                )
            if token_book is not None and UsageMeter.objects.filter(
                organization=contract.organization, period_start=start
            ).exists():
                raise BillingError(
                    "Há consumo legado e consumo por tokens na mesma competência. "
                    "Reconcilie antes de fechar a fatura."
                )
            base_amount = (
                sum(
                    rate.monthly_base_cents or 0
                    for rate in TokenModuleRate.objects.filter(book=token_book)
                )
                if token_book is not None
                else contract.monthly_price_cents
            )
            invoice, created = Invoice.objects.get_or_create(
                organization=contract.organization,
                period_start=start,
                defaults={
                    "contract": contract,
                    "period_end": end,
                    "due_on": (end + timedelta(days=10)),
                    "base_amount_cents": base_amount,
                    "total_amount_cents": base_amount,
                },
            )
            if not created:
                BillingCloseDeferral.objects.filter(
                    organization=contract.organization, period_start=start,
                    resolved_at__isnull=True,
                ).update(resolved_at=timezone.now())
                invoices.append(invoice)
                continue
            if token_book is None:
                InvoiceLine.objects.create(
                    invoice=invoice,
                    kind=InvoiceLine.Kind.SUBSCRIPTION,
                    description=f"Mensalidade {contract.plan.name}",
                    unit_amount_cents=contract.monthly_price_cents,
                    total_amount_cents=contract.monthly_price_cents,
                )
            else:
                for rate in TokenModuleRate.objects.filter(book=token_book).order_by(
                    "module_code"
                ):
                    InvoiceLine.objects.create(
                        invoice=invoice,
                        kind=InvoiceLine.Kind.SUBSCRIPTION,
                        action_code=rate.module_code,
                        description=f"Mensalidade {rate.module_code}",
                        unit_amount_cents=rate.monthly_base_cents or 0,
                        total_amount_cents=rate.monthly_base_cents or 0,
                    )
                overage_total = 0
                for meter in TokenMeter.objects.filter(
                    organization=contract.organization, period_start=start
                ).order_by("module_code"):
                    if meter.book_id != token_book.id:
                        raise BillingError("O medidor de tokens não pertence ao preço do período.")
                    if not meter.overage_tokens:
                        continue
                    amount = meter.overage_tokens * meter.token_price_cents
                    overage_total += amount
                    InvoiceLine.objects.create(
                        invoice=invoice,
                        kind=InvoiceLine.Kind.OVERAGE,
                        action_code=meter.module_code,
                        description=f"Tokens excedentes {meter.module_code}",
                        quantity=meter.overage_tokens,
                        unit_amount_cents=meter.token_price_cents,
                        total_amount_cents=amount,
                    )
                invoice.overage_amount_cents = overage_total
                invoice.total_amount_cents = invoice.base_amount_cents + overage_total
                invoice.save(update_fields=[
                    "overage_amount_cents", "total_amount_cents", "updated_at"
                ])
                BillingCloseDeferral.objects.filter(
                    organization=contract.organization, period_start=start,
                    resolved_at__isnull=True,
                ).update(resolved_at=timezone.now())
                invoices.append(invoice)
                continue
            meters = UsageMeter.objects.filter(
                organization=contract.organization, period_start=start
            ).order_by("action_code")
            overage_total = 0
            for meter in meters:
                if not meter.overage_units:
                    continue
                amount = meter.overage_units * meter.overage_unit_price_cents
                overage_total += amount
                InvoiceLine.objects.create(
                    invoice=invoice,
                    kind=InvoiceLine.Kind.OVERAGE,
                    action_code=meter.action_code,
                    description=f"Excedente {meter.action_code}",
                    quantity=meter.overage_units,
                    unit_amount_cents=meter.overage_unit_price_cents,
                    total_amount_cents=amount,
                )
            invoice.overage_amount_cents = overage_total
            invoice.total_amount_cents = invoice.base_amount_cents + overage_total
            invoice.save(update_fields=["overage_amount_cents", "total_amount_cents", "updated_at"])
            BillingCloseDeferral.objects.filter(
                organization=contract.organization, period_start=start,
                resolved_at__isnull=True,
            ).update(resolved_at=timezone.now())
            invoices.append(invoice)
    return invoices
