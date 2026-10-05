from __future__ import annotations

import hashlib
from datetime import timedelta
from io import BytesIO
from zipfile import ZipFile

import pytest
from defusedxml import ElementTree
from django.utils import timezone

from apps.accounts.models import User
from apps.hub.models import (
    AccumulatorObservation,
    ClientCompany,
    DataSource,
    ImportBatch,
    IntegrationArtifact,
    NfseDocument,
    ReviewCase,
)
from apps.hub.nfse_reclassification import reclassify_nfse_from_backup
from apps.hub.services import create_nfse_export
from apps.organizations.models import Organization

pytestmark = pytest.mark.django_db(databases=["default", "knowledge"])


def _scenario() -> tuple[Organization, NfseDocument, ReviewCase, User]:
    organization = Organization.objects.create(name="Reclassificação", slug="reclassificacao")
    actor = User.objects.create_user("reclass@example.test", "safe-password-123")
    source = DataSource.objects.create(
        organization=organization,
        kind=DataSource.Kind.DOMINIO_WEB_BACKUP,
        label="Backup Domínio Web",
    )
    snapshot_at = timezone.now() - timedelta(hours=1)
    ImportBatch.objects.create(
        organization=organization,
        data_source=source,
        kind=ImportBatch.Kind.DOMINIO_BACKUP,
        status=ImportBatch.Status.COMPLETED,
        original_filename="backup.zip",
        content_hash="a" * 64,
        source_snapshot_at=snapshot_at,
        completed_at=snapshot_at,
        mapping={
            "received_capabilities": [
                "companies",
                "accumulator_catalog",
                "accumulator_observations",
            ]
        },
    )
    company = ClientCompany.objects.create(
        organization=organization,
        name="Empresa",
        dominio_code="109",
        data_source=source,
        external_key="109",
    )
    AccumulatorObservation.objects.create(
        organization=organization,
        company=company,
        accumulator_code="23",
        service_code="S-100",
        counterparty_ref="FORN-1",
        frequency=25,
        last_used_at=timezone.now(),
    )
    xml = '<NFSe xmlns="urn:nfse"><infNFSe><valores><vLiq>100.00</vLiq></valores></infNFSe></NFSe>'
    document = NfseDocument.objects.create(
        organization=organization,
        company=company,
        source_nsu="100",
        document_hash=hashlib.sha256(xml.encode()).hexdigest(),
        original_xml=xml,
        normalized_data={"service_code": "S-100", "counterparty_ref": "FORN-1"},
        issued_at=timezone.now(),
    )
    review = ReviewCase.objects.create(
        organization=organization,
        document=document,
        reason="Sem histórico no momento da captura",
    )
    return organization, document, review, actor


def test_reclassification_preview_is_read_only_and_apply_is_idempotent() -> None:
    organization, document, review, _actor = _scenario()

    preview = reclassify_nfse_from_backup(organization=organization)

    assert preview.scanned == 1
    assert preview.classified == 1
    assert preview.artifacts_created == 1
    assert preview.reviews_resolved == 1
    assert not IntegrationArtifact.objects.filter(document=document).exists()
    review.refresh_from_db()
    assert review.status == ReviewCase.Status.OPEN

    applied = reclassify_nfse_from_backup(organization=organization, apply=True)
    assert applied.artifacts_created == 1
    artifact = IntegrationArtifact.objects.get(document=document)
    assert artifact.accumulator_code == "23"
    assert artifact.evidence["source"] == "backup_reclassification"
    review.refresh_from_db()
    assert review.status == ReviewCase.Status.RESOLVED
    assert review.resolution_source == ReviewCase.ResolutionSource.BACKUP
    assert review.resolved_by is None
    assert review.resolved_accumulator == "23"

    replay = reclassify_nfse_from_backup(organization=organization, apply=True)
    assert replay.artifacts_created == 0
    assert replay.unchanged == 1
    assert IntegrationArtifact.objects.filter(document=document).count() == 1


