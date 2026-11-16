"""Immutable fiscal payment provenance and company-wide cash capacity.

Account-specific allocation identifiers remain unchanged. Only explicitly reviewed
native payments share capacity; neither bank linkage nor component semantics is inferred.
"""

from __future__ import annotations

import hashlib
from dataclasses import asdict
from typing import Any

from apps.hub.models import (
    FinancialAccount,
    ReconciliationTitleAllocation,
    ReconciliationTitleSnapshot,
)
from apps.hub.title_contract import TitleContractError, TitleSnapshot
from apps.intelligence.models import (
    CompanyTitleCollection,
    NativeTitleCollection,
    NativeTitleSettlementProvenance,
)
from apps.intelligence.native_title_comparison import TitleSourceEvidence, _validated
from apps.intelligence.native_title_contract import MAX_BYTES, canonical_hash, is_automatic_scope

CONFLICT = (
    "Esta baixa de origem já possui vínculo bancário com outra interpretação ou agrupamento. "
    "Desfaça os vínculos anteriores antes de alterá-la."
)


def _keys(row: Any) -> tuple[str, str, str]:
    return row.title_key, row.installment_key, row.settlement_key


def _digest(row: NativeTitleSettlementProvenance) -> str:
    return canonical_hash(
        {
            "organization": str(row.organization_id),
            "company": str(row.company_id),
            "snapshot": str(row.snapshot_id),
            "source": str(row.source_file_id),
            "capture": str(row.capture_id),
            "source_sha256": row.source_sha256,
            "keys": list(_keys(row)),
            "payment_references": row.payment_references,
            "interpretation": row.interpretation,
        }
    )


def _signature(row: NativeTitleSettlementProvenance) -> tuple[Any, Any]:
    return row.payment_references, row.interpretation


def _overlaps(
    left: NativeTitleSettlementProvenance, right: NativeTitleSettlementProvenance
) -> bool:
    return bool(
        left.interpretation["event_identity"] == right.interpretation["event_identity"]
        or set(left.payment_references).intersection(right.payment_references)
    )


def _unique_events(rows: Any) -> None:
    events: set[str] = set()
    references: set[str] = set()
    for row in rows:
        identity = row.interpretation["event_identity"]
        if identity in events or references.intersection(row.payment_references):
            raise TitleContractError(
                "Agrupamento conflitante: reúna todos os componentes da mesma baixa de origem "
                "em uma única interpretação. O caixa pode ser alocado parcialmente entre contas."
            )
        events.add(identity)
        references.update(row.payment_references)


def _verify(row: NativeTitleSettlementProvenance, company_id: Any, checked: set[Any]) -> None:
    if (
        row.company_id != company_id
        or row.snapshot.company_id != company_id
        or row.snapshot.organization_id != row.organization_id
        or row.fingerprint != _digest(row)
        or not isinstance(row.payment_references, list)
        or not row.payment_references
        or row.payment_references != sorted(set(row.payment_references))
        or not isinstance(row.interpretation, dict)
        or set(row.interpretation)
        != {"event_identity", "kind", "principal_cents", "due_on", "settlement"}
    ):
        raise TitleContractError("A proveniência da baixa precisa de revisão de integridade.")
    if row.source_file_id in checked:
        return
    legacy = NativeTitleCollection.objects.filter(
        pk=row.capture_id, organization_id=row.organization_id
    ).first()
    modern = CompanyTitleCollection.objects.filter(
        pk=row.capture_id, organization_id=row.organization_id
    ).first()
    if (legacy is None) == (modern is None):
        raise TitleContractError("A origem da baixa está ausente ou ambígua.")
    job = legacy if legacy is not None else modern
    assert job is not None
    source = row.source_file
    if (
        job.state != "captured"
        or is_automatic_scope(job.scope) != isinstance(job, CompanyTitleCollection)
        or job.scope_revision != canonical_hash(job.scope)
        or job.source_file_id != source.pk
        or job.content_hash != row.source_sha256
        or source.organization_id != row.organization_id
        or source.company_id != row.company_id
        or source.content_hash != row.source_sha256
        or source.origin != "obligation"
        or source.kind != "json"
        or source.financial_account_id != (legacy.financial_account_id if legacy else None)
        or (modern and modern.company_id != row.company_id)
    ):
        raise TitleContractError(
            "A fonte original da baixa mudou. Confira a origem antes de alocar."
        )
    try:
        with source.content.open("rb") as stream:
            content = stream.read(MAX_BYTES + 1)
        if (
            len(content) != source.size_bytes
            or hashlib.sha256(content).hexdigest() != row.source_sha256
        ):
            raise ValueError
        _validated(TitleSourceEvidence(content, job.scope, row.source_sha256, job.contract_hash))
    except (OSError, ValueError):
        raise TitleContractError(
            "A fonte original da baixa não passou na verificação de integridade."
        ) from None
    checked.add(row.source_file_id)


