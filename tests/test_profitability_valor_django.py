"""Valor por colaborador: montagem da entrada, recusas e honestidade da tela."""

from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import Client
from django.urls import reverse

from apps.accounts.models import User
from apps.hub.models import ClientCompany, CompanyAreaResponsible, ProductModule
from apps.organizations.models import Membership, Organization
from apps.profitability.models import (
    AtribuicaoDepartamento,
    Colaborador,
    Competencia,
    Departamento,
    Mensalidade,
    SalarioColaborador,
)
from apps.profitability.valor import valor_da_competencia

pytestmark = pytest.mark.django_db

D = Decimal
COMPETENCIA = "2026-09"


@pytest.fixture
def office() -> Organization:
    escritorio = Organization.objects.create(name="Escritório", slug="escritorio")
    ProductModule.objects.create(
        organization=escritorio, code=ProductModule.Code.PROFITABILITY, enabled=True
    )
    Competencia.objects.create(
        organization=escritorio,
        competencia=COMPETENCIA,
        inicio="2026-09-01",
        fim="2026-09-30",
        is_atual=True,
    )
    return escritorio


def _pessoa(office: Organization, codigo: str, depto: str, salario: str = "3000") -> Colaborador:
    pessoa = Colaborador.objects.create(
        organization=office, codigo=codigo, nome=f"Pessoa {codigo}", departamento=depto
    )
    SalarioColaborador.objects.create(
        organization=office,
        colaborador=pessoa,
        competencia=COMPETENCIA,
        salario=D(salario),
        fonte=Colaborador.Origem.MANUAL,
    )
    return pessoa


def _empresa(office: Organization, nome: str, mensalidade: str) -> ClientCompany:
    empresa = ClientCompany.objects.create(organization=office, name=nome)
    Mensalidade.objects.create(
        organization=office,
        empresa=empresa,
        competencia=COMPETENCIA,
        valor=D(mensalidade),
        fonte=Colaborador.Origem.MANUAL,
    )
    return empresa


def _atribuir(
    office: Organization, empresa: ClientCompany, depto: str, pessoa: Colaborador
) -> None:
    AtribuicaoDepartamento.objects.create(
        organization=office, empresa=empresa, departamento=depto, colaborador=pessoa
    )


def test_valor_fecha_com_a_receita_e_separa_o_que_nao_tem_dono(office: Organization) -> None:
    fiscal = _pessoa(office, "F1", Departamento.FISCAL)
    contabil = _pessoa(office, "C1", Departamento.CONTABIL)
    a = _empresa(office, "A", "1000")
    b = _empresa(office, "B", "600")
    _empresa(office, "Sem dono", "400")
    _atribuir(office, a, Departamento.FISCAL, fiscal)
    _atribuir(office, a, Departamento.CONTABIL, contabil)
    _atribuir(office, b, Departamento.FISCAL, fiscal)

    resultado = valor_da_competencia(office, COMPETENCIA)

    por_codigo = {linha.colaborador.codigo: linha for linha in resultado.linhas}
    # Capacidades iguais: A divide 500/500, B é só fiscal.
    assert por_codigo["F1"].valor == D(1100)
    assert por_codigo["C1"].valor == D(500)
    assert resultado.sem_dono == D(400)
    assert [item.empresa.name for item in resultado.sem_responsavel] == ["Sem dono"]
    assert sum(linha.valor for linha in resultado.linhas) + resultado.sem_dono == resultado.receita


def test_responsavel_de_area_da_carteira_vale_quando_nao_ha_atribuicao(
    office: Organization,
) -> None:
    usuario = User.objects.create_user(email="ana@example.com", password="uma-senha-longa")
    pessoa = _pessoa(office, "F1", Departamento.FISCAL)
    pessoa.usuario = usuario
    pessoa.save(update_fields=["usuario"])
    empresa = _empresa(office, "A", "800")
    CompanyAreaResponsible.objects.create(
        organization=office, company=empresa, area="fiscal", user=usuario
    )

    resultado = valor_da_competencia(office, COMPETENCIA)

    assert [(linha.colaborador.codigo, linha.valor) for linha in resultado.linhas] == [
        ("F1", D(800))
    ]


