"""Filtros de apresentação do módulo Rentabilidade."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation
from urllib.parse import urlencode

from django import template
from django.http import QueryDict

register = template.Library()


@register.filter
def horas(minutos: object) -> str:
    """Minutos em horas e minutos.

    O fato é gravado em minutos inteiros porque somas em float derivam depois de
    algumas centenas de milhares de linhas. Quem lê a tela, porém, pensa em horas:
    `90 min` é aritmética, `1h30` é a jornada.
    """

    try:
        total = int(minutos)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return "—"
    if total <= 0:
        return "—"
    return f"{total // 60}h{total % 60:02d}"


@register.filter
def horas_assinadas(minutos: object) -> str:
    """Diferença de minutos preservando o sinal e o zero.

    O filtro `horas` usa travessão para zero porque zero hora numa carteira é
    ausência de trabalho. Numa conciliação, porém, zero é justamente a resposta:
    as duas fontes fecharam.
    """

    try:
        total = int(minutos)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return "—"
    sinal = "-" if total < 0 else "+" if total > 0 else ""
    absoluto = abs(total)
    return f"{sinal}{absoluto // 60}h{absoluto % 60:02d}"


@register.filter
def percentual(valor: object, casas: int = 1) -> str:
    """Uma fração exibida como percentual.

    Os parâmetros são guardados como fração — 0,3500 — porque é assim que entram
    na conta. Na tela isso lê como trinta e cinco centésimos de por cento, que é
    cem vezes menor do que a pessoa configurou.
    """

    try:
        numero = Decimal(str(valor)) * 100
    except (TypeError, ValueError, InvalidOperation):
        return "—"
    return f"{numero:.{casas}f}".replace(".", ",") + "%"


@register.filter
def pontos(valor: object) -> str:
    """Uma diferença de margem lida em pontos percentuais.

    "A margem subiu 20%" sobre uma margem de 5% é ambíguo: pode ser 6% ou 25%.
    "Subiu 1 ponto" não é.
    """

    try:
        numero = Decimal(str(valor)) * 100
    except (TypeError, ValueError, InvalidOperation):
        return "—"
    sinal = "+" if numero > 0 else ""
    return f"{sinal}{numero:.1f}".replace(".", ",") + " p.p."


@register.filter
def participacao(parte: object, total: object) -> str:
    """Quanto uma parte pesa no total, em percentual."""

    try:
        numerador = Decimal(str(parte))
        denominador = Decimal(str(total))
    except (TypeError, ValueError, InvalidOperation):
        return "—"
    if denominador == 0:
        return "—"
    return percentual(numerador / denominador)


@register.filter
def pagina_url(parametros: QueryDict, numero: int) -> str:
    """Mantém os filtros correntes ao mudar de página.

    Uma paginação que descarta o filtro devolve a pessoa à lista inteira sem
    avisar, e ela costuma não perceber que mudou de pergunta.
    """

    itens = {chave: valor for chave, valor in parametros.items() if chave != "page"}
    itens["page"] = str(numero)
    return urlencode(itens)
