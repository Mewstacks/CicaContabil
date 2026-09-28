"""As telas do módulo Rentabilidade.

Seguem o idioma fixo da CICA: `office_required` para a porta, `_module_page_context`
para o portão do módulo e do colaborador, e `hub/workspace.html` como esqueleto.
Nada aqui reimplementa autorização — o que decide quem vê o quê continua sendo o
`CompanyAccessGrant` da carteira, que é a razão de D-109 ter mantido a carteira
única.
"""

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any, cast

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Count, Q, QuerySet, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.audit.services import record_event
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import _module_page_context, office_required, refuse
from apps.organizations.models import Membership, Organization
from apps.profitability.calc import custo_anual_colaborador, mensalidade_sugerida
from apps.profitability.forms import ProfitabilityConfigForm
from apps.profitability.matching import aplicar_vinculo
from apps.profitability.models import (
    ClienteCompetenciaMetrics,
    Colaborador,
    ColaboradorCompetenciaMetrics,
    Competencia,
    FaixaMargem,
    OrigemHoras,
    RegistroHoras,
    Segmento,
    StatusRegistro,
    UsuarioErp,
)
from apps.profitability.services import (
    agrupar_carteira,
    atividades_f9,
    capacidade_produtiva_mensal,
    colaboradores_da_competencia,
    colaboradores_do_cliente,
    comparacoes_do_cliente,
    competencia_anterior,
    concentracao_de_receita,
    evolucao_da_carteira,
    frescor_das_importacoes,
    get_config,
    historico_do_cliente,
    horas_por_dia,
    mapa_da_carteira,
    ocupacao_da_equipe,
    receita_fora_da_meta,
    recompute_competencia,
    salario_vigente_map,
    totais_da_carteira,
    unidades_do_grupo,
    variacao,
    vinculos_do_erp,
)

PAGINA = 20

AGRUPAMENTOS = (
    ("segmento", "Segmento"),
    ("regime", "Regime tributário"),
    ("responsavel", "Responsável"),
)


def _competencias(office: Organization) -> list[str]:
    return list(
        Competencia.objects.filter(organization=office).values_list("competencia", flat=True)
    )


def _competencia_selecionada(request: HttpRequest, office: Organization) -> str:
    """A competência da tela: a pedida, a marcada como atual, ou a mais recente."""

    pedida = request.GET.get("competencia", "").strip()
    disponiveis = list(
        Competencia.objects.filter(organization=office).values_list("competencia", flat=True)
    )
    if pedida in disponiveis:
        return pedida
    atual = (
        Competencia.objects.filter(organization=office, is_atual=True)
        .values_list("competencia", flat=True)
        .first()
    )
    return atual or (disponiveis[0] if disponiveis else "")


