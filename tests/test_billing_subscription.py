"""Assinatura (E3): conversão do teste em plano, proporcional do primeiro mês e a página."""

from __future__ import annotations

import calendar
from datetime import date, timedelta
from typing import Any

import pytest
from django.test import Client
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.models import AuditEvent
from apps.hub.models import ClientCompany, OfficeProfile
from apps.organizations.models import Membership, Organization
from apps.platform import collection, subscription
from apps.platform.billing import close_competence, prorate_first_month
from apps.platform.models import (
    Entitlement,
    Invoice,
    InvoiceLine,
    PaymentAttempt,
    Plan,
    TenantContract,
    TenantLifecycle,
)
from apps.platform.signup import TRIAL_PLAN_CODE
from apps.platform.subscription import SubscriptionError, convert_to_plan, selectable_plans
from billing_support import FakeAsaas, contract, invoice, office, owner, plan
from test_nfse_procuracao_views import login

pytestmark = pytest.mark.django_db


def trial_office(slug: str = "teste-grat", *, ended: bool = False):
    organization = office(slug=slug)
    user = owner(organization, f"dono.{slug}@example.test")
    today = timezone.localdate()
    record = contract(
        organization,
        mode=TenantContract.BillingMode.MANUAL,
        status=TenantContract.Status.GRACE if ended else TenantContract.Status.TRIAL,
        price=0,
        starts_on=today - timedelta(days=14 if ended else 3),
        reference="self-service:abc",
        lifecycle=TenantLifecycle.State.GRACE if ended else TenantLifecycle.State.ACTIVE,
    )
    Entitlement.objects.create(
        organization=organization, code="nfse", enabled=True, valid_until=today + timedelta(days=11)
    )
    return organization, user, record


# ---------------------------------------------------------------- planos à venda


def test_only_active_priced_plans_are_offered_and_never_the_trial_plan() -> None:
    plan("b", price=49900, name="B")
    plan("a", price=19900, name="A")
    plan("rascunho", price=9900, is_active=False)
    plan("gratis", price=0)
    plan(TRIAL_PLAN_CODE, price=100)

    assert [item.code for item in selectable_plans()] == ["a", "b"]


def test_without_plans_nothing_can_be_converted() -> None:
    organization, _, _ = trial_office()

    assert selectable_plans() == []
    with pytest.raises(SubscriptionError, match="não está disponível"):
        convert_to_plan(organization=organization, plan=plan("zerado", price=0))


# ---------------------------------------------------------------- conversão


def test_a_trial_converts_into_an_automatic_active_contract_at_the_plan_price() -> None:
    organization, user, record = trial_office()
    chosen = plan("b", price=49900, limits={"companies": 120})
    today = timezone.localdate()

    converted = convert_to_plan(organization=organization, plan=chosen, actor=user, today=today)

    assert converted.pk == record.pk
    record.refresh_from_db()
    assert record.status == TenantContract.Status.ACTIVE
    assert record.billing_mode == TenantContract.BillingMode.AUTOMATIC
    assert record.plan_id == chosen.pk and record.monthly_price_cents == 49900
    assert record.monthly_price_locked and record.starts_on == today
    assert record.selected_modules == ["nfse"]
    assert TenantLifecycle.objects.get(organization=organization).state == "active"
    assert Entitlement.objects.get(organization=organization).valid_until is None
    event = AuditEvent.objects.get(action="platform.billing.plan_converted")
    assert event.metadata == {"plan": "b", "starts_on": today.isoformat()}


def test_an_office_whose_trial_already_ended_converts_and_gets_access_back() -> None:
    organization, user, record = trial_office("terminou", ended=True)

    convert_to_plan(organization=organization, plan=plan("b"), actor=user)

    record.refresh_from_db()
    assert record.status == TenantContract.Status.ACTIVE and record.grace_ends_on is None
    assert TenantLifecycle.objects.get(organization=organization).state == "active"


def test_a_manual_contract_never_converts_by_click() -> None:
    organization = office(slug="bianchi")
    record = contract(organization, mode=TenantContract.BillingMode.MANUAL, reference="")

    with pytest.raises(SubscriptionError, match="Fale com a Mewstack"):
        convert_to_plan(organization=organization, plan=plan("b"))

    record.refresh_from_db()
    assert record.billing_mode == "manual" and record.status == "active"
    assert subscription.convertible_contract(organization) is None


