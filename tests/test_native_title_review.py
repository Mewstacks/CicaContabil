"""Synthetic customer source review, cumulative publication and isolation."""

from copy import deepcopy
from datetime import date
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.hub.models import (
    CompanyAccessGrant,
    FinancialAccount,
    JournalEntry,
    ProductModule,
    ReconciliationSourceFile,
    ReconciliationTitleSnapshot,
)
from apps.hub.native_title_forms import NativeSettlementForm
from apps.hub.title_persistence import (
    _load,
    confirm_title_allocations,
    import_title_snapshot,
    latest_title_snapshot,
    prepare_title_allocations,
    undo_title_allocation,
)
from apps.intelligence.native_title_contract import canonical_hash, manifest
from apps.intelligence.native_title_review import (
    ACTION,
    NativeReviewConflict,
    confirm_native_review,
    installment_context,
    load_native_source,
    preview_native_review,
    review_token,
    source_installments,
)
from apps.intelligence.native_title_translation import (
    import_reviewed_native_titles,
    row_reference,
    translate_reviewed_titles,
)
from apps.organizations.models import Membership
from apps.platform.models import TenantContract
from test_native_title_translation import review_data
from test_native_titles import complete, encode
from test_native_titles import fiscal as fiscal_fixture
from test_title_persistence import bank

fiscal_source = fiscal_fixture
pytestmark = pytest.mark.django_db


@pytest.fixture
def captured(fiscal_source):
    agent, account, actor, job, data, _ = fiscal_source
    assert complete(agent, job, data).status_code == 200
    source = load_native_source(account=account, capture_id=job.pk, actor=actor)
    review = review_data(job.scope, data)
    return account, actor, source, review


def prepare(captured, review=None):
    account, actor, source, original = captured
    review = review or original
    reference = review["decisions"][0]["installment_reference"]
    token = review_token(source, reference, actor)
    preview = preview_native_review(
        source=source, actor=actor, reference=reference, review=review, token=token
    )
    return dict(
        account=account,
        capture_id=source.capture.pk,
        actor=actor,
        reference=reference,
        review=review,
        confirmation_token=preview["confirmation_token"],
    ), preview


def post_fields(response):
    form = response.context["native_form"]
    data = {
        "action": "preview",
        "review-token": form.initial["token"],
        "review-kind": "payable",
        "review-principal_field": next(
            c[0] for c in form.fields["principal_field"].choices if c[0]
        ),
        "review-evidence_reference": "Documento sintético conferido",
        "review-source_confirmed": "on",
        "review-grouping_confirmed": "on",
        "review-limits_confirmed": "on",
    }
    for index, amount in enumerate(("40,00", "30,00")):
        for field in ("principal", "cash"):
            data[f"event-{index}-{field}"] = amount
        for field in ("interest", "penalty", "fees", "discount"):
            data[f"event-{index}-{field}"] = "0"
        data[f"event-{index}-direction"] = "outflow"
        data[f"event-{index}-reverses"] = "none"
    return data


def review_url(captured):
    account, _, source, review = captured
    return reverse(
        "hub:reconciliation-native-title-review",
        args=[account.pk, source.capture.pk, review["decisions"][0]["installment_reference"]],
    )


def test_source_preview_never_writes_and_keeps_zero_components(captured, settings):
    _account, _actor, source, review = captured
    before = (ReconciliationSourceFile.objects.count(), AuditEvent.objects.count())
    files = set(settings.MEDIA_ROOT.rglob("*.json"))
    options, preview = prepare(captured)
    assert options["confirmation_token"]
    assert preview["installment"]["outstanding_cents"] is None
    assert preview["preserved_count"] == 0
    part = installment_context(source, review["decisions"][0]["installment_reference"])
    assert [len(e["rows"]) for e in part["events"]] == [2, 1]
    assert not ReconciliationTitleSnapshot.objects.exists()
    assert not JournalEntry.objects.exists()
    assert (ReconciliationSourceFile.objects.count(), AuditEvent.objects.count()) == before
    assert set(settings.MEDIA_ROOT.rglob("*.json")) == files


