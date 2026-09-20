"""Versioned API for the outbound-only CICA Windows agent."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import timedelta
from pathlib import Path, PureWindowsPath
from typing import Any
from urllib.parse import unquote

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.x509.oid import ExtendedKeyUsageOID
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.http import FileResponse, HttpRequest, HttpResponse, JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from apps.audit.services import record_event
from apps.hub.backup_bridge import apply_backup_page, complete_backup, fail_backup
from apps.hub.models import ImportBatch
from apps.intelligence.agents import redeem_enrollment, verify_agent_signature
from apps.intelligence.models import EdgeAgent, IntelligenceConnector
from apps.intelligence.sync import sync_bank_entries, sync_companies
from apps.triage.models import AgentFileJob, DestinationProfile, TriageEvent, TriageItem
from apps.triage.services import open_verified_quarantine_for_agent
from apps.triage.transitions import TriageStatus


def _error(detail: str, status: int) -> JsonResponse:
    response = JsonResponse({"error": detail}, status=status)
    response["Cache-Control"] = "no-store"
    return response


def _payload(request: HttpRequest, limit: int = 5_000_000) -> dict[str, Any] | None:
    if len(request.body) > limit:
        return None
    try:
        value = json.loads(request.body or b"{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def _agent(request: HttpRequest) -> EdgeAgent | None:
    agent_id = request.headers.get("X-Hub-Agent-ID", "")
    try:
        agent = EdgeAgent.objects.select_related("organization").filter(id=agent_id).first()
    except (TypeError, ValueError):
        return None
    if agent is None:
        return None
    if settings.EDGE_AGENT_MTLS_REQUIRED:
        verified = request.headers.get("X-Hub-MTLS-Verified", "")
        encoded = request.headers.get("X-Hub-MTLS-Client-Cert", "")
        try:
            observed = (
                x509.load_pem_x509_certificate(unquote(encoded).encode("ascii"))
                .fingerprint(hashes.SHA256())
                .hex()
            )
        except (TypeError, ValueError):
            return None
        if verified != "SUCCESS" or not hmac.compare_digest(
            observed, agent.mtls_certificate_sha256
        ):
            return None
    if not verify_agent_signature(
        agent=agent,
        timestamp=request.headers.get("X-Hub-Agent-Timestamp", ""),
        body=request.body,
        signature=request.headers.get("X-Hub-Agent-Signature", ""),
    ):
        return None
    return agent


def _sign_csr(csr_pem: str) -> tuple[str, str, str]:
    """Sign one client CSR with the deployment CA; the private key never leaves Windows."""

    cert_path = Path(settings.EDGE_AGENT_CA_CERT_PATH)
    key_path = Path(settings.EDGE_AGENT_CA_KEY_PATH)
    if not cert_path.is_file() or not key_path.is_file():
        raise RuntimeError("A autoridade certificadora do agente não está configurada.")
    try:
        csr = x509.load_pem_x509_csr(csr_pem.encode("ascii"))
        if not csr.is_signature_valid:
            raise ValueError
        ca_cert = x509.load_pem_x509_certificate(cert_path.read_bytes())
        ca_key = serialization.load_pem_private_key(key_path.read_bytes(), password=None)
    except (TypeError, ValueError) as exc:
        raise ValueError("CSR inválida.") from exc
    now = timezone.now()
    certificate = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=90))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256())
    )
    pem = certificate.public_bytes(serialization.Encoding.PEM).decode("ascii")
    chain = ca_cert.public_bytes(serialization.Encoding.PEM).decode("ascii")
    return pem, chain, certificate.fingerprint(hashes.SHA256()).hex()


@csrf_exempt
@require_POST
def enroll(request: HttpRequest) -> JsonResponse:
    payload = _payload(request, 64_000)
    if payload is None:
        return _error("Cadastro do agente inválido.", 400)
    try:
        certificate, chain, fingerprint = _sign_csr(str(payload.get("csr", "")))
    except RuntimeError as exc:
        return _error(str(exc), 503)
    except ValueError as exc:
        return _error(str(exc), 400)
    try:
        credentials = redeem_enrollment(
            code=str(payload.get("code", "")),
            label=str(payload.get("label", "")),
            fingerprint=str(payload.get("fingerprint", "")),
            mtls_certificate_sha256=fingerprint,
            request=request,
        )
    except ValueError as exc:
        return _error(str(exc), 403)
    response = JsonResponse(
        {
            "agent_id": credentials.agent_id,
            "shared_secret": credentials.shared_secret,
            "certificate": certificate,
            "certificate_chain": chain,
            "certificate_expires_in_days": 90,
        }
    )
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_POST
def heartbeat(request: HttpRequest) -> JsonResponse:
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    payload = _payload(request, 64_000)
    if payload is None:
        return _error("Heartbeat inválido.", 400)
    agent.last_seen_at = timezone.now()
    agent.save(update_fields=["last_seen_at", "updated_at"])
    return JsonResponse(
        {
            "status": "ok",
            "server_time": timezone.now().isoformat(),
            "update": getattr(settings, "EDGE_AGENT_LATEST_VERSION", ""),
            "installer_url": getattr(settings, "EDGE_AGENT_INSTALLER_URL", ""),
        }
    )


@csrf_exempt
@require_POST
def next_configuration(request: HttpRequest) -> JsonResponse:
    """Return only the office-scoped Windows archive root to its enrolled agent."""
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    profile = DestinationProfile.objects.filter(organization=agent.organization).first()
    root = (
        profile.windows_root
        if profile and profile.mode == DestinationProfile.Mode.WINDOWS
        else ""
    )
    response = JsonResponse({"windows_archive_root": root})
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_POST
def next_backup(request: HttpRequest) -> JsonResponse:
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    with transaction.atomic():
        batch = ImportBatch.objects.filter(
            organization=agent.organization,
            kind=ImportBatch.Kind.DOMINIO_BACKUP,
            status=ImportBatch.Status.PROCESSING,
            mapping__claimed_by=str(agent.id),
        ).first()
        if batch is None:
            batch = (
                ImportBatch.objects.select_for_update(skip_locked=True)
                .filter(
                    organization=agent.organization,
                    kind=ImportBatch.Kind.DOMINIO_BACKUP,
                    status=ImportBatch.Status.QUEUED,
                )
                .order_by("created_at")
                .first()
            )
        if batch is None:
            return JsonResponse({"job": None})
        if batch.status == ImportBatch.Status.QUEUED:
            batch.status = ImportBatch.Status.PROCESSING
            batch.mapping = {
                **batch.mapping,
                "claimed_by": str(agent.id),
                "claimed_at": timezone.now().isoformat(),
            }
            batch.save(update_fields=["status", "mapping", "updated_at"])
    response = JsonResponse(
        {
            "job": {
                "id": str(batch.id),
                "filename": batch.original_filename,
                "sha256": batch.content_hash,
                "backup_key": batch.backup_key,
                "source_snapshot_at": batch.source_snapshot_at.isoformat()
                if batch.source_snapshot_at
                else None,
                "download_url": request.build_absolute_uri(
                    reverse("agent-v2-backup-download", args=(batch.id,))
                ),
            }
        }
    )
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_POST
def next_file_job(request: HttpRequest) -> JsonResponse:
    """Claim one office-scoped Windows archive job, reclaiming abandoned work safely."""
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    now = timezone.now()
    stale_before = now - timedelta(minutes=15)
    with transaction.atomic():
        job = (
            AgentFileJob.objects.select_for_update()
            .select_related("triage_item")
            .filter(
                organization=agent.organization,
                status=AgentFileJob.Status.CLAIMED,
                claimed_by=str(agent.id),
            )
            .order_by("claimed_at")
            .first()
        )
        if job is None:
            job = (
                AgentFileJob.objects.select_for_update(skip_locked=True)
                .select_related("triage_item")
                .filter(organization=agent.organization)
                .filter(
                    models.Q(status=AgentFileJob.Status.QUEUED)
                    | models.Q(
                        status=AgentFileJob.Status.CLAIMED,
                        claimed_at__lt=stale_before,
                    )
                )
                .order_by("created_at")
                .first()
            )
        if job is None:
            return JsonResponse({"job": None})
        item = job.triage_item
        if item.status != TriageStatus.ARCHIVING:
            job.status = AgentFileJob.Status.FAILED
            job.completed_at = now
            job.result = "O item saiu da etapa de arquivamento."
            job.save(update_fields=["status", "completed_at", "result", "updated_at"])
            return JsonResponse({"job": None})
        job.status = AgentFileJob.Status.CLAIMED
        job.claimed_by = str(agent.id)
        job.claimed_at = now
        job.save(update_fields=["status", "claimed_by", "claimed_at", "updated_at"])
        profile = DestinationProfile.objects.filter(organization=agent.organization).first()
        if profile is None or profile.mode != DestinationProfile.Mode.WINDOWS:
            job.status = AgentFileJob.Status.FAILED
            job.completed_at = now
            job.result = "O destino Windows não está ativo."
            job.save(update_fields=["status", "completed_at", "result", "updated_at"])
            _agent_item_transition(
                item=item,
                target=TriageStatus.ARCHIVE_FAILED,
                note=job.result,
            )
            return JsonResponse({"job": None})
        normalized_root = str(PureWindowsPath(profile.windows_root)).rstrip("\\").lower()
        root_sha256 = hashlib.sha256(normalized_root.encode("utf-8")).hexdigest()
    response = JsonResponse(
        {
            "job": {
                "id": str(job.id),
                "relative_path": job.destination_path,
                "sha256": item.content_hash,
                "byte_size": item.byte_size,
                "root_sha256": root_sha256,
                "download_url": request.build_absolute_uri(
                    reverse("agent-v2-file-download", args=(job.id,))
                ),
            }
        }
    )
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@require_POST
def download_file_job(request: HttpRequest, job_id: str) -> HttpResponse:
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    job = (
        AgentFileJob.objects.select_related("triage_item__company", "triage_item__document_type")
        .filter(
            id=job_id,
            organization=agent.organization,
            status=AgentFileJob.Status.CLAIMED,
            claimed_by=str(agent.id),
        )
        .first()
    )
    if job is None:
        return _error("Trabalho de arquivo não encontrado para este agente.", 404)
    try:
        source = open_verified_quarantine_for_agent(item=job.triage_item)
    except ValidationError as exc:
        return _error(str(exc), 409)
    response = FileResponse(
        source,
        as_attachment=True,
        filename=PureWindowsPath(job.destination_path).name,
        content_type="application/octet-stream",
    )
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    response["X-CICA-Content-SHA256"] = job.triage_item.content_hash
    return response


def _agent_item_transition(*, item: TriageItem, target: str, note: str) -> None:
    previous = item.status
    item.transition_to(target)
    item.save(update_fields=["status", "updated_at"])
    TriageEvent.objects.create(
        organization=item.organization,
        triage_item=item,
        actor=None,
        from_status=previous,
        to_status=target,
        note=note[:500],
    )


@csrf_exempt
@require_POST
def complete_file_job(request: HttpRequest, job_id: str) -> JsonResponse:
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    payload = _payload(request, 16_384)
    if payload is None:
        return _error("Resultado de arquivamento inválido.", 400)
    success = payload.get("success") is True
    reported_hash = str(payload.get("sha256", "")).lower()
    reported_path = str(payload.get("relative_path", ""))
    detail = str(payload.get("detail", ""))[:500]
    try:
        reported_size = int(payload.get("byte_size", -1))
    except (TypeError, ValueError):
        reported_size = -1
    with transaction.atomic():
        job = (
            AgentFileJob.objects.select_for_update()
            .select_related("triage_item")
            .filter(id=job_id, organization=agent.organization)
            .first()
        )
        if job is None or job.claimed_by != str(agent.id):
            return _error("Trabalho de arquivo não encontrado para este agente.", 404)
        item = TriageItem.objects.select_for_update().get(
            id=job.triage_item_id, organization=agent.organization
        )
        if job.status == AgentFileJob.Status.DONE:
            if (
                success
                and reported_hash == item.content_hash
                and reported_path == job.destination_path
                and reported_size == item.byte_size
            ):
                return JsonResponse({"status": "completed"})
            return _error("A confirmação repetida não corresponde ao arquivo concluído.", 409)
        if job.status != AgentFileJob.Status.CLAIMED or item.status != TriageStatus.ARCHIVING:
            return _error("Este trabalho não aceita mais resultado.", 409)
        if not success:
            job.status = AgentFileJob.Status.FAILED
            job.completed_at = timezone.now()
            job.result = detail or "O agente não conseguiu gravar o arquivo."
            job.save(update_fields=["status", "completed_at", "result", "updated_at"])
            _agent_item_transition(
                item=item,
                target=TriageStatus.ARCHIVE_FAILED,
                note=job.result,
            )
            record_event(
                action="triage.item.windows_archive_failed",
                organization=agent.organization,
                target=item,
                request=request,
                metadata={"job_id": str(job.id), "detail": job.result},
            )
            return JsonResponse({"status": "failed"})
        if (
            reported_hash != item.content_hash
            or reported_size != item.byte_size
            or reported_path != job.destination_path
        ):
            return _error("Hash, tamanho ou destino não correspondem ao trabalho.", 409)
        profile = DestinationProfile.objects.filter(organization=agent.organization).first()
        if profile is None or profile.mode != DestinationProfile.Mode.WINDOWS:
            return _error("O destino Windows não está mais ativo.", 409)
        absolute_path = str(PureWindowsPath(profile.windows_root) / job.destination_path)
        item.destination_kind = DestinationProfile.Mode.WINDOWS
        item.destination_path = absolute_path
        item.destination_hash = reported_hash
        item.archived_at = timezone.now()
        item.save(
            update_fields=[
                "destination_kind",
                "destination_path",
                "destination_hash",
                "archived_at",
                "updated_at",
            ]
        )
        _agent_item_transition(
            item=item,
            target=TriageStatus.ARCHIVED,
            note="Hash e destino confirmados pelo agente Windows",
        )
        job.status = AgentFileJob.Status.DONE
        job.completed_at = timezone.now()
        job.result = "Hash e destino confirmados."
        job.save(update_fields=["status", "completed_at", "result", "updated_at"])
    record_event(
        action="triage.item.archived_windows",
        organization=agent.organization,
        target=item,
        request=request,
        metadata={"job_id": str(job.id), "content_hash": reported_hash},
    )
    return JsonResponse({"status": "completed"})


@csrf_exempt
@require_POST
def download_backup(request: HttpRequest, batch_id: str) -> HttpResponse:
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    batch = ImportBatch.objects.filter(
        id=batch_id,
        organization=agent.organization,
        kind=ImportBatch.Kind.DOMINIO_BACKUP,
        status=ImportBatch.Status.PROCESSING,
    ).first()
    if batch is None or batch.mapping.get("claimed_by") != str(agent.id):
        return _error("Backup não encontrado para este agente.", 404)
    if not batch.source_file:
        return _error("Arquivo do backup não está disponível.", 410)
    response = FileResponse(
        batch.source_file.open("rb"),
        as_attachment=True,
        filename=batch.original_filename,
        content_type="application/octet-stream",
    )
    response["Cache-Control"] = "no-store"
    response["X-Content-Type-Options"] = "nosniff"
    return response


@csrf_exempt
@require_POST
def sync_local_companies(request: HttpRequest) -> JsonResponse:
    """Accept one bounded, read-only Domínio Local page from the native agent."""
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    payload = _payload(request)
    rows = payload.get("companies") if payload is not None else None
    if (
        not isinstance(rows, list)
        or len(rows) > 500
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        return _error("Página de empresas Domínio inválida.", 400)
    connector, _ = IntelligenceConnector.objects.get_or_create(
        organization=agent.organization,
        mode=IntelligenceConnector.Mode.EDGE_AGENT,
        defaults={"status": "healthy"},
    )
    result = sync_companies(
        organization=agent.organization,
        connector=connector,
        rows=[dict(row) for row in rows],
        request=request,
        full_snapshot=False,
    )
    return JsonResponse(
        {"created": result.created, "updated": result.updated, "ignored": result.ignored}
    )


@csrf_exempt
@require_POST
def sync_local_bank_entries(request: HttpRequest) -> JsonResponse:
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    payload = _payload(request)
    rows = payload.get("rows") if payload is not None else None
    if (
        not isinstance(rows, list)
        or len(rows) > 500
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        return _error("Página de extratos Domínio inválida.", 400)
    connector, _ = IntelligenceConnector.objects.get_or_create(
        organization=agent.organization,
        mode=IntelligenceConnector.Mode.EDGE_AGENT,
        defaults={"status": "healthy"},
    )
    result = sync_bank_entries(
        organization=agent.organization,
        connector=connector,
        rows=[dict(row) for row in rows],
        request=request,
    )
    return JsonResponse(
        {"created": result.created, "updated": result.updated, "ignored": result.ignored}
    )


@csrf_exempt
@require_POST
def sync_capability(request: HttpRequest, capability: str) -> JsonResponse:
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    payload = _payload(request)
    if payload is None:
        return _error("Página de sincronização inválida.", 400)
    batch = ImportBatch.objects.filter(
        id=payload.get("batch_id"),
        organization=agent.organization,
        kind=ImportBatch.Kind.DOMINIO_BACKUP,
        status=ImportBatch.Status.PROCESSING,
    ).first()
    if batch is None or batch.mapping.get("claimed_by") != str(agent.id):
        return _error("Trabalho não encontrado para este agente.", 404)
    if capability == "complete":
        complete_backup(batch=batch, agent=agent, request=request)
        return JsonResponse({"status": "completed"})
    if capability == "failed":
        fail_backup(
            batch=batch,
            code=str(payload.get("code", "processing_failed")),
            detail=str(payload.get("detail", "Não foi possível ler o backup.")),
            agent=agent,
            request=request,
        )
        return JsonResponse({"status": "failed"})
    rows = payload.get("rows")
    if (
        capability not in {"companies", "obligations", "accounting_entries"}
        or not isinstance(rows, list)
        or len(rows) > 2_000
        or not all(isinstance(row, Mapping) for row in rows)
    ):
        return _error("Capacidade ou registros inválidos.", 400)
    try:
        result = apply_backup_page(
            batch=batch,
            capability=capability,
            rows=[dict(row) for row in rows],
            agent=agent,
            request=request,
        )
    except ValueError as exc:
        return _error(str(exc), 400)
    return JsonResponse(result)


@csrf_exempt
@require_POST
def renew_certificate(request: HttpRequest) -> JsonResponse:
    agent = _agent(request)
    if agent is None:
        return _error("Agente não autorizado.", 401)
    payload = _payload(request, 64_000)
    if payload is None:
        return _error("Renovação inválida.", 400)
    try:
        certificate, chain, fingerprint = _sign_csr(str(payload.get("csr", "")))
    except RuntimeError as exc:
        return _error(str(exc), 503)
    except ValueError as exc:
        return _error(str(exc), 400)
    agent.mtls_certificate_sha256 = fingerprint
    agent.save(update_fields=["mtls_certificate_sha256", "updated_at"])
    record_event(
        action="intelligence.agent.certificate_renewed",
        organization=agent.organization,
        target=agent,
        request=request,
    )
    response = JsonResponse({"certificate": certificate, "certificate_chain": chain})
    response["Cache-Control"] = "no-store"
    return response
