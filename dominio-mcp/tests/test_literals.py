from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from dominio_mcp.literals import (
    UnsafeIdentifier,
    UnsafeLiteral,
    encode_literal,
    like_escape,
    qualified,
    quote_ident,
)


def test_plain_identifiers_are_double_quoted() -> None:
    assert quote_ident("efsaidas") == '"efsaidas"'
    assert quote_ident("EFMVSPRO_APURACAO_ESTOQUE") == '"EFMVSPRO_APURACAO_ESTOQUE"'
    assert quote_ident("nome da coluna") == '"nome da coluna"'
    assert quote_ident("município") == '"município"'


def test_qualified_name_quotes_both_parts() -> None:
    assert qualified("bethadba", "geempre") == '"bethadba"."geempre"'


@pytest.mark.parametrize(
    "name",
    [
        'a"b',
        'x"; DROP TABLE y; --',
        "a\x00b",
        "linha\nquebrada",
        "tab\there",
        "\x7f",
        "x\x85y",
        "",
        "x" * 129,
    ],
)
def test_unsafe_identifiers_are_refused(name: str) -> None:
    with pytest.raises(UnsafeIdentifier):
        quote_ident(name)


def test_error_message_never_repeats_the_identifier() -> None:
    with pytest.raises(UnsafeIdentifier) as exc:
        quote_ident('segredo"x')
    assert "segredo" not in str(exc.value)


# --- literais tipados ---------------------------------------------------------------------------


def test_typed_literals() -> None:
    assert encode_literal("int", 560) == "560"
    assert encode_literal("int", -7) == "-7"
    assert encode_literal("decimal", Decimal("1234.50")) == "1234.50"
    assert encode_literal("decimal", Decimal("1E+3")) == "1000"
    assert encode_literal("date", date(2026, 11, 21)) == "'2026-11-21'"
    assert encode_literal("timestamp", datetime(2026, 11, 21, 14, 5, 6)) == "'2026-11-21 14:05:06'"
    assert encode_literal("bool", 1) == "1"
    assert encode_literal("uuid", "12345678-1234-5678-1234-567812345678") == (
        "'12345678-1234-5678-1234-567812345678'"
    )
    assert encode_literal("text", "O'Brien") == "'O''Brien'"
    assert encode_literal("text", "Ação") == "'Ação'"


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("int", True),
        ("int", "560"),
        ("int", 2**63),
        ("int", 1.5),
        ("decimal", Decimal("NaN")),
        ("decimal", Decimal("Infinity")),
        ("decimal", "1.5"),
        ("decimal", Decimal("1" * 39)),
        ("date", datetime(2026, 1, 1)),
        ("date", "2026-01-01"),
        ("timestamp", date(2026, 1, 1)),
        ("uuid", "nao-e-uuid"),
        ("uuid", "12345678-1234-5678-1234-567812345678'; DROP"),
        ("bool", 2),
        ("bool", "1"),
        ("text", 5),
        ("text", "x" * 201),
        ("text", r"barra\invertida"),
        ("text", "nul\x00byte"),
        ("text", "quebra\nde linha"),
        ("text", "tab\taqui"),
        ("text", "del\x7f"),
        ("text", "c1\x85controle"),
        ("text", "sep" + chr(0x2028) + "linha"),
        ("coisa", 1),
    ],
)
def test_literals_that_cannot_be_written_safely_are_refused(kind: str, value: object) -> None:
    with pytest.raises(UnsafeLiteral):
        encode_literal(kind, value)


@pytest.mark.parametrize(
    "text",
    [
        "'; DROP TABLE x; --",
        "' OR '1'='1",
        "/* c */",
        "x'' y",
        "'",
        "''",
        "%_!",
        chr(0x0441) + chr(0x0430),
    ],
)
def test_adversarial_text_stays_inside_one_string_literal(text: str) -> None:
    literal = encode_literal("text", text)
    inner = literal[1:-1]
    assert literal.startswith("'") and literal.endswith("'")
    assert "'" not in inner.replace("''", "")
    assert inner.replace("''", "'") == text


@given(st.text(max_size=200))
def test_text_literal_roundtrips_or_is_refused(text: str) -> None:
    try:
        literal = encode_literal("text", text)
    except UnsafeLiteral:
        return
    inner = literal[1:-1]
    assert "'" not in inner.replace("''", "")
    assert "\\" not in inner
    assert all(ord(c) >= 0x20 and not 0x7F <= ord(c) <= 0x9F for c in inner)
    assert inner.replace("''", "'") == text


def test_like_escape_protects_wildcards_and_the_escape_char() -> None:
    assert like_escape("100%_ok!") == "100!%!_ok!!"
    assert like_escape("abc") == "abc"