def test_reclassified_export_keeps_original_and_writes_lowercase_acum_under_values() -> None:
    organization, document, _review, actor = _scenario()
    original = document.original_xml
    reclassify_nfse_from_backup(organization=organization, apply=True)

    export = create_nfse_export(organization=organization, documents=[document], actor=actor)

    with ZipFile(BytesIO(export.content.read())) as bundle:
        rendered = bundle.read(export.snapshot["documents"][0]["path"]).decode()
    root = ElementTree.fromstring(rendered)
    info = next(node for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "infNFSe")
    values = next(node for node in info if node.tag.rsplit("}", 1)[-1] == "valores")
    assert [(node.tag.rsplit("}", 1)[-1], node.text) for node in values] == [
        ("vLiq", "100.00"),
        ("acum", "23"),
    ]
    document.refresh_from_db()
    assert document.original_xml == original


def test_reclassification_never_overrides_a_human_decision() -> None:
    organization, document, review, actor = _scenario()
    review.status = ReviewCase.Status.RESOLVED
    review.resolution_source = ReviewCase.ResolutionSource.HUMAN
    review.resolved_accumulator = "31"
    review.resolved_by = actor
    review.resolved_at = timezone.now()
    review.save()
    IntegrationArtifact.objects.create(
        organization=organization,
        document=document,
        accumulator_code="31",
        applied_rule="Decisão humana",
        confidence=100,
        evidence={"source": "human_review"},
    )

    summary = reclassify_nfse_from_backup(organization=organization, apply=True)

    assert summary.skipped_human == 1
    assert IntegrationArtifact.objects.filter(document=document).count() == 1
    review.refresh_from_db()
    assert review.resolved_accumulator == "31"


def test_reclassification_requires_a_completed_backup_with_both_capabilities() -> None:
    organization = Organization.objects.create(name="Sem backup", slug="sem-backup")

    with pytest.raises(ValueError, match="catálogo e observações"):
        reclassify_nfse_from_backup(organization=organization)


def test_reclassification_accepts_linked_catalog_and_observation_batches() -> None:
    organization, document, _review, _actor = _scenario()
    combined = ImportBatch.objects.get(organization=organization)
    combined.mapping = {"received_capabilities": ["companies", "accumulator_catalog"]}
    combined.save(update_fields=["mapping"])
    observations = ImportBatch.objects.create(
        organization=organization,
        data_source=combined.data_source,
        kind=ImportBatch.Kind.DOMINIO_BACKUP,
        status=ImportBatch.Status.COMPLETED,
        original_filename="observations.json",
        content_hash="b" * 64,
        source_snapshot_at=combined.source_snapshot_at,
        completed_at=combined.completed_at + timedelta(minutes=1),
        mapping={
            "capability": "accumulator_observations",
            "parent_batch_id": str(combined.id),
        },
    )

    summary = reclassify_nfse_from_backup(organization=organization)

    assert summary.backup_batch_id == str(combined.id)
    assert summary.observations_batch_id == str(observations.id)
    assert summary.scanned == 1
    assert summary.classified == 1
    assert document.original_xml


def test_reclassification_reopens_a_backup_decision_the_evidence_no_longer_supports() -> None:
    organization, document, review, _actor = _scenario()
    reclassify_nfse_from_backup(organization=organization, apply=True)
    AccumulatorObservation.objects.filter(organization=organization).delete()

    replay = reclassify_nfse_from_backup(organization=organization, apply=True)

    assert replay.reviews_reopened == 1
    review.refresh_from_db()
    assert review.status == ReviewCase.Status.OPEN
    assert review.resolution_source == ""
    assert review.resolved_accumulator == ""
    assert IntegrationArtifact.objects.filter(document=document).count() == 1


def test_reclassification_keeps_an_artifact_the_aged_evidence_still_points_to() -> None:
    organization, document, review, _actor = _scenario()
    reclassify_nfse_from_backup(organization=organization, apply=True)
    AccumulatorObservation.objects.filter(organization=organization).update(
        frequency=1, last_used_at=timezone.now() - timedelta(days=900)
    )
    AccumulatorObservation.objects.create(
        organization=organization,
        company=document.company,
        accumulator_code="99",
        counterparty_ref="FORN-1",
        frequency=1,
        last_used_at=timezone.now() - timedelta(days=2000),
    )

    replay = reclassify_nfse_from_backup(organization=organization, apply=True)

    assert replay.unchanged == 1
    assert replay.reviews_reopened == 0
    review.refresh_from_db()
    assert review.status == ReviewCase.Status.RESOLVED
