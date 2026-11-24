"""Consultas verificadas (L1): ferramentas de negocio com SQL fixo, versionado e conferido (T5.2).

Cada arquivo `data/verified/*.yaml` descreve uma ferramenta: parametros tipados, as colunas de que
depende (com a classe de dados declarada), o SQL e as colunas de saida. O SQL e escrito por nos e
revisado; o cliente so escolhe valores tipados dos parametros. Mini-linguagem do modelo de SQL:

- `?nome` liga o parametro `nome` (vira `?` no SQL, valor por parametro do ODBC);
- `{top}` vira o limite mais um (inteiro validado);
- `{?nome: ... ?nome ...}` so entra no SQL quando o parametro `nome` foi informado.

No carregamento (e a cada pack novo) as dependencias sao conferidas contra o pack: tabela ou coluna
que sumiu, ou classe do pack mais restritiva que a declarada, **desliga a ferramenta com o motivo**
em vez de devolver numero errado. Coluna que o pack ainda nao classificou (`nao_classificada`) e
aceita aqui: a classe declarada no YAML, revisada, faz o papel de curadoria.

A execucao reaproveita o mesmo caminho do L2: frescor, estimativa de custo (`PLAN`), admissao,
moldagem com mascara por classe, auditoria.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from importlib import resources
from typing import Any

import yaml

from dominio_mcp.compiler import CompiledQuery, OutColumn
from dominio_mcp.config import HARD_TOOL_PLAN_COST_BUDGET, HARD_TOOL_PLAN_ROWS_BUDGET
from dominio_mcp.executor import QueryEngine
from dominio_mcp.literals import UnsafeLiteral, encode_literal
from dominio_mcp.overlay import Overlay
from dominio_mcp.pack import Pack
from dominio_mcp.policy import PolicyClass
from dominio_mcp.query_spec import QueryRefused, coerce

MAX_WINDOW_DAYS = 396
DATE_MIN = date(1990, 1, 1)  # o banco tem datas lixo (1979, 8320, 5026); fora disto e recusa
DATE_MAX = date(2100, 12, 31)
OFFSET = "deslocamento"
_CONDITIONAL = re.compile(r"\{\?(\w+):([^{}]*)\}")
_NAMED = re.compile(r"\?(\w+)")
_RANK = {
    PolicyClass.NAO_CLASSIFICADA: -1,
    PolicyClass.NORMAL: 0,
    PolicyClass.TEXTO_LIVRE: 1,
    PolicyClass.DOCUMENTO: 2,
    PolicyClass.PESSOAL: 3,
    PolicyClass.SEGREDO: 4,
}
_PARAM_KINDS = {"int": "int", "text": "text", "date": "date", "choice": "text"}


class VerifiedError(Exception):
    """Arquivo de consulta verificada malformado (erro de programacao, nao do cliente)."""


class ToolDisabled(Exception):
    def __init__(self, name: str, reason: str) -> None:
        super().__init__(f"a ferramenta {name} esta desligada: {reason}")
        self.name = name
        self.reason = reason


@dataclass(frozen=True, slots=True)
class Param:
    nome: str
    tipo: str
    descricao: str = ""
    obrigatorio: bool = False
    padrao: Any = None
    valores: tuple[str, ...] = ()
    minimo: int | None = None
    maximo: int | None = None


@dataclass(frozen=True, slots=True)
class Output:
    nome: str
    tipo: str
    classe: PolicyClass
    categoria: str | None = None
    legenda_tabela: str | None = None
    legenda_coluna: str | None = None
    legenda_overlay: str | None = None


@dataclass(frozen=True, slots=True)
class Variant:
    sql: str
    dependencias: dict[str, dict[str, PolicyClass]]


@dataclass(frozen=True, slots=True)
class Tool:
    name: str
    titulo: str
    descricao: str
    params: tuple[Param, ...]
    variants: dict[str | None, Variant]
    variant_param: str | None
    saidas: tuple[Output, ...]
    janela: tuple[str, str] | None
    aviso: str
    version: int = 1
    sql_hash: str = field(default="", compare=False)
    orcamento: tuple[int, int] | None = None  # (custo, linhas) estimados que a consulta admite


def _param(raw: dict[str, Any]) -> Param:
    tipo = str(raw["tipo"])
    if tipo not in _PARAM_KINDS:
        raise VerifiedError(f"tipo de parametro desconhecido: {tipo}")
    return Param(
        nome=str(raw["nome"]),
        tipo=tipo,
        descricao=str(raw.get("descricao", "")),
        obrigatorio=bool(raw.get("obrigatorio", False)),
        padrao=raw.get("padrao"),
        valores=tuple(str(v) for v in raw.get("valores", [])),
        minimo=raw.get("minimo"),
        maximo=raw.get("maximo"),
    )


def _dependencies(raw: dict[str, Any]) -> dict[str, dict[str, PolicyClass]]:
    result: dict[str, dict[str, PolicyClass]] = {}
    for table, columns in raw.items():
        result[str(table).lower()] = {
            str(col).lower(): PolicyClass(str(klass)) for col, klass in columns.items()
        }
    return result


def _budget(raw: Any) -> tuple[int, int] | None:
    """`orcamento: {custo, linhas, medido_ms}`: dentro do teto duro e nunca vindo do cliente."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise VerifiedError("orcamento deve ser um mapa")
    cost, rows = raw.get("custo"), raw.get("linhas")
    for value, ceiling in ((cost, HARD_TOOL_PLAN_COST_BUDGET), (rows, HARD_TOOL_PLAN_ROWS_BUDGET)):
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= ceiling:
            raise VerifiedError("orcamento fora do teto duro ou malformado")
    return int(cost), int(rows)  # type: ignore[arg-type]


