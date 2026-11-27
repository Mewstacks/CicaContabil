"""Segredo nunca entra em fila, resultado nem log de automação RPA.

Duas defesas: ``assert_no_secrets`` recusa carga com chave de aparência sensível (a carga de um
trabalho descreve *o quê* fazer; senha e certificado vivem no cofre da máquina do agente), e
``redact_text`` apaga do texto livre o que parece credencial antes de gravar erro ou evento.
"""

from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEY = re.compile(
    r"(passw|senha|secret|segredo|token|api_?key|private_?key|pfx|certificad|credential|"
    r"credencial|cookie|authorization)",
    re.IGNORECASE,
)
_BEARER = re.compile(r"(?i)\b(bearer|basic)\s+[A-Za-z0-9._~+/=-]{8,}")
_ASSIGNED = re.compile(
    r"(?i)\b(senha|password|passwd|pwd|token|secret|segredo|api[_-]?key)\b\s*[:=]\s*\S+"
)
_LONG_BLOB = re.compile(r"[A-Za-z0-9+/=_-]{40,}")
_CPF = re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")
MAX_DEPTH = 8


class SecretInPayload(ValueError):
    """A carga traz uma chave que parece segredo."""


def assert_no_secrets(value: Any, *, path: str = "$", depth: int = 0) -> None:
    if depth > MAX_DEPTH:
        raise SecretInPayload(f"{path}: aninhamento profundo demais")
    if isinstance(value, dict):
        for key, inner in value.items():
            if SENSITIVE_KEY.search(str(key)):
                raise SecretInPayload(f"{path}.{key}: chave de aparência sensível")
            assert_no_secrets(inner, path=f"{path}.{key}", depth=depth + 1)
    elif isinstance(value, list | tuple):
        for index, inner in enumerate(value):
            assert_no_secrets(inner, path=f"{path}[{index}]", depth=depth + 1)


def redact_text(text: str, *, limit: int = 500) -> str:
    cleaned = _CPF.sub("[cpf]", str(text or ""))
    cleaned = _BEARER.sub(r"\1 [oculto]", cleaned)
    cleaned = _ASSIGNED.sub(lambda m: f"{m.group(1)}=[oculto]", cleaned)
    cleaned = _LONG_BLOB.sub("[oculto]", cleaned)
    return cleaned[:limit]
