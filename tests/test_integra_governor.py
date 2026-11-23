"""T10.4: cost governor. Fake transport only: nothing here reaches the Serpro."""

from __future__ import annotations

import json
import ssl
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from django.core.cache import cache
from django.utils import timezone

from apps.integra.client import Credentials, IntegraClient
from apps.integra.errors import IntegraBudgetExceeded, IntegraProcuracaoMissing
from apps.integra.governor import (
    MAX_CALLS_PER_CONVERSATION,
    GovernedClient,
    call_cost_cents,
    charged_status,
    request_tag,
)
from apps.integra.models import IntegraCall, OfficeSerproIdentity
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db

CREDENTIALS = Credentials(
    consumer_key="key",
    consumer_secret="secret",
    certificate_path=Path("unused.pfx"),
    certificate_password="",
    contratante="11222333000181",
    autor_pedido="11444777000161",
    environment="trial",
)
CLIENT_CNPJ = "11222333000181"


class Gateway:
    """Answers by idServico; the default is a plain 200."""

    def __init__(self, **statuses: int) -> None:
        self.statuses = statuses
        self.calls: list[dict[str, Any]] = []

    def __call__(
        self, url: str, *, data: bytes, headers: dict[str, str], context: ssl.SSLContext | None
    ) -> tuple[int, bytes]:
        if url.endswith("/authenticate"):
            body = {"access_token": "a", "jwt_token": "j", "expires_in": 2008}
            return 200, json.dumps(body).encode()
        envelope = json.loads(data)
        service = envelope["pedidoDados"]["idServico"]
        self.calls.append({"service": service, "headers": headers})
        status = self.statuses.get(service, 200)
        return status, json.dumps({"status": status, "mensagens": [], "dados": "{}"}).encode()

    def services(self) -> list[str]:
        return [call["service"] for call in self.calls]


@pytest.fixture(autouse=True)
def _clean_cache() -> None:
    cache.clear()


def _governed(
    organization: Organization, gateway: Gateway, *, conversation: str = "", check: bool = True
) -> GovernedClient:
    client = IntegraClient(CREDENTIALS, transport=gateway)
    return GovernedClient(
        client, organization, conversation_id=conversation, check_procuracao=check
    )


def test_cost_is_the_first_band_price_and_only_where_serpro_charges() -> None:
    from apps.integra.catalog import service

    assert call_cost_cents(service("pgdasd.declaracoes")) == 24
    assert call_cost_cents(service("pgdasd.das")) == 32
    assert call_cost_cents(service("pgdasd.transmitir")) == 40
    assert call_cost_cents(service("eventosatualizacao.obter_pj")) == 0
    assert call_cost_cents(service("sitfis.protocolo")) == 0
    assert [charged_status(code) for code in (200, 202, 403, 204, 400, 404, 429, 500)] == [
        True, True, True, False, False, False, False, False,
    ]


def test_the_request_tag_names_the_office_and_fits_the_limit(organization: Organization) -> None:
    other = Organization.objects.create(name="Outro", slug="outro")

    assert len(request_tag(organization)) <= 32
    assert request_tag(organization) == request_tag(organization)
    assert request_tag(organization) != request_tag(other)


def test_a_call_is_recorded_with_its_cost_tag_and_conversation(organization: Organization) -> None:
    gateway = Gateway()
    governed = _governed(organization, gateway, conversation="c1", check=False)

    governed.call("pgdasd.declaracoes", contribuinte=CLIENT_CNPJ, dados={"anoCalendario": "2018"})

    call = IntegraCall.objects.get()
    assert (call.service_key, call.http_status, call.charged, call.cost_cents) == (
        "pgdasd.declaracoes", 200, True, 24,
    )
    assert call.conversation_id == "c1" and call.request_tag == request_tag(organization)
    assert gateway.calls[0]["headers"]["X-Request-Tag"] == request_tag(organization)


def test_free_services_cost_nothing_but_are_still_recorded(organization: Organization) -> None:
    governed = _governed(organization, Gateway(), check=False)

    governed.call("sitfis.protocolo", contribuinte=CLIENT_CNPJ)

    call = IntegraCall.objects.get()
    assert (call.charged, call.cost_cents) == (False, 0)


def test_a_denied_call_is_charged_and_a_server_error_is_not(organization: Organization) -> None:
    from apps.integra.errors import IntegraNotAuthorized, IntegraServiceError

    governed = _governed(organization, Gateway(CONSDECLARACAO13=403, CONSDECREC15=500), check=False)

    with pytest.raises(IntegraNotAuthorized):
        governed.call("pgdasd.declaracoes", contribuinte=CLIENT_CNPJ)
    with pytest.raises(IntegraServiceError):
        governed.call("pgdasd.declaracao", contribuinte=CLIENT_CNPJ)

    denied, failed = IntegraCall.objects.order_by("created_at")
    assert (denied.http_status, denied.charged, denied.cost_cents) == (403, True, 24)
    assert (failed.http_status, failed.charged, failed.cost_cents) == (500, False, 0)


