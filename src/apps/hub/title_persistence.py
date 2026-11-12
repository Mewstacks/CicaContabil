"""Durable human-reviewed title evidence and cash allocations, without ERP writes."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from typing import Any, cast
from uuid import UUID

from django.core.exceptions import PermissionDenied
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q

from apps.accounts.models import User
from apps.audit.services import record_event
from apps.hub.controlplane import company_queryset_for_module
from apps.hub.models import (
    FinancialAccount,
    NormalizedMovement,
    ProductModule,
    ReconciliationSourceFile,
    ReconciliationTitleAllocation,
    ReconciliationTitleBatch,
    ReconciliationTitleDecision,
    ReconciliationTitleSnapshot,
)
from apps.hub.reconciliation_service import MAX_BYTES
from apps.hub.title_allocation import TitleAllocationPreview, preview_title_allocations
from apps.hub.title_contract import TitleContractError, TitleSnapshot, validate_title_snapshot
from apps.organizations.models import Membership
from apps.platform.operation_access import require_operation_access

MAX_PLAN_ALLOCATIONS = 1000


def _hash(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    ).hexdigest()


def _reason(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 240:
        raise TitleContractError("Informe uma referência de revisão com até 240 caracteres.")
    return value.strip()


def authorize_title_account(account: FinancialAccount, actor: User) -> None:
    """Current role, company grant and contract, shared by reviewed and raw title intake."""
    membership = (
        Membership.objects.select_related("organization")
        .filter(
            organization_id=account.organization_id,
            user=actor,
            is_active=True,
            user__is_active=True,
            role__in=[
                Membership.Role.OWNER,
                Membership.Role.ADMIN,
                Membership.Role.MANAGER,
                Membership.Role.OPERATOR,
            ],
        )
        .first()
    )
    if (
        membership is None
        or not account.active
        or account.company.organization_id != account.organization_id
        or not account.account_reference
        or not company_queryset_for_module(membership, ProductModule.Code.RECONCILIATION)
        .filter(pk=account.company_id)
        .exists()
    ):
        raise PermissionDenied("Seu acesso atual não permite revisar títulos desta conta.")
    require_operation_access(account.organization, ProductModule.Code.RECONCILIATION)


def _account(identifier: Any, *, lock: bool = False) -> FinancialAccount:
    query = FinancialAccount.objects.all()
    if lock:
        query = query.select_for_update(of=("self",))
    return query.select_related("company", "organization").get(pk=identifier)


def _parse(content: bytes, account: FinancialAccount) -> tuple[dict[str, Any], TitleSnapshot]:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError
            result[key] = value
        return result

    if not isinstance(content, bytes) or not 1 <= len(content) <= MAX_BYTES:
        raise TitleContractError("Fonte de títulos vazia ou maior que 25 MiB.")
    try:
        payload = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=unique,
            parse_constant=lambda _: (_ for _ in ()).throw(ValueError()),
        )
        snapshot = validate_title_snapshot(
            payload,
            company_key=str(account.company_id),
            account_reference=account.account_reference,
        )
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise TitleContractError("Fonte fora do contrato normalizado de títulos.") from None
    return payload, snapshot


def _load(
    snapshot: ReconciliationTitleSnapshot, account: FinancialAccount
) -> tuple[dict[str, Any], TitleSnapshot]:
    source = snapshot.source_file
    if (
        snapshot.organization_id != account.organization_id
        or snapshot.company_id != account.company_id
        or snapshot.financial_account_id != account.id
        or source.organization_id != account.organization_id
        or source.company_id != account.company_id
        or source.financial_account_id != account.id
        or source.kind != "json"
        or source.origin != "obligation"
    ):
        raise TitleContractError("Fonte de títulos fora da empresa ou conta revisada.")
    try:
        with source.content.open("rb") as stream:
            content = stream.read(MAX_BYTES + 1)
    except (OSError, ValueError):
        raise TitleContractError("Fonte privada ausente; restaure o arquivo original.") from None
    if (
        len(content) != source.size_bytes
        or hashlib.sha256(content).hexdigest() != source.content_hash
    ):
        raise TitleContractError("Hash da fonte de títulos diverge; restaure o original.")
    payload, parsed = _parse(content, account)
    if (
        parsed.fingerprint != snapshot.fingerprint
        or parsed.as_of != snapshot.as_of
        or parsed.settlements_complete != snapshot.settlements_complete
    ):
        raise TitleContractError("Fotografia persistida diverge da fonte original.")
    return payload, parsed


def import_title_snapshot(
    *, financial_account: FinancialAccount, content: bytes, actor: User, evidence_reference: str
) -> tuple[ReconciliationTitleSnapshot, bool]:
    """Retain a complete reviewed contract atomically; a replay never duplicates it."""
    saved_source: ReconciliationSourceFile | None = None
    try:
        with transaction.atomic():
            account = _account(financial_account.pk, lock=True)
            authorize_title_account(account, actor)
            reason = _reason(evidence_reference)
            _, parsed = _parse(content, account)
            existing = (
                ReconciliationTitleSnapshot.objects.select_related("source_file")
                .filter(
                    organization_id=account.organization_id,
                    financial_account=account,
                    fingerprint=parsed.fingerprint,
                )
                .first()
            )
            if existing:
                _load(existing, account)
                return existing, False
            digest = hashlib.sha256(content).hexdigest()
            source = ReconciliationSourceFile.objects.filter(
                organization_id=account.organization_id,
                company_id=account.company_id,
                content_hash=digest,
            ).first()
            if source is not None:
                raise TitleContractError("Arquivo já registrado em outro contexto de importação.")
            source = ReconciliationSourceFile(
                organization_id=account.organization_id,
                company_id=account.company_id,
                financial_account=account,
                kind="json",
                origin="obligation",
                original_filename="titulos-normalizados.json",
                content_hash=digest,
                content_type="application/json",
                size_bytes=len(content),
                uploaded_by=actor,
            )
            source.content.save(source.original_filename, ContentFile(content), save=False)
            saved_source = source
            source.save()
            snapshot = ReconciliationTitleSnapshot.objects.create(
                organization_id=account.organization_id,
                company_id=account.company_id,
                financial_account=account,
                source_file=source,
                fingerprint=parsed.fingerprint,
                as_of=parsed.as_of,
                settlements_complete=parsed.settlements_complete,
                evidence_reference=reason,
                reviewed_by=actor,
            )
            record_event(
                action="hub.reconciliation.titles_imported",
                organization=account.organization,
                actor=actor,
                target=snapshot,
                metadata={
                    "snapshot_id": str(snapshot.pk),
                    "titles": len(parsed.titles),
                    "settlements_complete": parsed.settlements_complete,
                },
            )
            return snapshot, True
    except Exception:
        if saved_source is not None:
            saved_source.content.delete(save=False)
        raise


def _bank_identity(movement: NormalizedMovement) -> str:
    source = movement.source_file
    # FITID identifies an OFX fact across overlapping files; other formats require
    # the same original file plus source key, never a guessed date/value identity.
    key = [source.kind, movement.source_key]
    if source.kind != "ofx":
        key.append(source.content_hash)
    return _hash([str(movement.financial_account_id), key])


def _bank_fingerprint(movement: NormalizedMovement) -> str:
    return _hash(
        [
            _bank_identity(movement),
            str(movement.occurred_on),
            movement.amount_cents,
            movement.direction,
            movement.currency,
            movement.original_description,
            movement.document_number,
            movement.source_file.origin,
        ]
    )


def _verify_bank_source(source: ReconciliationSourceFile) -> None:
    try:
        with source.content.open("rb") as stream:
            content = stream.read(MAX_BYTES + 1)
    except (OSError, ValueError):
        raise TitleContractError("Fonte bancária privada ausente; restaure o original.") from None
    if (
        len(content) != source.size_bytes
        or hashlib.sha256(content).hexdigest() != source.content_hash
    ):
        raise TitleContractError("Hash da fonte bancária diverge; restaure o original.")


def _settlement_identity(account: FinancialAccount, title: str, part: str, event: str) -> str:
    return _hash([str(account.pk), title, part, event])


def _settlements(parsed: TitleSnapshot, account: FinancialAccount) -> dict[str, tuple[Any, str]]:
    result = {}
    for title in parsed.titles:
        for part in title.installments:
            for event in part.settlements:
                identity = _settlement_identity(account, title.key, part.key, event.key)
                raw = {**asdict(event), "posted_on": event.posted_on.isoformat()}
                result[identity] = (event, _hash([title.kind, raw]))
    return result


@dataclass(frozen=True)
class TitleAllocationPlan:
    fingerprint: str
    preview: TitleAllocationPreview


def title_plan_review(plan: TitleAllocationPlan) -> dict[str, Any]:
    """The exact bounded review retained with the receipt and private operator file."""
    selected = {row.reference for row in plan.preview.allocations}
    result = {
        "snapshot_fingerprint": plan.preview.snapshot_fingerprint,
        "source_settlements_complete": plan.preview.source_settlements_complete,
        "movements": [asdict(row) for row in plan.preview.movements],
        "settlements": [
            asdict(row) for row in plan.preview.settlements if row.reference in selected
        ],
        "allocations": [asdict(row) for row in plan.preview.allocations],
        "requires_review": True,
    }
    return cast(dict[str, Any], json.loads(json.dumps(result, default=str)))


@dataclass
class _PreparedPlan:
    plan: TitleAllocationPlan
    movements: dict[str, NormalizedMovement]
    settlements: dict[str, tuple[Any, str]]


def _prepare(
    snapshot: ReconciliationTitleSnapshot,
    account: FinancialAccount,
    requests: Any,
    period_start: date,
    period_end: date,
    *,
    lock: bool = False,
) -> _PreparedPlan:
    if type(period_start) is not date or type(period_end) is not date:
        raise TitleContractError("Período exige datas explícitas.")
    latest = (
        ReconciliationTitleSnapshot.objects.filter(
            organization_id=account.organization_id, financial_account=account
        )
        .order_by("-as_of", "-created_at", "-id")
        .first()
    )
    if latest is None or latest.pk != snapshot.pk:
        raise TitleContractError("Há fotografia mais recente; revise os títulos atuais.")
    payload, parsed = _load(latest, account)
    if not isinstance(requests, list) or not 1 <= len(requests) <= MAX_PLAN_ALLOCATIONS:
        raise TitleContractError("Revise de 1 a 1.000 alocações por lote.")
    try:
        keys = {row["movement_key"] for row in requests}
        if any(str(UUID(key)) != key for key in keys):
            raise ValueError
    except (TypeError, KeyError, ValueError, AttributeError):
        raise TitleContractError("Movimento selecionado exige identificador CICA válido.") from None
    movement_query = NormalizedMovement.objects.select_related("source_file")
    if lock:
        movement_query = movement_query.select_for_update(of=("self",))
    movements = {
        str(item.pk): item
        for item in movement_query.filter(
            pk__in=keys,
            financial_account=account,
            organization_id=account.organization_id,
            company_id=account.company_id,
        )
    }
    if len(movements) != len(keys):
        raise TitleContractError("Movimento fora da empresa ou conta selecionada.")
    bank_rows = []
    identities = set()
    checked_sources = set()
    for movement in movements.values():
        source = movement.source_file
        if source.pk not in checked_sources:
            _verify_bank_source(source)
            checked_sources.add(source.pk)
        identity = _bank_identity(movement)
        if (
            source.organization_id != account.organization_id
            or source.company_id != account.company_id
            or source.financial_account_id != account.id
            or source.origin != "bank_statement"
            or movement.currency != "BRL"
            or not movement.occurred_on
            or not movement.amount_cents
            or identity in identities
            or movement.review_state in {"ignored", "conflict"}
            or movement.direction != ("inflow" if movement.amount_cents > 0 else "outflow")
        ):
            raise TitleContractError("Movimento bancário inválido, repetido ou em revisão.")
        identities.add(identity)
        bank_rows.append(
            {
                "key": str(movement.pk),
                "occurred_on": movement.occurred_on.isoformat(),
                "cash_cents": abs(movement.amount_cents),
                "direction": movement.direction,
            }
        )
    preview = preview_title_allocations(
        payload,
        {
            "contract": "bank-cash-normalized-v1",
            "company_key": str(account.company_id),
            "account_reference": account.account_reference,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "movements": bank_rows,
        },
        requests,
        company_key=str(account.company_id),
        account_reference=account.account_reference,
        period_start=period_start,
        period_end=period_end,
    )
    settlements = _settlements(parsed, account)
    selected = {
        _settlement_identity(
            account,
            row.reference.title_key,
            row.reference.installment_key,
            row.reference.settlement_key,
        )
        for row in preview.allocations
    }
    active = list(
        ReconciliationTitleAllocation.objects.filter(
            Q(movement_identity__in=identities) | Q(settlement_identity__in=selected),
            organization_id=account.organization_id,
            financial_account=account,
            state="confirmed",
        )
        .select_related("movement__source_file")
        .order_by("id")
    )
    bank_used: dict[str, int] = defaultdict(int)
    event_used: dict[str, int] = defaultdict(int)
    affected = []
    for previous in active:
        if previous.movement_fingerprint != _bank_fingerprint(previous.movement):
            raise TitleContractError("Fonte de vínculo anterior mudou; revise antes de alocar.")
        if previous.movement_identity in identities:
            current = next(
                m for m in movements.values() if _bank_identity(m) == previous.movement_identity
            )
            if previous.movement_fingerprint != _bank_fingerprint(current):
                raise TitleContractError(
                    "Movimento já alocado mudou; revise e desfaça o vínculo anterior."
                )
            bank_used[previous.movement_identity] += previous.cash_cents
        if previous.settlement_identity in selected:
            if previous.settlement_fingerprint != settlements[previous.settlement_identity][1]:
                raise TitleContractError(
                    "Baixa já alocada mudou; revise e desfaça o vínculo anterior."
                )
            event_used[previous.settlement_identity] += previous.cash_cents
        if previous.movement_identity in identities or previous.settlement_identity in selected:
            affected.append([str(previous.pk), previous.cash_cents])
    for row in preview.allocations:
        movement = movements[row.movement_key]
        bank_id = _bank_identity(movement)
        event_id = _settlement_identity(
            account,
            row.reference.title_key,
            row.reference.installment_key,
            row.reference.settlement_key,
        )
        bank_used[bank_id] += row.cash_cents
        event_used[event_id] += row.cash_cents
        if (
            bank_used[bank_id] > abs(movement.amount_cents)
            or event_used[event_id] > settlements[event_id][0].cash_cents
        ):
            raise TitleContractError("Capacidade já utilizada por outra alocação confirmada.")
    fingerprint = _hash(
        {
            "snapshot": str(snapshot.pk),
            "preview": preview.fingerprint,
            "active": affected,
            "bank": sorted(
                [
                    key,
                    movement.revision,
                    _bank_fingerprint(movement),
                    movement.source_file.content_hash,
                ]
                for key, movement in movements.items()
            ),
        }
    )
    return _PreparedPlan(TitleAllocationPlan(fingerprint, preview), movements, settlements)


def prepare_title_allocations(
    *,
    snapshot: ReconciliationTitleSnapshot,
    requests: Any,
    actor: User,
    period_start: date,
    period_end: date,
) -> TitleAllocationPlan:
    account = _account(snapshot.financial_account_id)
    authorize_title_account(account, actor)
    return _prepare(snapshot, account, requests, period_start, period_end).plan


@transaction.atomic
def confirm_title_allocations(
    *,
    snapshot: ReconciliationTitleSnapshot,
    requests: Any,
    actor: User,
    period_start: date,
    period_end: date,
    request_id: UUID,
    preview_fingerprint: str,
    evidence_reference: str,
    accept_date_differences: bool = False,
) -> tuple[ReconciliationTitleBatch, bool]:
    account = _account(snapshot.financial_account_id, lock=True)
    authorize_title_account(account, actor)
    reason = _reason(evidence_reference)
    if type(request_id) is not UUID or type(accept_date_differences) is not bool:
        raise TitleContractError("Lote exige chave de reenvio e revisão explícita das datas.")
    if type(period_start) is not date or type(period_end) is not date:
        raise TitleContractError("Período exige datas explícitas.")
    if not isinstance(requests, list) or not 1 <= len(requests) <= MAX_PLAN_ALLOCATIONS:
        raise TitleContractError("Revise de 1 a 1.000 alocações por lote.")
    try:
        request_fingerprint = _hash(
            [
                str(snapshot.pk),
                requests,
                period_start.isoformat(),
                period_end.isoformat(),
                accept_date_differences,
                reason,
            ]
        )
    except (TypeError, ValueError, RecursionError):
        raise TitleContractError("Pedido de alocação inválido.") from None
    previous = ReconciliationTitleBatch.objects.filter(
        organization_id=account.organization_id, financial_account=account, request_id=request_id
    ).first()
    if previous:
        if (
            previous.preview_fingerprint != preview_fingerprint
            or previous.request_fingerprint != request_fingerprint
            or previous.snapshot_id != snapshot.pk
            or previous.period_start != period_start
            or previous.period_end != period_end
        ):
            raise TitleContractError("Chave de reenvio já utilizada por outra revisão.")
        return previous, False
    prepared = _prepare(snapshot, account, requests, period_start, period_end, lock=True)
    if prepared.plan.fingerprint != preview_fingerprint:
        raise TitleContractError("A prévia mudou; revise novamente antes de confirmar.")
    if (
        any(row.date_difference for row in prepared.plan.preview.allocations)
        and not accept_date_differences
    ):
        raise TitleContractError("Revise explicitamente as diferenças de data antes de confirmar.")
    batch = ReconciliationTitleBatch.objects.create(
        organization_id=account.organization_id,
        financial_account=account,
        snapshot=snapshot,
        request_id=request_id,
        preview_fingerprint=preview_fingerprint,
        request_fingerprint=request_fingerprint,
        review_snapshot=title_plan_review(prepared.plan),
        period_start=period_start,
        period_end=period_end,
        reviewed_by=actor,
        evidence_reference=reason,
        accepted_date_differences=accept_date_differences,
    )
    for row in prepared.plan.preview.allocations:
        movement = prepared.movements[row.movement_key]
        event_id = _settlement_identity(
            account,
            row.reference.title_key,
            row.reference.installment_key,
            row.reference.settlement_key,
        )
        allocation = ReconciliationTitleAllocation.objects.create(
            organization_id=account.organization_id,
            batch=batch,
            financial_account=account,
            movement=movement,
            movement_identity=_bank_identity(movement),
            movement_fingerprint=_bank_fingerprint(movement),
            title_key=row.reference.title_key,
            installment_key=row.reference.installment_key,
            settlement_key=row.reference.settlement_key,
            settlement_identity=event_id,
            settlement_fingerprint=prepared.settlements[event_id][1],
            cash_cents=row.cash_cents,
        )
        ReconciliationTitleDecision.objects.create(
            organization_id=account.organization_id,
            allocation=allocation,
            state="confirmed",
            actor=actor,
            reason=reason,
        )
    record_event(
        action="hub.reconciliation.title_allocations_confirmed",
        organization=account.organization,
        actor=actor,
        target=batch,
        metadata={"count": len(prepared.plan.preview.allocations), "snapshot_id": str(snapshot.pk)},
    )
    return batch, True


@transaction.atomic
def undo_title_allocation(
    *, allocation: ReconciliationTitleAllocation, actor: User, reason: str
) -> bool:
    account = _account(allocation.financial_account_id, lock=True)
    authorize_title_account(account, actor)
    reason = _reason(reason)
    current = ReconciliationTitleAllocation.objects.select_for_update().get(
        pk=allocation.pk, organization_id=account.organization_id, financial_account=account
    )
    if current.state == "undone":
        return False
    current.state = "undone"
    current.save(update_fields=["state", "updated_at"])
    ReconciliationTitleDecision.objects.create(
        organization_id=account.organization_id,
        allocation=current,
        state="undone",
        actor=actor,
        reason=reason,
    )
    record_event(
        action="hub.reconciliation.title_allocation_undone",
        organization=account.organization,
        actor=actor,
        target=current,
        metadata={"batch_id": str(current.batch_id)},
    )
    return True
