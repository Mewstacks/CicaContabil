"""Normalized, idempotent mirror writes from trusted read-only Domínio adapters."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from django.db import transaction
from django.utils import timezone

from apps.audit.services import record_event
from apps.hub.models import ClientCompany
from apps.intelligence.connectors import CatalogColumn, CatalogTable
from apps.intelligence.models import DataCatalogEntry, DominioSchemaObject, IntelligenceConnector
from apps.organizations.models import Organization


@dataclass(frozen=True)
class SyncResult:
    created: int
    updated: int
    ignored: int


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
) -> SyncResult:
    """Mirror only minimum company metadata; raw taxpayer IDs must already be masked."""
    if connector.organization_id != organization.id:
        raise ValueError("Conector não pertence ao escritório informado.")
    created = updated = ignored = 0
    now = timezone.now()
    with transaction.atomic():
        for row in rows:
            code = _clean_text(row.get("codigo") or row.get("dominio_code"), 64)
            name = _clean_text(row.get("nome") or row.get("name"), 180)
            masked = _clean_text(row.get("cnpj_masked"), 18)
            if not code or not name:
                ignored += 1
                continue
            company, was_created = ClientCompany.objects.get_or_create(
                organization=organization,
                dominio_code=code,
                defaults={"name": name, "cnpj_masked": masked, "last_dominio_sync_at": now},
            )
            if was_created:
                created += 1
                continue
            changes: list[str] = []
            if company.name != name:
                company.name = name
                changes.append("name")
            if masked and company.cnpj_masked != masked:
                company.cnpj_masked = masked
                changes.append("cnpj_masked")
            company.last_dominio_sync_at = now
            changes.extend(["last_dominio_sync_at", "updated_at"])
            company.save(update_fields=changes)
            updated += 1
        connector.status = "healthy"
        connector.last_sync_at = now
        connector.save(update_fields=["status", "last_sync_at", "updated_at"])
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
                "mode": connector.mode,
            },
        )
    return SyncResult(created, updated, ignored)
