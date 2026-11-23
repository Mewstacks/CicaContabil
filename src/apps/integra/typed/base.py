"""A strict, bounded engine for typed Integra Contador requests and readers.

A response model is a frozen, keyword-only dataclass that inherits `Model`; each field is
declared as `Annotated[T, J("jsonName", ...)]`, which carries the name of the documented field
and, where the annotation is not enough, the wire format (`Fmt`). A required field has no default
and an optional one defaults to `None` (or `()` for a list). `Model.parse` then reads one
decoded JSON object into the dataclass:

* structure is strict (objects, lists, scalars, bounded sizes and depth) while extra keys are
  ignored, so a documented addition never breaks a reader;
* scalars are lenient only inside their own meaning (a number may arrive as `"2018"`, a date as
  `20230131` or `"20230131"`), because the official pages disagree with their own examples;
* PDF and XML documents arrive in base64: the reader only decodes and validates them, it never
  parses a PDF, and XML is checked for well-formedness without entities or DTDs;
* errors name the field path and the expectation, never the received value.

A request model inherits `Request`; `to_dados()` validates every value and builds the object that
travels as the escaped `dados` string of `pedidoDados`.
"""

from __future__ import annotations

import base64
import binascii
import dataclasses
import json
import re
from collections.abc import Callable, Mapping
from dataclasses import MISSING, dataclass
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from functools import cache
from types import NoneType, UnionType
from typing import Annotated, Any, Self, Union, get_args, get_origin, get_type_hints
from xml.etree.ElementTree import ParseError

from defusedxml import ElementTree as SafeElementTree  # type: ignore[import-untyped]
from django.core.exceptions import ValidationError

from apps.common.cnpj import normalize_cnpj
from apps.integra.errors import IntegraPayloadError, IntegraRequestError

MAX_DADOS_CHARS = 2_000_000
MAX_ITEMS = 2_000
MAX_DEPTH = 8
MAX_TEXT = 4_000
MAX_DOCUMENT_BYTES = 8_000_000
MAX_MESSAGE_TEXT = 1_000

# Brazil has no daylight saving time since 2019: the timestamps of the RFB are -03:00.
BRASILIA = timezone(timedelta(hours=-3))
_PDF_TAIL = 1_024
_DECIMAL_PLACES = 8
_DECIMAL_LIMIT = Decimal("1e15")


class Fmt(StrEnum):
    DATE8 = "yyyymmdd"  # 20230131 (number or text)
    DATETIME14 = "yyyymmddhhmmss"  # 20260408123015
    ISO_DATE = "iso_date"  # 2019-09-01
    ISO_DATETIME = "iso_datetime"  # 2019-01-01T00:00:00-03:00, ...Z, or without offset
    BR_DATE = "dd/mm/yyyy"
    YEAR_MONTH = "yyyymm"  # 202304 as an int, validated
    PDF = "pdf"  # base64 of a PDF -> bytes
    XML = "xml"  # base64 of an XML document -> bytes
    TEXT_B64 = "text_b64"  # base64 of UTF-8 text -> str
    MONEY_STR = "money_str"  # request only: "1000.00"
    CNPJ = "cnpj"  # request only: numeric or alphanumeric, with check digits
    CPF = "cpf"  # request only
    NI = "ni"  # request only: CPF or CNPJ


@dataclass(frozen=True)
class J:
    """What a field is on the wire; carried in `Annotated[T, J("jsonName", ...)]`.

    `fmt` says how a date, a document or a number is written; `max_len`, `pattern`, `ge` and `le`
    bound request values; `text=True` sends an int as text (`"201801"`); `parse` replaces the
    built-in reading of a response value (it gets the raw JSON value and may raise ValueError).
    """

    alias: str
    fmt: Fmt | None = None
    max_len: int = MAX_TEXT
    pattern: str | None = None
    ge: int | None = None
    le: int | None = None
    text: bool = False
    parse: Callable[[Any], Any] | None = None


