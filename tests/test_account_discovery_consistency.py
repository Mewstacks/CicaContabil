"""Only positive aggregate counts may differ across pinned v3 source reads."""

from __future__ import annotations

from copy import deepcopy

import pytest

from account_discovery_fixtures import write_discovery_archive
from apps.hub import account_discovery_contract as contract
from apps.hub.account_discovery import (
    AccountDiscoveryError,
    _consistent_discovery,
    latest_consistent_discovery,
    prepared_account_facts,
)
from apps.hub.models import ReconciliationAccountDiscovery
from test_account_discovery import discovered_profile as discovered_profile_fixture
from test_account_discovery import scoped
from test_account_discovery import sources as sources_fixture
from test_account_discovery_archive import run_archive
from test_account_source_details import protected

sources = sources_fixture
discovered_profile = discovered_profile_fixture
pytestmark = pytest.mark.django_db


def consistency_profile(profile):
    data = deepcopy(profile)
    data["read_consistency"] = dict(
        cadastral_reads_identical=True,
        observed_usage_keys_identical=True,
        observed_usage_counts_identical=True,
        first_observed_chart_usage=deepcopy(data["snapshot"]["observed_chart_usage"]),
        first_read_started_at_utc="2026-11-14T17:58:00.0000000Z",
        first_read_completed_at_utc="2026-11-14T17:58:30.0000000Z",
        second_read_started_at_utc="2026-11-14T17:59:00.0000000Z",
        second_read_completed_at_utc="2026-11-14T17:59:30.0000000Z",
    )
    return data


@pytest.mark.parametrize("variation", ["identical", "increase", "decrease", "reordered", "empty"])
def test_v3_recomputes_consistency_preserves_both_reads_and_uses_second_snapshot(
    organization,
    sources,
    discovered_profile,
    tmp_path,
    variation,
):
    profile = consistency_profile(discovered_profile)
    proof = profile["read_consistency"]
    if variation in {"increase", "decrease"}:
        proof["first_observed_chart_usage"][0]["entry_count"] = 10
        profile["snapshot"]["observed_chart_usage"][0]["entry_count"] = (
            11 if variation == "increase" else 1
        )
        proof["observed_usage_counts_identical"] = False
        profile["two_reads_identical"] = False
    elif variation == "reordered":
        proof["first_observed_chart_usage"].reverse()
    elif variation == "empty":
        proof["first_observed_chart_usage"] = []
        profile["snapshot"]["observed_chart_usage"] = []
    before = protected()
    package = write_discovery_archive(
        profile, tmp_path / "v3.zip", version=contract.CONSISTENCY_VERSION
    )
    preview = run_archive(organization, sources, package)
    result = run_archive(
        organization, sources, package, apply=True, expected_manifest=preview["manifest_sha256"]
    )
    assert result["created"] == 1
    discovery = latest_consistent_discovery(organization)
    assert _consistent_discovery(discovery, deep=True)
    assert discovery.source_metadata["read_consistency"] == proof
    assert discovery.source_metadata["two_reads_identical"] == profile["two_reads_identical"]
    assert (
        discovery.source_data["observed_chart_usage"] == profile["snapshot"]["observed_chart_usage"]
    )
    company, chart = scoped(discovery)
    assert prepared_account_facts(company, chart, month="2026-09")["valid"]
    assert run_archive(organization, sources, package, apply=True)["created"] == 0
    assert protected() == before


