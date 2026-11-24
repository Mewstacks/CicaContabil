from __future__ import annotations

import json
import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal

import pytest

from dominio_mcp.values import date_is_plausible, normalize_row, normalize_value


def test_none_and_plain_types_pass_through() -> None:
    assert normalize_value(None) is None
    assert normalize_value(True) is True
    assert normalize_value(False) is False
    assert normalize_value(7) == 7
    assert normalize_value(1.5) == 1.5


def test_bool_is_not_turned_into_int() -> None:
    assert normalize_value(True) is True
    assert type(normalize_value(True)) is bool


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_non_finite_float_becomes_none(bad: float) -> None:
    assert normalize_value(bad) is None


def test_huge_int_becomes_text_to_avoid_precision_loss() -> None:
    assert normalize_value(2**53) == 2**53
    assert normalize_value(2**53 + 1) == str(2**53 + 1)


def test_small_decimal_becomes_json_number() -> None:
    assert normalize_value(Decimal("1234.56")) == 1234.56
    assert normalize_value(Decimal("0.00")) == 0.0
    assert normalize_value(Decimal("-10")) == -10.0
    assert type(normalize_value(Decimal("1234"))) is int
    assert type(normalize_value(Decimal("12.50"))) is float
    assert normalize_value(Decimal("1E+3")) == 1000


def test_decimal_with_more_than_15_digits_stays_exact_as_text() -> None:
    value = Decimal("12345678901234567.89")
    assert normalize_value(value) == "12345678901234567.89"


@pytest.mark.parametrize("bad", [Decimal("NaN"), Decimal("Infinity"), Decimal("-Infinity")])
def test_non_finite_decimal_becomes_none(bad: Decimal) -> None:
    assert normalize_value(bad) is None


def test_char_padding_is_trimmed_but_leading_space_stays() -> None:
    assert normalize_value("ABC   ") == "ABC"
    assert normalize_value("  AB  ") == "  AB"
    assert normalize_value("   ") == ""
    assert normalize_value("linha\n\n") == "linha"


def test_control_characters_are_removed_but_tab_and_newline_stay() -> None:
    assert normalize_value("a\x00b\x07c") == "abc"
    assert normalize_value("a\tb\nc") == "a\tb\nc"
    assert normalize_value("x\x85y") == "xy"


def test_accents_are_preserved_by_code_point() -> None:
    value = normalize_value("inscrição  ")
    assert isinstance(value, str)
    assert [ord(c) for c in value[-3:-1]] == [0x00E7, 0x00E3]


def test_bytes_never_leave_as_content() -> None:
    for blob in (b"segredo-123", bytearray(b"segredo-123"), memoryview(b"segredo-123")):
        out = normalize_value(blob)
        assert out == "<binario 11 bytes>"
        assert "segredo" not in str(out)


def test_dates_and_datetimes_are_iso() -> None:
    assert normalize_value(date(2026, 11, 21)) == "2026-11-21"
    assert normalize_value(datetime(2026, 11, 21, 14, 0, 0)) == "2026-11-21 14:00:00"
    assert normalize_value(datetime(2026, 11, 21, 14, 0, 0, 123000)) == "2026-11-21 14:00:00.123"
    assert normalize_value(time(8, 30)) == "08:30:00"
    assert normalize_value(datetime(2026, 1, 1, tzinfo=UTC)) == "2026-01-01 00:00:00+00:00"


def test_garbage_dates_are_emitted_but_flagged_by_plausibility() -> None:
    assert normalize_value(date(1979, 1, 1)) == "1979-01-01"
    assert normalize_value(date(8320, 1, 1)) == "8320-01-01"
    assert not date_is_plausible(date(1979, 12, 31))
    assert not date_is_plausible(datetime(8320, 1, 1))
    assert date_is_plausible(date(1980, 1, 1))
    assert date_is_plausible(date(2100, 12, 31))
    assert not date_is_plausible(date(2101, 1, 1))
    assert date_is_plausible("texto")
    assert date_is_plausible(None)


def test_uuid_timedelta_and_unknown_objects_become_short_text() -> None:
    u = uuid.UUID("12345678-1234-5678-1234-567812345678")
    assert normalize_value(u) == "12345678-1234-5678-1234-567812345678"
    assert normalize_value(timedelta(seconds=90)) == "0:01:30"

    class Weird:
        def __str__(self) -> str:
            return "x" * 500

    out = normalize_value(Weird())
    assert isinstance(out, str)
    assert len(out) <= 200

    class Broken:
        def __str__(self) -> str:
            raise RuntimeError("nao imprime")

    assert normalize_value(Broken()) == "<ilegivel>"


def test_normalize_row_is_json_serializable() -> None:
    row = (Decimal("10.50"), "Empresa   ", date(2026, 1, 31), None, b"\x00\x01", 3)
    out = normalize_row(row)
    assert out == [10.5, "Empresa", "2026-01-31", None, "<binario 2 bytes>", 3]
    json.dumps(out)
