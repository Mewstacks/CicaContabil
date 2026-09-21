from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import re
import zipfile
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import cast

from defusedxml import ElementTree  # type: ignore[import-untyped]
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import (
    AccountingEntry,
    ClientCompany,
    DataSource,
    FiscalGuide,
    ImportBatch,
)
from apps.hub.reconciliation import import_ofx, rebuild_reconciliation_matches
from apps.hub.services import create_document_and_artifact
from apps.organizations.models import Organization

MAX_TABULAR_BYTES = 10 * 1024 * 1024
MAX_BACKUP_BYTES = 2 * 1024 * 1024 * 1024
MAX_ROWS = 10_000


class ImportValidationError(ValueError):
    pass


def _read_upload(upload: UploadedFile, *, limit: int) -> bytes:
    if upload.size and upload.size > limit:
        raise ImportValidationError("O arquivo excede o limite permitido para este tipo.")
    content = upload.read(limit + 1)
    if len(content) > limit:
        raise ImportValidationError("O arquivo excede o limite permitido para este tipo.")
    if not content:
        raise ImportValidationError("O arquivo está vazio.")
    return cast(bytes, content)


def _normalize_header(value: str) -> str:
    value = value.strip().casefold()
    return re.sub(r"[^a-z0-9]+", "_", value).strip("_")


def _csv_rows(content: bytes) -> list[dict[str, str]]:
    text = content.decode("utf-8-sig", errors="strict")
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
        dialect.delimiter = ";"
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    if not reader.fieldnames:
        raise ImportValidationError("O arquivo precisa ter uma linha de cabeçalho.")
    rows: list[dict[str, str]] = []
    for raw in reader:
        if len(rows) >= MAX_ROWS:
            raise ImportValidationError("O arquivo excede o limite de 10.000 linhas.")
        row = {
            _normalize_header(key): str(value or "").strip() for key, value in raw.items() if key
        }
        if any(row.values()):
            rows.append(row)
    return rows


