"""Documentos escaneados (boletos, recibos, DANFE, CT-e) lidos por OCR local — D-412, PC-33.

O OCR roda só na máquina (Tesseract `por`, o mesmo binário da conciliação). No boleto, valor e
vencimento vêm da linha digitável, cujos dígitos verificadores (módulo 10 dos campos e módulo 11 do
código de barras) são conferidos: um dígito lido errado invalida a linha em vez de produzir valor
errado. Nos demais documentos, valor, CNPJ e número vêm do texto, com a confiança do OCR registrada.

D-414: guias e contas de consumo pela linha de 48 dígitos (dígitos de bloco e geral conferidos),
linha do boleto tolerante a separadores lidos errado, valor por extenso e soma de valores da página
como confirmação da leitura. O extenso nunca substitui sozinho o valor em algarismos.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from difflib import get_close_matches
from itertools import combinations
from pathlib import PurePath

from apps.hub.multisource.common import MultisourceError, cents_from_text, money

LOW_CONFIDENCE = 90
# Escaneados são imagens: 50 páginas passam fácil de 25 MiB (limite das demais fontes).
MAX_SCAN_BYTES = 100 * 1024 * 1024
MAX_PAGES = 300
# Fator de vencimento: a contagem recomeçou em 1000 em 22/02/2025 (base anterior 07/10/1997).
FACTOR_BASE = date(2025, 2, 22)
# Separadores entre campos: o OCR troca o ponto por vírgula ou dois-pontos, cola campos, lê a
# borda da caixa como barra e gruda ruído no começo ("123793.39704"). A busca é sobreposta
# (lookahead) para um trecho inválido não esconder a linha que começa dentro dele; os dígitos
# verificadores decidem se a linha vale (D-414).
_SEP = r"[\s.,:;|]*"
LINE_PATTERN = re.compile(
    rf"(?=(\d{{5}}){_SEP}(\d{{5}}){_SEP}(\d{{5}}){_SEP}(\d{{6}}){_SEP}(\d{{5}}){_SEP}(\d{{6}})"
    rf"{_SEP}(\d){_SEP}(\d{{14}}))"
)
# Guia de arrecadação e conta de consumo: 4 blocos de 11 dígitos, cada um com seu dígito (D-414).
_BLOCK = r"(\d{11})[\s-]*(\d)"
COLLECTION_LINE_PATTERN = re.compile(
    rf"(?=(8\d{{10}})[\s-]*(\d){_SEP}{_BLOCK}{_SEP}{_BLOCK}{_SEP}{_BLOCK})"
)
# CNPJ formatado (00.000.000/0000-00) ou 14 dígitos logo após o rótulo "CNPJ"; dígitos soltos
# (como o final da linha digitável) não contam.
CNPJ_PATTERN = re.compile(
    r"\b(\d{2})\.(\d{3})\.(\d{3})/(\d{4})-(\d{2})\b"
    r"|CNPJ\s*:?\s*(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})\b"
)
MONEY = r"(\d{1,3}(?:\.\d{3})*,\d{2})"


@dataclass(frozen=True)
class BoletoLine:
    bank: str  # código do banco; vazio na guia de arrecadação
    due_on: date | None
    amount_cents: int
    barcode: str
    kind: str = "boleto"  # boleto | guia


@dataclass(frozen=True)
class ScannedDocument:
    source: str
    page: int
    kind: str  # boleto | recibo | danfe | cte | fatura | outro
    amount_cents: int | None
    due_on: date | None
    tax_ids: tuple[str, ...]
    number: str
    confidence: int
    boleto: BoletoLine | None = None
    issuer: str = ""
    refs: tuple[str, ...] = field(default=())
    # Valor confirmado na página: repetido, igual ao extenso ou à soma de outros dois (D-414).
    corroborated: bool = False
    note: str = ""

    @property
    def is_payment(self) -> bool:
        return self.kind in PAYMENT_KINDS and bool(self.amount_cents)

    @property
    def uncertain(self) -> bool:
        return self.boleto is None and self.confidence < LOW_CONFIDENCE and not self.corroborated

    @property
    def label(self) -> str:
        parts = [self.kind.upper(), self.issuer or (self.tax_ids[0] if self.tax_ids else "")]
        if self.number:
            parts.append(f"nº {self.number}")
        return " ".join(p for p in parts if p) + f" ({self.source} p. {self.page})"


def _mod10(digits: str) -> int:
    total = 0
    for index, char in enumerate(reversed(digits)):
        product = int(char) * (2 if index % 2 == 0 else 1)
        total += product // 10 + product % 10
    return (10 - total % 10) % 10


PAYMENT_KINDS = ("boleto", "guia", "recibo", "fatura")


def _mod11_barcode(digits: str) -> int:
    total, weight = 0, 2
    for char in reversed(digits):
        total += int(char) * weight
        weight = 2 if weight == 9 else weight + 1
    result = 11 - total % 11
    return 1 if result in (0, 10, 11) else result


def parse_boleto_line(text: str) -> BoletoLine | None:
    """Primeira linha digitável válida do texto (boleto bancário de 47 dígitos)."""
    for match in LINE_PATTERN.finditer(text):
        f1 = match[1] + match[2]
        f2 = match[3] + match[4]
        f3 = match[5] + match[6]
        general, tail = match[7], match[8]
        if (
            _mod10(f1[:9]) != int(f1[9])
            or _mod10(f2[:10]) != int(f2[10])
            or _mod10(f3[:10]) != int(f3[10])
        ):
            continue
        free = f1[4:9] + f2[:10] + f3[:10]
        barcode = f1[:4] + general + tail + free
        if _mod11_barcode(barcode[:4] + barcode[5:]) != int(general):
            continue
        factor, value = int(tail[:4]), int(tail[4:])
        due = FACTOR_BASE + timedelta(days=factor - 1000) if factor >= 1000 else None
        if due and not date(2020, 1, 1) <= due <= date(2035, 12, 31):
            due = None  # fator fora do padrão (alguns emissores): vencimento vem do texto
        return BoletoLine(f1[:3], due, value, barcode)
    return None


def _mod11_collection(digits: str) -> int:
    total, weight = 0, 2
    for char in reversed(digits):
        total += int(char) * weight
        weight = 2 if weight == 9 else weight + 1
    rest = total % 11
    return 0 if rest in (0, 1) else 11 - rest


def parse_collection_line(text: str) -> BoletoLine | None:
    """Primeira linha válida de guia ou conta de consumo (48 dígitos, começa por 8).

    O identificador de valor (3º dígito) escolhe o módulo: 6 e 7 usam módulo 10; 8 e 9, módulo 11.
    Só 6 e 8 trazem valor efetivo em reais; 7 e 9 trazem quantidade de referência (sem valor)."""
    for match in COLLECTION_LINE_PATTERN.finditer(text):
        blocks = [match[i] for i in (1, 3, 5, 7)]
        checks = [int(match[i]) for i in (2, 4, 6, 8)]
        barcode = "".join(blocks)
        value_id = barcode[2]
        if value_id not in "6789":
            continue
        check = _mod10 if value_id in "67" else _mod11_collection
        if any(check(block) != dv for block, dv in zip(blocks, checks, strict=True)):
            continue
        if check(barcode[:3] + barcode[4:]) != int(barcode[3]):
            continue
        value = int(barcode[4:15]) if value_id in "68" else 0
        return BoletoLine("", None, value, barcode, kind="guia")
    return None


UNITS = {
    "UM": 1, "UMA": 1, "DOIS": 2, "DUAS": 2, "TRES": 3, "QUATRO": 4, "CINCO": 5, "SEIS": 6,
    "SETE": 7, "OITO": 8, "NOVE": 9, "DEZ": 10, "ONZE": 11, "DOZE": 12, "TREZE": 13,
    "QUATORZE": 14, "CATORZE": 14, "QUINZE": 15, "DEZESSEIS": 16, "DEZESSETE": 17, "DEZOITO": 18,
    "DEZENOVE": 19, "VINTE": 20, "TRINTA": 30, "QUARENTA": 40, "CINQUENTA": 50, "SESSENTA": 60,
    "SETENTA": 70, "OITENTA": 80, "NOVENTA": 90, "CEM": 100, "CENTO": 100, "DUZENTOS": 200,
    "DUZENTAS": 200, "TREZENTOS": 300, "TREZENTAS": 300, "QUATROCENTOS": 400,
    "QUATROCENTAS": 400, "QUINHENTOS": 500, "QUINHENTAS": 500, "SEISCENTOS": 600,
    "SEISCENTAS": 600, "SETECENTOS": 700, "SETECENTAS": 700, "OITOCENTOS": 800,
    "OITOCENTAS": 800, "NOVECENTOS": 900, "NOVECENTAS": 900,
}  # fmt: skip
SCALES = {"MIL": 1_000, "MILHAO": 1_000_000, "MILHOES": 1_000_000}
CURRENCY = {"REAL": "reais", "REAIS": "reais", "CENTAVO": "centavos", "CENTAVOS": "centavos"}
_WORDS = (*UNITS, *SCALES, *CURRENCY)


def _word(token: str) -> str:
    """Palavra do extenso reconhecida, tolerando erro de grafia do OCR em palavras longas."""
    if token in UNITS or token in SCALES or token in CURRENCY or token in ("E", "DE"):
        return token
    if len(token) >= 5:
        close = get_close_matches(token, _WORDS, n=1, cutoff=0.85)
        if close:
            return close[0]
    return ""


def _words_value(words: list[str]) -> int | None:
    total = current = 0
    seen = False
    for word in words:
        if word in ("E", "DE"):
            continue
        if word in UNITS:
            current += UNITS[word]
            seen = True
        elif word in SCALES:
            total += (current or 1) * SCALES[word]
            current = 0
            seen = True
    return total + current if seen else None


def amount_in_words(text: str) -> int | None:
    """Valor por extenso em centavos ("seiscentos e cinquenta reais e dez centavos")."""
    plain = unicodedata.normalize("NFKD", text.upper()).encode("ascii", "ignore").decode()
    tokens = [_word(token) for token in re.findall(r"[A-Z]+", plain)]
    run: list[str] = []
    reais: int | None = None
    for token in tokens:
        if not token:
            if reais is not None:
                return reais * 100
            run = []
            continue
        if CURRENCY.get(token) == "reais":
            value = _words_value(run)
            if value is not None:
                reais = value
            run = []
        elif CURRENCY.get(token) == "centavos":
            cents = _words_value(run)
            if cents is not None and cents < 100 and (reais is not None or run):
                return (reais or 0) * 100 + cents
            run = []
        else:
            run.append(token)
    return reais * 100 if reais is not None else None


def _kind(text: str, boleto: BoletoLine | None) -> str:
    upper = text.upper()
    if boleto:
        return boleto.kind
    # Documento fiscal antes de "recibo": CT-e e DANFE trazem "recibo do sacado/pagador" no rodapé.
    if "DANFE" in upper or "DOCUMENTO AUXILIAR DA NOTA FISCAL" in upper:
        return "danfe"
    if "CT-E" in upper or "DACTE" in upper or "CONHECIMENTO DE TRANSPORTE" in upper:
        return "cte"
    if "FICHA DE COMPENSA" in upper or "RECIBO DO PAGADOR" in upper:
        return "boleto"
    if "RECIBO" in upper:
        return "recibo"
    if "FATURA" in upper or re.search(r"TOTAL\s*A\s*PAGAR", upper):
        return "fatura"  # conta de consumo sem a palavra "fatura" legível (D-414)
    return "outro"


AMOUNT_LABELS = (
    "Valor do Documento",
    "Valor Cobrado",
    r"Total\s*a\s*pagar",
    "Total desta Fatura",
    r"Total (?:da )?fatura",
    "Pagamento Total",
    "L[ií]quido",
    "Soma",
    "Valor Total da Nota",
)
MIN_BOLETO_CONFIDENCE = 75


def _money_values(text: str) -> list[int]:
    # Percentuais ("50,00%") não são valores.
    pattern = r"(?<![\d.,])" + MONEY + r"(?![\d,]|\s*%)"
    return [cents_from_text(m) for m in re.findall(pattern, text)]


def _first_amount(text: str, labels: tuple[str, ...]) -> int | None:
    for label in labels:
        match = re.search(label + r"[^\d\n]{0,40}\n?[^\d\n]{0,40}" + MONEY, text, re.I)
        if match:
            return cents_from_text(match[1])
    return None


def _sum_of_two(amount: int, values: list[int]) -> bool:
    # Valores repetidos contam: dois sócios com 5.000,00 cada somam o total de 10.000,00.
    others = [v for v in values if 0 < v < amount][:200]
    return any(a + b == amount for a, b in combinations(others, 2))


def extract_document(
    text: str, *, source: str, page: int, confidence: int, own_tax_id: str = ""
) -> ScannedDocument:
    """Interpreta o texto de uma página. Não lança erro: campos não lidos ficam vazios."""
    boleto = parse_boleto_line(text) or parse_collection_line(text)
    tax_ids = []
    for match in CNPJ_PATTERN.finditer(text):
        digits = "".join(g for g in match.groups() if g)
        if digits != own_tax_id and digits not in tax_ids:
            tax_ids.append(digits)
    if (
        boleto
        and confidence < MIN_BOLETO_CONFIDENCE
        and boleto.amount_cents not in _money_values(text)
    ):
        # Com OCR fraco, os dígitos verificadores podem fechar por acaso (1 em 11 no geral):
        # sem o valor confirmado no texto, a linha é descartada.
        boleto = None
    kind = _kind(text, boleto)
    amount: int | None
    if boleto:
        amount = boleto.amount_cents or None
    else:
        amount = _first_amount(text, AMOUNT_LABELS)
        if amount is None and kind == "recibo":
            total = re.search(r"\bTOTAL\b[^\n]*?R\$\s*" + MONEY, text, re.I)
            if total:
                amount = cents_from_text(total[1])
            else:
                # O valor repetido nos campos (aluguel, soma, líquido) é o valor pago.
                values = Counter(_money_values(text)).most_common(1)
                amount = values[0][0] if values and values[0][1] >= 2 else None
    due = boleto.due_on if boleto else None
    found = re.search(r"Vencimento[^\d]{0,20}(\d{2}/\d{2}/\d{4})", text, re.I)
    if due is None and found:
        day, month, year = (int(x) for x in found[1].split("/"))
        try:
            due = date(year, month, day)
        except ValueError:
            due = None
    number_match = re.search(
        r"N(?:[ºo°]|r\.?|úmero)\s*(?:do\s*)?Documento\s*[:\n ]\s*([0-9][0-9./-]{1,20})", text, re.I
    )
    number = number_match[1].strip(".-/") if number_match else ""
    found_refs = re.findall(r"\b(?:NF-?e?|CT-?e)\s*(?:n[ºo°]\s*)?(\d{3,9})", text, re.I)
    refs = tuple(dict.fromkeys(found_refs))
    issuer = ""
    issuer_match = re.search(r"Benefici[áa]rio\s*[:\n]?\s*([A-ZÀ-Ú0-9 .&-]{4,60})", text)
    if issuer_match:
        issuer = " ".join(issuer_match[1].split())
    values = _money_values(text)
    words = amount_in_words(text)
    note = ""
    if amount is None and words is not None and words in values:
        amount = words  # algarismo confirmado pelo extenso
    corroborated = bool(amount) and (
        values.count(amount or 0) >= 2 or words == amount or _sum_of_two(amount or 0, values)
    )
    if amount and words is not None and words != amount:
        note = f"valor por extenso diferente ({money(words)}); confirmar"
    return ScannedDocument(
        source,
        page,
        kind,
        amount,
        due,
        tuple(tax_ids),
        number,
        confidence,
        boleto,
        issuer,
        refs,
        corroborated,
        note,
    )


def ocr_pdf_pages(
    content: bytes, *, psm: int = 4, pages: set[int] | None = None
) -> dict[int, tuple[str, int]]:
    """Texto e confiança média (0 a 100) por página (1 em diante), por OCR local.

    `psm` é o modo de segmentação do Tesseract; `pages` limita as páginas lidas."""
    from apps.hub.reconciliation_service import (
        _tesseract_environment,
        _tesseract_executable,
        local_ocr_available,
    )

    if len(content) > MAX_SCAN_BYTES:
        raise MultisourceError("Documento escaneado: arquivo maior que 100 MiB.")
    tesseract = _tesseract_executable()
    if tesseract is None or not local_ocr_available():
        raise MultisourceError(
            "OCR local indisponível: instale o Tesseract com o idioma português (por)."
        )
    import pypdfium2  # type: ignore[import-untyped]

    try:
        document = pypdfium2.PdfDocument(content)
    except Exception as exc:  # pypdfium2 levanta PdfiumError genérico
        raise MultisourceError("Documento escaneado: PDF ilegível.") from exc
    if len(document) > MAX_PAGES:
        raise MultisourceError("Documento escaneado: PDF excede 300 páginas.")
    texts: dict[int, tuple[str, int]] = {}
    with tempfile.TemporaryDirectory(prefix="cica-multifontes-ocr-") as directory:
        for number in range(len(document)):
            if pages is not None and number + 1 not in pages:
                continue
            image = PurePath(directory, f"page-{number + 1}.png")
            document[number].render(scale=3).to_pil().convert("L").save(image)
            result = subprocess.run(  # noqa: S603 - binário local resolvido, arquivo temporário privado
                [tesseract, str(image), "stdout", "-l", "por", "--psm", str(psm), "tsv"],
                capture_output=True,
                check=False,
                text=True,
                timeout=120,
                env=_tesseract_environment(),
            )
            texts[number + 1] = _tsv_text(result.stdout) if result.returncode == 0 else ("", 0)
    document.close()
    return texts


def _tsv_text(tsv: str) -> tuple[str, int]:
    lines: dict[tuple[str, str, str], list[str]] = {}
    confidences: list[float] = []
    for row in tsv.splitlines()[1:]:
        parts = row.split("\t")
        if len(parts) != 12 or not parts[11].strip():
            continue
        lines.setdefault((parts[2], parts[3], parts[4]), []).append(parts[11])
        try:
            confidences.append(max(0.0, float(parts[10])))
        except ValueError:
            continue
    text = "\n".join(" ".join(words) for words in lines.values())
    confidence = round(sum(confidences) / len(confidences)) if confidences else 0
    return text, confidence


def read_scanned_pdf(content: bytes, *, source: str, own_tax_id: str = "") -> list[ScannedDocument]:
    """Um documento por página; boletos repetidos (via do pagador + ficha) contam uma vez."""
    documents: list[ScannedDocument] = []
    seen_barcodes: set[str] = set()
    first = ocr_pdf_pages(content)

    def read(page: int, text: str, confidence: int) -> ScannedDocument:
        return extract_document(
            text, source=source, page=page, confidence=confidence, own_tax_id=own_tax_id
        )

    parsed = {page: read(page, *first[page]) for page in sorted(first) if first[page][0].strip()}
    # Segunda passada (bloco único, psm 6) só onde o valor não foi lido: recupera colunas de
    # valores que a primeira leitura perdeu, como os campos do recibo de aluguel.
    retry = {
        page
        for page, document in parsed.items()
        if document.amount_cents is None and document.kind in ("recibo", "fatura", "boleto")
    }
    if retry:
        for page, (text, confidence) in ocr_pdf_pages(content, psm=6, pages=retry).items():
            merged = read(page, f"{first[page][0]}\n{text}", min(first[page][1], confidence))
            if merged.amount_cents is not None:
                parsed[page] = merged
    last_invoice: dict[int, int] = {}
    for page in sorted(parsed):
        document = parsed[page]
        if document.kind == "fatura" and document.amount_cents:
            # Fatura de várias páginas repete o total: conta uma vez.
            previous = last_invoice.get(document.amount_cents)
            last_invoice[document.amount_cents] = page
            if previous is not None and page - previous <= 3:
                continue
        if document.boleto:
            if document.boleto.barcode in seen_barcodes:
                continue
            seen_barcodes.add(document.boleto.barcode)
        documents.append(document)
    return documents
