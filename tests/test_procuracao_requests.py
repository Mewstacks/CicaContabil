"""Pedido de procuração por e-mail (D-304/D-305): por clique, com intervalo e sem segredo."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core import mail
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.hub import procuracao_requests
from apps.hub.models import ClientCompany, NfseProcuracaoRequest, OfficeProfile
from apps.hub.procuracao_requests import request_procuracao
from apps.organizations.models import Organization
from apps.platform.notifications import TransactionalEmailError
from test_nfse_procuracao import CLIENT_CNPJ, OFFICE_CNPJ


def office(cnpj: str = OFFICE_CNPJ) -> Organization:
    organization = Organization.objects.create(name="Escritório Pedido", slug="pedido")
    OfficeProfile.objects.create(
        organization=organization,
        cnpj=cnpj,
        nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
    )
    return organization


def company(organization: Organization, name: str, email: str = "") -> ClientCompany:
    return ClientCompany.objects.create(
        organization=organization, name=name, cnpj_masked=CLIENT_CNPJ, contact_email=email
    )


@pytest.mark.django_db
def test_each_company_with_an_address_gets_one_clear_message() -> None:
    organization = office()
    target = company(organization, "Padaria Central", "dono@padaria.example")

    outcome = request_procuracao(organization=organization, companies=[target])

    assert outcome.sent == 1
    [message] = mail.outbox
    assert message.to == ["dono@padaria.example"]
    assert "Escritório Pedido" in message.subject
    assert "Padaria Central" in message.body
    assert "19.131.243/0001-97" in message.body
    assert "NFS-e - Nota Fiscal de Serviço Eletrônica" in message.body
    assert "servicos.receitafederal.gov.br" in message.body
    row = NfseProcuracaoRequest.objects.get()
    assert row.status == NfseProcuracaoRequest.Status.SENT
    assert row.recipient_masked == "d***@padaria.example"
    assert "dono@padaria.example" not in row.recipient_masked


@pytest.mark.django_db
def test_the_same_company_is_not_asked_again_inside_three_days() -> None:
    organization = office()
    target = company(organization, "Padaria", "dono@padaria.example")
    request_procuracao(organization=organization, companies=[target])

    second = request_procuracao(organization=organization, companies=[target])

    assert (second.sent, second.recent) == (0, 1)
    assert len(mail.outbox) == 1
    NfseProcuracaoRequest.objects.update(sent_at=timezone.now() - timedelta(days=3, minutes=1))
    third = request_procuracao(organization=organization, companies=[target])
    assert third.sent == 1 and len(mail.outbox) == 2


@pytest.mark.django_db
def test_a_company_without_address_is_counted_not_mailed() -> None:
    organization = office()

    outcome = request_procuracao(
        organization=organization, companies=[company(organization, "Sem e-mail")]
    )

    assert (outcome.sent, outcome.no_email) == (0, 1)
    assert mail.outbox == []


@pytest.mark.django_db
def test_a_click_sends_at_most_the_batch_limit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(procuracao_requests, "BATCH_LIMIT", 2)
    organization = office()
    companies = [company(organization, f"Cliente {n}", f"c{n}@example.test") for n in range(4)]

    outcome = request_procuracao(organization=organization, companies=companies)

    assert (outcome.sent, outcome.over_limit) == (2, 2)
    assert len(mail.outbox) == 2


@pytest.mark.django_db
def test_a_delivery_failure_stops_the_batch_and_says_so() -> None:
    organization = office()
    companies = [company(organization, f"Cliente {n}", f"c{n}@example.test") for n in range(3)]

    with patch(
        "apps.hub.procuracao_requests.send_transactional_email",
        side_effect=TransactionalEmailError("O servidor de e-mail não respondeu."),
    ) as send:
        outcome = request_procuracao(organization=organization, companies=companies)

    assert send.call_count == 1
    assert (outcome.sent, outcome.failed) == (0, 1)
    assert "e-mail não saiu" in outcome.stopped
    row = NfseProcuracaoRequest.objects.get()
    assert row.status == NfseProcuracaoRequest.Status.FAILED


@pytest.mark.django_db
def test_without_the_office_cnpj_nothing_is_sent() -> None:
    organization = Organization.objects.create(name="Sem CNPJ", slug="sem-cnpj")
    OfficeProfile.objects.create(organization=organization)

    outcome = request_procuracao(
        organization=organization, companies=[company(organization, "X", "x@example.test")]
    )

    assert outcome.sent == 0 and "CNPJ do escritório" in outcome.stopped
    assert mail.outbox == []


@pytest.mark.django_db
def test_a_company_of_another_office_is_never_mailed() -> None:
    organization = office()
    stranger = Organization.objects.create(name="Outro", slug="outro")
    foreign = company(stranger, "De outro escritório", "outro@example.test")

    outcome = request_procuracao(organization=organization, companies=[foreign])

    assert outcome.sent == 0 and mail.outbox == []


@pytest.mark.django_db
def test_the_batch_is_audited_without_addresses() -> None:
    organization = office()
    request_procuracao(
        organization=organization,
        companies=[company(organization, "Padaria", "dono@padaria.example")],
    )

    event = AuditEvent.objects.get(action="hub.nfse.procuracao_requested")
    assert event.metadata["sent"] == 1
    assert "padaria" not in str(event.metadata).lower()


@pytest.mark.django_db
def test_a_slow_batch_stops_before_the_web_timeout_and_leaves_the_rest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization = office()
    companies = [company(organization, f"Cliente {n}", f"c{n}@example.test") for n in range(4)]
    ticks = iter([0.0, 1.0, 2.0, 25.0, 26.0, 27.0, 28.0, 29.0, 30.0])

    outcome = request_procuracao(
        organization=organization, companies=companies, clock=lambda: next(ticks)
    )

    assert outcome.sent == 2 and outcome.over_limit == 2
    assert len(mail.outbox) == 2
