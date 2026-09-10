"""Explicit, auditable local-model publication and rollback."""

from __future__ import annotations

from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.intelligence.models import EvaluationRun, ModelVersion
from apps.intelligence.training import compare_evaluation_runs
from apps.organizations.models import Organization


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
