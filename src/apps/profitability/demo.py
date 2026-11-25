"""Dados fictícios do Lucrums para o escritório de demonstração.

Tudo aqui é sintético e só roda em escritório marcado `is_demo`: nomes inventados,
salários redondos, mensalidades e horas geradas por conta. É repetível — rodar de
novo atualiza os mesmos registros em vez de duplicar — e termina recalculando as
métricas, então todas as telas do módulo (visão geral, colaboradores, valor,
horas, análises) abrem com número.
"""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

from django.db import transaction

from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.profitability.models import (
    AtribuicaoDepartamento,
    Colaborador,
    CompanyErpProfile,
    Competencia,
    Departamento,
    Mensalidade,
    OrigemHoras,
    RegistroHoras,
    SalarioColaborador,
    Segmento,
)
from apps.profitability.services import recompute_competencia

MESES = 6
D = Decimal

# (código, nome, departamento, salário-base)
EQUIPE = (
    ("D-01", "Marina Castelo Branco", Departamento.FISCAL, "5200"),
    ("D-02", "Rafael Tonelli Duarte", Departamento.FISCAL, "4300"),
    ("D-03", "Helena Paixão Vidal", Departamento.CONTABIL, "5600"),
    ("D-04", "Gustavo Menezes Leal", Departamento.CONTABIL, "4100"),
    ("D-05", "Priscila Andrade Souto", Departamento.FOLHA, "4400"),
    ("D-06", "Tiago Moraes Brandão", Departamento.FOLHA, "3600"),
    ("D-07", "Camila Rocha Peixoto", Departamento.SOCIETARIO, "4800"),
    ("D-08", "Otávio Lima Fontana", Departamento.OUTROS, "3400"),
)

SEGMENTOS = ("Comércio", "Serviços", "Indústria")
REGIMES = ("Simples Nacional", "Lucro Presumido", "Lucro Real")
MENSALIDADES = ("1450", "2300", "3200", "1850", "4100", "2750", "980", "3650")
# Quais departamentos atendem cada empresa, por posição na lista (fiscal e
# contábil sempre; folha e societário variam).
ATENDIMENTO = (
    (Departamento.FISCAL, Departamento.CONTABIL, Departamento.FOLHA),
    (Departamento.FISCAL, Departamento.CONTABIL),
    (Departamento.FISCAL, Departamento.CONTABIL, Departamento.FOLHA, Departamento.SOCIETARIO),
    (Departamento.FISCAL, Departamento.CONTABIL),
    (Departamento.FISCAL, Departamento.CONTABIL, Departamento.FOLHA, Departamento.OUTROS),
    (Departamento.FISCAL, Departamento.CONTABIL, Departamento.FOLHA),
    (Departamento.CONTABIL, Departamento.SOCIETARIO),
    (Departamento.FISCAL, Departamento.CONTABIL, Departamento.FOLHA, Departamento.SOCIETARIO),
)
# Horas por mês de cada departamento numa empresa, em minutos.
MINUTOS = {
    Departamento.FISCAL: 420,
    Departamento.CONTABIL: 360,
    Departamento.FOLHA: 300,
    Departamento.SOCIETARIO: 150,
    Departamento.OUTROS: 120,
}


def _competencias(today: date) -> list[str]:
    ano, mes = today.year, today.month
    saida: list[str] = []
    for _ in range(MESES):
        saida.append(f"{ano:04d}-{mes:02d}")
        mes -= 1
        if mes == 0:
            ano, mes = ano - 1, 12
    return list(reversed(saida))


def _limites(competencia: str) -> tuple[date, date]:
    ano, mes = int(competencia[:4]), int(competencia[5:])
    inicio = date(ano, mes, 1)
    proximo = date(ano + (mes == 12), 1 if mes == 12 else mes + 1, 1)
    return inicio, date.fromordinal(proximo.toordinal() - 1)


