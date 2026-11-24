"""Cobrança por Asaas (E3): uma fatura vira um pagamento, sem repetir e sem perder resposta."""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.cache import cache
from django.test.utils import override_settings
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.platform import collection
from apps.platform.asaas import AsaasTransportError
from apps.platform.collection import CollectionError, reconcile_unconfirmed, request_payment
from apps.platform.models import Invoice, PaymentAttempt, TenantContract
from billing_support import FakeAsaas, contract, invoice, office, owner

PIX = PaymentAttempt.Method.PIX.value
BOLETO = PaymentAttempt.Method.BOLETO.value


@pytest.fixture
def fake() -> FakeAsaas:
    return FakeAsaas()


@pytest.fixture
def setup(db: object) -> tuple[Invoice, TenantContract]:
    organization = office()
    owner(organization)
    record = contract(organization)
    return invoice(record), record


def pay(setup: tuple[Invoice, TenantContract], fake: FakeAsaas, method: str = PIX, **kw: object):
    return request_payment(invoice=setup[0], method=method, client=fake.client(), **kw)


# ---------------------------------------------------------------- desligada por padrão


@pytest.mark.django_db
def test_collection_is_off_by_default_and_needs_the_key(
    setup: tuple[Invoice, TenantContract],
) -> None:
    assert collection.enabled() is False
    with pytest.raises(CollectionError, match="desligada"):
        request_payment(invoice=setup[0], method=PIX)
    with override_settings(BILLING_COLLECTION_ENABLED=True, ASAAS_API_KEY=""):
        assert collection.enabled() is False
    with (
        override_settings(
            BILLING_COLLECTION_ENABLED=True, ASAAS_API_KEY="k", ASAAS_ENVIRONMENT="x"
        ),
        pytest.raises(CollectionError, match="não está configurada"),
    ):
        collection.build_client()
    with override_settings(BILLING_COLLECTION_ENABLED=True, ASAAS_API_KEY="k"):
        assert collection.build_client().credentials.environment == "sandbox"


# ---------------------------------------------------------------- caminho feliz


@pytest.mark.django_db
def test_an_open_invoice_becomes_a_customer_and_a_payment(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas
) -> None:
    attempt = pay(setup, fake)

    assert attempt.status == PaymentAttempt.Status.PENDING
    assert attempt.external_id == "pay_1"
    assert attempt.checkout_url == "https://sandbox.asaas.com/i/pay_1"
    assert attempt.idempotency_key == f"asaas:{setup[0].pk}:pix:1"
    [customer] = fake.posts("/customers")
    assert customer["name"] == "Escritório Cobrança Ltda"
    assert customer["cpfCnpj"] and customer["email"] == "dono.cobranca@example.test"
    assert customer["externalReference"] == str(setup[1].organization_id)
    [charge] = fake.posts("/payments")
    assert charge["billingType"] == "PIX" and charge["value"] == 499.0
    assert charge["externalReference"] == str(attempt.pk)  # é por aqui que se concilia
    assert "competência" in charge["description"]
    setup[1].refresh_from_db()
    assert setup[1].asaas_customer_id == "cus_1"
    assert Invoice.objects.get(pk=setup[0].pk).status == Invoice.Status.OPEN
    event = AuditEvent.objects.get(action="platform.billing.payment_requested")
    assert event.metadata == {"method": "pix", "invoice": str(setup[0].pk)}


@pytest.mark.django_db
def test_asking_again_returns_the_same_attempt_without_a_second_charge(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas
) -> None:
    first = pay(setup, fake)
    again = pay(setup, fake)

    assert again.pk == first.pk
    assert len(fake.posts("/payments")) == 1


@pytest.mark.django_db
def test_another_method_is_another_attempt_and_the_customer_is_reused(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas
) -> None:
    pix = pay(setup, fake, PIX)
    boleto = pay(setup, fake, BOLETO)

    assert {pix.method, boleto.method} == {"pix", "boleto"} and pix.pk != boleto.pk
    assert len(fake.posts("/customers")) == 1  # o cliente do Asaas é criado uma vez só
    assert [c["billingType"] for c in fake.posts("/payments")] == ["PIX", "BOLETO"]


