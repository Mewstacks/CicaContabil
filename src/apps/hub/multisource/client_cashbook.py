"""Planilha de caixa preparada pelo cliente (`.xlsx`) — D-409, PC-33.

Cada aba é uma conta (ex.: SICREDI, CAIXA, CEF) com colunas DATA, HISTÓRICO, ENTRADA, SAÍDA e
SALDO. Linhas sem entrada nem saída continuam o histórico da linha anterior (listas longas de
notas). O mês do cabeçalho da aba não é usado: só a data de cada linha. Referências (NF, CT-e) são
extraídas do histórico.
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from datetime import date

from apps.hub.multisource.common import (
    MAX_SOURCE_BYTES,
    MultisourceError,
    cents_from_number,
    parse_day,
)

LAYOUT = "client-cashbook-xlsx-v1"
MAX_ROWS = 100_000
HEADERS = {
    "DATA": "date",
    "HISTÓRICO": "history",
    "HISTORICO": "history",
    "ENTRADA": "inflow",
    "SAÍDA": "outflow",
    "SAIDA": "outflow",
    "SALDO": "balance",
}
TOKEN = re.compile(r"[A-ZÀ-Ú]+|\d+(?:/\d+)?")
KIND_WORDS = {
    "NF": "nf",
    "NFS": "nf",
    "NOTA": "nf",
    "NOTAS": "nf",
    "CTE": "cte",
    "CT": "cte",
    "FATURA": "doc",
    "DEBITO": "doc",
    "DÉBITO": "doc",
}


@dataclass(frozen=True)
class DocumentRef:
    kind: str  # "nf", "cte" ou "doc"
    number: str
    installment: str = ""

    def __str__(self) -> str:
        label = {"nf": "NF", "cte": "CT-e", "doc": "Doc."}[self.kind]
        return f"{label} {self.number}" + (f"/{self.installment}" if self.installment else "")


@dataclass(frozen=True)
class CashbookLine:
    sheet: str
    row: int
    occurred_on: date
    history: str
    inflow_cents: int
    outflow_cents: int
    balance_cents: int | None
    refs: tuple[DocumentRef, ...] = field(default=())

    @property
    def amount_cents(self) -> int:
        """Positivo para entrada, negativo para saída."""
        return self.inflow_cents - self.outflow_cents


@dataclass(frozen=True)
class CashbookSheet:
    name: str
    opening_cents: int
    lines: tuple[CashbookLine, ...]
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class Cashbook:
    sheets: tuple[CashbookSheet, ...]

    def sheet(self, name: str) -> CashbookSheet:
        wanted = name.strip().upper()
        for sheet in self.sheets:
            if sheet.name.strip().upper() == wanted:
                return sheet
        raise MultisourceError(
            f"Caixa do cliente: aba {name!r} não encontrada; abas: "
            + ", ".join(s.name for s in self.sheets)
        )


def extract_refs(history: str) -> tuple[DocumentRef, ...]:
    """Extrai NF/CT-e do histórico: "FRANC NF 29740/03", "PAGTO XY (CTE 323599, 323808)".

    Um número só vira referência quando vem depois de uma palavra de documento (NF, CTE, FATURA...).
    "SERIE 200" é ignorado. Parcela só quando o sufixo tem até 2 dígitos.
    """
    refs: list[DocumentRef] = []
    kind = ""
    skip_next = False
    for piece in TOKEN.findall(history.upper()):
        if piece.isalpha():
            if piece == "SERIE":
                skip_next = True
            elif piece in KIND_WORDS:
                kind = KIND_WORDS[piece]
            elif piece not in {"E", "DE"}:
                kind = "" if len(piece) > 2 else kind
            continue
        if skip_next:
            skip_next = False
            continue
        if not kind:
            continue
        number, _, installment = piece.partition("/")
        if len(installment) > 2:
            number, installment = piece, ""
        ref = DocumentRef(kind, number.lstrip("0") or "0", installment)
        if ref not in refs:
            refs.append(ref)
    return tuple(refs)


def parse_cashbook_sheet(name: str, rows: list[list[object]]) -> CashbookSheet | None:
    """Interpreta uma aba; devolve None se a aba não tiver o cabeçalho de caixa."""
    columns: dict[str, int] = {}
    opening = 0
    lines: list[dict[str, object]] = []
    warnings: list[str] = []
    for number, row in enumerate(rows, 1):
        texts = [str(c).strip().upper() if c not in (None, "") else "" for c in row]
        if not columns:
            found = {HEADERS[t]: i for i, t in enumerate(texts) if t in HEADERS}
            if {"date", "history", "inflow", "outflow"} <= set(found):
                columns = found
            continue

        def cell(key: str, row: list[object] = row, columns: dict[str, int] = columns) -> object:
            index = columns.get(key, -1)
            return row[index] if 0 <= index < len(row) else None

        history = str(cell("history") or "").strip()
        inflow, outflow = cents_from_number(cell("inflow")), cents_from_number(cell("outflow"))
        if history.upper() == "SALDO ANTERIOR":
            opening = cents_from_number(cell("balance"))
            continue
        if not history and not inflow and not outflow:
            continue
        if inflow < 0 or outflow < 0 or (inflow and outflow):
            raise MultisourceError(
                f"Caixa do cliente: aba {name}, linha {number} com entrada e saída ao mesmo tempo "
                "ou valor negativo."
            )
        if not inflow and not outflow:
            if lines:
                lines[-1]["history"] = f"{lines[-1]['history']} {history}".strip()
            else:
                warnings.append(
                    f"Aba {name}, linha {number}: histórico sem valor antes do 1º movimento."
                )
            continue
        try:
            occurred = parse_day(cell("date"))
        except MultisourceError as exc:
            raise MultisourceError(f"Caixa do cliente: aba {name}, linha {number}: {exc}") from exc
        if occurred is None:
            raise MultisourceError(f"Caixa do cliente: aba {name}, linha {number} sem data.")
        balance = cell("balance")
        lines.append(
            {
                "row": number,
                "date": occurred,
                "history": history,
                "inflow": inflow,
                "outflow": outflow,
                "balance": cents_from_number(balance)
                if isinstance(balance, (int, float))
                else None,
            }
        )
        if len(lines) > MAX_ROWS:
            raise MultisourceError("Caixa do cliente: aba excede 100.000 linhas.")
    if not columns:
        return None
    running = opening
    result = []
    for item in lines:
        running += int(item["inflow"]) - int(item["outflow"])  # type: ignore[call-overload]
        reported = item["balance"]
        if reported is not None and reported != running:
            warnings.append(
                f"Aba {name}, linha {item['row']}: saldo da planilha difere do calculado "
                f"({int(reported) / 100:.2f} vs. {running / 100:.2f})."  # type: ignore[call-overload]
            )
        history = str(item["history"])
        result.append(
            CashbookLine(
                name,
                int(item["row"]),  # type: ignore[call-overload]
                item["date"],  # type: ignore[arg-type]
                history,
                int(item["inflow"]),  # type: ignore[call-overload]
                int(item["outflow"]),  # type: ignore[call-overload]
                reported,  # type: ignore[arg-type]
                extract_refs(history),
            )
        )
    return CashbookSheet(name, opening, tuple(result), tuple(warnings))


def read_client_cashbook_xlsx(content: bytes) -> Cashbook:
    from openpyxl import load_workbook

    if len(content) > MAX_SOURCE_BYTES:
        raise MultisourceError("Caixa do cliente: arquivo maior que 25 MiB.")
    try:
        # data_only: usa o último valor calculado pelo Excel nas fórmulas de saldo.
        book = load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl levanta vários tipos para arquivo inválido
        raise MultisourceError(
            "Caixa do cliente: arquivo não é uma planilha .xlsx legível."
        ) from exc
    try:
        sheets = []
        for worksheet in book.worksheets:
            rows = [list(r) for r in worksheet.iter_rows(values_only=True)]
            parsed = parse_cashbook_sheet(worksheet.title, rows)
            if parsed is not None:
                sheets.append(parsed)
    finally:
        book.close()
    if not sheets:
        raise MultisourceError(
            "Caixa do cliente: nenhuma aba com DATA, HISTÓRICO, ENTRADA e SAÍDA."
        )
    return Cashbook(tuple(sheets))