@cache
def _compiled(pattern: str) -> re.Pattern[str]:
    return re.compile(pattern)


# ---- plan: what each dataclass field means ----------------------------------------------


@dataclass(frozen=True)
class _Slot:
    attr: str
    base: Any
    many: bool
    optional: bool
    has_default: bool
    spec: J
    owner: str


_SCALARS = (str, int, bool, Decimal, date, datetime, bytes)
_NEEDS_FMT = (date, datetime, bytes)
# Which wire formats make sense for the types that have formats at all.
_FORMATS: dict[Any, tuple[Fmt, ...]] = {
    date: (Fmt.DATE8, Fmt.ISO_DATE, Fmt.BR_DATE),
    datetime: (Fmt.DATETIME14, Fmt.ISO_DATETIME),
    bytes: (Fmt.PDF, Fmt.XML),
    int: (Fmt.YEAR_MONTH,),
    Decimal: (Fmt.MONEY_STR,),
    str: (Fmt.TEXT_B64, Fmt.CNPJ, Fmt.CPF, Fmt.NI),
}


def _is_class(base: Any, parent: type) -> bool:
    return isinstance(base, type) and issubclass(base, parent) and base is not parent


@cache
def _plan(cls: Any) -> tuple[_Slot, ...]:
    hints = get_type_hints(cls, include_extras=True)
    slots = []
    for item in dataclasses.fields(cls):
        where = f"{cls.__name__}.{item.name}"
        annotation = hints[item.name]
        marker = None
        if get_origin(annotation) is Annotated:
            annotation, *extras = get_args(annotation)
            marker = next((extra for extra in extras if isinstance(extra, J)), None)
        if marker is None:
            raise TypeError(f"{where}: declare o campo como Annotated[T, J(...)].")
        optional = False
        origin = get_origin(annotation)
        if origin in (Union, UnionType):
            options = [arg for arg in get_args(annotation) if arg is not NoneType]
            optional = len(options) != len(get_args(annotation))
            if len(options) != 1:
                raise TypeError(f"{where}: uniões só são aceitas com None.")
            annotation = options[0]
            origin = get_origin(annotation)
        many = False
        if origin is tuple:
            args = get_args(annotation)
            if len(args) != 2 or args[1] is not Ellipsis:
                raise TypeError(f"{where}: use tuple[T, ...] para listas.")
            annotation, many = args[0], True
        supported = (
            annotation in _SCALARS
            or annotation is Any
            or _is_class(annotation, Model)
            or _is_class(annotation, Request)
        )
        if not supported:
            raise TypeError(f"{where}: tipo não suportado ({annotation!r}).")
        if annotation in _NEEDS_FMT and marker.fmt is None:
            raise TypeError(f"{where}: informe o formato (fmt) do campo.")
        formats = _FORMATS.get(annotation)
        if marker.fmt is not None and formats is not None and marker.fmt not in formats:
            raise TypeError(f"{where}: formato {marker.fmt.value} não serve para este tipo.")
        has_default = item.default is not MISSING or item.default_factory is not MISSING
        slots.append(_Slot(item.name, annotation, many, optional, has_default, marker, where))
    return tuple(slots)


# ---- envelope ----------------------------------------------------------------------------


@dataclass(frozen=True)
class Message:
    codigo: str
    texto: str


@dataclass(frozen=True)
class Envelope:
    status: int
    mensagens: tuple[Message, ...]
    dados: Any


def _message(raw: Any, index: int) -> Message:
    if not isinstance(raw, Mapping):
        raise IntegraPayloadError(f"mensagens[{index}] deve ser um objeto.")
    codigo, texto = raw.get("codigo", ""), raw.get("texto", "")
    if not isinstance(codigo, str) or not isinstance(texto, str):
        raise IntegraPayloadError(f"mensagens[{index}] tem tipos inesperados.")
    return Message(codigo[:100], texto[:MAX_MESSAGE_TEXT])


