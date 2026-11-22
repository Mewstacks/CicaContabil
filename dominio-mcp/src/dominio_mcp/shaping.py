"""Moldagem da saida de L1 e L2 (D-319, D-322, D-323, T4.7).

Tudo que sai passa por aqui: mascara por valor conforme a classe da coluna de origem (documento,
pessoal, texto livre), supressao de grupos com menos de 3 linhas quando ha dado pessoal agregado,
celulas de no maximo 200 caracteres, teto de 12 KB na resposta inteira (`truncado` e
`proximo_passo`), aviso de data fora da faixa plausivel, e o rotulo de consistencia: a leitura roda
com `isolation_level = 0`, entao toda resposta traz `consistencia: leitura_nao_confirmada` e
`lido_em`. Numero fiscal e diagnostico a conferir contra relatorio do Dominio, nao apuracao.

Os avisos so trazem contagem e nome de coluna da propria consulta: nunca valor de linha.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from dominio_mcp.compiler import CompiledQuery, OutColumn
from dominio_mcp.odbc import RawResult
from dominio_mcp.policy import mask_document, mask_pii, mask_text
from dominio_mcp.values import Cell

MAX_RESPONSE_BYTES = 12 * 1024
MAX_CELL_CHARS = 200
MIN_GROUP_SIZE = 3
CONSISTENCY = "leitura_nao_confirmada"


@dataclass(frozen=True, slots=True)
class ShapeContext:
    """Dados da execucao que entram no cabecalho da resposta."""

    pack_version: str = ""
    elapsed_ms: float = 0.0
    max_bytes: int = MAX_RESPONSE_BYTES
    plan_cost: float | None = None
    # campos que o chamador acrescenta ao envelope (L1: consulta, legendas, aviso); entram na
    # conta dos 12 KB, senao a resposta final passaria do teto
    extra: tuple[tuple[str, Any], ...] = ()


def _clip(text: str) -> str:
    if len(text) <= MAX_CELL_CHARS:
        return text
    return text[: MAX_CELL_CHARS - 1] + "…"


def _mask_cell(column: OutColumn, value: Cell) -> Cell:
    if value is None:
        return None
    if column.mask == "documento":
        masked = mask_document(value, allow=False)
        return _clip(masked) if isinstance(masked, str) else masked
    if column.mask == "pessoal":
        return mask_pii(value, column.category or "")
    if column.mask == "texto":
        return _clip(mask_text(value if isinstance(value, str) else str(value)) or "")
    return _clip(value) if isinstance(value, str) else value


def _too_small(count: Cell) -> bool:
    return not isinstance(count, int | float) or count < MIN_GROUP_SIZE


def _implausible_year(value: Cell) -> bool:
    if not isinstance(value, str) or len(value) < 4 or not value[:4].isdigit():
        return False
    year = int(value[:4])
    return year < 1980 or year > 2100


def _envelope(
    headers: list[str],
    rows: list[list[Cell]],
    *,
    truncated: bool,
    read_at: datetime,
    tables: tuple[str, ...],
    free_text: list[str],
    warnings: list[str],
    ctx: ShapeContext,
    next_step: str | None,
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "colunas": headers,
        "linhas": rows,
        "quantidade": len(rows),
        "truncado": truncated,
        "consistencia": CONSISTENCY,
        "lido_em": read_at.astimezone(UTC).isoformat(timespec="seconds"),
        "tabelas": list(tables),
        "pack": ctx.pack_version,
        "consulta_ms": round(ctx.elapsed_ms),
    }
    if ctx.plan_cost is not None:
        body["custo_estimado"] = float(f"{ctx.plan_cost:.3g}")
    if free_text:
        body["texto_livre"] = free_text
    if warnings:
        body["avisos"] = warnings
    if next_step:
        body["proximo_passo"] = next_step
    for key, value in ctx.extra:
        body.setdefault(key, value)
    return body


def _size(body: dict[str, Any]) -> int:
    return len(json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))


def shape_result(compiled: CompiledQuery, raw: RawResult, ctx: ShapeContext) -> dict[str, Any]:
    columns = list(compiled.columns)
    hidden = [i for i, c in enumerate(columns) if c.hidden]
    warnings: list[str] = []
    rows: list[list[Cell]] = []
    suppressed = 0
    guards = [i for i in (compiled.count_index, *compiled.contrib_indexes) if i is not None]
    for source in raw.rows[: compiled.limit]:
        if guards and any(_too_small(source[i]) for i in guards):
            suppressed += 1
            continue
        visible = [
            _mask_cell(col, value)
            for i, (col, value) in enumerate(zip(columns, source, strict=False))
            if i not in hidden
        ]
        rows.append(visible)
    headers = [c.header for c in columns if not c.hidden]
    visible_columns = [c for c in columns if not c.hidden]
    if suppressed:
        warnings.append(
            f"{suppressed} grupo(s) com menos de {MIN_GROUP_SIZE} linhas foram ocultados "
            "(dado pessoal agregado)"
        )
    for index, col in enumerate(visible_columns):
        if col.kind in ("date", "timestamp") and any(_implausible_year(r[index]) for r in rows):
            warnings.append(f"a coluna {col.header} tem data fora de 1980-2100: confira o dado")
    free_text = [c.header for c in visible_columns if c.mask == "texto"]

    truncated = raw.truncated
    next_step = None
    if truncated:
        next_step = "ha mais linhas: use `deslocamento` ou estreite os filtros"

    def build(kept: list[list[Cell]], is_truncated: bool, step: str | None) -> dict[str, Any]:
        return _envelope(
            headers,
            kept,
            truncated=is_truncated,
            read_at=raw.read_at,
            tables=compiled.tables,
            free_text=free_text,
            warnings=warnings,
            ctx=ctx,
            next_step=step,
        )

    body = build(rows, truncated, next_step)
    if _size(body) <= ctx.max_bytes:
        return body
    low, high = 0, len(rows)
    cut_step = (
        "resposta cortada em 12 KB: use `deslocamento`, menos colunas ou filtros mais estreitos"
    )
    while low < high:
        mid = (low + high + 1) // 2
        if _size(build(rows[:mid], True, cut_step)) <= ctx.max_bytes:
            low = mid
        else:
            high = mid - 1
    return build(rows[:low], True, cut_step)