@office_required
@require_http_methods(["GET"])
def overview(request: HttpRequest) -> HttpResponse:
    """O painel executivo da competência.

    Cada bloco responde a uma pergunta de negócio, e não a uma consulta de banco:
    para onde o número foi, de que dado ele depende, onde a carteira concentra
    receita, quem da equipe não apareceu, e quanto de reajuste está na mesa.
    """

    context, blocked = _module_page_context(request, definition(ProductModule.Code.PROFITABILITY))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])

    # A carteira que o colaborador pode ver, não a do escritório inteiro: é o
    # filtro que a ficha de empresa já aplica, e a margem por cliente não pode
    # escapar dele.
    empresas = cast("QuerySet[ClientCompany]", context["companies"])
    competencia = _competencia_selecionada(request, office)
    if not competencia:
        context.update({"competencia": "", "competencias": [], "page_title": "Rentabilidade"})
        return render(request, "profitability/overview.html", context)

    config = get_config(office)
    totais = totais_da_carteira(office, competencia, empresas=empresas)
    anterior = totais_da_carteira(office, competencia_anterior(competencia), empresas=empresas)
    evolucao = evolucao_da_carteira(office, competencia, meses=12, empresas=empresas)
    pessoas, horas_lancadas, horas_disponiveis, sem_horas = ocupacao_da_equipe(
        office, competencia, config
    )
    reajustes, reajuste_total = receita_fora_da_meta(office, competencia, config, empresas=empresas)
    maiores, soma_maiores, participacao = concentracao_de_receita(
        office, competencia, empresas=empresas
    )
    mapa, fora_do_mapa = mapa_da_carteira(office, competencia, empresas=empresas)
    ultima_importacao, datasets = frescor_das_importacoes(office)
    por_faixa = _contagem_por_faixa(office, competencia, empresas)
    ocupacao_geral = (horas_lancadas / horas_disponiveis) if horas_disponiveis > 0 else Decimal(0)

    context.update(
        {
            "competencia": competencia,
            "competencias": _competencias(office),
            "totais": totais,
            # Sem competência anterior a variação é omitida, nunca zerada: zero
            # afirma que o número ficou parado, o que não é o mesmo que não haver
            # com o que comparar.
            "variacoes": {
                "receita": variacao(totais.receita, anterior.receita),
                "custo": variacao(totais.custo, anterior.custo),
                "resultado": variacao(totais.resultado, anterior.resultado),
                "ticket": variacao(totais.ticket_medio, anterior.ticket_medio),
                # Margem anda em pontos percentuais, não em porcentagem de si
                # mesma: "a margem subiu 20%" sobre 5% é ambíguo, "subiu 1 ponto"
                # não é.
                "margem_pp": totais.margem - anterior.margem,
            },
            "tem_anterior": anterior.clientes > 0,
            "evolucao": evolucao,
            "evolucao_json": _serie_json(evolucao),
            "cobertura_custo": (
                round((totais.clientes - totais.incompletos) * 100 / totais.clientes)
                if totais.clientes
                else 0
            ),
            "ultima_importacao": ultima_importacao,
            "datasets": datasets,
            "mapa": mapa,
            "mapa_json": _mapa_json(mapa),
            "fora_do_mapa": fora_do_mapa,
            "maiores": maiores,
            "soma_maiores": soma_maiores,
            "participacao_maiores": participacao,
            "grupos": agrupar_carteira(
                office, competencia, por=_agrupamento(request), empresas=empresas
            ),
            "por": _agrupamento(request),
            "agrupamentos": AGRUPAMENTOS,
            "ocupacao": pessoas[:12],
            "ocupacao_geral": ocupacao_geral,
            "horas_lancadas": horas_lancadas,
            "horas_disponiveis": horas_disponiveis,
            "sem_horas": sem_horas,
            "equipe": len(pessoas),
            "reajustes": reajustes[:10],
            "reajuste_total": reajuste_total,
            "reajuste_quantidade": len(reajustes),
            "faixas": por_faixa,
            "carteira": _pagina(
                request,
                ClienteCompetenciaMetrics.objects.filter(
                    organization=office, competencia=competencia, empresa__in=empresas
                )
                .select_related("empresa")
                .order_by("margem", "empresa__name"),
            ),
            "page_title": "Rentabilidade",
        }
    )
    return render(request, "profitability/overview.html", context)


def _contagem_por_faixa(office: Organization, competencia: str, empresas: Any) -> dict[str, int]:
    contagem = {valor: 0 for valor, _ in FaixaMargem.choices}
    for linha in (
        ClienteCompetenciaMetrics.objects.filter(
            organization=office, competencia=competencia, empresa__in=empresas
        )
        .values("faixa")
        .annotate(total=Count("id"))
    ):
        contagem[str(linha["faixa"])] = int(linha["total"])
    return contagem


def _serie_json(evolucao: list[dict[str, Any]]) -> str:
    return json.dumps(
        [
            {
                "competencia": item["competencia"],
                "mensalidade": float(item["mensalidade"]),
                "custo": float(item["custo"]),
                "margem": float(item["margem"]),
            }
            for item in evolucao
        ]
    )


def _mapa_json(linhas: list[ClienteCompetenciaMetrics]) -> str:
    """O mapa da carteira: um retângulo por cliente, área pela receita.

    Área proporcional à receita e cor pela faixa. O gráfico anterior era de
    dispersão, uma bolha por cliente — e como o custo subapurado empurra quase
    todos para margem alta, as bolhas se empilhavam numa faixa estreita e nenhuma
    era legível. Retângulo não sobrepõe: densidade vira área em vez de borrão.
    """

    return json.dumps(
        [
            {
                "nome": linha.empresa.name,
                "valor": float(linha.mensalidade),
                "faixa": linha.faixa,
                "margem": float(linha.margem),
            }
            for linha in linhas
        ]
    )


def _agrupamento(request: HttpRequest) -> str:
    pedido = request.GET.get("por", "segmento")
    return pedido if pedido in {valor for valor, _ in AGRUPAMENTOS} else "segmento"


def _e_admin(context: dict[str, Any]) -> bool:
    membership = context.get("membership")
    return bool(membership and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN})


def _pagina(request: HttpRequest, itens: Any, por_pagina: int = PAGINA) -> Any:
    return Paginator(itens, por_pagina).get_page(request.GET.get("page"))