@pytest.mark.django_db
def test_an_existing_asaas_customer_is_found_not_duplicated(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas
) -> None:
    fake.customers["cus_9"] = {
        "id": "cus_9",
        "name": "Já existe",
        "externalReference": str(setup[1].organization_id),
    }

    pay(setup, fake)

    assert fake.posts("/customers") == []
    setup[1].refresh_from_db()
    assert setup[1].asaas_customer_id == "cus_9"


@pytest.mark.django_db
def test_an_overdue_invoice_is_charged_with_today_as_the_due_date(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas
) -> None:
    today = timezone.localdate()
    Invoice.objects.filter(pk=setup[0].pk).update(
        due_on=today - timedelta(days=12), status=Invoice.Status.OVERDUE
    )

    pay(setup, fake)

    assert fake.posts("/payments")[0]["dueDate"] == today.isoformat()


# ---------------------------------------------------------------- recusas


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"status": Invoice.Status.PAID}, "não está em aberto"),
        ({"status": Invoice.Status.VOID}, "não está em aberto"),
        ({"status": Invoice.Status.DISPUTED}, "não está em aberto"),
        ({"total_amount_cents": 0}, "não tem valor"),
    ],
)
def test_only_an_open_invoice_with_a_value_is_charged(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas, changes: dict[str, object], message: str
) -> None:
    Invoice.objects.filter(pk=setup[0].pk).update(**changes)

    with pytest.raises(CollectionError, match=message):
        pay(setup, fake)

    assert fake.calls == []


@pytest.mark.django_db
def test_a_manual_contract_is_never_charged_by_the_system(fake: FakeAsaas) -> None:
    organization = office(slug="manual")
    record = contract(organization, mode=TenantContract.BillingMode.MANUAL)
    manual = invoice(record)

    with pytest.raises(CollectionError, match="fora do sistema"):
        request_payment(invoice=manual, method=PIX, client=fake.client())

    assert fake.calls == []


@pytest.mark.django_db
def test_an_unknown_method_and_a_missing_cnpj_are_refused(fake: FakeAsaas) -> None:
    organization = office(slug="sem-cnpj", with_cnpj=False)
    record = contract(organization)
    open_invoice = invoice(record)

    with pytest.raises(CollectionError, match="Forma de pagamento"):
        request_payment(invoice=open_invoice, method="cheque", client=fake.client())
    with pytest.raises(CollectionError, match="CNPJ do escritório"):
        request_payment(invoice=open_invoice, method=PIX, client=fake.client())


@pytest.mark.django_db
def test_a_paid_attempt_blocks_a_second_payment(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas
) -> None:
    attempt = pay(setup, fake)
    PaymentAttempt.objects.filter(pk=attempt.pk).update(status=PaymentAttempt.Status.PAID)

    with pytest.raises(CollectionError, match="já foi paga"):
        pay(setup, fake)


@pytest.mark.django_db
def test_two_clicks_at_once_create_one_charge(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas
) -> None:
    attempt = PaymentAttempt.objects.create(
        invoice=setup[0],
        provider=PaymentAttempt.Provider.ASAAS,
        method=PIX,
        idempotency_key=f"asaas:{setup[0].pk}:pix:1",
    )
    cache.add(f"collection:{attempt.pk}", 1, timeout=60)  # outra requisição já está criando

    with pytest.raises(CollectionError, match="sendo criada"):
        pay(setup, fake)

    assert fake.calls == []
    cache.delete(f"collection:{attempt.pk}")


# ---------------------------------------------------------------- falhas do provedor


