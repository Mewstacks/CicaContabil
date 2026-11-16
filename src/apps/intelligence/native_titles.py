"""Private authenticated raw title intake; no normalized titles or postings are created."""

from __future__ import annotations

import base64
import binascii
import hashlib
import heapq
from typing import Any

from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.audit.services import record_event
from apps.hub.models import ClientCompany, FinancialAccount, ReconciliationSourceFile
from apps.hub.title_persistence import authorize_title_account
from apps.hub.title_requests import title_job_company, validate_title_job
from apps.intelligence.agent_scope import ACTIVE_PORTFOLIO_VERSION
from apps.intelligence.agent_v2 import agent_error, authenticated_agent
from apps.intelligence.models import CompanyTitleCollection, EdgeAgent, NativeTitleCollection
from apps.intelligence.native_title_contract import (
    MAX_BYTES,
    canonical_hash,
    contract_hash,
    is_automatic_scope,
    review_summary,
    snapshot_version,
    strict_json,
    validate_scope,
    validate_snapshot,
)

type TitleJob = NativeTitleCollection | CompanyTitleCollection


def _payload(request: HttpRequest, limit: int) -> dict[str, Any] | None:
    try:
        return strict_json(request.body, limit)
    except ValueError:
        return None


def _official(request: HttpRequest) -> EdgeAgent | None:
    agent = authenticated_agent(request, lock=True)
    if (
        agent is None
        or not agent.is_official
        or agent.status != EdgeAgent.Status.ACTIVE
        or not isinstance(agent.sync_scope, dict)
        or agent.sync_scope.get("version") != ACTIVE_PORTFOLIO_VERSION
    ):
        return None
    return agent


def _valid(job: TitleJob, agent: EdgeAgent) -> bool:
    if isinstance(job, CompanyTitleCollection):
        return (
            job.agent_id == agent.id
            and job.organization_id == agent.organization_id
            and is_automatic_scope(job.scope)
            and validate_title_job(job)
        )
    account = job.financial_account
    try:
        scope = validate_scope(job.scope)
        if is_automatic_scope(scope):
            return False
        authorize_title_account(account, job.requested_by)
        return (
            job.agent_id == agent.id
            and job.organization_id == agent.organization_id
            and account.organization_id == agent.organization_id
            and account.company.organization_id == agent.organization_id
            and account.company.dominio_code == str(scope["company_code"])
            and account.ledger_code == str(scope["comparison_bank_account_code"])
            and str(job.id) == scope["capture_id"]
            and job.scope_revision == canonical_hash(scope)
            and job.contract_hash == contract_hash()
            and bool(job.evidence_reference.strip())
        )
    except (ValueError, PermissionDenied):
        return False


def _retained(source: ReconciliationSourceFile, job: TitleJob, digest: str) -> bool:
    account_id = job.financial_account_id if isinstance(job, NativeTitleCollection) else None
    if (
        source.organization_id != job.organization_id
        or source.company_id != title_job_company(job).pk
        or source.financial_account_id != account_id
        or source.origin != "obligation"
        or source.kind != "json"
        or source.content_hash != digest
        or not 1 <= source.size_bytes <= MAX_BYTES
    ):
        return False
    try:
        with source.content.open("rb") as stream:
            content = stream.read(MAX_BYTES + 1)
        return len(content) == source.size_bytes and hashlib.sha256(content).hexdigest() == digest
    except (OSError, ValueError):
        return False


