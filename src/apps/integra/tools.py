"""Tool functions over the typed Integra Contador reads, ready for a single tool registry.

Each of the 59 typed reads the copilot may call (class A, `copilot_allowed`) becomes a tool:
a name (`serpro_<key>`), a JSON schema of its arguments, a cost and `run_tool`, a function that

* builds and validates the request from plain JSON arguments (dates as text, numbers, lists);
* makes one call through the access it receives (the governed client of the office, so limits,
  procuração check and cost record already apply);
* returns plain JSON data: money as text, dates as ISO text, and **no document**: a PDF or XML
  comes back as `{"tipo", "bytes", "sha256"}` only, never persisted and never given to a model;
* audits what was called, at what cost, with a reference of the taxpayer and never its number.

The returned data is Serpro data. Until Serpro answers in writing about repasse to a language
model (docs/legal/perguntas-serpro.md), it must not be sent to an external LLM; the registry that
exposes these tools decides what a model may see (`ToolResult.serpro_data` is always True).
"""

from __future__ import annotations

import dataclasses
import hashlib
import time
import types
import typing
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Annotated, Any, Protocol

from apps.integra.catalog import service
from apps.integra.governor import call_cost_cents
from apps.integra.typed.base import Request
from apps.integra.typed.registry import TypedService
from apps.integra.typed_registry import TYPED


class ToolError(ValueError):
    """The tool name or its arguments are not acceptable; nothing was sent."""


