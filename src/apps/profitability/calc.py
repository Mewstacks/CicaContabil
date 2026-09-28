"""Profitability formulas.

Portadas do Lucrums por D-108, sem alterar uma conta. O que governa este arquivo
é a tabela de vetores em `contracts/calculations/v1.json`: um teste a lê e
compara valor a valor, então mudar uma fórmula aqui quebra o teste, que é o
ponto. O contrato veio junto com o código e seus valores não foram tocados.

No Lucrums havia uma segunda implementação em TypeScript para um simulador que
rodava no navegador, e o contrato existia para manter as duas em acordo. Por
D-110 a interface da CICA é servida pelo servidor e essa segunda implementação
não foi portada — o contrato continua valendo como prova de que a aritmética
atravessou intacta.

Dinheiro é Decimal de ponta a ponta: uma coluna que alimenta `SUM()` sobre a
carteira inteira não pode ser float.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Final, Literal

FaixaMargem = Literal["negativa", "atencao", "saudavel", "sem_dados"]

MARGEM_ATENCAO_PADRAO: Final = Decimal("0.15")

_MINUTOS_POR_HORA: Final = Decimal(60)

# `custo_hora_colaborador` -- (salário x fator de encargos) / 176 -- vivia aqui e
# foi removida, com as constantes 176 e 1,40 que a alimentavam.
#
# Ela respondia a pergunta errada: 176 h é o mês-referência da CLT, o divisor com
# que se acha o valor da hora extra, ou seja o valor/hora DO FUNCIONÁRIO. O que a
# carteira precisa é o custo que a EMPRESA tem por hora dele, e para isso errava
# nas duas pontas -- o fator de 1,40 cobre doze salários e não os treze mais o
# terço de férias, e 176 h/mês cobra por 368 horas ao ano que a empresa paga sem
# receber trabalho. Ver `services.custo_hora_do_colaborador`, que divide o custo
# anual pelas horas do ano e é a única conta de custo horário que restou.


def custo_de_minutos(minutos: int, custo_hora: Decimal) -> Decimal:
    """Cost of a span of work. Minutes are the canonical unit of the fact table."""

    return (Decimal(minutos) / _MINUTOS_POR_HORA) * custo_hora


def resultado(mensalidade: Decimal, custo: Decimal) -> Decimal:
    return mensalidade - custo


def margem(resultado_valor: Decimal, mensalidade: Decimal) -> Decimal:
    """Margin, defined as 0 when there is no fee to divide by.

    Returning 0 rather than raising keeps a company with no mensalidade out of
    the "negative margin" bucket it would otherwise fall into, which would be a
    data-quality problem misreported as a profitability one.
    """

    if mensalidade <= 0:
        return Decimal(0)
    try:
        return resultado_valor / mensalidade
    except (ZeroDivisionError, InvalidOperation):  # pragma: no cover - guarded above
        return Decimal(0)


def faixa_margem(
    margem_valor: Decimal,
    *,
    tem_horas: bool,
    margem_atencao: Decimal = MARGEM_ATENCAO_PADRAO,
) -> FaixaMargem:
    """negativa (<0) · atenção (0 até o limiar) · saudável (≥ limiar).

    "Sem dados" is not a margin band: with no hours there is no cost, so the
    margin would read as a perfect 100% and the company would rank at the top of
    the portfolio. It has to be its own answer.
    """

    if not tem_horas:
        return "sem_dados"
    if margem_valor < 0:
        return "negativa"
    if margem_valor < margem_atencao:
        return "atencao"
    return "saudavel"


def mensalidade_sugerida(custo: Decimal, margem_alvo: Decimal) -> Decimal:
    """custo / (1 - margem-alvo).

    A target margin of 100% or more has no finite answer, so the cost itself is
    returned rather than dividing by zero or by a negative.
    """

    if margem_alvo >= 1:
        return custo
    return custo / (Decimal(1) - margem_alvo)


_PERCENTUAL_VT_FUNCIONARIO: Final = Decimal("0.06")
_MESES_ANO: Final = Decimal(12)
_SALARIOS_ANO: Final = Decimal(13)
_TERCO_FERIAS: Final = Decimal(3)


@dataclass(frozen=True)
class CustoAnual:
    """Decomposição do custo anual de um colaborador.

    Cada parcela fica visível porque a tela de Financeiro mostra o total e o
    detalhe lado a lado; esconder o passo a passo faria o usuário refazer a
    conta à mão para conferir.
    """

    salarios_anuais: Decimal
    terco_ferias: Decimal
    encargos_anuais: Decimal
    beneficios_anuais: Decimal
    vt_excedente_mensal: Decimal
    vt_empresa_anual: Decimal
    outros_custos_anuais: Decimal
    custo_anual_total: Decimal
    dias_uteis: int
    horas_anuais: Decimal
    horas_produtivas: Decimal
    valor_hora: Decimal
    valor_hora_produtivo: Decimal


def vt_excedente_mensal(vt_mensal: Decimal, salario: Decimal) -> Decimal:
    """Parcela do vale-transporte paga pela empresa.

    O funcionário arca com até 6% do salário; a empresa paga apenas o que
    exceder esse desconto, nunca um valor negativo.
    """

    return max(Decimal(0), vt_mensal - _PERCENTUAL_VT_FUNCIONARIO * salario)


def dias_uteis_efetivos(
    dias_uteis_ano: int,
    feriados_dias_ano: int,
    dias_ferias: int,
    folgas_dias: int,
    ausencias_dias: int,
) -> int:
    """Dias realmente trabalhados no ano, com piso em zero."""

    return max(0, dias_uteis_ano - feriados_dias_ano - dias_ferias - folgas_dias - ausencias_dias)


def horas_anuais(dias_uteis: int, horas_dia: Decimal) -> Decimal:
    return Decimal(dias_uteis) * horas_dia


def horas_produtivas(horas: Decimal, indice_produtividade: Decimal) -> Decimal:
    """Horas efetivamente faturáveis: o índice desconta reuniões e apoio."""

    return horas * indice_produtividade


def valor_hora(custo_anual: Decimal, horas: Decimal) -> Decimal:
    """Custo por hora; sem horas não há quociente, então o custo por hora é 0."""

    if horas <= 0:
        return Decimal(0)
    return custo_anual / horas


def custo_anual_colaborador(
    salario: Decimal,
    *,
    beneficios_mensais: Decimal = Decimal(0),
    vt_mensal: Decimal = Decimal(0),
    outros_custos_mensais: Decimal = Decimal(0),
    dias_ferias: int = 22,
    folgas_dias: int = 0,
    ausencias_dias: int = 0,
    encargos_percentual: Decimal,
    dias_uteis_ano: int,
    feriados_dias_ano: int,
    horas_dia: Decimal,
    indice_produtividade: Decimal,
) -> CustoAnual:
    """(S x 13) + (S/3) + encargos + benefícios + VT da empresa + outros custos.

    S x 13 cobre os 12 salários e o 13º; S/3 é o terço constitucional de férias.
    Os encargos incidem sobre salários e 13º; benefícios, VT e outros custos
    são parcelas mensais multiplicadas por 12.
    """

    salarios_anuais = salario * _SALARIOS_ANO
    terco_ferias = salario / _TERCO_FERIAS
    encargos_anuais = encargos_percentual * salarios_anuais
    beneficios_anuais = beneficios_mensais * _MESES_ANO
    excedente = vt_excedente_mensal(vt_mensal, salario)
    vt_empresa_anual = excedente * _MESES_ANO
    outros_custos_anuais = outros_custos_mensais * _MESES_ANO
    total = (
        salarios_anuais
        + terco_ferias
        + encargos_anuais
        + beneficios_anuais
        + vt_empresa_anual
        + outros_custos_anuais
    )
    dias = dias_uteis_efetivos(
        dias_uteis_ano, feriados_dias_ano, dias_ferias, folgas_dias, ausencias_dias
    )
    horas = horas_anuais(dias, horas_dia)
    produtivas = horas_produtivas(horas, indice_produtividade)
    return CustoAnual(
        salarios_anuais=salarios_anuais,
        terco_ferias=terco_ferias,
        encargos_anuais=encargos_anuais,
        beneficios_anuais=beneficios_anuais,
        vt_excedente_mensal=excedente,
        vt_empresa_anual=vt_empresa_anual,
        outros_custos_anuais=outros_custos_anuais,
        custo_anual_total=total,
        dias_uteis=dias,
        horas_anuais=horas,
        horas_produtivas=produtivas,
        valor_hora=valor_hora(total, horas),
        valor_hora_produtivo=valor_hora(total, produtivas),
    )
