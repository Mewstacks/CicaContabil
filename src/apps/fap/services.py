"""Regras do FAP: lote, consulta, conferência do PDF no servidor e recuperação.

Travas: ``enabled`` e ``portal_validated`` do escritório (reconferidas no instante em que o agente
reserva cada consulta), teto de empresas por lote, uma consulta viva por CNPJ e vigência, cadastro
conferido antes de consultar e PDF validado pelo SERVIDOR (CNPJ rotulado e vigência), nunca pela
palavra do agente.
"""

from __future__ import annotations

import io
import re
import unicodedata
from typing import Any

from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import ClientCompany
from apps.organizations.models import Organization
from apps.rpa import services as rpa
from apps.rpa.models import RpaJob
from apps.rpa.registry import RpaError

from .models import FapBatch, FapItem, FapSettings

KIND = "fap.consultar"
MAX_PDF = 20 * 1024 * 1024
MAX_PAGES = 100
RESULTS = {"ok", "no_report", "no_permission", "root_missing", "failed"}
_STATE_OF = {
    "no_report": FapItem.State.NO_REPORT,
    "no_permission": FapItem.State.NO_PERMISSION,
    "root_missing": FapItem.State.ROOT_MISSING,
    "failed": FapItem.State.FAILED,
}


class FapError(Exception):
    """Regra do FAP recusou a operação; a mensagem é segura para a tela."""


def settings_for(organization: Organization) -> FapSettings:
    obj, _ = FapSettings.objects.get_or_create(organization=organization)
    return obj


def valid_cnpj(digits: str) -> bool:
    if not re.fullmatch(r"\d{14}", digits) or len(set(digits)) == 1:
        return False
    for size in (12, 13):
        weights = list(range(size - 7, 1, -1)) + list(range(9, 1, -1))
        total = sum(int(d) * w for d, w in zip(digits[:size], weights, strict=False))
        check = 11 - total % 11
        if int(digits[size]) != (0 if check >= 10 else check):
            return False
    return True


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _registry_problem(company: ClientCompany, cnpj_count: dict[str, int]) -> str:
    cnpj = _digits(company.cnpj_masked)
    if not company.dominio_code or not company.name.strip():
        return "Falta código do Domínio ou nome."
    if not valid_cnpj(cnpj):
        return "CNPJ ausente, inválido ou em formato ainda não suportado."
    if cnpj_count.get(cnpj, 0) > 1:
        return "CNPJ repetido em mais de uma empresa da seleção."
    return ""


# --- lote ----------------------------------------------------------------------------------


def create_batch(
    *, organization: Organization, user: User, year: int, companies: list[ClientCompany]
) -> FapBatch:
    cfg = settings_for(organization)
    if not cfg.enabled:
        raise FapError("O FAP não está liberado para este escritório.")
    if not (2000 <= year <= 2100):
        raise FapError("Vigência inválida.")
    if not companies:
        raise FapError("Escolha ao menos uma empresa.")
    if cfg.batch_limit and len(companies) > cfg.batch_limit:
        raise FapError(f"O lote aceita no máximo {cfg.batch_limit} empresas por ora.")
    if any(c.organization_id != organization.pk for c in companies):
        raise FapError("Há empresa de outro escritório.")
    counts: dict[str, int] = {}
    for company in companies:
        counts[_digits(company.cnpj_masked)] = counts.get(_digits(company.cnpj_masked), 0) + 1
    live = {
        row
        for row in FapItem.objects.filter(
            organization=organization, year=year, state__in=FapItem.ACTIVE
        ).values_list("cnpj", flat=True)
    }
    try:
        with transaction.atomic():
            batch = FapBatch.objects.create(organization=organization, year=year, created_by=user)
            for company in companies:
                cnpj = _digits(company.cnpj_masked)
                problem = _registry_problem(company, counts)
                if not problem and cnpj in live:
                    raise FapError(f"{company.name}: já há consulta em andamento desta vigência.")
                item = FapItem.objects.create(
                    organization=organization,
                    batch=batch,
                    company=company,
                    code=company.dominio_code or str(company.pk),
                    name=company.name[:255],
                    cnpj="" if problem else cnpj,
                    year=year,
                    state=FapItem.State.REGISTRY if problem else FapItem.State.PENDING,
                    message=problem,
                )
                if not problem:
                    _enqueue(item)
            recompute(batch)
            record_event(
                action="fap.batch.created",
                organization=organization,
                target=batch,
                metadata={"items": len(companies), "user": str(user.pk)},
            )
    except IntegrityError as exc:
        raise FapError("Outra consulta do mesmo CNPJ e vigência já está viva.") from exc
    return batch


