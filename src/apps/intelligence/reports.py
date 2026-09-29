"""Small, scoped exports for an answer produced inside the CICA Copilot."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from django.utils import timezone
from django.utils.text import slugify

from apps.intelligence.models import Message


def _text(value: object) -> str:
    return str(value or "").replace("\x00", "").strip()


def _evidence(message: Message) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for item in message.evidence if isinstance(message.evidence, list) else []:
        if not isinstance(item, dict):
            continue
        result.append(
            {
                "label": _text(item.get("label")),
                "reference": _text(item.get("reference")),
                "detail": _text(item.get("detail")),
            }
        )
    return result


def _metadata(message: Message) -> dict[str, str]:
    company = message.conversation.company
    if company is None:
        raise ValueError("A resposta não está vinculada a uma empresa.")
    generated_at = timezone.localtime().strftime("%d/%m/%Y %H:%M")
    return {
        "company": _text(company.name),
        "conversation": _text(message.conversation.title) or "Análise sem título",
        "generated_at": generated_at,
    }


def report_snapshot(message: Message) -> dict[str, Any]:
    """Translate one authorized Copilot answer to the renderer's restricted contract."""

    metadata = _metadata(message)
    return {
        "organizationId": str(message.organization_id),
        "reportName": "Relatório CICA",
        "generatedAt": timezone.now().isoformat(),
        "sourceUpdatedAt": message.updated_at.isoformat(),
        "templateVersion": "copilot-answer-v1",
        "periodLabel": "Resposta do Copiloto",
        "preliminary": False,
        "pendingNotes": [],
        "filters": [
            {"label": "Empresa", "value": metadata["company"]},
            {"label": "Análise", "value": metadata["conversation"]},
        ],
        "rows": [],
        "narrative": _text(message.content),
        "evidence": _evidence(message),
    }


def snapshot_json(snapshot: dict[str, Any]) -> str:
    """Serialize the restricted renderer contract in a stable form for evidence."""

    return json.dumps(snapshot, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def snapshot_sha256(snapshot: dict[str, Any]) -> str:
    return hashlib.sha256(snapshot_json(snapshot).encode("utf-8")).hexdigest()


def export_filename(*, message: Message, export_format: str) -> str:
    metadata = _metadata(message)
    base = (
        slugify(f"cica-{metadata['company']}-{metadata['conversation']}")[:72] or "cica-relatorio"
    )
    return f"{base}.{export_format}"
