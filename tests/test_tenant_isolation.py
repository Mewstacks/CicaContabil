from __future__ import annotations

import pytest
from django.test import RequestFactory
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.organizations.models import Membership, Organization
from apps.organizations.viewsets import OrganizationScopedViewSet
from config.urls_api import router

SCOPED_PREFIXES = [
    prefix
    for prefix, viewset, _ in router.registry
    if isinstance(viewset, type) and issubclass(viewset, OrganizationScopedViewSet)
]


class ScopedMembershipViewSet(OrganizationScopedViewSet):  # type: ignore[type-arg]
    """Stand-in resource, so the base class stays covered before real ones exist."""

    queryset = Membership.objects.all()


@pytest.mark.django_db
def test_the_base_viewset_filters_by_the_selected_organization(
    organization: Organization,
    membership: Membership,
) -> None:
    outsider = User.objects.create_user("outsider2@example.com", "another-strong-password")
    other = Organization.objects.create(name="Globex", slug="globex-two")
    Membership.objects.create(organization=other, user=outsider)

    request = RequestFactory().get("/")
    request.organization = organization  # type: ignore[attr-defined]
    view = ScopedMembershipViewSet()
    view.request = request  # type: ignore[assignment]

    assert list(view.get_queryset()) == [membership]


@pytest.mark.django_db
@pytest.mark.skipif(not SCOPED_PREFIXES, reason="no organization-scoped routes registered yet")
def test_a_foreign_organization_header_is_never_accepted(
    other_org_client: APIClient,
    organization: Organization,
) -> None:
    """Sweeps every scoped route, including ones added long after this was written."""

    for prefix in SCOPED_PREFIXES:
        response = other_org_client.get(
            f"/api/v1/{prefix}/",
            HTTP_X_ORGANIZATION_ID=str(organization.id),
        )
        assert response.status_code == 404, prefix


@pytest.mark.django_db
@pytest.mark.skipif(not SCOPED_PREFIXES, reason="no organization-scoped routes registered yet")
def test_scoped_routes_refuse_requests_without_a_selected_organization(
    user: object,
    org_client: APIClient,
) -> None:
    org_client.credentials()  # drop the X-Organization-ID header
    for prefix in SCOPED_PREFIXES:
        response = org_client.get(f"/api/v1/{prefix}/")
        assert response.status_code == 403, prefix
