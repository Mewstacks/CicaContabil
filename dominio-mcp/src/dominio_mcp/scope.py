"""Escopo da consulta em tabela grande (D-327, T4.5).

`TOP` limita a saida, nao o trabalho. Antes de pedir a estimativa de custo, a consulta que toca
tabela grande precisa mostrar que e estreita:

- filtro de empresa (`codi_emp` com `=` ou `in`) em toda tabela grande que tem `codi_emp`; vale o
  filtro da propria tabela ou o de uma tabela ligada a ela por FK que carrega `codi_emp`;
- janela de datas fechada e de no maximo 13 meses, numa coluna de data de alguma **tabela grande**
  da consulta (a da propria tabela ou a de uma tabela-pai tambem grande, como `efsaidas` para
  `efmvspro`). Data de tabela pequena (cadastro da empresa) nao limita o movimento.

Tabela grande = mais de 50 mil linhas (estimativa do catalogo). A junção ja e limitada a 2 saltos
na validacao. A checagem de coluna lider de indice fica com o custo estimado (`admission.py`).
"""

from __future__ import annotations

from datetime import date, datetime

from dominio_mcp.query_spec import FilterItem, QueryRefused, ValidatedQuery, type_kind

BIG_TABLE_ROWS = 50_000
MAX_WINDOW_DAYS = 396  # 13 meses
COMPANY_COLUMN = "codi_emp"


def _as_date(value: object) -> date:
    return value.date() if isinstance(value, datetime) else value  # type: ignore[return-value]


def _company_groups(vq: ValidatedQuery) -> dict[str, set[str]]:
    """Aliases ligados entre si por uma juncao que carrega `codi_emp` dos dois lados."""
    alias_of = {qt.row.key: qt.alias for qt in vq.tables}
    parent = {qt.alias: qt.alias for qt in vq.tables}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for step in vq.joins:
        pairs = zip(step.from_columns, step.to_columns, strict=True)
        if any(a == COMPANY_COLUMN and b == COMPANY_COLUMN for a, b in pairs):
            parent[find(alias_of[step.from_table])] = find(alias_of[step.to_table])
    groups: dict[str, set[str]] = {}
    for alias in parent:
        groups.setdefault(find(alias), set()).add(alias)
    return groups


def _window_ok(filters: list[FilterItem]) -> tuple[bool, bool]:
    """(ha janela fechada valida, ha alguma janela fechada longa demais)."""
    bounds: dict[tuple[str, str], dict[str, list[date]]] = {}
    for flt in filters:
        if type_kind(flt.ref.column.type) not in ("date", "timestamp"):
            continue
        key = (flt.ref.table.alias, flt.ref.column.key)
        slot = bounds.setdefault(key, {"low": [], "high": []})
        values = [_as_date(v) for v in flt.values]
        if flt.op == "=":
            slot["low"].append(values[0])
            slot["high"].append(values[0])
        elif flt.op == "between":
            slot["low"].append(values[0])
            slot["high"].append(values[1])
        elif flt.op == "in":
            slot["low"].append(min(values))
            slot["high"].append(max(values))
        elif flt.op in (">", ">="):
            slot["low"].append(values[0])
        elif flt.op in ("<", "<="):
            slot["high"].append(values[0])
    ok = too_long = False
    for slot in bounds.values():
        if slot["low"] and slot["high"]:
            span = (min(slot["high"]) - max(slot["low"])).days
            if span < 0 or span <= MAX_WINDOW_DAYS:
                ok = True
            else:
                too_long = True
    return ok, too_long


def check_scope(vq: ValidatedQuery) -> None:
    big = [qt for qt in vq.tables if (qt.row.approx_rows or 0) > BIG_TABLE_ROWS]
    if not big:
        return
    filtered = {
        flt.ref.table.alias
        for flt in vq.filters
        if flt.ref.column.key == COMPANY_COLUMN and flt.op in ("=", "in")
    }
    groups = _company_groups(vq)
    covered: set[str] = set()
    for members in groups.values():
        if members & filtered:
            covered |= members
    for qt in big:
        if qt.has_company and qt.alias not in covered:
            raise QueryRefused(
                "sem_filtro_de_empresa",
                f"{qt.row.name} e uma tabela grande: filtre `{COMPANY_COLUMN}` com `=` ou `in`",
                tabela=qt.row.name,
            )
    # So conta a data de tabela grande: a data cadastral de um pai pequeno (`geempre.dina_emp`)
    # nao limita as linhas do movimento.
    big_aliases = {qt.alias for qt in big}
    ok, too_long = _window_ok([f for f in vq.filters if f.ref.table.alias in big_aliases])
    if not ok:
        if too_long:
            raise QueryRefused(
                "janela_de_datas_longa", "a janela de datas passa de 13 meses; reduza o periodo"
            )
        names = ", ".join(qt.row.name for qt in big)
        raise QueryRefused(
            "sem_janela_de_datas",
            f"a consulta toca tabela grande ({names}): informe uma janela fechada de ate 13 meses "
            "numa coluna de data (`between` ou `>=` e `<=`)",
        )