def open_envelope(
    payload: Any, *, accept: tuple[int, ...] = (200,), max_chars: int = MAX_DADOS_CHARS
) -> Envelope:
    """Check the answer of the gateway and decode the escaped `dados` string."""

    if not isinstance(payload, Mapping):
        raise IntegraPayloadError("A resposta do Serpro não é um objeto.")
    status = payload.get("status")
    if isinstance(status, bool) or not isinstance(status, int):
        raise IntegraPayloadError("A resposta do Serpro veio sem status numérico.")
    if status not in accept:
        raise IntegraPayloadError(f"O Serpro respondeu com status {status}, fora do esperado.")
    raw_messages = payload.get("mensagens") or []
    if not isinstance(raw_messages, list) or len(raw_messages) > MAX_ITEMS:
        raise IntegraPayloadError("mensagens deve ser uma lista dentro do limite.")
    messages = tuple(_message(item, index) for index, item in enumerate(raw_messages))

    raw = payload.get("dados")
    if raw is None or raw == "":
        return Envelope(status, messages, None)
    if isinstance(raw, str):
        if len(raw) > max_chars:
            raise IntegraPayloadError("dados excede o tamanho seguro de leitura.")
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise IntegraPayloadError("dados não contém JSON válido.") from exc
    if isinstance(raw, bool) or not (
        raw is None or isinstance(raw, dict | list | int | float | str)
    ):
        raise IntegraPayloadError("dados tem um tipo inesperado.")
    return Envelope(status, messages, raw)


# ---- reading -----------------------------------------------------------------------------

_ABSENT_DATES = (0, "0", "00000000", "00000000000000")
_CLOCK_SLICES = ((0, 4), (4, 6), (6, 8), (8, 10), (10, 12), (12, 14))


def _fail(where: str, expected: str) -> IntegraPayloadError:
    return IntegraPayloadError(f"{where} deve ser {expected}.")


def _is_absent(raw: Any, slot: _Slot) -> bool:
    if raw is None:
        return True
    if raw == "":
        return slot.many or slot.base is not str
    return slot.base in (date, datetime) and not isinstance(raw, bool) and raw in _ABSENT_DATES


def _digits(raw: Any, size: int) -> str | None:
    if isinstance(raw, bool):
        return None
    text = str(raw).strip() if isinstance(raw, int | str) else ""
    return text if len(text) == size and text.isdigit() else None


def _year_month(raw: Any, where: str) -> int:
    text = _digits(raw, 6)
    if text is None or not 1900 <= int(text[:4]) <= 2100 or not 1 <= int(text[4:]) <= 12:
        raise _fail(where, "um período AAAAMM válido")
    return int(text)


def _date(raw: Any, fmt: Fmt, where: str) -> date | datetime:
    try:
        if fmt is Fmt.DATE8:
            text = _digits(raw, 8)
            if text:
                return date(int(text[:4]), int(text[4:6]), int(text[6:]))
        elif fmt is Fmt.DATETIME14:
            text = _digits(raw, 14)
            if text:
                year, month, day, hour, minute, second = (
                    int(text[start:stop]) for start, stop in _CLOCK_SLICES
                )
                return datetime(year, month, day, hour, minute, second, tzinfo=BRASILIA)
        elif fmt is Fmt.ISO_DATE and isinstance(raw, str):
            if re.fullmatch(r"\d{4}-\d{2}-\d{2}(T.*)?", raw.strip()):
                return date.fromisoformat(raw.strip()[:10])
        elif fmt is Fmt.ISO_DATETIME and isinstance(raw, str):
            moment = datetime.fromisoformat(raw.strip())
            if moment.tzinfo is None:
                return moment.replace(tzinfo=BRASILIA)
            return moment.astimezone(BRASILIA)
        elif fmt is Fmt.BR_DATE and isinstance(raw, str):
            match = re.fullmatch(r"(\d{2})/(\d{2})/(\d{4})", raw.strip())
            if match:
                return date(int(match[3]), int(match[2]), int(match[1]))
    except ValueError:
        pass
    raise _fail(where, f"uma data válida ({fmt.value})")


