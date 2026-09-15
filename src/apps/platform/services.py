from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.platform.models import (
    Entitlement,
    FeatureFlag,
    PlatformAccess,
    TenantContract,
    TenantLifecycle,
)


def platform_role(user: User | AnonymousUser) -> str | None:
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return PlatformAccess.Role.ADMIN
    access = PlatformAccess.objects.filter(user=user, is_active=True).only("role").first()
    return access.role if access else None


def has_platform_role(user: User | AnonymousUser, *roles: str) -> bool:
    role = platform_role(user)
    return bool(role and (role == PlatformAccess.Role.ADMIN or role in roles))


def support_access_mode(user: User | AnonymousUser) -> str:
    """Only an explicit local developer mode can open a mutable support session."""
    role = platform_role(user)
    if settings.PLATFORM_DEVELOPER_FULL_ACCESS and role in {
        PlatformAccess.Role.DEVELOPER,
        PlatformAccess.Role.ADMIN,
    }:
        return "full"
    return "read_only"


def has_entitlement(organization: Organization, code: str) -> bool:
    today = timezone.localdate()
    entitlement = Entitlement.objects.filter(
        organization=organization, code=code, enabled=True
    ).first()
    if entitlement is not None and (
        entitlement.valid_until is None or entitlement.valid_until >= today
    ):
        return True
    contract = (
        TenantContract.objects.filter(
            organization=organization,
            status__in=[
                TenantContract.Status.TRIAL,
                TenantContract.Status.ACTIVE,
                TenantContract.Status.GRACE,
            ],
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )
    if contract is None:
        return False
    # Older contracts were created before module snapshots existed. Preserve
    # their access until commercial migration can review them; every new
    # contract gets a non-empty snapshot on creation.
    modules = contract.selected_modules or (contract.plan.modules if contract.plan else [])
    return code in modules


def flag_enabled(key: str, organization: Organization | None = None) -> bool:
    now = timezone.now()
    flags = FeatureFlag.objects.filter(key=key, enabled=True).filter(
        expires_at__isnull=True
    ) | FeatureFlag.objects.filter(key=key, enabled=True, expires_at__gt=now)
    if organization is not None:
        scoped = flags.filter(organization=organization).first()
        if scoped:
            return True
    return flags.filter(organization__isnull=True).exists()


class LifecycleTransitionError(Exception):
    """A tenant's lifecycle moved somewhere the state machine does not go."""


# Archived is terminal on purpose: a tenant comes back by being provisioned again,
# not by a click that silently revives data somebody decided to retire.
LIFECYCLE_TRANSITIONS: dict[str, tuple[str, ...]] = {
    TenantLifecycle.State.PROVISIONING: (
        TenantLifecycle.State.ACTIVATION_PENDING,
        TenantLifecycle.State.ARCHIVED,
    ),
    TenantLifecycle.State.ACTIVATION_PENDING: (
        TenantLifecycle.State.ACTIVE,
        TenantLifecycle.State.ARCHIVED,
    ),
    TenantLifecycle.State.ACTIVE: (
        TenantLifecycle.State.GRACE,
        TenantLifecycle.State.SUSPENDED,
        TenantLifecycle.State.ARCHIVED,
    ),
    TenantLifecycle.State.GRACE: (
        TenantLifecycle.State.ACTIVE,
        TenantLifecycle.State.SUSPENDED,
        TenantLifecycle.State.ARCHIVED,
    ),
    TenantLifecycle.State.SUSPENDED: (
        TenantLifecycle.State.ACTIVE,
        TenantLifecycle.State.ARCHIVED,
    ),
    TenantLifecycle.State.ARCHIVED: (),
}


def allowed_lifecycle_targets(lifecycle: TenantLifecycle) -> tuple[str, ...]:
    return LIFECYCLE_TRANSITIONS.get(lifecycle.state, ())


def transition_lifecycle(
    *, lifecycle: TenantLifecycle, target: str, reason: str, actor: User
) -> TenantLifecycle:
    """Move a tenant between lifecycle states, always with a reason on the record."""

    if target not in allowed_lifecycle_targets(lifecycle):
        raise LifecycleTransitionError(f"{lifecycle.get_state_display()} não vai para este estado.")
    if not reason.strip():
        raise LifecycleTransitionError("Escreva o motivo da mudança.")
    lifecycle.state = target
    lifecycle.reason = reason.strip()[:240]
    lifecycle.changed_by = actor
    lifecycle.save(update_fields=["state", "reason", "changed_by", "updated_at"])
    return lifecycle
