from __future__ import annotations

import base64
import gzip
import hashlib
import json
import stat
from copy import deepcopy

import pytest
from scripts.prepare_contad_portfolio_readiness import main

from apps.hub.contad_relations import CatalogEvidenceError
from apps.hub.portfolio_evidence import FLAGS
from apps.hub.portfolio_readiness import prepare_portfolio_readiness


def profiles():
    companies = [
        {
            "company_code": code,
            "configuration_rows": 0 if code == 214 else 1,
            "codi_pad_raw": None if code == 214 else code,
            "comp_pad_raw": None if code == 214 else "N",
            "i_planocontas_raw": None if code == 214 else 1,
        }
        for code in (212, 213, 214)
    ]
    common = {
        **FLAGS,
        "observed_at_utc": "2026-11-13T17:30:00+00:00",
        "period_start": "2026-09-01",
        "period_end_exclusive": "2026-11-01",
        "company_selector": "A",
    }
    portfolio = {
        **common,
        "version": "contad-portfolio-profile-v1",
        "snapshot": {
            "companies": deepcopy(companies),
            "cash_candidates": [
                {
                    "company_code": 213,
                    "cash_account_code": 0,
                    "selection_raw": "S",
                    "cash_type_raw": 1,
                    "bank_reference_count": 0,
                }
            ],
            "monthly_ledger": [
                {
                    "company_code": company,
                    "source_plan_company_code": plan,
                    "branch_code": branch,
                    "year": 2026,
                    "month": month,
                    "entry_count": count,
                    "zero_debit_rows": 0,
                    "zero_credit_rows": 0,
                    "rows_without_lot": 0,
                }
                for company, plan, branch, month, count in (
                    (212, 212, 212, 9, 3),
                    (213, 99, 213, 9, 4),
                    (213, 99, 500, 9, 5),
                    (213, 99, 500, 10, 6),
                )
            ],
        },
    }
    accounts = {
        **common,
        "version": "contad-reconciliation-account-profile-v1",
        "observed_at_utc": "2026-11-13T18:00:00+00:00",
        "snapshot": {
            "companies": deepcopy(companies),
            "configured_accounts": [
                {
                    "company_code": 213,
                    "chart_company_code": 99,
                    "account_code": code,
                    "account_type_raw": "A",
                    "account_status_raw": "A",
                    "catalogue_matches": 1,
                }
                for code in (8, 9)
            ],
        },
    }
    return portfolio, accounts


def encode(value):
    return json.dumps(value).encode()


def prepare(portfolio, accounts):
    return prepare_portfolio_readiness(encode(portfolio), encode(accounts))


def test_all_companies_and_independent_pilot_survive_missing_configuration():
    portfolio, accounts = profiles()
    report = prepare(portfolio, accounts)
    assert [row["company_code"] for row in report["companies"]] == [212, 213, 214]
    pilot, candidate, empty = report["companies"]
    assert pilot["status"] == empty["status"] == "account_evidence_missing"
    assert "no_ledger_rows_in_period" not in pilot["gaps"]
    assert "no_ledger_rows_in_period" in empty["gaps"]
    assert "missing_accounting_parameters" in empty["gaps"]
    assert empty["monthly_entry_counts"] == {"2026-09": 0, "2026-10": 0}
    assert candidate["status"] == "account_candidates_require_review"
    assert report["existing_pilot_reference"]["company_present_in_profiles"]
    assert not report["existing_pilot_reference"]["account_present_as_configured_candidate"]
    assert report["existing_pilot_reference"]["assessment"] == "not_evaluated_by_these_profiles"
    assert not report["existing_pilot_reference"]["changes_existing_configuration"]
    assert report["summary"]["companies_without_candidates_with_ledger_rows"] == 1
    assert report["summary"]["companies_without_candidates"] == 2
    assert report["summary"]["companies_missing_parameters"] == 1
    assert report["summary"]["ready_for_financial_capture_count"] == 0
    assert not report["human_reviewed"] and not report["financial_collection_enabled"]
    assert not report["bank_association_approved"] and not report["creates_accounts_rules_or_jobs"]