def test_an_already_converted_office_cannot_convert_again() -> None:
    organization, _, _ = trial_office()
    convert_to_plan(organization=organization, plan=plan("b"))

    with pytest.raises(SubscriptionError, match="Fale com a Mewstack"):
        convert_to_plan(organization=organization, plan=plan("c", price=99900))


@pytest.mark.parametrize("state", ["suspended", "archived", "provisioning"])
def test_a_suspended_or_archived_office_cannot_buy_its_way_back(state: str) -> None:
    organization, _, record = trial_office()
    TenantLifecycle.objects.filter(organization=organization).update(state=state)

    with pytest.raises(SubscriptionError, match="estado"):
        convert_to_plan(organization=organization, plan=plan("b"))

    record.refresh_from_db()
    assert record.billing_mode == "manual"


# ---------------------------------------------------------------- proporcional (D-79)


@pytest.mark.parametrize(("starts", "days_in_force"), [(1, 30), (11, 20), (16, 15), (30, 1)])
def test_the_first_month_is_proportional_to_the_days_in_force(
    starts: int, days_in_force: int
) -> None:
    start, end = date(2026, 11, 1), date(2026, 11, 30)

    assert prorate_first_month(49900, start, end, date(2026, 11, starts)) == round(
        49900 * days_in_force / 30
    )


def last_month() -> tuple[date, date]:
    first_of_this_month = timezone.localdate().replace(day=1)
    end = first_of_this_month - timedelta(days=1)
    return end.replace(day=1), end


def test_closing_the_month_charges_an_automatic_contract_pro_rata() -> None:
    start, end = last_month()
    organization = office(slug="proporcional")
    record = contract(
        organization,
        starts_on=start.replace(day=11),
        lifecycle=TenantLifecycle.State.ACTIVE,
    )

    [closed] = [inv for inv in close_competence(period_start=start) if inv.contract_id == record.pk]

    in_force = (end - start.replace(day=11)).days + 1
    expected = round(49900 * in_force / calendar.monthrange(start.year, start.month)[1])
    assert closed.base_amount_cents == closed.total_amount_cents == expected
    [line] = InvoiceLine.objects.filter(invoice=closed)
    assert line.total_amount_cents == expected and line.unit_amount_cents == 49900
    assert line.description.endswith("(proporcional)")


def test_a_manual_contract_is_charged_in_full_exactly_as_before() -> None:
    start, _ = last_month()
    organization = office(slug="integral")
    record = contract(
        organization, mode=TenantContract.BillingMode.MANUAL, starts_on=start.replace(day=11)
    )

    [closed] = [inv for inv in close_competence(period_start=start) if inv.contract_id == record.pk]

    assert closed.base_amount_cents == 49900
    [line] = InvoiceLine.objects.filter(invoice=closed)
    assert line.total_amount_cents == 49900 and not line.description.endswith("(proporcional)")


def test_an_automatic_contract_that_started_before_the_month_pays_the_full_month() -> None:
    start, _ = last_month()
    organization = office(slug="cheio")
    record = contract(organization, starts_on=start - timedelta(days=40))

    [closed] = [inv for inv in close_competence(period_start=start) if inv.contract_id == record.pk]

    assert closed.base_amount_cents == 49900


# ---------------------------------------------------------------- a página


def test_the_checkout_url_must_be_an_https_asaas_page() -> None:
    from apps.hub.views_subscription import safe_checkout_url

    assert safe_checkout_url("https://www.asaas.com/i/abc") == "https://www.asaas.com/i/abc"
    assert safe_checkout_url("https://sandbox.asaas.com/i/abc")
    for bad in (
        "http://www.asaas.com/i/abc",
        "https://asaas.com.evil.example/i/abc",
        "https://evil.example/asaas.com",
        "javascript:alert(1)",
        "//evil.example",
        "",
    ):
        assert safe_checkout_url(bad) == "", bad


def page(client: Client) -> Any:
    return client.get(reverse("hub:subscription"))


def test_a_manual_contract_shows_state_and_invoices_but_offers_no_payment() -> None:
    organization = office(slug="so-leitura")
    user = owner(organization)
    record = contract(organization, mode=TenantContract.BillingMode.MANUAL)
    invoice(record)

    html = page(login(user, organization)).content.decode()

    assert "Mewstack" in html and "Faturas" in html
    assert 'name="action" value="pay"' not in html and "Contratar" not in html


