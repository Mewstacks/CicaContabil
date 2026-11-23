"""T10.5: fiscal radar from the free update events (E0301, E0601, E0701). Fake access only."""

from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from typing import Any

import pytest

from apps.hub.models import ClientCompany
from apps.integra.envelope import BatchParty
from apps.integra.models import RadarRequest, RadarSignal
from apps.integra.radar import (
    EVENTOS,
    collect_events,
    radar_enabled,
    request_events,
    summary_for,
)
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db

BRT = timezone(timedelta(hours=-3))
NOW = datetime(2026, 11, 23, 10, 0, tzinfo=BRT)
A, B, C = "11222333000181", "11444777000161", "12ABC34501DE35"
PROTOCOL = "q90n3455-fa91-419c-c0ad-a4ms50215acl"


class FakeAccess:
    def __init__(self, matrix: list[list[str]] | None = None, status: int = 200) -> None:
        self.calls: list[dict[str, Any]] = []
        self.matrix = matrix or []
        self.status = status

    def call(self, key: str, *, contribuinte: Any, dados: Any = None, **_: Any) -> dict[str, Any]:
        self.calls.append({"key": key, "contribuinte": contribuinte, "dados": dados})
        if key.endswith("solicitar_pj"):
            body = {"protocolo": PROTOCOL, "TempoEsperaMedioEmMs": 354, "TempoLimiteEmMin": 5}
            return {"status": 200, "mensagens": [], "dados": json.dumps(body)}
        if self.status == 202:
            return {"status": 202, "mensagens": [], "dados": ""}
        return {"status": 200, "mensagens": [], "dados": json.dumps({"elementos": self.matrix})}


def _company(
    organization: Organization, cnpj: str, name: str, *, active: bool = True
) -> ClientCompany:
    return ClientCompany.objects.create(
        organization=organization, name=name, cnpj_masked=cnpj, active=active
    )


def test_the_radar_is_off_by_default() -> None:
    assert radar_enabled() is False


def test_the_batch_party_carries_cnpjs_in_numero_and_is_empty_on_retrieval() -> None:
    assert BatchParty((A, B)).as_payload() == {"numero": f"{A},{B}", "tipo": 4}
    assert BatchParty(()).as_payload() == {"numero": "", "tipo": 4}
    assert BatchParty(("52998224725",), tipo=3).as_payload()["tipo"] == 3
    for bad in (BatchParty(("123",)), BatchParty((A,), tipo=2), BatchParty((A,) * 1001)):
        with pytest.raises(ValueError):
            bad.as_payload()


def test_requests_are_made_per_event_in_batches_of_active_valid_companies(
    organization: Organization,
) -> None:
    _company(organization, A, "A")
    _company(organization, B, "B")
    _company(organization, C, "Alfa")
    _company(organization, "00000000000000", "Inválida")
    _company(organization, "11111111111111", "Inativa", active=False)
    access = FakeAccess()

    requests = request_events(access, organization, now=NOW)

    assert len(requests) == len(EVENTOS) == 3
    assert [call["dados"] for call in access.calls] == [{"evento": e} for e in EVENTOS]
    for call in access.calls:
        assert call["key"] == "eventosatualizacao.solicitar_pj"
        assert set(call["contribuinte"].numeros) == {A, B, C}
    first = RadarRequest.objects.filter(evento="E0301").get()
    assert first.protocolo == PROTOCOL and first.state == RadarRequest.State.REQUESTED
    assert first.ready_at == NOW + timedelta(milliseconds=354)
    assert first.expires_at == NOW + timedelta(minutes=5)


def test_nothing_is_requested_for_an_office_without_companies(organization: Organization) -> None:
    access = FakeAccess()

    assert request_events(access, organization, now=NOW) == []
    assert access.calls == []


def test_a_pending_request_is_not_asked_again_before_it_expires(organization: Organization) -> None:
    _company(organization, A, "A")
    access = FakeAccess()
    request_events(access, organization, now=NOW)
    access.calls.clear()

    assert request_events(access, organization, now=NOW + timedelta(minutes=1)) == []
    assert access.calls == []


def test_the_events_are_collected_into_one_signal_per_company_and_event(
    organization: Organization,
) -> None:
    company_a = _company(organization, A, "A")
    company_b = _company(organization, B, "B")
    request_events(FakeAccess(), organization, now=NOW)
    matrix = [[A, "261110"], [B, "x"], ["99999999999999", "261111"]]
    access = FakeAccess(matrix)

    collect_events(access, organization, now=NOW + timedelta(seconds=1))

    signal = RadarSignal.objects.get(company=company_a, evento="E0301")
    assert signal.event_date == date(2026, 11, 10) and not signal.sem_procuracao
    denied = RadarSignal.objects.get(company=company_b, evento="E0301")
    assert denied.event_date is None and denied.sem_procuracao
    assert RadarSignal.objects.filter(evento="E0301").count() == 2  # the stranger is ignored
    assert not RadarRequest.objects.filter(state=RadarRequest.State.REQUESTED).exists()
    assert all(
        call["contribuinte"].numeros == () and call["dados"]["protocolo"] == PROTOCOL
        for call in access.calls
    )


def test_a_request_still_in_process_is_left_for_the_next_tick(organization: Organization) -> None:
    _company(organization, A, "A")
    request_events(FakeAccess(), organization, now=NOW)

    collect_events(FakeAccess(status=202), organization, now=NOW + timedelta(seconds=1))

    assert RadarRequest.objects.filter(state=RadarRequest.State.REQUESTED).count() == 3
    assert not RadarSignal.objects.exists()


def test_a_request_is_not_collected_before_the_wait_and_expires_after_the_limit(
    organization: Organization,
) -> None:
    _company(organization, A, "A")
    request_events(FakeAccess(), organization, now=NOW)
    early = FakeAccess([[A, "261110"]])

    collect_events(early, organization, now=NOW)
    assert early.calls == []

    late = FakeAccess([[A, "261110"]])
    collect_events(late, organization, now=NOW + timedelta(minutes=6))
    assert late.calls == []
    assert RadarRequest.objects.filter(state=RadarRequest.State.EXPIRED).count() == 3


def test_a_later_event_updates_the_signal_instead_of_adding_one(organization: Organization) -> None:
    company = _company(organization, A, "A")
    for matrix, offset in (([[A, "261110"]], 0), ([[A, "261120"]], 10)):
        moment = NOW + timedelta(minutes=offset)
        request_events(FakeAccess(), organization, now=moment)
        collect_events(FakeAccess(matrix), organization, now=moment + timedelta(seconds=1))

    signals = RadarSignal.objects.filter(company=company, evento="E0301")
    assert signals.count() == 1 and signals.get().event_date == date(2026, 11, 20)


def test_the_summary_is_scoped_to_the_office(organization: Organization) -> None:
    other = Organization.objects.create(name="Outro", slug="outro")
    mine = _company(organization, A, "A")
    theirs = _company(other, B, "B")
    for company, evento in ((mine, "E0301"), (mine, "E0601"), (theirs, "E0301")):
        RadarSignal.objects.create(
            organization=company.organization, company=company, evento=evento,
            event_date=date(2026, 11, 10), sem_procuracao=False, observed_at=NOW,
        )

    rows = summary_for(organization)

    assert [row.company.pk for row in rows] == [mine.pk]
    assert set(rows[0].events) == {"E0301", "E0601"}
    assert rows[0].events["E0301"].event_date == date(2026, 11, 10)
