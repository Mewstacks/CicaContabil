"""Commercial authorization for work that consumes resources or changes data."""

from datetime import timedelta

from django.utils import timezone

from apps.hub.models import OfficeProfile, ProductModule
from apps.organizations.models import Organization
from apps.platform.models import TenantContract, TenantLifecycle


def require_operation_access(organization: Organization, module: str) -> None:
    """Fail closed before starting work, independently from scheduled state updates."""
    contract = (
        TenantContract.objects.filter(organization=organization)
        .select_related("plan")
        .order_by("-created_at", "-id")
        .first()
    )
    if contract is None or contract.status not in {
        TenantContract.Status.TRIAL,
        TenantContract.Status.ACTIVE,
    }:
        raise ValueError("O contrato não permite novas operações. Consulte seu plano.")
    if TenantLifecycle.objects.filter(
        organization=organization,
        state__in=["grace", "suspended", "archived"],
    ).exists():
        raise ValueError("Novas operações estão indisponíveis para este escritório.")
    now = timezone.now()
    today = timezone.localdate(now)
    if (contract.starts_on and today < contract.starts_on) or (
        contract.ends_on and today > contract.ends_on
    ):
        raise ValueError("O contrato está fora do período de vigência.")
    if contract.status == TenantContract.Status.TRIAL:
        profile = OfficeProfile.objects.filter(organization=organization).first()
        if (
            contract.starts_on is None
            or contract.trial_ends_on is None
            or today > contract.trial_ends_on
            or profile is None
            or profile.trial_started_at is None
            or not profile.trial_started_at <= now < profile.trial_started_at + timedelta(days=14)
        ):
            raise ValueError("Seu teste gratuito terminou. Consulte as opções de contratação.")
    contracted = contract.selected_modules or (contract.plan.modules if contract.plan else [])
    if (
        module not in contracted
        or not ProductModule.objects.filter(
            organization=organization, code=module, enabled=True
        ).exists()
    ):
        raise ValueError("Este módulo não está habilitado no contrato do escritório.")