def parse_tool(text: str) -> Tool:
    try:
        raw = yaml.safe_load(text)
        saidas = tuple(
            Output(
                nome=str(s["nome"]),
                tipo=str(s["tipo"]),
                classe=PolicyClass(str(s.get("classe", "normal"))),
                categoria=s.get("categoria"),
                legenda_tabela=(s.get("legenda") or {}).get("tabela"),
                legenda_coluna=(s.get("legenda") or {}).get("coluna"),
                legenda_overlay=(s.get("legenda") or {}).get("overlay"),
            )
            for s in raw["saidas"]
        )
        variants: dict[str | None, Variant] = {}
        if "variantes" in raw:
            for key, body in raw["variantes"].items():
                variants[str(key)] = Variant(str(body["sql"]), _dependencies(body["dependencias"]))
            variant_param: str | None = str(raw["variante_por"])
        else:
            variants[None] = Variant(str(raw["sql"]), _dependencies(raw["dependencias"]))
            variant_param = None
        janela = raw.get("janela")
        orcamento = _budget(raw.get("orcamento"))
        digest = hashlib.sha256(
            json.dumps({str(k): v.sql for k, v in variants.items()}, sort_keys=True).encode()
        ).hexdigest()[:12]
        params = tuple(_param(p) for p in raw["parametros"])
        if any("{start}" in v.sql for v in variants.values()) and not any(
            p.nome == OFFSET for p in params
        ):
            params += (
                Param(
                    nome=OFFSET,
                    tipo="int",
                    descricao="Linhas ja recebidas (a proxima pagina comeca depois delas)",
                    padrao=0,
                    minimo=0,
                    maximo=100_000,
                ),
            )
        return Tool(
            name=str(raw["name"]),
            titulo=str(raw["titulo"]),
            descricao=str(raw["descricao"]),
            params=params,
            variants=variants,
            variant_param=variant_param,
            saidas=saidas,
            janela=None if janela is None else (str(janela["inicio"]), str(janela["fim"])),
            aviso=str(raw.get("aviso", "")),
            version=int(raw.get("version", 1)),
            sql_hash=digest,
            orcamento=orcamento,
        )
    except (KeyError, TypeError, ValueError, yaml.YAMLError) as exc:
        raise VerifiedError(f"consulta verificada malformada: {type(exc).__name__}") from None


def load_shipped_tools() -> dict[str, Tool]:
    folder = resources.files("dominio_mcp").joinpath("data/verified")
    tools: dict[str, Tool] = {}
    for entry in sorted(folder.iterdir(), key=lambda e: e.name):
        if entry.name.endswith(".yaml"):
            tool = parse_tool(entry.read_text(encoding="utf-8"))
            tools[tool.name] = tool
    return tools


