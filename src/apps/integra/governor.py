"""Cost governor for the Integra Contador (T10.4).

Every call that reaches the gateway goes through `GovernedClient`, which

* refuses, before sending, a call that would pass the monthly limit of the office or the limit
  of the conversation, and a conversation that already made too many calls (no loop of a model
  can spend without bound);
* checks the procuração of the taxpayer once (OBTERPROCURACAO41, cached for a few minutes)
  before any paid call, because a 403 for a missing procuração is charged too;
* records what each call may have cost: Serpro charges 200, 202 and 403 on /Consultar, /Emitir
  and /Declarar, and nothing on /Apoiar and /Monitorar or on any other status;
* tags every request with `X-Request-Tag`, which shows up in the consumption report of Serpro.

Prices are the first-band prices of the Loja Serpro (Consulta 0,24, Emissão 0,32, Declaração
0,40), a ceiling: the real price falls with the monthly volume (research report, 1.6). No payload
is stored.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from django.core.cache import cache
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.integra.catalog import ServiceSpec, Verb, service
from apps.integra.client import IntegraClient
from apps.integra.errors import (
    IntegraBudgetExceeded,
    IntegraNotAuthorized,
    IntegraProcuracaoMissing,
    IntegraServiceError,
)
from apps.integra.models import IntegraCall, OfficeSerproIdentity
from apps.organizations.models import Organization

PRICE_CENTS = {Verb.CONSULTAR: 24, Verb.EMITIR: 32, Verb.DECLARAR: 40}
CHARGED_STATUSES = frozenset({200, 202, 403})
MAX_CALLS_PER_CONVERSATION = 20
PROCURACAO_OK_SECONDS = 600
PROCURACAO_MISSING_SECONDS = 300
PROCURACAO_KEY = "procuracao.obter"
_DEFAULT_MONTHLY_CAP = 5000
_DEFAULT_CONVERSATION_CAP = 500


def charged_status(status: int) -> bool:
    return status in CHARGED_STATUSES


def call_cost_cents(spec: ServiceSpec) -> int:
    """What a charged call to this service costs, at the first-band price."""

    return PRICE_CENTS.get(spec.verb, 0) if spec.billable else 0


def request_tag(organization: Organization) -> str:
    """`X-Request-Tag` of the office: up to 32 characters, stable, no personal data."""

    return f"cica-{organization.pk.hex[:20]}"


def _month_start(now: datetime) -> datetime:
    local = timezone.localtime(now)
    return local.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


class GovernedClient:
    def __init__(
        self,
        client: IntegraClient,
        organization: Organization,
        *,
        conversation_id: str = "",
        check_procuracao: bool = True,
    ) -> None:
        self.client = client
        self.organization = organization
        self.conversation_id = conversation_id[:64]
        self.check_procuracao = check_procuracao

    # -- limits ------------------------------------------------------------------------------

    def _caps(self) -> tuple[int, int]:
        identity = OfficeSerproIdentity.objects.filter(organization=self.organization).first()
        if identity is None:
            return _DEFAULT_MONTHLY_CAP, _DEFAULT_CONVERSATION_CAP
        return identity.monthly_cap_cents, identity.conversation_cap_cents

    def _spent(self, **filters: Any) -> int:
        total = IntegraCall.objects.filter(organization=self.organization, **filters).aggregate(
            total=Sum("cost_cents")
        )["total"]
        return int(total or 0)

    def _ensure_budget(self, cost: int) -> None:
        monthly_cap, conversation_cap = self._caps()
        if self.conversation_id:
            calls = IntegraCall.objects.filter(
                organization=self.organization, conversation_id=self.conversation_id
            ).count()
            if calls >= MAX_CALLS_PER_CONVERSATION:
                raise IntegraBudgetExceeded(
                    f"A conversa chegou a {MAX_CALLS_PER_CONVERSATION} chamadas ao Serpro."
                )
        if cost == 0:
            return
        if self.conversation_id:
            spent = self._spent(conversation_id=self.conversation_id)
            if spent + cost > conversation_cap:
                raise IntegraBudgetExceeded("A conversa atingiu o limite de gasto no Serpro.")
        month = self._spent(created_at__gte=_month_start(timezone.now()))
        if month + cost > monthly_cap:
            raise IntegraBudgetExceeded("O escritório atingiu o limite mensal de gasto no Serpro.")

    # -- one call ----------------------------------------------------------------------------

    def _reserve(self, spec: ServiceSpec) -> IntegraCall:
        """Check the limits and book the cost of the call in one step.

        The row of the office is locked while the limits are read and the provisional call is
        written, so two calls that arrive together cannot both pass a limit that only one fits.
        The booked cost counts for the next check right away and is settled after the answer.
        """

        with transaction.atomic():
            Organization.objects.select_for_update().get(pk=self.organization.pk)
            cost = call_cost_cents(spec)
            self._ensure_budget(cost)
            return IntegraCall.objects.create(
                organization=self.organization,
                service_key=spec.key,
                http_status=0,
                charged=cost > 0,
                cost_cents=cost,
                conversation_id=self.conversation_id,
                request_tag=request_tag(self.organization),
            )

    @staticmethod
    def _settle(call: IntegraCall, spec: ServiceSpec, status: int) -> None:
        charged = spec.billable and charged_status(status)
        call.http_status = status
        call.charged = charged
        call.cost_cents = call_cost_cents(spec) if charged else 0
        call.save(update_fields=["http_status", "charged", "cost_cents", "updated_at"])

    def _send(
        self,
        key: str,
        contribuinte: str,
        dados: dict[str, Any] | str | None,
        autenticar_procurador_token: str | None,
        autor_pedido: str | None = None,
    ) -> dict[str, Any]:
        spec = service(key)
        call = self._reserve(spec)
        try:
            payload = self.client.call(
                key,
                contribuinte=contribuinte,
                dados=dados,
                autor_pedido=autor_pedido,
                autenticar_procurador_token=autenticar_procurador_token,
                request_tag=request_tag(self.organization),
            )
        except IntegraServiceError as exc:
            self._settle(call, spec, exc.status)
            raise
        except BaseException:
            # Nothing reached the gateway or nothing was charged: give the booked cost back.
            self._settle(call, spec, 0)
            raise
        status = payload.get("status", 200)
        self._settle(call, spec, status if isinstance(status, int) else 200)
        return payload

    # -- procuração --------------------------------------------------------------------------

    def _procuracao_key(self, contribuinte: str) -> str:
        return f"integra:procuracao:{self.organization.pk.hex}:{contribuinte}"

    def _ensure_procuracao(self, contribuinte: str, autor_pedido: str | None) -> None:
        key = self._procuracao_key(contribuinte)
        known = cache.get(key)
        if known == "missing":
            raise IntegraProcuracaoMissing("O cliente não tem procuração para o escritório.")
        if known == "ok":
            return
        author = autor_pedido or self.client.credentials.autor_pedido
        dados = {
            "outorgante": contribuinte,
            "tipoOutorgante": "1" if len(contribuinte) == 11 else "2",
            "outorgado": author,
            "tipoOutorgado": "1" if len(author) == 11 else "2",
        }
        try:
            payload = self._send(PROCURACAO_KEY, contribuinte, dados, None, autor_pedido)
        except IntegraNotAuthorized:
            cache.set(key, "missing", PROCURACAO_MISSING_SECONDS)
            raise IntegraProcuracaoMissing(
                "O cliente não tem procuração para o escritório."
            ) from None
        if payload.get("dados") in ("[]", []):
            cache.set(key, "missing", PROCURACAO_MISSING_SECONDS)
            raise IntegraProcuracaoMissing("O cliente não tem procuração para o escritório.")
        cache.set(key, "ok", PROCURACAO_OK_SECONDS)

    # -- public ------------------------------------------------------------------------------

    def call(
        self,
        service_key: str,
        *,
        contribuinte: str,
        dados: dict[str, Any] | str | None = None,
        autenticar_procurador_token: str | None = None,
        autor_pedido: str | None = None,
    ) -> dict[str, Any]:
        spec = service(service_key)
        if self.check_procuracao and spec.billable and spec.key != PROCURACAO_KEY:
            self._ensure_procuracao(contribuinte, autor_pedido)
        return self._send(spec.key, contribuinte, dados, autenticar_procurador_token, autor_pedido)
