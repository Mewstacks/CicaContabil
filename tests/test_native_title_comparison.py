"""Snapshot differences are technical evidence, never an implicit reversal or approval."""

from __future__ import annotations

import hashlib
import io
import json
import stat
from copy import deepcopy
from uuid import uuid4

import pytest
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.files.base import ContentFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.utils import timezone

from apps.audit.models import AuditEvent
from apps.hub.models import (
    FinancialAccount,
    JournalEntry,
    ProductModule,
    ReconciliationSourceFile,
    ReconciliationTitleSnapshot,
)
from apps.intelligence.models import NativeTitleCollection
from apps.intelligence.native_title_comparison import (
    NativeTitleComparisonError,
    TitleSourceEvidence,
    compare_collected_titles,
    compare_title_sources,
)
from apps.intelligence.native_title_contract import (
    MAX_BYTES,
    canonical_hash,
    contract_hash,
    manifest,
    review_summary,
)
from apps.organizations.models import Membership
from apps.platform.models import TenantContract
from test_native_titles import complete, encode, sample
from test_native_titles import fiscal as fiscal


def evidence(scope, data):
    content = encode(data)
    return TitleSourceEvidence(content, scope, hashlib.sha256(content).hexdigest(), contract_hash())


def refresh(scope, data, *, new_capture=True):
    if new_capture:
        scope["capture_id"] = str(uuid4())
    for family in data["families"]:
        spec = manifest()["families"][family["name"]]
        control = family["control"]
        control.update(
            due_installments=sum(
                scope["period_start"] <= row[spec["due_field"]] < scope["period_end_exclusive"]
                for row in family["installments"]
            ),
            selected_installments=len(family["installments"]),
            payments=len(family["payments"]),
            accounting_links=len(family["accounting_links"]),
        )
        scope["expected_counts"][family["name"]] = {
            key: control[key] for key in ("due_installments", "payments", "accounting_links")
        }
    data["scope_revision"] = canonical_hash(scope)
    return evidence(scope, data)


def pair():
    scope, data = sample()
    return evidence(scope, data), deepcopy(scope), deepcopy(data)


def test_new_capture_and_reordered_rows_do_not_create_new_financial_facts():
    old, scope, data = pair()
    data["families"].reverse()
    for family in data["families"]:
        for kind in ("installments", "payments", "accounting_links"):
            family[kind].reverse()
    report = compare_title_sources(old, refresh(scope, data))
    assert old.expected_sha256 != report["current"]["sha256"] and not report["same_capture"]
    assert report["counts"] == {"added": 0, "absent": 0, "changed": 0, "unchanged": 9}
    assert report["requires_semantic_review"] and report["financial_actions_applied"] == 0
    assert report["bank_linkage"] == "unproven"


@pytest.mark.parametrize("old_value,value", [("40.00", "123.45"), (None, "0.00")])
def test_changed_literal_is_reported_without_its_value(old_value, value):
    scope, data = sample()
    field = "vpag_entp"
    data["families"][0]["payments"][0][field] = old_value
    old = evidence(deepcopy(scope), deepcopy(data))
    data["families"][0]["payments"][0][field] = value
    current = refresh(scope, data)
    report = compare_title_sources(old, current)
    assert report["counts"]["changed"] == 1
    detail = report["families"]["entradas"]["payments"]["changes"][0]
    assert detail["changed_fields"] == [field]
    assert len(detail["key_sha256"]) == 64
    assert value not in json.dumps(detail)
    assert report == compare_title_sources(old, current)


def test_padded_document_identifier_change_is_not_normalized_or_disclosed():
    old, scope, data = pair()
    data["families"][0]["installments"][0]["numero_titulo_entp"] = "CONFIDENTIAL-ONLY"
    report = compare_title_sources(old, refresh(scope, data))
    assert report["counts"]["changed"] == 1
    assert "CONFIDENTIAL-ONLY" not in json.dumps(report)
    assert report["families"]["entradas"]["installments"]["changes"][0]["changed_fields"] == [
        "numero_titulo_entp"
    ]


def test_absent_payment_can_remove_parent_from_union_without_proving_erp_deletion():
    old, scope, data = pair()
    family = data["families"][1]
    assert family["installments"][0]["vcto_saip"] >= scope["period_end_exclusive"]
    for kind in ("installments", "payments", "accounting_links"):
        family[kind].clear()
    report = compare_title_sources(old, refresh(scope, data))
    assert report["counts"]["absent"] == 3 and report["counts"]["changed"] == 0
    assert not report["absence_proves_reversal"]
    assert (
        report["families"]["saidas"]["installments"]["changes"][0]["state"] == "absent_from_current"
    )
    assert report["financial_actions_applied"] == 0


def test_new_parent_uses_complete_keys_and_retains_all_child_differences():
    old, scope, data = pair()
    family = data["families"][0]
    for kind in ("installments", "payments", "accounting_links"):
        additions = deepcopy(family[kind])
        for row in additions:
            row["codi_ent"] = 20
        family[kind].extend(additions)
    report = compare_title_sources(old, refresh(scope, data))
    assert report["counts"]["added"] == 6
    assert report["counts"]["absent"] == report["counts"]["changed"] == 0