def test_branches_and_plan_totals_never_become_account_counts_or_approval():
    report = prepare(*profiles())
    company = report["companies"][1]
    assert company["branches_observed"] == [213, 500]
    assert company["monthly_entry_counts"] == {"2026-09": 9, "2026-10": 6}
    assert "multiple_branches_complete_lots_review" in company["gaps"]
    assert "source_plan_differs_company" in company["gaps"]
    assert "cash_registers_not_bank_accounts" in company["gaps"]
    assert "account_level_counts_missing" in company["gaps"]
    assert "truncar partidas" in report["gap_guidance"]["multiple_branches_complete_lots_review"]
    for candidate in company["configured_account_candidates"]:
        assert candidate["account_level_counts"] is None
        assert candidate["collection_scope"] is None
        assert candidate["branches_observed_for_plan"] == [213, 500]
        assert candidate["periods_observed_for_plan"] == ["2026-09", "2026-10"]
        assert candidate["account_type_raw"] == candidate["account_status_raw"] == "A"
        assert all(value is None for value in candidate["review"].values())
        assert not candidate["ready_for_financial_capture"]
    assert all(value is None for value in company["company_review"].values())


def test_no_rows_and_unknown_catalogue_keep_candidate_visible_and_unapproved():
    portfolio, accounts = profiles()
    portfolio["snapshot"]["monthly_ledger"] = []
    candidate = accounts["snapshot"]["configured_accounts"][0]
    candidate.update(catalogue_matches=0, account_type_raw=None, account_status_raw=None)
    report = prepare(portfolio, accounts)
    assert report["summary"]["companies_without_ledger_rows"] == 3
    company = report["companies"][1]
    assert len(company["configured_account_candidates"]) == 2
    assert "missing_catalogue_match" in company["gaps"]
    assert "configured_plan_not_observed" in company["gaps"]
    assert company["branches_observed"] == []
    assert not company["ready_for_financial_capture"]


def test_empty_sources_do_not_add_the_historical_pilot_to_the_discovered_portfolio():
    portfolio, accounts = profiles()
    for source in (portfolio, accounts):
        for key in source["snapshot"]:
            source["snapshot"][key] = []
    report = prepare(portfolio, accounts)
    assert report["companies"] == []
    assert report["summary"]["company_count"] == 0
    assert not report["existing_pilot_reference"]["company_present_in_profiles"]


@pytest.mark.parametrize("mismatch", ["company", "configuration", "period"])
def test_individually_valid_but_misaligned_profiles_rejected(mismatch):
    portfolio, accounts = profiles()
    if mismatch == "company":
        accounts["snapshot"]["companies"].pop()
    elif mismatch == "configuration":
        accounts["snapshot"]["companies"][0]["codi_pad_raw"] = 99
    else:
        accounts["period_end_exclusive"] = "2026-10-01"
    with pytest.raises(CatalogEvidenceError, match="divergem"):
        prepare(portfolio, accounts)


def test_row_order_is_not_semantics_and_original_bytes_are_fingerprinted():
    portfolio, accounts = profiles()
    accounts["snapshot"]["companies"].reverse()
    accounts["snapshot"]["configured_accounts"].reverse()
    originals = deepcopy((portfolio, accounts))
    p_raw, a_raw = encode(portfolio), encode(accounts)
    report = prepare_portfolio_readiness(p_raw, a_raw)
    assert (portfolio, accounts) == originals
    assert report["sources"]["portfolio"]["input_file_sha256"] == hashlib.sha256(p_raw).hexdigest()
    assert report["sources"]["configured_accounts"]["input_file_sha256"] == (
        hashlib.sha256(a_raw).hexdigest()
    )
    candidate_rows = report["companies"][1]["configured_account_candidates"]
    assert [row["account_code"] for row in candidate_rows] == [8, 9]
    assert report == prepare_portfolio_readiness(p_raw, a_raw)


@pytest.mark.parametrize("target", [0, 1])
@pytest.mark.parametrize(
    "flag", ["account_meanings_approved", "bank_association_approved", "uploaded"]
)
def test_claimed_approval_or_external_operation_rejected(target, flag):
    sources = profiles()
    sources[target][flag] = True
    with pytest.raises(CatalogEvidenceError):
        prepare(*sources)