class Access(Protocol):
    def call(
        self, service_key: str, *, contribuinte: str, dados: dict[str, Any] | str | None = None
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class Tool:
    name: str
    key: str
    description: str
    cost_cents: int
    typed: TypedService


@dataclass(frozen=True)
class ToolResult:
    tool: str
    service_key: str
    cost_cents: int
    data: Any
    serpro_data: bool = True


def _build_tools() -> dict[str, Tool]:
    tools = {}
    for key, typed in TYPED.items():
        spec = service(key)
        if not spec.copilot_allowed:
            continue
        name = "serpro_" + key.replace(".", "_")
        tools[name] = Tool(name, key, spec.label, call_cost_cents(spec), typed)
    return tools


TOOLS: dict[str, Tool] = _build_tools()


# ---- arguments -----------------------------------------------------------------------------


def _unwrap(hint: Any) -> tuple[Any, bool, bool]:
    """Annotation -> (base type, optional, list)."""

    if typing.get_origin(hint) is Annotated:
        hint = typing.get_args(hint)[0]
    optional = False
    if typing.get_origin(hint) in (typing.Union, types.UnionType):
        options = [arg for arg in typing.get_args(hint) if arg is not type(None)]
        optional = len(options) != len(typing.get_args(hint))
        hint = options[0]
    many = False
    if typing.get_origin(hint) is tuple:
        hint, many = typing.get_args(hint)[0], True
    return hint, optional, many


def _fields(request: type[Request]) -> dict[str, tuple[Any, bool, bool, bool]]:
    hints = typing.get_type_hints(request, include_extras=True)
    result = {}
    for item in dataclasses.fields(request):  # type: ignore[arg-type]
        base, optional, many = _unwrap(hints[item.name])
        has_default = item.default is not dataclasses.MISSING or (
            item.default_factory is not dataclasses.MISSING
        )
        result[item.name] = (base, optional, many, not has_default)
    return result


def _coerce(base: Any, value: Any, where: str) -> Any:
    try:
        if isinstance(base, type) and issubclass(base, Request):
            return _build(base, value, where)
        if base is date:
            return date.fromisoformat(value)
        if base is datetime:
            return datetime.fromisoformat(value)
        if base is Decimal:
            if isinstance(value, bool):
                raise TypeError
            return Decimal(str(value))
        if base is int:
            if isinstance(value, bool) or (isinstance(value, float) and not value.is_integer()):
                raise TypeError
            return int(value)
        if base is bool:
            if not isinstance(value, bool):
                raise TypeError
            return value
        if base is str:
            if not isinstance(value, str):
                raise TypeError
            return value
    except (TypeError, ValueError, InvalidOperation):
        raise ToolError(f"O argumento {where} tem um valor inválido.") from None
    raise ToolError(f"O argumento {where} não é aceito por esta ferramenta.")


def _build(request: type[Request], arguments: Mapping[str, Any], where: str = "") -> Request:
    if not isinstance(arguments, Mapping):
        raise ToolError(f"O argumento {where or 'principal'} deve ser um objeto.")
    fields = _fields(request)
    unknown = sorted(set(arguments) - set(fields))
    if unknown:
        raise ToolError(f"Argumento desconhecido: {unknown[0]}.")
    values: dict[str, Any] = {}
    for name, value in arguments.items():
        base, _optional, many, _required = fields[name]
        path = f"{where}.{name}" if where else name
        if many:
            if not isinstance(value, list | tuple):
                raise ToolError(f"O argumento {path} deve ser uma lista.")
            values[name] = tuple(_coerce(base, item, path) for item in value)
        else:
            values[name] = _coerce(base, value, path)
    try:
        return request(**values)
    except TypeError:
        raise ToolError("Faltam argumentos obrigatórios.") from None


# ---- results -------------------------------------------------------------------------------


def to_plain(value: Any) -> Any:
    """JSON-safe data. Money and dates become text; a document becomes its description."""

    if isinstance(value, bytes):
        kind = "pdf" if value.startswith(b"%PDF-") else "xml"
        return {"tipo": kind, "bytes": len(value), "sha256": hashlib.sha256(value).hexdigest()}
    if dataclasses.is_dataclass(value) and not isinstance(value, type):
        fields = dataclasses.fields(value)
        return {item.name: to_plain(getattr(value, item.name)) for item in fields}
    if isinstance(value, tuple | list):
        return [to_plain(item) for item in value]
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    if isinstance(value, dict):
        return {str(key): to_plain(item) for key, item in value.items()}
    return value


def tool_schema(name: str) -> dict[str, Any]:
    """Name, description and JSON schema of the arguments of one tool."""

    tool = _tool(name)
    properties: dict[str, Any] = {}
    required: list[str] = []
    if tool.typed.request is not None:
        for field_name, (base, _optional, many, is_required) in _fields(tool.typed.request).items():
            properties[field_name] = _json_type(base, many)
            if is_required:
                required.append(field_name)
    return {
        "name": tool.name,
        "description": f"{tool.description} (Serpro, custo estimado {tool.cost_cents} centavos).",
        "input_schema": {"type": "object", "properties": properties, "required": required},
    }


def _json_type(base: Any, many: bool) -> dict[str, Any]:
    if isinstance(base, type) and issubclass(base, Request):
        item: dict[str, Any] = {"type": "object"}
    elif base is int:
        item = {"type": "integer"}
    elif base is Decimal:
        item = {"type": "number"}
    elif base is bool:
        item = {"type": "boolean"}
    else:
        item = {"type": "string"}
        if base in (date, datetime):
            item["format"] = "date" if base is date else "date-time"
    return {"type": "array", "items": item} if many else item


def _tool(name: str) -> Tool:
    try:
        return TOOLS[name]
    except KeyError:
        raise ToolError(f"Ferramenta {name!r} desconhecida.") from None


def _default_audit(event: dict[str, Any]) -> None:
    return None


def run_tool(
    access: Access,
    name: str,
    *,
    contribuinte: str,
    arguments: Mapping[str, Any],
    audit: Callable[[dict[str, Any]], None] = _default_audit,
) -> ToolResult:
    tool = _tool(name)
    request_type = tool.typed.request
    if request_type is None:
        if arguments:
            raise ToolError("Esta ferramenta não recebe argumentos.")
        dados: dict[str, Any] | None = None
    else:
        request = _build(request_type, arguments)
        dados = request.to_dados()
    reference = hashlib.sha256(contribuinte.encode()).hexdigest()[:12]
    started = time.monotonic()
    event: dict[str, Any] = {
        "tool": tool.name,
        "service_key": tool.key,
        "cost_cents": tool.cost_cents,
        "contribuinte_ref": reference,
    }
    try:
        payload = access.call(tool.key, contribuinte=contribuinte, dados=dados)
        data = to_plain(tool.typed.read(payload))
    except BaseException:
        event.update(outcome="error", seconds=round(time.monotonic() - started, 3))
        audit(event)
        raise
    event.update(outcome="ok", seconds=round(time.monotonic() - started, 3))
    audit(event)
    return ToolResult(tool.name, tool.key, tool.cost_cents, data)


__all__ = [
    "TOOLS",
    "Access",
    "Tool",
    "ToolError",
    "ToolResult",
    "run_tool",
    "to_plain",
    "tool_schema",
]
