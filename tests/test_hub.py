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
def test_history_keeps_an_ambiguous_match_in_human_review() -> None:
    office = Organization.objects.create(name="Escritório B2", slug="escritorio-b2")
    company = ClientCompany.objects.create(organization=office, name="Cliente B2")
    for accumulator_code in ("501", "502"):
        AccumulatorObservation.objects.create(
            organization=office,
            company=company,
            accumulator_code=accumulator_code,
            service_code="123",
            frequency=18,
            last_used_at=timezone.now() - timedelta(days=1),
        )

    _document, artifact, review = create_document_and_artifact(
        company=company,
        original_xml="<nfse id='ambiguous' />",
        normalized_data={"service_code": "123"},
    )

    assert artifact is None
    assert review is not None


@pytest.mark.django_db
def test_history_does_not_suggest_an_unrelated_accumulator() -> None:
    office = Organization.objects.create(name="Escritório B3", slug="escritorio-b3")
    company = ClientCompany.objects.create(organization=office, name="Cliente B3")
    AccumulatorObservation.objects.create(
        organization=office,
        company=company,
        accumulator_code="501",
        service_code="123",
        counterparty_ref="known-counterparty",
        frequency=100,
        last_used_at=timezone.now(),
    )

    _document, artifact, review = create_document_and_artifact(
        company=company,
        original_xml="<nfse id='unrelated' />",
        normalized_data={"service_code": "999", "counterparty_ref": "another-counterparty"},
    )

    assert artifact is None
    assert review is not None
    assert review.suggested_accumulator == ""


@pytest.mark.django_db
def test_recent_counterparty_history_can_classify_the_next_month() -> None:
    office = Organization.objects.create(name="Escritório B4", slug="escritorio-b4")
    company = ClientCompany.objects.create(organization=office, name="Cliente B4")
    AccumulatorObservation.objects.create(
        organization=office,
        company=company,
        accumulator_code="701",
        counterparty_ref="same-counterparty",
        frequency=8,
        last_used_at=timezone.now() - timedelta(days=31),
    )

    _document, artifact, review = create_document_and_artifact(
        company=company,
        original_xml="<nfse id='next-month' />",
        normalized_data={"counterparty_ref": "same-counterparty"},
    )

    assert review is None
    assert artifact is not None
    assert artifact.accumulator_code == "701"


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
