from __future__ import annotations

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.utils import timezone

from apps.accounts.models import User
from apps.organizations.models import Organization
from apps.platform.models import Entitlement, FeatureFlag, PlatformAccess, TenantContract


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
            status__in=[TenantContract.Status.ACTIVE, TenantContract.Status.GRACE],
        )
        .select_related("plan")
        .order_by("-created_at")
        .first()
    )
    return bool(contract and contract.plan and code in contract.plan.modules)


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
