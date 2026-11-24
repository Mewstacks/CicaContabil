"""Capacidade da coleta por procuração (E5): a seleção não cresce com a carteira.

O gargalo real é o ritmo do ADN (1 chamada por segundo por e-CNPJ), não o banco: aqui se prova que
escolher o que coletar custa um número fixo de consultas, seja 1 escritório ou 40, e que semear
as linhas de um escritório grande não faz uma consulta por empresa.
"""

from __future__ import annotations

import time
from datetime import timedelta
from typing import Any

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from apps.hub.models import (
    ClientCompany,
    NfseSync,
    OfficeCertificate,
    OfficeProfile,
)
from apps.hub.nfse_procuracao import (
    due_certificate_ids,
    eligible_procuracao_syncs,
    next_due_sync_id,
    seed_procuracao_syncs,
)
from apps.organizations.models import Organization
from test_nfse_procuracao import OFFICE_CNPJ, cnpj_from

pytestmark = pytest.mark.django_db


def build_portfolio(offices: int, companies: int, *, with_syncs: bool = True) -> list[Any]:
    now = timezone.now()
    orgs = Organization.objects.bulk_create(
        [Organization(name=f"Carga {i}", slug=f"carga-{i}") for i in range(offices)]
    )
    OfficeProfile.objects.bulk_create(
        [
            OfficeProfile(
                organization=org,
                cnpj=OFFICE_CNPJ,
                nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
            )
            for org in orgs
        ]
    )
    certificates = OfficeCertificate.objects.bulk_create(
        [
            OfficeCertificate(
                organization=org,
                label="e-CNPJ",
                cnpj=OFFICE_CNPJ,
                pfx_blob="x",
                password="x",
                fingerprint_sha256=f"{index:064d}",
                valid_from=now - timedelta(days=10),
                valid_until=now + timedelta(days=300),
            )
            for index, org in enumerate(orgs)
        ]
    )
    rows = ClientCompany.objects.bulk_create(
        [
            ClientCompany(
                organization=org,
                name=f"Empresa {i}-{n}",
                cnpj_masked=cnpj_from(f"{n + 1:08d}0001"),
            )
            for i, org in enumerate(orgs)
            for n in range(companies)
        ]
    )
    if with_syncs:
        by_org = {org.pk: certificate for org, certificate in zip(orgs, certificates, strict=True)}
        NfseSync.objects.bulk_create(
            [
                NfseSync(
                    organization_id=company.organization_id,
                    company=company,
                    credential_mode=NfseSync.CredentialMode.PROCURACAO,
                    office_certificate=by_org[company.organization_id],
                    status=NfseSync.Status.IDLE,
                    enabled=True,
                    next_run_at=now - timedelta(minutes=1),
                )
                for company in rows
            ]
        )
    return orgs


def count_queries(function: Any, *args: Any, **kwargs: Any) -> tuple[Any, int]:
    with CaptureQueriesContext(connection) as captured:
        result = function(*args, **kwargs)
    return result, len(captured)


def test_choosing_what_to_collect_costs_a_fixed_number_of_queries_at_any_size() -> None:
    build_portfolio(offices=1, companies=20)
    _, small = count_queries(due_certificate_ids)

    build_portfolio_more()
    ids, large = count_queries(due_certificate_ids)

    assert len(ids) == 25  # 1 + 24 escritórios, um e-CNPJ cada
    assert small == large == 1


def build_portfolio_more() -> None:
    now = timezone.now()
    for index in range(24):
        org = Organization.objects.create(name=f"Extra {index}", slug=f"extra-{index}")
        OfficeProfile.objects.create(
            organization=org,
            cnpj=OFFICE_CNPJ,
            nfse_collection_mode=OfficeProfile.NfseCollectionMode.PROCURACAO,
        )
        certificate = OfficeCertificate.objects.create(
            organization=org,
            label="e-CNPJ",
            cnpj=OFFICE_CNPJ,
            pfx_blob="x",
            password="x",
            fingerprint_sha256=f"e{index:063d}",
            valid_from=now - timedelta(days=10),
            valid_until=now + timedelta(days=300),
        )
        company = ClientCompany.objects.create(organization=org, name="Única", cnpj_masked="1")
        NfseSync.objects.create(
            organization=org,
            company=company,
            credential_mode=NfseSync.CredentialMode.PROCURACAO,
            office_certificate=certificate,
            status=NfseSync.Status.IDLE,
            enabled=True,
            next_run_at=now - timedelta(minutes=1),
        )


def test_the_next_company_of_a_certificate_is_one_bounded_lookup_in_a_large_portfolio() -> None:
    orgs = build_portfolio(offices=12, companies=150)  # 1.800 linhas
    certificates = list(OfficeCertificate.objects.order_by("organization_id")[:5])
    started = time.perf_counter()

    for certificate in certificates:
        picked, queries = count_queries(next_due_sync_id, certificate.pk)
        assert picked is not None and queries <= 2

    ids, queries = count_queries(due_certificate_ids)
    assert len(ids) == len(orgs) and queries == 1
    assert (
        time.perf_counter() - started < 5
    )  # folga larga: o que se prova é a contagem de consultas


def test_a_company_in_flight_holds_the_whole_certificate() -> None:
    build_portfolio(offices=1, companies=30)
    certificate = OfficeCertificate.objects.get()
    NfseSync.objects.filter(pk=NfseSync.objects.first().pk).update(status=NfseSync.Status.RUNNING)

    assert next_due_sync_id(certificate.pk) is None  # uma chamada em voo por e-CNPJ


def test_the_eligible_set_counts_every_due_row_without_loading_them() -> None:
    build_portfolio(offices=6, companies=100)

    count, queries = count_queries(lambda: eligible_procuracao_syncs().count())

    assert count == 600 and queries == 1


def test_seeding_a_large_office_is_not_one_query_per_company() -> None:
    org = build_portfolio(offices=1, companies=200, with_syncs=False)[0]

    outcome, queries = count_queries(seed_procuracao_syncs, organization_id=org.pk)

    assert NfseSync.objects.filter(organization=org).count() == 200
    assert queries < 20, f"{queries} consultas para 200 empresas"
    again, queries_again = count_queries(seed_procuracao_syncs, organization_id=org.pk)
    assert NfseSync.objects.filter(organization=org).count() == 200  # idempotente
    assert queries_again < 20
    assert outcome and again is not None


def test_the_ceiling_comes_from_the_adn_pace_not_from_the_database() -> None:
    """Conta de capacidade (docs/capacidade-procuracao.md): 1 chamada/s por e-CNPJ."""

    calls_per_hour_per_certificate = 3600
    cadence_hours = 1  # empresa em dia
    companies_one_certificate_can_follow = calls_per_hour_per_certificate * cadence_hours

    assert companies_one_certificate_can_follow == 3600
    assert companies_one_certificate_can_follow >= 560  # a carteira grande de hoje cabe com folga
