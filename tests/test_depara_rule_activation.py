"""Activation is a fresh human operation, with current references and atomic audit."""

from copy import deepcopy
from unittest.mock import patch

import pytest
from django.core.exceptions import PermissionDenied
from django.urls import reverse

from apps.audit.models import AuditEvent
from apps.hub.depara_rule_activation import RuleActivationConflict, set_reconciliation_rule_state
from apps.hub.models import CompanyAccessGrant, LedgerAccount, ReconciliationRule
from test_depara_review_ui import case as case_fixture
from test_depara_review_ui import data, url

case = case_fixture
pytestmark = pytest.mark.django_db


def draft(case):
    assert case["client"].post(url(case), data(case)).status_code == 200
    return ReconciliationRule.objects.get()


def activate(case, rule, **extra):
    return case["client"].post(reverse("hub:reconciliation-configuration"), {
        "action": "toggle_rule", "company": str(case["account"].company_id),
        "rule_id": str(rule.pk), "expected_rule_state": rule.state, **extra,
    })


def test_activation_and_deactivation_are_explicit_and_stale_click_does_not_invert(case):
    rule = draft(case)
    before = AuditEvent.objects.count()
    assert activate(case, rule).status_code == 302
    assert activate(case, rule).status_code == 409
    rule.refresh_from_db()
    assert rule.state == "active"
    assert AuditEvent.objects.count() == before + 1
    assert activate(case, rule).status_code == 302
    rule.refresh_from_db()
    assert rule.state == "disabled"
    assert AuditEvent.objects.count() == before + 2


@pytest.mark.parametrize("change", ["inactive", "synthetic", "missing", "foreign"])
def test_activation_rechecks_current_scoped_analytic_accounts(case, change):
    rule = draft(case)
    query = LedgerAccount.objects.filter(company=rule.company, code="2000")
    if change == "inactive":
        query.update(active=False)
    elif change == "synthetic":
        query.update(accepts_entries=False)
    else:
        query.delete()
        if change == "foreign":
            from apps.hub.models import ClientCompany

            other = ClientCompany.objects.create(
                organization=case["organization"], name="Empresa restrita fictícia",
            )
            LedgerAccount.objects.create(
                organization=case["organization"], company=other, code="2000", name="Outra conta",
            )
    assert activate(case, rule).status_code == 400
    rule.refresh_from_db()
    assert rule.state == "draft"


def test_deactivation_remains_possible_when_legacy_references_are_missing(case):
    rule = draft(case)
    ReconciliationRule.objects.filter(pk=rule.pk).update(state="active", actions={"legacy": 1})
    LedgerAccount.objects.filter(company=rule.company).delete()
    rule.refresh_from_db()
    assert activate(case, rule).status_code == 302
    rule.refresh_from_db()
    assert rule.state == "disabled"


def test_audit_failure_rolls_back_rule_state(case):
    rule = draft(case)
    before = AuditEvent.objects.count()
    with (
        patch(
            "apps.hub.depara_rule_activation.record_event", side_effect=RuntimeError("synthetic"),
        ),
        pytest.raises(RuntimeError, match="synthetic"),
    ):
        activate(case, rule)
    rule.refresh_from_db()
    assert rule.state == "draft" and AuditEvent.objects.count() == before


def test_service_rechecks_revocation_after_view_context_was_built(case):
    rule = draft(case)
    original = set_reconciliation_rule_state

    def revoke(**kwargs):
        case["membership"].is_active = False
        case["membership"].save()
        return original(**kwargs)

    with patch("apps.hub.depara_rule_activation.set_reconciliation_rule_state", side_effect=revoke):
        assert activate(case, rule).status_code == 403
    rule.refresh_from_db()
    assert rule.state == "draft"


def test_service_requires_module_grant_for_the_same_company(case):
    rule = draft(case)
    case["membership"].role = "operator"
    case["membership"].save()
    CompanyAccessGrant.objects.create(
        organization=case["organization"], membership=case["membership"],
        company=rule.company, modules=["payroll"],
    )
    with pytest.raises(PermissionDenied):
        set_reconciliation_rule_state(rule=rule, actor=case["user"], expected_state="draft")
    rule.refresh_from_db()
    assert rule.state == "draft"


@pytest.mark.parametrize("actions", [
    {"debit_account_code": 2000}, {"require_review": "false"}, {"ignore": []},
    {"script": "invalid"}, {}, {"debit_account_code": "1000", "credit_account_code": "1000"},
])
def test_untyped_or_invalid_actions_cannot_be_activated(case, actions):
    rule = draft(case)
    ReconciliationRule.objects.filter(pk=rule.pk).update(actions=actions)
    assert activate(case, rule).status_code == 400
    rule.refresh_from_db()
    assert rule.state == "draft"


def test_invalid_conditions_cannot_be_promoted_to_match_everything(case):
    rule = draft(case)
    ReconciliationRule.objects.filter(pk=rule.pk).update(all_conditions=["invalid"])
    assert activate(case, rule).status_code == 400
    rule.refresh_from_db()
    assert rule.state == "draft"


def test_new_active_conflict_is_checked_at_activation(case):
    rule = draft(case)
    ReconciliationRule.objects.create(
        organization=rule.organization, company=rule.company,
        name="Decisão humana posterior", state="active", all_conditions=rule.all_conditions,
        any_conditions=rule.any_conditions,
        actions={**deepcopy(rule.actions), "debit_account_code": "3000"},
        created_by=case["user"],
    )
    response = activate(case, rule)
    assert response.status_code == 400
    assert "conflitante" in response.content.decode()
    rule.refresh_from_db()
    assert rule.state == "draft"


def test_state_field_is_required_and_duplicate_is_rejected(case):
    rule = draft(case)
    assert activate(case, rule, expected_rule_state=["draft", "active"]).status_code == 403
    assert activate(case, rule, expected_rule_state="").status_code == 409
    rule.refresh_from_db()
    assert rule.state == "draft"


@pytest.mark.django_db(transaction=True)
def test_competing_activation_preserves_first_decision(case):
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    from django.db import close_old_connections, connection

    if connection.vendor != "postgresql":
        pytest.skip("Activation requires independent PostgreSQL row locks.")
    rule = draft(case)
    barrier = Barrier(2)

    def toggle():
        close_old_connections()
        try:
            barrier.wait(timeout=15)
            try:
                return set_reconciliation_rule_state(
                    rule=rule, actor=case["user"], expected_state="draft",
                ).state
            except RuleActivationConflict:
                return "conflict"
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(lambda _: toggle(), range(2))) == ["active", "conflict"]
    rule.refresh_from_db()
    assert rule.state == "active"
