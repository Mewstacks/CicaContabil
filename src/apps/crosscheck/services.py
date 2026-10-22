"""Ciclo de vida de uma conferência do Contraprova: rascunho, arquivos, fila e execução.

Molde de `reporting_exports.py` e `reconciliation_service.py`: o arrendamento é um UPDATE
condicional pelo `lease_token`, a fila só recebe depois do commit e quem perde o arrendamento
sai sem tocar no estado. O que muda é o que a execução produz: achados no banco (até um teto)
e um XLSX completo; os arquivos de entrada seguem a retenção de D-302 (ver `retention.py`).
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import tempfile
import time
import uuid
import zipfile
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path, PurePath
from typing import Any, BinaryIO, cast

from celery.exceptions import SoftTimeLimitExceeded
from django.core.exceptions import ValidationError
from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.audit.services import record_event
from apps.common.cnpj import normalize_cnpj
from apps.hub.controlplane import company_queryset_for_membership
from apps.hub.models import ClientCompany
from apps.organizations.models import Membership, Organization

from . import limits
from .engine.dominio_file import DominioRow
from .engine.efd import EfdFormatError, peek_header, peek_trailer
from .engine.findings import DIVERGENT, IGNORED, Finding, MatchedRow, RunCancelled
from .engine.keys import format_cnpj
from .engine.report import XlsxReport
from .engine.rules import RuleSet, build_rules, describe
from .engine.runner import InputFile, Problem, RunRejected, run_tool
from .engine.tools import TOOLS, UF_DOMINIO, RoleDef, ToolDef
from .engine.zipreader import ZipRejected, summarize_zip
from .models import (
    CrosscheckFinding,
    CrosscheckInput,
    CrosscheckRun,
    crosscheck_storage,
    private_result_path,
)

_BOM = b"\xef\xbb\xbf"
_ZIP_MAGIC = b"PK\x03\x04"
_PROGRESS_INTERVAL = 2.0
_FLUSH_EVERY = 1000
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")

DOMINIO_FILE = "arquivo"
DOMINIO_AGENT = "agente"


class CrosscheckError(Exception):
    """Recusa com texto seguro para a tela (sem caminho, sem rastro de erro interno)."""

    def __init__(self, messages: str | Iterable[str], code: str = "invalid") -> None:
        self.messages = [messages] if isinstance(messages, str) else list(messages)
        self.code = code
        super().__init__("; ".join(self.messages))


class LeaseLost(Exception):
    """Outro worker assumiu a conferência; este sai sem alterar nada."""


@dataclass(frozen=True)
class Issue:
    severity: str
    message: str
    role: str = ""


# ---------------------------------------------------------------------------------------
# Empresa e acesso


def company_document(company: ClientCompany) -> str:
    """CNPJ normalizado da empresa, ou vazio quando o cadastro não o tem válido."""

    try:
        return normalize_cnpj(company.cnpj_masked or "")
    except ValidationError:
        return ""


def requester_still_authorized(run: CrosscheckRun) -> bool:
    """Quem pediu continua no escritório e a empresa continua na sua carteira."""

    if run.created_by_id is None:
        return False
    membership = (
        Membership.objects.filter(
            organization_id=run.organization_id, user_id=run.created_by_id, is_active=True
        )
        .select_related("organization")
        .first()
    )
    if membership is None or not membership.organization.is_active:
        return False
    return company_queryset_for_membership(membership).filter(id=run.company_id).exists()


def _clean_name(name: str) -> str:
    text = _CONTROL.sub("", PurePath(name.replace("\\", "/")).name).strip()
    return text[:200] or "arquivo"


def _audit(
    action: str,
    run: CrosscheckRun,
    actor: Any,
    request: Any = None,
    *,
    success: bool = True,
    **metadata: object,
) -> None:
    """Auditoria sem CNPJ, nome de empresa ou de arquivo (lista proibida em `audit/models.py`)."""

    record_event(
        action=f"crosscheck.{action}",
        actor=actor,
        organization=run.organization,
        target=run,
        request=request,
        success=success,
        metadata={"run_id": str(run.id), "tool": run.tool, **metadata},
    )


# ---------------------------------------------------------------------------------------
# Rascunho


def create_draft(
    *,
    organization: Organization,
    company: ClientCompany,
    tool: str,
    competence: date,
    options: Mapping[str, Any],
    actor: Any,
    request: Any = None,
) -> CrosscheckRun:
    if tool not in TOOLS:
        raise CrosscheckError("Escolha uma das ferramentas.")
    if company.organization_id != organization.id:
        raise CrosscheckError("A empresa não pertence ao escritório.")
    if not 2000 <= competence.year <= 2100:
        raise CrosscheckError("Informe uma competência válida.")
    rules, errors = build_rules(options, tool=tool)
    if errors:
        raise CrosscheckError(errors)
    source = str(options.get("dominio_source") or DOMINIO_FILE)
    if source not in {DOMINIO_FILE, DOMINIO_AGENT}:
        raise CrosscheckError("Escolha a fonte do Domínio.")
    if source == DOMINIO_AGENT and tool == UF_DOMINIO:
        from .agent import agent_enabled

        if not agent_enabled():
            raise CrosscheckError("A consulta pelo agente não está habilitada.")
    run = CrosscheckRun(
        organization=organization,
        company=company,
        tool=tool,
        competence=competence.replace(day=1),
        options={"dominio_source": source if tool == UF_DOMINIO else DOMINIO_FILE},
        rules_snapshot=rules.snapshot(),
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    run.clean()
    run.save()
    _audit("run.created", run, actor, request)
    return run


# ---------------------------------------------------------------------------------------
# Arquivos


def _sha256(upload: UploadedFile) -> str:
    digest = hashlib.sha256()
    upload.seek(0)
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    return digest.hexdigest()


def _head(upload: UploadedFile, size: int = 8) -> bytes:
    upload.seek(0)
    data = bytes(upload.read(size))
    upload.seek(0)
    return data


def _extension(name: str) -> str:
    return PurePath(name).suffix.lower()


def _inspect_efd(upload: UploadedFile, name: str, run: CrosscheckRun) -> dict[str, Any]:
    try:
        header = peek_header(cast(BinaryIO, upload))
    except EfdFormatError as exc:
        raise CrosscheckError(f"{name}: {exc.message}") from exc
    declared = peek_trailer(cast(BinaryIO, upload))
    company_doc = company_document(run.company)
    notes: list[str] = []
    if company_doc and header.cnpj != company_doc:
        if header.cnpj[:8] == company_doc[:8]:
            notes.append("Outro estabelecimento da mesma empresa.")
        else:
            raise CrosscheckError(
                f"{name}: o SPED é do CNPJ {format_cnpj(header.cnpj)}, "
                "que não é o da empresa escolhida."
            )
    if header.competence != f"{run.competence:%Y-%m}":
        notes.append(
            f"Competência do SPED: {header.dt_ini.month:02d}/{header.dt_ini.year}, "
            f"diferente da escolhida ({run.competence_label})."
        )
    if declared is None:
        notes.append("Sem o registro 9999 no fim: o arquivo pode estar incompleto.")
    return {
        "cnpj": header.cnpj,
        "nome": header.nome,
        "uf": header.uf,
        "competencia": header.competence,
        "periodo": [header.dt_ini.isoformat(), header.dt_fin.isoformat()],
        "cod_ver": header.cod_ver,
        "finalidade": "substituto" if header.cod_fin == "1" else "original",
        "linhas_declaradas": declared,
        "avisos": notes,
    }


def _inspect_zip(upload: UploadedFile, name: str) -> tuple[dict[str, Any], int]:
    try:
        summary = summarize_zip(cast(BinaryIO, upload))
    except ZipRejected as exc:
        raise CrosscheckError(f"{name}: {exc}") from exc
    finally:
        upload.seek(0)
    if summary.xml_entries == 0:
        raise CrosscheckError(f"{name}: o ZIP não tem nenhum arquivo XML.")
    notes = []
    other = summary.entries - summary.xml_entries
    if other:
        notes.append(f"{other} arquivo(s) que não são XML serão ignorados.")
    return (
        {"entradas": summary.entries, "xml": summary.xml_entries, "avisos": notes},
        summary.xml_entries,
    )


def _inspect_dominio(upload: UploadedFile, name: str) -> dict[str, Any]:
    extension = _extension(name)
    if extension not in {".csv", ".xlsx", ".txt"}:
        raise CrosscheckError(f"{name}: envie o Domínio em CSV ou XLSX.")
    head = _head(upload, 4)
    if extension == ".xlsx":
        if head != _ZIP_MAGIC:
            raise CrosscheckError(f"{name}: o arquivo não é uma planilha XLSX.")
        try:
            with zipfile.ZipFile(upload) as archive:
                names = set(archive.namelist())
                total = sum(info.file_size for info in archive.infolist())
        except (zipfile.BadZipFile, OSError, EOFError) as exc:
            raise CrosscheckError(f"{name}: o arquivo não é uma planilha XLSX válida.") from exc
        finally:
            upload.seek(0)
        if "xl/workbook.xml" not in names or total > 400 * limits.MiB:
            raise CrosscheckError(f"{name}: o arquivo não é uma planilha XLSX válida.")
        return {"formato": "xlsx"}
    if head == _ZIP_MAGIC or b"\x00" in _head(upload, 4096):
        raise CrosscheckError(f"{name}: o arquivo não é um CSV de texto.")
    return {"formato": "csv"}


def _write_loose_zip(files: list[tuple[str, bytes]]) -> tempfile.SpooledTemporaryFile[bytes]:
    # Quem chama fecha (`_attach_loose`, em `finally`); fechar aqui apagaria o ZIP pronto.
    handle: tempfile.SpooledTemporaryFile[bytes] = tempfile.SpooledTemporaryFile(  # noqa: SIM115
        max_size=8 * limits.MiB
    )
    used: Counter[str] = Counter()
    with zipfile.ZipFile(handle, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files:
            used[name] += 1
            entry = name if used[name] == 1 else f"{used[name]}-{name}"
            archive.writestr(entry, data)
    handle.seek(0)
    return handle


def _store_input(
    run: CrosscheckRun,
    *,
    role: str,
    kind: str,
    name: str,
    content: Any,
    size: int,
    sha: str,
    detected: dict[str, Any],
    xml_count: int,
    actor: Any,
) -> CrosscheckInput:
    item = CrosscheckInput(
        organization=run.organization,
        run=run,
        role=role,
        kind=kind,
        original_name=name,
        size_bytes=size,
        sha256=sha,
        detected=detected,
        xml_count=xml_count,
        uploaded_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    item.content.save(name, content, save=False)
    item.save()
    return item


@dataclass
class AttachResult:
    """O que entrou e o que foi recusado numa remessa: um erro não derruba os outros arquivos."""

    stored: list[CrosscheckInput] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def attach_files(
    run: CrosscheckRun,
    role: str,
    uploads: list[UploadedFile],
    *,
    actor: Any,
    request: Any = None,
) -> AttachResult:
    """Recebe os arquivos de um papel e devolve os recibos. Recusa o que não presta."""

    if not uploads:
        raise CrosscheckError("Selecione ao menos um arquivo.")
    try:
        role_def = TOOLS[run.tool].role(role)
    except KeyError as exc:
        raise CrosscheckError("Esse papel de arquivo não existe nesta ferramenta.") from exc
    result = AttachResult()
    units: list[tuple[str, Any]] = []
    if role_def.kind == "xml":
        loose: list[UploadedFile] = []
        for upload in uploads:
            extension = _extension(upload.name or "")
            if extension == ".zip":
                units.append(("zip", upload))
            elif extension == ".xml":
                loose.append(upload)
            else:
                result.errors.append(f"{_clean_name(upload.name or '')}: envie XML ou ZIP de XML.")
        if loose:
            units.append(("loose", loose))
    else:
        units = [("single", upload) for upload in uploads]
    for mode, payload in units:
        try:
            item = _attach_unit(run, role, role_def, mode, payload, actor)
        except CrosscheckError as exc:
            result.errors.extend(exc.messages)
            continue
        result.stored.append(item)
        _audit(
            "input.added",
            run,
            actor,
            request,
            role=item.role,
            kind=item.kind,
            size_bytes=item.size_bytes,
            sha256=item.sha256,
            xml_count=item.xml_count,
        )
    return result


def _attach_unit(
    run: CrosscheckRun, role: str, role_def: RoleDef, mode: str, payload: Any, actor: Any
) -> CrosscheckInput:
    with transaction.atomic():
        # of=("self",): the nullable `company` join cannot be row-locked on PostgreSQL.
        locked = (
            CrosscheckRun.objects.select_for_update(of=("self",))
            .select_related("company")
            .get(pk=run.pk)
        )
        if locked.state != CrosscheckRun.State.DRAFT:
            raise CrosscheckError("A conferência já foi enviada; abra um rascunho novo.")
        existing = list(locked.inputs.all())
        if role_def.kind == "dominio" and dominio_source(locked) == DOMINIO_AGENT:
            raise CrosscheckError("O Domínio desta conferência vem do agente, não de arquivo.")
        if sum(1 for item in existing if item.role == role) >= role_def.maximum:
            raise CrosscheckError(f"{role_def.label}: o limite de arquivos foi atingido.")
        if mode == "single":
            item = _attach_single(locked, role, role_def.kind, payload, existing, actor)
        elif mode == "zip":
            item = _attach_zip(locked, role, payload, existing, actor)
        else:
            item = _attach_loose(locked, role, payload, existing, actor)
        CrosscheckRun.objects.filter(pk=run.pk).update(updated_at=timezone.now())
    return item


def _check_totals(existing: list[CrosscheckInput], size: int, name: str) -> None:
    if sum(item.size_bytes for item in existing) + size > limits.MAX_RUN_BYTES:
        raise CrosscheckError(
            f"{name}: a soma dos arquivos passa de {limits.MAX_RUN_BYTES // limits.MiB} MiB."
        )


def _attach_single(
    run: CrosscheckRun,
    role: str,
    kind: str,
    upload: UploadedFile,
    existing: list[CrosscheckInput],
    actor: Any,
) -> CrosscheckInput:
    name = _clean_name(upload.name or "")
    size = int(upload.size or 0)
    if size <= 0:
        raise CrosscheckError(f"{name}: o arquivo está vazio.")
    cap = limits.MAX_SPED_BYTES if kind == "efd" else limits.MAX_DOMINIO_BYTES
    if size > cap:
        raise CrosscheckError(f"{name}: acima de {cap // limits.MiB} MiB.")
    if kind == "efd":
        if _extension(name) not in {".txt", ".sped"}:
            raise CrosscheckError(f"{name}: envie o SPED em .txt.")
        detected = _inspect_efd(upload, name, run)
    else:
        detected = _inspect_dominio(upload, name)
    _check_totals(existing, size, name)
    sha = _sha256(upload)
    if any(item.role == role and item.sha256 == sha for item in existing):
        raise CrosscheckError(f"{name}: esse arquivo já foi enviado.")
    return _store_input(
        run,
        role=role,
        kind=kind,
        name=name,
        content=upload,
        size=size,
        sha=sha,
        detected=detected,
        xml_count=0,
        actor=actor,
    )


def _attach_zip(
    run: CrosscheckRun,
    role: str,
    upload: UploadedFile,
    existing: list[CrosscheckInput],
    actor: Any,
) -> CrosscheckInput:
    name = _clean_name(upload.name or "")
    size = int(upload.size or 0)
    if size <= 0:
        raise CrosscheckError(f"{name}: o arquivo está vazio.")
    if size > limits.MAX_ZIP_BYTES:
        raise CrosscheckError(f"{name}: acima de {limits.MAX_ZIP_BYTES // limits.MiB} MiB.")
    if _head(upload, 4) != _ZIP_MAGIC:
        raise CrosscheckError(f"{name}: o arquivo não é um ZIP.")
    detected, count = _inspect_zip(upload, name)
    if sum(item.xml_count for item in existing) + count > limits.MAX_XML_PER_RUN:
        raise CrosscheckError(
            f"{name}: a conferência aceita até {limits.MAX_XML_PER_RUN} XML no total."
        )
    _check_totals(existing, size, name)
    sha = _sha256(upload)
    if any(item.role == role and item.sha256 == sha for item in existing):
        raise CrosscheckError(f"{name}: esse arquivo já foi enviado.")
    return _store_input(
        run,
        role=role,
        kind="xml",
        name=name,
        content=upload,
        size=size,
        sha=sha,
        detected=detected,
        xml_count=count,
        actor=actor,
    )


def _attach_loose(
    run: CrosscheckRun,
    role: str,
    loose: list[UploadedFile],
    existing: list[CrosscheckInput],
    actor: Any,
) -> CrosscheckInput:
    """XML soltos viram um ZIP no servidor: um arquivo só para guardar, baixar e ler."""

    if len(loose) > limits.MAX_LOOSE_XML_PER_REQUEST:
        raise CrosscheckError(
            f"Envie no máximo {limits.MAX_LOOSE_XML_PER_REQUEST} XML soltos por vez; "
            "para mais que isso, use um ZIP."
        )
    payload: list[tuple[str, bytes]] = []
    received = 0
    for upload in loose:
        name = _clean_name(upload.name or "")
        size = int(upload.size or 0)
        if size <= 0 or size > limits.MAX_XML_BYTES:
            raise CrosscheckError(
                f"{name}: XML vazio ou acima de {limits.MAX_XML_BYTES // limits.MiB} MiB."
            )
        received += size
        if received > limits.MAX_LOOSE_XML_BYTES_PER_REQUEST:
            raise CrosscheckError(
                "Os XML desta remessa passam de "
                f"{limits.MAX_LOOSE_XML_BYTES_PER_REQUEST // limits.MiB} MiB; envie em partes."
            )
        upload.seek(0)
        data = upload.read(limits.MAX_XML_BYTES + 1)
        upload.seek(0)
        probe = data[len(_BOM) :] if data.startswith(_BOM) else data
        if b"\x00" in data[:4096] or probe.lstrip()[:1] != b"<":
            raise CrosscheckError(f"{name}: o arquivo não é um XML.")
        payload.append((name, data))
    if sum(item.xml_count for item in existing) + len(payload) > limits.MAX_XML_PER_RUN:
        raise CrosscheckError(f"A conferência aceita até {limits.MAX_XML_PER_RUN} XML no total.")
    handle = _write_loose_zip(payload)
    try:
        size = handle.seek(0, 2)
        handle.seek(0)
        digest = hashlib.sha256()
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
        handle.seek(0)
        sha = digest.hexdigest()
        label = f"{len(payload)} XML"
        _check_totals(existing, size, label)
        if any(item.role == role and item.sha256 == sha for item in existing):
            raise CrosscheckError("Essa remessa de XML já foi enviada.")
        return _store_input(
            run,
            role=role,
            kind="xml",
            name=f"{label} soltos.zip",
            content=File(handle, name="lote.zip"),
            size=size,
            sha=sha,
            detected={"entradas": len(payload), "xml": len(payload), "avisos": [], "soltos": True},
            xml_count=len(payload),
            actor=actor,
        )
    finally:
        handle.close()


def _delete_file(item: CrosscheckInput) -> None:
    """Apaga o objeto só se nenhuma outra entrada ainda o referencia."""

    name = item.content.name
    if not name:
        return
    shared = (
        CrosscheckInput.objects.filter(content=name, purged_at__isnull=True)
        .exclude(pk=item.pk)
        .exists()
    )
    if not shared:
        crosscheck_storage().delete(name)


def remove_input(
    run: CrosscheckRun, input_id: uuid.UUID, *, actor: Any, request: Any = None
) -> None:
    with transaction.atomic():
        locked = CrosscheckRun.objects.select_for_update().get(pk=run.pk)
        if locked.state != CrosscheckRun.State.DRAFT:
            raise CrosscheckError("A conferência já foi enviada; os arquivos não mudam mais.")
        item = locked.inputs.filter(pk=input_id).first()
        if item is None:
            raise CrosscheckError("Arquivo não encontrado.", code="not_found")
        role, kind, sha = item.role, item.kind, item.sha256
        _delete_file(item)
        item.delete()
        CrosscheckRun.objects.filter(pk=run.pk).update(updated_at=timezone.now())
    _audit("input.removed", run, actor, request, role=role, kind=kind, sha256=sha)


# ---------------------------------------------------------------------------------------
# Prontidão e envio


def dominio_source(run: CrosscheckRun) -> str:
    return str(run.options.get("dominio_source") or DOMINIO_FILE)


def agent_rows_ready(run: CrosscheckRun) -> bool:
    from . import agent

    return agent.rows_ready(run)


def readiness(run: CrosscheckRun) -> list[Issue]:
    """O que ainda impede de conferir (erro) ou merece atenção (aviso)."""

    tool = TOOLS[run.tool]
    inputs = list(run.inputs.all())
    issues: list[Issue] = []
    for role in tool.roles:
        count = sum(1 for item in inputs if item.role == role.code)
        if count < role.minimum:
            issues.append(Issue("error", f"Falta o arquivo: {role.label}.", role.code))
    if run.tool == UF_DOMINIO:
        has_file = any(item.role == "dominio" for item in inputs)
        if dominio_source(run) == DOMINIO_AGENT:
            if not agent_rows_ready(run):
                issues.append(Issue("error", "O agente ainda não trouxe o Domínio.", "dominio"))
        elif not has_file:
            issues.append(Issue("error", "Falta o arquivo: Domínio.", "dominio"))
    xml_total = sum(item.xml_count for item in inputs if item.kind == "xml")
    if xml_total > limits.MAX_XML_PER_RUN:
        issues.append(Issue("error", f"Mais de {limits.MAX_XML_PER_RUN} XML na conferência."))
    for item in inputs:
        for note in item.detected.get("avisos", []):
            issues.append(Issue("warning", f"{item.original_name}: {note}", item.role))
    return issues


def inputs_fingerprint(run: CrosscheckRun) -> str:
    material = {
        "engine": limits.ENGINE_VERSION,
        "tool": run.tool,
        "company": str(run.company_id),
        "competence": f"{run.competence:%Y-%m}",
        "rules": run.rules_snapshot,
        "dominio": dominio_source(run),
        "inputs": sorted((item.role, item.sha256) for item in run.inputs.all()),
    }
    blob = json.dumps(material, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode()).hexdigest()


def active_runs(organization: Organization) -> QuerySet[CrosscheckRun]:
    return CrosscheckRun.objects.filter(
        organization=organization, state__in=CrosscheckRun.ACTIVE_STATES
    )


def start_run(
    run: CrosscheckRun, *, actor: Any, request: Any = None, dispatch: bool = True
) -> tuple[CrosscheckRun, bool]:
    """Enfileira a conferência. Devolve (conferência, reaproveitada).

    `dispatch=False` deixa a conferência na fila sem enviar a tarefa: quem chama (o comando de
    demonstração, um teste) executa `process_run` ele mesmo.

    Se já existe uma conferência concluída e ainda guardada com exatamente as mesmas
    entradas, empresa, competência, regras e versão do motor, ela é devolvida no lugar e o
    rascunho é descartado: o motor é determinístico, repetir só gastaria o worker.
    """

    from .tasks import process_run_task

    with transaction.atomic():
        locked = (
            CrosscheckRun.objects.select_for_update(of=("self",))
            .select_related("company", "organization")
            .get(pk=run.pk)
        )
        if locked.state != CrosscheckRun.State.DRAFT:
            raise CrosscheckError("Esta conferência já foi enviada.")
        errors = [item.message for item in readiness(locked) if item.severity == "error"]
        if errors:
            raise CrosscheckError(errors, code="not_ready")
        if active_runs(locked.organization).count() >= limits.MAX_ACTIVE_RUNS_PER_OFFICE:
            raise CrosscheckError(
                "Já há conferências em andamento neste escritório; aguarde uma terminar.",
                code="busy",
            )
        fingerprint = inputs_fingerprint(locked)
        if dominio_source(locked) != DOMINIO_AGENT:
            twin = (
                CrosscheckRun.objects.filter(
                    organization=locked.organization,
                    company=locked.company,
                    inputs_fingerprint=fingerprint,
                    state=CrosscheckRun.State.DONE,
                    results_expire_at__gt=timezone.now(),
                )
                .exclude(pk=locked.pk)
                .order_by("-finished_at")
                .first()
            )
            if twin is not None:
                for item in list(locked.inputs.all()):
                    _delete_file(item)
                locked.delete()
                return twin, True
        now = timezone.now()
        locked.state = CrosscheckRun.State.QUEUED
        locked.stage = "queued"
        locked.inputs_fingerprint = fingerprint
        locked.queued_at = now
        locked.attempts = 0
        locked.problems = []
        locked.error_code = ""
        locked.cancel_requested_at = None
        locked.save(
            update_fields=[
                "state",
                "stage",
                "inputs_fingerprint",
                "queued_at",
                "attempts",
                "problems",
                "error_code",
                "cancel_requested_at",
                "updated_at",
            ]
        )
        run_id = str(locked.id)
        if dispatch:
            transaction.on_commit(lambda: process_run_task.delay(run_id))
    _audit(
        "run.queued",
        locked,
        actor,
        request,
        input_count=locked.inputs.count(),
        fingerprint=fingerprint,
    )
    return locked, False


def cancel_run(run: CrosscheckRun, *, actor: Any, request: Any = None) -> CrosscheckRun:
    now = timezone.now()
    with transaction.atomic():
        locked = CrosscheckRun.objects.select_for_update().get(pk=run.pk)
        if locked.is_terminal:
            raise CrosscheckError("Esta conferência já terminou.")
        if locked.state == CrosscheckRun.State.PROCESSING:
            locked.cancel_requested_at = now
            locked.save(update_fields=["cancel_requested_at", "updated_at"])
            outcome = "cancel_requested"
        else:
            locked.state = CrosscheckRun.State.CANCELED
            locked.stage = ""
            locked.finished_at = now
            locked.cancel_requested_at = now
            locked.save(
                update_fields=["state", "stage", "finished_at", "cancel_requested_at", "updated_at"]
            )
            outcome = "canceled"
    _audit("run.cancel", locked, actor, request, outcome=outcome)
    return locked


def repeat_run(
    run: CrosscheckRun,
    *,
    options: Mapping[str, Any] | None,
    actor: Any,
    request: Any = None,
) -> CrosscheckRun:
    """Novo rascunho com os mesmos arquivos (ainda guardados) e, opcionalmente, outras regras."""

    if not run.is_terminal and run.state != CrosscheckRun.State.DRAFT:
        raise CrosscheckError("Espere a conferência terminar para repetir.")
    if not run.inputs_available:
        raise CrosscheckError(
            "Os arquivos desta conferência já foram apagados; envie-os de novo.", code="purged"
        )
    merged: dict[str, Any] = dict(run.rules_snapshot)
    merged.update(run.options)
    if options:
        merged.update(options)
    with transaction.atomic():
        fresh = create_draft(
            organization=run.organization,
            company=run.company,
            tool=run.tool,
            competence=run.competence,
            options=merged,
            actor=actor,
            request=request,
        )
        for source in run.inputs.all():
            if not source.content.name:
                raise CrosscheckError(
                    "Os arquivos desta conferência já foram apagados; envie-os de novo.",
                    code="purged",
                )
            CrosscheckInput.objects.create(
                organization=run.organization,
                run=fresh,
                role=source.role,
                kind=source.kind,
                original_name=source.original_name,
                size_bytes=source.size_bytes,
                sha256=source.sha256,
                content=source.content.name,
                detected=source.detected,
                xml_count=source.xml_count,
                uploaded_by=source.uploaded_by,
            )
    _audit("run.repeated", fresh, actor, request, source_run_id=str(run.id))
    return fresh


# ---------------------------------------------------------------------------------------
# Execução (worker)


def _problem_dict(problem: Problem) -> dict[str, str]:
    return {
        "severity": problem.severity,
        "code": problem.code,
        "message": problem.message,
        "file": problem.file,
    }


def _to_row(run_id: uuid.UUID, seq: int, finding: Finding) -> CrosscheckFinding:
    return CrosscheckFinding(
        run_id=run_id,
        seq=seq,
        kind=finding.kind[:32],
        status=finding.status[:10],
        doc_key=finding.doc_key[:80],
        doc_type=finding.doc_type[:8],
        number=finding.number[:20],
        field=finding.field[:40],
        field_label=finding.field_label[:120],
        left_cents=finding.left_cents,
        right_cents=finding.right_cents,
        left_text=finding.left_text[:120],
        right_text=finding.right_text[:120],
        cfop=finding.cfop[:60],
        operation=finding.operation[:1],
        message=finding.message[:300],
        detail=finding.detail,
    )


class RunSink:
    """Grava os achados em lote, alimenta o XLSX, renova o arrendamento e vê o cancelamento."""

    def __init__(self, run_id: uuid.UUID, token: uuid.UUID, report: XlsxReport) -> None:
        self.run_id = run_id
        self.token = token
        self.report = report
        self.buffer: list[CrosscheckFinding] = []
        self.seq = 0
        self.stored = 0
        self.truncated = False
        self.statuses: Counter[str] = Counter()
        self.by_kind: Counter[str] = Counter()
        self.matched_count = 0
        self._stage = ""
        self._last_progress = 0.0
        self._last_cancel_check = 0.0
        self._cancel = False

    def finding(self, finding: Finding) -> None:
        self.seq += 1
        self.statuses[finding.status] += 1
        self.by_kind[f"{finding.kind}:{finding.status}"] += 1
        self.report.finding(finding)
        if self.stored >= limits.MAX_FINDINGS_STORED:
            self.truncated = True
            return
        self.stored += 1
        self.buffer.append(_to_row(self.run_id, self.seq, finding))
        if len(self.buffer) >= _FLUSH_EVERY:
            self.flush()

    def matched(self, row: MatchedRow) -> None:
        self.matched_count += 1
        self.report.matched(row)

    def flush(self) -> None:
        if self.buffer:
            CrosscheckFinding.objects.bulk_create(self.buffer, batch_size=500)
            self.buffer = []

    def _renew(self, **fields: object) -> None:
        now = timezone.now()
        updated = CrosscheckRun.objects.filter(pk=self.run_id, lease_token=self.token).update(
            lease_until=now + limits.RUN_LEASE, updated_at=now, **fields
        )
        if not updated:
            raise LeaseLost

    def progress(self, stage: str, done: int, total: int | None = None) -> None:
        now = time.monotonic()
        if stage == self._stage and now - self._last_progress < _PROGRESS_INTERVAL:
            return
        self._stage = stage
        self._last_progress = now
        self._renew(stage=stage[:40], progress_done=done, progress_total=total)

    def cancelled(self) -> bool:
        if self._cancel:
            return True
        now = time.monotonic()
        if now - self._last_cancel_check < _PROGRESS_INTERVAL:
            return False
        self._last_cancel_check = now
        row = (
            CrosscheckRun.objects.filter(pk=self.run_id)
            .values_list("lease_token", "cancel_requested_at")
            .first()
        )
        if row is None or row[0] != self.token:
            raise LeaseLost
        self._cancel = row[1] is not None
        return self._cancel


def _claim(run_id: uuid.UUID, token: uuid.UUID) -> str | CrosscheckRun:
    now = timezone.now()
    with transaction.atomic():
        run = (
            CrosscheckRun.objects.select_for_update(of=("self",))
            .select_related("organization", "company", "created_by")
            .filter(pk=run_id)
            .first()
        )
        if run is None:
            return "missing"
        if run.state == CrosscheckRun.State.PROCESSING and (
            run.lease_until is not None and run.lease_until >= now
        ):
            return "busy"
        if run.state not in {CrosscheckRun.State.QUEUED, CrosscheckRun.State.PROCESSING}:
            return "not_queued"
        if run.cancel_requested_at is not None:
            run.state = CrosscheckRun.State.CANCELED
            run.finished_at = now
            run.lease_token = None
            run.lease_until = None
            run.save(update_fields=["state", "finished_at", "lease_token", "lease_until"])
            return "canceled"
        if run.attempts >= limits.MAX_ATTEMPTS:
            run.state = CrosscheckRun.State.FAILED
            run.error_code = "tentativas"
            run.problems = [
                {
                    "severity": "error",
                    "code": "tentativas",
                    "message": "A conferência não terminou depois de várias tentativas.",
                    "file": "",
                }
            ]
            run.finished_at = now
            run.lease_token = None
            run.lease_until = None
            run.save(
                update_fields=[
                    "state",
                    "error_code",
                    "problems",
                    "finished_at",
                    "lease_token",
                    "lease_until",
                ]
            )
            return "attempts"
        run.state = CrosscheckRun.State.PROCESSING
        run.attempts += 1
        run.lease_token = token
        run.lease_until = now + limits.RUN_LEASE
        run.started_at = now
        run.stage = "Preparando"
        run.progress_done = 0
        run.progress_total = None
        run.save(
            update_fields=[
                "state",
                "attempts",
                "lease_token",
                "lease_until",
                "started_at",
                "stage",
                "progress_done",
                "progress_total",
                "updated_at",
            ]
        )
        return run


def _finish_failed(
    run_id: uuid.UUID, token: uuid.UUID, code: str, problems: list[dict[str, str]]
) -> bool:
    CrosscheckFinding.objects.filter(run_id=run_id).delete()
    return bool(
        CrosscheckRun.objects.filter(pk=run_id, lease_token=token).update(
            state=CrosscheckRun.State.FAILED,
            error_code=code[:60],
            problems=problems,
            stage="",
            finished_at=timezone.now(),
            lease_token=None,
            lease_until=None,
            finding_count=0,
            divergent_count=0,
            ignored_count=0,
            matched_count=0,
        )
    )


_GONE = "Os arquivos desta conferência já foram apagados; envie-os de novo."


def _download(item: CrosscheckInput, destination: Path) -> None:
    try:
        with item.content.open("rb") as source, destination.open("wb") as target:
            shutil.copyfileobj(source, target, 1024 * 1024)
    except FileNotFoundError as exc:
        raise RunRejected([Problem("error", "arquivo_ausente", _GONE, item.original_name)]) from exc


def process_run(run_id: str) -> str:
    """Executa uma conferência. Reentregar a tarefa é seguro: quem não tem o arrendamento sai."""

    try:
        parsed = uuid.UUID(str(run_id))
    except (TypeError, ValueError, AttributeError):
        return "invalid_id"
    token = uuid.uuid4()
    claimed = _claim(parsed, token)
    if isinstance(claimed, str):
        return claimed
    run = claimed
    tool = TOOLS[run.tool]
    started = time.monotonic()
    try:
        if not requester_still_authorized(run):
            _finish_failed(
                parsed,
                token,
                "access_revoked",
                [
                    {
                        "severity": "error",
                        "code": "access_revoked",
                        "message": "Quem pediu a conferência não tem mais acesso à empresa.",
                        "file": "",
                    }
                ],
            )
            return "access_revoked"
        return _execute(run, tool, token, started)
    except LeaseLost:
        return "superseded"
    except RunCancelled:
        CrosscheckFinding.objects.filter(run_id=parsed).delete()
        done = CrosscheckRun.objects.filter(pk=parsed, lease_token=token).update(
            state=CrosscheckRun.State.CANCELED,
            stage="",
            finished_at=timezone.now(),
            lease_token=None,
            lease_until=None,
        )
        if done:
            _audit("run.canceled", run, run.created_by)
        return "canceled"
    except RunRejected as exc:
        problems = [_problem_dict(item) for item in exc.problems]
        code = exc.problems[0].code if exc.problems else "rejeitada"
        if _finish_failed(parsed, token, code, problems):
            _audit("run.failed", run, run.created_by, success=False, reason="rejected")
        return "rejected"
    except SoftTimeLimitExceeded:
        _finish_failed(
            parsed,
            token,
            "tempo_esgotado",
            [
                {
                    "severity": "error",
                    "code": "tempo_esgotado",
                    "message": "A conferência passou do tempo limite; divida os arquivos.",
                    "file": "",
                }
            ],
        )
        _audit("run.failed", run, run.created_by, success=False, reason="timeout")
        return "timeout"
    except Exception:
        _finish_failed(
            parsed,
            token,
            "inesperado",
            [
                {
                    "severity": "error",
                    "code": "inesperado",
                    "message": "A conferência falhou por um erro inesperado; tente de novo.",
                    "file": "",
                }
            ],
        )
        _audit("run.failed", run, run.created_by, success=False, reason="unexpected")
        raise


def _execute(run: CrosscheckRun, tool: ToolDef, token: uuid.UUID, started: float) -> str:
    CrosscheckFinding.objects.filter(run_id=run.id).delete()
    rules = RuleSet.from_snapshot(run.rules_snapshot)
    storage = crosscheck_storage()
    inputs = list(run.inputs.all())
    if any(not item.content.name or item.purged_at is not None for item in inputs):
        raise RunRejected(
            [
                Problem(
                    "error",
                    "arquivo_ausente",
                    "Os arquivos desta conferência já foram apagados; envie-os de novo.",
                )
            ]
        )
    with tempfile.TemporaryDirectory(prefix="contraprova-") as raw:
        workdir = Path(raw)
        files: list[InputFile] = []
        for index, item in enumerate(inputs):
            target = workdir / f"entrada-{index:03d}.bin"
            _download(item, target)
            files.append(InputFile(role=item.role, path=target, name=item.original_name))
        report = XlsxReport(tool, f"{tool.label} - competência {run.competence_label}")
        sink = RunSink(run.id, token, report)
        try:
            outcome = run_tool(
                run.tool,
                company_doc=company_document(run.company),
                competence=f"{run.competence:%Y-%m}",
                rules=rules,
                inputs=files,
                workdir=workdir,
                sink=sink,
                dominio_rows=_agent_rows(run),
            )
            sink.flush()
            sink.progress("Relatório", 0, None)
        except BaseException:
            report.abort()
            raise
        warnings = [_problem_dict(item) for item in outcome.warnings]
        counts = dict(outcome.counts)
        counts["conferem"] = counts.get("conferem", sink.matched_count)
        xlsx_path = workdir / "resultado.xlsx"
        report.finish(
            xlsx_path,
            facts={
                "Ferramenta": tool.label,
                "Competência": run.competence_label,
                "Divergências": sink.statuses.get(DIVERGENT, 0),
                "Ignoradas por regra": sink.statuses.get(IGNORED, 0),
            },
            rules=describe(rules, run.tool),
            files=[
                (item.name, f"{item.kind}; {json.dumps(item.details, ensure_ascii=False)}")
                for item in outcome.files
            ],
            counts=counts,
        )
        digest = hashlib.sha256()
        with xlsx_path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        size = xlsx_path.stat().st_size
        with xlsx_path.open("rb") as handle:
            saved = storage.save(private_result_path(run, "resultado.xlsx"), File(handle))
        finished = timezone.now()
        summary = {
            "counts": counts,
            "ingest": outcome.ingest,
            "files": [
                {"role": item.role, "name": item.name, "kind": item.kind, "details": item.details}
                for item in outcome.files
            ],
            "by_kind": dict(sink.by_kind),
            "xlsx_truncated": report.truncated,
            "engine_version": limits.ENGINE_VERSION,
            "seconds": round(time.monotonic() - started, 1),
        }
        updated = CrosscheckRun.objects.filter(pk=run.id, lease_token=token).update(
            state=CrosscheckRun.State.DONE,
            stage="done",
            problems=warnings,
            error_code="",
            summary=summary,
            finding_count=sink.seq,
            divergent_count=sink.statuses.get(DIVERGENT, 0),
            ignored_count=sink.statuses.get(IGNORED, 0),
            matched_count=counts["conferem"],
            findings_truncated=sink.truncated,
            result_file=saved,
            result_sha256=digest.hexdigest(),
            result_size=size,
            finished_at=finished,
            results_expire_at=finished + limits.RESULT_RETENTION,
            lease_token=None,
            lease_until=None,
            progress_done=0,
            progress_total=None,
        )
    if not updated:
        storage.delete(saved)
        raise LeaseLost
    _audit(
        "run.done",
        run,
        run.created_by,
        divergent=sink.statuses.get(DIVERGENT, 0),
        ignored=sink.statuses.get(IGNORED, 0),
        matched=counts["conferem"],
        truncated=sink.truncated,
        seconds=summary["seconds"],
    )
    return "done"


def _agent_rows(run: CrosscheckRun) -> Iterable[DominioRow] | None:
    """Linhas do Domínio recebidas do agente; sem agente, o motor lê o arquivo enviado."""

    if dominio_source(run) != DOMINIO_AGENT:
        return None
    from . import agent

    return agent.iter_rows(run)


# ---------------------------------------------------------------------------------------
# Consultas usadas pela tela e pelo painel


def runs_needing_attention(organization: Organization, companies: Any) -> int:
    """Conferências concluídas nos últimos 30 dias com divergência, na carteira informada."""

    since = timezone.now() - timedelta(days=30)
    return (
        CrosscheckRun.objects.filter(
            organization=organization,
            company__in=companies,
            state=CrosscheckRun.State.DONE,
            finished_at__gte=since,
            divergent_count__gt=0,
        )
        .filter(Q(results_expire_at__isnull=True) | Q(results_expire_at__gt=timezone.now()))
        .count()
    )
