"""Scoped, read-only title catalog and globally committed cash capacity."""

from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from django.core.exceptions import PermissionDenied

from apps.accounts.models import User
from apps.hub.controlplane import company_queryset_for_module
from apps.hub.models import (
    FinancialAccount,
    NormalizedMovement,
    ProductModule,
    ReconciliationTitleAllocation,
    ReconciliationTitleDecision,
    ReconciliationTitleSnapshot,
)
from apps.hub.reconciliation_report import _money
from apps.hub.title_contract import TitleContractError, TitleSnapshot
from apps.hub.title_persistence import (
    _account,
    _bank_fingerprint,
    _bank_identity,
    _load,
    _settlement_identity,
    _settlements,
    _verify_bank_source,
    latest_title_snapshot,
)
from apps.organizations.models import Membership
from apps.platform.operation_access import require_operation_access

MAX_MOVEMENTS = 2500
EDIT_ROLES = {"owner", "admin", "manager", "operator"}
KIND_LABELS = {"payable": "A pagar", "receivable": "A receber"}
DIRECTION_LABELS = {"inflow": "Entrada", "outflow": "Saída"}


def authorize_title_read(account: FinancialAccount, actor: User) -> Membership:
    """Recheck live scope before reading files, including for a read-only auditor."""
    account = _account(account.pk)
    membership = Membership.objects.select_related("organization").filter(
        organization_id=account.organization_id,
        user=actor,
        user__is_active=True,
        is_active=True,
        role__in=[*EDIT_ROLES, Membership.Role.AUDITOR],
    ).first()
    if (
        membership is None
        or account.company.organization_id != account.organization_id
        or not company_queryset_for_module(membership, ProductModule.Code.RECONCILIATION)
        .filter(pk=account.company_id).exists()
    ):
        raise PermissionDenied("Seu acesso atual não permite consultar títulos desta conta.")
    require_operation_access(account.organization, ProductModule.Code.RECONCILIATION)
    return membership


def load_latest_title_snapshot(
    *, account: FinancialAccount, actor: User, snapshot_id: Any = None,
) -> tuple[ReconciliationTitleSnapshot | None, TitleSnapshot | None]:
    """Never silently fall back to an older, missing or damaged photograph."""
    account = _account(account.pk)
    authorize_title_read(account, actor)
    latest = latest_title_snapshot(account)
    if snapshot_id is not None and (latest is None or str(latest.pk) != str(snapshot_id)):
        raise TitleContractError("A fotografia mudou; abra novamente os títulos desta conta.")
    if latest is None:
        return None, None
    _, parsed = _load(latest, account)
    return latest, parsed


def _amounts(**values: int | None) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in values.items():
        result[f"{key}_cents"] = value
        result[f"{key}_display"] = _money(value)
    return result


def _movement_scope(movement: NormalizedMovement, account: FinancialAccount) -> bool:
    source = movement.source_file
    return (
        movement.organization_id == account.organization_id
        and movement.company_id == account.company_id
        and movement.financial_account_id == account.pk
        and source.organization_id == account.organization_id
        and source.company_id == account.company_id
        and source.financial_account_id == account.pk
        and source.origin == "bank_statement"
    )


def _history(account: FinancialAccount) -> tuple[list[Any], list[Any]]:
    allocations = list(
        ReconciliationTitleAllocation.objects.filter(
            organization_id=account.organization_id, financial_account=account,
        ).select_related("movement__source_file", "batch__snapshot", "batch__reviewed_by")
        .order_by("-created_at", "-id")
    )
    # Relationships are checked before a template can display a foreign source.
    if any(
        not _movement_scope(row.movement, account)
        or row.batch.organization_id != account.organization_id
        or row.batch.financial_account_id != account.pk
        or row.batch.snapshot.organization_id != account.organization_id
        or row.batch.snapshot.financial_account_id != account.pk
        or row.batch.snapshot.company_id != account.company_id
        for row in allocations
    ):
        raise TitleContractError("Histórico fora da empresa ou conta; solicite revisão do vínculo.")
    decisions = list(
        ReconciliationTitleDecision.objects.filter(
            organization_id=account.organization_id, allocation__in=allocations,
        ).select_related("allocation", "actor").order_by("-created_at", "-id")
    )
    return allocations, decisions


