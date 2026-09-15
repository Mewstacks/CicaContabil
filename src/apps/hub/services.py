from __future__ import annotations

import base64
import hashlib
import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from cryptography.hazmat.primitives.serialization import pkcs12
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.cnpj import normalize_cnpj
from apps.hub.models import (
    AccumulatorObservation,
    AccumulatorRule,
    Certificate,
    ClientCompany,
    Connector,
    ConsumptionConfirmation,
    DteRun,
    DteRunItem,
    FiscalGuide,
    IntegrationArtifact,
    NfseDocument,
    ReviewCase,
)
from apps.platform.billing import BillingError, quote_usage, reserve_usage


@dataclass(frozen=True)
class ClassificationResult:
    accumulator_code: str
    confidence: int
    rule_name: str
    evidence: dict[str, object]
    needs_review: bool


@dataclass(frozen=True)
class FiscalGuideSyncResult:
    created: int
    updated: int
    ignored: int


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
        raise ValueError("Todas as empresas precisam pertencer ao mesmo escritório.")
    for company in companies:
        try:
            normalize_cnpj(company.cnpj_masked)
        except ValidationError as exc:
            raise ValueError(
                "Uma empresa selecionada está sem CNPJ válido. Revise o cadastro antes de preparar."
            ) from exc
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


class DteRunTransitionError(RuntimeError):
    """A run was asked for a transition its current status does not allow."""


# The catalogue key that a Caixa Postal consultation bills against. Kept here rather than
# imported so a change to the Integra catalogue cannot silently change what was approved.
DTE_ACTION_CODE = "caixapostal.mensagens"
DTE_DETAIL_ACTION_CODE = "caixapostal.detalhe"


class FiscalGuideTransitionError(RuntimeError):
    """An obligation cannot be sent from its current operational state."""


@transaction.atomic
def issue_fiscal_guide(
    *,
    guide: FiscalGuide,
    actor: Any = None,
    request: Any = None,
    approved_overage: bool = False,
) -> FiscalGuide:
    """Reserve one central issuance before queueing a Domínio obligation."""

    guide = FiscalGuide.objects.select_for_update().get(id=guide.id)
    if guide.status not in {FiscalGuide.Status.READY, FiscalGuide.Status.FAILED}:
        raise FiscalGuideTransitionError("Essa obrigação já está em emissão ou foi concluída.")
    try:
        normalize_cnpj(guide.company.cnpj_masked)
    except ValidationError as exc:
        raise FiscalGuideTransitionError(
            "Confira o CNPJ da empresa antes de autorizar a emissão."
        ) from exc
    guide.issue_attempt += 1
    idempotency_key = f"fiscal-guide:{guide.id}:{guide.issue_attempt}"
    try:
        reserve_usage(
            organization=guide.organization,
            action_code=guide.integra_service_key,
            idempotency_key=idempotency_key,
            approved_overage=approved_overage,
        )
    except BillingError as exc:
        raise FiscalGuideTransitionError(str(exc)) from exc
    guide.status = FiscalGuide.Status.QUEUED
    guide.issue_requested_by = actor if getattr(actor, "is_authenticated", False) else None
    guide.issue_requested_at = timezone.now()
    guide.error_code = ""
    guide.error_message = ""
    guide.save(
        update_fields=[
            "status",
            "issue_attempt",
            "issue_requested_by",
            "issue_requested_at",
            "error_code",
            "error_message",
            "updated_at",
        ]
    )
    from apps.hub.tasks import dispatch_fiscal_guide

    transaction.on_commit(lambda: dispatch_fiscal_guide.delay(str(guide.id)))
    record_event(
        action="hub.fiscal_guide.issuance_requested",
        actor=actor,
        organization=guide.organization,
        target=guide,
        request=request,
        metadata={
            "kind": guide.kind,
            "competence": guide.competence,
            "service": guide.integra_service_key,
        },
    )
    return guide


_GUIDE_SERVICE_BY_KIND: dict[str, str] = {
    FiscalGuide.Kind.DCTFWEB: "dctfweb.guia",
    FiscalGuide.Kind.DAS: "pgdasd.das",
    FiscalGuide.Kind.MEI: "pgmei.das",
}


