from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from django.db import close_old_connections, connection, connections
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Membership, Organization
from apps.platform.billing import BillingError, close_competence
from apps.platform.models import (
    InvoiceLine,
    Plan,
    TenantContract,
    TokenActionWeight,
    TokenMeter,
    TokenModuleRate,
    TokenPriceBook,
    TokenUsageEvent,
)
from apps.platform.token_billing import (
    activate_token_book,
    quote_tokens,
    reserve_tokens,
    settle_tokens,
)

pytestmark = pytest.mark.django_db
DAY = date(2026, 10, 15)


def _book() -> tuple[Organization, TokenPriceBook]:
    office = Organization.objects.create(name="Escritório token", slug="escritorio-token")
    plan = Plan.objects.create(code="token-qa", name="Token QA")
    contract = TenantContract.objects.create(
        organization=office, plan=plan, status=TenantContract.Status.ACTIVE
    )
    owner = User.objects.create_user("token-owner@example.test", "test-only-password")
    Membership.objects.create(
        organization=office, user=owner, role=Membership.Role.OWNER
    )
    book = TokenPriceBook.objects.create(
        contract=contract, version=1,
        token_price_cents=5, monthly_overage_cap_cents=30,
        effective_from=date(2026, 10, 1),
        accepted_by=owner, accepted_at=timezone.now(), activated_at=timezone.now(),
    )
    integra = TokenModuleRate.objects.create(
        book=book, module_code="integra", monthly_base_cents=1000, included_tokens=12
    )
    TokenActionWeight.objects.create(
        module_rate=integra, action_code="dte.list", tokens=8
    )
    triage = TokenModuleRate.objects.create(
        book=book, module_code="triage", monthly_base_cents=1000, included_tokens=5
    )
    TokenActionWeight.objects.create(
        module_rate=triage, action_code="triage.classify", tokens=4
    )
    book.status = TokenPriceBook.Status.ACTIVE
    book.save(update_fields=["status"])
    return office, book


def test_tokens_have_one_price_but_separate_module_allowances_and_weights() -> None:
    office, _book_record = _book()
    first = reserve_tokens(
        organization=office, module_code="integra", action_code="dte.list",
        idempotency_key="dte-1", on_date=DAY,
    )
    first_again = reserve_tokens(
        organization=office, module_code="integra", action_code="dte.list",
        idempotency_key="dte-1", on_date=DAY,
    )
    assert first.id == first_again.id
    integra_quote = quote_tokens(
        organization=office, module_code="integra", action_code="dte.list",
        on_date=DAY,
    )
    triage_quote = quote_tokens(
        organization=office, module_code="triage", action_code="triage.classify",
        on_date=DAY,
    )
    assert integra_quote.included_remaining == 4
    assert integra_quote.additional_overage_tokens == 4
    assert integra_quote.additional_overage_cents == 20
    assert triage_quote.included_remaining == 5
    assert triage_quote.additional_overage_cents == 0
    assert integra_quote.token_price_cents == triage_quote.token_price_cents == 5
    triage = reserve_tokens(
        organization=office, module_code="triage", action_code="triage.classify",
        idempotency_key="triage-1", on_date=DAY,
    )
    settle_tokens(event=first, provider_http_status=200, billable=True)
    settle_tokens(event=triage, provider_http_status=503, billable=False)
    first.refresh_from_db()
    triage.refresh_from_db()
    assert first.status == TokenUsageEvent.Status.SETTLED
    assert first.overage_cents == 0
    assert triage.status == TokenUsageEvent.Status.RELEASED
    assert TokenMeter.objects.get(organization=office, module_code="triage").consumed_tokens == 0


def test_automatic_overage_stops_before_accepted_global_cap() -> None:
    office, _book_record = _book()
    for number in (1, 2):
        reserve_tokens(
            organization=office, module_code="integra", action_code="dte.list",
            idempotency_key=f"dte-{number}", on_date=DAY,
        )
    quote = quote_tokens(
        organization=office, module_code="integra", action_code="dte.list",
        on_date=DAY,
    )
    assert quote.additional_overage_cents == 40
    with pytest.raises(BillingError, match="teto mensal"):
        reserve_tokens(
            organization=office, module_code="integra", action_code="dte.list",
            idempotency_key="dte-3", on_date=DAY,
        )
    assert TokenUsageEvent.objects.filter(organization=office).count() == 2


@pytest.mark.django_db(transaction=True)
def test_concurrent_token_reservations_share_one_idempotency_key() -> None:
    if connection.vendor != "postgresql":
        pytest.skip("A concorrência de locks é validada no PostgreSQL.")
    office, _book_record = _book()
    barrier = Barrier(4)

    def reserve_from_another_connection() -> str:
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            organization = Organization.objects.get(id=office.id)
            event = reserve_tokens(
                organization=organization,
                module_code="integra",
                action_code="dte.list",
                idempotency_key="concurrent-reserve",
                on_date=DAY,
            )
            return str(event.id)
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=4) as executor:
        event_ids = list(executor.map(lambda _: reserve_from_another_connection(), range(4)))

    assert len(set(event_ids)) == 1
    assert TokenUsageEvent.objects.filter(organization=office).count() == 1
    meter = TokenMeter.objects.get(organization=office, module_code="integra")
    assert meter.reserved_tokens == 8