def test_payment_sequence_change_is_absent_and_new_not_the_same_component():
    old, scope, data = pair()
    family = data["families"][0]
    family["payments"][0]["nropag_entp"] = 3
    family["accounting_links"][0]["nropag_entp"] = 3
    report = compare_title_sources(old, refresh(scope, data))
    assert report["counts"]["added"] == report["counts"]["absent"] == 2
    assert report["counts"]["changed"] == 0


@pytest.mark.parametrize(
    "field,value,added,changed",
    [
        ("codi_emp", 1000, 1, 0),
        ("contra_partida", 42, 0, 1),
    ],
)
def test_link_ledger_company_is_a_key_and_fiscal_owner_is_fili_lan(field, value, added, changed):
    old, scope, data = pair()
    row = data["families"][1]["accounting_links"][0]
    assert row["codi_emp"] == 999 and row["fili_lan"] == 212
    row[field] = value
    report = compare_title_sources(old, refresh(scope, data))
    counts = report["families"]["saidas"]["accounting_links"]["counts"]
    assert counts["added"] == counts["absent"] == added and counts["changed"] == changed


def test_same_capture_with_different_valid_bytes_is_refused():
    old, scope, data = pair()
    data["families"][0]["payments"][0]["vpag_entp"] = "41.00"
    with pytest.raises(NativeTitleComparisonError, match="mesma captura"):
        compare_title_sources(old, refresh(scope, data, new_capture=False))


@pytest.mark.parametrize("corruption", ["hash", "contract", "size", "duplicate_json"])
def test_corrupt_or_unbounded_evidence_is_refused(corruption):
    old, scope, _data = pair()
    content, digest, contract = old.content, old.expected_sha256, old.contract_sha256
    if corruption == "hash":
        digest = "0" * 64
    elif corruption == "contract":
        contract = "0" * 64
    elif corruption == "size":
        content = b"x" * (MAX_BYTES + 1)
        digest = hashlib.sha256(content).hexdigest()
    else:
        content = old.content.replace(b'"version":', b'"version":"duplicate","version":', 1)
        digest = hashlib.sha256(content).hexdigest()
    with pytest.raises(NativeTitleComparisonError):
        compare_title_sources(old, TitleSourceEvidence(content, scope, digest, contract))


@pytest.mark.parametrize(
    "field,value",
    [
        ("company_code", 213),
        ("comparison_bank_account_code", 9),
        ("period_start", "2026-08-01"),
    ],
)
def test_other_company_account_or_period_cannot_be_mixed(field, value):
    old, scope, data = pair()
    scope[field] = value
    with pytest.raises(NativeTitleComparisonError):
        compare_title_sources(old, refresh(scope, data))


def captured(fiscal):
    agent, account, actor, job, data, _ = fiscal
    assert complete(agent, job, data).status_code == 200
    job.refresh_from_db()
    return account, actor, job


@pytest.mark.django_db
def test_retained_comparison_and_private_cli_do_not_modify_records(fiscal, tmp_path):
    account, actor, job = captured(fiscal)
    audit_count = AuditEvent.objects.count()
    output = tmp_path / "technical.json"
    stdout = io.StringIO()
    options = dict(
        organization=str(account.organization_id),
        actor=str(actor.pk),
        previous=str(job.pk),
        current=str(job.pk),
    )
    call_command("compare_contad_native_titles", **options, output=str(output), stdout=stdout)
    result = json.loads(stdout.getvalue())
    assert result["same_capture"] and result["counts"]["unchanged"] == 9
    assert result["details_written"] and stat.S_IMODE(output.stat().st_mode) == 0o600
    assert json.loads(output.read_text())["financial_actions_applied"] == 0
    assert NativeTitleCollection.objects.count() == 1 and AuditEvent.objects.count() == audit_count
    assert not JournalEntry.objects.exists() and not ReconciliationTitleSnapshot.objects.exists()
    with pytest.raises(CommandError):
        call_command("compare_contad_native_titles", **options, output=str(output))
    assert output.exists() and AuditEvent.objects.count() == audit_count


@pytest.mark.django_db
@pytest.mark.parametrize("revocation", ["role", "user", "module", "contract", "account"])
def test_current_operational_permission_is_required(fiscal, revocation):
    account, actor, job = captured(fiscal)
    if revocation == "role":
        Membership.objects.filter(user=actor, organization=account.organization).update(
            role="auditor"
        )
    elif revocation == "user":
        type(actor).objects.filter(pk=actor.pk).update(is_active=False)
    elif revocation == "module":
        ProductModule.objects.filter(
            organization=account.organization, code="reconciliation"
        ).update(enabled=False)
    elif revocation == "contract":
        TenantContract.objects.filter(organization=account.organization).update(status="suspended")
    else:
        type(account).objects.filter(pk=account.pk).update(active=False)
    refused = ValueError if revocation in {"module", "contract"} else PermissionDenied
    with pytest.raises(refused):
        compare_collected_titles(
            organization_id=account.organization_id,
            previous_id=job.pk,
            current_id=job.pk,
            actor=actor,
        )


