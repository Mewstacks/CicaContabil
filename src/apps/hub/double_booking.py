"""D-397: keep direct-use automatic entries (D-393) from booking twice what the office booked.

* A bank movement is "similar" to the Razão when a record of the same bank account, direction and
  amount exists within ``SIMILAR_DAYS`` calendar days and that record is not already confirmed with
  another movement. Similar movements are never posted automatically.
* An automatic entry only goes into the Domínio file once a Razão of its account and month arrived
  *after* the entry was approved; at file generation, an automatic entry that became similar (or
  was confirmed against the Razão) is withdrawn instead of exported.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from apps.audit.models import AuditEvent
from apps.audit.services import record_event
from apps.hub.models import (
    FinancialAccount,
    IndependentLedgerRecord,
    JournalEntry,
    MovementReconciliation,
    NormalizedMovement,
    ReconciliationSourceFile,
)

DECISION = "D-397"
SIMILAR_DAYS = 5
POSTED_ACTION = "hub.reconciliation.direct_use_posted"
WITHDRAWN_ACTION = "hub.reconciliation.direct_use_withdrawn"

LedgerIndex = dict[tuple[str, int], list[tuple[date, frozenset[Any]]]]


def ledger_index(account: FinancialAccount) -> LedgerIndex:
    """Razão records of the account by (direction, amount), with the movements they confirm."""
    confirmed: dict[Any, set[Any]] = defaultdict(set)
    for entry_id, movement_id in MovementReconciliation.objects.filter(
        organization_id=account.organization_id,
        state=MovementReconciliation.State.CONFIRMED,
        entry__independent_source__financial_account=account,
    ).values_list("entry_id", "movement_id"):
        confirmed[entry_id].add(movement_id)
    index: LedgerIndex = defaultdict(list)
    for entry_id, occurred, direction, amount in IndependentLedgerRecord.objects.filter(
        organization_id=account.organization_id, financial_account=account
    ).values_list(
        "entry_id",
        "accounting_entry__occurred_on",
        "accounting_entry__direction",
        "accounting_entry__amount_cents",
    ):
        if occurred:
            index[(str(direction), abs(int(amount or 0)))].append(
                (occurred, frozenset(confirmed.get(entry_id, ())))
            )
    return index


def is_similar(index: LedgerIndex, movement: NormalizedMovement) -> bool:
    """A free Razão record close enough in date may be this very booking: never post it."""
    if movement.occurred_on is None:
        return False
    for occurred, used_by in index.get((movement.direction, abs(movement.amount_cents)), ()):
        if abs((occurred - movement.occurred_on).days) <= SIMILAR_DAYS and not (
            used_by - {movement.pk}
        ):
            return True
    return False


def razao_read_after(account: FinancialAccount, month: date, moment: datetime | None) -> bool:
    """A Razão of this account and month arrived after ``moment`` (agent or CSV import)."""
    from apps.intelligence.models import NativeLedgerCollection

    if moment is None:
        return False
    for scope in NativeLedgerCollection.objects.filter(
        financial_account=account,
        state=NativeLedgerCollection.State.IMPORTED,
        completed_at__gt=moment,
    ).values_list("scope", flat=True):
        try:
            start = date.fromisoformat(str((scope or {}).get("period_start")))
        except (TypeError, ValueError):
            continue
        if (start.year, start.month) == (month.year, month.month):
            return True
    return ReconciliationSourceFile.objects.filter(
        organization_id=account.organization_id,
        financial_account=account,
        origin=ReconciliationSourceFile.Origin.ACCOUNTING,
        created_at__gt=moment,
    ).exists()


def automatic_entry_ids(entry_ids: list[Any]) -> set[str]:
    return set(
        AuditEvent.objects.filter(
            action=POSTED_ACTION, target_id__in=[str(pk) for pk in entry_ids]
        ).values_list("target_id", flat=True)
    )


@dataclass
class ExportCheck:
    held: dict[tuple[Any, date], int] = field(default_factory=dict)
    held_ids: set[str] = field(default_factory=set)
    withdrawn: int = 0
    accounts: dict[Any, FinancialAccount] = field(default_factory=dict)

    def held_months(self) -> list[dict[str, Any]]:
        rows = []
        for (account_id, month), count in sorted(
            self.held.items(), key=lambda item: (str(item[0][0]), item[0][1])
        ):
            account = self.accounts[account_id]
            rows.append(
                {
                    "account": account,
                    "company_id": account.company_id,
                    "month": month,
                    "count": count,
                }
            )
        return rows

    def message(self) -> str:
        months = ", ".join(
            f"{row['account'].name} {row['month']:%m/%Y}" for row in self.held_months()
        )
        return (
            f"{len(self.held_ids)} lançamento(s) da CICA aguardam o Razão atualizado de {months}. "
            "Atualize o Razão em Extrato e Razão e gere o arquivo de novo."
        )


def check_export(
    *, organization: Any, company: Any, start: date, end: date, withdraw: bool
) -> ExportCheck:
    """Hold automatic entries without a newer Razão; withdraw the ones the Razão now covers."""
    from apps.hub.direct_use import direct_use_enabled
    from apps.hub.reconciliation_bridge import movement_has_ledger_match

    result = ExportCheck()
    if not direct_use_enabled(organization):
        return result
    entries = list(
        JournalEntry.objects.filter(
            organization=organization,
            company=company,
            state=JournalEntry.State.APPROVED,
            occurred_on__range=(start, end),
            movement__isnull=False,
        )
        .exclude(purpose="source_ledger")
        .select_related("movement", "movement__financial_account")
        .order_by("occurred_on", "id")
    )
    automatic = automatic_entry_ids([entry.pk for entry in entries])
    indexes: dict[Any, LedgerIndex] = {}
    for entry in entries:
        if str(entry.pk) not in automatic:
            continue
        movement = entry.movement
        account = movement.financial_account if movement else None
        if movement is None or account is None:
            continue
        result.accounts[account.pk] = account
        if account.pk not in indexes:
            indexes[account.pk] = ledger_index(account)
        reason = ""
        if movement_has_ledger_match(movement):
            reason = "conferido_com_o_razao"
        elif is_similar(indexes[account.pk], movement):
            reason = "parecido_com_o_razao"
        if reason:
            if withdraw:
                JournalEntry.objects.filter(pk=entry.pk, state=JournalEntry.State.APPROVED).update(
                    state=JournalEntry.State.INVALID
                )
                record_event(
                    action=WITHDRAWN_ACTION,
                    actor=None,
                    organization=organization,
                    target=entry,
                    metadata={"decision": DECISION, "reason": reason},
                )
            result.withdrawn += 1
            result.held_ids.add(str(entry.pk))
            continue
        month = entry.occurred_on.replace(day=1)
        if not razao_read_after(account, month, entry.approved_at):
            key = (account.pk, month)
            result.held[key] = result.held.get(key, 0) + 1
            result.held_ids.add(str(entry.pk))
    return result


def statement_complement(history: str, description: str) -> str:
    """Rule history followed by the bank text, so the office recognises the document."""
    history, description = (history or "").strip(), (description or "").strip()
    if not description or description.casefold() in history.casefold():
        return history[:500]
    if not history:
        return description[:500]
    return f"{history} · {description}"[:500]


def withdraw_covered(account: FinancialAccount) -> int:
    """After a Razão arrives, automatic entries it now covers (confirmed/similar) are withdrawn."""
    from apps.hub.reconciliation_bridge import movement_has_ledger_match

    entries = list(
        JournalEntry.objects.filter(
            organization_id=account.organization_id,
            state=JournalEntry.State.APPROVED,
            movement__financial_account=account,
        ).select_related("movement", "organization")
    )
    automatic = automatic_entry_ids([entry.pk for entry in entries])
    index = None
    count = 0
    for entry in entries:
        if str(entry.pk) not in automatic or entry.movement is None:
            continue
        if index is None:
            index = ledger_index(account)
        if movement_has_ledger_match(entry.movement):
            reason = "conferido_com_o_razao"
        elif is_similar(index, entry.movement):
            reason = "parecido_com_o_razao"
        else:
            continue
        JournalEntry.objects.filter(pk=entry.pk, state=JournalEntry.State.APPROVED).update(
            state=JournalEntry.State.INVALID
        )
        record_event(
            action=WITHDRAWN_ACTION,
            actor=None,
            organization=entry.organization,
            target=entry,
            metadata={"decision": DECISION, "reason": reason},
        )
        count += 1
    return count


def pending_export_summary(office: Any, companies: Any) -> list[dict[str, Any]]:
    """Per company: approved entries ready for the Domínio file and the ones awaiting the Razão."""
    from django.db.models import Max, Min

    from apps.hub.direct_use import direct_use_enabled

    if not direct_use_enabled(office):
        return []
    rows = []
    approved = (
        JournalEntry.objects.filter(
            organization=office, company__in=companies, state=JournalEntry.State.APPROVED
        )
        .exclude(purpose="source_ledger")
        .values("company_id")
        .annotate(first=Min("occurred_on"), last=Max("occurred_on"))
    )
    for item in approved:
        company = companies.get(pk=item["company_id"])
        check = check_export(
            organization=office,
            company=company,
            start=item["first"],
            end=item["last"],
            withdraw=False,
        )
        total = (
            JournalEntry.objects.filter(
                organization=office,
                company=company,
                state=JournalEntry.State.APPROVED,
            )
            .exclude(purpose="source_ledger")
            .count()
        )
        rows.append(
            {
                "company": company,
                "ready": max(total - len(check.held_ids), 0),
                "held": check.held_months(),
                "first": item["first"],
                "last": item["last"],
            }
        )
    return sorted(rows, key=lambda row: row["company"].name)
