"""Dinheiro e alíquota fiscais como inteiros.

O legado comparava `float` com tolerância de 0,01: 100,03 contra 100,02 acusava diferença
(0,010000000000005116) e 10,02 contra 10,01 passava (0,0099999…). Aqui todo valor entra como
`Decimal`, é arredondado uma única vez (meio para cima) para centavos e, dali em diante, só
existem inteiros. Alíquota usa quatro casas decimais (18,00 -> 180000).

SPED usa vírgula decimal e não tem separador de milhar; XML usa ponto. Texto fora desses
formatos é erro de leitura, nunca zero: tratar lixo como zero esconderia a divergência.
"""

from __future__ import annotations

import re
from decimal import ROUND_HALF_UP, Decimal

_CENT = Decimal("0.01")
_RATE = Decimal("0.0001")
_SPED_NUMBER = re.compile(r"-?\d{1,18}(?:,\d{1,10})?")
_XML_NUMBER = re.compile(r"-?\d{1,18}(?:\.\d{1,10})?")


class MoneyError(ValueError):
    """Texto que não é número no formato do arquivo de origem."""


def sped_decimal(text: str) -> Decimal | None:
    """`1234,56` -> Decimal; campo vazio (não informado) -> None."""

    value = text.strip()
    if not value:
        return None
    if not _SPED_NUMBER.fullmatch(value):
        raise MoneyError(f"número inválido no SPED: {value[:30]!r}")
    return Decimal(value.replace(",", "."))


def xml_decimal(text: str | None) -> Decimal | None:
    """`1234.56` -> Decimal; ausente ou vazio -> None."""

    if text is None:
        return None
    value = text.strip()
    if not value:
        return None
    if not _XML_NUMBER.fullmatch(value):
        raise MoneyError(f"número inválido no XML: {value[:30]!r}")
    return Decimal(value)


def to_cents(value: Decimal) -> int:
    return int(value.quantize(_CENT, rounding=ROUND_HALF_UP).scaleb(2))


def to_rate(value: Decimal) -> int:
    return int(value.quantize(_RATE, rounding=ROUND_HALF_UP).scaleb(4))


def sped_cents(text: str) -> int | None:
    value = sped_decimal(text)
    return None if value is None else to_cents(value)


def sped_rate(text: str) -> int | None:
    value = sped_decimal(text)
    return None if value is None else to_rate(value)


def xml_cents(text: str | None) -> int | None:
    value = xml_decimal(text)
    return None if value is None else to_cents(value)


def xml_rate(text: str | None) -> int | None:
    value = xml_decimal(text)
    return None if value is None else to_rate(value)


def plain(cents: int | None) -> str:
    """`123456` -> `1234.56` (formato de máquina para CSV/TXT); None -> vazio."""

    if cents is None:
        return ""
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"{sign}{whole}.{fraction:02d}"


def brl(cents: int | None) -> str:
    """`123456` -> `1.234,56` (exibição); None -> vazio."""

    if cents is None:
        return ""
    sign = "-" if cents < 0 else ""
    whole, fraction = divmod(abs(cents), 100)
    return f"{sign}{whole:,}".replace(",", ".") + f",{fraction:02d}"


def rate_text(rate: int | None) -> str:
    """`180000` -> `18,00`; None -> vazio."""

    if rate is None:
        return ""
    whole, fraction = divmod(abs(rate), 10_000)
    digits = f"{fraction:04d}".rstrip("0").ljust(2, "0")
    return f"{'-' if rate < 0 else ''}{whole},{digits}"
