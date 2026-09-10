from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.hub.models import ClientCompany, CompanyAccessGrant, ControlPlaneBinding
from apps.organizations.models import Membership, Organization


@pytest.mark.django_db
def test_company_api_returns_only_the_companies_granted_by_crmew(
    org_client: APIClient,
    organization: Organization,
    membership: Membership,
) -> None:
    allowed = ClientCompany.objects.create(
        organization=organization,
        name="Empresa permitida",
        dominio_code="001",
    )
    ClientCompany.objects.create(
        organization=organization,
        name="Empresa bloqueada",
        dominio_code="002",
    )
    ControlPlaneBinding.objects.create(
        organization=organization,
        remote_installation_id=uuid4(),
        controller_url="https://crmew.example.test",
        device_private_key="encrypted-test-key",
        controller_public_key="controller-key",
        cache_expires_at=timezone.now() + timedelta(minutes=10),
    )
    CompanyAccessGrant.objects.create(
        organization=organization,
        membership=membership,
        company=allowed,
        modules=[],
        capabilities=[],
    )

    response = org_client.get("/api/v1/companies/")

    assert response.status_code == 200
    assert [item["id"] for item in response.data["results"]] == [str(allowed.id)]
    assert "organization" not in response.data["results"][0]


@pytest.mark.django_db
def test_company_api_blocks_stale_crmew_authorization(
    org_client: APIClient,
    organization: Organization,
) -> None:
    ControlPlaneBinding.objects.create(
        organization=organization,
        remote_installation_id=uuid4(),
        controller_url="https://crmew.example.test",
        device_private_key="encrypted-test-key",
        controller_public_key="controller-key",
        cache_expires_at=timezone.now() - timedelta(seconds=1),
    )

    response = org_client.get("/api/v1/companies/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_company_api_is_read_only(
    org_client: APIClient,
    organization: Organization,
) -> None:
    response = org_client.post(
        "/api/v1/companies/",
        {"name": "Empresa não criada", "organization": str(organization.id)},
        format="json",
    )

    assert response.status_code == 405
    assert not ClientCompany.objects.filter(organization=organization).exists()
