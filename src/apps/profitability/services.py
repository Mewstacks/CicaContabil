"""Rebuild the materialised metrics for one organisation x period.

Deliberately a full delete-and-insert per organisation and period rather than an
incremental diff. The cardinality is small (companies x 24 periods at worst), the
inputs change in bulk after every sync, and a wholesale rebuild is the only shape
that is trivially idempotent — re-running it after a partial failure converges,
which an incremental update does not.

Portado do Lucrums por D-108. A diferenca estrutural e D-109: onde a origem lia
`Empresa`, aqui se le `CompanyErpProfile` e a chave devolvida e a da carteira do
hub, `hub.ClientCompany` -- e por isso que a ligacao um-para-um se chama
`empresa`, e `values_list("empresa_id")` ja devolve o id que as metricas usam.

Uma consequencia vale registrar: a carteira deste modulo sao as empresas com
perfil de ERP. Uma empresa cadastrada so no hub, sem perfil, nao ganha linha de
metrica -- que e o mesmo destino que a origem dava a empresa sem documento, por
nao haver como um honorario encontra-la.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, cast
from uuid import UUID

from django.db import transaction
from django.db.models import Q, Sum

from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.profitability import calc
from apps.profitability.models import (
    ClienteCompetenciaMetrics,
    Colaborador,
    ColaboradorCompetenciaMetrics,
    CompanyErpProfile,
    Mensalidade,
    OrigemHoras,
    ProfitabilityConfig,
    RegistroHoras,
    SalarioColaborador,
    SistemaOrigem,
)
from apps.profitability.normalize import cnpj_ordem, only_digits


def get_config(organization: Organization) -> ProfitabilityConfig:
    config, _ = ProfitabilityConfig.objects.get_or_create(organization=organization)
    return config


def salario_vigente_map(
    organization: Organization, competencia: str
) -> dict[str, tuple[str, Decimal]]:
    """O salário em vigor de cada colaborador, e em que competência foi gravado.

    "Em vigor" é a observação mais recente **até** a competência, não a mais
    recente de todas: recalcular maio não pode precificar o trabalho de maio com
    o salário de julho, senão toda margem histórica se move quando a folha
    sincroniza.

    Fica sozinha aqui porque a consulta já existiu em dois módulos, palavra por
    palavra. Duas cópias de uma regra concordam até o dia em que alguém mexe numa
    -- foi assim que o custo do PJ passou meses divergindo entre duas telas.
    """

    vigentes: dict[str, tuple[str, Decimal]] = {}
    linhas = (
        SalarioColaborador.objects.filter(organization=organization, competencia__lte=competencia)
        .order_by("colaborador_id", "-competencia")
        .values_list("colaborador_id", "competencia", "salario")
    )
    for colaborador_id, gravada, salario in linhas:
        vigentes.setdefault(str(colaborador_id), (gravada, salario))
    return vigentes


def custo_hora_map(
    organization: Organization, competencia: str, config: ProfitabilityConfig
) -> dict[str, Decimal]:
    """Quanto uma hora de cada pessoa custa À EMPRESA, pelo salário vigente.

    "Vigente" é a observação mais recente até a competência, não a mais recente
    de todas: recalcular maio não pode precificar o trabalho de maio com o
    salário de julho, senão toda margem histórica se move quando a folha
    sincroniza.

    A conta é a do custo anual, dividida pelas horas que a pessoa realmente
    trabalha. Antes era `salario vezes fator_encargos, dividido por 176`, que é outra pergunta:
    176 h é o mês-referência da CLT, usado para achar o valor da hora extra --
    ou seja, o valor/hora DO FUNCIONÁRIO, não o custo que a empresa tem por
    hora dele. Ela errava nas duas pontas: o fator de 1,40 cobre doze salários,
    não os treze mais o terço de férias; e 176 h/mês cobra por 368 horas ao ano
    que a empresa paga e não recebe trabalho -- férias e feriados. Juntos,
    28,9% a menos.

    Manter as duas contas em paralelo era manter duas descrições da mesma
    realidade, com dois conjuntos de parâmetros para o escritório conciliar à
    mão. Agora existe uma, e os campos por pessoa (férias, folgas, ausências,
    benefícios, VT) finalmente pesam: quem tira sessenta dias de licença deixa
    de custar por hora o mesmo que o colega de mesmo salário que não tirou.
    """

    salarios = {
        chave: salario
        for chave, (_competencia, salario) in salario_vigente_map(organization, competencia).items()
    }
    pessoas = {
        str(colaborador.id): colaborador
        for colaborador in Colaborador.objects.filter(
            organization=organization, id__in=sorted(salarios)
        )
    }
    return {
        chave: custo_hora_do_colaborador(pessoas[chave], salario, config)
        for chave, salario in salarios.items()
        if chave in pessoas
    }


def custo_hora_do_colaborador(
    colaborador: Colaborador, salario: Decimal, config: ProfitabilityConfig
) -> Decimal:
    """O custo horário de uma pessoa: o que sai do caixa por ano ÷ horas do ano.

    CLT e PJ diferem só no numerador. O CLT custa treze salários, mais o terço
    constitucional, mais os encargos, mais benefícios e VT -- é o que
    `custo_anual_colaborador` monta. O PJ custa as doze notas e nada mais: não
    há décimo terceiro, terço nem encargo numa nota de prestador, e somá-los
    inventaria um custo que ninguém paga.

    O denominador é o mesmo para os dois, e é o que respeita as férias, folgas e
    ausências de cada um: a empresa paga o ano inteiro e recebe trabalho nos
    dias em que a pessoa está lá.
    """

    if colaborador.contratacao == Colaborador.Contratacao.PJ:
        dias = calc.dias_uteis_efetivos(
            config.dias_uteis_ano,
            config.feriados_dias_ano,
            colaborador.dias_ferias,
            colaborador.folgas_dias,
            colaborador.ausencias_dias,
        )
        return calc.valor_hora(salario * 12, calc.horas_anuais(dias, config.horas_dia))

    return calc.custo_anual_colaborador(
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
    ).valor_hora


@dataclass
class _EmpresaAcc:
    auto_minutos: int = 0
    f9_minutos: int = 0
    custo: Decimal = field(default_factory=lambda: Decimal(0))
    tem_registros: bool = False
    minutos_sem_custo: int = 0
    motivos_incompletude: set[str] = field(default_factory=set)


@dataclass
class _ColaboradorAcc:
    auto_minutos: int = 0
    f9_minutos: int = 0
    auto_comparavel: int = 0
    f9_comparavel: int = 0
    empresas: set[str] = field(default_factory=set)
    f9_pendente: bool = False


def acumular_registro(
    acc: _EmpresaAcc,
    *,
    origem: str,
    colaborador_id: UUID | None,
    minutos: int,
    custo_hora: Mapping[str, Decimal],
) -> None:
    """A regra de custo de uma linha do fato. Existe uma so, e e esta.

    Esta fora do laco que a criou porque a carteira e a abertura por unidade
    precisam da MESMA conta sobre recortes diferentes das mesmas horas. Duas
    copias divergem -- e ja divergiram: o custo por colaborador do cliente
    esqueceu que PJ nao tem encargo e vem cobrando encargo a mais numa tela
    enquanto a carteira cobra certo na outra.

    De quem e a hora fica de fora de proposito: o acumulador que chega ja e o da
    unidade certa, dobrado na matriz ou nao.
    """

    acc.tem_registros = True
    if origem == OrigemHoras.AUTOMATICA:
        acc.auto_minutos += minutos
        if colaborador_id is None:
            acc.minutos_sem_custo += minutos
            acc.motivos_incompletude.add("colaborador_nao_mapeado")
        elif str(colaborador_id) not in custo_hora:
            acc.minutos_sem_custo += minutos
            acc.motivos_incompletude.add("salario_nao_disponivel")
        else:
            acc.custo += calc.custo_de_minutos(minutos, custo_hora[str(colaborador_id)])
    else:
        acc.f9_minutos += minutos


def _empresas_com_f9_pendente(organization: Organization, competencia: str) -> set[str]:
    """Companies with automatic hours but no F9 at all in the period.

    Derived rather than stored: a flag would go stale the moment the missing
    import arrives, and the whole point of the pendente state is that it clears
    itself.
    """

    rows = (
        RegistroHoras.objects.filter(
            organization=organization, competencia=competencia, deleted_at__isnull=True
        )
        .values("empresa_id", "origem")
        .annotate(minutos=Sum("duracao_minutos"))
    )
    por_empresa: dict[str, dict[str, int]] = {}
    for raw_row in rows:
        row = cast(dict[str, Any], raw_row)
        empresa_id = str(row["empresa_id"])
        totais = por_empresa.setdefault(empresa_id, {"auto": 0, "f9": 0})
        chave = "auto" if row["origem"] == OrigemHoras.AUTOMATICA else "f9"
        totais[chave] = int(row["minutos"] or 0)
    return {
        empresa_id
        for empresa_id, totais in por_empresa.items()
        if totais["auto"] > 0 and totais["f9"] == 0
    }


@transaction.atomic
def recompute_competencia(organization: Organization, competencia: str) -> None:
    config = get_config(organization)
    custo_hora = custo_hora_map(organization, competencia, config)
    f9_pendentes = _empresas_com_f9_pendente(organization, competencia)
    matriz_de = grupos_por_raiz_de_cnpj(organization)

    empresas: dict[str, _EmpresaAcc] = {}
    colaboradores: dict[str, _ColaboradorAcc] = {}

    # The database reduces the fact table to company x collaborator x source.
    # Python only combines this bounded aggregate into the two read models.
    registros = (
        RegistroHoras.objects.filter(
            organization=organization, competencia=competencia, deleted_at__isnull=True
        )
        .values("empresa_id", "colaborador_id", "origem")
        .annotate(minutos=Sum("duracao_minutos"))
    )

    for raw_row in registros:
        row = cast(dict[str, Any], raw_row)
        # A hora da filial é custo do grupo. Dobrar aqui, no acumulador, é o que
        # faz a matriz carregar o custo que ela de fato gera; esconder a linha
        # da filial mais adiante, sem isto, apenas jogaria essas horas fora.
        empresa_key = str(row["empresa_id"])
        empresa_key = matriz_de.get(empresa_key, empresa_key)
        colaborador_id = row["colaborador_id"]
        origem = row["origem"]
        minutos = int(row["minutos"] or 0)
        empresa = empresas.setdefault(empresa_key, _EmpresaAcc())
        pendente = empresa_key in f9_pendentes
        acumular_registro(
            empresa,
            origem=origem,
            colaborador_id=colaborador_id,
            minutos=minutos,
            custo_hora=custo_hora,
        )

        if colaborador_id is None:
            # An unmapped Domínio user still counts towards the company's hours,
            # but it has no person to attribute cost or divergence to.
            continue

        colaborador = colaboradores.setdefault(str(colaborador_id), _ColaboradorAcc())
        colaborador.empresas.add(empresa_key)
        if pendente:
            colaborador.f9_pendente = True
        if origem == OrigemHoras.AUTOMATICA:
            colaborador.auto_minutos += minutos
            if not pendente:
                colaborador.auto_comparavel += minutos
        else:
            colaborador.f9_minutos += minutos
            if not pendente:
                colaborador.f9_comparavel += minutos

    _rebuild_cliente_metrics(organization, competencia, config, empresas, f9_pendentes, matriz_de)
    _rebuild_colaborador_metrics(organization, competencia, config, colaboradores, custo_hora)


def competencia_anterior(competencia: str) -> str:
    """Mês anterior a `competencia`, no formato AAAA-MM."""

    ano, _, mes = competencia.partition("-")
    numero = int(ano) * 12 + int(mes) - 2
    return f"{numero // 12:04d}-{numero % 12 + 1:02d}"


def competencia_seguinte(competencia: str) -> str:
    """Mês seguinte a `competencia`, no formato AAAA-MM."""

    ano, _, mes = competencia.partition("-")
    numero = int(ano) * 12 + int(mes)
    return f"{numero // 12:04d}-{numero % 12 + 1:02d}"


def mapa_de_substituicao(organization: Organization) -> dict[str, str]:
    """Empresa oculta -> a que ficou no lugar dela na carteira.

    Existe para a ficha de uma empresa oculta não responder "não encontrado".
    Ela está no cadastro, só não tem linha de métrica; sem este mapa a tela diz
    que o cliente não existe neste tenant, que é falso e assusta.
    """

    return _duplicidade(organization)[1]


def grupos_por_raiz_de_cnpj(organization: Organization) -> dict[str, str]:
    """Filial -> matriz, para as unidades do mesmo CNPJ raiz.

    Um grupo econômico costuma ter o honorário cobrado só na matriz, enquanto as
    horas são lançadas em cada unidade. Sem juntar, as duas linhas mentem: a
    filial aparece sem receita e sem margem, e a matriz aparece rentável demais
    porque cobra por um trabalho cujo custo está na linha ao lado.

    O CNPJ resolve o vínculo sozinho — mesma raiz de oito dígitos é o mesmo
    grupo, e a ordem `0001` é a matriz. Quando nenhuma unidade `0001` está na
    carteira, manda a de menor ordem: é arbitrário, mas é estável entre
    execuções, e o que importa é existir uma linha só para o grupo.

    Roda sobre quem sobrou da deduplicação entre ERPs, nunca sobre o cadastro
    cru: eleger como matriz uma gêmea que está escondida deixaria o grupo
    apontando para uma linha que a carteira não mostra.
    """

    ocultas = _empresas_ocultas_por_duplicidade(organization)
    porRaiz: dict[str, list[tuple[str, str]]] = {}
    for empresa_id, raiz, documento in (
        CompanyErpProfile.objects.filter(
            organization=organization, empresa__active=True, deleted_at__isnull=True
        )
        .exclude(documento_raiz_bi="")
        .values_list("empresa_id", "documento_raiz_bi", "documento")
    ):
        chave = str(empresa_id)
        if chave in ocultas:
            continue
        porRaiz.setdefault(raiz, []).append((chave, cnpj_ordem(only_digits(documento))))

    matriz_de: dict[str, str] = {}
    for unidades in porRaiz.values():
        if len(unidades) < 2:
            continue
        # `0001` primeiro; empatando, a menor ordem. A chave entra no desempate
        # para a escolha não depender da ordem que o banco devolveu.
        matriz, _ = min(unidades, key=lambda par: (par[1] != "0001", par[1], par[0]))
        for chave, _ordem in unidades:
            if chave != matriz:
                matriz_de[chave] = matriz
    return matriz_de


@dataclass(frozen=True)
class UnidadeDoGrupo:
    """Os numeros de UMA unidade, sem a dobra que a carteira aplica."""

    empresa: ClientCompany
    documento: str
    eh_matriz: bool
    auto_minutos: int
    f9_minutos: int
    custo: Decimal
    custo_completo: bool
    minutos_sem_custo: int
    motivos_incompletude: list[str]
    divergencia_minutos: int
    tem_divergencia: bool
    sem_base_de_custo: bool


def unidades_do_grupo(
    organization: Organization, competencia: str, empresa_id: str
) -> list[UnidadeDoGrupo]:
    """Abre o grupo economico de `empresa_id` unidade por unidade.

    A carteira mostra o grupo somado numa linha so, e para decidir preco e o
    certo: o honorario e um so. Para conferir uma importacao e o contrario -- a
    pergunta e de qual unidade veio cada hora, e a linha somada nao responde.

    Aceita o id da matriz ou o de qualquer filial porque quem audita chega pela
    ficha que tem na mao, e a da filial nem linha de metrica possui.

    Nao devolve mensalidade nem margem de proposito. O honorario e cobrado numa
    unidade so, entao receita por unidade nao existe, e uma margem por unidade
    leria -100% em toda filial -- exatamente a mentira que o agrupamento foi
    escrito para tirar da tela.
    """

    matriz_de = grupos_por_raiz_de_cnpj(organization)
    chave_pedida = str(empresa_id)
    matriz = matriz_de.get(chave_pedida, chave_pedida)
    ids = {matriz} | {filial for filial, alvo in matriz_de.items() if alvo == matriz}

    perfis = {
        str(perfil.empresa_id): perfil
        for perfil in CompanyErpProfile.objects.select_related("empresa").filter(
            organization=organization, empresa_id__in=sorted(ids), deleted_at__isnull=True
        )
    }
    if not perfis:
        return []

    config = get_config(organization)
    custo_hora = custo_hora_map(organization, competencia, config)
    f9_pendentes = _empresas_com_f9_pendente(organization, competencia)
    limiar = config.limiar_divergencia_horas * 60
    piso = max(1, config.minutos_minimos_custo)

    acumuladores: dict[str, _EmpresaAcc] = {}
    registros = (
        RegistroHoras.objects.filter(
            organization=organization,
            competencia=competencia,
            deleted_at__isnull=True,
            empresa_id__in=sorted(perfis),
        )
        .values("empresa_id", "colaborador_id", "origem")
        .annotate(minutos=Sum("duracao_minutos"))
    )
    for raw_row in registros:
        row = cast(dict[str, Any], raw_row)
        acumular_registro(
            acumuladores.setdefault(str(row["empresa_id"]), _EmpresaAcc()),
            origem=row["origem"],
            colaborador_id=row["colaborador_id"],
            minutos=int(row["minutos"] or 0),
            custo_hora=custo_hora,
        )

    unidades: list[UnidadeDoGrupo] = []
    for chave, perfil in perfis.items():
        acc = acumuladores.get(chave, _EmpresaAcc())
        pendente = chave in f9_pendentes
        divergencia = (
            0 if pendente or not acc.tem_registros else abs(acc.auto_minutos - acc.f9_minutos)
        )
        unidades.append(
            UnidadeDoGrupo(
                empresa=perfil.empresa,
                documento=perfil.documento,
                eh_matriz=chave == matriz,
                auto_minutos=acc.auto_minutos,
                f9_minutos=acc.f9_minutos,
                custo=acc.custo.quantize(Decimal("0.01")),
                # A incompletude aqui e so sobre a hora. A mensalidade nao falta
                # a unidade: ela e do grupo, e quem cobra e a matriz.
                custo_completo=not acc.motivos_incompletude,
                minutos_sem_custo=acc.minutos_sem_custo,
                motivos_incompletude=sorted(acc.motivos_incompletude),
                divergencia_minutos=divergencia,
                tem_divergencia=divergencia > limiar,
                sem_base_de_custo=acc.auto_minutos < piso,
            )
        )
    # Matriz primeiro, filiais por documento -- a mesma ordem da lista `filiais`
    # da ficha, para as duas telas nao se contradizerem.
    unidades.sort(key=lambda unidade: (not unidade.eh_matriz, unidade.documento))
    return unidades


def _empresas_ocultas_por_duplicidade(organization: Organization) -> set[str]:
    """Empresas que não podem ocupar uma linha própria na carteira.

    São três casos, e nenhum deles é cliente de verdade a mais.

    O primeiro é a duplicata entre ERPs: os dois cadastram o mesmo cliente e
    sobram duas linhas — no Fedrizzi são 506 CNPJs em duas linhas cada. Só uma
    carrega alguma coisa, porque honorários e horas caem na do sistema que
    fatura. A que fica é essa, e não é desempate arbitrário: é de onde vêm
    receita e hora, e portanto a única linha que tem o que mostrar.

    A gêmea é procurada **pelo documento e, depois, pela razão social**. Só o
    documento não basta: o cadastro do Siescon guarda no mesmo campo CNPJ, CPF e
    inscrição estadual, e às vezes um CNPJ que o cliente já trocou. Medido na
    base do Fedrizzi em 22/09/2026, das 27 linhas do Siescon que sobravam na
    carteira, 4 eram a mesma empresa que já estava lá pelo Domínio — `ANDRE LUIS
    RECH` com inscrição estadual de um lado e CNPJ do outro, `K M BOGADO
    FERREIRA` com dois CNPJs diferentes. Razão social idêntica depois de
    normalizada, vinda de dois ERPs, é a mesma empresa.

    O segundo é a empresa sem documento. Cliente de escritório contábil tem
    CNPJ ou CPF, sempre; sem documento é registro de estrutura do próprio ERP —
    `EXEMPLO PLANO CONTAS` no Domínio, `MODELO PLANO` e `ZZZ EMPRESA MODELO
    SIESCON` no Siescon. Além de não serem clientes, não há como um honorário
    achá-las, porque a correspondência é pelo documento.

    O terceiro é o próprio escritório. A empresa armada como fonte de
    honorários ou de folha é de onde os dados saem, não para quem eles apontam;
    no Fedrizzi ela aparecia na carteira com horas internas, nenhuma
    mensalidade e margem de -100%. Uma contabilidade não é cliente dela mesma.

    Nada é apagado: as empresas continuam no cadastro e acessíveis pela ficha;
    apenas não viram linha da carteira.
    """

    return _duplicidade(organization)[0]


def codigos_erp(organization: Organization) -> dict[str, tuple[str, int]]:
    """Empresa -> (sistema, codi_emp) que a tela deve exibir como código.

    A tela mostra um código só, e o do Domínio é o que o escritório usa: é lá que
    ficam horas e honorários, e é a tela do Domínio que a pessoa abre ao lado para
    conferir a linha. Só que a empresa que sobrevive na carteira é a do sistema
    que fatura, e ela pode ser a do Siescon — nesse caso a linha visível é a
    Siescon e o código útil está na gêmea, do outro lado do documento.

    Então a preferência é pelo documento, não pela linha: existindo qualquer
    cadastro no Domínio com o mesmo CPF/CNPJ, vale o código dele. Quem não tem
    cadastro no Domínio exibe o próprio, e aí o sistema devolvido é `siescon` —
    é o que faz a tela poder escrever "Siescon · 711" em vez de mentir um número
    do Domínio que não existe.

    `codi_emp` só é único dentro de um sistema, por isso o par sempre viaja junto.
    """

    proprio: dict[str, tuple[str, int]] = {}
    documento_de: dict[str, str] = {}
    melhor_do_documento: dict[str, tuple[str, int]] = {}

    for empresa_id, documento, sistema, codi_emp in CompanyErpProfile.objects.filter(
        organization=organization, empresa__active=True, deleted_at__isnull=True
    ).values_list("empresa_id", "documento_bi", "sistema_origem", "codi_emp"):
        if codi_emp is None:
            continue
        chave = str(empresa_id)
        proprio[chave] = (sistema, codi_emp)
        if not documento:
            continue
        documento_de[chave] = documento
        atual = melhor_do_documento.get(documento)
        # Domínio primeiro; entre dois do mesmo sistema, o menor código, só para a
        # escolha não depender da ordem em que o banco devolveu as linhas.
        if atual is None or _ordem_do_codigo(sistema, codi_emp) < _ordem_do_codigo(*atual):
            melhor_do_documento[documento] = (sistema, codi_emp)

    return {
        chave: melhor_do_documento.get(documento_de.get(chave, ""), valor)
        for chave, valor in proprio.items()
    }


# Papéis que marcam a empresa-fonte de um contrato: é de onde o dado vem.
PAPEIS_DE_FONTE = {"billing_source", "payroll_source"}


def _ordem_do_codigo(sistema: str, codi_emp: int) -> tuple[int, int]:
    return (0 if sistema == SistemaOrigem.DOMINIO else 1, codi_emp)


def _duplicidade(organization: Organization) -> tuple[set[str], dict[str, str]]:
    """Calcula de uma vez as ocultas e para quem cada uma aponta."""

    # O papel é filtrado em Python porque `papel__contains` exige suporte a JSON
    # do banco, que o SQLite dos testes não tem.
    faturamento: set[str] = set()
    fontes: set[str] = set()
    for empresa_id, sistema, papel, ativo in CompanyErpProfile.objects.filter(
        organization=organization, deleted_at__isnull=True
    ).values_list("empresa_id", "sistema_origem", "papel", "empresa__active"):
        papeis = set(papel or [])
        if "billing_source" in papeis:
            faturamento.add(sistema)
        # O escritório não é cliente do escritório: a empresa armada como fonte
        # de honorários ou de folha é de onde o dado vem.
        if ativo and PAPEIS_DE_FONTE & papeis:
            fontes.add(str(empresa_id))

    sem_documento = {
        str(empresa_id)
        for empresa_id in CompanyErpProfile.objects.filter(
            organization=organization,
            empresa__active=True,
            deleted_at__isnull=True,
            documento_bi="",
        ).values_list("empresa_id", flat=True)
    }
    if not faturamento:
        # Sem fonte de faturamento armada não há critério para escolher entre as
        # gêmeas, e esconder pela errada é pior que mostrar duplicado. As sem
        # documento e as fontes continuam fora: para elas o critério não depende
        # de saber quem fatura.
        return sem_documento | fontes, {}

    por_documento: dict[str, set[tuple[str, str]]] = {}
    por_razao: dict[str, set[tuple[str, str]]] = {}
    for empresa_id, documento, razao, sistema in CompanyErpProfile.objects.filter(
        organization=organization, empresa__active=True, deleted_at__isnull=True
    ).values_list("empresa_id", "documento_bi", "razao_normalizada_bi", "sistema_origem"):
        linha = (str(empresa_id), sistema)
        if documento:
            por_documento.setdefault(documento, set()).add(linha)
        if razao:
            por_razao.setdefault(razao, set()).add(linha)

    ocultas: set[str] = set()
    substituta: dict[str, str] = {}

    def esconder_gemeas(grupos: dict[str, set[tuple[str, str]]]) -> None:
        for linhas in grupos.values():
            # O que a passada anterior já escondeu não volta a contar: uma
            # gêmea escondida pelo documento não pode ressuscitar como segunda
            # unidade de um grupo de razão social e fazer o grupo parecer maior
            # do que é.
            vivas = {(chave, sistema) for chave, sistema in linhas if chave not in ocultas}
            if len(vivas) < 2:
                continue
            preferidas = sorted(chave for chave, sistema in vivas if sistema in faturamento)
            # Todas do mesmo lado não é duplicata entre ERPs: são duas empresas
            # do mesmo sistema, e esconder uma delas apagaria cliente.
            if not preferidas or len(preferidas) == len(vivas):
                continue
            escondidas = {chave for chave, _ in vivas} - set(preferidas)
            ocultas.update(escondidas)
            for chave in escondidas:
                substituta[chave] = preferidas[0]

    # O documento primeiro: é o casamento forte, e é ele que decide para quem a
    # razão social vai apontar quando as duas regras alcançarem a mesma empresa.
    esconder_gemeas(por_documento)
    esconder_gemeas(por_razao)

    # Sem documento não há cliente e não há como um honorário achá-la; a fonte
    # não é cliente por definição.
    ocultas |= sem_documento | fontes
    return ocultas, substituta


def _rebuild_cliente_metrics(
    organization: Organization,
    competencia: str,
    config: ProfitabilityConfig,
    empresas: dict[str, _EmpresaAcc],
    f9_pendentes: set[str],
    matriz_de: dict[str, str],
) -> None:
    # A mensalidade do mês que se olha é a lançada no mês anterior: o escritório
    # fatura em atraso, então setembro exibe o honorário de agosto enquanto
    # horas e custo continuam sendo de setembro. Sem o deslocamento, todo mês
    # corrente aparece com receita zero até o faturamento ser lançado.
    mensalidades: dict[str, Decimal] = {}
    for empresa_id, valor, override in Mensalidade.objects.filter(
        organization=organization, competencia=competencia_anterior(competencia)
    ).values_list("empresa_id", "valor", "manual_override"):
        # Soma na matriz: uma filial com honorário próprio é receita do mesmo
        # grupo, e a linha do grupo tem de mostrar o que ele paga ao todo.
        chave = str(empresa_id)
        chave = matriz_de.get(chave, chave)
        mensalidades[chave] = mensalidades.get(chave, Decimal(0)) + (
            override if override is not None else valor
        )

    # A filial não ocupa linha: horas, custo e receita dela já estão na matriz.
    ocultas = _empresas_ocultas_por_duplicidade(organization) | set(matriz_de)

    limiar = config.limiar_divergencia_horas * 60
    linhas = []
    # Every active company gets a row, including those with no hours: the
    # portfolio screens have to be able to show "sem dados" as a state rather
    # than as an absence.
    for empresa_id in CompanyErpProfile.objects.filter(
        organization=organization, empresa__active=True, deleted_at__isnull=True
    ).values_list("empresa_id", flat=True):
        chave = str(empresa_id)
        if chave in ocultas:
            continue
        acc = empresas.get(chave, _EmpresaAcc())
        pendente = chave in f9_pendentes

        custo = acc.custo.quantize(Decimal("0.01"))
        tem_mensalidade = chave in mensalidades
        mensalidade = mensalidades.get(chave, Decimal(0))
        motivos = set(acc.motivos_incompletude)
        if acc.tem_registros and not tem_mensalidade:
            motivos.add("mensalidade_nao_disponivel")
        custo_completo = not motivos
        resultado = calc.resultado(mensalidade, custo)
        margem = calc.margem(resultado, mensalidade)
        divergencia = (
            0 if pendente or not acc.tem_registros else abs(acc.auto_minutos - acc.f9_minutos)
        )

        linhas.append(
            ClienteCompetenciaMetrics(
                organization=organization,
                empresa_id=empresa_id,
                competencia=competencia,
                horas_auto_minutos=acc.auto_minutos,
                horas_f9_minutos=acc.f9_minutos,
                custo=custo,
                mensalidade=mensalidade,
                resultado=resultado,
                margem=margem.quantize(Decimal("0.000001")),
                faixa=(
                    "incompleta"
                    if not custo_completo
                    else calc.faixa_margem(
                        margem,
                        # Minuto que gera custo, não "existe uma linha de hora".
                        # `tem_registros` é verdadeiro para um apontamento de
                        # duração zero e para quem só tem F9 — e nos dois casos o
                        # custo é zero, a margem lê 100% e a empresa sobe ao topo
                        # da carteira como a mais rentável que existe. Foi o que
                        # aconteceu: seis clientes sem um minuto sequer apareciam
                        # como saudáveis com margem cheia. Sem hora automática não
                        # há base de custo, e a resposta certa é "sem dados".
                        #
                        # O piso generaliza isso: meia dúzia de minutos num mês
                        # inteiro não é custo do mês, é um pedaço dele, e a
                        # mensalidade cheia dividida por esse pedaço devolve
                        # margem quase plena pelo mesmo motivo errado. Medido na
                        # base do Fedrizzi em 18/09/2026, competência 2026-09:
                        # das 175 linhas que a carteira dava como "saudáveis",
                        # 70 tinham menos de 10 minutos apontados -- e todas liam
                        # margem acima de 90%, algumas com um único minuto no mês.
                        # Eram 40% da carteira saudável. O piso de 20 minutos pegaria
                        # 99 das 175; o escritório escolheu o corte mais conservador.
                        # Quanto basta é do escritório, não do código — por isso vem da
                        # configuração, e em 0 o comportamento anterior volta
                        # inteiro -- daí o `max(1, ...)`: piso zero ainda exige um
                        # minuto, senão quem não tem hora nenhuma passaria no teste.
                        tem_horas=acc.auto_minutos >= max(1, config.minutos_minimos_custo),
                        margem_atencao=config.margem_atencao,
                    )
                ),
                custo_completo=custo_completo,
                minutos_sem_custo=acc.minutos_sem_custo,
                motivos_incompletude=sorted(motivos),
                divergencia_minutos=divergencia,
                tem_divergencia=divergencia > limiar,
                f9_pendente=pendente,
            )
        )

    ClienteCompetenciaMetrics.objects.filter(
        organization=organization, competencia=competencia
    ).delete()
    ClienteCompetenciaMetrics.objects.bulk_create(linhas, batch_size=500)


def _rebuild_colaborador_metrics(
    organization: Organization,
    competencia: str,
    config: ProfitabilityConfig,
    colaboradores: dict[str, _ColaboradorAcc],
    custo_hora: dict[str, Decimal],
) -> None:
    limiar = config.limiar_divergencia_colaborador * 60
    linhas = []
    # Ativo, ou inativo que trabalhou neste mes. Filtrar so por `ativo` deixava
    # de fora quem saiu depois de ter trabalhado -- mas as horas dele continuam
    # entrando no custo do cliente, entao as duas telas nao fechavam. Quem esta
    # na competencia pertence a competencia.
    elegiveis = set(
        Colaborador.objects.filter(Q(organization=organization) & Q(ativo=True)).values_list(
            "id", flat=True
        )
    )
    elegiveis |= {
        colaborador_id
        for colaborador_id in Colaborador.objects.filter(
            organization=organization, id__in=[chave for chave in colaboradores]
        ).values_list("id", flat=True)
    }
    for colaborador_id in elegiveis:
        chave = str(colaborador_id)
        acc = colaboradores.get(chave, _ColaboradorAcc())
        hora = custo_hora.get(chave, Decimal(0))
        diferenca = acc.auto_comparavel - acc.f9_comparavel

        linhas.append(
            ColaboradorCompetenciaMetrics(
                organization=organization,
                colaborador_id=colaborador_id,
                competencia=competencia,
                horas_auto_minutos=acc.auto_minutos,
                horas_f9_minutos=acc.f9_minutos,
                diferenca_minutos=diferenca,
                custo=calc.custo_de_minutos(acc.auto_minutos, hora).quantize(Decimal("0.01")),
                custo_hora=hora.quantize(Decimal("0.0001")),
                # So e "sem salario" quem tem hora para custear: quem nao
                # trabalhou no mes nao tem custo a apurar, e marca-lo seria
                # apontar um problema que nao existe.
                sem_salario=acc.auto_minutos > 0 and chave not in custo_hora,
                empresas_count=len(acc.empresas),
                f9_pendente=acc.f9_pendente,
                divergente=abs(diferenca) > limiar,
            )
        )

    ColaboradorCompetenciaMetrics.objects.filter(
        organization=organization, competencia=competencia
    ).delete()
    ColaboradorCompetenciaMetrics.objects.bulk_create(linhas, batch_size=500)