def _rows(company_id: Any, installment_keys: set[str]) -> list[NativeTitleSettlementProvenance]:
    return list(
        NativeTitleSettlementProvenance.objects.filter(
            company_id=company_id, installment_key__in=installment_keys
        )
        .select_related("snapshot", "source_file")
        .order_by("created_at", "id")
    )


def _active(company_id: Any, installment_keys: set[str]) -> list[ReconciliationTitleAllocation]:
    return list(
        ReconciliationTitleAllocation.objects.filter(
            financial_account__company_id=company_id,
            installment_key__in=installment_keys,
            state="confirmed",
        )
        .select_related(
            "batch__snapshot__source_file",
            "financial_account__company",
            "financial_account__organization",
        )
        .order_by("id")
    )


def _active_provenance(
    allocation: ReconciliationTitleAllocation,
    rows: list[NativeTitleSettlementProvenance],
    checked: set[Any],
    snapshots: dict[Any, Any],
) -> NativeTitleSettlementProvenance | None:
    from apps.hub.title_persistence import _load, _settlements

    candidates = [row for row in rows if _keys(row) == _keys(allocation)]
    if not candidates:
        return None  # Existing manually normalized title contracts remain account-scoped.
    account = allocation.financial_account
    if (
        allocation.organization_id != account.organization_id
        or allocation.batch.organization_id != account.organization_id
        or allocation.batch.financial_account_id != account.pk
    ):
        raise TitleContractError("O histórico de baixas contém um vínculo fora da empresa.")
    if allocation.batch.snapshot_id not in snapshots:
        _, parsed = _load(allocation.batch.snapshot, account)
        snapshots[allocation.batch.snapshot_id] = _settlements(parsed, account)
    settlement = snapshots[allocation.batch.snapshot_id].get(allocation.settlement_identity)
    if settlement is None or settlement[1] != allocation.settlement_fingerprint:
        raise TitleContractError("Uma baixa já alocada mudou; revise o vínculo anterior.")
    matching = [row for row in candidates if row.snapshot_id == allocation.batch.snapshot_id]
    chosen = matching[0] if matching else candidates[0]
    _verify(chosen, account.company_id, checked)
    if chosen.interpretation["settlement"] != {
        **asdict(settlement[0]),
        "posted_on": settlement[0].posted_on.isoformat(),
    }:
        raise TitleContractError(CONFLICT)
    return chosen


def shared_native_usage(
    *, account: FinancialAccount, snapshot: ReconciliationTitleSnapshot, parsed: TitleSnapshot
) -> tuple[dict[str, int], list[list[Any]]]:
    """Return additional committed cash in other accounts; never count own cash twice."""
    from apps.hub.title_persistence import _settlement_identity

    installment_keys = {part.key for title in parsed.titles for part in title.installments}
    rows = _rows(account.company_id, installment_keys)
    if not rows:
        return {}, []
    selected: dict[str, NativeTitleSettlementProvenance] = {}
    checked: set[Any] = set()
    for title in parsed.titles:
        for part in title.installments:
            for event in part.settlements:
                candidates = [row for row in rows if _keys(row) == (title.key, part.key, event.key)]
                if not candidates:
                    continue
                own = [row for row in candidates if row.snapshot_id == snapshot.pk]
                row = own[0] if own else candidates[0]
                _verify(row, account.company_id, checked)
                expected = {
                    "kind": title.kind,
                    "principal_cents": part.principal_cents,
                    "due_on": part.due_on.isoformat() if part.due_on else None,
                    "settlement": {**asdict(event), "posted_on": event.posted_on.isoformat()},
                }
                if any(row.interpretation[key] != value for key, value in expected.items()):
                    raise TitleContractError(CONFLICT)
                selected[_settlement_identity(account, title.key, part.key, event.key)] = row
    _unique_events(selected.values())
    used: dict[str, int] = {}
    affected = []
    snapshots: dict[Any, Any] = {}
    for allocation in _active(account.company_id, installment_keys):
        prior = _active_provenance(allocation, rows, checked, snapshots)
        if prior is None:
            continue
        for identity, current in selected.items():
            if not _overlaps(prior, current):
                continue
            if _signature(prior) != _signature(current):
                raise TitleContractError(CONFLICT)
            if allocation.financial_account_id != account.pk:
                used[identity] = used.get(identity, 0) + allocation.cash_cents
                affected.append([str(allocation.pk), allocation.cash_cents])
    return used, affected