@pytest.mark.django_db
def test_other_tenant_and_tampered_retained_file_are_refused(fiscal):
    account, actor, job = captured(fiscal)
    with pytest.raises(ObjectDoesNotExist):
        compare_collected_titles(
            organization_id=uuid4(), previous_id=job.pk, current_id=job.pk, actor=actor
        )
    with job.source_file.content.open("wb") as stream:
        stream.write(b"tampered-synthetic-only")
    with pytest.raises(NativeTitleComparisonError):
        compare_collected_titles(
            organization_id=account.organization_id,
            previous_id=job.pk,
            current_id=job.pk,
            actor=actor,
        )


@pytest.mark.django_db
def test_permission_revoked_during_storage_read_is_rechecked(fiscal, monkeypatch):
    import apps.intelligence.native_title_comparison as comparison

    account, actor, job = captured(fiscal)
    original = comparison._validated

    def revoke(evidence):
        result = original(evidence)
        Membership.objects.filter(user=actor, organization=account.organization).update(
            role="auditor"
        )
        return result

    monkeypatch.setattr(comparison, "_validated", revoke)
    with pytest.raises(PermissionDenied):
        compare_collected_titles(
            organization_id=account.organization_id,
            previous_id=job.pk,
            current_id=job.pk,
            actor=actor,
        )


@pytest.mark.django_db
def test_changed_retained_review_result_cannot_approve_semantics(fiscal):
    account, actor, job = captured(fiscal)
    NativeTitleCollection.objects.filter(pk=job.pk).update(
        result=dict(job.result, requires_semantic_review=False)
    )
    with pytest.raises(NativeTitleComparisonError, match="Recibo"):
        compare_collected_titles(
            organization_id=account.organization_id,
            previous_id=job.pk,
            current_id=job.pk,
            actor=actor,
        )


@pytest.mark.django_db
def test_two_valid_sources_from_different_account_contexts_cannot_be_mixed(fiscal):
    account, actor, prior = captured(fiscal)
    other_account = FinancialAccount.objects.create(
        organization=account.organization,
        company=account.company,
        name="Other synthetic context",
        account_reference="SYN-OTHER",
        ledger_code="8",
    )
    scope, data = sample()
    raw = encode(data)
    digest = hashlib.sha256(raw).hexdigest()
    source = ReconciliationSourceFile(
        organization=account.organization,
        company=account.company,
        financial_account=other_account,
        origin="obligation",
        kind="json",
        original_filename="synthetic-only.json",
        content_hash=digest,
        size_bytes=len(raw),
    )
    source.content.save(source.original_filename, ContentFile(raw), save=True)
    current = NativeTitleCollection.objects.create(
        id=scope["capture_id"],
        organization=account.organization,
        agent=prior.agent,
        financial_account=other_account,
        requested_by=actor,
        evidence_reference="Synthetic only",
        scope=scope,
        scope_revision=canonical_hash(scope),
        contract_hash=contract_hash(),
        state="captured",
        source_file=source,
        content_hash=digest,
        result=review_summary(data),
        completed_at=timezone.now(),
    )
    with pytest.raises(NativeTitleComparisonError, match="Contas"):
        compare_collected_titles(
            organization_id=account.organization_id,
            previous_id=prior.pk,
            current_id=current.pk,
            actor=actor,
        )


@pytest.mark.django_db
def test_cli_refuses_symlink_output_and_preserves_target(fiscal, tmp_path):
    account, actor, job = captured(fiscal)
    target = tmp_path / "existing-user-file.json"
    target.write_bytes(b"preserve-me")
    output = tmp_path / "review.json"
    output.symlink_to(target)
    with pytest.raises(CommandError):
        call_command(
            "compare_contad_native_titles",
            organization=str(account.organization_id),
            actor=str(actor.pk),
            previous=str(job.pk),
            current=str(job.pk),
            output=str(output),
        )
    assert target.read_bytes() == b"preserve-me" and output.is_symlink()


@pytest.mark.django_db
def test_storage_failure_is_safe_and_does_not_expose_private_backend_details(fiscal, monkeypatch):
    account, actor, job = captured(fiscal)

    def unavailable(*args, **kwargs):
        raise RuntimeError("synthetic-private-backend-key")

    monkeypatch.setattr(job.source_file.content.storage, "open", unavailable)
    with pytest.raises(NativeTitleComparisonError, match="fonte privada") as error:
        compare_collected_titles(
            organization_id=account.organization_id,
            previous_id=job.pk,
            current_id=job.pk,
            actor=actor,
        )
    assert "synthetic-private-backend-key" not in str(error.value)
    with pytest.raises(CommandError) as error:
        call_command(
            "compare_contad_native_titles",
            organization=str(account.organization_id),
            actor=str(actor.pk),
            previous=str(job.pk),
            current=str(job.pk),
        )
    assert "synthetic-private-backend-key" not in str(error.value)
