"""Raw fiscal evidence for review; no principal, cash, balance or reversal inference."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import date
from pathlib import Path
from typing import Any
from uuid import UUID

from apps.intelligence.native_ledger_contract import canonical_hash as canonical_hash

ROOT = Path(__file__).resolve().parents[3] / "contracts" / "titles"
VERSION = "dominio-title-snapshot-v1"
MAX_BYTES = 4_000_000
MAX_ROWS = 50_000
FAMILIES = ("entradas", "saidas", "servicos")
COUNT_FIELDS = {"due_installments", "payments", "accounting_links"}
COVERAGE = {
    "installments": "due_in_period_or_paid_in_period",
    "payments": "posted_in_period",
    "settlements_complete": False,
    "bank_linkage": "unproven",
    "normalization": "none",
}


def manifest() -> dict[str, Any]:
    value: dict[str, Any] = json.loads((ROOT / "manifest.json").read_bytes())
    if value["version"] != VERSION or value["maximum_bytes"] != MAX_BYTES:
        raise ValueError("title_contract_invalid")
    expected = {
        f"{family}_{kind}"
        for family in FAMILIES
        for kind in ("control", "installments", "payments", "accounting_links")
    }
    if set(value["queries"]) != expected or value["coverage"] != COVERAGE:
        raise ValueError("title_contract_invalid")
    for name, spec in value["queries"].items():
        content = (ROOT / f"{name}.sql").read_bytes()
        if (
            spec["file"] != f"{name}.sql"
            or hashlib.sha256(content).hexdigest() != spec["sha256"]
            or content.count(b"?") != len(spec["parameters"])
            or b";" in content
        ):
            raise ValueError("title_contract_invalid")
    return value


def contract_hash() -> str:
    manifest()
    return hashlib.sha256((ROOT / "manifest.json").read_bytes()).hexdigest()


def validate_scope(value: Any) -> dict[str, Any]:
    fields = {
        "capture_id",
        "company_code",
        "comparison_bank_account_code",
        "period_start",
        "period_end_exclusive",
        "expected_counts",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("title_scope_invalid")
    fixed = {
        "company_code": 212,
        "comparison_bank_account_code": 8,
        "period_start": "2026-09-01",
        "period_end_exclusive": "2026-10-01",
    }
    if any(type(value[k]) is not type(v) or value[k] != v for k, v in fixed.items()):
        raise ValueError("title_scope_invalid")
    try:
        if (
            not isinstance(value["capture_id"], str)
            or str(UUID(value["capture_id"])) != value["capture_id"]
        ):
            raise ValueError
    except (ValueError, AttributeError, TypeError):
        raise ValueError("title_scope_invalid") from None
    counts = value["expected_counts"]
    if not isinstance(counts, dict) or set(counts) != set(FAMILIES):
        raise ValueError("title_scope_invalid")
    for group in counts.values():
        if (
            not isinstance(group, dict)
            or set(group) != COUNT_FIELDS
            or any(type(n) is not int or not 0 <= n <= MAX_ROWS for n in group.values())
        ):
            raise ValueError("title_scope_invalid")
    return value


def _object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("title_snapshot_json")
        result[key] = value
    return result


def strict_json(content: bytes, maximum: int = MAX_BYTES) -> dict[str, Any]:
    if not isinstance(content, bytes) or not 1 <= len(content) <= maximum:
        raise ValueError("title_snapshot_bytes")
    try:
        value = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_object,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
    except (ValueError, UnicodeError, RecursionError):
        raise ValueError("title_snapshot_json") from None
    if not isinstance(value, dict):
        raise ValueError("title_snapshot_json")
    return value


def _field(value: Any, spec: dict[str, Any]) -> None:
    if value is None:
        if spec["nullable"]:
            return
        raise ValueError("title_source_null")
    kind = spec["type"]
    valid = False
    if kind == "int":
        valid = type(value) is int and spec["minimum"] <= value <= spec["maximum"]
    elif kind == "text":
        valid = isinstance(value, str) and len(value) <= spec["maximum_length"]
    elif kind == "decimal":
        # Preserve exact signed source decimals, including zero and withheld amounts.
        pattern = rf"-?[0-9]{{1,{spec['integer_digits']}}}\.[0-9]{{{spec['scale']}}}"
        valid = isinstance(value, str) and re.fullmatch(pattern, value) is not None
    elif kind == "date":
        try:
            valid = (
                isinstance(value, str)
                and bool(re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", value))
                and date.fromisoformat(value).isoformat() == value
            )
        except ValueError:
            valid = False
    if not valid:
        raise ValueError("title_source_field")


def _rows(value: Any, spec: dict[str, Any]) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > spec["row_limit"]:
        raise ValueError("title_source_rows")
    fields = {c["name"] for c in spec["columns"]}
    for row in value:
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError("title_source_fields")
        for field in spec["columns"]:
            _field(row[field["name"]], field)
    return value


def _part_key(row: dict[str, Any], spec: dict[str, Any]) -> tuple[int, int, int]:
    return (row["codi_emp"], row[spec["note_field"]], row[spec["installment_field"]])


def validate_snapshot(content: bytes, scope: dict[str, Any]) -> dict[str, Any]:
    scope = validate_scope(scope)
    data = strict_json(content)
    if (
        not isinstance(data, dict)
        or set(data) != {"version", "scope_revision", "coverage", "families"}
        or data["version"] != VERSION
        or data["scope_revision"] != canonical_hash(scope)
        or data["coverage"] != COVERAGE
        or type(data["coverage"].get("settlements_complete")) is not bool
        or not isinstance(data["families"], list)
        or len(data["families"]) != len(FAMILIES)
    ):
        raise ValueError("title_snapshot_scope")
    contract = manifest()
    seen = set()
    for family in data["families"]:
        if (
            not isinstance(family, dict)
            or set(family) != {"name", "control", "installments", "payments", "accounting_links"}
            or not isinstance(family["name"], str)
            or family["name"] not in FAMILIES
            or family["name"] in seen
        ):
            raise ValueError("title_source_family")
        name = family["name"]
        seen.add(name)
        spec = contract["families"][name]
        control_rows = _rows([family["control"]], contract["queries"][f"{name}_control"])
        control = control_rows[0]
        for kind in ("installments", "payments", "accounting_links"):
            _rows(family[kind], contract["queries"][f"{name}_{kind}"])
        if (
            any(control[k] != scope["expected_counts"][name][k] for k in COUNT_FIELDS)
            or control["missing_headers"] != 0
            or control["missing_installments"] != 0
            or control["selected_installments"] != len(family["installments"])
            or control["payments"] != len(family["payments"])
            or control["accounting_links"] != len(family["accounting_links"])
        ):
            raise ValueError("title_source_coverage")

        parts = {_part_key(row, spec): row for row in family["installments"]}
        if len(parts) != len(family["installments"]):
            raise ValueError("title_installment_duplicate")
        payment_keys = set()
        paid_parts = set()
        for row in family["payments"]:
            key = _part_key(row, spec)
            posted = row[spec["payment_date_field"]]
            identity = (
                *key,
                posted,
                row[spec["payment_type_field"]],
                row[spec["payment_number_field"]],
            )
            if (
                key not in parts
                or identity in payment_keys
                or not scope["period_start"] <= posted < scope["period_end_exclusive"]
            ):
                raise ValueError("title_payment_identity")
            payment_keys.add(identity)
            paid_parts.add(key)
        due_count = 0
        for key, row in parts.items():
            due = row[spec["due_field"]]
            in_period = scope["period_start"] <= due < scope["period_end_exclusive"]
            if (
                key[0] != scope["company_code"]
                or key[1] < 0
                or key[2] < 0
                or not (in_period or key in paid_parts)
            ):
                raise ValueError("title_installment_scope")
            due_count += int(in_period)
        if due_count != control["due_installments"]:
            raise ValueError("title_source_coverage")
        link_keys = set()
        for row in family["accounting_links"]:
            identity = (
                row["fili_lan"],
                row[spec["note_field"]],
                row[spec["installment_field"]],
                row[spec["payment_date_field"]],
                row[spec["payment_type_field"]],
                row[spec["payment_number_field"]],
            )
            physical = (row["codi_emp"], row["nume_lan"], *identity, row["grupo"])
            if (
                identity not in payment_keys
                or physical in link_keys
                or row["codi_emp"] < 0
                or row["nume_lan"] < 0
            ):
                raise ValueError("title_link_identity")
            link_keys.add(physical)
    return data


def review_summary(snapshot: dict[str, Any]) -> dict[str, Any]:
    return {
        "families": {f["name"]: f["control"] for f in snapshot["families"]},
        "requires_semantic_review": True,
        "normalized_titles_created": 0,
        "bank_allocations_created": 0,
        "journals_created": 0,
        "settlements_complete": False,
        "bank_linkage": "unproven",
    }
