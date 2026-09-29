"""Current authorization for metered company operations, independent of HTTP views."""

from uuid import UUID

from apps.hub.controlplane import company_queryset_for_membership
from apps.hub.models import CompanyAccessGrant, ProductModule
from apps.organizations.models import Membership


def can_consult_dctfweb(*, organization_id: UUID, company_id: UUID, actor_id: UUID | None) -> bool:
    return can_execute_company_operation(
        organization_id=organization_id,
        company_id=company_id,
        actor_id=actor_id,
        module_code=ProductModule.Code.GUIDES,
    )


def can_execute_company_operation(
    *,
    organization_id: UUID,
    company_id: UUID,
    actor_id: UUID | None,
    module_code: str,
) -> bool:
    if module_code not in {ProductModule.Code.GUIDES, ProductModule.Code.INTEGRA}:
        return False
    if actor_id is None:
        return False
    member = (
        Membership.objects.select_related("organization")
        .filter(
            organization_id=organization_id,
            user_id=actor_id,
            is_active=True,
            user__is_active=True,
            organization__is_active=True,
        )
        .first()
    )
    if member is None or member.role in {Membership.Role.AUDITOR, Membership.Role.BILLING}:
        return False
    if not company_queryset_for_membership(member).filter(pk=company_id).exists():
        return False
    if not ProductModule.objects.filter(
        organization_id=organization_id,
        code=module_code,
        enabled=True,
    ).exists():
        return False
    if member.role in {Membership.Role.OWNER, Membership.Role.ADMIN}:
        return True
    return any(
        module_code in grant.modules
        for grant in CompanyAccessGrant.objects.filter(
            organization_id=organization_id,
            membership=member,
            company_id=company_id,
            is_active=True,
        )
    )