def _capacities(
    account: FinancialAccount, parsed: TitleSnapshot, allocations: list[Any],
) -> tuple[dict[str, int], dict[str, int], dict[str, str], set[Any]]:
    bank_used: dict[str, int] = defaultdict(int)
    event_used: dict[str, int] = defaultdict(int)
    bank_fingerprints: dict[str, str] = {}
    checked_sources: set[Any] = set()
    events = _settlements(parsed, account)
    for previous in allocations:
        if previous.state != "confirmed":
            continue
        movement = previous.movement
        event = events.get(previous.settlement_identity)
        if (
            previous.movement_identity != _bank_identity(movement)
            or previous.movement_fingerprint != _bank_fingerprint(movement)
            or previous.settlement_identity != _settlement_identity(
                account, previous.title_key, previous.installment_key, previous.settlement_key,
            )
            or event is None
            or previous.settlement_fingerprint != event[1]
        ):
            raise TitleContractError(
                "Uma fonte ou baixa já alocada mudou; consulte o histórico e desfaça "
                "o vínculo anterior antes de uma nova alocação."
            )
        if movement.source_file_id not in checked_sources:
            _verify_bank_source(movement.source_file)
            checked_sources.add(movement.source_file_id)
        bank_used[previous.movement_identity] += previous.cash_cents
        event_used[previous.settlement_identity] += previous.cash_cents
        bank_fingerprints[previous.movement_identity] = previous.movement_fingerprint
        if (
            bank_used[previous.movement_identity] > abs(movement.amount_cents)
            or event_used[previous.settlement_identity] > event[0].cash_cents
        ):
            raise TitleContractError("Capacidade excedida no histórico; revise as alocações.")
    return bank_used, event_used, bank_fingerprints, checked_sources


def _catalog(
    account: FinancialAccount, parsed: TitleSnapshot, event_used: dict[str, int],
    start: date, end: date, direction: str | None,
) -> tuple[list[Any], list[Any], list[Any]]:
    titles, installments, settlements = [], [], []
    for title in parsed.titles:
        title_row = {
            "key": title.key, "title_key": title.key, "kind": title.kind,
            "kind_label": KIND_LABELS[title.kind], "installment_count": len(title.installments),
            "label": f"{KIND_LABELS[title.kind]} · {title.key}",
        }
        titles.append(title_row)
        for part in title.installments:
            part_row = {
                **title_row, "key": part.key, "installment_key": part.key,
                "due_on": part.due_on, "settlement_count": len(part.settlements),
                "label": f"{title.key} · parcela {part.key}",
                **_amounts(principal=part.principal_cents, outstanding=part.outstanding_cents),
            }
            installments.append(part_row)
            for event in part.settlements:
                if not start <= event.posted_on <= end or (
                    direction is not None and event.direction != direction
                ):
                    continue
                identity = _settlement_identity(account, title.key, part.key, event.key)
                used = event_used.get(identity, 0)
                settlements.append({
                    **part_row, "key": identity, "settlement_key": event.key,
                    "posted_on": event.posted_on, "direction": event.direction,
                    "direction_label": DIRECTION_LABELS[event.direction],
                    "reverses": event.reverses, "is_reversal": event.reverses is not None,
                    "label": (
                        f"{title.key} · parcela {part.key} · baixa {event.key} · "
                        f"{event.posted_on:%d/%m/%Y} · {_money(event.cash_cents - used)} disponível"
                    ),
                    **_amounts(
                        principal=event.principal_cents, interest=event.interest_cents,
                        penalty=event.penalty_cents, fees=event.fees_cents,
                        discount=event.discount_cents, cash=event.cash_cents,
                        allocated=used, remaining=event.cash_cents - used,
                    ),
                    "available": used < event.cash_cents,
                })
    return titles, installments, settlements