def test_translation_reuses_validated_spec_and_preserves_public_row_references(
    captured, monkeypatch
):
    account, _, source, review = captured
    family = source.raw["families"][0]
    expected_part = row_reference(family["name"], "installments", family["installments"][0])
    expected_payments = {
        row_reference(family["name"], "payments", row) for row in family["payments"]
    }
    calls = []

    def counted_manifest():
        calls.append(True)
        return manifest()

    monkeypatch.setattr("apps.intelligence.native_title_translation.manifest", counted_manifest)
    payload, provenance = translate_reviewed_titles(
        evidence=source.evidence,
        review=review,
        company_key=str(account.company_id),
        account_reference=account.account_reference,
    )
    assert calls == [True]
    assert payload["titles"][0]["installments"][0]["key"] == expected_part
    assert {
        ref for event in provenance[0]["settlements"] for ref in event["payment_references"]
    } == expected_payments


def test_legacy_native_import_audit_rollback_cleans_only_new_source(
    captured, monkeypatch, settings
):
    account, actor, source, review = captured
    before = set(settings.MEDIA_ROOT.rglob("*.json"))
    source_count = ReconciliationSourceFile.objects.count()

    def fail(**kwargs):
        raise RuntimeError("synthetic legacy audit failure")

    monkeypatch.setattr("apps.intelligence.native_title_translation.record_event", fail)
    with pytest.raises(RuntimeError, match="legacy audit"):
        import_reviewed_native_titles(
            organization_id=account.organization_id,
            capture_id=source.capture.pk,
            actor=actor,
            review=review,
        )
    assert not ReconciliationTitleSnapshot.objects.exists()
    assert ReconciliationSourceFile.objects.count() == source_count
    assert latest_title_snapshot(account) is None
    assert set(settings.MEDIA_ROOT.rglob("*.json")) == before


def test_publish_is_private_idempotent_and_preserves_actor(captured):
    options, _ = prepare(captured)
    first, created = confirm_native_review(**options)
    second, replay_created = confirm_native_review(**options)
    assert created and not replay_created and first.pk == second.pk
    assert first.reviewed_by_id == captured[1].pk
    assert ReconciliationTitleSnapshot.objects.count() == 1
    audit = AuditEvent.objects.get(action=ACTION)
    assert audit.metadata["capture_id"] == str(captured[2].capture.pk)
    assert audit.metadata["previous_snapshot_id"] is None
    assert audit.metadata["provenance"][0]["installment_key"] == options["reference"]
    assert audit.metadata["evidence_reference"] == options["review"]["evidence_reference"]
    assert not JournalEntry.objects.exists()


def test_accumulation_preserves_existing_known_facts_and_prior_snapshot(captured):
    account, actor, _, _ = captured
    old_part = {
        "key": "existing-part",
        "due_on": "2026-10-10",
        "principal_cents": 900,
        "outstanding_cents": 900,
        "settlements": [],
    }
    payload = {
        "contract": "titles-normalized-v1",
        "company_key": str(account.company_id),
        "account_reference": account.account_reference,
        "as_of": "2026-09-29",
        "settlements_complete": True,
        "titles": [{"key": "existing-title", "kind": "receivable", "installments": [old_part]}],
    }
    old, _ = import_title_snapshot(
        financial_account=account,
        actor=actor,
        content=encode(payload),
        evidence_reference="Fonte sintética anterior",
    )
    options, preview = prepare(captured)
    assert preview["preserved_count"] == 1
    current, _ = confirm_native_review(**options)
    body, _ = _load(current, account)
    assert body["titles"][0]["installments"][0] == old_part
    assert len(body["titles"]) == 2 and body["settlements_complete"] is False
    assert _load(old, account)[0] == payload
    audit = AuditEvent.objects.get(action=ACTION)
    assert audit.metadata["previous_snapshot_id"] == str(old.pk)
    assert audit.metadata["previous_fingerprint"] == old.fingerprint


