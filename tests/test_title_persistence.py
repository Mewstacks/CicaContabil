"""Synthetic bank/title journeys: integrity, permission, replay and shared capacity."""

from copy import deepcopy
from datetime import date
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile

from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    JournalEntry,
    NormalizedMovement,
    ProductModule,
    ReconciliationRun,
    ReconciliationSourceFile,
    ReconciliationTitleAllocation,
    ReconciliationTitleBatch,
    ReconciliationTitleDecision,
    ReconciliationTitleSnapshot,
)
from apps.hub.title_contract import TitleContractError
from apps.hub.title_persistence import (
    confirm_title_allocations,
    import_title_snapshot,
    prepare_title_allocations,
    undo_title_allocation,
)
from apps.organizations.models import Membership
from apps.platform.models import TenantContract

pytestmark = pytest.mark.django_db
START, END = date(2026, 9, 1), date(2026, 9, 30)


def encoded(payload):
    import json

    return json.dumps(payload, ensure_ascii=False).encode()


@pytest.fixture
def context(organization, user, membership, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"]
    )
    company = ClientCompany.objects.create(organization=organization, name="Empresa sintética")
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Banco sintético",
        account_reference="SYN-1",
    )
    payload = {
        "contract": "titles-normalized-v1",
        "company_key": str(company.pk),
        "account_reference": account.account_reference,
        "as_of": "2026-09-30",
        "settlements_complete": True,
        "titles": [
            {
                "key": "T-1",
                "kind": "payable",
                "installments": [
                    {
                        "key": "01",
                        "due_on": "2026-10-01",
                        "principal_cents": 10000,
                        "outstanding_cents": 4000,
                        "settlements": [
                            {
                                "key": "P-1",
                                "posted_on": "2026-09-12",
                                "principal_cents": 6000,
                                "interest_cents": 150,
                                "penalty_cents": 50,
                                "fees_cents": 25,
                                "discount_cents": 100,
                                "cash_cents": 6125,
                                "direction": "outflow",
                                "reverses": None,
                            }
                        ],
                    }
                ],
            }
        ],
    }
    return account, user, payload


def bank(account, *, key=None, cents=-6125, day=date(2026, 9, 12), kind="ofx"):
    import hashlib

    content = f"SYNTHETIC {uuid4()}".encode()
    source = ReconciliationSourceFile.objects.create(
        organization=account.organization,
        company=account.company,
        financial_account=account,
        kind=kind,
        origin="bank_statement",
        original_filename="sintetico.ofx",
        content_hash=hashlib.sha256(content).hexdigest(),
        size_bytes=len(content),
    )
    source.content.save(source.original_filename, ContentFile(content))
    run = ReconciliationRun.objects.create(
        organization=account.organization, source_file=source, state="completed"
    )
    return NormalizedMovement.objects.create(
        organization=account.organization,
        company=account.company,
        financial_account=account,
        source_file=source,
        run=run,
        source_key=key or f"ofx:{uuid4()}",
        occurred_on=day,
        amount_cents=cents,
        direction="inflow" if cents > 0 else "outflow",
        original_description="Movimento sintético",
        review_state="pending",
    )


def imported(context, payload=None):
    account, actor, original = context
    snapshot, _created = import_title_snapshot(
        financial_account=account,
        content=encoded(payload or original),
        actor=actor,
        evidence_reference="Exemplos sintéticos revisados",
    )
    return snapshot


def request(movement, *, cents=6125, title="T-1", settlement="P-1"):
    return {
        "movement_key": str(movement.pk),
        "title_key": title,
        "installment_key": "01",
        "settlement_key": settlement,
        "cash_cents": cents,
    }


def prepared(snapshot, requests, actor):
    return prepare_title_allocations(
        snapshot=snapshot, requests=requests, actor=actor, period_start=START, period_end=END
    )


