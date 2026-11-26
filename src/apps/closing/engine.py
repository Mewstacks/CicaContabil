"""Reading and anchor-based extraction for closing receipts and guides (no database).

A layout is a set of *markers* (texts that must all appear: they say which document this
is) and *fields* (an anchor text plus the value that follows it). The same two ideas
appear in invoice2data templates ("keywords" must all match; fields are read by pattern),
and the extraction rules below are the ones the HubFedrizzi closing module settled on
after real receipts: accent-blind anchors, numeric borders, ``A || B`` variants, column
headers split over lines, and the Nth/summed value of block layouts.

Nothing here touches the database or the network; ``services`` owns that.
"""

from __future__ import annotations

import io
import re
import unicodedata
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from defusedxml import ElementTree as SafeET  # type: ignore[import-untyped]

MAX_PDF_PAGES = 30
TEXT_LIMIT = 256 * 1024
#: Characters scanned after an anchor when a layout lists values in blocks.
BLOCK_WINDOW = 3000
VARIANT_SEPARATOR = "||"
MARKER = "marker"
MARKER_PREFIX = "marker_"


def is_marker(variable: str) -> bool:
    return variable == MARKER or variable.startswith(MARKER_PREFIX)


#: Kind of value each variable carries.
KIND = {
    "cnpj": "cnpj",
    "cnpj_root": "cnpj_root",
    "state_registration": "ie",
    "municipal_registration": "im",
    "competence": "competence",
    "amount": "money",
    "icms": "money",
    "ipi": "money",
    "iss": "money",
    "iss_withheld": "money",
    "number": "text",
    "legal_name": "text",
}


def kind_of(variable: str) -> str:
    return MARKER if is_marker(variable) else KIND.get(variable, "text")


@dataclass(frozen=True)
class FieldSpec:
    variable: str
    anchor: str
    occurrence: int = 0
    sum_count: int = 0
    nullified: bool = False


@dataclass(frozen=True)
class ReadResult:
    text: str
    error_code: str = ""
    message: str = ""


# --- reading the file ---------------------------------------------------------------


def _page_text(page: object, mode: str) -> str:
    try:
        if mode == "layout":
            return str(page.extract_text(extraction_mode="layout") or "")  # type: ignore[attr-defined]
        return str(page.extract_text() or "")  # type: ignore[attr-defined]
    except Exception:
        return ""


def decode_text(data: bytes) -> str:
    """UTF-8 first, then cp1252/latin-1: Brazilian fiscal exports are often not UTF-8."""
    for codec in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return data.decode(codec)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", "replace")


def read_text(data: bytes, name: str) -> ReadResult:
    """Text of one file. Layout mode keeps columns together, which the anchors rely on."""
    lowered = (name or "").lower()
    if not lowered.endswith(".pdf"):
        return ReadResult(decode_text(data)[:TEXT_LIMIT].replace("\x00", ""))
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(data), strict=False)
        pages: list[str] = []
        for page in list(reader.pages)[:MAX_PDF_PAGES]:
            text = _page_text(page, "layout")
            if not text.strip():
                # Some PDFs draw the whole page in a form XObject: layout mode returns an
                # empty page without error and the plain extractor reads it fine.
                text = _page_text(page, "plain")
            pages.append(text)
    except Exception:
        return ReadResult(
            "", "pdf_invalido", "Não foi possível abrir o PDF. Confira se o arquivo está íntegro."
        )
    text = "\n".join(pages).replace("\x00", "")[:TEXT_LIMIT]
    if not text.strip():
        return ReadResult(
            "", "pdf_sem_texto", "O PDF não tem texto selecionável (documento digitalizado)."
        )
    return ReadResult(text)


# --- anchors ------------------------------------------------------------------------

