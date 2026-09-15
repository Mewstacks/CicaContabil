"""Bounded interpretation of the PARCSN escaped JSON response."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date
from typing import Any

MAX_DADOS_CHARS = 1_000_000
MAX_ROWS = 500


class ParcelamentoPayloadError(ValueError):
    """A paid response cannot be shown as a verified parcelment summary."""


@dataclass(frozen=True)
class ParcelamentoSummary:
    numero: int
    data_pedido: date | None
    situacao: str
    data_situacao: date | None


def _date(value: Any) -> date | None:
    raw = str(value or "")
    if len(raw) != 8 or not raw.isdigit():
        return None
    try:
        return date(int(raw[:4]), int(raw[4:6]), int(raw[6:]))
    except ValueError:
        return None


def pedidos(payload: dict[str, Any]) -> list[ParcelamentoSummary]:
    """Read the official `dados` string without losing an empty result."""

    if payload.get("status") != 200:
        raise ParcelamentoPayloadError("A consulta não retornou sucesso do Serpro.")
    dados = payload.get("dados")
    if not isinstance(dados, str) or len(dados) > MAX_DADOS_CHARS:
        raise ParcelamentoPayloadError("O retorno de parcelamentos veio fora do formato esperado.")
    try:
        document = json.loads(dados)
    except json.JSONDecodeError as exc:
        raise ParcelamentoPayloadError("O retorno de parcelamentos não contém JSON válido.") from exc
    if not isinstance(document, dict) or not isinstance(document.get("parcelamentos"), list):
        raise ParcelamentoPayloadError("A lista de parcelamentos não foi encontrada.")
    rows = document["parcelamentos"]
    if len(rows) > MAX_ROWS:
        raise ParcelamentoPayloadError("A lista excede o limite seguro de exibição.")
    summaries = []
    for row in rows:
        if not isinstance(row, dict):
            raise ParcelamentoPayloadError("Um parcelamento veio em formato inesperado.")
        numero = row.get("numero")
        if isinstance(numero, bool) or not isinstance(numero, int) or numero < 1:
            raise ParcelamentoPayloadError("Um parcelamento veio sem número válido.")
        summaries.append(
            ParcelamentoSummary(
                numero=numero,
                data_pedido=_date(row.get("dataDoPedido")),
                situacao=str(row.get("situacao") or "Situação não informada")[:160],
                data_situacao=_date(row.get("dataDaSituacao")),
            )
        )
    return summaries
