"""Cobrança automática por Asaas (E3): uma fatura em aberto vira um pagamento no provedor.

Regras:
- Desligada por `BILLING_COLLECTION_ENABLED` (padrão falso) e sem `ASAAS_API_KEY` nada é chamado.
  Só contrato com `billing_mode = automatic` é cobrado; todo contrato de hoje é manual.
- A tentativa (`PaymentAttempt`) é gravada ANTES da chamada, com chave de idempotência
  `asaas:{fatura}:{método}:{n}`: a mesma fatura e método devolvem a mesma tentativa.
- O Asaas não tem cabeçalho de idempotência (docs.asaas.com, lido em 20/11/2026). Falha de rede
  não repete o POST: a tentativa fica pendente sem id externo e `reconcile_unconfirmed` procura a
  cobrança pela `externalReference` (= id da tentativa) antes de dar a tentativa por perdida.
- Nenhum valor, plano ou preço nasce aqui: o valor é o da fatura que o fechamento de competência
  já gerou (D-79).
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.hub.models import OfficeProfile
from apps.organizations.models import Membership, Organization
from apps.platform.asaas import (
    AsaasClient,
    AsaasConfigurationError,
    AsaasResponseError,
    AsaasTransportError,
    Credentials,
    Payment,
)
from apps.platform.models import Invoice, PaymentAttempt, TenantContract

logger = logging.getLogger(__name__)

BILLING_TYPES: dict[str, str] = {
    PaymentAttempt.Method.PIX.value: "PIX",
    PaymentAttempt.Method.BOLETO.value: "BOLETO",
    PaymentAttempt.Method.CARD.value: "CREDIT_CARD",
}
UNCONFIRMED_AFTER = timedelta(minutes=2)
LOST_AFTER = timedelta(hours=1)
CLAIM_SECONDS = 90


class CollectionError(ValueError):
    """The charge cannot be created now; the message is safe to show to the office."""


def enabled() -> bool:
    return bool(settings.BILLING_COLLECTION_ENABLED and settings.ASAAS_API_KEY)


def build_client() -> AsaasClient:
    if not enabled():
        raise CollectionError("A cobrança automática está desligada.")
    try:
        credentials = Credentials(
            api_key=str(settings.ASAAS_API_KEY), environment=str(settings.ASAAS_ENVIRONMENT)
        )
        credentials.base_url  # noqa: B018 - validates key and environment before any call
    except AsaasConfigurationError as exc:
        raise CollectionError("A cobrança automática não está configurada.") from exc
    return AsaasClient(credentials)


def _customer_data(organization: Organization) -> tuple[str, str, str]:
    profile = OfficeProfile.objects.filter(organization=organization).first()
    name = (profile.legal_name if profile and profile.legal_name else organization.name).strip()
    cnpj = (profile.cnpj if profile else "").strip()
    if not cnpj:
        raise CollectionError("Falta o CNPJ do escritório para emitir a cobrança.")
    owner = (
        Membership.objects.filter(
            organization=organization, role=Membership.Role.OWNER, is_active=True
        )
        .select_related("user")
        .order_by("created_at")
        .first()
    )
    return name, cnpj, owner.user.email if owner is not None else ""


def _attempt_for(invoice: Invoice, method: str) -> tuple[PaymentAttempt, bool]:
    """The live attempt for this invoice and method, or a fresh one after a failed attempt.

    The flag says whether the attempt was just created: an older one without an external id may
    already exist at the provider (a lost response), so it is looked up before any new POST.
    """

    attempts = PaymentAttempt.objects.filter(
        invoice=invoice, provider=PaymentAttempt.Provider.ASAAS, method=method
    ).order_by("-created_at")
    latest = attempts.first()
    if latest is not None and latest.status in {
        PaymentAttempt.Status.PENDING,
        PaymentAttempt.Status.PAID,
    }:
        return latest, False
    key = f"asaas:{invoice.pk}:{method}:{attempts.count() + 1}"
    try:
        with transaction.atomic():
            created = PaymentAttempt.objects.create(
                invoice=invoice,
                provider=PaymentAttempt.Provider.ASAAS,
                method=method,
                idempotency_key=key,
            )
            return created, True
    except IntegrityError:
        return PaymentAttempt.objects.get(idempotency_key=key), False


def _record(attempt: PaymentAttempt, payment: Payment) -> PaymentAttempt:
    attempt.external_id = payment.external_id
    attempt.checkout_url = payment.checkout_url
    attempt.save(update_fields=["external_id", "checkout_url", "updated_at"])
    return attempt


def request_payment(
    *,
    invoice: Invoice,
    method: str,
    actor: Any = None,
    request: Any = None,
    client: AsaasClient | None = None,
    today: date | None = None,
) -> PaymentAttempt:
    """Create (or return) the Asaas charge of one open invoice."""

    if client is None and not enabled():
        raise CollectionError("A cobrança automática está desligada.")
    billing_type = BILLING_TYPES.get(method)
    if billing_type is None:
        raise CollectionError("Forma de pagamento indisponível.")
    today = today or timezone.localdate()
    with transaction.atomic():
        locked = Invoice.objects.select_for_update().select_related("contract").get(pk=invoice.pk)
        if locked.contract.billing_mode != TenantContract.BillingMode.AUTOMATIC:
            raise CollectionError("Este contrato é cobrado pela Mewstack, fora do sistema.")
        if locked.status not in {Invoice.Status.OPEN, Invoice.Status.OVERDUE}:
            raise CollectionError("Esta fatura não está em aberto.")
        if locked.total_amount_cents <= 0:
            raise CollectionError("Esta fatura não tem valor a cobrar.")
        attempt, created = _attempt_for(locked, method)
    if attempt.status == PaymentAttempt.Status.PAID:
        raise CollectionError("Esta fatura já foi paga.")
    if attempt.external_id:
        return attempt
    claim = f"collection:{attempt.pk}"
    if not cache.add(claim, 1, timeout=CLAIM_SECONDS):
        raise CollectionError("Já existe uma cobrança sendo criada para esta fatura. Aguarde.")
    try:
        api = client or build_client()
        contract = locked.contract
        try:
            # An attempt that already existed may have reached Asaas with the response lost:
            # look it up by reference before any new POST (Asaas has no idempotency header).
            payment = None if created else api.find_payment_by_reference(str(attempt.pk))
            if payment is None:
                if not contract.asaas_customer_id:
                    name, cnpj, email = _customer_data(locked.organization)
                    customer = api.find_or_create_customer(
                        name=name,
                        cpf_cnpj=cnpj,
                        external_reference=str(locked.organization_id),
                        email=email,
                    )
                    contract.asaas_customer_id = customer.external_id
                    contract.save(update_fields=["asaas_customer_id", "updated_at"])
                payment = api.create_payment(
                    customer_id=contract.asaas_customer_id,
                    billing_type=billing_type,
                    amount_cents=locked.total_amount_cents,
                    due_on=max(locked.due_on, today),
                    description=f"Mensalidade CICA, competência {locked.period_start:%m/%Y}"[:500],
                    external_reference=str(attempt.pk),
                )
        except AsaasTransportError as exc:
            logger.warning("collection.transport_error attempt=%s", attempt.pk)
            raise CollectionError(
                "O Asaas não respondeu. A cobrança será conferida em alguns minutos; "
                "não tente de novo agora."
            ) from exc
        except AsaasResponseError as exc:
            attempt.status = PaymentAttempt.Status.FAILED
            attempt.save(update_fields=["status", "updated_at"])
            raise CollectionError("O Asaas recusou a cobrança. Fale com o suporte.") from exc
        except AsaasConfigurationError as exc:
            attempt.status = PaymentAttempt.Status.FAILED
            attempt.save(update_fields=["status", "updated_at"])
            raise CollectionError("Dados da cobrança incompletos. Fale com o suporte.") from exc
    finally:
        cache.delete(claim)
    attempt = _record(attempt, payment)
    record_event(
        action="platform.billing.payment_requested",
        actor=actor,
        organization=locked.organization,
        target=attempt,
        request=request,
        metadata={"method": method, "invoice": str(locked.pk)},
    )
    return attempt


def reconcile_unconfirmed(
    *,
    client: AsaasClient | None = None,
    now: datetime | None = None,
) -> dict[str, int]:
    """Find charges whose creation response was lost; give up on those Asaas never saw."""

    now = now or timezone.now()
    stale = list(
        PaymentAttempt.objects.filter(
            provider=PaymentAttempt.Provider.ASAAS,
            status=PaymentAttempt.Status.PENDING,
            external_id="",
            created_at__lt=now - UNCONFIRMED_AFTER,
            invoice__contract__billing_mode=TenantContract.BillingMode.AUTOMATIC,
        ).order_by("created_at")[:100]
    )
    outcome = {"found": 0, "lost": 0, "waiting": 0, "unavailable": 0}
    if not stale:
        return outcome
    api = client or build_client()
    for attempt in stale:
        try:
            payment = api.find_payment_by_reference(str(attempt.pk))
        except (AsaasTransportError, AsaasResponseError):
            outcome["unavailable"] += 1
            continue
        if payment is not None:
            _record(attempt, payment)
            outcome["found"] += 1
        elif attempt.created_at < now - LOST_AFTER:
            attempt.status = PaymentAttempt.Status.FAILED
            attempt.save(update_fields=["status", "updated_at"])
            outcome["lost"] += 1
        else:
            outcome["waiting"] += 1
    return outcome