def test_second_native_parcel_accumulates_and_stale_first_preview_cannot_overwrite(captured):
    account, _actor, source, review = captured
    original_options, _ = prepare(captured)
    first, _ = confirm_native_review(**original_options)
    before = _load(first, account)[0]
    other = next(p for p in source_installments(source) if p["family"] == "saidas")
    part = installment_context(source, other["reference"])
    changed = deepcopy(review)
    changed["decisions"][0].update(
        family="saidas",
        installment_reference=other["reference"],
        kind="receivable",
        principal_field=part["principal_choices"][0][0],
        settlements=[
            {
                "payment_references": part["events"][0]["references"],
                "normalized": {
                    "key": part["events"][0]["key"],
                    "posted_on": part["events"][0]["posted_on"],
                    "principal_cents": 200,
                    "cash_cents": 200,
                    "interest_cents": 0,
                    "penalty_cents": 0,
                    "fees_cents": 0,
                    "discount_cents": 0,
                    "direction": "inflow",
                    "reverses": None,
                },
            }
        ],
    )
    options, preview = prepare(captured, changed)
    assert preview["preserved_count"] == 1
    current, _ = confirm_native_review(**options)
    assert _load(current, account)[0]["titles"][0] == before["titles"][0]
    assert len(_load(current, account)[0]["titles"]) == 2
    with pytest.raises(NativeReviewConflict, match="Outra revisão"):
        confirm_native_review(**original_options)
    assert ReconciliationTitleSnapshot.objects.count() == 2


@pytest.mark.parametrize("change", ["decision", "reference", "signature"])
def test_confirmation_rejects_changed_review_and_unsigned_context(captured, change):
    options, _ = prepare(captured)
    if change == "decision":
        options["review"] = deepcopy(options["review"])
        options["review"]["evidence_reference"] = "Alterada após prévia"
    elif change == "reference":
        options["reference"] = "0" * 64
    else:
        options["confirmation_token"] += "changed"
    with pytest.raises(NativeReviewConflict):
        confirm_native_review(**options)
    assert not ReconciliationTitleSnapshot.objects.exists()


def test_confirmation_is_bound_to_original_human(captured):
    account, actor, _, _ = captured
    options, _ = prepare(captured)
    another = type(actor).objects.create_user("second-reviewer@example.test", "synthetic-password")
    Membership.objects.create(organization=account.organization, user=another, role="owner")
    options["actor"] = another
    with pytest.raises(NativeReviewConflict):
        confirm_native_review(**options)
    assert not ReconciliationTitleSnapshot.objects.exists()


@pytest.mark.parametrize(
    "change", ["role", "module", "contract", "account", "user", "company_code", "ledger"]
)
def test_confirmation_rechecks_live_scope_after_preview(captured, membership, change):
    account, actor, _, _ = captured
    options, _ = prepare(captured)
    if change == "role":
        Membership.objects.filter(pk=membership.pk).update(role="auditor")
    elif change == "module":
        ProductModule.objects.filter(
            organization=account.organization, code="reconciliation"
        ).update(enabled=False)
    elif change == "contract":
        TenantContract.objects.filter(organization=account.organization).update(status="suspended")
    elif change == "account":
        FinancialAccount.objects.filter(pk=account.pk).update(active=False)
    elif change == "user":
        type(actor).objects.filter(pk=actor.pk).update(is_active=False)
    elif change == "company_code":
        type(account.company).objects.filter(pk=account.company_id).update(dominio_code="999")
    else:
        FinancialAccount.objects.filter(pk=account.pk).update(ledger_code="999")
    with pytest.raises((PermissionDenied, ValueError)):
        confirm_native_review(**options)
    assert not ReconciliationTitleSnapshot.objects.exists()


