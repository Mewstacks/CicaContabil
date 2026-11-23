"""L3: SQL somente leitura como porta de entrada da consulta estruturada (D-330, M9).

Nao ha filtro lexico de SQL arbitrario aqui. O texto e lido por uma gramatica minima e **traduzido**
para `ConsultaEstruturada`; dali em diante vale tudo o que vale em L2 (pack, politica de dados,
escopo de tabela grande, compilacao parametrizada, admissao por custo, moldagem). Qualquer
construcao fora da gramatica e recusada, nunca "limpa":

    SELECT [DISTINCT] [TOP n] item {, item}
    FROM tabela [[AS] apelido]
    {[INNER] JOIN tabela [[AS] apelido] ON a.c = b.c {AND a.c = b.c}}
    [WHERE pred {AND pred}]
    [GROUP BY ref {, ref}]
    [ORDER BY (ref | apelido) [ASC|DESC] {, ...}]
    [LIMIT n [OFFSET m]]

    item = ref | (COUNT|SUM|AVG|MIN|MAX) '(' [DISTINCT] (ref | '*') ')' AS apelido
    pred = ref (=|<>|!=|<|<=|>|>=) literal | ref IN '(' literal {, literal} ')'
         | ref BETWEEN literal AND literal | ref IS [NOT] NULL
         | ref LIKE 'texto%' | ref LIKE '%texto%'

Fora: `*`, expressao, funcao escalar, subconsulta, CTE, `UNION`, `OR`, `NOT`, parenteses em filtro,
`HAVING`, identificador entre aspas, comentario, `;`, qualquer caractere nao ASCII fora de texto
entre aspas simples e qualquer juncao cujo `ON` nao seja exatamente a FK declarada.

Com juncao, toda coluna precisa de apelido (a traducao nao adivinha de qual tabela vem).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, NamedTuple

from dominio_mcp.query_spec import (
    AggFunc,
    Agregacao,
    ConsultaEstruturada,
    Filtro,
    Juncao,
    Ordem,
    QueryRefused,
    ValidatedQuery,
)

MAX_SQL_CHARS = 4000
MAX_TOKENS = 400
SHOWN_TOKEN = 40
_AGG_FUNCS: dict[str, AggFunc] = {
    "COUNT": "count",
    "SUM": "sum",
    "AVG": "avg",
    "MIN": "min",
    "MAX": "max",
}
_RESERVED = frozenset(
    {
        "SELECT", "FROM", "WHERE", "GROUP", "BY", "ORDER", "JOIN", "INNER", "LEFT", "RIGHT",
        "FULL", "OUTER", "CROSS", "ON", "AS", "AND", "OR", "NOT", "IN", "IS", "NULL", "LIKE",
        "BETWEEN", "TOP", "LIMIT", "OFFSET", "DISTINCT", "ASC", "DESC", "HAVING", "UNION",
        "ALL", "INTO", "WITH", "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END", "INTERSECT",
        "EXCEPT", "CALL", "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "SET",
        "EXEC", "EXECUTE", "FOR", "START", "AT",
    }
)  # fmt: skip
_COMPARISONS = {"=": "=", "<>": "!=", "!=": "!=", "<": "<", "<=": "<=", ">": ">", ">=": ">="}
_ALIAS_RX = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,40}$")


class RawSqlRefused(QueryRefused):
    """Recusa da gramatica: mesmo contrato de erro de L2 (`code` estavel, mensagem curta)."""


def _refuse(message: str, **details: Any) -> RawSqlRefused:
    return RawSqlRefused("sql_recusado", message, **details)


class Tok(NamedTuple):
    kind: str  # word | num | str | op | end
    text: str
    pos: int


def _shown(text: str) -> str:
    one_line = " ".join(text.split())
    return one_line if len(one_line) <= SHOWN_TOKEN else one_line[: SHOWN_TOKEN - 1] + "…"


def tokenize(sql: str) -> list[Tok]:
    if not isinstance(sql, str) or not sql.strip():
        raise _refuse("o SQL esta vazio")
    if len(sql) > MAX_SQL_CHARS:
        raise _refuse(f"o SQL passa de {MAX_SQL_CHARS} caracteres")
    tokens: list[Tok] = []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        if ch in " \t\r\n":
            i += 1
            continue
        if ch == "'":
            j, parts = i + 1, []
            while True:
                if j >= n:
                    raise _refuse("texto entre aspas sem fechar", posicao=i)
                if sql[j] == "'":
                    if j + 1 < n and sql[j + 1] == "'":
                        parts.append("'")
                        j += 2
                        continue
                    break
                if ord(sql[j]) < 0x20 or ord(sql[j]) == 0x7F:
                    raise _refuse("caractere de controle dentro do texto", posicao=j)
                parts.append(sql[j])
                j += 1
            tokens.append(Tok("str", "".join(parts), i))
            i = j + 1
        elif ch.isascii() and (ch.isalpha() or ch == "_"):
            j = i + 1
            while j < n and sql[j].isascii() and (sql[j].isalnum() or sql[j] == "_"):
                j += 1
            tokens.append(Tok("word", sql[i:j], i))
            i = j
        elif ch.isascii() and ch.isdigit():
            j = i + 1
            while j < n and sql[j].isascii() and sql[j].isdigit():
                j += 1
            if j < n and sql[j] == "." and j + 1 < n and sql[j + 1].isdigit():
                j += 1
                while j < n and sql[j].isascii() and sql[j].isdigit():
                    j += 1
            if j < n and (sql[j].isalpha() or sql[j] == "_"):
                raise _refuse("numero seguido de letra", posicao=i)
            tokens.append(Tok("num", sql[i:j], i))
            i = j
        elif sql.startswith(("<>", "!=", "<=", ">="), i):
            tokens.append(Tok("op", sql[i : i + 2], i))
            i += 2
        elif ch in ",.()*=<>-":
            tokens.append(Tok("op", ch, i))
            i += 1
        else:
            raise _refuse(
                f"caractere nao aceito fora de texto entre aspas simples: {_shown(ch)!r}",
                posicao=i,
            )
        if len(tokens) > MAX_TOKENS:
            raise _refuse(f"o SQL passa de {MAX_TOKENS} elementos")
    tokens.append(Tok("end", "", n))
    return tokens


@dataclass(frozen=True, slots=True)
class RawQuery:
    spec: ConsultaEstruturada
    on_pairs: frozenset[frozenset[tuple[str, str]]]


@dataclass(slots=True)
class _Source:
    table: str
    alias: str  # minusculo; igual ao nome da tabela quando nao ha apelido


class _Parser:
    def __init__(self, tokens: list[Tok]) -> None:
        self.t = tokens
        self.i = 0
        self.sources: list[_Source] = []

    # -- utilidades ---------------------------------------------------------------------------
    @property
    def cur(self) -> Tok:
        return self.t[self.i]

    def _is_word(self, *words: str) -> bool:
        return self.cur.kind == "word" and self.cur.text.upper() in words

    def _is_op(self, *ops: str) -> bool:
        return self.cur.kind == "op" and self.cur.text in ops

    def _eat_word(self, word: str) -> bool:
        if self._is_word(word):
            self.i += 1
            return True
        return False

    def _eat_op(self, op: str) -> bool:
        if self._is_op(op):
            self.i += 1
            return True
        return False

    def _expect_word(self, word: str) -> None:
        if not self._eat_word(word):
            raise self._unexpected(f"esperava {word}")

    def _expect_op(self, op: str) -> None:
        if not self._eat_op(op):
            raise self._unexpected(f"esperava {op!r}")

    def _unexpected(self, expected: str) -> RawSqlRefused:
        got = "o fim do SQL" if self.cur.kind == "end" else repr(_shown(self.cur.text))
        return _refuse(
            f"construcao nao aceita em L3: {expected}, achei {got}", posicao=self.cur.pos
        )

    # -- nomes --------------------------------------------------------------------------------
    def _name(self, what: str) -> str:
        tok = self.cur
        if tok.kind != "word":
            raise self._unexpected(f"esperava {what}")
        if tok.text.upper() in _RESERVED:
            raise _refuse(f"{tok.text.upper()} e palavra reservada e nao serve de {what}")
        self.i += 1
        return tok.text

    def _alias(self) -> str | None:
        if self._eat_word("AS"):
            return self._name("apelido")
        if self.cur.kind == "word" and self.cur.text.upper() not in _RESERVED:
            return self._name("apelido")
        return None

    def _ref(self) -> tuple[str | None, str]:
        first = self._name("coluna")
        if self._eat_op("."):
            return first.lower(), self._name("coluna")
        return None, first

    def _spec_ref(self, ref: tuple[str | None, str], joined: bool) -> str:
        alias, column = ref
        if alias is None:
            if joined:
                raise _refuse(f"com juncao, qualifique a coluna {column!r} com o apelido da tabela")
            return column
        source = next((s for s in self.sources if s.alias == alias), None)
        if source is None:
            raise _refuse(f"o apelido {alias!r} nao esta em FROM nem em JOIN")
        return column if source is self.sources[0] else f"{source.alias}.{column}"

    # -- literais -----------------------------------------------------------------------------
    def _literal(self) -> Any:
        negative = self._eat_op("-")
        tok = self.cur
        if tok.kind == "num":
            self.i += 1
            text = ("-" if negative else "") + tok.text
            return int(text) if tok.text.isdigit() else text
        if negative:
            raise self._unexpected("esperava numero depois de '-'")
        if tok.kind == "str":
            self.i += 1
            return tok.text
        if self._is_word("NULL"):
            raise _refuse("use IS NULL ou IS NOT NULL para testar nulo")
        raise self._unexpected("esperava um valor (numero ou texto entre aspas simples)")

    # -- gramatica ----------------------------------------------------------------------------
    def parse(self) -> RawQuery:
        self._expect_word("SELECT")
        distinct = self._eat_word("DISTINCT")
        top: int | None = None
        if self._eat_word("TOP"):
            top = self._count("TOP")
        raw_items = self._select_items()
        self._expect_word("FROM")
        self._from_source()
        on_pairs = self._joins()
        joined = len(self.sources) > 1

        columns: list[str] = []
        aggregations: list[Agregacao] = []
        for kind, payload in raw_items:
            if kind == "col":
                if aggregations:
                    raise _refuse("coloque as colunas antes das agregacoes no SELECT")
                columns.append(self._spec_ref(payload, joined))
            else:
                func, distinct_arg, arg, alias = payload
                column = "*" if arg is None else self._spec_ref(arg, joined)
                name: AggFunc = "count_distinct" if distinct_arg else func
                aggregations.append(Agregacao(funcao=name, coluna=column, alias=alias))

        filters: list[Filtro] = []
        if self._eat_word("WHERE"):
            filters = self._where(joined)
        group_by: list[str] = []
        if self._eat_word("GROUP"):
            self._expect_word("BY")
            group_by.append(self._spec_ref(self._ref(), joined))
            while self._eat_op(","):
                group_by.append(self._spec_ref(self._ref(), joined))
        order_by: list[Ordem] = []
        if self._eat_word("ORDER"):
            self._expect_word("BY")
            order_by.append(self._order_item(aggregations, joined))
            while self._eat_op(","):
                order_by.append(self._order_item(aggregations, joined))
        limit, offset = top, 0
        if self._eat_word("LIMIT"):
            if top is not None:
                raise _refuse("use TOP ou LIMIT, nao os dois")
            limit = self._count("LIMIT")
            if self._eat_word("OFFSET"):
                offset = self._count("OFFSET", zero_ok=True)
        if self.cur.kind != "end":
            raise self._unexpected("o SQL devia terminar aqui")

        spec = ConsultaEstruturada(
            tabela=self.sources[0].table,
            colunas=columns,
            agregacoes=aggregations,
            filtros=filters,
            agrupar_por=group_by,
            ordenar_por=order_by,
            juntar=[
                Juncao(tabela=s.table, apelido=None if s.alias == s.table.lower() else s.alias)
                for s in self.sources[1:]
            ],
            distinto=distinct,
            limite=limit,
            deslocamento=offset,
        )
        return RawQuery(spec, on_pairs)

    def _count(self, what: str, *, zero_ok: bool = False) -> int:
        tok = self.cur
        if tok.kind != "num" or not tok.text.isdigit() or len(tok.text) > 9:
            raise self._unexpected(f"esperava um inteiro depois de {what}")
        self.i += 1
        value = int(tok.text)
        if value == 0 and not zero_ok:
            raise _refuse(f"{what} precisa ser maior que zero")
        return value

    def _select_items(self) -> list[tuple[str, Any]]:
        items = [self._select_item()]
        while self._eat_op(","):
            items.append(self._select_item())
        return items

    def _select_item(self) -> tuple[str, Any]:
        if self._is_op("*"):
            raise _refuse("SELECT * nao e aceito: liste as colunas (use `descrever_tabela`)")
        if self.cur.kind == "word" and self.cur.text.upper() in _AGG_FUNCS:
            nxt = self.t[self.i + 1]
            if nxt.kind == "op" and nxt.text == "(":
                return self._aggregate()
        ref = self._ref()
        if self._is_word("AS"):
            raise _refuse("apelido de coluna nao e aceito; so agregacao leva AS")
        if self._is_op("(") or self._is_op("-"):
            raise _refuse("expressao e funcao nao sao aceitas em L3")
        return "col", ref

    def _aggregate(self) -> tuple[str, Any]:
        func = _AGG_FUNCS[self.cur.text.upper()]
        self.i += 2  # nome e '('
        distinct = self._eat_word("DISTINCT")
        arg: tuple[str | None, str] | None
        if self._eat_op("*"):
            if func != "count" or distinct:
                raise _refuse("so COUNT(*) aceita *")
            arg = None
        else:
            arg = self._ref()
        if distinct and func != "count":
            raise _refuse("DISTINCT so vale em COUNT")
        self._expect_op(")")
        if not self._eat_word("AS"):
            raise _refuse("toda agregacao precisa de apelido: AS nome")
        alias = self._name("apelido")
        if not _ALIAS_RX.match(alias):
            raise _refuse("apelido de agregacao invalido")
        return "agg", (func, distinct, arg, alias)

    def _from_source(self) -> None:
        table = self._name("tabela")
        if self._is_op("."):
            raise _refuse("nome de tabela sem dono: escreva so o nome, sem 'bethadba.'")
        alias = (self._alias() or table).lower()
        self._add_source(table, alias)

    def _add_source(self, table: str, alias: str) -> None:
        if not _ALIAS_RX.match(alias):
            raise _refuse("apelido invalido")
        names = {s.alias for s in self.sources} | {s.table.lower() for s in self.sources}
        if alias in names or (table.lower() in names and alias != table.lower()):
            raise _refuse(f"apelido ou tabela repetida: {alias!r}")
        self.sources.append(_Source(table, alias))

    def _joins(self) -> frozenset[frozenset[tuple[str, str]]]:
        pairs: set[frozenset[tuple[str, str]]] = set()
        while True:
            if self._is_word("LEFT", "RIGHT", "FULL", "CROSS", "OUTER"):
                raise _refuse("so JOIN interno e aceito")
            inner = self._eat_word("INNER")
            if not self._eat_word("JOIN"):
                if inner:
                    raise self._unexpected("esperava JOIN")
                return frozenset(pairs)
            table = self._name("tabela")
            if self._is_op("."):
                raise _refuse("nome de tabela sem dono: escreva so o nome, sem 'bethadba.'")
            alias = (self._alias() or table).lower()
            self._add_source(table, alias)
            self._expect_word("ON")
            pairs.add(self._on_pair())
            while self._eat_word("AND"):
                pairs.add(self._on_pair())
            if len(self.sources) - 1 > 2:
                raise _refuse("no maximo 2 juncoes")

    def _on_pair(self) -> frozenset[tuple[str, str]]:
        left = self._on_side()
        if not self._eat_op("="):
            raise self._unexpected("o ON so aceita igualdade entre colunas")
        right = self._on_side()
        if left[0] == right[0]:
            raise _refuse("o ON precisa ligar duas tabelas diferentes")
        return frozenset({left, right})

    def _on_side(self) -> tuple[str, str]:
        alias, column = self._ref()
        if alias is None:
            raise _refuse("no ON, qualifique as colunas com o apelido da tabela")
        source = next((s for s in self.sources if s.alias == alias), None)
        if source is None:
            raise _refuse(f"o apelido {alias!r} nao esta em FROM nem em JOIN")
        return source.table.lower(), column.lower()

    def _where(self, joined: bool) -> list[Filtro]:
        filters = [self._predicate(joined)]
        while self._eat_word("AND"):
            filters.append(self._predicate(joined))
        if self._is_word("OR"):
            raise _refuse("OR nao e aceito; separe em consultas ou use IN")
        return filters

    def _predicate(self, joined: bool) -> Filtro:
        if self._is_op("(") or self._is_word("NOT", "EXISTS"):
            raise _refuse("parenteses, NOT e EXISTS nao sao aceitos no filtro")
        if self.cur.kind not in ("word",):
            raise self._unexpected("o filtro precisa comecar por uma coluna")
        column = self._spec_ref(self._ref(), joined)
        tok = self.cur
        if tok.kind == "op" and tok.text in _COMPARISONS:
            self.i += 1
            if self.cur.kind == "word" and not self._is_word("NULL"):
                raise _refuse("compare a coluna com um valor, nao com outra coluna")
            return Filtro(coluna=column, op=_COMPARISONS[tok.text], valor=self._literal())  # type: ignore[arg-type]
        if self._eat_word("IN"):
            self._expect_op("(")
            values = [self._literal()]
            while self._eat_op(","):
                values.append(self._literal())
            self._expect_op(")")
            return Filtro(coluna=column, op="in", valor=values)
        if self._eat_word("BETWEEN"):
            low = self._literal()
            self._expect_word("AND")
            return Filtro(coluna=column, op="between", valor=[low, self._literal()])
        if self._eat_word("IS"):
            negated = self._eat_word("NOT")
            self._expect_word("NULL")
            return Filtro(coluna=column, op="not_null" if negated else "is_null")
        if self._eat_word("LIKE"):
            return self._like(column)
        if self._is_word("NOT"):
            raise _refuse("NOT IN, NOT LIKE e NOT BETWEEN nao sao aceitos")
        raise self._unexpected("esperava um operador de filtro")

    def _like(self, column: str) -> Filtro:
        if self.cur.kind != "str":
            raise self._unexpected("LIKE so aceita texto entre aspas simples")
        pattern = self.cur.text
        self.i += 1
        body = pattern
        starts, ends = pattern.startswith("%"), pattern.endswith("%") and len(pattern) > 1
        if starts:
            body = body[1:]
        if ends:
            body = body[:-1]
        if not body or any(c in body for c in "%_[]^"):
            raise _refuse(
                "LIKE so aceita 'texto%' (comeca com) ou '%texto%' (contem), sem curingas"
            )
        if starts and ends:
            return Filtro(coluna=column, op="contains", valor=body)
        if ends and not starts:
            return Filtro(coluna=column, op="prefix", valor=body)
        raise _refuse("LIKE so aceita 'texto%' (comeca com) ou '%texto%' (contem)")

    def _order_item(self, aggregations: list[Agregacao], joined: bool) -> Ordem:
        if self.cur.kind == "num":
            raise _refuse("ORDER BY posicional nao e aceito; use o nome da coluna ou o apelido")
        ref = self._ref()
        known = {a.alias.lower() for a in aggregations}
        name = ref[1] if ref[0] is None and ref[1].lower() in known else self._spec_ref(ref, joined)
        desc = False
        if self._eat_word("DESC"):
            desc = True
        else:
            self._eat_word("ASC")
        return Ordem(coluna=name, ordem="desc" if desc else "asc")


def translate(sql: str) -> RawQuery:
    """SQL (gramatica minima) -> consulta estruturada. Recusa o que nao reconhece."""
    return _Parser(tokenize(sql)).parse()


def check_joins(raw: RawQuery, validated: ValidatedQuery) -> None:
    """O `ON` escrito tem que ser exatamente a FK declarada que L2 usara.

    L2 escolhe o caminho pelo catalogo. Se o texto ligar outras colunas, ou se o caminho passar por
    uma tabela que o SQL nao juntou, recusa: o resultado nao seria o que o autor escreveu.
    """
    expected: set[frozenset[tuple[str, str]]] = set()
    for step in validated.joins:
        for left, right in zip(step.from_columns, step.to_columns, strict=True):
            expected.add(
                frozenset(
                    {
                        (step.from_table.lower(), left.lower()),
                        (step.to_table.lower(), right.lower()),
                    }
                )
            )
    if expected != set(raw.on_pairs):
        raise RawSqlRefused(
            "juncao_diferente_da_fk",
            "o ON nao e a chave estrangeira declarada entre as tabelas (ou o caminho passa por "
            "uma tabela que o SQL nao juntou); use `caminho_entre_tabelas`",
        )
