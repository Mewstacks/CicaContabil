"""Official-agent intake of one frozen, privately retained native ledger snapshot."""

from __future__ import annotations

import base64
import binascii
import hashlib
from typing import Any

from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.db import transaction
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.hub.models import ReconciliationSourceFile
from apps.hub.native_ledger_import import import_native_source
from apps.hub.title_persistence import authorize_title_account
from apps.intelligence.agent_v2 import agent_error, agent_payload, authenticated_agent
from apps.intelligence.models import EdgeAgent, NativeLedgerCollection
from apps.intelligence.native_ledger_contract import (
    MAX_BYTES,
    VERSION,
    canonical_hash,
    contract_hash,
    normalize_snapshot,
    pilot_scope,
    validate_scope,
    validate_snapshot,
)


def _job_valid(job: NativeLedgerCollection, agent: EdgeAgent) -> bool:
    account = job.financial_account
    try:
        scope = validate_scope(job.scope)
        if job.requested_by_id:
            if not job.evidence_reference.strip() or job.requested_by is None:
                return False
            authorize_title_account(account, job.requested_by)
        elif scope != pilot_scope():
            return False
        return (
            job.organization_id == agent.organization_id
            and job.agent_id == agent.id
            and account.organization_id == agent.organization_id
            and account.company.organization_id == agent.organization_id
            and account.company.dominio_code == str(scope["company_code"])
            and account.ledger_code == str(scope["bank_account_code"])
            and account.active
            and bool(account.account_reference)
            and job.scope_revision == canonical_hash(scope)
            and job.contract_hash == contract_hash()
        )
    except (ValueError, PermissionDenied):
        return False


def _official(request: HttpRequest) -> EdgeAgent | None:
    agent = authenticated_agent(request, lock=True)
    if agent is None or not agent.is_official or agent.status != EdgeAgent.Status.ACTIVE:
        return None
    return agent


@csrf_exempt
@require_POST
@transaction.atomic
def next_job(request: HttpRequest) -> JsonResponse:
    agent = _official(request)
    if agent is None:
        return agent_error("Agente não autorizado.", 401)
    payload = agent_payload(request, 1024)
    expanded = payload == {"version": "1.0.8", "portfolio_scope": True}
    if not expanded and payload != {"version": "1.0.8"}:
        return agent_error("Versão de coleta nativa incompatível.", 400)
    jobs = (
        NativeLedgerCollection.objects.select_for_update()
        .select_related("financial_account__company")
        .filter(agent=agent, organization=agent.organization, state="queued")
    )
    if not expanded:
        jobs = jobs.filter(scope_revision=canonical_hash(pilot_scope()))
    job = jobs.order_by("created_at").first()
    result: dict[str, Any] = {
        "job": None,
        "review_required": (
            NativeLedgerCollection.objects.filter(
                agent=agent, organization=agent.organization, state="review"
            ).exists()
        ),
    }
    if job is not None:
        if not _job_valid(job, agent):
            return agent_error("Escopo de coleta nativa incompatível.", 409)
        result["job"] = {
            "id": str(job.id),
            "version": VERSION,
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
    payload = agent_payload(request, 2_800_000)
    if payload is None or set(payload) != {
        "scope_revision",
        "contract_hash",
        "content_sha256",
        "content_base64",
    }:
        return agent_error("Snapshot nativo inválido.", 400)
    job = (
        NativeLedgerCollection.objects.select_for_update()
        .select_related("financial_account__company")
        .filter(id=job_id, agent=agent, organization=agent.organization)
        .first()
    )
    if job is None:
        return agent_error("Coleta não encontrada.", 404)
    if (
        not _job_valid(job, agent)
        or payload["scope_revision"] != job.scope_revision
        or payload["contract_hash"] != job.contract_hash
    ):
        return agent_error("Escopo de coleta nativa incompatível.", 409)
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
        return agent_error("Snapshot fora do contrato nativo.", 400)
    if job.state != NativeLedgerCollection.State.QUEUED:
        if job.content_hash == digest and job.state in {"imported", "review"}:
            return JsonResponse({"state": job.state, "result": job.result})
        return agent_error("Coleta já encerrada ou conteúdo divergente.", 409)
    source = ReconciliationSourceFile.objects.filter(
        organization=agent.organization, company=job.financial_account.company, content_hash=digest
    ).first()
    if source is not None and (
        source.financial_account_id != job.financial_account_id
        or source.kind != "json"
        or source.origin != "accounting"
    ):
        return agent_error("Arquivo existente com escopo divergente.", 409)
    saved = False
    if source is None:
        source = ReconciliationSourceFile(
            organization=agent.organization,
            company=job.financial_account.company,
            financial_account=job.financial_account,
            kind="json",
            origin="accounting",
            original_filename=f"dominio-ledger-{job.id}.json",
            content_hash=digest,
            content_type="application/json",
            size_bytes=len(content),
        )
        source.content.save(source.original_filename, ContentFile(content), save=False)
        saved = True
    try:
        source.save()
        try:
            candidate = normalize_snapshot(snapshot, job.scope)
            job.result = import_native_source(
                source=source, candidate=candidate, snapshot=snapshot, job_id=str(job.id)
            )
            job.state = NativeLedgerCollection.State.IMPORTED
        except ValueError as error:
            # The nested import rolls back all journals; retain the original source for review.
            job.state = NativeLedgerCollection.State.REVIEW
            job.error_code = (
                "ledger_content_conflict"
                if str(error) == "ledger_content_conflict"
                else "ledger_import_review"
            )
            job.result = {"source_rows": len(snapshot["records"]), "created": 0}
        job.source_file = source
        job.content_hash = digest
        job.completed_at = timezone.now()
        job.save(
            update_fields=[
                "state",
                "result",
                "error_code",
                "source_file",
                "content_hash",
                "completed_at",
                "updated_at",
            ]
        )
    except Exception:
        if saved:
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
    payload = agent_payload(request, 2048)
    if (
        payload is None
        or set(payload) != {"scope_revision", "contract_hash", "code"}
        or payload["code"] not in {"source_changed", "source_contract", "source_unavailable"}
    ):
        return agent_error("Diagnóstico de coleta inválido.", 400)
    job = (
        NativeLedgerCollection.objects.select_for_update()
        .select_related("financial_account__company")
        .filter(id=job_id, agent=agent, organization=agent.organization)
        .first()
    )
    if job is None:
        return agent_error("Coleta não encontrada.", 404)
    if (
        not _job_valid(job, agent)
        or payload["scope_revision"] != job.scope_revision
        or payload["contract_hash"] != job.contract_hash
    ):
        return agent_error("Escopo de coleta nativa incompatível.", 409)
    if job.state == "queued":
        # Technical transient failures remain retryable. Scope/data faults require review.
        job.error_code = payload["code"]
        if payload["code"] == "source_contract":
            job.state = NativeLedgerCollection.State.REVIEW
        job.save(update_fields=["state", "error_code", "updated_at"])
    return JsonResponse({"state": job.state})