@transaction.atomic
def sync_fiscal_guides(
    *, organization: Any, rows: list[dict[str, object]]
) -> FiscalGuideSyncResult:
    """Accept the bounded obligation snapshot emitted by the local Domínio agent."""

    companies = {
        company.dominio_code: company
        for company in ClientCompany.objects.filter(organization=organization, active=True)
        if company.dominio_code
    }
    created = updated = ignored = 0
    for row in rows:
        company = companies.get(str(row.get("company_code", "")).strip())
        reference = str(row.get("reference", "")).strip()
        kind = str(row.get("kind", "")).strip()
        competence = str(row.get("competence", "")).strip()
        try:
            due_on = datetime.strptime(str(row.get("due_on", "")), "%Y-%m-%d").date()
            amount_cents = int(str(row.get("amount_cents", 0)))
        except (TypeError, ValueError):
            ignored += 1
            continue
        if (
            company is None
            or not reference
            or kind not in FiscalGuide.Kind.values
            or re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", competence) is None
            or amount_cents < 0
        ):
            ignored += 1
            continue
        guide, was_created = FiscalGuide.objects.get_or_create(
            organization=organization,
            company=company,
            reference=reference[:120],
            defaults={
                "kind": kind,
                "competence": competence,
                "due_on": due_on,
                "amount_cents": amount_cents,
                "integra_service_key": _GUIDE_SERVICE_BY_KIND[kind],
            },
        )
        if was_created:
            created += 1
            continue
        if guide.status not in {FiscalGuide.Status.READY, FiscalGuide.Status.FAILED}:
            ignored += 1
            continue
        guide.kind = kind
        guide.competence = competence
        guide.due_on = due_on
        guide.amount_cents = amount_cents
        guide.integra_service_key = _GUIDE_SERVICE_BY_KIND[kind]
        guide.save(
            update_fields=[
                "kind",
                "competence",
                "due_on",
                "amount_cents",
                "integra_service_key",
                "updated_at",
            ]
        )
        updated += 1
    return FiscalGuideSyncResult(created=created, updated=updated, ignored=ignored)


@transaction.atomic
def approve_dte_run(
    *,
    run: DteRun,
    actor: Any = None,
    request: Any = None,
    approved_overage: bool = False,
    approved_overage_total_cents: int | None = None,
) -> ConsumptionConfirmation:
    """Record the consumption the operator is authorizing, and release the run.

    CICA owns the Serpro credentials; the office only approves its operational
    scope.  The queued worker later performs the centrally metered dispatch.
    """

    if run.status != DteRun.Status.AWAITING_APPROVAL:
        raise DteRunTransitionError("Esta consulta já saiu da fila de autorização.")
    for item in run.items.select_related("company"):
        try:
            normalize_cnpj(item.company.cnpj_masked)
        except ValidationError as exc:
            raise DteRunTransitionError(
                "Uma empresa desta consulta está sem CNPJ válido. Retire a preparação, "
                "revise o cadastro e prepare novamente antes de autorizar consumo."
            ) from exc
    try:
        quote = quote_usage(
            organization=run.organization,
            action_code=DTE_ACTION_CODE,
            units=run.total_companies,
        )
    except BillingError as exc:
        raise DteRunTransitionError(str(exc)) from exc
    if quote.additional_overage_units and (
        not approved_overage
        or approved_overage_total_cents != quote.additional_overage_cents
    ):
        raise DteRunTransitionError(
            "O excedente desta consulta mudou ou não foi autorizado com o valor exato. "
            "Revise a fila antes de enviar."
        )
    # Reserve each outbound Caixa Postal call before it is queued. A failed reservation
    # means no provider request can escape the product and no unexpected overage occurs.
    for item in run.items.select_for_update().filter(status=DteRunItem.Status.PENDING):
        try:
            reserve_usage(
                organization=run.organization,
                action_code=DTE_ACTION_CODE,
                idempotency_key=f"dte-run-item:{item.id}:caixapostal",
                approved_overage=approved_overage,
                approved_overage_cents=(
                    quote.overage_unit_price_cents if approved_overage else None
                ),
                require_explicit_overage=True,
            )
        except BillingError as exc:
            raise DteRunTransitionError(str(exc)) from exc

    confirmation = ConsumptionConfirmation.objects.create(
        organization=run.organization,
        connector=run.connector,
        action_code=DTE_ACTION_CODE,
        scope_summary=f"Caixa Postal de {run.total_companies} empresa(s).",
        estimated_units=run.total_companies,
        status="confirmed",
        confirmed_by=actor if getattr(actor, "is_authenticated", False) else None,
        confirmed_at=timezone.now(),
    )
    run.status = DteRun.Status.QUEUED
    run.save(update_fields=["status", "updated_at"])
    from apps.hub.tasks import dispatch_dte_run

    transaction.on_commit(lambda: dispatch_dte_run.delay(str(run.id)))
    record_event(
        action="hub.dte.run_approved",
        actor=actor,
        organization=run.organization,
        target=run,
        request=request,
        metadata={
            "companies": run.total_companies,
            "action_code": DTE_ACTION_CODE,
            "queued_for_central_dispatch": True,
        },
    )
    return confirmation


@transaction.atomic
def cancel_dte_run(
    *,
    run: DteRun,
    actor: Any = None,
    request: Any = None,
) -> DteRun:
    """Withdraw a run the operator decided not to authorize.

    Without this the only way out of the approval queue is approving, so a scope chosen
    by mistake stays on the screen forever.
    """

    if run.status != DteRun.Status.AWAITING_APPROVAL:
        raise DteRunTransitionError("Esta consulta já saiu da fila de autorização.")

    run.status = DteRun.Status.CANCELLED
    run.completed_at = timezone.now()
    run.save(update_fields=["status", "completed_at", "updated_at"])
    run.items.filter(status=DteRunItem.Status.PENDING).update(status=DteRunItem.Status.SKIPPED)
    record_event(
        action="hub.dte.run_cancelled",
        actor=actor,
        organization=run.organization,
        target=run,
        request=request,
        metadata={"companies": run.total_companies},
    )
    return run
