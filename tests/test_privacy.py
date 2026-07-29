from __future__ import annotations

import uuid
from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.db import connection
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.privacy.models import (
    ConsentRecord,
    PersonalDataIncident,
    PrivacyNotice,
    ProcessingPurpose,
)


@pytest.fixture
def notice(db: object) -> PrivacyNotice:
    from django.utils import timezone

    return PrivacyNotice.objects.create(
        version="2026-01",
        document_url="https://example.com/privacy/2026-01",
        checksum_sha256="a" * 64,
        effective_at=timezone.now(),
        active=True,
    )


@pytest.fixture
def consent_purpose(db: object) -> ProcessingPurpose:
    return ProcessingPurpose.objects.create(
        code="product-email",
        name="Product email",
        description="Optional product announcements.",
        lawful_basis=ProcessingPurpose.LawfulBasis.CONSENT,
        data_categories=["identity", "contact"],
        retention_days=365,
    )


@pytest.mark.django_db
def test_consent_ledger_is_idempotent_and_lawful_basis_aware(
    user: User,
    notice: PrivacyNotice,
    consent_purpose: ProcessingPurpose,
) -> None:
    client = APIClient()
    client.force_authenticate(user)
    key = uuid.uuid4()
    payload = {
        "idempotency_key": str(key),
        "purpose": str(consent_purpose.id),
        "notice": str(notice.id),
        "decision": ConsentRecord.Decision.GRANTED,
    }
    first = client.post("/api/v1/privacy/consents/", payload, format="json")
    second = client.post("/api/v1/privacy/consents/", payload, format="json")
    assert first.status_code == 201
    assert second.status_code == 201
    assert ConsentRecord.objects.filter(user=user, purpose=consent_purpose).count() == 1

    contract_purpose = ProcessingPurpose.objects.create(
        code="provide-service",
        name="Provide the service",
        description="Required to perform the customer contract.",
        lawful_basis=ProcessingPurpose.LawfulBasis.CONTRACT,
        data_categories=["identity"],
        retention_days=1825,
    )
    rejected = client.post(
        "/api/v1/privacy/consents/",
        {**payload, "idempotency_key": str(uuid.uuid4()), "purpose": str(contract_purpose.id)},
        format="json",
    )
    assert rejected.status_code == 400


@pytest.mark.django_db
def test_subject_request_details_are_encrypted_at_application_layer(user: User) -> None:
    client = APIClient()
    client.force_authenticate(user)
    response = client.post(
        "/api/v1/privacy/requests/",
        {"request_type": "access", "details": "Please include my account history."},
        format="json",
    )
    assert response.status_code == 201
    request_id = response.data["id"]
    database_id: object = (
        request_id.replace("-", "") if connection.vendor == "sqlite" else uuid.UUID(request_id)
    )

    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT details FROM privacy_datasubjectrequest WHERE id = %s",
            [database_id],
        )
        raw_value = cursor.fetchone()[0]
    assert raw_value.startswith("enc:v1:test-v1:")

    retrieved = client.get(f"/api/v1/privacy/requests/{request_id}/")
    assert retrieved.status_code == 200
    assert retrieved.data["details"] == "Please include my account history."


@pytest.mark.django_db
def test_subject_requests_are_visible_only_to_requester(user: User) -> None:
    owner_client = APIClient()
    owner_client.force_authenticate(user)
    created = owner_client.post(
        "/api/v1/privacy/requests/",
        {"request_type": "correction", "details": "My profile needs correction."},
        format="json",
    )

    other = User.objects.create_user("second@example.com", "second-strong-password")
    other_client = APIClient()
    other_client.force_authenticate(other)
    hidden = other_client.get(f"/api/v1/privacy/requests/{created.data['id']}/")
    assert hidden.status_code == 404


@pytest.mark.django_db
def test_incident_retention_cannot_be_shortened_below_five_years() -> None:
    discovered_at = timezone.now()
    with pytest.raises(ValidationError):
        PersonalDataIncident.objects.create(
            reference="INC-2026-0001",
            discovered_at=discovered_at,
            summary="Test incident",
            retain_until=discovered_at + timedelta(days=30),
        )
