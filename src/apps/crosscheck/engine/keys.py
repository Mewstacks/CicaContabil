"""Chave de acesso de 44 posições (NF-e, NFC-e, CT-e).

Composição: cUF(2) AAMM(4) CNPJ(14) modelo(2) série(3) número(9) tpEmis(1) cNF(8) DV(1).
O dígito verificador é módulo 11 com pesos 2..9 da direita para a esquerda; resto 0 ou 1
vira DV 0. A Nota Técnica Conjunta 2025.001 manteve o cálculo e passou a aceitar letras nas
doze primeiras posições do CNPJ, valendo cada caractere o seu código ASCII menos 48 (os
dígitos continuam valendo 0..9; A vale 17).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

KEY_RE = re.compile(r"\d{6}[0-9A-Z]{12}\d{2}\d{24}")


@dataclass(frozen=True, slots=True)
class KeyParts:
    uf_code: str
    aamm: str
    cnpj: str
    model: str
    series: str
    number: str
    emission_type: str
    numeric_code: str
    check_digit: str


def _value(char: str) -> int:
    return ord(char) - 48


def format_cnpj(value: str) -> str:
    """`12345678000195` -> `12.345.678/0001-95`; qualquer outra coisa volta como veio."""

    text = str(value or "")
    if len(text) != 14:
        return text
    return f"{text[:2]}.{text[2:5]}.{text[5:8]}/{text[8:12]}-{text[12:]}"


def check_digit(first43: str) -> int:
    total = 0
    weight = 2
    for char in reversed(first43):
        total += _value(char) * weight
        weight = 2 if weight == 9 else weight + 1
    rest = total % 11
    return 0 if rest in (0, 1) else 11 - rest


def is_well_formed(key: str) -> bool:
    return bool(KEY_RE.fullmatch(key))


def is_valid_key(key: str) -> bool:
    """44 posições no formato certo e dígito verificador conferido."""

    return is_well_formed(key) and check_digit(key[:43]) == int(key[43])


def split_key(key: str) -> KeyParts:
    if not is_well_formed(key):
        raise ValueError("chave de acesso fora do formato de 44 posições")
    return KeyParts(
        uf_code=key[0:2],
        aamm=key[2:6],
        cnpj=key[6:20],
        model=key[20:22],
        series=key[22:25],
        number=key[25:34],
        emission_type=key[34],
        numeric_code=key[35:43],
        check_digit=key[43],
    )


def with_check_digit(first43: str) -> str:
    """Completa uma chave de 43 posições com o DV (usado pelos geradores sintéticos)."""

    return first43 + str(check_digit(first43))
