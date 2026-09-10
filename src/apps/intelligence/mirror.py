"""Private, governed operational mirror for Domínio data.

The mirror is the only database read by a chat request.  A trusted synchronizer
(direct ODBC service or edge agent) writes reviewed semantic-package rows here;
the model never invokes an adapter or receives the stored payload.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.hub.models import ClientCompany
from apps.intelligence.models import MirrorRecord, SemanticPackage
from apps.intelligence.package_governance import semantic_package_ready
from apps.organizations.models import Organization

MAX_SYNC_ROWS = 1_000
MAX_CARD_RECORDS = 4
MAX_CARD_FIELDS = 5


@dataclass(frozen=True)
class MirrorSyncResult:
    created: int
    updated: int
    ignored: int


@dataclass(frozen=True)
class MirrorCard:
    label: str
    reference: str
    detail: str

    def as_dict(self) -> dict[str, str]:
        return {"label": self.label, "reference": self.reference, "detail": self.detail}


def _canonical_payload(row: dict[str, Any]) -> tuple[str, str]:
    serialized = json.dumps(
        row, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":")
    )
    return serialized, hashlib.sha256(serialized.encode()).hexdigest()


def _source_timestamp(value: object) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        parsed = parse_datetime(value)
        if parsed is not None:
            return parsed
    return None


def sync_mirror_rows(
    *, organization: Organization, package: SemanticPackage, rows: list[object]
) -> MirrorSyncResult:
    """Persist rows supplied by a trusted package synchronizer.

    The caller deliberately supplies row dictionaries, not SQL.  Validation is
    strict enough to make this safe for a future ODBC worker and signed edge
    agent, while retaining no connection or credential in this layer.
    """
    if package.organization_id != organization.id:
        raise ValueError("Pacote semântico fora do escritório.")
    if not semantic_package_ready(package):
        raise ValueError("Pacote semântico não está habilitado.")
    if len(rows) > min(package.max_rows, MAX_SYNC_ROWS):
        raise ValueError("Quantidade de registros excede o limite do pacote.")

    created = updated = ignored = 0
    company_codes = {
        str(row.get(package.company_key, "")).strip()
        for row in rows
        if isinstance(row, dict) and str(row.get(package.company_key, "")).strip()
    }
    companies = {
        company.dominio_code: company
        for company in ClientCompany.objects.filter(
            organization=organization, dominio_code__in=company_codes
        )
    }

    with transaction.atomic():
        for row in rows:
            if not isinstance(row, dict):
                ignored += 1
                continue
            external_key = str(row.get(package.primary_key, "")).strip()
            if not external_key or len(external_key) > 160:
                ignored += 1
                continue
            serialized, payload_hash = _canonical_payload(row)
            company_code = str(row.get(package.company_key, "")).strip()
            company = companies.get(company_code)
            source_updated_at = _source_timestamp(
                row.get("updated_at") or row.get("updated_at_iso")
            )
            record, was_created = MirrorRecord.objects.update_or_create(
                organization=organization,
                semantic_package=package,
                external_key=external_key,
                defaults={
                    "company": company,
                    "payload": serialized,
                    "payload_hash": payload_hash,
                    "source_updated_at": source_updated_at,
                },
            )
            # ``record`` is intentionally unused: never log its encrypted payload.
            del record
            if was_created:
                created += 1
            else:
                updated += 1
        package.last_synced_at = timezone.now()
        package.save(update_fields=["last_synced_at", "updated_at"])
    return MirrorSyncResult(created=created, updated=updated, ignored=ignored)


def _package_is_fresh(package: SemanticPackage, *, now: datetime) -> bool:
    if package.last_synced_at is None:
        return False
    return package.last_synced_at >= now - timedelta(seconds=package.max_staleness_seconds)


def _card_detail(*, package: SemanticPackage, payload: str) -> str:
    """Expose only fields reviewed in the semantic package test specification."""
    try:
        row = json.loads(payload)
    except (TypeError, json.JSONDecodeError):
        return "Registro disponível no espelho autorizado."
    if not isinstance(row, dict):
        return "Registro disponível no espelho autorizado."
    fields = package.test_specification.get("card_fields", [])
    if not isinstance(fields, list):
        fields = []
    values: list[str] = []
    for field in fields[:MAX_CARD_FIELDS]:
        if not isinstance(field, str) or field not in row:
            continue
        value = str(row[field]).replace("\n", " ").strip()
        if value:
            values.append(f"{field}: {value[:100]}")
    return " · ".join(values)[:520] or "Registro disponível no espelho autorizado."


def get_mirror_cards(
    *, organization: Organization, company: ClientCompany, tool_name: str, period_days: int = 31
) -> tuple[str, list[MirrorCard]]:
    """Return compact evidence from fresh packages; never fall through to ODBC."""
    packages = [
        package
        for package in SemanticPackage.objects.filter(
            organization=organization,
            tool_name=tool_name,
            enabled=True,
            max_period_days__gte=period_days,
        ).order_by("module", "created_at")
        if semantic_package_ready(package)
    ]
    if not packages:
        return "not_configured", []
    now = timezone.now()
    fresh_packages = [package for package in packages if _package_is_fresh(package, now=now)]
    if not fresh_packages:
        return "stale", []

    cards: list[MirrorCard] = []
    for package in fresh_packages:
        records = MirrorRecord.objects.filter(
            organization=organization,
            semantic_package=package,
            company=company,
        ).order_by("-source_updated_at", "-synchronized_at")[:MAX_CARD_RECORDS]
        for record in records:
            cards.append(
                MirrorCard(
                    label=f"{package.module}: dado sincronizado",
                    reference=package.source_reference,
                    detail=_card_detail(package=package, payload=record.payload),
                )
            )
            if len(cards) >= MAX_CARD_RECORDS:
                return "fresh", cards
    return ("fresh" if len(fresh_packages) == len(packages) else "partial"), cards
