"""Compilador da consulta estruturada L2 para SQL do SQL Anywhere (D-317, T4.2 a T4.4).

Entra uma `ValidatedQuery` (ja conferida contra o pack e a politica) e sai SQL com parametros `?`.
Nada aqui le texto do cliente como SQL: identificadores vem do catalogo (`quote_ident`), valores
vao por parametro. O compilador gera tambem a **versao com literais** usada so por
`SELECT PLAN(?)` na admissao por custo; se algum valor nao puder ser escrito com seguranca, a
compilacao inteira e recusada (nem estimativa nem execucao).

Dialeto: `SELECT [DISTINCT] TOP n START AT m`, `LIKE ? ESCAPE '!'`, junção `INNER JOIN` pela FK
declarada. Regra do banco (erro -854): com `DISTINCT`, o `ORDER BY` usa os apelidos da lista.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from dominio_mcp.literals import (
    UnsafeIdentifier,
    UnsafeLiteral,
    encode_literal,
    like_escape,
    qualified,
    quote_ident,
)
from dominio_mcp.query_spec import (
    CELL_FETCH_CHARS,
    ColRef,
    FilterItem,
    QueryRefused,
    SelectItem,
    ValidatedQuery,
    needs_cut,
    type_kind,
)

COUNT_HEADER = "__k"
_AGG_SQL = {
    "count": "COUNT({x})",
    "count_distinct": "COUNT(DISTINCT {x})",
    "sum": "SUM({x})",
    "avg": "AVG({x})",
    "min": "MIN({x})",
    "max": "MAX({x})",
}


@dataclass(frozen=True, slots=True)
class OutColumn:
    header: str
    mask: str  # none | documento | pessoal | texto
    category: str | None
    kind: str
    from_aggregate: bool
    hidden: bool = False


@dataclass(frozen=True, slots=True)
class CompiledQuery:
    sql: str
    params: tuple[Any, ...]
    literal_sql: str
    columns: tuple[OutColumn, ...]
    limit: int
    tables: tuple[str, ...]
    count_index: int | None
    # contagem de contribuicoes nao nulas de cada agregado pessoal (SUM de [9000, NULL, NULL] e
    # o salario de uma pessoa so, mesmo com tres linhas no grupo)
    contrib_indexes: tuple[int, ...] = ()


class _Emit:
    """Gera os pedacos do SQL: em modo literal escreve o valor; senao, `?` e guarda o parametro."""

    def __init__(self, *, literal: bool) -> None:
        self.literal = literal
        self.params: list[Any] = []

    def value(self, kind: str, value: Any) -> str:
        if self.literal:
            return encode_literal(kind, value)
        self.params.append(_odbc_value(kind, value))
        return "?"


def _odbc_value(kind: str, value: Any) -> Any:
    if kind == "bool":
        return int(value)
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, Decimal | date | datetime | str | int | float):
        return value
    return str(value)


def _column(ref: ColRef) -> str:
    return f"{quote_ident(ref.sql_alias)}.{quote_ident(ref.column.name)}"


def _fetch(ref: ColRef) -> str:
    """Coluna como vai para a saida: texto longo (ou de largura desconhecida) e cortado no servidor,
    senao `fetchmany` traria megabytes por celula antes do corte de 200 caracteres. Como o corte
    muda o valor, a validacao so deixa essa coluna ser lida, nunca agrupada nem ordenada."""
    column = _column(ref)
    return f"LEFT({column}, {CELL_FETCH_CHARS})" if needs_cut(ref.column) else column


def _select_sql(item: SelectItem) -> str:
    if item.kind == "col":
        assert item.ref is not None
        expr = _fetch(item.ref)
    elif item.ref is None:
        expr = "COUNT(*)"
    else:
        assert item.func is not None
        target = _fetch(item.ref) if item.func in ("min", "max") else _column(item.ref)
        expr = _AGG_SQL[item.func].format(x=target)
    return f"{expr} AS {quote_ident(item.header)}"


def _filter_sql(flt: FilterItem, emit: _Emit) -> str:
    col = _column(flt.ref)
    kind = flt.kind
    op = flt.op
    if op == "is_null":
        return f"{col} IS NULL"
    if op == "not_null":
        return f"{col} IS NOT NULL"
    if op == "in":
        marks = ", ".join(emit.value(kind, v) for v in flt.values)
        return f"{col} IN ({marks})"
    if op == "between":
        low, high = flt.values
        return f"{col} BETWEEN {emit.value(kind, low)} AND {emit.value(kind, high)}"
    if op in ("prefix", "contains"):
        text = like_escape(str(flt.values[0]))
        pattern = f"{text}%" if op == "prefix" else f"%{text}%"
        return f"{col} LIKE {emit.value('text', pattern)} ESCAPE '!'"
    return f"{col} {op} {emit.value(kind, flt.values[0])}"


def _build(
    vq: ValidatedQuery, owner: str, emit: _Emit
) -> tuple[str, tuple[OutColumn, ...], int | None, tuple[int, ...]]:
    select_items = list(vq.select)
    columns: list[OutColumn] = []
    for item in select_items:
        if item.kind == "col":
            assert item.ref is not None
            access = item.ref.access
            columns.append(
                OutColumn(
                    item.header,
                    access.mask,
                    item.ref.column.category,
                    type_kind(item.ref.column.type),
                    False,
                )
            )
        else:
            kind = "int" if item.func in ("count", "count_distinct") else "decimal"
            columns.append(OutColumn(item.header, "none", None, kind, True))
    parts = [_select_sql(item) for item in select_items]
    count_index: int | None = None
    contrib: list[int] = []
    if vq.suppress_small_groups:
        count_index = len(parts)
        parts.append(f"COUNT(*) AS {quote_ident(COUNT_HEADER)}")
        columns.append(OutColumn(COUNT_HEADER, "none", None, "int", True, hidden=True))
        for number, item in enumerate(select_items):
            if (
                item.kind == "agg"
                and item.ref is not None
                and item.ref.access.suppress_small_groups
            ):
                header = f"{COUNT_HEADER}{number}"
                contrib.append(len(parts))
                measure = _column(item.ref)
                if item.person is not None:  # pessoas distintas com valor, nao linhas
                    count = (
                        f"COUNT(DISTINCT CASE WHEN {measure} IS NOT NULL "
                        f"THEN {_column(item.person)} END)"
                    )
                else:
                    count = f"COUNT({measure})"
                parts.append(f"{count} AS {quote_ident(header)}")
                columns.append(OutColumn(header, "none", None, "int", True, hidden=True))

    head = "SELECT " + ("DISTINCT " if vq.distinct else "")
    head += f"TOP {vq.limit + 1} START AT {vq.offset + 1} "
    base = vq.tables[0]
    sql = [
        head + ", ".join(parts),
        f"FROM {qualified(owner, base.row.name)} AS {quote_ident('t0')}",
    ]
    alias_of = {qt.row.key: qt.alias for qt in vq.tables}
    names = {qt.alias: qt.row.name for qt in vq.tables}
    for step in vq.joins:
        left, right = alias_of[step.from_table], alias_of[step.to_table]
        on = " AND ".join(
            f"{quote_ident(left)}.{quote_ident(a)} = {quote_ident(right)}.{quote_ident(b)}"
            for a, b in zip(step.from_columns, step.to_columns, strict=True)
        )
        sql.append(f"INNER JOIN {qualified(owner, names[right])} AS {quote_ident(right)} ON {on}")
    if vq.filters:
        sql.append("WHERE " + " AND ".join(_filter_sql(f, emit) for f in vq.filters))
    if vq.group_by:
        sql.append("GROUP BY " + ", ".join(_fetch(g) for g in vq.group_by))
    if vq.order_by:
        sql.append("ORDER BY " + ", ".join(_order_sql(vq, o) for o in vq.order_by))
    return "\n".join(sql), tuple(columns), count_index, tuple(contrib)


def _order_sql(vq: ValidatedQuery, order: Any) -> str:
    direction = " DESC" if order.desc else ""
    if order.header is not None:
        return f"{quote_ident(order.header)}{direction}"
    ref: ColRef = order.ref
    if vq.distinct:
        for item in vq.select:
            if item.ref is not None and (item.ref.table.alias, item.ref.column.key) == (
                ref.table.alias,
                ref.column.key,
            ):
                return f"{quote_ident(item.header)}{direction}"
    return f"{_fetch(ref)}{direction}"


def compile_query(vq: ValidatedQuery, owner: str) -> CompiledQuery:
    try:
        emit = _Emit(literal=False)
        sql, columns, count_index, contrib = _build(vq, owner, emit)
        literal_sql = _build(vq, owner, _Emit(literal=True))[0]
    except UnsafeLiteral:
        raise QueryRefused(
            "valor_nao_codificavel",
            "um valor do filtro nao pode ser escrito com seguranca (barra invertida, caractere de "
            "controle ou texto longo demais)",
        ) from None
    except UnsafeIdentifier:
        raise QueryRefused(
            "identificador_invalido", "o catalogo tem um nome que nao pode ser citado com seguranca"
        ) from None
    return CompiledQuery(
        sql=sql,
        params=tuple(emit.params),
        literal_sql=literal_sql,
        columns=columns,
        limit=vq.limit,
        tables=tuple(qt.row.name for qt in vq.tables),
        count_index=count_index,
        contrib_indexes=contrib,
    )
