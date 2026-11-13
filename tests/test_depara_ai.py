import hashlib
import io
import json
from unittest.mock import patch

import pytest

from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    LedgerAccount,
    ProductModule,
    ReconciliationRule,
    ReconciliationSourceFile,
)
from apps.intelligence.depara_ai import (
    depara_payload,
    depara_review_packet,
    generate_depara_ai,
    prepare_depara_ai,
    review_depara_ai,
)
from apps.intelligence.gateway import ClaudeCompletion
from apps.intelligence.models import (
    AssistantSettings,
    ClaudeFallbackApproval,
    DeparaAiBatch,
    EdgeAgent,
    EgressAudit,
    NativeLedgerCollection,
)
from apps.intelligence.native_ledger_contract import VERSION, canonical_hash, contract_hash
from apps.organizations.models import Membership
from apps.platform.models import PlatformConfiguration, TenantContract

pytestmark = pytest.mark.django_db


@pytest.fixture
def ai_batch(organization, user, membership):
    ProductModule.objects.create(organization=organization, code="reconciliation", enabled=True)
    TenantContract.objects.create(
        organization=organization, status="active", selected_modules=["reconciliation"]
    )
    company = ClientCompany.objects.create(organization=organization, name="Synthetic private name")
    account = FinancialAccount.objects.create(
        organization=organization,
        company=company,
        name="Bank",
        account_reference="private-bank-id",
        ledger_code="1",
    )
    for code in ("1", "2", "3"):
        LedgerAccount.objects.create(
            organization=organization, company=company, code=code, name=f"Conta {code}"
        )
    items = [
        {
            "reference": "private-original-key",
            "description": "Tarifa 123.456.789-01 user@example.com senha=secret",
            "direction": "outflow",
        }
    ]
    batch, created = prepare_depara_ai(
        account=account, actor=user, items=items, candidate_codes=["1", "2", "3"]
    )
    assert created
    PlatformConfiguration.objects.update_or_create(
        key="default",
        defaults={
            "cloud_fallback_enabled": True,
            "cloud_fallback_api_key": "synthetic-only",
            "cloud_fallback_model": "claude-sonnet-4-5",
            "cloud_fallback_max_request_cents": 1,
            "cloud_fallback_daily_limit_cents": 10,
            "cloud_fallback_monthly_limit_cents": 100,
        },
    )
    AssistantSettings.objects.create(
        organization=organization,
        claude_fallback_enabled=True,
        claude_allowed_roles=["owner"],
        claude_max_request_cents=1,
    )
    ClaudeFallbackApproval.objects.create(
        organization=organization,
        status="approved",
        daily_limit_cents=10,
        monthly_limit_cents=100,
        approved_by=user,
    )
    return account, user, batch, items


def generate(ai_batch, completion=None):
    _, actor, batch, _ = ai_batch
    answer = completion or ClaudeCompletion(
        json.dumps({"suggestions": [{"reference": "item_1", "debit": "2", "credit": "1"}]}),
        "claude-sonnet-4-5",
        100,
        40,
    )
    with patch(
        "apps.intelligence.depara_ai.generate_claude_fallback_completion", return_value=answer
    ) as call:
        result = generate_depara_ai(
            batch=batch, actor=actor, max_request_cents=1, allow_data_egress=True
        )
        return result, call


def test_preparation_is_reusable_and_provider_receives_only_masked_opaque_context(ai_batch):
    account, actor, batch, items = ai_batch
    repeated, created = prepare_depara_ai(
        account=account, actor=actor, items=items, candidate_codes=["3", "2", "1"]
    )
    assert not created and repeated.pk == batch.pk
    question, cards = depara_payload(batch.context)
    payload = question + json.dumps(cards)
    for secret in (
        "123.456.789-01",
        "user@example.com",
        "secret",
        "private-original-key",
        account.account_reference,
        account.company.name,
    ):
        assert secret not in payload
    assert len(question) <= 1500 and len(cards) <= 6
    assert not EgressAudit.objects.exists() and not ReconciliationRule.objects.exists()


