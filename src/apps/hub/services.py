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
    DctfWebDocument,
    DteRun,
    DteRunItem,
    FiscalGuide,
    IntegrationArtifact,
    NfseDocument,
    ParcelamentoOperation,
    ReviewCase,
)
from apps.platform.billing import BillingError, quote_usage, reserve_usage
from apps.platform.token_billing import quote_tokens, reserve_tokens


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
        company=company,
        document_hash=digest,
        defaults={
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


@transaction.atomic
def prepare_dte_next_page(
    *, source_item: DteRunItem, actor: Any = None, request: Any = None
) -> DteRun:
    """Prepare exactly one additional Serpro page; approval and billing stay separate."""

    source = (
        DteRunItem.objects.select_for_update()
        .select_related("run", "company")
        .get(id=source_item.id)
    )
    if source.status != DteRunItem.Status.COMPLETED or not source.more_available:
        raise ValueError("Esta consulta não tem outra página disponível.")
    if not re.fullmatch(r"\d{1,24}", source.next_page_pointer):
        raise ValueError("Falta o ponteiro da próxima página. Atualize a primeira consulta.")
    if DteRunItem.objects.filter(continued_from=source).exists():
        raise ValueError("A próxima página desta consulta já foi preparada.")
    run = DteRun.objects.create(
        organization=source.organization,
        connector=source.run.connector,
        requested_by=actor if getattr(actor, "is_authenticated", False) else None,
        total_companies=1,
    )
    DteRunItem.objects.create(
        organization=source.organization,
        run=run,
        company=source.company,
        requested_page_pointer=source.next_page_pointer,
        continued_from=source,
    )
    record_event(
        action="hub.dte.next_page_prepared",
        actor=actor,
        organization=source.organization,
        target=run,
        request=request,
        metadata={"source_item_id": str(source.id), "network_dispatched": False},
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


class DctfWebDocumentTransitionError(RuntimeError):
    """A DCTFWeb document cannot be consulted from its current state."""


@transaction.atomic
def prepare_dctfweb_guide_from_documents(
    *,
    organization: Any,
    company: ClientCompany,
    competence: str,
    due_on: date,
    amount_cents: int,
    source_reference: str,
    actor: Any = None,
    request: Any = None,
) -> FiscalGuide:
    """Promote one governed Domínio calculation after both official PDFs exist."""

    if company.organization_id != organization.id or not company.active:
        raise DctfWebDocumentTransitionError("A empresa não pertence à carteira ativa.")
    if re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", competence) is None:
        raise DctfWebDocumentTransitionError("Informe uma competência no formato MM/AAAA.")
    if amount_cents < 1 or not source_reference:
        raise DctfWebDocumentTransitionError(
            "A apuração do Domínio não possui valor e referência válidos."
        )
    available_kinds = set(
        DctfWebDocument.objects.filter(
            organization=organization,
            company=company,
            competence=competence,
            status=DctfWebDocument.Status.AVAILABLE,
        ).values_list("kind", flat=True)
    )
    required = {
        DctfWebDocument.Kind.DECLARATION,
        DctfWebDocument.Kind.RECEIPT,
    }
    if not required.issubset(available_kinds):
        raise DctfWebDocumentTransitionError(
            "Baixe e confira a declaração completa e o recibo antes de preparar a emissão."
        )

    reference = f"dominio-dctfweb-{company.dominio_code}-{competence[3:]}{competence[:2]}"
    guide, created = FiscalGuide.objects.select_for_update().get_or_create(
        organization=organization,
        company=company,
        reference=reference,
        defaults={
            "kind": FiscalGuide.Kind.DCTFWEB,
            "status": FiscalGuide.Status.READY,
            "competence": competence,
            "due_on": due_on,
            "amount_cents": amount_cents,
            "integra_service_key": "dctfweb.guia",
            "external_key": source_reference[:160],
            "source_updated_at": timezone.now(),
        },
    )
    if not created:
        if guide.status in {
            FiscalGuide.Status.QUEUED,
            FiscalGuide.Status.ISSUING,
            FiscalGuide.Status.ISSUED,
        }:
            return guide
        guide.kind = FiscalGuide.Kind.DCTFWEB
        guide.status = FiscalGuide.Status.READY
        guide.competence = competence
        guide.due_on = due_on
        guide.amount_cents = amount_cents
        guide.integra_service_key = "dctfweb.guia"
        guide.external_key = source_reference[:160]
        guide.source_updated_at = timezone.now()
        guide.error_code = ""
        guide.error_message = ""
        guide.save()
    record_event(
        action="hub.dctfweb.guide_prepared",
        actor=actor,
        organization=organization,
        target=guide,
        request=request,
        metadata={
            "competence": competence,
            "source_reference": source_reference[:160],
            "documents": sorted(required),
            "created": created,
        },
    )
    return guide


class ParcelamentoTransitionError(RuntimeError):
    """A PARCSN operation cannot be queued in its current state."""


DCTFWEB_DOCUMENT_SERVICE = {
    DctfWebDocument.Kind.DECLARATION: "dctfweb.declaracao_completa",
    DctfWebDocument.Kind.RECEIPT: "dctfweb.recibo",
}

PARCELAMENTO_SERVICE = {
    ParcelamentoOperation.Kind.ORDERS: "parcelamento.parcsn.pedidos",
    ParcelamentoOperation.Kind.DETAIL: "parcelamento.parcsn.detalhe",
    ParcelamentoOperation.Kind.INSTALLMENTS: "parcelamento.parcsn.parcelas",
    ParcelamentoOperation.Kind.DAS: "parcelamento.parcsn.das",
}


@transaction.atomic
def request_parcelamento_operation(
    *,
    organization: Any,
    company: ClientCompany,
    kind: str,
    agreement_number: int | None = None,
    competence: str = "",
    actor: Any = None,
    request: Any = None,
    approved_overage_cents: int = 0,
) -> ParcelamentoOperation:
    """Reserve the quoted PARCSN action before dispatching it once."""

    if company.organization_id != organization.id or not company.active:
        raise ParcelamentoTransitionError("A empresa não pertence à carteira ativa.")
    try:
        service_key = PARCELAMENTO_SERVICE[kind]
    except KeyError as exc:
        raise ParcelamentoTransitionError("Escolha uma operação de parcelamento válida.") from exc
    if kind == ParcelamentoOperation.Kind.DETAIL:
        if agreement_number is None or agreement_number < 1:
            raise ParcelamentoTransitionError("Informe um acordo válido para consultar o detalhe.")
    elif agreement_number is not None:
        raise ParcelamentoTransitionError("Esta operação não aceita número de acordo.")
    if kind == ParcelamentoOperation.Kind.DAS:
        if re.fullmatch(r"\d{4}(0[1-9]|1[0-2])", competence) is None:
            raise ParcelamentoTransitionError("Informe a parcela no formato AAAAMM.")
    elif competence:
        raise ParcelamentoTransitionError("Esta operação não aceita competência.")
    try:
        normalize_cnpj(company.cnpj_masked)
    except ValidationError as exc:
        raise ParcelamentoTransitionError(
            "Confira o CNPJ da empresa antes de consultar o parcelamento."
        ) from exc

    previous = (
        ParcelamentoOperation.objects.select_for_update()
        .filter(
            organization=organization,
            company=company,
            kind=kind,
            agreement_number=agreement_number,
            competence=competence,
        )
        .first()
    )
    if previous and previous.status in {
        ParcelamentoOperation.Status.QUEUED,
        ParcelamentoOperation.Status.FETCHING,
        ParcelamentoOperation.Status.UNKNOWN,
    }:
        raise ParcelamentoTransitionError(
            "Essa operação já está na fila ou aguardando confirmação."
        )
    if (
        previous
        and kind == ParcelamentoOperation.Kind.DAS
        and previous.status == ParcelamentoOperation.Status.AVAILABLE
    ):
        raise ParcelamentoTransitionError("O DAS desta competência já foi emitido.")
    operation = ParcelamentoOperation(
        organization=organization,
        company=company,
        kind=kind,
        agreement_number=agreement_number,
        competence=competence,
        attempt=(previous.attempt + 1 if previous else 1),
    )
    if not organization.is_demo:
        try:
            live_quote = quote_tokens(
                organization=organization,
                module_code="integra",
                action_code=service_key,
            )
            if live_quote.additional_overage_cents != approved_overage_cents:
                raise ParcelamentoTransitionError(
                    "O custo em tokens mudou. Revise e confirme novamente."
                )
            operation.token_usage_event = reserve_tokens(
                organization=organization,
                module_code="integra",
                action_code=service_key,
                idempotency_key=f"parcelamento:{operation.id}:{operation.attempt}",
            )
        except BillingError as exc:
            raise ParcelamentoTransitionError(str(exc)) from exc
    operation.service_key = service_key
    operation.status = ParcelamentoOperation.Status.QUEUED
    operation.requested_by = actor if getattr(actor, "is_authenticated", False) else None
    operation.requested_at = timezone.now()
    operation.completed_at = None
    operation.provider_request_id = ""
    operation.provider_payload = ""
    operation.error_code = ""
    operation.error_message = ""
    operation.save()

    from apps.hub.tasks import dispatch_parcelamento_operation

    if organization.is_demo:
        transaction.on_commit(lambda: dispatch_parcelamento_operation.run(str(operation.id)))
    else:
        transaction.on_commit(lambda: dispatch_parcelamento_operation.delay(str(operation.id)))
    record_event(
        action="hub.parcelamento.requested",
        actor=actor,
        organization=organization,
        target=operation,
        request=request,
        metadata={
            "kind": kind,
            "agreement_number": agreement_number,
            "competence": competence,
            "service": service_key,
        },
    )
    return operation


@transaction.atomic
def request_dctfweb_document(
    *,
    organization: Any,
    company: ClientCompany,
    competence: str,
    kind: str,
    actor: Any = None,
    request: Any = None,
    approved_overage_cents: int = 0,
) -> DctfWebDocument:
    """Reserve exactly the quoted consultation before it reaches the worker."""

    if company.organization_id != organization.id or not company.active:
        raise DctfWebDocumentTransitionError("A empresa não pertence à carteira ativa.")
    if re.fullmatch(r"(0[1-9]|1[0-2])/\d{4}", competence) is None:
        raise DctfWebDocumentTransitionError("Informe uma competência no formato MM/AAAA.")
    try:
        service_key = DCTFWEB_DOCUMENT_SERVICE[kind]
    except KeyError as exc:
        raise DctfWebDocumentTransitionError("Escolha declaração completa ou recibo.") from exc
    try:
        normalize_cnpj(company.cnpj_masked)
    except ValidationError as exc:
        raise DctfWebDocumentTransitionError(
            "Confira o CNPJ da empresa antes de consultar a DCTFWeb."
        ) from exc

    document, _created = DctfWebDocument.objects.select_for_update().get_or_create(
        organization=organization,
        company=company,
        competence=competence,
        kind=kind,
        defaults={"service_key": service_key},
    )
    if (
        document.status
        in {
            DctfWebDocument.Status.QUEUED,
            DctfWebDocument.Status.FETCHING,
            DctfWebDocument.Status.AVAILABLE,
            DctfWebDocument.Status.UNKNOWN,
        }
        and document.attempt
    ):
        raise DctfWebDocumentTransitionError(
            "Essa consulta já está na fila, concluída ou aguardando confirmação."
        )
    document.attempt += 1
    idempotency_key = f"dctfweb-document:{document.id}:{document.attempt}"
    if not organization.is_demo:
        try:
            live_quote = quote_tokens(
                organization=organization,
                module_code="integra",
                action_code=service_key,
            )
            if live_quote.additional_overage_cents != approved_overage_cents:
                raise DctfWebDocumentTransitionError(
                    "O custo em tokens mudou. Revise e confirme novamente."
                )
            usage = reserve_tokens(
                organization=organization,
                module_code="integra",
                action_code=service_key,
                idempotency_key=idempotency_key,
            )
        except BillingError as exc:
            raise DctfWebDocumentTransitionError(str(exc)) from exc
        document.token_usage_event = usage
    document.service_key = service_key
    document.status = DctfWebDocument.Status.QUEUED
    document.requested_by = actor if getattr(actor, "is_authenticated", False) else None
    document.requested_at = timezone.now()
    document.completed_at = None
    document.error_code = ""
    document.error_message = ""
    document.save()

    from apps.hub.tasks import dispatch_dctfweb_document

    if organization.is_demo:
        transaction.on_commit(lambda: dispatch_dctfweb_document.run(str(document.id)))
    else:
        transaction.on_commit(lambda: dispatch_dctfweb_document.delay(str(document.id)))
    record_event(
        action="hub.dctfweb.document_requested",
        actor=actor,
        organization=organization,
        target=document,
        request=request,
        metadata={"kind": kind, "competence": competence, "service": service_key},
    )
    return document


@transaction.atomic
def issue_fiscal_guide(
    *,
    guide: FiscalGuide,
    actor: Any = None,
    request: Any = None,
    approved_overage_cents: int = 0,
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
    if not guide.organization.is_demo:
        try:
            live_quote = quote_tokens(
                organization=guide.organization,
                module_code="integra",
                action_code=guide.integra_service_key,
            )
            if live_quote.additional_overage_cents != approved_overage_cents:
                raise FiscalGuideTransitionError(
                    "O custo em tokens mudou. Revise e confirme novamente."
                )
            reserve_tokens(
                organization=guide.organization,
                module_code="integra",
                action_code=guide.integra_service_key,
                idempotency_key=idempotency_key,
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

    if guide.organization.is_demo:
        transaction.on_commit(lambda: dispatch_fiscal_guide.run(str(guide.id)))
    else:
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
                "status": FiscalGuide.Status.DISCOVERED,
                "competence": competence,
                "due_on": due_on,
                "amount_cents": amount_cents,
                "integra_service_key": _GUIDE_SERVICE_BY_KIND[kind],
            },
        )
        if was_created:
            created += 1
            continue
        if guide.status not in {FiscalGuide.Status.DISCOVERED, FiscalGuide.Status.FAILED}:
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
    if run.organization.is_demo:
        quote = None
    else:
        try:
            quote = quote_tokens(
                organization=run.organization,
                module_code="integra",
                action_code=DTE_ACTION_CODE,
                operations=run.total_companies,
            )
        except BillingError as exc:
            try:
                quote = quote_usage(
                    organization=run.organization,
                    action_code=DTE_ACTION_CODE,
                    units=run.total_companies,
                )
            except BillingError:
                raise DteRunTransitionError(str(exc)) from exc
    additional_overage_cents = quote.additional_overage_cents if quote is not None else 0
    if additional_overage_cents and (
        not approved_overage or approved_overage_total_cents != quote.additional_overage_cents
    ):
        raise DteRunTransitionError(
            "O excedente desta consulta mudou ou não foi autorizado com o valor exato. "
            "Revise a fila antes de enviar."
        )
    # Reserve each outbound Caixa Postal call before it is queued. A failed reservation
    # means no provider request can escape the product and no unexpected overage occurs.
    for item in run.items.select_for_update().filter(status=DteRunItem.Status.PENDING):
        if run.organization.is_demo:
            continue
        try:
            key = f"dte-run-item:{item.id}:caixapostal"
            if hasattr(quote, "total_tokens"):
                usage = reserve_tokens(
                    organization=run.organization,
                    module_code="integra",
                    action_code=DTE_ACTION_CODE,
                    idempotency_key=key,
                )
                item.token_usage_event = usage
                item.save(update_fields=["token_usage_event", "updated_at"])
            else:
                usage = reserve_usage(
                    organization=run.organization,
                    action_code=DTE_ACTION_CODE,
                    idempotency_key=key,
                    approved_overage=approved_overage,
                    approved_overage_cents=(
                        quote.overage_unit_price_cents if approved_overage else None
                    ),
                    require_explicit_overage=True,
                )
                item.usage_event = usage
                item.save(update_fields=["usage_event", "updated_at"])
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

    if run.organization.is_demo:
        transaction.on_commit(lambda: dispatch_dte_run.run(str(run.id)))
    else:
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
