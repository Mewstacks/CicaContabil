from __future__ import annotations

import hashlib
import io
import json
from copy import deepcopy
from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.audit.models import AuditEvent
from apps.hub.account_discovery import (
    AccountDiscoveryError,
    discovery_company_facts,
    import_account_discovery,
    latest_consistent_discovery,
    prepared_account_facts,
)
from apps.hub.account_discovery_contract import (
    CHART_FIELDS,
    CONSISTENCY_SCRIPT_SHA,
    FALSE_FLAGS,
    PROVENANCE,
    SCRIPT_SHA,
    TARGETS,
    Invalid,
    decode_discovery,
    digest,
    text,
)
from apps.hub.models import (
    ClientCompany,
    ReconciliationAccountCandidate,
    ReconciliationAccountDiscovery,
    ReconciliationCompanyDiscovery,
    ReconciliationDiscoveredChartAccount,
)
from apps.organizations.models import Organization
from test_account_candidates import run_import
from test_account_candidates import sources as sources_fixture
from test_account_source_details import detail_profile, protected
from test_portfolio_readiness import encode

sources = sources_fixture
pytestmark = pytest.mark.django_db


def test_reader_pin_matches_the_committed_source():
    reader = (
        Path(__file__).resolve().parents[1] / "agent-windows/inspect-contad-chart-discovery.ps1"
    )
    assert hashlib.sha256(reader.read_bytes()).hexdigest() == CONSISTENCY_SCRIPT_SHA


def discovery_profile(sources):
    data = detail_profile(sources)
    data.update(
        version="contad-chart-discovery-v1",
        decision="D-373",
        script_sha256=SCRIPT_SHA,
        provenance=deepcopy(PROVENANCE),
        period_start="2026-09-01",
        period_end_exclusive="2026-12-01",
        **{flag: False for flag in FALSE_FLAGS},
    )
    snapshot = data["snapshot"]
    snapshot["companies"] = [
        dict(row, cash_account_parameter_raw=None, branch_parameter_raw=None)
        for row in sources[0]["snapshot"]["companies"]
    ]
    snapshot["observed_chart_usage"] = [
        {
            "company_code": row["company_code"],
            "chart_company_code": row["source_plan_company_code"],
            **{field: row[field] for field in ("branch_code", "year", "month", "entry_count")},
        }
        for row in sources[0]["snapshot"]["monthly_ledger"]
    ]
    snapshot["chart_owners"] = [{"chart_company_code": code} for code in (99, 212, 213, 214)]
    snapshot["chart_accounts"] = [
        {field: row[field] for field in CHART_FIELDS} for row in snapshot["configured_accounts"]
    ]
    # Account outside CTCONCILIACAO proves complete catalogue discovery.
    snapshot["chart_accounts"].append(
        dict(
            chart_company_code=213,
            account_code=77,
            account_name_raw="Outro nome literal ",
            classification_raw="001.077 ",
            account_type_raw="S",
            account_status_raw="I",
            inactive_on_raw="2026-10-01",
        )
    )
    snapshot["equivalent_accounts"] = []
    snapshot["plan_template_accounts"] = []
    snapshot["nature_rules"] = []
    snapshot["metadata"] = dict(
        targets=sorted(TARGETS),
        tables=[
            dict(table_id=index, table_name=name.lower(), table_type=1)
            for index, name in enumerate(sorted(TARGETS), 1)
        ],
        key_columns=[],
        relation_columns=[],
    )
    return data


@pytest.fixture
def discovered_profile(organization, sources):
    run_import(organization, sources, apply=True)
    return discovery_profile(sources)


def run_discovery(organization, sources, data, **changes):
    raw = encode(data)
    return import_account_discovery(
        **{
            "organization": organization,
            "portfolio_raw": encode(sources[0]),
            "accounts_raw": encode(sources[1]),
            "discovery_raw": raw,
            "expected_sha256": hashlib.sha256(raw).hexdigest(),
            "expected_size_bytes": len(raw),
            "request_reference": "Synthetic D-373 preparation",
            **changes,
        }
    )


