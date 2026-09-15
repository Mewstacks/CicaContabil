"""Normalization boundary for manually uploaded Domínio Web backup snapshots."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from datetime import date
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date

from apps.audit.services import record_event
from apps.hub.models import AccountingEntry, ClientCompany, DataSource, FiscalGuide, ImportBatch
from apps.intelligence.models import EdgeAgent


def _text(row: Mapping[str, object], name: str, limit: int) -> str:
    return str(row.get(name, "") or "").strip()[:limit]


def _date(row: Mapping[str, object], name: str) -> date:
    parsed = parse_date(_text(row, name, 10))
    if parsed is None:
        raise ValueError(f"Data inválida no campo {name}.")
    return parsed


def _cents(value: object) -> int:
    try:
        return int((Decimal(str(value)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Valor monetário inválido.") from exc


def _company(batch: ImportBatch, external_key: str) -> ClientCompany:
    company = ClientCompany.objects.filter(
        organization=batch.organization,
        data_source=batch.data_source,
        external_key=external_key,
    ).first()
    if company is None:
        raise ValueError(f"Empresa {external_key} ainda não foi recebida neste backup.")
    return company


@transaction.atomic
def apply_backup_page(
    *,
    batch: ImportBatch,
    capability: str,
    rows: Iterable[Mapping[str, object]],
    agent: EdgeAgent,
    request: object = None,
) -> dict[str, int]:
    """Apply one idempotent page produced by the local, allowlisted extractor."""

    batch = ImportBatch.objects.select_for_update().select_related("data_source").get(id=batch.id)
    created = updated = ignored = 0
    errors = list(batch.errors)
    for index, row in enumerate(rows, 1):
        try:
            if capability == "companies":
                external_key = _text(row, "external_key", 160)
                name = _text(row, "name", 180)
                if not external_key or not name:
                    raise ValueError("Empresa sem código ou nome.")
                cnpj = _text(row, "cnpj", 18)
                existing_key = ClientCompany.objects.filter(
                    data_source=batch.data_source, external_key=external_key
                ).exists()
                if cnpj and not existing_key and any(
                    item.cnpj_masked == cnpj
                    for item in ClientCompany.objects.filter(organization=batch.organization)
                    .exclude(data_source=batch.data_source)
                    .iterator()
                ):
                    raise ValueError(
                        "O CNPJ já existe em outra fonte; nenhum registro foi mesclado."
                    )
                _, was_created = ClientCompany.objects.update_or_create(
                    data_source=batch.data_source,
                    external_key=external_key,
                    defaults={
                        "organization": batch.organization,
                        "name": name,
                        "cnpj_masked": cnpj,
                        "dominio_code": external_key[:64],
                        "active": bool(row.get("active", True)),
                        "source_updated_at": batch.source_snapshot_at,
                        "last_dominio_sync_at": timezone.now(),
                    },
                )
            elif capability == "accounting_entries":
                external_key = _text(row, "external_key", 160)
                company = _company(batch, _text(row, "company_key", 160))
                if not external_key:
                    raise ValueError("Lançamento sem identificador.")
                _, was_created = AccountingEntry.objects.update_or_create(
                    data_source=batch.data_source,
                    external_key=external_key,
                    defaults={
                        "organization": batch.organization,
                        "source_batch": batch,
                        "company": company,
                        "occurred_on": _date(row, "occurred_on"),
                        "description": _text(row, "description", 500),
                        "amount_cents": abs(_cents(row.get("amount", 0))),
                        "direction": _text(row, "direction", 8),
                        "is_linked": bool(row.get("is_linked", False)),
                        "source_updated_at": batch.source_snapshot_at,
                    },
                )
            else:
                external_key = _text(row, "external_key", 160)
                company = _company(batch, _text(row, "company_key", 160))
                kind = _text(row, "kind", 16).casefold()
                if kind not in FiscalGuide.Kind.values or not external_key:
                    raise ValueError("Obrigação sem tipo ou identificador válido.")
                _, was_created = FiscalGuide.objects.update_or_create(
                    organization=batch.organization,
                    company=company,
                    reference=external_key[:120],
                    defaults={
                        "kind": kind,
                        "competence": _text(row, "competence", 7),
                        "due_on": _date(row, "due_on"),
                        "amount_cents": abs(_cents(row.get("amount", 0))),
                        "integra_service_key": _text(row, "service_key", 100),
                        "data_source": batch.data_source,
                        "source_batch": batch,
                        "external_key": external_key,
                        "source_updated_at": batch.source_snapshot_at,
                    },
                )
            created += int(was_created)
            updated += int(not was_created)
        except (TypeError, ValueError) as exc:
            ignored += 1
            if len(errors) < 200:
                errors.append({"capability": capability, "row": index, "message": str(exc)})
    batch.created_count += created
    batch.updated_count += updated
    batch.ignored_count += ignored
    batch.errors = errors
    batch.mapping = {
        **batch.mapping,
        "received_capabilities": sorted(
            set(batch.mapping.get("received_capabilities", [])) | {capability}
        ),
    }
    batch.save(
        update_fields=[
            "created_count",
            "updated_count",
            "ignored_count",
            "errors",
            "mapping",
            "updated_at",
        ]
    )
    return {"created": created, "updated": updated, "ignored": ignored}


@transaction.atomic
def complete_backup(*, batch: ImportBatch, agent: EdgeAgent, request: object = None) -> ImportBatch:
    batch = ImportBatch.objects.select_for_update().select_related("data_source").get(id=batch.id)
    capabilities = set(batch.data_source.capabilities)
    capabilities.update(batch.mapping.get("received_capabilities", []))
    batch.status = ImportBatch.Status.COMPLETED
    batch.completed_at = timezone.now()
    batch.backup_key = ""
    batch.data_source.capabilities = sorted(capabilities)
    batch.data_source.status = (
        DataSource.Status.READY if not batch.errors else DataSource.Status.ATTENTION
    )
    batch.data_source.last_import_at = timezone.now()
    batch.data_source.source_snapshot_at = batch.source_snapshot_at
    batch.data_source.last_error_code = "row_validation" if batch.errors else ""
    batch.data_source.last_error_message = (
        f"{len(batch.errors)} registro(s) não puderam ser importados." if batch.errors else ""
    )
    batch.data_source.save()
    file_to_delete = batch.source_file
    batch.source_file = ""
    batch.save(update_fields=["status", "completed_at", "backup_key", "source_file", "updated_at"])
    if file_to_delete:
        file_to_delete.delete(save=False)
    record_event(
        action="hub.dominio_web_backup.completed",
        organization=batch.organization,
        target=batch,
        request=request,
        metadata={"agent_id": str(agent.id), "errors": len(batch.errors)},
    )
    return batch


@transaction.atomic
def fail_backup(
    *,
    batch: ImportBatch,
    code: str,
    detail: str,
    agent: EdgeAgent,
    request: object = None,
) -> ImportBatch:
    batch = ImportBatch.objects.select_for_update().select_related("data_source").get(id=batch.id)
    safe_detail = detail.replace("\r", " ").replace("\n", " ")[:240]
    batch.status = ImportBatch.Status.FAILED
    batch.errors = [*batch.errors[:199], {"code": code[:80], "message": safe_detail}]
    batch.completed_at = timezone.now()
    batch.save(update_fields=["status", "errors", "completed_at", "updated_at"])
    batch.data_source.status = DataSource.Status.ATTENTION
    batch.data_source.last_error_code = code[:80]
    batch.data_source.last_error_message = safe_detail
    batch.data_source.save()
    record_event(
        action="hub.dominio_web_backup.failed",
        organization=batch.organization,
        target=batch,
        request=request,
        metadata={"agent_id": str(agent.id), "code": code[:80]},
    )
    return batch