def confirmed(snapshot, requests, actor, **overrides):
    plan = prepared(snapshot, requests, actor)
    options = dict(
        snapshot=snapshot,
        requests=requests,
        actor=actor,
        period_start=START,
        period_end=END,
        request_id=uuid4(),
        preview_fingerprint=plan.fingerprint,
        evidence_reference="Conferência sintética",
    )
    return confirm_title_allocations(**(options | overrides))


def test_import_replay_keeps_original_and_immutable_normalized_evidence(context):
    account, actor, payload = context
    first = imported(context)
    duplicate, created = import_title_snapshot(
        financial_account=account,
        actor=actor,
        content=encoded(payload),
        evidence_reference="Replay sintético",
    )
    assert not created and duplicate.pk == first.pk
    assert (
        ReconciliationTitleSnapshot.objects.count() == ReconciliationSourceFile.objects.count() == 1
    )
    with first.source_file.content.open("rb") as stream:
        assert stream.read() == encoded(payload)
    first.evidence_reference = "Alteração indevida"
    with pytest.raises(ValidationError):
        first.save()
    with pytest.raises(ValidationError):
        ReconciliationTitleSnapshot.objects.all().update(evidence_reference="não permitido")


def test_confirm_undo_and_reconfirm_preserve_receipts_without_posting(context):
    account, actor, _ = context
    snapshot = imported(context)
    movement = bank(account)
    rows = [request(movement)]
    plan = prepared(snapshot, rows, actor)
    request_id = uuid4()
    options = dict(
        snapshot=snapshot,
        requests=rows,
        actor=actor,
        period_start=START,
        period_end=END,
        request_id=request_id,
        preview_fingerprint=plan.fingerprint,
        evidence_reference="Conferência sintética",
    )
    batch, created = confirm_title_allocations(**options)
    replay, created_again = confirm_title_allocations(**options)
    assert created and not created_again and batch.pk == replay.pk
    allocation = batch.allocations.get()
    assert allocation.cash_cents == 6125
    assert ReconciliationTitleDecision.objects.count() == 1
    assert not JournalEntry.objects.exists()
    assert undo_title_allocation(allocation=allocation, actor=actor, reason="Revisão sintética")
    assert not undo_title_allocation(allocation=allocation, actor=actor, reason="Replay")
    assert list(allocation.decisions.order_by("created_at").values_list("state", flat=True)) == [
        "confirmed",
        "undone",
    ]
    second, created = confirmed(snapshot, rows, actor)
    assert created and second.pk != batch.pk
    assert ReconciliationTitleAllocation.objects.filter(state="confirmed").count() == 1
    assert ReconciliationTitleDecision.objects.count() == 3


def test_same_idempotency_key_rejects_changed_request(context):
    account, actor, _ = context
    snapshot = imported(context)
    rows = [request(bank(account), cents=3000)]
    plan = prepared(snapshot, rows, actor)
    options = dict(
        snapshot=snapshot,
        requests=rows,
        actor=actor,
        period_start=START,
        period_end=END,
        request_id=uuid4(),
        preview_fingerprint=plan.fingerprint,
        evidence_reference="Conferência",
    )
    confirm_title_allocations(**options)
    with pytest.raises(TitleContractError, match="reenvio"):
        confirm_title_allocations(**(options | {"requests": [{**rows[0], "cash_cents": 2000}]}))
    assert ReconciliationTitleBatch.objects.count() == 1


def test_two_previews_cannot_overallocate_same_settlement(context):
    account, actor, _ = context
    snapshot = imported(context)
    rows = [request(bank(account), cents=4000)]
    competing = [request(bank(account), cents=4000)]
    competing_plan = prepared(snapshot, competing, actor)
    confirmed(snapshot, rows, actor)
    with pytest.raises(TitleContractError, match="Capacidade"):
        confirm_title_allocations(
            snapshot=snapshot,
            requests=competing,
            actor=actor,
            period_start=START,
            period_end=END,
            request_id=uuid4(),
            preview_fingerprint=competing_plan.fingerprint,
            evidence_reference="Revisão concorrente",
        )
    assert ReconciliationTitleAllocation.objects.count() == 1


