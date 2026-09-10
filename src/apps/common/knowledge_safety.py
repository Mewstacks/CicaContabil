"""Validation shared by tenant and global RAG source ingestion."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError

_PERSONAL_DATA_RE = re.compile(
    r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b|"
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)


def validate_knowledge_source(*, source_reference: str, version: str, content: str) -> None:
    """Reject unsourced or identifiable material before it can enter either RAG corpus."""
    errors: dict[str, str] = {}
    if not source_reference.strip():
        errors["source_reference"] = "Informe a origem verificável antes de ingerir a fonte."
    if not version.strip():
        errors["version"] = "Informe a versão da fonte antes de ingerir o conteúdo."
    if not content.strip():
        errors["content"] = "A fonte não possui conteúdo para indexar."
    elif _PERSONAL_DATA_RE.search(content):
        errors["content"] = "Remova CPF, CNPJ ou e-mail antes de ingerir a fonte."
    if errors:
        raise ValidationError(errors)
