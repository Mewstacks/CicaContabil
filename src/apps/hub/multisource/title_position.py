"""Posição de contas a receber/pagar exportada pelo Domínio em `.xls` (D-409, PC-33).

Leiaute lido: relatório "CONTAS A RECEBER POR CLIENTE" / "CONTAS A PAGAR POR FORNECEDOR", com
grupos "Cliente:"/"Fornecedor:" (código - nome), uma linha por parcela, "Sub Total:" por grupo e
"Total Geral:". O documento é o número da nota, sem sufixo de parcela: a parcela recebe um ordinal
pelo vencimento.
"""

from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date

from apps.hub.multisource.common import (
    MAX_SOURCE_BYTES,
    MultisourceError,
    cents_from_number,
    parse_day,
)

RECEIVABLE = "receivable"
PAYABLE = "payable"
LAYOUT = "dominio-titles-position-xls-v1"

# Rótulos do cabeçalho → nome do campo. CR usa "Saída"/"V. Recebido"; CP usa "Entrada"/"Valor Pago".
HEADER_FIELDS = {
    "documento": "document",
    "emissao": "issued_on",
    "entrada": "moved_on",
    "saida": "moved_on",
    "vencimento": "due_on",
    "v. parcela": "amount",
    "valor pago": "paid",
    "v. recebido": "paid",
    "juros": "interest",
    "multa": "penalty",
    "outras": "other",
    "desconto": "discount",
    "devolucao": "returned",
    "saldo": "balance",
    "situacao": "status",
}
REQUIRED = {"document", "due_on", "amount", "paid", "balance", "status"}
STATUSES = {"Aberta", "Parcial"}


@dataclass(frozen=True)
class PositionInstallment:
    kind: str
    party_code: str
    party_name: str
    document: str
    ordinal: int
    count: int
    issued_on: date | None
    moved_on: date | None
    due_on: date
    amount_cents: int
    paid_cents: int
    interest_cents: int
    penalty_cents: int
    other_cents: int
    discount_cents: int
    returned_cents: int
    balance_cents: int
    status: str
    row: int

    @property
    def key(self) -> tuple[str, str, str, int]:
        return (self.kind, self.party_code, self.document, self.ordinal)

    @property
    def label(self) -> str:
        return f"NF {self.document} · parcela {self.ordinal}/{self.count} · {self.party_name}"


@dataclass(frozen=True)
class TitlePosition:
    kind: str
    company_name: str
    company_cnpj: str
    emitted_on: date | None
    installments: tuple[PositionInstallment, ...]
    reported_amount_cents: int
    reported_paid_cents: int
    reported_balance_cents: int
    warnings: tuple[str, ...]

    @property
    def balance_cents(self) -> int:
        return sum(i.balance_cents for i in self.installments)

    @property
    def open_installments(self) -> tuple[PositionInstallment, ...]:
        return tuple(i for i in self.installments if i.balance_cents > 0)


def _fold(value: object) -> str:
    text = str(value or "").strip().lower()
    for a, b in (
        ("ã", "a"),
        ("á", "a"),
        ("ç", "c"),
        ("í", "i"),
        ("é", "e"),
        ("ê", "e"),
        ("ó", "o"),
    ):
        text = text.replace(a, b)
    return text


def _cnpj(value: object) -> str:
    digits = re.sub(r"\D", "", str(value or ""))
    if isinstance(value, float) and value.is_integer():
        digits = str(int(value))
    return digits.zfill(14) if digits else ""


