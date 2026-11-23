"""Pedido de procuração ao cliente, por e-mail e por clique (D-304, D-305).

Nunca é automático: só sai quando uma pessoa do escritório pede. Cada pedido fica
registrado; quem recebeu há menos de três dias é pulado; um clique manda no máximo 80.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.audit.services import record_event
from apps.hub.models import ClientCompany, NfseProcuracaoRequest
from apps.hub.office_certificate import office_cnpj
from apps.organizations.models import Organization
from apps.platform.notifications import TransactionalEmailError, send_transactional_email

COOLDOWN = timedelta(days=3)
BATCH_LIMIT = 80
# Sends are synchronous inside a web request; stop well before the gunicorn timeout and
# leave the rest for the next click.
TIME_BUDGET_SECONDS = 20.0
PORTAL_URL = "https://servicos.receitafederal.gov.br/"


@dataclass
class RequestOutcome:
    sent: int = 0
    recent: int = 0
    no_email: int = 0
    failed: int = 0
    over_limit: int = 0
    stopped: str = ""


def mask_email(address: str) -> str:
    local, _, domain = address.partition("@")
    return f"{local[:1]}***@{domain}" if domain else "***"


def mask_cnpj(cnpj: str) -> str:
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"


def request_message(
    *, office_name: str, office_cnpj_value: str, company_name: str
) -> tuple[str, str]:
    subject = f"Procuração para {office_name} acessar as NFS-e"
    body = (
        f"{office_name} (CNPJ {mask_cnpj(office_cnpj_value)}) precisa de uma procuração "
        f"eletrônica para consultar as notas fiscais de serviço (NFS-e) de {company_name}.\n\n"
        "Quem cadastra: o responsável legal da empresa, no Portal de Serviços da Receita "
        f"Federal ({PORTAL_URL}).\n\n"
        "Dados da procuração:\n"
        f"- Outorgado: CNPJ {mask_cnpj(office_cnpj_value)}\n"
        "- Serviço: NFS-e - Nota Fiscal de Serviço Eletrônica\n"
        "- Validade: a critério da empresa\n\n"
        "A procuração pode levar até 24 horas para valer. Não é preciso responder este e-mail."
    )
    return subject, body


def request_procuracao(
    *,
    organization: Organization,
    companies: Iterable[ClientCompany],
    actor: Any = None,
    request: Any = None,
    clock: Callable[[], float] = time.monotonic,
) -> RequestOutcome:
    outcome = RequestOutcome()
    started = clock()
    cnpj = office_cnpj(organization)
    if cnpj is None:
        outcome.stopped = "Informe o CNPJ do escritório antes de pedir procurações."
        return outcome
    now = timezone.now()
    recent_ids = set(
        NfseProcuracaoRequest.objects.filter(
            organization=organization,
            status=NfseProcuracaoRequest.Status.SENT,
            sent_at__gte=now - COOLDOWN,
        ).values_list("company_id", flat=True)
    )
    for company in companies:
        if company.organization_id != organization.pk:
            continue
        if company.pk in recent_ids:
            outcome.recent += 1
            continue
        address = company.contact_email.strip()
        if not address:
            outcome.no_email += 1
            continue
        if outcome.sent >= BATCH_LIMIT or clock() - started > TIME_BUDGET_SECONDS:
            outcome.over_limit += 1
            continue
        subject, body = request_message(
            office_name=organization.name,
            office_cnpj_value=cnpj,
            company_name=company.name,
        )
        row = NfseProcuracaoRequest(
            organization=organization,
            company=company,
            requested_by=actor if getattr(actor, "is_authenticated", False) else None,
            recipient_masked=mask_email(address),
        )
        try:
            send_transactional_email(
                subject=subject, message=body, from_email=None, recipient_list=[address]
            )
        except TransactionalEmailError as exc:
            row.status = NfseProcuracaoRequest.Status.FAILED
            row.error = str(exc)[:240]
            row.save()
            outcome.failed += 1
            outcome.stopped = "O e-mail não saiu. Confira a configuração de envio."
            break
        row.save()
        outcome.sent += 1
    record_event(
        action="hub.nfse.procuracao_requested",
        actor=actor,
        organization=organization,
        target=organization,
        request=request,
        metadata={
            "sent": outcome.sent,
            "recent": outcome.recent,
            "no_email": outcome.no_email,
            "failed": outcome.failed,
        },
    )
    return outcome