def _decimal(raw: Any, where: str) -> Decimal:
    if isinstance(raw, bool) or not isinstance(raw, int | float | str):
        raise _fail(where, "um número")
    try:
        amount = Decimal(str(raw).strip())
    except InvalidOperation:
        raise _fail(where, "um número") from None
    exponent = amount.as_tuple().exponent
    if (
        not amount.is_finite()
        or abs(amount) >= _DECIMAL_LIMIT
        or not isinstance(exponent, int)
        or exponent < -_DECIMAL_PLACES
    ):
        raise _fail(where, "um número dentro do limite")
    return amount


def _integer(raw: Any, where: str) -> int:
    if isinstance(raw, bool):
        raise _fail(where, "um número inteiro")
    if isinstance(raw, int):
        return raw
    if isinstance(raw, float) and raw.is_integer():
        return int(raw)
    if isinstance(raw, str) and re.fullmatch(r"-?\d{1,18}", raw.strip()):
        return int(raw.strip())
    raise _fail(where, "um número inteiro")


def _bool(raw: Any, where: str) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str) and raw.strip().lower() in ("true", "false"):
        return raw.strip().lower() == "true"
    raise _fail(where, "verdadeiro ou falso")


def _decode_base64(raw: Any, where: str) -> bytes:
    if not isinstance(raw, str) or not raw:
        raise _fail(where, "um documento em base64")
    if len(raw) > MAX_DOCUMENT_BYTES * 4 // 3 + 64:
        raise IntegraPayloadError(f"{where} excede o tamanho máximo do documento.")
    try:
        data = base64.b64decode(re.sub(r"\s+", "", raw), validate=True)
    except (binascii.Error, ValueError):
        raise _fail(where, "um documento em base64 válido") from None
    if len(data) > MAX_DOCUMENT_BYTES:
        raise IntegraPayloadError(f"{where} excede o tamanho máximo do documento.")
    return data


def _document(raw: Any, fmt: Fmt, where: str) -> bytes:
    data = _decode_base64(raw, where)
    if fmt is Fmt.PDF:
        if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-_PDF_TAIL:]:
            raise _fail(where, "um PDF válido")
    else:
        try:
            SafeElementTree.fromstring(data, forbid_dtd=True)
        except (ParseError, ValueError):
            raise _fail(where, "um XML válido, sem entidades nem DTD") from None
    return data


def _scalar(slot: _Slot, raw: Any, where: str) -> Any:
    spec, base = slot.spec, slot.base
    if spec.parse is not None:
        try:
            return spec.parse(raw)
        except (ValueError, TypeError, ArithmeticError):
            raise IntegraPayloadError(f"{where}: valor inválido.") from None
    if base is Any:
        return raw
    if base is str:
        if spec.fmt is Fmt.TEXT_B64:
            try:
                return _decode_base64(raw, where).decode("utf-8")
            except UnicodeDecodeError:
                raise _fail(where, "um texto UTF-8 em base64") from None
        if not isinstance(raw, str):
            raise _fail(where, "um texto")
        if len(raw) > spec.max_len:
            raise IntegraPayloadError(f"{where} excede o tamanho máximo de texto.")
        return raw
    if base is bool:
        return _bool(raw, where)
    if base is int:
        if spec.fmt is Fmt.YEAR_MONTH:
            return _year_month(raw, where)
        return _integer(raw, where)
    if base is Decimal:
        return _decimal(raw, where)
    if base is bytes:
        return _document(raw, spec.fmt or Fmt.PDF, where)
    return _date(raw, spec.fmt or Fmt.DATE8, where)


def _read_item(slot: _Slot, raw: Any, where: str, depth: int) -> Any:
    if _is_class(slot.base, Model):
        return _read_object(slot.base, raw, where, depth + 1)
    return _scalar(slot, raw, where)


