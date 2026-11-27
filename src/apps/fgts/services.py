"""Regras do FGTS Digital: conferir antes de emitir, emitir só com as três travas, nunca repetir.

O que o servidor decide sozinho (nunca confia no "bateu" do agente):

* a comparação de valor e vencimento do portal com a apuração do Domínio;
* se o clique de emitir está autorizado, no instante em que o agente reserva o trabalho;
* o que acontece com um emitir que ficou incerto (parou depois do clique): só pessoa decide.
"""

from __future__ import annotations

import hashlib
import re
from datetime import date
from typing import Any

from django.conf import settings
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.rpa import services as rpa
from apps.rpa.models import RpaJob
from apps.rpa.registry import RpaError

from .models import FgtsBatch, FgtsItem, FgtsSettings, FgtsSource

KIND_SOURCE = "fgts.fonte"
KIND_CHECK = "fgts.conferir"
KIND_EMIT = "fgts.emitir"
MAX_GROUPS = 200
MAX_PDF = 8 * 1024 * 1024
MIN_PDF = 500
_ROOT = re.compile(r"^\d{8}$")
_CNPJ = re.compile(r"^\d{14}$")


class FgtsError(Exception):
    """Regra do FGTS recusou a operação; a mensagem é segura para a tela."""


def settings_for(organization: Organization) -> FgtsSettings:
    obj, _ = FgtsSettings.objects.get_or_create(organization=organization)
    return obj


def emission_allowed(organization: Organization) -> tuple[bool, str]:
    """As três travas. Devolve ``(liberado, motivo_se_não)``."""

    if not getattr(settings, "FGTS_EMISSAO_HABILITADA", False):
        return False, "A emissão está desligada no servidor."
    cfg = settings_for(organization)
    if not cfg.source_validated:
        return False, "A fonte do Domínio ainda não foi validada com guias reais."
    if not cfg.emission_enabled:
        return False, "A emissão não foi liberada para este escritório."
    return True, ""


def _audit(action: str, organization: Organization, target: Any, **meta: Any) -> None:
    record_event(action=action, organization=organization, target=target, metadata=meta)


# --- fonte ---------------------------------------------------------------------------------


def request_source(organization: Organization, year: int, month: int) -> RpaJob:
    if not (1 <= month <= 12 and 2000 <= year <= 2100):
        raise FgtsError("Competência inválida.")
    count = FgtsSource.objects.filter(organization=organization, year=year, month=month).count()
    job, _ = rpa.enqueue(
        organization=organization,
        kind=KIND_SOURCE,
        idempotency_key=f"fonte:{year}-{month:02d}:{count}",
        payload={"year": year, "month": month},
    )
    return job


def validate_source_result(result: dict[str, Any]) -> None:
    groups = result.get("groups")
    if not isinstance(groups, list) or len(groups) > 2000:
        raise RpaError("validacao", "Lista de grupos inválida.")
    seen: set[str] = set()
    for group in groups:
        root = str(group.get("root", "")) if isinstance(group, dict) else ""
        cents = group.get("amount_cents") if isinstance(group, dict) else None
        if (
            not _ROOT.match(root)
            or root in seen
            or not isinstance(cents, int)
            or isinstance(cents, bool)
            or cents < 0
            or not _CNPJ.match(str(group.get("cnpj", "")))
        ):
            raise RpaError("validacao", "Grupo com raiz, CNPJ ou valor inválido.")
        seen.add(root)


def on_source_success(job: RpaJob) -> None:
    FgtsSource.objects.create(
        organization=job.organization,
        year=int(job.payload["year"]),
        month=int(job.payload["month"]),
        groups=job.result["groups"],
        pendencies=job.result.get("pendencies", [])[:200],
        job=job,
    )


def latest_source(organization: Organization, year: int, month: int) -> FgtsSource | None:
    return (
        FgtsSource.objects.filter(organization=organization, year=year, month=month)
        .order_by("-created_at")
        .first()
    )


# --- lote ----------------------------------------------------------------------------------


def _company_for(organization: Organization, codes: list[str]) -> ClientCompany | None:
    matches = list(
        ClientCompany.objects.filter(
            organization=organization, dominio_code__in=[str(c) for c in codes]
        )[:2]
    )
    return matches[0] if len(matches) == 1 else None