@pytest.fixture
def discovered(organization, sources, discovered_profile):
    run_discovery(organization, sources, discovered_profile, apply=True)
    return latest_consistent_discovery(organization)


def scoped(discovered, company=212, chart=212, account=8):
    return (
        discovered.company_coverage.select_related("company", "discovery", "organization").get(
            source_company_code=company
        ),
        discovered.chart_accounts.select_related("discovery", "organization").get(
            chart_company_code=chart, account_code=account
        ),
    )


def test_preview_apply_replay_complete_shared_catalogue_preserves_human_and_old_sources(
    organization,
    sources,
    discovered_profile,
):
    before = protected()
    with CaptureQueriesContext(connection) as queries:
        preview = run_discovery(organization, sources, discovered_profile)
    assert preview["company_count"] == 3 and preview["chart_account_count"] == 4
    assert not [
        q for q in queries if q["sql"].lstrip().split()[0] in {"INSERT", "UPDATE", "DELETE"}
    ]
    applied = run_discovery(
        organization,
        sources,
        discovered_profile,
        apply=True,
        expected_manifest=preview["manifest_sha256"],
    )
    assert applied["created"] == 1 and applied["chart_accounts_created"] == 4
    replay = run_discovery(organization, sources, discovered_profile, apply=True)
    assert replay["created"] == replay["chart_accounts_created"] == 0
    assert replay["manifest_sha256"] == preview["manifest_sha256"]
    assert before == protected()
    event = AuditEvent.objects.get(action="hub.reconciliation.account_discovery.imported")
    assert event.actor_id is None and "Outro nome" not in json.dumps(event.metadata)
    batch = latest_consistent_discovery(organization)
    assert batch.chart_accounts.count() == 4 and batch.company_coverage.count() == 3
    missing = batch.company_coverage.get(source_company_code=214)
    assert missing.coverage_state == "no_accounts"
    assert "missing_accounting_parameters" in missing.gaps
    assert batch.chart_accounts.filter(chart_company_code=99).count() == 2
    assert batch.chart_accounts.get(chart_company_code=213).row["account_name_raw"].endswith(" ")


def test_prepared_facts_use_selected_month_and_never_interpret_raw_semantics(discovered):
    company, chart = scoped(discovered, 213, 99, 8)
    september = prepared_account_facts(company, chart, month="2026-09")
    october = prepared_account_facts(company, chart, month="2026-10")
    november = prepared_account_facts(company, chart, month="2026-11")
    assert september["valid"] and september["branches"] == [213, 500]
    assert "branch_scope_confirmed" in september["pending_fields"]
    assert october["known_fields"]["branch_code"] == 500
    assert "branch_code" in november["pending_fields"]
    assert "observed_usage" not in november["proof"]["chart_link"]["kinds"]
    assert november["proof"]["chart_link"]["kinds"] == ["configured_reference"]
    assert "chart_owner_confirmed" in november["pending_fields"]
    for result in (september, october, november):
        assert "account_active_and_postable" in result["pending_fields"]
        assert "bank_inflow_side" in result["pending_fields"]
        assert "nature" not in result["known_fields"]
        assert not result["collection_ready"]
    option = scoped(discovered, 213, 213, 77)
    assert (
        "chart_owner_confirmed"
        in prepared_account_facts(*option, month="2026-09")["pending_fields"]
    )


def test_observed_link_is_not_reused_for_another_month(organization, sources, discovered_profile):
    discovered_profile["snapshot"]["configured_accounts"] = []
    run_discovery(organization, sources, discovered_profile, apply=True)
    pair = scoped(latest_consistent_discovery(organization))
    assert (
        "chart_owner_confirmed"
        not in prepared_account_facts(*pair, month="2026-09")["pending_fields"]
    )
    assert (
        "chart_owner_confirmed" in prepared_account_facts(*pair, month="2026-11")["pending_fields"]
    )


