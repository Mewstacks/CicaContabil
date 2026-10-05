"""Replay stored NFS-e against the latest completed Domínio backup evidence."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from django.db import transaction
from django.db.models import QuerySet
from django.utils import timezone

from apps.audit.services import record_event
from apps.hub.models import (
    AccumulatorObservation,
    AccumulatorRule,
    ClientCompany,
    ImportBatch,
    IntegrationArtifact,
    NfseDocument,
    ReviewCase,
)
from apps.hub.module_activities import sync_nfse_review_activity
from apps.hub.nfse_sync import nfse_match_data
from apps.hub.services import active_catalog_codes, classify_nfse_from_candidates
from apps.organizations.models import Organization

REQUIRED_BACKUP_CAPABILITIES = {"accumulator_catalog", "accumulator_observations"}
HUMAN_SOURCES = {"human_review", "human_correction"}


@dataclass(frozen=True)
class BackupEvidence:
    catalog_batch: ImportBatch
    observations_batch: ImportBatch

    @property
    def snapshot_at(self) -> datetime | None:
        return self.catalog_batch.source_snapshot_at


@dataclass
class ReclassificationSummary:
    run_id: str
    organization_id: str
    backup_batch_id: str
    observations_batch_id: str
    backup_snapshot_at: str
    apply: bool
    scanned: int = 0
    classified: int = 0
    artifacts_created: int = 0
    unchanged: int = 0
    reviews_resolved: int = 0
    reviews_updated: int = 0
    reviews_created: int = 0
    reviews_reopened: int = 0
    needs_review: int = 0
    skipped_human: int = 0

    def payload(self) -> dict[str, Any]:
        return asdict(self)


def _batch_capabilities(batch: ImportBatch) -> set[str]:
    received = batch.mapping.get("received_capabilities", [])
    capabilities = {str(value) for value in received if isinstance(value, str)}
    capability = batch.mapping.get("capability")
    if isinstance(capability, str):
        capabilities.add(capability)
    return capabilities


def latest_eligible_backup(organization: Organization) -> BackupEvidence:
    batches = list(
        ImportBatch.objects.filter(
            organization=organization,
            status=ImportBatch.Status.COMPLETED,
            source_snapshot_at__isnull=False,
        ).order_by("-source_snapshot_at", "-completed_at")
    )
    for catalog_batch in batches:
        catalog_capabilities = _batch_capabilities(catalog_batch)
        if "accumulator_catalog" not in catalog_capabilities:
            continue
        if REQUIRED_BACKUP_CAPABILITIES.issubset(catalog_capabilities):
            return BackupEvidence(catalog_batch, catalog_batch)
        for observations_batch in batches:
            if observations_batch.source_snapshot_at != catalog_batch.source_snapshot_at:
                continue
            if "accumulator_observations" not in _batch_capabilities(observations_batch):
                continue
            parent_batch_id = observations_batch.mapping.get("parent_batch_id")
            if str(parent_batch_id or "") == str(catalog_batch.id):
                return BackupEvidence(catalog_batch, observations_batch)
    raise ValueError("Nenhum backup concluído contém catálogo e observações de acumuladores.")


def _in_pages(queryset: QuerySet[NfseDocument], size: int = 200) -> Iterator[NfseDocument]:
    """Fetch a few notes at a time.

    Production runs behind PgBouncer with server-side cursors disabled, so ``.iterator()``
    would still pull every decrypted XML of the company into memory at once.
    """

    ids = list(queryset.values_list("pk", flat=True))
    for start in range(0, len(ids), size):
        yield from queryset.filter(pk__in=ids[start : start + size])


def _effective_artifact(artifacts: list[IntegrationArtifact]) -> IntegrationArtifact | None:
    superseded: set[str] = set()
    for artifact in artifacts:
        for container in (artifact.payload, artifact.evidence):
            if not isinstance(container, dict):
                continue
            previous_id = container.get("previous_artifact_id")
            if previous_id:
                superseded.add(str(previous_id))
    for artifact in reversed(artifacts):
        if str(artifact.id) not in superseded:
            return artifact
    return artifacts[-1] if artifacts else None


def _is_human_decision(review: ReviewCase | None, artifact: IntegrationArtifact | None) -> bool:
    if (
        review is not None
        and review.status == ReviewCase.Status.RESOLVED
        and (review.resolution_source == ReviewCase.ResolutionSource.HUMAN or review.resolved_by_id)
    ):
        return True
    if artifact is None:
        return False
    source = artifact.evidence.get("source") if isinstance(artifact.evidence, dict) else ""
    return str(source) in HUMAN_SOURCES


def reclassify_nfse_from_backup(
    *, organization: Organization, apply: bool = False, actor: object = None
) -> ReclassificationSummary:
    """Reclassify all stored documents, preserving originals and human decisions."""

    backup = latest_eligible_backup(organization)
    assert backup.snapshot_at is not None
    run_id = str(uuid4())
    summary = ReclassificationSummary(
        run_id=run_id,
        organization_id=str(organization.id),
        backup_batch_id=str(backup.catalog_batch.id),
        observations_batch_id=str(backup.observations_batch.id),
        backup_snapshot_at=backup.snapshot_at.isoformat(),
        apply=apply,
    )
    companies = (
        ClientCompany.objects.filter(
            organization=organization,
            nfse_documents__isnull=False,
        )
        .distinct()
        .order_by("pk")
    )
    catalogs = active_catalog_codes(list(companies))
    changed_review_ids: set[UUID] = set()
    for company in companies.iterator(chunk_size=100):
        # One company's candidates at a time: the whole office history does not fit beside the
        # worker in a 512 MB machine.
        rules = list(
            AccumulatorRule.objects.filter(
                organization=organization, company=company, active=True
            ).order_by("priority", "pk")
        )
        observations = list(
            AccumulatorObservation.objects.filter(
                organization=organization, company=company
            ).order_by("pk")
        )
        with transaction.atomic():
            documents = (
                NfseDocument.objects.filter(organization=organization, company=company)
                .select_related("company", "review_case")
                .prefetch_related("integration_artifacts")
                .select_for_update(of=("self",))
                .order_by("pk")
            )
            for document in _in_pages(documents):
                summary.scanned += 1
                artifacts = sorted(
                    document.integration_artifacts.all(), key=lambda item: item.created_at
                )
                effective = _effective_artifact(artifacts)
                review = getattr(document, "review_case", None)
                if _is_human_decision(review, effective):
                    summary.skipped_human += 1
                    continue
                result = classify_nfse_from_candidates(
                    document,
                    rules=rules,
                    observations=observations,
                    catalog_codes=catalogs.get(company.id),
                    match_data=nfse_match_data(document),
                    on_date=(document.issued_at.date() if document.issued_at else None),
                )
                if (
                    result.needs_review
                    and effective is not None
                    and result.accumulator_code
                    and result.accumulator_code == effective.accumulator_code
                ):
                    # Weaker today only because the history aged; it still points to the
                    # accumulator already chosen, so the note keeps it without a new review.
                    summary.unchanged += 1
                    continue
                if result.needs_review or not result.accumulator_code:
                    summary.needs_review += 1
                    if review is None:
                        summary.reviews_created += 1
                        if apply:
                            review = ReviewCase.objects.create(
                                organization=organization,
                                document=document,
                                reason="Backup sem correspondência segura",
                                suggested_accumulator=result.accumulator_code,
                                confidence=result.confidence,
                            )
                            changed_review_ids.add(review.pk)
                    elif review.status == ReviewCase.Status.OPEN and (
                        review.suggested_accumulator != result.accumulator_code
                        or review.confidence != result.confidence
                    ):
                        summary.reviews_updated += 1
                        if apply:
                            review.suggested_accumulator = result.accumulator_code
                            review.confidence = result.confidence
                            review.reason = "Backup sem correspondência segura"
                            review.save(
                                update_fields=[
                                    "suggested_accumulator",
                                    "confidence",
                                    "reason",
                                    "updated_at",
                                ]
                            )
                    elif (
                        review.status == ReviewCase.Status.RESOLVED
                        and review.resolution_source == ReviewCase.ResolutionSource.BACKUP
                    ):
                        # An earlier replay decided this note; the current evidence no longer
                        # supports any accumulator safely, so it returns to the review queue.
                        summary.reviews_reopened += 1
                        if apply:
                            review.status = ReviewCase.Status.OPEN
                            review.resolved_accumulator = ""
                            review.resolution_source = ""
                            review.resolved_at = None
                            review.suggested_accumulator = result.accumulator_code
                            review.confidence = result.confidence
                            review.reason = "Backup sem correspondência segura"
                            review.save(
                                update_fields=[
                                    "status",
                                    "resolved_accumulator",
                                    "resolution_source",
                                    "resolved_at",
                                    "suggested_accumulator",
                                    "confidence",
                                    "reason",
                                    "updated_at",
                                ]
                            )
                            changed_review_ids.add(review.pk)
                    continue

                summary.classified += 1
                artifact_changed = (
                    effective is None or effective.accumulator_code != result.accumulator_code
                )
                if artifact_changed:
                    summary.artifacts_created += 1
                    if apply:
                        previous_id = str(effective.id) if effective is not None else ""
                        IntegrationArtifact.objects.create(
                            organization=organization,
                            document=document,
                            accumulator_code=result.accumulator_code,
                            applied_rule="Reclassificação pelo backup Domínio",
                            confidence=result.confidence,
                            evidence={
                                **result.evidence,
                                "source": "backup_reclassification",
                                "backup_batch_id": str(backup.catalog_batch.id),
                                "observations_batch_id": str(backup.observations_batch.id),
                                "backup_snapshot_at": backup.snapshot_at.isoformat(),
                                "previous_artifact_id": previous_id,
                            },
                            payload={
                                "contract": "hub-nfse-v1",
                                "original_hash": document.document_hash,
                                "accumulator": result.accumulator_code,
                                "reclassification_run_id": run_id,
                                "previous_artifact_id": previous_id,
                            },
                        )
                else:
                    summary.unchanged += 1

                if review is not None and review.status == ReviewCase.Status.OPEN:
                    summary.reviews_resolved += 1
                    if apply:
                        review.status = ReviewCase.Status.RESOLVED
                        review.resolved_accumulator = result.accumulator_code
                        review.resolution_source = ReviewCase.ResolutionSource.BACKUP
                        review.resolved_by = None
                        review.resolved_at = timezone.now()
                        review.suggested_accumulator = result.accumulator_code
                        review.confidence = result.confidence
                        review.save(
                            update_fields=[
                                "status",
                                "resolved_accumulator",
                                "resolution_source",
                                "resolved_by",
                                "resolved_at",
                                "suggested_accumulator",
                                "confidence",
                                "updated_at",
                            ]
                        )
                        changed_review_ids.add(review.pk)
                elif (
                    apply
                    and review is not None
                    and review.status == ReviewCase.Status.RESOLVED
                    and review.resolution_source == ReviewCase.ResolutionSource.BACKUP
                ):
                    if review.resolved_accumulator != result.accumulator_code:
                        review.resolved_accumulator = result.accumulator_code
                        review.suggested_accumulator = result.accumulator_code
                        review.confidence = result.confidence
                        review.save(
                            update_fields=[
                                "resolved_accumulator",
                                "suggested_accumulator",
                                "confidence",
                                "updated_at",
                            ]
                        )
                    changed_review_ids.add(review.pk)

    if apply:
        for review_id in changed_review_ids:
            sync_nfse_review_activity(review_id)
        record_event(
            action="hub.nfse.reclassified_from_backup",
            actor=actor,
            organization=organization,
            target=backup.catalog_batch,
            metadata=summary.payload(),
        )
    return summary