def _locked_job(job_id: str, agent: EdgeAgent) -> TitleJob | None:
    # Requests/configuration share Agent → Company → Account (legacy only) → Job.
    # Two tables deliberately isolate v2 from old runtimes. An ambiguous UUID
    # cannot be delivered or completed through their common endpoint.
    legacy = (
        NativeTitleCollection.objects.filter(
            pk=job_id, agent=agent, organization=agent.organization
        )
        .select_related("financial_account__company")
        .first()
    )
    company_job = (
        CompanyTitleCollection.objects.filter(
            pk=job_id, agent=agent, organization=agent.organization
        )
        .select_related("company")
        .first()
    )
    if (legacy is None) == (company_job is None):
        return None
    candidate: TitleJob
    if legacy is not None:
        candidate = legacy
    else:
        assert company_job is not None
        candidate = company_job
    company_id = title_job_company(candidate).pk
    if (
        not ClientCompany.objects.select_for_update()
        .filter(pk=company_id, organization_id=agent.organization_id)
        .exists()
    ):
        return None
    if isinstance(candidate, NativeTitleCollection):
        if (
            not FinancialAccount.objects.select_for_update()
            .filter(
                pk=candidate.financial_account_id,
                company_id=company_id,
                organization_id=agent.organization_id,
            )
            .exists()
        ):
            return None
        return (
            NativeTitleCollection.objects.select_for_update(of=("self",))
            .select_related(
                "financial_account__company", "financial_account__organization", "requested_by"
            )
            .filter(pk=job_id, agent=agent, organization=agent.organization)
            .first()
        )
    return (
        CompanyTitleCollection.objects.select_for_update(of=("self",))
        .select_related("company", "requested_by")
        .filter(pk=job_id, agent=agent, organization=agent.organization)
        .first()
    )