def create_batch(
    *,
    organization: Organization,
    user: User,
    year: int,
    month: int,
    deadline: date,
    roots: list[str],
) -> FgtsBatch:
    source = latest_source(organization, year, month)
    if source is None:
        raise FgtsError("Consulte o Domínio desta competência antes.")
    if not roots or len(roots) > MAX_GROUPS or len(roots) != len(set(roots)):
        raise FgtsError(f"Selecione de 1 a {MAX_GROUPS} grupos.")
    by_root = {g["root"]: g for g in source.groups}
    if set(roots) - by_root.keys():
        raise FgtsError("A seleção contém grupos que a apuração não tem.")
    live = set(
        FgtsItem.objects.filter(
            organization=organization,
            year=year,
            month=month,
            root__in=roots,
            state__in=FgtsItem.BLOCKING,
        ).values_list("root", flat=True)
    )
    if live:
        raise FgtsError("Já existe pedido ou guia para: " + ", ".join(sorted(live)))
    try:
        with transaction.atomic():
            batch = FgtsBatch.objects.create(
                organization=organization,
                year=year,
                month=month,
                deadline=deadline,
                created_by=user,
            )
            for root in roots:
                group = by_root[root]
                item = FgtsItem.objects.create(
                    organization=organization,
                    batch=batch,
                    root=root,
                    year=year,
                    month=month,
                    company=_company_for(organization, group.get("codes", [])),
                    company_name=str(group.get("name", ""))[:255],
                    representative_cnpj=group["cnpj"],
                    codes=group.get("codes", []),
                    expected_cents=group["amount_cents"],
                )
                _enqueue_check(item)
            _audit("fgts.batch.created", organization, batch, groups=len(roots), user=str(user.pk))
    except IntegrityError as exc:
        raise FgtsError("Outro lote tomou um destes grupos agora; atualize.") from exc
    return batch


def _enqueue_check(item: FgtsItem) -> None:
    job, _ = rpa.enqueue(
        organization=item.organization,
        kind=KIND_CHECK,
        idempotency_key=f"conferir:{item.pk}:{item.check_job_id or 0}:{item.updated_at:%f}",
        payload={
            "item_id": str(item.pk),
            "root": item.root,
            "cnpj": item.representative_cnpj,
            "year": item.year,
            "month": item.month,
            "deadline": item.batch.deadline.isoformat(),
        },
    )
    item.check_job = job
    item.state = FgtsItem.State.QUEUED
    item.save(update_fields=["check_job", "state", "updated_at"])


def compare_portal(item: FgtsItem, cents: int, due: date | None) -> str:
    """Texto do motivo da divergência, ou vazio quando tudo confere."""

    if cents != item.expected_cents:
        return "O valor do portal diverge do Domínio; guia não emitida."
    if due is None or due > item.batch.deadline:
        return "O vencimento supera a data limite; guia não emitida."
    return ""


def _parse_due(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value)) if value else None
    except ValueError:
        return None


def _item_of(job: RpaJob) -> FgtsItem:
    try:
        return (
            FgtsItem.objects.select_for_update()
            .select_related("batch")
            .get(pk=job.payload.get("item_id"), organization=job.organization)
        )
    except (FgtsItem.DoesNotExist, ValueError, TypeError) as exc:
        raise RpaError("validacao", "Item do FGTS não encontrado.") from exc


def validate_check_result(result: dict[str, Any]) -> None:
    cents = result.get("portal_cents")
    if not isinstance(cents, int) or isinstance(cents, bool) or cents < 0:
        raise RpaError("validacao", "Valor do portal inválido.")
    if result.get("portal_due") and _parse_due(result["portal_due"]) is None:
        raise RpaError("validacao", "Vencimento do portal inválido.")


def on_check_success(job: RpaJob) -> None:
    item = _item_of(job)
    cents = int(job.result["portal_cents"])
    due = _parse_due(job.result.get("portal_due"))
    item.portal_cents, item.portal_due = cents, due
    problem = compare_portal(item, cents, due)  # o servidor decide; o "bateu" do agente não conta
    item.state = FgtsItem.State.DIVERGENCE if problem else FgtsItem.State.PREPARED
    item.message = problem or "Conferido com o portal."
    item.save()


def on_check_failure(job: RpaJob) -> None:
    item = _item_of(job)
    item.state = FgtsItem.State.FAILED
    item.message = (job.error_detail or "Falha antes da emissão.")[:500]
    item.save()


# --- emissão -------------------------------------------------------------------------------


def request_emission(item: FgtsItem, *, user: User) -> RpaJob:
    ok, why = emission_allowed(item.organization)
    if not ok:
        raise FgtsError(why)
    if item.state != FgtsItem.State.PREPARED or item.portal_cents is None:
        raise FgtsError("Só um item conferido com o portal pode ser emitido.")
    if compare_portal(item, item.portal_cents, item.portal_due):
        raise FgtsError("Os valores do portal não conferem com o Domínio.")
    with transaction.atomic():
        job, _ = rpa.enqueue(
            organization=item.organization,
            kind=KIND_EMIT,
            idempotency_key=f"emitir:{item.pk}",
            payload={
                "item_id": str(item.pk),
                "root": item.root,
                "cnpj": item.representative_cnpj,
                "year": item.year,
                "month": item.month,
                "expected_cents": item.expected_cents,
                "deadline": item.batch.deadline.isoformat(),
            },
        )
        item.emit_job = job
        item.state = FgtsItem.State.EMITTING
        item.message = "Emissão pedida."
        item.save(update_fields=["emit_job", "state", "message", "updated_at"])
        _audit("fgts.emission.requested", item.organization, item, user=str(user.pk))
    return job