@pytest.mark.parametrize(
    "change",
    [
        lambda d: d.update(human_reviewed=True),
        lambda d: d.update(script_sha256="f" * 64),
        lambda d: d.update(period_end_exclusive="2027-01-01"),
        lambda d: d["snapshot"]["companies"].pop(),
        lambda d: d["snapshot"]["chart_owners"].pop(),
        lambda d: d["snapshot"]["chart_accounts"].append(
            deepcopy(d["snapshot"]["chart_accounts"][0])
        ),
        lambda d: d["snapshot"]["chart_accounts"][0].update(account_code=True),
        lambda d: d["snapshot"]["chart_accounts"][0].update(inactive_on_raw="2026-02-30"),
        lambda d: d["snapshot"]["chart_accounts"][0].update(account_name_raw="drift"),
        lambda d: d["snapshot"]["companies"][-1].update(codi_pad_raw=99),
        lambda d: d["snapshot"]["observed_chart_usage"][0].update(month=8),
        lambda d: d["snapshot"]["observed_chart_usage"][0].update(entry_count=0),
        lambda d: d["snapshot"]["metadata"]["tables"][0].update(table_type=2),
        lambda d: d["snapshot"]["metadata"]["targets"].pop(),
    ],
)
def test_corrupt_incomplete_or_out_of_scope_source_is_rejected_before_writes(
    organization,
    sources,
    discovered_profile,
    change,
):
    change(discovered_profile)
    before = protected()
    with pytest.raises(AccountDiscoveryError):
        run_discovery(organization, sources, discovered_profile, apply=True)
    assert not ReconciliationAccountDiscovery.objects.exists()
    assert protected() == before


def test_hash_bytes_manifest_and_old_scope_drift_are_rejected(
    organization, sources, discovered_profile
):
    for changes in (
        {"expected_sha256": "0" * 64},
        {"expected_size_bytes": 1},
        {"expected_manifest": "0" * 64},
    ):
        with pytest.raises(AccountDiscoveryError):
            run_discovery(organization, sources, discovered_profile, apply=True, **changes)
    ClientCompany.objects.filter(organization=organization, dominio_code="214").update(
        dominio_code="215"
    )
    with pytest.raises(AccountDiscoveryError):
        run_discovery(organization, sources, discovered_profile, apply=True)
    assert not ReconciliationAccountDiscovery.objects.exists()


def test_immutability_scope_and_bulk_upsert_protection(discovered, organization):
    company, chart = scoped(discovered)
    for instance in (discovered, company, chart):
        with pytest.raises(ValidationError):
            instance.save()
        with pytest.raises(ValidationError):
            instance.delete()
        with pytest.raises(ValidationError):
            type(instance).objects.filter(pk=instance.pk).update(organization=organization)
        with pytest.raises(ValidationError):
            type(instance).objects.filter(pk=instance.pk).delete()
    other = Organization.objects.create(name="Other synthetic office", slug="discovery-other")
    alien = ReconciliationDiscoveredChartAccount(
        organization=other,
        discovery=discovered,
        chart_company_code=chart.chart_company_code,
        account_code=chart.account_code,
        row=chart.row,
        row_sha256=chart.row_sha256,
    )
    with pytest.raises(ValidationError):
        ReconciliationDiscoveredChartAccount.objects.insert_validated([alien])
    with pytest.raises(ValidationError):
        ReconciliationDiscoveredChartAccount.objects.bulk_create([chart], update_conflicts=True)
    assert not prepared_account_facts(company, alien, month="2026-09")["valid"]
    assert not prepared_account_facts(company, chart, month="2026-13")["valid"]


def test_apply_rolls_back_all_three_tables_on_audit_failure(
    organization, sources, discovered_profile, monkeypatch
):
    def fail(**kwargs):
        raise RuntimeError("Synthetic audit failure")

    monkeypatch.setattr("apps.hub.account_discovery.record_event", fail)
    with pytest.raises(RuntimeError):
        run_discovery(organization, sources, discovered_profile, apply=True)
    assert not ReconciliationAccountDiscovery.objects.exists()
    assert not ReconciliationDiscoveredChartAccount.objects.exists()
    assert not ReconciliationCompanyDiscovery.objects.exists()


