"""As telas do módulo Rentabilidade.

Seguem o idioma fixo da CICA: `office_required` para a porta, `_module_page_context`
para o portão do módulo e do colaborador, e `hub/workspace.html` como esqueleto.
Nada aqui reimplementa autorização — o que decide quem vê o quê continua sendo o
`CompanyAccessGrant` da carteira, que é a razão de D-109 ter mantido a carteira
única.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import cast

from django.core.paginator import Paginator
from django.db.models import QuerySet
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render
from django.views.decorators.http import require_http_methods

from apps.hub.models import ClientCompany, ProductModule
from apps.hub.module_catalog import definition
from apps.hub.views import _module_page_context, office_required
from apps.organizations.models import Organization
from apps.profitability.models import (
    ClienteCompetenciaMetrics,
    Competencia,
    FaixaMargem,
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
            "competencias": list(
                Competencia.objects.filter(organization=office).values_list(
                    "competencia", flat=True
                )
            ),
            "linhas": pagina,
            "resumo": resumo,
            "faixas": faixas,
            "cobertura_horas": cobertura,
            "clientes_sem_horas": resumo.clientes - resumo.com_horas,
        }
    )
    return render(request, "profitability/overview.html", context)
