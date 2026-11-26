"""Windows-agent endpoints for folder jobs: create directories, inventory a tree.

Same claim/complete pattern and root check as ``AgentFileJob`` (agent_v2.next_file_job).
The agent never receives an absolute path: only relative directories the server re-validated.
"""

from __future__ import annotations

import hashlib
from datetime import timedelta
from pathlib import PureWindowsPath

from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.http import HttpRequest, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.audit.services import record_event
from apps.intelligence.agent_v2 import _agent, _error, _payload
from apps.triage.folders import MAX_PLAN_DIRS, _checked
from apps.triage.models import AgentFolderJob, DestinationProfile

_REPORT_LIMIT = 200
_STALE = timedelta(minutes=15)


def _safe_paths(job: AgentFolderJob) -> list[str]:
    raw = job.paths if isinstance(job.paths, list) else []
    if job.kind == AgentFolderJob.Kind.INVENTORY:
        return ["."]
    if not raw or len(raw) > MAX_PLAN_DIRS:
        raise ValidationError("Plano de pastas inválido.")
    return [_checked(str(path)) for path in raw]


@csrf_exempt
@require_POST
def next_folder_job(request: HttpRequest) -> JsonResponse:
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    now = timezone.now()
    with transaction.atomic():
        jobs = AgentFolderJob.objects.select_for_update(skip_locked=True).filter(
            organization=agent.organization
        )
        job = (
            jobs.filter(status=AgentFolderJob.Status.CLAIMED, claimed_by=str(agent.id))
            .order_by("claimed_at")
            .first()
        ) or (
            jobs.filter(
                models.Q(status=AgentFolderJob.Status.QUEUED)
                | models.Q(status=AgentFolderJob.Status.CLAIMED, claimed_at__lt=now - _STALE)
            )
            .order_by("created_at")
            .first()
        )
        if job is None:
            return JsonResponse({"job": None})
        profile = DestinationProfile.objects.filter(organization=agent.organization).first()
        failure = ""
        paths: list[str] = []
        if profile is None or profile.mode != DestinationProfile.Mode.WINDOWS:
            failure = "O destino Windows não está ativo."
        else:
            try:
                paths = _safe_paths(job)
            except ValidationError:
                failure = "Plano de pastas inválido."
        if failure:
            job.status = AgentFolderJob.Status.FAILED
            job.completed_at = now
            job.result = failure
            job.save(update_fields=["status", "completed_at", "result", "updated_at"])
            from apps.triage.folders import mark_job_result

            mark_job_result(job, success=False, detail=failure)
            return JsonResponse({"job": None})
        assert profile is not None
        job.status = AgentFolderJob.Status.CLAIMED
        job.claimed_by = str(agent.id)
        job.claimed_at = now
        job.save(update_fields=["status", "claimed_by", "claimed_at", "updated_at"])
        normalized_root = str(PureWindowsPath(profile.windows_root)).rstrip("\\").lower()
        root_sha256 = hashlib.sha256(normalized_root.encode("utf-8")).hexdigest()
    response = JsonResponse(
        {
            "job": {
                "id": str(job.id),
                "kind": job.kind,
                "paths": paths,
                "root_sha256": root_sha256,
            }
        }
    )
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_POST
def complete_folder_job(request: HttpRequest, job_id: str) -> JsonResponse:
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    payload = _payload(request, 262_144)
    if payload is None:
        return _error("Resultado de pastas inválido.", 400)
    success = payload.get("success") is True
    detail = str(payload.get("detail", ""))[:500]
    entries = payload.get("entries", [])
    with transaction.atomic():
        try:
            job = (
                AgentFolderJob.objects.select_for_update()
                .filter(id=job_id, organization=agent.organization)
                .first()
            )
        except (ValueError, ValidationError):
            job = None
        if job is None or job.claimed_by != str(agent.id):
            return _error("Trabalho de pastas não encontrado para este agente.", 404)
        if job.status == AgentFolderJob.Status.DONE:
            return JsonResponse({"status": "completed"})
        if job.status != AgentFolderJob.Status.CLAIMED:
            return _error("Este trabalho não aceita mais resultado.", 409)
        job.status = AgentFolderJob.Status.DONE if success else AgentFolderJob.Status.FAILED
        job.completed_at = timezone.now()
        job.result = detail or ("Pastas conferidas." if success else "O agente não concluiu.")
        if success and job.kind == AgentFolderJob.Kind.INVENTORY and isinstance(entries, list):
            job.report = {
                "entries": [
                    {
                        "path": str(entry.get("path", ""))[:300],
                        "dirs": int(entry.get("dirs", 0)),
                        "files": int(entry.get("files", 0)),
                    }
                    for entry in entries[:_REPORT_LIMIT]
                    if isinstance(entry, dict)
                ],
                "truncated": len(entries) > _REPORT_LIMIT,
            }
        job.save(update_fields=["status", "completed_at", "result", "report", "updated_at"])
        from apps.triage.folders import mark_job_result

        mark_job_result(job, success=success, detail=job.result)
    record_event(
        action="triage.folders.job_completed",
        organization=agent.organization,
        target=job,
        request=request,
        metadata={"job_id": str(job.id), "kind": job.kind, "success": success},
    )
    return JsonResponse({"status": "completed" if success else "failed"})