def test_latest_observation_conflicts_and_corrupt_rows_fail_closed(
    organization,
    sources,
    discovered_profile,
    discovered,
):
    changed = deepcopy(discovered_profile)
    changed["snapshot"]["chart_accounts"][-1]["account_name_raw"] = "Changed synthetic name"
    with pytest.raises(AccountDiscoveryError):
        run_discovery(organization, sources, changed, apply=True)
    changed["observed_at_utc"] = "2026-11-15T18:00:00.0000000Z"
    run_discovery(organization, sources, changed, apply=True)
    latest = latest_consistent_discovery(organization)
    assert latest.pk != discovered.pk
    assert not prepared_account_facts(*scoped(discovered), month="2026-09")["valid"]
    company, chart = scoped(latest)
    chart.row = {**chart.row, "account_name_raw": "Corrupted"}
    assert not prepared_account_facts(company, chart, month="2026-09")["valid"]
    assert discovery_company_facts(company.company).discovery_id == latest.pk


def test_bulk_catalogue_does_not_query_per_account(organization, sources, discovered_profile):
    template = discovered_profile["snapshot"]["chart_accounts"][-1]
    discovered_profile["snapshot"]["chart_accounts"].extend(
        [dict(template, account_code=code) for code in range(1000, 2000)]
    )
    with CaptureQueriesContext(connection) as queries:
        run_discovery(organization, sources, discovered_profile, apply=True)
    assert ReconciliationDiscoveredChartAccount.objects.count() == 1004
    assert len(queries) < 150


def test_command_receipt_safe_and_requires_reviewed_manifest(
    organization, sources, discovered_profile, tmp_path
):
    args = []
    for name, value in (
        ("portfolio", sources[0]),
        ("accounts", sources[1]),
        ("discovery", discovered_profile),
    ):
        path = tmp_path / f"{name}.json"
        path.write_bytes(encode(value))
        args += [f"--{name}-file", str(path)]
    raw = encode(discovered_profile)
    args += [
        "--organization",
        str(organization.pk),
        "--expected-sha256",
        hashlib.sha256(raw).hexdigest(),
        "--expected-size-bytes",
        str(len(raw)),
        "--request-reference",
        "Synthetic command",
    ]
    output = io.StringIO()
    call_command("import_reconciliation_account_discovery", *args, stdout=output)
    preview = json.loads(output.getvalue())
    assert "Nome literal" not in output.getvalue()
    with pytest.raises(CommandError):
        call_command("import_reconciliation_account_discovery", *args, "--apply")
    output = io.StringIO()
    call_command(
        "import_reconciliation_account_discovery",
        *args,
        "--apply",
        "--expected-manifest",
        preview["manifest_sha256"],
        stdout=output,
    )
    assert json.loads(output.getvalue())["created"] == 1


def test_read_helpers_do_not_load_full_snapshot_and_source_revision_is_stable(discovered):
    company, chart = scoped(discovered)
    with CaptureQueriesContext(connection) as queries:
        latest = latest_consistent_discovery(discovered.organization)
        coverage = discovery_company_facts(company.company, latest)
        first = prepared_account_facts(coverage, chart, month="2026-09")
        second = prepared_account_facts(coverage, chart, month="2026-09")
    assert latest.get_deferred_fields() == {"source_data"}
    assert not any('"source_data"' in q["sql"] for q in queries)
    assert first["source_revision"] == second["source_revision"]
    assert first["revision"] == second["revision"]


