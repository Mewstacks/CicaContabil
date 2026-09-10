from __future__ import annotations

from uuid import UUID

from apps.organizations.models import Organization


def resolve_organization(selector: str) -> Organization | None:
    """Resolve a organização por UUID ou slug sem tratar slug como UUID."""
    normalized = selector.strip()
    try:
        organization_id = UUID(normalized)
    except ValueError:
        return Organization.objects.filter(slug=normalized.casefold()).first()
    return Organization.objects.filter(id=organization_id).first()