@csrf_exempt
@require_POST
@transaction.atomic
def next_job(request: HttpRequest) -> JsonResponse:
    agent = _official(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    payload = _payload(request, 1024)
    automatic = (
        isinstance(payload, dict)
        and set(payload) == {"version", "company_scope", "automatic_counts"}
        and payload["version"] == "1.0.9"
        and payload["company_scope"] is True
        and payload["automatic_counts"] is True
    )
    if not automatic and payload != {"version": "1.0.9"}:
        return agent_error("Versão de captura fiscal incompatível.", 400)
    agent.title_capabilities = {
        "version": "1.0.9",
        "company_scope": automatic,
        "automatic_counts": automatic,
    }
    agent.title_capabilities_observed_at = timezone.now()
    agent.save(update_fields=["title_capabilities", "title_capabilities_observed_at"])
    legacy = NativeTitleCollection.objects.filter(
        agent=agent, organization=agent.organization, state="queued"
    ).order_by("updated_at", "created_at", "id")
    company_jobs = CompanyTitleCollection.objects.filter(
        agent=agent, organization=agent.organization, state="queued"
    ).order_by("updated_at", "created_at", "id")
    candidates = heapq.merge(
        legacy.iterator(),
        company_jobs.iterator() if automatic else iter(()),
        key=lambda item: (item.updated_at, item.created_at, str(item.pk)),
    )
    result: dict[str, Any] = {
        "job": None,
        "review_required": NativeTitleCollection.objects.filter(
            agent=agent, organization=agent.organization, state__in=["captured", "review"]
        ).exists()
        or CompanyTitleCollection.objects.filter(
            agent=agent, organization=agent.organization, state__in=["captured", "review"]
        ).exists(),
    }
    job: TitleJob | None = None
    invalid_pending = False
    for candidate in candidates:
        locked = _locked_job(str(candidate.pk), agent)
        if locked is not None and _valid(locked, agent):
            job = locked
            break
        invalid_pending = True
    if invalid_pending:
        result["review_required"] = True
        if job is None:
            return agent_error("Escopo ou autorização de captura fiscal incompatível.", 409)
    if job is not None:
        if isinstance(job, CompanyTitleCollection) and job.claimed_at is None:
            job.claimed_at = timezone.now()
            job.save(update_fields=["claimed_at"])
        result["job"] = {
            "id": str(job.id),
            "version": snapshot_version(job.scope),
            "scope": job.scope,
            "scope_revision": job.scope_revision,
            "contract_hash": job.contract_hash,
        }
    response = JsonResponse(result)
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_POST
@transaction.atomic
def complete_job(request: HttpRequest, job_id: str) -> JsonResponse:
    agent = _official(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    payload = _payload(request, 5_400_000)
    if payload is None or set(payload) != {
        "scope_revision",
        "contract_hash",
        "content_sha256",
        "content_base64",
    }:
        return agent_error("Fotografia fiscal inválida.", 400)
    job = _locked_job(job_id, agent)
    if job is None:
        return agent_error("Captura não encontrada.", 404)
    if (
        not _valid(job, agent)
        or payload["scope_revision"] != job.scope_revision
        or payload["contract_hash"] != job.contract_hash
    ):
        return agent_error("Escopo ou autorização de captura fiscal incompatível.", 409)
    try:
        encoded = payload["content_base64"]
        if not isinstance(encoded, str) or len(encoded) > (MAX_BYTES + 2) // 3 * 4:
            raise ValueError
        content = base64.b64decode(encoded, validate=True)
        digest = hashlib.sha256(content).hexdigest()
        if digest != payload["content_sha256"]:
            raise ValueError
        snapshot = validate_snapshot(content, job.scope)
    except (ValueError, TypeError, binascii.Error):
        return agent_error("Fotografia fora do contrato fiscal.", 400)
    if job.state != "queued":
        if (
            job.state == "captured"
            and job.content_hash == digest
            and job.source_file is not None
            and _retained(job.source_file, job, digest)
            and job.result == review_summary(snapshot)
        ):
            return JsonResponse({"state": job.state, "result": job.result})
        return agent_error("Captura encerrada, divergente ou fonte privada indisponível.", 409)
    source = ReconciliationSourceFile.objects.filter(
        organization=agent.organization, company=title_job_company(job), content_hash=digest
    ).first()
    if source is not None and not _retained(source, job, digest):
        return agent_error("Fonte privada existente incompatível.", 409)
    created_file = False
    if source is None:
        source = ReconciliationSourceFile(
            organization=agent.organization,
            company=title_job_company(job),
            financial_account=job.financial_account
            if isinstance(job, NativeTitleCollection)
            else None,
            kind="json",
            origin="obligation",
            original_filename=f"dominio-fiscal-titles-{job.id}.json",
            content_hash=digest,
            content_type="application/json",
            size_bytes=len(content),
        )
        source.content.save(source.original_filename, ContentFile(content), save=False)
        created_file = True
    try:
        if created_file:
            source.save()
        job.source_file = source
        job.content_hash = digest
        job.state = NativeTitleCollection.State.CAPTURED
        job.completed_at = timezone.now()
        job.error_code = ""
        job.result = review_summary(snapshot)
        job.save(
            update_fields=[
                "source_file",
                "content_hash",
                "state",
                "completed_at",
                "error_code",
                "result",
                "updated_at",
            ]
        )
        record_event(
            action="intelligence.native_titles_captured",
            organization=agent.organization,
            actor=job.requested_by,
            target=job,
            request=request,
            metadata={
                "source_file_id": str(source.id),
                "content_hash": digest,
                "scope_revision": job.scope_revision,
                "requires_semantic_review": True,
            },
        )
    except Exception:
        if created_file:
            source.content.delete(save=False)
        raise
    return JsonResponse({"state": job.state, "result": job.result})


@csrf_exempt
@require_POST
@transaction.atomic
def fail_job(request: HttpRequest, job_id: str) -> JsonResponse:
    agent = _official(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    payload = _payload(request, 2048)
    if (
        payload is None
        or set(payload) != {"scope_revision", "contract_hash", "code"}
        or payload["code"] not in {"source_changed", "source_contract", "source_unavailable"}
    ):
        return agent_error("Diagnóstico fiscal inválido.", 400)
    job = _locked_job(job_id, agent)
    if job is None:
        return agent_error("Captura não encontrada.", 404)
    if (
        not _valid(job, agent)
        or payload["scope_revision"] != job.scope_revision
        or payload["contract_hash"] != job.contract_hash
    ):
        return agent_error("Escopo ou autorização de captura fiscal incompatível.", 409)
    if job.state == "queued":
        job.error_code = payload["code"]
        if payload["code"] == "source_contract":
            job.state = NativeTitleCollection.State.REVIEW
        job.save(update_fields=["error_code", "state", "updated_at"])
    return JsonResponse({"state": job.state})