def test_replay_reuses_one_discovery_without_repeating_metadata_in_company_join(
    organization,
    sources,
    discovered_profile,
    discovered,
    monkeypatch,
):
    from apps.hub import account_discovery as service

    verified_batches = []
    verified_companies = []
    original_discovery = service._consistent_discovery
    original_company = service._consistent_company

    def check_discovery(batch, *, deep=False):
        if deep:
            verified_batches.append(batch)
        return original_discovery(batch, deep=deep)

    def check_company(company):
        assert len(verified_batches) == 1
        assert company._state.fields_cache["discovery"] is verified_batches[0]
        verified_companies.append(company.pk)
        return original_company(company)

    monkeypatch.setattr(service, "_consistent_discovery", check_discovery)
    monkeypatch.setattr(service, "_consistent_company", check_company)
    with CaptureQueriesContext(connection) as captured:
        result = run_discovery(organization, sources, discovered_profile, apply=True)
    assert result["created"] == 0
    assert len(verified_companies) == discovered.company_count == 3
    company_queries = [
        item["sql"]
        for item in captured
        if '"hub_reconciliationcompanydiscovery"."facts"' in item["sql"]
    ]
    assert len(company_queries) == 1
    assert '"hub_reconciliationaccountdiscovery"' not in company_queries[0]
    assert '"source_metadata"' not in company_queries[0]


def test_deep_guard_checks_retained_payload_and_full_catalogue(discovered):
    from apps.hub.account_discovery import _consistent_discovery

    assert _consistent_discovery(discovered, deep=True)
    original = deepcopy(discovered.source_data)
    discovered.source_data["nature_rules"] = [{"unexpected": "tampered"}]
    assert not _consistent_discovery(discovered, deep=True)
    discovered.source_data = original
    chart = discovered.chart_accounts.get(chart_company_code=213, account_code=77)
    chart.row["account_name_raw"] = "Storage changed with new local checksum"
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE hub_reconciliationdiscoveredchartaccount SET row=%s, row_sha256=%s WHERE id=%s",
            [
                json.dumps(chart.row),
                digest(chart.row),
                chart.pk.hex if connection.vendor == "sqlite" else chart.pk,
            ],
        )
    assert not _consistent_discovery(discovered, deep=True)


def test_prior_candidate_decision_invalidates_prepared_revision(discovered):
    pair = scoped(discovered)
    before = prepared_account_facts(*pair, month="2026-09")
    candidate = ReconciliationAccountCandidate.objects.get(pk=before["existing_candidate_id"])
    candidate.state = "dismissed"
    candidate.review_evidence = "Synthetic changed decision"
    candidate.save()
    after = prepared_account_facts(*pair, month="2026-09")
    assert before["source_revision"] == after["source_revision"]
    assert before["revision"] != after["revision"]
    assert after["existing_candidate_state"] == "dismissed"
    assert after["blocking_reason"] == "previously_dismissed_candidate"


@pytest.mark.parametrize(
    "name",
    [
        "Nome\tcom\ncontrole\r ",
        "\u200bFormato\u200d",
        "Privado\ue000",
        "Suplementar\U0001f600",
        "Controle\x01literal",
        "Não atribuído\u0378",
    ],
)
def test_business_unicode_is_preserved_through_import_and_preparation(
    organization,
    sources,
    discovered_profile,
    name,
):
    row = discovered_profile["snapshot"]["chart_accounts"][0]
    row["account_name_raw"] = name
    for configured in discovered_profile["snapshot"]["configured_accounts"]:
        if (configured["chart_company_code"], configured["account_code"]) == (
            row["chart_company_code"],
            row["account_code"],
        ):
            configured["account_name_raw"] = name
    run_discovery(organization, sources, discovered_profile, apply=True)
    pair = scoped(latest_consistent_discovery(organization), 213, 99, 8)
    assert pair[1].row["account_name_raw"] == name
    assert prepared_account_facts(*pair, month="2026-09")["known_fields"]["name"] == name
    assert run_discovery(organization, sources, discovered_profile, apply=True)["created"] == 0


def test_utf16_units_and_wellformed_surrogates_match_reader_without_changing_d372():
    from apps.hub.account_source_contract import text as legacy_text

    text("\U0001f600" * 75, 150)
    with pytest.raises(Invalid):
        text("\U0001f600" * 76, 150)
    for invalid in ("\ud800", "\udfff", 3, True):
        with pytest.raises(Invalid):
            text(invalid, 150)
    with pytest.raises(Invalid):
        legacy_text("\u200b", 150)