def test_bank_capacity_is_shared_across_different_titles(context):
    account, actor, payload = context
    other = deepcopy(payload["titles"][0])
    other["key"] = "T-2"
    payload["titles"].append(other)
    snapshot = imported(context)
    movement = bank(account)
    confirmed(snapshot, [request(movement, cents=4000)], actor)
    with pytest.raises(TitleContractError, match="Capacidade"):
        prepared(snapshot, [request(movement, cents=4000, title="T-2")], actor)


def test_overlapping_ofx_files_share_a_bank_fact_capacity(context):
    account, actor, payload = context
    other = deepcopy(payload["titles"][0])
    other["key"] = "T-2"
    payload["titles"].append(other)
    snapshot = imported(context)
    first, duplicate = bank(account, key="ofx:SAME"), bank(account, key="ofx:SAME")
    confirmed(snapshot, [request(first, cents=4000)], actor)
    with pytest.raises(TitleContractError, match="Capacidade"):
        prepared(snapshot, [request(duplicate, cents=4000, title="T-2")], actor)
    with pytest.raises(TitleContractError, match="repetido"):
        prepared(snapshot, [request(first, cents=1000), request(duplicate, cents=1000)], actor)


def test_capacity_survives_a_new_snapshot_and_rejects_old_previews(context):
    account, actor, payload = context
    first = imported(context)
    movement = bank(account)
    rows = [request(movement, cents=4000)]
    old_plan = prepared(first, rows, actor)
    confirmed(first, rows, actor)
    newer = deepcopy(payload)
    newer["as_of"] = "2026-10-01"
    second = imported(context, newer)
    with pytest.raises(TitleContractError, match="recente"):
        confirmed(first, rows, actor, preview_fingerprint=old_plan.fingerprint)
    with pytest.raises(TitleContractError, match="Capacidade"):
        prepared(second, rows, actor)
    remaining, _ = confirmed(second, [request(movement, cents=2125)], actor)
    assert remaining.allocations.get().cash_cents == 2125


def test_changed_settlement_requires_explicit_undo_before_new_allocation(context):
    account, actor, payload = context
    first = imported(context)
    confirmed(first, [request(bank(account), cents=3000)], actor)
    changed = deepcopy(payload)
    changed["titles"][0]["installments"][0]["settlements"][0]["posted_on"] = "2026-09-13"
    second = imported(context, changed)
    with pytest.raises(TitleContractError, match="Baixa já alocada mudou"):
        prepared(second, [request(bank(account), cents=2000)], actor)


def test_preview_is_invalidated_by_changed_bank_facts(context):
    account, actor, _ = context
    snapshot = imported(context)
    movement = bank(account)
    rows = [request(movement, cents=3000)]
    plan = prepared(snapshot, rows, actor)
    movement.original_description = "Descrição alterada após revisão"
    movement.save()
    with pytest.raises(TitleContractError, match="prévia mudou"):
        confirm_title_allocations(
            snapshot=snapshot,
            requests=rows,
            actor=actor,
            period_start=START,
            period_end=END,
            request_id=uuid4(),
            preview_fingerprint=plan.fingerprint,
            evidence_reference="Conferido",
        )
    assert not ReconciliationTitleBatch.objects.exists()


def test_date_difference_requires_a_separate_explicit_decision(context):
    account, actor, _ = context
    snapshot = imported(context)
    rows = [request(bank(account, day=date(2026, 9, 13)))]
    assert prepared(snapshot, rows, actor).preview.allocations[0].date_difference
    with pytest.raises(TitleContractError, match="diferenças de data"):
        confirmed(snapshot, rows, actor)
    batch, _ = confirmed(snapshot, rows, actor, accept_date_differences=True)
    assert batch.accepted_date_differences