def test_operator_grant_revocation_and_cross_account_capture_are_closed(
    captured, membership, monkeypatch
):
    account, actor, source, _ = captured
    membership.role = "operator"
    membership.save()
    grant = CompanyAccessGrant.objects.create(
        organization=account.organization,
        membership=membership,
        company=account.company,
        modules=["reconciliation"],
        is_active=True,
    )
    options, _ = prepare(captured)
    grant.is_active = False
    grant.save()
    with pytest.raises(PermissionDenied):
        confirm_native_review(**options)
    grant.is_active = True
    grant.save()
    other = FinancialAccount.objects.create(
        organization=account.organization,
        company=account.company,
        name="Outra sintética",
        account_reference="OTHER",
        ledger_code="8",
    )
    with monkeypatch.context() as patch:
        patch.setattr(
            "apps.intelligence.native_title_review._load",
            lambda *a, **k: pytest.fail("private source opened outside account"),
        )
        with pytest.raises(ValueError, match="conta selecionada"):
            load_native_source(account=other, capture_id=source.capture.pk, actor=actor)


def test_storage_corruption_and_audit_failure_do_not_publish(captured, monkeypatch, settings):
    options, _ = prepare(captured)
    before = set(settings.MEDIA_ROOT.rglob("*.json"))
    count = ReconciliationSourceFile.objects.count()

    def fail(**kwargs):
        raise RuntimeError("synthetic audit failure")

    with monkeypatch.context() as patch:
        patch.setattr("apps.intelligence.native_title_review.record_event", fail)
        with pytest.raises(RuntimeError, match="synthetic audit"):
            confirm_native_review(**options)
    assert not ReconciliationTitleSnapshot.objects.exists()
    assert ReconciliationSourceFile.objects.count() == count
    assert set(settings.MEDIA_ROOT.rglob("*.json")) == before
    with captured[2].capture.source_file.content.open("wb") as stream:
        stream.write(b"synthetic tampering")
    with pytest.raises(ValueError):
        confirm_native_review(**options)
    assert not ReconciliationTitleSnapshot.objects.exists()


def test_older_source_is_rejected_preserving_newer_snapshot(captured):
    options, _ = prepare(captured)
    first, _ = confirm_native_review(**options)
    payload, _ = _load(first, captured[0])
    payload["as_of"] = "2026-10-01"
    newer, _ = import_title_snapshot(
        financial_account=captured[0],
        actor=captured[1],
        content=encode(payload),
        evidence_reference="Fotografia sintética mais recente",
    )
    with pytest.raises(NativeReviewConflict, match="anterior"):
        prepare(captured)
    assert ReconciliationTitleSnapshot.objects.count() == 2
    assert _load(newer, captured[0])[0]["as_of"] == "2026-10-01"


def test_restoring_previous_fingerprint_preserves_snapshots_and_activates_review(captured):
    original, _ = prepare(captured)
    first, _ = confirm_native_review(**original)
    changed = deepcopy(captured[3])
    changed["decisions"][0]["settlements"][0]["normalized"].update(
        principal_cents=3500, cash_cents=3500
    )
    corrected_options, _ = prepare(captured, changed)
    second, _ = confirm_native_review(**corrected_options)
    assert second.pk != first.pk
    original_event = AuditEvent.objects.get(action=ACTION, target_id=str(second.pk))
    restore_options, _ = prepare(captured)
    restored, changed = confirm_native_review(**restore_options)
    assert restored.pk == first.pk and changed
    assert latest_title_snapshot(captured[0]).pk == first.pk
    assert (
        _load(second, captured[0])[0]["titles"][0]["installments"][0]["settlements"][0][
            "cash_cents"
        ]
        == 3500
    )
    assert ReconciliationTitleSnapshot.objects.count() == 2
    assert AuditEvent.objects.filter(action=ACTION).count() == 3
    activation = AuditEvent.objects.filter(action=ACTION).first()
    assert activation.metadata["activated_existing"] is True
    assert activation.metadata["previous_snapshot_id"] == str(second.pk)
    assert activation.metadata["previous_review_event_id"] == str(original_event.pk)
    replay, changed = confirm_native_review(**restore_options)
    assert replay.pk == first.pk and not changed


