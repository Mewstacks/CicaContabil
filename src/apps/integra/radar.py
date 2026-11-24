"""Fiscal radar from the update events of the Integra Contador (T10.5).

EVENTOSATUALIZACAO is free (/Monitorar) and says whether something changed for a company since
the last look: E0301 (DCTFWeb), E0601 (Caixa Postal) and E0701 (Pagamentos). A request goes for up
to 1000 CNPJs; its answer is collected after the wait the gateway announces and only once
(the result is delivered one time). The radar only reads; it never opens a mailbox message and
never calls a paid service. It runs only when `INTEGRA_RADAR_ENABLED` is on (off by default).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Protocol

from django.conf import settings
from django.core.exceptions import ValidationError

from apps.common.cnpj import normalize_cnpj
from apps.hub.models import ClientCompany
from apps.integra.envelope import BatchParty
from apps.integra.models import RadarRequest, RadarSignal
from apps.integra.typed.eventosatualizacao import (
    EVENTO_CAIXA_POSTAL,
    EVENTO_DCTFWEB,
    EVENTO_PAGAMENTOS,
    ObterEventos,
    SolicitarEventos,
    read_eventos,
    read_solicitacao,
)
from apps.organizations.models import Organization

EVENTOS = (EVENTO_DCTFWEB, EVENTO_CAIXA_POSTAL, EVENTO_PAGAMENTOS)
EVENT_LABELS = {
    EVENTO_DCTFWEB: "DCTFWeb",
    EVENTO_CAIXA_POSTAL: "Caixa Postal",
    EVENTO_PAGAMENTOS: "Pagamentos",
}
BATCH_SIZE = BatchParty.MAX_ITEMS


class Access(Protocol):
    def call(
        self, service_key: str, *, contribuinte: str | BatchParty, dados: Any = None
    ) -> dict[str, Any]: ...


def radar_enabled() -> bool:
    return bool(getattr(settings, "INTEGRA_RADAR_ENABLED", False))


def _digits(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9]", "", value).upper()


def _eligible(organization: Organization) -> dict[str, ClientCompany]:
    """Active companies of the office with a valid CNPJ, by CNPJ without mask."""

    companies = {}
    for company in ClientCompany.objects.filter(organization=organization, active=True):
        digits = _digits(company.cnpj_masked)
        try:
            normalize_cnpj(digits)
        except ValidationError:
            continue
        companies[digits] = company
    return companies


def request_events(
    access: Access, organization: Organization, *, now: datetime
) -> list[RadarRequest]:
    cnpjs = sorted(_eligible(organization))
    if not cnpjs:
        return []
    created = []
    for evento in EVENTOS:
        pending = RadarRequest.objects.filter(
            organization=organization,
            evento=evento,
            state=RadarRequest.State.REQUESTED,
            expires_at__gt=now,
        )
        if pending.exists():
            continue
        for start in range(0, len(cnpjs), BATCH_SIZE):
            batch = tuple(cnpjs[start : start + BATCH_SIZE])
            payload = access.call(
                "eventosatualizacao.solicitar_pj",
                contribuinte=BatchParty(batch, 4),
                dados=SolicitarEventos(evento=evento).to_dados(),
            )
            ticket = read_solicitacao(payload)
            created.append(
                RadarRequest.objects.create(
                    organization=organization,
                    evento=evento,
                    protocolo=ticket.protocolo,
                    ready_at=now + timedelta(milliseconds=ticket.tempo_espera_medio_ms),
                    expires_at=now + timedelta(minutes=ticket.tempo_limite_min),
                    companies_count=len(batch),
                )
            )
    return created


def collect_events(access: Access, organization: Organization, *, now: datetime) -> int:
    """Collect every request whose wait is over; return how many were collected."""

    open_requests = list(
        RadarRequest.objects.filter(
            organization=organization, state=RadarRequest.State.REQUESTED
        ).order_by("created_at")
    )
    if not open_requests:
        return 0
    companies = _eligible(organization)
    collected = 0
    for item in open_requests:
        if item.expires_at <= now:
            item.state = RadarRequest.State.EXPIRED
            item.save(update_fields=["state", "updated_at"])
            continue
        if item.ready_at > now:
            continue
        payload = access.call(
            "eventosatualizacao.obter_pj",
            contribuinte=BatchParty((), 4),
            dados=ObterEventos(protocolo=item.protocolo, evento=item.evento).to_dados(),
        )
        result = read_eventos(payload)
        if result.em_processamento:
            continue
        for row in result.linhas:
            company = companies.get(_digits(row.ni))
            if company is None:
                continue
            signal, _ = RadarSignal.objects.get_or_create(
                company=company,
                evento=item.evento,
                defaults={"organization": organization, "observed_at": now},
            )
            signal.sem_procuracao = row.sem_procuracao
            if row.data is not None:
                signal.event_date = row.data
            signal.observed_at = now
            signal.save()
        item.state = RadarRequest.State.COLLECTED
        item.save(update_fields=["state", "updated_at"])
        collected += 1
    return collected


@dataclass
class RadarRow:
    company: ClientCompany
    events: dict[str, RadarSignal] = field(default_factory=dict)


def summary_for(organization: Organization) -> list[RadarRow]:
    """Companies of this office that have at least one signal, by name."""

    rows: dict[Any, RadarRow] = {}
    signals = RadarSignal.objects.filter(organization=organization).select_related("company")
    for signal in signals.order_by("company__name", "evento"):
        row = rows.setdefault(signal.company_id, RadarRow(signal.company))
        row.events[signal.evento] = signal
    return list(rows.values())
