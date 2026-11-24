"""Carteira de clientes por planilha, para escritório em modo procuração (D-304, E2).

A planilha vira prévia linha a linha antes de qualquer gravação. Só entra empresa com CNPJ válido.
Empresa que já existe só recebe o e-mail de contato: nome e CNPJ de quem veio do Domínio nunca são
sobrescritos (D-277). Nada é apagado nem desativado por aqui, e o legado (`imports.confirm_import`)
não é tocado: os escritórios em modo `certificate` seguem pelo caminho antigo.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.core.validators import validate_email
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.common.cnpj import normalize_cnpj
from apps.hub.imports import (
    MAX_TABULAR_BYTES,
    ImportValidationError,
    _pick,
    _read_upload,
    _tabular_rows,
)
from apps.hub.models import ClientCompany, CompanyAccessGrant, DataSource, ImportBatch
from apps.hub.module_catalog import OFFERED_MODULE_CODES
from apps.organizations.models import Membership, Organization

SOURCE_LABEL = "Planilha de carteira"
TEMPLATE_HEADER = ("nome", "cnpj", "email", "codigo")
ERROR_REPORT_HEADER = ("linha", "nome", "cnpj", "email", "codigo", "situacao", "motivo")
MAX_NAME = 180
# LGPD: prévia esquecida (planilha cifrada) e relatório de ocorrências não ficam para sempre.
PREVIEW_RETENTION = timedelta(days=7)
REPORT_RETENTION = timedelta(days=30)
MAX_REPORT_ERRORS = 200

# Cabeçalhos já normalizados por `imports._normalize_header` (acento vira "_": "Razão" -> "raz_o").
NAME_COLUMNS = (
    "nome",
    "razao_social",
    "raz_o_social",
    "razao",
    "raz_o",
    "empresa",
    "nome_empresa",
    "nome_da_empresa",
    "cliente",
)
CNPJ_COLUMNS = ("cnpj", "cnpj_empresa", "cnpj_cliente")
EMAIL_COLUMNS = (
    "email",
    "e_mail",
    "email_contato",
    "contato_email",
    "email_cliente",
    "email_do_cliente",
)
CODE_COLUMNS = ("codigo", "c_digo", "codigo_empresa", "c_digo_empresa", "external_key", "cod")

CREATE = "create"
UPDATE = "update"
SAME = "same"
PROBLEM = "problem"
STATUS_LABELS = {
    CREATE: "Nova",
    UPDATE: "Atualiza e-mail",
    SAME: "Já existe",
    PROBLEM: "Com problema",
}


@dataclass(frozen=True)
class RosterLine:
    """Uma linha da planilha, já avaliada. `number` é a linha da planilha (cabeçalho = 1)."""

    number: int
    name: str
    cnpj: str
    email: str
    code: str
    action: str
    problems: tuple[str, ...] = ()
    notes: tuple[str, ...] = ()
    company_id: str = ""

    @property
    def status_label(self) -> str:
        return STATUS_LABELS[self.action]

    @property
    def reason(self) -> str:
        return "; ".join((*self.problems, *self.notes))


@dataclass
class RosterPreview:
    lines: list[RosterLine] = field(default_factory=list)

    def _count(self, action: str) -> int:
        return sum(1 for line in self.lines if line.action == action)

    @property
    def create(self) -> int:
        return self._count(CREATE)

    @property
    def update(self) -> int:
        return self._count(UPDATE)

    @property
    def same(self) -> int:
        return self._count(SAME)

    @property
    def problems(self) -> int:
        return self._count(PROBLEM)

    @property
    def importable(self) -> int:
        return self.create + self.update

    @property
    def without_email(self) -> int:
        return sum(1 for line in self.lines if "Sem e-mail" in line.notes)

    def reportable(self) -> list[RosterLine]:
        return [line for line in self.lines if line.problems or line.notes]


@dataclass(frozen=True)
class RosterResult:
    created: int
    updated: int
    same: int
    problems: int
    lines: tuple[RosterLine, ...]


def safe_cell(value: object) -> str:
    """Neutraliza fórmula em planilha: o relatório volta ao Excel do escritório."""

    text = str(value or "")
    return f"'{text}" if text[:1] in {"=", "+", "-", "@", "\t", "\r"} else text


def template_csv() -> bytes:
    """Modelo só com cabeçalho: uma linha de exemplo seria importada por engano."""

    buffer = io.StringIO()
    csv.writer(buffer, delimiter=";", lineterminator="\r\n").writerow(TEMPLATE_HEADER)
    return buffer.getvalue().encode("utf-8-sig")


def error_report_csv(lines: Iterable[RosterLine]) -> bytes:
    buffer = io.StringIO()
    writer = csv.writer(buffer, delimiter=";", lineterminator="\r\n")
    writer.writerow(ERROR_REPORT_HEADER)
    for line in lines:
        writer.writerow(
            [
                line.number,
                safe_cell(line.name),
                safe_cell(line.cnpj),
                safe_cell(line.email),
                safe_cell(line.code),
                line.status_label,
                safe_cell(line.reason),
            ]
        )
    return buffer.getvalue().encode("utf-8-sig")


def _as_utf8(content: bytes) -> bytes:
    """O CSV do Excel brasileiro sai em Windows-1252; sem isso o acento derruba a leitura."""

    try:
        content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return content.decode("cp1252", errors="replace").encode("utf-8")
    return content


def _read_rows(filename: str, content: bytes) -> list[dict[str, str]]:
    lowered = filename.casefold()
    if lowered.endswith(".csv"):
        content = _as_utf8(content)
    rows = _tabular_rows(filename, content)
    if not rows:
        raise ImportValidationError("O arquivo não possui linhas para importar.")
    headers = set(rows[0])
    if not headers & set(NAME_COLUMNS) or not headers & set(CNPJ_COLUMNS):
        raise ImportValidationError("Faltam as colunas nome e cnpj na primeira linha.")
    return rows


def ensure_roster_source(organization: Organization) -> DataSource:
    source, _ = DataSource.objects.get_or_create(
        organization=organization,
        kind=DataSource.Kind.OTHER_MANUAL,
        defaults={"label": SOURCE_LABEL},
    )
    return source


def create_roster_batch(
    *,
    organization: Organization,
    upload: UploadedFile,
    actor: User,
    request: object = None,
) -> tuple[ImportBatch, bool]:
    """Guarda a planilha cifrada até a confirmação. A mesma planilha volta o mesmo lote."""

    filename = upload.name or ""
    if not filename.casefold().endswith((".csv", ".xlsx")):
        raise ImportValidationError("Envie um arquivo .csv ou .xlsx.")
    content = _read_upload(upload, limit=MAX_TABULAR_BYTES)
    rows = _read_rows(filename, content)
    source = ensure_roster_source(organization)
    digest = hashlib.sha256(content).hexdigest()
    existing = ImportBatch.objects.filter(
        organization=organization,
        data_source=source,
        kind=ImportBatch.Kind.COMPANIES,
        content_hash=digest,
    ).first()
    if existing is not None:
        return existing, False
    batch = ImportBatch.objects.create(
        organization=organization,
        data_source=source,
        kind=ImportBatch.Kind.COMPANIES,
        original_filename=filename[:255],
        content_hash=digest,
        mapping={"roster": True, "headers": list(rows[0])},
        encrypted_payload=json.dumps(rows, ensure_ascii=False),
        row_count=len(rows),
        created_by=actor,
    )
    record_event(
        action="hub.roster.preview_created",
        actor=actor,
        organization=organization,
        target=batch,
        request=request,
        metadata={"rows": len(rows)},
    )
    return batch, True


def batch_rows(batch: ImportBatch) -> list[dict[str, str]]:
    payload = json.loads(batch.encrypted_payload or "[]")
    return [
        {str(key): str(value) for key, value in row.items()}
        for row in payload
        if isinstance(row, dict)
    ]


def is_roster_batch(batch: ImportBatch) -> bool:
    return batch.kind == ImportBatch.Kind.COMPANIES and bool(batch.mapping.get("roster"))


def _valid_cnpj(raw: str) -> tuple[str, str]:
    """Devolve (cnpj normalizado, problema)."""

    if not raw:
        return "", "Informe o CNPJ"
    try:
        return normalize_cnpj(raw), ""
    except ValidationError as exc:
        message = " ".join(exc.messages)
        return "", "Dígitos do CNPJ não conferem" if "dígitos" in message else "CNPJ inválido"


def _valid_email(raw: str) -> bool:
    try:
        validate_email(raw)
    except ValidationError:
        return False
    return len(raw) <= 254


def _existing_by_cnpj(organization: Organization) -> dict[str, ClientCompany]:
    found: dict[str, ClientCompany] = {}
    for company in ClientCompany.objects.filter(organization=organization).order_by("created_at"):
        try:
            found.setdefault(normalize_cnpj(company.cnpj_masked), company)
        except ValidationError:
            continue
    return found


def analyse_roster(
    *,
    organization: Organization,
    rows: Iterable[Mapping[str, str]],
    data_source: DataSource | None = None,
    max_new: int | None = None,
    visible_ids: Collection[str] | None = None,
) -> RosterPreview:
    """Avalia cada linha contra a carteira atual sem gravar nada.

    `visible_ids`: as empresas que quem importa pode ver (acesso por empresa). `None` = o
    escritório inteiro. Um CNPJ que já existe no escritório mas fora dessa carteira vira problema
    sem dizer o nome da empresa e nunca é alterado: a planilha não é caminho para enxergar nem
    mexer no que o perfil do membro não alcança.
    """

    by_cnpj = _existing_by_cnpj(organization)
    by_code: dict[str, ClientCompany] = {}
    if data_source is not None:
        by_code = {
            company.external_key: company
            for company in ClientCompany.objects.filter(
                organization=organization, data_source=data_source, external_key__gt=""
            )
        }
    seen_cnpj: dict[str, int] = {}
    seen_code: dict[str, int] = {}
    new_so_far = 0
    # The plan counts CNPJ roots: a branch of a company already in the portfolio (or earlier in
    # the file) takes no room.
    roots_in_use = (
        set(
            ClientCompany.objects.filter(organization=organization, active=True)
            .exclude(commercial_root_cnpj="")
            .values_list("commercial_root_cnpj", flat=True)
        )
        if max_new is not None
        else set()
    )
    preview = RosterPreview()
    for number, row in enumerate(rows, 2):
        name = " ".join(_pick(dict(row), *NAME_COLUMNS).split())
        raw_cnpj = _pick(dict(row), *CNPJ_COLUMNS)
        email = _pick(dict(row), *EMAIL_COLUMNS).strip().lower()
        code = _pick(dict(row), *CODE_COLUMNS)[:160]
        cnpj, cnpj_problem = _valid_cnpj(raw_cnpj)
        problems: list[str] = []
        notes: list[str] = []
        if not name:
            problems.append("Informe o nome")
        elif len(name) > MAX_NAME:
            problems.append("Nome acima de 180 caracteres")
        if cnpj_problem:
            problems.append(cnpj_problem)
        elif cnpj in seen_cnpj:
            problems.append(f"CNPJ repetido na linha {seen_cnpj[cnpj]}")
        else:
            seen_cnpj[cnpj] = number
        if code and code in seen_code:
            problems.append(f"Código repetido na linha {seen_code[code]}")
        elif code:
            seen_code[code] = number
        if email and not _valid_email(email):
            notes.append("E-mail inválido, ignorado")
            email = ""
        existing = by_cnpj.get(cnpj) if cnpj and not cnpj_problem else None
        if existing is None and code and code in by_code and not problems:
            problems.append("Código já usado por outra empresa")
        if problems:
            preview.lines.append(
                RosterLine(
                    number=number,
                    name=name,
                    cnpj=cnpj or raw_cnpj,
                    email=email,
                    code=code,
                    action=PROBLEM,
                    problems=tuple(problems),
                    notes=tuple(notes),
                )
            )
            continue
        if existing is not None and visible_ids is not None and str(existing.pk) not in visible_ids:
            preview.lines.append(
                RosterLine(
                    number=number,
                    name=name,
                    cnpj=cnpj,
                    email=email,
                    code=code,
                    action=PROBLEM,
                    problems=("Empresa fora da sua carteira",),
                    notes=tuple(notes),
                )
            )
            continue
        if existing is not None:
            if not existing.active:
                notes.append("Empresa inativa")
            if email and email != existing.contact_email and existing.active:
                action = UPDATE
            else:
                action = SAME
                if not email and not existing.contact_email:
                    notes.append("Sem e-mail")
            preview.lines.append(
                RosterLine(
                    number=number,
                    name=existing.name,
                    cnpj=cnpj,
                    email=email,
                    code=code,
                    action=action,
                    notes=tuple(notes),
                    company_id=str(existing.pk),
                )
            )
            continue
        root = cnpj[:8]
        takes_room = root not in roots_in_use
        if max_new is not None and takes_room and new_so_far >= max_new:
            preview.lines.append(
                RosterLine(
                    number=number,
                    name=name,
                    cnpj=cnpj,
                    email=email,
                    code=code,
                    action=PROBLEM,
                    problems=("Limite de empresas do plano",),
                    notes=tuple(notes),
                )
            )
            continue
        if takes_room:
            new_so_far += 1
            roots_in_use.add(root)
        if not email:
            notes.append("Sem e-mail")
        preview.lines.append(
            RosterLine(
                number=number,
                name=name,
                cnpj=cnpj,
                email=email,
                code=code,
                action=CREATE,
                notes=tuple(notes),
            )
        )
    return preview


def _error_entries(lines: Iterable[RosterLine]) -> list[dict[str, Any]]:
    entries = [
        {"row": line.number, "message": line.reason or "Linha com problema."}
        for line in lines
        if line.action == PROBLEM
    ]
    return entries[:MAX_REPORT_ERRORS]


@transaction.atomic
def apply_roster(
    *,
    batch: ImportBatch,
    actor: User,
    membership: Membership | None = None,
    max_new: int | None = None,
    visible_ids: Collection[str] | None = None,
    request: object = None,
) -> RosterResult | None:
    """Grava o que a prévia aprovou. Devolve `None` se o lote já não está em prévia.

    `membership`: quem importa. Se o acesso dele é por empresa (`CompanyAccessGrant`), as empresas
    novas entram na carteira dele, como no cadastro manual.
    """

    batch = ImportBatch.objects.select_for_update().select_related("data_source").get(pk=batch.pk)
    if batch.status != ImportBatch.Status.PREVIEW or not is_roster_batch(batch):
        return None
    organization = batch.organization
    source = batch.data_source
    preview = analyse_roster(
        organization=organization,
        rows=batch_rows(batch),
        data_source=source,
        max_new=max_new,
        visible_ids=visible_ids,
    )
    grantee = (
        membership
        if membership is not None
        and CompanyAccessGrant.objects.filter(
            membership=membership, organization=organization, is_active=True
        ).exists()
        else None
    )
    created = updated = 0
    for line in preview.lines:
        if line.action == CREATE:
            company = ClientCompany.objects.create(
                organization=organization,
                data_source=source,
                name=line.name,
                cnpj_masked=line.cnpj,
                contact_email=line.email,
                external_key=line.code,
                active=True,
            )
            if grantee is not None:
                CompanyAccessGrant.objects.create(
                    organization=organization,
                    membership=grantee,
                    company=company,
                    modules=list(OFFERED_MODULE_CODES),
                    capabilities=["*"],
                )
            created += 1
        elif line.action == UPDATE:
            if visible_ids is not None and line.company_id not in visible_ids:
                continue  # never reached through `analyse_roster`; the write path checks again
            company = ClientCompany.objects.get(pk=line.company_id, organization=organization)
            company.contact_email = line.email
            company.save(update_fields=["contact_email", "updated_at"])
            updated += 1
    now = timezone.now()
    batch.status = ImportBatch.Status.COMPLETED
    batch.created_count = created
    batch.updated_count = updated
    batch.ignored_count = preview.problems + preview.same
    batch.errors = _error_entries(preview.lines)
    batch.completed_at = now
    batch.encrypted_payload = json.dumps(
        [
            {
                "linha": line.number,
                "nome": line.name,
                "cnpj": line.cnpj,
                "email": line.email,
                "codigo": line.code,
                "situacao": line.status_label,
                "motivo": line.reason,
            }
            for line in preview.reportable()
        ],
        ensure_ascii=False,
    )
    batch.save(
        update_fields=[
            "status",
            "created_count",
            "updated_count",
            "ignored_count",
            "errors",
            "completed_at",
            "encrypted_payload",
            "updated_at",
        ]
    )
    source.capabilities = sorted({*source.capabilities, "companies"})
    source.status = DataSource.Status.READY
    source.last_import_at = now
    source.last_error_code = ""
    source.last_error_message = ""
    source.save()
    record_event(
        action="hub.roster.imported",
        actor=actor,
        organization=organization,
        target=batch,
        request=request,
        metadata={
            "created": created,
            "updated": updated,
            "same": preview.same,
            "problems": preview.problems,
        },
    )
    return RosterResult(
        created=created,
        updated=updated,
        same=preview.same,
        problems=preview.problems,
        lines=tuple(preview.lines),
    )


def stored_report_lines(batch: ImportBatch) -> list[RosterLine]:
    """Linhas com problema ou aviso de um lote concluído, para o relatório de erros."""

    lines: list[RosterLine] = []
    for item in batch_rows(batch):
        status = item.get("situacao", "")
        action = next((key for key, label in STATUS_LABELS.items() if label == status), PROBLEM)
        reason = item.get("motivo", "")
        parts = tuple(part for part in reason.split("; ") if part)
        problems = parts if action == PROBLEM else ()
        notes = () if action == PROBLEM else parts
        number = item.get("linha", "0")
        lines.append(
            RosterLine(
                number=int(number) if number.isdigit() else 0,
                name=item.get("nome", ""),
                cnpj=item.get("cnpj", ""),
                email=item.get("email", ""),
                code=item.get("codigo", ""),
                action=action,
                problems=problems,
                notes=notes,
            )
        )
    return lines


def purge_roster_artifacts(*, now: datetime | None = None) -> dict[str, int]:
    """Prévia esquecida some em 7 dias; o relatório de ocorrências, em 30 (E4, retenção)."""

    now = now or timezone.now()
    roster_batches = ImportBatch.objects.filter(
        kind=ImportBatch.Kind.COMPANIES, mapping__roster=True
    )
    stale = roster_batches.filter(
        status=ImportBatch.Status.PREVIEW, created_at__lt=now - PREVIEW_RETENTION
    )
    discarded = stale.count()
    stale.delete()
    # The payload is encrypted, so "already empty" cannot be tested in SQL: the sweep is
    # idempotent and `reports_cleared` counts every finished batch past the retention.
    finished = roster_batches.filter(
        status=ImportBatch.Status.COMPLETED, completed_at__lt=now - REPORT_RETENTION
    )
    cleared = finished.update(encrypted_payload="")
    return {"previews_discarded": discarded, "reports_cleared": cleared}
