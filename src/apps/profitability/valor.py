"""Valor gerado por colaborador na competência.

Junta o que o módulo já sabe (mensalidade, salário, capacidade) com quem atende
cada empresa em cada departamento, e entrega à tela uma linha por pessoa. A
conta em si é `calc.valor_por_colaborador`; aqui só se monta a entrada e se
confronta o valor com o custo.

Nada é gravado: é uma leitura derivada, recalculada a cada abertura. A cardinalidade
é pequena (empresas x pessoas de uma competência) e assim o número nunca fica
velho em relação a uma mensalidade ou a uma atribuição recém-corrigida.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from apps.hub.models import ClientCompany, CompanyAreaResponsible
from apps.organizations.models import Organization
from apps.profitability import calc
from apps.profitability.models import (
    DEPARTAMENTO_DA_AREA,
    AtribuicaoDepartamento,
    Colaborador,
    Departamento,
    Mensalidade,
    ProfitabilityConfig,
)
from apps.profitability.services import (
    capacidade_produtiva_mensal,
    get_config,
    salario_vigente_map,
)

_MESES = Decimal(12)


@dataclass(frozen=True)
class LinhaDoColaborador:
    colaborador: Colaborador
    departamento: str
    empresas: int
    valor: Decimal
    custo: Decimal | None
    resultado: Decimal | None
    margem: Decimal | None


@dataclass(frozen=True)
class PesoDoDepartamento:
    departamento: str
    rotulo: str
    pessoas: int
    capacidade_horas: Decimal
    peso: Decimal


@dataclass(frozen=True)
class SemResponsavel:
    empresa: ClientCompany
    mensalidade: Decimal


@dataclass(frozen=True)
class ValorDaCompetencia:
    linhas: list[LinhaDoColaborador]
    departamentos: list[PesoDoDepartamento]
    sem_responsavel: list[SemResponsavel]
    receita: Decimal
    atribuido: Decimal
    sem_dono: Decimal
    # Pessoas sem departamento ou sem salário: o que falta para o número fechar.
    sem_departamento: list[Colaborador]
    sem_salario: int


def custo_mensal(
    colaborador: Colaborador, salario: Decimal, config: ProfitabilityConfig
) -> Decimal:
    """O que a pessoa custa à empresa por mês: custo anual / 12 (CLT), nota (PJ)."""

    if colaborador.contratacao == Colaborador.Contratacao.PJ:
        return salario
    anual = calc.custo_anual_colaborador(
        salario,
        beneficios_mensais=colaborador.beneficios_mensais,
        vt_mensal=colaborador.vt_mensal,
        outros_custos_mensais=colaborador.outros_custos_mensais,
        dias_ferias=colaborador.dias_ferias,
        folgas_dias=colaborador.folgas_dias,
        ausencias_dias=colaborador.ausencias_dias,
        encargos_percentual=config.encargos_percentual,
        dias_uteis_ano=config.dias_uteis_ano,
        feriados_dias_ano=config.feriados_dias_ano,
        horas_dia=config.horas_dia,
        indice_produtividade=config.indice_produtividade,
    )
    return anual.custo_anual_total / _MESES


def atendimento_por_empresa(organization: Organization) -> dict[str, dict[str, list[str]]]:
    """empresa -> departamento -> colaboradores, da tabela e do responsável de área.

    A atribuição explícita vence: se existe linha para (empresa, departamento), o
    responsável de área da carteira daquele departamento é ignorado, senão a mesma
    pessoa receberia duas vezes.
    """

    atendimento: dict[str, dict[str, list[str]]] = {}
    explicitos: set[tuple[str, str]] = set()
    for empresa_id, depto, colaborador_id in AtribuicaoDepartamento.objects.filter(
        organization=organization, colaborador__ativo=True
    ).values_list("empresa_id", "departamento", "colaborador_id"):
        atendimento.setdefault(str(empresa_id), {}).setdefault(depto, []).append(
            str(colaborador_id)
        )
        explicitos.add((str(empresa_id), depto))

    por_usuario = {
        usuario_id: str(colaborador_id)
        for usuario_id, colaborador_id in Colaborador.objects.filter(
            organization=organization, ativo=True, usuario__isnull=False
        ).values_list("usuario_id", "id")
    }
    for company_id, area, user_id in CompanyAreaResponsible.objects.filter(
        organization=organization, user__isnull=False
    ).values_list("company_id", "area", "user_id"):
        departamento = DEPARTAMENTO_DA_AREA.get(area)
        responsavel = por_usuario.get(user_id)
        if (
            departamento is None
            or responsavel is None
            or (str(company_id), str(departamento)) in explicitos
        ):
            continue
        atendimento.setdefault(str(company_id), {}).setdefault(str(departamento), []).append(
            responsavel
        )
    return atendimento


def valor_da_competencia(organization: Organization, competencia: str) -> ValorDaCompetencia:
    config = get_config(organization)
    pessoas = list(Colaborador.objects.filter(organization=organization, ativo=True))
    por_id = {str(pessoa.id): pessoa for pessoa in pessoas}

    capacidade: dict[str, Decimal] = {}
    quantas: dict[str, int] = {}
    for pessoa in pessoas:
        if not pessoa.departamento:
            continue
        capacidade[pessoa.departamento] = capacidade.get(
            pessoa.departamento, Decimal(0)
        ) + capacidade_produtiva_mensal(config, pessoa)
        quantas[pessoa.departamento] = quantas.get(pessoa.departamento, 0) + 1

    mensalidades = {
        str(empresa_id): (manual if manual is not None else valor)
        for empresa_id, valor, manual in Mensalidade.objects.filter(
            organization=organization, competencia=competencia
        ).values_list("empresa_id", "valor", "manual_override")
    }
    atendimento = atendimento_por_empresa(organization)
    empresas = [
        calc.EmpresaAtendida(
            empresa=empresa_id,
            mensalidade=valor,
            atendimento={
                depto: tuple(ids) for depto, ids in atendimento.get(empresa_id, {}).items()
            },
        )
        for empresa_id, valor in mensalidades.items()
    ]
    resultado = calc.valor_por_colaborador(capacidade, empresas)

    salarios = salario_vigente_map(organization, competencia)
    empresas_por_pessoa: dict[str, set[str]] = {}
    for pessoa_id, empresa_id in resultado.por_colaborador_empresa:
        empresas_por_pessoa.setdefault(pessoa_id, set()).add(empresa_id)

    linhas: list[LinhaDoColaborador] = []
    for pessoa_id, valor in resultado.por_colaborador.items():
        quem = por_id.get(pessoa_id)
        if quem is None:
            continue
        vigente = salarios.get(pessoa_id)
        custo = custo_mensal(quem, vigente[1], config) if vigente else None
        saldo = valor - custo if custo is not None else None
        linhas.append(
            LinhaDoColaborador(
                colaborador=quem,
                departamento=quem.departamento,
                empresas=len(empresas_por_pessoa.get(pessoa_id, ())),
                valor=valor,
                custo=custo,
                resultado=saldo,
                margem=calc.margem(saldo, valor) if saldo is not None else None,
            )
        )
    linhas.sort(key=lambda linha: -linha.valor)

    rotulos = dict(Departamento.choices)
    pesos = resultado.pesos
    departamentos = [
        PesoDoDepartamento(
            departamento=depto,
            rotulo=str(rotulos.get(depto, depto)),
            pessoas=quantas.get(depto, 0),
            capacidade_horas=capacidade[depto],
            peso=pesos[depto],
        )
        for depto in sorted(pesos, key=lambda chave: -pesos[chave])
    ]

    nomes = {
        str(empresa.id): empresa
        for empresa in ClientCompany.objects.filter(
            organization=organization, id__in=list(resultado.sem_responsavel)
        )
    }
    sem_responsavel = [
        SemResponsavel(empresa=nomes[empresa_id], mensalidade=valor)
        for empresa_id, valor in sorted(
            resultado.sem_responsavel.items(), key=lambda item: -item[1]
        )
        if empresa_id in nomes
    ]
    receita = sum((e.mensalidade for e in empresas), Decimal(0))
    sem_dono = sum(resultado.sem_responsavel.values(), Decimal(0))
    return ValorDaCompetencia(
        linhas=linhas,
        departamentos=departamentos,
        sem_responsavel=sem_responsavel,
        receita=receita,
        atribuido=receita - sem_dono,
        sem_dono=sem_dono,
        sem_departamento=[pessoa for pessoa in pessoas if not pessoa.departamento],
        sem_salario=sum(1 for linha in linhas if linha.custo is None),
    )
