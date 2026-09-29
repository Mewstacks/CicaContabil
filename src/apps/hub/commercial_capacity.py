"""Commercial capacity measured from the operational office, without pricing assumptions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from apps.hub.models import ClientCompany, UsageAllowance
from apps.organizations.models import Membership, Organization


@dataclass(frozen=True)
class CommercialCapacity:
    active_users: int
    active_company_roots: int
    active_companies_without_root: int


def calculate_commercial_capacity(*, organization: Organization) -> CommercialCapacity:
    """Count active users and unique active CNPJ roots; never fabricate a missing root."""

    active_companies = ClientCompany.objects.filter(organization=organization, active=True)
    roots = active_companies.exclude(commercial_root_cnpj="").values_list(
        "commercial_root_cnpj", flat=True
    ).distinct()
    return CommercialCapacity(
        active_users=Membership.objects.filter(organization=organization, is_active=True).count(),
        active_company_roots=roots.count(),
        active_companies_without_root=active_companies.filter(commercial_root_cnpj="").count(),
    )


def refresh_configured_capacity(
    *, organization: Organization, period_start: date
) -> CommercialCapacity:
    """Refresh only configured allowance rows; limits and prices remain commercial inputs."""

    capacity = calculate_commercial_capacity(organization=organization)
    values = {
        UsageAllowance.Metric.USERS: capacity.active_users,
        UsageAllowance.Metric.COMPANIES: capacity.active_company_roots,
    }
    for metric, consumed in values.items():
        UsageAllowance.objects.filter(
            organization=organization,
            metric=metric,
            period_start=period_start,
        ).update(consumed=consumed)
    return capacity
