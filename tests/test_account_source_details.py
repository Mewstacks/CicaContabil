from __future__ import annotations

import hashlib
import io
import json
from copy import deepcopy

import pytest
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import connection
from django.test.utils import CaptureQueriesContext

from apps.audit.models import AuditEvent
from apps.hub.account_source_contract import FALSE_FLAGS, PROVENANCE, SCRIPT_SHA, scope_hash
from apps.hub.account_source_details import (
    AccountSourceDetailError,
    import_account_source_details,
    latest_consistent_source_detail,
)
from apps.hub.models import (
    FinancialAccount,
    LedgerAccount,
    ReconciliationAccountCandidate,
    ReconciliationAccountSourceDetail,
    ReconciliationLedgerMapping,
)
from apps.intelligence.models import NativeLedgerCollection
from apps.organizations.models import Organization
from test_account_candidates import run_import
from test_account_candidates import sources as sources_fixture
from test_portfolio_readiness import encode

sources = sources_fixture
pytestmark = pytest.mark.django_db


def detail_profile(sources):
    codes = [row["company_code"] for row in sources[0]["snapshot"]["companies"]]
    rows = [
        dict(
            row,
            catalogue_account_code=row["account_code"],
            account_name_raw="Nome literal sintético ",
            classification_raw="001.0008 ",
            inactive_on_raw=None,
        )
        for row in sources[1]["snapshot"]["configured_accounts"]
    ]
    return dict(
        version="contad-account-details-v1",
        completed=True,
        observed_at_utc="2026-11-14T18:00:00.0000000Z",
        decision="D-372",
        company_selector="A",
        expected_company_count=len(codes),
        two_reads_identical=True,
        company_codes_sha256=scope_hash(codes),
        retained_portfolio_sha256=hashlib.sha256(encode(sources[0])).hexdigest(),
        script_sha256=SCRIPT_SHA,
        provenance=deepcopy(PROVENANCE),
        snapshot=dict(
            companies=[{"company_code": code} for code in codes],
            configured_accounts=rows,
            cash_accounts=[],
            bank_references=[],
            integration_account_configurations=[],
        ),
        cadastral_names_and_bank_references_selected=True,
        **{flag: False for flag in FALSE_FLAGS},
    )


@pytest.fixture
def prepared_details(organization, sources):
    run_import(organization, sources, apply=True)
    return detail_profile(sources)


def apply_details(organization, sources, data, **changes):
    raw = encode(data)
    options = dict(
        organization=organization,
        portfolio_raw=encode(sources[0]),
        accounts_raw=encode(sources[1]),
        details_raw=raw,
        expected_sha256=hashlib.sha256(raw).hexdigest(),
        expected_size_bytes=len(raw),
        request_reference="D-372 synthetic preparation",
    )
    return import_account_source_details(**{**options, **changes})


def protected():
    return [
        list(model.objects.order_by("pk").values())
        for model in (
            ReconciliationAccountCandidate,
            FinancialAccount,
            LedgerAccount,
            ReconciliationLedgerMapping,
            NativeLedgerCollection,
        )
    ]


def test_preview_apply_and_replay_preserve_origin_and_every_human_or_operational_record(
    organization,
    sources,
    prepared_details,
):
    before = protected()
    with CaptureQueriesContext(connection) as queries:
        preview = apply_details(organization, sources, prepared_details)
    assert preview["to_create"] == 3 and not preview["applied"]
    assert not any(q["sql"].lstrip().startswith(("INSERT", "UPDATE", "DELETE")) for q in queries)
    result = apply_details(organization, sources, prepared_details, apply=True)
    assert result["created"] == 3 and protected() == before
    detail = ReconciliationAccountSourceDetail.objects.first()
    assert detail.row["classification_raw"] == "001.0008 "
    assert detail.row["account_name_raw"] == "Nome literal sintético "
    assert latest_consistent_source_detail(detail.candidate).pk == detail.pk
    assert detail.provenance["company_counts"] == dict(
        cash_accounts=0, bank_references=0, integration_account_configurations=0
    )
    audit_before = list(AuditEvent.objects.values())
    replay = apply_details(
        organization,
        sources,
        prepared_details,
        apply=True,
        request_reference="D-372 second technical execution",
    )
    assert replay["created"] == 0 and replay["existing"] == 3
    assert protected() == before and list(AuditEvent.objects.values()) == audit_before
    event = AuditEvent.objects.get(action="hub.reconciliation.account_source_details.imported")
    assert event.actor_id is None and event.metadata["human_review_performed"] is False
    assert "Nome literal" not in json.dumps(event.metadata)
    assert "row" not in event.metadata and "candidate" not in event.metadata
    assert run_import(organization, sources, apply=True)["created"] == 0


