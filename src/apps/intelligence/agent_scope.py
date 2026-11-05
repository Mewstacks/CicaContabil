"""Explicit, office-bound restrictions for the Domínio pilot (D-309)."""

from __future__ import annotations

import hashlib
import json
import re
from calendar import monthrange
from datetime import date
from typing import Any
from uuid import UUID

from django.utils import timezone

from apps.hub.models import FinancialAccount
from apps.organizations.models import Organization

PROTOCOL = "scoped-v1"
VERSION = "dominio-pilot-v1"
_FIELDS = {
    "version",
    "financial_account_id",
    "company_code",
    "account_reference",
    "period_start",
    "period_end",
    "statement_ids",
}
_ID = re.compile(r"[0-9]{1,18}")


def validate_sync_scope(value: Any, organization: Organization) -> dict[str, Any]:
    """Reject missing/stale manifests; never derive account identity from bank rows."""
    if not isinstance(value, dict) or set(value) != _FIELDS | {"revision"}:
        raise ValueError("Recorte financeiro ausente ou inválido.")
    if value["version"] != VERSION or not all(
        isinstance(value[key], str) for key in _FIELDS - {"statement_ids"}
    ):
        raise ValueError("Contrato do recorte financeiro inválido.")
    try:
        account_id = UUID(value["financial_account_id"])
        start = date.fromisoformat(value["period_start"])
        end = date.fromisoformat(value["period_end"])
    except (ValueError, TypeError) as exc:
        raise ValueError("Conta ou competência do recorte inválida.") from exc
    if (
        start.day != 1
        or start.isoformat() != value["period_start"]
        or end.isoformat() != value["period_end"]
        or start.year != end.year
        or start.month != end.month
        or end.day != monthrange(start.year, start.month)[1]
        or end >= timezone.localdate()
    ):
        raise ValueError("Escolha uma competência anterior completa para o piloto.")
    ids = value["statement_ids"]
    if (
        not isinstance(ids, list)
        or not 1 <= len(ids) <= 500
        or any(not isinstance(item, str) or not _ID.fullmatch(item) for item in ids)
        or len(ids) != len(set(ids))
        or not _ID.fullmatch(value["company_code"])
    ):
        raise ValueError("Informe identificadores de extrato revisados, sem repetição.")
    account = (
        FinancialAccount.objects.select_related("company")
        .filter(
            pk=account_id,
            organization=organization,
            company__organization=organization,
            active=True,
            company__dominio_code=value["company_code"],
            account_reference=value["account_reference"],
        )
        .first()
    )
    if account is None or not value["account_reference"]:
        raise ValueError("A conta do recorte não está ativa nesta empresa/escritório.")
    content = {key: value[key] for key in sorted(_FIELDS)}
    digest = hashlib.sha256(
        json.dumps(content, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    if value["revision"] != digest:
        raise ValueError("A revisão do recorte financeiro não confere.")
    return {**content, "revision": digest}


def build_sync_scope(
    *, account: FinancialAccount, start: date, end: date, statement_ids: list[str]
) -> dict[str, Any]:
    scope: dict[str, Any] = {
        "version": VERSION,
        "financial_account_id": str(account.pk),
        "company_code": account.company.dominio_code,
        "account_reference": account.account_reference,
        "period_start": start.isoformat(),
        "period_end": end.isoformat(),
        "statement_ids": sorted(statement_ids),
    }
    scope["revision"] = hashlib.sha256(
        json.dumps(scope, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return validate_sync_scope(scope, account.organization)


def validate_scope_page(scope: dict[str, Any], payload: dict[str, Any], *, bank: bool) -> None:
    if payload.get("scope_revision") != scope["revision"]:
        raise ValueError("A página não corresponde à revisão do recorte financeiro.")
    rows = payload["rows" if bank else "companies"]
    for row in rows:
        if row.get("company_code" if bank else "codigo") != scope["company_code"]:
            raise ValueError("Página fora da empresa autorizada.")
        if bank:
            source = row.get("source_id")
            occurred = row.get("occurred_on")
            parts = source.split("|") if isinstance(source, str) else []
            if (
                len(parts) != 3
                or parts[0] != scope["company_code"]
                or parts[1] not in scope["statement_ids"]
                or not _ID.fullmatch(parts[2])
                or not isinstance(occurred, str)
                or not scope["period_start"] <= occurred <= scope["period_end"]
                or row.get("account_reference") != scope["account_reference"]
            ):
                raise ValueError("Página fora da conta, competência ou extratos autorizados.")
            try:
                date.fromisoformat(occurred)
            except ValueError as exc:
                raise ValueError("Data de extrato inválida.") from exc
