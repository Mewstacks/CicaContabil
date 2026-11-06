"""Private Domínio previews without enabling or recording an accounting export."""

from __future__ import annotations

import hashlib
import json
import secrets
from datetime import date
from typing import Any, BinaryIO, cast

from django.conf import settings
from django.core.files.base import ContentFile
from django.db import transaction

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.models import (
    AccountingExport,
    AccountingExportPreview,
    ClientCompany,
    FinancialAccount,
    JournalEntry,
    ReconciliationSourceFile,
)
from apps.hub.reconciliation_service import (
    MAX_ROWS,
    ReconciliationError,
    get_accounting_export_adapter,
    validate_journal_entry,
)
from apps.organizations.models import Organization


def preview_enabled(organization: Organization) -> bool:
    """An explicit office UUID is required; names, slugs and demos never opt in."""
    return (
        organization.is_active
        and not organization.is_demo
        and str(organization.pk) in settings.RECONCILIATION_DOMINIO_PREVIEW_ORGANIZATION_IDS
    )


def _prepared(
    account: FinancialAccount, start: date, end: date
) -> tuple[list[JournalEntry], dict[str, Any]]:
    if (
        not account.active
        or not account.company.active
        or account.company.organization_id != account.organization_id
        or not account.account_reference
        or not account.ledger_code
        or start > end
    ):
        raise ReconciliationError("Confira empresa, conta financeira e período da prévia.")
    adapter = get_accounting_export_adapter(AccountingExport.Target.DOMINIO)
    entries = list(
        JournalEntry.objects.filter(
            organization_id=account.organization_id,
            company_id=account.company_id,
            state=JournalEntry.State.APPROVED,
            occurred_on__range=(start, end),
            movement__organization_id=account.organization_id,
            movement__company_id=account.company_id,
            movement__source_file__financial_account=account,
            movement__source_file__organization_id=account.organization_id,
            movement__source_file__company_id=account.company_id,
            movement__source_file__origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
        )
        .exclude(purpose="source_ledger")
        .select_related("movement", "movement__source_file")
        .prefetch_related("lines")
        .order_by("occurred_on", "id")[: MAX_ROWS + 1]
    )
    if not entries:
        raise ReconciliationError(
            "Não há lançamentos novos aprovados nesta conta e período. Revise e aprove antes."
        )
    if len(entries) > MAX_ROWS:
        raise ReconciliationError("O período excede o limite de lançamentos; reduza o recorte.")
    ids = {str(entry.pk) for entry in entries}
    exported = AccountingExport.objects.filter(
        organization_id=account.organization_id,
        company_id=account.company_id,
        state__in=[AccountingExport.State.READY, AccountingExport.State.CONFIRMED],
    ).values_list("entry_ids", flat=True)
    if any(ids.intersection(prior) for prior in exported.iterator()):
        raise ReconciliationError("Há lançamentos já exportados; confira o histórico original.")
    records = []
    for entry in entries:
        errors = validate_journal_entry(entry)
        lines = sorted(entry.lines.all(), key=lambda line: str(line.pk))
        if any(line.organization_id != account.organization_id for line in lines):
            errors.append("As partidas não pertencem ao escritório selecionado.")
        if account.ledger_code not in {line.account_code for line in lines}:
            errors.append("O lançamento não utiliza a conta contábil do banco selecionado.")
        movement = entry.movement
        if movement is None or movement.review_state in {"ignored", "pending", "conflict"}:
            errors.append("O movimento precisa de revisão antes da prévia.")
        if errors:
            raise ReconciliationError(" ".join(errors))
        assert movement is not None
        records.append(
            {
                "id": str(entry.pk),
                "revision": entry.revision,
                "date": entry.occurred_on.isoformat(),
                "history": entry.history,
                "purpose": entry.purpose,
                "approved_at": entry.approved_at.isoformat() if entry.approved_at else None,
                "approved_by": str(entry.approved_by_id) if entry.approved_by_id else None,
                "movement_id": str(movement.pk),
                "movement_revision": movement.revision,
                "movement_updated_at": movement.updated_at.isoformat(),
                "source_id": str(movement.source_file_id),
                "source_hash": movement.source_file.content_hash,
                "lines": [
                    {
                        "id": str(line.pk),
                        "account": line.account_code,
                        "side": line.side,
                        "amount_cents": line.amount_cents,
                        "cost_center": line.cost_center_code,
                        "history": line.history,
                    }
                    for line in lines
                ],
            }
        )
    return entries, {
        "contract": "dominio-private-preview-v1",
        "homologated": False,
        "organization_id": str(account.organization_id),
        "company_id": str(account.company_id),
        "financial_account_id": str(account.pk),
        "account_reference": account.account_reference,
        "ledger_code": account.ledger_code,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "adapter_version": adapter.version,
        "entries": records,
    }


