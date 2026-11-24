"""Apoio dos testes de cobrança (E3): Asaas falso, escritório com contrato e faturas."""

from __future__ import annotations

import json
from datetime import date, timedelta
from typing import Any
from urllib.parse import parse_qs, urlparse

from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import OfficeProfile
from apps.organizations.models import Membership, Organization
from apps.platform.asaas import AsaasClient, AsaasTransportError, Credentials
from apps.platform.models import Invoice, Plan, TenantContract, TenantLifecycle
from test_nfse_procuracao import OFFICE_CNPJ


class FakeAsaas:
    """Transporte que imita o essencial da API v3 e guarda cada chamada."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str, dict[str, Any] | None]] = []
        self.customers: dict[str, dict[str, Any]] = {}
        self.payments: dict[str, dict[str, Any]] = {}
        self.script: list[Any] = []  # (status, payload) ou Exception, consumido na ordem
        self.hide_created_payments = (
            False  # simula a resposta perdida: o Asaas criou, nós não vimos
        )

    def client(self) -> AsaasClient:
        return AsaasClient(
            Credentials(api_key="chave-de-teste", environment="sandbox"), transport=self
        )

    def posts(self, path: str) -> list[dict[str, Any]]:
        return [body for method, p, body in self.calls if method == "POST" and p == path and body]

    def __call__(
        self, url: str, *, method: str, data: bytes | None, headers: dict[str, str]
    ) -> tuple[int, bytes]:
        parsed = urlparse(url)
        path = parsed.path.removeprefix("/v3")
        body = json.loads(data) if data else None
        self.calls.append((method, path, body))
        if self.script:
            step = self.script.pop(0)
            if isinstance(step, Exception):
                raise step
            status, payload = step
            return status, json.dumps(payload).encode()
        query = parse_qs(parsed.query)
        if method == "GET" and path == "/customers":
            ref = query["externalReference"][0]
            rows = [c for c in self.customers.values() if c["externalReference"] == ref]
            return 200, json.dumps({"data": rows}).encode()
        if method == "POST" and path == "/customers" and body:
            customer = {"id": f"cus_{len(self.customers) + 1}", **body}
            self.customers[customer["id"]] = customer
            return 200, json.dumps(customer).encode()
        if method == "GET" and path == "/payments":
            ref = query["externalReference"][0]
            rows = [p for p in self.payments.values() if p["externalReference"] == ref]
            return 200, json.dumps({"data": rows}).encode()
        if method == "POST" and path == "/payments" and body:
            payment = {
                "id": f"pay_{len(self.payments) + 1}",
                "status": "PENDING",
                "invoiceUrl": f"https://sandbox.asaas.com/i/pay_{len(self.payments) + 1}",
                **body,
            }
            self.payments[payment["id"]] = payment
            if self.hide_created_payments:
                raise AsaasTransportError("resposta perdida")
            return 200, json.dumps(payment).encode()
        return 404, b"{}"


def office(*, slug: str = "cobranca", with_cnpj: bool = True) -> Organization:
    organization = Organization.objects.create(name="Escritório Cobrança", slug=slug)
    OfficeProfile.objects.create(
        organization=organization,
        legal_name="Escritório Cobrança Ltda",
        cnpj=OFFICE_CNPJ if with_cnpj else "",
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
    )
    return organization


def owner(organization: Organization, email: str = "dono.cobranca@example.test") -> User:
    user = User.objects.create_user(email=email, password="uma-senha-longa")
    Membership.objects.create(organization=organization, user=user, role=Membership.Role.OWNER)
    return user


def plan(code: str = "plano-b", *, price: int = 49900, limits: Any = None, **extra: Any) -> Plan:
    return Plan.objects.create(
        code=code,
        name=extra.pop("name", "Plano B"),
        monthly_price_cents=price,
        limits=limits if limits is not None else {"companies": 120, "users": 8},
        modules=extra.pop("modules", ["nfse"]),
        **extra,
    )


def contract(
    organization: Organization,
    *,
    mode: str = TenantContract.BillingMode.AUTOMATIC,
    status: str = TenantContract.Status.ACTIVE,
    price: int = 49900,
    starts_on: date | None = None,
    reference: str = "",
    lifecycle: str | None = TenantLifecycle.State.ACTIVE,
) -> TenantContract:
    record = TenantContract.objects.create(
        organization=organization,
        plan=plan(f"plano-{organization.slug}", price=price),
        monthly_price_cents=price,
        monthly_price_locked=True,
        status=status,
        billing_mode=mode,
        starts_on=starts_on,
        reference=reference,
        selected_modules=["nfse"],
    )
    if lifecycle is not None:
        TenantLifecycle.objects.create(organization=organization, state=lifecycle)
    return record


def invoice(
    record: TenantContract,
    *,
    period_start: date | None = None,
    due_on: date | None = None,
    total: int = 49900,
    status: str = Invoice.Status.OPEN,
) -> Invoice:
    today = timezone.localdate()
    start = period_start or today.replace(day=1) - timedelta(days=31)
    start = start.replace(day=1)
    end = (start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
    return Invoice.objects.create(
        organization=record.organization,
        contract=record,
        period_start=start,
        period_end=end,
        due_on=due_on or (end + timedelta(days=10)),
        status=status,
        base_amount_cents=total,
        total_amount_cents=total,
    )