def tool_status(tool: Tool, pack: Pack, allow_pii: frozenset[str]) -> str | None:
    """None se a ferramenta pode rodar; senao o motivo de estar desligada."""
    for key, variant in tool.variants.items():
        label = tool.name if key is None else f"{tool.name}[{key}]"
        for table, columns in variant.dependencias.items():
            row = pack.table(table)
            if row is None:
                return f"{label}: a tabela {table} nao existe mais no banco"
            if row.blocked_reason is not None and row.blocked_reason.startswith("ilegivel"):
                return f"{label}: a tabela {table} nao e legivel para este usuario"
            if row.blocked_reason in ("tabela_de_credencial", "view_nao_aprovada"):
                return f"{label}: a tabela {table} esta bloqueada ({row.blocked_reason})"
            for name, declared in columns.items():
                column = pack.column(table, name)
                if column is None:
                    return f"{label}: a coluna {table}.{name} nao existe mais no banco"
                if column.klass is PolicyClass.SEGREDO:
                    return f"{label}: a coluna {table}.{name} e bloqueada pela politica"
                if _RANK[column.klass] > _RANK[declared]:
                    return (
                        f"{label}: a politica trata {table}.{name} como {column.klass.value}, "
                        f"mais restrita que a declarada ({declared.value}); revise o YAML"
                    )
                if column.klass is PolicyClass.PESSOAL and column.category not in allow_pii:
                    return f"{label}: {table}.{name} e dado pessoal nao liberado"
    return None


def _coerce_param(param: Param, raw: Any) -> Any:
    kind = _PARAM_KINDS[param.tipo]
    try:
        if param.tipo == "choice":
            if raw not in param.valores:
                raise ValueError
            return str(raw)
        value = coerce(kind, raw)
        if kind == "date" and not DATE_MIN <= value <= DATE_MAX:
            raise ValueError
    except (ValueError, TypeError):
        raise QueryRefused(
            "parametro_invalido",
            f"o parametro {param.nome} nao serve (tipo {param.tipo}"
            + (", data entre 1990 e 2100" if param.tipo == "date" else "")
            + (f", valores {', '.join(param.valores)}" if param.valores else "")
            + ")",
            parametro=param.nome,
        ) from None
    if param.tipo == "int":
        if param.minimo is not None and value < param.minimo:
            raise QueryRefused("parametro_invalido", f"{param.nome} minimo e {param.minimo}")
        if param.maximo is not None and value > param.maximo:
            raise QueryRefused("parametro_invalido", f"{param.nome} maximo e {param.maximo}")
    return value


def assemble(sql: str, values: dict[str, Any], top: int, start: int = 1) -> tuple[str, list[str]]:
    """Aplica `{top}`, `{start}` e os blocos condicionais; devolve o SQL com `?` e a ordem dos
    parametros. `{start}` e a primeira linha (base 1) de `TOP n START AT m`."""

    def conditional(match: re.Match[str]) -> str:
        return match.group(2) if values.get(match.group(1)) is not None else ""

    text = (
        _CONDITIONAL.sub(conditional, sql)
        .replace("{top}", str(int(top)))
        .replace("{start}", str(int(start)))
    )
    names: list[str] = []

    def bind(match: re.Match[str]) -> str:
        names.append(match.group(1))
        return "?"

    return _NAMED.sub(bind, text), names


def render_literal(
    sql: str, names: list[str], kinds: dict[str, str], values: dict[str, Any]
) -> str:
    parts = sql.split("?")
    if len(parts) - 1 != len(names):
        raise VerifiedError("numero de parametros diferente do numero de ?")
    out = [parts[0]]
    for name, tail in zip(names, parts[1:], strict=True):
        out.append(encode_literal(kinds[name], values[name]))
        out.append(tail)
    return "".join(out)


