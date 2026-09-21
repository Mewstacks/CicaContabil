"""Normalized, idempotent mirror writes from trusted read-only Domínio adapters."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import TypedDict

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.hub.models import AccountingEntry, ClientCompany, DataSource, DominioBankEntry
from apps.intelligence.connectors import (
    MAX_BANK_ENTRY_ROWS,
    CatalogColumn,
    CatalogTable,
)
from apps.intelligence.models import (
    DataCatalogEntry,
    DominioCommunication,
    DominioSchemaObject,
    IntelligenceConnector,
)
from apps.organizations.models import Organization


@dataclass(frozen=True)
class SyncResult:
    created: int
    updated: int
    ignored: int
    deactivated: int


@dataclass(frozen=True)
class CommunicationSyncResult:
    created: int
    updated: int
    ignored: int


@dataclass(frozen=True)
class BankEntrySyncResult:
    created: int
    updated: int
    ignored: int
    may_be_truncated: bool = False


class NormalizedBankEntry(TypedDict):
    company_code: str
    occurred_on: date
    description: str
    amount_cents: int
    direction: str
    is_linked: bool


@dataclass(frozen=True)
class SchemaCatalogResult:
    created: int
    updated: int
    unchanged: int


def _schema_hash(columns: list[dict[str, object]]) -> str:
    payload = json.dumps(columns, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _suggest_schema_sensitivity(columns: list[dict[str, object]]) -> str:
    names = " ".join(str(column.get("name", "")).casefold() for column in columns)
    if any(
        word in names
        for word in ("senha", "password", "secret", "token", "cert", "pfx", "private_key")
    ):
        return DataCatalogEntry.Sensitivity.EXCLUDED
    if any(
        word in names
        for word in (
            "cpf",
            "cnpj",
            "email",
            "telefone",
            "celular",
            "endereco",
            "logradouro",
            "nascimento",
        )
    ):
        return DataCatalogEntry.Sensitivity.PERSONAL
    return DataCatalogEntry.Sensitivity.RESTRICTED


def _most_restrictive(left: str, right: str) -> str:
    rank: dict[str, int] = {
        DataCatalogEntry.Sensitivity.OPERATIONAL: 0,
        DataCatalogEntry.Sensitivity.RESTRICTED: 1,
        DataCatalogEntry.Sensitivity.PERSONAL: 2,
        DataCatalogEntry.Sensitivity.EXCLUDED: 3,
    }
    return left if rank.get(left, 2) >= rank.get(right, 2) else right


def record_schema_object(
    *,
    organization: Organization,
    table: CatalogTable,
    columns: Iterable[CatalogColumn],
) -> tuple[DominioSchemaObject, bool, bool]:
    """Persist only schema metadata; an altered structure must be reviewed again."""
    normalized_columns: list[dict[str, object]] = [
        {
            "name": column.name[:128],
            "type": column.type_name[:96],
            "ordinal": max(0, int(column.ordinal)),
            "nullable": column.nullable,
        }
        for column in columns
    ]
    structure_hash = _schema_hash(normalized_columns)
    suggested_sensitivity = _suggest_schema_sensitivity(normalized_columns)
    with transaction.atomic():
        schema_object, created = DominioSchemaObject.objects.select_for_update().get_or_create(
            organization=organization,
            schema_name=table.schema_name[:128],
            object_name=table.object_name[:128],
            object_kind=table.object_kind,
            defaults={
                "columns": normalized_columns,
                "structure_hash": structure_hash,
                "sensitivity": suggested_sensitivity,
            },
        )
        if created:
            return schema_object, True, False
        if schema_object.structure_hash == structure_hash:
            schema_object.save(update_fields=["last_discovered_at", "updated_at"])
            return schema_object, False, False
        schema_object.columns = normalized_columns
        schema_object.structure_hash = structure_hash
        schema_object.sensitivity = _most_restrictive(
            schema_object.sensitivity, suggested_sensitivity
        )
        schema_object.approved_for_package = False
        schema_object.save(
            update_fields=[
                "columns",
                "structure_hash",
                "sensitivity",
                "approved_for_package",
                "last_discovered_at",
                "updated_at",
            ]
        )
    return schema_object, False, True


def record_schema_snapshot(
    *,
    organization: Organization,
    objects: Iterable[tuple[CatalogTable, Iterable[CatalogColumn]]],
) -> SchemaCatalogResult:
    created = updated = unchanged = 0
    for table, columns in objects:
        _, was_created, was_updated = record_schema_object(
            organization=organization, table=table, columns=columns
        )
        if was_created:
            created += 1
        elif was_updated:
            updated += 1
        else:
            unchanged += 1
    return SchemaCatalogResult(created=created, updated=updated, unchanged=unchanged)


def _clean_text(value: object, limit: int) -> str:
    return str(value or "").strip()[:limit]


def sync_companies(
    *,
    organization: Organization,
    connector: IntelligenceConnector,
    rows: Iterable[Mapping[str, object]],
    actor: object = None,
    request: object = None,
    full_snapshot: bool = False,
) -> SyncResult:
    """Mirror operational company metadata from the authenticated Domínio agent."""
    if connector.organization_id != organization.id:
        raise ValueError("Conector não pertence ao escritório informado.")
    created = updated = ignored = deactivated = 0
    now = timezone.now()
    active_codes: set[str] = set()
    with transaction.atomic():
        data_source, _ = DataSource.objects.get_or_create(
            organization=organization,
            kind=DataSource.Kind.DOMINIO_LOCAL_AGENT,
            defaults={"label": "Domínio Local"},
        )
        for row in rows:
            code = _clean_text(row.get("codigo") or row.get("dominio_code"), 64)
            name = _clean_text(row.get("nome") or row.get("name"), 180)
            cnpj = _clean_text(row.get("cnpj_masked"), 18)
            if not code or not name:
                ignored += 1
                continue
            active_codes.add(code)
            company, was_created = ClientCompany.objects.get_or_create(
                organization=organization,
                dominio_code=code,
                defaults={
                    "name": name,
                    "cnpj_masked": cnpj,
                    "last_dominio_sync_at": now,
                    "data_source": data_source,
                    "external_key": code,
                    "source_updated_at": now,
                },
            )
            if was_created:
                created += 1
                continue
            changes: list[str] = []
            if company.name != name:
                company.name = name
                changes.append("name")
            if cnpj and company.cnpj_masked != cnpj:
                company.cnpj_masked = cnpj
                changes.append("cnpj_masked")
            if not company.active:
                company.active = True
                changes.append("active")
            company.last_dominio_sync_at = now
            company.data_source = data_source
            company.external_key = code
            company.source_updated_at = now
            changes.extend(
                [
                    "last_dominio_sync_at",
                    "data_source",
                    "external_key",
                    "source_updated_at",
                    "updated_at",
                ]
            )
            company.save(update_fields=changes)
            updated += 1
        if full_snapshot:
            stale_companies = ClientCompany.objects.filter(
                organization=organization, active=True, dominio_code__gt=""
            ).exclude(dominio_code__in=active_codes)
            deactivated = stale_companies.update(active=False, updated_at=now)
        connector.status = "healthy"
        connector.last_sync_at = now
        connector.last_error_code = ""
        connector.last_error_message = ""
        connector.last_error_at = None
        connector.save(
            update_fields=[
                "status",
                "last_sync_at",
                "last_error_code",
                "last_error_message",
                "last_error_at",
                "updated_at",
            ]
        )
        capabilities = set(data_source.capabilities)
        capabilities.add("companies")
        data_source.capabilities = sorted(capabilities)
        data_source.status = DataSource.Status.READY
        data_source.last_import_at = now
        data_source.source_snapshot_at = now
        data_source.last_error_code = ""
        data_source.last_error_message = ""
        data_source.save()
        record_event(
            action="intelligence.dominio.companies_synced",
            actor=actor,
            organization=organization,
            target=connector,
            request=request,
            metadata={
                "created": created,
                "updated": updated,
                "ignored": ignored,
                "deactivated": deactivated,
                "full_snapshot": full_snapshot,
                "mode": connector.mode,
            },
        )
    return SyncResult(created, updated, ignored, deactivated)


def _as_read_flag(value: object) -> bool:
    return str(value or "").strip().casefold() in {"1", "s", "sim", "true", "yes"}


def _as_date(value: object) -> date | None:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return datetime.strptime(str(value).strip()[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def _as_cents(value: object) -> int | None:
    try:
        amount = Decimal(str(value).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return int((amount * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def sync_bank_entries(
    *,
    organization: Organization,
    connector: IntelligenceConnector,
    rows: Iterable[Mapping[str, object]],
    actor: object = None,
    request: object = None,
) -> BankEntrySyncResult:
    """Mirror only verified bank-statement items, preserving Domínio linkage state."""
    if connector.organization_id != organization.id:
        raise ValueError("Conector não pertence ao escritório informado.")
    created = updated = ignored = 0
    now = timezone.now()
    normalized: dict[str, NormalizedBankEntry] = {}
    company_codes: set[str] = set()
    for row in rows:
        source_id = _clean_text(row.get("source_id"), 160)
        company_code = _clean_text(row.get("company_code"), 64)
        occurred_on = _as_date(row.get("occurred_on"))
        amount_cents = _as_cents(row.get("amount"))
        if not source_id or not company_code or occurred_on is None or amount_cents is None:
            ignored += 1
            continue
        company_codes.add(company_code)
        normalized[source_id] = {
            "company_code": company_code,
            "occurred_on": occurred_on,
            "description": _clean_text(row.get("description"), 500),
            "amount_cents": amount_cents,
            "direction": _clean_text(row.get("direction"), 8),
            "is_linked": _as_read_flag(row.get("is_linked")),
        }
    may_be_truncated = len(normalized) >= MAX_BANK_ENTRY_ROWS
    with transaction.atomic():
        data_source, _ = DataSource.objects.get_or_create(
            organization=organization,
            kind=DataSource.Kind.DOMINIO_LOCAL_AGENT,
            defaults={"label": "Domínio Local"},
        )
        companies_by_code = dict(
            ClientCompany.objects.filter(
                organization=organization, dominio_code__in=company_codes
            ).values_list("dominio_code", "id")
        )
        existing_by_source = {
            entry.source_id: entry
            for entry in DominioBankEntry.objects.filter(
                organization=organization, source_id__in=normalized
            )
        }
        to_create: list[DominioBankEntry] = []
        to_update: list[DominioBankEntry] = []
        tracked_fields = (
            "company_id",
            "occurred_on",
            "description",
            "amount_cents",
            "direction",
            "is_linked",
        )
        for source_id, values in normalized.items():
            defaults = {
                "company_id": companies_by_code.get(str(values["company_code"])),
                "occurred_on": values["occurred_on"],
                "description": values["description"],
                "amount_cents": values["amount_cents"],
                "direction": values["direction"],
                "is_linked": values["is_linked"],
            }
            entry = existing_by_source.get(source_id)
            if entry is None:
                to_create.append(
                    DominioBankEntry(organization=organization, source_id=source_id, **defaults)
                )
                continue
            if any(getattr(entry, field) != value for field, value in defaults.items()):
                for field, value in defaults.items():
                    setattr(entry, field, value)
                entry.updated_at = now
                to_update.append(entry)
        DominioBankEntry.objects.bulk_create(to_create, batch_size=500)
        if to_update:
            DominioBankEntry.objects.bulk_update(
                to_update, [*tracked_fields, "updated_at"], batch_size=500
            )
        for source_id, values in normalized.items():
            AccountingEntry.objects.update_or_create(
                data_source=data_source,
                external_key=source_id,
                defaults={
                    "organization": organization,
                    "company_id": companies_by_code.get(str(values["company_code"])),
                    "occurred_on": values["occurred_on"],
                    "description": values["description"],
                    "amount_cents": values["amount_cents"],
                    "direction": values["direction"],
                    "is_linked": values["is_linked"],
                    "source_updated_at": now,
                },
            )
        created = len(to_create)
        updated = len(to_update)
        connector.status = "healthy"
        connector.last_sync_at = now
        connector.last_error_code = ""
        connector.last_error_message = ""
        connector.last_error_at = None
        connector.save(
            update_fields=[
                "status",
                "last_sync_at",
                "last_error_code",
                "last_error_message",
                "last_error_at",
                "updated_at",
            ]
        )
        capabilities = set(data_source.capabilities)
        capabilities.add("accounting_entries")
        data_source.capabilities = sorted(capabilities)
        data_source.status = DataSource.Status.READY
        data_source.last_import_at = now
        data_source.source_snapshot_at = now
        data_source.save()
        record_event(
            action="intelligence.dominio.bank_entries_synced",
            actor=actor,
            organization=organization,
            target=connector,
            request=request,
            metadata={
                "created": created,
                "updated": updated,
                "ignored": ignored,
                "may_be_truncated": may_be_truncated,
            },
        )
    from apps.hub.reconciliation import rebuild_reconciliation_matches

    rebuild_reconciliation_matches(organization=organization)
    return BankEntrySyncResult(
        created,
        updated,
        ignored,
        may_be_truncated=may_be_truncated,
    )


def sync_communications(
    *,
    organization: Organization,
    connector: IntelligenceConnector,
    rows: Iterable[Mapping[str, object]],
    actor: object = None,
    request: object = None,
) -> CommunicationSyncResult:
    """Mirror the allowlisted notification projection; personal source fields never enter it."""
    if connector.organization_id != organization.id:
        raise ValueError("Conector não pertence ao escritório informado.")
    created = updated = ignored = 0
    now = timezone.now()
    with transaction.atomic():
        for row in rows:
            source_id = _clean_text(row.get("source_id"), 64)
            if not source_id:
                ignored += 1
                continue
            company_code = _clean_text(row.get("company_code"), 64)
            company = (
                ClientCompany.objects.filter(
                    organization=organization, dominio_code=company_code
                ).first()
                if company_code
                else None
            )
            defaults = {
                "connector": connector,
                "company": company,
                "subject": _clean_text(row.get("subject"), 500),
                "type_code": _clean_text(row.get("type_code"), 32),
                "status_code": _clean_text(row.get("status_code"), 32),
                "is_read": _as_read_flag(row.get("is_read")),
            }
            communication, was_created = DominioCommunication.objects.get_or_create(
                organization=organization,
                source_id=source_id,
                defaults=defaults,
            )
            if was_created:
                created += 1
                continue
            changed = [
                field for field, value in defaults.items() if getattr(communication, field) != value
            ]
            if changed:
                for field in changed:
                    setattr(communication, field, defaults[field])
                communication.save(update_fields=[*changed, "source_captured_at", "updated_at"])
                updated += 1
        connector.status = "healthy"
        connector.last_sync_at = now
        connector.last_error_code = ""
        connector.last_error_message = ""
        connector.last_error_at = None
        connector.save(
            update_fields=[
                "status",
                "last_sync_at",
                "last_error_code",
                "last_error_message",
                "last_error_at",
                "updated_at",
            ]
        )
        record_event(
            action="intelligence.dominio.communications_synced",
            actor=actor,
            organization=organization,
            target=connector,
            request=request,
            metadata={
                "created": created,
                "updated": updated,
                "ignored": ignored,
                "mode": connector.mode,
            },
        )
    return CommunicationSyncResult(created, updated, ignored)
