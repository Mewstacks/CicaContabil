"""Normalizacao de texto para a busca: sem acento, minusculas e radical simples do portugues.

O mesmo tratamento vale no indice (`pack_index.py`) e na consulta (`search.py`), entao plural e
singular se encontram (`adicoes` e `adicao`, `departamentos` e `departamento`). O radical e
deliberadamente simples: erra de forma consistente dos dois lados, o que basta para recuperar.
"""

from __future__ import annotations

import re
import unicodedata

_TOKEN = re.compile(r"[a-z0-9]+")


def fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def stem(token: str) -> str:
    if len(token) <= 3 or token.isdigit():
        return token
    if token.endswith(("oes", "aes")):
        return token[:-3] + "ao"
    if token.endswith("ais"):
        return token[:-3] + "al"
    if token.endswith("eis"):
        return token[:-3] + "el"
    if token.endswith("ns"):
        return token[:-2] + "m"
    if token.endswith("res") and len(token) > 4:
        return token[:-2]
    if token.endswith("s") and not token.endswith("ss"):
        return token[:-1]
    return token


def tokens(text: str) -> list[str]:
    return [stem(t) for t in _TOKEN.findall(fold(text))]


def index_text(text: str) -> str:
    return " ".join(tokens(text))