def parse_title_position_rows(rows: list[list[object]]) -> TitlePosition:
    """Interpreta as células (já com datas convertidas) de uma planilha da posição."""
    kind = ""
    company_name = company_cnpj = ""
    emitted_on: date | None = None
    columns: dict[str, int] = {}
    party_code = party_name = ""
    raw: list[dict[str, object]] = []
    totals: list[int] | None = None
    for number, row in enumerate(rows, 1):
        cells = list(row)
        texts = [str(c).strip() if c not in (None, "") else "" for c in cells]
        joined = " ".join(t for t in texts if t)
        if not joined:
            continue
        upper = joined.upper()
        if "CONTAS A RECEBER POR CLIENTE" in upper:
            kind = RECEIVABLE
            continue
        if "CONTAS A PAGAR POR FORNECEDOR" in upper:
            kind = PAYABLE
            continue
        first = texts[0] if texts else ""
        if first == "Empresa:":
            company_name = next((t for t in texts[1:] if t and not t.startswith("Página")), "")
            continue
        if first == "CNPJ:":
            company_cnpj = _cnpj(next((c for c in cells[1:] if c not in (None, "")), ""))
            if "Emissão:" in texts:
                emitted_on = _after_label(cells, texts, "Emissão:")
            continue
        if "Emissão:" in texts and not columns:
            emitted_on = emitted_on or _after_label(cells, texts, "Emissão:")
        if "Documento" in texts and "Situação" in texts:
            found = {}
            for index, text in enumerate(texts):
                field = HEADER_FIELDS.get(_fold(text))
                if field:
                    found[field] = index
            if not set(found) >= REQUIRED:
                raise MultisourceError("Posição de títulos: cabeçalho de colunas incompleto.")
            if columns and found != columns:
                raise MultisourceError("Posição de títulos: colunas mudaram no meio do arquivo.")
            columns = found
            continue
        if first in ("Cliente:", "Fornecedor:"):
            label = next((t for t in texts[1:] if t), "")
            code, _, name = label.partition(" - ")
            if not code.strip().isdigit() or not name.strip():
                raise MultisourceError(
                    f"Posição de títulos: grupo sem código/nome na linha {number}."
                )
            party_code, party_name = code.strip(), name.strip()
            continue
        if "Total Geral:" in texts:
            numbers = [cents_from_number(c) for c in cells if isinstance(c, (int, float))]
            saldo_index = columns.get("balance", -1)
            if len(numbers) < 2 or not 0 <= saldo_index < len(cells):
                raise MultisourceError("Posição de títulos: 'Total Geral' fora do leiaute.")
            # Valor da parcela e pago são os dois primeiros números; o saldo fica na coluna "Saldo".
            totals = [numbers[0], numbers[1], cents_from_number(cells[saldo_index])]
            continue
        if "Sub Total:" in texts:
            continue
        if not columns:
            continue
        status = texts[columns["status"]] if columns["status"] < len(texts) else ""
        if not status:
            continue
        if status not in STATUSES:
            raise MultisourceError(
                f"Posição de títulos: situação desconhecida {status!r} na linha {number}."
            )
        if not party_code:
            raise MultisourceError(
                f"Posição de títulos: parcela sem cliente/fornecedor na linha {number}."
            )
        record: dict[str, object] = {
            "row": number,
            "party_code": party_code,
            "party_name": party_name,
        }
        for field, index in columns.items():
            record[field] = cells[index] if index < len(cells) else None
        raw.append(record)
    if not kind:
        raise MultisourceError(
            "Arquivo não é a posição de contas a receber ou a pagar do Domínio "
            "(título não encontrado)."
        )
    if not columns:
        raise MultisourceError("Posição de títulos: cabeçalho de colunas não encontrado.")
    if totals is None or len(totals) < 3:
        raise MultisourceError(
            "Posição de títulos: linha 'Total Geral' ausente; arquivo incompleto?"
        )
    installments = [_installment(kind, r) for r in raw]
    installments = _with_ordinals(installments)
    reported_amount, reported_paid, reported_balance = totals[0], totals[1], totals[-1]
    balance = sum(i.balance_cents for i in installments)
    if balance != reported_balance:
        raise MultisourceError(
            "Posição de títulos: a soma dos saldos das parcelas não fecha com o Total Geral; "
            "revise o arquivo exportado."
        )
    warnings = [
        f"Parcela listada com saldo zero ({i.label}, linha {i.row}); fica fora do casamento."
        for i in installments
        if i.balance_cents == 0
    ]
    amount = sum(i.amount_cents for i in installments)
    paid = sum(i.paid_cents for i in installments)
    if amount != reported_amount or paid != reported_paid:
        # Q-59: o saldo fecha, mas valor da parcela e pago do Total Geral não; causa a confirmar.
        warnings.append(
            "Total Geral de valor da parcela/valor pago difere da soma das parcelas "
            f"({(reported_amount - amount) / 100:.2f} / {(reported_paid - paid) / 100:.2f}); "
            "o saldo fecha. Causa a confirmar com a contabilidade (Q-59)."
        )
    return TitlePosition(
        kind,
        company_name,
        company_cnpj,
        emitted_on,
        tuple(installments),
        reported_amount,
        reported_paid,
        reported_balance,
        tuple(warnings),
    )


