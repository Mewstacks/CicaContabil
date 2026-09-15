"""CICA's single Windows company-folder component; no filesystem writes here."""

from __future__ import annotations

import re
import unicodedata

from django.core.exceptions import ValidationError

_FORBIDDEN = frozenset('<>:"/\\|?*')
_MAX_COMPONENT_UTF16_UNITS = 160


def _windows_units(value: str) -> int:
    return len(value.encode("utf-16-le")) // 2


def company_folder_component(*, company_name: str, dominio_code: str) -> str:
    """Produce `Nome [Domínio código]` while preserving the exact Domínio key."""
    code = unicodedata.normalize("NFC", dominio_code)
    if (
        not code
        or code != code.strip()
        or code in {".", ".."}
        or any(char in _FORBIDDEN or unicodedata.category(char).startswith("C") for char in code)
    ):
        raise ValidationError("Cadastre um código Domínio válido antes de escolher pastas Windows.")
    suffix = f" [Domínio {code}]"
    if _windows_units(suffix) >= _MAX_COMPONENT_UTF16_UNITS:
        raise ValidationError("O código Domínio é longo demais para o padrão de pasta CICA.")
    name = unicodedata.normalize("NFC", company_name)
    name = "".join(
        " " if char in _FORBIDDEN or unicodedata.category(char).startswith("C") else char
        for char in name
    )
    name = re.sub(r"\s+", " ", name).strip(" .")
    if not name:
        raise ValidationError("Cadastre um nome de empresa válido antes de arquivar no Windows.")
    while _windows_units(name + suffix) > _MAX_COMPONENT_UTF16_UNITS:
        name = name[:-1].rstrip(" .")
    if not name:
        raise ValidationError("O nome da empresa não cabe no padrão de pasta CICA.")
    return name + suffix
