"""Identificadores e literais seguros para o SQL gerado pelo proprio programa.

O SQL interno so nasce do compilador e das consultas verificadas, nunca de texto do cliente.

- Identificador vem do catalogo e e citado com aspas duplas; um que tenha aspas ou caractere de
  controle e recusado (nunca "escapado"): um nome assim num catalogo legitimo nao existe.
- Literal tipado (so para o SQL de estimativa de custo, `SELECT PLAN(?)`): inteiro, decimal, data
  ISO, texto com aspas simples duplicadas. Texto com barra invertida, caractere de controle ou
  longo demais e recusado, porque a semantica de escape do servidor nao foi provada para eles;
  recusado o literal, recusam-se a estimativa **e** a execucao. A execucao em si usa parametros
  `?`, nunca literal.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any

MAX_IDENTIFIER = 128
MAX_LITERAL_TEXT = 200
_UUID = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")


class UnsafeIdentifier(ValueError):
    """Identificador com aspas, caractere de controle, vazio ou longo demais."""


class UnsafeLiteral(ValueError):
    """Valor que nao da para escrever como literal SQL com seguranca."""


def quote_ident(name: str) -> str:
    if not name or len(name) > MAX_IDENTIFIER:
        raise UnsafeIdentifier("identificador vazio ou longo demais")
    for ch in name:
        code = ord(ch)
        if ch == '"' or code < 0x20 or 0x7F <= code <= 0x9F:
            raise UnsafeIdentifier("identificador com caractere nao permitido")
    return f'"{name}"'


def qualified(owner: str, name: str) -> str:
    return f"{quote_ident(owner)}.{quote_ident(name)}"


def like_escape(text: str, escape: str = "!") -> str:
    """Escapa `%`, `_`, `[` e o proprio escape para uso com `LIKE ... ESCAPE '!'`.

    No SQL Anywhere 17.0.11 o `[` abre uma classe de caracteres (`[0-9]`, `[^a]`), o que deixaria
    o valor do filtro virar padrao; `]`, `^` e `-` fora de uma classe sao literais (conferido no
    servidor, e `!]` seria erro -630).
    """
    doubled = text.replace(escape, escape + escape)
    return doubled.replace("%", escape + "%").replace("_", escape + "_").replace("[", escape + "[")


MAX_DECIMAL_EXPONENT = 38


def decimal_in_range(number: Decimal) -> bool:
    """Expoente pequeno dos dois lados: `format(Decimal('1e1000000000'), 'f')` escreveria um bilhao
    de digitos antes de qualquer controle de custo."""
    exponent = number.as_tuple().exponent
    return (
        isinstance(exponent, int)
        and exponent >= -MAX_DECIMAL_EXPONENT
        and number.adjusted() <= MAX_DECIMAL_EXPONENT
    )


def encode_literal(kind: str, value: Any) -> str:
    """Literal SQL de um valor ja tipado (inteiro, decimal, data, texto...). Recusa o duvidoso."""
    if kind == "int":
        if isinstance(value, bool) or not isinstance(value, int) or abs(value) >= 2**63:
            raise UnsafeLiteral("inteiro invalido")
        return str(value)
    if kind == "bool":
        if isinstance(value, str) or value not in (0, 1):
            raise UnsafeLiteral("booleano invalido")
        return str(int(value))
    if kind == "decimal":
        if not isinstance(value, Decimal | int | float) or isinstance(value, bool):
            raise UnsafeLiteral("decimal invalido")
        number = value if isinstance(value, Decimal) else Decimal(str(value))
        if (
            not number.is_finite()
            or len(number.as_tuple().digits) > 38
            or not decimal_in_range(number)
        ):
            raise UnsafeLiteral("decimal invalido")
        return format(number, "f")
    if kind == "date":
        if not isinstance(value, date) or isinstance(value, datetime):
            raise UnsafeLiteral("data invalida")
        return f"'{value.isoformat()}'"
    if kind == "timestamp":
        if not isinstance(value, datetime):
            raise UnsafeLiteral("data e hora invalidas")
        return f"'{value.isoformat(sep=' ')}'"
    if kind == "uuid":
        if not isinstance(value, str) or not _UUID.match(value):
            raise UnsafeLiteral("uuid invalido")
        return f"'{value.lower()}'"
    if kind == "text":
        return _encode_text(value)
    raise UnsafeLiteral("tipo de literal desconhecido")


def _encode_text(value: Any) -> str:
    if not isinstance(value, str) or len(value) > MAX_LITERAL_TEXT:
        raise UnsafeLiteral("texto invalido ou longo demais")
    for ch in value:
        code = ord(ch)
        if code < 0x20 or 0x7F <= code <= 0x9F or ch == "\\" or code in (0x2028, 0x2029):
            raise UnsafeLiteral("texto com caractere que nao da para escrever com seguranca")
    return "'" + value.replace("'", "''") + "'"