def test_restoration_rollback_preserves_current_pointer_and_both_source_files(
    captured, monkeypatch, settings
):
    original, _ = prepare(captured)
    first, _ = confirm_native_review(**original)
    changed = deepcopy(captured[3])
    changed["decisions"][0]["settlements"][0]["normalized"].update(
        principal_cents=3500, cash_cents=3500
    )
    options, _ = prepare(captured, changed)
    second, _ = confirm_native_review(**options)
    restore, _ = prepare(captured)
    before = set(settings.MEDIA_ROOT.rglob("*.json"))

    def fail(**kwargs):
        raise RuntimeError("synthetic restore audit failure")

    monkeypatch.setattr("apps.intelligence.native_title_review.record_event", fail)
    with pytest.raises(RuntimeError, match="restore audit"):
        confirm_native_review(**restore)
    assert latest_title_snapshot(captured[0]).pk == second.pk
    assert _load(first, captured[0]) and _load(second, captured[0])
    assert set(settings.MEDIA_ROOT.rglob("*.json")) == before
    assert AuditEvent.objects.filter(action=ACTION).count() == 2


def test_normal_import_replay_does_not_restore_and_null_pointer_uses_legacy_order(captured):
    account, actor, _, _ = captured
    options, _ = prepare(captured)
    first, _ = confirm_native_review(**options)
    first_payload, _ = _load(first, account)
    changed = deepcopy(captured[3])
    changed["decisions"][0]["settlements"][0]["normalized"].update(
        principal_cents=3500, cash_cents=3500
    )
    corrected, _ = prepare(captured, changed)
    second, _ = confirm_native_review(**corrected)
    replay, created = import_title_snapshot(
        financial_account=account,
        actor=actor,
        content=encode(first_payload),
        evidence_reference="Reenvio sintético",
    )
    assert replay.pk == first.pk and not created
    assert latest_title_snapshot(account).pk == second.pk
    FinancialAccount.objects.filter(pk=account.pk).update(current_title_snapshot=None)
    assert latest_title_snapshot(account).pk == second.pk


def test_pointer_outside_account_fails_closed_before_reading_source(captured):
    account, actor, _, _ = captured
    options, _ = prepare(captured)
    first, _ = confirm_native_review(**options)
    other = FinancialAccount.objects.create(
        organization=account.organization,
        company=account.company,
        name="Outra conta sintética",
        account_reference="OTHER",
    )
    payload, _ = _load(first, account)
    payload["account_reference"] = other.account_reference
    foreign, _ = import_title_snapshot(
        financial_account=other,
        actor=actor,
        content=encode(payload),
        evidence_reference="Fonte sintética da outra conta",
    )
    FinancialAccount.objects.filter(pk=account.pk).update(current_title_snapshot=foreign)
    with pytest.raises(ValueError, match="fora desta"):
        latest_title_snapshot(account)
    with pytest.raises(ValueError, match="fora desta"):
        prepare(captured)


