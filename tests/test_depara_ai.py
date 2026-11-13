import json
from unittest.mock import patch

import pytest

from apps.hub.models import (
    ClientCompany,
    FinancialAccount,
    LedgerAccount,
    ProductModule,
    ReconciliationRule,
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
    EgressAudit,
)
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
