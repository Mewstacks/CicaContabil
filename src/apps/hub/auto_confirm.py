"""D-388: unique exact bank/Razão pairs are confirmed by the system, not by an extra click."""

from __future__ import annotations

import calendar
from datetime import date
from typing import Any

from django.db import transaction

from apps.audit.services import record_event

AUTO_NOTE = (
    "Confirmação automática (D-388): data, valor, direção e conta iguais a um único "
    "registro do Razão."
)


def _month_period(month: date) -> dict[str, date]:
    last = calendar.monthrange(month.year, month.month)[1]
    return {"start": month.replace(day=1), "end": month.replace(day=last)}


def auto_confirm_exact(*, source: Any, month: date, actor: Any) -> int:
    """Confirm every unique exact pair of one bank statement in one month; never raises."""

    from apps.hub.models import ClientCompany, ReconciliationSourceFile
    from apps.hub.reconciliation_service import confirm_reconciliation
    from apps.hub.reconciliation_workbench import exact_conference_pairs

    if (
        source is None
        or actor is None
        or source.origin != ReconciliationSourceFile.Origin.BANK_STATEMENT
        or not source.financial_account_id
    ):
        return 0
    period = _month_period(month)
    try:
        with transaction.atomic():
            ClientCompany.objects.select_for_update().get(pk=source.company_id)
            pairs = exact_conference_pairs(source, period)[:1000]
            for movement, record in pairs:
                reconciliation = confirm_reconciliation(
                    movement=movement,
                    entry=record.entry,
                    amount_cents=abs(movement.amount_cents),
                    evidence={
                        "note": AUTO_NOTE,
                        "source": movement.source_reference,
                        "batch": True,
                        "automatic": True,
                    },
                    actor=actor,
                )
                record_event(
                    action="hub.reconciliation.reconciliation_confirmed",
                    actor=actor,
                    organization=source.organization,
                    target=reconciliation,
                    metadata={
                        "movement_id": str(movement.id),
                        "entry_id": str(reconciliation.entry_id),
                        "amount_cents": reconciliation.amount_cents,
                        "batch": True,
                        "automatic": True,
                    },
                )
            if pairs:
                record_event(
                    action="hub.reconciliation.exact_matches_confirmed",
                    actor=actor,
                    organization=source.organization,
                    target=source,
                    metadata={
                        "count": len(pairs),
                        "automatic": True,
                        "period": {key: str(value) for key, value in period.items()},
                    },
                )
            return len(pairs)
    except Exception:
        return 0


def auto_confirm_for_job(job: Any) -> int:
    """After a Razão arrives, confirm exact pairs of the statement it was requested for."""

    from apps.hub.models import ReconciliationSourceFile

    try:
        month = date.fromisoformat(str(job.scope.get("period_start")))
    except (TypeError, ValueError):
        return 0
    sources = []
    if job.bank_source_id:
        sources.append(job.bank_source)
    else:
        sources.extend(
            ReconciliationSourceFile.objects.filter(
                financial_account_id=job.financial_account_id,
                origin=ReconciliationSourceFile.Origin.BANK_STATEMENT,
            )
        )
    return sum(
        auto_confirm_exact(source=source, month=month, actor=job.requested_by) for source in sources
    )


def auto_confirm_after_run(run_id: str) -> int:
    """When a statement finishes processing after its Razão already arrived (D-388)."""

    from apps.hub.models import ReconciliationRun, ReconciliationSourceFile
    from apps.intelligence.models import NativeLedgerCollection

    run = ReconciliationRun.objects.select_related("source_file").filter(pk=run_id).first()
    source = run.source_file if run else None
    if (
        source is None
        or source.origin != ReconciliationSourceFile.Origin.BANK_STATEMENT
        or not source.financial_account_id
    ):
        return 0
    total = 0
    jobs = NativeLedgerCollection.objects.filter(
        financial_account_id=source.financial_account_id,
        state=NativeLedgerCollection.State.IMPORTED,
    ).select_related("requested_by")
    for job in jobs:
        try:
            month = date.fromisoformat(str(job.scope.get("period_start")))
        except (TypeError, ValueError):
            continue
        total += auto_confirm_exact(source=source, month=month, actor=job.requested_by)
    return total