@pytest.mark.django_db
def test_a_provider_refusal_fails_the_attempt_and_the_next_one_starts_clean(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas
) -> None:
    fake.script = [
        (200, {"data": []}),
        (200, {"id": "cus_1", "name": "x"}),
        (400, {"errors": [{"description": "Cliente inválido."}]}),
    ]

    with pytest.raises(CollectionError, match="recusou"):
        pay(setup, fake)
    failed = PaymentAttempt.objects.get(invoice=setup[0])
    assert failed.status == PaymentAttempt.Status.FAILED and failed.external_id == ""

    second = pay(setup, fake)

    assert second.pk != failed.pk and second.idempotency_key.endswith(":pix:2")
    assert second.external_id.startswith("pay_")


@pytest.mark.django_db
def test_a_lost_response_is_not_retried_and_is_found_later_by_its_reference(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas
) -> None:
    fake.hide_created_payments = True
    with pytest.raises(CollectionError, match="não tente de novo"):
        pay(setup, fake)
    attempt = PaymentAttempt.objects.get(invoice=setup[0])
    assert attempt.status == PaymentAttempt.Status.PENDING and attempt.external_id == ""
    assert len(fake.posts("/payments")) == 1

    # clicar de novo antes da conciliação acha a cobrança pela referência, não cria outra
    fake.hide_created_payments = False
    again = pay(setup, fake)
    assert again.pk == attempt.pk and again.external_id == "pay_1"
    assert len(fake.posts("/payments")) == 1
    PaymentAttempt.objects.filter(pk=attempt.pk).update(external_id="", checkout_url="")
    outcome = reconcile_unconfirmed(
        client=fake.client(),
        now=timezone.now() + collection.UNCONFIRMED_AFTER + timedelta(seconds=5),
    )

    assert outcome["found"] == 1
    attempt.refresh_from_db()
    assert attempt.external_id == "pay_1" and attempt.checkout_url.endswith("/pay_1")
    assert len(fake.posts("/payments")) == 1


@pytest.mark.django_db
def test_reconciliation_waits_then_gives_up_on_a_charge_the_provider_never_saw(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas
) -> None:
    attempt = PaymentAttempt.objects.create(
        invoice=setup[0],
        provider=PaymentAttempt.Provider.ASAAS,
        method=PIX,
        idempotency_key=f"asaas:{setup[0].pk}:pix:1",
    )
    soon = attempt.created_at + collection.UNCONFIRMED_AFTER + timedelta(seconds=1)
    late = attempt.created_at + collection.LOST_AFTER + timedelta(minutes=1)

    assert reconcile_unconfirmed(client=fake.client(), now=attempt.created_at) == {
        "found": 0,
        "lost": 0,
        "waiting": 0,
        "unavailable": 0,
    }
    assert reconcile_unconfirmed(client=fake.client(), now=soon)["waiting"] == 1
    attempt.refresh_from_db()
    assert attempt.status == PaymentAttempt.Status.PENDING

    assert reconcile_unconfirmed(client=fake.client(), now=late)["lost"] == 1
    attempt.refresh_from_db()
    assert attempt.status == PaymentAttempt.Status.FAILED


@pytest.mark.django_db
def test_reconciliation_survives_a_provider_outage_and_skips_manual_contracts(
    setup: tuple[Invoice, TenantContract], fake: FakeAsaas
) -> None:
    attempt = PaymentAttempt.objects.create(
        invoice=setup[0],
        provider=PaymentAttempt.Provider.ASAAS,
        method=PIX,
        idempotency_key=f"asaas:{setup[0].pk}:pix:1",
    )
    later = attempt.created_at + timedelta(minutes=10)
    fake.script = [AsaasTransportError("fora do ar")]

    assert reconcile_unconfirmed(client=fake.client(), now=later)["unavailable"] == 1

    TenantContract.objects.filter(pk=setup[1].pk).update(billing_mode="manual")
    assert reconcile_unconfirmed(client=fake.client(), now=later) == {
        "found": 0,
        "lost": 0,
        "waiting": 0,
        "unavailable": 0,
    }