@office_required
@require_http_methods(["GET"])
def client_detail(request: HttpRequest, company_id: str) -> HttpResponse:
    """A memória analítica de um cliente dentro da carteira autorizada.

    A ficha do Hub continua sendo o cadastro transversal da empresa. Esta rota
    responde à pergunta específica do módulo — de onde vieram custo, horas,
    margem e comparação — sem recriar a entidade `ClientCompany` que D-109
    descartou.
    """

    context, blocked = _module_page_context(request, definition(ProductModule.Code.PROFITABILITY))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    empresas_visiveis = cast("QuerySet[ClientCompany]", context["companies"])
    empresa = get_object_or_404(empresas_visiveis, pk=company_id)
    competencia = _competencia_selecionada(request, office)
    metrica = ClienteCompetenciaMetrics.objects.filter(
        organization=office, empresa=empresa, competencia=competencia
    ).first()
    config = get_config(office)
    perfil = empresa.erp_profiles.order_by("-sistema_origem").first()
    margem_alvo = (
        config.margem_alvo_padrao
        if config.margem_alvo_global or perfil is None or perfil.margem_alvo is None
        else perfil.margem_alvo
    )
    sugerida = (
        mensalidade_sugerida(metrica.custo, margem_alvo)
        if metrica is not None and metrica.custo_completo and metrica.faixa != FaixaMargem.SEM_DADOS
        else None
    )
    historico = historico_do_cliente(office, empresa)
    ids_visiveis = set(empresas_visiveis.values_list("id", flat=True))
    unidades = (
        [
            unidade
            for unidade in unidades_do_grupo(office, competencia, str(empresa.id))
            if unidade.empresa.id in ids_visiveis
        ]
        if competencia
        else []
    )

    context.update(
        {
            "empresa": empresa,
            "perfil": perfil,
            "is_admin": _e_admin(context),
            "competencia": competencia,
            "competencias": _competencias(office),
            "metrica": metrica,
            "margem_alvo": margem_alvo,
            "mensalidade_sugerida": sugerida,
            "colaboradores": colaboradores_do_cliente(
                office,
                empresa,
                competencia,
                empresas_visiveis=empresas_visiveis,
            )
            if competencia
            else [],
            "horas_por_dia": horas_por_dia(
                office,
                empresa,
                competencia,
                empresas_visiveis=empresas_visiveis,
            )
            if competencia
            else [],
            "atividades": atividades_f9(
                office,
                empresa,
                competencia,
                empresas_visiveis=empresas_visiveis,
            )
            if competencia
            else [],
            "comparacoes": comparacoes_do_cliente(
                office,
                empresa,
                competencia,
                empresas_visiveis=empresas_visiveis,
            )
            if competencia
            else [],
            "historico": historico,
            "historico_json": json.dumps(
                [
                    {
                        "competencia": linha.competencia,
                        "mensalidade": float(linha.mensalidade),
                        "custo": float(linha.custo),
                        "margem": float(linha.margem),
                    }
                    for linha in reversed(historico)
                ]
            ),
            "unidades": unidades if len(unidades) > 1 else [],
            "page_title": empresa.name,
        }
    )
    return render(request, "profitability/client_detail.html", context)


@office_required
@require_http_methods(["GET", "POST"])
def collaborators(request: HttpRequest) -> HttpResponse:
    """Quem trabalhou no mês, e quais logins do ERP ainda não têm dono.

    As duas coisas moram na mesma tela porque são a mesma pergunta vista de dois
    lados: um login sem colaborador é uma hora que existe e não gera custo, e é a
    maior causa isolada de margem irreal.
    """

    context, blocked = _module_page_context(request, definition(ProductModule.Code.PROFITABILITY))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    competencia = _competencia_selecionada(request, office)
    admin = _e_admin(context)

    if request.method == "POST":
        if not context["support_can_mutate"]:
            return refuse(request, "Esta sessão é somente leitura.")
        if not admin:
            return refuse(request, "Só um administrador decide um vínculo do ERP.")
        return _salvar_vinculo(request, office, competencia)

    pessoas = colaboradores_da_competencia(
        office, competencia, busca=request.GET.get("q", "").strip()
    )
    vinculos = vinculos_do_erp(office, competencia) if competencia else []
    somente_pendentes = request.GET.get("vinculos", "pendentes") != "todos"
    if somente_pendentes:
        vinculos = [item for item in vinculos if item.estado in {"sem_vinculo", "empate"}]

    context.update(
        {
            "competencia": competencia,
            "competencias": _competencias(office),
            "busca": request.GET.get("q", "").strip(),
            "linhas": _pagina(request, pessoas, 10),
            "vinculos": vinculos,
            "vinculos_pendentes": somente_pendentes,
            "is_admin": admin,
            "folha": (
                Colaborador.objects.filter(organization=office, ativo=True).order_by("codigo")
                if admin
                else Colaborador.objects.none()
            ),
            "page_title": "Colaboradores",
        }
    )
    return render(request, "profitability/collaborators.html", context)


