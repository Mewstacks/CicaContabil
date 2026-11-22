"""Admissao por custo estimado (D-327, T4.6).

`TOP` limita a saida, nao o trabalho: antes de executar L1 ou L2 o programa pergunta ao servidor
quanto a consulta custa, **sem executa-la**, com `SELECT PLAN(?)` e o SQL interno como parametro
ligado (nada de aninhar aspas). O `PLAN` devolve `Estimated cost` e `Estimated rows`; medido: uma
agregacao indexada custa ~0,5, a varredura inteira de `efsaidas` ~1,0 e uma auto-juncao de 917 mil
linhas ~2,35e+06, tudo em poucos milissegundos.

O SQL interno vem so do compilador (literais tipados, `literals.py`). A resposta do `PLAN` e
validada pela forma antes de ser lida; qualquer coisa fora do padrao recusa a execucao. O limite
vem de `Limits.plan_cost_budget` (custo, sinal principal) e `plan_rows_budget`, **provisorios ate a
calibracao estimado x real de T4.9**.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Any, Protocol

from dominio_mcp.odbc import RawResult
from dominio_mcp.query_spec import QueryRefused

PLAN_SQL = "SELECT PLAN(?)"
MAX_PLAN_CHARS = 20_000
_PLAN_HEAD = re.compile(
    r"^\(\s*Plan\s*\[\s*Estimated cost:\s*([0-9.eE+\-]+),\s*Estimated rows:\s*([0-9.eE+\-]+)"
)


class Executor(Protocol):
    def __call__(
        self, sql: str, params: tuple[Any, ...] = (), *, max_rows: int, timeout: float | None = None
    ) -> RawResult: ...


@dataclass(frozen=True, slots=True)
class PlanEstimate:
    cost: float
    rows: float


def _invalid(message: str = "o servidor devolveu um plano fora do padrao esperado") -> QueryRefused:
    return QueryRefused("plano_invalido", message)


def parse_plan(text: object) -> PlanEstimate:
    if not isinstance(text, str) or not text or len(text) > MAX_PLAN_CHARS:
        raise _invalid()
    match = _PLAN_HEAD.match(text.lstrip())
    if match is None:
        raise _invalid()
    try:
        cost, rows = float(match.group(1)), float(match.group(2))
    except ValueError:
        raise _invalid("estimativa de custo ilegivel") from None
    if not (math.isfinite(cost) and math.isfinite(rows)) or cost < 0 or rows < 0:
        raise _invalid("estimativa de custo invalida")
    return PlanEstimate(cost, rows)


def estimate_plan(execute: Executor, literal_sql: str, *, timeout: float = 10.0) -> PlanEstimate:
    result = execute(PLAN_SQL, (literal_sql,), max_rows=2, timeout=timeout)
    if len(result.rows) != 1 or len(result.rows[0]) != 1:
        raise _invalid()
    return parse_plan(result.rows[0][0])


def admit(estimate: PlanEstimate, *, cost_budget: float, rows_budget: float) -> None:
    if estimate.cost > cost_budget:
        raise QueryRefused(
            "custo_estimado_alto",
            f"a consulta custaria {estimate.cost:.3g} no plano do servidor (limite "
            f"{cost_budget:g}): estreite com `codi_emp`, uma janela de datas menor ou menos "
            "juncoes",
            custo=estimate.cost,
            limite=cost_budget,
        )
    if estimate.rows > rows_budget:
        raise QueryRefused(
            "linhas_estimadas_demais",
            f"o plano estima {estimate.rows:.3g} linhas (limite {rows_budget:g}): estreite "
            "os filtros",
            linhas=estimate.rows,
            limite=rows_budget,
        )
