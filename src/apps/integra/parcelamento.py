"""Bounded interpretation of the PARCSN escaped JSON response."""

from __future__ import annotations

import base64
import binascii
import json
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

MAX_DADOS_CHARS = 1_000_000
MAX_ROWS = 500
MAX_PDF_BYTES = 3_000_000


class ParcelamentoPayloadError(ValueError):
    """A paid response cannot be shown as a verified parcelment summary."""


@dataclass(frozen=True)
class ParcelamentoSummary:
    numero: int
    data_pedido: date | None
    situacao: str
    data_situacao: date | None


@dataclass(frozen=True)
class ParcelamentoPagamento:
    mes_parcela: int
    vencimento: date | None
    arrecadado_em: date | None
    valor_pago: Decimal | None


@dataclass(frozen=True)
class ParcelamentoDetalhe:
    resumo: ParcelamentoSummary
    valor_consolidado: Decimal | None
    quantidade_parcelas: int | None
    parcela_basica: Decimal | None
    pagamentos: tuple[ParcelamentoPagamento, ...]


@dataclass(frozen=True)
class ParcelaDisponivel:
    ano_mes: int
    valor: Decimal


def _date(value: Any) -> date | None:
    raw = str(value or "")
    if len(raw) != 8 or not raw.isdigit():
        return None
    try:
        return date(int(raw[:4]), int(raw[4:6]), int(raw[6:]))
    except ValueError:
        return None


def _document(payload: dict[str, Any], *, max_chars: int = MAX_DADOS_CHARS) -> dict[str, Any]:
    if payload.get("status") != 200:
        raise ParcelamentoPayloadError("A consulta não retornou sucesso do Serpro.")
    dados = payload.get("dados")
    if not isinstance(dados, str) or len(dados) > max_chars:
        raise ParcelamentoPayloadError("O retorno de parcelamentos veio fora do formato esperado.")
    try:
        document = json.loads(dados)
    except json.JSONDecodeError as exc:
        raise ParcelamentoPayloadError(
            "O retorno de parcelamentos não contém JSON válido."
        ) from exc
    if not isinstance(document, dict):
        raise ParcelamentoPayloadError("O retorno de parcelamentos não contém um objeto.")
    return document


def _money(value: Any, *, optional: bool = False) -> Decimal | None:
    if value is None and optional:
        return None
    if isinstance(value, bool) or value is None:
        raise ParcelamentoPayloadError("O Serpro devolveu um valor monetário inválido.")
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ParcelamentoPayloadError("O Serpro devolveu um valor monetário inválido.") from exc
    exponent = amount.as_tuple().exponent
    if (
        not amount.is_finite()
        or amount < 0
        or not isinstance(exponent, int)
        or exponent < -2
    ):
        raise ParcelamentoPayloadError("O Serpro devolveu um valor monetário inválido.")
    return amount


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ParcelamentoPayloadError(f"O Serpro devolveu {label} inválido.")
    return int(value)


def _year_month(value: Any) -> int:
    year_month = _positive_int(value, "o mês da parcela")
    year, month = divmod(year_month, 100)
    if year < 2000 or month < 1 or month > 12:
        raise ParcelamentoPayloadError("O Serpro devolveu o mês da parcela fora do formato AAAAMM.")
    return year_month


def _summary(row: dict[str, Any]) -> ParcelamentoSummary:
    return ParcelamentoSummary(
        numero=_positive_int(row.get("numero"), "o número do parcelamento"),
        data_pedido=_date(row.get("dataDoPedido")),
        situacao=str(row.get("situacao") or "Situação não informada")[:160],
        data_situacao=_date(row.get("dataDaSituacao")),
    )


def pedidos(payload: dict[str, Any]) -> list[ParcelamentoSummary]:
    """Read the official `dados` string without losing an empty result."""

    document = _document(payload)
    if not isinstance(document, dict) or not isinstance(document.get("parcelamentos"), list):
        raise ParcelamentoPayloadError("A lista de parcelamentos não foi encontrada.")
    rows = document["parcelamentos"]
    if len(rows) > MAX_ROWS:
        raise ParcelamentoPayloadError("A lista excede o limite seguro de exibição.")
    summaries = []
    for row in rows:
        if not isinstance(row, dict):
            raise ParcelamentoPayloadError("Um parcelamento veio em formato inesperado.")
        summaries.append(_summary(row))
    return summaries


