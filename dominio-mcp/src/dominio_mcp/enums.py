"""Legendas de coluna lidas do comentario do proprio banco (T2.2).

Muitos comentarios do Dominio trazem a legenda do codigo: `(1 - CNPJ/2 - CPF)`, `A - Ativa / I -
Inativa`, `1=Normal, 2=Zerada`, `14-19=Honorarios`, `(S/N)`. Esta leitura e **do comentario**, que
pode estar errado (ex.: `situacao_*`): a confianca nunca passa de "media" e a legenda confirmada
vem do overlay. Sem rotulo, nao ha legenda: nada e inventado. Um unico par nunca e legenda.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

MAX_ENTRIES = 40
MAX_LABEL = 40
_CODE = r"(\d{1,3}|[A-Za-z])"
_PREFIX = r"(?:^|[\s(/,;:])"
_LABEL = r"([^\W_][^/;,()=]*?)"
_END = r"(?=\s*(?:[/;,]|\)|$))"
_DASH = re.compile(_PREFIX + _CODE + r"\s*-\s*" + _LABEL + _END)
_EQUAL = re.compile(_PREFIX + _CODE + r"\s*=\s*" + _LABEL + _END)
_RANGE = re.compile(_PREFIX + r"(\d{1,3})\s*-\s*(\d{1,3})\s*=\s*" + _LABEL + _END)
_SN = re.compile(r"\(\s*S\s*/\s*N\s*\)", re.IGNORECASE)


@dataclass(frozen=True, slots=True)
class LegendEntry:
    code: str
    label: str
    upper: str | None = None


@dataclass(frozen=True, slots=True)
class Legend:
    entries: tuple[LegendEntry, ...]
    confidence: str
    style: str

    def render(self) -> str:
        parts = []
        for e in self.entries:
            code = e.code if e.upper is None else f"{e.code}-{e.upper}"
            parts.append(f"{code}={e.label}")
        return "; ".join(parts)


def _label(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().rstrip(".").strip()[:MAX_LABEL]


def _dedupe(entries: list[LegendEntry]) -> tuple[LegendEntry, ...]:
    seen: set[tuple[str, str | None]] = set()
    out: list[LegendEntry] = []
    for e in entries:
        key = (e.code, e.upper)
        if key in seen or not e.label:
            continue
        seen.add(key)
        out.append(e)
    return tuple(out[:MAX_ENTRIES])


def parse_legend(comment: str | None) -> Legend | None:
    if not comment or not comment.strip():
        return None
    text = comment.strip()

    ranges = [LegendEntry(m[1], _label(m[3]), m[2]) for m in _RANGE.finditer(text)]
    equals = [LegendEntry(m[1], _label(m[2])) for m in _EQUAL.finditer(text)]
    combined = _dedupe(ranges + equals)
    if len(combined) >= 2:
        return Legend(combined, "media", "faixa" if ranges else "igual")

    dashes = _dedupe([LegendEntry(m[1], _label(m[2])) for m in _DASH.finditer(text)])
    if len(dashes) >= 2:
        return Legend(dashes, "media", "traco")

    if _SN.search(text):
        return Legend((LegendEntry("S", "Sim"), LegendEntry("N", "Nao")), "baixa", "sn")
    return None


_UNUSED = re.compile(
    r"nao (?:e )?(?:mais )?(?:utilizad|usad)|campo nao utiliz|obsolet|desuso|nao ser[a]? mais"
    r"|descontinu|deprecated"
)


def is_unused(comment: str | None) -> bool:
    """O comentario diz que o campo ou a tabela nao e mais usado (54 colunas, 5 tabelas medidas)."""
    if not comment:
        return False
    decomposed = unicodedata.normalize("NFD", comment.lower())
    folded = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return _UNUSED.search(folded) is not None
