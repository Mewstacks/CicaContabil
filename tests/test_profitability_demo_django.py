"""Dados fictícios do Lucrums: só em demonstração, repetíveis e com telas que abrem."""

from __future__ import annotations

from datetime import date

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany, ProductModule
from apps.organizations.models import Membership, Organization
from apps.profitability.demo import populate_demo
from apps.profitability.models import (
    AtribuicaoDepartamento,
    ClienteCompetenciaMetrics,
    Colaborador,
    Mensalidade,
    RegistroHoras,
)
from apps.profitability.valor import valor_da_competencia

pytestmark = pytest.mark.django_db

HOJE = date(2026, 11, 25)


@pytest.fixture
def demo() -> Organization:
    office = Organization.objects.create(name="Demo", slug="demo-x", is_demo=True)
    ProductModule.objects.create(
        organization=office, code=ProductModule.Code.PROFITABILITY, enabled=True
    )
    for nome in ("Padaria Central", "Oficina Sul", "Clínica Norte"):
        ClientCompany.objects.create(organization=office, name=nome)
    return office


def test_recusa_escritorio_real() -> None:
    real = Organization.objects.create(name="Real", slug="real-x")
    with pytest.raises(ValueError):
        populate_demo(real, today=HOJE)
    assert not Colaborador.objects.filter(organization=real).exists()


def test_preenche_equipe_mensalidades_horas_e_metricas(demo: Organization) -> None:
    resumo = populate_demo(demo, today=HOJE)

    assert resumo["empresas"] == 3 and resumo["colaboradores"] == 8
    assert Mensalidade.objects.filter(organization=demo).count() == 3 * 6
    assert AtribuicaoDepartamento.objects.filter(organization=demo).exists()
    assert ClienteCompetenciaMetrics.objects.filter(
        organization=demo, competencia="2026-11"
    ).exists()


def test_repetir_nao_duplica(demo: Organization) -> None:
    populate_demo(demo, today=HOJE)
    antes = (
        Colaborador.objects.count(),
        Mensalidade.objects.count(),
        RegistroHoras.objects.count(),
        AtribuicaoDepartamento.objects.count(),
    )

    populate_demo(demo, today=HOJE)

    assert antes == (
        Colaborador.objects.count(),
        Mensalidade.objects.count(),
        RegistroHoras.objects.count(),
        AtribuicaoDepartamento.objects.count(),
    )


def test_valor_por_colaborador_fecha_com_a_receita(demo: Organization) -> None:
    populate_demo(demo, today=HOJE)

    valor = valor_da_competencia(demo, "2026-11")

    assert valor.linhas
    atribuido = sum(linha.valor for linha in valor.linhas)
    assert abs(atribuido + valor.sem_dono - valor.receita) < 1


def test_telas_do_modulo_abrem_com_dados(demo: Organization) -> None:
    populate_demo(demo, today=HOJE)
    dono = User.objects.create_user(email="dono@example.com", password="uma-senha-longa")
    Membership.objects.create(organization=demo, user=dono, role=Membership.Role.OWNER)
    cliente = Client()
    cliente.force_login(dono)
    sessao = cliente.session
    sessao["hub_organization_id"] = str(demo.id)
    sessao.save()

    for nome in ("overview", "collaborators", "value", "hours", "analyses"):
        resposta = cliente.get(reverse(f"profitability:{nome}"))
        assert resposta.status_code == 200, nome
    assert "Marina Castelo Branco" in cliente.get(reverse("profitability:value")).content.decode()


def test_comando_preenche_lucrums_e_contraprova_e_recusa_escritorio_real(
    demo: Organization,
) -> None:
    from django.core.management import CommandError, call_command

    from apps.crosscheck.models import CrosscheckRun

    dono = User.objects.create_user(email="dono2@example.com", password="uma-senha-longa")
    Membership.objects.create(organization=demo, user=dono, role=Membership.Role.OWNER)
    demo.slug = "escritorio-demo"
    demo.save(update_fields=["slug"])

    call_command("seed_demo_modules", "--slug", "escritorio-demo")

    assert Colaborador.objects.filter(organization=demo).count() == 8
    assert CrosscheckRun.objects.filter(organization=demo).exists()

    antes = CrosscheckRun.objects.filter(organization=demo).count()
    call_command("seed_demo_modules", "--slug", "escritorio-demo")
    assert CrosscheckRun.objects.filter(organization=demo).count() == antes

    Organization.objects.create(name="Real", slug="real-y")
    with pytest.raises(CommandError):
        call_command("seed_demo_modules", "--slug", "real-y")