@pytest.mark.parametrize("role", [Membership.Role.AUDITOR, Membership.Role.BILLING])
def test_consultative_role_cannot_import_or_confirm(context, membership, role):
    account, actor, payload = context
    snapshot = imported(context)
    rows = [request(bank(account))]
    plan = prepared(snapshot, rows, actor)
    membership.role = role
    membership.save()
    with pytest.raises(PermissionDenied):
        import_title_snapshot(
            financial_account=account,
            content=encoded(payload),
            actor=actor,
            evidence_reference="Revisão",
        )
    with pytest.raises(PermissionDenied):
        confirm_title_allocations(
            snapshot=snapshot,
            requests=rows,
            actor=actor,
            period_start=START,
            period_end=END,
            request_id=uuid4(),
            preview_fingerprint=plan.fingerprint,
            evidence_reference="Revisão",
        )


def test_revocation_between_preview_and_confirmation_blocks_write(context, membership):
    account, actor, _ = context
    snapshot = imported(context)
    rows = [request(bank(account))]
    plan = prepared(snapshot, rows, actor)
    membership.is_active = False
    membership.save()
    with pytest.raises(PermissionDenied):
        confirm_title_allocations(
            snapshot=snapshot,
            requests=rows,
            actor=actor,
            period_start=START,
            period_end=END,
            request_id=uuid4(),
            preview_fingerprint=plan.fingerprint,
            evidence_reference="Revisão",
        )
    assert not ReconciliationTitleBatch.objects.exists()


def test_suspended_contract_blocks_import(context):
    account, actor, payload = context
    TenantContract.objects.filter(organization=account.organization).update(status="suspended")
    with pytest.raises(ValueError, match="contrato"):
        import_title_snapshot(
            financial_account=account,
            content=encoded(payload),
            actor=actor,
            evidence_reference="Revisão",
        )


def test_cross_company_movement_is_rejected(context):
    account, actor, _ = context
    other = ClientCompany.objects.create(organization=account.organization, name="Outra sintética")
    second = FinancialAccount.objects.create(
        organization=account.organization,
        company=other,
        name="Outro banco",
        account_reference="SYN-2",
    )
    with pytest.raises(TitleContractError, match="fora da empresa"):
        prepared(imported(context), [request(bank(second))], actor)


@pytest.mark.parametrize("field,value", [("company_key", "other"), ("account_reference", "other")])
def test_import_rejects_source_scope_before_creating_files(context, field, value):
    account, actor, payload = context
    payload[field] = value
    with pytest.raises(TitleContractError):
        import_title_snapshot(
            financial_account=account,
            content=encoded(payload),
            actor=actor,
            evidence_reference="Revisão",
        )
    assert not ReconciliationSourceFile.objects.exists()


def test_tampered_private_source_blocks_preview(context):
    account, actor, _ = context
    snapshot = imported(context)
    with snapshot.source_file.content.open("wb") as stream:
        stream.write(b"tampered")
    with pytest.raises(TitleContractError, match="Hash"):
        prepared(snapshot, [request(bank(account))], actor)


def test_source_write_is_rolled_back_and_private_file_removed_on_audit_failure(context, tmp_path):
    account, actor, payload = context
    with (
        patch("apps.hub.title_persistence.record_event", side_effect=RuntimeError("synthetic")),
        pytest.raises(RuntimeError),
    ):
        import_title_snapshot(
            financial_account=account,
            content=encoded(payload),
            actor=actor,
            evidence_reference="Revisão",
        )
    assert not ReconciliationTitleSnapshot.objects.exists()
    assert not ReconciliationSourceFile.objects.exists()
    assert not list(tmp_path.rglob("*.json"))