def detalhe(payload: dict[str, Any], *, numero_esperado: int) -> ParcelamentoDetalhe:
    """Read a selected agreement, refusing another agreement's response."""

    document = _document(payload)
    row = document.get("parcelamento")
    if not isinstance(row, dict):
        raise ParcelamentoPayloadError("O Serpro não devolveu o detalhe do parcelamento.")
    summary = _summary(row)
    if summary.numero != numero_esperado:
        raise ParcelamentoPayloadError("O Serpro devolveu outro parcelamento.")
    consolidation = row.get("consolidacaoOriginal")
    if consolidation is not None and not isinstance(consolidation, dict):
        raise ParcelamentoPayloadError("A consolidação veio em formato inesperado.")
    consolidation = consolidation or {}
    payments = row.get("demonstrativoPagamentos", [])
    if not isinstance(payments, list) or len(payments) > MAX_ROWS:
        raise ParcelamentoPayloadError("O demonstrativo de pagamentos veio fora do limite.")
    parsed_payments = []
    for payment in payments:
        if not isinstance(payment, dict):
            raise ParcelamentoPayloadError("Uma parcela paga veio em formato inesperado.")
        parsed_payments.append(
            ParcelamentoPagamento(
                mes_parcela=_year_month(payment.get("mesDaParcela")),
                vencimento=_date(payment.get("vencimentoDoDas")),
                arrecadado_em=_date(payment.get("dataDeArrecadacao")),
                valor_pago=_money(payment.get("valorPago"), optional=True),
            )
        )
    count = consolidation.get("quantidadeParcelas")
    return ParcelamentoDetalhe(
        resumo=summary,
        valor_consolidado=_money(consolidation.get("valorTotalConsolidado"), optional=True),
        quantidade_parcelas=(
            _positive_int(count, "a quantidade de parcelas") if count is not None else None
        ),
        parcela_basica=_money(consolidation.get("parcelaBasica"), optional=True),
        pagamentos=tuple(parsed_payments),
    )


def parcelas_disponiveis(payload: dict[str, Any]) -> list[ParcelaDisponivel]:
    """The official schema says listaParcela, while its example uses listaParcelas."""

    document = _document(payload)
    rows = document.get("listaParcelas", document.get("listaParcela"))
    if not isinstance(rows, list) or len(rows) > MAX_ROWS:
        raise ParcelamentoPayloadError("A lista de parcelas disponíveis veio fora do formato.")
    result = []
    seen: set[int] = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ParcelamentoPayloadError("Uma parcela disponível veio em formato inesperado.")
        year_month = _year_month(row.get("parcela"))
        if year_month in seen:
            raise ParcelamentoPayloadError("O Serpro repetiu uma parcela disponível.")
        seen.add(year_month)
        amount = _money(row.get("valor"))
        assert amount is not None
        result.append(ParcelaDisponivel(ano_mes=year_month, valor=amount))
    return result


def pdf_das(payload: dict[str, Any]) -> bytes:
    """Decode only a bounded real PDF, never arbitrary provider-supplied bytes."""

    document = _document(payload, max_chars=(MAX_PDF_BYTES * 4 // 3) + 1000)
    encoded = document.get("docArrecadacaoPdfB64")
    if not isinstance(encoded, str) or len(encoded) > (MAX_PDF_BYTES * 4 // 3) + 8:
        raise ParcelamentoPayloadError("O DAS não veio como PDF dentro do limite seguro.")
    try:
        document_bytes = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ParcelamentoPayloadError("O DAS devolvido pelo Serpro não é base64 válido.") from exc
    if (
        len(document_bytes) > MAX_PDF_BYTES
        or not document_bytes.startswith(b"%PDF-")
        or b"%%EOF" not in document_bytes[-1024:]
    ):
        raise ParcelamentoPayloadError("O DAS devolvido pelo Serpro não é um PDF válido.")
    return document_bytes
