"""As telas do módulo Rentabilidade.

Seguem o idioma fixo da CICA: `office_required` para a porta, `_module_page_context`
para o portão do módulo e do colaborador, e `hub/workspace.html` como esqueleto.
Nada aqui reimplementa autorização — o que decide quem vê o quê continua sendo o
`CompanyAccessGrant` da carteira, que é a razão de D-109 ter mantido a carteira
única.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, cast

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, QuerySet, Sum
from django.http import HttpRequest, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from apps.audit.services import record_event
from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import _module_page_context, office_required, refuse
from apps.organizations.models import Membership, Organization
from apps.profitability.calc import custo_anual_colaborador
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
    capacidade_produtiva_mensal,
    colaboradores_da_competencia,
    evolucao_da_carteira,
    get_config,
    recompute_competencia,
    salario_vigente_map,
    vinculos_do_erp,
)

PAGINA = 20


@dataclass
class _Resumo:
    """O agregado que o cabeçalho da tela mostra."""

    clientes: int = 0
    com_horas: int = 0
    incompletos: int = 0
    custo: Decimal = Decimal(0)
    mensalidade: Decimal = Decimal(0)
    resultado: Decimal = Decimal(0)


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
    context, blocked = _module_page_context(request, definition(ProductModule.Code.PROFITABILITY))
    if blocked:
        return blocked
    office = cast(Organization, context["office"])

    # A carteira que o colaborador pode ver, não a do escritório inteiro: é o
    # filtro que a ficha de empresa já aplica, e a margem por cliente não pode
    # escapar dele.
    empresas_visiveis = cast("QuerySet[ClientCompany]", context["companies"])
    competencia = _competencia_selecionada(request, office)

    linhas = (
        ClienteCompetenciaMetrics.objects.filter(
            organization=office, competencia=competencia, empresa__in=empresas_visiveis
        )
        .select_related("empresa")
        .order_by("margem", "empresa__name")
        if competencia
        else ClienteCompetenciaMetrics.objects.none()
    )

    # Totais e cobertura sobre a carteira inteira que a pessoa vê, não sobre a
    # página: somar a página responderia outra pergunta.
    resumo = _Resumo()
    faixas: dict[str, int] = {valor: 0 for valor, _ in FaixaMargem.choices}
    for linha in linhas:
        resumo.clientes += 1
        resumo.custo += linha.custo
        resumo.mensalidade += linha.mensalidade
        resumo.resultado += linha.resultado
        if linha.horas_auto_minutos > 0:
            resumo.com_horas += 1
        if not linha.custo_completo:
            resumo.incompletos += 1
        faixas[linha.faixa] = faixas.get(linha.faixa, 0) + 1

    cobertura = round(resumo.com_horas * 100 / resumo.clientes) if resumo.clientes else 0

    paginator = Paginator(linhas, PAGINA)
    pagina = paginator.get_page(request.GET.get("page"))

    context.update(
        {
            "competencia": competencia,
            "competencias": _competencias(office),
            "linhas": pagina,
            "resumo": resumo,
            "faixas": faixas,
            "cobertura_horas": cobertura,
            "clientes_sem_horas": resumo.clientes - resumo.com_horas,
        }
    )
    return render(request, "profitability/overview.html", context)


def _e_admin(context: dict[str, Any]) -> bool:
    membership = context.get("membership")
    return bool(membership and membership.role in {Membership.Role.OWNER, Membership.Role.ADMIN})


def _pagina(request: HttpRequest, itens: Any, por_pagina: int = PAGINA) -> Any:
    return Paginator(itens, por_pagina).get_page(request.GET.get("page"))


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