# CNPJ alfanumérico (IN RFB 2.229/2024, a partir de jul/2026): letras na raiz e na ordem; os
# dois dígitos verificadores seguem numéricos. Token só com dígitos vale como sempre valeu;
# com letras só vale se os dígitos verificadores fecham (uma palavra de mesmo formato não).
_RE_CNPJ = re.compile(
    r"(?<![A-Za-z0-9])([A-Za-z0-9]{2})\.?([A-Za-z0-9]{3})\.?([A-Za-z0-9]{3})/?"
    r"([A-Za-z0-9]{4})-?(\d{2})(?![A-Za-z0-9])"
)
_RE_CNPJ_ROOT = re.compile(r"(?<![\d./-])\d{2}\.?\d{3}\.?\d{3}(?![\d./-])")
_RE_IE = re.compile(r"\d{3}/\d{7}(?:-\d)?|\d{2}\.\d{3}\.\d{3}-\d|\d{8,13}")
_RE_IM = re.compile(r"(?<![\d])\d[\d./-]{1,20}\d(?![\d])|(?<![\d])\d{3,15}(?![\d])")
_MONTHS = {
    "janeiro": 1,
    "jan": 1,
    "fevereiro": 2,
    "fev": 2,
    "marco": 3,
    "mar": 3,
    "abril": 4,
    "abr": 4,
    "maio": 5,
    "mai": 5,
    "junho": 6,
    "jun": 6,
    "julho": 7,
    "jul": 7,
    "agosto": 8,
    "ago": 8,
    "setembro": 9,
    "set": 9,
    "outubro": 10,
    "out": 10,
    "novembro": 11,
    "nov": 11,
    "dezembro": 12,
    "dez": 12,
}
_MONTH_NAMES = "|".join(sorted((*_MONTHS, "março"), key=len, reverse=True))
_RE_COMPETENCE = re.compile(
    r"(0[1-9]|1[0-2])[/.\-]?(20\d{2})"
    r"|(20\d{2})[/.\-]?(0[1-9]|1[0-2])"
    rf"|({_MONTH_NAMES})(?:\.)?\s*(?:[/.\-]|\bde\b)\s*(20\d{{2}})",
    re.IGNORECASE,
)
# Month and year printed in separate boxes: "Competência: [Agosto] / [2026]".
_RE_COMPETENCE_SPLIT = re.compile(
    rf"\b({_MONTH_NAMES})\b[^\d]{{0,120}}?(?<![\d/.\-])(20\d{{2}})(?![\d/.\-])", re.IGNORECASE
)
_MONEY = r"\d{1,3}(?:\.\d{3})*,\d{2}|\d+\,\d{2}|\d+\.\d{2}"
_RE_MONEY = re.compile(rf"-\s*(?:{_MONEY})|\((?:{_MONEY})\)|(?:{_MONEY})")


def _nfc(text: str) -> str:
    return unicodedata.normalize("NFC", text or "")


def _strip_accents(value: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", value or "") if unicodedata.category(c) != "Mn"
    )


_ACCENTED: dict[str, str] = {}
for _accented in "áàâãäéèêëíìîïóòôõöúùûüçñ":
    _base = _strip_accents(_accented)
    if _base and _base != _accented:
        _ACCENTED[_base] = _ACCENTED.get(_base, "") + _accented


def _flexible_letter(char: str) -> str:
    """Match the letter with or without accent, keeping one character per position."""
    base = _strip_accents(char).casefold()
    variants = _ACCENTED.get(base)
    if not variants:
        return re.escape(char)
    return "[" + re.escape(base + base.upper() + variants + variants.upper()) + "]"


def _pattern(anchor: str) -> re.Pattern[str] | None:
    parts = re.split(r"\s+", _nfc(anchor).strip())
    if not parts or not parts[0]:
        return None
    body = r"\s+".join("".join(_flexible_letter(c) for c in part) for part in parts)
    # A numeric border keeps a revenue code ("1162") from matching inside "116201".
    prefix = r"(?<!\d)" if parts[0][0].isdigit() else ""
    suffix = r"(?!\d)" if parts[-1][-1].isdigit() else ""
    return re.compile(f"{prefix}{body}{suffix}", re.IGNORECASE)


def _find(text: str, anchor: str) -> re.Match[str] | None:
    pattern = _pattern(anchor)
    return pattern.search(_nfc(text)) if pattern else None


def variants(marker: str) -> list[str]:
    return [p.strip() for p in (marker or "").split(VARIANT_SEPARATOR) if p.strip()]


def marker_hit(text: str, marker: str) -> str | None:
    """The first variant of ``marker`` present in the text, or None."""
    for variant in variants(marker):
        if _find(text, variant):
            return variant
    return None


def winners(text: str, candidates: Mapping[object, Sequence[str]]) -> list[object]:
    """Layouts whose markers ALL appear, those tied for the most specific.

    Specificity is (number of markers, characters actually matched): a short exclusive code
    plus the header beats a long generic header alone. More than one winner is ambiguous;
    the caller sends the document to review instead of guessing.
    """
    if not (text or "").strip():
        return []
    matched: list[tuple[tuple[int, int], object]] = []
    for key, markers in candidates.items():
        unique = [m for m in dict.fromkeys(markers) if m and m.strip()]
        if not unique:
            continue
        hits = [marker_hit(text, marker) for marker in unique]
        if all(hits):
            matched.append(((len(unique), sum(len(h or "") for h in hits)), key))
    if not matched:
        return []
    top = max(score for score, _ in matched)
    return [key for score, key in matched if score == top]


# --- values -------------------------------------------------------------------------


