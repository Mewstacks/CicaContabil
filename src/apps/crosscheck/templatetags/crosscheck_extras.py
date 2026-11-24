"""Filtros de exibição do Contraprova: valores em centavos, rótulos e detalhe de achado."""

from __future__ import annotations

from typing import Any

from django import template

from ..engine.keys import format_cnpj
from ..engine.money import brl, rate_text
from ..queries import KIND_LABELS, STATUS_LABELS

register = template.Library()

_SOURCE_LABELS = {"1": "SPED 1", "2": "SPED 2", 1: "SPED 1", 2: "SPED 2"}
_REASONS = {"cfop_sem_credito": "CFOP sem direito a crédito"}


@register.filter
def cents(value: int | None) -> str:
    return "" if value is None else brl(value)


@register.filter
def signed_cents(value: int | None) -> str:
    if value is None:
        return ""
    text = brl(value)
    return f"+{text}" if value > 0 else text


@register.filter
def kind_label(value: str) -> str:
    return KIND_LABELS.get(value, value)


@register.filter
def status_label(value: str) -> str:
    return STATUS_LABELS.get(value, value)


@register.filter
def bytes_label(value: int | None) -> str:
    size = int(value or 0)
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f}".replace(".", ",") + " MiB"
    return f"{max(1, round(size / 1024))} KiB"


@register.filter
def cnpj_mask(value: str | None) -> str:
    return format_cnpj(str(value or ""))


@register.filter
def short_key(value: str) -> str:
    """Chave de 44 posições em grupos de quatro, para ler e copiar sem errar."""

    text = str(value or "")
    return " ".join(text[i : i + 4] for i in range(0, len(text), 4))


def _money_or_empty(value: Any) -> str:
    return brl(value) if isinstance(value, int) else ""


@register.filter
def detail_view(detail: dict[str, Any] | None) -> dict[str, Any]:
    """Organiza o JSON de detalhe de um achado em fatos, C190 e ICMS por CFOP."""

    detail = detail or {}
    facts: list[tuple[str, str]] = []
    if detail.get("source"):
        facts.append(("Arquivo do XML", str(detail["source"])))
    if detail.get("arquivo") in _SOURCE_LABELS:
        facts.append(("Arquivo", _SOURCE_LABELS[detail["arquivo"]]))
    if detail.get("vezes"):
        facts.append(("Ocorrências", str(detail["vezes"])))
    if detail.get("reason"):
        facts.append(("Motivo", _REASONS.get(str(detail["reason"]), str(detail["reason"]))))
    if detail.get("sped_vazio"):
        facts.append(("SPED", "campo vazio"))
    if detail.get("cred_sn"):
        facts.append(("Crédito do Simples", _money_or_empty(detail["cred_sn"])))
    if detail.get("emit_doc"):
        facts.append(
            ("Emitente", f"{detail['emit_doc']} · {detail.get('emit_uf', '')}".strip(" ·"))
        )
    c190 = [
        {
            "cst": item.get("cst", ""),
            "cfop": item.get("cfop", ""),
            "aliq": rate_text(item["aliq"]) if isinstance(item.get("aliq"), int) else "",
            "vl_opr": _money_or_empty(item.get("vl_opr")),
            "vl_bc_icms": _money_or_empty(item.get("vl_bc_icms")),
            "vl_icms": _money_or_empty(item.get("vl_icms")),
            "vl_ipi": _money_or_empty(item.get("vl_ipi")),
        }
        for item in detail.get("c190") or []
        if isinstance(item, dict)
    ]
    by_cfop = [
        (str(cfop), _money_or_empty(value))
        for cfop, value in sorted((detail.get("icms_por_cfop") or {}).items())
    ]
    return {"facts": facts, "c190": c190, "by_cfop": by_cfop}