def test_the_monthly_cap_stops_the_call_before_it_is_sent(organization: Organization) -> None:
    OfficeSerproIdentity.objects.create(organization=organization, monthly_cap_cents=50)
    gateway = Gateway()
    governed = _governed(organization, gateway, check=False)

    governed.call("pgdasd.declaracoes", contribuinte=CLIENT_CNPJ)
    governed.call("pgdasd.declaracoes", contribuinte=CLIENT_CNPJ)
    with pytest.raises(IntegraBudgetExceeded, match="mensal"):
        governed.call("pgdasd.declaracoes", contribuinte=CLIENT_CNPJ)

    assert gateway.services().count("CONSDECLARACAO13") == 2
    # A free service is never blocked by the cap.
    governed.call("sitfis.protocolo", contribuinte=CLIENT_CNPJ)


def test_spending_of_another_month_or_office_does_not_count(organization: Organization) -> None:
    other = Organization.objects.create(name="Outro", slug="outro")
    OfficeSerproIdentity.objects.create(organization=organization, monthly_cap_cents=30)
    IntegraCall.objects.create(
        organization=organization, service_key="x", http_status=200, charged=True,
        cost_cents=24, request_tag="t",
    )
    IntegraCall.objects.filter(organization=organization).update(
        created_at=timezone.now() - timedelta(days=45)
    )
    IntegraCall.objects.create(
        organization=other, service_key="x", http_status=200, charged=True,
        cost_cents=500, request_tag="t",
    )

    _governed(organization, Gateway(), check=False).call(
        "pgdasd.declaracoes", contribuinte=CLIENT_CNPJ
    )


def test_the_conversation_cap_and_the_call_count_stop_a_loop(organization: Organization) -> None:
    OfficeSerproIdentity.objects.create(
        organization=organization, monthly_cap_cents=100_000, conversation_cap_cents=40
    )
    gateway = Gateway()
    governed = _governed(organization, gateway, conversation="loop", check=False)

    governed.call("pgdasd.declaracoes", contribuinte=CLIENT_CNPJ)
    with pytest.raises(IntegraBudgetExceeded, match="conversa"):
        governed.call("pgdasd.declaracoes", contribuinte=CLIENT_CNPJ)
    # Another conversation has its own budget.
    _governed(organization, gateway, conversation="outra", check=False).call(
        "pgdasd.declaracoes", contribuinte=CLIENT_CNPJ
    )

    OfficeSerproIdentity.objects.filter(organization=organization).update(
        conversation_cap_cents=100_000
    )
    busy = _governed(organization, Gateway(), conversation="busy", check=False)
    for _ in range(MAX_CALLS_PER_CONVERSATION):
        busy.call("sitfis.protocolo", contribuinte=CLIENT_CNPJ)
    with pytest.raises(IntegraBudgetExceeded, match="chamadas"):
        busy.call("sitfis.protocolo", contribuinte=CLIENT_CNPJ)


def test_the_procuracao_is_checked_once_before_spending_and_remembered(
    organization: Organization,
) -> None:
    gateway = Gateway()
    governed = _governed(organization, gateway)

    governed.call("pgdasd.declaracoes", contribuinte=CLIENT_CNPJ)
    governed.call("pgdasd.declaracao", contribuinte=CLIENT_CNPJ)

    assert gateway.services() == ["OBTERPROCURACAO41", "CONSDECLARACAO13", "CONSDECREC15"]
    assert IntegraCall.objects.filter(service_key="procuracao.obter").count() == 1


def test_without_procuracao_the_paid_call_is_not_made_and_the_answer_is_remembered(
    organization: Organization,
) -> None:
    gateway = Gateway(OBTERPROCURACAO41=403)
    governed = _governed(organization, gateway)

    for _ in range(2):
        with pytest.raises(IntegraProcuracaoMissing):
            governed.call("pgdasd.declaracoes", contribuinte=CLIENT_CNPJ)

    assert gateway.services() == ["OBTERPROCURACAO41"]
    # The denied check was the only charge: R$ 0,24.
    assert sum(IntegraCall.objects.values_list("cost_cents", flat=True)) == 24


def test_free_services_skip_the_procuracao_check(organization: Organization) -> None:
    gateway = Gateway()

    _governed(organization, gateway).call("sitfis.protocolo", contribuinte=CLIENT_CNPJ)

    assert gateway.services() == ["SOLICITARPROTOCOLO91"]


def test_the_defaults_apply_when_the_office_has_no_identity_row(
    organization: Organization,
) -> None:
    gateway = Gateway()
    governed = _governed(organization, gateway, check=False)

    for _ in range(3):
        governed.call("pgdasd.declaracoes", contribuinte=CLIENT_CNPJ)

    assert not OfficeSerproIdentity.objects.exists()
    assert IntegraCall.objects.count() == 3
