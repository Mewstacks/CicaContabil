"""Draft-ready, contract-snapshotted token metering by module.

No production caller uses this ledger until commercial terms are accepted and
the existing per-service billing has been migrated. No prices are hardcoded.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.organizations.models import Organization
from apps.platform.billing import BillingError, active_contract, month_bounds
from apps.platform.models import (
    Invoice,
    TokenActionWeight,
    TokenMeter,
    TokenModuleRate,
    TokenPriceBook,
    TokenUsageEvent,
    UsageMeter,
)


@dataclass(frozen=True)
class TokenQuote:
    module_code: str
    action_code: str
    operations: int
    tokens_per_operation: int
    total_tokens: int
    included_remaining: int
    additional_overage_tokens: int
    additional_overage_cents: int
    monthly_cap_remaining_cents: int
    token_price_cents: int


def _active_book(organization: Organization, on_date: date) -> TokenPriceBook:
    contract = active_contract(organization)
    book = (
        TokenPriceBook.objects.filter(
            contract=contract,
            status=TokenPriceBook.Status.ACTIVE,
            effective_from__lte=on_date,
        )
        .select_related("contract")
        .first()
    )
    if book is None or not book.token_price_cents or book.monthly_overage_cap_cents is None:
        raise BillingError("Este escritório ainda não tem uma tabela de tokens aceita e ativa.")
    if book.accepted_by_id is None or book.accepted_at is None:
        raise BillingError("O escritório ainda não aceitou o preço e o teto de tokens.")
    return book


def _rate_weight(
    book: TokenPriceBook, module_code: str, action_code: str
) -> tuple[TokenModuleRate, TokenActionWeight]:
    rate = TokenModuleRate.objects.filter(book=book, module_code=module_code).first()
    if rate is None or rate.included_tokens is None or rate.monthly_base_cents is None:
        raise BillingError("Este módulo não tem mensalidade e franquia de tokens definidas.")
    weight = TokenActionWeight.objects.filter(
        module_rate=rate, action_code=action_code
    ).first()
    if weight is None or not weight.tokens:
        raise BillingError("Esta operação não tem peso de tokens definido no contrato.")
    return rate, weight


def _meter(
    organization: Organization, book: TokenPriceBook, rate: TokenModuleRate, on_date: date
) -> TokenMeter:
    start, end = month_bounds(on_date)
    try:
        with transaction.atomic():
            meter, _created = TokenMeter.objects.get_or_create(
                organization=organization,
                module_code=rate.module_code,
                period_start=start,
                defaults={
                    "contract": book.contract,
                    "book": book,
                    "period_end": end,
                    "included_tokens": rate.included_tokens,
                    "token_price_cents": book.token_price_cents,
                },
            )
    except IntegrityError:
        meter = TokenMeter.objects.get(
            organization=organization, module_code=rate.module_code, period_start=start
        )
    if meter.book_id != book.id:
        raise BillingError(
            "A tabela de tokens mudou nesta competência. Mantenha o preço contratado "
            "até o próximo mês."
        )
    return meter


def _projected_overage_tokens(meter: TokenMeter, additional: int = 0) -> int:
    return max(
        0,
        meter.consumed_tokens + meter.reserved_tokens + additional - meter.included_tokens,
    )


def _global_projected_overage_cents(
    organization: Organization, on_date: date, current: TokenMeter, additional: int
) -> int:
    start, _end = month_bounds(on_date)
    total = 0
    for meter in TokenMeter.objects.filter(organization=organization, period_start=start):
        total += _projected_overage_tokens(
            meter, additional if meter.id == current.id else 0
        ) * meter.token_price_cents
    return total


def _quote_locked(
    organization: Organization, module_code: str, action_code: str,
    operations: int, on_date: date,
) -> tuple[TokenQuote, TokenMeter]:
    if operations < 1:
        raise BillingError("Selecione ao menos uma operação para cotar tokens.")
    book = _active_book(organization, on_date)
    rate, weight = _rate_weight(book, module_code, action_code)
    assert weight.tokens is not None and book.token_price_cents is not None
    total_tokens = operations * weight.tokens
    meter = _meter(organization, book, rate, on_date)
    before = _projected_overage_tokens(meter)
    after = _projected_overage_tokens(meter, total_tokens)
    global_after = _global_projected_overage_cents(
        organization, on_date, meter, total_tokens
    )
    assert book.monthly_overage_cap_cents is not None
    cap_remaining = max(0, book.monthly_overage_cap_cents - global_after)
    return TokenQuote(
        module_code=module_code,
        action_code=action_code,
        operations=operations,
        tokens_per_operation=weight.tokens,
        total_tokens=total_tokens,
        included_remaining=max(
            0, meter.included_tokens - meter.consumed_tokens - meter.reserved_tokens
        ),
        additional_overage_tokens=after - before,
        additional_overage_cents=(after - before) * meter.token_price_cents,
        monthly_cap_remaining_cents=cap_remaining,
        token_price_cents=meter.token_price_cents,
    ), meter


def quote_tokens(
    *, organization: Organization, module_code: str, action_code: str,
    operations: int = 1, on_date: date | None = None,
) -> TokenQuote:
    day = on_date or timezone.localdate()
    with transaction.atomic():
        Organization.objects.select_for_update().get(id=organization.id)
        start, _end = month_bounds(day)
        if Invoice.objects.filter(organization=organization, period_start=start).exists():
            raise BillingError("A competência já foi faturada; não prepare outro consumo.")
        quote, _meter_record = _quote_locked(
            organization, module_code, action_code, operations, day
        )
        return quote


def reserve_tokens(
    *, organization: Organization, module_code: str, action_code: str,
    idempotency_key: str, on_date: date | None = None,
) -> TokenUsageEvent:
    """Reserve one weighted action; automatic overage stops at the accepted office cap."""

    day = on_date or timezone.localdate()
    with transaction.atomic():
        Organization.objects.select_for_update().get(id=organization.id)
        existing = TokenUsageEvent.objects.filter(idempotency_key=idempotency_key).first()
        if existing is not None:
            if (
                existing.organization_id != organization.id
                or existing.module_code != module_code
                or existing.action_code != action_code
            ):
                raise BillingError("A chave de idempotência pertence a outro consumo.")
            return existing
        start, _end = month_bounds(day)
        if Invoice.objects.filter(organization=organization, period_start=start).exists():
            raise BillingError("A competência já foi faturada; não reserve outro consumo.")
        quote, meter = _quote_locked(organization, module_code, action_code, 1, day)
        book = TokenPriceBook.objects.get(id=meter.book_id)
        assert book.monthly_overage_cap_cents is not None
        global_after = _global_projected_overage_cents(
            organization, day, meter, quote.total_tokens
        )
        if global_after > book.monthly_overage_cap_cents:
            raise BillingError("O teto mensal aceito de tokens deste escritório foi atingido.")
        event = TokenUsageEvent.objects.create(
            meter=meter,
            organization=organization,
            module_code=module_code,
            action_code=action_code,
            idempotency_key=idempotency_key,
            tokens=quote.total_tokens,
            token_price_cents=quote.token_price_cents,
        )
        meter.reserved_tokens += quote.total_tokens
        meter.save(update_fields=["reserved_tokens", "updated_at"])
        return event


def settle_tokens(
    *, event: TokenUsageEvent, provider_http_status: int,
    provider_request_id: str = "", billable: bool,
) -> TokenUsageEvent:
    with transaction.atomic():
        Organization.objects.select_for_update().get(id=event.organization_id)
        event = TokenUsageEvent.objects.select_for_update().get(id=event.id)
        if event.status != TokenUsageEvent.Status.RESERVED:
            return event
        meter = TokenMeter.objects.select_for_update().get(id=event.meter_id)
        meter.reserved_tokens -= event.tokens
        if billable:
            before = max(0, meter.consumed_tokens - meter.included_tokens)
            meter.consumed_tokens += event.tokens
            meter.overage_tokens = max(0, meter.consumed_tokens - meter.included_tokens)
            event.overage_cents = (
                meter.overage_tokens - before
            ) * event.token_price_cents
            event.status = TokenUsageEvent.Status.SETTLED
        else:
            event.status = TokenUsageEvent.Status.RELEASED
        meter.save(update_fields=[
            "reserved_tokens", "consumed_tokens", "overage_tokens", "updated_at"
        ])
        event.provider_http_status = provider_http_status
        event.provider_request_id = provider_request_id[:160]
        event.save(update_fields=[
            "status", "overage_cents", "provider_http_status",
            "provider_request_id", "updated_at",
        ])
        return event


def activate_token_book(
    *, book: TokenPriceBook, accepted_by: object, effective_from: date,
) -> TokenPriceBook:
    """Activate accepted terms only for a future clean competence."""

    with transaction.atomic():
        if not getattr(settings, "TOKEN_BILLING_ENABLED", False):
            raise BillingError("A migração operacional para tokens ainda não foi liberada.")
        book = TokenPriceBook.objects.select_for_update().select_related("contract").get(
            id=book.id
        )
        if book.status != TokenPriceBook.Status.DRAFT:
            raise BillingError("Esta tabela de tokens não é mais um rascunho.")
        if not book.token_price_cents or book.monthly_overage_cap_cents is None:
            raise BillingError("Defina o valor do token e o teto mensal aceito.")
        if effective_from <= timezone.localdate().replace(day=1):
            raise BillingError("A tabela de tokens deve começar em uma competência futura.")
        if effective_from.day != 1:
            raise BillingError("A tabela de tokens deve começar no primeiro dia do mês.")
        if not getattr(accepted_by, "is_authenticated", False):
            raise BillingError("Um usuário do escritório precisa aceitar o preço e o teto.")
        if not accepted_by.organization_memberships.filter(
            organization=book.contract.organization,
            role__in=["owner", "admin"],
            is_active=True,
        ).exists():
            raise BillingError("Somente dono ou administrador pode aceitar o preço e o teto.")
        rates = list(TokenModuleRate.objects.filter(book=book))
        if not rates or any(
            rate.monthly_base_cents is None or rate.monthly_base_cents < 1
            or rate.included_tokens is None or rate.included_tokens < 1
            for rate in rates
        ):
            raise BillingError("Defina mensalidade e franquia positiva para cada módulo.")
        for rate in rates:
            if not TokenActionWeight.objects.filter(
                module_rate=rate, tokens__gt=0
            ).exists():
                raise BillingError("Cada módulo precisa de operações com pesos inteiros.")
        if UsageMeter.objects.filter(
            organization=book.contract.organization,
            period_start=effective_from,
        ).exists():
            raise BillingError("Há consumo legado na competência de início; migre antes de ativar.")
        if TokenPriceBook.objects.filter(
            contract=book.contract, status=TokenPriceBook.Status.ACTIVE
        ).exists():
            raise BillingError("Encerre a tabela ativa antes de ativar outra versão.")
        book.status = TokenPriceBook.Status.ACTIVE
        book.effective_from = effective_from
        book.activated_at = timezone.now()
        book.accepted_by = accepted_by
        book.accepted_at = timezone.now()
        book.save(update_fields=[
            "status", "effective_from", "activated_at", "accepted_by", "accepted_at",
            "updated_at",
        ])
        return book