@pytest.mark.parametrize("corruption", ["duplicate", "extra", "outside", "missing", "swapped"])
def test_incomplete_or_contaminated_inputs_rejected(corruption):
    portfolio, accounts = profiles()
    if corruption == "duplicate":
        accounts["snapshot"]["configured_accounts"].append(
            deepcopy(accounts["snapshot"]["configured_accounts"][0])
        )
    elif corruption == "extra":
        portfolio["snapshot"]["companies"][0]["private_name"] = "must-not-leak"
    elif corruption == "outside":
        accounts["snapshot"]["configured_accounts"][0]["company_code"] = 999
    elif corruption == "missing":
        del portfolio["snapshot"]["monthly_ledger"]
    else:
        portfolio, accounts = accounts, portfolio
    with pytest.raises(CatalogEvidenceError):
        prepare(portfolio, accounts)


def test_transport_digest_and_duplicate_json_keys_checked_before_matrix():
    portfolio, accounts = profiles()
    p_raw = encode(portfolio)
    transfer = {
        "version": "contad-portfolio-profile-transfer-v1",
        "sha256": hashlib.sha256(p_raw).hexdigest(),
        "bytes": len(p_raw),
        "encoding": "gzip-base64",
        "data": base64.b64encode(gzip.compress(p_raw)).decode(),
    }
    report = prepare_portfolio_readiness(encode(transfer), encode(accounts))
    assert report["summary"]["company_count"] == 3
    transfer["sha256"] = "0" * 64
    with pytest.raises(CatalogEvidenceError):
        prepare_portfolio_readiness(encode(transfer), encode(accounts))
    with pytest.raises(CatalogEvidenceError):
        prepare_portfolio_readiness(b'{"version":"one","version":"two"}', encode(accounts))


def test_multiple_plans_preserved_without_assigning_a_candidate_to_another_plan():
    portfolio, accounts = profiles()
    row = deepcopy(portfolio["snapshot"]["monthly_ledger"][1])
    row["source_plan_company_code"] = 98
    row["branch_code"] = 501
    portfolio["snapshot"]["monthly_ledger"].append(row)
    report = prepare(portfolio, accounts)
    company = report["companies"][1]
    assert company["source_plan_codes_observed"] == [98, 99]
    assert "multiple_source_plans" in company["gaps"]
    assert company["branches_observed"] == [213, 500, 501]
    assert company["configured_account_candidates"][0]["branches_observed_for_plan"] == [213, 500]


def test_cli_writes_private_exclusive_matrix_and_only_safe_summary(tmp_path, capsys):
    portfolio, accounts = profiles()
    source, candidate_source = tmp_path / "source.json", tmp_path / "accounts.json"
    output = tmp_path / "matrix.json"
    source.write_bytes(encode(portfolio))
    candidate_source.write_bytes(encode(accounts))
    args = [
        "--portfolio-input",
        str(source),
        "--accounts-input",
        str(candidate_source),
        "--output",
        str(output),
    ]
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["summary"]["company_count"] == 3
    assert result["report_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()
    assert "companies" not in result and "configured_account_candidates" not in result
    assert stat.S_IMODE(output.stat().st_mode) == 0o600
    original = output.read_bytes()
    assert main(args) == 1
    assert output.read_bytes() == original
    assert capsys.readouterr().out == ""
    output.unlink()
    output.symlink_to(source)
    assert main(args) == 1
    assert source.read_bytes() == encode(portfolio)
    assert output.is_symlink()
    assert not list(tmp_path.glob(".cica-evidence-*"))


def test_cli_invalid_input_does_not_write_or_print_source(tmp_path, capsys):
    portfolio, accounts = profiles()
    portfolio["snapshot"]["companies"][0]["private_name"] = "must-not-leak"
    source, candidate_source = tmp_path / "source.json", tmp_path / "accounts.json"
    output = tmp_path / "matrix.json"
    source.write_bytes(encode(portfolio))
    candidate_source.write_bytes(encode(accounts))
    assert (
        main(
            [
                "--portfolio-input",
                str(source),
                "--accounts-input",
                str(candidate_source),
                "--output",
                str(output),
            ]
        )
        == 1
    )
    captured = capsys.readouterr()
    assert not output.exists() and captured.out == ""
    assert "must-not-leak" not in captured.err
