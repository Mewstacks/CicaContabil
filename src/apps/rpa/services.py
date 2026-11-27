"""Regras da fila RPA: enfileirar, reivindicar, renovar, fechar.

Tudo roda em transação com ``select_for_update``. A reivindicação nunca entrega trabalho de outro
escritório, de módulo desligado, de tipo que o agente não declarou ou que dispute o mesmo grupo
exclusivo de um trabalho ainda reservado. Reserva vencida volta à fila — exceto se o agente já
tinha entrado numa fase irreversível: aí o trabalho vira ``uncertain`` e espera decisão humana.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta
from typing import Any

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.hub.models import ProductModule
from apps.organizations.models import Organization

from . import registry
from .models import RpaArtifact, RpaJob, RpaJobEvent
from .redaction import SecretInPayload, assert_no_secrets, redact_text
from .registry import RpaError

MAX_PAYLOAD_BYTES = 64_000
MAX_RESULT_BYTES = 256_000
MAX_ARTIFACT_BYTES = 25_000_000
MAX_ARTIFACTS_PER_JOB = 30
FAILURE_CODES = frozenset(
    {
        "agent_error",
        "dominio_indisponivel",
        "portal_indisponivel",
        "login_necessario",
        "validacao",
        "conferencia_divergente",
        "bloqueado_por_trava",
        "nao_suportado",
        "timeout",
    }
)
#: Falhas que não adianta repetir: pedem uma pessoa.
PERMANENT_FAILURES = frozenset(
    {"validacao", "conferencia_divergente", "bloqueado_por_trava", "nao_suportado"}
)


def agent_enabled() -> bool:
    return bool(getattr(settings, "RPA_AGENT_ENABLED", False))


def module_enabled(organization: Organization, module_code: str) -> bool:
    return ProductModule.objects.filter(
        organization=organization, code=module_code, enabled=True
    ).exists()


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _event(job: RpaJob, event: str, detail: str = "") -> None:
    RpaJobEvent.objects.create(
        organization=job.organization, job=job, event=event, detail=redact_text(detail)
    )


def _size(value: Any) -> int:
    return len(json.dumps(value, ensure_ascii=False, default=str).encode("utf-8"))


def _ready(now: datetime) -> Q:
    return Q(not_before__isnull=True) | Q(not_before__lte=now)


# --- enfileirar ----------------------------------------------------------------------------


def enqueue(
    *,
    organization: Organization,
    kind: str,
    idempotency_key: str,
    payload: dict[str, Any] | None = None,
    not_before: datetime | None = None,
) -> tuple[RpaJob, bool]:
    """Cria o trabalho ou devolve o que já existe com a mesma chave. ``(job, created)``."""

    spec = registry.get(kind)
    if not module_enabled(organization, spec.module_code):
        raise RpaError("modulo_desligado", "O módulo deste trabalho não está ligado no escritório.")
    key = (idempotency_key or "").strip()
    if not key or len(key) > 120:
        raise RpaError("chave_invalida", "Chave de idempotência vazia ou longa demais.")
    body = dict(payload or {})
    try:
        assert_no_secrets(body)
    except SecretInPayload as exc:
        raise RpaError("segredo_na_carga", str(exc)) from exc
    if _size(body) > MAX_PAYLOAD_BYTES:
        raise RpaError("carga_grande", "A carga do trabalho passou do limite.")
    if spec.validate_payload is not None:
        spec.validate_payload(body)
    with transaction.atomic():
        job, created = RpaJob.objects.get_or_create(
            organization=organization,
            kind=kind,
            idempotency_key=key,
            defaults={
                "payload": body,
                "max_attempts": spec.max_attempts,
                "not_before": not_before,
            },
        )
        if created:
            _event(job, "enfileirado")
    return job, created


def retry(job_id: Any, *, organization: Organization) -> RpaJob:
    """Reabre um trabalho que *falhou* (um incerto passa por ``resolve_uncertain``)."""

    with transaction.atomic():
        job = RpaJob.objects.select_for_update().get(id=job_id, organization=organization)
        if job.state != RpaJob.State.FAILED:
            raise RpaError("estado_invalido", "Só um trabalho que falhou pode ser repetido.")
        job.state = RpaJob.State.QUEUED
        job.attempts = 0
        job.error_code = ""
        job.error_detail = ""
        job.completed_at = None
        job.not_before = None
        job.save()
        _event(job, "reaberto")
    return job


def resolve_uncertain(
    job_id: Any, *, organization: Organization, requeue: bool, note: str
) -> RpaJob:
    """Decisão humana sobre um incerto: confirmou que NÃO houve efeito (repete) ou encerra."""

    with transaction.atomic():
        job = RpaJob.objects.select_for_update().get(id=job_id, organization=organization)
        if job.state != RpaJob.State.UNCERTAIN:
            raise RpaError("estado_invalido", "O trabalho não está incerto.")
        if requeue:
            job.state = RpaJob.State.QUEUED
            job.attempts = 0
            job.phase = ""
            job.completed_at = None
            job.error_code = ""
            job.error_detail = ""
        else:
            job.state = RpaJob.State.CANCELLED
            job.completed_at = timezone.now()
        job.save()
        _event(job, "incerto_resolvido", ("repetir: " if requeue else "encerrar: ") + note)
    return job


def cancel(job_id: Any, *, organization: Organization) -> RpaJob:
    with transaction.atomic():
        job = RpaJob.objects.select_for_update().get(id=job_id, organization=organization)
        if job.state != RpaJob.State.QUEUED:
            raise RpaError("estado_invalido", "Só um trabalho na fila pode ser cancelado.")
        job.state = RpaJob.State.CANCELLED
        job.completed_at = timezone.now()
        job.save()
        _event(job, "cancelado")
    return job


# --- reserva vencida -----------------------------------------------------------------------


def release_expired(
    organization: Organization | None = None, *, now: datetime | None = None
) -> int:
    """Devolve à fila (ou marca incerto) o que o agente deixou vencer. Idempotente."""

    now = now or timezone.now()
    count = 0
    with transaction.atomic():
        stale = RpaJob.objects.select_for_update(skip_locked=True).filter(
            state=RpaJob.State.LEASED, lease_expires_at__lt=now
        )
        if organization is not None:
            stale = stale.filter(organization=organization)
        for job in stale:
            spec = registry.get(job.kind)
            irreversible = bool(job.phase and job.phase in spec.irreversible_phases)
            phase = job.phase
            job.leased_by = ""
            job.lease_token_hash = ""
            job.lease_expires_at = None
            if irreversible:
                job.state = RpaJob.State.UNCERTAIN
                job.completed_at = now
                job.error_code = "incerto"
                job.error_detail = "O agente parou após etapa sem volta; confira antes de repetir."
                job.save()
                _event(job, "incerto", f"fase={phase}")
                if spec.on_uncertain:
                    spec.on_uncertain(job)
            elif job.attempts >= job.max_attempts:
                job.state = RpaJob.State.FAILED
                job.completed_at = now
                job.error_code = "timeout"
                job.error_detail = "O agente não respondeu a tempo."
                job.save()
                _event(job, "expirou")
                if spec.on_failure:
                    spec.on_failure(job)
            else:
                job.state = RpaJob.State.QUEUED
                job.save()
                _event(job, "devolvido", "reserva vencida")
            count += 1
    return count


# --- agente --------------------------------------------------------------------------------


def claim_next(
    *,
    organization: Organization,
    agent_id: str,
    kinds: list[str],
    now: datetime | None = None,
) -> tuple[RpaJob, str] | None:
    """Reserva o próximo trabalho que o agente sabe executar. ``(job, token_em_claro)``."""

    now = now or timezone.now()
    known = [code for code in kinds if code in registry.known_codes()]
    if not known:
        return None
    release_expired(organization, now=now)
    with transaction.atomic():
        busy_groups = {
            registry.get(code).exclusive_group
            for code in RpaJob.objects.filter(
                organization=organization, state=RpaJob.State.LEASED
            ).values_list("kind", flat=True)
            if registry.get(code).exclusive_group
        }
        candidates = (
            RpaJob.objects.select_for_update(skip_locked=True)
            .filter(organization=organization, state=RpaJob.State.QUEUED, kind__in=known)
            .filter(_ready(now))
            .order_by("created_at")
        )
        for job in candidates[:50]:
            spec = registry.get(job.kind)
            if spec.exclusive_group and spec.exclusive_group in busy_groups:
                continue
            if not module_enabled(organization, spec.module_code):
                continue
            patch: dict[str, Any] = {}
            if spec.prepare_claim is not None:
                try:
                    patch = spec.prepare_claim(job)
                    if not spec.transient_claim:
                        job.payload = {**job.payload, **patch}
                except RpaError as exc:
                    job.state = RpaJob.State.FAILED
                    job.error_code = "bloqueado_por_trava"
                    job.error_detail = redact_text(exc.message)
                    job.completed_at = now
                    job.save()
                    _event(job, "bloqueado", exc.message)
                    if spec.on_failure:
                        spec.on_failure(job)
                    continue
            token = secrets.token_urlsafe(32)
            job.state = RpaJob.State.LEASED
            job.leased_by = agent_id
            job.lease_token_hash = _hash(token)
            job.lease_expires_at = now + timedelta(seconds=spec.lease_seconds)
            job.last_heartbeat_at = now
            job.started_at = job.started_at or now
            job.attempts += 1
            job.phase = ""
            job.save()
            _event(job, "reservado", f"tentativa {job.attempts}")
            if spec.transient_claim and patch:
                job.payload = {**job.payload, **patch}  # só em memória; já foi salvo sem isto
            return job, token
    return None


def _leased(job_id: Any, *, organization: Organization, agent_id: str, token: str) -> RpaJob:
    job = RpaJob.objects.select_for_update().filter(id=job_id, organization=organization).first()
    if job is None or job.leased_by != agent_id:
        raise RpaError("nao_encontrado", "Trabalho não encontrado para este agente.")
    if job.state != RpaJob.State.LEASED or not hmac.compare_digest(
        job.lease_token_hash, _hash(token or "")
    ):
        raise RpaError("reserva_perdida", "A reserva deste trabalho não é mais sua.")
    return job


def heartbeat(
    *, job_id: Any, organization: Organization, agent_id: str, token: str, phase: str = ""
) -> RpaJob:
    now = timezone.now()
    with transaction.atomic():
        job = _leased(job_id, organization=organization, agent_id=agent_id, token=token)
        spec = registry.get(job.kind)
        job.lease_expires_at = now + timedelta(seconds=spec.lease_seconds)
        job.last_heartbeat_at = now
        if phase:
            job.phase = redact_text(phase, limit=40)
        job.save()
    return job


def _clean_result(spec: registry.RpaKind, result: dict[str, Any]) -> dict[str, Any]:
    if _size(result) > MAX_RESULT_BYTES:
        raise RpaError("resultado_grande", "O resultado passou do limite.")
    kept = {k: v for k, v in result.items() if k in spec.result_keys}
    try:
        assert_no_secrets(kept)
    except SecretInPayload as exc:
        raise RpaError("segredo_no_resultado", str(exc)) from exc
    return kept


def complete(
    *, job_id: Any, organization: Organization, agent_id: str, token: str, result: dict[str, Any]
) -> RpaJob:
    """Fecha com sucesso. Repetir a mesma confirmação é inofensivo; outra é recusada."""

    with transaction.atomic():
        job = (
            RpaJob.objects.select_for_update().filter(id=job_id, organization=organization).first()
        )
        if job is None or job.leased_by != agent_id:
            raise RpaError("nao_encontrado", "Trabalho não encontrado para este agente.")
        spec = registry.get(job.kind)
        cleaned = _clean_result(spec, result)
        if job.state == RpaJob.State.SUCCEEDED:
            if job.result == cleaned:
                return job
            raise RpaError("resultado_diferente", "Confirmação repetida não confere.")
        job = _leased(job_id, organization=organization, agent_id=agent_id, token=token)
        if spec.validate_result is not None:
            spec.validate_result(cleaned)
        job.state = RpaJob.State.SUCCEEDED
        job.result = cleaned
        job.completed_at = timezone.now()
        job.lease_token_hash = ""
        job.lease_expires_at = None
        job.error_code = ""
        job.error_detail = ""
        job.save()
        _event(job, "concluido")
        if spec.on_success:
            spec.on_success(job)
    return job


def fail(
    *,
    job_id: Any,
    organization: Organization,
    agent_id: str,
    token: str,
    code: str,
    detail: str = "",
) -> RpaJob:
    with transaction.atomic():
        job = _leased(job_id, organization=organization, agent_id=agent_id, token=token)
        spec = registry.get(job.kind)
        code = code if code in FAILURE_CODES else "agent_error"
        irreversible = bool(job.phase and job.phase in spec.irreversible_phases)
        job.error_code = code
        job.error_detail = redact_text(detail)
        job.lease_token_hash = ""
        job.lease_expires_at = None
        job.leased_by = ""
        now = timezone.now()
        if irreversible:
            job.state = RpaJob.State.UNCERTAIN
            job.completed_at = now
            job.save()
            _event(job, "incerto", f"{code} na fase {job.phase}")
            if spec.on_uncertain:
                spec.on_uncertain(job)
        elif code in PERMANENT_FAILURES or job.attempts >= job.max_attempts:
            job.state = RpaJob.State.FAILED
            job.completed_at = now
            job.save()
            _event(job, "falhou", f"{code}: {job.error_detail}")
            if spec.on_failure:
                spec.on_failure(job)
        else:
            job.state = RpaJob.State.QUEUED
            job.not_before = now + timedelta(seconds=min(60 * 2**job.attempts, 1800))
            job.save()
            _event(job, "repetir", f"{code}: {job.error_detail}")
    return job


def attach_artifact(
    *,
    job_id: Any,
    organization: Organization,
    agent_id: str,
    token: str,
    name: str,
    content: bytes,
    claimed_sha256: str,
    content_type: str = "",
) -> RpaArtifact:
    if len(content) > MAX_ARTIFACT_BYTES:
        raise RpaError("arquivo_grande", "O arquivo passou do limite.")
    digest = hashlib.sha256(content).hexdigest()
    if not hmac.compare_digest(digest, (claimed_sha256 or "").lower()):
        raise RpaError("hash_diverge", "O hash do arquivo não confere.")
    with transaction.atomic():
        job = _leased(job_id, organization=organization, agent_id=agent_id, token=token)
        existing = job.artifacts.filter(sha256=digest).first()
        if existing is not None:
            return existing
        if job.artifacts.count() >= MAX_ARTIFACTS_PER_JOB:
            raise RpaError("arquivos_demais", "Arquivos demais neste trabalho.")
        artifact = RpaArtifact(
            organization=organization,
            job=job,
            name=redact_text(name.replace("\\", "/").rsplit("/", 1)[-1], limit=200) or "arquivo",
            sha256=digest,
            byte_size=len(content),
            content_type=content_type[:80],
        )
        artifact.file.save(f"{digest}.bin", ContentFile(content), save=False)
        artifact.save()
        _event(job, "arquivo", f"{artifact.name} {artifact.byte_size} bytes")
    return artifact