def test_atribuicao_explicita_vence_o_responsavel_de_area(office: Organization) -> None:
    usuario = User.objects.create_user(email="ana@example.com", password="uma-senha-longa")
    ana = _pessoa(office, "F1", Departamento.FISCAL)
    ana.usuario = usuario
    ana.save(update_fields=["usuario"])
    bia = _pessoa(office, "F2", Departamento.FISCAL)
    empresa = _empresa(office, "A", "800")
    CompanyAreaResponsible.objects.create(
        organization=office, company=empresa, area="fiscal", user=usuario
    )
    _atribuir(office, empresa, Departamento.FISCAL, bia)

    resultado = valor_da_competencia(office, COMPETENCIA)

    assert [(linha.colaborador.codigo, linha.valor) for linha in resultado.linhas] == [
        ("F2", D(800))
    ]


def test_pessoa_sem_salario_aparece_sem_inventar_custo(office: Organization) -> None:
    pessoa = Colaborador.objects.create(
        organization=office, codigo="X", nome="Sem folha", departamento=Departamento.FISCAL
    )
    empresa = _empresa(office, "A", "500")
    _atribuir(office, empresa, Departamento.FISCAL, pessoa)

    resultado = valor_da_competencia(office, COMPETENCIA)

    linha = resultado.linhas[0]
    assert linha.valor == D(500)
    assert linha.custo is None and linha.resultado is None and linha.margem is None
    assert resultado.sem_salario == 1


def test_pessoa_sem_departamento_fica_de_fora_do_peso_e_e_listada(office: Organization) -> None:
    _pessoa(office, "F1", Departamento.FISCAL)
    solta = Colaborador.objects.create(organization=office, codigo="S", nome="Solta")

    resultado = valor_da_competencia(office, COMPETENCIA)

    assert [item.departamento for item in resultado.departamentos] == [Departamento.FISCAL]
    assert resultado.sem_departamento == [solta]


def _logar(office: Organization, papel: str) -> Client:
    usuario = User.objects.create_user(email=f"{papel}@example.com", password="uma-senha-longa")
    Membership.objects.create(organization=office, user=usuario, role=papel)
    cliente = Client()
    cliente.force_login(usuario)
    sessao = cliente.session
    sessao["hub_organization_id"] = str(office.id)
    sessao.save()
    return cliente


def test_tela_abre_para_dono_e_mostra_o_valor(office: Organization) -> None:
    pessoa = _pessoa(office, "F1", Departamento.FISCAL)
    _atribuir(office, _empresa(office, "A", "1000"), Departamento.FISCAL, pessoa)

    resposta = _logar(office, Membership.Role.OWNER).get(reverse("profitability:value"))

    assert resposta.status_code == 200
    html = resposta.content.decode()
    assert "Pessoa F1" in html
    assert "1.000,00" in html


def test_tela_recusa_quem_nao_e_administrador(office: Organization) -> None:
    resposta = _logar(office, Membership.Role.OPERATOR).get(reverse("profitability:value"))

    assert resposta.status_code != 200
    assert "Pessoa" not in resposta.content.decode()


def test_atribuir_grava_e_a_empresa_sai_da_lista_sem_responsavel(office: Organization) -> None:
    pessoa = _pessoa(office, "F1", Departamento.FISCAL)
    empresa = _empresa(office, "A", "700")
    cliente = _logar(office, Membership.Role.OWNER)

    resposta = cliente.post(
        reverse("profitability:value"),
        {
            "acao": "atribuir",
            "empresa": str(empresa.id),
            "departamento": Departamento.FISCAL,
            "colaborador": str(pessoa.id),
        },
    )

    assert resposta.status_code == 302
    assert AtribuicaoDepartamento.objects.filter(empresa=empresa, colaborador=pessoa).exists()
    assert valor_da_competencia(office, COMPETENCIA).sem_responsavel == []


def test_definir_departamento_so_aceita_valor_conhecido(office: Organization) -> None:
    pessoa = Colaborador.objects.create(organization=office, codigo="S", nome="Solta")
    cliente = _logar(office, Membership.Role.OWNER)

    cliente.post(
        reverse("profitability:value"),
        {"acao": "departamento", "colaborador": str(pessoa.id), "departamento": "inventado"},
    )
    pessoa.refresh_from_db()
    assert pessoa.departamento == ""

    cliente.post(
        reverse("profitability:value"),
        {"acao": "departamento", "colaborador": str(pessoa.id), "departamento": "fiscal"},
    )
    pessoa.refresh_from_db()
    assert pessoa.departamento == Departamento.FISCAL