def _salvar_vinculo(request: HttpRequest, office: Organization, competencia: str) -> HttpResponse:
    """Liga (ou desliga) um login do ERP e reprojeta o que isso mudou.

    Reprojetar aqui não é zelo: `RegistroHoras.colaborador` foi gravado na
    importação, então consertar o vínculo não conserta as horas que já estão no
    banco, e sem isso a tela continua mostrando o número velho.
    """

    usuario = get_object_or_404(UsuarioErp, pk=request.POST.get("usuario", ""), organization=office)
    escolhido = request.POST.get("colaborador", "").strip()
    colaborador = (
        get_object_or_404(Colaborador, pk=escolhido, organization=office) if escolhido else None
    )
    competencias = aplicar_vinculo(usuario, colaborador.id if colaborador else None, manual=True)
    for tocada in competencias:
        recompute_competencia(office, tocada)
    record_event(
        action="profitability.erp_user.linked",
        actor=request.user,
        organization=office,
        target=usuario,
        request=request,
        metadata={"vinculado": colaborador is not None, "competencias": len(competencias)},
    )
    messages.success(
        request,
        (
            f"Vínculo gravado. {len(competencias)} competência"
            f"{'s' if len(competencias) != 1 else ''} recalculada"
            f"{'s' if len(competencias) != 1 else ''}."
        )
        if competencias
        else "Vínculo gravado. Nenhuma hora deste login precisou ser recalculada.",
    )
    destino = f"{reverse('profitability:collaborators')}?competencia={competencia}"
    return redirect(destino)


