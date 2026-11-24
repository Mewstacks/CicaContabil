"""Normalizacao dos valores que saem do ODBC para JSON seguro.

Regras (T1.1):

- Nada binario sai como conteudo: so um marcador com o tamanho.
- Decimal vira numero JSON quando cabe em 15 digitos significativos (inteiro se nao tem casas
  decimais, senao ponto flutuante); acima disso fica texto exato (nao arredonda dinheiro em
  silencio).
- `char` do Dominio vem preenchido com espacos a direita: sao removidos (os da esquerda ficam).
- Caracteres de controle (menos tab, quebra de linha e retorno) sao removidos.
- Data com lixo (1979, 8320 aparecem em colunas de data do banco) e emitida como esta; quem
  consome decide com `date_is_plausible`.
- Nunca levanta excecao: valor desconhecido vira texto curto.
"""

from __future__ import annotations

import math
from collections.abc import Iterable
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from uuid import UUID

Cell = str | int | float | bool | None

_MAX_SAFE_INT = 2**53
_MAX_DECIMAL_DIGITS = 15
_MAX_UNKNOWN_TEXT = 200
_PLAUSIBLE_MIN = date(1980, 1, 1)
_PLAUSIBLE_MAX = date(2100, 12, 31)
_CONTROL = dict.fromkeys(
    c for c in (*range(0x00, 0x20), 0x7F, *range(0x80, 0xA0)) if c not in (0x09, 0x0A, 0x0D)
)


def _text(value: str) -> str:
    return value.translate(_CONTROL).rstrip()


def _decimal(value: Decimal) -> Cell:
    if not value.is_finite():
        return None
    _sign, digits, exponent = value.as_tuple()
    if len(digits) > _MAX_DECIMAL_DIGITS:
        return str(value)
    if isinstance(exponent, int) and exponent >= 0:
        whole = int(value)  # numerico sem casas decimais (numero de nota, serie, codigo)
        return whole if abs(whole) <= _MAX_SAFE_INT else str(whole)
    return float(value)


def _datetime(value: datetime) -> str:
    spec = "seconds" if value.microsecond == 0 else "milliseconds"
    return value.isoformat(sep=" ", timespec=spec)


def normalize_value(value: object) -> Cell:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value if abs(value) <= _MAX_SAFE_INT else str(value)
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    if isinstance(value, Decimal):
        return _decimal(value)
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, datetime):
        return _datetime(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat(timespec="seconds" if value.microsecond == 0 else "milliseconds")
    if isinstance(value, memoryview):
        return f"<binario {value.nbytes} bytes>"
    if isinstance(value, bytes | bytearray):
        return f"<binario {len(value)} bytes>"
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, timedelta):
        return str(value)
    try:
        return _text(str(value))[:_MAX_UNKNOWN_TEXT]
    except Exception:  # qualquer __str__ quebrado nao pode derrubar a resposta
        return "<ilegivel>"


def normalize_row(row: Iterable[object]) -> list[Cell]:
    return [normalize_value(v) for v in row]


def date_is_plausible(value: object) -> bool:
    """False para data fora de 1980-01-01..2100-12-31; valor que nao e data e plausivel."""
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        return _PLAUSIBLE_MIN <= value <= _PLAUSIBLE_MAX
    return True