def _after_label(cells: list[object], texts: list[str], label: str) -> date | None:
    index = texts.index(label)
    for cell in cells[index + 1 :]:
        if cell not in (None, ""):
            try:
                return parse_day(cell)
            except MultisourceError:
                return None
    return None


def _installment(kind: str, record: dict[str, object]) -> PositionInstallment:
    row = int(str(record["row"]))
    document = record.get("document")
    if isinstance(document, float) and document.is_integer():
        document = int(document)
    document_text = str(document or "").strip()
    due_on = parse_day(record.get("due_on"))
    if not document_text or due_on is None:
        raise MultisourceError(
            f"Posição de títulos: parcela sem documento ou vencimento na linha {row}."
        )

    def cents(field: str) -> int:
        return cents_from_number(record.get(field)) if field in record else 0

    item = PositionInstallment(
        kind=kind,
        party_code=str(record["party_code"]),
        party_name=str(record["party_name"]),
        document=document_text,
        ordinal=0,
        count=0,
        issued_on=parse_day(record.get("issued_on")),
        moved_on=parse_day(record.get("moved_on")),
        due_on=due_on,
        amount_cents=cents("amount"),
        paid_cents=cents("paid"),
        interest_cents=cents("interest"),
        penalty_cents=cents("penalty"),
        other_cents=cents("other"),
        discount_cents=cents("discount"),
        returned_cents=cents("returned"),
        balance_cents=cents("balance"),
        status=str(record["status"]).strip(),
        row=row,
    )
    if item.balance_cents < 0:
        raise MultisourceError(f"Posição de títulos: parcela com saldo negativo na linha {row}.")
    return item


def _with_ordinals(items: list[PositionInstallment]) -> list[PositionInstallment]:
    groups: dict[tuple[str, str], list[PositionInstallment]] = defaultdict(list)
    for item in items:
        groups[(item.party_code, item.document)].append(item)
    numbered: dict[int, PositionInstallment] = {}
    for group in groups.values():
        group.sort(key=lambda i: (i.due_on, i.row))
        for ordinal, item in enumerate(group, 1):
            numbered[item.row] = replace(item, ordinal=ordinal, count=len(group))
    return [numbered[i.row] for i in items]


def read_title_position_xls(content: bytes) -> TitlePosition:
    """Lê o `.xls` (BIFF) exportado pelo Domínio. Somente leitura; nada é gravado."""
    import xlrd

    if len(content) > MAX_SOURCE_BYTES:
        raise MultisourceError("Posição de títulos: arquivo maior que 25 MiB.")
    try:
        book = xlrd.open_workbook(file_contents=content, on_demand=True)
    except xlrd.XLRDError as exc:
        raise MultisourceError("Arquivo não é uma planilha .xls legível.") from exc
    try:
        sheet = book.sheet_by_index(0)
        rows: list[list[object]] = []
        for r in range(sheet.nrows):
            row: list[object] = []
            for c in range(sheet.ncols):
                cell = sheet.cell(r, c)
                if cell.ctype == xlrd.XL_CELL_DATE:
                    row.append(xlrd.xldate.xldate_as_datetime(cell.value, book.datemode).date())
                elif cell.ctype in (xlrd.XL_CELL_EMPTY, xlrd.XL_CELL_BLANK):
                    row.append(None)
                else:
                    row.append(cell.value)
            rows.append(row)
    finally:
        book.release_resources()
    return parse_title_position_rows(rows)