def _movements(
    account: FinancialAccount, start: date, end: date, direction: str | None,
    bank_used: dict[str, int], fingerprints: dict[str, str], checked_sources: set[Any],
) -> list[dict[str, Any]]:
    query = NormalizedMovement.objects.filter(
        organization_id=account.organization_id, company_id=account.company_id,
        financial_account=account, source_file__origin="bank_statement",
        occurred_on__range=(start, end),
    ).select_related("source_file").order_by("occurred_on", "created_at", "id")
    if direction is not None:
        query = query.filter(direction=direction)
    movements = list(query[:MAX_MOVEMENTS + 1])
    if len(movements) > MAX_MOVEMENTS:
        raise TitleContractError("Muitos movimentos; reduza o período para até 2.500 registros.")
    identities: dict[str, str] = {}
    rows = []
    for movement in movements:
        if not _movement_scope(movement, account):
            raise TitleContractError("Fonte bancária fora da empresa ou conta revisada.")
        identity, fingerprint = _bank_identity(movement), _bank_fingerprint(movement)
        if (
            (identity in identities and identities[identity] != fingerprint)
            or (identity in fingerprints and fingerprints[identity] != fingerprint)
        ):
            raise TitleContractError(
                "Movimentos com a mesma identidade divergem; revise os extratos antes de alocar."
            )
        if movement.source_file_id not in checked_sources:
            _verify_bank_source(movement.source_file)
            checked_sources.add(movement.source_file_id)
        if identity in identities:
            continue  # Overlapping OFX files represent one bank capacity.
        identities[identity] = fingerprint
        used, cash = bank_used.get(identity, 0), abs(movement.amount_cents)
        issues = []
        if (
            not cash or movement.currency != "BRL"
            or movement.direction != ("inflow" if movement.amount_cents > 0 else "outflow")
            or movement.review_state in {"ignored", "conflict"}
        ):
            issues.append("Revise este movimento antes de alocar uma baixa.")
        rows.append({
            "movement": movement, "id": str(movement.pk), "key": str(movement.pk),
            "identity": identity, "occurred_on": movement.occurred_on,
            "description": movement.original_description, "direction": movement.direction,
            "direction_label": DIRECTION_LABELS.get(movement.direction, "Revisar direção"),
            "label": (
                f"{movement.occurred_on:%d/%m/%Y} · {movement.original_description} · "
                f"{_money(cash - used)} disponível"
            ),
            **_amounts(cash=cash, allocated=used, remaining=cash - used),
            "issues": issues, "available": not issues and used < cash,
        })
    return rows


def build_title_workspace(
    *, account: FinancialAccount, actor: User, start: date, end: date,
    snapshot_id: Any = None, direction: str | None = None,
) -> dict[str, Any]:
    """Read current reviewed facts; integrity errors leave history but no selectable rows."""
    account = _account(account.pk)
    membership = authorize_title_read(account, actor)
    if (
        type(start) is not date or type(end) is not date or start > end
        or (direction is not None and (
            not isinstance(direction, str) or direction not in {"inflow", "outflow"}
        ))
    ):
        raise TitleContractError("Confira o período e a direção solicitados.")
    allocations, decisions = _history(account)
    result: dict[str, Any] = {
        "account": account, "snapshot": None, "parsed": None,
        "title_rows": [], "installment_rows": [], "settlement_rows": [], "movement_rows": [],
        "allocations": allocations, "decisions": decisions,
        "warnings": [], "errors": [], "blocking": False,
        "can_manage": membership.role in EDIT_ROLES and account.active,
        "start": start, "end": end, "direction": direction,
    }
    try:
        snapshot, parsed = load_latest_title_snapshot(
            account=account, actor=actor, snapshot_id=snapshot_id,
        )
        result.update(snapshot=snapshot, parsed=parsed)
        if parsed is None:
            result["warnings"].append("Importe ou revise uma fonte de títulos desta conta.")
            return result
        if end > parsed.as_of:
            raise TitleContractError(
                "O período termina após a posição revisada; ajuste a data final "
                "ou revise uma fonte mais recente."
            )
        bank_used, event_used, fingerprints, checked = _capacities(account, parsed, allocations)
        titles, parts, events = _catalog(account, parsed, event_used, start, end, direction)
        movements = _movements(account, start, end, direction, bank_used, fingerprints, checked)
        result.update(
            title_rows=titles, installment_rows=parts,
            settlement_rows=events, movement_rows=movements,
        )
        if not parsed.settlements_complete:
            result["warnings"].append(
                "A cobertura de baixas é parcial; ausência de baixa não comprova saldo ou quitação."
            )
        if not account.active:
            result["warnings"].append("Conta inativa: consulta e histórico disponíveis.")
    except TitleContractError as exc:
        result["errors"].append(str(exc))
        result["blocking"] = True
    return result
