"""Consulta estruturada L2: modelo e validacao contra o pack (D-317, T4.1).

A IA descreve a consulta em JSON (tabela, colunas, filtros, agrupamento, agregacao, juncao por FK
declarada). Nada aqui e SQL: `compiler.py` gera o SQL parametrizado so depois desta validacao, que
confere cada coluna contra o pack e a politica de dados:

- objeto legivel, classificado e (se view) aprovado; coluna fora do catalogo e recusada;
- cada uso (selecionar, filtrar, agrupar, ordenar, agregar) e uma permissao separada por classe;
- junção so por FK declarada, ate 2 saltos, nunca subindo e descendo (`joins.py`);
- valor tipado pela coluna (inteiro, decimal, data ISO, texto, ...); documento so com CNPJ valido.

Toda recusa tem `code` estavel e mensagem que ajuda a IA a corrigir sem expor o que e bloqueado.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from dominio_mcp.config import Settings
from dominio_mcp.joins import JoinStep, find_path
from dominio_mcp.literals import decimal_in_range
from dominio_mcp.pack import ColumnRow, Pack, TableRow
from dominio_mcp.policy import Access, ColumnPolicy, Policy, PolicyClass, is_valid_cnpj

MAX_IN_VALUES = 100
MAX_TEXT_VALUE = 200
MAX_OFFSET = 100_000
MAX_JOINS = 2
MAX_NAME = 200  # nome de tabela, coluna ou apelido.coluna; o que passa disso nem chega a ecoar
PERSON_KEY = "i_empregados"  # chave da pessoa nas 298 tabelas por empregado do Dominio
CELL_FETCH_CHARS = 400  # o servidor corta a celula de texto longo; a saida mostra 200
_LONG_TEXT_TYPES = frozenset({"long varchar", "long nvarchar", "text"})
_REF = re.compile(r"^(?:([A-Za-z0-9_]+)\.)?([A-Za-z0-9_]+)$")
_ALIAS = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,40}$")
_INT_TYPES = frozenset(
    {
        "integer",
        "smallint",
        "tinyint",
        "bigint",
        "unsigned int",
        "unsigned smallint",
        "unsigned bigint",
        "unsigned tinyint",
    }
)
_DECIMAL_TYPES = frozenset({"numeric", "decimal", "float", "double", "real", "money", "smallmoney"})
_TEXT_TYPES = frozenset(
    {"char", "varchar", "nvarchar", "nchar", "long varchar", "long nvarchar", "text"}
)

FilterOp = Literal[
    "=", "!=", "<", "<=", ">", ">=", "in", "between", "prefix", "contains", "is_null", "not_null"
]
AggFunc = Literal["count", "sum", "avg", "min", "max", "count_distinct"]


class QueryRefused(Exception):
    def __init__(self, code: str, message: str, **details: Any) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details


class _Base(BaseModel):
    model_config = ConfigDict(extra="forbid")


Name = Annotated[str, Field(max_length=MAX_NAME)]


class Filtro(_Base):
    coluna: Name = Field(description="coluna da tabela base ou apelido.coluna")
    op: FilterOp
    valor: Any = Field(default=None, description="escalar, lista (in) ou par [de, ate] (between)")


class Agregacao(_Base):
    funcao: AggFunc
    coluna: Name = Field(description="coluna, ou * so com count")
    alias: Name = Field(description="nome da coluna no resultado (letras, numeros e _)")


class Ordem(_Base):
    coluna: Name = Field(description="coluna do resultado, apelido de agregacao ou coluna")
    ordem: Literal["asc", "desc"] = "asc"


class Juncao(_Base):
    tabela: Name
    apelido: Name | None = None


class ConsultaEstruturada(_Base):
    tabela: Name
    colunas: list[Name] = Field(default_factory=list, max_length=40)
    agregacoes: list[Agregacao] = Field(default_factory=list, max_length=10)
    filtros: list[Filtro] = Field(default_factory=list, max_length=20)
    agrupar_por: list[Name] = Field(default_factory=list, max_length=10)
    ordenar_por: list[Ordem] = Field(default_factory=list, max_length=5)
    juntar: list[Juncao] = Field(default_factory=list, max_length=MAX_JOINS)
    distinto: bool = False
    limite: int | None = Field(default=None, ge=1)
    deslocamento: int = Field(default=0, ge=0)


@dataclass(frozen=True, slots=True)
class QTable:
    alias: str  # alias interno do SQL: t0, t1...
    row: TableRow
    user_alias: str
    step: JoinStep | None
    has_company: bool = False


@dataclass(frozen=True, slots=True)
class ColRef:
    table: QTable
    column: ColumnRow
    access: Access

    @property
    def sql_alias(self) -> str:
        return self.table.alias


@dataclass(frozen=True, slots=True)
class SelectItem:
    header: str
    kind: Literal["col", "agg"]
    ref: ColRef | None  # None em count(*)
    func: AggFunc | None = None
    # Chave da pessoa na tabela da medida (`i_empregados`): o agregado pessoal conta pessoas
    # distintas, nao linhas (doze competencias de um empregado so nao formam um grupo).
    person: ColRef | None = None


@dataclass(frozen=True, slots=True)
class FilterItem:
    ref: ColRef
    op: FilterOp
    values: tuple[Any, ...]
    kind: str


@dataclass(frozen=True, slots=True)
class OrderItem:
    header: str | None  # cabecalho do resultado (agregacao) ou None se for coluna simples
    ref: ColRef | None
    desc: bool


@dataclass(slots=True)
class ValidatedQuery:
    spec: ConsultaEstruturada
    tables: list[QTable]
    select: list[SelectItem]
    filters: list[FilterItem]
    group_by: list[ColRef]
    order_by: list[OrderItem]
    distinct: bool
    limit: int
    offset: int
    aggregated: bool
    suppress_small_groups: bool
    joins: list[JoinStep] = field(default_factory=list)


def type_kind(column_type: str) -> str:
    t = column_type.lower()
    if t in _INT_TYPES:
        return "int"
    if t in _DECIMAL_TYPES:
        return "decimal"
    if t in _TEXT_TYPES:
        return "text"
    if t in ("date",):
        return "date"
    if t in ("timestamp", "datetime", "smalldatetime"):
        return "timestamp"
    if t == "bit":
        return "bool"
    if t == "uniqueidentifier":
        return "uuid"
    return "other"


def coerce(kind: str, raw: Any) -> Any:
    """Converte o valor do JSON para o tipo da coluna; levanta `ValueError` se nao for seguro."""
    if kind == "int":
        if isinstance(raw, bool):
            raise ValueError
        if isinstance(raw, int):
            return raw
        if isinstance(raw, str) and re.fullmatch(r"-?\d{1,18}", raw.strip()):
            return int(raw.strip())
        raise ValueError
    if kind == "decimal":
        if isinstance(raw, bool) or not isinstance(raw, int | float | str):
            raise ValueError
        try:
            value = Decimal(str(raw).strip())
        except InvalidOperation:
            raise ValueError from None
        if not value.is_finite() or not decimal_in_range(value):
            raise ValueError
        return value
    if kind == "date":
        if isinstance(raw, str):
            return date.fromisoformat(raw.strip())
        raise ValueError
    if kind == "timestamp":
        if isinstance(raw, str):
            text = raw.strip().replace(" ", "T")
            return datetime.fromisoformat(text)
        raise ValueError
    if kind == "text":
        if not isinstance(raw, str) or len(raw) > MAX_TEXT_VALUE:
            raise ValueError
        if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in raw):
            raise ValueError
        return raw
    if kind == "bool":
        if raw in (True, False, 0, 1) and not isinstance(raw, str):
            return int(bool(raw))
        raise ValueError
    if kind == "uuid":
        if isinstance(raw, str):
            return str(uuid.UUID(raw.strip()))
        raise ValueError
    raise ValueError


def _column_policy(column: ColumnRow) -> ColumnPolicy:
    return ColumnPolicy(column.klass, column.category, column.rule, column.blocked_reason)


class _Resolver:
    def __init__(self, pack: Pack, settings: Settings, policy: Policy) -> None:
        self.pack = pack
        self.allow_pii = settings.allow_pii
        self.policy = policy
        self.by_alias: dict[str, QTable] = {}
        self.tables: list[QTable] = []

    def add(self, qtable: QTable, *names: str) -> None:
        self.tables.append(qtable)
        for name in names:
            self.by_alias[name.lower()] = qtable

    def resolve(self, ref: str) -> ColRef:
        match = _REF.match(ref.strip())
        if not match:
            raise QueryRefused("referencia_invalida", f"referencia de coluna invalida: {ref!r}")
        alias, name = match.groups()
        qtable = self.tables[0] if alias is None else self.by_alias.get(alias.lower())
        if qtable is None:
            raise QueryRefused(
                "tabela_nao_juntada",
                f"o apelido {alias!r} nao esta em `juntar`; so a tabela base e as juntadas valem",
            )
        column = self.pack.column(qtable.row.key, name)
        if column is None:
            raise QueryRefused(
                "coluna_desconhecida",
                f"a coluna {name!r} nao existe em {qtable.row.name}; use `descrever_tabela`",
                tabela=qtable.row.name,
            )
        access = self.policy.access(_column_policy(column), self.allow_pii)
        return ColRef(qtable, column, access)


def _blocked(table: TableRow) -> QueryRefused:
    reason = table.blocked_reason or "indisponivel"
    if reason == "tabela_de_credencial":
        return QueryRefused("tabela_bloqueada", "tabela bloqueada pela politica de dados")
    if reason == "view_nao_aprovada":
        return QueryRefused(
            "tabela_bloqueada",
            f"{table.name} e uma view nao aprovada: so e descritivel, nao consultavel",
            motivo=reason,
        )
    return QueryRefused(
        "tabela_bloqueada", f"{table.name} nao pode ser consultada ({reason})", motivo=reason
    )


def _require(table: TableRow | None, name: str) -> TableRow:
    if table is None:
        raise QueryRefused(
            "tabela_desconhecida", f"a tabela {name!r} nao existe; use `buscar_esquema`"
        )
    if not table.queryable:
        raise _blocked(table)
    return table


def _coerce_filter(ref: ColRef, op: FilterOp, raw: Any) -> tuple[tuple[Any, ...], str]:
    kind = type_kind(ref.column.type)
    where = ref.column.name
    if op in ("is_null", "not_null"):
        return (), kind
    if kind == "other":
        raise QueryRefused("tipo_nao_filtravel", f"a coluna {where} nao aceita filtro")
    try:
        if op == "in":
            if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_IN_VALUES:
                raise ValueError
            values = tuple(coerce(kind, v) for v in raw)
        elif op == "between":
            if not isinstance(raw, list) or len(raw) != 2:
                raise ValueError
            values = tuple(coerce(kind, v) for v in raw)
        elif op in ("prefix", "contains"):
            if kind != "text" or not isinstance(raw, str):
                raise ValueError
            values = (coerce("text", raw),)
        else:
            values = (coerce(kind, raw),)
    except (ValueError, TypeError):
        raise QueryRefused(
            "valor_incompativel",
            f"o valor do filtro em {where} nao serve para o tipo {ref.column.type} (operador {op})",
            coluna=where,
        ) from None
    if ref.column.klass is PolicyClass.DOCUMENTO:
        if kind != "text" and kind != "decimal" and kind != "int":
            raise QueryRefused("tipo_nao_filtravel", f"a coluna {where} nao aceita filtro")
        for value in values:
            if not is_valid_cnpj(str(value)):
                raise QueryRefused(
                    "documento_invalido",
                    f"{where} so aceita filtro por CNPJ valido (14 caracteres com digito "
                    "verificador)",
                    coluna=where,
                )
    return values, kind


def _person_key(ref: ColRef, pack: Pack, policy: Policy, settings: Settings) -> ColRef | None:
    column = pack.column(ref.table.row.key, PERSON_KEY)
    if column is None:
        return None
    return ColRef(ref.table, column, policy.access(_column_policy(column), settings.allow_pii))


def needs_cut(column: ColumnRow) -> bool:
    """Texto longo (ou de largura desconhecida): o servidor entrega so o comeco da celula."""
    if type_kind(column.type) != "text":
        return False
    return (
        column.type.lower() in _LONG_TEXT_TYPES
        or column.width is None
        or column.width > CELL_FETCH_CHARS
    )


def _no_cut(ref: ColRef, use: str) -> None:
    """Agrupar, ordenar ou usar `DISTINCT` num valor cortado trataria o prefixo como o valor."""
    if needs_cut(ref.column):
        raise QueryRefused(
            "coluna_longa",
            f"{ref.column.name} guarda texto longo: so pode ser lida (cortada) ou contada por "
            f"valor inteiro, nao usada em {use}",
            coluna=ref.column.name,
            uso=use,
        )


def _check_use(ref: ColRef, use: str, allowed: bool) -> None:
    if allowed:
        return
    reason = ref.access.reason or "bloqueada"
    raise QueryRefused(
        "coluna_bloqueada",
        f"a coluna {ref.column.name} nao pode ser usada em {use} ({reason})",
        coluna=ref.column.name,
        uso=use,
        motivo=reason,
    )


def _check_join_keys(steps: list[JoinStep], pack: Pack) -> None:
    """A igualdade do `ON` tambem le a coluna: chave classificada como segredo, pessoal, documento
    ou texto livre revelaria o valor ao juntar com uma tabela que enumera os candidatos."""
    for step in steps:
        for key, names in ((step.from_table, step.from_columns), (step.to_table, step.to_columns)):
            for name in names:
                column = pack.column(key, name)
                if column is None or column.klass is not PolicyClass.NORMAL:
                    raise QueryRefused(
                        "juncao_bloqueada",
                        f"a juncao de {step.from_table} com {step.to_table} usa uma coluna de "
                        "chave que a politica de dados nao libera",
                    )


def _check_fan_out(steps: list[JoinStep]) -> None:
    """Dois filhos independentes do mesmo pai formam produto cartesiano: cada linha de um se repete
    para cada linha do outro e todo total sai multiplicado."""
    parents: set[str] = set()
    for step in steps:
        if step.direction != "down":
            continue
        if step.from_table in parents:
            raise QueryRefused(
                "juncao_multiplicadora",
                f"juntar duas tabelas filhas de {step.from_table} multiplica as linhas; junte uma "
                "de cada vez",
            )
        parents.add(step.from_table)


def _plan_joins(
    spec: ConsultaEstruturada, pack: Pack, resolver: _Resolver, base: TableRow
) -> list[JoinStep]:
    steps: list[JoinStep] = []
    seen: set[tuple[str, str]] = set()
    requested: list[tuple[TableRow, str]] = []
    for join in spec.juntar:
        target = _require(pack.table(join.tabela), join.tabela)
        user_alias = (join.apelido or target.key).lower()
        if not _ALIAS.match(user_alias):
            raise QueryRefused("apelido_invalido", f"apelido invalido: {join.apelido!r}")
        path = find_path(pack, base.key, target.key)
        if path is None:
            raise QueryRefused(
                "juncao_sem_fk",
                f"nao ha juncao segura por chave estrangeira declarada entre {base.name} e "
                f"{target.name}; use `caminho_entre_tabelas`",
            )
        for step in path:
            if (step.from_table, step.to_table) not in seen:
                seen.add((step.from_table, step.to_table))
                steps.append(step)
        requested.append((target, user_alias))
    if len(steps) > MAX_JOINS:
        raise QueryRefused(
            "muitas_juncoes", f"a consulta exigiria {len(steps)} juncoes; o maximo e {MAX_JOINS}"
        )
    _check_join_keys(steps, pack)
    _check_fan_out(steps)
    for internal, step in enumerate(steps, start=1):
        row = _require(pack.table(step.to_table), step.to_table)
        names = [row.key] + [alias for target, alias in requested if target.key == row.key]
        has_company = pack.column(row.key, "codi_emp") is not None
        resolver.add(QTable(f"t{internal}", row, names[-1], step, has_company), *names)
    return steps


def validate_query(
    spec: ConsultaEstruturada, pack: Pack, settings: Settings, policy: Policy
) -> ValidatedQuery:
    base = _require(pack.table(spec.tabela), spec.tabela)
    resolver = _Resolver(pack, settings, policy)
    base_has_company = pack.column(base.key, "codi_emp") is not None
    resolver.add(QTable("t0", base, base.key, None, base_has_company), base.key)
    joins = _plan_joins(spec, pack, resolver, base)
    # Tabela "um" de uma juncao (o pai, subindo ou descendo): cada linha dela se repete por linha
    # filha, entao somar, tirar media ou contar coluna dela multiplica o total.
    repeated = {step.to_table if step.direction == "up" else step.from_table for step in joins}
    limits = settings.limits

    aggregated = bool(spec.agregacoes or spec.agrupar_por)
    group_by: list[ColRef] = []
    for ref_text in spec.agrupar_por:
        ref = resolver.resolve(ref_text)
        _check_use(ref, "agrupar_por", ref.access.group)
        _no_cut(ref, "agrupar_por")
        group_by.append(ref)
    group_keys = {(g.table.alias, g.column.key) for g in group_by}

    select: list[SelectItem] = []
    headers: set[str] = set()

    def add_header(header: str) -> str:
        if header.lower() in headers:
            raise QueryRefused("saida_duplicada", f"a coluna de saida {header!r} se repete")
        headers.add(header.lower())
        return header

    if aggregated:
        for g in group_by:
            select.append(SelectItem(add_header(_header(g, resolver)), "col", g))
        for ref_text in spec.colunas:
            ref = resolver.resolve(ref_text)
            if (ref.table.alias, ref.column.key) not in group_keys:
                raise QueryRefused(
                    "coluna_fora_do_agrupamento",
                    f"{ref.column.name} precisa estar em `agrupar_por` numa consulta agregada",
                )
    else:
        for ref_text in spec.colunas:
            ref = resolver.resolve(ref_text)
            _check_use(ref, "colunas", ref.access.select)
            if spec.distinto:  # DISTINCT agrupa o valor cru, antes da mascara
                _check_use(ref, "distinto", ref.access.group)
                _no_cut(ref, "distinto")
            select.append(SelectItem(add_header(_header(ref, resolver)), "col", ref))
    if not aggregated and not select:
        raise QueryRefused(
            "sem_colunas", "informe `colunas` (ou `agregacoes`); a consulta nao tem o que devolver"
        )

    suppress = any(g.access.suppress_small_groups for g in group_by)
    agg_refs: dict[str, tuple[AggFunc, ColRef | None]] = {}
    for agg in spec.agregacoes:
        if not _ALIAS.match(agg.alias) or agg.alias.startswith("__"):
            raise QueryRefused("apelido_invalido", "alias de agregacao invalido")
        if agg.coluna.strip() == "*":
            if agg.funcao != "count":
                raise QueryRefused("funcao_incompativel", "so count aceita `*`")
            select.append(SelectItem(add_header(agg.alias), "agg", None, "count"))
            agg_refs[agg.alias.lower()] = ("count", None)
            continue
        ref = resolver.resolve(agg.coluna)
        if agg.funcao not in ref.access.aggregates:
            _check_use(ref, f"agregacao {agg.funcao}", False)
        kind = type_kind(ref.column.type)
        if agg.funcao in ("sum", "avg") and kind not in ("int", "decimal"):
            raise QueryRefused(
                "funcao_incompativel",
                f"{agg.funcao} so vale para coluna numerica; {ref.column.name} e {ref.column.type}",
            )
        if agg.funcao in ("sum", "avg", "count") and ref.table.row.key in repeated:
            raise QueryRefused(
                "agregacao_multiplicada",
                f"{agg.funcao} de {ref.column.name} depois da juncao conta cada linha de "
                f"{ref.table.row.name} uma vez por linha ligada a ela; agregue uma coluna da "
                "tabela filha (o lado 'muitos') ou use max, min ou count_distinct",
            )
        suppress = suppress or ref.access.suppress_small_groups
        person = (
            _person_key(ref, pack, policy, settings) if ref.access.suppress_small_groups else None
        )
        select.append(SelectItem(add_header(agg.alias), "agg", ref, agg.funcao, person))
        agg_refs[agg.alias.lower()] = (agg.funcao, ref)
    if aggregated and not select:
        raise QueryRefused("sem_colunas", "a consulta agregada nao tem o que devolver")
    if len(select) > limits.max_columns:
        raise QueryRefused(
            "colunas_demais",
            f"a saida teria {len(select)} colunas; o maximo e {limits.max_columns}",
        )

    filters: list[FilterItem] = []
    for flt in spec.filtros:
        ref = resolver.resolve(flt.coluna)
        if flt.op not in ref.access.filter_ops:
            _check_use(ref, f"filtro {flt.op}", False)
        values, kind = _coerce_filter(ref, flt.op, flt.valor)
        filters.append(FilterItem(ref, flt.op, values, kind))

    order_by: list[OrderItem] = []
    selected_headers = {item.header.lower(): item for item in select}
    for ordem in spec.ordenar_por:
        key = ordem.coluna.strip().lower()
        if key in agg_refs:
            _func, aref = agg_refs[key]
            if aref is not None:
                _check_use(aref, "ordenar_por", aref.access.order)
            order_by.append(OrderItem(ordem.coluna.strip(), None, ordem.ordem == "desc"))
            continue
        ref = resolver.resolve(ordem.coluna)
        _check_use(ref, "ordenar_por", ref.access.order)
        _no_cut(ref, "ordenar_por")
        if aggregated and (ref.table.alias, ref.column.key) not in group_keys:
            raise QueryRefused(
                "ordenacao_fora_do_agrupamento",
                f"{ref.column.name} precisa estar em `agrupar_por` para ordenar a agregacao",
            )
        if spec.distinto and not any(
            i.ref is not None
            and (i.ref.table.alias, i.ref.column.key) == (ref.table.alias, ref.column.key)
            for i in select
        ):
            raise QueryRefused(
                "ordenacao_fora_da_selecao",
                "com `distinto`, so se ordena por coluna que esta na saida",
            )
        order_by.append(OrderItem(None, ref, ordem.ordem == "desc"))
    del selected_headers

    cap = limits.max_rows_aggregate if aggregated else limits.max_rows
    limit = spec.limite if spec.limite is not None else min(limits.default_rows, cap)
    if limit > cap:
        raise QueryRefused(
            "limite_acima_do_teto", f"`limite` maximo e {cap} para esta consulta", maximo=cap
        )
    if spec.deslocamento > MAX_OFFSET:
        raise QueryRefused("deslocamento_alto", f"`deslocamento` maximo e {MAX_OFFSET}")
    if suppress and not aggregated:
        suppress = False
    return ValidatedQuery(
        spec=spec,
        tables=resolver.tables,
        select=select,
        filters=filters,
        group_by=group_by,
        order_by=order_by,
        distinct=spec.distinto,
        limit=limit,
        offset=spec.deslocamento,
        aggregated=aggregated,
        suppress_small_groups=suppress,
        joins=joins,
    )


def _header(ref: ColRef, resolver: _Resolver) -> str:
    base_alias = resolver.tables[0].alias
    return (
        ref.column.name
        if ref.table.alias == base_alias
        else f"{ref.table.user_alias}.{ref.column.name}"
    )
