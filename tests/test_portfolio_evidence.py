from __future__ import annotations

import base64
import gzip
import hashlib
import json
import stat
from copy import deepcopy

import pytest
from scripts.analyze_contad_portfolio import main

from apps.hub.contad_relations import CatalogEvidenceError
from apps.hub.portfolio_evidence import (
    FLAGS,
    MAX_BYTES,
    analyze_portfolio_profile,
    decode_portfolio_profile,
)


def evidence():
    return {
        "version": "contad-portfolio-profile-v1",
        "observed_at_utc": "2026-11-13T17:30:00+00:00",
        "period_start": "2026-09-01",
        "period_end_exclusive": "2026-11-01",
        "company_selector": "A",
        **FLAGS,
        "snapshot": {
            "companies": [
                {
                    "company_code": 212,
                    "configuration_rows": 1,
                    "codi_pad_raw": 100,
                    "comp_pad_raw": "N",
                    "i_planocontas_raw": 1,
                },
                {
                    "company_code": 213,
                    "configuration_rows": 0,
                    "codi_pad_raw": None,
                    "comp_pad_raw": None,
                    "i_planocontas_raw": None,
                },
            ],
            "cash_candidates": [
                {
                    "company_code": 212,
                    "cash_account_code": 8,
                    "selection_raw": "S",
                    "cash_type_raw": 1,
                    "bank_reference_count": 2,
                },
            ],
            "monthly_ledger": [
                {
                    "company_code": 212,
                    "source_plan_company_code": 100,
                    "branch_code": 0,
                    "year": 2026,
                    "month": 9,
                    "entry_count": 200,
                    "zero_debit_rows": 20,
                    "zero_credit_rows": 10,
                    "rows_without_lot": 1,
                },
            ],
        },
    }


def packed(value):
    raw = json.dumps(value).encode()
    return {
        "version": "contad-portfolio-profile-transfer-v1",
        "encoding": "gzip-base64",
        "bytes": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
        "data": base64.b64encode(gzip.compress(raw)).decode(),
    }


def test_coverage_keeps_empty_companies_raw_flags_and_unapproved_mapping():
    original = evidence()
    copy = deepcopy(original)
    report = analyze_portfolio_profile(original)
    assert original == copy
    assert report["company_count"] == 2 and report["entry_count"] == 200
    assert report["companies_without_ledger_rows"] == 1
    used, empty = report["companies"]
    assert used["monthly_entry_counts"] == {"2026-09": 200, "2026-10": 0}
    assert empty["monthly_entry_counts"] == {"2026-09": 0, "2026-10": 0}
    assert used["source_plan_codes_observed"] == [100]
    assert used["configuration_raw"]["comp_pad_raw"] == "N"
    assert used["cash_candidates"][0]["bank_reference_count"] == 2
    assert used["requires_review"]["source_plan_differs_company"]
    assert used["requires_review"]["rows_without_lot"]
    assert empty["requires_review"]["missing_configuration"]
    assert empty["requires_review"]["no_cash_candidate"]
    assert not report["financial_collection_enabled"] and not report["human_reviewed"]
    assert not report["bank_association_approved"] and report["acceptance_distinct_facts"] == 0
    assert all(not row["ready_for_financial_capture"] for row in report["companies"])


def test_empty_selection_and_multiple_plans_are_evidence_not_fabricated_accounts():
    value = evidence()
    row = deepcopy(value["snapshot"]["monthly_ledger"][0])
    row["source_plan_company_code"] = 212
    value["snapshot"]["monthly_ledger"].append(row)
    report = analyze_portfolio_profile(value)
    assert report["companies"][0]["requires_review"]["multiple_source_plans"]
    assert report["entry_count"] == 400
    value["snapshot"] = {"companies": [], "cash_candidates": [], "monthly_ledger": []}
    report = analyze_portfolio_profile(value)
    assert report["companies"] == [] and report["entry_count"] == 0


@pytest.mark.parametrize("flag", FLAGS)
def test_claimed_semantics_or_missing_guards_are_rejected(flag):
    value = evidence()
    value[flag] = not FLAGS[flag]
    with pytest.raises(CatalogEvidenceError):
        analyze_portfolio_profile(value)


@pytest.mark.parametrize(
    "key,value",
    [
        ("company_selector", "M"),
        ("company_selector", ["A"]),
        ("period_start", "2026-08-01"),
        ("period_end_exclusive", "2026-10-31"),
        ("period_end_exclusive", "2026-12-01"),
        ("period_end_exclusive", "2026-09-01"),
        ("period_end_exclusive", "2029-01-01"),
        ("observed_at_utc", "2026-11-13"),
        ("observed_at_utc", "2026-11-13T11:00:00-03:00"),
        ("observed_at_utc", None),
        ("period_start", None),
        ("snapshot", []),
    ],
)
def test_scope_or_provenance_rejected(key, value):
    report = evidence()
    report[key] = value
    with pytest.raises(CatalogEvidenceError):
        analyze_portfolio_profile(report)


