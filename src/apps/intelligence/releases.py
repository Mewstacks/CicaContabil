"""Explicit, auditable local-model publication and rollback."""

from __future__ import annotations

import re

from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.intelligence.models import EvaluationRun, ModelVersion
from apps.intelligence.training import compare_evaluation_runs
from apps.organizations.models import Organization

_SHA256_RE = re.compile(r"[a-f0-9]{64}")


def _has_declared_artifact(version: ModelVersion) -> bool:
    return any(
        (
            version.manifest_sha256,
            version.base_model,
            version.adapter_version,
            version.adapter_artifact_sha256,
        )
    )


def _require_matching_provenance(*, version: ModelVersion, evaluation: EvaluationRun) -> None:
    if not _has_declared_artifact(version):
        return
    version_provenance = (
        version.manifest_sha256,
        version.base_model,
        version.adapter_version,
        version.adapter_artifact_sha256,
    )
    if not all(version_provenance) or not all(
        _SHA256_RE.fullmatch(value)
        for value in (version.manifest_sha256, version.adapter_artifact_sha256)
    ):
        raise ValueError("A versão local precisa de proveniência completa e hashes válidos.")
    evaluation_provenance = (
        evaluation.manifest_sha256,
        evaluation.base_model,
        evaluation.adapter_version,
        evaluation.adapter_artifact_sha256,
    )
    if version_provenance != evaluation_provenance:
        raise ValueError("A avaliação não corresponde ao corpus e adaptador da versão.")
    if not _SHA256_RE.fullmatch(evaluation.evaluation_manifest_sha256):
        raise ValueError("A avaliação precisa identificar o manifesto independente de avaliação.")


def publish_model(
    *,
    organization: Organization,
    version: ModelVersion,
    evaluation: EvaluationRun,
    actor: User | None,
    request: object = None,
) -> ModelVersion:
    if version.organization_id != organization.id or evaluation.organization_id != organization.id:
        raise ValueError("Versão ou avaliação não pertence ao escritório.")
    if not evaluation.passed or evaluation.corpus_version != version.corpus_version:
        raise ValueError("A avaliação aprovada para este corpus é obrigatória antes da publicação.")
    _require_matching_provenance(version=version, evaluation=evaluation)
    with transaction.atomic():
        active_version = (
            ModelVersion.objects.select_for_update()
            .filter(organization=organization, is_active=True)
            .first()
        )
        if active_version is not None and active_version.id != version.id:
            baseline = (
                EvaluationRun.objects.filter(
                    organization=organization,
                    corpus_version=active_version.corpus_version,
                    passed=True,
                )
                .order_by("-created_at")
                .first()
            )
            if baseline is None:
                raise ValueError("A versão ativa não possui avaliação aprovada para comparação.")
            regression = compare_evaluation_runs(baseline=baseline, candidate=evaluation)
            if not regression.passed:
                raise ValueError(regression.reason)
        ModelVersion.objects.filter(organization=organization, is_active=True).update(
            is_active=False
        )
        version.is_active = True
        version.published_by = actor
        version.save(update_fields=["is_active", "published_by", "updated_at"])
        record_event(
            action="intelligence.model.published",
            actor=actor,
            organization=organization,
            target=version,
            request=request,
            metadata={
                "corpus_version": version.corpus_version,
                "evaluation_id": str(evaluation.id),
            },
        )
    return version


def rollback_model(
    *,
    organization: Organization,
    version: ModelVersion,
    evaluation: EvaluationRun,
    actor: User | None,
    request: object = None,
) -> ModelVersion:
    """Restore one previously approved office-local version without retraining it."""
    if version.organization_id != organization.id or evaluation.organization_id != organization.id:
        raise ValueError("Versão ou avaliação não pertence ao escritório.")
    if not evaluation.passed or evaluation.corpus_version != version.corpus_version:
        raise ValueError("A avaliação aprovada para este corpus é obrigatória antes do retorno.")
    _require_matching_provenance(version=version, evaluation=evaluation)
    with transaction.atomic():
        current = (
            ModelVersion.objects.select_for_update()
            .filter(organization=organization, is_active=True)
            .first()
        )
        if current is not None and current.id == version.id:
            return version
        ModelVersion.objects.filter(organization=organization, is_active=True).update(
            is_active=False
        )
        version.is_active = True
        version.published_by = actor
        version.save(update_fields=["is_active", "published_by", "updated_at"])
        record_event(
            action="intelligence.model.rolled_back",
            actor=actor,
            organization=organization,
            target=version,
            request=request,
            metadata={
                "from_version_id": str(current.id) if current is not None else "",
                "corpus_version": version.corpus_version,
                "evaluation_id": str(evaluation.id),
            },
        )
    return version
