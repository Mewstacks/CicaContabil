from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.hub.models import (
    AccumulatorObservation,
    ClientCompany,
    IntegrationArtifact,
    NfseDocument,
)
from apps.hub.services import create_document_and_artifact
from apps.organizations.models import Organization


@pytest.mark.django_db
def test_nfse_original_and_integration_artifact_are_append_only() -> None:
    office = Organization.objects.create(name="Escritório A", slug="escritorio-a")
    company = ClientCompany.objects.create(organization=office, name="Cliente A")
    document, _, review = create_document_and_artifact(
        company=company, original_xml="<nfse id='1'/>", normalized_data={"service_code": "100"}
    )
    assert review is not None
    document.normalized_data = {"service_code": "changed"}
    with pytest.raises(ValidationError):
        document.save()
    with pytest.raises(ValidationError):
        NfseDocument.objects.filter(id=document.id).update(source_nsu="2")


@pytest.mark.django_db
def test_history_creates_a_confident_derived_artifact() -> None:
    office = Organization.objects.create(name="Escritório B", slug="escritorio-b")
    company = ClientCompany.objects.create(organization=office, name="Cliente B")
    AccumulatorObservation.objects.create(
        organization=office,
        company=company,
        accumulator_code="501",
        service_code="123",
        frequency=18,
        last_used_at=timezone.now() - timedelta(days=1),
    )
    document, artifact, review = create_document_and_artifact(
        company=company, original_xml="<nfse id='2'/>", normalized_data={"service_code": "123"}
    )
    assert review is None
    assert artifact is not None
    assert artifact.accumulator_code == "501"
    assert IntegrationArtifact.objects.filter(document=document).count() == 1


@pytest.mark.django_db
def test_document_hash_is_isolated_by_office_but_cannot_repeat_inside_it() -> None:
    office = Organization.objects.create(name="Escritório C", slug="escritorio-c")
    company = ClientCompany.objects.create(organization=office, name="Cliente C")
    first, _, _ = create_document_and_artifact(
        company=company, original_xml="<same/>", normalized_data={}
    )
    second, artifact, review = create_document_and_artifact(
        company=company, original_xml="<same/>", normalized_data={}
    )
    assert first.id == second.id
    assert artifact is None and review is None