def _enqueue(item: FapItem) -> None:
    job, _ = rpa.enqueue(
        organization=item.organization,
        kind=KIND,
        idempotency_key=f"item:{item.pk}:{item.generation}",
        payload={
            "item_id": str(item.pk),
            "cnpj": item.cnpj,
            "root": item.cnpj[:8],
            "year": item.year,
        },
    )
    item.job = job
    item.save(update_fields=["job", "updated_at"])


def prepare_claim(job: RpaJob) -> dict[str, Any]:
    """Travas no instante da entrega ao agente. Qualquer uma caída bloqueia o trabalho."""

    cfg = settings_for(job.organization)
    if not cfg.enabled:
        raise RpaError("trava", "O FAP foi desligado para este escritório.")
    if not cfg.portal_validated:
        raise RpaError("trava", "O portal do FAP ainda não foi validado.")
    item = (
        FapItem.objects.select_related("batch")
        .filter(pk=job.payload.get("item_id"), organization=job.organization)
        .first()
    )
    if item is None or item.state != FapItem.State.PENDING or item.job_id != job.pk:
        raise RpaError("trava", "O item não está mais pendente.")
    if item.batch.state == FapBatch.State.PAUSED:
        raise RpaError("trava", "O lote está pausado.")
    item.state = FapItem.State.QUERYING
    item.save(update_fields=["state", "updated_at"])
    return {}


def validate_payload(payload: dict[str, Any]) -> None:
    if not payload.get("item_id") or not valid_cnpj(str(payload.get("cnpj", ""))):
        raise RpaError("validacao", "Carga sem item ou com CNPJ inválido.")


def validate_result(result: dict[str, Any]) -> None:
    if result.get("status") not in RESULTS:
        raise RpaError("validacao", "Resultado desconhecido.")
    if result.get("status") == "ok" and not re.fullmatch(
        r"[0-9a-f]{64}", str(result.get("sha256", ""))
    ):
        raise RpaError("validacao", "Hash do PDF ausente.")


def _normalize(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text or "")
    return re.sub(r"\s+", " ", "".join(c for c in folded if not unicodedata.combining(c))).upper()


def pdf_text(content: bytes) -> str:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(content), strict=True)
    if reader.is_encrypted or len(reader.pages) > MAX_PAGES:
        raise ValueError("PDF criptografado ou longo demais.")
    return "\n".join((page.extract_text() or "") for page in reader.pages)


def validate_pdf(content: bytes, *, cnpj: str, year: int) -> str:
    """Texto do problema, ou vazio se o PDF é o resultado oficial desta empresa e vigência."""

    if not content.startswith(b"%PDF-") or len(content) > MAX_PDF:
        return "O arquivo não é um PDF válido de até 20 MB."
    try:
        text = _normalize(pdf_text(content))
    except Exception:
        return "Não foi possível ler o PDF."
    titled = "RESULTADO DA CONSULTA FAP" in text
    sections = "DADOS DO ESTABELECIMENTO" in text and "DADOS DO FAP" in text
    if not (titled and sections):
        return "O PDF não tem o título e as seções oficiais do FAP."
    found = {_digits(m) for m in re.findall(r"CNPJ:\s*([\d./-]{14,18})", text)}
    if found != {cnpj}:
        return "O CNPJ rotulado no PDF não é o da empresa."
    years = set(re.findall(r"VIGENCIA:\s*(\d{4})", text))
    if years != {str(year)}:
        return "A vigência rotulada no PDF não é a pedida."
    return ""


def _item_of(job: RpaJob) -> FapItem:
    try:
        return (
            FapItem.objects.select_for_update()
            .select_related("batch")
            .get(pk=job.payload.get("item_id"), organization=job.organization)
        )
    except (FapItem.DoesNotExist, ValueError, TypeError) as exc:
        raise RpaError("validacao", "Item do FAP não encontrado.") from exc