def test_an_automatic_contract_with_an_open_invoice_offers_the_three_methods(settings: Any) -> None:
    settings.BILLING_COLLECTION_ENABLED = True
    settings.ASAAS_API_KEY = "chave"
    organization = office(slug="paga-aqui")
    user = owner(organization)
    invoice(contract(organization))

    html = page(login(user, organization)).content.decode()

    assert 'name="action" value="pay"' in html
    for label in ("Pix", "Boleto", "Cartão"):
        assert f">{label}<" in html


def test_without_collection_enabled_there_is_nothing_to_click(settings: Any) -> None:
    organization = office(slug="desligada")
    user = owner(organization)
    invoice(contract(organization))

    html = page(login(user, organization)).content.decode()

    assert 'name="action" value="pay"' not in html and "Automática" in html


def test_paying_redirects_to_the_provider_page_and_creates_one_attempt(
    settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.BILLING_COLLECTION_ENABLED = True
    settings.ASAAS_API_KEY = "chave"
    fake = FakeAsaas()
    monkeypatch.setattr(collection, "build_client", fake.client)
    organization = office(slug="redireciona")
    user = owner(organization)
    open_invoice = invoice(contract(organization))
    client = login(user, organization)

    response = client.post(
        reverse("hub:subscription"),
        {"action": "pay", "invoice": str(open_invoice.pk), "method": "pix"},
    )

    assert response.status_code == 302
    assert response["Location"] == "https://sandbox.asaas.com/i/pay_1"
    assert PaymentAttempt.objects.filter(invoice=open_invoice).count() == 1
    again = client.get(reverse("hub:subscription")).content.decode()
    assert "Abrir cobrança" in again and 'name="method"' not in again  # o link substitui os botões


def test_a_refused_charge_comes_back_to_the_page_with_the_reason(settings: Any) -> None:
    organization = office(slug="recusada")
    user = owner(organization)
    open_invoice = invoice(contract(organization))

    response = login(user, organization).post(
        reverse("hub:subscription"),
        {"action": "pay", "invoice": str(open_invoice.pk), "method": "pix"},
        follow=True,
    )

    assert any("desligada" in str(m) for m in response.context["messages"])
    assert not PaymentAttempt.objects.exists()


def test_another_offices_invoice_cannot_be_charged() -> None:
    mine = office(slug="minha")
    user = owner(mine)
    contract(mine)
    theirs = office(slug="alheia")
    owner(theirs, "outro@example.test")
    foreign = invoice(contract(theirs))

    response = login(user, mine).post(
        reverse("hub:subscription"),
        {"action": "pay", "invoice": str(foreign.pk), "method": "pix"},
        follow=True,
    )

    assert any("não encontrada" in str(m) for m in response.context["messages"])


def test_a_read_only_office_sees_why_and_where_to_go(settings: Any) -> None:
    settings.BILLING_COLLECTION_ENABLED = True
    settings.ASAAS_API_KEY = "chave"
    organization = office(slug="somente-leitura")
    user = owner(organization)
    TenantLifecycle.objects.create(
        organization=organization, state="grace", reason="Pagamento em atraso há mais de 7 dias."
    )
    record = contract(organization, lifecycle=None)
    invoice(record, status=Invoice.Status.OVERDUE)

    html = page(login(user, organization)).content.decode()

    assert "Somente leitura" in html and "atraso há mais de 7 dias" in html
    assert 'href="#faturas"' in html


def test_the_limits_show_their_use_with_a_word_and_not_only_a_color() -> None:
    organization = office(slug="limites")
    user = owner(organization)
    record = contract(organization)
    Plan.objects.filter(pk=record.plan_id).update(limits={"companies": 5, "users": 1})
    for index in range(5):
        from apps.hub.models import ClientCompany

        ClientCompany.objects.create(organization=organization, name=f"E{index}")

    html = page(login(user, organization)).content.decode()

    assert "5 de 5" in html and "Limite" in html and 'role="progressbar"' in html
    assert "1 de 1" in html


def test_the_plans_appear_only_to_a_convertible_contract_and_the_click_converts() -> None:
    organization, user, record = trial_office("vitrine")
    plan("b", price=49900, name="Plano B")
    client = login(user, organization)

    html = page(client).content.decode()
    assert "Plano B" in html and "R$ 499,00/mês" in html and "Contratar" in html

    response = client.post(
        reverse("hub:subscription"), {"action": "convert", "plan": "b"}, follow=True
    )

    assert any("Plano Plano B contratado" in str(m) for m in response.context["messages"])
    record.refresh_from_db()
    assert record.billing_mode == "automatic"
    assert "Contratar" not in page(client).content.decode()


def test_only_the_contract_roles_open_the_page() -> None:
    organization = office(slug="papeis")
    contract(organization)
    for role, expected in (
        (Membership.Role.OWNER, 200),
        (Membership.Role.ADMIN, 200),
        (Membership.Role.BILLING, 200),
        (Membership.Role.MANAGER, 403),
        (Membership.Role.OPERATOR, 403),
        (Membership.Role.AUDITOR, 403),
    ):
        user = User.objects.create_user(email=f"{role}@example.test", password="uma-senha-longa")
        Membership.objects.create(organization=organization, user=user, role=role)

        assert page(login(user, organization)).status_code == expected, role


def test_the_navigation_offers_the_page_to_new_offices_only() -> None:
    new_org = office(slug="nova")
    new_user = owner(new_org)
    contract(new_org)
    legacy = Organization.objects.create(name="Legado", slug="legado-nav")
    OfficeProfile.objects.create(organization=legacy)
    legacy_user = owner(legacy, "dono.legado@example.test")
    contract(legacy, mode=TenantContract.BillingMode.MANUAL)

    new_html = login(new_user, new_org).get(reverse("hub:setup")).content.decode()
    legacy_html = login(legacy_user, legacy).get(reverse("hub:setup")).content.decode()

    assert reverse("hub:subscription") in new_html
    assert reverse("hub:subscription") not in legacy_html


# ---------------------------------------------------------------- saída da somente leitura (D-79)


def test_an_office_whose_trial_ended_can_subscribe_through_the_page_while_read_only() -> None:
    """Em carência o `office_required` recusa todo POST; a saída da carência tem de ser exceção."""

    organization, user, record = trial_office("terminou-na-tela", ended=True)
    assert TenantLifecycle.objects.get(organization=organization).state == "grace"
    plan("b", price=49900, name="Plano B")
    client = login(user, organization)

    response = client.post(reverse("hub:subscription"), {"action": "convert", "plan": "b"})

    assert response.status_code == 302  # e não 403
    record.refresh_from_db()
    assert record.status == TenantContract.Status.ACTIVE
    assert record.billing_mode == TenantContract.BillingMode.AUTOMATIC
    assert TenantLifecycle.objects.get(organization=organization).state == "active"


def test_an_overdue_office_can_still_open_a_charge_to_pay_while_read_only(
    settings: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    settings.BILLING_COLLECTION_ENABLED = True
    settings.ASAAS_API_KEY = "chave"
    fake = FakeAsaas()
    monkeypatch.setattr(collection, "build_client", fake.client)
    organization = office(slug="atrasado-na-tela")
    user = owner(organization)
    record = contract(organization, lifecycle=TenantLifecycle.State.GRACE)
    TenantContract.objects.filter(pk=record.pk).update(status=TenantContract.Status.GRACE)
    late = invoice(record, status=Invoice.Status.OVERDUE)

    response = login(user, organization).post(
        reverse("hub:subscription"),
        {"action": "pay", "invoice": str(late.pk), "method": "pix"},
    )

    assert response.status_code == 302
    assert response["Location"] == "https://sandbox.asaas.com/i/pay_1"
    assert PaymentAttempt.objects.filter(invoice=late).count() == 1


def test_read_only_still_refuses_every_other_write() -> None:
    """A exceção é só da assinatura: o resto do produto segue recusando POST em carência."""

    organization, user, _ = trial_office("so-assinatura", ended=True)
    client = login(user, organization)

    refused = client.post(reverse("hub:companies"), {"name": "Nova", "cnpj_masked": "1"})
    team = client.post(reverse("hub:team"), {"full_name": "A", "email": "a@example.test"})

    assert refused.status_code == 403 and team.status_code == 403
    assert not ClientCompany.objects.filter(organization=organization, name="Nova").exists()


def test_a_suspended_office_still_cannot_reach_the_subscription_page() -> None:
    organization, user, _ = trial_office("suspensa")
    TenantLifecycle.objects.filter(organization=organization).update(state="suspended")

    page_response = login(user, organization).get(reverse("hub:subscription"))

    assert page_response.status_code == 403