def test_correction_of_allocated_parcel_requires_undo(captured):
    account, actor, _, review = captured
    options, _ = prepare(captured)
    first, _ = confirm_native_review(**options)
    body, _ = _load(first, account)
    title = body["titles"][0]
    part = title["installments"][0]
    movement = bank(account, cents=-4000)
    requests = [
        {
            "movement_key": str(movement.pk),
            "title_key": title["key"],
            "installment_key": part["key"],
            "settlement_key": part["settlements"][0]["key"],
            "cash_cents": 1000,
        }
    ]
    kwargs = dict(
        snapshot=first,
        requests=requests,
        actor=actor,
        period_start=date(2026, 9, 1),
        period_end=date(2026, 9, 30),
    )
    plan = prepare_title_allocations(**kwargs)
    batch, _ = confirm_title_allocations(
        **kwargs,
        request_id=uuid4(),
        preview_fingerprint=plan.fingerprint,
        evidence_reference="Vínculo sintético revisado",
    )
    changed = deepcopy(review)
    changed["decisions"][0]["settlements"][0]["normalized"].update(
        principal_cents=3500, cash_cents=3500
    )
    with pytest.raises(NativeReviewConflict, match="Desfaça"):
        prepare(captured, changed)
    assert undo_title_allocation(
        allocation=batch.allocations.get(), actor=actor, reason="Correção sintética comprovada"
    )
    corrected_options, _ = prepare(captured, changed)
    corrected, _ = confirm_native_review(**corrected_options)
    assert (
        _load(first, account)[0]["titles"][0]["installments"][0]["settlements"][0]["cash_cents"]
        == 4000
    )
    assert (
        _load(corrected, account)[0]["titles"][0]["installments"][0]["settlements"][0]["cash_cents"]
        == 3500
    )


@pytest.mark.parametrize(
    "value,expected", [("1.234,56", 123456), ("12,34", 1234), ("0", 0), ("0,00", 0), ("12", 1200)]
)
def test_component_money_uses_explicit_brazilian_reais(value, expected):
    form = NativeSettlementForm(events=[{"key": "a"}], index=0)
    assert form.fields["principal"].clean(value) == expected


@pytest.mark.parametrize(
    "value", ["12.34", "1,234.56", "1e3", "NaN", "-1", "+1", "1.2.3", "0,001", "9" * 31]
)
def test_component_money_rejects_ambiguous_formats(value):
    from django import forms

    form = NativeSettlementForm(events=[{"key": "a"}], index=0)
    with pytest.raises(forms.ValidationError):
        form.fields["principal"].clean(value)


def test_http_human_journey_preview_confirm_report_destination_and_replay(captured, org_client):
    url = review_url(captured)
    first = org_client.get(url)
    assert first.status_code == 200
    assert "no-store" in first["Cache-Control"]
    assert "checked" not in str(first.context["native_form"]["source_confirmed"])
    assert first.context["native_events"][0][1]["principal"].value() is None
    fields = post_fields(first)
    response = org_client.post(url, fields)
    assert response.status_code == 200
    assert response.context["native_preview"]["principal_display"] == "100,00"
    assert not ReconciliationTitleSnapshot.objects.exists()
    fields.update(
        action="confirm",
        publication_confirmed="on",
        confirmation_token=response.context["native_preview"]["confirmation_token"],
    )
    confirmed = org_client.post(url, fields)
    assert confirmed.status_code == 302
    assert "start=2026-09-01" in confirmed.url and "end=2026-09-30" in confirmed.url
    assert str(captured[0].pk) in confirmed.url
    assert org_client.post(url, fields).status_code == 302
    assert ReconciliationTitleSnapshot.objects.count() == 1


@pytest.mark.parametrize(
    "field",
    [
        "review-source_confirmed",
        "review-grouping_confirmed",
        "review-limits_confirmed",
        "event-0-interest",
        "event-0-direction",
        "event-0-reverses",
    ],
)
def test_http_explicit_decisions_required_no_default_semantics(captured, org_client, field):
    url = review_url(captured)
    fields = post_fields(org_client.get(url))
    fields.pop(field)
    assert org_client.post(url, fields).status_code == 400
    assert not ReconciliationTitleSnapshot.objects.exists()