def test_successful_call_is_reserved_once_reused_and_requires_separate_review(ai_batch):
    account, actor, _, _ = ai_batch
    batch, call = generate(ai_batch)
    assert batch.state == "succeeded" and call.call_count == 1
    assert not ReconciliationRule.objects.exists()
    assert batch.egress.call_state == "succeeded" and batch.egress.input_tokens == 100
    with patch("apps.intelligence.depara_ai.generate_claude_fallback_completion") as again:
        generate_depara_ai(batch=batch, actor=actor, max_request_cents=1)
        again.assert_not_called()
    choices = [
        {"reference": "item_1", "debit": "3", "credit": "1", "history": "Reviewed correction"}
    ]
    result = review_depara_ai(batch=batch, actor=actor, choices=choices)
    rule = ReconciliationRule.objects.get(pk=result[0].rule_id)
    assert rule.state == "draft" and rule.actions["require_review"] is True
    assert rule.actions["debit_account_code"] == "3"  # Human can correct AI.
    assert not account.company.journal_entries.exists()
    assert review_depara_ai(batch=batch, actor=actor, choices=choices)[0].status == "preserved"
    assert EgressAudit.objects.count() == 1


@pytest.mark.parametrize(
    "case", ["no_egress", "no_budget", "disabled", "revoked", "quota", "chart_changed"]
)
def test_gates_block_provider_before_any_consumption(ai_batch, case):
    account, actor, batch, _ = ai_batch
    if case == "disabled":
        AssistantSettings.objects.update(claude_fallback_enabled=False)
    if case == "revoked":
        ClaudeFallbackApproval.objects.update(status="revoked")
    if case == "quota":
        ClaudeFallbackApproval.objects.update(daily_limit_cents=0)
    if case == "chart_changed":
        LedgerAccount.objects.filter(company=account.company, code="2").update(active=False)
    with patch("apps.intelligence.depara_ai.generate_claude_fallback_completion") as call:
        with pytest.raises(ValueError):
            generate_depara_ai(
                batch=batch,
                actor=actor,
                max_request_cents=0 if case == "no_budget" else 1,
                allow_data_egress=case != "no_egress",
            )
        call.assert_not_called()
    assert not EgressAudit.objects.exists()


@pytest.mark.parametrize(
    "content",
    [
        '{"suggestions":[{"reference":"item_1","debit":"999","credit":"1"}]}',
        '{"suggestions":[{"reference":"other","debit":"2","credit":"1"}]}',
        '{"suggestions":[{"reference":"item_1","debit":"2","credit":"2"}]}',
        '{"suggestions":[],"activate":true}',
        '{"suggestions":[],"suggestions":[]}',
    ],
)
def test_untrusted_ai_output_cannot_create_or_activate_rules(ai_batch, content):
    batch, _ = generate(ai_batch, ClaudeCompletion(content, "claude-sonnet-4-5"))
    assert batch.state == "invalid"
    assert not ReconciliationRule.objects.exists()
    with pytest.raises(ValueError):
        generate_depara_ai(
            batch=batch, actor=ai_batch[1], max_request_cents=1, allow_data_egress=True
        )


def test_unknown_response_retains_quota_and_never_automatically_retries(ai_batch):
    _, actor, batch, _ = ai_batch
    with patch(
        "apps.intelligence.depara_ai.generate_claude_fallback_completion", return_value=None
    ) as call:
        assert (
            generate_depara_ai(
                batch=batch, actor=actor, max_request_cents=1, allow_data_egress=True
            ).state
            == "unknown"
        )
        with pytest.raises(ValueError):
            generate_depara_ai(
                batch=batch, actor=actor, max_request_cents=1, allow_data_egress=True
            )
        assert call.call_count == 1
    assert EgressAudit.objects.get().estimated_cost_cents == 1


def test_revoked_reviewer_cannot_see_reused_batch_or_apply_ai(ai_batch):
    _, actor, _, _ = ai_batch
    batch, _ = generate(ai_batch)
    Membership.objects.filter(user=actor).update(is_active=False)
    from django.core.exceptions import PermissionDenied

    with pytest.raises(PermissionDenied):
        generate_depara_ai(batch=batch, actor=actor, max_request_cents=1)
    assert DeparaAiBatch.objects.count() == 1 and not ReconciliationRule.objects.exists()


def test_review_packet_contains_original_context_and_editable_unactivated_choices(ai_batch):
    batch, _ = generate(ai_batch)
    packet = depara_review_packet(batch=batch, actor=ai_batch[1])
    assert packet["context"]["items"][0]["reference"] == "private-original-key"
    assert packet["choices"] == [
        {"reference": "item_1", "debit": "2", "credit": "1", "history": ""}
    ]
    assert packet["requires_human_review"] is True and not ReconciliationRule.objects.exists()