def test_batch_and_decisions_roll_back_together_after_partial_write(context):
    account, actor, _ = context
    snapshot = imported(context)
    rows = [request(bank(account))]
    with (
        patch("apps.hub.title_persistence.record_event", side_effect=RuntimeError("synthetic")),
        pytest.raises(RuntimeError),
    ):
        confirmed(snapshot, rows, actor)
    assert not ReconciliationTitleBatch.objects.exists()
    assert not ReconciliationTitleAllocation.objects.exists()
    assert not ReconciliationTitleDecision.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_postgresql_competing_confirmations_share_one_settlement_capacity(context):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connection, connections

    if connection.vendor != "postgresql":
        pytest.skip("Requires independent PostgreSQL transactions and row locks")
    account, actor, _ = context
    snapshot = imported(context)
    rows = [[request(bank(account), cents=4000)] for _ in range(2)]
    plans = [prepared(snapshot, row, actor) for row in rows]
    barrier = Barrier(2)

    def confirm(index):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            try:
                confirm_title_allocations(
                    snapshot=snapshot,
                    requests=rows[index],
                    actor=actor,
                    period_start=START,
                    period_end=END,
                    request_id=uuid4(),
                    preview_fingerprint=plans[index].fingerprint,
                    evidence_reference="Concorrência sintética",
                )
                return "confirmed"
            except TitleContractError:
                return "blocked"
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(confirm, range(2)))
    assert sorted(results) == ["blocked", "confirmed"]
    assert list(ReconciliationTitleAllocation.objects.values_list("cash_cents", flat=True)) == [
        4000
    ]
    assert (
        ReconciliationTitleBatch.objects.count() == ReconciliationTitleDecision.objects.count() == 1
    )


def test_operator_command_import_preview_confirm_replay_and_undo(context, tmp_path):
    import io
    import json
    import stat

    from django.core.management import call_command

    account, actor, payload = context
    input_file = tmp_path / "titles.json"
    input_file.write_bytes(encoded(payload))
    base = [
        "--organization",
        str(account.organization_id),
        "--account",
        str(account.pk),
        "--actor",
        str(actor.pk),
    ]

    def run(*args):
        output = io.StringIO()
        call_command("reconcile_titles", *base, *args, stdout=output)
        return json.loads(output.getvalue())

    receipt = run("import", "--input", str(input_file), "--evidence", "Exemplos sintéticos")
    requests = tmp_path / "requests.json"
    requests.write_bytes(encoded([request(bank(account))]))
    plan_file = tmp_path / "reviewed-plan.json"
    preview = run(
        "preview",
        "--snapshot",
        receipt["snapshot_id"],
        "--requests",
        str(requests),
        "--start",
        "2026-09-01",
        "--end",
        "2026-09-30",
        "--output",
        str(plan_file),
    )
    assert preview["requires_human_review"]
    assert stat.S_IMODE(plan_file.stat().st_mode) == 0o600
    plan = json.loads(plan_file.read_text())
    assert plan["review"]["allocations"][0]["cash_cents"] == 6125
    request_id = str(uuid4())
    confirmation = run(
        "confirm", "--plan", str(plan_file), "--request-id", request_id, "--evidence", "Conferido"
    )
    assert confirmation["created"] and confirmation["erp_written"] is False
    assert not run(
        "confirm", "--plan", str(plan_file), "--request-id", request_id, "--evidence", "Conferido"
    )["created"]
    allocation = ReconciliationTitleAllocation.objects.get()
    assert run("undo", "--allocation", str(allocation.pk), "--reason", "Revisão")["changed"]