class VerifiedRunner:
    def __init__(self, engine: QueryEngine, tools: dict[str, Tool], overlay: Overlay) -> None:
        self._engine = engine
        self._tools = tools
        self._legends = overlay.data("legends.yaml").get("legends", {}) or {}

    @property
    def tools(self) -> dict[str, Tool]:
        return self._tools

    def status(self, name: str) -> str | None:
        tool = self._tools[name]
        return tool_status(tool, self._engine.precheck(), self._engine.settings.allow_pii)

    def _out_columns(self, tool: Tool) -> tuple[OutColumn, ...]:
        mask = {
            PolicyClass.DOCUMENTO: "documento",
            PolicyClass.PESSOAL: "pessoal",
            PolicyClass.TEXTO_LIVRE: "texto",
        }
        return tuple(
            OutColumn(
                header=o.nome,
                mask=mask.get(o.classe, "none"),
                category=o.categoria,
                kind=o.tipo,
                from_aggregate=False,
            )
            for o in tool.saidas
        )

    def _legendas(self, tool: Tool, pack: Pack) -> dict[str, str]:
        result: dict[str, str] = {}
        for out in tool.saidas:
            if out.legenda_tabela and out.legenda_coluna:
                column = pack.column(out.legenda_tabela, out.legenda_coluna)
                if column is not None and column.legend:
                    result[out.nome] = f"{column.legend} (do comentario do banco)"
            elif out.legenda_overlay:
                entry = self._legends.get(out.legenda_overlay)
                if entry:
                    items = "; ".join(f"{k}={v}" for k, v in entry["valores"].items())
                    result[out.nome] = f"{items} ({entry.get('confianca', 'inferida')})"
        return result

    def run(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        tool = self._tools.get(name)
        if tool is None:
            raise QueryRefused(
                "ferramenta_desconhecida", f"nao existe a consulta verificada {name!r}"
            )
        pack = self._engine.precheck()
        reason = tool_status(tool, pack, self._engine.settings.allow_pii)
        if reason is not None:
            raise ToolDisabled(name, reason)
        values = self._values(tool, args)
        variant = self._variant(tool, values)
        limits = self._engine.settings.limits
        top = min(int(values["limite"]), limits.max_rows) if "limite" in values else 1
        sql, names = assemble(variant.sql, values, top + 1, int(values.get(OFFSET, 0)) + 1)
        kinds = {p.nome: _PARAM_KINDS[p.tipo] for p in tool.params}
        try:
            literal = render_literal(sql, names, kinds, values)
        except UnsafeLiteral:
            raise QueryRefused(
                "valor_nao_codificavel", "um parametro nao pode ser escrito com seguranca"
            ) from None
        params = tuple(values[n] for n in names)
        tables = tuple(sorted({t for v in tool.variants.values() for t in v.dependencias}))
        compiled = CompiledQuery(
            sql=sql,
            params=params,
            literal_sql=literal,
            columns=self._out_columns(tool),
            limit=top,
            tables=tables,
            count_index=None,
        )
        digest = hashlib.sha256(
            json.dumps(
                {k: str(v) for k, v in sorted(values.items())}, separators=(",", ":")
            ).encode()
        ).hexdigest()[:16]
        extra: dict[str, Any] = {"consulta": f"{tool.name} v{tool.version} ({tool.sql_hash})"}
        legends = self._legendas(tool, pack)
        if legends:
            extra["legendas"] = legends
        if tool.aviso:
            extra["aviso"] = tool.aviso
        return self._engine.execute_compiled(
            compiled,
            tool=f"verificada:{tool.name}",
            args=digest,
            pack=pack,
            extra=extra,
            budget=tool.orcamento,
        )

    def _values(self, tool: Tool, args: dict[str, Any]) -> dict[str, Any]:
        known = {p.nome: p for p in tool.params}
        unknown = sorted(set(args) - set(known))
        if unknown:
            raise QueryRefused(
                "parametro_desconhecido",
                f"parametro(s) desconhecido(s): {', '.join(unknown)}; validos: {', '.join(known)}",
            )
        values: dict[str, Any] = {}
        for param in tool.params:
            raw = args.get(param.nome, param.padrao)
            if raw is None:
                if param.obrigatorio:
                    raise QueryRefused(
                        "parametro_ausente", f"o parametro {param.nome} e obrigatorio"
                    )
                continue
            values[param.nome] = _coerce_param(param, raw)
        if tool.janela is not None:
            start, end = (values.get(tool.janela[0]), values.get(tool.janela[1]))
            if (
                not isinstance(start, date)
                or not isinstance(end, date)
                or isinstance(start, datetime)
            ):
                raise QueryRefused("janela_invalida", "informe a janela de datas (inicio e fim)")
            span = (end - start).days
            if span < 0:
                raise QueryRefused("janela_invalida", "o fim da janela e anterior ao inicio")
            if span > MAX_WINDOW_DAYS:
                raise QueryRefused(
                    "janela_de_datas_longa", "a janela de datas passa de 13 meses; reduza o periodo"
                )
        return values

    def _variant(self, tool: Tool, values: dict[str, Any]) -> Variant:
        key = None if tool.variant_param is None else values.get(tool.variant_param)
        variant = tool.variants.get(key)
        if variant is None:
            raise QueryRefused("parametro_invalido", "valor sem consulta verificada para ele")
        return variant