@pytest.mark.parametrize(
    "group,key,value",
    [
        ("companies", "company_code", True),
        ("companies", "company_code", 0),
        ("companies", "configuration_rows", 2),
        ("companies", "comp_pad_raw", "SENSITIVE"),
        ("companies", "comp_pad_raw", "\n"),
        ("companies", "i_planocontas_raw", -1),
        ("companies", "configuration_rows", 0),
        ("companies", "codi_pad_raw", "100"),
        ("cash_candidates", "company_code", 999),
        ("cash_candidates", "cash_account_code", -1),
        ("cash_candidates", "bank_reference_count", 10001),
        ("cash_candidates", "cash_type_raw", False),
        ("cash_candidates", "selection_raw", "\x00"),
        ("monthly_ledger", "company_code", 999),
        ("monthly_ledger", "source_plan_company_code", 0),
        ("monthly_ledger", "branch_code", -1),
        ("monthly_ledger", "month", 8),
        ("monthly_ledger", "month", 11),
        ("monthly_ledger", "month", 13),
        ("monthly_ledger", "year", 2025),
        ("monthly_ledger", "entry_count", 0),
        ("monthly_ledger", "entry_count", 1000001),
        ("monthly_ledger", "entry_count", 1.5),
        ("monthly_ledger", "zero_debit_rows", 201),
        ("monthly_ledger", "rows_without_lot", None),
    ],
)
def test_invalid_or_cross_company_rows_rejected(group, key, value):
    report = evidence()
    report["snapshot"][group][0][key] = value
    with pytest.raises(CatalogEvidenceError):
        analyze_portfolio_profile(report)


@pytest.mark.parametrize(
    "group,limit", [("companies", 500), ("cash_candidates", 5000), ("monthly_ledger", 10000)]
)
def test_duplicate_extra_fields_and_row_limits_rejected(group, limit):
    value = evidence()
    rows = value["snapshot"][group]
    rows.append(deepcopy(rows[0]))
    with pytest.raises(CatalogEvidenceError):
        analyze_portfolio_profile(value)
    rows.pop()
    rows[0]["unexpected_private_field"] = "must-not-leak"
    with pytest.raises(CatalogEvidenceError):
        analyze_portfolio_profile(value)
    value["snapshot"][group] = [None] * (limit + 1)
    with pytest.raises(CatalogEvidenceError):
        analyze_portfolio_profile(value)


def test_global_count_limit_and_nullable_raw_codes():
    value = evidence()
    value["snapshot"]["cash_candidates"][0].update(selection_raw=None, cash_type_raw=None)
    assert analyze_portfolio_profile(value)["cash_candidate_count"] == 1
    value["snapshot"]["monthly_ledger"] = [
        {**value["snapshot"]["monthly_ledger"][0], "branch_code": i, "entry_count": 1000000}
        for i in range(6)
    ]
    with pytest.raises(CatalogEvidenceError):
        analyze_portfolio_profile(value)


@pytest.mark.parametrize("wrapped", [False, True])
def test_private_cli_and_hash_checked_transfer(tmp_path, capsys, wrapped):
    value = evidence()
    source = tmp_path / "private.json"
    raw = json.dumps(packed(value) if wrapped else value).encode()
    source.write_bytes(raw)
    target = tmp_path / "analysis.json"
    assert main(["--input", str(source), "--output", str(target)]) == 0
    report = json.loads(target.read_bytes())
    assert report["input_file_sha256"] == hashlib.sha256(raw).hexdigest()
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert main(["--input", str(source), "--output", str(target)]) == 1
    assert "212" not in capsys.readouterr().out


@pytest.mark.parametrize(
    "field,value",
    [
        ("sha256", "0" * 64),
        ("bytes", True),
        ("bytes", MAX_BYTES + 1),
        ("encoding", "plain"),
        ("data", "!not-base64"),
        ("data", base64.b64encode(b"not-gzip").decode()),
    ],
)
def test_transfer_tampering_rejected(field, value):
    transfer = packed(evidence())
    transfer[field] = value
    with pytest.raises(CatalogEvidenceError):
        decode_portfolio_profile(json.dumps(transfer).encode())


@pytest.mark.parametrize("raw", [b'{"version":1,"version":2}', b'{"value":NaN}', b"[]", b"\xff"])
def test_invalid_json_rejected_without_partial_report(raw):
    with pytest.raises(CatalogEvidenceError):
        decode_portfolio_profile(raw)


def test_compression_bomb_is_bounded():
    transfer = packed(evidence())
    transfer["data"] = base64.b64encode(gzip.compress(b" " * (MAX_BYTES + 1))).decode()
    with pytest.raises(CatalogEvidenceError):
        decode_portfolio_profile(json.dumps(transfer).encode())
