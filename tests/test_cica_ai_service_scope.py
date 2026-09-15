from datetime import timedelta
from unittest.mock import patch

import pytest
from django.utils import timezone

from apps.hub.models import ClientCompany, OfficeProfile, ProductModule
from apps.intelligence.models import Conversation, Message
from apps.intelligence.services import answer_question
from apps.organizations.models import Membership, Organization
from apps.platform.models import Plan, PlanServiceRate, TenantContract

pytestmark = pytest.mark.django_db


@pytest.mark.parametrize(
    "denial",
    [
        "missing_membership",
        "inactive_membership",
        "other_company",
        "inactive_user",
        "inactive_office",
    ],
)
def test_ai_service_rejects_scope_before_any_model_or_message(user, organization, denial):
    plan = Plan.objects.create(code="scope-ai", name="AI scope")
    PlanServiceRate.objects.create(plan=plan, action_code="ai.answer", included_units=10)
    OfficeProfile.objects.create(organization=organization, trial_started_at=timezone.now())
    ProductModule.objects.create(organization=organization, code="ai", enabled=True)
    TenantContract.objects.create(
        organization=organization,
        plan=plan,
        status="trial",
        starts_on=timezone.localdate(),
        trial_ends_on=timezone.localdate() + timedelta(days=14),
        selected_modules=["ai"],
    )
    if denial != "missing_membership":
        Membership.objects.create(
            user=user,
            organization=organization,
            role="owner",
            is_active=denial != "inactive_membership",
        )
    company = ClientCompany.objects.create(organization=organization, name="Authorized")
    if denial == "other_company":
        other = Organization.objects.create(name="Other", slug="other-ai-scope")
        company = ClientCompany.objects.create(organization=other, name="Private")
    if denial == "inactive_user":
        user.is_active = False
        user.save()
    if denial == "inactive_office":
        organization.is_active = False
        organization.save()
    with (
        patch("apps.intelligence.services.generate_local_completion") as local,
        patch("apps.intelligence.services.generate_claude_fallback_completion") as cloud,
        pytest.raises(ValueError),
    ):
        answer_question(
            organization=organization,
            actor=user,
            company=company,
            question="Confidential",
            request=None,
        )
    local.assert_not_called()
    cloud.assert_not_called()
    assert not Conversation.objects.exists()
    assert not Message.objects.exists()
