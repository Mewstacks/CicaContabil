"""Relatório Financeiro Francesinha do Sicredi em PDF texto (D-409, PC-33).

Cada título liquidado tem Seu Nº, Nosso Nº, pagador, data do movimento, data de lançamento em c/c,
valor nominal, abatimento, desconto, juros, multa e valor do movimento. O nome do pagador e a
descrição do movimento podem quebrar em linhas acima e abaixo da linha principal; os pedaços são
devolvidos à linha principal mais próxima pela posição na página. O "Seu Nº" é guardado como veio
e não é interpretado como número da nota (Q-52).
"""

from __future__ import annotations

import io
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

from apps.hub.multisource.common import (
    MAX_SOURCE_BYTES,
    MultisourceError,
    cents_from_text,
    parse_day,
)

LAYOUT = "sicredi-francesinha-text-v1"
MAX_PAGES = 500
M = r"-?\d{1,3}(?:\.\d{3})*,\d{2}"
D = r"\d{2}/\d{2}/\d{4}"
OUR_NUMBER = re.compile(r"^\d{2}/\d{6}-\d$")
ROW = re.compile(
    rf"^(?P<your>\S+) (?P<our>\d{{2}}/\d{{6}}-\d) (?:(?P<payer>.+?) )??(?P<moved>{D})"
    rf"(?: (?P<credited>{D}))? (?P<nominal>{M}) (?P<abatement>{M}) (?P<discount>{M})"
    rf" (?P<interest>{M}) (?P<penalty>{M}) (?P<amount>{M}) (?P<kind>Crédito|Débito)"
    rf"(?: (?P<description>.*?))? (?P<wallet>[A-Za-zÀ-ú]+) (?P<agency>\d{{4}})"
    rf" (?P<account>[\d-]+) (?P<share>[\d,]+%) (?P<value>{M})$"
)


@dataclass(frozen=True)
class CollectionItem:
    your_number: str
    our_number: str
    payer: str
    moved_on: date
    credited_on: date | None
    nominal_cents: int
    abatement_cents: int
    discount_cents: int
    interest_cents: int
    penalty_cents: int
    amount_cents: int
    kind: str
    description: str
    page: int
    line: int

    @property
    def invoice_from_your_number(self) -> str:
        """NF codificada no Seu Nº `*1NNNNNNPP` (D-420, Q-52); vazio nos demais formatos.

        A parcela (PP) não é usada: a posição do Domínio numera só as parcelas em aberto."""
        match = re.fullmatch(r"\*1(\d{6})(\d{2})", self.your_number.strip())
        return match[1].lstrip("0") if match else ""

    @property
    def extra_cents(self) -> int:
        """Juros + multa recebidos além do nominal."""
        return self.interest_cents + self.penalty_cents


@dataclass(frozen=True)
class CollectionReport:
    period_start: date
    period_end: date
    account: str
    movement_kind: str
    items: tuple[CollectionItem, ...]
    reported_count: int
    reported_credit_cents: int
    reported_interest_cents: int
    reported_penalty_cents: int
    reported_discount_cents: int
    reported_abatement_cents: int