@transaction.atomic
def populate_demo(office: Organization, *, today: date | None = None) -> dict[str, int]:
    """Preenche o Lucrums do escritório de demonstração. Recusa escritório real."""

    if not office.is_demo:
        raise ValueError("Dados fictícios só entram em escritório de demonstração.")
    today = today or date.today()
    empresas = list(ClientCompany.objects.filter(organization=office, active=True).order_by("name"))
    if not empresas:
        return {"empresas": 0}
    empresas = empresas[: len(MENSALIDADES)]
    competencias = _competencias(today)

    for indice, competencia in enumerate(competencias):
        inicio, fim = _limites(competencia)
        Competencia.objects.update_or_create(
            organization=office,
            competencia=competencia,
            defaults={"inicio": inicio, "fim": fim, "is_atual": indice == len(competencias) - 1},
        )

    segmentos = [
        Segmento.objects.get_or_create(organization=office, nome=nome)[0] for nome in SEGMENTOS
    ]
    for posicao, empresa in enumerate(empresas):
        perfil, _ = CompanyErpProfile.objects.get_or_create(
            organization=office,
            empresa=empresa,
            sistema_origem="dominio",
            defaults={"codi_emp": 9000 + posicao, "papel": ["cliente"]},
        )
        perfil.codi_emp = 9000 + posicao
        perfil.papel = ["cliente"]
        perfil.codigo = f"{9000 + posicao}"
        # Documento sintético e distinto por empresa: sem ele todas contariam como a
        # mesma empresa duplicada e a carteira esconderia as linhas.
        perfil.documento = f"{20 + posicao}.345.678/0001-{90 + posicao}"
        perfil.regime = REGIMES[posicao % len(REGIMES)]
        perfil.segmento = segmentos[posicao % len(segmentos)]
        perfil.margem_alvo = D("0.2000")
        perfil.save()

    pessoas: dict[str, Colaborador] = {}
    for codigo, nome, departamento, base in EQUIPE:
        pessoa, _ = Colaborador.objects.get_or_create(
            organization=office,
            codigo=codigo,
            defaults={"nome": nome, "origem": Colaborador.Origem.MANUAL},
        )
        pessoa.nome = nome
        pessoa.departamento = departamento
        pessoa.beneficios_mensais = D("620")
        pessoa.vt_mensal = D("260")
        pessoa.ativo = True
        pessoa.save()
        pessoas[codigo] = pessoa
        for indice, competencia in enumerate(competencias):
            # Reajuste de 4% no quarto mês, para o histórico mostrar uma mudança.
            salario = D(base) * (D("1.04") if indice >= 3 else D(1))
            SalarioColaborador.objects.update_or_create(
                organization=office,
                colaborador=pessoa,
                competencia=competencia,
                defaults={"salario": salario.quantize(D("0.01")), "fonte": "manual"},
            )

    por_departamento: dict[str, list[Colaborador]] = {}
    for codigo, _nome, departamento, _base in EQUIPE:
        por_departamento.setdefault(departamento, []).append(pessoas[codigo])

    horas = 0
    for posicao, empresa in enumerate(empresas):
        for indice, competencia in enumerate(competencias):
            # A mensalidade sobe um pouco por trimestre; uma empresa fica sem valor num
            # mês, para a tela mostrar a falta em vez de esconder.
            base = D(MENSALIDADES[posicao]) * (D("1.05") if indice >= 3 else D(1))
            Mensalidade.objects.update_or_create(
                organization=office,
                empresa=empresa,
                competencia=competencia,
                defaults={"valor": base.quantize(D("0.01")), "fonte": "manual"},
            )
        for departamento in ATENDIMENTO[posicao]:
            equipe = por_departamento[departamento]
            responsavel = equipe[posicao % len(equipe)]
            AtribuicaoDepartamento.objects.get_or_create(
                organization=office,
                empresa=empresa,
                departamento=departamento,
                colaborador=responsavel,
            )
            for indice, competencia in enumerate(competencias):
                inicio, _fim = _limites(competencia)
                minutos = MINUTOS[departamento] + ((posicao * 17 + indice * 11) % 90)
                marca = hashlib.sha256(
                    f"demo|{office.pk}|{empresa.pk}|{responsavel.pk}|{competencia}".encode()
                ).hexdigest()
                RegistroHoras.objects.update_or_create(
                    organization=office,
                    source_content_hash=marca,
                    occurrence_index=0,
                    defaults={
                        "empresa": empresa,
                        "colaborador": responsavel,
                        "competencia": competencia,
                        "data": date(inicio.year, inicio.month, 10),
                        "origem": OrigemHoras.AUTOMATICA,
                        "inicio": "09:00",
                        "fim": "11:30",
                        "duracao_minutos": minutos,
                        "deleted_at": None,
                    },
                )
                horas += 1

    for competencia in competencias:
        recompute_competencia(office, competencia)
    return {
        "empresas": len(empresas),
        "colaboradores": len(pessoas),
        "competencias": len(competencias),
        "registros_de_horas": horas,
    }
