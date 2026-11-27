"""Catálogo de campos dos relatórios (fail-closed) e extração do texto do PDF.

O catálogo descreve, por tipo de relatório, quais campos ler e com que regex. Ele é validado
INTEIRO antes de qualquer PDF: layout ruim nunca passa em silêncio. Um catálogo vazio reprova
(``pendente`` até a sessão de mapeamento com a cliente). Todo valor extraído guarda o original;
a correção humana preserva o original e exige justificativa.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

FIELD_KEY = re.compile(r"^[a-z][a-z0-9_]*$")
FIELD_TYPES = frozenset({"texto", "inteiro", "dinheiro", "data", "competencia"})
PARSER_VERSION = "1"


class CatalogIncomplete(ValueError):
    """O catálogo não pode ser usado."""


def validate_catalog(catalog: dict[str, Any], *, required_items: tuple[str, ...]) -> None:
    if not str(catalog.get("version") or "").strip():
        raise CatalogIncomplete("Catálogo sem versão.")
    reports = catalog.get("reports")
    if not isinstance(reports, dict):
        raise CatalogIncomplete("Catálogo sem relatórios.")
    for item in required_items:
        rules = reports.get(item)
        if not isinstance(rules, list) or not rules:
            raise CatalogIncomplete(f"Relatório sem regras: {item}.")
        seen: set[str] = set()
        for rule in rules:
            if not isinstance(rule, dict):
                raise CatalogIncomplete(f"Regra inválida em {item}.")
            key = str(rule.get("key") or "")
            if not FIELD_KEY.match(key) or key in seen:
                raise CatalogIncomplete(f"Chave inválida ou repetida em {item}: {key!r}.")
            seen.add(key)
            if rule.get("type") not in FIELD_TYPES:
                raise CatalogIncomplete(f"Tipo desconhecido em {item}.{key}.")
            if not isinstance(rule.get("required"), bool):
                raise CatalogIncomplete(f"'required' precisa ser booleano em {item}.{key}.")
            try:
                pattern = re.compile(str(rule.get("pattern") or ""))
            except re.error as exc:
                raise CatalogIncomplete(f"Regex inválida em {item}.{key}.") from exc
            if pattern.groups < 1:
                raise CatalogIncomplete(f"Regex sem grupo de captura em {item}.{key}.")


@dataclass(frozen=True)
class Extracted:
    key: str
    value: str
    required: bool


def extract(text: str, rules: list[dict[str, Any]]) -> tuple[list[Extracted], list[str]]:
    """Valores lidos e as chaves obrigatórias que faltaram."""

    found: list[Extracted] = []
    missing: list[str] = []
    for rule in rules:
        match = re.search(str(rule["pattern"]), text, flags=re.MULTILINE)
        value = match.group(1).strip() if match else ""
        if value:
            found.append(Extracted(str(rule["key"]), value, bool(rule["required"])))
        elif rule["required"]:
            missing.append(str(rule["key"]))
    return found, missing