@office_required
@require_http_methods(["GET"])
def collaborator_detail(request: HttpRequest, collaborator_id: str) -> HttpResponse:
    """A ficha de uma pessoa: horas, logins do ERP e, para administrador, o custo."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.PROFITABILITY))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    colaborador = get_object_or_404(Colaborador, pk=collaborator_id, organization=office)
    competencia = _competencia_selecionada(request, office)
    admin = _e_admin(context)

    metrica = ColaboradorCompetenciaMetrics.objects.filter(
        organization=office, colaborador=colaborador, competencia=competencia
    ).first()
    config = get_config(office)

    custo_anual = None
    salario = None
    if admin:
        vigente = salario_vigente_map(office, competencia).get(str(colaborador.id))
        if vigente is not None:
            _, salario = vigente
            if colaborador.contratacao != Colaborador.Contratacao.PJ:
                custo_anual = custo_anual_colaborador(
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

    context.update(
        {
            "colaborador": colaborador,
            "competencia": competencia,
            "competencias": _competencias(office),
            "metrica": metrica,
            "logins": list(UsuarioErp.objects.filter(organization=office, colaborador=colaborador)),
            "is_admin": admin,
            "salario": salario,
            "custo_anual": custo_anual,
            "config": config,
            "capacidade_mes": capacidade_produtiva_mensal(config, colaborador),
            "page_title": colaborador.codigo or "Colaborador",
        }
    )
    return render(request, "profitability/collaborator_detail.html", context)


@office_required
@require_http_methods(["GET"])
def hours(request: HttpRequest) -> HttpResponse:
    """Reconciliar o que o ERP registrou sozinho com o que a equipe apontou."""

    context, blocked = _module_page_context(request, definition(ProductModule.Code.PROFITABILITY))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    competencia = _competencia_selecionada(request, office)
    empresas_visiveis = cast("QuerySet[ClientCompany]", context["companies"])

    registros = (
        RegistroHoras.objects.filter(
            organization=office,
            competencia=competencia,
            deleted_at__isnull=True,
            empresa__in=empresas_visiveis,
        )
        .select_related("empresa", "colaborador", "usuario_erp")
        .order_by("-data", "inicio")
        if competencia
        else RegistroHoras.objects.none()
    )

    filtro = request.GET.get("filtro", "todas")
    if filtro == "automaticas":
        registros = registros.filter(origem=OrigemHoras.AUTOMATICA)
    elif filtro == "f9":
        registros = registros.filter(origem=OrigemHoras.F9)
    elif filtro == "divergentes":
        registros = registros.filter(status=StatusRegistro.DIVERGENTE)

    totais = registros.aggregate(
        auto=Sum("duracao_minutos", filter=Q(origem=OrigemHoras.AUTOMATICA)),
        f9=Sum("duracao_minutos", filter=Q(origem=OrigemHoras.F9)),
    )
    auto = int(totais["auto"] or 0)
    f9 = int(totais["f9"] or 0)

    context.update(
        {
            "competencia": competencia,
            "competencias": _competencias(office),
            "filtro": filtro,
            "filtros": (
                ("todas", "Todas"),
                ("automaticas", "Automáticas"),
                ("f9", "F9"),
                ("divergentes", "Divergentes"),
            ),
            "linhas": _pagina(request, registros),
            "minutos_auto": auto,
            "minutos_f9": f9,
            "minutos_diferenca": auto - f9,
            "page_title": "Horas",
        }
    )
    return render(request, "profitability/hours.html", context)


@office_required
@require_http_methods(["GET"])
def analyses(request: HttpRequest) -> HttpResponse:
    """A carteira olhada por recorte, e não cliente a cliente.

    A pergunta aqui é outra da visão geral: lá se procura o cliente a tratar, aqui
    se procura o padrão — qual segmento, regime ou responsável concentra prejuízo.
    """

    context, blocked = _module_page_context(request, definition(ProductModule.Code.PROFITABILITY))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    competencia = _competencia_selecionada(request, office)
    empresas_visiveis = cast("QuerySet[ClientCompany]", context["companies"])

    por = request.GET.get("por", "segmento")
    if por not in {"segmento", "regime", "responsavel"}:
        por = "segmento"

    grupos = (
        agrupar_carteira(office, competencia, por=por, empresas=empresas_visiveis)
        if competencia
        else []
    )
    evolucao = evolucao_da_carteira(office, competencia, meses=12, empresas=empresas_visiveis)

    context.update(
        {
            "competencia": competencia,
            "competencias": _competencias(office),
            "por": por,
            "agrupamentos": (
                ("segmento", "Segmento"),
                ("regime", "Regime tributário"),
                ("responsavel", "Responsável"),
            ),
            "grupos": grupos,
            "evolucao": evolucao,
            "evolucao_json": json.dumps(
                [
                    {
                        "competencia": item["competencia"],
                        "mensalidade": float(item["mensalidade"]),
                        "custo": float(item["custo"]),
                        "margem": float(item["margem"]),
                    }
                    for item in evolucao
                ]
            ),
            "page_title": "Análises",
        }
    )
    return render(request, "profitability/analyses.html", context)


@office_required
@require_http_methods(["GET", "POST"])
def settings_view(request: HttpRequest) -> HttpResponse:
    """Os parâmetros que alimentam o custo de toda a carteira.

    Salvar aqui reprojeta todas as competências na hora. Antes de existir esse
    passo, a carteira só mudava na importação seguinte enquanto a ficha do cliente,
    que recalcula a cada pedido, mudava na hora — e as duas telas se contradiziam.
    """

    context, blocked = _module_page_context(request, definition(ProductModule.Code.PROFITABILITY))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])
    admin = _e_admin(context)
    config = get_config(office)

    if request.method == "POST":
        if not context["support_can_mutate"]:
            return refuse(request, "Esta sessão é somente leitura.")
        if not admin:
            return refuse(request, "Só um administrador altera os parâmetros de custo.")
        form = ProfitabilityConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            competencias = _competencias(office)
            for competencia in competencias:
                recompute_competencia(office, competencia)
            record_event(
                action="profitability.config.updated",
                actor=request.user,
                organization=office,
                target=config,
                request=request,
                metadata={"competencias_reprojetadas": len(competencias)},
            )
            messages.success(
                request,
                f"Parâmetros gravados e {len(competencias)} competência"
                f"{'s' if len(competencias) != 1 else ''} recalculada"
                f"{'s' if len(competencias) != 1 else ''}.",
            )
            return redirect("profitability:settings")
    else:
        form = ProfitabilityConfigForm(instance=config)

    context.update(
        {
            "form": form,
            "config": config,
            "is_admin": admin,
            "segmentos": Segmento.objects.filter(organization=office),
            "competencias": _competencias(office),
            "page_title": "Configuração da rentabilidade",
        }
    )
    return render(request, "profitability/settings.html", context)