def test_draft_token_book_cannot_activate_without_operational_switch() -> None:
    office = Organization.objects.create(name="Escritório draft", slug="escritorio-draft")
    plan = Plan.objects.create(code="token-draft", name="Token Draft")
    contract = TenantContract.objects.create(
        organization=office, plan=plan, status=TenantContract.Status.ACTIVE
    )
    owner = User.objects.create_user("token-draft@example.test", "test-only-password")
    Membership.objects.create(organization=office, user=owner, role=Membership.Role.OWNER)
    book = TokenPriceBook.objects.create(
        contract=contract, version=1, token_price_cents=5,
        monthly_overage_cap_cents=30,
    )
    rate = TokenModuleRate.objects.create(
        book=book, module_code="integra", monthly_base_cents=1000, included_tokens=12
    )
    TokenActionWeight.objects.create(module_rate=rate, action_code="dte.list", tokens=8)
    with pytest.raises(BillingError, match="migração operacional"):
        activate_token_book(book=book, accepted_by=owner, effective_from=date(2026, 10, 1))
    with override_settings(TOKEN_BILLING_ENABLED=True):
        activated = activate_token_book(
            book=book, accepted_by=owner, effective_from=date(2026, 10, 1)
        )
    assert activated.status == TokenPriceBook.Status.ACTIVE
    assert activated.accepted_by == owner


def test_token_competence_has_one_invoice_with_module_bases_and_overage() -> None:
    office, _book_record = _book()
    for number in (1, 2):
        event = reserve_tokens(
            organization=office, module_code="integra", action_code="dte.list",
            idempotency_key=f"invoice-dte-{number}", on_date=DAY,
        )
        settle_tokens(event=event, provider_http_status=200, billable=True)
    with override_settings(TOKEN_BILLING_ENABLED=True), patch(
        "apps.platform.billing.timezone.localdate", return_value=date(2026, 11, 1)
    ):
        first = close_competence(period_start=date(2026, 10, 1))
        second = close_competence(period_start=date(2026, 10, 1))
    invoice = first[0]
    invoice.refresh_from_db()
    assert second[0].id == invoice.id
    assert invoice.organization_id == office.id
    assert invoice.base_amount_cents == 2000
    assert invoice.overage_amount_cents == 20
    assert invoice.total_amount_cents == 2020
    assert list(invoice.lines.filter(kind=InvoiceLine.Kind.SUBSCRIPTION).values_list(
        "action_code", "total_amount_cents"
    )) == [("integra", 1000), ("triage", 1000)]
    assert list(invoice.lines.filter(kind=InvoiceLine.Kind.OVERAGE).values_list(
        "action_code", "quantity", "total_amount_cents"
    )) == [("integra", 4, 20)]
    assert invoice.lines.count() == 3


def test_accepted_token_terms_require_a_new_version_to_change() -> None:
    _office, book = _book()
    book.token_price_cents = 6
    with pytest.raises(ValidationError, match="congelados"):
        book.save(update_fields=["token_price_cents"])
    book.refresh_from_db()
    rate = TokenModuleRate.objects.get(book=book, module_code="integra")
    rate.included_tokens = 99
    with pytest.raises(ValidationError, match="congeladas"):
        rate.save(update_fields=["included_tokens"])
    weight = TokenActionWeight.objects.get(module_rate=rate, action_code="dte.list")
    weight.tokens = 1
    with pytest.raises(ValidationError, match="congelado"):
        weight.save(update_fields=["tokens"])
    stale_rate = TokenModuleRate.objects.get(id=rate.id)
    stale_rate.book.status = TokenPriceBook.Status.DRAFT
    stale_rate.monthly_base_cents = 1
    with pytest.raises(ValidationError, match="congeladas"):
        stale_rate.save(update_fields=["monthly_base_cents"])


def test_token_invoice_waits_for_reservations_and_refuses_late_use() -> None:
    office, _book_record = _book()
    event = reserve_tokens(
        organization=office, module_code="integra", action_code="dte.list",
        idempotency_key="token-pending-close", on_date=DAY,
    )
    with override_settings(TOKEN_BILLING_ENABLED=True), patch(
        "apps.platform.billing.timezone.localdate", return_value=date(2026, 11, 1)
    ):
        with pytest.raises(BillingError, match="operações reservadas"):
            close_competence(period_start=date(2026, 10, 1))
        settle_tokens(event=event, provider_http_status=200, billable=True)
        close_competence(period_start=date(2026, 10, 1))
    with pytest.raises(BillingError, match="já foi faturada"):
        quote_tokens(
            organization=office, module_code="integra", action_code="dte.list",
            on_date=DAY,
        )
    with pytest.raises(BillingError, match="já foi faturada"):
        reserve_tokens(
            organization=office, module_code="integra", action_code="dte.list",
            idempotency_key="token-late-close", on_date=DAY,
        )
    assert reserve_tokens(
        organization=office, module_code="integra", action_code="dte.list",
        idempotency_key="token-pending-close", on_date=DAY,
    ).id == event.id
