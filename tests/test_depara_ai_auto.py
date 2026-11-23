"""D-395: DE-PARA second opinion by Claude Haiku for direct-use offices (provider mocked)."""

from __future__ import annotations

import json

import pytest
from tests.test_depara_ledger import BASE, _load, setup  # noqa: F401
from tests.test_direct_use import OCTOBER_BANK, OCTOBER_LEDGER, _october

import apps.hub.depara_ai_auto as ai
from apps.hub.models import JournalEntry, NormalizedMovement, ReconciliationRule
from apps.intelligence.models import EgressAudit

pytestmark = pytest.mark.django_db


def _fake(answers_by_word, calls):
    def post(payload):
        calls.append(payload)
        items = json.loads(payload["messages"][0]["content"])
        rows = []
        for item in items:
            code = next(
                (c for word, c in answers_by_word.items() if word in item["historico"].upper()),
                ai.NONE,
            )
            rows.append({"id": item["id"], "conta": code})
        return (
            {
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": json.dumps({"itens": rows})}],
                "usage": {"input_tokens": 900, "output_tokens": 60},
            },
            200,
            "req_test",
        )

    return post


@pytest.fixture
def ai_on(setup, settings, monkeypatch):  # noqa: F811
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(setup["org"].pk)]
    settings.CICA_DEPARA_AI_ORGANIZATION_IDS = [str(setup["org"].pk)]
    settings.CICA_CLAUDE_API_KEY = "test-key-not-real"
    monkeypatch.setattr(ai, "MIN_MEASURED", 2)  # the synthetic Razão has two unanimous patterns
    return setup


def _run(setup, monkeypatch, answers, capture):  # noqa: F811
    calls = []
    monkeypatch.setattr(ai, "_post", _fake(answers, calls))
    with capture(execute=True):
        _load(setup, BASE)
        _october(setup, OCTOBER_BANK, OCTOBER_LEDGER)
    return calls


GOOD = {"BOLETO": "4.1", "PIX": "3.1", "DEPOSITO": "3.1"}


def test_passing_measurement_activates_and_posts(
    ai_on, monkeypatch, django_capture_on_commit_callbacks
):
    calls = _run(ai_on, monkeypatch, GOOD, django_capture_on_commit_callbacks)
    assert calls and all(call["model"] == "claude-haiku-5-5" for call in calls)
    # Only codes the company books in its Razão can be answered.
    schema = calls[-1]["output_config"]["format"]["schema"]
    allowed = schema["properties"]["itens"]["items"]["properties"]["conta"]["enum"]
    assert "1.1" not in allowed and "3.1" in allowed and ai.NONE in allowed
    [rule] = ReconciliationRule.objects.filter(name__startswith=ai.RULE_PREFIX)
    assert rule.state == "active" and rule.actions["require_review"] is False
    assert (rule.actions["debit_account_code"], rule.actions["credit_account_code"]) == (
        "1.1",
        "3.1",
    )
    deposit = NormalizedMovement.objects.get(description="DEPOSITO QUALQUER")
    entry = deposit.journal_entries.get()
    assert entry.state == JournalEntry.State.APPROVED
    egress = EgressAudit.objects.filter(purpose=ai.PURPOSE)
    assert egress.count() == len(calls)
    assert all(e.call_state == "succeeded" and e.estimated_cost_cents == 1 for e in egress)


def test_each_pattern_is_asked_once(ai_on, monkeypatch, django_capture_on_commit_callbacks):
    _run(ai_on, monkeypatch, GOOD, django_capture_on_commit_callbacks)
    before = EgressAudit.objects.filter(purpose=ai.PURPOSE).count()
    from apps.hub.direct_use import run_for_account

    run_for_account(ai_on["account"])
    assert EgressAudit.objects.filter(purpose=ai.PURPOSE).count() == before


def test_failing_measurement_keeps_ai_rules_as_drafts(
    ai_on, monkeypatch, django_capture_on_commit_callbacks
):
    _run(
        ai_on,
        monkeypatch,
        {"BOLETO": "5.1", "PIX": "5.1", "DEPOSITO": "3.1"},
        django_capture_on_commit_callbacks,
    )
    [rule] = ReconciliationRule.objects.filter(name__startswith=ai.RULE_PREFIX)
    assert rule.state == "draft" and rule.actions["require_review"] is True
    deposit = NormalizedMovement.objects.get(description="DEPOSITO QUALQUER")
    assert not deposit.journal_entries.exists()


def test_spend_cap_blocks_the_call_but_not_posting(
    ai_on, settings, monkeypatch, django_capture_on_commit_callbacks
):
    settings.CICA_DEPARA_AI_DAILY_CENTS = 0
    calls = _run(ai_on, monkeypatch, GOOD, django_capture_on_commit_callbacks)
    assert calls == []
    assert not ReconciliationRule.objects.filter(name__startswith=ai.RULE_PREFIX).exists()
    # Razão-based posting (D-393) still happened.
    assert JournalEntry.objects.filter(movement__description="LIQUIDACAO BOLETO 777").exists()


def test_offices_without_authorization_never_call(
    setup,  # noqa: F811
    settings,
    monkeypatch,
    django_capture_on_commit_callbacks,
):
    settings.CICA_DIRECT_USE_ORGANIZATION_IDS = [str(setup["org"].pk)]
    settings.CICA_CLAUDE_API_KEY = "test-key-not-real"
    calls = _run(setup, monkeypatch, GOOD, django_capture_on_commit_callbacks)
    assert calls == []
    assert not EgressAudit.objects.exists()


def test_razao_contradiction_retires_the_ai_rule(
    ai_on, monkeypatch, django_capture_on_commit_callbacks
):
    _run(ai_on, monkeypatch, GOOD, django_capture_on_commit_callbacks)
    [rule] = ReconciliationRule.objects.filter(name__startswith=ai.RULE_PREFIX)
    assert rule.state == "active"
    with django_capture_on_commit_callbacks(execute=True):
        _load(ai_on, [("DEPOSITO QUALQUER", 7000, "5.1")], month="11", tag="n")
    rule.refresh_from_db()
    assert rule.state == ReconciliationRule.State.DISABLED


def test_payload_sends_no_amounts_dates_or_company(ai_on):
    payload = ai._payload(
        [{"code": "3.1", "name": "Receitas"}, {"code": "4.1", "name": "Fornecedores"}],
        [{"id": "p1", "description": "PIX 123.456.789-00 JOSE", "direction": "inflow"}],
    )
    body = json.dumps(payload, ensure_ascii=False)
    assert "123.456.789-00" not in body  # CPF masked
    assert "Empresa" not in body and "748:123" not in body
    assert payload["thinking"] == {"type": "disabled"}
    assert payload["output_config"]["effort"] == "low"