def proposed_provenance(
    *,
    account: FinancialAccount,
    job: Any,
    payload: dict[str, Any],
    provenance: list[dict[str, Any]],
) -> list[NativeTitleSettlementProvenance]:
    result = []
    for entry in provenance:
        title = next(t for t in payload["titles"] if t["key"] == entry["title_key"])
        part = next(p for p in title["installments"] if p["key"] == entry["installment_key"])
        for event in entry["settlements"]:
            normalized = next(e for e in part["settlements"] if e["key"] == event["settlement_key"])
            result.append(
                NativeTitleSettlementProvenance(
                    organization_id=account.organization_id,
                    company_id=account.company_id,
                    source_file_id=job.source_file_id,
                    capture_id=job.pk,
                    source_sha256=job.content_hash,
                    title_key=title["key"],
                    installment_key=part["key"],
                    settlement_key=event["settlement_key"],
                    payment_references=event["payment_references"],
                    interpretation={
                        "event_identity": event["event_identity"],
                        "kind": title["kind"],
                        "principal_cents": part["principal_cents"],
                        "due_on": part["due_on"],
                        "settlement": normalized,
                    },
                )
            )
    return result


def validate_native_revision(
    *,
    account: FinancialAccount,
    proposed: list[NativeTitleSettlementProvenance],
    installments: set[tuple[str, str]],
) -> None:
    _unique_events(proposed)
    installment_keys = {key for _, key in installments}
    rows = _rows(account.company_id, installment_keys)
    checked: set[Any] = set()
    snapshots: dict[Any, Any] = {}
    for allocation in _active(account.company_id, installment_keys):
        if (allocation.title_key, allocation.installment_key) not in installments:
            continue
        prior = _active_provenance(allocation, rows, checked, snapshots)
        if prior is None:
            # A pre-migration native allocation cannot safely acquire fresh company capacity.
            raise TitleContractError(
                "Esta parcela já tem vínculo anterior sem proveniência nativa. "
                "Desfaça-o e revise a fonte antes de continuar."
            )
        matches = [row for row in proposed if _overlaps(prior, row)]
        if len(matches) != 1 or _signature(prior) != _signature(matches[0]):
            raise TitleContractError(CONFLICT)


def persist_native_provenance(
    *,
    account: FinancialAccount,
    snapshot: ReconciliationTitleSnapshot,
    proposed: list[NativeTitleSettlementProvenance],
    installments: set[tuple[str, str]],
    previous: ReconciliationTitleSnapshot | None = None,
) -> None:
    carried = (
        list(
            NativeTitleSettlementProvenance.objects.filter(snapshot=previous).select_related(
                "snapshot", "source_file"
            )
        )
        if previous
        else []
    )
    checked: set[Any] = set()
    for old in carried:
        if (old.title_key, old.installment_key) in installments:
            continue
        _verify(old, account.company_id, checked)
        proposed.append(
            NativeTitleSettlementProvenance(
                organization_id=old.organization_id,
                company_id=old.company_id,
                source_file_id=old.source_file_id,
                capture_id=old.capture_id,
                source_sha256=old.source_sha256,
                title_key=old.title_key,
                installment_key=old.installment_key,
                settlement_key=old.settlement_key,
                payment_references=old.payment_references,
                interpretation=old.interpretation,
            )
        )
    for row in proposed:
        existing = NativeTitleSettlementProvenance.objects.filter(
            snapshot=snapshot,
            title_key=row.title_key,
            installment_key=row.installment_key,
            settlement_key=row.settlement_key,
        ).first()
        if existing:
            if _signature(existing) != _signature(row):
                raise TitleContractError("A proveniência preservada diverge desta revisão.")
            continue
        row.snapshot = snapshot
        row.fingerprint = _digest(row)
        row.save()
