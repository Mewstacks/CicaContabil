"""Read-only discovery row validation for the release 100 contingency.

Exact source primitives retained from D-373; no importer or confirmation service.
"""
from __future__ import annotations

import hashlib
from typing import Any

from apps.hub import account_source_contract as details

Invalid = details.Invalid
require = details.require
integer = details.integer
keys = details.keys

def text(value: Any, length: int, nullable: bool = False) -> None:
    """Preserve well-formed source Unicode, including controls; count UTF-16 units."""
    if nullable and value is None:
        return
    require(type(value) is str, "TEXT_TYPE")
    try:
        encoded = value.encode("utf-16-le", errors="strict")
    except UnicodeError:
        raise Invalid("INVALID_SURROGATE") from None
    require(len(encoded) // 2 <= length, "TEXT_LENGTH")

def digest(value: Any) -> str:
    return hashlib.sha256(details.canonical(value).encode()).hexdigest()

CHART_FIELDS = {
    "chart_company_code",
    "account_code",
    "account_name_raw",
    "classification_raw",
    "account_type_raw",
    "account_status_raw",
    "inactive_on_raw",
}

def validate_chart_row(row: Any, *, template: bool = False) -> None:
    keys(row, CHART_FIELDS | ({"plan_id_raw"} if template else set()))
    integer(row["chart_company_code"], positive=True)
    integer(row["account_code"], positive=True)
    if template:
        integer(row["plan_id_raw"])
    for field, length in (
        ("account_name_raw", 60 if template else 150),
        ("classification_raw", 20),
        ("account_type_raw", 1),
        ("account_status_raw", 1),
    ):
        text(row[field], length)
    details.day(row["inactive_on_raw"])
