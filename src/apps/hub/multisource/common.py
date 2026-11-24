"""Tipos e conversões comuns aos leitores multifontes (D-409)."""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal

MAX_SOURCE_BYTES = 25 * 1024 * 1024


class MultisourceError(ValueError):
    """Fonte fora do leiaute esperado; a mensagem é mostrada ao usuário."""


def cents_from_number(value: object) -> int:
    """Converte número de planilha (float/int/Decimal) em centavos, arredondando meio para cima."""
    if value is None or value == "":
        return 0
    if isinstance(value, bool):
        raise MultisourceError("Valor lógico onde se esperava número.")
    if isinstance(value, (int, float, Decimal)):
        amount = Decimal(str(value))
    elif isinstance(value, str):
        return cents_from_text(value)
    else:
        raise MultisourceError(f"Valor inesperado: {value!r}.")
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


MONEY_TEXT = re.compile(r"^-?\d{1,3}(?:\.\d{3})*,\d{2}$|^-?\d+,\d{2}$")


def cents_from_text(value: str) -> int:
    text = value.strip().replace("R$", "").strip()
    if not MONEY_TEXT.fullmatch(text):
        raise MultisourceError(f"Valor fora do formato 0.000,00: {value!r}.")
    return int(Decimal(text.replace(".", "").replace(",", ".")) * 100)


def parse_day(value: object) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        text = value.strip()
        for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date()
            except ValueError:
                continue
    raise MultisourceError(f"Data fora do formato dd/mm/aaaa: {value!r}.")


def normalize_name(value: str) -> str:
    """Nome em maiúsculas, sem acentos, pontuação nem sufixos societários comuns."""
    text = unicodedata.normalize("NFKD", value or "").encode("ascii", "ignore").decode()
    text = re.sub(r"[^A-Z0-9 ]+", " ", text.upper())
    stop = {"LTDA", "ME", "EPP", "EIRELI", "SA", "S", "A", "DE", "DA", "DO", "E", "COM", "IND"}
    return " ".join(t for t in text.split() if t not in stop)


def name_tokens(value: str) -> set[str]:
    return {t for t in normalize_name(value).split() if len(t) >= 3 and not t.isdigit()}


def names_match(a: str, b: str) -> bool:
    """Casamento conservador: o nome menor (ex.: truncado no extrato) cabe no maior.

    Exige ao menos um termo significativo em comum e que todos os termos completos do nome
    menor apareçam no maior; o último termo pode estar truncado (prefixo).
    """
    left, right = normalize_name(a).split(), normalize_name(b).split()
    if not left or not right:
        return False
    short, long_ = (left, right) if len(" ".join(left)) <= len(" ".join(right)) else (right, left)
    long_join = " ".join(long_)
    if not name_tokens(" ".join(short)):
        return False
    *full, last = short
    if any(term not in long_ for term in full):
        return False
    return any(term.startswith(last) for term in long_) or last in long_join


def money(cents: int) -> str:
    sign = "-" if cents < 0 else ""
    value = f"{abs(cents) / 100:,.2f}"
    return sign + value.replace(",", "X").replace(".", ",").replace("X", ".")
