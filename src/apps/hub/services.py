from __future__ import annotations

import base64
import hashlib
import json
from dataclasses import dataclass
from datetime import date
from typing import Any

from cryptography.hazmat.primitives.serialization import pkcs12
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.hub.models import (
    AccumulatorObservation,
    AccumulatorRule,
    Certificate,
    ClientCompany,
    Connector,
    DteRun,
    DteRunItem,
    IntegrationArtifact,
    NfseDocument,
    ReviewCase,
)


@dataclass(frozen=True)
class ClassificationResult:
    accumulator_code: str
    confidence: int
    rule_name: str
    evidence: dict[str, object]
    needs_review: bool


def _matches(rule: AccumulatorRule, data: dict[str, Any]) -> bool:
    return all(str(data.get(key, "")) == str(expected) for key, expected in rule.match.items())


def classify_nfse(document: NfseDocument, *, on_date: date | None = None) -> ClassificationResult:
    """Deterministic, explainable classification. It never decides a tax treatment by AI."""

    data = document.normalized_data
    current_day = on_date or timezone.localdate()
    rules = document.company.accumulator_rules.filter(active=True).order_by("priority")
    for rule in rules:
        if rule.valid_from and rule.valid_from > current_day:
            continue
        if rule.valid_until and rule.valid_until < current_day:
            continue
        if _matches(rule, data):
            return ClassificationResult(
                accumulator_code=rule.accumulator_code,
                confidence=95 if not rule.is_transitory else 70,
                rule_name=rule.name,
                evidence={"source": "configured_rule", "transitory": rule.is_transitory},
                needs_review=rule.is_transitory,
            )

    service_code = str(data.get("service_code", ""))
    counterparty_ref = str(data.get("counterparty_ref", ""))
    candidates = AccumulatorObservation.objects.filter(
        organization=document.organization, company=document.company
    )
    scored: list[tuple[int, AccumulatorObservation]] = []
    for candidate in candidates:
        score = min(candidate.frequency, 20)
        if service_code and candidate.service_code == service_code:
            score += 45
        if counterparty_ref and candidate.counterparty_ref == counterparty_ref:
            score += 25
        age_days = (timezone.now() - candidate.last_used_at).days
        score += max(0, 20 - min(age_days, 20))
        scored.append((score, candidate))
    if scored:
        score, winner = max(scored, key=lambda item: item[0])
        return ClassificationResult(
            accumulator_code=winner.accumulator_code,
            confidence=min(score, 90),
            rule_name="histórico Domínio",
            evidence={"source": "dominio_history", "frequency": winner.frequency, "score": score},
            needs_review=score < 70,
        )
    return ClassificationResult("", 0, "sem correspondência", {"source": "none"}, True)


@transaction.atomic
def create_document_and_artifact(
    *,
    company: ClientCompany,
    original_xml: str,
    normalized_data: dict[str, Any],
    source_nsu: str = "",
    actor: Any = None,
    request: Any = None,
) -> tuple[NfseDocument, IntegrationArtifact | None, ReviewCase | None]:
    digest = hashlib.sha256(original_xml.encode()).hexdigest()
    document, created = NfseDocument.objects.get_or_create(
        organization=company.organization,
        document_hash=digest,
        defaults={
            "company": company,
            "source_nsu": source_nsu,
            "original_xml": original_xml,
            "normalized_data": normalized_data,
        },
    )
    if not created:
        return document, None, None
    result = classify_nfse(document)
    review_case = None
    artifact = None
    if result.needs_review:
        review_case = ReviewCase.objects.create(
            organization=company.organization,
            document=document,
            reason="Baixa confiança ou regra transitória",
            suggested_accumulator=result.accumulator_code,
            confidence=result.confidence,
        )
    elif result.accumulator_code:
        artifact = IntegrationArtifact.objects.create(
            organization=company.organization,
            document=document,
            accumulator_code=result.accumulator_code,
            applied_rule=result.rule_name,
            confidence=result.confidence,
            evidence=result.evidence,
            payload={
                "contract": "hub-nfse-v1",
                "original_hash": digest,
                "accumulator": result.accumulator_code,
            },
        )
    record_event(
        action="hub.nfse.document_captured",
        actor=actor,
        organization=company.organization,
        target=document,
        request=request,
        metadata={"source": "adn", "has_review": bool(review_case)},
    )
    return document, artifact, review_case


def store_certificate(
    *,
    company: ClientCompany,
    pfx_bytes: bytes,
    password: str,
    label: str,
    actor: Any = None,
    request: Any = None,
) -> Certificate:
    """Stores PFX once, encrypted; no view/form exposes its source bytes after upload."""
    try:
        _, parsed_certificate, _ = pkcs12.load_key_and_certificates(pfx_bytes, password.encode())
    except ValueError as exc:
        raise ValueError("Não foi possível abrir o A1/PFX com esta senha.") from exc
    if parsed_certificate is None:
        raise ValueError("O arquivo não contém um certificado A1 válido.")
    fingerprint = hashlib.sha256(pfx_bytes).hexdigest()
    valid_from = parsed_certificate.not_valid_before_utc
    valid_until = parsed_certificate.not_valid_after_utc
    certificate = Certificate.objects.create(
        organization=company.organization,
        company=company,
        label=label,
        pfx_blob=base64.b64encode(pfx_bytes).decode("ascii"),
        password=password,
        fingerprint_sha256=fingerprint,
        subject_name=parsed_certificate.subject.rfc4514_string()[:240],
        valid_from=valid_from,
        valid_until=valid_until,
        uploaded_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    record_event(
        action="hub.certificate.uploaded",
        actor=actor,
        organization=company.organization,
        target=certificate,
        request=request,
        metadata={"fingerprint_prefix": fingerprint[:12]},
    )
    return certificate


def integration_artifact_export(artifact: IntegrationArtifact) -> str:
    """Contract v1: a derived artifact only. The immutable original XML is never altered."""
    return json.dumps(artifact.payload, ensure_ascii=False, sort_keys=True)


@transaction.atomic
def prepare_dte_run(
    *,
    organization: Any,
    connector: Connector | None,
    companies: list[ClientCompany],
    actor: Any = None,
    request: Any = None,
) -> DteRun:
    """Persist the operator's scope before a separately-authorized Serpro dispatch.

    This deliberately creates no network request. The later dispatcher must require a
    confirmed ConsumptionConfirmation and configured mTLS credentials.
    """

    if not companies:
        raise ValueError("Selecione pelo menos uma empresa.")
    if any(company.organization_id != organization.id for company in companies):
        raise ValueError("Todas as empresas precisam pertencer ao mesmo escrit\u00f3rio.")
    run = DteRun.objects.create(
        organization=organization,
        connector=connector,
        requested_by=actor if getattr(actor, "is_authenticated", False) else None,
        total_companies=len(companies),
    )
    DteRunItem.objects.bulk_create(
        [DteRunItem(organization=organization, run=run, company=company) for company in companies]
    )
    record_event(
        action="hub.dte.run_prepared",
        actor=actor,
        organization=organization,
        target=run,
        request=request,
        metadata={"companies": len(companies), "network_dispatched": False},
    )
    return run