@pytest.mark.django_db(transaction=True)
def test_competing_calls_commit_reservation_once_before_provider_io(ai_batch):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Event

    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("One paid-call reservation requires independent PostgreSQL transactions.")
    _, actor, batch, _ = ai_batch
    entered, release = Event(), Event()
    result = ClaudeCompletion('{"suggestions":[]}', "claude-sonnet-4-5")

    def provider(**kwargs):
        entered.set()
        assert release.wait(15)
        return result

    def first():
        close_old_connections()
        try:
            return generate_depara_ai(
                batch=batch, actor=actor, max_request_cents=1, allow_data_egress=True
            ).state
        finally:
            close_old_connections()

    with patch(
        "apps.intelligence.depara_ai.generate_claude_fallback_completion", side_effect=provider
    ) as call:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(first)
            try:
                assert entered.wait(15)
                with pytest.raises(ValueError):
                    generate_depara_ai(
                        batch=batch, actor=actor, max_request_cents=1, allow_data_egress=True
                    )
            finally:
                release.set()
            assert pending.result(timeout=15) == "succeeded"
        assert call.call_count == 1
    assert EgressAudit.objects.count() == 1


@pytest.fixture
def native_ai_batch(ai_batch, settings, tmp_path):
    from django.core.files.base import ContentFile

    settings.MEDIA_ROOT = tmp_path
    account, actor, _, items = ai_batch
    account.company.dominio_code = "212"
    account.company.save(update_fields=["dominio_code"])
    LedgerAccount.objects.filter(company=account.company).delete()
    scope = {
        "company_code": 212,
        "chart_company_code": 212,
        "branch_code": 212,
        "bank_account_code": 1,
        "absent_account_code": 0,
        "bank_inflow_side": "debit",
        "period_start": "2026-09-01",
        "period_end_exclusive": "2026-10-01",
        "expected_source_rows": 2,
        "expected_lots": 2,
        "expected_bank_effects": 2,
    }
    snapshot = {
        "version": VERSION,
        "scope_revision": canonical_hash(scope),
        "lots": [{"lot_code": lot, "row_count": 1, "type_raw": "C"} for lot in (1, 2)],
        "records": [
            {
                "company_code": 212,
                "chart_company_code": 212,
                "branch_code": 212,
                "lot_code": 1,
                "row_code": 1,
                "occurred_on": "2026-09-03",
                "debit_account_code": 1,
                "credit_account_code": 2,
                "amount": "1.00",
                "history": None,
                "history_code_raw": None,
                "document": None,
            }
        ],
        "accounts": [
            {
                "company_code": 212,
                "account_code": code,
                "name_raw": name,
                "classification_raw": "1",
                "type_raw": "A",
                "status_raw": "I",
                "inactive_date_raw": None,
            }
            for code, name in [
                (1, "Banco privado 123"),
                (2, "Despesas bancarias"),
                (3, "Pessoa privada"),
            ]
        ],
    }
    snapshot["records"].append(
        {**snapshot["records"][0], "lot_code": 2, "row_code": 2, "credit_account_code": 3}
    )
    raw = json.dumps(snapshot).encode()
    digest = hashlib.sha256(raw).hexdigest()
    source = ReconciliationSourceFile.objects.create(
        organization=account.organization,
        company=account.company,
        financial_account=account,
        kind="json",
        origin="accounting",
        original_filename="synthetic.json",
        content_hash=digest,
        size_bytes=len(raw),
    )
    source.content.save("synthetic.json", ContentFile(raw))
    agent = EdgeAgent.objects.create(
        organization=account.organization,
        label="Synthetic",
        fingerprint="native-ai",
        shared_secret="synthetic-only",
    )
    job = NativeLedgerCollection.objects.create(
        organization=account.organization,
        agent=agent,
        financial_account=account,
        scope=scope,
        scope_revision=canonical_hash(scope),
        contract_hash=contract_hash(),
        state="imported",
        source_file=source,
        content_hash=digest,
    )
    batch, created = prepare_depara_ai(
        account=account,
        actor=actor,
        items=items,
        candidate_codes=["3", "2", "1"],
        native_collection_id=str(job.pk),
    )
    assert created
    return account, actor, batch, items, job