def on_success(job: RpaJob) -> None:
    item = _item_of(job)
    status = job.result["status"]
    if status != "ok":
        item.state = _STATE_OF[status]
        item.message = str(job.result.get("message", ""))[:500]
    else:
        artifact = job.artifacts.filter(sha256=job.result["sha256"]).first()
        if artifact is None:
            raise RpaError("validacao", "O PDF do FAP não foi entregue.")
        with artifact.file.open("rb") as handle:
            content = handle.read(MAX_PDF + 1)
        problem = validate_pdf(content, cnpj=item.cnpj, year=item.year)
        item.pdf, item.sha256 = artifact, artifact.sha256
        if problem:
            item.state, item.message = FapItem.State.REVIEW, problem
        else:
            item.state, item.message = FapItem.State.DONE, ""
            item.validated_at = timezone.now()
    item.save()
    recompute(item.batch)


def on_failure(job: RpaJob) -> None:
    item = _item_of(job)
    blocked = job.error_code == "bloqueado_por_trava"
    item.state = FapItem.State.PENDING if blocked else FapItem.State.FAILED
    item.message = (job.error_detail or "Falha na consulta.")[:500]
    item.save()
    recompute(item.batch)


def recompute(batch: FapBatch) -> str:
    states = list(batch.items.values_list("state", flat=True))
    if not states:
        return batch.state
    if batch.state == FapBatch.State.PAUSED and any(s in FapItem.ACTIVE for s in states):
        return batch.state
    if any(s == FapItem.State.QUERYING for s in states):
        new = FapBatch.State.RUNNING
    elif any(s == FapItem.State.PENDING for s in states):
        new = FapBatch.State.QUEUED
    elif all(s == FapItem.State.DONE for s in states):
        new = FapBatch.State.DONE
    else:
        new = FapBatch.State.ATTENTION
    if new != batch.state:
        batch.state = new
        batch.save(update_fields=["state", "updated_at"])
    return new


# --- operador ------------------------------------------------------------------------------


def pause(batch: FapBatch, *, user: User) -> None:
    with transaction.atomic():
        batch.state = FapBatch.State.PAUSED
        batch.save(update_fields=["state", "updated_at"])
        for item in batch.items.filter(state=FapItem.State.PENDING).select_related("job"):
            if item.job is not None and item.job.state == RpaJob.State.QUEUED:
                rpa.cancel(item.job.pk, organization=batch.organization)
        record_event(
            action="fap.batch.paused",
            organization=batch.organization,
            target=batch,
            metadata={"user": str(user.pk)},
        )


def resume(batch: FapBatch, *, user: User) -> int:
    if batch.state != FapBatch.State.PAUSED:
        raise FapError("O lote não está pausado.")
    count = 0
    with transaction.atomic():
        batch.state = FapBatch.State.QUEUED
        batch.save(update_fields=["state", "updated_at"])
        for item in batch.items.filter(state=FapItem.State.PENDING):
            if item.job is None or item.job.state in (RpaJob.State.CANCELLED, RpaJob.State.FAILED):
                item.generation += 1
                item.save(update_fields=["generation", "updated_at"])
                _enqueue(item)
                count += 1
        recompute(batch)
        record_event(
            action="fap.batch.resumed",
            organization=batch.organization,
            target=batch,
            metadata={"user": str(user.pk)},
        )
    return count


def reprocess(item: FapItem, *, user: User, reason: str) -> FapItem:
    """Nova consulta de um item que não deu certo. Exige motivo; o PDF antigo é preservado."""

    if item.state in FapItem.ACTIVE:
        raise FapError("O item ainda está ativo.")
    if not reason.strip():
        raise FapError("Informe o motivo do reprocesso.")
    if item.state == FapItem.State.REGISTRY:
        company = item.company
        if company is None:
            raise FapError("Empresa removida do cadastro.")
        problem = _registry_problem(company, {_digits(company.cnpj_masked): 1})
        if problem:
            raise FapError(problem)
        item.cnpj = _digits(company.cnpj_masked)
    with transaction.atomic():
        item.generation += 1
        item.state = FapItem.State.PENDING
        item.message = f"Reprocesso: {reason.strip()[:200]}"
        item.save()
        _enqueue(item)
        batch = item.batch
        if batch.state == FapBatch.State.PAUSED:
            pass
        else:
            recompute(batch)
        record_event(
            action="fap.item.reprocessed",
            organization=item.organization,
            target=item,
            metadata={"user": str(user.pk), "generation": item.generation},
        )
    return item
