"""O zip sintético não pode depender da hora: o hash das entradas decide o reaproveitamento."""

from __future__ import annotations

import time
from unittest.mock import patch

from apps.crosscheck.synthetic import build_zip


def test_build_zip_is_byte_identical_across_seconds() -> None:
    files = {"nota-1.xml": b"<a/>", "nota-2.xml": b"<b/>"}
    with patch.object(time, "time", return_value=1_700_000_000.0):
        first = build_zip(files)
    with patch.object(time, "time", return_value=1_700_000_007.0):
        second = build_zip(files)
    assert first == second