def test_native_catalogue_can_propose_without_approving_flags_or_posting_accounts(native_ai_batch):
    account, actor, batch, items, job = native_ai_batch
    repeated, created = prepare_depara_ai(
        account=account,
        actor=actor,
        items=items,
        candidate_codes=["1", "2", "3"],
        native_collection_id=str(job.pk),
    )
    assert not created and repeated.pk == batch.pk
    assert batch.context["catalogue_source"]["sha256"] == job.content_hash
    assert not LedgerAccount.objects.exists()
    question, cards = depara_payload(batch.context)
    sent = question + json.dumps(cards)
    assert "DESPESAS BANCARIAS" in sent and "Conta bancaria" in sent
    for private in ("Banco privado", "Pessoa privada", "123", str(job.pk), job.content_hash):
        assert private not in sent
    result, call = generate(native_ai_batch[:4])
    assert result.state == "succeeded" and call.call_count == 1
    assert not LedgerAccount.objects.exists() and not ReconciliationRule.objects.exists()
    assert depara_review_packet(batch=result, actor=actor)["requires_chart_review"] is True


def test_native_suggestions_require_separate_verified_accounts_before_rule_creation(
    native_ai_batch,
):
    account, actor, _, _, _ = native_ai_batch
    batch, _ = generate(native_ai_batch[:4])
    choices = [{"reference": "item_1", "debit": "2", "credit": "1", "history": "Reviewed"}]
    with pytest.raises(ValueError):
        review_depara_ai(batch=batch, actor=actor, choices=choices)
    assert not ReconciliationRule.objects.exists()
    for code in ("1", "2"):
        LedgerAccount.objects.create(
            organization=account.organization,
            company=account.company,
            code=code,
            name="Human approved",
            active=True,
            accepts_entries=True,
        )
    reviewed = review_depara_ai(batch=batch, actor=actor, choices=choices)
    assert ReconciliationRule.objects.get(pk=reviewed[0].rule_id).state == "draft"
    assert LedgerAccount.objects.count() == 2  # Unselected candidate 3 remains unapproved.


@pytest.mark.parametrize("failure", ["state", "hash", "scope", "source_company", "bytes"])
def test_native_catalogue_revalidates_provenance_before_paid_call(native_ai_batch, failure):
    account, actor, batch, _, job = native_ai_batch
    if failure == "state":
        NativeLedgerCollection.objects.filter(pk=job.pk).update(state="review")
    elif failure == "hash":
        NativeLedgerCollection.objects.filter(pk=job.pk).update(content_hash="0" * 64)
    elif failure == "scope":
        account.company.dominio_code = "213"
        account.company.save(update_fields=["dominio_code"])
    elif failure == "source_company":
        other = ClientCompany.objects.create(organization=account.organization, name="Other")
        ReconciliationSourceFile.objects.filter(pk=job.source_file_id).update(company=other)
    else:
        with job.source_file.content.open("wb") as stream:
            stream.write(b"{}")
    from django.core.exceptions import ObjectDoesNotExist

    with patch("apps.intelligence.depara_ai.generate_claude_fallback_completion") as call:
        with pytest.raises((ValueError, ObjectDoesNotExist)):
            generate_depara_ai(
                batch=batch, actor=actor, max_request_cents=1, allow_data_egress=True
            )
        call.assert_not_called()
    assert not EgressAudit.objects.exists()


def test_native_collection_cannot_be_borrowed_from_another_account(native_ai_batch):
    account, actor, _, items, job = native_ai_batch
    other = FinancialAccount.objects.create(
        organization=account.organization,
        company=account.company,
        name="Other",
        account_reference="other-account",
        ledger_code="1",
    )
    from django.core.exceptions import ObjectDoesNotExist

    with pytest.raises(ObjectDoesNotExist):
        prepare_depara_ai(
            account=other,
            actor=actor,
            items=items,
            candidate_codes=["1", "2"],
            native_collection_id=str(job.pk),
        )


def test_native_prepare_command_keeps_only_private_catalogue_in_batch(native_ai_batch, tmp_path):
    from django.core.management import call_command

    account, actor, batch, items, job = native_ai_batch
    source = tmp_path / "prepare.json"
    source.write_text(json.dumps({"items": items, "candidate_codes": ["1", "2", "3"]}))
    output = io.StringIO()
    call_command(
        "depara_ai",
        "--organization",
        str(account.organization_id),
        "--account",
        str(account.pk),
        "--actor",
        str(actor.pk),
        "prepare",
        input=str(source),
        native_collection=str(job.pk),
        stdout=output,
    )
    result = json.loads(output.getvalue())
    assert result["batch_id"] == str(batch.pk) and result["provider_called"] is False
    assert "Pessoa privada" not in output.getvalue()