def _read_object(cls: type, data: Any, where: str, depth: int) -> Any:
    if depth > MAX_DEPTH:
        raise IntegraPayloadError(f"{where}: estrutura com profundidade acima do limite.")
    if not isinstance(data, Mapping):
        raise _fail(where, "um objeto")
    kwargs: dict[str, Any] = {}
    for slot in _plan(cls):
        raw = data.get(slot.spec.alias)
        path = f"{where}.{slot.spec.alias}"
        if _is_absent(raw, slot):
            if slot.has_default:
                continue
            if slot.many:
                kwargs[slot.attr] = ()
            elif slot.optional:
                kwargs[slot.attr] = None
            else:
                raise IntegraPayloadError(f"{path}: campo obrigatório ausente.")
            continue
        if slot.many:
            if not isinstance(raw, list):
                raise _fail(path, "uma lista")
            if len(raw) > MAX_ITEMS:
                raise IntegraPayloadError(f"{path}: lista acima do limite de {MAX_ITEMS} itens.")
            items = []
            for index, item in enumerate(raw):
                item_path = f"{path}[{index}]"
                if item is None:
                    raise IntegraPayloadError(f"{item_path}: item ausente.")
                items.append(_read_item(slot, item, item_path, depth))
            kwargs[slot.attr] = tuple(items)
        else:
            value = _read_item(slot, raw, path, depth)
            # An empty text is "nothing to say" for an optional field.
            kwargs[slot.attr] = None if value == "" and slot.optional else value
    return cls(**kwargs)


def read_int(data: Any, where: str = "dados") -> int:
    """A `dados` that is a bare integer (a count, for instance)."""

    return _integer(data, where)


class Model:
    """Base of the response models: frozen, keyword-only dataclasses declared with `J`."""

    @classmethod
    def parse(cls, data: Any, *, where: str = "dados") -> Self:
        parsed: Self = _read_object(cls, data, where, 0)
        return parsed

    @classmethod
    def parse_many(cls, data: Any, *, where: str = "dados") -> tuple[Self, ...]:
        """Read a `dados` whose root is a list of objects."""

        if not isinstance(data, list):
            raise _fail(where, "uma lista")
        if len(data) > MAX_ITEMS:
            raise IntegraPayloadError(f"{where}: lista acima do limite de {MAX_ITEMS} itens.")
        return tuple(cls.parse(item, where=f"{where}[{index}]") for index, item in enumerate(data))


# ---- requests ----------------------------------------------------------------------------


def normalize_cpf(value: str) -> str:
    cpf = re.sub(r"[.\-\s]", "", value)
    if not re.fullmatch(r"\d{11}", cpf) or len(set(cpf)) == 1:
        raise IntegraRequestError("Confira o CPF informado.")
    for size in (9, 10):
        total = sum(int(cpf[index]) * (size + 1 - index) for index in range(size))
        if int(cpf[size]) != (total * 10 % 11) % 10:
            raise IntegraRequestError("Confira os dígitos do CPF informado.")
    return cpf


def _cnpj(value: str) -> str:
    try:
        return normalize_cnpj(value)
    except ValidationError:
        raise IntegraRequestError("Confira o CNPJ informado.") from None


def _ni(value: str) -> str:
    bare = re.sub(r"[.\-/\s]", "", value)
    return normalize_cpf(bare) if re.fullmatch(r"\d{11}", bare) else _cnpj(value)


def _bad(slot: _Slot, reason: str) -> IntegraRequestError:
    return IntegraRequestError(f"{slot.owner} ({slot.spec.alias}): {reason}.")


def _dump_text(slot: _Slot, value: Any) -> str:
    spec = slot.spec
    if not isinstance(value, str):
        raise _bad(slot, "deve ser texto")
    text = value.strip()
    if len(text) > spec.max_len:
        raise _bad(slot, "texto longo demais")
    if spec.fmt is Fmt.CNPJ:
        return _cnpj(text)
    if spec.fmt is Fmt.CPF:
        return normalize_cpf(text)
    if spec.fmt is Fmt.NI:
        return _ni(text)
    if spec.pattern is not None and not _compiled(spec.pattern).fullmatch(text):
        raise _bad(slot, "formato inválido")
    return text