def test_http_repeated_unknown_and_changed_confirmation_fields_fail_closed(captured, org_client):
    url = review_url(captured)
    fields = post_fields(org_client.get(url))
    fields["review-kind"] = ["payable", "receivable"]
    assert org_client.post(url, fields).status_code == 400
    fields["review-kind"] = "payable"
    fields["event-2-cash"] = "500"
    assert org_client.post(url, fields).status_code == 400
    fields.pop("event-2-cash")
    preview = org_client.post(url, fields)
    fields.update(
        action="confirm",
        publication_confirmed="on",
        confirmation_token=preview.context["native_preview"]["confirmation_token"],
    )
    fields["review-evidence_reference"] = "Alterada"
    assert org_client.post(url, fields).status_code == 409
    assert not ReconciliationTitleSnapshot.objects.exists()


def test_http_foreign_organization_role_and_capture_are_private(
    captured, org_client, other_org_client, membership
):
    url = review_url(captured)
    assert other_org_client.get(url).status_code == 404
    assert org_client.get(url.replace(str(captured[2].capture.pk), str(uuid4()))).status_code == 409
    membership.role = "auditor"
    membership.save()
    CompanyAccessGrant.objects.create(
        organization=captured[0].organization,
        membership=membership,
        company=captured[0].company,
        modules=["reconciliation"],
        is_active=True,
    )
    assert org_client.get(url).status_code == 403
    assert not ReconciliationTitleSnapshot.objects.exists()


def test_list_pagination_literal_source_escaping_and_no_write(fiscal_source, org_client):
    agent, account, _actor, job, data, _ = fiscal_source
    family = data["families"][0]
    spec = manifest()["families"]["entradas"]
    base = family["installments"][0]
    title_field = next(key for key in base if key.startswith("numero_titulo_"))
    base[title_field] = "<script>alert(1)</script>"
    for number in range(2, 27):
        added = deepcopy(base)
        added[spec["installment_field"]] = number
        family["installments"].append(added)
    family["control"]["due_installments"] = 26
    family["control"]["selected_installments"] = 26
    job.scope["expected_counts"]["entradas"]["due_installments"] = 26
    job.scope_revision = canonical_hash(job.scope)
    job.save(update_fields=["scope", "scope_revision"])
    data["scope_revision"] = job.scope_revision
    assert complete(agent, job, data).status_code == 200
    url = reverse("hub:reconciliation-native-titles", args=[account.pk])
    first = org_client.get(url)
    second = org_client.get(url, {"page": "2"})
    assert first.status_code == second.status_code == 200
    assert len(first.context["native_page"].object_list) == 25
    assert len(second.context["native_page"].object_list) == 2
    detail = org_client.get(first.context["native_page"].object_list[0]["url"])
    assert b"&lt;script&gt;alert(1)&lt;/script&gt;" in detail.content
    assert b"<script>alert(1)</script>" not in detail.content
    assert org_client.get(url + "?page=1&page=2").status_code == 400
    assert org_client.get(url, {"capture": str(uuid4())}).status_code == 400
    assert not ReconciliationTitleSnapshot.objects.exists()


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("different", [False, True])
def test_postgresql_concurrent_publication_serializes_without_losing_parcels(captured, different):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import connection, connections

    if connection.vendor != "postgresql":
        pytest.skip("Row-lock concurrency requires PostgreSQL")
    first, _ = prepare(captured)
    second = first
    if different:
        changed = deepcopy(captured[3])
        changed["decisions"][0]["settlements"][0]["normalized"].update(
            principal_cents=3500, cash_cents=3500
        )
        second, _ = prepare(captured, changed)
    barrier = Barrier(2)

    def publish(options):
        try:
            barrier.wait(timeout=10)
            snapshot, created = confirm_native_review(**options)
            return str(snapshot.pk), created
        except NativeReviewConflict:
            return "stale", False
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(publish, [first, second]))
    assert sum(created for _, created in outcomes) == 1
    if different:
        assert sum(identifier == "stale" for identifier, _ in outcomes) == 1
    else:
        assert len({identifier for identifier, _ in outcomes}) == 1
    assert ReconciliationTitleSnapshot.objects.count() == 1
    assert AuditEvent.objects.filter(action=ACTION).count() == 1
