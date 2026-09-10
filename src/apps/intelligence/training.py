"""Reproducible preparation and gatekeeping for local-model training.

This module never trains or calls a remote model. It prepares validated, source-linked
examples and records an independently produced evaluation report, so adapter training
(LoRA/QLoRA) can run in isolated GPU infrastructure with a deterministic input set.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, TypedDict

from django.utils import timezone

from apps.intelligence.models import (
    AssistantSettings,
    ClaudeFallbackApproval,
    EvaluationRun,
    TrainingExample,
)
from apps.organizations.models import Organization

MINIMUM_QUALITY_PERCENT = 95
_CLAUDE_MODEL_RE = re.compile(r"claude-[a-z0-9._-]{1,72}")
_LOCAL_MODEL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,159}")
_ADAPTER_NAME_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,119}")
_CHAT_TEMPLATE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}")
_PERSONAL_DATA_RE = re.compile(
    r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b|\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b|"
    r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b",
    re.IGNORECASE,
)
CURATION_SYSTEM_PROMPT = (
    "Você é um avaliador de treinamento do HubContador. Gere apenas JSON válido com "
    "cenários de teste, ambiguidades e critérios de correção. Use exclusivamente a resposta "
    "aprovada e as fontes fornecidas; não invente regras, não gere SQL e não inclua dados pessoais."
)


class TrainingManifestItem(TypedDict):
    id: str
    category: str
    question: str
    expected_answer: str
    source_references: list[str]
    scenario_hash: str


def stable_hash(*parts: str) -> str:
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def training_manifest(*, organization: Organization) -> list[TrainingManifestItem]:
    """Return no content without a validated source reference; no tenant crossing."""
    examples = TrainingExample.objects.filter(
        organization=organization, status=TrainingExample.Status.VALIDATED
    ).order_by("created_at")
    return [
        {
            "id": str(example.id),
            "category": example.category,
            "question": example.question,
            "expected_answer": example.expected_answer,
            "source_references": [str(reference) for reference in example.source_references],
            "scenario_hash": example.scenario_hash,
        }
        for example in examples
        if example.source_references
    ]


def corpus_fingerprint(*, organization: Organization) -> tuple[str, str, int]:
    """Return a stable, non-secret version for the validated tenant-only corpus."""
    manifest = training_manifest(organization=organization)
    canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.sha256(canonical.encode()).hexdigest()
    return f"corpus-{digest[:16]}", digest, len(manifest)


def qlora_job_spec(
    *, organization: Organization, base_model: str, adapter_name: str, chat_template: str
) -> dict[str, object]:
    """Build an immutable GPU-runner contract; it neither starts a job nor sends data."""
    if not _LOCAL_MODEL_RE.fullmatch(base_model) or ".." in base_model:
        raise ValueError("O modelo base local é inválido.")
    if not _ADAPTER_NAME_RE.fullmatch(adapter_name):
        raise ValueError("O nome do adaptador é inválido.")
    if not _CHAT_TEMPLATE_RE.fullmatch(chat_template):
        raise ValueError("O template de chat é inválido.")
    corpus_version, manifest_hash, example_count = corpus_fingerprint(organization=organization)
    if not example_count:
        raise ValueError("Não há exemplos validados com fonte para preparar o treinamento.")
    return {
        "format": "hubcontador.lora-job.v1",
        "organization_id": str(organization.id),
        "corpus_version": corpus_version,
        "manifest_sha256": manifest_hash,
        "example_count": example_count,
        "base_model": base_model[:160],
        "adapter_name": adapter_name[:120],
        "chat_template": chat_template[:80],
        "method": "qlora",
        "training": {
            "max_seq_length": 4096,
            "epochs": 3,
            "learning_rate": 0.0001,
            "quantization": "4bit-nf4",
        },
        "required_evaluation": {
            "source_coverage_percent": 100,
            "minimum_accuracy_percent": MINIMUM_QUALITY_PERCENT,
            "tenant_isolation_passed": True,
            "masking_passed": True,
            "tool_policy_passed": True,
        },
    }


def claude_curation_batch_spec(
    *,
    organization: Organization,
    assistant_settings: AssistantSettings,
    approval: ClaudeFallbackApproval | None,
) -> dict[str, object]:
    """Prepare, but never submit, Anthropic Batch API requests for offline curation.

    The artifact contains only the validated, source-linked examples of one office.
    It excludes attachments, live Domínio data and any record matching basic CPF/CNPJ/e-mail
    patterns. Returned suggestions must still become review candidates; they never alter a
    source, RAG entry or model automatically.
    """
    if assistant_settings.organization_id != organization.id:
        raise ValueError("A política de curadoria pertence a outro escritório.")
    if not assistant_settings.claude_offline_curation_enabled:
        raise ValueError("Curadoria Claude em lote não foi habilitada para este escritório.")
    if not _CLAUDE_MODEL_RE.fullmatch(assistant_settings.claude_model):
        raise ValueError("Curadoria Claude sem modelo permitido.")
    if approval is None or approval.status != ClaudeFallbackApproval.Status.APPROVED:
        raise ValueError("Curadoria Claude sem aprovação de custo vigente.")
    if approval.valid_until is not None and approval.valid_until <= timezone.now():
        raise ValueError("A aprovação Claude para curadoria expirou.")
    limit = assistant_settings.claude_curation_max_batch_requests
    if limit <= 0:
        raise ValueError("Curadoria Claude sem limite de lote configurado.")

    manifest = training_manifest(organization=organization)
    if not manifest:
        raise ValueError("Não há exemplos validados com fonte para curadoria.")
    selected = manifest[:limit]
    serialized = json.dumps(selected, ensure_ascii=False)
    if _PERSONAL_DATA_RE.search(serialized):
        raise ValueError(
            "O lote contém identificador pessoal; anonimize o exemplo antes da curadoria."
        )

    requests = []
    for item in selected:
        source_references = [str(value)[:240] for value in item["source_references"][:8]]
        prompt = {
            "pergunta_aprovada": str(item["question"])[:1_500],
            "resposta_aprovada": str(item["expected_answer"])[:1_800],
            "fontes": source_references,
            "tarefa": (
                "Crie até três cenários de regressão e uma ambiguidade. Cada item deve informar "
                "a fonte usada e quando a resposta deve declarar incerteza."
            ),
        }
        requests.append(
            {
                "custom_id": f"curation-{str(item['scenario_hash'])[:24]}",
                "params": {
                    "model": assistant_settings.claude_model,
                    "max_tokens": 700,
                    "temperature": 0,
                    "system": [{"type": "text", "text": CURATION_SYSTEM_PROMPT}],
                    "messages": [
                        {
                            "role": "user",
                            "content": json.dumps(
                                prompt, ensure_ascii=False, separators=(",", ":")
                            ),
                        }
                    ],
                },
            }
        )
    corpus_version, manifest_hash, _example_count = corpus_fingerprint(organization=organization)
    return {
        "format": "hubcontador.claude-curation-batch.v1",
        "organization_id": str(organization.id),
        "corpus_version": corpus_version,
        "manifest_sha256": manifest_hash,
        "request_count": len(requests),
        "model": assistant_settings.claude_model,
        "requests": requests,
    }


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reason: str
    accuracy_percent: float
    source_coverage_percent: float


@dataclass(frozen=True)
class RegressionResult:
    passed: bool
    reason: str


def record_evaluation(
    *, organization: Organization, report: dict[str, Any]
) -> tuple[EvaluationRun, GateResult]:
    """Persist a model-evaluator report and enforce the production publication gate."""
    total = report.get("total_cases")
    correct = report.get("correct_cases")
    sourced = report.get("sourced_cases")
    regressions = report.get("safety_regressions")
    if not all(
        isinstance(value, int) and value >= 0 for value in (total, correct, sourced, regressions)
    ):
        raise ValueError("O relatório de avaliação possui contadores inválidos.")
    assert isinstance(total, int)
    assert isinstance(correct, int)
    assert isinstance(sourced, int)
    assert isinstance(regressions, int)
    if total == 0 or correct > total or sourced > total:
        raise ValueError("O relatório de avaliação não possui uma base de casos válida.")
    accuracy = (correct / total) * 100
    coverage = (sourced / total) * 100
    passed = (
        accuracy >= MINIMUM_QUALITY_PERCENT
        and coverage == 100
        and regressions == 0
        and bool(report.get("tenant_isolation_passed"))
        and bool(report.get("masking_passed"))
        and bool(report.get("tool_policy_passed"))
    )
    reason = (
        "Aprovado para publicação manual."
        if passed
        else "Gate não atingido; mantenha a versão fora de produção."
    )
    run = EvaluationRun.objects.create(
        organization=organization,
        suite_name=str(report.get("suite_name", "unnamed"))[:100],
        model_name=str(report.get("model_name", "unknown"))[:100],
        corpus_version=str(report.get("corpus_version", "unknown"))[:80],
        total_cases=total,
        correct_cases=correct,
        sourced_cases=sourced,
        safety_regressions=regressions,
        passed=passed,
        results={
            key: value for key, value in report.items() if key not in {"raw_prompts", "raw_outputs"}
        },
    )
    return run, GateResult(passed, reason, accuracy, coverage)


def compare_evaluation_runs(
    *, baseline: EvaluationRun, candidate: EvaluationRun
) -> RegressionResult:
    """Require a candidate to match the frozen suite and never degrade its safety gate."""
    if baseline.organization_id != candidate.organization_id:
        raise ValueError("As avaliações pertencem a escritórios diferentes.")
    if not baseline.passed or not candidate.passed:
        return RegressionResult(False, "As duas avaliações precisam passar no gate de qualidade.")
    if baseline.suite_name != candidate.suite_name or baseline.total_cases != candidate.total_cases:
        return RegressionResult(
            False, "A comparação exige a mesma suíte congelada e quantidade de casos."
        )
    if candidate.correct_cases < baseline.correct_cases:
        return RegressionResult(
            False, "A versão candidata reduziu o número de acertos da versão ativa."
        )
    if candidate.sourced_cases < baseline.sourced_cases:
        return RegressionResult(False, "A versão candidata reduziu a cobertura de fontes.")
    if candidate.safety_regressions > baseline.safety_regressions:
        return RegressionResult(False, "A versão candidata introduziu regressão de segurança.")
    return RegressionResult(True, "Sem regressão na suíte congelada.")