@pytest.mark.parametrize(
    "problem",
    [
        "counts_flag_true",
        "counts_flag_false",
        "two_reads_true",
        "two_reads_false",
        "keys_flag_false",
        "cadastral_flag_false",
        "counts_flag_int",
        "two_reads_int",
        "removed_key",
        "extra_key",
        "duplicate_key",
        "changed_branch",
        "changed_month",
        "first_zero",
        "first_negative",
        "first_bool",
        "second_zero",
        "second_negative",
        "missing_proof",
        "extra_proof_key",
        "missing_time",
        "invalid_date",
        "wrong_timezone",
        "first_end_before_start",
        "second_start_before_first_end",
        "second_end_before_start",
        "report_before_end",
        "fractional_tick_reversal",
        "first_wrong_scope",
        "first_wrong_period",
        "missing_first_field",
        "extra_first_field",
        "wrong_version_pin",
    ],
)
def test_v3_rejects_false_consistency_claims_before_writes(
    organization,
    sources,
    discovered_profile,
    tmp_path,
    problem,
):
    profile = consistency_profile(discovered_profile)
    proof = profile["read_consistency"]
    first = proof["first_observed_chart_usage"]
    second = profile["snapshot"]["observed_chart_usage"]
    if problem in {"counts_flag_true", "two_reads_true"}:
        first[0]["entry_count"] += 1
        if problem == "counts_flag_true":
            profile["two_reads_identical"] = False
        else:
            proof["observed_usage_counts_identical"] = False
    elif problem == "counts_flag_false":
        proof["observed_usage_counts_identical"] = False
    elif problem == "two_reads_false":
        profile["two_reads_identical"] = False
    elif problem == "keys_flag_false":
        proof["observed_usage_keys_identical"] = False
    elif problem == "cadastral_flag_false":
        proof["cadastral_reads_identical"] = False
    elif problem == "counts_flag_int":
        proof["observed_usage_counts_identical"] = 1
    elif problem == "two_reads_int":
        profile["two_reads_identical"] = 1
    elif problem == "removed_key":
        first.pop()
    elif problem == "extra_key":
        first.append(dict(first[0], branch_code=9999))
    elif problem == "duplicate_key":
        first.append(deepcopy(first[0]))
    elif problem == "changed_branch":
        first[0]["branch_code"] += 1
    elif problem == "changed_month":
        first[0]["month"] = 11
    elif problem.startswith("first_") and problem in {"first_zero", "first_negative", "first_bool"}:
        first[0]["entry_count"] = {"first_zero": 0, "first_negative": -1, "first_bool": True}[
            problem
        ]
    elif problem == "second_zero":
        second[0]["entry_count"] = 0
    elif problem == "second_negative":
        second[0]["entry_count"] = -1
    elif problem == "missing_proof":
        del profile["read_consistency"]
    elif problem == "extra_proof_key":
        proof["unexpected"] = True
    elif problem == "missing_time":
        del proof["first_read_started_at_utc"]
    elif problem == "invalid_date":
        proof["first_read_started_at_utc"] = "2026-02-30T00:00:00.0000000Z"
    elif problem == "wrong_timezone":
        proof["first_read_started_at_utc"] = "2026-11-14T17:58:00.0000000+00:00"
    elif problem == "first_end_before_start":
        proof["first_read_completed_at_utc"] = "2026-11-14T17:57:00.0000000Z"
    elif problem == "second_start_before_first_end":
        proof["second_read_started_at_utc"] = "2026-11-14T17:58:29.0000000Z"
    elif problem == "second_end_before_start":
        proof["second_read_completed_at_utc"] = "2026-11-14T17:58:59.0000000Z"
    elif problem == "report_before_end":
        proof["second_read_completed_at_utc"] = "2026-11-14T18:00:00.0000001Z"
    elif problem == "fractional_tick_reversal":
        proof["first_read_completed_at_utc"] = "2026-11-14T17:59:00.0000002Z"
        proof["second_read_started_at_utc"] = "2026-11-14T17:59:00.0000001Z"
    elif problem == "first_wrong_scope":
        first[0]["company_code"] = 99999
    elif problem == "first_wrong_period":
        first[0]["year"] = 2025
    elif problem == "missing_first_field":
        del first[0]["branch_code"]
    elif problem == "extra_first_field":
        first[0]["unexpected"] = 1
    package = write_discovery_archive(
        profile,
        tmp_path / "invalid-v3.zip",
        version=contract.CONSISTENCY_VERSION,
        script_sha256=contract.ARCHIVE_SCRIPT_SHA if problem == "wrong_version_pin" else None,
    )
    with pytest.raises(AccountDiscoveryError):
        run_archive(organization, sources, package, apply=True)
    assert not ReconciliationAccountDiscovery.objects.exists()


def test_v2_does_not_accept_v3_pin_or_consistency_exception(
    organization,
    sources,
    discovered_profile,
    tmp_path,
):
    package = write_discovery_archive(
        discovered_profile, tmp_path / "wrong-v2.zip", script_sha256=contract.CONSISTENCY_SCRIPT_SHA
    )
    with pytest.raises(AccountDiscoveryError):
        run_archive(organization, sources, package, apply=True)
    discovered_profile["two_reads_identical"] = False
    package = write_discovery_archive(discovered_profile, tmp_path / "false-v2.zip")
    with pytest.raises(AccountDiscoveryError):
        run_archive(organization, sources, package, apply=True)