def _normalize_money(raw: str) -> str:
    s = raw.strip()
    negative = s.startswith("-") or (s.startswith("(") and s.endswith(")"))
    s = s.strip("()").lstrip("-").strip()
    pos = max(s.rfind(","), s.rfind("."))
    if pos == -1:
        return f"-{s}" if negative else s
    whole = re.sub(r"[.,]", "", s[:pos])
    return f"{'-' if negative else ''}{whole}.{s[pos + 1 :]}"


def parse_money(raw: str) -> Decimal | None:
    try:
        return Decimal(_normalize_money(raw)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        return None


def _competences(chunk: str) -> list[tuple[int, int, int]]:
    found: list[tuple[int, int, int]] = []
    covered: list[tuple[int, int]] = []
    for m in _RE_COMPETENCE.finditer(chunk):
        if m.group(1):
            year, month = int(m.group(2)), int(m.group(1))
        elif m.group(3):
            year, month = int(m.group(3)), int(m.group(4))
        else:
            year = int(m.group(6))
            month = _MONTHS.get(_strip_accents(m.group(5)).casefold(), 0)
        if year and month:
            found.append((m.start(), year, month))
            covered.append((m.start(), m.end()))
    for m in _RE_COMPETENCE_SPLIT.finditer(chunk):
        if any(start <= m.start() < end for start, end in covered):
            continue
        month = _MONTHS.get(_strip_accents(m.group(1)).casefold(), 0)
        if month:
            found.append((m.start(), int(m.group(2)), month))
    found.sort(key=lambda item: item[0])
    return found


def _window(text: str, anchor: str) -> str:
    text = _nfc(text)
    hit = _find(text, anchor)
    return text[hit.end() : hit.end() + BLOCK_WINDOW] if hit else ""


def _after_anchor(text: str, anchor: str) -> str:
    """The cell right after (or below) the anchor, where the value lives."""
    text = _nfc(text)
    hit = _find(text, anchor)
    if not hit:
        return ""
    line_start = text.rfind("\n", 0, hit.start()) + 1
    column = hit.start() - line_start
    rest = text[hit.end() :]
    # An anchor typed as a prefix of the label ("apura") leaves the word's tail behind.
    if anchor and anchor.strip()[-1:].isalpha():
        tail = re.match(r"[^\W\d_]+", rest)
        if tail:
            rest = rest[tail.end() :]
    line = rest.split("\n", 1)[0]
    if "<" in line:  # one-line XML: stop at the closing tag
        if anchor.strip().endswith(">"):
            return line[: line.index("<")].strip()
        if line.startswith(">"):
            return line[1 : line.index("<")].strip()
    if line.strip():
        return re.split(r"\s{2,}", line.strip(), maxsplit=1)[0].strip()
    for following in rest.splitlines()[1:4]:
        if not following.strip():
            continue
        cell = following[column:] if len(following) > column else following
        return re.split(r"\s{2,}", cell.lstrip(), maxsplit=1)[0].strip()
    return rest[:120].strip()


_CELL = re.compile(r"\S(?:.*?\S)?(?=\s{2,}|$)")


def _column_of_label(text: str, anchor: str) -> str:
    """Rebuild a table header split over lines and return the values under that column."""
    target = re.sub(r"\s+", " ", _strip_accents(anchor)).strip().casefold()
    lines = _nfc(text).splitlines()
    for i, line in enumerate(lines):
        cells = list(_CELL.finditer(line))
        if len(cells) < 2:
            continue
        for j, cell in enumerate(cells):
            parts = [cell.group()]
            start = _strip_accents(parts[0]).strip().casefold()
            if not start or start == target or not target.startswith(start + " "):
                continue
            centers = [(c.start() + c.end()) / 2 for c in cells]
            center = centers[j]
            left = (centers[j - 1] + center) / 2 if j else 0
            right = (center + centers[j + 1]) / 2 if j + 1 < len(cells) else len(line) + 10
            for k in range(i + 1, min(i + 5, len(lines))):
                if not lines[k].strip():
                    break
                pieces = [
                    c.group()
                    for c in _CELL.finditer(lines[k])
                    if left <= (c.start() + c.end()) / 2 < right
                ]
                if len(pieces) != 1:
                    break
                parts += pieces
                label = _strip_accents(" ".join(parts)).casefold()
                if label == target:
                    values: list[str] = []
                    for below in lines[k + 1 : k + 7]:
                        if not below.strip():
                            continue
                        values += [
                            c.group()
                            for c in _CELL.finditer(below)
                            if left <= (c.start() + c.end()) / 2 < right
                        ]
                        if values:
                            break
                    return "\n".join(values)
                if not target.startswith(label + " "):
                    break
    return ""


def _nth(pattern: re.Pattern[str], chunk: str, n: int) -> str:
    found = pattern.findall(chunk)
    return found[n - 1] if 1 <= n <= len(found) else ""


def xml_taxpayer_root(text: str) -> str:
    """Taxpayer id from an eSocial/REINF closing event, never the service provider's.

    The receipts of S-1299 and R-9011/R-9015 carry the taxpayer as the 8-digit root in
    ``ideEmpregador``/``ideContri``; the only full CNPJ in them is a third party's.
    """
    if "<" not in text or not any(
        marker in text for marker in ("evtFechaEvPer", "evtTotalContrib", "evtRetCons")
    ):
        return ""
    try:
        root = SafeET.fromstring(text)
    except Exception:
        return ""
    events = {"evtFechaEvPer", "evtTotalContrib", "evtRetCons"}
    ids = {"ideEmpregador", "ideContri"}
    for event in root.iter():
        if event.tag.rsplit("}", 1)[-1] not in events:
            continue
        for ident in event:
            if ident.tag.rsplit("}", 1)[-1] not in ids:
                continue
            values = {i.tag.rsplit("}", 1)[-1]: (i.text or "").strip() for i in ident}
            number = values.get("nrInsc", "")
            if values.get("tpInsc") == "1" and re.fullmatch(r"(?:\d{8}|\d{14})", number):
                return number
    return ""


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _cnpjs(chunk: str) -> list[str]:
    """CNPJs written in ``chunk`` (compact, uppercase), in order of appearance."""
    from django.core.exceptions import ValidationError

    from apps.common.cnpj import normalize_cnpj

    found: list[str] = []
    for m in _RE_CNPJ.finditer(chunk or ""):
        token = "".join(m.groups()).upper()
        if token.isdigit():
            found.append(token)
            continue
        try:
            found.append(normalize_cnpj(token))
        except ValidationError:
            continue
    return found


def extract(text: str, spec: FieldSpec) -> object | None:
    """Value of one field: str digits, (year, month), Decimal, text, or None if unread."""
    if spec.nullified:
        return None
    kind = kind_of(spec.variable)
    if kind == MARKER:
        return marker_hit(text, spec.anchor)
    n = spec.occurrence or 0
    cell = _after_anchor(text, spec.anchor)
    column = ""
    if kind in {"money", "competence"}:
        column = _column_of_label(text, spec.anchor)
        if column:
            cell = column
    if kind == "cnpj":
        structured = xml_taxpayer_root(text)
        if structured:
            return structured
        if n >= 1:
            ordered = _cnpjs(_window(text, spec.anchor))
            return ordered[n - 1] if n <= len(ordered) else None
        in_cell = _cnpjs(cell)
        if in_cell:
            return in_cell[0]
        root = _RE_CNPJ_ROOT.match(cell.strip())
        return _digits(root.group(0)) if root else None
    if kind == "cnpj_root":
        structured = xml_taxpayer_root(text)
        if len(structured) == 8:
            return structured
        if n >= 1:
            return _digits(_nth(_RE_CNPJ_ROOT, _window(text, spec.anchor), n)) or None
        m = _RE_CNPJ_ROOT.search(cell)
        return _digits(m.group(0)) if m else None
    if kind == "ie":
        if n >= 1:
            found = _nth(_RE_IE, _window(text, spec.anchor), n)
        else:
            m = _RE_IE.search(cell)
            found = m.group(0) if m else ""
        digits = _digits(found)
        return digits if 6 <= len(digits) <= 14 else None
    if kind == "im":
        pool = _RE_IM.findall(_window(text, spec.anchor) if n >= 1 else cell)
        valid = [v for v in pool if 3 <= len(_digits(v)) <= 15]
        pick = valid[n - 1] if n >= 1 and n <= len(valid) else (valid[0] if n < 1 and valid else "")
        return _digits(pick) or None
    if kind == "competence":
        if column:
            found = _competences(column)
            idx = max(n, 1) - 1
        elif n >= 1:
            found = _competences(_window(text, spec.anchor))
            idx = n - 1
        else:
            found = _competences(cell)
            idx = 0
        return (found[idx][1], found[idx][2]) if idx < len(found) else None
    if kind == "money":
        pool = _RE_MONEY.findall(
            column or (_window(text, spec.anchor) if (n >= 1 or spec.sum_count >= 2) else cell)
        )
        if spec.sum_count >= 2:
            parts = [parse_money(v) for v in pool[: spec.sum_count]]
            valid = [p for p in parts if p is not None]
            return sum(valid, Decimal("0.00")) if len(valid) == spec.sum_count else None
        idx = max(n, 1) - 1
        if column or n >= 1:
            return parse_money(pool[idx]) if idx < len(pool) else None
        m = _RE_MONEY.search(cell)
        return parse_money(m.group(0)) if m else None
    return (cell[:255] or None) if cell else None
