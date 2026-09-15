from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.hub.models import OfficeProfile, ProductModule
from apps.intelligence.models import Conversation, Message
from apps.intelligence.services import answer_question
from apps.organizations.models import Membership
from apps.platform.billing import BillingError, reserve_usage
from apps.platform.models import (
    Plan,
    PlanServiceRate,
    PlatformConfiguration,
    TenantContract,
    UsageMeter,
)
from apps.platform.operation_access import require_operation_access

pytestmark = pytest.mark.django_db(databases={"default", "knowledge"})


@pytest.fixture
def trial(organization):
    PlatformConfiguration.objects.update_or_create(
        key="default", defaults={"copilot_available_for_offices": True}
    )
    plan = Plan.objects.create(code="operation-ai", name="Operation AI")
    PlanServiceRate.objects.create(plan=plan, action_code="ai.answer", included_units=1)
    OfficeProfile.objects.create(organization=organization, trial_started_at=timezone.now())
    ProductModule.objects.create(organization=organization, code="ai", enabled=True)
    return TenantContract.objects.create(
        organization=organization,
        plan=plan,
        status="trial",
        starts_on=timezone.localdate(),
        trial_ends_on=timezone.localdate() + timedelta(days=14),
        selected_modules=["ai"],
    )


def test_trial_and_paid_contract_allow_enabled_module(organization, trial):
    require_operation_access(organization, "ai")


def test_operation_access_uses_the_contract_module_snapshot(organization, trial):
    plan = trial.plan
    assert plan is not None
    plan.modules = ["journey"]
    plan.save(update_fields=["modules", "updated_at"])

    require_operation_access(organization, "ai")


def test_ai_trial_quota_blocks_before_second_model_call(user, organization, trial):
    Membership.objects.create(organization=organization, user=user, role="owner")
    with patch("apps.intelligence.services.generate_local_completion", return_value=None) as local:
        answer_question(
            organization=organization,
            actor=user,
            company=None,
            question="First",
            request=None,
        )
        with pytest.raises(ValueError, match="franquia"):
            answer_question(
                organization=organization,
                actor=user,
                company=None,
                question="Second",
                request=None,
            )
    assert local.call_count == 1
    meter = UsageMeter.objects.get(organization=organization, action_code="ai.answer")
    assert meter.consumed_units == 1
    assert meter.reserved_units == 0
    assert Message.objects.filter(organization=organization).count() == 2


def test_grace_contract_cannot_reserve_new_usage_directly(organization, trial):
    trial.status = "grace"
    trial.save()
    with pytest.raises(BillingError, match="contrato vigente"):
        reserve_usage(
            organization=organization,
            action_code="ai.answer",
            idempotency_key="grace-direct-attempt",
        )
    trial.status = "active"
    trial.save()
    require_operation_access(organization, "ai")


@pytest.mark.parametrize(
    "reason",
    ["missing", "suspended", "grace", "archived", "draft", "expired", "disabled", "uncontracted"],
)
def test_ai_stops_before_model_or_writes(user, organization, trial, reason):
    Membership.objects.create(organization=organization, user=user, role="owner")
    if reason == "missing":
        trial.delete()
    elif reason in {"suspended", "grace", "archived", "draft"}:
        trial.status = reason
        trial.save()
    elif reason == "expired":
        OfficeProfile.objects.filter(organization=organization).update(
            trial_started_at=timezone.now() - timedelta(days=14)
        )
    elif reason == "disabled":
        ProductModule.objects.filter(organization=organization).update(enabled=False)
    elif reason == "uncontracted":
        trial.selected_modules = ["journey"]
        trial.save()
    with (
        patch("apps.intelligence.services.generate_local_completion") as local,
        patch("apps.intelligence.services.generate_claude_fallback_completion") as cloud,
        pytest.raises(ValueError),
    ):
        answer_question(
            organization=organization, actor=user, company=None, question="Test", request=None
        )
    local.assert_not_called()
    cloud.assert_not_called()
    assert not Conversation.objects.exists()
