"""Scoped export approval and immutable, human-observed ERP import results (D-375).

These functions never call the ERP or infer that generating/downloading a file imported it.
The technical homologation entry point records an already obtained human decision; it
is intentionally separate from the customer receipt endpoint and permits actor=None.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
from typing import Any
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.controlplane import company_queryset_for_module
from apps.hub.models import (
    AccountingExport,
    AccountingExportHomologation,
    AccountingImportReceipt,
    ClientCompany,
    JournalEntry,
    ProductModule,
    ReconciliationSourceFile,
)
from apps.organizations.models import Membership, Organization
from apps.platform.operation_access import require_operation_access


class ImportReceiptError(ValueError):
    pass


class ImportReceiptConflict(ImportReceiptError):
    pass


def _authorize(company: ClientCompany, actor: User, *, write: bool) -> None:
    members = Membership.objects.select_related("organization").filter(
        organization_id=company.organization_id,
        user=actor,
        user__is_active=True,
        is_active=True,
        role__in=["owner", "admin", "manager", "operator"] + ([] if write else ["auditor"]),
    )
    if write:
        members = members.select_for_update(of=("self",))
    member = members.first()
    if (
        member is None
        or not company_queryset_for_module(
            member,
            ProductModule.Code.RECONCILIATION,
        )
        .filter(pk=company.pk)
        .exists()
    ):
        raise PermissionDenied("Seu acesso atual não permite conferir esta importação.")
    if write:
        try:
            require_operation_access(member.organization, ProductModule.Code.RECONCILIATION)
        except ValueError as exc:
            raise ImportReceiptError(str(exc)) from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")
    ).hexdigest()


def _text(value: Any, maximum: int, label: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > maximum
        or any(ord(c) < 32 or ord(c) == 127 for c in value)
    ):
        raise ImportReceiptError(f"Confira {label}.")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError:
        raise ImportReceiptError(f"Confira os caracteres em {label}.") from None
    return value.strip()


def _sha(value: Any) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ImportReceiptError("Confira o SHA-256 da evidência ou do arquivo.")
    return value


def _uuid(value: Any) -> UUID:
    try:
        return UUID(str(value))
    except (ValueError, TypeError, AttributeError):
        raise ImportReceiptError("Reabra a conferência para obter uma referência válida.") from None


def _approval_payload(row: AccountingExportHomologation) -> dict[str, Any]:
    return dict(
        organization=str(row.organization_id),
        target=row.target,
        adapter_version=row.adapter_version,
        request_key=str(row.request_key),
        approved=row.approved,
        evidence=row.evidence,
    )


def _active_homologation(
    organization: Organization,
    target: str,
    adapter_version: str,
) -> AccountingExportHomologation | None:
    """The old global switch cannot grant an office permission to export."""
    if not Organization.objects.filter(
        pk=organization.pk,
        is_active=True,
        is_demo=False,
    ).exists():
        return None
    row = AccountingExportHomologation.objects.filter(
        organization=organization,
        target=target,
        adapter_version=adapter_version,
    ).first()
    valid = bool(
        row
        and row.approved
        and isinstance(row.evidence, dict)
        and hmac.compare_digest(row.fingerprint, _digest(_approval_payload(row)))
    )
    return row if valid else None


def export_homologated(organization: Organization, target: str, adapter_version: str) -> bool:
    return _active_homologation(organization, target, adapter_version) is not None


@transaction.atomic
def record_export_homologation(
    *,
    organization: Organization,
    target: str,
    adapter_version: str,
    request_key: Any,
    approved: bool,
    evidence_reference: str,
    evidence_sha256: str,
    artifact_sha256: str,
    importer_version: str,
    human_decision_reference: str,
    actor: User | None = None,
    request: Any = None,
) -> tuple[AccountingExportHomologation, bool]:
    """Record technical evidence of an explicit human approval/revocation, never infer one."""
    organization = Organization.objects.select_for_update(no_key=True).get(pk=organization.pk)
    if not organization.is_active or organization.is_demo:
        raise ImportReceiptError("Homologação indisponível para este escritório.")
    if (
        actor is not None
        and not Membership.objects.filter(
            organization=organization,
            user=actor,
            user__is_active=True,
            is_active=True,
            role__in=["owner", "admin"],
        ).exists()
    ):
        raise PermissionDenied("Somente a administração pode registrar a homologação.")
    require_operation_access(organization, ProductModule.Code.RECONCILIATION)
    if target not in AccountingExport.Target.values or type(approved) is not bool:
        raise ImportReceiptError("Confira o destino e a decisão da homologação.")
    evidence = dict(
        reference=_text(evidence_reference, 1000, "a referência privada da evidência"),
        sha256=_sha(evidence_sha256),
        artifact_sha256=_sha(artifact_sha256),
        importer_version=_text(importer_version, 120, "a versão do importador"),
        human_decision_reference=_text(
            human_decision_reference,
            1000,
            "a referência da decisão humana",
        ),
        actor=str(actor.pk) if actor else None,
        authorship="user" if actor else "technical_record_of_external_decision",
    )
    row = AccountingExportHomologation(
        organization=organization,
        target=target,
        adapter_version=_text(adapter_version, 32, "a versão do adaptador"),
        request_key=_uuid(request_key),
        approved=approved,
        evidence=evidence,
        created_by=actor,
    )
    row.fingerprint = _digest(_approval_payload(row))
    prior = AccountingExportHomologation.objects.filter(
        organization=organization,
        request_key=row.request_key,
    ).first()
    if prior:
        if (
            prior.fingerprint != row.fingerprint
            or _digest(_approval_payload(prior)) != row.fingerprint
        ):
            raise ImportReceiptConflict("Esta referência já registra outra decisão.")
        return prior, False
    row.save()
    record_event(
        action="hub.reconciliation.export_homologation_recorded",
        actor=actor,
        organization=organization,
        target=row,
        request=request,
        metadata={
            "target": target,
            "adapter_version": adapter_version,
            "approved": approved,
            "fingerprint": row.fingerprint,
        },
    )
    return row, True


def _artifact(export: AccountingExport) -> None:
    try:
        _sha(export.content_hash)
        digest = hashlib.sha256()
        with export.content.open("rb") as stream:
            for chunk in stream.chunks():
                digest.update(chunk)
        if not hmac.compare_digest(digest.hexdigest(), export.content_hash):
            raise ValueError
    except (OSError, ValueError):
        raise ImportReceiptError("O arquivo original está ausente ou diverge do hash.") from None


def _evidence(
    company: ClientCompany,
    reference: str,
    source: ReconciliationSourceFile | None,
) -> dict[str, Any]:
    reference = _text(reference, 1000, "a referência privada do retorno do ERP")
    if source is None:
        return dict(
            kind="attestation",
            reference=reference,
            sha256=hashlib.sha256(reference.encode("utf-8")).hexdigest(),
        )
    if not isinstance(source, ReconciliationSourceFile):
        raise ImportReceiptError("Selecione um comprovante privado válido.")
    retained = ReconciliationSourceFile.objects.filter(
        pk=source.pk,
        organization_id=company.organization_id,
        company=company,
        origin=ReconciliationSourceFile.Origin.DOCUMENT,
    ).first()
    if retained is None or not 0 < retained.size_bytes <= 25 * 1024 * 1024:
        raise ImportReceiptError("O comprovante não pertence à empresa ou excede 25 MiB.")
    try:
        size = 0
        digest = hashlib.sha256()
        with retained.content.open("rb") as stream:
            for chunk in stream.chunks():
                size += len(chunk)
                if size > retained.size_bytes:
                    raise ValueError
                digest.update(chunk)
        if size != retained.size_bytes or digest.hexdigest() != retained.content_hash:
            raise ValueError
    except (OSError, ValueError):
        raise ImportReceiptError("O comprovante está ausente ou diverge do hash.") from None
    return dict(
        kind="document",
        reference=reference,
        source_id=str(retained.pk),
        sha256=retained.content_hash,
        size_bytes=retained.size_bytes,
    )


def _original(export: AccountingExport) -> AccountingExport:
    seen: set[Any] = set()
    current = export
    while current.reexport_of_id:
        if current.pk in seen:
            raise ImportReceiptError("O histórico de cópias precisa de revisão.")
        seen.add(current.pk)
        parent = AccountingExport.objects.get(pk=current.reexport_of_id)
        if any(
            getattr(parent, field) != getattr(export, field)
            for field in (
                "organization_id",
                "company_id",
                "target",
                "adapter_version",
                "content_hash",
                "period_start",
                "period_end",
                "entry_ids",
            )
        ):
            raise ImportReceiptError("A cópia diverge do arquivo original.")
        current = parent
    return current


def _receipt_payload(row: AccountingImportReceipt) -> dict[str, Any]:
    return dict(
        organization=str(row.organization_id),
        export=str(row.export_id),
        submitted_export=str(row.submitted_export_id),
        previous=str(row.previous_id) if row.previous_id else None,
        request_key=str(row.request_key),
        content_hash=row.content_hash,
        outcome=row.outcome,
        items=row.items,
        evidence=row.evidence,
    )


def _check_receipt(row: AccountingImportReceipt, export: AccountingExport) -> None:
    if (
        row.export_id != export.pk
        or row.organization_id != export.organization_id
        or row.content_hash != export.content_hash
        or not hmac.compare_digest(row.fingerprint, _digest(_receipt_payload(row)))
    ):
        raise ImportReceiptError("O recibo precisa de revisão de integridade.")


def _items(value: Any, export: AccountingExport) -> tuple[list[dict[str, str]], str]:
    expected = export.entry_ids
    if (
        not isinstance(expected, list)
        or not expected
        or any(not isinstance(identifier, str) for identifier in expected)
        or len(expected) != len(set(expected))
        or len(expected) > 100_000
        or not isinstance(value, list)
        or len(value) != len(expected)
    ):
        raise ImportReceiptError("Confira o resultado de todos os lançamentos do arquivo.")
    parsed: dict[str, dict[str, str]] = {}
    for item in value:
        if not isinstance(item, dict) or set(item) != {
            "entry_id",
            "status",
            "erp_reference",
            "evidence_reference",
        }:
            raise ImportReceiptError("Confira os campos de cada resultado da importação.")
        identifier = str(_uuid(item["entry_id"]))
        status = item["status"]
        if (
            identifier in parsed
            or identifier not in expected
            or not isinstance(status, str)
            or status
            not in {
                "accepted",
                "rejected",
                "uncertain",
            }
        ):
            raise ImportReceiptError(
                "Há lançamento repetido, fora do arquivo ou resultado inválido."
            )
        reference = item["erp_reference"]
        if status == "accepted" or reference:
            reference = _text(reference, 240, "a identificação do lançamento no ERP")
        elif reference != "":
            raise ImportReceiptError("Confira a identificação do lançamento no ERP.")
        parsed[identifier] = dict(
            entry_id=identifier,
            status=status,
            erp_reference=reference,
            evidence_reference=(
                ""
                if status == "uncertain" and item["evidence_reference"] == ""
                else _text(item["evidence_reference"], 1000, "a evidência do lançamento")
            ),
        )
    statuses = {item["status"] for item in parsed.values()}
    outcome = (
        "accepted"
        if statuses == {"accepted"}
        else "uncertain"
        if "uncertain" in statuses
        else "rejected"
        if statuses == {"rejected"}
        else "partial"
    )
    return [parsed[identifier] for identifier in expected], outcome


@transaction.atomic
def record_import_receipt(
    *,
    export: AccountingExport,
    actor: User,
    request_key: Any,
    content_hash: str,
    items: Any,
    evidence_reference: str,
    importer_version: str,
    review_confirmed: bool,
    evidence_source: ReconciliationSourceFile | None = None,
    expected_previous_id: Any = None,
    request: Any = None,
) -> tuple[AccountingImportReceipt, bool]:
    """Append one complete observation; partial/uncertain outcomes never confirm an export."""
    Organization.objects.select_for_update(no_key=True).get(pk=export.organization_id)
    company = ClientCompany.objects.select_for_update().get(
        pk=export.company_id,
        organization_id=export.organization_id,
    )
    _authorize(company, actor, write=True)
    submitted = AccountingExport.objects.select_for_update().get(
        pk=export.pk,
        organization_id=company.organization_id,
        company=company,
    )
    original = _original(submitted)
    original = AccountingExport.objects.select_for_update().get(pk=original.pk)
    homologation = _active_homologation(
        company.organization,
        original.target,
        original.adapter_version,
    )
    if homologation is None:
        raise ImportReceiptError("O adaptador não está homologado para este escritório.")
    if importer_version != homologation.evidence.get("importer_version"):
        raise ImportReceiptError("Confira a versão do importador homologado para este escritório.")
    if review_confirmed is not True:
        raise ImportReceiptError("Confirme a conferência do resultado no Domínio.")
    if content_hash != original.content_hash or original.state not in {"ready", "confirmed"}:
        raise ImportReceiptConflict("O arquivo mudou ou não está disponível para conferência.")
    _artifact(submitted)
    if original.pk != submitted.pk:
        _artifact(original)
    parsed, outcome = _items(items, original)
    entries = JournalEntry.objects.filter(
        pk__in=original.entry_ids,
        organization_id=company.organization_id,
        company=company,
    )
    if (
        entries.count() != len(original.entry_ids)
        or entries.filter(purpose="source_ledger").exists()
    ):
        raise ImportReceiptError("O arquivo contém lançamentos ausentes ou fonte do Razão.")
    prior_id = _uuid(expected_previous_id) if expected_previous_id is not None else None
    evidence = dict(
        **_evidence(company, evidence_reference, evidence_source),
        importer_version=_text(importer_version, 120, "a versão do importador"),
        actor=str(actor.pk),
        review_confirmed=True,
        homologation=str(homologation.pk),
    )
    receipt = AccountingImportReceipt(
        organization_id=company.organization_id,
        export=original,
        submitted_export=submitted,
        previous_id=prior_id,
        request_key=_uuid(request_key),
        content_hash=content_hash,
        outcome=outcome,
        items=parsed,
        evidence=evidence,
        created_by=actor,
    )
    receipt.fingerprint = _digest(_receipt_payload(receipt))
    existing = AccountingImportReceipt.objects.filter(
        organization_id=company.organization_id,
        request_key=receipt.request_key,
    ).first()
    if existing:
        _check_receipt(existing, original)
        if existing.fingerprint != receipt.fingerprint:
            raise ImportReceiptConflict("Esta referência já registra outro resultado.")
        return existing, False
    previous = original.import_receipts.first()
    if (previous.pk if previous else None) != prior_id:
        raise ImportReceiptConflict("Há um resultado mais recente. Reabra a conferência.")
    if previous:
        _check_receipt(previous, original)
        old_items = {item["entry_id"]: item for item in previous.items}
        if any(
            old_items[item["entry_id"]]["status"] == "accepted"
            and item != old_items[item["entry_id"]]
            for item in parsed
        ):
            raise ImportReceiptConflict("Preserve os lançamentos já aceitos e sua evidência.")
    if original.state == "confirmed":
        raise ImportReceiptConflict("A importação já está confirmada; preserve o recibo original.")
    receipt.save()
    if outcome == "accepted":
        original.state = AccountingExport.State.CONFIRMED
        original.confirmed_at = timezone.now()
        original.confirmed_by = actor
        original.save(update_fields=["state", "confirmed_at", "confirmed_by", "updated_at"])
    record_event(
        action="hub.reconciliation.import_receipt_recorded",
        actor=actor,
        organization=company.organization,
        target=receipt,
        request=request,
        metadata={
            "export": str(original.pk),
            "outcome": outcome,
            "content_hash": content_hash,
            "fingerprint": receipt.fingerprint,
        },
    )
    return receipt, True


def import_receipt_context(*, export: AccountingExport, actor: User) -> dict[str, Any]:
    company = ClientCompany.objects.select_related("organization").get(
        pk=export.company_id,
        organization_id=export.organization_id,
    )
    _authorize(company, actor, write=False)
    export = AccountingExport.objects.get(pk=export.pk, company=company)
    original = _original(export)
    receipt = original.import_receipts.first()
    if receipt:
        _check_receipt(receipt, original)
    homologation = _active_homologation(
        company.organization,
        original.target,
        original.adapter_version,
    )
    return dict(
        original=original,
        receipt=receipt,
        outcome=receipt.outcome if receipt else "not_recorded",
        items=receipt.items if receipt else [],
        expected_previous_id=str(receipt.pk) if receipt else None,
        homologated=homologation is not None,
        importer_version=homologation.evidence["importer_version"] if homologation else "",
    )