def prepare_emission_claim(job: RpaJob) -> dict[str, Any]:
    """Reconfere as travas NO INSTANTE da entrega ao agente; qualquer uma caída bloqueia."""

    ok, why = emission_allowed(job.organization)
    if not ok:
        raise RpaError("trava", why)
    item = FgtsItem.objects.filter(
        pk=job.payload.get("item_id"), organization=job.organization
    ).first()
    if (
        item is None
        or item.state != FgtsItem.State.EMITTING
        or item.portal_cents is None
        or compare_portal(item, item.portal_cents, item.portal_due)
    ):
        raise RpaError("trava", "O item não está mais conferido para emissão.")
    return {"emit_allowed": True}


def validate_emit_result(result: dict[str, Any]) -> None:
    validate_check_result(result)
    sha = str(result.get("sha256", ""))
    if not re.match(r"^[0-9a-f]{64}$", sha):
        raise RpaError("validacao", "Hash da guia ausente.")


def on_emit_success(job: RpaJob) -> None:
    item = _item_of(job)
    result = job.result
    artifact = job.artifacts.filter(sha256=result["sha256"]).first()
    if artifact is None:
        raise RpaError("validacao", "A guia em PDF não foi entregue.")
    with artifact.file.open("rb") as handle:
        head = handle.read(8)
    if not head.startswith(b"%PDF-") or not (MIN_PDF <= artifact.byte_size <= MAX_PDF):
        raise RpaError("validacao", "O arquivo recebido não é um PDF de guia válido.")
    cents, due = int(result["portal_cents"]), _parse_due(result.get("portal_due"))
    item.portal_cents, item.portal_due = cents, due
    item.pdf, item.sha256 = artifact, artifact.sha256
    problem = compare_portal(item, cents, due)
    item.state = FgtsItem.State.REVIEW
    item.message = (
        f"Guia emitida com divergência: {problem}" if problem else "Guia emitida; aguarda revisão."
    )[:500]
    item.save()


def on_emit_failure(job: RpaJob) -> None:
    item = _item_of(job)
    # Bloqueio antes de entregar ao agente: nada foi emitido, volta a conferido (e re-emitir
    # exigirá as travas de novo). Falha técnica antes do clique também.
    item.state = FgtsItem.State.PREPARED
    item.message = (job.error_detail or "Emissão não realizada.")[:500]
    item.save()


def on_emit_uncertain(job: RpaJob) -> None:
    item = _item_of(job)
    item.state = FgtsItem.State.UNCERTAIN
    item.message = "Emissão incerta; confira no portal antes de repetir."
    item.save()


def resolve_uncertain(
    item: FgtsItem, *, user: User, issued: bool, note: str, pdf: bytes | None = None
) -> FgtsItem:
    """Pessoa conferiu o portal. ``issued``: a guia existe (anexe o mesmo PDF); senão encerra."""

    if item.state != FgtsItem.State.UNCERTAIN or item.emit_job is None:
        raise FgtsError("O item não está incerto.")
    if not note.strip():
        raise FgtsError("Informe o que foi conferido no portal.")
    with transaction.atomic():
        if issued:
            content = pdf or b""
            if not content.startswith(b"%PDF-") or not (MIN_PDF <= len(content) <= MAX_PDF):
                raise FgtsError("Envie o PDF da guia emitida.")
            digest = hashlib.sha256(content).hexdigest()
            from django.core.files.base import ContentFile

            from apps.rpa.models import RpaArtifact

            artifact = RpaArtifact(
                organization=item.organization,
                job=item.emit_job,
                name=f"fgts_{item.root}.pdf",
                sha256=digest,
                byte_size=len(content),
                content_type="application/pdf",
            )
            artifact.file.save(f"{digest}.bin", ContentFile(content), save=False)
            artifact.save()
            item.pdf, item.sha256 = artifact, digest
            item.state = FgtsItem.State.REVIEW
            item.message = "Guia anexada pela equipe; aguarda revisão."
        else:
            item.state = FgtsItem.State.FAILED
            item.message = "Confirmado no portal que não houve emissão."
        item.save()
        rpa.resolve_uncertain(
            item.emit_job.pk, organization=item.organization, requeue=False, note=note
        )
        _audit("fgts.emission.resolved", item.organization, item, issued=issued, user=str(user.pk))
    return item


def mark_reviewed(item: FgtsItem, *, user: User) -> FgtsItem:
    if item.state != FgtsItem.State.REVIEW:
        raise FgtsError("Só uma guia em revisão pode ser conferida.")
    if item.portal_cents != item.expected_cents:
        raise FgtsError("O valor da guia diverge do Domínio; trate fora do sistema.")
    item.message = f"Guia revisada em {timezone.localdate():%d/%m/%Y}."
    item.save(update_fields=["message", "updated_at"])
    _audit("fgts.guide.reviewed", item.organization, item, user=str(user.pk))
    return item