def _dump_int(slot: _Slot, value: Any) -> int | str:
    spec = slot.spec
    if isinstance(value, bool) or not isinstance(value, int):
        raise _bad(slot, "deve ser um número inteiro")
    if spec.fmt is Fmt.YEAR_MONTH:
        try:
            _year_month(value, slot.spec.alias)
        except IntegraPayloadError:
            raise _bad(slot, "deve ser um período AAAAMM válido") from None
    if (spec.ge is not None and value < spec.ge) or (spec.le is not None and value > spec.le):
        raise _bad(slot, "fora do intervalo permitido")
    return str(value) if spec.text else value


def _dump_decimal(slot: _Slot, value: Any) -> int | float | str:
    if isinstance(value, bool) or not isinstance(value, Decimal | int):
        raise _bad(slot, "deve ser um valor decimal")
    amount = Decimal(value)
    exponent = amount.as_tuple().exponent
    if not amount.is_finite() or abs(amount) >= _DECIMAL_LIMIT or not isinstance(exponent, int):
        raise _bad(slot, "valor fora do limite")
    if slot.spec.fmt is Fmt.MONEY_STR:
        if exponent < -2:
            raise _bad(slot, "no máximo duas casas decimais")
        return f"{amount:.2f}"
    return int(amount) if amount == amount.to_integral_value() else float(amount)


def _dump_date(slot: _Slot, value: Any) -> str:
    fmt = slot.spec.fmt
    if slot.base is datetime:
        if not isinstance(value, datetime):
            raise _bad(slot, "deve ser data e hora")
        moment: datetime = value.astimezone(BRASILIA) if value.tzinfo else value
        if fmt is Fmt.DATETIME14:
            return moment.strftime("%Y%m%d%H%M%S")
        return moment.strftime("%Y-%m-%dT%H:%M:%S")
    if isinstance(value, datetime) or not isinstance(value, date):
        raise _bad(slot, "deve ser uma data")
    day: date = value
    if fmt is Fmt.DATE8:
        return day.strftime("%Y%m%d")
    if fmt is Fmt.BR_DATE:
        return day.strftime("%d/%m/%Y")
    return day.isoformat()


def _dump_one(slot: _Slot, value: Any) -> Any:
    base = slot.base
    if _is_class(base, Request):
        if not isinstance(value, Request):
            raise _bad(slot, "deve ser um pedido aninhado")
        return value.to_dados()
    if base is str:
        return _dump_text(slot, value)
    if base is bool:
        if not isinstance(value, bool):
            raise _bad(slot, "deve ser verdadeiro ou falso")
        return value
    if base is int:
        return _dump_int(slot, value)
    if base is Decimal:
        return _dump_decimal(slot, value)
    if base is bytes:
        if not isinstance(value, bytes):
            raise _bad(slot, "deve ser um documento")
        return base64.b64encode(value).decode("ascii")
    if base is Any:
        return value
    return _dump_date(slot, value)


class Request:
    """Base of the request models. Invalid data fails at construction, before any call."""

    def __post_init__(self) -> None:
        self.to_dados()

    def to_dados(self) -> dict[str, Any]:
        dados: dict[str, Any] = {}
        model: Any = type(self)
        for slot in _plan(model):
            value = getattr(self, slot.attr)
            if value is None or (slot.many and not value):
                continue
            if slot.many:
                if not isinstance(value, tuple | list) or len(value) > MAX_ITEMS:
                    raise _bad(slot, "lista inválida")
                dados[slot.spec.alias] = [_dump_one(slot, item) for item in value]
            else:
                dados[slot.spec.alias] = _dump_one(slot, value)
        return dados