def _lines(words: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    rows: list[list[dict[str, Any]]] = []
    for word in sorted(words, key=lambda w: (float(w["top"]), float(w["x0"]))):
        if not rows or abs(float(word["top"]) - float(rows[-1][0]["top"])) > 2:
            rows.append([])
        rows[-1].append(word)
    for row in rows:
        row.sort(key=lambda w: float(w["x0"]))
    return rows


def _text(row: list[dict[str, Any]]) -> str:
    return " ".join(str(w["text"]) for w in row)


def _header(text: str, pattern: str) -> re.Match[str] | None:
    return re.search(pattern, text)


def parse_collection_pages(pages: list[list[dict[str, Any]]]) -> CollectionReport:
    """Interpreta as palavras (pdfplumber `extract_words`) de cada página."""
    if not pages:
        raise MultisourceError("Francesinha: PDF sem páginas.")
    first_text = "\n".join(_text(r) for r in _lines(pages[0]))
    if "Francesinha" not in first_text:
        raise MultisourceError("Arquivo não é o Relatório Financeiro Francesinha do Sicredi.")
    period = _header(first_text, rf"período ({D}) a ({D})")
    account = _header(first_text, r"Conta Corrente:\s*(\d+)")
    kind = _header(first_text, r"Tipo de movimento:\s*(\S+)")
    count = _header(first_text, r"Quantidade de Títulos:\s*(\d+)")
    totals = {
        name: _header(first_text, rf"{label}\s+(\d+)\s+R\$\s*({M})")
        for name, label in (
            ("credit", "Total de Créditos"),
            ("interest", "Total Juros"),
            ("penalty", "Total Multa"),
            ("discount", "Total Desconto"),
            ("abatement", "Total Abatimento"),
        )
    }
    if not (period and account and kind and count and all(totals.values())):
        raise MultisourceError("Francesinha: cabeçalho com período, conta e totais não encontrado.")
    start, end = parse_day(period[1]), parse_day(period[2])
    assert start and end

    items: list[CollectionItem] = []
    for page_number, words in enumerate(pages, 1):
        rows = _lines(words)
        header_index = next(
            (i for i, r in enumerate(rows) if "Pagador" in _text(r) and "Nominal" in _text(r)), None
        )
        if header_index is None:
            continue
        mains: list[tuple[float, re.Match[str], int]] = []
        others: list[list[dict[str, Any]]] = []
        payer_start = payer_end = desc_start = desc_end = None
        for line_number, row in enumerate(rows[header_index + 1 :], header_index + 2):
            text = _text(row)
            if len(row) >= 2 and OUR_NUMBER.fullmatch(str(row[1]["text"])):
                match = ROW.fullmatch(text)
                if not match:
                    raise MultisourceError(
                        f"Francesinha: linha fora do leiaute na página {page_number}: {text[:60]}"
                    )
                mains.append((float(row[0]["top"]), match, line_number))
                # Colunas centralizadas: as faixas de pagador e descrição ficam entre as colunas
                # vizinhas das linhas de título, não sob o rótulo do cabeçalho.
                kind_word = next(w for w in row if w["text"] in ("Crédito", "Débito"))
                date_word = next(w for w in row if re.fullmatch(D, str(w["text"])))
                bounds = (
                    float(row[1]["x1"]),
                    float(date_word["x0"]),
                    float(kind_word["x1"]),
                    float(row[-5]["x0"]),
                )
                payer_start = max(payer_start or 0.0, bounds[0])
                payer_end = min(payer_end or bounds[1], bounds[1])
                desc_start = max(desc_start or 0.0, bounds[2])
                desc_end = min(desc_end or bounds[3], bounds[3])
                continue
            others.append(row)
        if not mains:
            continue
        assert payer_start is not None and payer_end and desc_start is not None and desc_end
        fragments: list[tuple[float, str, str]] = []  # (top, coluna, texto)
        for row in others:
            if float(row[0]["x0"]) < payer_start - 1:
                continue  # rodapé ou texto fora das colunas de pagador/descrição
            payer = " ".join(
                str(w["text"]) for w in row if payer_start <= float(w["x0"]) < payer_end
            )
            description = " ".join(
                str(w["text"]) for w in row if desc_start <= float(w["x0"]) < desc_end
            )
            if payer:
                fragments.append((float(row[0]["top"]), "payer", payer))
            if description:
                fragments.append((float(row[0]["top"]), "description", description))
        if not mains:
            continue
        extra: dict[int, dict[str, list[tuple[float, str]]]] = {
            i: {"payer": [], "description": []} for i in range(len(mains))
        }
        for top, column, text in fragments:
            nearest = min(range(len(mains)), key=lambda i: (abs(mains[i][0] - top), i))
            extra[nearest][column].append((top, text))
        for index, (top, match, line_number) in enumerate(mains):
            payer = _merge(top, match["payer"], extra[index]["payer"])
            description = _merge(top, match["description"], extra[index]["description"])
            if not payer:
                raise MultisourceError(
                    f"Francesinha: título {match['our']} sem pagador (página {page_number})."
                )
            moved = parse_day(match["moved"])
            assert moved
            item = CollectionItem(
                your_number=match["your"],
                our_number=match["our"],
                payer=payer,
                moved_on=moved,
                credited_on=parse_day(match["credited"]) if match["credited"] else None,
                nominal_cents=cents_from_text(match["nominal"]),
                abatement_cents=cents_from_text(match["abatement"]),
                discount_cents=cents_from_text(match["discount"]),
                interest_cents=cents_from_text(match["interest"]),
                penalty_cents=cents_from_text(match["penalty"]),
                amount_cents=cents_from_text(match["amount"]),
                kind=match["kind"],
                description=description,
                page=page_number,
                line=line_number,
            )
            expected = (
                item.nominal_cents
                - item.abatement_cents
                - item.discount_cents
                + item.interest_cents
                + item.penalty_cents
            )
            if (
                expected != item.amount_cents
                or cents_from_text(match["value"]) != item.amount_cents
            ):
                raise MultisourceError(
                    f"Francesinha: valores do título {item.our_number} não fecham; revise o PDF."
                )
            items.append(item)
    report = CollectionReport(
        start,
        end,
        account[1],
        kind[1],
        tuple(items),
        int(count[1]),
        cents_from_text(totals["credit"][2]),  # type: ignore[index]
        cents_from_text(totals["interest"][2]),  # type: ignore[index]
        cents_from_text(totals["penalty"][2]),  # type: ignore[index]
        cents_from_text(totals["discount"][2]),  # type: ignore[index]
        cents_from_text(totals["abatement"][2]),  # type: ignore[index]
    )
    _check_totals(report)
    return report


def _merge(top: float, inline: str | None, parts: list[tuple[float, str]]) -> str:
    above = [t for y, t in sorted(parts) if y < top]
    below = [t for y, t in sorted(parts) if y >= top]
    return " ".join([*above, *([inline] if inline else []), *below]).strip()


def _check_totals(report: CollectionReport) -> None:
    items = report.items
    if len(items) != report.reported_count:
        raise MultisourceError(
            f"Francesinha: {len(items)} títulos lidos, o relatório informa {report.reported_count}."
        )
    checks = (
        ("créditos", sum(i.amount_cents for i in items), report.reported_credit_cents),
        ("juros", sum(i.interest_cents for i in items), report.reported_interest_cents),
        ("multa", sum(i.penalty_cents for i in items), report.reported_penalty_cents),
        ("desconto", sum(i.discount_cents for i in items), report.reported_discount_cents),
        ("abatimento", sum(i.abatement_cents for i in items), report.reported_abatement_cents),
    )
    for name, read, reported in checks:
        if read != reported:
            raise MultisourceError(
                f"Francesinha: total de {name} lido ({read / 100:.2f}) difere do informado "
                f"({reported / 100:.2f}); revise o PDF."
            )
    for item in items:
        if not report.period_start <= item.moved_on <= report.period_end and not (
            item.credited_on and report.period_start <= item.credited_on <= report.period_end
        ):
            raise MultisourceError(f"Francesinha: título {item.our_number} fora do período.")


def read_francesinha_pdf(content: bytes) -> CollectionReport:
    import pdfplumber

    if len(content) > MAX_SOURCE_BYTES:
        raise MultisourceError("Francesinha: arquivo maior que 25 MiB.")
    try:
        with pdfplumber.open(io.BytesIO(content)) as pdf:
            if len(pdf.pages) > MAX_PAGES:
                raise MultisourceError("Francesinha: PDF excede 500 páginas.")
            pages = [page.extract_words() for page in pdf.pages]
    except MultisourceError:
        raise
    except Exception as exc:  # pdfplumber/pdfminer levantam tipos variados para PDF inválido
        raise MultisourceError("Francesinha: PDF ilegível.") from exc
    return parse_collection_pages(pages)