def _fingerprint(snapshot: dict[str, Any]) -> str:
    encoded = json.dumps(snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("ascii")).hexdigest()


@transaction.atomic
def create_preview(
    *,
    organization: Organization,
    account: FinancialAccount,
    start: date,
    end: date,
    actor: User,
    request: object = None,
) -> tuple[AccountingExportPreview, bool]:
    if not preview_enabled(organization) or account.organization_id != organization.pk:
        raise ReconciliationError("Prévia indisponível para este escritório.")
    ClientCompany.objects.select_for_update().get(pk=account.company_id, organization=organization)
    account = FinancialAccount.objects.select_related("company").get(
        pk=account.pk, organization=organization
    )
    entries, snapshot = _prepared(account, start, end)
    fingerprint = _fingerprint(snapshot)
    existing = AccountingExportPreview.objects.filter(
        organization=organization, financial_account=account, source_fingerprint=fingerprint
    ).first()
    if existing:
        stream = open_preview_content(existing)
        stream.close()
        return existing, False
    adapter = get_accounting_export_adapter(AccountingExport.Target.DOMINIO)
    rendered = adapter.render(entries)
    preview = AccountingExportPreview(
        organization=organization,
        company=account.company,
        financial_account=account,
        period_start=start,
        period_end=end,
        adapter_version=adapter.version,
        source_snapshot=snapshot,
        source_fingerprint=fingerprint,
        content_hash=hashlib.sha256(rendered).hexdigest(),
        created_by=actor,
    )
    try:
        preview.content.save("previa-nao-homologada.csv", ContentFile(rendered), save=False)
        preview.save()
        record_event(
            action="hub.reconciliation.preview_created",
            actor=actor,
            organization=organization,
            target=preview,
            request=request,
            metadata={"entries": len(entries), "hash": preview.content_hash, "homologated": False},
        )
    except Exception:
        if preview.content.name:
            preview.content.storage.delete(preview.content.name)
        raise
    return preview, True


def preview_is_current(preview: AccountingExportPreview) -> bool:
    try:
        account = FinancialAccount.objects.select_related("company").get(
            pk=preview.financial_account_id,
            organization_id=preview.organization_id,
            company_id=preview.company_id,
        )
        _, snapshot = _prepared(account, preview.period_start, preview.period_end)
        return secrets.compare_digest(_fingerprint(snapshot), preview.source_fingerprint)
    except (FinancialAccount.DoesNotExist, ReconciliationError):
        return False


def open_preview_content(preview: AccountingExportPreview) -> BinaryIO:
    """Verify the same private stream that will be returned to the authorized caller."""
    stream = None
    try:
        stream = preview.content.open("rb")
        digest = hashlib.sha256()
        for chunk in stream.chunks():
            digest.update(chunk)
        if not secrets.compare_digest(digest.hexdigest(), preview.content_hash):
            raise ReconciliationError("Arquivo da prévia divergente; solicite conferência técnica.")
        stream.seek(0)
        return cast(BinaryIO, stream)
    except (OSError, ValueError) as exc:
        if stream is not None:
            stream.close()
        raise ReconciliationError(
            "Arquivo da prévia indisponível; solicite conferência técnica."
        ) from exc
