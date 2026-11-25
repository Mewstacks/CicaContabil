"""Conferências fictícias do Contraprova para o escritório de demonstração.

Reaproveita o gerador sintético de `seed_crosscheck` (arquivos SPED/XML montados em
memória, sem dado de cliente), mas sem a trava de DEBUG: a trava aqui é o
escritório ser de demonstração.
"""

from __future__ import annotations

from django.utils import timezone

from apps.accounts.models import User
from apps.crosscheck.management.commands.seed_crosscheck import Seeder, mask
from apps.crosscheck.models import CrosscheckRun
from apps.hub.models import ClientCompany, ProductModule
from apps.organizations.models import Organization


def populate_demo(office: Organization, user: User) -> int:
    """Cria as conferências de exemplo uma vez; devolve quantas criou."""

    if not office.is_demo:
        raise ValueError("Dados fictícios só entram em escritório de demonstração.")
    ProductModule.objects.update_or_create(
        organization=office,
        code=ProductModule.Code.CROSSCHECK,
        defaults={"enabled": True, "enabled_at": timezone.now()},
    )
    if CrosscheckRun.objects.filter(organization=office).exists():
        return 0
    companies = list(ClientCompany.objects.filter(organization=office, active=True)[:3])
    if not companies:
        return 0
    seeder = Seeder(office, user, companies)
    for index, company in enumerate(companies):
        company.cnpj_masked = mask(seeder.cnpjs[index])
        company.save()
    count = len(companies)
    runs = [
        seeder.sped_xml_mixed(0),
        seeder.sped_xml_clean(1 % count),
        seeder.sped_sped(2 % count),
        seeder.icms51(0),
        seeder.uf_dominio(1 % count),
        seeder.failed(2 % count),
        seeder.sped_xml_draft(0),
        *seeder.in_flight(1 % count),
    ]
    return len(runs)
