"""Shared fixed-query snapshot contract. No dynamic SQL or inferred source semantics."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from apps.hub.dominio_journal_normalization import (
    FIELDS,
    JournalNormalizationError,
    JournalScope,
    NormalizedJournalCandidate,
    normalize_native_journal_snapshot,
)

VERSION = "dominio-ledger-snapshot-v1"
MAX_BYTES = 2_000_000
ROOT = Path(__file__).resolve().parents[3] / "contracts" / "ledger"
SCOPE_FIELDS = frozenset(
    {
        "company_code",
        "chart_company_code",
        "branch_code",
        "bank_account_code",
        "absent_account_code",
        "bank_inflow_side",
        "period_start",
        "period_end_exclusive",
        "expected_source_rows",
        "expected_lots",
        "expected_bank_effects",
    }
)


def contract_hash() -> str:
    manifest = (ROOT / "manifest.json").read_bytes()
    parsed = json.loads(manifest)
    if parsed["version"] != VERSION or set(parsed["queries"]) != {"lots", "accounts", "records"}:
        raise ValueError("ledger_contract_invalid")
    for name, query in parsed["queries"].items():
        if query["file"] != f"{name}.sql":
            raise ValueError("ledger_contract_invalid")
        content = (ROOT / query["file"]).read_bytes()
        if hashlib.sha256(content).hexdigest() != query["sha256"]:
            raise ValueError("ledger_contract_invalid")
    return hashlib.sha256(manifest).hexdigest()


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def pilot_scope() -> dict[str, Any]:
    return {
        "company_code": 212,
        "chart_company_code": 212,
        "branch_code": 212,
        "bank_account_code": 8,
        "absent_account_code": 0,
        "bank_inflow_side": "debit",
        "period_start": "2026-09-01",
        "period_end_exclusive": "2026-10-01",
        "expected_source_rows": 177,
        "expected_lots": 163,
        "expected_bank_effects": 163,
    }


def validate_scope(scope: Any) -> dict[str, Any]:
    """Validate an explicit mapping, never discover or authorize it by inference."""
    if not isinstance(scope, dict) or set(scope) != SCOPE_FIELDS:
        raise ValueError("ledger_scope_invalid")
    for field in ("company_code", "chart_company_code", "branch_code", "bank_account_code"):
        if type(scope[field]) is not int or not 1 <= scope[field] <= 2147483647:
            raise ValueError("ledger_scope_invalid")
    if type(scope["absent_account_code"]) is not int or scope["absent_account_code"] != 0:
        raise ValueError("ledger_scope_invalid")
    if not isinstance(scope["bank_inflow_side"], str) or scope["bank_inflow_side"] not in {
        "debit",
        "credit",
    }:
        raise ValueError("ledger_scope_invalid")
    try:
        start, end = (
            date.fromisoformat(scope[k]) for k in ("period_start", "period_end_exclusive")
        )
        if (
            start.isoformat() != scope["period_start"]
            or end.isoformat() != scope["period_end_exclusive"]
            or start < date(2026, 9, 1)
            or not 1 <= (end - start).days <= 31
            or start.day != 1
            or end.day != 1
        ):
            raise ValueError
    except (ValueError, TypeError):
        raise ValueError("ledger_scope_invalid") from None
    for field in ("expected_source_rows", "expected_lots", "expected_bank_effects"):
        if type(scope[field]) is not int or not 0 <= scope[field] <= 50_000:
            raise ValueError("ledger_scope_invalid")
    if not (
        scope["expected_lots"] <= scope["expected_source_rows"]
        and scope["expected_bank_effects"] == scope["expected_lots"]
        and (scope["expected_source_rows"] == 0) == (scope["expected_lots"] == 0)
    ):
        raise ValueError("ledger_scope_invalid")
    return dict(scope)


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("ledger_duplicate_json_key")
        result[key] = value
    return result


def strict_json(content: bytes) -> dict[str, Any]:
    if not 1 <= len(content) <= MAX_BYTES:
        raise ValueError("ledger_snapshot_size")
    try:
        result = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_object,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (UnicodeError, ValueError, RecursionError):
        raise ValueError("ledger_snapshot_json") from None
    if not isinstance(result, dict):
        raise ValueError("ledger_snapshot_json")
    return result


def validate_snapshot(content: bytes, scope: dict[str, Any]) -> dict[str, Any]:
    scope = validate_scope(scope)
    data = strict_json(content)
    if set(data) != {"version", "scope_revision", "lots", "records", "accounts"}:
        raise ValueError("ledger_snapshot_fields")
    if data["version"] != VERSION or data["scope_revision"] != canonical_hash(scope):
        raise ValueError("ledger_snapshot_scope")
    for key, count in (
        ("records", scope["expected_source_rows"]),
        ("lots", scope["expected_lots"]),
    ):
        if not isinstance(data[key], list) or len(data[key]) != count:
            raise ValueError("ledger_snapshot_coverage")
    if not isinstance(data["accounts"], list) or not 0 <= len(data["accounts"]) <= 5000:
        raise ValueError("ledger_catalogue_coverage")
    codes = set()
    for account in data["accounts"]:
        if not isinstance(account, dict) or set(account) != {
            "company_code",
            "account_code",
            "name_raw",
            "classification_raw",
            "type_raw",
            "status_raw",
            "inactive_date_raw",
        }:
            raise ValueError("ledger_catalogue_fields")
        if (
            type(account["company_code"]) is not int
            or account["company_code"] != scope["chart_company_code"]
        ):
            raise ValueError("ledger_catalogue_scope")
        code = account["account_code"]
        if type(code) is not int or not 1 <= code <= 2147483647 or code in codes:
            # Code zero must actually be absent, rather than silently discarded.
            raise ValueError("ledger_catalogue_code")
        codes.add(code)
        for field, limit in (
            ("name_raw", 150),
            ("classification_raw", 20),
            ("type_raw", 1),
            ("status_raw", 1),
        ):
            value = account[field]
            if value is not None and (not isinstance(value, str) or len(value) > limit):
                raise ValueError("ledger_catalogue_text")
        inactive = account["inactive_date_raw"]
        if inactive is not None and (
            not isinstance(inactive, str) or date.fromisoformat(inactive).isoformat() != inactive
        ):
            raise ValueError("ledger_catalogue_date")
    lot_codes = set()
    for lot in data["lots"]:
        if not isinstance(lot, dict) or set(lot) != {"lot_code", "row_count", "type_raw"}:
            raise ValueError("ledger_lot_fields")
        if (
            type(lot["lot_code"]) is not int
            or not 0 <= lot["lot_code"] <= 2147483647
            or lot["lot_code"] in lot_codes
            or type(lot["row_count"]) is not int
            or not 1 <= lot["row_count"] <= scope["expected_source_rows"]
            or not isinstance(lot["type_raw"], str)
            or len(lot["type_raw"]) != 1
        ):
            raise ValueError("ledger_lot_coverage")
        lot_codes.add(lot["lot_code"])
    # Check privacy/shape before storage. Accounting consistency is checked afterward,
    # so an in-scope but unbalanced source can be reviewed without another ERP read.
    seen = set()
    for row in data["records"]:
        if not isinstance(row, dict) or set(row) != FIELDS | {"history_code_raw"}:
            raise ValueError("ledger_record_fields")
        for field in (
            "company_code",
            "chart_company_code",
            "branch_code",
            "lot_code",
            "row_code",
            "debit_account_code",
            "credit_account_code",
        ):
            if type(row[field]) is not int or not 0 <= row[field] <= 2147483647:
                raise ValueError("ledger_record_code")
        if (
            row["company_code"] != scope["company_code"]
            or row["chart_company_code"] != scope["chart_company_code"]
            or row["branch_code"] != scope["branch_code"]
            or row["row_code"] in seen
        ):
            raise ValueError("ledger_record_scope")
        seen.add(row["row_code"])
        if (
            not isinstance(row["occurred_on"], str)
            or not scope["period_start"] <= row["occurred_on"] < scope["period_end_exclusive"]
            or date.fromisoformat(row["occurred_on"]).isoformat() != row["occurred_on"]
        ):
            raise ValueError("ledger_record_date")
        for field in ("document", "history_code_raw"):
            if row[field] is not None and (
                type(row[field]) is not int or not 0 <= row[field] <= 2147483647
            ):
                raise ValueError("ledger_record_code")
        if row["history"] is not None and (
            not isinstance(row["history"], str) or len(row["history"]) > 1000
        ):
            raise ValueError("ledger_record_text")
        if not isinstance(row["amount"], str) or not re.fullmatch(
            r"[0-9]{1,12}(?:\.[0-9]{1,2})?", row["amount"]
        ):
            raise ValueError("ledger_record_amount")
    if sum(lot["row_count"] for lot in data["lots"]) != len(data["records"]):
        raise ValueError("ledger_lot_coverage")
    referenced = {
        r[f"{side}_account_code"] for r in data["records"] for side in ("debit", "credit")
    } - {scope["absent_account_code"]}
    if codes != referenced:
        raise ValueError("ledger_catalogue_extraneous")
    return data


def normalize_snapshot(data: dict[str, Any], scope: dict[str, Any]) -> NormalizedJournalCandidate:
    scope = validate_scope(scope)
    if (
        scope["expected_source_rows"] == 0
        and not data["records"]
        and not data["lots"]
        and not data["accounts"]
    ):
        return NormalizedJournalCandidate(parties=(), source_rows=0, journals=0, bank_effects=0)
    try:
        return normalize_native_journal_snapshot(
            data["records"],
            JournalScope(
                company_code=scope["company_code"],
                chart_company_code=scope["chart_company_code"],
                bank_account_code=scope["bank_account_code"],
                branch_codes=frozenset({scope["branch_code"]}),
                account_codes=frozenset(a["account_code"] for a in data["accounts"]),
                absent_account_code=scope["absent_account_code"],
                bank_inflow_side=scope["bank_inflow_side"],
                period_start=date.fromisoformat(scope["period_start"]),
                period_end_exclusive=date.fromisoformat(scope["period_end_exclusive"]),
                expected_lot_rows=tuple(
                    (lot["lot_code"], lot["row_count"]) for lot in data["lots"]
                ),
                expected_bank_effects=scope["expected_bank_effects"],
            ),
        )
    except (JournalNormalizationError, KeyError, TypeError, ValueError):
        raise ValueError("ledger_normalization_review") from None