def test_operator_command_rejects_changed_human_review_document(context, tmp_path):
    import io
    import json

    from django.core.management import call_command
    from django.core.management.base import CommandError

    account, actor, _ = context
    snapshot = imported(context)
    requests = tmp_path / "requests.json"
    requests.write_bytes(encoded([request(bank(account))]))
    target = tmp_path / "plan.json"
    base = [
        "--organization",
        str(account.organization_id),
        "--account",
        str(account.pk),
        "--actor",
        str(actor.pk),
    ]
    call_command(
        "reconcile_titles",
        *base,
        "preview",
        "--snapshot",
        str(snapshot.pk),
        "--requests",
        str(requests),
        "--start",
        "2026-09-01",
        "--end",
        "2026-09-30",
        "--output",
        str(target),
        stdout=io.StringIO(),
    )
    payload = json.loads(target.read_text())
    payload["review"]["allocations"][0]["cash_cents"] = 1
    target.write_bytes(encoded(payload))
    with pytest.raises(CommandError, match="conferência do arquivo mudou"):
        call_command(
            "reconcile_titles",
            *base,
            "confirm",
            "--plan",
            str(target),
            "--request-id",
            str(uuid4()),
            "--evidence",
            "Conferido",
            stdout=io.StringIO(),
        )
    assert not ReconciliationTitleBatch.objects.exists()


def test_partial_payment_and_its_reversal_keep_separate_gross_cash_events(context):
    account, actor, payload = context
    part = payload["titles"][0]["installments"][0]
    original = part["settlements"][0]
    part["settlements"].append(
        {
            **original,
            "key": "R-1",
            "posted_on": "2026-09-13",
            "direction": "inflow",
            "reverses": "P-1",
        }
    )
    part["outstanding_cents"] = 10000
    snapshot = imported(context)
    rows = [
        request(bank(account)),
        request(bank(account, cents=6125, day=date(2026, 9, 13)), settlement="R-1"),
    ]
    batch, _ = confirmed(snapshot, rows, actor)
    assert batch.allocations.count() == 2
    assert sum(batch.allocations.values_list("cash_cents", flat=True)) == 12250
    assert len(batch.review_snapshot["settlements"]) == 2
    assert not JournalEntry.objects.exists()


def test_missing_settlements_are_never_inferred_from_due_date_or_bank_amount(context):
    account, actor, payload = context
    part = payload["titles"][0]["installments"][0]
    part["settlements"] = []
    part["outstanding_cents"] = None
    payload["settlements_complete"] = False
    snapshot = imported(context)
    assert snapshot.settlements_complete is False
    with pytest.raises(TitleContractError, match="fora do recorte"):
        prepared(snapshot, [request(bank(account))], actor)
    assert not ReconciliationTitleAllocation.objects.exists()


def test_tampered_bank_source_cannot_be_confirmed(context):
    account, actor, _ = context
    snapshot = imported(context)
    movement = bank(account)
    rows = [request(movement)]
    plan = prepared(snapshot, rows, actor)
    with movement.source_file.content.open("wb") as stream:
        stream.write(b"tampered")
    with pytest.raises(TitleContractError, match="fonte bancária"):
        confirm_title_allocations(
            snapshot=snapshot,
            requests=rows,
            actor=actor,
            period_start=START,
            period_end=END,
            request_id=uuid4(),
            preview_fingerprint=plan.fingerprint,
            evidence_reference="Conferido",
        )
    assert not ReconciliationTitleBatch.objects.exists()


def test_operator_portfolio_grant_is_revalidated_at_confirmation(context, membership):
    from apps.hub.models import CompanyAccessGrant

    account, actor, _ = context
    snapshot = imported(context)
    membership.role = Membership.Role.OPERATOR
    membership.save()
    grant = CompanyAccessGrant.objects.create(
        organization=account.organization,
        membership=membership,
        company=account.company,
        modules=["reconciliation"],
        is_active=True,
    )
    rows = [request(bank(account))]
    plan = prepared(snapshot, rows, actor)
    grant.is_active = False
    grant.save()
    with pytest.raises(PermissionDenied):
        confirm_title_allocations(
            snapshot=snapshot,
            requests=rows,
            actor=actor,
            period_start=START,
            period_end=END,
            request_id=uuid4(),
            preview_fingerprint=plan.fingerprint,
            evidence_reference="Conferido",
        )
    assert not ReconciliationTitleBatch.objects.exists()
