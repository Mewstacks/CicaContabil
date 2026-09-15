from datetime import timedelta

import pytest
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.platform.models import (
    Entitlement,
    FeatureFlag,
    Plan,
    PlatformAccess,
    TenantContract,
    TenantLifecycle,
)
from apps.platform.services import (
    LifecycleTransitionError,
    allowed_lifecycle_targets,
    flag_enabled,
    has_entitlement,
    has_platform_role,
    platform_role,
    support_access_mode,
    transition_lifecycle,
)

pytestmark = pytest.mark.django_db


def test_platform_roles_and_support_mode(settings) -> None:
    user = User.objects.create_user("developer-services@example.test", "safe-password-123")
    PlatformAccess.objects.create(user=user, role=PlatformAccess.Role.DEVELOPER)

    assert platform_role(AnonymousUser()) is None
    assert platform_role(user) == PlatformAccess.Role.DEVELOPER
    assert has_platform_role(user, PlatformAccess.Role.DEVELOPER)
    assert not has_platform_role(user, PlatformAccess.Role.COMMERCIAL)
    settings.PLATFORM_DEVELOPER_FULL_ACCESS = False
    assert support_access_mode(user) == "read_only"
    settings.PLATFORM_DEVELOPER_FULL_ACCESS = True
    assert support_access_mode(user) == "full"


def test_entitlements_and_flags_respect_expiry() -> None:
    office = Organization.objects.create(name="Serviços", slug="servicos")
    plan = Plan.objects.create(code="service-plan", name="Plano", modules=["integra"])
    TenantContract.objects.create(
        organization=office, plan=plan, status=TenantContract.Status.ACTIVE
    )
    assert has_entitlement(office, "integra")
    Entitlement.objects.create(organization=office, code="integra", enabled=False)
    assert has_entitlement(office, "integra")
    Entitlement.objects.update(enabled=True, valid_until=timezone.localdate() - timedelta(days=1))
    assert has_entitlement(office, "integra")
    FeatureFlag.objects.create(key="global-services", enabled=True)
    assert flag_enabled("global-services", office)
    FeatureFlag.objects.create(
        key="expired-services", enabled=True, expires_at=timezone.now() - timedelta(days=1)
    )
    assert not flag_enabled("expired-services", office)


def test_contract_module_snapshot_does_not_follow_a_later_catalogue_edit() -> None:
    office = Organization.objects.create(name="Snapshot", slug="snapshot")
    plan = Plan.objects.create(code="snapshot-plan", name="Snapshot", modules=["integra"])
    contract = TenantContract.objects.create(
        organization=office, plan=plan, status=TenantContract.Status.ACTIVE
    )
    contract.refresh_from_db()
    assert contract.selected_modules == ["integra"]

    plan.modules = ["journey"]
    plan.save(update_fields=["modules", "updated_at"])

    assert has_entitlement(office, "integra")
    assert not has_entitlement(office, "journey")


def test_lifecycle_transition_requires_reason_and_follows_state_machine() -> None:
    office = Organization.objects.create(name="Lifecycle", slug="lifecycle")
    actor = User.objects.create_user("lifecycle@example.test", "safe-password-123")
    lifecycle = TenantLifecycle.objects.create(
        organization=office, state=TenantLifecycle.State.ACTIVE
    )

    assert TenantLifecycle.State.SUSPENDED in allowed_lifecycle_targets(lifecycle)
    with pytest.raises(LifecycleTransitionError):
        transition_lifecycle(
            lifecycle=lifecycle, target=TenantLifecycle.State.SUSPENDED, reason="", actor=actor
        )
    updated = transition_lifecycle(
        lifecycle=lifecycle,
        target=TenantLifecycle.State.SUSPENDED,
        reason="Inadimplência",
        actor=actor,
    )
    assert updated.state == TenantLifecycle.State.SUSPENDED
    with pytest.raises(LifecycleTransitionError):
        transition_lifecycle(
            lifecycle=updated,
            target=TenantLifecycle.State.GRACE,
            reason="Não permitido",
            actor=actor,
        )