@pytest.mark.parametrize(
    "change",
    [
        "scope",
        "candidate",
        "duplicate",
        "catalogue",
        "status",
        "name_control",
        "date",
        "flag",
        "extra",
        "bool_code",
        "source_hash",
        "source_size",
        "origin",
    ],
)
def test_invalid_or_drifting_source_fails_before_any_write(
    organization,
    sources,
    prepared_details,
    change,
):
    data = deepcopy(prepared_details)
    row = data["snapshot"]["configured_accounts"][0]
    kwargs = {}
    if change == "scope":
        data["snapshot"]["companies"].pop()
    elif change == "candidate":
        row["account_code"] = row["catalogue_account_code"] = 999
    elif change == "duplicate":
        data["snapshot"]["configured_accounts"].append(deepcopy(row))
    elif change == "catalogue":
        row["catalogue_matches"] = 0
    elif change == "status":
        row["account_status_raw"] = "I"
    elif change == "name_control":
        row["account_name_raw"] = "private\nname"
    elif change == "date":
        row["inactive_on_raw"] = "2026-02-30"
    elif change == "flag":
        data["human_reviewed"] = True
    elif change == "extra":
        row["SALDO_INICIAL"] = 1
    elif change == "bool_code":
        row["company_code"] = True
    elif change == "source_hash":
        kwargs["expected_sha256"] = "0" * 64
    elif change == "source_size":
        kwargs["expected_size_bytes"] = 1
    elif change == "origin":
        c = ReconciliationAccountCandidate.objects.first()
        c.evidence["unexpected"] = True
        c.save()
    before, audits = protected(), AuditEvent.objects.count()
    with pytest.raises(AccountSourceDetailError):
        apply_details(organization, sources, data, apply=True, **kwargs)
    assert not ReconciliationAccountSourceDetail.objects.exists()
    assert before == protected() and AuditEvent.objects.count() == audits


def test_newer_details_append_same_time_conflicts_refuse_and_latest_corruption_never_falls_back(
    organization,
    sources,
    prepared_details,
):
    apply_details(organization, sources, prepared_details, apply=True)
    data = deepcopy(prepared_details)
    for row in data["snapshot"]["configured_accounts"]:
        row["account_name_raw"] = "Novo literal"
    with pytest.raises(AccountSourceDetailError, match="mesmo horário"):
        apply_details(organization, sources, data, apply=True)
    data["observed_at_utc"] = "2026-11-15T18:00:00.0000000Z"
    assert apply_details(organization, sources, data, apply=True)["created"] == 3
    candidate = ReconciliationAccountCandidate.objects.first()
    detail = latest_consistent_source_detail(candidate)
    assert detail.row["account_name_raw"] == "Novo literal"
    candidate.evidence["changed"] = True
    candidate.save()
    assert latest_consistent_source_detail(candidate) is None


def test_immutable_rows_reject_every_orm_mutation_and_cross_office_assignment(
    organization,
    sources,
    prepared_details,
):
    apply_details(organization, sources, prepared_details, apply=True)
    detail = ReconciliationAccountSourceDetail.objects.first()
    for operation in (
        lambda: detail.save(),
        lambda: detail.delete(),
        lambda: ReconciliationAccountSourceDetail.objects.all().update(row={}),
        lambda: ReconciliationAccountSourceDetail.objects.all().delete(),
        lambda: ReconciliationAccountSourceDetail.objects.bulk_update([detail], ["row"]),
    ):
        with pytest.raises(ValidationError):
            operation()
    other = Organization.objects.create(name="Other", slug="source-detail-other")
    detail.pk = None
    detail._state.adding = True
    detail.organization = other
    with pytest.raises(ValidationError):
        detail.save()