def _xlsx_rows(content: bytes) -> list[dict[str, str]]:
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
        shared: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.itertext()) for node in root]
        workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
        relations = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        relation_map = {item.attrib.get("Id"): item.attrib.get("Target") for item in relations}
        first_sheet = next(node for node in workbook.iter() if node.tag.endswith("sheet"))
        relation_id = next(
            value for key, value in first_sheet.attrib.items() if key.endswith("}id")
        )
        target = relation_map[relation_id]
        sheet_path = "xl/" + str(target).lstrip("/").removeprefix("xl/")
        sheet = ElementTree.fromstring(archive.read(sheet_path))
    except (KeyError, StopIteration, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        raise ImportValidationError("A planilha XLSX não pôde ser lida.") from exc
    matrix: list[list[str]] = []
    for row_node in (node for node in sheet.iter() if node.tag.endswith("}row")):
        cells: dict[int, str] = {}
        for cell in (node for node in row_node if node.tag.endswith("}c")):
            reference = cell.attrib.get("r", "A1")
            letters = re.match(r"[A-Z]+", reference)
            if letters is None:
                continue
            column = 0
            for character in letters.group(0):
                column = column * 26 + ord(character) - 64
            value_node = next((node for node in cell if node.tag.endswith("}v")), None)
            value = value_node.text if value_node is not None and value_node.text else ""
            if cell.attrib.get("t") == "s" and value:
                try:
                    value = shared[int(value)]
                except (IndexError, ValueError):
                    value = ""
            elif cell.attrib.get("t") == "inlineStr":
                value = "".join(cell.itertext())
            cells[column - 1] = value.strip()
        if cells:
            width = max(cells) + 1
            matrix.append([cells.get(index, "") for index in range(width)])
        if len(matrix) > MAX_ROWS + 1:
            raise ImportValidationError("A planilha excede o limite de 10.000 linhas.")
    if not matrix:
        raise ImportValidationError("A planilha está vazia.")
    headers = [_normalize_header(item) for item in matrix[0]]
    return [
        {
            header: row[index].strip() if index < len(row) else ""
            for index, header in enumerate(headers)
            if header
        }
        for row in matrix[1:]
        if any(value.strip() for value in row)
    ]


def _tabular_rows(filename: str, content: bytes) -> list[dict[str, str]]:
    return _xlsx_rows(content) if filename.casefold().endswith(".xlsx") else _csv_rows(content)


def _sha256_upload(upload: UploadedFile) -> str:
    digest = hashlib.sha256()
    for chunk in upload.chunks():
        digest.update(chunk)
    upload.seek(0)
    return digest.hexdigest()


def create_import_preview(
    *,
    organization: Organization,
    data_source: DataSource,
    kind: str,
    upload: UploadedFile,
    actor: User,
    company: ClientCompany | None = None,
    source_snapshot_at: datetime | None = None,
    backup_key: str = "",
    request: object = None,
) -> tuple[ImportBatch, bool]:
    if data_source.organization_id != organization.id:
        raise ImportValidationError("A fonte não pertence a este escritório.")
    filename = upload.name
    if not filename:
        raise ImportValidationError("O arquivo não possui nome.")
    digest = _sha256_upload(upload)
    existing = ImportBatch.objects.filter(
        organization=organization, data_source=data_source, kind=kind, content_hash=digest
    ).first()
    if existing is not None:
        if (
            kind == ImportBatch.Kind.DOMINIO_BACKUP
            and existing.status == ImportBatch.Status.FAILED
            and existing.source_file
        ):
            existing.status = ImportBatch.Status.PREVIEW
            existing.backup_key = backup_key
            existing.source_snapshot_at = source_snapshot_at
            existing.errors = []
            existing.completed_at = None
            existing.save(
                update_fields=[
                    "status",
                    "backup_key",
                    "source_snapshot_at",
                    "errors",
                    "completed_at",
                    "updated_at",
                ]
            )
        return existing, False
    mapping: dict[str, object] = {"company_id": str(company.id) if company else ""}
    payload = ""
    row_count = 0
    batch = ImportBatch(
        organization=organization,
        data_source=data_source,
        kind=kind,
        original_filename=filename[:255],
        content_hash=digest,
        source_snapshot_at=source_snapshot_at,
        backup_key=backup_key,
        created_by=actor,
    )
    if kind == ImportBatch.Kind.DOMINIO_BACKUP:
        if upload.size and upload.size > MAX_BACKUP_BYTES:
            raise ImportValidationError("O backup excede o limite de 2 GB.")
        signature = upload.read(4)
        upload.seek(0)
        if signature[:2] != b"PK":
            raise ImportValidationError(
                "O .dom não parece ser um backup compactado completo. Baixe novamente no Onvio."
            )
        batch.status = ImportBatch.Status.PREVIEW
        batch.mapping = {"bridge_required": True, "full_backup": True}
        batch.row_count = 1
        batch.save()
        batch.source_file.save(filename, upload, save=True)
    else:
        content = _read_upload(upload, limit=MAX_TABULAR_BYTES)
        if kind in {
            ImportBatch.Kind.COMPANIES,
            ImportBatch.Kind.OBLIGATIONS,
            ImportBatch.Kind.ACCOUNTING,
        }:
            rows = _tabular_rows(filename, content)
            if not rows:
                raise ImportValidationError("O arquivo não possui linhas para importar.")
            payload = json.dumps(rows, ensure_ascii=False)
            row_count = len(rows)
            mapping["headers"] = list(rows[0])
        else:
            payload = base64.b64encode(content).decode("ascii")
            row_count = 1
        batch.mapping = mapping
        batch.encrypted_payload = payload
        batch.row_count = row_count
        batch.save()
    record_event(
        action="hub.import.preview_created",
        actor=actor,
        organization=organization,
        target=batch,
        request=request,
        metadata={"kind": kind, "rows": batch.row_count},
    )
    return batch, True


def _pick(row: dict[str, str], *names: str) -> str:
    return next((row.get(name, "").strip() for name in names if row.get(name, "").strip()), "")


def _company_for_row(
    organization: Organization, data_source: DataSource, row: dict[str, str]
) -> ClientCompany | None:
    external = _pick(row, "codigo", "codigo_empresa", "external_key")
    cnpj = re.sub(r"\D", "", _pick(row, "cnpj", "cnpj_empresa"))
    query = ClientCompany.objects.filter(organization=organization)
    if external:
        found = query.filter(data_source=data_source, external_key=external).first()
        if found:
            return found
    if len(cnpj) == 14:
        matches = [
            company for company in query if re.sub(r"\D", "", company.cnpj_masked) == cnpj
        ]
        same_source = next(
            (company for company in matches if company.data_source_id == data_source.id), None
        )
        if same_source:
            return same_source
        if matches:
            raise ValueError(
                "O CNPJ já existe em outra fonte. Confirme o vínculo manualmente na empresa."
            )
    return None


def _cents(value: str) -> int:
    normalized = value.strip().replace("R$", "").replace(" ", "")
    if "," in normalized:
        normalized = normalized.replace(".", "").replace(",", ".")
    try:
        return int((Decimal(normalized) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except InvalidOperation as exc:
        raise ValueError from exc


@transaction.atomic
def confirm_import(*, batch: ImportBatch, actor: User, request: object = None) -> ImportBatch:
    batch = ImportBatch.objects.select_for_update().select_related("data_source").get(id=batch.id)
    if batch.status != ImportBatch.Status.PREVIEW:
        return batch
    if batch.kind == ImportBatch.Kind.DOMINIO_BACKUP:
        batch.status = ImportBatch.Status.QUEUED
        batch.data_source.status = DataSource.Status.PROCESSING
        batch.data_source.save(update_fields=["status", "updated_at"])
        batch.save(update_fields=["status", "updated_at"])
        return batch
    errors: list[dict[str, object]] = []
    created = updated = ignored = 0
    company_id = str(batch.mapping.get("company_id", ""))
    company = ClientCompany.objects.filter(id=company_id, organization=batch.organization).first()
    if batch.kind in {
        ImportBatch.Kind.COMPANIES,
        ImportBatch.Kind.OBLIGATIONS,
        ImportBatch.Kind.ACCOUNTING,
    }:
        rows = json.loads(batch.encrypted_payload)
    else:
        content = base64.b64decode(batch.encrypted_payload)
        rows = []
    for number, row in enumerate(rows, 2):
        try:
            if batch.kind == ImportBatch.Kind.COMPANIES:
                name = _pick(row, "nome", "razao_social", "empresa")
                external = _pick(row, "codigo", "codigo_empresa", "external_key")
                cnpj = re.sub(r"\D", "", _pick(row, "cnpj", "cnpj_empresa"))
                if not name or (cnpj and len(cnpj) != 14):
                    raise ValueError("Informe nome e um CNPJ válido quando presente.")
                defaults = {
                    "name": name[:180],
                    "cnpj_masked": cnpj if cnpj else "",
                    "active": True,
                    "source_updated_at": batch.source_snapshot_at,
                }
                if cnpj and any(
                    re.sub(r"\D", "", existing.cnpj_masked) == cnpj
                    for existing in ClientCompany.objects.filter(organization=batch.organization)
                    .exclude(data_source=batch.data_source)
                    .iterator()
                ):
                    raise ValueError(
                        "O CNPJ já existe em outra fonte; nenhum registro foi mesclado."
                    )
                if external:
                    _, was_created = ClientCompany.objects.update_or_create(
                        data_source=batch.data_source,
                        external_key=external[:160],
                        defaults={"organization": batch.organization, **defaults},
                    )
                else:
                    ClientCompany.objects.create(
                        organization=batch.organization, data_source=batch.data_source, **defaults
                    )
                    was_created = True
                created += int(was_created)
                updated += int(not was_created)
            elif batch.kind == ImportBatch.Kind.OBLIGATIONS:
                row_company = _company_for_row(batch.organization, batch.data_source, row)
                reference = _pick(row, "referencia", "reference")
                kind = _pick(row, "tipo", "kind").casefold()
                aliases = {
                    "dctfweb": FiscalGuide.Kind.DCTFWEB,
                    "das": FiscalGuide.Kind.DAS,
                    "mei": FiscalGuide.Kind.MEI,
                    "das_mei": FiscalGuide.Kind.MEI,
                }
                if row_company is None or not reference or kind not in aliases:
                    raise ValueError("Empresa, referência ou tipo de guia inválido.")
                due_on = datetime.strptime(_pick(row, "vencimento", "due_on"), "%Y-%m-%d").date()
                defaults = {
                    "kind": aliases[kind],
                    "competence": _pick(row, "competencia", "competence"),
                    "due_on": due_on,
                    "amount_cents": _cents(_pick(row, "valor", "amount")),
                    "integra_service_key": {
                        FiscalGuide.Kind.DCTFWEB: "dctfweb.guia",
                        FiscalGuide.Kind.DAS: "pgdasd.das",
                        FiscalGuide.Kind.MEI: "pgmei.das",
                    }[aliases[kind]],
                    "data_source": batch.data_source,
                    "source_batch": batch,
                    "external_key": reference[:160],
                    "source_updated_at": batch.source_snapshot_at,
                }
                _, was_created = FiscalGuide.objects.update_or_create(
                    organization=batch.organization,
                    company=row_company,
                    reference=reference[:120],
                    defaults=defaults,
                )
                created += int(was_created)
                updated += int(not was_created)
            elif batch.kind == ImportBatch.Kind.ACCOUNTING:
                row_company = _company_for_row(batch.organization, batch.data_source, row)
                external = _pick(row, "id", "codigo", "external_key")
                if row_company is None or not external:
                    raise ValueError("Informe a empresa e um identificador externo.")
                defaults = {
                    "organization": batch.organization,
                    "source_batch": batch,
                    "company": row_company,
                    "occurred_on": datetime.strptime(
                        _pick(row, "data", "occurred_on"), "%Y-%m-%d"
                    ).date(),
                    "description": _pick(row, "descricao", "historico", "description")[:500],
                    "amount_cents": abs(_cents(_pick(row, "valor", "amount"))),
                    "direction": _pick(row, "natureza", "direction")[:8],
                    "source_updated_at": batch.source_snapshot_at,
                }
                _, was_created = AccountingEntry.objects.update_or_create(
                    data_source=batch.data_source, external_key=external[:160], defaults=defaults
                )
                created += int(was_created)
                updated += int(not was_created)
        except (ValueError, TypeError) as exc:
            ignored += 1
            if len(errors) < 200:
                errors.append({"row": number, "message": str(exc) or "Linha inválida."})
    if batch.kind == ImportBatch.Kind.FISCAL_XML:
        assert company is not None
        text = content.decode("utf-8", errors="strict")
        root = ElementTree.fromstring(text)
        normalized = {"document_type": root.tag.split("}")[-1], "source": "manual_xml"}
        _, artifact, review = create_document_and_artifact(
            company=company,
            original_xml=text,
            normalized_data=normalized,
            actor=actor,
            request=request,
        )
        created = int(artifact is not None or review is not None)
        ignored = int(not created)
    elif batch.kind == ImportBatch.Kind.BANK_OFX:
        assert company is not None
        statement, was_created = import_ofx(
            organization=batch.organization,
            company=company,
            filename=batch.original_filename,
            content=content,
            actor=actor,
            request=request,
        )
        created = statement.transaction_count if was_created else 0
        ignored = 0 if was_created else 1
    if batch.kind == ImportBatch.Kind.ACCOUNTING:
        rebuild_reconciliation_matches(organization=batch.organization)
    batch.status = ImportBatch.Status.COMPLETED if not errors else ImportBatch.Status.FAILED
    batch.created_count = created
    batch.updated_count = updated
    batch.ignored_count = ignored
    batch.errors = errors
    batch.completed_at = timezone.now()
    batch.encrypted_payload = ""
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
    capabilities = set(batch.data_source.capabilities)
    capability_by_kind: dict[str, str] = {
        ImportBatch.Kind.COMPANIES: "companies",
        ImportBatch.Kind.OBLIGATIONS: "obligations",
        ImportBatch.Kind.ACCOUNTING: "accounting_entries",
        ImportBatch.Kind.FISCAL_XML: "fiscal_documents",
        ImportBatch.Kind.BANK_OFX: "bank_statements",
    }
    capabilities.add(capability_by_kind[batch.kind])
    batch.data_source.capabilities = sorted(capabilities)
    batch.data_source.status = (
        DataSource.Status.READY if not errors else DataSource.Status.ATTENTION
    )
    batch.data_source.last_import_at = timezone.now()
    batch.data_source.source_snapshot_at = batch.source_snapshot_at
    batch.data_source.last_error_code = "row_validation" if errors else ""
    batch.data_source.last_error_message = (
        f"{len(errors)} linha(s) precisam de correção." if errors else ""
    )
    batch.data_source.save()
    record_event(
        action="hub.import.completed",
        actor=actor,
        organization=batch.organization,
        target=batch,
        request=request,
        metadata={"created": created, "updated": updated, "ignored": ignored},
    )
    return batch