def test_nul_is_accepted_in_source_but_cannot_reach_jsonb_without_lossless_codec(
    organization,
    sources,
    discovered_profile,
):
    discovered_profile["snapshot"]["chart_accounts"][-1]["account_name_raw"] = "Name\0literal"
    raw = encode(discovered_profile)
    parsed = decode_discovery(
        raw,
        expected_sha256=hashlib.sha256(raw).hexdigest(),
        expected_size_bytes=len(raw),
        companies={212, 213, 214},
        portfolio_sha256=hashlib.sha256(encode(sources[0])).hexdigest(),
    )
    assert parsed["snapshot"]["chart_accounts"][-1]["account_name_raw"] == "Name\0literal"
    with pytest.raises(AccountDiscoveryError, match=r"U\+0000"):
        run_discovery(organization, sources, discovered_profile, apply=True)
    assert not ReconciliationAccountDiscovery.objects.exists()


def test_configured_reference_does_not_approve_another_account_in_same_chart(
    organization,
    sources,
    discovered_profile,
):
    extra = dict(discovered_profile["snapshot"]["chart_accounts"][0], account_code=80)
    discovered_profile["snapshot"]["chart_accounts"].append(extra)
    run_discovery(organization, sources, discovered_profile, apply=True)
    pair = scoped(latest_consistent_discovery(organization), 213, 99, 80)
    september = prepared_account_facts(*pair, month="2026-09")
    november = prepared_account_facts(*pair, month="2026-11")
    assert september["proof"]["chart_link"]["kinds"] == ["observed_usage"]
    assert "chart_owner_confirmed" in november["pending_fields"]


def test_equivalent_reference_and_zero_branch_remain_literal(
    organization,
    sources,
    discovered_profile,
):
    discovered_profile["snapshot"]["equivalent_accounts"] = [
        dict(company_code=214, chart_company_code=213, account_code=77)
    ]
    discovered_profile["snapshot"]["observed_chart_usage"].append(
        dict(
            company_code=214,
            chart_company_code=213,
            branch_code=0,
            year=2026,
            month=11,
            entry_count=3,
        )
    )
    run_discovery(organization, sources, discovered_profile, apply=True)
    pair = scoped(latest_consistent_discovery(organization), 214, 213, 77)
    result = prepared_account_facts(*pair, month="2026-11")
    assert result["branches"] == [0]
    assert result["blocking_reason"] == "unsupported_observed_branch"
    assert "branch_code" in result["pending_fields"]
    assert "chart_owner_confirmed" not in result["pending_fields"]
    assert result["known_fields"]["inactive_on_raw"] == "2026-10-01"
    assert "account_active_and_postable" in result["pending_fields"]


def test_replay_refuses_stored_catalogue_identity_drift(
    organization,
    sources,
    discovered_profile,
    discovered,
):
    chart = discovered.chart_accounts.get(chart_company_code=213, account_code=77)
    # Simulate storage damage outside the append-only application APIs.
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE hub_reconciliationdiscoveredchartaccount SET account_code=78 WHERE id=%s",
            [chart.pk.hex if connection.vendor == "sqlite" else chart.pk],
        )
    with pytest.raises(AccountDiscoveryError):
        run_discovery(organization, sources, discovered_profile, apply=True)


@pytest.mark.django_db(transaction=True)
def test_concurrent_discovery_replay_serializes_one_complete_set_and_one_audit(
    organization,
    sources,
    discovered_profile,
):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections

    if connection.vendor != "postgresql":
        pytest.skip("Requires PostgreSQL row locks.")
    barrier = Barrier(2)

    def apply():
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return run_discovery(organization, sources, discovered_profile, apply=True)["created"]
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: apply(), range(2)))
    assert sorted(results) == [0, 1]
    assert ReconciliationAccountDiscovery.objects.count() == 1
    assert ReconciliationDiscoveredChartAccount.objects.count() == 4
    assert ReconciliationCompanyDiscovery.objects.count() == 3
    assert (
        AuditEvent.objects.filter(action="hub.reconciliation.account_discovery.imported").count()
        == 1
    )