def test_audit_failure_rolls_back_all_details(organization, sources, prepared_details, monkeypatch):
    def fail(**kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr("apps.hub.account_source_details.record_event", fail)
    with pytest.raises(RuntimeError):
        apply_details(organization, sources, prepared_details, apply=True)
    assert not ReconciliationAccountSourceDetail.objects.exists()


def test_command_is_preview_and_never_prints_names(
    organization, sources, prepared_details, tmp_path
):
    paths = {}
    for key, data in (
        ("portfolio", sources[0]),
        ("accounts", sources[1]),
        ("details", prepared_details),
    ):
        path = tmp_path / f"{key}.json"
        path.write_bytes(encode(data))
        paths[f"{key}_file"] = str(path)
    stdout = io.StringIO()
    raw = encode(prepared_details)
    call_command(
        "import_reconciliation_account_details",
        organization=str(organization.pk),
        **paths,
        expected_sha256=hashlib.sha256(raw).hexdigest(),
        expected_size_bytes=len(raw),
        request_reference="D-372 synthetic",
        stdout=stdout,
    )
    assert json.loads(stdout.getvalue())["to_create"] == 3
    assert "Nome literal" not in stdout.getvalue()
    assert not ReconciliationAccountSourceDetail.objects.exists()


@pytest.mark.parametrize("state", ["linked", "dismissed"])
def test_import_preserves_completed_human_review(
    organization, sources, prepared_details, user, state
):
    from django.utils import timezone

    candidate = ReconciliationAccountCandidate.objects.first()
    candidate.state = state
    candidate.reviewed_by = user
    candidate.reviewed_at = timezone.now()
    candidate.review_data = {"decision": state, "bank_inflow_side": "credit"}
    candidate.review_evidence = "Evidência humana preservada"
    candidate.review_history = [{"reason": "Revisão anterior"}]
    candidate.save()
    before = protected()
    apply_details(organization, sources, prepared_details, apply=True)
    assert protected() == before
    assert latest_consistent_source_detail(candidate) is not None


def test_equivalent_timestamp_representations_are_deterministic(
    organization, sources, prepared_details
):
    apply_details(organization, sources, prepared_details, apply=True)
    # Different bytes/hash, identical source timestamp and factual data.
    raw = json.dumps(prepared_details, ensure_ascii=True, indent=2).encode()
    assert (
        apply_details(
            organization,
            sources,
            prepared_details,
            apply=True,
            details_raw=raw,
            expected_sha256=hashlib.sha256(raw).hexdigest(),
            expected_size_bytes=len(raw),
        )["created"]
        == 3
    )
    candidate = ReconciliationAccountCandidate.objects.first()
    selected = latest_consistent_source_detail(candidate)
    assert selected.source_file_sha256 == min(
        candidate.source_details.values_list("source_file_sha256", flat=True)
    )


def test_existing_conflicting_evidence_blocks_the_whole_batch(
    organization, sources, prepared_details
):
    candidate = ReconciliationAccountCandidate.objects.first()
    raw = encode(prepared_details)
    ReconciliationAccountSourceDetail.objects.create(
        organization=organization,
        candidate=candidate,
        source_file_sha256=hashlib.sha256(raw).hexdigest(),
        source_size_bytes=len(raw),
        source_observed_at="2026-11-14T18:00:00+00:00",
        candidate_source_sha256=candidate.source_file_sha256,
        portfolio_file_sha256=candidate.portfolio_file_sha256,
        row={"invalid": "synthetic conflicting facts"},
        provenance={"invalid": True},
        request_reference="Synthetic conflicting seed",
    )
    before = list(ReconciliationAccountSourceDetail.objects.values())
    with pytest.raises(AccountSourceDetailError, match="diverge"):
        apply_details(organization, sources, prepared_details, apply=True)
    assert before == list(ReconciliationAccountSourceDetail.objects.values())
    assert latest_consistent_source_detail(candidate) is None


def test_wrong_office_and_duplicate_json_never_write(organization, sources, prepared_details):
    other = Organization.objects.create(name="Other", slug="source-detail-import-other")
    with pytest.raises(AccountSourceDetailError):
        apply_details(other, sources, prepared_details, apply=True)
    raw = b'{"completed":true,' + encode(prepared_details)[1:]
    with pytest.raises(AccountSourceDetailError):
        apply_details(
            organization,
            sources,
            prepared_details,
            apply=True,
            details_raw=raw,
            expected_sha256=hashlib.sha256(raw).hexdigest(),
            expected_size_bytes=len(raw),
        )
    assert not ReconciliationAccountSourceDetail.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_concurrent_replay_serializes_one_set_and_one_audit(
    organization, sources, prepared_details
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
            return apply_details(organization, sources, prepared_details, apply=True)["created"]
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: apply(), range(2)))
    assert sorted(results) == [0, 3]
    assert ReconciliationAccountSourceDetail.objects.count() == 3
    assert (
        AuditEvent.objects.filter(
            action="hub.reconciliation.account_source_details.imported"
        ).count()
        == 1
    )
