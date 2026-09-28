"""Normalisation that must agree, character for character, with the Domínio SQL.

The `billing_services` query matches a honorários client to a company file first
by document and, failing that, by accent-stripped uppercase razão social. Both
sides of that comparison are built by a chain of `REPLACE(...)` calls inside SQL
Anywhere. Whatever the cloud computes here has to produce the same key, because
the blind index built from it is what lets us reproduce and audit the match
without keeping the plaintext searchable.

`unicodedata.normalize("NFKD")` is deliberately NOT used: it decomposes far more
than the 23 characters the SQL knows about (Ñ, Å, Ø, ligatures, Greek…), so a
razão social containing any of them would hash differently on the two sides and
the match would silently disappear.
"""

from __future__ import annotations

# The exact table from the SQL, in the same order. Reproduced literally so a
# diff against the query is a visual check rather than an act of faith.
_ACCENT_TABLE = {
    "Á": "A",
    "À": "A",
    "Â": "A",
    "Ã": "A",
    "Ä": "A",
    "É": "E",
    "È": "E",
    "Ê": "E",
    "Ë": "E",
    "Í": "I",
    "Ì": "I",
    "Î": "I",
    "Ï": "I",
    "Ó": "O",
    "Ò": "O",
    "Ô": "O",
    "Õ": "O",
    "Ö": "O",
    "Ú": "U",
    "Ù": "U",
    "Û": "U",
    "Ü": "U",
    "Ç": "C",
}

_ACCENT_TRANSLATION = str.maketrans(_ACCENT_TABLE)

# `REPLACE(TRIM(x), '.', '')` and friends, in the order the SQL applies them.
_DOCUMENT_STRIPPED = (".", "/", "-", " ")


def only_digits(value: str | None) -> str:
    """Reduce a CPF/CNPJ to the form the SQL compares.

    The SQL strips exactly `.`, `/`, `-` and spaces after TRIM. Anything else it
    would have left in place, so this keeps every other character rather than
    filtering to `str.isdigit()` — a document with a stray letter must produce
    the same (non-matching) key on both sides, not a silently different one.
    """

    if not value:
        return ""
    result = value.strip()
    for char in _DOCUMENT_STRIPPED:
        result = result.replace(char, "")
    return result


def strip_accents_upper(value: str | None) -> str:
    """Uppercase and fold the 23 accented characters the SQL folds. Nothing more."""

    if not value:
        return ""
    return value.strip().upper().translate(_ACCENT_TRANSLATION)


def document_kind(digits: str) -> str:
    """Classify a stripped document. Empty when it is neither shape."""

    if len(digits) == 14 and digits.isdigit():
        return "cnpj"
    if len(digits) == 11 and digits.isdigit():
        return "cpf"
    return ""


def cnpj_raiz(digits: str) -> str:
    """Os 8 primeiros dígitos, que toda unidade do mesmo grupo compartilha.

    Vazio quando não é CNPJ. Diferente das demais funções deste módulo, esta não
    espelha nada do SQL do Domínio: ela alimenta agrupamento interno, não
    correspondência com o ERP, então pode filtrar por dígito sem quebrar a
    paridade que o resto do arquivo precisa manter.
    """

    return digits[:8] if document_kind(digits) == "cnpj" else ""


def cnpj_ordem(digits: str) -> str:
    """Do 9º ao 12º dígito: `0001` na matriz, outro número em cada filial."""

    return digits[8:12] if document_kind(digits) == "cnpj" else ""
